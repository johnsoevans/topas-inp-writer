#!/usr/bin/env python3
"""
expand_inp_macros.py -- Expand TOPAS macros in a .inp file to approximate
what TOPAS itself writes to tc.log (the literal text actually fed to the
kernel), without needing to run TOPAS.

Performs, in order: #ingest resolution (textually merges a target
file in place, relative to the referencing file's own directory --
"ingested files are treated as part of the original INP file" per the
manual), #include resolution (against the bundled references/system-
files/inc/ library, since topas.inc is auto-loaded by TOPAS for every
run), #define/#ifdef/#ifndef/#else/#elseif/#endif preprocessing
(pruning untaken branches), comment stripping, recursive macro
expansion with overload-by-argument-count resolution, plain
(non-parenthesizing) parameter substitution, @-parameter auto-naming,
interpretation of the "#m_*" macro-body directive family (#m_argu,
#m_unique, #m_first_word, #m_ifarg/#m_else/#m_endif -- TOPAS's own
preprocessor mini-language for inspecting an argument's shape, used
pervasively inside topas.inc's refinable-parameter macros), and "##"
token-paste resolution -- all matching the rules confirmed in
references/macro-expansion-and-log-files.md by diffing real tc.log
output against real source.

Note on parentheses: parameter substitution itself is plain text
replacement with no parentheses added, EXCEPT for TOPAS's documented
"&" macro syntax (manual section "Superfluous parentheses and the '&'
Type for macros"), which this expander implements: '&' before a macro
NAME ('macro & CeV(c, v) { CV(c, v) }') wraps that macro's whole
expansion result in one pair of parens at each call site; '&' before
an ARGUMENT name in the parameter list wraps that argument's bound
value in parens everywhere it's referenced in the body. E.g. the
built-in CeV(c, v) macro is declared with '&' before its name (its
body is plain "CV(c, v)", no literal parens in the source), so
CeV(17) expands to "(17)" via the name-level rule, matching real
tc.log output such as "Cos((17) 0.0174...)".

This is a best-effort STATIC expander, not TOPAS itself. Known
limitations, stated up front rather than silently guessed around:

  - Only `macro` definitions are expanded. `fn`-defined functions (used
    inside equations, e.g. `fn factorial(x) = ...;`) and built-in
    equation functions (Cos, Sin, Gauss, Get, ...) are left untouched --
    they're evaluated numerically by the TOPAS equation engine at
    refinement time, not by macro/text substitution, and some (like a
    recursive `fn factorial`) would infinite-loop a naive text expander.
  - The "#m_*" directive family was reverse-engineered from real usage
    in the bundled topas.inc (the manual documents only #m_argu, in one
    line) and validated against confirmed real tc.log expansions of
    LP_Factor, Zero_Error, and Simple_Axial_Model. #m_code / #m_code_
    refine / #m_eqn / #m_one_word specifically only occur, in the
    bundled library, inside the one (very widely used) If_Prm_Eqn_Rpt
    macro -- correct there, but a custom macro using them in a novel
    way could expose a gap. An #m_ifarg comparing against a literal
    other than "" (unseen in the bundled library) falls back to a plain
    string-equality check, which may not match TOPAS's own rule.
  - `#if (expr)` / `#elseif (expr)` can only be statically evaluated when
    it reduces to a comparison against Run_Number (see --run-number) or
    a name that was #define'd in the file being expanded. Anything else
    (e.g. a condition on a #prm-declared runtime parameter) cannot be
    known without actually running TOPAS -- both branches are kept in
    that case, each wrapped in a clearly labeled marker comment, rather
    than silently guessing one.
  - The runtime `if cond { } else { }` keyword (lowercase, distinct from
    the `#if` preprocessor directive) is never pruned, matching real
    TOPAS behavior -- both branches always survive expansion.
  - @-parameter auto-generated names use the same m<hash>_<n> shape seen
    in real tc.log output, but the hash is simply derived from the file
    name and an incrementing counter -- it will NOT match what TOPAS
    itself would generate. Only the structural behavior (the same name
    reused consistently at every occurrence of that one @ argument) is
    meaningful, not the exact string.
  - Macro overload resolution matches purely by argument count, exactly
    as documented -- except the one confirmed real-world edge case (see
    the beq-2-create.inp discussion in SKILL.md / console-output-and-
    errors.md) where a file-local macro colliding with a same-named,
    different-arity system macro can fail to resolve at runtime even
    though this script will still happily expand it.
  - Output line numbers will NOT match TOPAS's own "at LINE N" numbering
    (see references/macro-expansion-and-log-files.md for those exact
    rules) -- this tool favors a clean, readable expansion over
    line-for-line fidelity with tc.log.
  - #external_INP is intentionally NOT textually merged into its
    referencing file's own expansion -- confirmed via a real bundled
    before/after pair (references/examples/external_inp/ext_inp.inp and
    its own .out result) that TOPAS keeps each #external_INP target as
    its own separately loaded/saved file rather than inlining it. The
    directive line is left as-is in the parent's expansion, and each
    target's own expansion is appended afterward as a clearly labeled,
    clearly separate section (nesting handled, with cycle protection).
  - Both #ingest and #external_INP only resolve a LITERAL filename
    appearing in the source text -- like #include, a dynamically-built
    path ("$file can be a function of macros" per the manual) can't be
    resolved by this static tool.

Usage:
    python3 expand_inp_macros.py file.inp
    python3 expand_inp_macros.py file.inp -o expanded.inp
    python3 expand_inp_macros.py file.inp --run-number 1
"""

import sys
import os
import re
import argparse
import hashlib
import topas_install

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Prefer the macro library shipping with the user's OWN current TOPAS
# install (via the TOPAS_DIR environment variable -- see topas_install.py)
# over this skill's bundled snapshot, so expansion reflects the release
# actually in use rather than a copy that can go stale. Falls back to the
# bundled copy automatically if TOPAS_DIR isn't set/reachable.
MACRO_LIB_DIR, MACRO_LIB_FROM_LIVE_INSTALL = topas_install.get_inc_dir()

MAX_EXPANSION_PASSES = 60

IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# --- macro-body conditional/argument-inspection directives ("#m_*") ---
# These are TOPAS's own preprocessor mini-language used INSIDE macro
# bodies (not to be confused with the file-level #if/#ifdef family
# handled by preprocess_directives). They inspect the actual argument
# text bound to a parameter of the CURRENT macro invocation:
#   #m_argu p              -- if p's bound arg is bare '@', replace it
#                              (for the rest of this invocation) with a
#                              freshly auto-generated unique name.
#   #m_unique name          -- emit a freshly auto-generated unique name
#                              here, and bind `name` to it for the rest
#                              of this invocation (used for `local`/
#                              object names that must not collide across
#                              repeated invocations of the same macro).
#   #m_first_word src dest  -- bind `dest` to the first whitespace-
#                              separated token of src's current bound
#                              value, and emit that token here.
#   #m_ifarg p COND ... [#m_else ...] #m_endif
#                           -- conditional on p's bound value: COND is
#                              either the literal "" (true if blank),
#                              or one of #m_code / #m_code_refine /
#                              #m_eqn / #m_one_word (see eval_ifarg_cond
#                              below), or (rarely, unseen in the bundled
#                              topas.inc) a literal to compare against.
# These were reverse-engineered from real usage in topas.inc (there is
# no fuller written spec than the one-line mention of #m_argu in the
# manual's macro chapter), cross-checked against confirmed real tc.log
# expansions of LP_Factor, Zero_Error, Simple_Axial_Model. #m_code /
# #m_code_refine / #m_eqn / #m_one_word each occur only inside the one
# (very widely used) If_Prm_Eqn_Rpt macro in the bundled library --
# correct there, but any OTHER real-world macro using them in a novel
# way could expose a gap in this best-effort implementation.
RE_M_ARGU = re.compile(r"#m_argu\s+([A-Za-z_]\w*)")
RE_M_UNIQUE = re.compile(r"#m_unique\s+([A-Za-z_]\w*)")
RE_M_FIRST_WORD = re.compile(r"#m_first_word\s+([A-Za-z_]\w*)\s+([A-Za-z_]\w*)")
RE_M_IFARG = re.compile(
    r'#m_ifarg\s+([A-Za-z_]\w*)\s+(""|#m_code_refine\b|#m_code\b|#m_eqn\b|#m_one_word\b|[A-Za-z_]\w*)'
)
STOP_ELSE_OR_ENDIF = re.compile(r"#m_else\b|#m_endif\b")
STOP_ENDIF_ONLY = re.compile(r"#m_endif\b")

DEFINE_RE = re.compile(r"#define\s+([A-Za-z_]\w*)")
IFDEF_RE = re.compile(r"#ifdef\s+([A-Za-z_]\w*)")
IFNDEF_RE = re.compile(r"#ifndef\s+([A-Za-z_]\w*)")
IF_EXPR_RE = re.compile(r"#if\s*\(([^)]*)\)")
ELSEIF_EXPR_RE = re.compile(r"#elseif\s*\(([^)]*)\)")
ELSE_RE = re.compile(r"#else\b")
ENDIF_RE = re.compile(r"#endif\b")
RUN_NUMBER_CMP_RE = re.compile(r"Run_Number\s*==\s*(\d+)")


# ---------------------------------------------------------------------------
# Comment / string stripping (identical convention to check_inp_syntax.py:
# block comments -> collapse away entirely for a clean expansion; line
# comments -> stripped to end of line; quoted-string interiors left intact
# here since we're producing real output text, not just analyzing it).
# ---------------------------------------------------------------------------


def strip_comments(text):
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            depth = 1
            i += 2
            while i < n and depth > 0:
                if text[i] == "/" and i + 1 < n and text[i + 1] == "*":
                    depth += 1
                    i += 2
                elif text[i] == "*" and i + 1 < n and text[i + 1] == "/":
                    depth -= 1
                    i += 2
                else:
                    i += 1
            continue
        if c == "'":
            while i < n and text[i] != "\n":
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Preprocessor directives: #define, #ifdef/#ifndef/#if/#elseif/#else/#endif
# ---------------------------------------------------------------------------


def preprocess_directives(text, run_number, extra_defines=None):
    defines = set(m.group(1) for m in DEFINE_RE.finditer(text))
    if extra_defines:
        defines |= set(extra_defines)

    def eval_simple_expr(expr):
        """Return True/False if staticaly resolvable, else None."""
        expr = expr.strip()
        m = RUN_NUMBER_CMP_RE.fullmatch(expr)
        if m:
            return run_number == int(m.group(1))
        # bare identifier -- treat like #ifdef
        m = re.fullmatch(r"([A-Za-z_]\w*)", expr)
        if m:
            return m.group(1) in defines
        m = re.fullmatch(r"!\s*([A-Za-z_]\w*)", expr)
        if m:
            return m.group(1) not in defines
        return None

    lines = text.split("\n")
    out_lines = []
    # stack entries: {'resolved': True/False/None, 'taken': bool, 'done': bool}
    stack = []

    def currently_active():
        return all(f["taken"] for f in stack)

    for line in lines:
        if DEFINE_RE.search(line):
            continue  # drop #define lines from output

        m = IFDEF_RE.search(line)
        if m:
            taken = m.group(1) in defines
            stack.append({"taken": taken, "done": taken, "unresolved": False})
            continue
        m = IFNDEF_RE.search(line)
        if m:
            taken = m.group(1) not in defines
            stack.append({"taken": taken, "done": taken, "unresolved": False})
            continue
        m = IF_EXPR_RE.search(line)
        if m:
            result = eval_simple_expr(m.group(1))
            if result is None:
                # Can't resolve -- keep both branches, marked.
                stack.append({"taken": True, "done": False, "unresolved": True})
                out_lines.append(
                    f"' >>> expand_inp_macros.py: could not statically evaluate "
                    f"#if ({m.group(1)}) -- showing this branch; check the #else too <<<"
                )
            else:
                stack.append({"taken": result, "done": result, "unresolved": False})
            continue
        m = ELSEIF_EXPR_RE.search(line)
        if m:
            if stack:
                top = stack[-1]
                if top["unresolved"]:
                    out_lines.append(
                        f"' >>> expand_inp_macros.py: could not statically evaluate "
                        f"#elseif ({m.group(1)}) -- showing this branch too <<<"
                    )
                    top["taken"] = True
                elif not top["done"]:
                    result = eval_simple_expr(m.group(1))
                    if result is None:
                        top["unresolved"] = True
                        top["taken"] = True
                        out_lines.append(
                            f"' >>> expand_inp_macros.py: could not statically evaluate "
                            f"#elseif ({m.group(1)}) -- showing this branch too <<<"
                        )
                    else:
                        top["taken"] = result
                        top["done"] = result
                else:
                    top["taken"] = False
            continue
        if ELSE_RE.search(line):
            if stack:
                top = stack[-1]
                if top["unresolved"]:
                    top["taken"] = True
                else:
                    top["taken"] = not top["done"]
            continue
        if ENDIF_RE.search(line):
            if stack:
                stack.pop()
            continue

        if stack and not currently_active():
            continue
        out_lines.append(line)

    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
# #include resolution: tried, in order, relative to the REFERENCING file's
# own directory (the common real-world case -- a project-local .inc/.inp
# file sitting alongside the main file, e.g. "WPPM_macros.inc",
# "myrigidbodies.inp", confirmed via many real files across the bundled
# example corpus), then against the system .inc macro library (topas.inc's
# own directory, via TOPAS_DIR). A target that's dynamically built (a
# macro call like 'File("ceo2.inp")', or a token-paste expression like
# 'Double_Quote##ROOT##pdf-generate.inc##Double_Quote') can't be resolved
# here at all -- it isn't a literal filename yet -- and is deliberately
# left unmatched by INCLUDE_RE (no '(' or '#' in either alternative) so it
# falls through to the later, post-macro-expansion resolution stage in
# _expand_single_file instead.
# ---------------------------------------------------------------------------

INCLUDE_RE = re.compile(r'#include\s+(?:"([^"]+)"|([^\s"(#]+))', re.IGNORECASE)

# #ingest and #external_INP are two DIFFERENT user-file-linking
# directives (documented in 01-syntax-and-parameters.md), distinct from
# both #include (system .inc macro library) and macro expansion:
#
#   #ingest $file       -- "ingested files are treated as part of the
#                          original INP file" (the manual's own words):
#                          textually merges the target file's content in
#                          place, same spirit as #include but resolved
#                          relative to the REFERENCING file's own
#                          directory rather than the system .inc
#                          library, and nestable (an ingested file can
#                          itself #ingest another).
#   #external_INP $file -- the opposite: confirmed via a real bundled
#                          before/after pair (references/examples/
#                          external_inp/ext_inp.inp + its .out result)
#                          that TOPAS does NOT merge this into the
#                          parent's own output -- the directive line
#                          itself survives verbatim even after a real
#                          refinement run. This matches the documented
#                          GUI behavior of each #external_INP target
#                          being independently re-saveable as its own
#                          OUT/INP file. Also documented as nestable.
#
# Both allow "$file [to be] a function of macros" (i.e. a computed
# path) -- like #include's own dynamic-path case, this tool can only
# resolve a LITERAL filename appearing in the source text, not one
# assembled at macro-expansion time.
INGEST_RE = re.compile(r'#ingest\s+"?([^"\s]+)"?')
EXTERNAL_INP_RE = re.compile(r'#external_INP\s+"?([^"\s]+)"?')


def resolve_includes(text, base_dir, already_included=None):
    if already_included is None:
        already_included = set()

    def repl(m):
        raw_target = m.group(1) if m.group(1) is not None else m.group(2)

        # An unquoted bare token with no '.' at all (e.g. "Path") is far
        # more likely a macro/identifier name meant to be resolved to a
        # real filename only after macro expansion (the late
        # _flag_unresolved_include stage in _expand_single_file) than a
        # real filename typo -- every literal filename actually seen
        # across the bundled example corpus carries an extension. Leave
        # it untouched here rather than eagerly failing and re-embedding
        # a warning + the original directive text, which would otherwise
        # get macro-expanded itself and double-processed by the later
        # stage (confirmed by a real synthetic test: a bodiless macro
        # named 'Path' used as '#include Path' produced a spurious
        # "could not resolve" note ahead of the correctly-resolved
        # content, instead of resolving cleanly once at the late stage).
        if "." not in raw_target:
            return m.group(0)

        fname = os.path.basename(raw_target)

        # 1. Relative to the referencing file's own directory -- the
        #    common real case (a project-local .inc/.inp file sitting
        #    alongside the main file).
        fpath = os.path.normpath(os.path.join(base_dir, raw_target))
        if not os.path.isfile(fpath):
            # 2. Fall back to the system .inc macro library (a bare
            #    filename like "pdf.inc", not a project file).
            fpath = None
            for candidate in os.listdir(MACRO_LIB_DIR) if os.path.isdir(MACRO_LIB_DIR) else []:
                if candidate.lower() == fname.lower():
                    fpath = os.path.join(MACRO_LIB_DIR, candidate)
                    break

        if fpath is None or not os.path.isfile(fpath):
            return (
                f"' >>> expand_inp_macros.py: could not resolve #include {raw_target} "
                f"(not found relative to {base_dir} or in {MACRO_LIB_DIR}; set TOPAS_DIR if this "
                f"should resolve against your real install -- left unexpanded) <<<\n" + m.group(0)
            )

        key = os.path.normcase(os.path.abspath(fpath))
        if key in already_included:
            return ""
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                included_text = f.read()
        except OSError:
            return m.group(0)
        included_text = strip_comments(included_text)
        return resolve_includes(
            included_text, os.path.dirname(os.path.abspath(fpath)), already_included | {key}
        )

    return INCLUDE_RE.sub(repl, text)


def resolve_ingests(text, base_dir, already_ingested=None):
    """
    Textually merge #ingest targets in place (recursively -- an ingested
    file can itself #ingest another), resolved relative to `base_dir`
    (the directory of the file that referenced it, NOT the system .inc
    library -- #ingest targets are the user's own project files, e.g.
    "common_str.txt", not macro libraries).
    """
    if already_ingested is None:
        already_ingested = set()

    def repl(m):
        fname = m.group(1)
        fpath = os.path.normpath(os.path.join(base_dir, fname))
        if fpath in already_ingested:
            return (
                f"' >>> expand_inp_macros.py: #ingest {fname} skipped (circular ingest chain) <<<"
            )
        if not os.path.isfile(fpath):
            return (
                m.group(0) + f"  ' >>> expand_inp_macros.py: could not resolve #ingest {fname} "
                f"(file not found relative to {base_dir}) <<<"
            )
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                ingested_text = f.read()
        except OSError:
            return m.group(0)
        ingested_text = strip_comments(ingested_text)
        return resolve_ingests(ingested_text, os.path.dirname(fpath), already_ingested | {fpath})

    return INGEST_RE.sub(repl, text)


def collect_external_inp_targets(text, base_dir, already_seen):
    """
    Find #external_INP targets in `text` (resolved relative to
    base_dir), recursively descending into each target file to also
    collect ITS #external_INP targets (nesting, per the manual).
    `already_seen` is a set of normalized paths, shared across the
    whole recursive walk, to guard against a circular reference.
    Returns a list of (declared_name, resolved_path) in first-seen
    order; does not read macro/comment content here, just locates
    files -- the actual per-file expansion happens in expand_file.
    """
    found = []
    for m in EXTERNAL_INP_RE.finditer(text):
        fname = m.group(1)
        fpath = os.path.normpath(os.path.join(base_dir, fname))
        if fpath in already_seen:
            continue
        already_seen.add(fpath)
        found.append((fname, fpath))
        if os.path.isfile(fpath):
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    sub_text = f.read()
            except OSError:
                continue
            found.extend(
                collect_external_inp_targets(sub_text, os.path.dirname(fpath), already_seen)
            )
    return found


# ---------------------------------------------------------------------------
# Macro definition harvesting (name -> list of (params, body) per arity)
# ---------------------------------------------------------------------------


def find_matching_brace(text, open_idx):
    """
    open_idx points at a '{'. Returns index just after the matching '}',
    counting nested '{'/'}' pairs so a macro body containing its own
    braces (an `if cond { } else { }` block, a nested object, ...) is
    captured as one unit rather than stopping at the first inner '}'.

    Skips over double-quoted string interiors while counting -- a literal
    '{' or '}' inside a string (e.g. a filename like "foo}bar.xy") is
    real text, not structural nesting, and must not be counted as one
    (confirmed to matter: without this, such a string closed the macro
    body early and left everything after it as mangled trailing text).
    Comments are NOT specially handled here since callers already strip
    them (via strip_comments) before this runs.
    """
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 1
            i += 1  # skip the closing quote itself (or run off the end)
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def parse_param_list(params_str):
    """
    Returns (names, amp_names) where amp_names is the subset of `names`
    declared with a leading '&' (e.g. 'macro divide(& a, & b)'). Per the
    manual's "Superfluous parentheses and the '&' Type for macros",
    an &-declared argument has its substituted value wrapped in one
    pair of parentheses at every point it's referenced in the macro
    body, so e.g. `divide(a + b, c - d)` expands to `(a + b) / (c - d)`
    instead of the precedence-broken `a + b / c - d`.
    """
    params_str = params_str.strip()
    if params_str == "":
        return [], set()
    parts = [p.strip() for p in params_str.split(",")]
    cleaned = []
    amp_names = set()
    for p in parts:
        is_amp = p.startswith("&")
        p = re.sub(r"^&\s*", "", p)
        cleaned.append(p)
        if is_amp:
            amp_names.add(p)
    return cleaned, amp_names


def extract_macro_defs(text):
    """
    Returns a dict: name -> {arity: (params_list, body_text, self_paren,
    amp_params)} for parenthesized macros, plus a separate dict name ->
    (body_text, self_paren) for bodiless ('macro Name { ... }') macros.
    Also returns the text with every macro DEFINITION removed (they emit
    nothing at their own location -- only invocations expand).

    `self_paren` is True when the definition used the '& before the name'
    form ('macro & Name(...) { ... }'). Per the manual's "Superfluous
    parentheses and the '&' Type for macros", that wraps the macro's
    entire expansion result in one pair of parentheses at each call
    site -- needed when the result is spliced into a larger expression
    with higher-precedence operators (e.g. real topas.inc: 'macro &
    CeV(c, v) { CV(c, v) }').
    """
    arity_macros = {}
    bodiless_macros = {}
    out = []
    i = 0
    n = len(text)
    macro_kw_re = re.compile(r"\bmacro\s+(&\s+)?([A-Za-z_]\w*)\s*")
    while i < n:
        m = macro_kw_re.match(text, i)
        if not m:
            out.append(text[i])
            i += 1
            continue
        self_paren = m.group(1) is not None
        name = m.group(2)
        j = m.end()
        if j < n and text[j] == "(":
            depth = 0
            k = j
            while k < n:
                if text[k] == "(":
                    depth += 1
                elif text[k] == ")":
                    depth -= 1
                    if depth == 0:
                        k += 1
                        break
                k += 1
            params_str = text[j + 1 : k - 1]
            params, amp_params = parse_param_list(params_str)
            # find the opening brace after the param list
            b = k
            while b < n and text[b] not in "{;":
                b += 1
            if b < n and text[b] == "{":
                end = find_matching_brace(text, b)
                if end == -1:
                    out.append(text[i:j])
                    i = j
                    continue
                body = text[b + 1 : end - 1]
                arity_macros.setdefault(name, {})[len(params)] = (
                    params,
                    body,
                    self_paren,
                    amp_params,
                )
                i = end
                continue
        elif j < n and text[j] == "{":
            end = find_matching_brace(text, j)
            if end == -1:
                out.append(text[i:j])
                i = j
                continue
            body = text[j + 1 : end - 1]
            bodiless_macros[name] = (body, self_paren)
            i = end
            continue
        # 'macro Name' not followed by '(' or '{' -- not a definition we
        # recognize; emit as-is.
        out.append(text[i : m.end()])
        i = m.end()
    return arity_macros, bodiless_macros, "".join(out)


def load_library_macros():
    arity_macros = {}
    bodiless_macros = {}
    try:
        fnames = os.listdir(MACRO_LIB_DIR)
    except OSError:
        return arity_macros, bodiless_macros
    for fname in sorted(fnames):
        fpath = os.path.join(MACRO_LIB_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        text = strip_comments(text)
        am, bm, _ = extract_macro_defs(text)
        for name, arities in am.items():
            arity_macros.setdefault(name, {}).update(arities)
        bodiless_macros.update(bm)
    return arity_macros, bodiless_macros


# ---------------------------------------------------------------------------
# Call-site argument parsing
# ---------------------------------------------------------------------------


def parse_call_args(text, paren_open_idx):
    """paren_open_idx points at '('. Returns (arg_strings, idx_after_close_paren)."""
    depth = 0
    i = paren_open_idx
    n = len(text)
    args = []
    current = []
    while i < n:
        c = text[i]
        if c == "(":
            depth += 1
            if depth > 1:
                current.append(c)
        elif c == ")":
            depth -= 1
            if depth == 0:
                args.append("".join(current).strip())
                i += 1
                break
            current.append(c)
        elif c == "," and depth == 1:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(c)
        i += 1
    return args, i


# ---------------------------------------------------------------------------
# @-parameter auto-naming
# ---------------------------------------------------------------------------


class AutoNamer:
    def __init__(self, seed):
        self.prefix = "m" + hashlib.md5(seed.encode("utf-8")).hexdigest()[:8]
        self.uprefix = "u" + hashlib.md5((seed + "_unique").encode("utf-8")).hexdigest()[:8]
        self.counter = 0
        self.ucounter = 0

    def next_name(self):
        """For @-flagged macro arguments (#m_argu)."""
        name = f"{self.prefix}_{self.counter}"
        self.counter += 1
        return name

    def next_unique(self):
        """For #m_unique local/object names."""
        name = f"{self.uprefix}_{self.ucounter}"
        self.ucounter += 1
        return name


# ---------------------------------------------------------------------------
# Macro expansion
# ---------------------------------------------------------------------------


def eval_ifarg_cond(cond, value, is_refine):
    """
    Evaluate one #m_ifarg condition against the CURRENT bound value of
    its parameter (as a plain string). See the RE_M_* block near the
    top of this file for what each condition means; reverse-engineered
    from real topas.inc usage (Not_Blank, CV, If_Prm_Eqn_Rpt, ...).
    """
    v = value.strip()
    if cond == '""':
        return v == ""
    if cond == "#m_code":
        # Non-blank and not itself an equation assignment.
        return v != "" and not v.startswith("=")
    if cond == "#m_code_refine":
        # In principle distinct from #m_code (whether the "code" is
        # specifically a refined parameter vs. a fixed/reused one), but
        # that distinction can only be recovered from a per-invocation
        # @-flag that doesn't survive a further level of macro-to-macro
        # delegation (e.g. Simple_Axial_Model's own #m_argu resolves
        # before it calls If_Prm_Eqn_Rpt, which starts a fresh binding
        # scope with no memory of that). Approximated as identical to
        # #m_code: in every real-world case seen in topas.inc, treating
        # it as "true whenever non-blank" means the fuller (bounds-
        # including) branch is emitted, which is the safer default --
        # under-showing refinement bounds would be a more misleading
        # gap than showing bounds that TOPAS itself might have omitted.
        return v != "" and not v.startswith("=")
    if cond == "#m_eqn":
        return v.startswith("=")
    if cond == "#m_one_word":
        return v != "" and len(v.split()) == 1
    # A literal bareword/string comparison -- not seen in the bundled
    # topas.inc for anything other than "", but handled generically.
    return v == cond


def process_range(text, start, bindings, refine, auto_namer, stop_re):
    """
    Recursive-descent interpreter for one macro invocation's body text.
    Scans text[start:] emitting literal characters, substituting bound
    parameter names (plain textual substitution; an &-declared argument's
    bound value already carries its wrapping parentheses -- added by the
    caller before this function ever sees it, see process_macro_invocation),
    and resolving #m_argu / #m_unique / #m_first_word /
    #m_ifarg-#m_else-#m_endif directives inline as it goes.

    Note this function does NOT apply the separate '&-before-macro-name'
    parenthesization (e.g. real topas.inc: 'macro & CeV(c, v) { CV(c, v) }')
    -- that wraps the whole RESULT of this call, and is applied by the
    caller in expand_macros() after process_macro_invocation() returns.

    If `stop_re` is given, stops (without consuming) as soon as it
    matches at the current scan position -- used so a nested #m_ifarg's
    own #m_else/#m_endif doesn't get swallowed by an enclosing call.

    Returns (emitted_text, index_after_stop_match_or_len, stop_match).
    """
    buf = []
    i = start
    n = len(text)
    while i < n:
        if stop_re is not None:
            sm = stop_re.match(text, i)
            if sm:
                return "".join(buf), sm.end(), sm

        m = RE_M_ARGU.match(text, i)
        if m:
            pname = m.group(1)
            val = bindings.get(pname, "")
            if val.strip() == "@" or re.fullmatch(r"@[A-Za-z_]\w*", val.strip()):
                bindings[pname] = auto_namer.next_name()
                refine[pname] = True
            i = m.end()
            continue

        m = RE_M_UNIQUE.match(text, i)
        if m:
            pname = m.group(1)
            newname = auto_namer.next_unique()
            bindings[pname] = newname
            buf.append(newname)
            i = m.end()
            continue

        m = RE_M_FIRST_WORD.match(text, i)
        if m:
            src_name, dest_name = m.group(1), m.group(2)
            val = bindings.get(src_name, "").strip()
            parts = val.split()
            first = parts[0] if parts else ""
            bindings[dest_name] = first
            buf.append(first)
            i = m.end()
            continue

        m = RE_M_IFARG.match(text, i)
        if m:
            pname, cond = m.group(1), m.group(2)
            value = bindings.get(pname, "")
            truth = eval_ifarg_cond(cond, value, refine.get(pname, False))
            true_text, after, stopmatch = process_range(
                text, m.end(), bindings, refine, auto_namer, STOP_ELSE_OR_ENDIF
            )
            if stopmatch is not None and stopmatch.group(0) == "#m_else":
                false_text, after2, _ = process_range(
                    text, after, bindings, refine, auto_namer, STOP_ENDIF_ONLY
                )
                i = after2
            else:
                false_text = ""
                i = after
            buf.append(true_text if truth else false_text)
            continue

        idm = IDENTIFIER_RE.match(text, i)
        if idm:
            word = idm.group(0)
            if word in bindings:
                buf.append(bindings[word])
            else:
                buf.append(word)
            i = idm.end()
            continue

        buf.append(text[i])
        i += 1

    return "".join(buf), i, None


def process_macro_invocation(body, params, args, auto_namer, amp_params=None):
    """
    Bind `params` to `args` (plain text, trimmed) and interpret the
    macro body against those bindings, resolving #m_* directives and
    substituting parameter references in place. See process_range.

    A param in `amp_params` (declared 'macro Name(& p, ...)') gets its
    bound value wrapped in one pair of parentheses, so every reference
    to it inside the body is auto-parenthesized -- see parse_param_list.
    """
    amp_params = amp_params or set()
    bindings = {}
    refine = {}
    for pname, arg in zip(params, args):
        val = arg.strip()
        if pname in amp_params:
            val = "(" + val + ")"
        bindings[pname] = val
        refine[pname] = False
    text, _, _ = process_range(body, 0, bindings, refine, auto_namer, None)
    return text


def expand_macros(text, arity_macros, bodiless_macros, auto_namer, warnings):
    """
    Fixed-point expansion: repeatedly scan for calls to known macros and
    splice in their (recursively-substituted) bodies, until no further
    known macro name is found as a call site, or MAX_EXPANSION_PASSES is
    hit (bails out with a warning rather than looping forever -- e.g. if
    a macro's body somehow calls itself).
    """
    for _pass in range(MAX_EXPANSION_PASSES):
        changed = False
        out = []
        i = 0
        n = len(text)
        while i < n:
            m = IDENTIFIER_RE.match(text, i)
            if not m:
                out.append(text[i])
                i += 1
                continue
            name = m.group(0)
            j = m.end()

            # Skip if this identifier is itself a macro DEFINITION site
            # (shouldn't occur post-extraction, but be defensive).
            prefix = text[max(0, i - 10) : i]
            if re.search(r"\bmacro\s*$", prefix):
                out.append(name)
                i = j
                continue

            j2 = j
            while j2 < n and text[j2] in " \t":
                j2 += 1
            is_call = j2 < n and text[j2] == "("

            if is_call and name in arity_macros:
                args, after = parse_call_args(text, j2)
                arity = len(args) if args != [""] else 0
                if arity in arity_macros[name]:
                    params, body, self_paren, amp_params = arity_macros[name][arity]
                    substituted = process_macro_invocation(
                        body, params, args, auto_namer, amp_params
                    )
                    if self_paren:
                        substituted = "(" + substituted.strip() + ")"
                    # Normalize whitespace within this invocation's own
                    # expansion to single spaces. Real tc.log output
                    # shows a library macro's internal formatting
                    # (arbitrary indentation/line-breaks chosen by
                    # whoever wrote topas.inc) collapsing to a single
                    # continuous token run -- e.g. LP_Factor's multi-
                    # line #m_ifarg-laden body ends up entirely on one
                    # output line. This can occasionally over-collapse
                    # a macro that was deliberately called with a multi-
                    # line argument, but that's a cosmetic trade-off,
                    # not a correctness one (whitespace is insignificant
                    # to TOPAS's own parser either way).
                    substituted = " " + re.sub(r"\s+", " ", substituted).strip() + " "
                    out.append(substituted)
                    i = after
                    changed = True
                    continue
                else:
                    out.append(text[i:after])
                    i = after
                    continue
            elif name in bodiless_macros:
                body, self_paren = bodiless_macros[name]
                substituted = process_macro_invocation(body, [], [], auto_namer)
                if self_paren:
                    substituted = "(" + substituted.strip() + ")"
                substituted = " " + re.sub(r"\s+", " ", substituted).strip() + " "
                out.append(substituted)
                i = j
                changed = True
                continue
            else:
                out.append(name)
                i = j
        text = "".join(out)
        if not changed:
            break
    else:
        warnings.append(
            f"Warning: expansion did not reach a fixed point after {MAX_EXPANSION_PASSES} "
            f"passes -- output may be incomplete (possible recursive macro?)."
        )
    return text


def _expand_single_file(path, run_number=0):
    """
    Expand ONE file's own content: #ingest merging, #include (.inc
    library) resolution, #define/#if family pruning, and macro
    expansion. Does NOT descend into #external_INP targets -- those are
    handled separately by expand_file, since (per confirmed real
    before/after behavior) they are NOT textually merged by TOPAS
    itself.
    """
    with open(path, encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    warnings = []
    base_dir = os.path.dirname(os.path.abspath(path))

    text = strip_comments(raw)
    text = resolve_ingests(text, base_dir)
    text = resolve_includes(text, base_dir)
    text = preprocess_directives(text, run_number)

    file_arity_macros, file_bodiless_macros, text = extract_macro_defs(text)

    lib_arity_macros, lib_bodiless_macros = load_library_macros()
    merged_arity = {k: dict(v) for k, v in lib_arity_macros.items()}
    for name, arities in file_arity_macros.items():
        merged_arity.setdefault(name, {}).update(arities)
    merged_bodiless = dict(lib_bodiless_macros)
    merged_bodiless.update(file_bodiless_macros)

    auto_namer = AutoNamer(os.path.basename(path))
    expanded = expand_macros(text, merged_arity, merged_bodiless, auto_namer, warnings)

    # Resolve the '##' token-pasting/concatenation operator used
    # throughout macro bodies for building dynamic strings/paths (e.g.
    # "root##lam\\##lam_file##.lam"): once argument substitution has
    # happened, join adjacent tokens by simply dropping the marker and
    # any surrounding whitespace.
    expanded = re.sub(r"\s*##\s*", "", expanded)

    # Any "#include" surviving this far reached a dynamically-built path
    # (e.g. a wavelength file assembled via ROOT##lam\\##name##.lam
    # inside a library macro like Load_Lam/CuKa1). `ROOT` is a TOPAS
    # built-in reserved word (never a literal #define/macro in topas.inc
    # itself -- confirmed by grep) that the running kernel substitutes
    # for its own install directory, WITH a trailing separator already
    # included. Resolve it against TOPAS_DIR (same env var used
    # everywhere else in this skill) before giving up, rather than
    # always flagging it as unresolvable.
    def _strip_macro_defs_for_late_include(inc_text):
        """
        Content inlined at THIS late stage (after the file's own main
        extract_macro_defs()/expand_macros() pass has already run) still
        needs its own macro DEFINITIONS dropped before splicing in -- the
        same thing extract_macro_defs() already does automatically for a
        normal #include resolved earlier in the pipeline (resolve_includes()
        runs before extract_macro_defs(), so that content's macro defs get
        harvested/removed for free). Without this, a macro definition
        sitting in a late-resolved include target (a project .inc file
        reached only after a dynamic/macro-built path, or a system ROOT
        target) would leak into the final expanded output verbatim instead
        of being consumed as a definition -- confirmed as a real gap by the
        user (TOPAS-Academic's author) directly. Any CALLS to such a
        late-defined macro are NOT themselves expanded (this file's macro
        harvesting/substitution has already finished by this point) -- an
        accepted limitation of inlining this late, not attempted here.
        """
        _, _, cleaned = extract_macro_defs(inc_text)
        return cleaned

    def _flag_unresolved_include(m):
        path_part = m.group(1)
        if path_part.startswith("ROOT"):
            topas_dir, found = topas_install.get_topas_dir()
            if found:
                candidate = os.path.normpath(topas_dir + os.sep + path_part[len("ROOT") :])
                if os.path.isfile(candidate):
                    # Actually inline the resolved file's content, same as
                    # resolve_includes() does for a literal .inc library
                    # include -- a real gap found and fixed here: this
                    # branch used to just rewrite the #include line to the
                    # resolved absolute path ('#include "C:\...\cuka5.lam"'),
                    # leaving the directive itself unexpanded, rather than
                    # merging the target's actual content the way #include
                    # is documented to behave. Confirmed on a real target
                    # (ta-web2\lam\cuka5.lam, reached via CuKa5's own
                    # ROOT##lam\\##name##.lam-built path): it's a genuine
                    # TOPAS 'lam { ... }' emission-profile block meant to be
                    # merged in place, not a reference left for the user to
                    # separately follow.
                    try:
                        with open(candidate, encoding="utf-8", errors="ignore") as f:
                            included_text = f.read()
                    except OSError:
                        return f'#include "{candidate}"'
                    return _strip_macro_defs_for_late_include(strip_comments(included_text))
                return (
                    m.group(0) + f"  ' >>> expand_inp_macros.py: ROOT resolved to "
                    f"{candidate} via TOPAS_DIR but no file was found there <<<"
                )
        else:
            # Not ROOT-prefixed: per TOPAS's own rule (confirmed directly
            # by the user, TOPAS-Academic's author), "#include operates
            # from the INP file directory unless the full path is given"
            # -- the same rule resolve_includes() already applies to a
            # literal (pre-macro-expansion) #include target; this branch
            # covers one only known after macro expansion, e.g. a macro
            # call used to build the path (#include File("ceo2.inp")).
            stripped = path_part.strip('"')
            candidate = (
                stripped
                if os.path.isabs(stripped)
                else os.path.normpath(os.path.join(base_dir, stripped))
            )
            if os.path.isfile(candidate):
                try:
                    with open(candidate, encoding="utf-8", errors="ignore") as f:
                        included_text = f.read()
                except OSError:
                    return f'#include "{candidate}"'
                return _strip_macro_defs_for_late_include(strip_comments(included_text))
        return (
            m.group(0)
            + "  ' >>> expand_inp_macros.py: #include not resolved (dynamic/system path, file not bundled) <<<"
        )

    expanded = re.sub(r"#include\s+(\S+)", _flag_unresolved_include, expanded)

    # Collapse runs of blank lines left behind by dropped directives/defs
    # for readability.
    expanded = re.sub(r"\n[ \t]*\n(\s*\n)+", "\n\n", expanded)

    return expanded.strip() + "\n", warnings


def expand_file(path, run_number=0, _already_external=None):
    """
    Full expansion of `path`, including locating (and separately
    expanding) any #external_INP targets it references. Per confirmed
    real behavior (references/examples/external_inp/ext_inp.inp vs. its
    own .out result), #external_INP targets are NOT merged into the
    parent's token stream by TOPAS -- each stays its own independently
    loaded/saved file. To respect that while still giving visibility
    into what those files contain, the parent's own #external_INP
    directive lines are left untouched in its own expansion, and each
    referenced file's own expansion is appended afterward as a clearly
    separate, clearly labeled section (handling nesting, since an
    #external_INP target may itself reference further ones).
    """
    if _already_external is None:
        _already_external = set()

    expanded, warnings = _expand_single_file(path, run_number=run_number)

    base_dir = os.path.dirname(os.path.abspath(path))
    with open(path, encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    external_targets = collect_external_inp_targets(
        strip_comments(raw), base_dir, _already_external
    )

    sections = [expanded]
    for fname, fpath in external_targets:
        if not os.path.isfile(fpath):
            warnings.append(f"Warning: #external_INP target '{fname}' not found at {fpath}.")
            continue
        sub_expanded, sub_warnings = _expand_single_file(fpath, run_number=run_number)
        warnings.extend(f"[{fname}] {w}" for w in sub_warnings)
        sections.append(
            f"\n' >>> expand_inp_macros.py: below is #external_INP {fname} -- TOPAS keeps this "
            f"as a SEPARATE linked file (not merged into the file above); shown here for reference only <<<\n"
            + sub_expanded
        )

    return "\n".join(sections), warnings


def main():
    parser = argparse.ArgumentParser(
        description="Expand TOPAS macros in a .inp file (best-effort static approximation of tc.log)."
    )
    parser.add_argument("inp_file")
    parser.add_argument(
        "-o", "--output", help="Write expanded text to this file instead of stdout."
    )
    parser.add_argument(
        "--run-number",
        type=int,
        default=0,
        help="Value to statically substitute for Run_Number in #if/#elseif conditions (default 0).",
    )
    args = parser.parse_args()

    expanded, warnings = expand_file(args.inp_file, run_number=args.run_number)

    if MACRO_LIB_FROM_LIVE_INSTALL:
        print(
            f"(Using the live TOPAS install's own macro library at {MACRO_LIB_DIR}, "
            f"via TOPAS_DIR.)",
            file=sys.stderr,
        )
    elif not os.path.isdir(MACRO_LIB_DIR):
        if os.environ.get("TOPAS_DIR", "").strip():
            print(
                f"Warning: TOPAS_DIR is set but no topas.inc was found under it "
                f"({MACRO_LIB_DIR}); library macros (topas.inc, pdf.inc, ...) won't expand -- "
                f"only macros defined in this file itself will.",
                file=sys.stderr,
            )
        else:
            print(
                "Warning: TOPAS_DIR is not set, so this skill has no macro library to expand "
                "against (it no longer bundles a copy -- see 'Locating your TOPAS installation' "
                "in SKILL.md). Set TOPAS_DIR to your TOPAS install root; until then, only macros "
                "defined in this file itself will expand.",
                file=sys.stderr,
            )

    for w in warnings:
        print(w, file=sys.stderr)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(expanded)
        print(f"Expanded output written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(expanded)


if __name__ == "__main__":
    main()
