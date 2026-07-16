#!/usr/bin/env python3
"""
topas_keyword_tree.py -- Render TOPAS's own keyword-hierarchy tree as a
self-contained, interactive HTML page, from two sources:

  1. The "Data structures" section of references/21-keyword-index.md --
     the manual's Ttop/Tcomm_2/Txdd/... type-dependency listing --
     rendered as the TREE panel, rooted at Ttop.
  2. Every OTHER numbered reference chapter (indexing, charge-flipping,
     stacking faults, the minimization routines, energy minimization,
     molecular dynamics, quantitative analysis, rigid bodies, magnetic
     structure, protein refinement, symmetry-mode/parametric
     refinement, GUI functionality, miscellaneous, ...) -- these topics
     have their own keywords (e.g. index_lam, flip_regime_2, tangent_num_h_read,
     madelung, r_wp) that are never mixed into Ttop's own dependency
     listing in 21-keyword-index.md, so they're extracted separately by
     scanning each chapter's prose/tables for TOPAS's own bracket
     notation (`[keyword ...]`) and shown as additional topic groups,
     alongside Ttop, in both panels.

Two panels, built from the same parsed data:
  1. TREE: rooted at Ttop, click a "type mixin" node to expand it inline
     -- lazy/on-demand, not pre-expanded server-side, since the same
     type is deliberately reused under many parents (e.g. Tcomm_2 is a
     member of Ttop, Txdd, AND every phase container at once -- the
     manual's own point, "trace which type(s) X is defined under, then
     check every place those type(s) get included") and pre-expanding
     everything would be both huge and misleadingly repetitive. Cycle-
     safe: a type reappearing in its own current expansion path shows
     "(recursive -- see Txxx's own entry in the index)" instead of
     recursing forever. Below Ttop and any orphan structural types, each
     "by topic" chapter group appears as its own expandable root too.
  2. INDEX: every type/topic as its own anchor-able heading with its
     direct members listed underneath -- keywords as plain bracket-
     notation text, type-mixin references as jump-links to that type's
     own heading. A live search box filters this list by keyword or
     type/topic name substring.

A leaf keyword line is shown verbatim (not split further) even when it
groups several brackets on one line (e.g. "[a E] [b E] [c E] [al E] [be
E] [ga E]") -- splitting would lose a meaningful grouping the manual
itself chose to keep together. For the "by topic" chapters, where
keywords mostly appear inline in prose/tables rather than as clean
indented lines (though a few, like PDF-generation and magnetic
structure, do have their own small Data-structures-style fenced
hierarchy block), each leaf is the outermost bracket-balanced group
starting at a keyword name (e.g. "[index_lam !E1.540596]",
"[grs_interaction [qi !E qj !E] $s1 $s2 c !E]"), extracted from the
whole chapter text -- deliberately including fenced code blocks, since
some chapters' real keyword hierarchy lives there. Array-index syntax
like bkg[0] from real INP snippets is naturally excluded because its
bracket content ("0") doesn't start with a keyword-shaped identifier;
a bare loop-variable index like x[i] can still slip through as a
spurious one-off "i" entry, a rare, low-impact false positive judged
worth accepting for the alternative (silently dropping real chapters
whose keyword hierarchy lives inside a fence, as PDF-generation and
magnetic-structure-refinement do). Separately, these reference files
are prose-extracted from a PDF manual and occasionally lose a closing
']' outright (confirmed in 22-charge-flipping.md); left unhandled, one
such unmatched '[' would nest every real bracket group for the rest of
that file inside it and starve the whole rest of the chapter's keyword
list -- see extract_bracket_groups()'s own docstring for the two-pass
recovery this triggered.

Usage:
    python3 topas_keyword_tree.py                 # uses the bundled reference file
    python3 topas_keyword_tree.py -o out.html
    python3 topas_keyword_tree.py --no-open
    python3 topas_keyword_tree.py --references-dir path/to/references   # defaults to the bundled references/ dir
"""

import sys
import os
import re
import json
import glob
import shutil
import subprocess
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REFERENCES_DIR = os.path.join(SCRIPT_DIR, "..", "references")
DEFAULT_REFERENCE = os.path.join(REFERENCES_DIR, "21-keyword-index.md")

TYPE_REF_RE = re.compile(r"^T\w+$")

# Chapters excluded from the "by topic" keyword scan: 21 (handled
# separately via its own Data structures section), 00/02/24 (no
# keywords of their own -- introduction, equation functions, and the
# bibliography respectively), any non-numbered meta file (console
# output, macro-expansion notes, example/system-file indexes, VS Code
# integration notes) which document tooling, not INP keywords, and
# 25/26 -- removed directly at the user's request: this tree is
# specifically a Technical_Reference.docx browser, and these two are
# NOT sourced from that manual at all (confirmed elsewhere in this skill
# -- SKILL.md, and MANUAL_CHAPTER_NUMBER's own docstring -- as sourced
# from a different book entirely, Dinnebier/Leineweber/Evans 2018), so
# they don't belong in a view whose whole premise is "match the manual's
# own hierarchy/order/numbering." Still real, valid reference chapters
# for the skill overall -- only excluded from THIS tool, not deleted.
CHAPTER_EXCLUDE = {"00-introduction.md", "02-equation-operators-and-functions.md",
                    "21-keyword-index.md", "24-bibliography.md",
                    "25-symmetry-mode-refinement.md",
                    "26-parametric-and-sequential-refinement.md"}
CHAPTER_FILE_RE = re.compile(r"^\d{2}-.*\.md$")
CHAPTER_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
BRACKET_KEYWORD_START_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*")


MAX_BRACKET_GROUP_LEN = 300
GLOSSARY_LINE_RE = re.compile(r"^[ \t]*\[[^\n\]]*\]:.*$", re.MULTILINE)


def _find_bracket_pairs_and_unmatched(text):
    """All (start, end) index pairs of matched '['...']' at any nesting
    depth, plus the start indices of any '[' still unmatched at EOF."""
    stack = []
    pairs = []
    for i, ch in enumerate(text):
        if ch == "[":
            stack.append(i)
        elif ch == "]" and stack:
            pairs.append((stack.pop(), i))
    return pairs, stack


def extract_bracket_groups(text):
    """Nesting-aware scan for top-level [...] groups anywhere in text.
    Returns (keyword_name, full_bracket_text, start_offset) for each
    group whose content starts with a keyword-shaped identifier -- skips
    groups like "[0]" or "[i+1]" (array-index syntax, not manual
    notation). start_offset (the group's opening '[' position in text)
    lets a caller merge these flat, prose-scattered entries back into
    true document order alongside any separately-parsed hierarchical
    fenced blocks -- see build_chapter_keyword_groups.

    These reference files are prose-extracted from a PDF manual, and
    that extraction occasionally drops a closing ']' entirely (a real,
    observed data-quality issue -- e.g. 22-charge-flipping.md has one
    "[a !E b !E c !E [al !E] [be !E] [ga !E] | ..." where the first
    bracket's own ']' went missing and is never seen again before EOF).
    A single such unmatched '[' would otherwise nest every real bracket
    group for the rest of the file inside it, so none of them ever
    complete back to depth 0 and the whole rest of the file's keywords
    go missing. To recover, two passes: (1) any '[' still unmatched at
    EOF is blanked out -- it has no partner to pair with, so it can
    only be corruption; (2) any matched pair (at any depth) spanning
    more than MAX_BRACKET_GROUP_LEN characters is almost certainly not
    real manual bracket notation either (genuine notation is always a
    short, single concept on one line) and gets blanked too. Repeated a
    few times in case of cascading corruption, before extracting the
    final top-level groups.

    A whole line matching '[name(s)]: description...' (e.g. '[s0, s1]:
    Site names.') is blanked out before scanning -- confirmed, widespread
    (06-macros-and-include-files.md, 13-rigid-bodies.md, ...) reuse of
    the SAME bracket notation for an entirely different purpose: labeling
    a macro's own argument names in a definition-list-style glossary, not
    documenting a real TOPAS keyword. This has to blank the WHOLE line,
    not just the leading '[name]:' bracket -- the description text itself
    routinely contains further bracket-wrapped unit abbreviations that
    would otherwise still slip through as bogus keywords on their own
    (e.g. '[filament_cv]: Tube filament length in [mm].' -- without
    blanking the full line, '[mm]' alone still passes the keyword-shaped-
    identifier check). Real keyword notation is never a whole line
    starting with '[...]:' this way."""
    text = GLOSSARY_LINE_RE.sub(lambda m: " " * len(m.group(0)), text)
    for _ in range(5):
        pairs, unmatched = _find_bracket_pairs_and_unmatched(text)
        bad_spans = [(s, e) for s, e in pairs if e - s > MAX_BRACKET_GROUP_LEN]
        if not unmatched and not bad_spans:
            break
        chars = list(text)
        for idx in unmatched:
            chars[idx] = " "
        for s, e in bad_spans:
            chars[s] = " "
            chars[e] = " "
        text = "".join(chars)

    results = []
    stack = []
    for i, ch in enumerate(text):
        if ch == "[":
            stack.append(i)
        elif ch == "]" and stack:
            start = stack.pop()
            if not stack:  # this close completes a top-level group
                if i + 1 < len(text) and text[i + 1] == ":":
                    continue  # macro-argument-glossary label, not a keyword
                group_text = text[start:i + 1]
                inner = group_text[1:-1].strip()
                m = BRACKET_KEYWORD_START_RE.match(inner)
                if m:
                    results.append((m.group(0), group_text, start))
    return results


FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
NODE_KEYWORD_NAME_RE = re.compile(r"\[([A-Za-z_]\w*)")


def find_fenced_blocks(text):
    """(content_start, content_end, content_text) for every fenced ```
    code block's inner content (excluding the fence lines themselves)."""
    return [(m.start(1), m.end(1), m.group(1)) for m in FENCE_RE.finditer(text)]


def looks_hierarchical(block_text):
    """True if a fenced block is genuinely a multi-level indented
    bracket-notation hierarchy (like the Data structures section, or
    stacking-faults' own two such blocks) rather than plain prose or an
    INP code snippet -- at least two distinct indent depths present,
    and most non-empty lines are bracket/brace/comment notation."""
    lines = [ln for ln in block_text.split("\n") if ln.strip()]
    if not lines:
        return False
    depths = set()
    bracketish = 0
    for ln in lines:
        indent = len(ln) - len(ln.lstrip(" "))
        depths.add(indent // 4)
        s = ln.strip()
        # a bracket/brace/comment line, OR a macro-style call
        # ('MM_CrystalAxis_Display(mxc, myc, mzc)') appearing as a
        # detail line inside an otherwise-bracket-notation block (seen
        # in 12-magnetic-structure-refinement.md) -- still counts as
        # structural content, not prose.
        if s[:1] in "[{}'" or re.match(r"^[A-Za-z_]\w*\s*\(", s):
            bracketish += 1
    return len(depths) >= 2 and bracketish / len(lines) >= 0.5


def parse_indented_bracket_tree(block_text, indent_width=4):
    """Generic indentation-based tree builder where EVERY line (including
    depth 0) is itself a real node -- unlike parse_hierarchy()'s Data-
    structures format, where a depth-0 line names a new TYPE rather than
    being a member itself. Returns a flat list of root Nodes (multiple
    roots allowed -- a chapter's fenced block often lists several
    independent top-level keyword groups, e.g. stacking-faults' first
    block has both '[site $name]...' and '[stack $layer]...' as
    separate depth-0 roots)."""
    roots = []
    stack = []  # (depth, node_list_to_append_into)
    for raw in block_text.split("\n"):
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        depth = indent // indent_width
        node = Node(raw.strip())
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if not stack:
            roots.append(node)
        else:
            stack[-1][1].append(node)
        stack.append((depth, node.children))
    return roots


def _node_keyword_names(nodes):
    """Every keyword name appearing anywhere in a Node tree (recursively)
    -- used to avoid the flat scanner re-adding, as a duplicate top-level
    entry, a keyword already captured with its real nesting intact. Uses
    findall (not just the first match) since a single compound line like
    '[z_matrix atom_1 [atom_2 E] [atom_3 E] [atom_4 E] ]...' embeds
    several keyword-shaped names in ONE node's text, not just its
    leading one -- confirmed necessary in 13-rigid-bodies.md, where
    prose elsewhere references '[atom_2 E]' again on its own (a cross-
    reference back to this same z_matrix line, not a second keyword)."""
    names = set()
    for n in nodes:
        for m in NODE_KEYWORD_NAME_RE.finditer(n.text):
            names.add(m.group(1).lower())
        names |= _node_keyword_names(n.children)
    return names


# This skill's own 00-26 filename prefixes are an independent
# organizational scheme (see SKILL.md's "Updating this skill from a
# revised Technical Reference" section) and were never meant to track
# Technical_Reference.docx's own chapter numbers -- confirmed directly by
# the user (TOPAS-Academic's author) that the displayed "ChNN" labels in
# this tree didn't match the real manual (e.g. "Parameters" shown as
# "Ch01" when the manual's own Chapter 2 is "Parameters"). This map was
# built by walking every Heading1-styled paragraph in the real
# Technical_Reference.docx (Downloads\Technical_Reference (1).DOCX, the
# copy whose 26 Heading1 titles match every one of this skill's own
# reference-file titles character for character, confirming it's the
# edition this skill was actually built from) and matching by heading
# TEXT, not by an assumed running number -- per this same section's own
# documented method, since chapter numbering drifts between editions/
# exports.
#
# That walk surfaced a real duplicate: "Indexing" appears as TWO separate
# Heading1 paragraphs -- one between "Rigid bodies" and "Energy
# Minimization", one between "Macros and Include files" and
# "Charge-flipping" -- with identical heading text, so heading-text
# matching alone can't tell which is the genuine chapter and which is a
# stray artifact. The first version of this map guessed the FIRST
# occurrence was real (Indexing = 14, Energy Minimization = 15) --
# WRONG, corrected after the user gave three independent subsection
# references that only resolve consistently the other way: "Section
# 14.2" for the Coulomb-potential-at-a-site keyword `co` (confirmed
# directly against 15-energy-minimization.md's own "Reporting on the
# Coulomb potential at a site" section -- the SECOND of that chapter's
# three subsections), which only lines up if Energy Minimization itself
# is chapter 14 -- and retroactively, two earlier messages ("Section
# 4.1" for Madelung, "Section 4.3" for grs_interaction) turn out to be
# "14.1"/"14.3" with a dropped leading digit, matching that same
# chapter's 1st and 3rd subsections ("Reporting on the Madelung
# constant", "Enhancements to the grs_interaction") in order. So the
# SECOND "Indexing" occurrence is the genuine chapter (22, between Macros
# and Include files and Charge-flipping) and the first is the stray
# duplicate -- Energy Minimization through Macros and Include files each
# shift down one slot from the first (wrong) version of this map.
# 25-symmetry-mode-refinement.md and 26-parametric-and-sequential-
# refinement.md are deliberately absent from this map -- confirmed
# elsewhere in this skill (SKILL.md) as sourced from a different book
# entirely (Dinnebier/Leineweber/Evans 2018), never part of
# Technical_Reference.docx, so no manual chapter number applies.
MANUAL_CHAPTER_NUMBER = {
    "00-introduction.md": 1,
    "01-syntax-and-parameters.md": 2,
    "02-equation-operators-and-functions.md": 3,
    "03-minimization-and-convergence.md": 4,
    "04-peak-generation-and-peak-type.md": 5,
    "05-reusing-objects-large-refinements.md": 6,
    "07-deconvolution.md": 7,
    "08-pdf-generation.md": 8,
    "09-pdf-refinement.md": 9,
    "10-stacking-faults.md": 10,
    "11-quantitative-analysis.md": 11,
    "12-magnetic-structure-refinement.md": 12,
    "13-rigid-bodies.md": 13,
    "15-energy-minimization.md": 14,
    "16-molecular-dynamics.md": 15,
    "17-amazon-ec2-cloud-computing.md": 16,
    "18-protein-refinement.md": 17,
    "19-solving-proteins-atomic-resolution.md": 18,
    "20-miscellaneous.md": 19,
    "21-keyword-index.md": 20,
    "06-macros-and-include-files.md": 21,
    "14-indexing.md": 22,
    "22-charge-flipping.md": 23,
    "23-gui-functionality.md": 24,
    "24-bibliography.md": 25,
}


def build_chapter_keyword_groups(references_dir):
    """Scans every non-excluded numbered reference chapter for its own
    bracket-notation keywords and returns an ordered list of
    (type_key, title, [Node, ...]) tuples, one per chapter that yielded
    at least one keyword.

    Two extraction passes, not one: a fenced code block that's genuinely
    a multi-level indented hierarchy (looks_hierarchical) is parsed WITH
    its nesting intact (parse_indented_bracket_tree) -- e.g. stacking-
    faults' 'generate_stack_sequences { transition { to { ta/tb/tz } } }'
    structure, confirmed against real MS-Word-table screenshots of the
    original manual showing four genuine indent levels that a naive flat
    scan collapses to a single alphabetized list. Everything else in the
    chapter (plain prose, ordinary tables, non-hierarchical fenced
    blocks) still goes through the flat extract_bracket_groups() scanner
    as before, with any keyword already captured by a hierarchical block
    skipped to avoid a duplicate flat entry alongside its structured one.

    Root-level ordering matches Technical_Reference.docx's own document
    order, not alphabetical order and not "every hierarchical block
    before every flat entry" -- confirmed directly by the user
    (TOPAS-Academic's author): "the hierarchy should display the
    dependents in the same order as in Technical_Reference.docx... for
    all sections." Every root -- whether it came from a hierarchical
    fenced block or the flat scanner -- carries the character offset of
    where it starts in the chapter's original text, and the final root
    list is sorted by that offset, so a fenced block sitting between two
    prose-documented keywords interleaves with them exactly as printed,
    rather than every block floating to the front the way the original
    (pre-ordering-fix) version did.

    The CHAPTER-level list itself is also sorted by real manual chapter
    number (MANUAL_CHAPTER_NUMBER), not by this skill's own filename
    prefix -- caught directly by the user asking "why is Chapter 22 in
    between Chapter 13 and Chapter 14" after the chapter-numbering fix
    below started showing real numbers but the underlying file iteration
    (sorted(glob.glob(...)), i.e. filename order) never changed to match:
    14-indexing.md (filename) is real chapter 22, but its name still
    sorts right after 13-rigid-bodies.md, so it rendered out of order
    until this second pass sorted the finished `groups` list by each
    chapter's real number afterward (chapters with no real number --
    25/26, a different book -- sort last, after every real chapter)."""
    groups = []
    for path in sorted(glob.glob(os.path.join(references_dir, "*.md"))):
        fname = os.path.basename(path)
        if fname in CHAPTER_EXCLUDE or not CHAPTER_FILE_RE.match(fname):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        heading_match = CHAPTER_HEADING_RE.search(text)
        title = heading_match.group(1).strip() if heading_match else fname

        hierarchical_roots = []  # (start_offset, Node)
        consumed_spans = []
        for start, end, block_text in find_fenced_blocks(text):
            if looks_hierarchical(block_text):
                for root in parse_indented_bracket_tree(block_text):
                    hierarchical_roots.append((start, root))
                consumed_spans.append((start, end))

        remaining_text = text
        if consumed_spans:
            chars = list(text)
            for s, e in consumed_spans:
                for i in range(s, e):
                    chars[i] = " "
            remaining_text = "".join(chars)

        covered = _node_keyword_names([n for _, n in hierarchical_roots])
        found = extract_bracket_groups(remaining_text)
        seen = {}
        for name, group_text, start in found:
            key = name.lower()
            if key in covered or key in seen:
                continue
            seen[key] = (group_text, start)
        flat_roots = [(start, Node(group_text)) for group_text, start in seen.values()]

        nodes = [n for _, n in sorted(hierarchical_roots + flat_roots, key=lambda pair: pair[0])]
        if not nodes:
            continue
        real_num = MANUAL_CHAPTER_NUMBER.get(fname)
        if real_num is not None:
            type_key = f"Ch{real_num} {title}"
        else:
            # Not part of Technical_Reference.docx at all -- see
            # MANUAL_CHAPTER_NUMBER's own note (25/26: a different book).
            type_key = f"{title} (not in Technical_Reference.docx)"
        groups.append((type_key, title, nodes, real_num))
    groups.sort(key=lambda g: (g[3] is None, g[3]))
    return [(type_key, title, nodes) for type_key, title, nodes, _ in groups]


def extract_data_structures_block(md_text):
    heading_idx = md_text.find("## Data structures")
    if heading_idx == -1:
        raise ValueError("'## Data structures' heading not found in the reference file")
    fence_start = md_text.find("```", heading_idx)
    if fence_start == -1:
        raise ValueError("Opening ``` fence not found after '## Data structures'")
    fence_start = md_text.find("\n", fence_start) + 1
    fence_end = md_text.find("```", fence_start)
    if fence_end == -1:
        raise ValueError("Closing ``` fence not found")
    return md_text[fence_start:fence_end]


class Node:
    def __init__(self, text):
        self.text = text
        self.children = []

    def to_dict(self):
        is_type = bool(TYPE_REF_RE.match(self.text))
        return {"text": self.text, "isType": is_type, "children": [c.to_dict() for c in self.children]}


def parse_hierarchy(block_text):
    """Returns {type_name: [Node, ...]} -- each type's own direct member
    list (a small tree, since a member can itself have further-indented
    children representing a genuine nested child object, e.g. [xdd ...]
    containing [xo_Is]... containing [xo E I E]...)."""
    type_defs = {}
    current_type = None
    stack = []  # list of (depth, node_list)

    for raw in block_text.split("\n"):
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        depth = indent // 4
        text = raw.strip()

        if depth == 0:
            current_type = text
            type_defs[current_type] = []
            stack = [(0, type_defs[current_type])]
            continue

        if current_type is None:
            continue  # malformed/unexpected -- skip rather than crash

        node = Node(text)
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if not stack:
            type_defs[current_type].append(node)
            stack = [(0, type_defs[current_type])]
        else:
            stack[-1][1].append(node)
        stack.append((depth, node.children))

    return type_defs


def find_orphan_types(type_defs):
    """Type names never referenced as a member anywhere -- these won't
    be reachable by expanding the Ttop tree, so the page shows them as
    additional top-level tree roots alongside Ttop."""
    referenced = set()

    def walk(nodes):
        for n in nodes:
            if TYPE_REF_RE.match(n.text) and n.text in type_defs:
                referenced.add(n.text)
            walk(n.children)

    for nodes in type_defs.values():
        walk(nodes)
    return [t for t in type_defs if t != "Ttop" and t not in referenced]


PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title_escaped}</title>
<style>
  :root {{
    --bg: #f7f5f1;
    --panel: #ffffff;
    --ink: #2a2622;
    --ink-muted: #6b6459;
    --grid: #ddd8cf;
    --border: #e2ddd2;
    --accent: #b5502f;
    --type-color: #3b6ea5;
    --type-bg: rgba(59, 110, 165, 0.09);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #1b1a18;
      --panel: #242220;
      --ink: #ece7de;
      --ink-muted: #a39a8c;
      --grid: #3a362f;
      --border: #38342c;
      --accent: #e8875f;
      --type-color: #7ba9e0;
      --type-bg: rgba(123, 169, 224, 0.12);
    }}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--ink);
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
  .wrap {{ max-width: 1400px; margin: 0 auto; padding: 20px 24px 40px; }}
  h1 {{ font-size: 1.05rem; font-weight: 600; margin: 0 0 2px; }}
  .meta {{ color: var(--ink-muted); font-size: 0.82rem; margin-bottom: 16px; }}
  .columns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start; }}
  @media (max-width: 900px) {{ .columns {{ grid-template-columns: 1fr; }} }}
  .panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 14px 16px 18px; }}
  .panel h2 {{ font-size: 0.92rem; margin: 0 0 10px; letter-spacing: 0.02em; text-transform: uppercase;
    color: var(--ink-muted); }}
  code, .mono {{ font-family: "SF Mono", Consolas, Menlo, monospace; font-size: 0.82rem; }}
  ul.tree {{ list-style: none; margin: 0; padding-left: 18px; }}
  ul.tree.root {{ padding-left: 0; }}
  li {{ margin: 3px 0; position: relative; }}
  .leaf {{ font-family: "SF Mono", Consolas, Menlo, monospace; font-size: 0.82rem; }}
  .type-toggle {{ cursor: pointer; user-select: none; color: var(--type-color); font-weight: 600;
    background: var(--type-bg); border-radius: 5px; padding: 1px 7px; display: inline-block; font-size: 0.82rem; }}
  .type-toggle:hover {{ text-decoration: underline; }}
  .type-toggle::before {{ content: "\\25B8 "; display: inline-block; transition: transform 0.1s; }}
  .type-toggle.open::before {{ transform: rotate(90deg); }}
  .type-children {{ display: none; }}
  .type-children.open {{ display: block; }}
  .cycle-note {{ color: var(--ink-muted); font-style: italic; font-size: 0.78rem; }}
  input#search {{ width: 100%; padding: 7px 10px; border-radius: 7px; border: 1px solid var(--border);
    background: var(--bg); color: var(--ink); font: inherit; margin-bottom: 12px; }}
  .index-block {{ margin-bottom: 16px; scroll-margin-top: 12px; }}
  .index-block h3 {{ font-size: 0.86rem; margin: 0 0 6px; font-family: monospace; color: var(--type-color); }}
  .index-block ul {{ list-style: none; margin: 0; padding-left: 0; }}
  .index-block li {{ font-size: 0.8rem; padding: 1px 0; }}
  .jump-link {{ color: var(--type-color); cursor: pointer; text-decoration: none; font-family: monospace; }}
  .jump-link:hover {{ text-decoration: underline; }}
  .index-block.hidden, li.hidden {{ display: none; }}
  .hint {{ color: var(--ink-muted); font-size: 0.78rem; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{title_escaped}</h1>
  <div class="meta">{ntypes} types/topics &middot; {nstructural} structural (from 21-keyword-index.md's "Data structures" section) + {nchapters} by-topic chapters (indexing, charge-flipping, stacking faults, minimization, ...) &middot; click a blue name to expand it inline</div>
  <div class="columns">
    <div class="panel">
      <h2>Tree</h2>
      <div id="treeRoot"></div>
      <div class="hint" style="margin-top:10px;">Below Ttop and any orphan structural types: every other manual chapter's own keywords, grouped by topic.</div>
      <div id="chapterRoot" style="margin-top:6px;"></div>
    </div>
    <div class="panel">
      <h2>Type / topic index</h2>
      <input id="search" type="text" placeholder="Filter by keyword, type, or topic name...">
      <div id="indexRoot"></div>
    </div>
  </div>
</div>
<script>
const TYPE_DEFS = {type_defs_json};
const ORPHANS = {orphans_json};
const CHAPTERS = {chapters_json};

function escapeHtml(s) {{
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}}

// --- Tree panel: lazy, click-to-expand mixin nodes, cycle-safe ---
let uid = 0;
function renderTreeNodes(nodes, ancestorTypes) {{
  const ul = document.createElement('ul');
  ul.className = 'tree';
  for (const node of nodes) {{
    const li = document.createElement('li');
    if (node.isType && TYPE_DEFS[node.text]) {{
      if (ancestorTypes.has(node.text)) {{
        li.innerHTML = '<span class="cycle-note">' + escapeHtml(node.text) +
          ' (recursive -- see its own entry in the index &rarr;)</span>';
      }} else {{
        const id = 'tt' + (uid++);
        const toggle = document.createElement('span');
        toggle.className = 'type-toggle';
        toggle.textContent = node.text;
        toggle.id = id;
        const childWrap = document.createElement('div');
        childWrap.className = 'type-children';
        let built = false;
        toggle.addEventListener('click', () => {{
          const opening = !toggle.classList.contains('open');
          toggle.classList.toggle('open');
          childWrap.classList.toggle('open');
          if (opening && !built) {{
            const nextAncestors = new Set(ancestorTypes);
            nextAncestors.add(node.text);
            childWrap.appendChild(renderTreeNodes(TYPE_DEFS[node.text], nextAncestors));
            built = true;
          }}
        }});
        li.appendChild(toggle);
        li.appendChild(childWrap);
      }}
    }} else {{
      const span = document.createElement('span');
      span.className = 'leaf';
      span.textContent = node.text;
      li.appendChild(span);
      if (node.children && node.children.length) {{
        li.appendChild(renderTreeNodes(node.children, ancestorTypes));
      }}
    }}
    ul.appendChild(li);
  }}
  return ul;
}}

const treeRoot = document.getElementById('treeRoot');
treeRoot.appendChild(renderTreeNodes(TYPE_DEFS['Ttop'] || [], new Set(['Ttop'])));
for (const orphan of ORPHANS) {{
  const h = document.createElement('div');
  h.innerHTML = '<span class="type-toggle" style="margin-top:10px;display:inline-block;">' + escapeHtml(orphan) + '</span>';
  const wrap = document.createElement('div');
  wrap.className = 'type-children';
  const toggle = h.querySelector('.type-toggle');
  let built = false;
  toggle.addEventListener('click', () => {{
    const opening = !toggle.classList.contains('open');
    toggle.classList.toggle('open');
    wrap.classList.toggle('open');
    if (opening && !built) {{
      wrap.appendChild(renderTreeNodes(TYPE_DEFS[orphan], new Set([orphan])));
      built = true;
    }}
  }});
  treeRoot.appendChild(h);
  treeRoot.appendChild(wrap);
}}

const chapterRoot = document.getElementById('chapterRoot');
for (const chapter of CHAPTERS) {{
  const h = document.createElement('div');
  h.innerHTML = '<span class="type-toggle" style="margin-top:6px;display:inline-block;">' + escapeHtml(chapter) + '</span>';
  const wrap = document.createElement('div');
  wrap.className = 'type-children';
  const toggle = h.querySelector('.type-toggle');
  let built = false;
  toggle.addEventListener('click', () => {{
    const opening = !toggle.classList.contains('open');
    toggle.classList.toggle('open');
    wrap.classList.toggle('open');
    if (opening && !built) {{
      wrap.appendChild(renderTreeNodes(TYPE_DEFS[chapter], new Set([chapter])));
      built = true;
    }}
  }});
  chapterRoot.appendChild(h);
  chapterRoot.appendChild(wrap);
}}

// --- Index panel: every type, its direct members, jump-links ---
function renderIndexLeafText(node) {{
  if (node.isType && TYPE_DEFS[node.text]) {{
    return '<a class="jump-link" href="#type-' + node.text + '">' + escapeHtml(node.text) + '</a>';
  }}
  let s = '<span class="leaf">' + escapeHtml(node.text) + '</span>';
  if (node.children && node.children.length) {{
    s += '<ul>' + node.children.map(c => '<li>' + renderIndexLeafText(c) + '</li>').join('') + '</ul>';
  }}
  return s;
}}

const indexRoot = document.getElementById('indexRoot');
const typeNames = Object.keys(TYPE_DEFS).sort();
for (const name of typeNames) {{
  const block = document.createElement('div');
  block.className = 'index-block';
  block.id = 'type-' + name;
  block.dataset.searchText = (name + ' ' + TYPE_DEFS[name].map(n => n.text).join(' ')).toLowerCase();
  const h3 = document.createElement('h3');
  h3.textContent = name;
  block.appendChild(h3);
  const ul = document.createElement('ul');
  ul.innerHTML = TYPE_DEFS[name].map(n => '<li>' + renderIndexLeafText(n) + '</li>').join('');
  block.appendChild(ul);
  indexRoot.appendChild(block);
}}

document.getElementById('search').addEventListener('input', (e) => {{
  const q = e.target.value.trim().toLowerCase();
  for (const block of indexRoot.querySelectorAll('.index-block')) {{
    block.classList.toggle('hidden', q !== '' && !block.dataset.searchText.includes(q));
  }}
}});
</script>
</body>
</html>
"""


def build_html(type_defs, orphans, chapters, nstructural, title):
    type_defs_dict = {name: [n.to_dict() for n in nodes] for name, nodes in type_defs.items()}
    return PAGE_TEMPLATE.format(
        title_escaped=title.replace("<", "&lt;").replace(">", "&gt;"),
        ntypes=len(type_defs),
        nstructural=nstructural,
        nchapters=len(chapters),
        type_defs_json=json.dumps(type_defs_dict),
        orphans_json=json.dumps(orphans),
        chapters_json=json.dumps(chapters),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reference", default=DEFAULT_REFERENCE, help="path to 21-keyword-index.md (default: bundled copy)")
    parser.add_argument("--references-dir", default=REFERENCES_DIR, help="directory of all reference chapters for the 'by topic' scan (default: bundled references/ dir)")
    parser.add_argument("-o", "--output", default="topas_keyword_tree.html", help="output HTML path")
    parser.add_argument("--no-open", action="store_true", help="don't open the result in the browser afterward")
    args = parser.parse_args()

    with open(args.reference, encoding="utf-8") as f:
        md_text = f.read()

    block = extract_data_structures_block(md_text)
    type_defs = parse_hierarchy(block)
    orphans = find_orphan_types(type_defs)
    nstructural = len(type_defs)

    chapter_groups = build_chapter_keyword_groups(args.references_dir)
    chapters = []
    for type_key, title, nodes in chapter_groups:
        type_defs[type_key] = nodes
        chapters.append(type_key)

    html = build_html(type_defs, orphans, chapters, nstructural, "TOPAS keyword hierarchy")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Written to {args.output} ({nstructural} structural types, {len(orphans)} orphan root(s): {orphans}, "
          f"{len(chapters)} by-topic chapters)", file=sys.stderr)

    if not args.no_open:
        # HTML output opens in the default browser -- unlike the plain-text
        # reports from param_dependency_trees.py/format_inp_hierarchy.py,
        # which open in VS Code instead (see this skill's own established
        # convention for each output type).
        abs_path = os.path.abspath(args.output)
        if os.name == "nt":
            os.startfile(abs_path)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            opener_path = shutil.which(opener)
            if opener_path:
                subprocess.run([opener_path, abs_path], check=False)


if __name__ == "__main__":
    main()
