#!/usr/bin/env python3
"""
check_inp_syntax.py -- A basic, heuristic syntax checker for TOPAS .inp files.

Catches thirteen classes of mistake before you hand a file to TOPAS:

  1. Unbalanced braces { } or parentheses ( )
  2. Equations ("= ... ;") that never reach a terminating semicolon before
     the enclosing scope changes or the file ends
  3. Any identifier that isn't a real TOPAS keyword or macro name (exact
     case), a name the file itself declares (prm/local/macro/site/...),
     or a bare token consumed by a keyword's own known multi-token
     argument grammar (z_matrix's atom labels, a parenthesized macro
     call's arguments) -- flagged whether or not it closely resembles a
     real keyword (a close resemblance gets "likely a typo of X"; no
     resemblance at all gets "likely a stray/leftover token"). Confirmed
     directly by the user (TOPAS-Academic's author): "An identifier must
     be a keyword or a macro. When a file is macro expanded then the
     identifier must be a keyword" -- no length floor, no fuzzy-match
     requirement to report something. Known names are harvested from
     bracket-notation keywords across every reference chapter, every
     macro definition (both 'macro Name(args) {}' and bodiless
     'macro Name {}' forms) in the bundled .inc library plus the file
     itself, and a small hand-verified supplemental list for real names
     that fall through both harvests.
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
  11. An ADP tensor component (u11..u23) or lattice parameter
      (a/b/c/al/be/ga) written as an independently refined value when the
      file's own declared space group requires it tied to another via a
      'Get()' equation (e.g. 'u22 = Get(u11);' for a site's ADP tensor, or
      'b = Get(a);' for a cubic cell) -- or fixed at an exact constant
      that's instead left '@'-refined. For ADPs specifically, a WRONG bare
      value (not just a refined one) is also flagged -- unlike a
      coordinate's required value, an ADP's required value doesn't come
      from its own written number, so a numeric mismatch is a genuine
      static error, not a tautology. Space-group operators are resolved
      via TOPAS's own sgcom6.exe/sg database (needs TOPAS_DIR; silently
      produces no findings if unavailable, like the macro-arity check's
      live-install fallback). See check_symmetry_constraints()'s own
      docstring for the full method and the built-in lattice-macro
      (Cubic/Tetragonal/Hexagonal/Trigonal/Rhombohedral) recognition.
      NOTE: site COORDINATE (x/y/z) constraint checking was built here
      and later explicitly REMOVED, directly at the request of the user
      (TOPAS-Academic's author) -- writing a coordinate independently
      (no '!') is itself the deliberate signal that a site should be
      treated as a general position, not a mistake worth flagging
      regardless of what numeric value it happens to hold. See
      check_symmetry_constraints()'s own docstring for the full story.
  12. A stray bare number sitting right after a keyword that takes NO
      value at all -- e.g. "str  123123" -- generalizing item 8 above from
      "a keyword that takes exactly one value" to "a keyword that takes
      zero". Found directly by the user (TOPAS-Academic's author) spotting
      it by eye in a macro-expanded file and pointing out this checker
      should already have caught it -- correct: item 3's identifier check
      never looked at it (numbers aren't identifier-shaped) and item 8
      only ever checked keywords that legitimately take one value first.
      See check_zero_arg_keywords()'s own docstring for exact scoping and
      the corpus verification behind it (including a real false-conflict
      exclusion for 'str' itself, and a real macro-argument-glossary false
      positive shared with topas_keyword_tree.py's own bracket scanner).
  13. A '@' (auto-name sigil) not immediately followed by a numeric value
      or '=' -- e.g. "scale @ a2.27742249e-05" (a stray letter prepended
      to a real number, corrupting it). Found directly by the user
      (TOPAS-Academic's author) immediately after item 12 above, in the
      same file: "The @ is corresponds to a unique name. The next item
      should be a number or an equal sign." See check_at_sigil_value()'s
      own docstring for exact scoping and the three real exceptions its
      own corpus regression sweep required (a bare '@'/'@name' as a
      macro-call argument, and a macro body that's just '@'/'@name').

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
# The optional '&' before the macro name (e.g. 'macro & CeV(c, v)') wraps
# the WHOLE expansion result in parens at call sites -- a real, distinct
# TOPAS macro-definition syntax (see expand_inp_macros.py, fixed for the
# same construct earlier). topas.inc's own CeV macro -- used constantly
# throughout the library -- is itself defined this way; without allowing
# for it here, CeV (and anything else defined with a leading '&') was
# silently invisible to this checker's own keyword/macro harvest, coming
# back as "not a recognized keyword, macro, or declared name" everywhere
# it was actually called.
MACRO_DEF_RE = re.compile(r"macro\s+&?\s*([A-Za-z_]\w*)\s*\(([^()]*)\)")
BODILESS_MACRO_DEF_RE = re.compile(r"macro\s+&?\s*([A-Za-z_]\w*)\s*\{")
# 'fn NAME(args) { ... }' user-defined functions -- same parameter-list
# shape as MACRO_DEF_RE, used by find_defined_names() to register a
# function's own parameter names as legitimate throughout its body.
FN_DEF_RE = re.compile(r"\bfn\s+([A-Za-z_]\w*)\s*\(([^()]*)\)")
TABLE_ROW_FUNC_RE = re.compile(r"^\|\s*([A-Za-z_][A-Za-z0-9_]*)\(", re.MULTILINE)
# A handful of equation functions in references/02-equation-operators-
# and-functions.md are documented as a bare 'Name(args)' signature line
# on its own (e.g. 'Constant(expression)', 'Bkg_at(x)') rather than a
# markdown table row -- TABLE_ROW_FUNC_RE alone misses these. Anchored to
# the WHOLE line (nothing else on it) so a function CALL embedded in a
# longer prose sentence or code example doesn't get mistaken for its own
# definition site.
BARE_FUNC_SIGNATURE_RE = re.compile(r"^([A-Za-z_]\w*)\([A-Za-z_#$][A-Za-z0-9_#$, ]*\)\s*(?::|$)", re.MULTILINE)
# A few low-level keywords are documented as a bare 'name E'/'name #'
# signature line with no surrounding brackets at all (e.g.
# 'lpsd_equitorial_sample_length_mm E', 'capillary_u_cm_inv E' in
# 21-keyword-index.md) -- neither BRACKET_KEYWORD_RE nor
# TABLE_ROW_FUNC_RE/BARE_FUNC_SIGNATURE_RE catch this form. Anchored to
# the whole line for the same reason as BARE_FUNC_SIGNATURE_RE.
BARE_KEYWORD_SIGNATURE_RE = re.compile(r"^([a-z][A-Za-z0-9_]{4,})\s+(?:!?[EN]|!?#\w*)\s*$", re.MULTILINE)

# A "type marker" placeholder in the manual's own bracket notation (see
# the longer note below on the sigil convention) -- NOT a keyword name,
# even though it's identifier-shaped. Used to tell keyword names apart
# from their own type annotations when several names are packed into one
# bracket (see extract_bracket_keyword_names()).
BRACKET_TYPE_MARKER_RE = re.compile(r"^(?:!?[EN]|!?#\w*|\$\w*|!?-?\d.*|\.\.\.|…)$")


def extract_bracket_keyword_names(inner_text):
    """Every keyword-shaped name inside one bracket's content, not just
    the first -- many manual entries pack several names into one bracket
    with type markers between them (e.g. '[pv_lor E  pv_fwhm E]',
    '[h1 E  h2 E  m1 E  m2 E]'), and the original single-capture harvest
    (a bare '\\[(\\w+)' regex) only ever saw the first ('pv_lor', 'h1'),
    silently missing the rest ('pv_fwhm', 'h2', 'm1', 'm2', ...) --
    confirmed as a real gap when 'pv_fwhm' (used constantly for pseudo-
    Voigt peak shapes) came back completely unrecognized in a real-corpus
    regression run after MIN_TYPO_CHECK_LEN was removed. Nested brackets
    (e.g. grs_interaction's own '[qi !E qj !E]') get walked too, since
    their own names are equally real, just an inner sub-argument rather
    than a top-level one."""
    names = []
    for tok in re.split(r"[\s,|\[\]]+", inner_text):
        tok = tok.strip()
        if not tok or BRACKET_TYPE_MARKER_RE.match(tok):
            continue
        if re.match(r"^[A-Za-z_]\w*$", tok):
            names.append(tok)
    return names

# No minimum length for typo-detection -- confirmed directly by the user
# (TOPAS-Academic's author): "An identifier must be a keyword or a macro.
# When a file is macro expanded then the identifier must be a keyword."
# A short, previous version of this checker skipped anything under 5
# characters to avoid noise from one/two-letter TOPAS tokens (a, b, al,
# be, ...) -- but those are all legitimately declared or consumed
# elsewhere (lattice-parameter keywords themselves, or the token right
# after a recognized keyword/macro call), so the length itself was never
# actually protecting against a real ambiguity; it was just hiding short,
# genuine mistakes (e.g. a stray leftover token like "eee" on its own
# line, 3 characters, previously invisible to this check both because of
# this length gate AND because it doesn't closely resemble any real
# keyword -- see the "no close match" handling in check_keyword_typos()).
MIN_TYPO_CHECK_LEN = 0

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

# The mirror image of SINGLE_ARG_FALSE_POSITIVES above: keywords that ARE
# genuinely zero-argument in every real usage, but load_zero_arg_keywords()
# drops them anyway because of a FALSE documented conflict -- a bracket
# entry elsewhere that LOOKS like a richer signature but is actually a
# different notation entirely, not really describing this keyword's own
# argument grammar. Populated and justified one at a time, same
# discipline as the set above; subtracted the opposite way (added to the
# harvest, not removed from it) at zero_arg_keywords' own computation
# site in main().
ZERO_ARG_KEYWORD_SUPPLEMENT = {
    "str",
    # references/21-keyword-index.md's alphabetical listing documents
    # '[str]...' as a clean bare entry (correctly harvested), but the SAME
    # file's "Data structures" schema section also has 'str' appearing as
    # part of '[str | dummy_str]...' inside Txdd's own child listing --
    # that's the schema's TYPE-ALTERNATION notation ("either str or
    # dummy_str is valid here"), not a statement about str's own argument
    # grammar, but BRACKET_FULL_RE's generic scan can't tell the two
    # notations apart, so the harvester's conflict-detection (correctly
    # cautious in general) drops 'str' here specifically as a false
    # positive. Confirmed zero-arg in every real corpus usage throughout
    # this whole skill's development -- 'str' never takes a following
    # value. Found directly from a real bug the user spotted by eye in a
    # macro-expanded file: a stray 'str  123123' (a leftover number with
    # nothing consuming it) passed this checker cleanly before this fix,
    # exactly the same class of miss check_single_e_arg_keywords was
    # built to catch for single-E-arg keywords, just for the zero-arg case.
    "dummy_str",
    # Same root cause and same fix as 'str' immediately above -- 'dummy_str'
    # only ever appears via that same '[str | dummy_str]...' alternation
    # entry, never as its own bare bracket line, so the raw harvest never
    # even considers it a candidate at all. Confirmed zero-arg the same
    # way 'str' is (a dummy_str block plays the identical structural role,
    # just excluded from contributing intensity).
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
OPAQUE_BLOCK_KEYWORDS = {
    "pdf_info",
    # Auto-generated correlation-matrix report blocks appended to the
    # file on refinement termination (references/21-keyword-index.md's
    # Data structures listing: "[A_matrix] [C_matrix] [A_matrix_normalized]
    # [C_matrix_normalized]") -- bare row-label names inside are whatever
    # hash-based auto-names macro expansion happened to generate that run
    # (e.g. 'bkg_rec28176AE3BB0_', 'm6a54dfe6_0'), never resolvable from
    # the raw, un-expanded source the way a real declared name is, so
    # they're display/report content, not parseable statement syntax --
    # found via a real false-positive flood in test_examples/simple.inp
    # once MIN_TYPO_CHECK_LEN was removed (see check_keyword_typos()).
    "A_matrix", "C_matrix", "A_matrix_normalized", "C_matrix_normalized",
}


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
        i = 0
        n = len(text)
        while i < n:
            if text[i] == "[":
                depth = 1
                j = i + 1
                while j < n and depth > 0:
                    if text[j] == "[":
                        depth += 1
                    elif text[j] == "]":
                        depth -= 1
                    j += 1
                inner = text[i + 1:max(j - 1, i + 1)]
                for name in extract_bracket_keyword_names(inner):
                    keywords.add(name)
                    # TOPAS documents many keywords with a trailing digit
                    # meaning "the first of possibly several numbered
                    # instances" (e.g. '[pdf_convolute1 E]',
                    # '[scale_phase_X1 E]', '[pdf_zero1 E]') -- bare,
                    # unnumbered usage (referring to the first/default
                    # instance) is valid and extremely common in real INP
                    # files, so register the digit-stripped base form too.
                    if name and name[-1].isdigit():
                        base = name.rstrip("0123456789")
                        if base:
                            keywords.add(base)
                i = j
            else:
                i += 1
        for m in TABLE_ROW_FUNC_RE.finditer(text):
            keywords.add(m.group(1))
        for m in BARE_FUNC_SIGNATURE_RE.finditer(text):
            keywords.add(m.group(1))
        for m in BARE_KEYWORD_SIGNATURE_RE.finditer(text):
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


# A whole line matching '[name]: description...' (e.g. '[r]: Distance in
# Å.', '[n1]: The closest n1 number of atoms...') is a macro-argument-
# glossary label, not a real TOPAS keyword -- the identical, already-
# confirmed data-quality issue topas_keyword_tree.py's own
# GLOSSARY_LINE_RE was built for (see that module's docstring: "using
# square brackets for macro arguments was a bad idea," confirmed
# directly by the user, TOPAS-Academic's own author). load_zero_arg_
# keywords() below is uniquely exposed to this, unlike its two siblings:
# a glossary bracket's OWN content (just the bare argument name, e.g.
# "r") is empty in exactly the same way a genuine zero-arg keyword's
# bracket is -- the description text sits AFTER the closing ']', outside
# BRACKET_FULL_RE's own capture -- so 'r'/'n1'/'n2' (real short glossary
# names from 13-rigid-bodies.md/06-macros-and-include-files.md) were
# silently harvested as if they were genuine bare TOPAS keywords, and
# then flagged real corpus files' own local prm/local names ('n !n1 0',
# a legitimate keyword-$name-value declaration, nothing to do with this
# glossary) as false positives -- found and fixed via this check's own
# curated-corpus regression sweep. The other two harvesters happen to be
# naturally immune (a glossary line's prose "rest" text never matches
# their own strict single-$-or-E-token shape, so it lands in
# `conflicting` instead of being wrongly added) -- this blanking step
# isn't needed there, only here.
GLOSSARY_LINE_RE = re.compile(r"^[ \t]*\[[^\n\]]*\]:.*$", re.MULTILINE)


def load_zero_arg_keywords(references_dir):
    """
    Harvest keywords whose bracket-notation signature is a BARE name and
    nothing else (e.g. '[str]', '[do_errors]', '[no_f11]') -- these take
    NO following value, name, or equation at all; TOPAS reads straight to
    the next real keyword/directive/macro/brace after one of these. Both
    load_single_string_arg_keywords() and load_single_e_arg_keywords()
    above already compute exactly this condition (`rest = m.group(2).
    strip()` being empty) and simply `continue` past it as "not relevant
    here" -- this is that same BRACKET_FULL_RE scan, just keeping what
    the other two throw away.

    Same conflict-detection as the other two harvesters: if the SAME
    keyword name is EVER documented elsewhere with a non-empty bracket
    signature, it's dropped from the result entirely, even if it also has
    a clean bare form elsewhere -- conflicting evidence means "don't
    trust this one."
    """
    zero_arg = set()
    conflicting = set()
    try:
        fnames = [f for f in os.listdir(references_dir) if f.lower().endswith(".md")]
    except OSError:
        return zero_arg

    for fname in fnames:
        fpath = os.path.join(references_dir, fname)
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        text = GLOSSARY_LINE_RE.sub(lambda m: " " * len(m.group(0)), text)
        for m in BRACKET_FULL_RE.finditer(text):
            name = m.group(1)
            rest = m.group(2).strip()
            if not rest:
                zero_arg.add(name)
            else:
                conflicting.add(name)

    return zero_arg - conflicting


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
            # The directive's own matched text (e.g. '#ifdef NAME', '#endif')
            # is never real TOPAS code to brace/paren-check either way, so it
            # is always blanked here -- but it MUST still be emitted as its
            # own piece (real bug, found by tracing a genuine offset drift on
            # a real corpus file: the loop previously jumped straight from
            # m.start() to pos = m.end() without ever emitting a piece for
            # [m.start(), m.end()), silently DELETING the directive's own
            # character span from the reconstructed line instead of blanking
            # it -- contradicting this function's own docstring promise to
            # preserve line lengths. Confirmed on a real file with 8 such
            # directives before a given str block: the cumulative dropped
            # length shifted every absolute character offset after them,
            # which in turn made symmetrize_str.py look up the wrong
            # physical line number for a site several hundred characters
            # later in the file).
            pieces.append((m.group(0), False))
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


def check_zero_arg_keywords(clean_text, zero_arg_keywords, issues):
    """
    Every keyword in zero_arg_keywords (harvested by
    load_zero_arg_keywords() -- keywords documented with a bare bracket
    signature, e.g. '[str]', '[do_errors]', and nothing else) takes NO
    following value, name, or equation at all -- TOPAS reads straight to
    the next real keyword/directive/macro/brace after one of these. A
    bare NUMBER sitting immediately after one is never valid TOPAS
    grammar -- there's no legitimate reading of "keyword number" as one
    statement when 'keyword' itself takes zero arguments.

    Deliberately scoped to a stray NUMBER specifically, not any
    unrecognized token: an unrecognized bare IDENTIFIER immediately after
    one of these keywords is already caught by the keyword-typo check
    elsewhere in this script (which scans every identifier-shaped token
    in the whole file, not just the ones right after a particular
    keyword class -- see feedback_identifier_must_resolve's "an
    identifier must be a keyword or a macro" principle). This check
    exists for the gap that principle doesn't cover: a bare NUMBER is
    invisible to the keyword-typo check (numbers aren't identifier-
    shaped), which is exactly how this real bug slipped through
    uncaught -- 'str  123123' in a macro-expanded test file, confirmed
    directly by the user (TOPAS-Academic's author): "This line is wrong
    as there's a number just floating there."

    Flagged as a warning, not a hard error -- the same caution applied to
    every other harvested-keyword check in this script: the harvest is
    corpus-verified (see this check's own development history) but can't
    prove every zero-arg keyword's real-world grammar is fully captured
    by its bare bracket notation.
    """
    if not zero_arg_keywords:
        return
    pattern = r"\b(" + "|".join(re.escape(k) for k in sorted(zero_arg_keywords, key=len, reverse=True)) + r")\b"
    for m in re.finditer(pattern, clean_text):
        kw = m.group(1)
        pos = m.end()
        n = len(clean_text)
        if pos >= n or clean_text[pos] not in " \t\r\n":
            continue
        j = pos
        while j < n and clean_text[j] in " \t\r\n":
            j += 1
        if j >= n:
            continue
        next_tok_m = re.match(r"\S+", clean_text[j:])
        if not next_tok_m:
            continue
        next_tok = next_tok_m.group(0)
        num_m = E_ARG_NUMBER_TOKEN_RE.match(next_tok)
        if num_m and num_m.group(0) == next_tok:
            issues.append(
                ("warning", line_of(clean_text, m.start()),
                 f"'{kw}' takes no value at all, but is immediately followed by a bare "
                 f"number '{next_tok}' with nothing in between. This looks like a stray "
                 f"leftover value from a bad edit -- verify manually and remove it if so "
                 f"(this is a heuristic).")
            )


def check_at_sigil_value(clean_text, issues):
    """
    '@' always means "auto-generate a unique name for the value/equation
    that follows" (Technical_Reference.pdf Chapter 2) -- confirmed
    directly by the user (TOPAS-Academic's author): "The @ is
    corresponds to a unique name. The next item should be a number or
    an equal sign. This is all spelled out in Chapter 2 of the Technical
    Reference." So the very next non-whitespace token after a real '@'
    sigil must be either a valid numeric value or '=' -- a bare
    identifier, or a malformed/corrupted number (e.g. a stray letter
    prepended to real digits, 'a2.27742249e-05' instead of
    '2.27742249e-05' -- the exact real bug this check was built to
    catch, found by the user in a macro-expanded test file, immediately
    after the zero-arg-keyword check above was built for the same class
    of "a value slot silently isn't validated" gap) is never valid
    grammar there.

    Three deliberate exceptions, all confirmed necessary directly from
    this check's own corpus regression sweep (real, common syntax
    throughout the example corpus, not rare edge cases):
      1. '@' used as a bare MACRO-CALL argument (e.g. 'TOF_PV(@, 100, @,
         .5, t1)', 'CS_L(@, 300)') means "auto-name whatever parameter
         this call site ends up building here" and is legitimately
         followed by ',' or ')' with no number at all -- that's the
         macro's own business, not a value this checker can see the
         shape of.
      2. '@' directly concatenated with a suggested name, no space (e.g.
         'TOF_PV(@pv6, 72.10546, ...)') -- the same concatenated-sigil
         convention already established for '!name' (e.g. 'prm !b1 .5'),
         just for '@' instead of '!'. The name is consumed first, then
         the SAME validation applies to whatever follows it.
      3. A macro body that's just a bare '@' (or '@name') and nothing
         else, e.g. 'macro SVs { @ }' -- a common TOPAS idiom for a
         toggle macro later substituted into other keyword calls to
         conditionally enable refinement (confirmed directly against a
         real corpus file, kaolinite.inp, using exactly this pattern for
         several such macros). '@' immediately followed by '}' is this
         case.

    Flagged as a warning, not a hard error, the same caution applied to
    every heuristic check in this script.
    """
    for m in re.finditer(r"@", clean_text):
        pos = m.end()
        n = len(clean_text)
        # Exception 2: '@' concatenated directly with a suggested name --
        # consume it before looking at what comes next.
        name_m = re.match(r"[A-Za-z_]\w*", clean_text[pos:])
        j = pos + name_m.end() if name_m else pos

        while j < n and clean_text[j] in " \t\r\n":
            j += 1
        if j >= n:
            continue
        c = clean_text[j]
        if c in "=,)}":
            continue  # exceptions 1 and 3, plus the equation form
        num_m = E_ARG_NUMBER_TOKEN_RE.match(clean_text[j:])
        if num_m and num_m.group(0):
            continue  # valid numeric value
        next_tok_m = re.match(r"\S+", clean_text[j:])
        next_tok = next_tok_m.group(0) if next_tok_m else ""
        if not next_tok:
            continue
        issues.append(
            ("warning", line_of(clean_text, m.start()),
             f"'@' (the auto-name sigil) must be immediately followed by a numeric value or "
             f"'=', but is followed by '{next_tok}', which is neither. This looks like a "
             f"corrupted value (e.g. a stray character prepended to a real number) -- verify "
             f"manually.")
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


Z_MATRIX_KW_RE = re.compile(r"\bz_matrix\b")
Z_MATRIX_ROW_TOKEN_RE = re.compile(r"([A-Za-z_]\w*)(?:\s*(=)\s*([^;]+);)?")


def find_z_matrix_block_spans(text):
    """Outer '{ ... }' span of every 'load z_matrix { ... }' block
    (brace-matched from the first '{' following the keyword). Mirrors
    param_dependency_trees.py's find_z_matrix_spans() -- duplicated
    rather than imported, since that module already imports THIS one
    (a `from param_dependency_trees import ...` here would be circular);
    keep the two in sync by hand if this grammar ever changes."""
    spans = []
    n = len(text)
    for m in Z_MATRIX_KW_RE.finditer(text):
        pos = m.end()
        while pos < n and text[pos] in " \t\r\n":
            pos += 1
        if pos < n and text[pos] == "{":
            depth = 0
            i = pos
            while i < n:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        spans.append((m.start(), i + 1))
                        break
                i += 1
    return spans


def find_z_matrix_label_spans(text):
    """Character spans of z_matrix's own atom-label/reference-label
    tokens (e.g. the 'C2'/'C1' in 'C2  C1  =dc1c2;', or the 'O1'/'C1' in
    the inline 'z_matrix O1 C1 =do1c1; ...' form) -- these are internal
    z-matrix atom tags, never TOPAS keywords or declared parameter
    names, so a generic 'is this a known name' check would misfire on
    every one of them (confirmed directly by the user when scoping this
    check: 'It knows that z_matrix will load a string as the next
    sequence on the stream... you already know the syntax of z_matrix').
    The EXPRESSION after each '=' is deliberately NOT included in these
    spans -- that text is a real equation that can reference real
    declared prm/local names, and should still go through normal typo
    checking. Mirrors the identical grammar in param_dependency_trees.py's
    parse_z_matrix_row_nodes()/parse_inline_z_matrix_rows() (see that
    module for the out_dependences_for/out_dependences verification this
    grammar was originally built and checked against)."""
    spans = []
    for start, end in find_z_matrix_block_spans(text):
        segment = text[start:end]
        in_row = False
        for m in Z_MATRIX_ROW_TOKEN_RE.finditer(segment):
            if m.group(2) is None:
                spans.append((start + m.start(1), start + m.end(1)))
                in_row = True
            elif in_row:
                spans.append((start + m.start(1), start + m.end(1)))

    n = len(text)
    for m in Z_MATRIX_KW_RE.finditer(text):
        pos = m.end()
        look = pos
        while look < n and text[look] in " \t":
            look += 1
        if look < n and text[look] == "{":
            continue  # block form, handled above
        eol = text.find("\n", pos)
        if eol == -1:
            eol = n
        line_text = text[pos:eol]
        lead_ws = len(line_text) - len(line_text.lstrip(" \t"))
        atom_m = IDENTIFIER_RE.match(line_text, lead_ws)
        if not atom_m:
            continue
        spans.append((pos + atom_m.start(), pos + atom_m.end()))
        p = atom_m.end()
        ll = len(line_text)
        while p < ll:
            while p < ll and line_text[p] in " \t":
                p += 1
            ref_m = IDENTIFIER_RE.match(line_text, p)
            if not ref_m:
                break
            spans.append((pos + ref_m.start(), pos + ref_m.end()))
            p = ref_m.end()
            while p < ll and line_text[p] in " \t":
                p += 1
            if p < ll and line_text[p] == "=":
                semi = line_text.find(";", p)
                if semi == -1:
                    break
                p = semi + 1
            else:
                val_m = E_ARG_NUMBER_TOKEN_RE.match(line_text, p)
                if val_m and val_m.group(0):
                    p = val_m.end()
                    # An optional trailing function-call modifier
                    # immediately after the value, e.g. 'MR(1.55)' or
                    # 'M12(90, 120)' in 'z_matrix C6 C5 1.55 MR(1.55)
                    # S1 a1 114.99792 M12(90, 120)' -- consume it too so
                    # it isn't left exposed to typo-checking (a real
                    # corpus false positive otherwise -- see cime-z-
                    # auto.inp's rigid-body z-matrix rows).
                    fn_m = re.match(r"[ \t]*[A-Za-z_]\w*[ \t]*\(", line_text[p:])
                    if fn_m:
                        paren_rel = p + fn_m.end() - 1
                        depth = 0
                        k = paren_rel
                        while k < ll:
                            if line_text[k] == "(":
                                depth += 1
                            elif line_text[k] == ")":
                                depth -= 1
                                if depth == 0:
                                    k += 1
                                    break
                            k += 1
                        p = k
                else:
                    # A richer variant this parser doesn't fully model
                    # (e.g. a '!name'/'name' tag before the real value,
                    # like '!rc5s1 1.70' or 'a1  114.99792') -- rather
                    # than mis-parsing it, exempt everything remaining
                    # on this z_matrix line wholesale and move on to the
                    # next one; still correct (these ARE legitimate
                    # z-matrix row tokens, not typos), just less granular
                    # than the clean '=expr;'/bare-number cases above.
                    spans.append((pos + p, pos + ll))
                    break
    return spans


# A "complex" bare filename -- containing hyphens, parens, and/or digits
# stitched together with no whitespace, ending in a recognized extension
# (e.g. 'cube-ln-normal-1.xy', 'CT-DMF(5oC)-100K-6-64-VC.raw') -- breaks
# into several separate IDENTIFIER_RE fragments no single existing
# exemption covers: the leading filename-fragment-suppression check only
# ever protects a token immediately followed by '.ext' or '-digit', not
# a middle fragment like 'ln' or 'DMF' sitting between two hyphens deep
# inside a longer compound name. Matched as one run of non-whitespace,
# filename-shaped characters ending in a real extension; every
# identifier-shaped fragment inside that run is exempted.
FILENAME_EXTENSIONS = ("xy", "xye", "xys", "raw", "dat", "txt", "cif", "inc", "inp", "hkl", "scr", "cld", "sst")
FILENAME_RUN_RE = re.compile(
    r"[A-Za-z0-9_.\-()#]*\.(?:" + "|".join(FILENAME_EXTENSIONS) + r")\b", re.IGNORECASE
)


def find_filename_run_spans(text):
    spans = []
    for m in FILENAME_RUN_RE.finditer(text):
        if "-" in m.group(0) or "(" in m.group(0):
            spans.append((m.start(), m.end()))
    return spans


def find_space_group_symbol_spans(text):
    """The single bare-token character-run immediately after 'space_group'
    (e.g. 'R_-3_c', 'P_21/c') is ONE symbol, but hyphens and digits inside
    it break IDENTIFIER_RE into several separate fragment tokens (e.g.
    'R_-3_c' tokenizes as 'R_' then, separately, '_c' -- the '-3' in
    between isn't identifier-shaped at all) -- consumed as a single span
    so none of its fragments get typo-checked individually. A quoted
    symbol ('space_group "P 21/c"') is skipped here since
    strip_comments_and_strings already blanks its interior."""
    spans = []
    n = len(text)
    for m in re.finditer(r"\bspace_group\b", text):
        pos = m.end()
        while pos < n and text[pos] in " \t":
            pos += 1
        if pos < n and text[pos] == '"':
            continue
        start = pos
        while pos < n and text[pos] not in " \t\r\n":
            pos += 1
        if pos > start:
            spans.append((start, pos))
    return spans


# Preprocessor directive words -- '#define', '#ifdef', '#ifndef', '#if',
# '#else', '#elseif', '#endif', '#include', '#ingest', '#list',
# '#undef', '#seed', '#m_argu' (macro-internal argument marker, e.g.
# 'macro Foo(x) { #m_argu x ... }') -- the leading '#' isn't a word
# character, so it strips away during tokenization, leaving the bare
# directive word looking like an unrecognized identifier (confirmed as a
# real false positive: '#m_argu sxc' inside a macro body flagged
# 'm_argu' as unrecognized in a real corpus regression run).
PREPROCESSOR_WORDS = {
    "define", "ifdef", "ifndef", "if", "else", "elseif", "endif",
    "include", "ingest", "list", "undef", "seed", "m_argu",
    "m_if", "m_else", "m_elseif", "m_endif", "m_ifarg", "m_prm",
    "delete_macros",
}

# Small hand-verified supplement of real keywords/reserved-parameter
# names that fall outside every harvester above (bracket-notation, table-
# row, bare-signature-line) -- found empirically, one at a time, the same
# way SINGLE_ARG_FALSE_POSITIVES was built. atomic_interaction's own
# ai_sites_1/ai_sites_2/etc. sub-keywords are documented as a single
# run-on prose line ('ai_sites_1 $sites_1 ai_sites_2 $sites_2'), not any
# of the three recognized signature forms. axial_del and INP_File are
# real (confirmed by real usage in the corpus -- axial_del alongside
# Full_Axial_Model in a real corpus file; INP_File as
# 'String(INP_File)' in another) but aren't documented in a form
# any harvester here catches; INP_File specifically is the reserved
# parameter name for the current INP file's own name/path.
SUPPLEMENTAL_MISC_KEYWORDS = {
    "ai_sites_1", "ai_sites_2", "ai_no_self_interation", "ai_closest_N",
    "ai_radius", "ai_exclude_eq_0", "ai_only_eq_0", "AI_R_CM",
    "axial_del", "INP_File", "Get_Element_Weight", "fft_max_order",
}

# axial_conv's own named sub-parameters (references/21-keyword-index.md,
# Tcomm_1: '[axial_conv]... filament_length E sample_length E
# receiving_slit_length E'; also cross-confirmed in the min/max defaults
# table, references/01-syntax-and-parameters.md Table: 'sample_length,
# receiving_slit_length, primary_soller_angle, secondary_soller_angle').
# Packed as bare name-then-value pairs directly after the axial_conv
# keyword (no further keyword in between each), the same
# multi-bare-token-argument grammar z_matrix has -- but since this is a
# small, fixed, well-documented set of names (not a repeating row
# structure), just registering the names themselves as always-known is
# simpler than a dedicated positional consumer like z_matrix's.
AXIAL_CONV_SUBPARAMS = {
    "filament_length", "sample_length", "receiving_slit_length",
    "primary_soller_angle", "secondary_soller_angle", "axial_n_beta",
}

# Keywords whose grammar takes TWO bare tag tokens before the real value,
# not just one -- occ's '$atom [$name] E' (the atom symbol is required,
# the name optional) and element_weight_percent's '$atom $Name #'
# (references/21-keyword-index.md's Data structures listing). A real
# corpus false positive otherwise: 'element_weight_percent Pr wt_Pr
# 28.29...' -- 'Pr' (the required atom) was already protected by the
# general single-token skip, but 'wt_Pr' (the second, tag-name token)
# wasn't.
WIDE_TAG_KEYWORDS = {"occ", "element_weight_percent"}

# Small hand-verified supplement to the Table 2-2/2-4 reserved-parameter-
# name harvest below (load_reserved_parameter_names()) -- real reserved
# names confirmed in reference-chapter prose (Fcalc/Fobs:
# 21-keyword-index.md's fourier_map_formula note; FT_K/WPPL_L/WPPM_L/
# WPPM_Ln_k: 20-miscellaneous.md's ft_conv/WPPM sections; I: Table 2-4's
# own footnote text, "1) I corresponds to I of hkl_Is..." -- prose, not
# a clean Name-column table row, so the table harvester alone misses it)
# that fall outside the two clean tables the harvester parses.
RESERVED_PARAMETER_NAME_SUPPLEMENT = {
    "Fcalc", "Fobs", "FT_K", "WPPL_L", "WPPM_L", "WPPM_Ln_k", "I",
}


def load_reserved_parameter_names(references_dir):
    """Harvest TOPAS's own reserved parameter names (X, Yobs, Ycalc, H,
    K, L, D_spacing, Th, Lam, T, Cycle, Val, Change, ...) from
    references/01-syntax-and-parameters.md's 'Table 2-2. Reserved
    parameter names.' and 'Table 2-4. Phase intensity reserved parameter
    names.' -- these are internally-updated names usable inside
    equations (see that file's own '## Reserved parameter names'
    section), never declared via prm/local and never a bracket-notation
    keyword either, so without this they were coming back as
    unrecognized identifiers everywhere real equations used them (Xo,
    Yobs, Ycalc, H, K, L, D_spacing, ... -- a large, real false-positive
    class found in a full corpus regression run). Each table row's first
    cell is a comma-separated list of names sharing one description;
    parsed by locating the two table's own header rows and reading every
    '| Name(s) | ... |' row until the next '##'/'|---|' section
    boundary that isn't part of the same table."""
    names = set(RESERVED_PARAMETER_NAME_SUPPLEMENT)
    path = os.path.join(references_dir, "01-syntax-and-parameters.md")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return names
    for header in ("Table 2-2. Reserved parameter names.", "Table 2-4. Phase intensity reserved parameter names."):
        idx = text.find(header)
        if idx == -1:
            continue
        end = text.find("\n\n\n", idx)
        if end == -1:
            end = len(text)
        block = text[idx:end]
        for line in block.split("\n"):
            line = line.strip()
            if not line.startswith("|") or line.startswith("| ---") or line.startswith("| Name"):
                continue
            cell = line.strip("|").split("|")[0]
            # Most rows comma-separate multiple names sharing one
            # description ('A_star, B_star, C_star'), but at least one
            # (Table 2-4's 'Iobs_no_scale_pks Iobs_no_scale_pks_err')
            # space-separates them instead with no comma at all -- split
            # on both.
            for tok in re.split(r"[,\s]+", cell):
                tok = tok.strip()
                if re.match(r"^[A-Za-z_]\w*$", tok):
                    names.add(tok)
    return names


# Trigger words for find_data_block_spans() -- deliberately a small,
# curated set (NOT "any recognized keyword/macro"), since a brace block
# immediately after most keywords/macros IS real, checkable TOPAS
# statement syntax (e.g. a macro's own body).
DATA_BLOCK_TRIGGER_WORDS = {
    "load", "ADPs", "adps",
    # '#list File_Name Time Temperature Gas { data rows }' (references/
    # 26-parametric-and-sequential-refinement.md) -- same
    # header-keyword-list-then-brace-table shape as 'load', for
    # sequential/parametric refinement's per-pattern data table. A real
    # corpus false positive otherwise: bare column values inside the
    # table (e.g. 'CH4', 'Gas') flagged as unrecognized.
    "list",
}

# For most trigger words (load/ADPs/adps), the HEADER between the
# trigger and the '{' is real, checkable syntax (load's column-type
# keywords are actual TOPAS keywords) and should stay validated
# normally -- only the brace BODY is data. '#list', however, uses
# user-CHOSEN column names in its own header ('#list File_Name Time
# Temperature Gas { ... }' -- none of File_Name/Time/Temperature/Gas
# are real keywords), so its header needs exempting too.
DATA_BLOCK_TRIGGERS_WITH_EXEMPT_HEADER = {"list"}


def find_data_block_spans(text):
    """The '{ ... }' body of a 'TRIGGER [KEYWORD1 KEYWORD2 ...] { data
    rows }' block, for a small curated set of trigger words known to
    introduce this shape (DATA_BLOCK_TRIGGER_WORDS below) -- NOT any
    arbitrary recognized keyword/macro, since e.g. 'macro Foo(x) {
    ...real TOPAS code... }' has the same surface shape (a keyword-ish
    name immediately followed by a brace block) but its body is genuine
    statement syntax that must still be checked normally. Two confirmed
    real cases: 'load site x y z occ beq layer { Al1 XX(0.2986)
    YY(0.4955) ZZ(0.4755) Al 1 0.25 A ... }' (references/20-
    miscellaneous.md's use_hklm example; the header keyword list itself
    is validated normally, but the DATA ROWS below follow whatever
    column types the header declared, not keyword syntax -- e.g. an
    'occ' column's row value is a bare atom symbol like 'Al'/'Si'/'O',
    not itself required to be a keyword -- 'Si' inside exactly this kind
    of table was a real corpus false positive); and 'ADPs { u11C1 0.01
    u22C1 0.01 ... }' (a CIF-import-generated file's own convention of
    suffixing each U_ij component name with its site label, e.g.
    'u23O3' -- also a real corpus false positive)."""
    spans = []
    n = len(text)
    for m in re.finditer(r"\b(?:" + "|".join(re.escape(w) for w in DATA_BLOCK_TRIGGER_WORDS) + r")\b", text):
        pos = m.end()
        brace_pos = None
        j = pos
        while j < n and j < pos + 300:
            c = text[j]
            if c == "{":
                brace_pos = j
                break
            if c == ";":
                break
            j += 1
        if brace_pos is None:
            continue
        depth = 0
        i = brace_pos
        while i < n:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    span_start = pos if m.group(0) in DATA_BLOCK_TRIGGERS_WITH_EXEMPT_HEADER else brace_pos + 1
                    spans.append((span_start, i))
                    break
            i += 1
    return spans


def find_call_argument_spans(text, keywords_plus_macros):
    """Character span of every '(...)' argument list immediately
    following a recognized keyword/macro name (e.g. 'CS_L(csl,
    207.591332)', 'MVW(6531.635, 1266.863, 100.000)') -- exempted from
    typo-checking wholesale, since these arguments are typically site/
    parameter names or literal values the callee's own grammar defines,
    not TOPAS keywords themselves (the same reasoning DEFINER_KEYWORDS
    already applies to 'prm NAME'/'local NAME', generalized to every
    parenthesized macro/keyword call). Brace-matched so nested parens in
    the argument list don't truncate the span early."""
    spans = []
    n = len(text)
    for m in re.finditer(r"([A-Za-z_]\w*)\s*\(", text):
        if m.group(1) not in keywords_plus_macros:
            continue
        paren_start = m.end() - 1
        depth = 0
        i = paren_start
        while i < n:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    spans.append((paren_start + 1, i))
                    break
            i += 1
    return spans


def _in_any_span(pos, spans):
    return any(s <= pos < e for s, e in spans)


def find_defined_names(clean_text, keywords=None):
    names = set()
    tokens = list(IDENTIFIER_RE.finditer(clean_text))
    for idx, m in enumerate(tokens):
        word = m.group(0)
        if word in DEFINER_KEYWORDS and idx + 1 < len(tokens):
            names.add(tokens[idx + 1].group(0))
    if keywords:
        # Many keywords use a 'keyword $name value' tagging convention
        # (occ/beq/number_of_sequences/scale/...) where the tag becomes a
        # real, persistently-referenceable name -- e.g.
        # 'number_of_sequences Nseqs 200' declares Nseqs, then some LATER
        # equation elsewhere in the file does 'Nv Nseqs'. This has to be
        # a full pre-pass over the WHOLE file (not just registered as a
        # side effect while the main check_keyword_typos() loop happens
        # to walk past the declaration), because a reference can appear
        # BEFORE its own declaration in the file (a real false positive
        # found in a corpus regression run: exactly this Nseqs case,
        # where the reference on an earlier line was still unresolved
        # even after teaching the main loop to register tags going
        # forward, since that single left-to-right pass hadn't reached
        # the later declaration yet when it hit the earlier reference).
        for idx, m in enumerate(tokens):
            word = m.group(0)
            if word not in keywords:
                continue
            after_pos = m.end()
            while after_pos < len(clean_text) and clean_text[after_pos] in " \t\r\n":
                after_pos += 1
            if after_pos < len(clean_text) and clean_text[after_pos] == "(":
                continue  # a parenthesized call -- no bare tag-name argument to register
            width = 2 if word in WIDE_TAG_KEYWORDS else 1
            for j in range(idx + 1, min(idx + width, len(tokens) - 1) + 1):
                names.add(tokens[j].group(0))
    for m in re.finditer(r"[@!]\s*([A-Za-z_][A-Za-z0-9_]*)", clean_text):
        names.add(m.group(1))
    # Names introduced via #define NAME are user-chosen flags, not keywords.
    for m in re.finditer(r"#define\s+([A-Za-z_]\w*)", clean_text):
        names.add(m.group(1))
    # 'def' can declare several comma-separated names in one statement
    # with no value at all ('def f21, f22;', a forward declaration) --
    # the general single-token skip-after-any-keyword mechanism only
    # ever protects the FIRST name in such a list ('f21'), missing the
    # rest ('f22', a real false positive found in a corpus regression
    # run). 'def NAME = expr;' (the far more common single-name form)
    # is already covered by that same general mechanism and doesn't need
    # duplicating here.
    for m in re.finditer(r"\bdef\s+([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)+)\s*;", clean_text):
        for name in m.group(1).split(","):
            names.add(name.strip())
    # TOPAS's '##' token-pasting operator builds a dynamic parameter name
    # from a macro-argument prefix and a literal suffix (e.g. 'prm
    # ZZ##z1' -- 'ZZ' is usually a real macro parameter, already handled
    # elsewhere, but the 'z1' suffix is hand-typed literal text meant to
    # be concatenated on, not an independent reference to anything). Any
    # identifier immediately preceded by '##' is this kind of suffix,
    # never meant to be independently meaningful/checkable.
    for m in re.finditer(r"##([A-Za-z_]\w*)", clean_text):
        names.add(m.group(1))
    # A macro's own PARAMETER names (e.g. 'macro Foo(sh_c22m, sh_c22p)')
    # are legitimate identifiers throughout that macro's own body, but
    # were never registered anywhere -- only the macro's own NAME was
    # harvested, never its parameter list. A real false-positive class
    # found in a full corpus regression run: spherical-harmonics-style
    # macro parameter names (sh_c22m, y22p, Lpa, u1, v1, ...) flagged as
    # unrecognized throughout the macro body that declares and uses them.
    for m in MACRO_DEF_RE.finditer(clean_text):
        for param in m.group(2).split(","):
            param = param.strip().lstrip("&").strip()
            if re.match(r"^[A-Za-z_]\w*$", param):
                names.add(param)
    # 'fn NAME(args) { ... }' user-defined functions have the same "own
    # parameter names are legitimate throughout the body" issue as
    # 'macro', but use a different keyword and so aren't matched by
    # MACRO_DEF_RE at all (a real false positive found in a corpus
    # regression run: x1/y1/z1/o1/b1 flagged inside a 'fn str_F2(h, k,
    # l, ...)' body that used them as its own parameters).
    for m in FN_DEF_RE.finditer(clean_text):
        for param in m.group(2).split(","):
            param = param.strip().lstrip("&").strip()
            if re.match(r"^[A-Za-z_]\w*$", param):
                names.add(param)
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
    defined_names = find_defined_names(clean_text, keywords)
    consumed_spans = (find_z_matrix_label_spans(clean_text) + find_call_argument_spans(clean_text, keywords)
                       + find_space_group_symbol_spans(clean_text) + find_data_block_spans(clean_text)
                       + find_filename_run_spans(clean_text))
    seen_already = set()
    keywords_by_len = {}
    for kw in keywords:
        keywords_by_len.setdefault(len(kw), []).append(kw)

    tokens = list(IDENTIFIER_RE.finditer(clean_text))
    skip_through_idx = -1
    for idx, m in enumerate(tokens):
        word = m.group(0)

        # If this token is itself a real keyword/macro (exact case), the
        # next token is very likely its argument/parameter-name position
        # (e.g. "scale scale_1", "peak_buffer_step ..."), not a keyword
        # itself -- skip it. Checked BEFORE the skip_through_idx test below
        # (not after -- a real, confirmed bug found once MIN_TYPO_CHECK_LEN
        # was removed: a keyword whose bare numeric argument produces no
        # IDENTIFIER_RE token at all, e.g. 'x 0.25', leaves skip_through_idx
        # pointing at the very NEXT keyword in the token list, e.g. 'y' in
        # 'x 0.25 y 0.5' -- checking skip_through_idx first would silently
        # swallow that next keyword as if it were a skipped argument,
        # permanently desyncing the skip chain for the rest of the
        # statement, e.g. across an entire dense 'site NAME x # y # z #
        # occ ATOM # beq #' line. Checking `word in keywords` first means a
        # real keyword is always recognized regardless of stale skip
        # state, and skip_through_idx only ever protects genuine non-
        # keyword value token(s) -- safe to widen the window for a
        # specific keyword (see 'occ' below) since a real keyword inside
        # that window still always wins.
        if word in keywords:
            # ...UNLESS this keyword/macro is being invoked as a
            # parenthesized call ('ZE(@, 0)', 'CS_L(csl, 207.6)') --
            # find_call_argument_spans() already exempts everything
            # inside those parens, so there's no "next bare tag-name
            # argument" to protect here at all. Without this check, a
            # call with no identifier-shaped token inside its own parens
            # (e.g. 'ZE(@, 0)' -- '@'/'0' aren't identifiers) leaves
            # skip_next_idx pointing at the next real identifier
            # anywhere AFTER the call closes, wrongly absorbing an
            # unrelated, genuinely stray token positioned right after it
            # (a real, confirmed bug: 'ZE(@, 0)' immediately followed by
            # a leftover 'eee' on the next line was silently swallowed
            # this way before this check was added).
            after_pos = m.end()
            while after_pos < len(clean_text) and clean_text[after_pos] in " \t\r\n":
                after_pos += 1
            if after_pos >= len(clean_text) or clean_text[after_pos] != "(":
                # occ's own grammar is 'occ $atom [$name] E [beq E] ...'
                # -- an OPTIONAL user-chosen name (the same "scale
                # scale_1"-style convention) can follow the required atom
                # symbol before the real value, so widen the window to 2
                # bare tokens for this one keyword specifically (e.g.
                # 'occ Na occn2 0.03259` ...', a real corpus false
                # positive on 'occn2' otherwise). Safe even when there's
                # no second bare tag present, since a real keyword
                # anywhere in the window still always wins (checked
                # first, above).
                width = 2 if word in WIDE_TAG_KEYWORDS else 1
                skip_through_idx = idx + width
                # (The tag-name token(s) in this window are ALSO
                # registered persistently into defined_names -- but as a
                # dedicated pre-pass over the whole file in
                # find_defined_names(), not here, since a reference can
                # appear BEFORE its own declaration; see that function's
                # own note.)
            continue

        if idx <= skip_through_idx:
            continue

        if word in defined_names:
            continue
        if word in seen_already:
            continue
        # A keyword's own documented multi-token argument grammar (right
        # now: z_matrix's atom-label/reference-label tokens, and the full
        # argument list of any parenthesized keyword/macro call) -- these
        # bare tokens are consumed by that grammar, not required to
        # themselves be a keyword. See find_z_matrix_label_spans() /
        # find_call_argument_spans() docstrings.
        if _in_any_span(m.start(), consumed_spans):
            continue
        # A string-literal placeholder ('x' repeated -- see
        # strip_comments_and_strings' docstring on why quoted-string
        # interiors become 'x' runs rather than blank spaces) is a
        # stripped-string artifact, never a real identifier.
        if re.fullmatch(r"x+", word):
            continue
        # The EXTENSION half of a bare, unquoted filename ('somefile.xy'
        # tokenizes as 'somefile' then, separately, 'xy' right after the
        # literal dot) -- the existing filename-fragment suppression
        # below only ever protected the STEM half (by checking what
        # follows a token for '.ext'); this protects the extension
        # token itself, recognized by being immediately preceded by '.'.
        if m.start() > 0 and clean_text[m.start() - 1] == "." and len(word) <= 5:
            continue
        # The fractional-part digits of a backtick-error value tokenize as
        # a bare '_N' identifier (e.g. the '_0' in '52.5347835`_0.817...',
        # matched up to the decimal point) purely because IDENTIFIER_RE
        # allows a leading underscore -- not a real identifier, just an
        # artifact of TOPAS's own 'value`_error' notation. Recognized by
        # being immediately preceded by a backtick OR a digit -- some
        # real corpus files write this without the backtick at all (e.g.
        # 'local !d0_1 4.32982_0.13351', found in a regression run), so
        # requiring the backtick specifically missed that variant. A bare
        # trailing '_' with NOTHING after it (e.g. 'prm !const2
        # 4.81474_', also found in a regression run) is the same artifact
        # with its error digits apparently truncated/missing -- still not
        # a real identifier either way, so exempted the same as the
        # digit-suffixed form (word[1:] == "" for this case).
        if word[0] == "_" and (word[1:].isdigit() or word[1:] == "") and m.start() > 0 and clean_text[m.start() - 1] in "`0123456789":
            continue
        # TOPAS's own '_LIMIT_MIN_value'/'_LIMIT_MAX_value' suffix,
        # appended directly after a refined value's error to record that
        # it terminated at a parameter limit (e.g.
        # '15.68351_LIMIT_MIN_-0.386567039') -- documented notation, not
        # an identifier.
        if word.startswith("_LIMIT_MIN_") or word.startswith("_LIMIT_MAX_"):
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
        # Exact-case near-miss matching -- a stricter comparison than the
        # earlier case-folded version, since case itself now counts as a
        # real difference (and a real class of typo: right word, wrong case).
        close = difflib.get_close_matches(word, candidates, n=1, cutoff=0.82) if candidates else []
        seen_already.add(word)
        if close:
            issues.append(
                ("warning", line_of(clean_text, m.start()),
                 f"'{word}' is not a recognized keyword/macro name (exact case) and closely "
                 f"resembles '{close[0]}'. Possible typo, or a case mistake since TOPAS names "
                 f"are case sensitive -- verify manually (this is a heuristic, not certain).")
            )
        else:
            # No length floor and no fuzzy-match requirement (confirmed
            # directly by the user): every identifier must resolve to a
            # keyword, a macro, a name this file itself declares, or a
            # token consumed by some keyword's own known argument
            # grammar -- anything left over is a stray/leftover token,
            # not a near-miss of anything in particular (e.g. "eee" sitting
            # alone on its own line, not a typo of any real keyword).
            issues.append(
                ("warning", line_of(clean_text, m.start()),
                 f"'{word}' is not a recognized keyword, macro, or declared name, and doesn't "
                 f"closely resemble any known one either -- likely a stray/leftover token rather "
                 f"than a typo of something specific; verify manually (this is a heuristic: if "
                 f"this is a legitimate bare-token argument to a keyword this checker doesn't yet "
                 f"know the grammar of, that's a gap in this checker, not a mistake in the file).")
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


def harvest_fn_names(text):
    """'fn NAME(args) { ... }' user-defined functions -- DEFINER_KEYWORDS
    already registers a fn's own NAME in find_defined_names() (so a bare
    mention of 'site_F' by itself wouldn't be flagged), but that's a
    SEPARATE set from keywords_plus_macros, which is what
    find_call_argument_spans() actually checks a callee name against
    before exempting its whole argument list. Without this, 'fn'
    definitions were invisible to the call-argument exemption -- e.g.
    'site_F(h, k, l, x1, y1, z1, o1, b1, d2_inv, f0_Al)' calling a real
    'fn site_F(...)' still had EVERY one of its own arguments individually
    typo-checked, a real false-positive class found in a corpus
    regression run (z1/o1/z2/o2/... flagged throughout)."""
    names = set()
    for m in FN_DEF_RE.finditer(text):
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
        # Skip the macro's own definition site ("macro Name(...)" or
        # "macro & Name(...)" -- see MACRO_DEF_RE's own note on the
        # optional '&' before the name).
        prefix = clean_text[:m.start()].rstrip()
        if prefix.endswith("&"):
            prefix = prefix[:-1].rstrip()
        prev_word_match = re.search(r"([A-Za-z_]\w*)\s*$", prefix)
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


FOR_XDDS_RE = re.compile(r"\bfor\s+xdds\s*\{")
FOR_STRS_ALL_RE = re.compile(r"\bfor\s+strs\s*\{")
FOR_STRS_RANGE_RE = re.compile(r"\bfor\s+strs\s+(\d+)\s+to\s+(\d+)\s*\{")


def find_xdd_count(clean_text):
    """Count of top-level `xdd` block declarations (each starts a new
    xdd/pattern object) -- used to determine the iteration count of a
    `for xdds { ... }` loop, which applies its body once per already-
    declared xdd object rather than declaring a new one itself. xdd
    objects are always declared as a bare 'xdd <file>' statement (never
    inside a for-loop body, which only ever APPLIES settings to objects
    that already exist), so a plain count of '\\bxdd\\b' tokens is
    sufficient -- word-boundary matching already excludes 'xdds' (as in
    'for xdds'). Confirmed against a real file: returns 65 for
    test_examples/matthew-rowles/2457_surface_paper_2.inp, matching that
    file's own tc.exe console output ('Num data files: 65')."""
    return len(re.findall(r"\bxdd\b", clean_text))


def _find_matching_brace(clean_text, open_brace_pos):
    """Given the offset of a '{' character, return the offset of its
    matching '}' via simple depth counting (clean_text is already
    comment/string-stripped, so no need to skip over those here)."""
    depth = 0
    n = len(clean_text)
    i = open_brace_pos
    while i < n:
        c = clean_text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return n


def find_for_loop_multipliers(clean_text):
    """Find every `for xdds { ... }` / `for strs { ... }` / `for strs N
    to M { ... }` construct and its multiplicity -- how many times TOPAS
    actually evaluates that block's body internally (once per already-
    declared xdd, once per already-declared str, or once per str in the
    given 1-based inclusive range, respectively). A parameter declared
    ONCE in a loop's source text is really N independent parameters at
    runtime (auto-uniquified per iteration) -- confirmed directly, at the
    user's own request, against a real file: TOPAS itself reported 1448
    independent parameters for test_examples/matthew-rowles/
    2457_surface_paper_2.inp, while a scan with no concept of this
    multiplication found only 800-864 (missing the multiplication inside
    that file's `for xdds { ... }`, which contains independently-refined
    parameters like `Pb_shift`/`Pb_ka1_fwhm` applied once per xdd -- 65
    times each, not once).

    Returns a list of (body_start, body_end, multiplier) offset spans
    (body = strictly between the '{' and its matching '}'). Nested loops
    just produce multiple overlapping spans -- a position inside more
    than one span is multiplied by all of them (the product), matching
    real nested-loop semantics (e.g. `for xdds { for strs 1 to 2 { ... }
    }`'s inner body is n_xdd * 2, not just one or the other).

    Only these three documented forms are recognized. TOPAS's `for` can
    also iterate over other internal node types (e.g. `for site_recs
    { ... }`, references/20-miscellaneous.md) -- those are NOT specially
    handled here; their body is scanned as literal text occurring once,
    same as before this function existed. Stated plainly as a known scope
    boundary, not a silent gap: xdds/strs are the dominant, corpus-
    confirmed forms actually used for multi-pattern refinement files.

    One deliberately conservative choice, stated plainly rather than
    guessed at: a BARE (no-range) `for strs { ... }` found NESTED inside
    another one of these spans (almost always a `for xdds { ... }`) does
    NOT get its own extra multiplier on top of the enclosing one -- only
    a TOP-LEVEL bare `for strs { ... }` uses the file's total str count.
    The real semantics of a nested bare `for strs` (every str in the
    whole file, again, for every xdd iteration? or just the strs
    belonging to the current xdd?) aren't confirmed, and the wrong guess
    in the "whole file, again" direction is a much worse failure mode
    (a 65x390 explosion instead of a 65x6) than simply not adding a
    second multiplier there. An explicit-range `for strs N to M { ... }`
    is unaffected by this caveat -- M-N+1 is unambiguous regardless of
    nesting, confirmed directly against a real nested example (`for xdds
    { ... for strs 3 to 4 { ... beq Ti5_Ti_beq 1.14414\\` ... } }` in
    2457_surface_paper_2.inp: the shared 'Ti5_Ti_beq' name already
    dedupes to one parameter WITHIN one iteration same as any other
    same-named beq, and this function's job is only to then multiply
    that by 2 for the two str-index iterations, exactly matching how the
    xdd-level multiplication already works).
    """
    n_str = None
    n_xdd = None
    spans = []

    for m in FOR_XDDS_RE.finditer(clean_text):
        if n_xdd is None:
            n_xdd = find_xdd_count(clean_text)
        open_pos = m.end() - 1
        close_pos = _find_matching_brace(clean_text, open_pos)
        spans.append((open_pos + 1, close_pos, n_xdd))

    for m in FOR_STRS_ALL_RE.finditer(clean_text):
        # Skip if this bare 'for strs' is itself nested inside a span
        # already found above (see the nesting caveat in the docstring).
        if any(start <= m.start() < end for start, end, _mult in spans):
            continue
        if n_str is None:
            n_str = len(find_str_blocks(clean_text))
        open_pos = m.end() - 1
        close_pos = _find_matching_brace(clean_text, open_pos)
        spans.append((open_pos + 1, close_pos, n_str))

    for m in FOR_STRS_RANGE_RE.finditer(clean_text):
        lo, hi = int(m.group(1)), int(m.group(2))
        mult = max(hi - lo + 1, 0)
        open_pos = m.end() - 1
        close_pos = _find_matching_brace(clean_text, open_pos)
        spans.append((open_pos + 1, close_pos, mult))

    return spans


def for_loop_multiplier_at(pos, spans):
    """Product of every span's multiplier that contains character offset
    `pos` -- nested for-loops multiply together, matching real semantics.
    `spans` is find_for_loop_multipliers()'s return value."""
    result = 1
    for start, end, mult in spans:
        if start <= pos < end:
            result *= mult
    return result


def for_loop_multiplier_at_line(line_no, clean_text, spans):
    """Same as for_loop_multiplier_at, but keyed by 1-indexed line number
    instead of a character offset -- convenient for callers (like
    find_refined_params.py) that only tracked a line number, not the
    original offset, for each parameter they found."""
    result = 1
    for start, end, mult in spans:
        if line_of(clean_text, start) <= line_no <= line_of(clean_text, max(end - 1, start)):
            result *= mult
    return result


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


def check_symmetry_constraints(clean_text, text_with_values, issues):
    """
    Validate that an existing .inp's ADPs (u11..u23) and lattice parameters
    actually implement the constraints their own declared space group
    requires -- e.g. flag a lattice length refined independently when the
    crystal system requires 'b = Get(a);', or an ADP tensor component that
    isn't correctly tied/zeroed per the site's Wyckoff position.

    Site COORDINATE (x/y/z) independent-refinement-vs-required-tie checking
    (e.g. flagging 'y' written independently when site symmetry would tie
    it to 'y = Get(x);') was originally built at the user's own request
    ("if 'y=Get(x);' is necessary and the INP file tries to refine on the y
    coordinate independently, then throw a warning") but was later
    explicitly REMOVED, again directly by the user (TOPAS-Academic's
    author), on a real file (test_examples/temp.inp's O1 site) where it
    flagged a deliberate, valid choice: "the act of refining on x or y
    independently means that TOPAS will treat these coordinates as being
    different to each other" -- i.e. writing a coordinate independently
    (not tied via Get()) is itself the deliberate signal that it should be
    treated as independent, a normal modeling choice, not an accidental
    omission worth flagging. This does NOT extend to ADPs or lattice
    parameters below -- neither has been challenged the same way, and the
    ADP check in particular is not the same kind of check to begin with
    (see the note above classify_adps' call site).

    The ADP check (symmetry_utils.classify_adps -- see its own docstring)
    differs from the (now-removed) coordinate check in one important way: a
    coordinate's required 'fixed' value was *derived from that same
    coordinate's own written number* (see resolve_site_coordinates), so a
    bare value could never numerically mismatch it -- only '@'-refining it
    was a real risk, which is exactly the class of warning that turned out
    to be unwanted. An ADP's required value is NOT derived from its own
    written number -- it's derived purely from the site's POSITION
    stabilizer, entirely independent of whatever u_ij value happens to be
    written. So a bare ADP value that's numerically wrong (e.g. 'u12 0.02'
    when site symmetry requires 'u12' fixed at 0, or requires it equal to
    'u11/2' but the written number doesn't match) is a genuine static data
    error, flagged regardless of refinement status -- a different situation
    from the coordinate case that was removed, not just a smaller version
    of it.

    Reuses the exact same crystallography engine as cif_to_str.py
    (symmetry_utils.py) -- classify_crystal_system/ANGLE_CONSTRAINTS_BY_SYSTEM/
    LENGTH_TIES_BY_SYSTEM for lattice-parameter constraints, classify_adps
    for per-site ADP constraints -- run here in the opposite direction:
    instead of generating correct syntax from a CIF, it parses the .inp's
    OWN already-written syntax and compares it against what the space
    group requires.

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
                # risk unless something can actually move.
                if form[0] == "value" and form[1] != "@":
                    indep_form = extract_keyword_form(preamble, indep)
                    indep_refined = indep_form is not None and indep_form[0] == "value" and indep_form[1] == "@"
                    if not indep_refined:
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
            # Coordinate (x/y/z) independent-refinement-vs-required-tie
            # checking was deliberately REMOVED here (previously flagged a
            # coordinate refined independently when site symmetry would
            # otherwise tie/fix it) -- confirmed directly by the user
            # (TOPAS-Academic's author) as a false-positive class, not a
            # real risk: "the act of refining on x or y independently means
            # that TOPAS will treat these coordinates as being different to
            # each other" -- i.e. writing a coordinate independently is
            # itself the deliberate signal that it should be treated as
            # independent, a normal and valid modeling choice, not an
            # accidental omission worth flagging. ADP (u11..u23)
            # fixed/tied checking below is unaffected -- only ever
            # confirmed, never objected to.

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
                            if this_refined or (resolvable and other_refined):
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


def check_file(path, keywords, library_arities, library_bodiless, single_arg_keywords, e_arg_keywords, zero_arg_keywords, extra_text=None):
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
    file_fn_names = harvest_fn_names(clean)
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
    keywords_plus_macros = (
        keywords | set(merged_arities.keys()) | library_bodiless | file_bodiless | file_fn_names | DEFINER_KEYWORDS | {"load"}
        | PREPROCESSOR_WORDS | AXIAL_CONV_SUBPARAMS | SUPPLEMENTAL_MISC_KEYWORDS
        | load_reserved_parameter_names(REFERENCES_DIR)
    )

    check_keyword_typos(clean, keywords_plus_macros, issues)
    check_macro_arity(clean, merged_arities, issues)
    check_single_string_arg_keywords(clean, keywords_plus_macros, single_arg_keywords, issues)
    check_single_e_arg_keywords(clean, keywords_plus_macros, e_arg_keywords, issues)
    check_zero_arg_keywords(clean, zero_arg_keywords, issues)
    check_at_sigil_value(clean, issues)
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
    zero_arg_keywords = load_zero_arg_keywords(REFERENCES_DIR) | ZERO_ARG_KEYWORD_SUPPLEMENT

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
        issues = check_file(path, keywords, library_arities, library_bodiless, single_arg_keywords, e_arg_keywords, zero_arg_keywords, extra_text=extra_text)
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
