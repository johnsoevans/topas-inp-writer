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
  4. The CIF's stated `_atom_site_symmetry_multiplicity` is cross-checked
     against the computed orbit size (number of distinct cosets of the
     stabilizer within the full operator list) -- see `check_multiplicity()`.
     This tag is used inconsistently across CIF-generating software: some
     (matching its formal core-dictionary definition) populate it with the
     true Wyckoff multiplicity, but others (SHELXL-derived CIFs, confirmed
     directly in the wild) populate it with the site-symmetry ORDER instead
     (1 for a general position, 2/3/4/... for a special one) -- a different
     number that happens to divide the multiplicity rather than equal it.
     A stated value is therefore only treated as a genuine disagreement
     (occupancy needs scaling: occ_topas = cif_occ * cif_mult /
     computed_mult) if it matches NEITHER the computed multiplicity NOR the
     computed site-symmetry order -- otherwise it's silently consistent with
     one of the two known conventions and left alone. Flagged, not silently
     "fixed", since which of disorder/split-site vs. off-special-position
     rounding it is can't be determined from the CIF alone.

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
import subprocess
from fractions import Fraction

import topas_install
from symmetry_utils import (
    parse_symop_string,
    find_stabilizer,
    classify_coordinates,
    check_multiplicity,
    determine_fixed_angles,
    determine_length_ties,
    classify_crystal_system,
    ANGLE_CONSTRAINTS_BY_SYSTEM,
    resolve_sg_operators,
    parse_sg_file,
    snap_to_fraction,
    classify_adps,
    format_adp_tie,
    complete_centering_operators,
    apply_symop,
    mod1,
    points_equal_mod1,
    ADP_NAMES,
    COORD_NAME,
)


# ---------------------------------------------------------------------------
# Colon-suffixed space-group symbol resolution (':1'/':2' centrosymmetric
# origin choice, ':H'/':R' rhombohedral axes choice) -- deliberately kept
# local to this script rather than in symmetry_utils.py, which is the
# shared, externally-maintained skill file this workflow doesn't modify.
# symmetry_utils.resolve_sg_operators's own .sg-filename prediction has no
# special handling for these suffixes (it only strips whitespace/underscores
# and maps '/' -> 'o'), which silently mispredicts the real filename
# sgcom6.exe/tc.exe use for a colon-suffixed symbol -- confirmed empirically
# against sgcom5.txt and live tc.exe runs for four independent space groups
# (125 P4/nbm, 68 Ccca, 70 Fddd, 166 R-3m) before trusting this as general:
#
# - ':H' (hexagonal axes) and ':1' (origin choice 1) are NOT real symbols in
#   sgcom5.txt at all -- both are simply the bare/unmarked table entry.
#   sgcom6.exe rejects 'symbol:H'/'symbol:1' outright ("Space group not
#   found in sgcom5.txt"), so the suffix must be stripped entirely before
#   generation.
# - ':R' (rhombohedral axes) and ':2'/':N>=2' (origin choice 2+) ARE real,
#   separately-listed sgcom5.txt entries (e.g. 'r-3mr = 166r',
#   'p4/nbm:2 = 125:2') -- sgcom6.exe accepts the raw symbol with the
#   suffix unchanged for GENERATION, but its own output filename replaces
#   the suffix with 'r' (axes) or 'qN' (origin), e.g. 'r-3mr.sg',
#   'p4onbmq2.sg' -- not a naive concatenation of the suffix.
# ---------------------------------------------------------------------------

def parse_colon_suffix(symbol):
    """Split a trailing CIF colon-suffix off `symbol`. Returns
    (base_symbol, kind, value): kind is 'axes' (value 'H'/'R') or 'origin'
    (value the digit string) or None (value None) if there was none."""
    m = re.search(r":\s*([HhRr]|\d+)\s*$", symbol)
    if not m:
        return symbol, None, None
    val = m.group(1)
    base = symbol[: m.start()]
    if val.upper() in ("H", "R"):
        return base, "axes", val.upper()
    return base, "origin", val


def generation_symbol_for_colon_suffix(symbol):
    """The symbol to actually pass to sgcom6.exe -- bare (suffix stripped)
    for ':H'/':1', unchanged for ':R'/':2'+."""
    base, kind, val = parse_colon_suffix(symbol)
    if (kind == "axes" and val == "H") or (kind == "origin" and val == "1"):
        return base
    return symbol


def sg_filename_for_colon_symbol(base, kind, val):
    """Predicts the .sg filename sgcom6.exe itself writes for a
    colon-suffixed symbol already split via parse_colon_suffix."""
    s = re.sub(r"[\s_]", "", base).lower().replace("/", "o")
    if kind == "axes":
        return s + ".sg" if val == "H" else s + "r.sg"
    return s + ".sg" if val == "1" else s + "q" + val + ".sg"


def resolve_colon_suffixed_sg_operators(symbol):
    """
    Local replacement for symmetry_utils.resolve_sg_operators, used only
    for colon-suffixed symbols (everything else still goes through the
    normal, unmodified function) -- generates/reads the .sg file under the
    correct filename per the module-level note above, then reuses
    symmetry_utils.parse_sg_file (a dumb text parser with no symbol
    prediction of its own) to read its operators. Returns
    (symops, header, message), matching resolve_sg_operators's own shape.
    """
    topas_dir, found = topas_install.get_topas_dir()
    if not found:
        return [], {}, "TOPAS_DIR is not set -- cannot resolve symmetry operators via sgcom6.exe."
    sgcom6_path = os.path.join(topas_dir, "sgcom6.exe")
    sg_dir = os.path.join(topas_dir, "sg")
    if not os.path.isfile(sgcom6_path):
        return [], {}, f"sgcom6.exe not found under TOPAS_DIR ({topas_dir})."

    base, kind, val = parse_colon_suffix(symbol)
    gen_symbol = generation_symbol_for_colon_suffix(symbol)
    filename = sg_filename_for_colon_symbol(base, kind, val)
    sg_path = os.path.join(sg_dir, filename)

    if not os.path.isfile(sg_path):
        try:
            subprocess.run(
                [sgcom6_path, gen_symbol, "-dir", "sg"],
                cwd=topas_dir, capture_output=True, timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as e:
            return [], {}, f"Failed to run sgcom6.exe for symbol {symbol!r}: {e}"

    if not os.path.isfile(sg_path):
        return [], {}, (
            f"sgcom6.exe did not produce a .sg file for symbol {symbol!r} "
            f"(expected {sg_path})."
        )

    symops, header = parse_sg_file(sg_path)
    return symops, header, f"Resolved via TOPAS's own space-group database: {sg_path}"


# ---------------------------------------------------------------------------
# Origin-choice detection (ITA groups with two listed origins) -- deliberately
# kept local to this script for the same reason as the colon-suffix handling
# above: symmetry_utils.py is shared/externally-maintained and not modified
# by this workflow.
#
# A CIF that states its space group WITHOUT a colon suffix but whose own
# _symmetry_equiv_pos_as_xyz loop actually corresponds to origin choice 2
# (not TOPAS's own bare-symbol default of origin choice 1) causes a silent,
# hard-to-detect bug: this script correctly derives Wyckoff/lattice
# constraints from the CIF's own operators, but the `space_group "..."`
# keyword written into the .inp is just the bare symbol -- and at refinement/
# simulation runtime TOPAS re-resolves THAT string independently via its own
# database, landing on origin choice 1. The CIF's coordinates and TOPAS's
# runtime symmetry then silently disagree, generating atoms in the wrong
# positions (confirmed directly: 130_GUCDUE.cif and 48_LAZWAK.cif both show
# this exact pattern -- the CIF's own operator loop contains a bare
# `-x,-y,-z` with ZERO translation, which is present in the ':2' resolution
# but absent from the bare/':1' one).
#
# The IT numbers below are exactly the space groups with two origins listed
# in International Tables for Crystallography Vol. A -- every other space
# group has only one origin, so this whole check is a no-op for them.
# ---------------------------------------------------------------------------

ORIGIN_CHOICE_AMBIGUOUS_SG_NUMBERS = {
    48, 50, 59, 68, 70, 85, 86, 88,
    125, 126, 129, 130, 133, 134, 137, 138, 141, 142,
    201, 222, 224, 227,
}


def _canonical_operator(rows, translation, ndigits=6):
    """(rows, translation) -> a hashable, translation-mod-1-normalized form,
    for order-independent set comparison of two operator lists."""
    canon_t = []
    for t in translation:
        v = float(t) % 1.0
        if v > 1 - 10 ** (-ndigits):
            v = 0.0
        canon_t.append(round(v, ndigits))
    return (tuple(tuple(r) for r in rows), tuple(canon_t))


def operator_sets_match(ops_a, ops_b):
    """True if two symmetry-operator lists (each in parse_symop_string's
    (rows, translation) shape) represent the identical set of operators,
    order-independent. Used to test whether a CIF's own operator loop
    matches a particular origin-choice resolution of its space group."""
    if not ops_a or not ops_b or len(ops_a) != len(ops_b):
        return False
    return {_canonical_operator(*op) for op in ops_a} == {_canonical_operator(*op) for op in ops_b}


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


def parse_fract_coord(s):
    """_atom_site_fract_x/y/z specifically use a bare '.' to mean the
    coordinate is fixed at 0 by the site's own symmetry (an ITA/ICSD
    special-position convention -- confirmed on 166_410784_O8_P2_Sr3.cif's
    Sr1 at Wyckoff 3a (0,0,0), written as 'Sr1 Sr2+ 3 a . . . ...'), NOT
    'not measured/inapplicable' the way parse_cif_value treats bare '.'
    everywhere else (occupancy, B_iso, cell parameters, ...) -- those really
    do mean missing data. Falls through to parse_cif_value's normal
    handling for anything that isn't exactly '.' (a real number, '?'
    genuinely unknown, an empty field, ...)."""
    if strip_cif_uncertainty(s).strip() == ".":
        return 0.0
    return parse_cif_value(s)


def read_cif_lines(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()


def find_scalar_tag(lines, tag):
    """Find a single-value CIF tag like '_cell_length_a 5.410278(11)'. Also
    handles the ICSD-for-WWW export convention of writing the tag alone on
    its own line with the value on the following line (e.g.
    '_chemical_formula_sum' then \"'H5.968 Cl0.032 O10.968 W2 Zr1'\" on the
    next line) -- confirmed common in ICSD CIFs carrying this tag, silently
    returning None for every one of them without this branch (COD/CSD CIFs
    always carry the value on the same line, so this branch is a no-op for
    those corpora -- it only ever turns a previous None into a real value,
    never changes an already-working same-line parse). Does NOT handle the
    separate ';'-delimited multi-line text-field convention -- left
    unsupported/opaque same as parse_cif_loop's own text-field handling,
    since no tag this script reads actually needs it."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(tag) and (len(stripped) == len(tag) or stripped[len(tag)].isspace()):
            rest = stripped[len(tag):].strip()
            if not rest:
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    nxt = lines[j].strip()
                    if nxt and not nxt.startswith(("_", "loop_", "data_", ";")):
                        rest = nxt
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


def generate_orbit(point, symops, tol):
    """All distinct images of `point` under `symops`, mod 1 -- used only for
    cross-site duplicate-atom detection (see the site loop in convert()), not
    for Wyckoff constraint derivation itself (that's find_stabilizer's job)."""
    orbit = []
    for rows, translation in symops:
        img = tuple(mod1(v, tol) for v in apply_symop(rows, translation, point))
        if not any(points_equal_mod1(img, p, tol) for p in orbit):
            orbit.append(img)
    return orbit


def topas_safe_identifier(label, used=None):
    """
    CIF atom labels routinely carry a literal apostrophe (the ribose/
    sugar-ring '-prime' convention, e.g. 'C1\'A', 'O5\'B', 'S3\'A') or other
    punctuation that TOPAS's own INP syntax can't use in a `site` name --
    confirmed directly: an apostrophe starts a comment-to-end-of-line in
    TOPAS's grammar, and a site named e.g. "S3'A" ran to completion without
    any reported error yet vanished entirely from TOPAS's own
    elemental_composition output (172_4506971.cif). Replace any character
    that isn't alphanumeric/underscore with '_', and prefix a leading digit
    (TOPAS identifiers, like most languages, can't start with one). `used`
    (a set, mutated in place) disambiguates a collision this substitution
    might create between two originally-distinct labels by appending a
    numeric suffix, so two different sites are never silently merged.
    """
    safe = re.sub(r"[^0-9A-Za-z_]", "_", label)
    if not safe or safe[0].isdigit():
        safe = "s" + safe
    if used is not None:
        base = safe
        n = 2
        while safe in used:
            safe = f"{base}_{n}"
            n += 1
        used.add(safe)
    return safe


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def convert(path, tol=0.0015, refine=False):
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

    nonstandard_symbol_warning = None
    if sg and "(" in sg:
        # A parenthesized H-M symbol (e.g. 'C m m 2 (2*c,a,b)') is a
        # nonstandard/transformed axis setting that TOPAS's own sgcom6.exe
        # database has no entry for -- writing it through literally into
        # 'space_group "..."' fails the moment the file is run in TOPAS,
        # not just silently. Deriving the correct standard-setting symbol
        # is a nontrivial crystallographic task this script doesn't
        # attempt (see also complete_centering_operators's own symbol
        # check); warn instead.
        modulation_dim = find_scalar_tag(lines, "_cell_modulation_dimension")
        if modulation_dim:
            nonstandard_symbol_warning = (
                f"space_group symbol {sg!r} is a nonstandard/transformed axis setting AND this "
                f"CIF has _cell_modulation_dimension={modulation_dim} -- this is likely an "
                f"incommensurate/modulated structure, which needs superspace-group handling this "
                f"script doesn't attempt. TOPAS's own space-group database has no entry for a "
                f"parenthesized symbol like this ('Space group not found in sgcom5.txt', confirmed "
                f"directly) -- the space_group line below WILL fail the moment this file is run in "
                f"TOPAS, not just look suspicious. Coordinate/Wyckoff constraints were still derived "
                f"correctly from the CIF's own (complete) operator list, if present, but the file "
                f"as a whole is not usable as-is."
            )
        else:
            nonstandard_symbol_warning = (
                f"space_group symbol {sg!r} is a nonstandard/transformed axis setting (parenthesized "
                f"transform suffix). TOPAS's own space-group database has no entry for this form "
                f"('Space group not found in sgcom5.txt', confirmed directly) -- the space_group "
                f"line below WILL fail the moment this file is run in TOPAS, not just look "
                f"suspicious. Coordinate/Wyckoff constraints were still derived correctly from the "
                f"CIF's own (complete) operator list, if present, but 'space_group' itself needs to "
                f"be replaced by hand with the equivalent standard-setting symbol (with a/b/c "
                f"transformed to match) before this file will run."
            )

    formula_elements = parse_formula_elements(find_scalar_tag(lines, "_chemical_formula_sum"))

    sym_tags, sym_rows = parse_cif_loop(lines, ["_symmetry_equiv_pos_as_xyz"])
    op_key = "_symmetry_equiv_pos_as_xyz" if sym_rows else None
    if sym_rows == []:
        sym_tags, sym_rows = parse_cif_loop(lines, ["_space_group_symop_operation_xyz"])
        op_key = "_space_group_symop_operation_xyz" if sym_rows else None
    # op_key is the specific required tag, NOT sym_tags[0] -- ICSD CIFs
    # commonly declare a numeric '_symmetry_equiv_pos_site_id' column
    # BEFORE the operator-string column, so sym_tags[0] would silently
    # pick the wrong column and discard the CIF's own operators entirely.
    symops = []
    if op_key:
        for row in sym_rows:
            try:
                symops.append(parse_symop_string(row[op_key]))
            except ValueError:
                continue
    symops_from_cif = bool(symops)

    truncated_operator_warning = None
    if symops and not any(
        tuple(rows) == ((1, 0, 0), (0, 1, 0), (0, 0, 1)) and all(float(t) % 1.0 < 1e-6 for t in translation)
        for rows, translation in symops
    ):
        # A genuine symmetry-equivalent-positions loop always includes the
        # identity operator 'x, y, z'. Its absence means the loop is
        # truncated/malformed, not just missing centering copies -- using
        # it as-is risks find_stabilizer finding no stabilizing operator
        # at all for some site (ZeroDivisionError in check_multiplicity)
        # or silently wrong constraints for others. Discard in favor of
        # the same sgcom6.exe fallback used for a CIF with no operator
        # loop at all.
        truncated_operator_warning = (
            f"CIF's own _symmetry_equiv_pos_as_xyz loop ({len(symops)} operators) doesn't "
            f"include the identity operator 'x, y, z' -- a genuine operator list always does, "
            f"so this loop is truncated/malformed. Discarding it in favor of TOPAS's own "
            f"space-group database, the same fallback used when a CIF has no operator loop at all."
        )
        symops = []
        symops_from_cif = False

    centering_warning = None
    if symops and sg:
        symops, n_added = complete_centering_operators(symops, sg, cell_angles=(al, be, ga))
        if n_added:
            centering_warning = (
                f"CIF's own _symmetry_equiv_pos_as_xyz loop listed only the primitive/reduced "
                f"operator set ({len(symops) - n_added} of {len(symops)}) for centered space "
                f"group {sg!r} -- a common, legitimate ICSD convention that expects the reader "
                f"to add the lattice-centering-translated copies itself. Added {n_added} "
                f"centering-translated operators before deriving Wyckoff constraints/multiplicity "
                f"below; without this, multiplicity would be undercounted by the centering factor "
                f"for any site whose stabilizer is entirely made of the originally-listed operators."
            )

    # Origin-choice check -- only ever engages when ALL of these hold, so it's
    # a no-op for the overwhelming majority of CIFs (any single-origin space
    # group, any CIF whose symbol already carries a colon suffix, and any CIF
    # without its own operator loop to check against in the first place):
    sg_origin_suffix = ""
    origin_choice_warning = None
    if symops_from_cif and sg and parse_colon_suffix(sg)[1] is None:
        it_number_raw = find_scalar_tag(lines, "_symmetry_Int_Tables_number")
        if it_number_raw is None:
            it_number_raw = find_scalar_tag(lines, "_space_group_IT_number")  # ICSD alt tag name
        try:
            it_number = int(strip_cif_uncertainty(it_number_raw)) if it_number_raw else None
        except ValueError:
            it_number = None
        if it_number in ORIGIN_CHOICE_AMBIGUOUS_SG_NUMBERS:
            sg_bare_topas = sg.replace(" ", "_")
            symops_o1, _, _ = resolve_sg_operators(sg_bare_topas)
            symops_o2, _, _ = resolve_colon_suffixed_sg_operators(sg_bare_topas + ":2")
            matches_o1 = operator_sets_match(symops, symops_o1)
            matches_o2 = operator_sets_match(symops, symops_o2)
            if matches_o2 and not matches_o1:
                sg_origin_suffix = ":2"
                origin_choice_warning = (
                    f"Space group {sg!r} (IT #{it_number}) has two ITA origin choices, and this "
                    f"CIF states neither via a colon suffix. Compared the CIF's own "
                    f"{len(symops)} symmetry operators against both of TOPAS's own database "
                    f"resolutions: they match origin choice 2, NOT TOPAS's bare-symbol default "
                    f"(origin choice 1). Writing space_group as {sg_bare_topas + sg_origin_suffix!r} "
                    f"instead of the CIF's bare form -- using the bare symbol here would make "
                    f"TOPAS's runtime symmetry generation silently disagree with the CIF's own "
                    f"coordinates (confirmed to cause large composition/density errors on "
                    f"130_GUCDUE.cif and 48_LAZWAK.cif) even though the constraints above, "
                    f"derived from the CIF's own operators, are themselves correct."
                )
            elif not matches_o1:
                origin_choice_warning = (
                    f"Space group {sg!r} (IT #{it_number}) has two ITA origin choices, and this "
                    f"CIF states neither via a colon suffix. Could not confirm which origin the "
                    f"CIF's own operators correspond to (matched "
                    f"{'both' if matches_o2 else 'neither'} of TOPAS's database resolutions) -- "
                    f"space_group is being written as the CIF's bare symbol as before, but "
                    f"VERIFY THE SETTING MANUALLY against the CIF's own operators."
                )

    sg_fallback_warning = None
    if not symops and sg:
        if parse_colon_suffix(sg)[1] is not None:
            symops, sg_header, sg_message = resolve_colon_suffixed_sg_operators(sg)
        else:
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
    # Angles/lengths the crystal system locks to a SPECIFIC value (not
    # necessarily 90 -- e.g. hexagonal/trigonal ga=120) must never be
    # written as independently refinable, even though they aren't omittable
    # the way a 90 angle is (fixed_angles only covers the omittable-at-90
    # case -- see determine_fixed_angles's own docstring). Anything NOT in
    # this set, and not tied to another length, is a genuinely free
    # parameter and gets `@` so it can refine -- matches the same @-means-
    # refinable convention already used for free atomic coordinates and
    # anisotropic ADPs below; harmless for the iters-0 simulate-only batch
    # (a refine flag with no refinement cycles is a no-op there).
    angle_constraints = ANGLE_CONSTRAINTS_BY_SYSTEM.get(classify_crystal_system(symops), {}) if symops else {}

    flag = "@ " if refine else ""

    out_lines = []
    out_lines.append("str")
    if a is not None:
        out_lines.append(f"   a {flag}{a}")
        out_lines.append(f"   b = Get({length_ties['b']});" if "b" in length_ties else f"   b {flag}{b}")
        out_lines.append(f"   c = Get({length_ties['c']});" if "c" in length_ties else f"   c {flag}{c}")
        for name, val in (("al", al), ("be", be), ("ga", ga)):
            if name in fixed_angles:
                continue  # forced to 90, relies on TOPAS's own default -- omitted entirely
            if name in angle_constraints:
                out_lines.append(f"   {name} {val}")  # forced (e.g. hexagonal ga=120) but not omittable -- never refined
            else:
                out_lines.append(f"   {name} {flag}{val}")
    if sg:
        sg_topas = sg.replace(" ", "_") + sg_origin_suffix
        out_lines.append(f'   space_group "{sg_topas}"')
    out_lines.append("")

    warnings = []
    if nonstandard_symbol_warning:
        warnings.append(nonstandard_symbol_warning)
    if truncated_operator_warning:
        warnings.append(truncated_operator_warning)
    if sg_fallback_warning:
        warnings.append(sg_fallback_warning)
    if centering_warning:
        warnings.append(centering_warning)
    if origin_choice_warning:
        warnings.append(origin_choice_warning)

    used_site_names = set()
    site_orbits = []  # [(label, species, occ, [orbit_points])] -- cross-site duplicate-atom detection
    for row in site_rows:
        label = row.get("_atom_site_label", "?")
        site_name = topas_safe_identifier(label, used_site_names)
        if site_name != label:
            warnings.append(
                f"{label}: site label contains characters TOPAS's own syntax can't use in a "
                f"`site` identifier (e.g. a literal apostrophe, which starts a comment in TOPAS's "
                f"grammar) -- emitted as '{site_name}' instead. Cross-reference by position, not "
                f"name, if comparing against the CIF."
            )
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
        x = parse_fract_coord(row.get("_atom_site_fract_x", "0"))
        y = parse_fract_coord(row.get("_atom_site_fract_y", "0"))
        z = parse_fract_coord(row.get("_atom_site_fract_z", "0"))
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
        cif_mult = row.get("_atom_site_symmetry_multiplicity")
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
                adp_part = f"  beq @ {beq}" if beq is not None else ""
            out_lines.append(
                f"   site {site_name}  num_posns 0  x @ {x}  y @ {y}  z @ {z}  occ {type_symbol} {occ}{adp_part}"
            )
            continue

        # Cross-site duplicate-atom detection: some CIFs (especially organic-
        # crystal deposits with a fragment sitting on a special axis) explicitly
        # enumerate every symmetry-related copy of that fragment as its own
        # separately-named atom, rather than relying on symmetry to generate
        # them from one independent site -- confirmed in the wild
        # (100_YOVPUY.cif, a squarate anion on a 4-fold axis: C1/C4/C5/C6 and
        # O1/O3/O4/O5 are two atoms, each listed four times, their coordinates
        # exact images of each other under P4bm's own rotation operators, e.g.
        # applying '-y,x,z' to C1 reproduces C4 exactly). Treating each listed
        # row as independent (as the rest of this loop does) silently
        # quadruple-counts that fragment's mass/composition/density -- caught
        # here by checking whether this site's own point coincides (mod 1)
        # with any point already placed by an EARLIER site's orbit. If so,
        # skip this row entirely (not merely rescale its occupancy, since the
        # duplicate fraction is 100%, not partial) rather than silently
        # keeping both.
        #
        # Species (type_symbol) MUST also match before treating this as a
        # duplicate -- a mixed-occupancy/substitutional-disorder site (e.g.
        # Ba2/Sr2 both partially occupying the identical position, a common,
        # entirely legitimate pattern in inorganic solid solutions) coincides
        # in coordinates by design, but is NOT a duplicate atom -- both
        # species genuinely contribute to that site's composition and must be
        # kept. Confirmed as a real false-positive risk directly: an earlier
        # version of this check (species-blind) silently dropped Sr2 as a
        # "duplicate" of Ba2 in 100_2100722.cif, corrupting composition/
        # density for a large fraction of an unrelated (COD-sourced) corpus
        # that has nothing to do with the CSD ring-duplication pattern this
        # check was built for.
        #
        # BOTH occupancies must also be (near) 1 -- matching species alone
        # still isn't enough: a same-element split/disordered site (e.g.
        # 95_9014926.cif's 'As' at occ 0.81 and 'AsSb' at occ 0.19, two
        # genuinely distinct partial components that happen to both resolve
        # to species 'As') coincides in both coordinates AND species, but is
        # exactly as legitimate as the Ba2/Sr2 case -- confirmed as a second
        # real false-positive this check produced before this condition was
        # added. The genuine CSD ring-duplication case (100_YOVPUY.cif) is
        # unaffected: every duplicated row there is individually written at
        # full occupancy (occ C 1), since the CIF is (incorrectly, for
        # TOPAS's purposes) describing each as if it fully, independently
        # occupied its own copy of the position.
        duplicate_of = None
        if abs(occ - 1.0) < 0.01:
            for other_label, other_species, other_occ, orbit in site_orbits:
                if (other_species == type_symbol and abs(other_occ - 1.0) < 0.01
                        and any(points_equal_mod1(point, p, tol) for p in orbit)):
                    duplicate_of = other_label
                    break
        if duplicate_of:
            warnings.append(
                f"{label}: coordinates coincide (under the space group's own symmetry) with "
                f"site {duplicate_of!r} already emitted, both are the same species "
                f"({type_symbol!r}), and both are at full occupancy -- this row is a "
                f"symmetry-duplicate of that atom, not an independent one (a common CIF "
                f"convention for a fragment on a special axis, explicitly listing every "
                f"symmetry copy under separate atom labels). Skipped entirely to avoid "
                f"double-counting composition/density -- verify against the CIF by hand."
            )
            continue
        site_orbits.append((label, type_symbol, occ, generate_orbit(point, symops, tol)))

        stabilizer = find_stabilizer(point, symops, tol)
        constraint = classify_coordinates(point, stabilizer)
        computed_mult = check_multiplicity(point, symops, stabilizer)

        if cif_mult is not None:
            site_symmetry_order = len(stabilizer)
            if cif_mult != computed_mult and cif_mult != site_symmetry_order:
                # Genuinely doesn't match either real-world convention this
                # tag is populated with (Wyckoff multiplicity, or the
                # site-symmetry order some CIF-generating software actually
                # writes here despite the tag's name -- see module docstring
                # point 4). Flagged only -- NOT auto-corrected. An earlier
                # version of this branch scaled occ by cif_mult/computed_mult
                # directly, which silently assumes computed_mult (derived
                # from the CIF's OWN _symmetry_equiv_pos_as_xyz loop) is
                # trustworthy. Confirmed it isn't always: 25_8103028.cif's
                # own loop lists only 1 operator for space group Pmm2 (should
                # be 4), so computed_mult came out wrong for every site in
                # the file, and correcting occ against it compounded with
                # TOPAS's own independent space_group-based multiplicity at
                # runtime -- occ 8 x TOPAS's own internal x4 for a genuine
                # general position gave a 4x-too-high density (28.3 vs the
                # CIF's own 7.06 g/cm^3), not a fix. Since which of
                # {disorder/split site, off-special-position rounding,
                # unreliable computed_mult from an incomplete CIF operator
                # loop} applies can't be told apart from the CIF alone,
                # leave occ untouched and surface it for manual review
                # instead of risking exactly this kind of silent corruption.
                warnings.append(
                    f"{label}: CIF states _atom_site_symmetry_multiplicity={cif_mult}, which "
                    f"matches neither the computed Wyckoff multiplicity ({computed_mult}) nor the "
                    f"computed site-symmetry order ({site_symmetry_order}) -- occupancy left as "
                    f"{occ} (NOT auto-adjusted: this mismatch could mean a genuine disorder/split "
                    f"site, coordinates not exactly on the special position, or that this CIF's own "
                    f"symmetry operator loop is incomplete relative to its declared space group -- "
                    f"VERIFY MANUALLY, do not trust either number blindly)"
                )

        coord_parts = []
        has_complex = False
        for i, coord in enumerate(COORD_NAME):
            kind = constraint[coord]
            val = point[i]
            if kind[0] == "free":
                # No snapping here -- a FREE coordinate is by definition not
                # symmetry-constrained to any fraction, so its true value
                # is whatever the CIF actually measured, not the nearest
                # "nice" fraction the raw number happens to be close to.
                coord_parts.append(f"{coord} @ {val:.10g}")
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
                    # Re-derive the sign from the MOD-1-REDUCED offset, not
                    # from the raw (possibly >1-in-magnitude or negative)
                    # offset classify_coordinates returns -- confirmed as a
                    # real bug: for offset=-0.75, `offset % 1.0` correctly
                    # gives the display MAGNITUDE 0.25, but combining that
                    # with the RAW offset's sign ("-", since -0.75 < 0) wrote
                    # "- 1/4" (i.e. an effective offset of -0.25), which is
                    # NOT congruent to the true -0.75 mod 1 (0.75) -- off by
                    # exactly 0.5, silently generating a genuinely wrong
                    # coordinate. Reducing first and choosing +/- from the
                    # REDUCED value keeps the small-magnitude-offset display
                    # preference (e.g. "- 1/4" over "+ 3/4") while staying
                    # mathematically correct: a reduced value > 0.5 is
                    # rewritten as -(1 - reduced), which is congruent to it
                    # mod 1 by construction.
                    reduced = offset % 1.0
                    disp_offset = reduced - 1.0 if reduced > 0.5 else reduced
                    off_snapped, off_exact = snap_to_fraction(abs(disp_offset), tol)
                    op = "+" if disp_offset >= 0 else "-"
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
            adp_part = f"  beq @ {beq}" if beq is not None else ""
        out_lines.append(f"   site {site_name}  num_posns {computed_mult}  {'  '.join(coord_parts)}  occ {type_symbol} {occ:.6g}{adp_part}")

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
