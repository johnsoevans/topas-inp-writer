#!/usr/bin/env python3
"""
insert_adps.py -- replace a `beq` clause on selected `site` line(s) with
symmetry-constrained anisotropic displacement parameters (u11/u22/u33/
u12/u13/u23), derived from the enclosing `str`'s real space group.

Trigger: **"insert adps"** -- run this whenever the user asks to replace
beq with ADPs on some site(s), instead of hand-deriving the constraints
each time (see the direct worked example in this skill's own session
history: CeO2's three Ce sites in F_M_3_M, one on a 24-fold special
position needing u11/u22/u13 free + u33=Get(u11) + u12=u23=0, two on
4-fold cubic positions needing the fully-isotropic-shaped u11 free +
u22=u33=Get(u11) + all off-diagonals 0 -- both derived and confirmed
self-consistent (R.U.R^T = U for every stabilizer operator) before being
written by hand; this script automates exactly that process).

Reuses this skill's existing engine rather than re-deriving it:
check_inp_syntax.py's find_str_blocks/find_sites/resolve_site_coordinates/
resolve_str_scope_values for parsing (the same code plot_str_3d.py and
check_symmetry_constraints already use), and symmetry_utils.py's
resolve_sg_operators/find_stabilizer/classify_adps/format_adp_tie for the
actual crystallography -- the same functions cif_to_str.py uses to write
ADPs when converting a CIF. A site's real space group is TOPAS's own
database (sgcom6.exe/sg/*.sg via TOPAS_DIR), not a guess.

After inserting the new u11/u22/u33/u12/u13/u23 columns, this also runs
fix_columns.py's own fix_columns() over the result (imported directly,
same pattern format_inp_hierarchy.py already established) so the new
columns -- and whatever's left of the old ones -- line up immediately,
rather than leaving that as a separate "now go run fix columns" step.

Usage:
    python3 scripts/insert_adps.py file.inp --lines 26-28   # only site(s) touching these lines
    python3 scripts/insert_adps.py file.inp                 # every site with a beq, whole file
    python3 scripts/insert_adps.py file.inp -o out.inp
    python3 scripts/insert_adps.py file.inp --check          # preview to stdout, don't write
    python3 scripts/insert_adps.py file.inp --no-open

When the user has active IDE selection context naming a line range and
asks to "insert adps" (or "replace beq with adps") on the selected
site(s), translate that range directly into `--lines START-END`, the
same convention fix_columns.py's own `--lines` flag already established.
"""

import sys
import os
import re
import math
import argparse
import subprocess
import shutil

import check_inp_syntax as cis
import symmetry_utils as su
from fix_columns import fix_columns  # same directory; realigns the newly-inserted u_ij columns

# Matches the no-space error-limit suffix TOPAS glues directly onto a
# refined value it's reporting on (e.g. "19.99883_LIMIT_MAX_20") -- not
# matched by E_ARG_NUMBER_TOKEN_RE (which only recognizes the backtick-
# error form), so a beq clause ending in one needs this swallowed too or
# it's left dangling right after the excised span.
LIMIT_SUFFIX_RE = re.compile(r"_LIMIT_(?:MIN|MAX)_-?[\d.]+(?:[eE][-+]?\d+)?")

BEQ_TO_U_FACTOR = 8 * math.pi ** 2  # Beq = 8 pi^2 Uiso


def parse_line_range(s):
    m = re.match(r"^(\d+)-(\d+)$", s.strip())
    if not m:
        raise argparse.ArgumentTypeError("expected START-END, e.g. 26-28")
    start, end = int(m.group(1)), int(m.group(2))
    if start < 1 or end < start:
        raise argparse.ArgumentTypeError("expected START-END with 1 <= START <= END")
    return start, end


def beq_clause_span(clean_slice, base_offset):
    """(abs_start, abs_end) of a 'beq ...' clause (the keyword through
    its value/equation, including any _LIMIT_MIN_/_LIMIT_MAX_ tail)
    within clean_slice, or None if beq isn't present. Mirrors
    extract_keyword_form()'s own internal span computation -- that
    function returns only the parsed VALUE, never the end offset, so
    this reimplements just enough of its logic (same E_ARG_NUMBER_TOKEN_RE,
    same optional sigil/name token shape) to also get where the clause
    ends, which is what a caller needs to excise-and-replace it."""
    m = re.search(r"\bbeq\b", clean_slice)
    if not m:
        return None
    start = m.start()
    pos = m.end()
    n = len(clean_slice)
    while pos < n and clean_slice[pos] in " \t\r\n":
        pos += 1
    if pos < n and clean_slice[pos] == "=":
        end = clean_slice.find(";", pos)
        if end == -1:
            return None
        return (base_offset + start, base_offset + end + 1)

    tok_m = re.match(r"(?:[!@]?[A-Za-z_]\w*|[!@])", clean_slice[pos:])
    val_start = pos
    if tok_m and tok_m.group(0):
        k = pos + tok_m.end()
        while k < n and clean_slice[k] in " \t\r\n":
            k += 1
        probe = cis.E_ARG_NUMBER_TOKEN_RE.match(clean_slice[k:])
        if probe and probe.group(0):
            val_start = k
    val_m = cis.E_ARG_NUMBER_TOKEN_RE.match(clean_slice[val_start:])
    if not val_m or not val_m.group(0):
        return None
    end = val_start + val_m.end()
    tail = LIMIT_SUFFIX_RE.match(clean_slice[end:])
    if tail:
        end += tail.end()
    return (base_offset + start, base_offset + end)


def resolve_beq_seed(beq_form, clean_text):
    """Best-effort starting Beq value for a site's existing beq clause:
    a plain value's own number, or -- if beq is a bare-name equation
    like 'beq = b1;', the common "one shared isotropic B" idiom -- that
    name's own prm/local declaration value found elsewhere in the file.
    Returns (beq_value_or_None, note_or_None)."""
    if beq_form is None:
        return None, None
    if beq_form[0] == "value":
        return beq_form[2], None
    if beq_form[0] == "equation":
        expr = beq_form[1].strip()
        if re.match(r"^[A-Za-z_]\w*$", expr):
            m = re.search(
                r"\b(?:prm|local)\s+[!@]?" + re.escape(expr) + r"\b\s+([+-]?[\d.]+(?:[eE][+-]?\d+)?)",
                clean_text,
            )
            if m:
                return float(m.group(1)), f"seeded from {expr}'s own prm/local declaration"
            # Not a prm/local -- try the other TOPAS naming convention,
            # a value-keyword giving its own value a name directly (e.g.
            # 'beq b2 19.99883...' on some OTHER site elsewhere in the
            # file), rather than through a separate prm/local statement.
            m = re.search(
                r"\bbeq\s+[!@]?" + re.escape(expr) + r"\b\s+([+-]?[\d.]+(?:[eE][+-]?\d+)?)",
                clean_text,
            )
            if m:
                return float(m.group(1)), f"seeded from {expr}'s own 'beq {expr} ...' declaration"
        return None, f"beq is an equation ({expr!r}) this script can't resolve to a plain number"
    return None, None


def format_adp_replacement(adp_kind, seed_u):
    """One space-joined 'u11 ... u22 ... ' string built from
    classify_adps()'s constraint dict, matching cif_to_str.py's own
    established ADP-writing convention exactly (free -> '@ value',
    fixed -> '0', tied -> '= <Get()-based equation>;') so a file mixing
    CIF-converted and this-script-converted sites reads consistently.
    Free diagonal components (u11/u22/u33) seed from the site's own old
    beq value (converted Beq -> Uiso); a free off-diagonal component
    seeds at 0, a standard starting guess for a term with no isotropic
    equivalent to derive from."""
    parts = []
    for name in su.ADP_NAMES:
        kind, extra = adp_kind[name]
        if kind == "free":
            seed = seed_u if name in ("u11", "u22", "u33") else 0.0
            parts.append(f"{name} @ {seed:.6g}")
        elif kind == "fixed":
            parts.append(f"{name} 0")
        else:
            parts.append(f"{name} = {su.format_adp_tie(extra)};")
    return " ".join(parts)


def insert_adps(raw, line_range=None):
    """Returns (new_text, converted_count, warnings)."""
    clean_text = cis.strip_comments_and_strings(raw)
    values_text = cis.strip_comments_only(raw)

    if line_range is not None:
        line_start, line_end = line_range
        line_offsets = [0]
        for line in raw.splitlines(keepends=True):
            line_offsets.append(line_offsets[-1] + len(line))
        range_start = line_offsets[min(line_start - 1, len(line_offsets) - 1)]
        range_end = line_offsets[min(line_end, len(line_offsets) - 1)]
    else:
        range_start, range_end = 0, len(raw)

    str_blocks = cis.find_str_blocks(clean_text)
    replacements = []
    warnings = []

    for content_start, content_end in str_blocks:
        block_clean = clean_text[content_start:content_end]
        block_values = values_text[content_start:content_end]

        sg_m = re.search(r"\bspace_group\b\s*(\"[^\"]*\"|\S+)", block_values)
        if not sg_m:
            continue
        symbol = sg_m.group(1).strip('"')
        symops, _header, msg = su.resolve_sg_operators(symbol)
        if not symops:
            warnings.append(f"space_group {symbol!r}: {msg}")
            continue

        first_site_m = re.search(r"\bsite\b", block_clean)
        preamble_end = first_site_m.start() if first_site_m else len(block_clean)
        preamble = block_clean[:preamble_end]
        str_scope = cis.resolve_str_scope_values(preamble)

        for name, site_slice, site_pos in cis.find_sites(block_clean):
            abs_site_start = content_start + site_pos
            if not (range_start <= abs_site_start < range_end):
                continue

            point, _forms = cis.resolve_site_coordinates(site_slice, outer_known=str_scope)
            if point is None:
                warnings.append(f"site {name}: couldn't resolve x/y/z, skipped")
                continue

            span = beq_clause_span(site_slice, abs_site_start)
            if span is None:
                warnings.append(f"site {name}: no 'beq' clause found, skipped")
                continue

            beq_form = cis.extract_keyword_form(site_slice, "beq")
            beq_val, note = resolve_beq_seed(beq_form, clean_text)
            if beq_val is not None:
                seed_u = beq_val / BEQ_TO_U_FACTOR
                if note:
                    warnings.append(f"site {name}: {note} (Beq={beq_val:.6g})")
            else:
                seed_u = 0.01
                warnings.append(
                    f"site {name}: {note or 'no usable beq value found'} -- "
                    f"seeding free ADP components at a generic {seed_u}"
                )

            stabilizer = su.find_stabilizer(point, symops, 1e-6)
            adp_kind = su.classify_adps(stabilizer)
            replacement = format_adp_replacement(adp_kind, seed_u)
            replacements.append((span[0], span[1], replacement))

    out = raw
    for start, end, new_text in sorted(replacements, key=lambda r: -r[0]):
        out = out[:start] + new_text + out[end:]

    if replacements:
        # Realign columns (the newly-inserted u11/u22/.../beq's old
        # column, whatever's left of it) the same way "fix columns" does
        # on its own -- reuses fix_columns() directly so the two
        # workflows can't drift apart, same pattern format_inp_hierarchy.py
        # already established. Scoped to the same line_range this run
        # itself was scoped to (or the whole file, if it wasn't scoped),
        # so this never reformats site lines the caller didn't ask about
        # even though column WIDTHS are still computed from the whole
        # group they belong to (fix_columns()'s own --lines semantics).
        out = fix_columns(out, line_range=line_range)

    return out, len(replacements), warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inp_file")
    parser.add_argument("--lines", type=parse_line_range,
                         help="1-indexed, inclusive line range containing the site(s) to convert "
                              "(e.g. 26-28); omit to convert every site with a beq in the whole file")
    parser.add_argument("-o", "--output", help="write to this file instead of overwriting the input")
    parser.add_argument("--check", action="store_true", help="print the result to stdout instead of writing any file")
    parser.add_argument("--no-open", action="store_true",
                         help="don't reopen/focus the file in VS Code afterward (default: do reopen it)")
    args = parser.parse_args()

    with open(args.inp_file, encoding="utf-8") as f:
        raw = f.read()

    out, converted, warnings = insert_adps(raw, args.lines)

    for w in warnings:
        print(f"note: {w}", file=sys.stderr)

    if converted == 0:
        print("No site with a 'beq' clause found in range -- nothing converted.", file=sys.stderr)
        return

    print(f"Converted {converted} site(s) from beq to ADPs.", file=sys.stderr)

    if args.check:
        print(out)
        return

    out_path = args.output or args.inp_file
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print(f"Written to {out_path}", file=sys.stderr)

    if not args.no_open:
        code_path = shutil.which("code") or shutil.which("code.cmd")
        if code_path:
            subprocess.run([code_path, out_path], check=False)
        else:
            print("Note: 'code' CLI not found on PATH -- couldn't reopen the file in VS Code.", file=sys.stderr)


if __name__ == "__main__":
    main()
