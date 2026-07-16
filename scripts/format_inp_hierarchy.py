#!/usr/bin/env python3
"""
format_inp_hierarchy.py -- Reindent a TOPAS .inp file to reflect its
hierarchical structure, using 3 spaces per indent level (never a tab).

If a line packs more than one keyword/statement onto it, it is left
exactly as-is (not split) -- the WHOLE line is just indented as a single
unit, at the level determined by its first keyword (see below). Beyond
leading-whitespace/indentation, this script also collapses unnecessary
internal spacing on most lines: any run of whitespace becomes a single
space, except it's dropped entirely right after `(`, right before `)`,
right before a `,`, and right before any `(` (`Radius(          173)` ->
`Radius(173)`, `CS_L(csl   ,   203.816479)` -> `CS_L(csl, 203.816479)`,
`bkg   @  1  2   3` -> `bkg @ 1 2 3`). One exception, where spacing is
intentional and left completely untouched by that pass: anything inside
a `C_matrix_normalized { ... }` block (TOPAS's own fixed-width
correlation matrix output) -- as well as, on any line, whatever is
inside `/* */`, `'...`, or `"..."`.

Consecutive `site` lines (and, separately, `la`/`lo`/`lh` lam
emission-profile lines) get their own treatment instead of the generic
collapse-to-one-space rule: this script runs fix_columns.py's own
column-alignment logic (imported directly, so the two scripts can never
drift apart) over the whole file *before* reindenting, so keywords like
x/y/z/occ/beq line up vertically within each run of consecutive `site`
lines, exactly as if fix_columns.py had been run first.

Why this isn't pure brace-counting: a lot of TOPAS's real structure has
no braces at all. `xdd`/`hkl_Is`/`xdd_Is` phases and the `str` structures
inside them are conventionally indented by every real example in this
project's corpus, but none of that nesting is delimited by `{ }` -- a
`str` block simply runs until the next `str`/phase keyword or the file
ends (confirmed directly against real corpus files during this skill's
own development; see SKILL.md's "Building a supercell" section). So this
formatter tracks TWO things together:

  1. Genuine `{ }` brace depth (macro bodies, C_matrix_normalized,
     system_before_save_OUT, etc.) -- the general, always-correct case.
  2. A stack of "open implicit sections", pushed/popped based on TOPAS's
     own keyword hierarchy: the "Data structures" section of
     references/21-keyword-index.md (Ttop/Tcomm_2/Txdd/Tstr_details/...),
     the same schema topas_keyword_tree.py already parses for its
     keyword-hierarchy browser. Confirmed directly by the user (TOPAS-
     Academic's author): "indentation comes from keyword hierarchy;
     therefore please look at the keyword hierarchy when doing
     indenting" -- this replaced an earlier, purely hand-curated
     RANK_KEYWORDS table. build_keyword_children_map() reuses
     topas_keyword_tree.py's own parser (extract_data_structures_block/
     parse_hierarchy/Node/TYPE_REF_RE) to build {keyword: {valid child
     keywords}}, transparently resolving type-mixin references (a bare
     Txxx line means "insert that type's own members here too, at the
     SAME level" -- see topas_keyword_tree.py's own docstring for why)
     and unioning children across every place a keyword occurs in the
     schema (`str` is a member of both Txdd and Txdd_scr; its resolved
     children merge Tstr_details + Thkl_lat + Tcomm_1_2_phase_1_2 +
     Tmin_max_rs + rigid + Tspace_group; etc.).

     Only keywords with a non-empty resolved children set ever open a
     new section ("section-openers": xdd, str, site, hkl_Is, xo_Is,
     d_Is, lam, ...) -- everything else (scale, bkg, prm, axial_conv,
     cell_mass, space_group, ...) is ordinary content that never itself
     changes the indent level, it just sits at whatever level is
     currently open. This is the same fallback rule the old
     RANK_KEYWORDS design used, just with a much larger, schema-derived
     set of recognized section-openers instead of a 2-entry hand list.

     A section-opener closes any open section it isn't a recognized
     child of -- but "recognized child of" means something different
     depending on how open-ended that section is, so there are two
     closing rules, both derived from the schema rather than hand-picked
     per keyword (see _is_wide_section): a "wide" section's resolved
     children reach TOPAS's general refinement-content mixin (Tcomm_2 --
     detected via `prm` being reachable, since everywhere Tcomm_2 is
     mixed in also accepts prm/local) -- true for xdd/str/hkl_Is/xo_Is/
     d_Is -- so it's only closed by ANOTHER section-opener it doesn't
     recognize as a child; ordinary content never closes it. A "narrow"
     section (no `prm` reachable -- true for `site` and `lam`, both of
     which have a small, fixed field list and nothing else) is closed by
     ANY keyword at all that isn't one of its own recognized children --
     e.g. `site`'s adps/u11 lines don't leak into the next `site`, and
     `lam`'s la/ymin_on_ymax lines don't leak into the `axial_conv` that
     follows a lam block.

Known limitation, stated plainly rather than overclaiming: the formal
Data-structures schema documents `lam`'s own ymin_on_ymax/
no_th_dependence/Lam/calculate_Lam fields as brackets nested inside
`lam`'s own single schema line (so those resolve automatically), but
`la` (and the lo/lh/lg fields packed onto the same real-file line as it)
is only ever connected to `lam` by PROSE immediately below it in
21-keyword-index.md's alphabetical listing ("[la E lo E [lh E] | [lg E]
...]... Defines an emission profile ... where each la determines an
emission profile line") -- never through any bracket nesting a parser
can see. PROSE_LINKED_CHILDREN below is the one narrow, explicitly-
justified supplement this couldn't avoid; everything else the
indentation engine treats as a section or a child is derived straight
from the schema.

Separately, a VERBATIM_BLOCK_KEYWORDS block's own '{ }' (currently just
C_matrix_normalized) does NOT add an indent level the way a normal brace
pair does -- its content, including the matrix's own header row, stays
level with the keyword itself, matching TOPAS's own auto-generated
report formatting rather than ordinary hand-written brace nesting. This
is orthogonal to keyword hierarchy (it's about how TOPAS formats its own
generated report output, not about which keywords nest under which).

Usage:
    python3 format_inp_hierarchy.py file.inp              # rewrite in place
    python3 format_inp_hierarchy.py file.inp -o out.inp   # write elsewhere
    python3 format_inp_hierarchy.py file.inp --check      # preview to stdout, don't write
"""

import sys
import os
import re
import argparse
import subprocess
import shutil

from fix_columns import fix_columns  # same directory; run first so site/lam keywords line up
import topas_keyword_tree as tkt      # same directory; reuses its Data-structures schema parser

INDENT_UNIT = "   "  # exactly 3 spaces, never a tab

FIRST_TOKEN_RE = re.compile(r"^([A-Za-z_]\w*)")

# A "site ..." line's spacing is intentional column alignment, produced by
# fix_columns.py -- never collapsed by normalize_line_whitespace.
SITE_LINE_RE = re.compile(r"^\s*site\b")

# Keywords that open a brace-delimited block TOPAS itself writes as a
# fixed-width table (e.g. the normalized parameter-correlation matrix after
# do_errors). Whitespace inside such a block is that table's own column
# alignment, not sloppy formatting -- compute_verbatim_flags() below marks
# every line inside it so normalize_line_whitespace never touches it.
# Separately (see the indentation loop below): these same lines are ALSO
# kept at the SAME indent level as the block-opening keyword itself, not
# one level deeper for being inside '{ }' -- confirmed directly by the
# user: the matrix's own header row ('1  2  3 ... 10') should line up
# with 'C_matrix_normalized', not sit indented under it, the same as
# every other line of this auto-generated report table (breaking that
# would also break the header's own vertical column alignment with the
# data rows below it, which DO need to stay unindented as a block for
# the same reason).
VERBATIM_BLOCK_KEYWORDS = {"C_matrix_normalized"}

# The one schema gap the hierarchy-driven engine below can't close purely
# by parsing brackets -- see the module docstring's "Known limitation"
# paragraph: la/lo/lh/lg are only connected to lam by prose in
# 21-keyword-index.md, never by bracket nesting.
PROSE_LINKED_CHILDREN = {
    "lam": {"la"},
}

_keyword_children_cache = None
_GROUP_HEAD_RE = re.compile(r"^[A-Za-z_]\w*")


def _split_top_level_groups(text):
    """Every top-level, bracket-matched '[...]' group's inner text found
    directly in text -- does not descend into brackets nested inside one
    already found; those are part of that group's own inner text,
    handled separately by whoever asked for them (see _nested_field_names
    vs _member_names_in_text)."""
    groups = []
    i, n = 0, len(text)
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
            groups.append(text[i + 1:j - 1])
            i = j
        else:
            i += 1
    return groups


def _group_head_names(inner):
    """Keyword-shaped name(s) heading one bracket group's own content --
    almost always one name, but '|'-alternation before any nested bracket
    (e.g. 'str | dummy_str', 'prm|local E [min !E]...') names more than
    one valid keyword for the same slot."""
    head_region = inner.split("[", 1)[0]
    names = [m.group(0) for m in (_GROUP_HEAD_RE.match(p.strip()) for p in head_region.split("|")) if m]
    if names:
        return names
    m = _GROUP_HEAD_RE.match(inner.strip())
    return [m.group(0)] if m else []


def _member_names_in_text(node_text):
    """Every sibling keyword name directly present in one schema line's
    own text -- handles a single bracket ('[xdd ...]...' -> {'xdd'}) and
    several brackets packed onto one manual line for brevity ('[a E] [b
    E] [c E]...' -> {'a', 'b', 'c', ...}), '|' alternation included."""
    names = set()
    for inner in _split_top_level_groups(node_text):
        names.update(_group_head_names(inner))
    return names


def _nested_field_names(node_text):
    """Keyword names nested one level inside this line's own top-level
    bracket group(s) -- a construct's own sub-fields written as nested
    brackets on the same schema line rather than as separately indented
    lines (lam's ymin_on_ymax/no_th_dependence/Lam/calculate_Lam, all
    nested inside lam's own single schema entry -- see the module
    docstring)."""
    names = set()
    for inner in _split_top_level_groups(node_text):
        for nested_inner in _split_top_level_groups(inner):
            names.update(_group_head_names(nested_inner))
    return names


def _resolve_member_names(nodes, type_defs, seen_types):
    """Direct child/member keyword names of a schema entry's own node
    list -- transparently resolving type-mixin references (a bare Txxx
    line) to that type's own members, at the same level, cycle-safe via
    seen_types. Does NOT descend into a member's own further-indented
    children -- that's a separate, deeper level, resolved independently
    when THAT keyword's own children are asked for."""
    names = set()
    for n in nodes:
        if tkt.TYPE_REF_RE.match(n.text) and n.text in type_defs:
            if n.text not in seen_types:
                names |= _resolve_member_names(type_defs[n.text], type_defs, seen_types | {n.text})
        else:
            names |= _member_names_in_text(n.text)
    return names


def build_keyword_children_map(references_dir=None):
    """{lowercased keyword name: set of lowercased valid child keyword
    names}, derived from 21-keyword-index.md's "## Data structures"
    fenced block -- TOPAS's own keyword-hierarchy schema, reusing
    topas_keyword_tree.py's parser. Cached after the first call (the
    schema doesn't change mid-process)."""
    global _keyword_children_cache
    if _keyword_children_cache is not None:
        return _keyword_children_cache

    ref_path = os.path.join(references_dir or tkt.REFERENCES_DIR, "21-keyword-index.md")
    with open(ref_path, encoding="utf-8") as f:
        md_text = f.read()
    type_defs = tkt.parse_hierarchy(tkt.extract_data_structures_block(md_text))

    by_name = {}

    def index_nodes(nodes):
        for n in nodes:
            if tkt.TYPE_REF_RE.match(n.text) and n.text in type_defs:
                continue  # a type-mixin reference isn't a keyword itself
            for name in _member_names_in_text(n.text):
                by_name.setdefault(name.lower(), []).append(n)
            index_nodes(n.children)

    for nodes in type_defs.values():
        index_nodes(nodes)

    children_map = {}
    for name, nodes in by_name.items():
        kids = set()
        for n in nodes:
            kids |= _resolve_member_names(n.children, type_defs, frozenset())
            kids |= _nested_field_names(n.text)
        kids |= {c.lower() for c in PROSE_LINKED_CHILDREN.get(name, set())}
        children_map[name] = kids

    _keyword_children_cache = children_map
    return children_map


def _is_wide_section(name, children_map):
    """A 'wide' section's resolved children reach TOPAS's general
    refinement-content mixin (Tcomm_2 -- detected via 'prm' being
    reachable, since everywhere Tcomm_2 is mixed in also accepts
    prm/local) -- true for xdd/str/hkl_Is/xo_Is/d_Is, so ordinary
    content never closes them, only another section-opener they don't
    recognize as a child does. A 'narrow' section (site, lam -- no prm
    reachable) has a small, fixed member list and NOTHING else, so it's
    closed by any keyword at all that isn't one of its own children."""
    return "prm" in children_map.get(name, ())


def strip_comments_and_strings_for_braces(text):
    """
    Blank out block comments (/* */), line comments ('...), and the
    interior of double-quoted strings -- with spaces, preserving length
    and newlines -- so brace-counting below never miscounts a '{' or '}'
    that's actually just text inside a comment or string. Mirrors
    check_inp_syntax.py's own strip_comments_and_strings for the same
    reason.
    """
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            out[i] = out[i + 1] = " "
            i += 2
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            if i < n:
                out[i] = out[i + 1] = " "
                i += 2
            continue
        if c == "'":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if c == '"':
            out[i] = " "
            i += 1
            while i < n and text[i] != '"' and text[i] != "\n":
                out[i] = " "
                i += 1
            if i < n and text[i] == '"':
                out[i] = " "
                i += 1
            continue
        i += 1
    return "".join(out)


def normalize_line_whitespace(bare_line):
    """
    Collapse unnecessary whitespace on a single line (not inside a comment
    or a quoted string, and never on a "site ..." line -- see
    SITE_LINE_RE): any run of whitespace collapses to a single space,
    except it's dropped entirely right after '(', right before ')', right
    before a ',', and right before any '(' (so "Keyword   (" becomes
    "Keyword(", "Radius(          173)" becomes "Radius(173)"); a ','
    keeps exactly one following space (unless immediately followed by
    ')'). Content inside /* */, '...', or "..." passes through completely
    unchanged, e.g. a quoted filename with spaces is never touched.

    Only tracks paren depth within a single line -- a call whose '(' and
    ')' land on different lines won't have its whitespace normalized.
    """
    if SITE_LINE_RE.match(bare_line):
        return bare_line

    out = []
    i, n = 0, len(bare_line)
    paren_depth = 0
    while i < n:
        c = bare_line[i]
        if c == "/" and i + 1 < n and bare_line[i + 1] == "*":
            j = bare_line.find("*/", i + 2)
            end = j + 2 if j != -1 else n
            out.append(bare_line[i:end])
            i = end
            continue
        if c == "'":
            out.append(bare_line[i:])
            break
        if c == '"':
            j = bare_line.find('"', i + 1)
            end = j + 1 if j != -1 else n
            out.append(bare_line[i:end])
            i = end
            continue
        if c in " \t":
            j = i
            while j < n and bare_line[j] in " \t":
                j += 1
            if j < n and bare_line[j] == "(":
                i = j  # drop whitespace directly before '('
                continue
            if out and out[-1] == "(":
                i = j  # drop whitespace directly after '('
                continue
            out.append(" ")  # collapse any other whitespace run to one space
            i = j
            continue
        if c == "(":
            paren_depth += 1
            out.append(c)
            i += 1
            continue
        if c == ")":
            while out and out[-1] == " ":
                out.pop()
            paren_depth = max(0, paren_depth - 1)
            out.append(c)
            i += 1
            continue
        if c == "," and paren_depth > 0:
            while out and out[-1] == " ":
                out.pop()
            out.append(",")
            i += 1
            j = i
            while j < n and bare_line[j] in " \t":
                j += 1
            if j < n and bare_line[j] != ")":
                out.append(" ")
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def compute_verbatim_flags(clean_lines):
    """
    Return one bool per line: True if that line falls STRICTLY inside a
    brace-delimited block opened by a VERBATIM_BLOCK_KEYWORDS keyword
    (currently just C_matrix_normalized{...}) -- the opening '{' line and
    the closing '}' line are both False, symmetric with each other and
    with the keyword's own line, since both are the block's own
    delimiters rather than its table content; only lines that stay at or
    above the block's depth for their ENTIRE span (both on entry and on
    exit) count as inside. Tracks real brace depth via the same
    comment/string-blanked clean_lines the main formatter uses, so a
    keyword and its '{' can land on the same line or different lines
    equally correctly.
    """
    flags = []
    brace_depth = 0
    awaiting_open = False
    verbatim_open_depth = None
    for clean in clean_lines:
        clean_stripped = clean.strip()

        first_tok_m = FIRST_TOKEN_RE.match(clean_stripped)
        first_kw = first_tok_m.group(1) if first_tok_m else None
        if verbatim_open_depth is None and first_kw in VERBATIM_BLOCK_KEYWORDS:
            awaiting_open = True

        depth_before = brace_depth
        opens = clean_stripped.count("{")
        closes = clean_stripped.count("}")
        if awaiting_open and opens > 0 and verbatim_open_depth is None:
            verbatim_open_depth = brace_depth + 1
            awaiting_open = False
        brace_depth = max(0, brace_depth + opens - closes)

        is_inside = (verbatim_open_depth is not None
                     and depth_before >= verbatim_open_depth
                     and brace_depth >= verbatim_open_depth)
        flags.append(is_inside)

        if verbatim_open_depth is not None and brace_depth < verbatim_open_depth:
            verbatim_open_depth = None
    return flags


def format_inp_hierarchy(text, references_dir=None):
    text = fix_columns(text)  # align site/lam-line keywords before reindenting
    raw_lines = text.splitlines(keepends=True)
    orig_bare_lines = [l.splitlines()[0] if l.splitlines() else "" for l in raw_lines]
    endings = [l[len(b):] for l, b in zip(raw_lines, orig_bare_lines)]
    clean_lines = strip_comments_and_strings_for_braces("\n".join(orig_bare_lines)).split("\n")

    verbatim_flags = compute_verbatim_flags(clean_lines)
    bare_lines = [
        b if v else normalize_line_whitespace(b)
        for b, v in zip(orig_bare_lines, verbatim_flags)
    ]

    children_map = build_keyword_children_map(references_dir)

    brace_depth = 0
    # stack entries: (lowercased keyword name, brace_depth_at_open)
    section_stack = []
    out_lines = []

    for bare, clean, verbatim in zip(bare_lines, clean_lines, verbatim_flags):
        stripped = bare.strip()
        if stripped == "":
            out_lines.append("")
            continue

        clean_stripped = clean.strip()
        leading_close_count = 0
        rest = clean_stripped
        while rest.startswith("}"):
            leading_close_count += 1
            rest = rest[1:].lstrip()
        print_brace_depth = max(0, brace_depth - leading_close_count)

        # pop sections invalidated by this line's brace closes -- strictly
        # greater, since a section opened AT the current brace depth (the
        # common case: no enclosing braces at all) must survive being
        # checked again at that same depth on the very next line.
        while section_stack and section_stack[-1][1] > print_brace_depth:
            section_stack.pop()

        first_tok_m = FIRST_TOKEN_RE.match(rest)
        first_kw = first_tok_m.group(1) if first_tok_m else None
        first_kw_lower = first_kw.lower() if first_kw else None
        is_opener = first_kw_lower is not None and bool(children_map.get(first_kw_lower))

        # Close any open section this line doesn't belong to -- see
        # _is_wide_section for the "wide vs narrow" distinction driving
        # the two different closing rules below.
        while section_stack:
            top_name, _ = section_stack[-1]
            if first_kw_lower is not None and first_kw_lower in children_map.get(top_name, ()):
                break  # recognized child of the currently-open section -- keep it open
            if _is_wide_section(top_name, children_map) and not is_opener:
                break  # wide section, ordinary content -- doesn't close it
            section_stack.pop()

        # A verbatim block's own brace pair (C_matrix_normalized{...})
        # doesn't add an indent level -- its content stays level with the
        # keyword that opens it, matching TOPAS's own auto-generated
        # report formatting (see VERBATIM_BLOCK_KEYWORDS' own note).
        verbatim_extra = -1 if verbatim else 0

        total_depth = max(0, print_brace_depth + len(section_stack) + verbatim_extra)
        out_lines.append(INDENT_UNIT * total_depth + stripped)

        if is_opener:
            section_stack.append((first_kw_lower, print_brace_depth))

        opens = clean_stripped.count("{")
        closes = clean_stripped.count("}")
        brace_depth = max(0, brace_depth + opens - closes)

    result_lines = [o + e for o, e in zip(out_lines, endings)]
    return "".join(result_lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inp_file")
    parser.add_argument("-o", "--output", help="write to this file instead of overwriting the input")
    parser.add_argument("--check", action="store_true", help="print the result to stdout instead of writing any file")
    parser.add_argument("--no-open", action="store_true",
                         help="don't reopen/focus the file in VS Code afterward (default: do reopen it)")
    args = parser.parse_args()

    with open(args.inp_file, encoding="utf-8") as f:
        text = f.read()

    fixed = format_inp_hierarchy(text)

    if args.check:
        print(fixed)
        return

    out_path = args.output or args.inp_file
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(fixed)
    print(f"Written to {out_path}", file=sys.stderr)

    if not args.no_open:
        # VS Code's file-watcher normally picks up an on-disk change on its
        # own, but only reliably if the file isn't already open with an
        # unsaved/dirty buffer (or the watcher simply hasn't fired yet) --
        # explicitly reopening/focusing it here forces the editor to show
        # the freshly written content rather than leaving that to chance.
        #
        # subprocess.run(["code", ...]) alone fails to find it on Windows:
        # the VS Code CLI is actually "code.cmd" on PATH there, and
        # subprocess's own PATH search (unlike PowerShell's/cmd's, which
        # both apply PATHEXT automatically) does not try that extension by
        # default -- confirmed directly (bare "code" raised
        # FileNotFoundError even though "code <file>" works fine when typed
        # straight into PowerShell). shutil.which() resolves the same way
        # the shell would, so ask it explicitly instead of guessing.
        code_path = shutil.which("code") or shutil.which("code.cmd")
        if code_path:
            subprocess.run([code_path, out_path], check=False)
        else:
            print("Note: 'code' CLI not found on PATH -- couldn't reopen the file in VS Code.", file=sys.stderr)


if __name__ == "__main__":
    main()
