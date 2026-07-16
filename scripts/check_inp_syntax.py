#!/usr/bin/env python3
"""
check_inp_syntax.py -- A basic, heuristic syntax checker for TOPAS .inp files.

Catches eleven classes of mistake before you hand a file to TOPAS:

  1. Unbalanced braces { } or parentheses ( )
  2. Equations ("= ... ;") that never reach a terminating semicolon before
     the enclosing scope changes or the file ends
  3. Identifiers that don't exactly match a real TOPAS keyword or macro
     name but closely resemble one (a likely typo, or a case mistake --
     TOPAS names are case sensitive, so matching here is exact-case).
     Known names are harvested from bracket-notation keywords across
     every reference chapter, every macro definition (both
     'macro Name(args) {}' and bodiless 'macro Name {}' forms) in the
     bundled .inc library plus the file itself, and a small hand-verified
     supplemental list for real names that fall through both harvests.
  4. Macro calls whose argument count doesn't match any known definition
     of that macro (same harvested arities as above)
  5. A space_group value that looks like it was split by a stray space
     into two whitespace-delimited tokens (e.g. "P_31_ 2_1" instead of
     "P_31_2_1") -- space_group takes exactly one bare token or one quoted
     string, so a second, unrecognized fragment right after it is almost
     always this bug, not a new statement. See check_space_group_symbol()'s
     own docstring for the full reasoning and why it's scoped to just this
     one keyword.
  6. A value-report ':' dropped after a ';' (e.g. "prm bb = cs1 + cs2;
     1088.36411`_7.84708627" instead of "...cs2; : 1088.36411..."), leaving
     the value as a bare, unparseable orphaned number.
  7. A refined prm/local (name has no leading '!') given a bare starting
     value but no 'min'/'max' attribute -- unlike subject-specific
     keywords (beq, CS_L, lattice parameters, ...), prm/local carry no
     default min/max limits (references/01-syntax-and-parameters.md,
     "Try and use parameter attributes"), so an unbounded refined
     parameter is a real best-practice mistake, not just a style nit. See
     check_prm_local_missing_min_max()'s own docstring for exact scoping.
  8. A stray extra bare number sitting right after a keyword that takes
     exactly one numeric (E-type) value -- e.g. "scale @ 0.00145344688 907"
     instead of "scale @ 0.00145344688" -- where '907' is left over from a
     bad edit, unparseable as anything else. See
     check_single_e_arg_keywords()'s own docstring for exact scoping and
     the corpus verification behind it.
  9. A bare x/y/z site-coordinate value suspiciously close to 1/3 or 2/3
     (e.g. "x 0.333") -- often a CIF-import artifact where a symmetry-fixed
     special-position coordinate got pasted in as a rounded decimal instead
     of the exact equation form ("x = 1/3;"). See
     check_xyz_near_one_third()'s own docstring for exact scoping, the
     tolerance used, and the corpus verification behind it (very noisy on
     large synthetic/simulated multi-atom cells -- read that docstring
     before trusting a large hit count on that class of file).
  10. A UTF-8 byte-order-mark (BOM) at the very start of the file -- TOPAS
      reads it as part of the first token, breaking the file's first
      keyword and producing "unknown or misplaced keyword" at LINE 1, even
      though the file looks completely normal in most text editors (the
      BOM renders as invisible). See check_bom()'s own docstring.
  11. A site coordinate, ADP tensor component (u11..u23), or lattice
      parameter (a/b/c/al/be/ga) written as an independently refined value
      when the file's own declared space group requires it tied to another
      via a 'Get()' equation (e.g. 'y = Get(x);' on a site sitting on a
      mirror/axis, 'u22 = Get(u11);' for that same site's ADP tensor, or
      'b = Get(a);' for a cubic cell) -- or fixed at an exact constant
      that's instead left '@'-refined. For ADPs specifically, a WRONG bare
      value (not just a refined one) is also flagged -- unlike a
      coordinate's required value, an ADP's required value doesn't come
      from its own written number, so a numeric mismatch is a genuine
      static error, not a tautology. Space-group operators are resolved
      via TOPAS's own sgcom6.exe/sg database (needs TOPAS_DIR; silently
      produces no findings if unavailable, like the macro-arity check's
      live-install fallback). See check_symmetry_constraints()'s own
      docstring for the full method, the built-in lattice-macro
      (Cubic/Tetragonal/Hexagonal/Trigonal/Rhombohedral) recognition, and
      the deliberately conservative scoping for coordinates/lattice
      parameters (only flags a real drift risk -- something actually being
      refined -- not every stylistic omission of a Get() tie).

This is NOT a full TOPAS parser. It does not understand macro expansion
and cannot verify semantics. It is a fast first pass to catch the
mechanical mistakes that produce "Abnormal program termination."
(unbalanced braces/parens, missing ';'), "unknown or misplaced keyword" /
"Cannot locate X in data structures" (typo'd or wrong-case names), and
"Cannot find match for macro X / Number of arguements N" (arity
mismatches) -- see references/console-output-and-errors.md for the real
error text TOPAS produces for each of these. One known blind spot: if a
file-local macro reuses a name already defined with a different arity by
a system #include, TOPAS can fail to resolve the file-local overload at
runtime even though this checker considers the argument count valid (see
the beq-2-create.inp case discussed in SKILL.md) -- a clean pass here
means "matches a documented arity/name," not an ironclad guarantee.

Important caveat on line numbers: TOPAS's own error messages count each
block comment (/* ... */), however many physical lines it spans, as a
SINGLE counted line. This script reports plain physical line numbers
(what you see in a text editor), so if a file has multi-line block
comments before the reported location, TOPAS's own "at LINE N" will be
LOWER than this script's line number by (physical lines in each block
comment above that point - 1). Use this script's line numbers to find
the right neighborhood in your editor, not as an exact match to TOPAS's
own error output.

Usage:
    python3 check_inp_syntax.py file1.inp [file2.inp ...]
    python3 check_inp_syntax.py some_directory/          # recurses for *.inp

Exit code is 0 if no brace/paren/semicolon errors were found in any file
(keyword-typo warnings never affect the exit code, since they are only
suggestions). Exit code is 1 if any file had a hard error.
"""

import sys
import os
import re
import difflib
from fractions import Fraction
import topas_install
import symmetry_utils
from expand_inp_macros import parse_call_args

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KEYWORD_INDEX_PATH = os.path.join(SCRIPT_DIR, "..", "references", "21-keyword-index.md")
REFERENCES_DIR = os.path.join(SCRIPT_DIR, "..", "references")

# Prefer the macro library that ships with the user's OWN current TOPAS
# install (via the TOPAS_DIR environment variable -- see topas_install.py)
# over this skill's bundled snapshot, so arity/keyword checks reflect the
# release actually in use rather than a copy that can go stale. Falls back
# to the bundled copy automatically if TOPAS_DIR isn't set/reachable.
MACRO_LIB_DIR, MACRO_LIB_FROM_LIVE_INSTALL = topas_install.get_inc_dir()

IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
BRACKET_KEYWORD_RE = re.compile(r"\[([A-Za-z_][A-Za-z0-9_]*)")
MACRO_DEF_RE = re.compile(r"macro\s+([A-Za-z_]\w*)\s*\(([^()]*)\)")
BODILESS_MACRO_DEF_RE = re.compile(r"macro\s+([A-Za-z_]\w*)\s*\{")
TABLE_ROW_FUNC_RE = re.compile(r"^\|\s*([A-Za-z_][A-Za-z0-9_]*)\(", re.MULTILINE)

# Keywords/attribute names shorter than this are excluded from the
# typo-detection pass (too many one- and two-letter TOPAS tokens like
# "a", "b", "be", "al" would otherwise swamp the report with noise).
MIN_TYPO_CHECK_LEN = 5

# Keywords load_single_string_arg_keywords() harvests as "takes exactly one
# '$'-sigil argument" purely from their bracket-notation entry, but which
# real usage across the 280+ example corpus proved actually have a second,
# richer grammar the bracket harvest never saw documented anywhere (so
# nothing caught the conflict at harvest time -- see that function's
# docstring on why a *documented* conflict gets excluded automatically;
# this list is for *undocumented* ones, found empirically instead). Populated
# and justified one at a time below; see check_single_string_arg_keywords'
# call site in main() for how this is subtracted from the harvested set.
SINGLE_ARG_FALSE_POSITIVES = {
    "site",
    # site's [site $site] bracket entry documents only its narrow use as a
    # bare site-name reference inside a stacking-faults `layer { }` block
    # (references/10-stacking-faults.md) -- not its everyday form
    # ("site Zr x 0 y 0 z 0 occ Zr+4 1 beq b1 0.5"), which takes many
    # arguments and is only ever described in prose/worked examples, never
    # as its own bracket line. Confirmed by running the un-excluded check
    # against the full example corpus: every real .inp file's ordinary
    # `site` statements produced false positives.
    "hkl_plane",
    # [hkl_plane $hkl]'s single '$hkl' sigil is a conceptual label for "an
    # hkl index", but real usage (test_examples/zro2.inp: "hkl_plane 1 1 1")
    # takes three separate space-separated integers, not one bare token --
    # a genuine mismatch between the manual's simplified bracket notation
    # and the keyword's actual multi-token grammar, found empirically (2
    # false positives across the example corpus) rather than documented
    # anywhere as a conflict the harvester could have caught on its own.
}

# Names defined BY the file itself (macro/prm/local names, refined
# parameter names after @ or !) are never flagged as typos, since they are
# legitimately user-chosen, not meant to match a keyword.
DEFINER_KEYWORDS = {"macro", "prm", "local", "for", "inp_text", "fn"}

# Keywords whose immediately-following '{ ... }' body is free-form
# documentation/display text rather than parsed TOPAS statements (e.g.
# pdf_info prints an interaction-matrix legend using '=' and '-' as
# plain prose characters, not equations). Content inside these blocks is
# blanked out (braces themselves kept, for brace-balance purposes) before
# the semicolon/typo checks run, to avoid false positives on prose.
OPAQUE_BLOCK_KEYWORDS = {"pdf_info"}


# Real low-level reserved keywords confirmed (against the bundled examples
# and manual prose) to be missing from the bracket-formatted harvest of
# 21-keyword-index.md, and NOT coming from a macro definition either (so
# the .inc-library merge in check_file() won't find them) -- add to this
# list if testing turns up more. z_matrix is a hardcoded keyword (see
# references/13-rigid-bodies.md), not something defined via the macro
# system, which is why it needs to be listed explicitly here.
SUPPLEMENTAL_KEYWORDS = {
    "z_matrix",
    # Real keyword, but documented as one of two alternatives inside a
    # single bracket ('[index_th2 !E / index_d !E]'), which the harvest
    # regex (one identifier per bracket) doesn't split out.
    "index_d",
    # Same "alternatives sharing one bracket" gap
    # ('[cross_corr $name #value cross_corr_s !E ...]').
    "cross_corr_s",
    # Documented in 02-equation-operators-and-functions.md's table but
    # missing its own '(x)' in that specific row (the row above it,
    # Erf_Approx(x), has it; this one doesn't), so the table-row-function
    # harvest (which requires a '(' right after the name) misses it.
    "Erfc_Approx",
    # Gauss/Lorentzian are real built-in equation functions (confirmed
    # used in real examples, e.g. 'prm damp = Gauss(0, damp_fwhm);') but
    # are documented as plain prose ('Gauss(xo, fwhm), Lorentzian(xo,
    # fwhm)') in 06-macros-and-include-files.md rather than as a table row
    # or bracket keyword, so neither harvest pass catches them.
    "Gauss",
    "Lorentzian",
    # Used in a real working example (out-1.inp) via Get()/Find_Child()
    # record introspection; not documented in the chapters scanned here.
    "atom_recs",
    # transform_X: the manual's own bracket notation shows lowercase
    # '[transform_x E]', and its surrounding prose inconsistently mixes
    # "transform_x" and "transform_X" in the same paragraph -- but every
    # real bundled example (tpx.inp, xrd-ct-0.inp, 05-reusing-objects...)
    # consistently uses capital-X 'transform_X', matching TOPAS's general
    # convention of capital X for x-axis-related reserved parameters. Real
    # working usage is treated as ground truth over the manual's own
    # inconsistent casing here.
    "transform_X",
    # Real, valid keyword emitted by cif1.exe (TOPAS's bundled CIF-to-str
    # converter -- see SKILL.md "Converting a CIF file to str format") in
    # its str-block output, e.g. "volume 158.3648" alongside a/b/c/al/be/ga.
    # Not in any indexed manual chapter's bracket notation or table-row
    # harvest; confirmed real (not a cif1.exe quirk) by running its raw
    # output through tc.exe directly with zero errors.
    "volume",
}


def load_keyword_set(index_path):
    """
    Harvest known keyword/function names from the reference chapters:
    bracket-notation keywords (e.g. '[translate ...]') appear throughout
    ALL chapters, not just 21-keyword-index.md -- many keywords (like
    rigid-body's point_for_site/translate) are only bracket-documented in
    their own topic chapter's header line and never duplicated into the
    dedicated keyword-index chapter, so scanning only that one file misses
    them. Built-in equation functions (Gauss, Cos, ArcTan2, ...) are
    documented as their own markdown table rows ('| Name(args) | ... |'),
    mostly in 02-equation-operators-and-functions.md but also scattered
    into 06-macros-and-include-files.md -- harvested the same way, from
    every chapter, for the same reason.
    """
    keywords = set(SUPPLEMENTAL_KEYWORDS)
    index_dir = os.path.dirname(index_path) or "."
    try:
        fnames = [f for f in os.listdir(index_dir) if f.lower().endswith(".md")]
    except OSError:
        fnames = []
    if not fnames:
        fnames = [os.path.basename(index_path)]
    for fname in fnames:
        fpath = os.path.join(index_dir, fname)
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        for m in BRACKET_KEYWORD_RE.finditer(text):
            name = m.group(1)
            keywords.add(name)
            # TOPAS documents many keywords with a trailing digit meaning
            # "the first of possibly several numbered instances" (e.g.
            # '[pdf_convolute1 E]', '[scale_phase_X1 E]', '[pdf_zero1 E]')
            # -- bare, unnumbered usage (referring to the first/default
            # instance) is valid and extremely common in real INP files,
            # so register the digit-stripped base form too.
            if name and name[-1].isdigit():
                base = name.rstrip("0123456789")
                if base:
                    keywords.add(base)
        for m in TABLE_ROW_FUNC_RE.finditer(text):
            keywords.add(m.group(1))
    return keywords


# The Technical Reference's own bracket notation (Chapter 2, "Parameters")
# encodes each keyword's argument shape with a leading sigil per argument:
#   $name / $symbol / $file / ...  -- a bare token or one quoted string
#   #value                          -- a plain number
#   E  (often written !E)           -- an equation-or-value parameter slot:
#                                      can be a bare value, @-auto-named,
#                                      !-fixed, explicitly named, or a full
#                                      "= ...;" equation -- confirmed by the
#                                      user (Technical_Reference.pdf Chapter
#                                      2) and consistent with prose seen
#                                      elsewhere in these chapters (e.g.
#                                      "[min !E] ... Attributes are
#                                      equations and cannot have a parameter
#                                      name" in 01-syntax-and-parameters.md).
# BRACKET_FULL_RE below captures a bracket's full interior, not just the
# leading keyword name, so callers can inspect the argument list itself.
BRACKET_FULL_RE = re.compile(r"\[([A-Za-z_][A-Za-z0-9_]*)((?:\s+[^\[\]]*)?)\]")


def load_single_string_arg_keywords(references_dir):
    """
    Harvest keywords whose bracket-notation signature is EXACTLY one
    '$'-sigil argument and nothing else (e.g. '[space_group $symbol]',
    '[phase_name $phase_name]') -- the same shape confirmed by hand for
    space_group and generalized here to every keyword documented the same
    way, since $ unambiguously means "bare token or one quoted string" per
    Chapter 2's own notation (see BRACKET_FULL_RE's comment above).

    Deliberately conservative: only '#'/'E'-typed single-argument keywords
    are excluded from this harvest entirely (their valid forms are far more
    varied -- see the module comment above -- so a strict single-token
    check would misfire on them; that generalization is not attempted
    here). And if the SAME keyword name is ever documented ANYWHERE with a
    different shape (more than one argument, or its lone argument isn't
    '$'-sigil'd), it's dropped from the result entirely, even if it also
    has a clean single-'$'-arg form elsewhere -- conflicting evidence means
    "don't trust this one," not "trust the majority."
    """
    single_arg = set()
    conflicting = set()
    try:
        fnames = [f for f in os.listdir(references_dir) if f.lower().endswith(".md")]
    except OSError:
        return single_arg

    for fname in fnames:
        fpath = os.path.join(references_dir, fname)
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        for m in BRACKET_FULL_RE.finditer(text):
            name = m.group(1)
            rest = m.group(2).strip()
            if not rest:
                continue  # zero-argument keyword; not relevant here
            tokens = rest.split()
            # A bare '$' with no name after it (e.g. the condensed summary
            # table in 22-charge-flipping.md: '[space_group $] | P1') is the
            # same single-string-argument shape as '$symbol' elsewhere for
            # the same keyword -- just written tersely -- not a conflict.
            if len(tokens) == 1 and tokens[0].startswith("$"):
                single_arg.add(name)
            else:
                conflicting.add(name)

    return single_arg - conflicting


# Keywords shorter than this are excluded from
# load_single_e_arg_keywords()'s harvest -- the same noise-avoidance
# rationale as MIN_TYPO_CHECK_LEN above, but tuned empirically for this
# check: 1-3 character names (a, b, c, x, y, z, al, be, ga, ta, tb, u11,
# occ, beq, min, max, del, ...) are common enough as ordinary equation
# variable names or attribute keywords chained together that they carry
# real false-positive risk even though the full corpus run below (see
# check_single_e_arg_keywords' docstring) happened not to trip any at
# length 1. Kept as a deliberate safety margin rather than trusting the
# empirical zero.
MIN_E_ARG_CHECK_LEN = 4


def load_single_e_arg_keywords(references_dir):
    """
    Harvest keywords whose bracket-notation signature is EXACTLY one
    'E'/'!E'-sigil argument and nothing else (e.g. '[scale E]', '[beq E]')
    -- the numeric-value counterpart to load_single_string_arg_keywords()
    above. Per Chapter 2's own notation (see BRACKET_FULL_RE's comment),
    'E' means an equation-or-value parameter slot: a bare value,
    '@'-auto-named, '!'-fixed, explicitly named, or a full '= ...;'
    equation -- all of which still resolve to exactly ONE numeric value
    for that keyword, never more. A second bare number sitting right after
    that value, with no attribute keyword (min/max/del/...) or new
    statement keyword in between, is never valid TOPAS grammar for a
    single-E-arg keyword -- there's no legitimate reading of "keyword
    value extra_value" as one statement.

    Uses the exact same conflict-detection as
    load_single_string_arg_keywords(): if the SAME keyword name is ever
    documented elsewhere with a different shape (more than one argument,
    or a non-E/!E lone argument), it's dropped from the result entirely.
    This alone is not sufficient to catch every richer real-world grammar
    (site/hkl_plane needed hand exclusion for the $-arg check despite a
    clean single-arg bracket entry, for the same reason: their multi-arg
    form is only ever shown in prose/examples, never its own conflicting
    bracket line) -- so the caller also applies MIN_E_ARG_CHECK_LEN, and
    this harvest was corpus-verified (see check_single_e_arg_keywords'
    docstring) rather than trusted on the harvest alone.
    """
    single_arg = set()
    conflicting = set()
    try:
        fnames = [f for f in os.listdir(references_dir) if f.lower().endswith(".md")]
    except OSError:
        return single_arg

    for fname in fnames:
        fpath = os.path.join(references_dir, fname)
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        for m in BRACKET_FULL_RE.finditer(text):
            name = m.group(1)
            rest = m.group(2).strip()
            if not rest:
                continue  # zero-argument keyword; not relevant here
            tokens = rest.split()
            if len(tokens) == 1 and tokens[0] in ("E", "!E"):
                single_arg.add(name)
            else:
                conflicting.add(name)

    return single_arg - conflicting


def strip_comments_and_strings(text):
    """
    Replace the contents of block comments (/* ... */, nestable), line
    comments ('...to end of line), and double-quoted strings with spaces,
    preserving newlines and overall character offsets so line numbers
    computed from the result still line up with the original file.
    """
    out = list(text)
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            depth = 1
            out[i] = " "
            out[i + 1] = " "
            i += 2
            while i < n and depth > 0:
                if text[i] == "/" and i + 1 < n and text[i + 1] == "*":
                    depth += 1
                    out[i] = " "
                    out[i + 1] = " "
                    i += 2
                elif text[i] == "*" and i + 1 < n and text[i + 1] == "/":
                    depth -= 1
                    out[i] = " "
                    out[i + 1] = " "
                    i += 2
                else:
                    if text[i] != "\n":
                        out[i] = " "
                    i += 1
            continue
        if c == "'":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if c == '"':
            # Use a non-space, non-syntax placeholder ('x') for the
            # interior so a quoted-string argument (e.g. Out_String("\n..."))
            # still counts as non-empty content for macro-arity checking,
            # rather than collapsing to whitespace and looking like a
            # missing/empty argument.
            out[i] = " "
            i += 1
            while i < n and text[i] != '"' and text[i] != "\n":
                out[i] = "x"
                i += 1
            if i < n and text[i] == '"':
                out[i] = " "
                i += 1
            continue
        i += 1
    return "".join(out)


def strip_comments_only(text):
    """
    Like strip_comments_and_strings, but leaves quoted-string CONTENTS
    intact (only blanks /* */ block comments and '-line comments) --
    preserves the same length/offsets/newlines as strip_comments_and_strings
    so positions computed against one text (e.g. a str-block extent found
    via brace-matching on the fully-cleaned text) can be sliced directly out
    of this one to recover a real value that might be quoted, e.g.
    space_group "Fm-3m" -- needed by check_symmetry_constraints, which has
    to read the actual space-group symbol, not a blanked-out placeholder.
    """
    out = list(text)
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            depth = 1
            out[i] = " "
            out[i + 1] = " "
            i += 2
            while i < n and depth > 0:
                if text[i] == "/" and i + 1 < n and text[i + 1] == "*":
                    depth += 1
                    out[i] = " "
                    out[i + 1] = " "
                    i += 2
                elif text[i] == "*" and i + 1 < n and text[i + 1] == "/":
                    depth -= 1
                    out[i] = " "
                    out[i + 1] = " "
                    i += 2
                else:
                    if text[i] != "\n":
                        out[i] = " "
                    i += 1
            continue
        if c == "'":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
            continue
        i += 1
    return "".join(out)


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


IFDEF_RE = re.compile(r"#ifdef\s+([A-Za-z_]\w*)")
IFNDEF_RE = re.compile(r"#ifndef\s+([A-Za-z_]\w*)")
IF_EXPR_RE = re.compile(r"#if\s*\(")
ELSE_RE = re.compile(r"#else\b")
ELSEIF_RE = re.compile(r"#elseif\b")
ENDIF_RE = re.compile(r"#endif\b")
DEFINE_RE = re.compile(r"#define\s+([A-Za-z_]\w*)")

# Single combined regex used by strip_inactive_ifdef_branches to find EVERY
# directive on a line (not just the first) -- see that function's docstring
# for why this matters: '#ifdef NAME content #endif' on one physical line
# is real, valid TOPAS syntax (confirmed directly by the user, TOPAS-
# Academic's author, and by a real corpus file,
# test_examples/1000s-of-patterns/10000.inp, line 140:
# '#ifdef USE_PEAK_BUFFER_SIMILAR_TAG peak_buffer_similar_tag 1 #endif').
LINE_DIRECTIVE_RE = re.compile(
    r"(?P<ifdef>#ifdef\s+[A-Za-z_]\w*)"
    r"|(?P<ifndef>#ifndef\s+[A-Za-z_]\w*)"
    r"|(?P<ifexpr>#if\s*\([^)]*\))"
    r"|(?P<elseifexpr>#elseif\s*\([^)]*\))"
    r"|(?P<elseb>#else\b)"
    r"|(?P<endif>#endif\b)"
)


def strip_inactive_ifdef_branches(clean_text):
    """
    TOPAS's preprocessor only compiles the taken branch of #ifdef/#ifndef.
    A common convention in the example set is a permanently-disabled
    #ifdef BLOCK of free-form notes/alternate solutions guarded by a name
    that is never #define'd anywhere in the file -- such content can
    contain prose that isn't valid TOPAS syntax at all (e.g. "50) ...")
    and must not be brace/paren/semicolon-checked.

    For #ifdef NAME / #ifndef NAME (simple identifier conditions), the
    branch is blanked out (preserving newlines/line lengths) if NAME's
    definedness (found via a file-wide #define NAME scan) doesn't match
    the branch. #if (...) with a computed/runtime expression can't be
    evaluated statically, so both branches of those are left intact --
    each individually should be internally balanced in well-formed code,
    so keeping both does not itself cause false positives.

    Processes each line as a SEQUENCE of directive matches (via
    LINE_DIRECTIVE_RE.finditer), not just the first one found -- a real
    bug caught directly against a real corpus file
    (test_examples/1000s-of-patterns/10000.inp line 140:
    '#ifdef USE_PEAK_BUFFER_SIMILAR_TAG peak_buffer_similar_tag 1
    #endif', confirmed valid TOPAS syntax by the user, TOPAS-Academic's
    author): the original version blanked the ENTIRE line on the first
    directive match found (via .search() + a per-line `continue`), so a
    '#ifdef NAME ... #endif' both on one physical line pushed a stack
    frame that was never popped -- the #endif sharing that line was never
    even looked at. Every line after that point was then silently
    misclassified (active/inactive) for the rest of the file, which in
    turn fed check_braces_and_parens() a text with real '{'/'}' characters
    incorrectly blanked away, producing spurious "unmatched opening
    brace" errors far from the actual (nonexistent) problem.
    """
    defined = set(m.group(1) for m in DEFINE_RE.finditer(clean_text))

    lines = clean_text.split("\n")
    out_lines = []
    # Stack of dicts: {'active': bool, 'unknown': bool}
    stack = []

    def currently_active():
        return all(f["active"] for f in stack)

    for line in lines:
        pieces = []
        pos = 0
        for m in LINE_DIRECTIVE_RE.finditer(line):
            pieces.append((line[pos:m.start()], currently_active()))
            kind = m.lastgroup
            if kind == "ifdef":
                name = m.group("ifdef").split(None, 1)[1]
                stack.append({"active": name in defined, "unknown": False})
            elif kind == "ifndef":
                name = m.group("ifndef").split(None, 1)[1]
                stack.append({"active": name not in defined, "unknown": False})
            elif kind == "ifexpr":
                stack.append({"active": True, "unknown": True})
            elif kind in ("elseb", "elseifexpr"):
                if stack:
                    top = stack[-1]
                    if top["unknown"]:
                        top["active"] = True
                    else:
                        top["active"] = not top["active"]
            elif kind == "endif":
                if stack:
                    stack.pop()
            pos = m.end()
        pieces.append((line[pos:], currently_active()))

        out_lines.append("".join(seg if active else " " * len(seg) for seg, active in pieces))
    return "\n".join(out_lines)


def strip_opaque_blocks(clean_text):
    """
    Blank the interior (keeping the outer braces) of '{ ... }' bodies
    that immediately follow a keyword in OPAQUE_BLOCK_KEYWORDS, since
    that content is display text, not parsed TOPAS statements.
    """
    out = list(clean_text)
    for kw in OPAQUE_BLOCK_KEYWORDS:
        for m in re.finditer(r"\b" + re.escape(kw) + r"\b", clean_text):
            j = m.end()
            while j < len(clean_text) and clean_text[j] in " \t\r\n":
                j += 1
            if j >= len(clean_text) or clean_text[j] != "{":
                continue
            depth = 0
            k = j
            while k < len(clean_text):
                if clean_text[k] == "{":
                    depth += 1
                elif clean_text[k] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            else:
                continue
            for p in range(j + 1, k):
                if out[p] != "\n":
                    out[p] = " "
    return "".join(out)


def check_braces_and_parens(clean_text, issues):
    for open_c, close_c, name in (("{", "}", "brace"), ("(", ")", "parenthesis")):
        stack = []
        for i, c in enumerate(clean_text):
            if c == open_c:
                stack.append(i)
            elif c == close_c:
                if not stack:
                    issues.append(
                        ("error", line_of(clean_text, i),
                         f"Unmatched closing {name} '{close_c}' with no matching '{open_c}' before it.")
                    )
                else:
                    stack.pop()
        for pos in stack:
            issues.append(
                ("error", line_of(clean_text, pos),
                 f"Unmatched opening {name} '{open_c}' -- no closing '{close_c}' found for it before end of file.")
            )


def check_single_string_arg_keywords(clean_text, keywords, single_arg_keywords, issues):
    """
    Every keyword in single_arg_keywords (harvested by
    load_single_string_arg_keywords -- see that function's docstring for the
    '$' sigil convention from Technical_Reference.pdf Chapter 2) takes
    exactly ONE value: either a bare token with no internal whitespace, or a
    single quoted string. By the time this runs, strip_comments_and_strings
    has already collapsed a quoted string's interior to one unbroken run of
    'x' placeholders (no internal whitespace survives), so both forms look
    identical here: a single whitespace-delimited token.

    A stray space accidentally typed inside what was meant to be one bare
    token (e.g. "P_31_ 2_1" instead of "P_31_2_1" after space_group) silently
    splits it into two tokens. TOPAS then reads the second fragment as if it
    were the start of a new statement -- almost never what the author
    intended, and a real, confirmed bug pattern (found in
    test_examples/aac2.inp during development of this check, originally as a
    space_group-only special case before being generalized to every keyword
    documented the same way in the manual). Flag it when the token
    immediately following the value is itself NOT a recognized keyword/macro
    name and doesn't look like a scope boundary, since a legitimate next
    statement in a real TOPAS file is essentially always one or the other.
    """
    if not single_arg_keywords:
        return
    pattern = r"\b(" + "|".join(re.escape(k) for k in sorted(single_arg_keywords, key=len, reverse=True)) + r")\b"
    for m in re.finditer(pattern, clean_text):
        kw = m.group(1)
        after = clean_text[m.end():]
        # Require at least one real space/tab before the "value" -- with
        # zero-or-more whitespace allowed here, a *reference* to the
        # keyword's reserved name inside another expression (e.g.
        # "Get(phase_name)", immediately followed by ')') was wrongly read
        # as if ')' were phase_name's own value. A genuine value-taking use
        # is always keyword-SPACE-value; anything with no space at all
        # between them isn't this keyword being invoked in that form.
        value_match = re.match(r"[ \t]+(\S+)", after)
        if not value_match:
            continue
        value_token = value_match.group(1)
        # If the very next thing is itself a structural character, this
        # keyword isn't being used in the "bare single value" form at all
        # here -- e.g. "layer {" opens a block rather than taking a $-token
        # value, which is a real, legitimate second grammar for `layer`
        # that its bracket entry doesn't capture. Skip rather than guess.
        if value_token[0] in "{}();,":
            continue
        rest = after[value_match.end():]
        next_match = re.match(r"\s*(\S+)", rest)
        if not next_match:
            continue
        next_token = next_match.group(1)

        # A brace/paren/semicolon/comma right after is a normal scope
        # boundary or separator, not a stray fragment.
        if next_token[0] in "{}();,":
            continue

        # A preprocessor directive (#define, #ifdef, #include, ...) is
        # always a legitimate next statement -- TOPAS's general rule is
        # that after a keyword's value is consumed, the next token must be
        # a preprocessor directive, a keyword, or a macro name (which can
        # itself expand to further macros/keywords). Checked explicitly
        # here rather than relying on '#' happening to fail the "plausible
        # fragment" filter below.
        if next_token[0] == "#":
            continue

        ident_match = re.match(r"[A-Za-z_]\w*", next_token)
        if ident_match and ident_match.group(0) in keywords:
            continue  # legitimate next statement (a real keyword/macro)

        # Only flag fragments that look like plausible (but wrong) symbol
        # continuations -- letters/digits/underscore/colon/slash/hyphen --
        # to avoid guessing at anything stranger this heuristic can't judge.
        if re.match(r"^[A-Za-z0-9_:/\-]+$", next_token):
            issues.append(
                ("warning", line_of(clean_text, m.start()),
                 f"{kw} value looks like it was split by a stray space: "
                 f"'{value_token}' is immediately followed by '{next_token}', which is not "
                 f"a recognized keyword/macro name. {kw} takes a single token (or one "
                 f"quoted string) -- if this was meant to be one value, remove the space "
                 f"(e.g. '{value_token}{next_token}'); verify manually, this is a heuristic.")
            )


# A refined-value report token, e.g. "1104.81015`_7.8085822" or plain
# "5.410202" -- an optional sign, digits, optional decimal part, optional
# scientific-notation exponent, then optionally a backtick-error suffix.
# Defined here (ahead of its first use) rather than reusing the later
# module-level NUMBER_TOKEN_RE, which check_single_e_arg_keywords() below
# needs before that definition appears; the two are identical.
#
# Real bug found and fixed, discovered via param_dependency_trees.py's own
# output (a "prm !b1 .5" node silently missing from the dependency graph):
# the digit group before the decimal point was mandatory (`\d+(\.\d+)?`),
# so a bare leading-dot decimal like ".5" -- valid, common TOPAS syntax,
# confirmed directly in this skill's own real corpus (e.g.
# test_examples/simple.inp's "prm !b1 .5") -- silently failed to match at
# all, not just mis-parsed. Since every consumer of this regex (and its
# identical twin NUMBER_TOKEN_RE below) treats "value doesn't match" as
# "this isn't a value here, skip the whole statement," this could
# silently drop an entire prm/local/keyword declaration from EVERY check
# built on it (check_single_e_arg_keywords, check_prm_local_missing_min_max,
# check_missing_colon_before_value, check_xyz_near_one_third,
# find_refined_params.py's independent-parameter scan, and
# param_dependency_trees.py's dependency graph) whenever that value
# happened to be written without a leading zero. Fixed by requiring
# EITHER "digits[.digits]" OR a bare ".digits" (at least one digit
# required either before or after the dot, matching real TOPAS's own
# accepted numeric-literal grammar).
E_ARG_NUMBER_TOKEN_RE = re.compile(
    r"-?(?:\d+\.?\d*|\.\d+)([eE][+-]?\d+)?(`_?-?(?:\d+\.?\d*|\.\d+)([eE][+-]?\d+)?)?"
)


def check_single_e_arg_keywords(clean_text, keywords, e_arg_keywords, issues):
    """
    Every keyword in e_arg_keywords (harvested by
    load_single_e_arg_keywords() -- see its docstring for the 'E' sigil
    convention) takes exactly ONE numeric value, in one of TOPAS's usual
    E-parameter forms: a bare value ("scale 0.001"), '@'-auto-named
    ("scale @ 0.001"), '!'-fixed ("scale !0.001"), or explicitly named
    ("scale myname 0.001"). An equation form ("scale = ...;") is skipped
    entirely here -- it's terminated by ';', covered by
    check_missing_semicolons(), not this check.

    A second bare number sitting immediately after that value, with
    nothing recognizable (an attribute keyword like min/max/del, or a new
    statement keyword) in between, is left over from a bad edit -- e.g.
    "scale @ 0.00145344688 907", a real bug found in
    test_examples/simple.inp's macro-expanded form during development of
    this check. There is no legitimate TOPAS grammar where a second bare
    number can follow a single-E-arg keyword's value with nothing between
    them.

    Flagged as a warning, not a hard error: e_arg_keywords is harvested
    automatically from ~200 bracket-notation entries across every
    reference chapter, and while a full run against the ~1,120-file
    test_examples/ corpus during development produced exactly one hit --
    the genuine bug above, zero false positives -- that corpus can't prove
    every harvested keyword's real-world grammar is fully captured by its
    bracket notation (the $-arg check above needed hand exclusions for
    site/hkl_plane for exactly this reason, found only empirically). Treat
    a flag here as "verify manually", the same standard applied throughout
    this script's other heuristic checks.
    """
    if not e_arg_keywords:
        return
    pattern = r"\b(" + "|".join(re.escape(k) for k in sorted(e_arg_keywords, key=len, reverse=True)) + r")\b"
    for m in re.finditer(pattern, clean_text):
        kw = m.group(1)
        pos = m.end()
        n = len(clean_text)
        if pos >= n or clean_text[pos] not in " \t\r\n":
            continue
        j = pos
        while j < n and clean_text[j] in " \t\r\n":
            j += 1
        if j >= n or clean_text[j] == "=":
            continue  # equation form -- not this check's concern

        # Consume at most one leading sigil/name token before the value
        # ("@", "!name", or a bare "name"). A bare numeric first token
        # (the anonymous, unnamed value form) won't match this at all,
        # which is fine -- it just falls through to the value match below.
        tok_m = re.match(r"(?:[!@]?[A-Za-z_]\w*|[!@])", clean_text[j:])
        val_start = j
        if tok_m and tok_m.group(0):
            k = j + tok_m.end()
            while k < n and clean_text[k] in " \t\r\n":
                k += 1
            if E_ARG_NUMBER_TOKEN_RE.match(clean_text[k:]) and E_ARG_NUMBER_TOKEN_RE.match(clean_text[k:]).group(0):
                val_start = k

        val_m = E_ARG_NUMBER_TOKEN_RE.match(clean_text[val_start:])
        if not val_m or not val_m.group(0):
            continue  # not actually followed by a numeric value; not this keyword's E-value form
        after_value = clean_text[val_start + val_m.end():]

        stripped = after_value.lstrip(" \t\r\n")
        if not stripped:
            continue
        next_tok_m = re.match(r"\S+", stripped)
        next_tok = next_tok_m.group(0)
        if next_tok[0] in "{}();,:'\"":
            continue  # normal scope boundary/separator

        # A preprocessor directive is always a legitimate next statement --
        # see the matching comment in check_single_string_arg_keywords for
        # the general rule this encodes.
        if next_tok[0] == "#":
            continue

        ident_m = re.match(r"[A-Za-z_]\w*", next_tok)
        if ident_m and ident_m.group(0) in keywords:
            continue  # legitimate next statement or attribute keyword

        num_m = E_ARG_NUMBER_TOKEN_RE.match(next_tok)
        if num_m and num_m.group(0) == next_tok:
            issues.append(
                ("warning", line_of(clean_text, m.start()),
                 f"'{kw}' takes a single numeric value, but is immediately followed by a "
                 f"second bare number '{next_tok}' with no attribute keyword (min/max/del/...) "
                 f"or new statement in between. This looks like a stray leftover value from a "
                 f"bad edit -- verify manually and remove it if so (this is a heuristic).")
            )


XYZ_FRACTION_TARGETS = (("1/3", 1.0 / 3.0), ("2/3", 2.0 / 3.0))
# 0.0015 catches CIF-rounded decimals from 3 to 5 places (0.333 .. 0.33333)
# without reaching into territory a genuinely-refined general-position
# coordinate could plausibly land in by chance.
XYZ_FRACTION_TOLERANCE = 0.0015


def check_xyz_near_one_third(clean_text, issues):
    """
    Flag a bare x/y/z site-coordinate value that sits suspiciously close to
    1/3 or 2/3 -- raised directly by the user (TOPAS-Academic's author). A
    common CIF-import artifact: a site sitting exactly on a 3-fold axis (or
    otherwise symmetry-constrained to 1/3 or 2/3) gets written by the CIF as
    a rounded decimal ("0.3333", "0.66667", ...) and then pasted into the
    INP as a bare value -- e.g. "x 0.333" -- instead of the exact equation
    form ("x = 1/3;", or "!x = 1/3;" if the coordinate must stay fixed
    rather than free-refine). Free-refining a coordinate the space group
    actually fixes at an exact special-position value is a real
    crystallographic bug: the coordinate can drift away from the symmetry-
    required exact fraction during refinement, which is invalid.

    Scoped to the bare "x [!@]NAME? VALUE" forms (mirrors the value-parsing
    already used in check_single_e_arg_keywords): an equation form
    ("x = ...;") is skipped outright, since a deliberate equation was
    presumably already written rather than a raw pasted decimal. Values are
    reduced mod 1 before comparing, so negative or >1 values (e.g. a
    translated coordinate like -0.6667, fractionally equivalent to 0.3333)
    are still caught.

    Flagged as a warning, not an error -- this is a heuristic prompt to
    double-check, not a certain bug. Corpus-verified against the full
    ~1,120-file test_examples/ corpus: 4,472 occurrences across 62 files,
    but ~97% concentrated in just 6 large synthetic/simulated multi-atom
    cells (e.g. je-pdf/pdf_662_01.inp, je-pdf/bragg.inp,
    pdf/philip/Phils-talk/04 SrTiO3_5K_largebox_START.inp -- 1400+ hits
    each) where near-1/3 coordinates are common and usually intentional
    (grid/supercell placement), not CIF-rounding artifacts -- so this check
    can be extremely noisy on that class of file. Treat a large hit count
    on a big multi-atom/simulated-box file as expected, not as evidence of
    that many real bugs; it's far more diagnostic on a normal, CIF-derived,
    modest-atom-count structure, which is the case the user described.
    """
    for m in re.finditer(r"\b(x|y|z)\b", clean_text):
        coord = m.group(1)
        pos = m.end()
        n = len(clean_text)
        if pos >= n or clean_text[pos] not in " \t\r\n":
            continue
        j = pos
        while j < n and clean_text[j] in " \t\r\n":
            j += 1
        if j >= n or clean_text[j] == "=":
            continue  # equation form -- a deliberate equation was already written

        # Consume at most one leading sigil/name token before the value
        # ("@", "!name", or a bare "name") -- same pattern as
        # check_single_e_arg_keywords.
        tok_m = re.match(r"(?:[!@]?[A-Za-z_]\w*|[!@])", clean_text[j:])
        val_start = j
        if tok_m and tok_m.group(0):
            k = j + tok_m.end()
            while k < n and clean_text[k] in " \t\r\n":
                k += 1
            val_probe = E_ARG_NUMBER_TOKEN_RE.match(clean_text[k:])
            if val_probe and val_probe.group(0):
                val_start = k

        val_m = E_ARG_NUMBER_TOKEN_RE.match(clean_text[val_start:])
        if not val_m or not val_m.group(0):
            continue
        raw = val_m.group(0)
        try:
            val = float(raw.split("`")[0])
        except ValueError:
            continue

        frac = val % 1.0
        for label, target in XYZ_FRACTION_TARGETS:
            if abs(frac - target) < XYZ_FRACTION_TOLERANCE:
                issues.append(
                    ("warning", line_of(clean_text, m.start()),
                     f"'{coord} {raw}' is suspiciously close to {label} ({target:.6f}) -- "
                     f"if this coordinate is symmetry-constrained to an exact special-position "
                     f"value (common for CIF-imported sites on a 3-fold axis), it should likely "
                     f"be written as '{coord} = {label};' (or '!{coord} = {label};' if it must "
                     f"stay fixed) rather than a bare rounded decimal -- verify manually, this "
                     f"is a heuristic.")
                )
                break


def check_missing_semicolons(clean_text, issues):
    """
    Heuristic: an '=' that is not part of ==, !=, <=, >= starts an
    equation. Track paren depth AND brace depth from there (relative to
    the '='): the equation should reach a ';' with both depths back at
    0 before the enclosing scope changes. Note TOPAS equations are
    allowed to have a '{ ... }' function-block as their RHS (containing
    'def' sub-statements and a 'return', e.g. "prm = { def a = ...;
    return ...; };"), so encountering '{' is not itself an error -- only
    a '}' that closes a scope we did NOT open (brace depth already at 0)
    means the equation's enclosing block ended without a ';', which is
    a genuine missing-semicolon signal.
    """
    n = len(clean_text)
    i = 0
    while i < n:
        c = clean_text[i]
        if c == "=":
            prev_c = clean_text[i - 1] if i > 0 else ""
            next_c = clean_text[i + 1] if i + 1 < n else ""
            if prev_c in "=!<>" or next_c == "=":
                i += 1
                continue
            start_line = line_of(clean_text, i)

            # Peek past whitespace: if the RHS is a '{ ... }' block
            # (TOPAS's function-block equation form, e.g.
            # "fit_obj = { def a = ...; return ...; }"), the block's own
            # closing brace terminates the equation -- no separate ';'
            # after it is required or expected. Just find the matching
            # closing brace and move on.
            k = i + 1
            while k < n and clean_text[k] in " \t\r\n":
                k += 1
            if k < n and clean_text[k] == "{":
                depth = 0
                j = k
                while j < n:
                    if clean_text[j] == "{":
                        depth += 1
                    elif clean_text[j] == "}":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    j += 1
                i = j
                continue

            paren_depth = 0
            brace_depth = 0
            j = i + 1
            terminated = False
            while j < n:
                cj = clean_text[j]
                if cj == "(":
                    paren_depth += 1
                elif cj == ")":
                    paren_depth -= 1
                elif cj == "{":
                    brace_depth += 1
                elif cj == "}":
                    if brace_depth <= 0:
                        break
                    brace_depth -= 1
                elif cj == ";" and paren_depth <= 0 and brace_depth <= 0:
                    terminated = True
                    break
                elif cj == "=" and paren_depth <= 0 and brace_depth <= 0:
                    pc = clean_text[j - 1] if j > 0 else ""
                    nc = clean_text[j + 1] if j + 1 < n else ""
                    if pc not in "=!<>" and nc != "=":
                        # A fresh equation starts here before the current one
                        # reached its own ';' -- e.g. "prm = a : 0\n  z = 1/3;"
                        # would otherwise let the *next* statement's ';' be
                        # mistaken for this one's terminator, masking a real
                        # missing semicolon. Stop here, unterminated; the
                        # outer loop will re-examine from this '=' as its own
                        # equation.
                        break
                j += 1
            if not terminated:
                issues.append(
                    ("error", start_line,
                     "Equation starting with '=' here does not reach a terminating ';' "
                     "before the enclosing scope changes (or end of file). Check for a missing semicolon.")
                )
                i = j
                continue
            i = j
        i += 1


# A refined-value report, e.g. "1104.81015`_7.8085822" or plain
# "5.410202" -- an optional sign, digits, optional decimal part, optional
# scientific-notation exponent, then optionally a backtick-error suffix
# (TOPAS's own "value`_error" or "value`error" convention). Same
# leading-dot-decimal fix as E_ARG_NUMBER_TOKEN_RE above (the two really
# are identical, per that regex's own comment) -- see there for the full
# story of the real bug this fixes.
NUMBER_TOKEN_RE = re.compile(
    r"-?(?:\d+\.?\d*|\.\d+)([eE][+-]?\d+)?(`_?-?(?:\d+\.?\d*|\.\d+)([eE][+-]?\d+)?)?"
)


def check_missing_colon_before_value(clean_text, issues):
    """
    TOPAS's equation-value-report convention is "<equation>; : <value>" --
    the ';' terminates the equation, and a SEPARATE ':' introduces the
    value TOPAS overwrites on the next run (see
    references/01-syntax-and-parameters.md, "Reporting on equation
    values"). If the ':' is accidentally dropped (e.g. "prm bb = cs1 +
    cs2; 1088.36411`_7.84708627" instead of "...cs2; : 1088.36411..."),
    the value is left as a bare, orphaned numeric literal directly after
    the ';' with nothing referencing it -- not part of any equation, not a
    keyword's argument, not a new statement TOPAS can parse. This is the
    mirror-image mistake of check_missing_semicolons: that one catches a
    dropped ';' before a ':'; this one catches a dropped ':' after a valid
    ';'.

    Flagged as an error (not a warning) since a bare number is never a
    valid way to start a new statement in TOPAS -- there's no legitimate
    reading of "; <number>" with nothing between them, unlike the
    single-string-arg check above, which has to reckon with keywords
    genuinely having more than one valid grammar.
    """
    for m in re.finditer(r";", clean_text):
        after = clean_text[m.end():]
        stripped = after.lstrip(" \t\r\n")
        if not stripped or stripped[0] == ":":
            continue
        num_match = NUMBER_TOKEN_RE.match(stripped)
        if num_match and num_match.group(0):
            value = num_match.group(0)
            issues.append(
                ("error", line_of(clean_text, m.end()),
                 f"'{value}' appears immediately after ';' with no ':' before it. "
                 f"TOPAS's value-report syntax is '<equation>; : <value>', not "
                 f"'<equation>; <value>' -- this looks like a missing ':' left the value as "
                 f"an orphaned, unparseable token.")
            )


# A conservative, hand-picked set of real statement-starting keywords used
# only to bound how far check_prm_local_missing_min_max() scans forward
# looking for a 'min'/'max' attribute. Deliberately NOT the full
# keywords_plus_macros set built in check_file(): that set includes
# built-in equation FUNCTIONS (Min, Max, Get, Rand, ...) harvested from the
# equation-operators table, and a capitalized 'Min(...)'/'Max(...)' call
# inside a *different*, earlier attribute equation (e.g. "update = Val +
# Min(Change, 1); min 0 max 1") would wrongly look like a new statement
# starting, truncating the scan before the legitimate later 'min'/'max' is
# reached. This smaller, static set trades a bit of recall (an unusual
# statement keyword not listed here lets the scan run further than ideal,
# risking a missed later min/max belonging to something else entirely) for
# not misfiring on that much more common built-in-function-name collision.
PRM_LOCAL_BOUNDARY_KEYWORDS = DEFINER_KEYWORDS | {
    "site", "str", "xdd", "xdd_scr", "hkl_Is", "xo_Is", "d_Is",
    "dummy_str", "space_group", "load", "bkg", "scale",
}
PRM_LOCAL_BOUNDARY_RE = re.compile(
    r"\b(" + "|".join(sorted(PRM_LOCAL_BOUNDARY_KEYWORDS, key=len, reverse=True)) + r")\b"
)
PRM_MIN_MAX_RE = re.compile(r"\b(min|max)\b")
# A bare numeric value (e.g. "0.5", ".5", "5", "5.") -- used to recognize
# the plain "prm name value" declaration form, as distinct from an
# equation form ("prm name = ...;"); see the function docstring below for
# why only the former is checked.
PRM_BARE_VALUE_RE = re.compile(r"-?(\d+\.?\d*|\.\d+)")


def harvest_macros_with_min_max_body(clean_text):
    """
    Return the set of macro names (parenthesized or bodiless, any arity)
    whose OWN body text contains a literal 'min' or 'max' token -- e.g. a
    common project-local shorthand like:

        macro MM(x1, x2) { min = x1; max = x2; val_on_continue = Rand(x1, x2); }

    called right after a bare prm/local value (e.g. "prm cs_g1_ 30
    MM(3, 1000)") to attach min/max indirectly through a macro call rather
    than literal keyword text sitting next to the value -- a real, working
    convention found in test_examples/1000s-of-patterns/fit.inp during
    corpus verification of check_prm_local_missing_min_max(), which
    otherwise false-positives on every prm/local using it (this checker
    does not expand macros in general, but this one cheap, targeted lookup
    -- does this macro's own body mention min/max at all -- is enough to
    close that specific gap without a full expansion pass). Scoped to the
    current file's own macro definitions only, not the shared .inc
    library -- a library-level macro following this same bare-min/max-
    wrapper idiom would not be caught here.
    """
    names = set()
    n = len(clean_text)

    def body_has_min_max(open_brace_pos):
        depth = 0
        k = open_brace_pos
        while k < n:
            if clean_text[k] == "{":
                depth += 1
            elif clean_text[k] == "}":
                depth -= 1
                if depth == 0:
                    return PRM_MIN_MAX_RE.search(clean_text[open_brace_pos + 1:k]) is not None
            k += 1
        return False

    for m in MACRO_DEF_RE.finditer(clean_text):
        j = m.end()
        while j < n and clean_text[j] in " \t\r\n":
            j += 1
        if j < n and clean_text[j] == "{" and body_has_min_max(j):
            names.add(m.group(1))

    for m in BODILESS_MACRO_DEF_RE.finditer(clean_text):
        brace_pos = m.end() - 1  # this regex's own match already ends right after '{'
        if body_has_min_max(brace_pos):
            names.add(m.group(1))

    return names


def check_prm_local_missing_min_max(clean_text, min_max_macro_names, issues):
    """
    Flag a refined prm/local parameter (no leading '!', so TOPAS WILL
    refine it) that is given a bare starting value but no 'min'/'max'
    attribute. Confirmed real-world bad practice (raised directly by the
    user, TOPAS-Academic's author) and documented in
    references/01-syntax-and-parameters.md, "Try and use parameter
    attributes": unlike subject-specific keywords (beq, CS_L, lattice
    parameters, ...), which all carry internal default min/max limits
    (Table 2-1), prm/local have NONE at all -- an unbounded refined
    parameter can wander to a numerically invalid or unphysical value with
    nothing to stop it during refinement.

    Deliberately scoped to only the plain "prm|local [!@$]NAME VALUE"
    form:
      - A '!' prefix means NOT refined -- no warning needed, regardless of
        min/max.
      - The bare, un-named auto form ("prm @ 0.5", no identifier at all --
        the auto-generated internal name is used and any following text
        would just be an ignored label) is skipped: there's no name left
        to report in the warning.
      - Equation forms ("prm name = ...;") are skipped entirely: per
        references/01-syntax-and-parameters.md section 2.9, an equation is
        only an independently REFINED parameter if it happens to reduce to
        a constant -- otherwise it's a dependent parameter, for which
        min/max isn't the relevant safeguard. That distinction can't be
        judged from static text alone, so this check does not attempt it.

    The forward search for 'min'/'max' is bounded by
    PRM_LOCAL_BOUNDARY_RE -- see that constant's own comment for why it's a
    small curated set rather than the full recognized-keyword list. A call
    to any macro in min_max_macro_names (see
    harvest_macros_with_min_max_body()) found within that same window also
    satisfies the check, since such a macro sets min/max indirectly rather
    than as literal keyword text next to the value. This is a warning, not
    an error: a best-practice recommendation, not a syntax mistake TOPAS
    itself would reject.
    """
    macro_call_re = None
    if min_max_macro_names:
        macro_call_re = re.compile(
            r"\b(" + "|".join(re.escape(n) for n in sorted(min_max_macro_names, key=len, reverse=True)) + r")\s*\("
        )
    for m in re.finditer(r"\b(prm|local)\b", clean_text):
        kw = m.group(1)
        after_kw = clean_text[m.end():]
        name_m = re.match(r"[ \t\r\n]+([!@$]?)([A-Za-z_]\w*)", after_kw)
        if not name_m:
            continue
        sigil, name = name_m.group(1), name_m.group(2)
        if sigil == "!":
            continue  # explicitly fixed -- not refined, min/max moot

        rest = after_kw[name_m.end():]
        stripped = rest.lstrip(" \t\r\n")
        if not stripped or not PRM_BARE_VALUE_RE.match(stripped):
            continue  # equation form (or something unexpected) -- skip, see docstring

        search_start = m.end() + name_m.end()
        bm = PRM_LOCAL_BOUNDARY_RE.search(clean_text, search_start)
        window_end = bm.start() if bm else len(clean_text)
        window = clean_text[search_start:window_end]
        if PRM_MIN_MAX_RE.search(window):
            continue  # has at least one of min/max already -- satisfied
        if macro_call_re and macro_call_re.search(window):
            continue  # a min/max-setting macro (see harvest_macros_with_min_max_body) is called here

        issues.append(
            ("warning", line_of(clean_text, m.start()),
             f"'{kw} {sigil}{name}' defines a refined parameter (no '!' prefix, so TOPAS "
             f"will refine it) with a bare value but no 'min'/'max' attribute. Unlike "
             f"subject-specific keywords (beq, CS_L, lattice parameters, ...), "
             f"'{kw}'/'local' carry no default min/max limits (references/01-syntax-and-"
             f"parameters.md, \"Try and use parameter attributes\") -- an unbounded "
             f"refined parameter is bad practice; add explicit min/max.")
        )


def find_defined_names(clean_text):
    names = set()
    tokens = list(IDENTIFIER_RE.finditer(clean_text))
    for idx, m in enumerate(tokens):
        word = m.group(0)
        if word in DEFINER_KEYWORDS and idx + 1 < len(tokens):
            names.add(tokens[idx + 1].group(0))
    for m in re.finditer(r"[@!]\s*([A-Za-z_][A-Za-z0-9_]*)", clean_text):
        names.add(m.group(1))
    # Names introduced via #define NAME are user-chosen flags, not keywords.
    for m in re.finditer(r"#define\s+([A-Za-z_]\w*)", clean_text):
        names.add(m.group(1))
    return names


def check_keyword_typos(clean_text, keywords, issues):
    if not keywords:
        return
    # TOPAS keywords, macro names, and parameter names are all CASE
    # SENSITIVE -- confirmed directly, so matching here is exact-case, no
    # folding. Earlier false positives on things like "Exclude",
    # "Grs_Interaction", "Remove_Phase", "PO_Spherical_Harmonics", and
    # "NoThDependence" were never a case-sensitivity problem: each is a
    # REAL, separately and exactly-cased macro defined in topas.inc /
    # interface.inc (e.g. `macro Exclude { load exclude }` alongside the
    # distinct low-level `exclude` keyword; `macro NoThDependence(yminymax)`
    # defined alongside the separate `macro No_Th_Dependence`), just not
    # captured by the chapter-21 bracket-keyword harvest (which only lists
    # low-level keywords, not the convenience macros layered on top of them
    # elsewhere in the manual). `keywords` here is expected to already
    # include those exact-cased macro names, merged in by the caller from
    # the bundled .inc library.
    defined_names = find_defined_names(clean_text)
    seen_already = set()
    keywords_by_len = {}
    for kw in keywords:
        keywords_by_len.setdefault(len(kw), []).append(kw)

    tokens = list(IDENTIFIER_RE.finditer(clean_text))
    skip_next_idx = -1
    for idx, m in enumerate(tokens):
        word = m.group(0)

        if idx == skip_next_idx:
            continue

        # If this token is itself a real keyword/macro (exact case), the
        # next token is very likely its argument/parameter-name position
        # (e.g. "scale scale_1", "peak_buffer_step ..."), not a keyword
        # itself -- skip it.
        if word in keywords:
            skip_next_idx = idx + 1
            continue

        if len(word) < MIN_TYPO_CHECK_LEN:
            continue
        if word in defined_names:
            continue
        if word in seen_already:
            continue

        # Filename-fragment suppression: an identifier immediately followed
        # by ".ext" (a bare, unquoted filename like "foo.xy") or by "-<digit>"
        # (a hyphenated filename stem like "rigida-1.xy" tokenizing to
        # "rigida" + "1") is very likely a file name/stem, not a keyword.
        end = m.end()
        tail = clean_text[end:end + 6]
        if re.match(r"\.[A-Za-z]{1,5}\b", tail) or re.match(r"-\d", tail):
            continue

        candidates = []
        for delta in (-2, -1, 0, 1, 2):
            candidates.extend(keywords_by_len.get(len(word) + delta, []))
        if not candidates:
            continue
        # Exact-case near-miss matching -- a stricter comparison than the
        # earlier case-folded version, since case itself now counts as a
        # real difference (and a real class of typo: right word, wrong case).
        close = difflib.get_close_matches(word, candidates, n=1, cutoff=0.82)
        if close:
            seen_already.add(word)
            issues.append(
                ("warning", line_of(clean_text, m.start()),
                 f"'{word}' is not a recognized keyword/macro name (exact case) and closely "
                 f"resembles '{close[0]}'. Possible typo, or a case mistake since TOPAS names "
                 f"are case sensitive -- verify manually (this is a heuristic, not certain).")
            )


def harvest_macro_arities(text):
    """
    Scan for 'macro Name(arg1, arg2, ...) { ... }'-style definitions and
    return {name: set_of_argument_counts}. Bodiless macros defined without
    parentheses at all (e.g. 'macro LP { }') are invoked without parens too,
    so they never show up as an 'Identifier(...)' call site and don't need
    an entry here.
    """
    arities = {}
    for m in MACRO_DEF_RE.finditer(text):
        name = m.group(1)
        params_str = m.group(2).strip()
        if params_str == "":
            count = 0
        else:
            count = len(params_str.split(","))
        arities.setdefault(name, set()).add(count)
    return arities


def harvest_bodiless_macro_names(text):
    """
    Macros can also be defined without any parentheses at all, e.g.
    'macro Exclude { load exclude }' or 'macro No_Th_Dependence { lam
    no_th_dependence ... }' -- invoked bare, by name only, with no
    argument list. These never show up as an 'Identifier(...)' call site,
    so they're irrelevant to arity-checking, but their exact-cased names
    still belong in the "known good" set for keyword-typo checking.
    """
    names = set()
    for m in BODILESS_MACRO_DEF_RE.finditer(text):
        names.add(m.group(1))
    return names


def load_library_macro_arities():
    """
    Harvest macro arities (and bodiless macro names) from every bundled
    .inc file under references/system-files/inc/ -- this is the standard
    macro library that's always in scope (topas.inc is auto-loaded every
    run, and it #includes the others), so calls to these macros are
    checked against this library merged with whatever the target file
    defines itself. Returns (arities_dict, bodiless_names_set).
    """
    merged = {}
    bodiless = set()
    try:
        fnames = os.listdir(MACRO_LIB_DIR)
    except OSError:
        return merged, bodiless
    for fname in fnames:
        fpath = os.path.join(MACRO_LIB_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        text = strip_comments_and_strings(text)
        for name, counts in harvest_macro_arities(text).items():
            merged.setdefault(name, set()).update(counts)
        bodiless.update(harvest_bodiless_macro_names(text))
    return merged, bodiless


def check_macro_arity(clean_text, library_arities, issues):
    """
    For every macro name that has a KNOWN arity (from the file's own
    definitions merged with the standard library), check that every call
    site's argument count matches at least one defined arity. Built-in
    functions (Cos, Sin, Get, ...) and any other identifier that isn't
    actually defined as a macro anywhere in scope are never checked here --
    only names with a known 'macro Name(...)' definition are, which keeps
    this specific to genuine macro-overload arity mismatches.

    Note: TOPAS resolves same-named macros by matching argument count, but
    a real observed edge case (see references/console-output-and-errors.md
    and the beq-2-create.inp / beq-3-create.inp example) shows that when a
    file-local macro reuses a name already defined with a different arity
    by a system #include (topas.inc/pdf.inc), the file-local arity can
    fail to resolve at runtime even though it's 'known' to this checker.
    Treat a clean pass here as "the argument count matches a documented
    definition somewhere," not an ironclad guarantee TOPAS will resolve it.
    """
    tokens_seen = set()
    for m in re.finditer(r"([A-Za-z_]\w*)\s*\(", clean_text):
        name = m.group(1)
        if name not in library_arities:
            continue
        # Skip the macro's own definition site ("macro Name(...)").
        prefix = clean_text[:m.start()]
        prev_word_match = re.search(r"([A-Za-z_]\w*)\s*$", prefix.rstrip())
        if prev_word_match and prev_word_match.group(1) == "macro":
            continue

        paren_start = m.end() - 1
        depth = 0
        j = paren_start
        n = len(clean_text)
        while j < n:
            if clean_text[j] == "(":
                depth += 1
            elif clean_text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        else:
            continue  # unterminated -- brace/paren check already flags this
        args_str = clean_text[paren_start + 1:j].strip()
        if args_str == "":
            arg_count = 0
        else:
            depth = 0
            count = 1
            for c in args_str:
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                elif c == "," and depth == 0:
                    count += 1
            arg_count = count

        valid_counts = library_arities[name]
        if arg_count not in valid_counts:
            key = (name, arg_count, m.start())
            if key in tokens_seen:
                continue
            tokens_seen.add(key)
            valid_str = " or ".join(str(v) for v in sorted(valid_counts))
            issues.append(
                ("warning", line_of(clean_text, m.start()),
                 f"Macro '{name}' called here with {arg_count} argument(s), but its only known "
                 f"definition(s) take {valid_str} argument(s) -- possible arity mismatch "
                 f"(verify manually; overloaded macros of the same name defined elsewhere could "
                 f"still be valid if not captured here).")
            )


GET_TIE_RE = re.compile(
    r"^\s*(?P<neg>-)?\s*Get\(\s*(?P<name>[A-Za-z_]\w*)\s*\)\s*"
    r"(?:(?P<mul_op>[*/])\s*(?P<mul_x>[\d.]+)|(?P<mul_j>[\d.]+))?\s*"
    r"(?:(?P<off_sign>[+-])\s*(?P<off_val>[\d./]+))?\s*$"
)
# Named groups (not purely positional -- see below) since a tie can now
# carry an optional multiplier/divisor as well as the original optional
# offset:
#   neg      -- leading '-' before Get(...), if any
#   name     -- the referenced coordinate/parameter name
#   mul_op / mul_x -- an explicit '* 0.99' or '/ 100' -- mul_op holds
#                      which operator, mul_x the factor.
#   mul_j    -- a multiplier written with NO operator at all, via bare
#               juxtaposition ('Get(x) .99') -- confirmed as real, valid
#               TOPAS equation syntax by running an .inp with exactly
#               this form ('z = Get(x) .99 + 0.1625;') through a live
#               tc.exe: it parsed and refined with no syntax error.
#               Division has no such implicit form -- only '/' is ever a
#               divisor, never juxtaposition.
#   off_sign / off_val -- an optional additive offset ('+ 0.1625')
# A tie with neither mul_x nor mul_j set (just 'Get(name)', optionally
# negated) is the original "bare" tie this regex handled before
# multiplier/divisor support was added -- callers checking for that exact
# form (e.g. a lattice length REQUIRED to equal 'Get(a);' with no
# scaling) must explicitly check mul_x/mul_j are both absent, not just
# rely on the offset groups.
def get_tie_value(tie_match, known_value):
    """Resolve a GET_TIE_RE match against the already-known numeric value
    of the coordinate/parameter it references -- sign * known_value,
    scaled by the multiplier/divisor if present, plus the additive
    offset if present."""
    sign = -1 if tie_match.group("neg") else 1
    val = sign * known_value
    mul_str = tie_match.group("mul_x") or tie_match.group("mul_j")
    if mul_str:
        factor = float(mul_str)
        val = val / factor if tie_match.group("mul_op") == "/" else val * factor
    if tie_match.group("off_sign"):
        offset = float(Fraction(tie_match.group("off_val")))
        if tie_match.group("off_sign") == "-":
            offset = -offset
        val += offset
    return val

ADP_TIE_TERM_RE = re.compile(
    r"^(?:(\d+)\*)?Get\(([A-Za-z_]\w*)\)(?:/(\d+))?$"
)


def parse_adp_tie_expression(expr):
    """
    Parse an ADP tie equation's RHS -- a linear combination of one or more
    'Get(other_adp_name)' terms, each optionally scaled (matching exactly
    what cif_to_str.py's format_adp_tie() emits: 'Get(u11)', '-Get(u12)',
    '3 * Get(u11)', 'Get(u11) / 2', or a multi-term sum like
    'Get(u12) + Get(u13)') -- into a list of (Fraction coeff, other_name)
    terms. Returns None if the expression doesn't match this pattern (e.g.
    it references a plain prm name or a non-ADP equation) -- this checker
    doesn't attempt to evaluate arbitrary equations.
    """
    stripped = expr.replace(" ", "")
    if not stripped:
        return None
    terms = []
    for raw_term in re.findall(r"[+-]?[^+-]+", stripped):
        if not raw_term:
            continue
        sign = 1
        body = raw_term
        if body[0] == "+":
            body = body[1:]
        elif body[0] == "-":
            sign = -1
            body = body[1:]
        m = ADP_TIE_TERM_RE.match(body)
        if not m:
            return None
        num_str, other_name, den_str = m.groups()
        coeff = Fraction(int(num_str) if num_str else 1, int(den_str) if den_str else 1)
        terms.append((sign * coeff, other_name))
    return terms if terms else None


def adp_terms_match(parsed, required):
    """Order-independent comparison of two (coeff, name) term lists."""
    if parsed is None or len(parsed) != len(required):
        return False
    parsed_map = {}
    for coeff, name in parsed:
        if name in parsed_map:
            return False
        parsed_map[name] = coeff
    required_map = {name: coeff for coeff, name in required}
    return parsed_map.keys() == required_map.keys() and all(
        parsed_map[n] == required_map[n] for n in required_map
    )

# Module-level (not per-file) so a symbol resolved once -- successfully or
# not -- is never re-attempted via sgcom6.exe across a whole directory run.
# Without this, a placeholder/non-crystallographic space_group symbol
# shared by many files in a corpus (real ones exist, e.g. synthetic PDF-fit
# test files with no real space group) would pay a full subprocess-timeout
# cost once PER FILE instead of once total -- confirmed as a real,
# multi-minute slowdown during corpus verification of this check.
_SG_OPERATOR_CACHE = {}

# Which crystal system(s) each built-in lattice-parameter macro (topas.inc)
# already correctly implements internally -- confirmed by reading their
# actual bodies (e.g. `macro Cubic(cv) { a cv b = Get(a); c = Get(a); }`,
# `macro Rhombohedral(a_cv, al_cv) { a a_cv b = Get(a); c = Get(a); al
# al_cv be = Get(al); ga = Get(al); }`). A .inp file using one of these
# doesn't need its own literal a/b/c/al/be/ga constraint checked -- the
# macro already ties everything correctly, even though that isn't visible
# as literal "= Get(...)" text at the site of the call.
LATTICE_MACRO_SYSTEMS = {
    "Cubic": {"cubic"},
    "Tetragonal": {"tetragonal"},
    "Hexagonal": {"hexagonal_or_trigonal"},
    "Trigonal": {"hexagonal_or_trigonal"},
    "Rhombohedral": {"hexagonal_or_trigonal"},  # rhombohedral-axes variant; same rotation classification
}


def find_str_blocks(clean_text):
    """
    Find the extent of each `str` phase block. Unlike most TOPAS block
    keywords, `str` does NOT use { } -- it's a bare keyword whose content
    implicitly extends until the next `str` at the same brace depth, or
    until the enclosing block (xdd { ... }, etc.) closes, whichever comes
    first (confirmed against real corpus files, e.g. test_examples/aac1.inp,
    which has many consecutive bare `str` phases with no braces between
    them at all). Returns a list of (content_start, content_end) offsets
    into clean_text, spanning each block's body (excluding the `str`
    keyword itself).

    A `for` keyword at the same relative depth ALSO terminates a str's
    span, same as another `str` keyword would. `for strs`/`for xdds`
    (optionally `for strs N to M`, applying a keyword like `space_group`
    to a RANGE of already-declared str objects by their 1-based
    sequential index) is a loop construct over pre-existing objects, not
    a continuation of the current str's own inline content -- but since
    it opens with `{`, the old code (which only checked for another `str`
    keyword or the enclosing depth reaching 0) walked straight through it,
    silently absorbing everything inside as if it belonged to the
    preceding bare str. Real bug found this way: a file with several bare
    `str`-only "reporting" objects (no space_group of their own) followed
    much later by `for xdds { for strs {...} for strs 1 to 1 {...}
    space_group ... }` had one of those bare strs' span swallow the
    ENTIRE for-loop region, including THREE separate space_group
    declarations meant for three different phases -- check_symmetry_
    constraints then attributed the FIRST one it found (via plain
    re.search) to unrelated content, flagging a nonexistent lattice-tie
    violation (test_examples/matthew-rowles/2457_surface_paper_2.inp,
    confirmed and diagnosed directly by the user, TOPAS-Academic's
    author, after checking the real file: str position 6's actual space
    group is P-1, set via 'for strs 5 to 6 { space_group P-1 }' much
    later in the file, not the P_42/M_N_M this checker had reported).
    """
    n = len(clean_text)
    str_positions = [m.start() for m in re.finditer(r"\bstr\b", clean_text)]
    str_pos_set = set(str_positions)
    for_pos_set = set(m.start() for m in re.finditer(r"\bfor\b", clean_text))
    blocks = []
    for pos in str_positions:
        i = pos + 3
        depth = 0
        end = n
        while i < n:
            c = clean_text[i]
            if c == "{":
                depth += 1
                i += 1
            elif c == "}":
                if depth == 0:
                    end = i
                    break
                depth -= 1
                i += 1
            elif depth == 0 and ((i in str_pos_set and i != pos) or i in for_pos_set):
                end = i
                break
            else:
                i += 1
        blocks.append((pos + 3, end))
    return blocks


def extract_keyword_form(clean_slice, keyword):
    """
    Find `keyword`'s value/equation at its FIRST occurrence in clean_slice
    (a str-block-scoped slice of the fully-cleaned text). Returns one of:
      ('equation', expr_string, match_start_offset)
      ('value', sigil, numeric_value, name_or_None, match_start_offset)
          -- sigil in ('', '@', '!'); name is the parameter name given
             before the number if any (e.g. 'qq' in 'x qq 0.123'), else
             None -- two keywords sharing the same name are a TOPAS
             kernel-enforced invariant (always equal, see check_symmetry_
             constraints' 'tied' handling), distinct from an anonymous
             bare value.
      None  -- keyword not found, or its form couldn't be parsed as a
              single bare/@/equation value (e.g. followed immediately by
              another keyword with no value at all -- not this function's
              concern, just means nothing to check).
    """
    m = re.search(r"\b" + re.escape(keyword) + r"\b", clean_slice)
    if not m:
        return None
    pos = m.end()
    n = len(clean_slice)
    while pos < n and clean_slice[pos] in " \t\r\n":
        pos += 1
    if pos < n and clean_slice[pos] == "=":
        end = clean_slice.find(";", pos)
        if end == -1:
            return None
        expr = clean_slice[pos + 1:end].strip()
        return ("equation", expr, m.start())

    tok_m = re.match(r"(?:[!@]?[A-Za-z_]\w*|[!@])", clean_slice[pos:])
    val_start = pos
    sigil = ""
    name = None
    if tok_m and tok_m.group(0):
        token = tok_m.group(0)
        sigil = "@" if token.startswith("@") else ("!" if token.startswith("!") else "")
        bare = token[1:] if sigil else token
        name = bare or None
        k = pos + tok_m.end()
        while k < n and clean_slice[k] in " \t\r\n":
            k += 1
        probe = E_ARG_NUMBER_TOKEN_RE.match(clean_slice[k:])
        if probe and probe.group(0):
            val_start = k
    val_m = E_ARG_NUMBER_TOKEN_RE.match(clean_slice[val_start:])
    if not val_m or not val_m.group(0):
        return None
    try:
        val = float(val_m.group(0).split("`")[0])
    except ValueError:
        return None
    return ("value", sigil, val, name, m.start())


def find_sites(clean_slice):
    """
    Find each `site NAME ...` occurrence within a str-block slice and its
    extent (until the next `site` keyword or the slice's end). Returns a
    list of (name, site_slice, site_slice_start_offset).
    """
    positions = [(m.start(), m.group(1)) for m in
                 re.finditer(r"\bsite\b\s+([!@]?[A-Za-z_]\w*)", clean_slice)]
    sites = []
    for idx, (pos, name) in enumerate(positions):
        end = positions[idx + 1][0] if idx + 1 < len(positions) else len(clean_slice)
        sites.append((name.lstrip("!@"), clean_slice[pos:end], pos))
    return sites


PLAIN_NUMBER_EQUATION_RE = re.compile(r"^-?\d+/\d+$|^-?\d+(\.\d+)?([eE][+-]?\d+)?$")


def parse_plain_numeric_equation(expr):
    """
    Try to evaluate an equation RHS that's just a plain fraction or decimal
    constant -- e.g. 'x = 1/4;' or 'z = 0.833333333;' -- exactly the form
    cif_to_str.py itself emits for a fixed coordinate that snaps to a
    common fraction (see snap_to_fraction/format there). Returns None for
    anything else (a Get() reference, a prm name, arithmetic beyond a bare
    constant) -- not a general expression evaluator.
    """
    s = expr.strip()
    if not PLAIN_NUMBER_EQUATION_RE.match(s):
        return None
    try:
        return float(Fraction(s)) if "/" in s else float(s)
    except (ValueError, ZeroDivisionError):
        return None


LATTICE_MACRO_SCOPE_ARGS = {"Cubic": 1, "Tetragonal": 2, "Hexagonal": 2, "Trigonal": 2, "Rhombohedral": 2}


def _numeric_from_macro_arg(arg):
    """Extract the trailing numeric token from a lattice-macro argument
    like '@ 10.820412', '!name 5.4', or a bare '5.4' -- the value is
    always the last whitespace-separated token in these built-in macros."""
    toks = arg.strip().split()
    if not toks:
        return None
    try:
        return float(toks[-1])
    except ValueError:
        return None


def resolve_str_scope_values(preamble):
    """
    Resolve a str block's own structural keyword values (a, b, c, al, be,
    ga, scale) to concrete numbers where possible -- this is the object-
    level scope a SITE's Get() call walks up into when it references a
    keyword that isn't one of the site's own x/y/z/u11..u23/occ/beq.

    This is NOT a guess -- it was confirmed directly against a live
    tc.exe run, using test_examples/simple.inp's own Cubic(@ 10.820412)
    str as a fixed baseline and changing exactly one thing at a time:
      - 'beq = Get(b1);' (b1 a str-level `prm !b1 .5`, the SAME name that
        already works fine as a bare reference: 'beq = b1;') FAILS with
        "Cannot locate b1 from beq in data structures" -- Get() is NOT a
        general named-variable lookup; a plain prm/local is referenced by
        ordinary bare identifier instead, never through Get().
      - 'beq = Get(a) / 10;' (site has no 'a' of its own; the enclosing
        str's 'a' comes only from the Cubic() macro, never written
        literally) resolves and refines successfully -- confirming Get()
        walks up to the NEAREST ENCLOSING object that owns a keyword
        actually named 'a' (a real structural slot: x/y/z/u_ij/occ/beq
        for a site; a/b/c/al/be/ga/scale/space_group for a str; ...),
        not just the current object.
    So Get() search order is: current object's own keyword slots first,
    then the nearest ancestor object that has a keyword of that name --
    exactly mirroring how the manual's own 'fn lat(h,k,l) = h Get(a) + k
    Get(b) + l Get(c);' example (references/20-miscellaneous.md) reads
    the ENCLOSING str's a/b/c when inlined into one of its equations.

    Handles both literal 'a 5' keywords and TOPAS's built-in lattice
    macros (Cubic/Tetragonal/Hexagonal/Trigonal/Rhombohedral), whose
    exact argument-to-parameter mapping was read from the live install's
    topas.inc (same mapping plot_str_3d.py's extract_cell_params uses).
    Only returns keywords that actually resolve -- no invented defaults
    (e.g. a str missing 'b' does NOT get 'b' silently assumed equal to
    'a' here, since Get(b) on such a str would genuinely fail in TOPAS
    too, not silently succeed with a guessed value).
    """
    known = {}
    macro_m = re.search(r"\b(Cubic|Tetragonal|Hexagonal|Trigonal|Rhombohedral)\s*\(", preamble)
    if macro_m:
        name = macro_m.group(1)
        args, _ = parse_call_args(preamble, macro_m.end() - 1)
        vals = [_numeric_from_macro_arg(a) for a in args]
        needed = LATTICE_MACRO_SCOPE_ARGS[name]
        if len(vals) >= needed and all(v is not None for v in vals[:needed]):
            if name == "Cubic":
                a = vals[0]
                known.update(a=a, b=a, c=a, al=90.0, be=90.0, ga=90.0)
            elif name == "Tetragonal":
                a, c = vals[0], vals[1]
                known.update(a=a, b=a, c=c, al=90.0, be=90.0, ga=90.0)
            elif name in ("Hexagonal", "Trigonal"):
                a, c = vals[0], vals[1]
                known.update(a=a, b=a, c=c, al=90.0, be=90.0, ga=120.0)
            elif name == "Rhombohedral":
                a, al = vals[0], vals[1]
                known.update(a=a, b=a, c=a, al=al, be=al, ga=al)
    for kw in ("a", "b", "c", "al", "be", "ga", "scale"):
        if kw in known:
            continue
        form = extract_keyword_form(preamble, kw)
        if form is None:
            continue
        if form[0] == "value":
            known[kw] = form[2]
        elif form[0] == "equation":
            v = parse_plain_numeric_equation(form[1])
            if v is None:
                tie_m = GET_TIE_RE.match(form[1])
                if tie_m and tie_m.group("name") in known:
                    v = get_tie_value(tie_m, known[tie_m.group("name")])
            if v is not None:
                known[kw] = v
    return known


def resolve_site_coordinates(site_slice, outer_known=None):
    """
    Extract numeric (x, y, z) values from a site's text, resolving simple
    'coord = Get(other)[*mult][+-offset];' ties against already-known
    bare/@ values (one pass is sufficient -- a coordinate can only tie to
    one of the other two, never itself, so no chains longer than one hop
    are possible here), and plain-constant equations ('x = 1/4;') directly
    via parse_plain_numeric_equation. Returns (point_or_None, forms_dict),
    where forms_dict maps 'x'/'y'/'z' -> the raw extract_keyword_form()
    result (or None). point is None if not all three coordinates could be
    resolved to a concrete number (e.g. an equation referencing something
    other than a simple Get() tie or a plain constant -- deliberately not
    evaluated further, since this check only trusts what it can verify
    structurally, not a general expression evaluator).

    `outer_known`, if given, is a dict of the ENCLOSING str's own resolved
    keyword values (see resolve_str_scope_values) -- if a Get() reference
    isn't one of this site's own x/y/z, it's looked up there next, before
    giving up. This mirrors Get()'s real, confirmed-via-tc.exe search
    order: current object first, then the nearest ancestor object that
    owns a keyword of that name.
    """
    forms = {c: extract_keyword_form(site_slice, c) for c in ("x", "y", "z")}
    known = {}
    for c, form in forms.items():
        if form and form[0] == "value":
            known[c] = form[2]
        elif form and form[0] == "equation":
            plain = parse_plain_numeric_equation(form[1])
            if plain is not None:
                known[c] = plain
    for c, form in forms.items():
        if c in known or not form or form[0] != "equation":
            continue
        tie_m = GET_TIE_RE.match(form[1])
        if not tie_m:
            continue
        other = tie_m.group("name")
        if other in known:
            known[c] = get_tie_value(tie_m, known[other])
        elif outer_known and other in outer_known:
            known[c] = get_tie_value(tie_m, outer_known[other])
    if len(known) == 3:
        return (known["x"], known["y"], known["z"]), forms
    return None, forms


def is_name_refined_or_tied_elsewhere(clean_text, name, exclude_pos):
    """True if `name` (a parameter name attached to a bare, locally-
    unrefined coordinate/length -- e.g. 'qq' in 'x qq 0.123') is '@'-refined
    or Get()-tied to ANYWHERE ELSE in the whole file's cleaned text.

    Exists because a bare value's OWN occurrence poses no drift risk by
    itself (see check_symmetry_constraints' "already tautologically
    consistent" reasoning) -- but TOPAS scopes parameters by NAME across
    the entire file: 'x qq 0.123' elsewhere refined via a second 'qq @
    0.123' declaration, or tied into via 'something = Get(qq);', moves
    THIS occurrence too, silently reintroducing exactly the drift risk the
    bare-value case is otherwise correctly exempt from. `exclude_pos` is
    the char offset of the coordinate's OWN name token (from extract_
    keyword_form's match_start_offset), excluded so this occurrence isn't
    mistaken for a second, independent one.

    Deliberately whole-file (not str-block-scoped): a parameter name is a
    single flat namespace across the entire .inp, not scoped to its str
    block (TOPAS itself enforces this -- see check_symmetry_constraints'
    own "same parameter name" comment) -- a refine/tie against this name
    anywhere, even in a different phase, still causes drift here.
    """
    if not name:
        return False
    for m in re.finditer(r"@\s*" + re.escape(name) + r"\b", clean_text):
        if m.start() != exclude_pos:
            return True
    for m in re.finditer(r"\bGet\(\s*" + re.escape(name) + r"\s*\)", clean_text):
        return True
    return False


def check_symmetry_constraints(clean_text, text_with_values, issues):
    """
    Validate that an existing .inp's site coordinates, ADPs (u11..u23), and
    lattice parameters actually implement the constraints their own
    declared space group requires -- e.g. flag a site coordinate refined
    independently (bare or '@') when site symmetry requires it tied to
    another via 'y = Get(x);', a lattice length refined independently when
    the crystal system requires 'b = Get(a);', or an ADP tensor component
    that isn't correctly tied/zeroed per the site's Wyckoff position.
    Raised directly by the user (TOPAS-Academic's author): "if 'y=Get(x);'
    is necessary and the INP file tries to refine on the y coordinate
    independently, then throw a warning" (coordinates/lattice), followed by
    "Ensure that warnings are given if ADP constraints are invalid
    depending on the Wyckoff position" (ADPs).

    The ADP check (symmetry_utils.classify_adps -- see its own docstring)
    differs from the coordinate/lattice checks in one important way: a
    coordinate's required 'fixed' value is *derived from that same
    coordinate's own written number* (see resolve_site_coordinates), so a
    bare value can never numerically mismatch it -- only '@'-refining it is
    a real risk. An ADP's required value is NOT derived from its own
    written number -- it's derived purely from the site's POSITION
    stabilizer, entirely independent of whatever u_ij value happens to be
    written. So a bare ADP value that's numerically wrong (e.g. 'u12 0.02'
    when site symmetry requires 'u12' fixed at 0, or requires it equal to
    'u11/2' but the written number doesn't match) is a genuine static data
    error, flagged regardless of refinement status -- not a tautology like
    the coordinate case, and not gated behind "is anything actually being
    refined."

    Reuses the exact same crystallography engine as cif_to_str.py
    (symmetry_utils.py) -- classify_coordinates for per-site Wyckoff
    constraints, classify_crystal_system/ANGLE_CONSTRAINTS_BY_SYSTEM/
    LENGTH_TIES_BY_SYSTEM for lattice-parameter constraints -- run here in
    the opposite direction: instead of generating correct syntax from a
    CIF, it parses the .inp's OWN already-written syntax and compares it
    against what the space group requires.

    Space-group operators are resolved via symmetry_utils.resolve_sg_operators
    (TOPAS's own sgcom6.exe / sg/ database) -- an .inp file never carries its
    own operator list the way a CIF can, so this is the only source here,
    not a fallback. Needs TOPAS_DIR; silently produces no findings (not an
    error) if it's unavailable, matching this script's existing degrade-
    gracefully pattern for the macro-arity/keyword-typo checks when the live
    install isn't reachable.

    Built-in lattice-parameter macros (Cubic/Tetragonal/Hexagonal/Trigonal/
    Rhombohedral -- see LATTICE_MACRO_SYSTEMS) already implement the correct
    ties internally; a str block using one is recognized and skipped for
    the literal a/b/c/al/be/ga checks, but cross-checked against the
    space group's own computed crystal system -- e.g. Cubic() called on a
    space group that's actually tetragonal is flagged, since that macro
    would incorrectly force a=b=c on a lattice that doesn't have that
    symmetry.

    Scoping deliberately kept conservative to avoid false positives on a
    static, non-expression-evaluating checker:
      - A site is only checked if all three of its x/y/z resolve to a
        concrete number from the text alone (bare/@ value, or a simple
        'Get(other)[+-offset];' tie to an already-known coordinate) --
        anything else (equations referencing prm names, external
        parameters, etc.) is silently skipped, not guessed at.
      - A coordinate the space group actually leaves FREE is never flagged
        for being written as a fixed/bare value -- deliberately holding a
        free coordinate fixed during a refinement stage is normal practice,
        not a bug.
      - 'complex' site-symmetry constraints (see classify_coordinates) are
        skipped -- this checker's simple per-coordinate tie model can't
        validate them either way.
      - The rhombohedral-vs-hexagonal-axes disambiguation (see
        symmetry_utils.determine_length_ties) is resolved from the .inp's
        own explicit al/be/ga values when present; a completely absent 'ga'
        under a hexagonal/trigonal space group is flagged regardless of
        which axes setting was intended, since it silently defaults to
        TOPAS's 90 rather than the required 120 either way.
      - A coordinate written as a bare/'@' independent value is only
        flagged if something can actually move it away from the tie: the
        coordinate itself is '@'-refined, or the coordinate it should track
        is. A bare value that's numerically already correct (which it
        always is, tautologically -- see 'fixed' below) but never refined
        poses no real drift risk, so isn't flagged. A written equation that
        doesn't match the required tie IS always flagged regardless of
        refinement status, since that's an unambiguous structural mismatch.
      - For the 'fixed' case specifically: the required constant is derived
        directly from the coordinate's OWN resolved value, so a bare form
        can never numerically mismatch it (this isn't a gap -- it's
        tautological, not worth checking). Only '@'-refining a coordinate
        the space group fixes at an exact constant is flagged.
      - This checker is numerically-, not symbolically-, driven: it derives
        "what does site symmetry require" FROM the coordinates' own
        resolved values, the same way cif_to_str.py does from a CIF. A
        badly-wrong tie equation (e.g. the correct target with a wrong
        offset) can shift the resolved point enough that it no longer sits
        on the intended special position at all -- in that case this
        checker sees an ordinary general position (nothing to flag), not a
        "wrong tie" (confirmed with a deliberate test: 'y = Get(x) + 0.1;'
        where the true tie has zero offset produced no warning, because the
        resulting point genuinely isn't on the 3-fold axis anymore). This
        checker catches the *independent-refinement* class of mistake
        reliably (the literal case the user described); a wrong-but-still-
        on-the-special-position tie (e.g. tied to the correct target with
        the right offset except a wrong SIGN) is also caught, since that's
        a direct GET_TIE_RE mismatch against the required form -- it's only
        the offset-shifts-the-point-off-symmetry class that can slip past.

    Flagged as warnings throughout -- this is a heuristic structural check
    against a static-text parse, not a TOPAS-equivalent evaluator; verify
    manually, the same standard as every other check in this script.
    """
    str_blocks = find_str_blocks(clean_text)
    if not str_blocks:
        return

    def get_symops(symbol):
        if symbol not in _SG_OPERATOR_CACHE:
            symops, _header, _msg = symmetry_utils.resolve_sg_operators(symbol)
            _SG_OPERATOR_CACHE[symbol] = symops
        return _SG_OPERATOR_CACHE[symbol]

    for content_start, content_end in str_blocks:
        block_clean = clean_text[content_start:content_end]
        block_values = text_with_values[content_start:content_end]

        sg_m = re.search(r"\bspace_group\b\s*(\"[^\"]*\"|\S+)", block_values)
        if not sg_m:
            continue
        symbol = sg_m.group(1).strip('"')
        if not symbol:
            continue

        symops = get_symops(symbol)
        if not symops:
            continue  # unresolvable symbol or TOPAS_DIR unavailable -- nothing to check against

        system = symmetry_utils.classify_crystal_system(symops)

        # Preamble = text before the first `site` keyword, where lattice
        # parameters are conventionally declared -- scoping the a/b/c/al/be/ga
        # search here (rather than the whole block) avoids an unrelated
        # standalone token happening to be literally named "a"/"b"/"c" deep
        # inside a site/equation section from being misread as the lattice
        # parameter (a real false-positive risk for such short names).
        first_site_m = re.search(r"\bsite\b", block_clean)
        preamble_end = first_site_m.start() if first_site_m else len(block_clean)
        preamble = block_clean[:preamble_end]

        macro_m = re.search(r"\b(Cubic|Tetragonal|Hexagonal|Trigonal|Rhombohedral)\s*\(", preamble)
        if macro_m:
            macro_name = macro_m.group(1)
            allowed_systems = LATTICE_MACRO_SYSTEMS[macro_name]
            if system not in allowed_systems:
                issues.append(
                    ("warning", line_of(clean_text, content_start + macro_m.start()),
                     f"'{macro_name}(...)' is used for phase with space_group {symbol!r}, but that "
                     f"space group's own symmetry resolves to crystal system '{system}', not what "
                     f"'{macro_name}' implements -- verify this is the intended macro (a mismatched "
                     f"one can force an incorrect a=b=c/a=b-style constraint the real lattice "
                     f"doesn't have).")
                )
        else:
            length_ties = dict(symmetry_utils.LENGTH_TIES_BY_SYSTEM.get(system, {}))
            angle_reqs = dict(symmetry_utils.ANGLE_CONSTRAINTS_BY_SYSTEM.get(system, {}))

            if system == "hexagonal_or_trigonal":
                al_form = extract_keyword_form(preamble, "al")
                be_form = extract_keyword_form(preamble, "be")
                ga_form = extract_keyword_form(preamble, "ga")
                explicit_vals = {}
                for name, form in (("al", al_form), ("be", be_form), ("ga", ga_form)):
                    if form and form[0] == "value":
                        explicit_vals[name] = form[2]
                if len(explicit_vals) == 3:
                    is_hex_axes = (abs(explicit_vals["al"] - 90) < 0.05
                                   and abs(explicit_vals["be"] - 90) < 0.05
                                   and abs(explicit_vals["ga"] - 120) < 0.05)
                    is_rhomb_axes = (abs(explicit_vals["al"] - explicit_vals["be"]) < 0.05
                                      and abs(explicit_vals["be"] - explicit_vals["ga"]) < 0.05)
                    if not is_hex_axes and is_rhomb_axes:
                        length_ties["c"] = "a"
                if ga_form is None:
                    issues.append(
                        ("warning", line_of(clean_text, content_start),
                         f"space_group {symbol!r} resolves to a hexagonal/trigonal crystal system, "
                         f"which requires 'ga' fixed at 120 degrees -- but 'ga' is absent from this "
                         f"str block, so TOPAS will silently default it to 90 instead. Add 'ga 120' "
                         f"explicitly, or use the Hexagonal()/Trigonal() (or Rhombohedral(), if this "
                         f"is meant to be the rhombohedral-axes setting) macro instead.")
                    )

            for dep, indep in length_ties.items():
                form = extract_keyword_form(preamble, dep)
                if form is None:
                    continue
                tie_m = GET_TIE_RE.match(form[1]) if form[0] == "equation" else None
                # A length tie must be the exact bare form ('c = Get(a);') --
                # no negation, multiplier, or offset -- since the crystal
                # system requires equality, not a scaled/shifted relationship.
                ok = (bool(tie_m) and not tie_m.group("neg") and not tie_m.group("mul_x")
                      and not tie_m.group("mul_j") and not tie_m.group("off_sign")
                      and tie_m.group("name") == indep)
                if ok:
                    continue
                # Same refinement-status reasoning as the site-coordinate
                # tie check above: a bare independent length poses no drift
                # risk unless something can actually move -- including via a
                # distant '@'-refine or Get()-tie against its own or the
                # independent length's parameter NAME elsewhere in the file
                # (see is_name_refined_or_tied_elsewhere).
                if form[0] == "value" and form[1] != "@":
                    indep_form = extract_keyword_form(preamble, indep)
                    indep_refined = indep_form is not None and indep_form[0] == "value" and indep_form[1] == "@"
                    this_name_elsewhere = is_name_refined_or_tied_elsewhere(
                        clean_text, form[3], content_start + form[-1])
                    indep_name_elsewhere = indep_form is not None and indep_form[0] == "value" and \
                        is_name_refined_or_tied_elsewhere(clean_text, indep_form[3], content_start + indep_form[-1])
                    if not indep_refined and not this_name_elsewhere and not indep_name_elsewhere:
                        continue
                kind_desc = f"'{form[0]}'" if form[0] == "equation" else f"an independent {form[0]} ('{form[1] + ' ' if form[1] else ''}{form[2]}')" if form[0] == "value" else form[0]
                issues.append(
                    ("warning", line_of(clean_text, content_start + form[-1]),
                     f"'{dep}' is required to equal '{indep}' for space_group {symbol!r} "
                     f"(crystal system '{system}'), but is written as {kind_desc} rather than "
                     f"'{dep} = Get({indep});' -- refinement could pull them apart, violating "
                     f"the space group's own symmetry.")
                )

            for name, expected in angle_reqs.items():
                if expected != 90:
                    continue
                form = extract_keyword_form(preamble, name)
                if form and form[0] == "value" and abs(form[2] - expected) > 0.05:
                    issues.append(
                        ("warning", line_of(clean_text, content_start + form[-1]),
                         f"'{name} {form[2]:g}' contradicts space_group {symbol!r} (crystal system "
                         f"'{system}'), which requires '{name}' fixed at {expected} degrees -- "
                         f"verify manually.")
                    )

        str_scope = resolve_str_scope_values(preamble)
        for name, site_slice, site_pos in find_sites(block_clean):
            point, forms = resolve_site_coordinates(site_slice, outer_known=str_scope)
            if point is None:
                continue
            stabilizer = symmetry_utils.find_stabilizer(point, symops, 0.0015)
            constraint = symmetry_utils.classify_coordinates(point, stabilizer)
            for coord in ("x", "y", "z"):
                kind = constraint[coord]
                form = forms[coord]
                if kind[0] in ("free", "complex") or form is None:
                    continue
                line_no = line_of(clean_text, content_start + site_pos)
                if kind[0] == "fixed":
                    # kind[1] is derived directly from this same coordinate's
                    # own resolved value (see resolve_site_coordinates), so a
                    # bare/'value'-form number can never numerically mismatch
                    # it -- the only real risk is '@' actively refining it
                    # away from the required exact constant.
                    if form[0] == "value" and form[1] == "@":
                        issues.append(
                            ("warning", line_no,
                             f"Site '{name}': '{coord}' is refined ('@') independently, but site "
                             f"symmetry under space_group {symbol!r} fixes it at an exact value "
                             f"({kind[1]:.6g}) -- refining it risks drifting off the required "
                             f"special-position value. Consider a bare fixed value instead.")
                        )
                    elif form[0] == "value" and form[3] is not None and \
                            is_name_refined_or_tied_elsewhere(clean_text, form[3], content_start + site_pos + form[-1]):
                        # Bare here, but this same parameter NAME is '@'-refined
                        # or Get()-tied somewhere else in the file -- TOPAS
                        # enforces one value per name across the whole file, so
                        # this occurrence drifts too even though nothing on
                        # this line looks refined.
                        issues.append(
                            ("warning", line_no,
                             f"Site '{name}': '{coord}' is a bare value named '{form[3]}', but that "
                             f"parameter name is '@'-refined or Get()-tied elsewhere in this file -- "
                             f"site symmetry under space_group {symbol!r} fixes '{coord}' at an exact "
                             f"value ({kind[1]:.6g}), and TOPAS enforces one shared value per parameter "
                             f"name, so this occurrence will drift with the other one.")
                        )
                elif kind[0] == "tied":
                    _, other, sign, offset = kind
                    matches = False
                    if form[0] == "equation":
                        tie_m = GET_TIE_RE.match(form[1])
                        # A Wyckoff position tie is always a pure sign flip
                        # plus offset (classify_coordinates never derives a
                        # scaling factor) -- a written tie WITH a multiplier
                        # can never be the required relationship, so it's
                        # excluded here rather than silently accepted.
                        if tie_m and not tie_m.group("mul_x") and not tie_m.group("mul_j"):
                            ref_other = tie_m.group("name")
                            ref_sign = -1 if tie_m.group("neg") else 1
                            ref_offset = float(Fraction(tie_m.group("off_val"))) if tie_m.group("off_sign") else 0.0
                            if tie_m.group("off_sign") == "-":
                                ref_offset = -ref_offset
                            matches = (ref_other == other and ref_sign == sign
                                       and abs(ref_offset - offset) < 0.0015)
                    if matches:
                        continue

                    other_form = forms.get(other)

                    # A coordinate written as a PLAIN NUMERIC CONSTANT (not a
                    # Get() tie) is tautologically consistent with whatever
                    # classify_coordinates derived here -- that derivation
                    # used THIS coordinate's own resolved value (via
                    # resolve_site_coordinates) in the first place, so a
                    # fixed number can never numerically contradict a
                    # requirement computed from itself. A real bug found
                    # this way on two real files (test_examples/clay.inp,
                    # test_examples/k-factor/k-factor.inp -- confirmed and
                    # diagnosed directly by the user, TOPAS-Academic's
                    # author): both write BOTH tied coordinates as
                    # independent plain-constant equations (e.g.
                    # 'x =1/3; y =2/3;', numerically consistent with a
                    # required 'y = -Get(x);' tie since 2/3 = -1/3 mod 1)
                    # rather than the literal Get()-tie syntax -- this
                    # checker flagged them anyway, since only the exact
                    # 'y = -Get(x);' form was ever accepted as "matching". A
                    # plain constant can never drift (recomputed identically
                    # every iteration), so this is always safe to skip,
                    # unconditionally -- no refinement-status gate needed.
                    if form[0] == "equation" and parse_plain_numeric_equation(form[1]) is not None:
                        continue

                    # Two keywords given the SAME parameter name are a
                    # TOPAS kernel-enforced invariant -- "Parameters with
                    # the same name must have the same value... an
                    # exception is thrown if [they] were defined with
                    # differing values" (Technical_Reference.pdf, section
                    # 2.4 "Parameter constraints") -- so if this coordinate
                    # and 'other' share a name (given directly, e.g.
                    # 'x qq 0.123 y qq 0.123', or via a bare -- not Get() --
                    # equation reference, e.g. 'y = qq;'), they can never
                    # numerically diverge no matter how the shared
                    # parameter is later refined. This only ever expresses
                    # a sign=+1 (equal-value) relationship, since a shared
                    # name forces identical values, never a sign flip --
                    # safe by the same point-derivation tautology as above.
                    this_name = form[3] if form[0] == "value" else None
                    other_name = other_form[3] if other_form is not None and other_form[0] == "value" else None
                    if this_name is not None and this_name == other_name:
                        continue
                    if form[0] == "equation" and other_name is not None and form[1].strip() == other_name:
                        continue

                    # A wrong/mismatched equation is a real structural bug
                    # regardless of refinement status -- always flag it. A
                    # bare independent value, though, is by construction
                    # already numerically consistent with the tie (it's
                    # exactly what the tie was derived from) and poses zero
                    # drift risk unless something can actually move: either
                    # this coordinate itself is '@'-refined, or the
                    # coordinate it should track ('other') is -- only then
                    # can the two actually separate during refinement.
                    other_refined = other_form is not None and other_form[0] == "value" and other_form[1] == "@"
                    this_refined = form[0] == "value" and form[1] == "@"
                    # A bare value's own NAME can also carry drift risk if
                    # that same name is '@'-refined or Get()-tied elsewhere
                    # in the file (see is_name_refined_or_tied_elsewhere) --
                    # TOPAS enforces one shared value per parameter name, so
                    # a second, distant refine/tie against this coordinate's
                    # name (or the tied-to 'other' coordinate's name) moves
                    # this occurrence too.
                    this_name_elsewhere = form[0] == "value" and \
                        is_name_refined_or_tied_elsewhere(clean_text, form[3], content_start + site_pos + form[-1])
                    other_name_elsewhere = other_form is not None and other_form[0] == "value" and \
                        is_name_refined_or_tied_elsewhere(clean_text, other_form[3],
                                                           content_start + site_pos + other_form[-1])
                    if form[0] == "value" and not this_refined and not other_refined \
                            and not this_name_elsewhere and not other_name_elsewhere:
                        continue
                    sign_str = "" if sign == 1 else "-"
                    expr = f"{sign_str}Get({other})"
                    offset_mod1 = offset % 1.0
                    if offset_mod1 > 1e-6:
                        off_snapped, off_exact = symmetry_utils.snap_to_fraction(offset_mod1)
                        off_disp = f"{off_exact.numerator}/{off_exact.denominator}" if off_exact else f"{off_snapped:.6g}"
                        expr += f" + {off_disp}" if offset >= 0 else f" - {off_disp}"
                    issues.append(
                        ("warning", line_no,
                         f"Site '{name}': '{coord}' is written as "
                         f"{'an independent ' + form[0] if form[0] == 'value' else 'a different equation'} "
                         f"but site symmetry under space_group {symbol!r} requires it tied to "
                         f"'{coord} = {expr};' -- refining independently risks violating that symmetry.")
                    )

            adp_forms = {n: extract_keyword_form(site_slice, n) for n in symmetry_utils.ADP_NAMES}
            if any(f is not None for f in adp_forms.values()):
                adp_constraint = symmetry_utils.classify_adps(stabilizer)
                known_adp = {n: f[2] for n, f in adp_forms.items() if f and f[0] == "value"}
                for adp_name in symmetry_utils.ADP_NAMES:
                    kind = adp_constraint[adp_name]
                    form = adp_forms[adp_name]
                    if kind[0] == "free" or form is None:
                        continue
                    line_no = line_of(clean_text, content_start + site_pos)

                    if kind[0] == "fixed":
                        # Unlike a coordinate's 'fixed' value, an ADP's
                        # required value (always exactly 0 here) does NOT
                        # come from this same component's own written
                        # number -- it's derived purely from the site's
                        # POSITION stabilizer, independent of whatever u_ij
                        # value happens to be written. So a bare nonzero
                        # value really is a genuine static mismatch here,
                        # not a tautology -- flag it regardless of
                        # refinement status.
                        if form[0] == "value":
                            if form[1] == "@":
                                issues.append(
                                    ("warning", line_no,
                                     f"Site '{name}': '{adp_name}' is refined ('@') independently, but "
                                     f"site symmetry under space_group {symbol!r} fixes it at exactly 0 "
                                     f"-- refining it risks a nonzero, symmetry-violating value.")
                                )
                            elif abs(form[2]) > 1e-6:
                                issues.append(
                                    ("warning", line_no,
                                     f"Site '{name}': '{adp_name} {form[2]:g}' contradicts site symmetry "
                                     f"under space_group {symbol!r}, which requires '{adp_name}' fixed at "
                                     f"exactly 0.")
                                )
                        elif form[0] == "equation":
                            plain = parse_plain_numeric_equation(form[1])
                            if plain is None or abs(plain) > 1e-6:
                                issues.append(
                                    ("warning", line_no,
                                     f"Site '{name}': '{adp_name}' is written as an equation, but site "
                                     f"symmetry under space_group {symbol!r} requires it fixed at exactly 0 "
                                     f"-- verify manually.")
                                )
                    elif kind[0] == "tied":
                        terms = kind[1]
                        if form[0] == "equation":
                            parsed = parse_adp_tie_expression(form[1])
                            if not adp_terms_match(parsed, terms):
                                issues.append(
                                    ("warning", line_no,
                                     f"Site '{name}': '{adp_name}' is written as a different/unrecognized "
                                     f"equation, but site symmetry under space_group {symbol!r} requires "
                                     f"'{adp_name} = {symmetry_utils.format_adp_tie(terms)};'.")
                                )
                        elif form[0] == "value":
                            resolvable = all(other in known_adp for _c, other in terms)
                            if resolvable:
                                required_val = sum(c * known_adp[other] for c, other in terms)
                                if abs(form[2] - required_val) > max(1e-6, 0.01 * abs(float(required_val))):
                                    issues.append(
                                        ("warning", line_no,
                                         f"Site '{name}': '{adp_name} {form[2]:g}' doesn't match the "
                                         f"site-symmetry-required value ({float(required_val):.6g}, from "
                                         f"'{symmetry_utils.format_adp_tie(terms)}') under space_group {symbol!r}.")
                                    )
                                    continue
                            this_refined = form[1] == "@"
                            other_refined = any(
                                adp_forms.get(other) is not None and adp_forms[other][0] == "value"
                                and adp_forms[other][1] == "@"
                                for _c, other in terms
                            )
                            # Same name-scoped drift risk as the coordinate
                            # 'tied' case above: a bare ADP value (or one of
                            # its tie terms) whose NAME is '@'-refined or
                            # Get()-tied elsewhere in the file drifts too.
                            this_name_elsewhere = is_name_refined_or_tied_elsewhere(
                                clean_text, form[3], content_start + site_pos + form[-1])
                            other_name_elsewhere = resolvable and any(
                                adp_forms.get(other) is not None and adp_forms[other][0] == "value"
                                and is_name_refined_or_tied_elsewhere(
                                    clean_text, adp_forms[other][3], content_start + site_pos + adp_forms[other][-1])
                                for _c, other in terms
                            )
                            if this_refined or (resolvable and other_refined) \
                                    or this_name_elsewhere or other_name_elsewhere:
                                issues.append(
                                    ("warning", line_no,
                                     f"Site '{name}': '{adp_name}' is written as an independent value, "
                                     f"but site symmetry under space_group {symbol!r} requires it tied to "
                                     f"'{adp_name} = {symmetry_utils.format_adp_tie(terms)};' -- refining "
                                     f"independently risks violating that symmetry.")
                                )


def check_bom(text, issues):
    """
    A UTF-8 byte-order-mark (BOM, bytes EF BB BF, decoded as a leading
    U+FEFF character) makes TOPAS's parser choke on the very first token --
    e.g. "process_times" becomes unparseable, and TOPAS reports "unknown or
    misplaced keyword" at LINE 1 even though the file looks completely
    normal in a text editor (most editors render the BOM as invisible, so
    there's no visual clue). A hard error, not a heuristic warning: there is
    no legitimate TOPAS file that should start with a BOM.

    Confirmed as a real, recurring problem directly by the user (TOPAS-
    Academic's author): test_examples/simple.inp picked up a BOM at least
    twice during this skill's development despite being fixed each time --
    apparently reintroduced by an external editor/tool between edits (this
    skill's own scripts write plain UTF-8 without a BOM throughout, so it
    isn't the source). Checking for it mechanically here means it gets
    caught before a run, rather than relying on remembering to check by hand
    each time.
    """
    if text.startswith(chr(0xFEFF)):
        issues.append(
            ("error", 1,
             "File starts with a UTF-8 byte-order-mark (BOM). TOPAS reads this as part "
             "of the first token, breaking it -- reported as 'unknown or misplaced "
             "keyword' at LINE 1. Most text editors render the BOM as invisible, so the "
             "file can look completely normal while still failing to load. Strip it by "
             "re-saving as UTF-8 without a BOM, e.g. in PowerShell: "
             "[System.IO.File]::WriteAllText($path, [System.IO.File]::ReadAllText($path), "
             "(New-Object System.Text.UTF8Encoding $false))")
        )


def check_file(path, keywords, library_arities, library_bodiless, single_arg_keywords, e_arg_keywords, extra_text=None):
    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()
    if extra_text:
        # Mirrors tc.exe's own documented command-line convention
        # (references/20-miscellaneous.md, "Batch mode operation"):
        # 'tc file.inp "macro FILE { file.xy }"' appends the quoted text
        # to the loaded file -- used for a #define flag gating an #ifdef
        # branch, or injecting a macro/local the file itself calls but
        # doesn't define (e.g. the shared 'aac$' auto-testing macro used
        # throughout this corpus's own test-runner convention). Appending
        # at the END (rather than needing to insert it at any particular
        # point) is safe: strip_inactive_ifdef_branches already does its
        # own file-wide #define scan before evaluating any branch, so a
        # #define appearing after its #ifdef still takes effect, matching
        # real TOPAS behavior (confirmed by that function's own docstring
        # -- not a strict single top-to-bottom pass requiring definition-
        # before-use).
        text = text + "\n" + extra_text + "\n"
    issues = []
    check_bom(text, issues)
    clean = strip_comments_and_strings(text)
    clean = strip_inactive_ifdef_branches(clean)
    clean = strip_opaque_blocks(clean)
    check_braces_and_parens(clean, issues)
    check_missing_semicolons(clean, issues)
    check_missing_colon_before_value(clean, issues)

    # Merge in every macro name (exact case) known from the bundled .inc
    # library plus this file's own macro definitions -- these are real,
    # correctly-cased identifiers and belong in the "known good" set used
    # for keyword-typo checking, not just the low-level bracket-keyword
    # list from 21-keyword-index.md (see check_keyword_typos' docstring
    # note for why this matters).
    file_arities = harvest_macro_arities(clean)
    merged_arities = {k: set(v) for k, v in library_arities.items()}
    for name, counts in file_arities.items():
        merged_arities.setdefault(name, set()).update(counts)

    file_bodiless = harvest_bodiless_macro_names(clean)
    # DEFINER_KEYWORDS ("macro", "prm", "local", "for", "inp_text", "fn") plus
    # "load" are real, low-level TOPAS structural keywords that the
    # bracket-notation harvest from the reference chapters doesn't capture
    # (they're documented as language constructs, not [keyword ...] entries).
    # Confirmed real: "load use_hklm { ... }" (references/20-miscellaneous.md,
    # "Defining hkls using use_hklm") and "macro Exclude { load exclude }"
    # (topas.inc). Without these, any real file with e.g. a macro definition
    # or a `load` statement right after a space_group line produces a false
    # positive from check_space_group_symbol below (found and fixed during
    # development: the full example corpus flagged exactly three distinct
    # false positives -- 'load', 'local', 'macro' -- until this was added).
    keywords_plus_macros = keywords | set(merged_arities.keys()) | library_bodiless | file_bodiless | DEFINER_KEYWORDS | {"load"}

    check_keyword_typos(clean, keywords_plus_macros, issues)
    check_macro_arity(clean, merged_arities, issues)
    check_single_string_arg_keywords(clean, keywords_plus_macros, single_arg_keywords, issues)
    check_single_e_arg_keywords(clean, keywords_plus_macros, e_arg_keywords, issues)
    check_xyz_near_one_third(clean, issues)
    min_max_macro_names = harvest_macros_with_min_max_body(clean)
    check_prm_local_missing_min_max(clean, min_max_macro_names, issues)

    # Mirrors `clean`'s exact pipeline (strip_inactive_ifdef_branches can
    # shrink certain lines, e.g. directive lines themselves become "" rather
    # than space-padded -- see that function's own blanking logic), just
    # swapping the first step so quoted-string contents survive. Needed so
    # offsets computed against `clean` (e.g. a str-block extent) can be
    # sliced directly out of this text and still land on the same content.
    clean_with_values = strip_opaque_blocks(strip_inactive_ifdef_branches(strip_comments_only(text)))
    check_symmetry_constraints(clean, clean_with_values, issues)

    issues.sort(key=lambda x: x[1])
    return issues


def resolve_inp_path(p):
    """A bare path with no extension (e.g. 'test_examples/clay') resolves
    the same way tc.exe itself does -- try it as-is first, then with a
    '.inp'/'.INP' extension appended. Returns the resolved path (which may
    still not exist -- callers report that themselves)."""
    if os.path.isfile(p):
        return p
    for ext in (".inp", ".INP"):
        if os.path.isfile(p + ext):
            return p + ext
    return p


def parse_cli_entries(argv):
    """
    Returns a list of (path, extra_text_or_None), resolving bare
    extensionless paths (see resolve_inp_path) and pairing a trailing
    non-path token with the file argument immediately before it -- this
    is tc.exe's own command-line convention (see check_file's docstring
    note and references/20-miscellaneous.md "Batch mode operation"):
    'tc file.inp "macro FILE { file.xy }"' or 'tc file "#define foo"'.
    A token is treated as extra text only when it does NOT itself resolve
    to an existing file or directory -- a directory can't take extra
    text (it expands to many files, there's no single file to append to),
    so extra text right after a directory argument is treated as its own
    (almost certainly non-existent) path instead of silently dropped.
    """
    entries = []
    pending_idx = None
    for tok in argv:
        if os.path.isdir(tok):
            entries.append((tok, None))
            pending_idx = None
            continue
        resolved = resolve_inp_path(tok)
        if os.path.isfile(resolved):
            entries.append((resolved, None))
            pending_idx = len(entries) - 1
            continue
        if pending_idx is not None:
            path, existing = entries[pending_idx]
            combined = (existing + "\n" + tok) if existing else tok
            entries[pending_idx] = (path, combined)
        else:
            entries.append((tok, None))
            pending_idx = None
    return entries


def collect_inp_files(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, fnames in os.walk(p):
                for fname in fnames:
                    if fname.lower().endswith(".inp"):
                        files.append(os.path.join(root, fname))
        else:
            files.append(p)
    return sorted(files)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    keywords = load_keyword_set(KEYWORD_INDEX_PATH)
    if not keywords:
        print(f"Warning: could not load keyword index from {KEYWORD_INDEX_PATH}; "
              f"typo-checking will be skipped.", file=sys.stderr)

    single_arg_keywords = load_single_string_arg_keywords(REFERENCES_DIR) - SINGLE_ARG_FALSE_POSITIVES
    e_arg_keywords = {k for k in load_single_e_arg_keywords(REFERENCES_DIR) if len(k) >= MIN_E_ARG_CHECK_LEN}

    library_arities, library_bodiless = load_library_macro_arities()
    if not library_arities:
        if os.environ.get("TOPAS_DIR", "").strip():
            print(f"Warning: TOPAS_DIR is set but no topas.inc was found under it "
                  f"({MACRO_LIB_DIR}); macro-arity checking will be skipped.", file=sys.stderr)
        else:
            print("Warning: TOPAS_DIR is not set, so this skill has no macro library to check "
                  "arities against (it no longer bundles a copy -- see 'Locating your TOPAS "
                  "installation' in SKILL.md). Set TOPAS_DIR to your TOPAS install root to "
                  "enable macro-arity checking; other checks still run normally.", file=sys.stderr)
    elif MACRO_LIB_FROM_LIVE_INSTALL:
        print(f"(Using the live TOPAS install's own macro library at {MACRO_LIB_DIR}, "
              f"via TOPAS_DIR.)", file=sys.stderr)

    entries = []
    for path, extra_text in parse_cli_entries(sys.argv[1:]):
        if os.path.isdir(path):
            entries.extend((f, None) for f in collect_inp_files([path]))
        else:
            entries.append((path, extra_text))
    if not entries:
        print("No .inp files found for the given path(s).")
        sys.exit(1)

    had_error = False
    for path, extra_text in entries:
        issues = check_file(path, keywords, library_arities, library_bodiless, single_arg_keywords, e_arg_keywords, extra_text=extra_text)
        errors = [i for i in issues if i[0] == "error"]
        warnings = [i for i in issues if i[0] == "warning"]
        if errors:
            had_error = True
        status = "FAIL" if errors else ("WARN" if warnings else "PASS")
        label = path if not extra_text else f"{path} [+cmdline: {extra_text!r}]"
        print(f"\n=== {label} [{status}] ===")
        if not issues:
            print("  No issues found.")
        for kind, lineno, msg in issues:
            tag = "ERROR" if kind == "error" else "warning"
            print(f"  line {lineno}: {tag}: {msg}")

    print(f"\n{len(entries)} file(s) checked.")
    sys.exit(1 if had_error else 0)


if __name__ == "__main__":
    main()
