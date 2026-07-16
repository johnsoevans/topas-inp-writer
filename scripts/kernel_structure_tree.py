"""
Render TOPAS's internal kernel data-structure listing (e.g. \\w\\K\\exx.txt) as an
interactive, collapsible HTML tree.

Input format (confirmed directly by the user, TOPAS-Academic's author):

    { Trigid_xyz;
    1 Crigid_xyz;
    2 Crx _cr rigid_prm pt rigid _r6;
    2 Cry _cr rigid_prm pt rigid _r6;
    2 Crz _cr rigid_prm pt rigid _r6;
    2 Ain_cart _cr fui;
    }

- The file is case sensitive.
- The whole file is wrapped in `start_templates` / `end_templates` marker lines,
  which are not part of the structure themselves.
- Each top-level block is delimited by a bare `{ TypeName;` opening line (no
  leading level number -- this is the Type itself, e.g. "Trigid_xyz") and a bare
  `}` closing line. Nothing between them nests via the braces themselves --
  braces elsewhere on a content line (e.g. `_on_cr { r translate 8 vonc_2 }`)
  are just part of that line's trailing content and are not structural.
- Every content line inside a block starts with a bare integer giving that
  line's nesting level (1 = direct child of the type, 2 = child of the nearest
  preceding level-1 line, etc.) -- indentation/hierarchy comes ONLY from this
  leading number, not from brace counting.
- The object's name is the first whitespace-delimited token after the level
  number, with a leading 'A' or 'C' stripped if present (e.g. "Crx" -> "rx",
  "Asite_name" -> "site_name"; a name with no A/C prefix, e.g. "rigid_ops", is
  left as-is).
- If a line contains `_tem`, the text right after it names one or more complex
  types this object inherits from: either a single bare name (`_tem Tarca`) or
  a brace-delimited list (`_tem { Tarca Tsh_hhh }`) for multiple inheritance.
  A referenced name may itself be prefixed with '@' (e.g. `@Tstr_sg`); the '@'
  is ignored entirely -- stripped from both the displayed label and the
  reference used to resolve it against this file's own top-level type blocks.
  These are captured as each
  node's `inherits` list and rendered in the tree as clickable links that
  inline-expand the referenced type's own members (cycle-safe -- a type that
  (transitively) inherits from itself is shown as a recursive reference rather
  than expanded again).
- Everything else on the line (`_cr`, `_on_cr { ... }`, `_alias`, trailing
  flags, etc.) is ignored.
- `/* ... */` block comments (nestable) are stripped before parsing -- their
  contents are not looked at at all.
- Objects whose (post A/C-stripped) name is in `IGNORED_NAMES` are dropped
  from the tree entirely, per an explicit user-supplied exclusion list.
- An object is flagged as a container of pointers with some type of symbol
  (shown as a small badge next to its name) if its name ends in `_ndx`, or its
  line contains the text `_cr nou`, or its name is `remove_phases`.
- An object whose line contains the standalone word `_arr` is flagged as also
  being an array with some sort of symbol (its own small badge).
"""

import argparse
import json
import os
import re
import shutil
import sys

DEFAULT_INPUT = r"c:\w\K\exx.txt"

HEADER_RE = re.compile(r"^\{\s*(\S+)")
CLOSE_RE = re.compile(r"^\}\s*$")
LINE_RE = re.compile(r"^(\d+)\s+(\S+)")
TEM_BRACE_RE = re.compile(r"_tem\s*\{\s*([^}]*)\}")
TEM_SINGLE_RE = re.compile(r"_tem\s+(\S+)")
ARR_RE = re.compile(r"\b_arr\b")

# Explicit user-supplied exclusion list: objects with these (post-prefix-strip)
# names are dropped from the tree entirely, wherever they occur.
IGNORED_NAMES = {
    "qsites_4", "qsites_4_t", "qradii_2", "t_scaler_7", "newton_approx",
    "quasi_newton", "load_free", "calc_ndx", "index_max_Nc", "pu5", "fin7",
    "on_cont3", "qsites_ndx", "in_deriv", "lat_prm_9", "ios_no_save", "cames_when",
}


def strip_block_comments(text):
    """Blank out /* ... */ block comments (nestable), preserving newlines and
    character offsets so everything else on a commented line stays intact."""
    out = list(text)
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "/" and i + 1 < n and text[i + 1] == "*":
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
        i += 1
    return "".join(out)


def strip_prefix(token):
    token = token.rstrip(";")
    if token and token[0] in ("A", "C") and len(token) > 1:
        return token[1:]
    return token


def is_ndx_container(name, line):
    return name.endswith("_ndx") or "_cr nou" in line or name == "remove_phases"


def is_array(line):
    return bool(ARR_RE.search(line))


def extract_tem(line):
    m = TEM_BRACE_RE.search(line)
    if m:
        tokens = m.group(1).split()
    else:
        m = TEM_SINGLE_RE.search(line)
        tokens = [m.group(1)] if m else []
    inherits = []
    for tok in tokens:
        tok = tok.rstrip(";")
        if tok.startswith("@"):
            tok = tok[1:]
        if not tok:
            continue
        inherits.append({"raw": tok, "key": tok})
    return inherits


def parse_kernel_structures(text):
    text = strip_block_comments(text)
    roots = []
    stack = []  # list of (level, node), level 0 = the root block itself
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in ("start_templates", "end_templates"):
            continue
        m = HEADER_RE.match(line)
        if m:
            name = m.group(1).rstrip(";")
            if name in IGNORED_NAMES:
                stack = []
                continue
            node = {"name": name, "children": [], "inherits": extract_tem(line),
                     "ndx": is_ndx_container(name, line), "arr": is_array(line)}
            roots.append(node)
            stack = [(0, node)]
            continue
        if CLOSE_RE.match(line):
            stack = []
            continue
        m = LINE_RE.match(line)
        if not m or not stack:
            continue
        level = int(m.group(1))
        name = strip_prefix(m.group(2))
        while stack and stack[-1][0] >= level:
            stack.pop()
        if name in IGNORED_NAMES:
            continue
        node = {"name": name, "children": [], "inherits": extract_tem(line),
                 "ndx": is_ndx_container(name, line), "arr": is_array(line)}
        if stack:
            stack[-1][1]["children"].append(node)
        stack.append((level, node))
    return roots


def count_nodes(node):
    return 1 + sum(count_nodes(c) for c in node["children"])


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
    --border: #e2ddd2;
    --accent: #b5502f;
    --type-color: #3b6ea5;
    --type-bg: rgba(59, 110, 165, 0.09);
    --match-bg: rgba(213, 168, 40, 0.28);
    --arr-color: #2f8f56;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #1b1a18;
      --panel: #242220;
      --ink: #ece7de;
      --ink-muted: #a39a8c;
      --border: #38342c;
      --accent: #e8875f;
      --type-color: #7ba9e0;
      --type-bg: rgba(123, 169, 224, 0.12);
      --match-bg: rgba(213, 168, 40, 0.35);
      --arr-color: #5cc98a;
    }}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--ink);
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
  .wrap {{ max-width: 900px; margin: 0 auto; padding: 20px 24px 40px; }}
  h1 {{ font-size: 1.05rem; font-weight: 600; margin: 0 0 2px; }}
  .meta {{ color: var(--ink-muted); font-size: 0.82rem; margin-bottom: 14px; }}
  .toolbar {{ display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }}
  input#search {{ flex: 1; padding: 7px 10px; border-radius: 7px; border: 1px solid var(--border);
    background: var(--panel); color: var(--ink); font: inherit; }}
  button {{ padding: 7px 12px; border-radius: 7px; border: 1px solid var(--border);
    background: var(--panel); color: var(--ink); font: inherit; cursor: pointer; }}
  button:hover {{ border-color: var(--type-color); }}
  .panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 14px 16px 18px; }}
  code, .mono {{ font-family: "SF Mono", Consolas, Menlo, monospace; font-size: 0.82rem; }}
  ul.tree {{ list-style: none; margin: 0; padding-left: 0; }}
  ul.tree ul.tree {{ padding-left: 18px; }}
  li {{ margin: 2px 0; }}
  .node {{ cursor: pointer; user-select: none; font-family: "SF Mono", Consolas, Menlo, monospace;
    font-size: 0.82rem; padding: 1px 4px; border-radius: 4px; }}
  .node:hover {{ background: var(--type-bg); }}
  .node.leaf {{ cursor: default; }}
  .node.leaf:hover {{ background: none; }}
  .node .arrow {{ display: inline-block; width: 0.9em; color: var(--ink-muted); transition: transform 0.1s; }}
  .node.open > .arrow {{ transform: rotate(90deg); }}
  .node .count {{ color: var(--ink-muted); font-size: 0.74rem; margin-left: 4px; }}
  .root > .node {{ color: var(--type-color); font-weight: 600; background: var(--type-bg); }}
  .children {{ display: none; }}
  .children.open {{ display: block; }}
  .node.match {{ background: var(--match-bg); }}
  li.hidden {{ display: none; }}
  .inherits-inline {{ font-family: "SF Mono", Consolas, Menlo, monospace; font-size: 0.76rem;
    color: var(--ink-muted); margin-left: 10px; }}
  .inherits-line {{ padding: 2px 4px 2px 18px; }}
  .inherits-label {{ margin-right: 4px; }}
  .chip {{ display: inline-block; padding: 0 6px; margin: 1px 3px 1px 0; border-radius: 4px; }}
  .chip.linked {{ color: var(--type-color); background: var(--type-bg); cursor: pointer; }}
  .chip.linked:hover {{ text-decoration: underline; }}
  .chip.linked::before {{ content: "\\25B8 "; display: inline-block; transition: transform 0.1s; }}
  .chip.linked.open::before {{ transform: rotate(90deg); }}
  .chip.cycle {{ color: var(--ink-muted); font-style: italic; border: 1px dashed var(--border); }}
  .chip.unresolved {{ color: var(--ink-muted); border: 1px dotted var(--border); }}
  .chip-body {{ display: none; padding-left: 16px; }}
  .chip-body.open {{ display: block; }}
  .ndx-badge {{ display: inline-block; margin-left: 8px; padding: 0 6px; border-radius: 4px;
    font-family: "SF Mono", Consolas, Menlo, monospace; font-size: 0.72rem;
    color: var(--accent); border: 1px solid var(--accent); cursor: help; }}
  .arr-badge {{ display: inline-block; margin-left: 4px; padding: 0 6px; border-radius: 4px;
    font-family: "SF Mono", Consolas, Menlo, monospace; font-size: 0.72rem;
    color: var(--arr-color); border: 1px solid var(--arr-color); cursor: help; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{title_escaped}</h1>
  <div class="meta">{nroots} top-level types &middot; {ntotal} nodes total &middot; parsed from <code>{source_escaped}</code> &middot; blue chips are <code>_tem</code> inheritance -- click to expand</div>
  <div class="toolbar">
    <input id="search" type="text" placeholder="Filter by name...">
    <button id="expandAll">Expand all</button>
    <button id="collapseAll">Collapse all</button>
  </div>
  <div class="panel">
    <div id="treeRoot"></div>
  </div>
</div>
<script>
const ROOTS = {roots_json};
const TYPES = {{}};
for (const r of ROOTS) TYPES[r.name] = r;

function countNodes(n) {{
  let c = 1;
  for (const ch of n.children) c += countNodes(ch);
  return c;
}}

function escapeHtml(s) {{
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}}

function buildTreeUl(nodes, ancestorTypes) {{
  const ul = document.createElement('ul');
  ul.className = 'tree';
  for (const node of nodes) {{
    ul.appendChild(buildLi(node, ancestorTypes));
  }}
  return ul;
}}

// A node's own _tem inheritance chips render inline, on the same line as its
// name (appended straight into `label`). Each linked chip's own expansion
// (that referenced type's members) is lazy and cycle-safe -- ancestorTypes is
// the set of type names already on the expansion path, so a type that
// (transitively) inherits from itself shows as a recursive reference instead
// of looping -- and renders as a block below, appended into `container`
// (the enclosing <li> for a normal node, or the chip-body div one level up
// when this is itself a further-inherits line inside an expanded chip).
function buildInheritsInline(node, ancestorTypes, container) {{
  const span = document.createElement('span');
  span.className = 'inherits-inline';
  const lbl = document.createElement('span');
  lbl.className = 'inherits-label';
  lbl.textContent = 'inherits ';
  span.appendChild(lbl);
  for (const inh of node.inherits) {{
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = inh.raw;
    if (ancestorTypes.has(inh.key)) {{
      chip.classList.add('cycle');
      chip.title = 'recursive reference -- already shown above this point';
    }} else if (TYPES[inh.key]) {{
      chip.classList.add('linked');
      const wrap = document.createElement('div');
      wrap.className = 'chip-body';
      let built = false;
      chip.addEventListener('click', (e) => {{
        e.stopPropagation();
        const opening = !chip.classList.contains('open');
        chip.classList.toggle('open');
        wrap.classList.toggle('open');
        if (opening && !built) {{
          const next = new Set(ancestorTypes);
          next.add(inh.key);
          buildTypeExpansion(TYPES[inh.key], next, wrap);
          built = true;
        }}
      }});
      container.appendChild(wrap);
    }} else {{
      chip.classList.add('unresolved');
      chip.title = 'not a top-level type defined in this file';
    }}
    span.appendChild(chip);
  }}
  return span;
}}

// Fills `container` (a chip-body div) with the expanded type's own further
// inherits-inline line (if it itself inherits from something) and its own
// literal children below that.
function buildTypeExpansion(node, ancestorTypes, container) {{
  if (node.inherits && node.inherits.length) {{
    const line = document.createElement('div');
    line.className = 'inherits-line';
    line.appendChild(buildInheritsInline(node, ancestorTypes, container));
    container.appendChild(line);
  }}
  if (node.children && node.children.length) {{
    container.appendChild(buildTreeUl(node.children, ancestorTypes));
  }}
}}

function buildLi(node, ancestorTypes) {{
  const li = document.createElement('li');
  const hasChildren = node.children && node.children.length > 0;
  const hasInherits = node.inherits && node.inherits.length > 0;
  const label = document.createElement('div');
  label.className = 'node' + (hasChildren ? '' : ' leaf');
  const n = countNodes(node);
  label.innerHTML = (hasChildren ? '<span class="arrow">\\u25B8</span>' : '<span class="arrow"></span>') +
    escapeHtml(node.name) + (hasChildren ? '<span class="count">(' + (n - 1) + ')</span>' : '');
  label.dataset.name = node.name.toLowerCase();
  li.appendChild(label);

  if (node.ndx) {{
    const badge = document.createElement('span');
    badge.className = 'ndx-badge';
    badge.textContent = 'ndx';
    badge.title = 'container of pointers with some type of symbol';
    label.appendChild(badge);
  }}
  if (node.arr) {{
    const badge = document.createElement('span');
    badge.className = 'arr-badge';
    badge.textContent = 'arr';
    badge.title = 'array with some sort of symbol';
    label.appendChild(badge);
  }}

  if (hasInherits) {{
    label.appendChild(buildInheritsInline(node, ancestorTypes, li));
  }}

  if (hasChildren) {{
    const bodyWrap = document.createElement('div');
    bodyWrap.className = 'children';
    bodyWrap.appendChild(buildTreeUl(node.children, ancestorTypes));
    li.appendChild(bodyWrap);
    label.addEventListener('click', (e) => {{
      if (e.target.closest('.chip')) return;
      label.classList.toggle('open');
      bodyWrap.classList.toggle('open');
    }});
  }}
  return li;
}}

const treeRoot = document.getElementById('treeRoot');
const rootUl = document.createElement('ul');
rootUl.className = 'tree';
for (const root of ROOTS) {{
  const li = buildLi(root, new Set([root.name]));
  li.className = 'root';
  rootUl.appendChild(li);
}}
treeRoot.appendChild(rootUl);

document.getElementById('expandAll').addEventListener('click', () => {{
  for (const label of treeRoot.querySelectorAll('.node:not(.leaf)')) label.classList.add('open');
  for (const ul of treeRoot.querySelectorAll('.children')) ul.classList.add('open');
}});
document.getElementById('collapseAll').addEventListener('click', () => {{
  for (const label of treeRoot.querySelectorAll('.node:not(.leaf)')) label.classList.remove('open');
  for (const ul of treeRoot.querySelectorAll('.children')) ul.classList.remove('open');
}});

document.getElementById('search').addEventListener('input', (e) => {{
  const q = e.target.value.trim().toLowerCase();
  const allLi = treeRoot.querySelectorAll('li');
  if (q === '') {{
    for (const li of allLi) li.classList.remove('hidden');
    for (const label of treeRoot.querySelectorAll('.node')) label.classList.remove('match');
    return;
  }}
  for (const label of treeRoot.querySelectorAll('.node')) label.classList.remove('match');
  for (const li of allLi) li.classList.add('hidden');
  for (const label of treeRoot.querySelectorAll('.node')) {{
    if (label.dataset.name.includes(q)) {{
      label.classList.add('match');
      let li = label.parentElement;
      while (li) {{
        li.classList.remove('hidden');
        const childUl = li.querySelector(':scope > div.children');
        if (childUl) {{
          childUl.classList.add('open');
          const parentLabel = li.querySelector(':scope > .node');
          if (parentLabel) parentLabel.classList.add('open');
        }}
        const parentUl = li.parentElement;
        li = (parentUl && parentUl.classList.contains('tree')) ? parentUl.closest('li') : null;
      }}
    }}
  }}
}});
</script>
</body>
</html>
"""


def build_html(roots, source_path, title):
    ntotal = sum(count_nodes(r) for r in roots)
    return PAGE_TEMPLATE.format(
        title_escaped=title.replace("<", "&lt;").replace(">", "&gt;"),
        nroots=len(roots),
        ntotal=ntotal,
        source_escaped=source_path.replace("<", "&lt;").replace(">", "&gt;"),
        roots_json=json.dumps(roots),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT, help=f"path to the kernel structure listing (default: {DEFAULT_INPUT})")
    parser.add_argument("-o", "--output", default="kernel_structure_tree.html", help="output HTML path")
    parser.add_argument("--no-open", action="store_true", help="don't open the result in the browser afterward")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    roots = parse_kernel_structures(text)
    html = build_html(roots, args.input, "TOPAS kernel data structures")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    ntotal = sum(count_nodes(r) for r in roots)
    print(f"Written to {args.output} ({len(roots)} top-level types, {ntotal} nodes total)", file=sys.stderr)

    if not args.no_open:
        abs_path = os.path.abspath(args.output)
        if os.name == "nt":
            os.startfile(abs_path)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            opener_path = shutil.which(opener)
            if opener_path:
                os.spawnl(os.P_NOWAIT, opener_path, opener, abs_path)


if __name__ == "__main__":
    main()
