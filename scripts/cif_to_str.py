#!/usr/bin/env python3
"""
cif_to_str.py -- Convert a CIF file's structure into a TOPAS `str { }` block,
with Wyckoff-position coordinate constraints correctly expressed as TOPAS
equations, rather than three independent free coordinates.

Why this exists (see SKILL.md "Converting a CIF file to str format"):
TOPAS's own bundled `cif1.exe` does a field-by-field pass-through -- it does
NOT check whether an atom's coordinates sit on a special position with
symmetry-imposed relationships between x/y/z (e.g. a site on a mirror plane
that forces y = x, or a diagonal axis that forces z = -x). Writing such a
site's coordinates as three independent values is wrong: refinement could
pull the tied coordinates apart, violating the space group's own symmetry
that the CIF's data already obeys. This script derives those constraints
directly from the CIF's own `_symmetry_equiv_pos_as_xyz` operator list (no
external space-group table needed) and emits the correct TOPAS syntax:

    site O1  x @ 0.1234  y = Get(x);  z 0  occ O-2 1  beq 0.5

confirmed directly by the user (TOPAS-Academic's author) that `Get(x)`
inside a site's own y/z equation resolves to that SAME site's `x` value with
no separate naming needed -- the identical mechanism used internally by the
`Cubic(cv)` macro (`a cv b = Get(a); c = Get(a);`).

Method (per atom site):
  1. Find every symmetry operator (from the CIF's own operator-string list)
     that maps the site's (x,y,z) back to itself, mod 1, within tolerance --
     this is the site's stabilizer (site-symmetry) subgroup. The identity
     operator always stabilizes; if it's the ONLY one, the site is a
     completely general position (x, y, z all independent and free).
  2. For each NON-identity stabilizing operator's rotation-matrix row i
     (i = x, y, or z), classify what it says about coordinate i:
       - row == the i-th unit vector: this operator doesn't constrain
         coordinate i (even though it may constrain the other two).
       - row has its only nonzero entry at position i itself, with
         coefficient -1: coordinate i is pinned to a fixed numeric constant
         (self-inverse equation) -- solved directly from the known numeric
         value already in the CIF, not symbolically.
       - row has its only nonzero entry at a DIFFERENT position j:
         coordinate i is tied to coordinate j (sign and translation offset
         read directly off the matrix row).
       - row is all zero: coordinate i is fixed to the operator's
         translation component alone.
  3. Ties are resolved transitively: if x turns out fixed and y is tied to
     x, y is really also just fixed (not a "y = Get(x)" equation to a
     constant -- TOPAS has no reason to reference a fixed keyword via Get()
     when the literal number is simpler and matches this file's existing
     convention for fully-fixed CeO2-style special positions).
  4. The CIF's stated `_atom_site_site_symmetry_multiplicity` is cross-
     checked against the computed orbit size (number of distinct cosets of
     the stabilizer within the full operator list) -- see
     `check_multiplicity()`. A mismatch means either the site is disordered/
     split (occupancy needs scaling: occ_topas = cif_occ * cif_mult /
     computed_mult) or the coordinates don't sit exactly on the intended
     special position (rounding) -- flagged, not silently "fixed", since
     which of these it is can't be determined from the CIF alone.

Known limitations (be upfront about these, don't claim more than is true):
  - Prefers the CIF's own `_symmetry_equiv_pos_as_xyz` (or
    `_space_group_symop_operation_xyz`) loop. If absent, falls back to
    resolving operators via TOPAS's own space-group database instead of
    guessing: `resolve_sg_operators()` reads an already-generated
    TOPAS_DIR/sg/<symbol>.sg if present, or generates one with
    `sgcom6.exe SYMBOL -dir sg` (run from TOPAS_DIR). This needs TOPAS_DIR
    set and the CIF's space_group string to already be in the concise form
    sgcom6.exe recognizes (`fm-3m`, `p21/n`) -- not CIF's underscore-spaced
    style (`F_M_3_M`). If TOPAS_DIR is unset or the symbol doesn't resolve,
    it says so plainly and emits independent (unconstrained) coordinates
    rather than guessing.
  - Coordinate-tie detection only handles the crystallographically normal
    case of integer (-1/0/1) rotation-matrix entries (true for every
    standard space-group operator) -- this is not a general linear-algebra
    solver.
  - Anisotropic displacement parameters (_atom_site_aniso_U_11 etc.) are
    read and emitted as a `u11 u22 u33 u12 u13 u23` block if present, WITH
    site-symmetry constraints applied via symmetry_utils.classify_adps()
    (the tensor analogue of classify_coordinates -- U must satisfy
    R U R^T = U for every stabilizing rotation R). Verified end-to-end
    against ZrW2O8's real refined aniso data: exact numeric agreement via
    tc.exe + Out_CIF_ADPs for every site. If a site has no aniso data in
    the CIF, it falls back to the isotropic `beq` keyword as before.
  - This is a from-scratch parser for the specific CIF constructs TOPAS
    conversion needs (cell, symmetry operators, atom sites, optional aniso
    loop) -- not a general CIF-dictionary-compliant parser. Unusual/non-
    standard CIF formatting may not parse correctly; verify the output.

Usage:
    python3 cif_to_str.py input.cif                  # print to stdout
    python3 cif_to_str.py input.cif -o output.txt     # write to file
    python3 cif_to_str.py input.cif --tolerance 0.002  # coordinate-match tolerance (default 0.0015)
"""

import sys
import os
import re
import math
import argparse
from fractions import Fraction

from symmetry_utils import (
    parse_symop_string,
    find_stabilizer,
    classify_coordinates,
    check_multiplicity,
    determine_fixed_angles,
    determine_length_ties,
    resolve_sg_operators,
    snap_to_fraction,
    classify_adps,
    format_adp_tie,
    ADP_NAMES,
    COORD_NAME,
)


# ---------------------------------------------------------------------------
# CIF parsing (minimal, targeted at exactly what conversion needs)
# ---------------------------------------------------------------------------

def strip_cif_uncertainty(s):
    """'5.410278(11)' -> '5.410278'; also strips a non-numeric uncertainty
    placeholder like '0.010(X)' -> '0.010' (real value, undetermined
    uncertainty -- seen in the wild). Bare numbers pass through unchanged."""
    return re.sub(r"\([^)]*\)", "", s).strip()


def parse_cif_value(s):
    s = strip_cif_uncertainty(s)
    if s in (".", "?", ""):
        return None
    try:
        return float(s)
    except ValueError:
        # Malformed numeric field (e.g. a stray '..0794' typo) -- treat as
        # missing rather than crashing the whole file's conversion; callers
        # already handle None (e.g. per-site skip for missing coordinates).
        return None


def read_cif_lines(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()


def find_scalar_tag(lines, tag):
    """Find a single-value CIF tag like '_cell_length_a 5.410278(11)'."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(tag) and (len(stripped) == len(tag) or stripped[len(tag)].isspace()):
            rest = stripped[len(tag):].strip()
            if rest:
                # value may itself be quoted
                m = re.match(r"""^['"]?(.*?)['"]?$""", rest)
                return m.group(1) if m else rest
    return None


def parse_cif_loop(lines, required_tags):
    """
    Find a `loop_` block whose tag list is a superset of required_tags
    (order-independent), and return (tag_order, list_of_row_dicts).
    Handles values spanning multiple physical lines only in the simple case
    of one value per line after the tag block (typical for these CIFs);
    does not handle CIF multi-line text fields (';'-delimited) beyond
    skipping them as opaque.
    """
    n = len(lines)
    i = 0
    while i < n:
        if lines[i].strip() == "loop_":
            j = i + 1
            tags = []
            while j < n and lines[j].strip().startswith("_"):
                tags.append(lines[j].strip())
                j += 1
            if set(required_tags).issubset(set(tags)):
                rows = []
                while j < n:
                    line = lines[j].strip()
                    if not line or line.startswith("_") or line.startswith("loop_") or line.startswith("#"):
                        if not line:
                            j += 1
                            continue
                        break
                    if line.startswith("data_") or line == "loop_":
                        break
                    # tokenize respecting single/double-quoted fields
                    tokens = re.findall(r"'[^']*'|\"[^\"]*\"|\S+", line)
                    if len(tokens) < len(tags):
                        j += 1
                        continue
                    cleaned = [t.strip("'\"") for t in tokens[:len(tags)]]
                    rows.append(dict(zip(tags, cleaned)))
                    j += 1
                return tags, rows
            i = j
        else:
            i += 1
    return None, []



# ---------------------------------------------------------------------------
# CIF-specific helper
# ---------------------------------------------------------------------------

def parse_formula_elements(formula_sum):
    """Bare element symbols appearing in a CIF's _chemical_formula_sum
    (e.g. \"Na4 Al2 Si2 O61 S6 Cl0.4\" -> {'Na','Al','Si','O','S','Cl'}) --
    used by guess_element_symbol to disambiguate an ambiguous 2-letter site
    label against elements the structure is actually reported to contain."""
    if not formula_sum:
        return set()
    s = formula_sum.strip().strip("'\"")
    return {m.group(1) for m in re.finditer(r"([A-Z][a-z]?)\d*\.?\d*", s)}


def guess_element_symbol(label, formula_elements=None):
    """
    Fallback when the CIF has no _atom_site_type_symbol column: strip a
    trailing digit/suffix off the site label (CIF convention: 'O1', 'O2',
    'Fe2' name distinct sites of the same element) to recover a plausible
    scattering-factor name for TOPAS's `occ` keyword. Not guaranteed correct
    for unusual labels -- callers should surface this as a warning.

    Prefers the 2-letter reading when it's a real tabulated element (e.g.
    'PT1' -> 'Pt', not 'P') -- a case-sensitive first-letter-only match
    misreads any ALL-CAPS two-letter-element label this way. BUT this is
    genuinely ambiguous when the 2-letter reading collides with an
    unrelated element that's implausible for the structure -- confirmed in
    the wild: label 'OS1' (a common "Oxygen of Sulfate" site-naming
    convention) was misread as Osmium 'Os' purely because Os happens to be
    tabulated, when the CIF's own formula contained no osmium at all. If
    `formula_elements` (the CIF's own _chemical_formula_sum, parsed via
    parse_formula_elements) is given and disambiguates -- one reading
    matches a real element in the formula, the other doesn't -- that
    reading wins over the bare tabulated-element check. Falls back to the
    tabulated-element heuristic if formula_elements doesn't resolve it
    (not given, or both/neither reading appears in the formula), or to 1
    letter if the 2-letter reading isn't a real element at all.
    """
    m = re.match(r"^([A-Za-z]{1,2})", label)
    if not m:
        return label
    candidate = m.group(1)
    if len(candidate) == 2:
        two_letter = candidate[0].upper() + candidate[1].lower()
        one_letter = candidate[0].upper()
        if formula_elements:
            two_in = two_letter in formula_elements
            one_in = one_letter in formula_elements
            if one_in and not two_in:
                return one_letter
            if two_in and not one_in:
                return two_letter
        table = load_atmscat_symbols()
        if not table or two_letter in table:
            return two_letter
    return candidate[0].upper()


ADP_CIF_TAGS = {
    "u11": "_atom_site_aniso_U_11", "u22": "_atom_site_aniso_U_22", "u33": "_atom_site_aniso_U_33",
    "u12": "_atom_site_aniso_U_12", "u13": "_atom_site_aniso_U_13", "u23": "_atom_site_aniso_U_23",
}


def normalize_species_symbol(symbol):
    """
    CIF's _atom_site_type_symbol writes oxidation state as
    <element><magnitude><sign> (e.g. 'Te6+', 'O2-', 'Fe3+'), but TOPAS's
    atmscat.txt / `occ` keyword expects <element><sign><magnitude> (e.g.
    'Te+6', 'O-2', 'Fe+3') -- confirmed directly against atmscat.txt entries
    (Na+1, Cl-1, Ti+4, ...). Passed straight through unchanged if it's
    already TOPAS-order, has no charge, or doesn't match either pattern.
    """
    symbol = symbol.strip()
    m = re.match(r"^([A-Za-z]{1,2})(\d*)([+-])$", symbol)
    if m:
        el, num, sign = m.groups()
        return f"{el}{sign}{num or '1'}"
    m = re.match(r"^([A-Za-z]{1,2})([+-])(\d*)$", symbol)
    if m:
        el, sign, num = m.groups()
        return f"{el}{sign}{num or '1'}"
    return symbol


_ATMSCAT_SYMBOLS = None


def load_atmscat_symbols():
    """Cached set of every species name (element or ionic) atmscat.txt has
    scattering-factor coefficients for -- used to check a species before
    emitting it, rather than letting tc.exe fail at runtime."""
    global _ATMSCAT_SYMBOLS
    if _ATMSCAT_SYMBOLS is not None:
        return _ATMSCAT_SYMBOLS
    _ATMSCAT_SYMBOLS = set()
    try:
        import topas_install
        topas_dir, found = topas_install.get_topas_dir()
        if found:
            path = os.path.join(topas_dir, "atmscat.txt")
            if os.path.isfile(path):
                with open(path, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        m = re.match(r"^\s*([A-Za-z]{1,2}(?:[+-]\d+)?)\s", line)
                        if m:
                            _ATMSCAT_SYMBOLS.add(m.group(1))
    except Exception:
        pass
    return _ATMSCAT_SYMBOLS


def resolve_scattering_species(symbol):
    """
    Returns (species_to_emit, warning_or_None). If `symbol` (after CIF->TOPAS
    oxidation-notation normalization) is a tabulated atmscat.txt species, use
    it as-is. Otherwise fall back to the bare neutral element -- the same
    manual workaround applied for V+4 in the first pilot batch -- with an
    explicit warning rather than silently emitting a species tc.exe will
    reject at runtime. If atmscat.txt can't be located at all, the symbol is
    passed through unchecked (no TOPAS_DIR -- can't verify either way).
    """
    normalized = normalize_species_symbol(symbol)
    table = load_atmscat_symbols()
    if not table or normalized in table:
        return normalized, None
    bare = re.match(r"^([A-Za-z]{1,2})", normalized)
    bare = bare.group(1) if bare else normalized
    if bare in table:
        return bare, (
            f"species '{normalized}' (from CIF symbol '{symbol}') is not in atmscat.txt -- "
            f"falling back to neutral '{bare}' for the scattering factor."
        )
    return normalized, (
        f"species '{normalized}' (from CIF symbol '{symbol}') is not in atmscat.txt, and neither "
        f"is the neutral element '{bare}' -- this site will likely fail at runtime, VERIFY."
    )


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def convert(path, tol=0.0015):
    lines = read_cif_lines(path)

    a = parse_cif_value(find_scalar_tag(lines, "_cell_length_a") or "")
    b = parse_cif_value(find_scalar_tag(lines, "_cell_length_b") or "")
    c = parse_cif_value(find_scalar_tag(lines, "_cell_length_c") or "")
    al = parse_cif_value(find_scalar_tag(lines, "_cell_angle_alpha") or "")
    be = parse_cif_value(find_scalar_tag(lines, "_cell_angle_beta") or "")
    ga = parse_cif_value(find_scalar_tag(lines, "_cell_angle_gamma") or "")
    sg = find_scalar_tag(lines, "_symmetry_space_group_name_H-M")
    if sg is None:
        sg = find_scalar_tag(lines, "_space_group_name_H-M_alt")
    if sg is None:
        sg = find_scalar_tag(lines, "_space_group")  # nonstandard but seen in the wild

    formula_elements = parse_formula_elements(find_scalar_tag(lines, "_chemical_formula_sum"))

    sym_tags, sym_rows = parse_cif_loop(lines, ["_symmetry_equiv_pos_as_xyz"])
    if sym_rows == []:
        sym_tags, sym_rows = parse_cif_loop(lines, ["_space_group_symop_operation_xyz"])
    op_key = sym_tags[0] if sym_tags else None
    symops = []
    if op_key:
        for row in sym_rows:
            try:
                symops.append(parse_symop_string(row[op_key]))
            except ValueError:
                continue

    sg_fallback_warning = None
    if not symops and sg:
        symops, sg_header, sg_message = resolve_sg_operators(sg)
        if symops:
            sg_fallback_warning = (
                f"CIF had no _symmetry_equiv_pos_as_xyz loop -- {sg_message}. "
                f"Coordinate/lattice constraints below are derived from TOPAS's own "
                f"space-group database for symbol {sg!r}, not from the CIF's own data -- "
                f"verify this symbol resolved to the setting the CIF actually intends."
            )
        else:
            sg_fallback_warning = (
                f"CIF had no _symmetry_equiv_pos_as_xyz loop, and the sgcom6.exe fallback "
                f"failed ({sg_message}) -- cannot derive Wyckoff or lattice constraints."
            )

    site_tags, site_rows = parse_cif_loop(
        lines, ["_atom_site_label", "_atom_site_fract_x", "_atom_site_fract_y", "_atom_site_fract_z"]
    )

    aniso_tags, aniso_rows = parse_cif_loop(lines, ["_atom_site_aniso_label"] + list(ADP_CIF_TAGS.values()))
    aniso_by_label = {row["_atom_site_aniso_label"]: row for row in aniso_rows} if aniso_rows else {}

    fixed_angles = determine_fixed_angles(symops, (al, be, ga)) if symops else set()
    length_ties = determine_length_ties(symops, (a, b, c), (al, be, ga)) if symops else {}

    out_lines = []
    out_lines.append("str")
    if a is not None:
        out_lines.append(f"   a {a}")
        out_lines.append(f"   b = Get({length_ties['b']});" if "b" in length_ties else f"   b {b}")
        out_lines.append(f"   c = Get({length_ties['c']});" if "c" in length_ties else f"   c {c}")
        if "al" not in fixed_angles:
            out_lines.append(f"   al {al}")
        if "be" not in fixed_angles:
            out_lines.append(f"   be {be}")
        if "ga" not in fixed_angles:
            out_lines.append(f"   ga {ga}")
    if sg:
        sg_topas = sg.replace(" ", "_")
        out_lines.append(f'   space_group "{sg_topas}"')
    out_lines.append("")

    warnings = []
    if sg_fallback_warning:
        warnings.append(sg_fallback_warning)

    for row in site_rows:
        label = row.get("_atom_site_label", "?")
        if "_atom_site_type_symbol" in row:
            type_symbol = row["_atom_site_type_symbol"]
        else:
            type_symbol = guess_element_symbol(label, formula_elements)
            warnings.append(
                f"{label}: CIF has no _atom_site_type_symbol column -- guessed scattering "
                f"species '{type_symbol}' from the site label. Verify this is the correct "
                f"element/ion for the occ keyword."
            )
        type_symbol, species_warning = resolve_scattering_species(type_symbol)
        if species_warning:
            warnings.append(f"{label}: {species_warning}")
        x = parse_cif_value(row.get("_atom_site_fract_x", "0"))
        y = parse_cif_value(row.get("_atom_site_fract_y", "0"))
        z = parse_cif_value(row.get("_atom_site_fract_z", "0"))
        if x is None or y is None or z is None:
            warnings.append(
                f"{label}: fractional coordinate missing/unparseable "
                f"(x={row.get('_atom_site_fract_x')!r}, y={row.get('_atom_site_fract_y')!r}, "
                f"z={row.get('_atom_site_fract_z')!r}) -- site skipped entirely."
            )
            continue
        occ = parse_cif_value(row.get("_atom_site_occupancy", "1")) or 1.0
        if "_atom_site_B_iso_or_equiv" in row:
            beq = parse_cif_value(row.get("_atom_site_B_iso_or_equiv", ""))
        elif "_atom_site_U_iso_or_equiv" in row:
            u_iso = parse_cif_value(row.get("_atom_site_U_iso_or_equiv", ""))
            if u_iso is not None:
                beq = 8 * math.pi ** 2 * u_iso
                warnings.append(
                    f"{label}: CIF gives _atom_site_U_iso_or_equiv (U_iso={u_iso:.6g}) rather than "
                    f"B_iso_or_equiv -- converted to beq = 8*pi^2*U_iso = {beq:.6g}."
                )
            else:
                beq = None
        else:
            beq = None
        cif_mult = row.get("_atom_site_site_symmetry_multiplicity")
        cif_mult = int(cif_mult) if cif_mult and cif_mult.isdigit() else None

        point = (x, y, z)

        if not symops:
            out_lines.append(
                f"   ' {label}: no _symmetry_equiv_pos_as_xyz loop found -- cannot derive "
                f"Wyckoff constraints, emitting independent coordinates (VERIFY MANUALLY)"
            )
            if label in aniso_by_label:
                adp_row = aniso_by_label[label]
                adp_part = "  " + "  ".join(
                    f"{name} @ {(parse_cif_value(adp_row.get(ADP_CIF_TAGS[name], '0')) or 0.0):.10g}"
                    for name in ADP_NAMES
                )
            else:
                adp_part = f"  beq {beq}" if beq is not None else ""
            out_lines.append(
                f"   site {label}  x @ {x}  y @ {y}  z @ {z}  occ {type_symbol} {occ}{adp_part}"
            )
            continue

        stabilizer = find_stabilizer(point, symops, tol)
        constraint = classify_coordinates(point, stabilizer)
        computed_mult = check_multiplicity(point, symops, stabilizer)

        if cif_mult is not None and cif_mult != computed_mult:
            adj_occ = occ * cif_mult / computed_mult
            warnings.append(
                f"{label}: CIF states multiplicity {cif_mult}, computed {computed_mult} from "
                f"symmetry -- occupancy adjusted {occ} -> {adj_occ:.6f} "
                f"(possible disorder/split site, or coordinates not exactly on the special "
                f"position -- verify manually)"
            )
            occ = adj_occ

        coord_parts = []
        has_complex = False
        for i, coord in enumerate(COORD_NAME):
            kind = constraint[coord]
            val = point[i]
            if kind[0] == "free":
                snapped, _ = snap_to_fraction(val, tol)
                coord_parts.append(f"{coord} @ {snapped:.10g}")
            elif kind[0] == "fixed":
                snapped, exact = snap_to_fraction(val, tol)
                if exact is not None and exact.numerator != 0:
                    coord_parts.append(f"{coord} = {exact.numerator}/{exact.denominator};")
                else:
                    coord_parts.append(f"{coord} {snapped:.10g}")
            elif kind[0] == "tied":
                _, other, sign, offset = kind
                tie_body = format_adp_tie([(Fraction(sign), other)])
                if abs(offset) < 1e-6:
                    coord_parts.append(f"{coord} = {tie_body};")
                else:
                    off_snapped, off_exact = snap_to_fraction(offset % 1.0, tol)
                    op = "+" if offset >= 0 else "-"
                    if off_exact is not None:
                        coord_parts.append(
                            f"{coord} = {tie_body} {op} {off_exact.numerator}/{off_exact.denominator};"
                        )
                    else:
                        coord_parts.append(f"{coord} = {tie_body} {op} {abs(off_snapped):.10g};")
            else:  # complex
                has_complex = True
                coord_parts.append(f"{coord} @ {val:.10g}  ' complex site-symmetry constraint, verify manually")

        if has_complex:
            warnings.append(
                f"{label}: at least one coordinate has a site-symmetry constraint this script's "
                f"simple per-coordinate model can't express as a single Get()-based tie -- "
                f"emitted as an independent value, VERIFY MANUALLY against the space group's "
                f"Wyckoff table."
            )

        aniso_row = aniso_by_label.get(label)
        aniso_all_zero = aniso_row is not None and all(
            abs(parse_cif_value(aniso_row.get(tag, "0")) or 0.0) < 1e-12 for tag in ADP_CIF_TAGS.values()
        )
        if aniso_all_zero:
            warnings.append(
                f"{label}: CIF's _atom_site_aniso_* row is all zero (a common unused/placeholder "
                f"pattern, not real refined data) -- falling back to the isotropic B_iso_or_equiv "
                f"value instead of emitting a physically meaningless zero ADP tensor."
            )

        if aniso_row is not None and not aniso_all_zero:
            adp_row = aniso_row
            adp_constraint = classify_adps(stabilizer)
            adp_parts = []
            for name in ADP_NAMES:
                cif_val = parse_cif_value(adp_row.get(ADP_CIF_TAGS[name], "0")) or 0.0
                kind = adp_constraint[name]
                if kind[0] == "free":
                    adp_parts.append(f"{name} @ {cif_val:.10g}")
                elif kind[0] == "fixed":
                    adp_parts.append(f"{name} 0")
                else:
                    adp_parts.append(f"{name} = {format_adp_tie(kind[1])};")
            adp_part = "  " + "  ".join(adp_parts)
        else:
            adp_part = f"  beq {beq}" if beq is not None else ""
        out_lines.append(f"   site {label}  {'  '.join(coord_parts)}  occ {type_symbol} {occ:.6g}{adp_part}")

    return "\n".join(out_lines), warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cif_file")
    parser.add_argument("-o", "--output", help="write to this file instead of stdout")
    parser.add_argument("--tolerance", type=float, default=0.0015,
                         help="coordinate-match tolerance for stabilizer/fraction detection (default 0.0015)")
    args = parser.parse_args()

    text, warnings = convert(args.cif_file, tol=args.tolerance)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(text)

    if warnings:
        print("\nWarnings:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
