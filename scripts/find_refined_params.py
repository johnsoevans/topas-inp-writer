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
    lists in points 2 and 4, and `load` forms other than the ADPs and
    hkl_m_d_th2/I cases in point 3, could still be missed -- a
    best-effort scan, not a full kernel-equivalent parser. Confirmed
    directly against test_examples/clay.inp (tc.exe vs this script,
    comparing "Num independent parameters"): `secondary_soller_angle`
    inside a `Full_Axial_Model(...)` call is one such uncurated
    directly-'@'-flagged keyword.
  - `spherical_harmonics_hkl ... sh_order N` generates a Laue-class-
    dependent NUMBER of refined coefficients purely inside the kernel --
    there is no static text pattern in the .inp source that reveals this
    count (it depends on the phase's Laue class and N via kernel-internal
    combinatorics), so it is NOT counted at all by this script. Confirmed
    directly: test_examples/clay.inp's `sh_order 8` block alone accounts
    for 44 of tc.exe's 222 reported independent parameters (222 vs this
    script's 178 with the block artificially disabled, vs 174 with it
    left in) -- by far the largest single known gap seen in practice, and
    deliberately left unimplemented rather than guessed at.
  - The `load hkl_m_d_th2 I { ... }` parser (point 3) treats any
    non-'!' intensity as independent, matching the manual's documented
    default ("intensity parameters are given the code of @"). This is
    WRONG for at least one confirmed real case: test_examples/quant/
    quant-4.inp provides an explicit hkl_m_d_th2/I block (12 rows) whose
    intensities tc.exe evidently does NOT treat as independently
    refined (tc.exe reports 17 total independent parameters for this
    file; this script's other categories alone already account for 14,
    leaving no room for the 12 hkl rows to be genuinely independent
    too) -- likely something specific to how this quant example uses
    the hkl_Is phase (e.g. as fixed reference intensities rather than a
    Pawley extraction), not yet understood well enough to encode a
    general rule for. Confirmed via tc.exe directly, not assumed; left
    as a known residual gap rather than guessed at.
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
# filament_length/sample_length/receiving_slit_length/primary_soller_angle/
# secondary_soller_angle are Full_Axial_Model(...)'s own expansion (an
# 'axial_conv <keyword> <value> ...' line) -- confirmed via a systematic,
# reproducible tc.exe-vs-script undercount of exactly 1 across nearly every
# curated-corpus file using Full_Axial_Model (quant-1..5, many, lab61,
# zro2, cylcorr, robust, clay, ...): 'secondary_soller_angle @ 8' was
# invisible to this scan entirely before being added here.
#
# Extended after a full curated-corpus tc.exe-vs-script parameter-count
# sweep (169 command lines) turned up 104 unexplained undercounts. The
# single biggest driver, by far: site 'x'/'y'/'z' coordinates written
# directly '@'-flagged (e.g. 'site S1 x @ 0.80985` y @ 0.18146` z @
# 0.74042`', confirmed in test_examples/single-crystal/ylidma.inp,
# test_examples/mag/mag.inp, test_examples/alvo4-grs-auto.inp) or bare-
# NAMED ('x x2 0.22', confirmed in test_examples/benzene.inp) -- neither
# form was recognized by ANY parser in this module before now, despite
# 'site $site [x E] [y E] [z E]' being direct, non-macro kernel syntax
# (Keywords chapter, Technical Reference). The same sweep also confirmed:
# 'beq'/ADP_NAMES carry a direct '@' form too (e.g. 'beq @ 1', 'u11 @ .1',
# confirmed in mag.inp) -- previously only their bare-NAMED form was
# handled (see NAMED_VALUE_KEYWORDS below), never '@'; 'mlx'/'mly'/'mlz'
# (magnetic moment components, mag.inp); 'Flack' (single-crystal Flack
# parameter, single-crystal/ylidma.inp); and the rigid-body transform
# keywords 'rotate' (takes its rotation-angle value directly, e.g.
# 'rotate @ 30 qx = ...;') plus tx/ty/tz/ta/tb/tc (translate),
# qx/qy/qz/qa/qb/qc (rotate's own axis-vector sub-keywords), ux/uy/uz/
# ua/ub/uc (point_for_site) -- confirmed in test_examples/rigid/rigidb.inp
# ('translate ta @ 0.13 tb @ 0.17 tc @ 0.33').
DIRECT_AT_KEYWORDS = ("a", "b", "c", "al", "be", "ga", "scale",
                       "filament_length", "sample_length", "receiving_slit_length",
                       "primary_soller_angle", "secondary_soller_angle",
                       "x", "y", "z", "beq", "mlx", "mly", "mlz", "Flack",
                       "rotate", "tx", "ty", "tz", "ta", "tb", "tc",
                       "qx", "qy", "qz", "qa", "qb", "qc",
                       "ux", "uy", "uz", "ua", "ub", "uc") + tuple(ADP_NAMES)

# Curated (not exhaustive) directly-written keywords known to carry a bare
# NAME before their value outside prm/local/@ -- e.g. 'beq b1 1.34160',
# 'x x2 0.22' (test_examples/benzene.inp). DIRECT_AT_KEYWORDS is now a
# superset of the original narrow ('beq',)+ADP_NAMES list, so this is
# just that -- no separate keyword set needed.
NAMED_VALUE_KEYWORDS = DIRECT_AT_KEYWORDS


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def loop_multiplier(p, clean_text, for_loop_spans, named):
    """How many times TOPAS actually evaluates the loop body this entry's
    'line' sits in -- 1 if it's not inside a for xdds/for strs[N to M]
    construct at all, and ALSO 1 if `named` is True (see below).

    Confirmed empirically, not assumed -- a bare NAMED declaration
    ('prm test_named_prm 1 min -2 max 2') inside a `for xdds { ... }`
    applied to 2 xdds reported 'Num independent parameters not taking
    part in refinement: 1', not 2: a bare name is subject to TOPAS's
    kernel-enforced 'parameters with the same name must have the same
    value' rule (Technical_Reference.pdf section 2.4) REGARDLESS of
    being inside a for-loop, so it stays ONE shared parameter across
    every iteration, not one per iteration. An ANONYMOUS '@' declaration
    in the exact same test (same 2-xdd loop, just 'prm @ 0.5 min -2
    max 2' instead) reported '2', confirming '@' -- having no name to
    share an identity by -- genuinely gets a fresh instance each
    iteration. This is why every caller below passes `named=True` only
    for entries that are known, by construction of the parser that
    produced them, to always carry an explicit name (parse_named_
    keyword_values, and 'local'/'prm' entries in deduped_named where
    p['scoped'] is False) -- 'local' entries (p['scoped'] is True) are
    NOT included in that named-and-shared set, since 'local' is already
    separately established (see this module's own docstring, point 1)
    to be genuinely re-scoped per xdd/phase regardless of naming, which
    a for-loop's once-per-xdd evaluation directly extends rather than
    contradicts."""
    if named:
        return 1
    return cis.for_loop_multiplier_at_line(p["line"], clean_text, for_loop_spans)


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


# 'occ $atom E [beq E] [scale_occ E]' -- the value slot sits AFTER an
# atom-type token (e.g. 'occ Al+3 @ 1', 'occ 26Mg+2 0.5'), unlike every
# other DIRECT_AT_KEYWORDS form where the value follows the keyword
# immediately -- confirmed in test_examples/alvo4-grs-auto.inp
# ('occ Al+3 @ 1 min 1 max 1.85'). Needs its own parser to skip the
# atom-type token first, same reason 'bkg' already needed one.
OCC_RE = re.compile(r"\bocc\b")
ATOM_TYPE_TOK_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+-]*")


def parse_occ_values(clean_text, exclude_spans):
    """Returns entries for both 'occ $atom @ value' (anonymous) and
    'occ $atom NAME value' (bare-named, deduplicated by name) forms."""
    results = []
    seen_names = {}
    n = len(clean_text)
    for m in OCC_RE.finditer(clean_text):
        if _in_any_span(m.start(), exclude_spans):
            continue
        pos = m.end()
        while pos < n and clean_text[pos] in " \t\r\n":
            pos += 1
        atom_m = ATOM_TYPE_TOK_RE.match(clean_text, pos)
        if not atom_m:
            continue
        pos = atom_m.end()
        while pos < n and clean_text[pos] in " \t\r\n":
            pos += 1
        if pos < n and clean_text[pos] == "!":
            continue
        name = None
        flagged = False
        if pos < n and clean_text[pos] == "@":
            flagged = True
            pos += 1
            while pos < n and clean_text[pos] in " \t\r\n":
                pos += 1
        else:
            name_m = IDENT_RE.match(clean_text, pos)
            if name_m and name_m.group(0) not in ("beq", "scale_occ", "min", "max", "del"):
                name = name_m.group(0)
                pos = name_m.end()
                while pos < n and clean_text[pos] in " \t\r\n":
                    pos += 1
        if not flagged and name is None:
            # Bare, unnamed, un-'@' value -- fixed by convention (same
            # rule as everywhere else in this module), not independent.
            continue
        val_m = NUMBER_RE.match(clean_text[pos:])
        if not val_m or not val_m.group(0):
            continue
        try:
            val = float(val_m.group(0).split("`")[0])
        except ValueError:
            continue
        if name:
            if name in seen_names:
                continue
            seen_names[name] = True
        results.append({"name": name, "keyword": "occ", "value": val,
                         "line": line_of(clean_text, m.start())})
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


# Manual-confirmed row layout for the Pawley/hkl_Is refined-intensity load
# form: 'load hkl_m_d_th2 I { h k l m d th2 @ I ... }' --
# references/21-keyword-index.md: '[hkl_m_d_th2 # # # # # # I E]...'
# documents hkl_m_d_th2 itself as SIX bare numbers (h, k, l, m, d, th2)
# followed by ONE I value (the only one that carries a '@'/'!' refinement
# sigil) -- a 7-value repeating row, not one value per listed keyword name
# (unlike the ADP case, where each of the 6 names maps 1:1 to one value).
# Confirmed against real corpus files (test_examples/clay.inp,
# test_examples/quant/quant-4.inp) that were undercounted 222 vs 20 (tc.exe
# vs this script) before this was added -- every '@'-flagged reflection
# intensity in the load block was previously invisible to this scan
# entirely, same class of gap as the ADP case in point 3 of the module
# docstring, just a different fixed keyword list.
HKL_M_D_TH2_ROW_LEN = 7  # h k l m d th2 I


def parse_hkl_intensity_load_blocks(clean_text, exclude_spans):
    """Recognizes 'load hkl_m_d_th2 I { ... }' (either keyword order) --
    the Pawley/hkl_Is refined-reflection-intensity form. Each 7-value row
    (h, k, l, m, d, th2, I) contributes exactly one independent parameter
    unless the trailing I value is '!'-fixed."""
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
        if sorted(keywords) != sorted(("hkl_m_d_th2", "I")):
            continue
        while pos < n and clean_text[pos] in " \t\r\n":
            pos += 1
        if pos >= n or clean_text[pos] != "{":
            continue
        pos += 1
        row = []
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
            row.append((sigil, val))
            pos += val_m.end()
            # A refined-but-not-yet-error-calculated intensity can end in a
            # bare trailing backtick with no error digits (e.g. '2.96309`'
            # before 'do_errors' has run) -- NUMBER_RE requires digits after
            # '`', so it doesn't consume this marker; skip it explicitly or
            # the next value's scan starts mid-token and the whole block
            # aborts after just one row (confirmed against test_examples/
            # clay.inp, which undercounted 1 row instead of ~154).
            if pos < n and clean_text[pos] == "`":
                pos += 1
            if len(row) == HKL_M_D_TH2_ROW_LEN:
                i_sigil, i_val = row[-1]
                if i_sigil != "!":
                    results.append({"keyword": "I", "name": None, "value": i_val,
                                     "line": line_of(clean_text, m.start())})
                row = []
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
    for_loop_spans = cis.find_for_loop_multipliers(clean)

    independent, dependent, prm_local_spans = parse_prm_local_statements(clean)
    direct_at = parse_direct_at_keywords(clean, prm_local_spans)
    adp_loads = parse_adp_load_blocks(clean, prm_local_spans)
    hkl_i_loads = parse_hkl_intensity_load_blocks(clean, prm_local_spans)
    named_direct = parse_named_keyword_values(clean, prm_local_spans)
    occ_values = parse_occ_values(clean, prm_local_spans)
    occ_named = [p for p in occ_values if p["name"]]
    occ_anon = [p for p in occ_values if not p["name"]]

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

    def mult_suffix(m):
        return f"  [x{m}, inside a for xdds/for strs loop]" if m > 1 else ""

    def weighted_count(entries, named):
        return sum(loop_multiplier(p, clean, for_loop_spans, named) for p in entries)

    lines = []
    lines.append(f"Independent refined parameters in {args.inp_file}")
    lines.append("(named or auto-named via '@', not '!'-fixed, not a dependent equation)")
    lines.append("=" * 78)
    lines.append("")

    # deduped_named mixes bare `prm` (named=True -- shared/never multiplied,
    # regardless of for-loop context) and `local` (named=False for this
    # purpose -- genuinely re-scoped per xdd/phase, which a for-loop's
    # once-per-xdd evaluation extends rather than contradicts) -- see
    # loop_multiplier()'s own docstring for the confirmed empirical basis.
    n_named = sum(loop_multiplier(p, clean, for_loop_spans, named=not p["scoped"]) for p in deduped_named)
    lines.append(f"-- {len(deduped_named)} named prm/local parameters ({n_named} counting for-loop repetition) --")
    for p in deduped_named:
        m = loop_multiplier(p, clean, for_loop_spans, named=not p["scoped"])
        sigil_str = f"'{p['sigil']}' " if p["sigil"] else ""
        scope_str = "local, per-scope" if p["scoped"] else "prm, global"
        lines.append(f"  {p['name']:<20} = {p['value']:<16.8g}  ({sigil_str}{scope_str}, expanded-text line {p['line']}){mult_suffix(m)}")
    lines.append("")

    if direct_at:
        # Always anonymous by construction (parse_direct_at_keywords never
        # captures a name) -- always eligible to multiply.
        n_direct_at = weighted_count(direct_at, named=False)
        lines.append(f"-- {len(direct_at)} directly-written '@'-flagged keyword values (a/b/c/al/be/ga/scale/bkg) "
                      f"({n_direct_at} counting for-loop repetition) --")
        for p in direct_at:
            m = loop_multiplier(p, clean, for_loop_spans, named=False)
            lines.append(f"  {p['keyword']:<20} = {p['value']:<16.8g}  (expanded-text line {p['line']}){mult_suffix(m)}")
        lines.append("")
    else:
        n_direct_at = 0

    if adp_loads:
        # Always anonymous/positional by construction (parse_adp_load_blocks
        # never captures a name either) -- always eligible to multiply.
        n_adp_loads = weighted_count(adp_loads, named=False)
        lines.append(f"-- {len(adp_loads)} ADP components from 'load u11 u22 u33 u12 u13 u23 {{ ... }}' blocks "
                      f"({n_adp_loads} counting for-loop repetition) --")
        for p in adp_loads:
            m = loop_multiplier(p, clean, for_loop_spans, named=False)
            lines.append(f"  {p['keyword']:<20} = {p['value']:<16.8g}  (expanded-text line {p['line']}){mult_suffix(m)}")
        lines.append("")
    else:
        n_adp_loads = 0

    if hkl_i_loads:
        # Always anonymous/positional by construction -- always eligible
        # to multiply, same as adp_loads above.
        n_hkl_i_loads = weighted_count(hkl_i_loads, named=False)
        lines.append(f"-- {len(hkl_i_loads)} Pawley/hkl_Is reflection intensities from "
                      f"'load hkl_m_d_th2 I {{ ... }}' blocks "
                      f"({n_hkl_i_loads} counting for-loop repetition) --")
        for p in hkl_i_loads:
            m = loop_multiplier(p, clean, for_loop_spans, named=False)
            lines.append(f"  {p['keyword']:<20} = {p['value']:<16.8g}  (expanded-text line {p['line']}){mult_suffix(m)}")
        lines.append("")
    else:
        n_hkl_i_loads = 0

    if occ_values:
        # occ_anon is always eligible to multiply (like direct_at);
        # occ_named is deduplicated-by-name/shared, like named_direct.
        n_occ_anon = weighted_count(occ_anon, named=False)
        n_occ_named = weighted_count(occ_named, named=True)
        n_occ = n_occ_anon + n_occ_named
        lines.append(f"-- {len(occ_values)} 'occ' (site occupancy) values "
                      f"({n_occ} counting for-loop repetition) --")
        for p in occ_anon:
            m = loop_multiplier(p, clean, for_loop_spans, named=False)
            lines.append(f"  (unnamed)            = {p['value']:<16.8g}  (occ, expanded-text line {p['line']}){mult_suffix(m)}")
        for p in occ_named:
            m = loop_multiplier(p, clean, for_loop_spans, named=True)
            lines.append(f"  {p['name']:<20} = {p['value']:<16.8g}  (occ, expanded-text line {p['line']}){mult_suffix(m)}")
        lines.append("")
    else:
        n_occ = 0

    if named_direct:
        # Always named by construction (parse_named_keyword_values only
        # matches the bare-NAME form) -- shared/never multiplied.
        n_named_direct = weighted_count(named_direct, named=True)
        lines.append(f"-- {len(named_direct)} other directly-written named keyword values (deduplicated by name) "
                      f"({n_named_direct} counting for-loop repetition) --")
        for p in named_direct:
            m = loop_multiplier(p, clean, for_loop_spans, named=True)
            lines.append(f"  {p['name']:<20} = {p['value']:<16.8g}  ({p['keyword']}, expanded-text line {p['line']}){mult_suffix(m)}")
        lines.append("")
    else:
        n_named_direct = 0

    if anon_prm:
        # Always unnamed by construction -- always eligible to multiply.
        n_anon_prm = weighted_count(anon_prm, named=False)
        lines.append(f"-- {len(anon_prm)} anonymous (unnamed) independent equations, e.g. 'prm = 5;' "
                      f"({n_anon_prm} counting for-loop repetition) --")
        for p in anon_prm:
            m = loop_multiplier(p, clean, for_loop_spans, named=False)
            lines.append(f"  (unnamed)            = {p['value']:<16.8g}  (expanded-text line {p['line']}){mult_suffix(m)}")
        lines.append("")
    else:
        n_anon_prm = 0

    total_written = (len(deduped_named) + len(direct_at) + len(adp_loads) + len(hkl_i_loads)
                      + len(occ_values) + len(named_direct) + len(anon_prm))
    total = n_named + n_direct_at + n_adp_loads + n_hkl_i_loads + n_occ + n_named_direct + n_anon_prm
    lines.append(f"TOTAL independent refined parameters found: {total} "
                  f"({total_written} distinct declarations in the source text, some repeated by a "
                  f"for xdds/for strs loop -- see check_inp_syntax.find_for_loop_multipliers)")
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
                  "kernel-equivalent parser. For-loop repetition ('for xdds { ... }', 'for strs { ... }', "
                  "'for strs N to M { ... }') is accounted for in the TOTAL above, confirmed empirically "
                  "(not assumed) against a minimal test file: a bare NAMED parameter inside a for-loop stays "
                  "ONE shared parameter across every iteration (TOPAS's own 'same name = same value' rule "
                  "applies regardless of the for-loop), so named entries are never multiplied; an ANONYMOUS "
                  "'@' parameter genuinely gets a fresh instance each iteration, so those ARE multiplied. "
                  "One remaining conservative choice: a bare (no-range) 'for strs { ... }' nested inside "
                  "another for-loop is left unmultiplied (counted once) rather than guess at its real scope "
                  "(every str in the whole file, again, per outer iteration? or just the current xdd's own "
                  "strs?) -- see find_for_loop_multipliers()'s own docstring in check_inp_syntax.py for both "
                  "of these points in full.")

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
