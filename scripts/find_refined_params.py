#!/usr/bin/env python3
"""
find_refined_params.py -- List every INDEPENDENT refined parameter in a
TOPAS .inp file: named (or auto-named via bare '@'), NOT '!'-prefixed
(fixed), and -- if written as a named equation -- evaluating to a plain
numeric constant rather than a function of other parameters (a
DEPENDENT parameter; the manual's own distinction, Technical_Reference.pdf
section 2.9 "Naming of equations": "If this evaluates to a constant, a1
is an independent parameter and will be refined unless preceded by !;
otherwise it is treated as a dependent parameter.").

Method: fully macro-expands the file first (via expand_inp_macros.py,
this skill's own verified expander), THEN scans the EXPANDED text -- not
the raw file. This matters because a macro call's bare '@' argument
(e.g. `TOF_PV(@, 533.98529, ...)`) doesn't sit textually next to the
number it actually binds to; only after expansion does it become an
unambiguous `prm AUTO_NAME 533.98529 ...;` statement that can be
reliably parsed. Confirmed directly: `TOF_PV(@, 533.98529, ...)` expands
to `prm mb6d5dfaa_0 533.98529\\`_13.02250 min .0001 max = ...;`, and
`ADPs { @ v1 @ v2 ... }` expands to
`load u11 u22 u33 u12 u13 u23 { @ v1 @ v2 ... }`.

Several reliable, keyword-independent signals are combined on the
expanded text:
  1. Explicit `prm`/`local NAME ...` declarations -- covers every
     macro-internal parameter (virtually all built-in TOPAS macros
     declare their refinable slots this way) plus any `prm`/`local`
     written directly. `local` is genuinely re-scoped per xdd/phase (see
     the manual's "The local keyword" -- the SAME name in two different
     `local` statements is two INDEPENDENT parameters), so these are
     never deduplicated by name; bare `prm` at file scope has no such
     re-scoping ("parameters with the same name must have the same
     value" -- see point 4) and IS deduplicated.
  2. The '@' sigil on a small set of common DIRECT (non-macro) keywords
     that carry it straight in the kernel and never go through macro
     expansion at all (a/b/c/al/be/ga/scale/bkg). `bkg`'s own documented
     convention (only its FIRST coefficient needs the literal '@'; every
     later space-separated coefficient on the same line is independently
     refined too) is handled explicitly.
  3. `load u11 u22 u33 u12 u13 u23 { v1 v2 v3 v4 v5 v6 }` -- the ADPs
     macro's own expansion, TOPAS's general `load KW1 KW2 ... { v1 v2
     ... }` positional-loading construct (manual section 2.18.1)
     specialized to the one safe, unambiguous case: the full canonical
     6-name ADP set with exactly 6 matching value slots. Deliberately
     NOT a general `load` parser -- other real `load` forms have
     entirely different internal structure (`load exclude { 20 22 32
     35 }` is flat range-pairs; `load sh_Cij_prm { k00 !sh2_c00 1.0000
     k41 sh2_c41 0.1000 ... }` is label/value pairs under ONE keyword) --
     so this only fires when the keyword list is EXACTLY the 6 ADP names
     and the value count matches; anything else is left alone rather
     than guessed at.
  4. A curated (not exhaustive) list of common directly-written (non-@,
     non-macro) NAMED keyword values -- `beq`/`u11..u23`/`a`/`b`/`c`/
     `al`/`be`/`ga`/`scale` -- e.g. `beq b1 1.34160`. Deduplicated by
     name: TOPAS enforces "parameters with the same name must have the
     same value" (Technical_Reference.pdf section 2.4) with no `local`-
     style re-scoping for these bare forms, so the same name written on
     several site lines (a shared beq, say) is one parameter, not
     several -- reported once.

Real gaps found and fixed this way, confirmed and diagnosed directly by
the user (TOPAS-Academic's author) against
test_examples/sp/serine_i_evans_n_ta_bang_rot-z.inp:
  - `site D1 ... beq b1 1.34160...` (point 4) -- a bare-named keyword
    value on a keyword outside the original narrow a/b/c/al/be/ga/scale
    list.
  - `site C1 ... ADPs { @ ... @ ... }` (point 3) -- six auto-@-refined
    ADP components that only become individually identifiable as
    u11/u22/u33/u12/u13/u23 after seeing the ADPs macro's own expansion
    to `load u11 u22 u33 u12 u13 u23 { ... }`.

Known limitations, stated plainly rather than overclaimed:
  - Bare, unnamed, un-'@'-flagged numeric values (e.g. a rigid body's
    reported site x/y/z, which are COMPUTED OUTPUTS of the rigid-body
    transform -- translate/rotate/Z-matrix internal geometry -- not
    independent parameters themselves) are deliberately NOT reported,
    since there's no reliable way to distinguish "independently
    refinable bare value" from "computed/reported bare value" by text
    pattern alone. Only a name (bare, '!', or '@') or the '@' sigil is
    trusted as a real refinement signal.
  - A handful of other directly-written keywords outside the curated
    lists in points 2 and 4, and `load` forms other than the ADPs case
    in point 3, could still be missed -- a best-effort scan, not a full
    kernel-equivalent parser.
  - Expanded-text line numbers do NOT match the original file's line
    numbers for macro-generated content (same caveat as
    expand_inp_macros.py itself) -- reported by NAME primarily, with the
    expanded-text line shown for reference only.

Usage:
    python3 find_refined_params.py file.inp
    python3 find_refined_params.py file.inp -o report.txt
"""

import sys
import os
import re
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import check_inp_syntax as cis
from expand_inp_macros import expand_file
from symmetry_utils import ADP_NAMES

PRM_LOCAL_RE = re.compile(r"\b(prm|local)\b")
LOAD_RE = re.compile(r"\bload\b")
IDENT_RE = re.compile(r"[A-Za-z_]\w*")
NUMBER_RE = cis.E_ARG_NUMBER_TOKEN_RE
NAME_TOK_RE = re.compile(r"(?:([!@])?([A-Za-z_]\w*))|([!@])")

# Keywords whose OWN '@' sigil is handled directly by the kernel (never a
# macro call) -- confirmed real forms seen throughout this skill's corpus,
# e.g. 'a @ 10.820412', 'scale @ 0.001', 'bkg @ 52.65 -7.2 20.6 -6.3'.
DIRECT_AT_KEYWORDS = ("a", "b", "c", "al", "be", "ga", "scale")

# Curated (not exhaustive) directly-written keywords known to carry a bare
# NAME before their value outside prm/local/@ -- e.g. 'beq b1 1.34160'.
NAMED_VALUE_KEYWORDS = ("beq",) + tuple(ADP_NAMES) + DIRECT_AT_KEYWORDS


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def _in_any_span(pos, spans):
    return any(s <= pos < e for s, e in spans)


def parse_prm_local_statements(clean_text):
    """Returns (independent, dependent, spans) -- independent/dependent
    are lists of dicts (independent entries additionally carry
    'scoped': True for `local`, which is never deduplicated by name,
    False for bare `prm`, which is), spans is the list of (start, end)
    character ranges each prm/local statement's own name/value/equation
    occupies, used by the other parsers below to avoid re-discovering
    the same '@'/value token a second time under a different label."""
    independent = []
    dependent = []
    spans = []
    n = len(clean_text)
    for m in PRM_LOCAL_RE.finditer(clean_text):
        scoped = m.group(1) == "local"
        pos = m.end()
        while pos < n and clean_text[pos] in " \t\r\n":
            pos += 1
        if pos < n and clean_text[pos] == "=":
            end = clean_text.find(";", pos)
            if end == -1:
                continue
            expr = clean_text[pos + 1:end].strip()
            spans.append((m.start(), end + 1))
            plain = cis.parse_plain_numeric_equation(expr)
            if plain is not None:
                independent.append({"name": None, "sigil": "", "value": plain, "scoped": scoped,
                                     "line": line_of(clean_text, m.start())})
            continue

        tok_m = NAME_TOK_RE.match(clean_text, pos)
        if not tok_m or not tok_m.group(0):
            continue
        sigil = tok_m.group(1) or tok_m.group(3) or ""
        name = tok_m.group(2)
        k = tok_m.end()
        while k < n and clean_text[k] in " \t\r\n":
            k += 1

        if k < n and clean_text[k] == "=":
            end = clean_text.find(";", k)
            if end == -1:
                continue
            expr = clean_text[k + 1:end].strip()
            spans.append((m.start(), end + 1))
            if sigil == "!":
                continue
            plain = cis.parse_plain_numeric_equation(expr)
            if plain is not None:
                independent.append({"name": name, "sigil": sigil, "value": plain, "scoped": scoped,
                                     "line": line_of(clean_text, m.start())})
            else:
                dependent.append({"name": name, "expr": expr,
                                   "line": line_of(clean_text, m.start())})
            continue

        val_m = NUMBER_RE.match(clean_text[k:])
        if not val_m or not val_m.group(0):
            continue
        end = k + val_m.end()
        spans.append((m.start(), end))
        try:
            val = float(val_m.group(0).split("`")[0])
        except ValueError:
            continue
        if sigil == "!":
            continue
        independent.append({"name": name, "sigil": sigil, "value": val, "scoped": scoped,
                             "line": line_of(clean_text, m.start())})
    return independent, dependent, spans


def parse_direct_at_keywords(clean_text, exclude_spans):
    """Returns a list of dicts for the curated DIRECT_AT_KEYWORDS forms
    ('a @ 5.4031', 'bkg @ c0 c1 c2 ...' with every space-separated
    coefficient after the '@' independently refined, not just the
    first)."""
    results = []
    n = len(clean_text)
    for kw in DIRECT_AT_KEYWORDS + ("bkg",):
        for m in re.finditer(r"\b" + re.escape(kw) + r"\b", clean_text):
            if _in_any_span(m.start(), exclude_spans):
                continue
            pos = m.end()
            while pos < n and clean_text[pos] in " \t\r\n":
                pos += 1
            if pos >= n or clean_text[pos] != "@":
                continue
            pos += 1
            while pos < n and clean_text[pos] in " \t\r\n":
                pos += 1
            if kw != "bkg":
                val_m = NUMBER_RE.match(clean_text[pos:])
                if val_m and val_m.group(0):
                    try:
                        val = float(val_m.group(0).split("`")[0])
                        results.append({"name": None, "keyword": kw, "value": val,
                                         "line": line_of(clean_text, m.start())})
                    except ValueError:
                        pass
                continue
            idx = 0
            while True:
                val_m = NUMBER_RE.match(clean_text[pos:])
                if not val_m or not val_m.group(0):
                    break
                try:
                    val = float(val_m.group(0).split("`")[0])
                    results.append({"name": None, "keyword": f"bkg[{idx}]", "value": val,
                                     "line": line_of(clean_text, m.start())})
                except ValueError:
                    break
                pos += val_m.end()
                idx += 1
                while pos < n and clean_text[pos] in " \t":
                    pos += 1
                if pos < n and clean_text[pos] == "\n":
                    break
    return results


def parse_adp_load_blocks(clean_text, exclude_spans):
    """Recognizes 'load u11 u22 u33 u12 u13 u23 { v1 v2 v3 v4 v5 v6 }'
    (any order) -- the ADPs macro's own expansion -- positionally
    matching each value to its real ADP component name. Only trusted
    when the FULL canonical 6-name ADP_NAMES set is listed and the
    '{ }' block contains EXACTLY 6 value slots; any other 'load ...'
    form is left alone (see module docstring point 3)."""
    results = []
    n = len(clean_text)
    for m in LOAD_RE.finditer(clean_text):
        if _in_any_span(m.start(), exclude_spans):
            continue
        pos = m.end()
        keywords = []
        while True:
            while pos < n and clean_text[pos] in " \t\r\n":
                pos += 1
            km = IDENT_RE.match(clean_text, pos)
            if not km:
                break
            keywords.append(km.group(0))
            pos = km.end()
        if sorted(keywords) != sorted(ADP_NAMES):
            continue
        while pos < n and clean_text[pos] in " \t\r\n":
            pos += 1
        if pos >= n or clean_text[pos] != "{":
            continue
        pos += 1
        values = []
        while pos < n:
            while pos < n and clean_text[pos] in " \t\r\n":
                pos += 1
            if pos < n and clean_text[pos] == "}":
                pos += 1
                break
            sigil = ""
            if pos < n and clean_text[pos] in "!@":
                sigil = clean_text[pos]
                pos += 1
                while pos < n and clean_text[pos] in " \t\r\n":
                    pos += 1
            val_m = NUMBER_RE.match(clean_text[pos:])
            if not val_m or not val_m.group(0):
                break
            try:
                val = float(val_m.group(0).split("`")[0])
            except ValueError:
                break
            values.append((sigil, val))
            pos += val_m.end()
        if len(values) != len(ADP_NAMES):
            continue
        for kw, (sigil, val) in zip(keywords, values):
            if sigil == "!":
                continue
            results.append({"keyword": kw, "name": None, "value": val,
                             "line": line_of(clean_text, m.start())})
    return results


def parse_named_keyword_values(clean_text, exclude_spans):
    """Curated (not exhaustive) directly-written keywords known to carry
    a bare NAME before their value -- e.g. 'beq b1 1.34160'. Results are
    deduplicated by name (see module docstring point 4): unlike `local`,
    these bare forms are never re-scoped, so the same name appearing on
    several lines is the SAME parameter, reported once."""
    seen_names = {}
    results = []
    n = len(clean_text)
    for kw in NAMED_VALUE_KEYWORDS:
        for m in re.finditer(r"\b" + re.escape(kw) + r"\b", clean_text):
            if _in_any_span(m.start(), exclude_spans):
                continue
            pos = m.end()
            while pos < n and clean_text[pos] in " \t\r\n":
                pos += 1
            if pos < n and clean_text[pos] in "!@=":
                continue  # handled by the fixed / '@' / equation paths instead
            name_m = IDENT_RE.match(clean_text, pos)
            if not name_m:
                continue
            name = name_m.group(0)
            k = name_m.end()
            while k < n and clean_text[k] in " \t\r\n":
                k += 1
            val_m = NUMBER_RE.match(clean_text[k:])
            if not val_m or not val_m.group(0):
                continue
            try:
                val = float(val_m.group(0).split("`")[0])
            except ValueError:
                continue
            if name in seen_names:
                continue
            seen_names[name] = True
            results.append({"keyword": kw, "name": name, "value": val,
                             "line": line_of(clean_text, m.start())})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inp_file")
    parser.add_argument("-o", "--output", help="write the report to this file instead of stdout")
    parser.add_argument("--run-number", type=int, default=0)
    args = parser.parse_args()

    expanded, warnings = expand_file(args.inp_file, run_number=args.run_number)
    clean = cis.strip_comments_and_strings(expanded)

    independent, dependent, prm_local_spans = parse_prm_local_statements(clean)
    direct_at = parse_direct_at_keywords(clean, prm_local_spans)
    adp_loads = parse_adp_load_blocks(clean, prm_local_spans)
    named_direct = parse_named_keyword_values(clean, prm_local_spans)

    # bare `prm` (not `local`) has no re-scoping -- dedup by name, same as
    # named_direct above.
    named_prm_local = [p for p in independent if p["name"]]
    seen = {}
    deduped_named = []
    for p in named_prm_local:
        if not p["scoped"] and p["name"] in seen:
            continue
        if not p["scoped"]:
            seen[p["name"]] = True
        deduped_named.append(p)
    deduped_named.sort(key=lambda p: p["name"])
    anon_prm = [p for p in independent if not p["name"]]

    lines = []
    lines.append(f"Independent refined parameters in {args.inp_file}")
    lines.append("(named or auto-named via '@', not '!'-fixed, not a dependent equation)")
    lines.append("=" * 78)
    lines.append("")

    lines.append(f"-- {len(deduped_named)} named prm/local parameters --")
    for p in deduped_named:
        sigil_str = f"'{p['sigil']}' " if p["sigil"] else ""
        scope_str = "local, per-scope" if p["scoped"] else "prm, global"
        lines.append(f"  {p['name']:<20} = {p['value']:<16.8g}  ({sigil_str}{scope_str}, expanded-text line {p['line']})")
    lines.append("")

    if direct_at:
        lines.append(f"-- {len(direct_at)} directly-written '@'-flagged keyword values (a/b/c/al/be/ga/scale/bkg) --")
        for p in direct_at:
            lines.append(f"  {p['keyword']:<20} = {p['value']:<16.8g}  (expanded-text line {p['line']})")
        lines.append("")

    if adp_loads:
        lines.append(f"-- {len(adp_loads)} ADP components from 'load u11 u22 u33 u12 u13 u23 {{ ... }}' blocks --")
        for p in adp_loads:
            lines.append(f"  {p['keyword']:<20} = {p['value']:<16.8g}  (expanded-text line {p['line']})")
        lines.append("")

    if named_direct:
        lines.append(f"-- {len(named_direct)} other directly-written named keyword values (deduplicated by name) --")
        for p in named_direct:
            lines.append(f"  {p['name']:<20} = {p['value']:<16.8g}  ({p['keyword']}, expanded-text line {p['line']})")
        lines.append("")

    if anon_prm:
        lines.append(f"-- {len(anon_prm)} anonymous (unnamed) independent equations, e.g. 'prm = 5;' --")
        for p in anon_prm:
            lines.append(f"  (unnamed)            = {p['value']:<16.8g}  (expanded-text line {p['line']})")
        lines.append("")

    total = len(deduped_named) + len(direct_at) + len(adp_loads) + len(named_direct) + len(anon_prm)
    lines.append(f"TOTAL independent refined parameters found: {total}")
    lines.append("")
    lines.append(f"(For reference only, not part of the total above: {len(dependent)} non-'!' DEPENDENT "
                  f"named equations were also found -- functions of other parameters, e.g. "
                  f"'prm a1 = a2 + a3/2;', not independently refined themselves. Note this count excludes "
                  f"any '!'-prefixed dependent equation, e.g. 'local !b1 = biso_0 + biso_1*Pressure + ...;' "
                  f"-- those are skipped outright for being '!'-fixed before their equation shape is even "
                  f"considered, the same as any other fixed value, so they aren't tallied here either way.)")
    lines.append("")
    lines.append("Known limitations of this scan -- see this script's own module docstring for the full "
                  "reasoning: bare, unnamed, un-'@' numeric values (e.g. a rigid body's reported/computed "
                  "site x/y/z) are deliberately NOT reported, since they can't be reliably distinguished "
                  "from a genuinely independent bare value by text pattern alone; a handful of other "
                  "directly-written keywords outside the curated lists, and 'load' forms other than the "
                  "ADPs case, could also be missed. This is a best-effort static scan, not a full "
                  "kernel-equivalent parser.")

    if warnings:
        lines.append("")
        lines.append(f"Macro-expansion warnings ({len(warnings)}):")
        for w in warnings:
            lines.append(f"  {w}")

    report = "\n".join(lines) + "\n"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
