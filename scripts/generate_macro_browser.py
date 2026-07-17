#!/usr/bin/env python3
"""
generate_macro_browser.py -- (re)builds macro_browser.html, a self-
contained interactive page for browsing every `macro`/`macro &`
definition in the real TOPAS .inc library (topas.inc, pdf.inc,
interface.inc, Charge_Flipping.inc, PDF-*.inc, Colours.inc,
GUI_PDF.inc, ...).

Ground truth for every macro's NAME, ARGUMENTS, ARITY, and BODY is
always the real .inc source, found via TOPAS_DIR (see
topas_install.py). Technical_Reference's section 21.2 "Overview" is an
OPTIONAL, best-effort explanation/category layer on top -- it is never
allowed to override or invent a signature. A real macro with no match
there is still shown in full, grouped by its source .inc file instead
of a §21.2 category, honestly labeled undocumented rather than guessed
at. (An earlier version of this cross-referencer tried to back-fill a
"shared" description from a following entry onto consecutive
signature-only entries -- correct for genuine shared-description pairs
like Surface_Roughness_Pitschke_et_al / _Suortti, but it wrongly
attributed an unrelated description to four actually-undocumented
macros elsewhere in the same category. Removed entirely: a
fabricated/borrowed description is worse than an honest gap.)

Usage:
    python3 generate_macro_browser.py [-o OUTPUT_HTML]
    python3 generate_macro_browser.py --docx PATH
    python3 generate_macro_browser.py --pdf PATH
    python3 generate_macro_browser.py --no-pdf

TOPAS_DIR must be set (see "Locating your TOPAS installation" in
SKILL.md) so topas_install.get_inc_dir() can find the real .inc files
-- this skill does not bundle copies of them.

§21.2 descriptions come from Technical_Reference.pdf by default,
auto-resolved under TOPAS_DIR (topas_install.get_technical_reference_pdf())
-- the PDF, unlike the .docx editing copy, actually ships with a real
TOPAS install, so this needs no extra setup on a normal install.
Requires the third-party `pypdf` package. Pass --docx to use a .docx
copy instead if you have one (it takes priority when given -- it's the
live editing copy, so it can be more current than a shipped PDF);
requires `python-docx`. Pass --pdf to point at a PDF explicitly rather
than relying on auto-resolution, or --no-pdf to skip descriptions
entirely. Without any source found, every macro is still shown in
full, just grouped by source .inc file with no §21.2 description.

Default output is macro_browser.html directly under TOPAS_DIR (not
inside this skill) -- the same spot topas_install.get_macro_browser_html()
resolves, mirroring how the "Show Schema" kernel page lives under
TOPAS_DIR rather than being bundled. Pass -o to write somewhere else.
"""
import argparse
import glob
import html as htmlmod
import os
import re
import sys

import topas_install

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Step 1: harvest real macro definitions from the .inc library (ground truth)
# ---------------------------------------------------------------------------

MACRO_START_RE = re.compile(r"macro\s+(&\s*)?([A-Za-z_]\w*)\s*(\(([^)]*)\))?\s*\{")


def strip_comments(text):
    """Blank ' comments to spaces (preserving length/newlines) so line
    numbers and match offsets in the ORIGINAL text stay valid."""
    out = []
    for line in text.split("\n"):
        idx = line.find("'")
        if idx != -1:
            line = line[:idx] + " " * (len(line) - idx)
        out.append(line)
    return "\n".join(out)


def find_matching_brace(text, open_pos):
    depth = 1
    i = open_pos + 1
    n = len(text)
    while i < n and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return i - 1


def harvest_file(path, source_label):
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    clean = strip_comments(raw)
    macros = []
    for m in MACRO_START_RE.finditer(clean):
        amp = bool(m.group(1))
        name = m.group(2)
        args_str = m.group(4)
        args = [a.strip() for a in args_str.split(",")] if args_str and args_str.strip() else []
        open_brace = m.end() - 1
        close_brace = find_matching_brace(clean, open_brace)
        body = raw[open_brace + 1:close_brace]
        line_no = raw.count("\n", 0, m.start()) + 1
        macros.append({
            "name": name, "amp": amp, "args": args, "arity": len(args),
            "body": body.strip(), "line": line_no, "source_file": source_label,
        })
    return macros


def find_inc_files(inc_dir):
    # a single case-insensitive-safe glob (Windows filesystems are already
    # case-insensitive, so this naturally de-duplicates)
    return sorted({os.path.abspath(p) for p in glob.glob(os.path.join(inc_dir, "*.[iI][nN][cC]"))})


def harvest_all(inc_dir):
    all_macros = []
    for path in find_inc_files(inc_dir):
        label = os.path.basename(path)
        macros = harvest_file(path, label)
        all_macros.extend(macros)
        print(f"  {label}: {len(macros)} macro definitions", file=sys.stderr)
    return all_macros


# ---------------------------------------------------------------------------
# Step 2 (optional): parse Technical_Reference.docx section 21.2 "Overview"
# ---------------------------------------------------------------------------

SIG_RE = re.compile(
    r"^([A-Za-z_]\w*(\([^)]*\))?)(\s*(or|,)\s*[A-Za-z_]\w*(\([^)]*\))?)*\.?,?$"
)


def is_signature_line(text):
    t = text.strip().rstrip(".")
    if not t:
        return False
    if not SIG_RE.match(t):
        return False
    # require at least one '(' -- bare words alone (e.g. a stray label)
    # are too ambiguous to trust as a signature
    return "(" in t or t[0].isupper()


def extract_overview_paragraphs(doc):
    """Scope to Chapter 21's "Overview" Heading-2 section only, so an
    unrelated Heading-3 elsewhere in the manual can't be misread as a
    macro category. Returns a list of (style_name, text)."""
    paras = doc.paragraphs
    chapter_start = None
    for i, p in enumerate(paras):
        style = p.style.name if p.style else ""
        if style.startswith("Heading 1") and re.search(r"macros and include", p.text, re.I):
            chapter_start = i
            break
    if chapter_start is None:
        return []
    overview_start = None
    end = len(paras)
    for i in range(chapter_start + 1, len(paras)):
        style = paras[i].style.name if paras[i].style else ""
        if style.startswith("Heading 1"):
            end = i
            break
        if overview_start is None and style.startswith("Heading 2") and paras[i].text.strip().lower() == "overview":
            overview_start = i
    if overview_start is None:
        return []
    return [(p.style.name if p.style else "", p.text.strip()) for p in paras[overview_start:end]]


# --- PDF variant of extract_overview_paragraphs -----------------------
# The distributed Technical_Reference.pdf has no paragraph "style" the way
# the docx does, but its Overview section has a stable numbered-heading
# convention we can regex against instead: "<chap>.<sect> ...... Overview"
# (Heading 2) and "<chap>.<sect>.<n> ...... Category Name" (Heading 3,
# dot-leader length varies). These regexes produce the same (style, text)
# shape as extract_overview_paragraphs, so parse_overview() below works
# unchanged on either source.
CHAPTER_ANCHOR_RE = re.compile(r"macros and include", re.IGNORECASE)
CHAPTER_TITLE_RE = re.compile(r"^\d+\.\s+[A-Z][A-Z0-9 \-/&']{3,}$")
OVERVIEW_HEADING_RE = re.compile(r"^(\d+)\.(\d+)[\s.]+Overview$", re.IGNORECASE)
SECTION2_HEADING_RE = re.compile(r"^(\d+)\.(\d+)[\s.]+(\S.*)$")
SECTION3_HEADING_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)[\s.]+(\S.*)$")


def _is_running_header_or_footer(line):
    # e.g. "Macros and Include files 246" or "246  Macros and Include files"
    stripped = re.sub(r"\d+", "", line).strip()
    return len(stripped) < 40 and bool(CHAPTER_ANCHOR_RE.search(stripped))


def extract_overview_lines_from_pdf(reader):
    """Same contract as extract_overview_paragraphs: returns a list of
    (style_name, text) scoped to the "Macros and Include files" chapter's
    Overview section only."""
    n_pages = len(reader.pages)
    page_texts = [reader.pages[i].extract_text() or "" for i in range(n_pages)]

    start_page = None
    prefix2 = None
    for i, text in enumerate(page_texts):
        if not CHAPTER_ANCHOR_RE.search(text):
            continue
        for line in text.split("\n"):
            m = OVERVIEW_HEADING_RE.match(line.strip())
            if m:
                start_page = i
                prefix2 = f"{m.group(1)}.{m.group(2)}"
                break
        if start_page is not None:
            break
    if start_page is None:
        return []

    entries = [("Heading 2", "Overview")]
    started = False
    for i in range(start_page, n_pages):
        for raw_line in page_texts[i].split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            if not started:
                if OVERVIEW_HEADING_RE.match(line):
                    started = True
                continue
            if CHAPTER_TITLE_RE.match(line):
                return entries
            m3 = SECTION3_HEADING_RE.match(line)
            if m3 and f"{m3.group(1)}.{m3.group(2)}" == prefix2:
                entries.append(("Heading 3", m3.group(4).strip()))
                continue
            m2 = SECTION2_HEADING_RE.match(line)
            if m2 and f"{m2.group(1)}.{m2.group(2)}" != prefix2:
                entries.append(("Heading 2", line))
                continue
            if _is_running_header_or_footer(line):
                continue
            entries.append(("Normal", line))
    return entries


def load_pdf_overview(pdf_path):
    try:
        import pypdf
    except ImportError:
        print("WARNING: no docx given and pypdf isn't installed (pip install pypdf) "
              "-- continuing without §21.2 descriptions.", file=sys.stderr)
        return {}
    if not os.path.isfile(pdf_path):
        print(f"WARNING: Technical_Reference.pdf not found at {pdf_path!r} -- continuing "
              f"without §21.2 descriptions.", file=sys.stderr)
        return {}
    reader = pypdf.PdfReader(pdf_path)
    entries = extract_overview_lines_from_pdf(reader)
    if not entries:
        print("WARNING: could not locate Chapter 21 'Overview' section in the given "
              "PDF -- continuing without §21.2 descriptions.", file=sys.stderr)
        return {}
    return parse_overview(entries)


def parse_overview(entries):
    """entries: list of (style_name, text). Returns {category: [entry, ...]}."""
    category = None
    current = None
    categories = {}
    for style, text in entries:
        if not text:
            continue
        if style.startswith("Heading 3"):
            category = text
            categories.setdefault(category, [])
            current = None
            continue
        if style.startswith("Heading 2"):
            category = None
            current = None
            continue
        if category is None:
            continue
        if is_signature_line(text):
            current = {"signature": text, "description": [], "args": []}
            categories[category].append(current)
            continue
        if current is None:
            categories[category].append({"signature": None, "description": [text], "args": []})
            continue
        # accepts both "name: desc" (current docx) and "[name]: desc" (older
        # PDF editions, back when brackets were used for glossary labels too)
        m = re.match(r"^\[?([A-Za-z_][\w, ]{0,40})\]?:\s*(.+)$", text)
        if m and len(m.group(1)) < 40:
            current["args"].append({"names": m.group(1).strip(), "desc": m.group(2).strip()})
        else:
            current["description"].append(text)
    return categories


def load_docx_overview(docx_path):
    try:
        import docx
    except ImportError:
        print("WARNING: --docx given but the 'python-docx' package isn't installed "
              "(pip install python-docx) -- continuing without §21.2 descriptions.",
              file=sys.stderr)
        return {}
    if not os.path.isfile(docx_path):
        print(f"WARNING: --docx path not found: {docx_path!r} -- continuing without "
              f"§21.2 descriptions.", file=sys.stderr)
        return {}
    doc = docx.Document(docx_path)
    entries = extract_overview_paragraphs(doc)
    if not entries:
        print("WARNING: could not locate Chapter 21 'Overview' section in the given "
              "docx -- continuing without §21.2 descriptions.", file=sys.stderr)
        return {}
    return parse_overview(entries)


# ---------------------------------------------------------------------------
# Step 3: cross-reference real macros against docx categories by name
# ---------------------------------------------------------------------------

NAME_IN_SIG_RE = re.compile(r"([A-Za-z_]\w*)\s*(\([^)]*\))?")


def build_groups(real_macros, overview):
    """overview's keys ARE the category order -- taken as-is from whatever
    Heading-3 text actually appears in the docx (in document order), never
    a hardcoded guess list. That way a manual edit to a category's name
    (a typo fix, a reordering, a new category) is picked up automatically
    instead of silently falling out of a stale hardcoded list."""
    category_order = list(overview.keys())

    doc_by_name = {}
    for cat in category_order:
        for entry in overview.get(cat, []):
            sig = entry.get("signature")
            if not sig:
                continue
            for nm in NAME_IN_SIG_RE.findall(sig):
                name = nm[0]
                if name.lower() == "or":
                    continue
                doc_by_name.setdefault(name.lower(), (cat, entry))

    by_name = {}
    for m in real_macros:
        by_name.setdefault(m["name"], []).append(m)

    documented = {cat: [] for cat in category_order}
    undocumented = {}

    for name, overloads in sorted(by_name.items(), key=lambda kv: kv[0].lower()):
        doc = doc_by_name.get(name.lower())
        source_files = sorted(set(o["source_file"] for o in overloads))
        entry = {
            "name": name, "overloads": overloads, "source_files": source_files,
            "doc_description": doc[1]["description"] if doc else [],
            "doc_args": doc[1]["args"] if doc else [],
        }
        if doc:
            documented[doc[0]].append(entry)
        else:
            undocumented.setdefault(source_files[0], []).append(entry)

    return documented, undocumented, category_order


# ---------------------------------------------------------------------------
# Step 4: render self-contained HTML
# ---------------------------------------------------------------------------

esc = htmlmod.escape


def signature_html(name, overloads):
    parts = []
    for ov in overloads:
        amp = "&amp;" if ov["amp"] else ""
        args = ", ".join(esc(a) for a in ov["args"])
        parts.append(f'<span class="sig">{esc(name)}({amp}{args})</span>' if ov["args"] or ov["amp"]
                      else f'<span class="sig">{esc(name)}</span>')
    return " &nbsp;or&nbsp; ".join(parts)


def macro_entry_html(entry, idx):
    name = entry["name"]
    overloads = entry["overloads"]
    sig_html = signature_html(name, overloads)
    desc = entry.get("doc_description") or []
    args = entry.get("doc_args") or []
    sources = sorted(set(ov["source_file"] for ov in overloads))
    bodies = []
    for ov in overloads:
        args_disp = ", ".join(ov["args"]) if ov["args"] else ""
        header = f'{"&amp; " if ov["amp"] else ""}{esc(name)}({esc(args_disp)})'
        src_file_js = esc(ov["source_file"])
        bodies.append(
            f'<div class="overload"><code class="ov-head">{header}</code> '
            f'<span class="src-tag">{esc(ov["source_file"])}:{ov["line"]}</span> '
            f'<button class="open-btn" onclick="openInEditor(event, \'{src_file_js}\', {ov["line"]})">'
            f'Open in editor</button>'
            f'<pre class="macro-body">{esc(ov["body"])}</pre></div>'
        )
    desc_html = "".join(f"<p>{esc(d)}</p>" for d in desc) if desc else \
        '<p class="undoc-note">Not individually described in Technical_Reference &sect;21.2 (real definition below).</p>'
    args_html = ""
    if args:
        rows = "".join(f'<tr><td class="arg-name">{esc(a["names"])}</td><td>{esc(a["desc"])}</td></tr>' for a in args)
        args_html = f'<table class="arg-table">{rows}</table>'
    body_html = "".join(bodies)
    return (
        f'<div class="macro" data-name="{esc(name.lower())}">'
        f'<div class="macro-head" onclick="toggleMacro(this)">'
        f'<span class="chevron">&#9656;</span> {sig_html} '
        f'<span class="src-tag">{esc(", ".join(sources))}</span></div>'
        f'<div class="macro-detail">{desc_html}{args_html}{body_html}</div>'
        f'</div>'
    )


FQ_PREFIX_RE = re.compile(r"^f0_")


def render_html(documented, undocumented, category_order, source_label="Technical_Reference"):
    sections_html = []
    idx = 0

    for cat in category_order:
        entries = documented.get(cat, [])
        if not entries:
            continue
        items = []
        for e in entries:
            items.append(macro_entry_html(e, idx))
            idx += 1
        sections_html.append(
            f'<div class="group"><div class="group-head" onclick="toggleGroup(this)">'
            f'<span class="chevron">&#9656;</span> {esc(cat)} <span class="count">({len(entries)})</span></div>'
            f'<div class="group-body">{"".join(items)}</div></div>'
        )

    for fname, entries in sorted(undocumented.items(), key=lambda kv: -len(kv[1])):
        fq_entries = [e for e in entries if FQ_PREFIX_RE.match(e["name"])]
        other_entries = [e for e in entries if not FQ_PREFIX_RE.match(e["name"])]
        items = []
        for e in other_entries:
            items.append(macro_entry_html(e, idx))
            idx += 1
        fq_html = ""
        if fq_entries:
            fq_items = []
            for e in fq_entries:
                fq_items.append(macro_entry_html(e, idx))
                idx += 1
            fq_html = (
                f'<div class="group nested"><div class="group-head" onclick="toggleGroup(this)">'
                f'<span class="chevron">&#9656;</span> Atomic scattering factor macros (f0_*) '
                f'<span class="count">({len(fq_entries)})</span></div>'
                f'<div class="group-body">{"".join(fq_items)}</div></div>'
            )
        sections_html.append(
            f'<div class="group"><div class="group-head" onclick="toggleGroup(this)">'
            f'<span class="chevron">&#9656;</span> {esc(fname)} <span class="undoc-badge">not in &sect;21.2</span> '
            f'<span class="count">({len(entries)})</span></div>'
            f'<div class="group-body">{"".join(items)}{fq_html}</div></div>'
        )

    body_content = "\n".join(sections_html)
    total_documented = sum(len(v) for v in documented.values())
    total_undocumented = sum(len(v) for v in undocumented.values())

    return f"""<title>TOPAS Macro Browser</title>
<style>
:root {{
  --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280; --border: #e2e2e2;
  --accent: #2563eb; --code-bg: #f4f4f5; --hover: #f0f4ff; --badge-bg: #fef3c7; --badge-fg: #92400e;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg: #12141a; --fg: #e6e6e6; --muted: #9aa0aa; --border: #2a2d36;
    --accent: #7aa2ff; --code-bg: #1c1f28; --hover: #1a2333; --badge-bg: #3a2f10; --badge-fg: #e8c874; }}
}}
:root[data-theme="dark"] {{ --bg: #12141a; --fg: #e6e6e6; --muted: #9aa0aa; --border: #2a2d36;
  --accent: #7aa2ff; --code-bg: #1c1f28; --hover: #1a2333; --badge-bg: #3a2f10; --badge-fg: #e8c874; }}
:root[data-theme="light"] {{ --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280; --border: #e2e2e2;
  --accent: #2563eb; --code-bg: #f4f4f5; --hover: #f0f4ff; --badge-bg: #fef3c7; --badge-fg: #92400e; }}
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--fg);
  margin: 0; padding: 1.5rem; line-height: 1.5; }}
h1 {{ font-size: 1.4rem; margin: 0 0 0.25rem; }}
.subtitle {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 1rem; }}
.toolbar {{ display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; align-items: center; }}
#filter {{ flex: 1; min-width: 220px; padding: 0.5rem 0.75rem; border-radius: 6px; border: 1px solid var(--border);
  background: var(--code-bg); color: var(--fg); font-size: 0.9rem; }}
button.tbtn {{ padding: 0.5rem 0.9rem; border-radius: 6px; border: 1px solid var(--border); background: var(--code-bg);
  color: var(--fg); cursor: pointer; font-size: 0.85rem; }}
button.tbtn:hover {{ background: var(--hover); }}
.group {{ border: 1px solid var(--border); border-radius: 8px; margin-bottom: 0.6rem; overflow: hidden; }}
.group.nested {{ margin: 0.5rem 0 0.5rem 1rem; }}
.group-head {{ padding: 0.6rem 0.9rem; cursor: pointer; font-weight: 600; user-select: none; background: var(--code-bg); }}
.group-head:hover {{ background: var(--hover); }}
.group-body {{ display: none; padding: 0.3rem 0.6rem 0.6rem; }}
.group.open > .group-body {{ display: block; }}
.group.open > .group-head > .chevron {{ transform: rotate(90deg); }}
.chevron {{ display: inline-block; transition: transform 0.1s; margin-right: 0.3rem; color: var(--accent); }}
.count {{ color: var(--muted); font-weight: 400; font-size: 0.85rem; }}
.undoc-badge {{ background: var(--badge-bg); color: var(--badge-fg); font-size: 0.7rem; padding: 0.1rem 0.4rem;
  border-radius: 4px; margin-left: 0.4rem; font-weight: 600; }}
.macro {{ border-top: 1px solid var(--border); }}
.macro:first-child {{ border-top: none; }}
.macro-head {{ padding: 0.5rem 0.4rem; cursor: pointer; }}
.macro-head:hover {{ background: var(--hover); }}
.sig {{ font-family: "Cascadia Code", Consolas, monospace; color: var(--accent); font-size: 0.9rem; }}
.src-tag {{ color: var(--muted); font-size: 0.75rem; margin-left: 0.5rem; }}
.macro-detail {{ display: none; padding: 0.3rem 0.6rem 0.8rem 1.6rem; }}
.macro.open > .macro-detail {{ display: block; }}
.macro.open > .macro-head > .chevron {{ transform: rotate(90deg); }}
.macro-detail p {{ margin: 0.3rem 0; }}
.undoc-note {{ color: var(--muted); font-style: italic; font-size: 0.85rem; }}
.arg-table {{ border-collapse: collapse; margin: 0.4rem 0; font-size: 0.85rem; }}
.arg-table td {{ padding: 0.15rem 0.6rem 0.15rem 0; vertical-align: top; }}
.arg-name {{ font-family: Consolas, monospace; color: var(--accent); white-space: nowrap; }}
.overload {{ margin-top: 0.4rem; }}
.ov-head {{ font-size: 0.8rem; color: var(--muted); }}
.macro-body {{ background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 0.6rem;
  font-family: Consolas, monospace; font-size: 0.8rem; white-space: pre-wrap; overflow-x: auto; margin: 0.3rem 0 0.6rem; }}
.hidden {{ display: none !important; }}
.open-btn {{ padding: 0.1rem 0.5rem; border-radius: 4px; border: 1px solid var(--border); background: var(--code-bg);
  color: var(--accent); cursor: pointer; font-size: 0.72rem; }}
.open-btn:hover {{ background: var(--hover); }}
#dirbar {{ display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.75rem; font-size: 0.8rem; color: var(--muted); }}
#dirbar input {{ flex: 1; min-width: 200px; padding: 0.35rem 0.6rem; border-radius: 6px; border: 1px solid var(--border);
  background: var(--code-bg); color: var(--fg); font-size: 0.8rem; font-family: Consolas, monospace; }}
</style>
<h1>TOPAS Macro Browser</h1>
<div class="subtitle">{total_documented} macros cross-referenced against {esc(source_label)} &sect;21.2 &middot;
{total_undocumented} more harvested directly from the real .inc source, grouped by file &middot;
signatures/arguments/bodies always come from the real .inc files, never the manual</div>
<div id="dirbar">
  <label for="dirInput">TOPAS install directory (for "Open in editor"):</label>
  <input id="dirInput" type="text" placeholder="e.g. C:\\TOPAS6 or C:\\w\\ta-web2" oninput="saveTopasDir()">
</div>
<div class="toolbar">
  <input id="filter" type="text" placeholder="Filter macros by name..." oninput="applyFilter()">
  <button class="tbtn" onclick="expandAll()">Expand all</button>
  <button class="tbtn" onclick="collapseAll()">Collapse all</button>
</div>
<div id="content">
{body_content}
</div>
<script>
var TOPAS_DIR_KEY = 'topas_macro_browser_dir';
(function() {{
  var saved = localStorage.getItem(TOPAS_DIR_KEY);
  if (saved) document.getElementById('dirInput').value = saved;
}})();
function saveTopasDir() {{
  localStorage.setItem(TOPAS_DIR_KEY, document.getElementById('dirInput').value.trim());
}}
function openInEditor(evt, sourceFile, line) {{
  evt.stopPropagation();
  var dir = document.getElementById('dirInput').value.trim();
  if (!dir) {{
    alert('Enter your TOPAS install directory above first, so this can find ' + sourceFile + '.');
    document.getElementById('dirInput').focus();
    return;
  }}
  var norm = dir.replace(/\\\\/g, '/');
  while (norm.charAt(norm.length - 1) === '/') {{ norm = norm.slice(0, -1); }}
  var url = 'vscode://file/' + norm + '/' + sourceFile + ':' + line;
  window.location.href = url;
}}
function toggleGroup(headEl) {{
  headEl.parentElement.classList.toggle('open');
}}
function toggleMacro(headEl) {{
  headEl.parentElement.classList.toggle('open');
}}
function expandAll() {{
  document.querySelectorAll('.group, .macro').forEach(function(el) {{ el.classList.add('open'); }});
}}
function collapseAll() {{
  document.querySelectorAll('.group, .macro').forEach(function(el) {{ el.classList.remove('open'); }});
}}
function applyFilter() {{
  var q = document.getElementById('filter').value.trim().toLowerCase();
  document.querySelectorAll('.macro').forEach(function(m) {{
    var match = !q || m.getAttribute('data-name').indexOf(q) !== -1;
    m.classList.toggle('hidden', !match);
    if (match && q) {{ m.classList.add('open'); }}
  }});
  document.querySelectorAll('.group').forEach(function(g) {{
    var anyVisible = g.querySelector('.macro:not(.hidden)') !== null || g.querySelector('.group:not(.hidden) .macro:not(.hidden)') !== null;
    g.classList.toggle('hidden', q && !anyVisible);
    if (q && anyVisible) {{ g.classList.add('open'); }}
  }});
}}
</script>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docx", metavar="PATH", help="Path to your own copy of Technical_Reference.docx, "
                         "if you have it (optional -- not bundled with this skill, and not what a real "
                         "TOPAS install ships). Requires python-docx. Takes priority over --pdf/auto-resolved "
                         "PDF when given, since the docx is the live editing copy.")
    parser.add_argument("--pdf", metavar="PATH", help="Path to Technical_Reference.pdf (optional -- by default "
                         "this is auto-resolved under TOPAS_DIR via topas_install.get_technical_reference_pdf(), "
                         "since the PDF, unlike the docx, ships with a real TOPAS install). Requires pypdf. "
                         "Pass --no-pdf to skip §21.2 descriptions entirely instead.")
    parser.add_argument("--no-pdf", action="store_true", help="Skip auto-resolving Technical_Reference.pdf "
                         "under TOPAS_DIR -- every macro will be grouped by source .inc file with no "
                         "§21.2 description/category. Ignored if --docx or --pdf is given.")
    parser.add_argument("-o", "--output", metavar="PATH", default=None,
                         help="Output HTML path (default: macro_browser.html directly under TOPAS_DIR, "
                              "the same 'lives in the real install, not the skill' spot resolved by "
                              "topas_install.get_macro_browser_html()).")
    args = parser.parse_args()

    inc_dir, found = topas_install.get_inc_dir()
    if not found:
        print("ERROR: could not find the real .inc library (topas.inc and friends). "
              "Set TOPAS_DIR to your TOPAS install root -- this skill does not bundle "
              "copies of the .inc files. See SKILL.md's 'Locating your TOPAS installation'.",
              file=sys.stderr)
        sys.exit(1)

    output_path = args.output
    if output_path is None:
        topas_dir, dir_found = topas_install.get_topas_dir()
        if not dir_found:
            print("ERROR: no -o/--output given and TOPAS_DIR isn't set, so there's nowhere to "
                  "default the output to. Either set TOPAS_DIR or pass -o explicitly.",
                  file=sys.stderr)
            sys.exit(1)
        output_path = os.path.join(topas_dir, topas_install.MACRO_BROWSER_HTML_BASENAME)
    print(f"Harvesting macros from {inc_dir}", file=sys.stderr)
    real_macros = harvest_all(inc_dir)
    print(f"Total real macro definitions: {len(real_macros)}", file=sys.stderr)

    overview = {}
    source_label = "Technical_Reference"
    if args.docx:
        overview = load_docx_overview(args.docx)
        source_label = "Technical_Reference.docx"
    elif args.no_pdf:
        print("--no-pdf given -- every macro will be grouped by source .inc file with "
              "no §21.2 description/category.", file=sys.stderr)
    else:
        pdf_path = args.pdf
        if pdf_path is None:
            pdf_path, pdf_found = topas_install.get_technical_reference_pdf()
            if not pdf_found:
                print("No --docx/--pdf given and no Technical_Reference.pdf found under TOPAS_DIR "
                      "-- every macro will be grouped by source .inc file with no §21.2 "
                      "description/category. Pass --pdf, or place a copy at "
                      "<TOPAS_DIR>/Technical_Reference.pdf.", file=sys.stderr)
                pdf_path = None
        if pdf_path:
            overview = load_pdf_overview(pdf_path)
            source_label = "Technical_Reference.pdf"

    if overview:
        n_entries = sum(len(v) for v in overview.values())
        print(f"Parsed {n_entries} §21.2 overview entries across {len(overview)} categories", file=sys.stderr)

    documented, undocumented, category_order = build_groups(real_macros, overview)
    n_doc = sum(len(v) for v in documented.values())
    n_undoc = sum(len(v) for v in undocumented.values())
    print(f"Matched to §21.2 categories: {n_doc} macro names; undocumented: {n_undoc}", file=sys.stderr)

    html_out = render_html(documented, undocumented, category_order, source_label)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"Wrote {output_path} ({len(html_out)} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
