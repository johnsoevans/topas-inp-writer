#!/usr/bin/env python3
"""
symmetrize_selection.py -- Given an .inp file and a highlighted line range
(the site lines a user selected in an editor), find the containing str
block's space_group, resolve its symmetry operators, and classify what the
cell parameters (a/b/c/al/be/ga) and the selected sites' coordinates
(x/y/z, u11..u23) are ALLOWED to be under that symmetry: free (allowed to
refine independently), fixed (pinned to an exact constant), or tied
(locked to another parameter via Get()). Every parameter is then
UNCONDITIONALLY normalized to its canonical written form -- regardless of
current refinement status, i.e. never just "when something could drift" --
with a precise replacement snippet ((line, start-column, end-column) span)
so a caller can build an editor edit directly:
  - FREE: given a parameter name if it doesn't already have one, and the
    current mode's sigil -- '!name' (fixed, the default) or bare 'name'
    with no sigil (--refineall). Only a free parameter is ever named: a
    parameter name should exist if and only if symmetry allows that value
    to actually vary.
  - FIXED (a special position -- nothing to refine): always rewritten to
    a bare, unnamed value with no sigil at all.
  - TIED (locked to another coordinate/length/ADP component): always
    rewritten to its canonical 'x = Get(y);' equation form.

Built for programmatic reuse (e.g. a VS Code/topas-editor extension calling
this as a child process) -- NOT a chat-facing tool. Every classification and
every proposed fix is produced by deterministic Python arithmetic (integer/
Fraction symmetry-operator algebra in symmetry_utils.py); there is no LLM
involved in generating any of it, and none is needed to reuse it.

This is a sibling to check_inp_syntax.py's check_symmetry_constraints
(same file, same function) -- it reuses the EXACT same underlying engine
(symmetry_utils.classify_coordinates/classify_adps/classify_crystal_system,
check_inp_syntax.resolve_site_coordinates/resolve_str_scope_values/
extract_keyword_form/GET_TIE_RE) for CLASSIFYING what symmetry allows. The
two tools differ only in what they do with that classification: that
function flags a real drift RISK (something currently refined that could
numerically diverge from its required constraint) as an English warning
string; this tool always normalizes to the canonical form outright and
emits a structured verdict (+ a ready-to-apply text replacement) instead.

Usage:
    python3 symmetrize_selection.py file.inp --lines 25-26
    python3 symmetrize_selection.py file.inp --lines 25-26 --json
    python3 symmetrize_selection.py file.inp --lines 25 -o report.json --json
    python3 symmetrize_selection.py file.inp --lines 25-26 --write
        (applies every 'fix' item directly, writing file_symmetrized.inp
        alongside file.inp -- CLI convenience only, see apply_fixes/--write)
    python3 symmetrize_selection.py file.inp --write
        (--lines omitted defaults to the whole file -- only valid when the
        file contains a single str block; multi-phase files must pass an
        explicit --lines range)
    python3 symmetrize_selection.py file.inp --lines 25-26 --refineall --write
        (every FREE cell parameter/coordinate/ADP in range gets named with
        NO sigil -- i.e. left free to actually refine -- instead of the
        default '!name'; see --refineall below)

Requires TOPAS_DIR (see topas_install.py) -- space-group operators are
resolved via TOPAS's own sgcom6.exe/sg database, the only source available
for an .inp file (which never carries its own operator loop the way a CIF
can). Without it, this tool reports an error rather than guessing.

Scope, deliberately conservative (mirrors check_symmetry_constraints):
  - Only the str block(s) whose extent overlaps the given line range are
    analyzed. Cell parameters are always included for that one block (the
    surrounding context symmetry-checking a site needs anyway); sites are
    included only if their own declaration line falls inside the range.
  - This tool only ever proposes REPLACING an existing span of text on a
    single physical line -- it never inserts a new line or deletes one.
    A parameter that's completely ABSENT from the file (a free parameter
    with no line to name, a missing 'ga' under a hexagonal/trigonal
    group, a missing 'b'/'c' tie, ...) is reported as 'skip' with an
    explanation instead of a fabricated edit. See free_param_sigil_fix's
    own docstring for the free-parameter naming schemes (lp_a/.../lp_ga
    for cell parameters, '{coord}{site}' e.g. 'xti1'/'u11o1' for sites).
  - A site/cell keyword whose value or equation doesn't fit entirely on
    one physical line, or whose form this engine can't resolve to a
    concrete number (an equation referencing something other than a
    simple Get() tie or plain constant), is reported as 'skip', never
    guessed at.
  - A lattice-macro (Cubic/Tetragonal/Hexagonal/Trigonal/Rhombohedral)
    mismatch against the space group's real crystal system is reported
    as 'skip' (swapping macros is a structural rewrite, not a value fix).
"""

import sys
import os
import re
import json
import argparse
from fractions import Fraction

import check_inp_syntax as cis
import symmetry_utils


def line_offsets(text):
    """offsets[i] = absolute character offset (into `text`) where physical
    line i+1 (1-indexed) begins. Built once per file and reused for every
    line/column lookup, so every position this tool reports is computed
    against the exact same coordinate system."""
    offsets = []
    acc = 0
    for line in text.splitlines(keepends=True):
        offsets.append(acc)
        acc += len(line)
    offsets.append(acc)  # sentinel, so line N's end is offsets[N] for the last real line too
    return offsets


def offset_range_for_lines(offsets, line_start, line_end):
    """Absolute [start, end) char offset spanning physical lines
    line_start..line_end inclusive (1-indexed)."""
    start = offsets[line_start - 1]
    end = offsets[min(line_end, len(offsets) - 1)]
    return start, end


def line_text_at(text, offsets, line_no):
    """The visible text of physical line `line_no` (1-indexed), with any
    trailing \\r/\\n stripped -- for local keyword-span searches, not for
    offset math (which always uses `offsets`, computed from the untouched
    original text)."""
    start = offsets[line_no - 1]
    end = offsets[line_no] if line_no < len(offsets) else len(text)
    return text[start:end].rstrip("\r\n")


def locate_keyword_span(line, keyword):
    """
    Find `keyword`'s full statement span on a SINGLE physical line: either
    'keyword = expr;' (equation) or 'keyword [sigil][name] number[`_error]'
    (value). Returns (kind, start_col, end_col) -- a half-open character
    range within `line` covering the ENTIRE replaceable statement (keyword
    through its value/terminating ';') -- or None if `keyword` isn't found
    on this line, or its form doesn't fit either of these two simple
    shapes (e.g. the equation's ';' isn't on this same line).

    Deliberately a line-scoped sibling of check_inp_syntax.extract_keyword_
    form (same TOPAS grammar, same token-walk, reuses its own compiled
    E_ARG_NUMBER_TOKEN_RE for the number-matching itself) rather than a
    rewritten variant of it -- kept separate because extract_keyword_form's
    existing return shape (a parsed value, not a replaceable span) is
    relied on by many other callers already; this one exists purely to
    answer "what text, exactly, would a caller overwrite."
    """
    m = re.search(r"\b" + re.escape(keyword) + r"\b", line)
    if not m:
        return None
    pos = m.end()
    n = len(line)
    while pos < n and line[pos] in " \t":
        pos += 1
    if pos < n and line[pos] == "=":
        end = line.find(";", pos)
        if end == -1:
            return None
        return ("equation", m.start(), end + 1)

    tok_m = re.match(r"(?:[!@]?[A-Za-z_]\w*|[!@])", line[pos:])
    val_start = pos
    if tok_m and tok_m.group(0):
        k = pos + tok_m.end()
        while k < n and line[k] in " \t":
            k += 1
        probe = cis.E_ARG_NUMBER_TOKEN_RE.match(line[k:])
        if probe and probe.group(0):
            val_start = k
    val_m = cis.E_ARG_NUMBER_TOKEN_RE.match(line[val_start:])
    if not val_m or not val_m.group(0):
        return None
    return ("value", m.start(), val_start + val_m.end())


def format_fixed_value(value):
    """A 'fixed' constraint's required constant, formatted the way this
    skill's own corpus writes a fixed coordinate: an exact 'N/D' fraction
    equation when the value snaps to a NON-integer fraction (matching
    check_xyz_near_one_third's own guidance against writing a rounded
    decimal like 0.333333), otherwise a plain decimal -- including the
    common case of an exact 0 or other whole number, where 'N/1' would be
    needlessly ugly compared to just writing the bare integer. Returns
    (is_equation, text)."""
    snapped, exact = symmetry_utils.snap_to_fraction(value)
    if exact is not None and exact.denominator != 1:
        return True, f"{exact.numerator}/{exact.denominator}"
    return False, f"{snapped:.6g}"


def format_tie_expr(other, sign, offset):
    """Same formatting check_symmetry_constraints itself uses for a
    coordinate tie's RHS -- e.g. 'Get(x)', '-Get(x)', 'Get(x) + 1/3'."""
    sign_str = "" if sign == 1 else "-"
    expr = f"{sign_str}Get({other})"
    offset_mod1 = offset % 1.0
    if offset_mod1 > 1e-6:
        off_snapped, off_exact = symmetry_utils.snap_to_fraction(offset_mod1)
        off_disp = f"{off_exact.numerator}/{off_exact.denominator}" if off_exact else f"{off_snapped:.6g}"
        expr += f" + {off_disp}" if offset >= 0 else f" - {off_disp}"
    return expr


CELL_PARAM_NAMES = {"a": "lp_a", "b": "lp_b", "c": "lp_c", "al": "lp_al", "be": "lp_be", "ga": "lp_ga"}


def auto_name_for(scope, keyword, site):
    """The name a free (unconstrained-by-symmetry) parameter gets when it
    doesn't already have one -- 'coord' + lowercased site name for a site
    coordinate/ADP (e.g. 'xti1', 'u11o1'), or the fixed lp_a/lp_b/.../lp_ga
    scheme for a cell parameter -- both schemes given directly by the user
    rather than derived. Cell names are fixed regardless of str block
    since there's only ever one a/b/c/al/be/ga per str, no site to
    disambiguate against the way there is for a site keyword."""
    if scope == "cell":
        return CELL_PARAM_NAMES[keyword]
    return f"{keyword}{site.lower()}"


def free_param_sigil_fix(scope, keyword, site, form, refineall, text, offsets, content_start, site_pos):
    """
    For a FREE (unconstrained-by-symmetry) cell parameter or site
    coordinate/ADP, ensure it carries a parameter name and the sigil this
    tool's current mode calls for: '!name' (fixed, the default) or 'name'
    with no sigil at all (--refineall) -- never '@', since the point here
    is giving every symmetry-allowed-to-refine parameter an explicit,
    inspectable name up front, not auto-refining it outright.

    Returns a 'fix' item if a rewrite is needed, or None if nothing needs
    to change -- callers append the 'ok'/'free' item themselves in that
    case. Two cases are left alone (None), both matching this tool's
    "never insert a new line" policy (module docstring):
      - form is None: the parameter is entirely ABSENT from the file --
        adding one would be a structural insertion, not a value fix.
      - An equation-form free value (e.g. 'x = 1/4;'): TOPAS's own naming-
        of-equations rule (Technical_Reference.pdf section 2.9) already
        determines refined-vs-dependent from whether the equation reduces
        to a constant, and neither '!' nor a name attaches to an
        equation's LHS the way it does to a bare value -- adding a sigil
        here would mean rewriting the equation into a different kind of
        statement, which this tool does not attempt.
    """
    if form is None or form[0] != "value":
        return None

    sigil, value, name = form[1], form[2], form[3]
    wanted_sigil = "" if refineall else "!"
    if sigil == wanted_sigil and name is not None:
        return None  # already has a name and the mode's own sigil -- nothing to do

    new_name = name if name is not None else auto_name_for(scope, keyword, site)
    val_text = f"{value:g}"
    new_text = f"{keyword} {wanted_sigil}{new_name} {val_text}" if wanted_sigil else f"{keyword} {new_name} {val_text}"

    abs_pos = content_start + site_pos + form[-1]
    resolved = resolve_and_span(text, offsets, abs_pos, keyword)
    mode_desc = "left fixed with '!' (default; pass --refineall to refine instead)" if refineall is False else \
                "left free to refine (--refineall), no '!'"
    if name is None:
        reason = (f"free -- allowed to refine by this space group's own symmetry, but had no "
                  f"parameter name -- named '{new_name}' and {mode_desc}.")
    else:
        reason = (f"free -- allowed to refine by this space group's own symmetry, but its sigil "
                  f"didn't match the requested mode -- {mode_desc}.")
    if resolved is None:
        return make_item("site" if scope == "site" else "cell", keyword, None, "skip",
                          reason + " (couldn't locate a single-line replaceable span)")
    line_no, sc, ec, old_text = resolved
    return make_item("site" if scope == "site" else "cell", keyword, line_no, "fix", reason, old_text, new_text, sc, ec)


def make_item(scope, name, line_no, status, reason, old_text=None, new_text=None,
              start_col=None, end_col=None, site=None):
    item = {
        "scope": scope,       # "cell" | "site"
        "name": name,         # keyword name, e.g. "x", "b", "u12"
        "line": line_no,      # 1-indexed
        "status": status,     # "ok" | "fix" | "skip"
        "reason": reason,
        "old_text": old_text,
        "new_text": new_text,
    }
    if start_col is not None:
        item["start_col"] = start_col  # 0-indexed, inclusive
        item["end_col"] = end_col      # 0-indexed, exclusive
    if site is not None:
        item["site"] = site
    return item


def resolve_and_span(text, offsets, abs_pos, keyword):
    """Given an absolute char offset landing somewhere inside `keyword`'s
    statement (as returned by extract_keyword_form's own m.start(), itself
    relative to whatever slice was searched), find the physical line it's
    on and that keyword's own precise (line, start_col, end_col, old_text)
    span via locate_keyword_span. Returns None if the span can't be
    resolved on that single line."""
    line_no = cis.line_of(text, abs_pos)
    line = line_text_at(text, offsets, line_no)
    span = locate_keyword_span(line, keyword)
    if span is None:
        return None
    _kind, start_col, end_col = span
    return line_no, start_col, end_col, line[start_col:end_col]


def evaluate_coordinate(coord, kind, form, forms, text, offsets, content_start, site_pos, symbol, system,
                         site=None, refineall=False):
    """Mirrors check_symmetry_constraints' coordinate branch (both 'fixed'
    and 'tied') term-for-term, but returns a verdict dict instead of
    appending a warning string. See module docstring for the scope gaps
    deliberately mirrored rather than "improved on" here."""
    if kind[0] == "complex" or form is None:
        return make_item("site", coord, None, "skip",
                          "constraint too complex for this tool's simple per-coordinate model -- verify manually")
    if kind[0] == "free":
        fix = free_param_sigil_fix("site", coord, site, form, refineall, text, offsets, content_start, site_pos)
        if fix is not None:
            return fix
        return make_item("site", coord, None, "ok",
                          "free -- allowed to refine by this space group's own symmetry, already "
                          "named with the requested mode's sigil.")

    abs_pos = content_start + site_pos + form[-1]
    resolved = resolve_and_span(text, offsets, abs_pos, coord)

    if kind[0] == "fixed":
        value = kind[1]
        if form[0] == "value":
            if form[1] == "" and form[3] is None:
                return make_item("site", coord, None, "ok",
                                  "already a bare, unnamed fixed value -- tautologically consistent "
                                  "with the resolved special-position value, since that value is "
                                  "derived from this same number.")
            # A name and/or '!'/'@' sigil is present on a coordinate site
            # symmetry fixes at an exact constant -- always stripped to a
            # bare value: a special-position coordinate has nothing to
            # refine, so it should carry no parameter name at all.
            is_eq, val_text = format_fixed_value(value)
            new_text = f"{coord} = {val_text};" if is_eq else f"{coord} {val_text}"
            if form[1] == "@":
                reason = (f"'@'-refined independently, but site symmetry under space_group {symbol!r} "
                          f"fixes it at an exact value ({value:.6g}) -- refining it risks drifting off "
                          f"the special position, so its name and sigil are removed entirely.")
            else:
                reason = (f"named {form[3]!r}, but site symmetry under space_group {symbol!r} fixes "
                          f"it at an exact value ({value:.6g}) with nothing to refine -- a fixed "
                          f"special-position coordinate should carry no parameter name at all, so "
                          f"its name{'/' + form[1] if form[1] else ''} is removed.")
            if resolved is None:
                return make_item("site", coord, None, "skip",
                                  reason + " (couldn't locate a single-line replaceable span)")
            line_no, sc, ec, old_text = resolved
            return make_item("site", coord, line_no, "fix", reason, old_text, new_text, sc, ec)
        # Equation form under a 'fixed' requirement: check_symmetry_constraints
        # itself has no branch for this case (a known, deliberately mirrored
        # gap -- see module docstring) -- report skip rather than inventing
        # a check the sibling tool doesn't perform either.
        return make_item("site", coord, None, "skip",
                          "written as an equation; this tool (matching check_inp_syntax.py's own "
                          "scope) doesn't validate an equation-form coordinate against a 'fixed' "
                          "requirement -- verify manually.")

    # kind[0] == "tied"
    _, other, sign, offset = kind
    expr = format_tie_expr(other, sign, offset)
    required_new_text = f"{coord} = {expr};"

    matches = False
    if form[0] == "equation":
        tie_m = cis.GET_TIE_RE.match(form[1])
        if tie_m and not tie_m.group("mul_x") and not tie_m.group("mul_j"):
            ref_other = tie_m.group("name")
            ref_sign = -1 if tie_m.group("neg") else 1
            ref_offset = float(Fraction(tie_m.group("off_val"))) if tie_m.group("off_sign") else 0.0
            if tie_m.group("off_sign") == "-":
                ref_offset = -ref_offset
            matches = (ref_other == other and ref_sign == sign and abs(ref_offset - offset) < 0.0015)
    if matches:
        return make_item("site", coord, None, "ok", f"already correctly tied ('{coord} = {expr};')")

    other_form = forms.get(other)

    if form[0] == "equation" and cis.parse_plain_numeric_equation(form[1]) is not None:
        return make_item("site", coord, None, "ok",
                          "written as an independent plain-constant equation -- numerically "
                          "consistent with the required tie by construction (it can never drift, "
                          "since it's recomputed identically every iteration).")

    this_name = form[3] if form[0] == "value" else None
    other_name = other_form[3] if other_form is not None and other_form[0] == "value" else None
    if (this_name is not None and this_name == other_name) or \
       (form[0] == "equation" and other_name is not None and form[1].strip() == other_name):
        return make_item("site", coord, None, "ok",
                          "shares a parameter name with the tied coordinate -- TOPAS enforces "
                          "identical values for same-named parameters, so this can never drift.")

    reason_needs_fix = (f"site symmetry under space_group {symbol!r} requires "
                        f"'{coord} = {expr};'")

    if form[0] == "value":
        reason = (f"written as an independent value, but {reason_needs_fix} -- a tied coordinate "
                  f"should always be expressed as its Get() equation, not an independent value that "
                  f"only happens to numerically agree.")
    else:
        reason = f"written as a different/mismatched equation, but {reason_needs_fix}."

    if resolved is None:
        return make_item("site", coord, None, "skip", reason + " (couldn't locate a single-line replaceable span)")
    line_no, sc, ec, old_text = resolved
    return make_item("site", coord, line_no, "fix", reason, old_text, required_new_text, sc, ec)


def evaluate_adp(adp_name, kind, form, known_adp, text, offsets, content_start, site_pos, symbol,
                  site=None, refineall=False):
    """Mirrors check_symmetry_constraints' ADP branch term-for-term."""
    if form is None:
        return make_item("site", adp_name, None, "ok", "not written on this site.")
    if kind[0] == "free":
        fix = free_param_sigil_fix("site", adp_name, site, form, refineall, text, offsets, content_start, site_pos)
        if fix is not None:
            return fix
        return make_item("site", adp_name, None, "ok",
                          "free -- not constrained by this site's symmetry, already named with the "
                          "requested mode's sigil.")

    abs_pos = content_start + site_pos + form[-1]
    resolved = resolve_and_span(text, offsets, abs_pos, adp_name)

    if kind[0] == "fixed":
        if form[0] == "value":
            if form[1] == "" and form[3] is None and abs(form[2]) <= 1e-6:
                return make_item("site", adp_name, None, "ok",
                                  "already a bare, unnamed value fixed at (approximately) 0.")
            new_text = f"{adp_name} 0"
            if form[1] == "@":
                reason = (f"'@'-refined independently, but site symmetry under space_group {symbol!r} "
                          f"fixes it at exactly 0 -- refining it risks a nonzero, symmetry-violating "
                          f"value, so its name and sigil are removed entirely.")
            elif abs(form[2]) > 1e-6:
                reason = (f"'{adp_name} {form[2]:g}' contradicts site symmetry under space_group "
                          f"{symbol!r}, which requires it fixed at exactly 0.")
            else:
                # Correct value (0) but named/'!'-fixed -- stripped anyway,
                # same reasoning as the coordinate 'fixed' branch above.
                reason = (f"named {form[3]!r}, but site symmetry under space_group {symbol!r} fixes "
                          f"it at exactly 0 with nothing to refine -- a fixed ADP component should "
                          f"carry no parameter name at all, so its name{'/' + form[1] if form[1] else ''} "
                          f"is removed.")
            if resolved is None:
                return make_item("site", adp_name, None, "skip", reason + " (couldn't locate a single-line replaceable span)")
            line_no, sc, ec, old_text = resolved
            return make_item("site", adp_name, line_no, "fix", reason, old_text, new_text, sc, ec)
        # equation form under 'fixed' -- mirrors the sibling checker's own
        # "verify manually" treatment (it warns but proposes no fix either).
        plain = cis.parse_plain_numeric_equation(form[1])
        if plain is not None and abs(plain) < 1e-6:
            return make_item("site", adp_name, None, "ok", "equation resolves to (approximately) 0, as required.")
        return make_item("site", adp_name, None, "skip",
                          f"written as an equation; site symmetry under space_group {symbol!r} requires "
                          f"it fixed at exactly 0 -- verify manually.")

    # kind[0] == "tied"
    terms = kind[1]
    required_new_text = f"{adp_name} = {symmetry_utils.format_adp_tie(terms)};"
    if form[0] == "equation":
        parsed = cis.parse_adp_tie_expression(form[1])
        if cis.adp_terms_match(parsed, terms):
            return make_item("site", adp_name, None, "ok", f"already correctly tied ('{required_new_text}').")
        reason = (f"written as a different/unrecognized equation, but site symmetry under "
                  f"space_group {symbol!r} requires '{required_new_text}'.")
        if resolved is None:
            return make_item("site", adp_name, None, "skip", reason + " (couldn't locate a single-line replaceable span)")
        line_no, sc, ec, old_text = resolved
        return make_item("site", adp_name, line_no, "fix", reason, old_text, required_new_text, sc, ec)

    # form[0] == "value" -- always rewritten to the required Get() tie
    # below, same as the coordinate/cell-length 'tied' branches.
    resolvable = all(other in known_adp for _c, other in terms)
    if resolvable:
        required_val = float(sum(c * known_adp[other] for c, other in terms))
        if abs(form[2] - required_val) > max(1e-6, 0.01 * abs(required_val)):
            reason = (f"'{adp_name} {form[2]:g}' doesn't match the site-symmetry-required value "
                      f"({required_val:.6g}, from '{required_new_text}') under space_group {symbol!r}.")
            if resolved is None:
                return make_item("site", adp_name, None, "skip", reason + " (couldn't locate a single-line replaceable span)")
            line_no, sc, ec, old_text = resolved
            return make_item("site", adp_name, line_no, "fix", reason, old_text, required_new_text, sc, ec)
    reason = (f"written as an independent value, but site symmetry under space_group {symbol!r} "
              f"requires it tied to '{required_new_text}' -- a tied ADP component should always be "
              f"expressed as its Get() equation, not an independent value that only happens to "
              f"numerically agree.")
    if resolved is None:
        return make_item("site", adp_name, None, "skip", reason + " (couldn't locate a single-line replaceable span)")
    line_no, sc, ec, old_text = resolved
    return make_item("site", adp_name, line_no, "fix", reason, old_text, required_new_text, sc, ec)


def evaluate_cell(text, offsets, content_start, preamble, symbol, system, refineall=False):
    """Mirrors check_symmetry_constraints' cell-parameter branch (lattice
    macro OR literal a/b/c/al/be/ga) term-for-term. Returns a list of
    items -- always populated for the str block regardless of the
    requested line range, since a site's own symmetry check needs this
    context anyway and the caller explicitly wants cell parameters back."""
    items = []
    macro_m = re.search(r"\b(Cubic|Tetragonal|Hexagonal|Trigonal|Rhombohedral)\s*\(", preamble)
    if macro_m:
        macro_name = macro_m.group(1)
        allowed = cis.LATTICE_MACRO_SYSTEMS[macro_name]
        if system not in allowed:
            items.append(make_item(
                "cell", macro_name, cis.line_of(text, content_start + macro_m.start()), "skip",
                f"'{macro_name}(...)' doesn't implement crystal system {system!r} required by "
                f"space_group {symbol!r} -- swapping lattice macros is a structural change this "
                f"tool won't auto-apply; verify and fix manually."))
        else:
            items.append(make_item(
                "cell", macro_name, cis.line_of(text, content_start + macro_m.start()), "ok",
                f"'{macro_name}(...)' correctly implements crystal system {system!r}."))
        return items

    length_ties = dict(symmetry_utils.LENGTH_TIES_BY_SYSTEM.get(system, {}))
    angle_reqs = dict(symmetry_utils.ANGLE_CONSTRAINTS_BY_SYSTEM.get(system, {}))

    if system == "hexagonal_or_trigonal":
        al_form = cis.extract_keyword_form(preamble, "al")
        be_form = cis.extract_keyword_form(preamble, "be")
        ga_form = cis.extract_keyword_form(preamble, "ga")
        explicit = {}
        for nm, f in (("al", al_form), ("be", be_form), ("ga", ga_form)):
            if f and f[0] == "value":
                explicit[nm] = f[2]
        if len(explicit) == 3:
            is_hex = abs(explicit["al"] - 90) < 0.05 and abs(explicit["be"] - 90) < 0.05 and abs(explicit["ga"] - 120) < 0.05
            is_rhomb = abs(explicit["al"] - explicit["be"]) < 0.05 and abs(explicit["be"] - explicit["ga"]) < 0.05
            if not is_hex and is_rhomb:
                length_ties["c"] = "a"
        if ga_form is None:
            items.append(make_item(
                "cell", "ga", None, "skip",
                f"space_group {symbol!r} resolves to a hexagonal/trigonal crystal system, which "
                f"requires 'ga' fixed at 120 degrees -- but 'ga' is absent from this str block, so "
                f"TOPAS will silently default it to 90. This tool doesn't insert new lines; add "
                f"'ga 120' manually (or use Hexagonal()/Trigonal()/Rhombohedral())."))

    for coord3 in ("a", "b", "c"):
        if coord3 in length_ties:
            continue
        form = cis.extract_keyword_form(preamble, coord3)
        if form is None:
            items.append(make_item("cell", coord3, None, "ok", "not written in this str block."))
            continue
        fix = free_param_sigil_fix("cell", coord3, None, form, refineall, text, offsets, content_start, 0)
        if fix is not None:
            items.append(fix)
            continue
        items.append(make_item("cell", coord3, cis.line_of(text, content_start + form[-1]), "ok",
                                "independent -- not tied by this crystal system, already named with "
                                "the requested mode's sigil."))

    for dep, indep in length_ties.items():
        form = cis.extract_keyword_form(preamble, dep)
        if form is None:
            items.append(make_item(
                "cell", dep, None, "skip",
                f"'{dep}' is required to equal '{indep}' for space_group {symbol!r} (crystal system "
                f"{system!r}), but is absent from this str block. This tool doesn't insert new "
                f"lines; add '{dep} = Get({indep});' manually."))
            continue
        tie_m = cis.GET_TIE_RE.match(form[1]) if form[0] == "equation" else None
        ok = (bool(tie_m) and not tie_m.group("neg") and not tie_m.group("mul_x")
              and not tie_m.group("mul_j") and not tie_m.group("off_sign") and tie_m.group("name") == indep)
        line_no = cis.line_of(text, content_start + form[-1])
        if ok:
            items.append(make_item("cell", dep, line_no, "ok", f"already correctly tied ('{dep} = Get({indep});')."))
            continue
        required_new_text = f"{dep} = Get({indep});"
        # Same "always tied" reasoning as the coordinate/ADP 'tied' branches.
        if form[0] == "value":
            reason = (f"'{dep}' is required to equal '{indep}' for space_group {symbol!r} (crystal "
                      f"system {system!r}), but is written as an independent value -- a tied lattice "
                      f"length should always be expressed as its Get() equation.")
        else:
            reason = (f"'{dep}' is required to equal '{indep}' for crystal system {system!r}, but is "
                      f"written as {form[0]} rather than '{dep} = Get({indep});'.")
        resolved = resolve_and_span(text, offsets, content_start + form[-1], dep)
        if resolved is None:
            items.append(make_item("cell", dep, line_no, "skip", reason + " (couldn't locate a single-line replaceable span)"))
            continue
        rline, sc, ec, old_text = resolved
        items.append(make_item("cell", dep, rline, "fix", reason, old_text, required_new_text, sc, ec))

    for name in ("al", "be", "ga"):
        expected = angle_reqs.get(name)
        form = cis.extract_keyword_form(preamble, name)
        if expected is None:
            if form is None:
                items.append(make_item("cell", name, None, "ok",
                                        "not written in this str block (defaults apply)."))
                continue
            fix = free_param_sigil_fix("cell", name, None, form, refineall, text, offsets, content_start, 0)
            if fix is not None:
                items.append(fix)
                continue
            items.append(make_item("cell", name, cis.line_of(text, content_start + form[-1]), "ok",
                                    "free -- not constrained by this crystal system, already named "
                                    "with the requested mode's sigil."))
            continue
        if expected != 90:
            # ga's 120-degree case: only the "completely absent" state is
            # validated above (mirroring check_symmetry_constraints' own
            # scope gap -- a PRESENT-but-wrong 120 value is not currently
            # checked by that function either, so this tool doesn't
            # fabricate a check for it here).
            if form is not None:
                items.append(make_item("cell", name, cis.line_of(text, content_start + form[-1]), "skip",
                                        f"present; this tool (matching check_inp_syntax.py's own scope) "
                                        f"doesn't currently validate a present-but-possibly-wrong "
                                        f"{expected}-degree angle value -- verify manually."))
            continue
        if form is None:
            items.append(make_item("cell", name, None, "ok",
                                    f"absent -- TOPAS defaults it to {expected} degrees, which is correct here."))
            continue
        line_no = cis.line_of(text, content_start + form[-1])
        if form[0] == "value" and abs(form[2] - expected) > 0.05:
            reason = (f"'{name} {form[2]:g}' contradicts space_group {symbol!r} (crystal system "
                      f"{system!r}), which requires it fixed at {expected} degrees.")
            resolved = resolve_and_span(text, offsets, content_start + form[-1], name)
            new_text = f"{name} {expected}"
            if resolved is None:
                items.append(make_item("cell", name, line_no, "skip", reason + " (couldn't locate a single-line replaceable span)"))
                continue
            rline, sc, ec, old_text = resolved
            items.append(make_item("cell", name, rline, "fix", reason, old_text, new_text, sc, ec))
        else:
            items.append(make_item("cell", name, line_no, "ok", f"correctly fixed at {expected} degrees."))

    return items


_SG_OPERATOR_CACHE = {}


def analyze_selection(path, line_start, line_end, refineall=False):
    """Core entry point. Returns a result dict -- see module docstring and
    make_item for the "items" shape. On any failure to even begin analysis
    (no str block covers the selection, no space_group found, symmetry
    operators unresolvable -- e.g. TOPAS_DIR unset), returns
    {"error": "..."} instead of a partial/misleading result.

    `refineall`: for every FREE (symmetry-unconstrained) cell parameter or
    site coordinate/ADP, controls the sigil this tool ensures it carries --
    '!name' (fixed, the default, refineall=False) or bare 'name' with no
    sigil at all (refineall=True) -- see free_param_sigil_fix's own
    docstring. Constrained (fixed/tied) parameters are unaffected either
    way; this flag only changes the free-parameter behavior."""
    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    offsets = line_offsets(text)
    n_lines = len(offsets) - 1
    if line_start < 1 or line_end < line_start or line_start > n_lines:
        return {"error": f"--lines {line_start}-{line_end} is out of range for a {n_lines}-line file."}
    sel_start, sel_end = offset_range_for_lines(offsets, line_start, line_end)

    clean = cis.strip_opaque_blocks(cis.strip_inactive_ifdef_branches(cis.strip_comments_and_strings(text)))
    text_with_values = cis.strip_opaque_blocks(cis.strip_inactive_ifdef_branches(cis.strip_comments_only(text)))

    str_blocks = cis.find_str_blocks(clean)
    containing = [b for b in str_blocks if not (b[1] <= sel_start or b[0] >= sel_end)]
    if len(containing) == 0:
        return {"error": f"Lines {line_start}-{line_end} don't fall inside any str block."}
    if len(containing) > 1:
        return {"error": f"Lines {line_start}-{line_end} span more than one str block ({len(containing)}) -- "
                          f"select lines within a single phase's str block."}
    content_start, content_end = containing[0]
    block_clean = clean[content_start:content_end]
    block_values = text_with_values[content_start:content_end]

    sg_m = re.search(r"\bspace_group\b\s*(\"[^\"]*\"|\S+)", block_values)
    if not sg_m or not sg_m.group(1).strip('"'):
        return {"error": "No space_group found in the containing str block."}
    symbol = sg_m.group(1).strip('"')

    if symbol not in _SG_OPERATOR_CACHE:
        symops, _header, msg = symmetry_utils.resolve_sg_operators(symbol)
        _SG_OPERATOR_CACHE[symbol] = (symops, msg)
    symops, resolve_msg = _SG_OPERATOR_CACHE[symbol]
    if not symops:
        return {"error": f"Could not resolve symmetry operators for space_group {symbol!r}: {resolve_msg}"}

    system = symmetry_utils.classify_crystal_system(symops)

    first_site_m = re.search(r"\bsite\b", block_clean)
    preamble_end = first_site_m.start() if first_site_m else len(block_clean)
    preamble = block_clean[:preamble_end]
    str_scope = cis.resolve_str_scope_values(preamble)

    str_line_start = cis.line_of(text, content_start)
    str_line_end = cis.line_of(text, content_end)

    items = evaluate_cell(text, offsets, content_start, preamble, symbol, system, refineall=refineall)

    sites_seen = []
    for name, site_slice, site_pos in cis.find_sites(block_clean):
        site_abs_pos = content_start + site_pos
        site_line = cis.line_of(text, site_abs_pos)
        if site_line < line_start or site_line > line_end:
            continue
        sites_seen.append(name)

        point, forms = cis.resolve_site_coordinates(site_slice, outer_known=str_scope)
        if point is None:
            items.append(make_item("site", None, site_line, "skip",
                                    "couldn't resolve x/y/z to concrete numbers (an equation "
                                    "references something other than a simple Get() tie or a plain "
                                    "constant) -- verify manually.", site=name))
            continue

        stabilizer = symmetry_utils.find_stabilizer(point, symops, 0.0015)
        constraint = symmetry_utils.classify_coordinates(point, stabilizer)
        for coord in ("x", "y", "z"):
            item = evaluate_coordinate(coord, constraint[coord], forms[coord], forms,
                                        text, offsets, content_start, site_pos, symbol, system,
                                        site=name, refineall=refineall)
            item["site"] = name
            if item["line"] is None:
                item["line"] = site_line
            items.append(item)

        adp_forms = {nm: cis.extract_keyword_form(site_slice, nm) for nm in symmetry_utils.ADP_NAMES}
        if any(f is not None for f in adp_forms.values()):
            adp_constraint = symmetry_utils.classify_adps(stabilizer)
            known_adp = {nm: f[2] for nm, f in adp_forms.items() if f and f[0] == "value"}
            for adp_name in symmetry_utils.ADP_NAMES:
                form = adp_forms[adp_name]
                if form is None:
                    continue
                item = evaluate_adp(adp_name, adp_constraint[adp_name], form, known_adp,
                                     text, offsets, content_start, site_pos, symbol,
                                     site=name, refineall=refineall)
                item["site"] = name
                if item["line"] is None:
                    item["line"] = site_line
                items.append(item)

    summary = {"ok": 0, "fix": 0, "skip": 0}
    for it in items:
        summary[it["status"]] += 1

    return {
        "file": path,
        "requested_lines": [line_start, line_end],
        "str_block_lines": [str_line_start, str_line_end],
        "space_group": symbol,
        "crystal_system": system,
        "sites_in_range": sites_seen,
        "items": items,
        "summary": summary,
    }


def format_text(result):
    if "error" in result:
        return f"ERROR: {result['error']}"
    lines = []
    lines.append(f"{result['file']}  (str block: lines {result['str_block_lines'][0]}-{result['str_block_lines'][1]})")
    lines.append(f"space_group {result['space_group']!r}  -> crystal system '{result['crystal_system']}'")
    lines.append(f"requested selection: lines {result['requested_lines'][0]}-{result['requested_lines'][1]}"
                 f"  (sites in range: {', '.join(result['sites_in_range']) or '(none)'})")
    lines.append("")
    for it in result["items"]:
        tag = {"ok": "OK  ", "fix": "FIX ", "skip": "SKIP"}[it["status"]]
        where = f"line {it['line']}" if it["line"] else "(no line)"
        label = f"{it['scope']}"
        if it.get("site"):
            label += f" '{it['site']}'"
        label += f".{it['name']}" if it["name"] else ""
        lines.append(f"[{tag}] {label}  ({where})")
        lines.append(f"        {it['reason']}")
        if it["status"] == "fix":
            lines.append(f"        - {it['old_text']!r}")
            lines.append(f"        + {it['new_text']!r}")
    lines.append("")
    s = result["summary"]
    lines.append(f"{s['ok']} ok, {s['fix']} fix, {s['skip']} skip.")
    return "\n".join(lines)


def apply_fixes(path, items):
    """Apply every 'fix' item's (line, start_col, end_col) -> new_text
    replacement directly to the file's text and return the new content.
    Applied in reverse line/column order so earlier spans' offsets aren't
    invalidated by later edits on the same line."""
    with open(path, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    fixes = [it for it in items if it["status"] == "fix"]
    fixes.sort(key=lambda it: (it["line"], it["start_col"]), reverse=True)

    for it in fixes:
        idx = it["line"] - 1
        line = lines[idx]
        ending = ""
        stripped = line
        if stripped.endswith("\r\n"):
            ending, stripped = "\r\n", stripped[:-2]
        elif stripped.endswith("\n"):
            ending, stripped = "\n", stripped[:-1]
        lines[idx] = stripped[:it["start_col"]] + it["new_text"] + stripped[it["end_col"]:] + ending

    return "".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inp_file")
    parser.add_argument("--lines",
                         help="1-indexed inclusive line range, e.g. '25-26' (or a single line: '25'). "
                              "Defaults to the whole file, which only works when the file contains a "
                              "single str block (multi-phase files must specify an explicit range).")
    parser.add_argument("--json", action="store_true", help="emit structured JSON instead of the text report")
    parser.add_argument("-o", "--output", help="write to this file instead of stdout")
    parser.add_argument("--write", action="store_true",
                         help="also apply every 'fix' item directly to a new file named "
                              "'{base}_symmetrized.inp' alongside inp_file (CLI convenience only -- "
                              "the programmatic analyze_selection()/items API is unaffected).")
    parser.add_argument("--refineall", action="store_true",
                         help="every FREE (symmetry-allowed-to-refine) cell parameter or site "
                              "coordinate/ADP is named and left with NO sigil (actually refining) "
                              "instead of the default '!name' (named but fixed). Constrained "
                              "(fixed/tied) parameters are unaffected either way.")
    args = parser.parse_args()

    if args.lines is None:
        with open(args.inp_file, encoding="utf-8", errors="ignore") as f:
            n_lines = f.read().count("\n") + 1
        line_start, line_end = 1, n_lines
    else:
        m = re.match(r"^(\d+)(?:-(\d+))?$", args.lines.strip())
        if not m:
            print(f"--lines must be START or START-END (e.g. '25' or '25-26'), got {args.lines!r}", file=sys.stderr)
            sys.exit(1)
        line_start = int(m.group(1))
        line_end = int(m.group(2)) if m.group(2) else line_start

    result = analyze_selection(args.inp_file, line_start, line_end, refineall=args.refineall)

    out_text = json.dumps(result, indent=2) if args.json else format_text(result)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out_text + "\n")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(out_text)

    if args.write and "error" not in result:
        n_fixes = result["summary"]["fix"]
        base, ext = os.path.splitext(args.inp_file)
        target = f"{base}_symmetrized{ext}"
        new_content = apply_fixes(args.inp_file, result["items"])
        with open(target, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Applied {n_fixes} fix(es) -> {target}", file=sys.stderr)

    sys.exit(1 if "error" in result else 0)


if __name__ == "__main__":
    main()
