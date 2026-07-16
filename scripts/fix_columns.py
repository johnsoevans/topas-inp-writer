#!/usr/bin/env python3
"""
fix_columns.py -- Column-align consecutive `site` statements, and
separately consecutive `la ... lo ... lh ...` emission-profile lines
(inside a `lam { }` block), in a TOPAS .inp file so their keywords line
up vertically -- values are padded to a shared column width, but exactly
ONE space always separates a column from the next keyword. A NUMERIC
value (optionally `@`/`!`-flagged) is right-aligned within its column,
so the digits/decimal points themselves line up down the page in a
fixed-width font -- confirmed directly by the user (TOPAS-Academic's
author): "can you also align numbers. Note, the fint [font] used is
always [a] fixed character width." A column mixing a plain number with
an equation (e.g. one site's `beq = b1;` alongside another's bare `beq
0.2`) stays left-aligned, since right-aligning an equation of varying
shape wouldn't mean the same thing; the same is true of a text value
like `occ`'s species symbol (`Ce+4`/`O-2`), e.g.:

    site Ce1 x  0.25 y   0.5 z  0.25 occ Ce+4 1 beq = b1;
    site Ce2 x     0 y   0.5 z   0.5 occ Ce+4 1 beq = b1;
    site O1  x 0.875 y 0.375 z 0.125 occ O-2  1 beq b2  0.43330

    la 0.0159 lo 1.534753 lh 3.6854
    la 0.5791 lo 1.540596 lh 0.437
    la 0.0762 lo 1.541058 lh 0.6

`ymin_on_ymax` (also a child of `lam` per Technical_Reference.docx's own
keyword hierarchy) is reindented one level deeper alongside `la`/`lo`/`lh`,
even though it has no columns of its own to align.

This does not validate or change TOPAS semantics -- it only reformats
whitespace. Run scripts/check_inp_syntax.py afterward as usual.

Method: a site line is tokenized as `site NAME` followed by a sequence of
(keyword, value) pairs, where a keyword is one of a known fixed set
(SITE_KEYWORDS below) and its value is everything up to the next
recognized keyword (or end of line) -- this naturally captures both
single-token values ('x 0.25'), two-token values ('occ Ce+4 1'), and
equation-terminated values ('beq = b1;') without special-casing each one.

Consecutive site lines (blank lines allowed between them, but no other
non-blank, non-site line) are treated as one alignment group and padded
to a shared column width per keyword, using the widest value seen for
that keyword across the group. The final keyword on each line (whichever
comes last -- usually beq or the last u_ij) is left unpadded, since
trailing whitespace after it serves no purpose.

Usage:
    python3 fix_columns.py file.inp                  # rewrite in place, whole file
    python3 fix_columns.py file.inp -o out.inp        # write elsewhere
    python3 fix_columns.py file.inp --check           # print result to stdout, don't write
    python3 fix_columns.py file.inp --lines 26-31      # only touch lines 26-31 (1-indexed, inclusive)

`--lines` is meant for "fix columns on the selected text": alignment
groups/column widths are still computed from the FULL file (so a
selection covering only part of a group still lines up with the rest of
that group), but only lines whose 1-indexed number falls inside the given
range are actually rewritten -- everything else is left byte-for-byte
untouched. Omit `--lines` to fix columns through the whole file.
"""

import sys
import re
import argparse

SITE_KEYWORDS = ["x", "y", "z", "occ", "beq", "u11", "u22", "u33", "u12", "u13", "u23"]
SITE_LINE_RE = re.compile(r"^(\s*)site\s+(\S+)\s+(.*\S)\s*$")
KEYWORD_SPLIT_RE = re.compile(r"\b(" + "|".join(SITE_KEYWORDS) + r")\b")

# A value that's a plain number (optionally @/!-flagged, optionally
# negative) -- as opposed to an equation ('= ...;') or a text token like
# occ's species symbol ('Ce+4', 'O-2'). In a fixed-width font, right-
# aligning these (so the digits/decimal points line up column-wise down
# the page) reads far more naturally than left-aligning -- confirmed
# directly by the user (TOPAS-Academic's author): "can you also align
# numbers. Note, the font used is always [a] fixed character width."
# Text/equation columns keep the original left-justify behavior, since
# right-aligning a chemical symbol or an equation of varying shape
# wouldn't mean the same thing.
NUMERIC_VALUE_RE = re.compile(r"^[!@]?\s*-?\d")


def parse_site_line(line):
    """Returns (indent, name, {keyword: value_text}, keyword_order) or None if not a site line.

    'occ' is special-cased: its captured value ('Ce+4  1', 'O-2 1', ...) is
    split into two synthetic columns, 'occ_type' and 'occ_n', so the
    scattering-species token and the occupancy number each get their own
    independently aligned column -- matching the established convention
    ('occ Ce+4  1', single space after the keyword, not the generic
    two-space keyword/value separator used elsewhere).

    A keyword's value that's an equation ('= ... ;') is NOT re-split on a
    keyword-looking word inside its own RHS -- e.g. 'z = Get(x) + 0.1625;'
    must not have that inner 'x' mistaken for the start of a new x-column.
    A real corpus bug found and fixed here: the original version used a
    single blind KEYWORD_SPLIT_RE.split() over the whole line, which had
    no concept of an equation's extent, so 'Get(x)' inside a z-equation
    silently corrupted the whole line (the x column got overwritten with
    text meant for z, and vice versa) -- confirmed directly against
    test_examples/simple.inp's real 'z = Get(x) .99 + 0.1625;' site.
    """
    m = SITE_LINE_RE.match(line)
    if not m:
        return None
    indent, name, rest = m.groups()
    n = len(rest)

    # Find every keyword occurrence, then drop any match that falls
    # inside an EARLIER keyword's equation body (between its '=' and the
    # equation's own terminating ';') -- those are references inside an
    # expression, not new keyword boundaries.
    keyword_spans = []  # (kw, kw_start, kw_end)
    skip_before = 0
    for cand in KEYWORD_SPLIT_RE.finditer(rest):
        if cand.start() < skip_before:
            continue
        kw, kw_start, kw_end = cand.group(1), cand.start(), cand.end()
        keyword_spans.append((kw, kw_start, kw_end))
        after_ws = rest[kw_end:]
        stripped = after_ws.lstrip()
        if stripped.startswith("="):
            eq_idx = kw_end + (len(after_ws) - len(stripped))
            semi_idx = rest.find(";", eq_idx)
            skip_before = semi_idx + 1 if semi_idx != -1 else n

    fields = {}
    order = []
    for idx, (kw, kw_start, kw_end) in enumerate(keyword_spans):
        val_end = keyword_spans[idx + 1][1] if idx + 1 < len(keyword_spans) else n
        val = rest[kw_end:val_end].strip()
        if kw == "occ":
            val = re.sub(r"\s+", " ", val)
            occ_type, _, occ_n = val.partition(" ")
            fields["occ_type"] = occ_type
            fields["occ_n"] = occ_n
            order.append("occ_type")
            order.append("occ_n")
        else:
            fields[kw] = val
            order.append(kw)
    if not order:
        return None
    return indent, name, fields, order


def fix_group(lines_with_idx):
    """lines_with_idx: list of (line_index, indent, name, fields, order). Returns {line_index: new_line_text}."""
    name_w = max(len(name) for _, _, name, _, _ in lines_with_idx)
    # Canonical column order: union of keywords used, in SITE_KEYWORDS order
    # (with 'occ' expanded to its two synthetic sub-columns).
    canonical_order = []
    for kw in SITE_KEYWORDS:
        canonical_order.extend(["occ_type", "occ_n"] if kw == "occ" else [kw])

    used_keywords = []
    for _, _, _, fields, _ in lines_with_idx:
        for kw in canonical_order:
            if kw in fields and kw not in used_keywords:
                used_keywords.append(kw)

    col_width = {}
    col_numeric = {}
    for kw in used_keywords:
        vals = [fields[kw] for _, _, _, fields, _ in lines_with_idx if kw in fields]
        if vals:
            col_width[kw] = max(len(v) for v in vals)
            # Only right-align a column if EVERY value in it is numeric --
            # a column mixing a bare number with an equation (e.g. one
            # site's 'beq 0.2' alongside another's 'beq = b1;') stays
            # left-justified rather than producing a jagged half-and-half
            # column.
            col_numeric[kw] = all(NUMERIC_VALUE_RE.match(v) for v in vals)

    result = {}
    for idx, indent, name, fields, order in lines_with_idx:
        # The field actually written LAST for this row is whichever of its
        # own fields comes last in used_keywords (the CANONICAL/rewritten
        # order) -- NOT order[-1] (that row's own original, possibly
        # non-canonical, source order). These can disagree: a real corpus
        # pattern (site NAME num_posns # occ ... beq ... x ... y ... z ...)
        # writes x/y/z AFTER occ/beq, so order[-1] is 'z', but the rewritten
        # line always follows canonical x/y/z/occ/beq order, so 'beq' is
        # what's actually printed last -- using order[-1] left 'z' wrongly
        # unpadded mid-line (and, confirmed directly: made a second run
        # produce a DIFFERENT result than the first, since the first run's
        # own reordering changes what the row's "original order" even is).
        row_used_keywords = [kw for kw in used_keywords if kw in fields]
        last_kw = row_used_keywords[-1] if row_used_keywords else None
        segments = [f"{indent}site {name:<{name_w}}"]
        for kw in used_keywords:
            if kw not in fields:
                continue
            val = fields[kw]
            if kw == last_kw:
                padded = val
            elif col_numeric.get(kw):
                padded = f"{val:>{col_width[kw]}}"
            else:
                padded = f"{val:<{col_width[kw]}}"
            if kw == "occ_type":
                segments.append(f"occ {padded}")
            elif kw == "occ_n":
                segments.append(padded)
            else:
                segments.append(f"{kw} {padded}")
        result[idx] = " ".join(segments)
    return result


LAM_KEYWORDS = ["la", "lo", "lh"]
LAM_LINE_RE = re.compile(r"^(\s*)la\s+(\S+)\s+lo\s+(\S+)\s+lh\s+(\S+)\s*$")
LAM_KW_RE = re.compile(r"^(\s*)lam\b")
# ymin_on_ymax is also a child of lam (Technical_Reference.docx p.209's
# own keyword hierarchy, confirmed directly by the user, TOPAS-Academic's
# author) -- reindented the same one level deeper as la/lo/lh, but it's a
# single bare value with nothing to column-align, so it only needs its
# leading indent rewritten, not the fix_lam_group() treatment.
YMIN_ON_YMAX_RE = re.compile(r"^(\s*)(ymin_on_ymax\b.*)$")


def parse_lam_line(line):
    """Returns (indent, {'la':..,'lo':..,'lh':..}) or None if not a
    'la ... lo ... lh ...' emission-profile line (one line per emission
    line component inside a lam { } block, e.g. a .lam library file or an
    inlined CuKa5-style expansion) -- always exactly this fixed 3-field,
    fixed-order shape, unlike site's open-ended keyword set, so a plain
    single regex is enough (no equation/nested-keyword risk to guard
    against the way parse_site_line has to for 'z = Get(x) + ...;').
    """
    m = LAM_LINE_RE.match(line)
    if not m:
        return None
    indent, la, lo, lh = m.groups()
    return indent, {"la": la, "lo": lo, "lh": lh}


def fix_lam_group(lines_with_idx):
    """lines_with_idx: list of (line_index, indent, fields), where `indent`
    is the FORCED indent to write (one level -- 3 spaces, matching
    format_inp_hierarchy.py's own convention -- deeper than the nearest
    preceding 'lam' keyword line, not each line's own original indent).
    la/lo/lh lines are logically children of 'lam' even though 'lam' has
    no braces of its own to make that nesting visually obvious -- confirmed
    directly by the user (TOPAS-Academic's author). Returns
    {line_index: new_line_text}.
    """
    col_width = {
        kw: max(len(fields[kw]) for _, _, fields in lines_with_idx) for kw in LAM_KEYWORDS[:-1]
    }
    result = {}
    for idx, indent, fields in lines_with_idx:
        segments = []
        for kw in LAM_KEYWORDS:
            val = fields[kw]
            padded = val if kw == LAM_KEYWORDS[-1] else f"{val:<{col_width[kw]}}"
            segments.append(f"{kw} {padded}")
        result[idx] = indent + " ".join(segments)
    return result


def fix_columns(text, line_range=None):
    """
    line_range: optional (start, end) 1-indexed, inclusive line numbers
    ("fix columns on the selected text"). Alignment groups and column
    widths are always computed from the FULL text -- a selection
    covering only part of a group still lines up with the rest of that
    group -- but only lines whose 1-indexed number falls inside the
    range are actually rewritten; everything else is returned unchanged.
    Pass None (the default) to fix columns through the whole file.
    """
    # keepends=True: each entry keeps its own original line terminator (or
    # none, for a final line with no trailing newline), so reassembly never
    # has to guess at or reconstruct newline style.
    raw_lines = text.splitlines(keepends=True)
    bare_lines = [l.splitlines()[0] if l.splitlines() else "" for l in raw_lines]
    endings = [l[len(b):] for l, b in zip(raw_lines, bare_lines)]
    parsed = [parse_site_line(l) for l in bare_lines]

    replacements = {}
    group = []
    for i, p in enumerate(parsed):
        if p is not None:
            indent, name, fields, order = p
            group.append((i, indent, name, fields, order))
        elif bare_lines[i].strip() == "":
            continue  # blank line inside a group doesn't break it
        else:
            if len(group) >= 2:
                replacements.update(fix_group(group))
            group = []
    if len(group) >= 2:
        replacements.update(fix_group(group))

    # la/lo/lh groups (and ymin_on_ymax lines, see YMIN_ON_YMAX_RE above):
    # forced one indent level deeper than the nearest PRECEDING 'lam' line
    # (positional, not "last lam in the whole file" -- a later,
    # differently-indented 'lam' block updates the target). `lam_indent`
    # deliberately stays active across intervening non-la lines (blank
    # lines, a reindented 'ymin_on_ymax') rather than being cleared on the
    # next non-blank line the way the site-group scan above is -- la/lo/lh
    # syntax only ever appears inside a lam context in real TOPAS usage,
    # so there's no risk of it leaking into an unrelated later block, and
    # the real corpus pattern this was built for ('lam' -> 'ymin_on_ymax'
    # -> five la lines -> blank -> another 'ymin_on_ymax') needs exactly
    # this persistence.
    parsed_lam = [parse_lam_line(l) for l in bare_lines]
    lam_indent = None
    lam_group = []

    def flush_lam_group():
        nonlocal lam_group
        if lam_group:
            replacements.update(fix_lam_group(lam_group))
        lam_group = []

    for i, bare in enumerate(bare_lines):
        m_lam = LAM_KW_RE.match(bare)
        if m_lam:
            flush_lam_group()
            lam_indent = m_lam.group(1) + "   "
            continue
        p_lam = parsed_lam[i]
        if p_lam is not None and lam_indent is not None:
            _orig_indent, fields = p_lam
            lam_group.append((i, lam_indent, fields))
            continue
        m_ymin = YMIN_ON_YMAX_RE.match(bare) if lam_indent is not None else None
        if m_ymin is not None:
            flush_lam_group()
            replacements[i] = lam_indent + m_ymin.group(2)
            continue
        flush_lam_group()
    flush_lam_group()

    if line_range is not None:
        start, end = line_range
        replacements = {i: v for i, v in replacements.items() if start - 1 <= i <= end - 1}

    out_lines = [replacements.get(i, b) + e for i, (b, e) in enumerate(zip(bare_lines, endings))]
    return "".join(out_lines)


def parse_line_range(s):
    m = re.match(r"^(\d+)-(\d+)$", s.strip())
    if not m:
        raise argparse.ArgumentTypeError("expected START-END, e.g. 26-31")
    start, end = int(m.group(1)), int(m.group(2))
    if start < 1 or end < start:
        raise argparse.ArgumentTypeError("expected START-END with 1 <= START <= END")
    return start, end


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inp_file")
    parser.add_argument("-o", "--output", help="write to this file instead of overwriting the input")
    parser.add_argument("--check", action="store_true", help="print the result to stdout instead of writing any file")
    parser.add_argument(
        "--lines",
        type=parse_line_range,
        help="only fix columns on this 1-indexed, inclusive line range (e.g. 26-31) -- "
        "'fix columns on the selected text'; omit to fix columns through the whole file",
    )
    args = parser.parse_args()

    with open(args.inp_file, encoding="utf-8") as f:
        text = f.read()

    fixed = fix_columns(text, line_range=args.lines)

    if args.check:
        print(fixed)
        return

    out_path = args.output or args.inp_file
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(fixed)
    print(f"Written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
