#!/usr/bin/env python3
"""
topas_install.py -- locate a real TOPAS installation's own files (topas.inc,
pdf.inc, and the release's own example .inp/.out files) via the TOPAS_DIR
environment variable.

This skill does NOT bundle copies of these files -- they ship with every
TOPAS release already, and keeping a separate snapshot inside the skill
meant maintaining (and inevitably letting go stale) two copies of the same
content. Instead, TOPAS_DIR must point at the root of a real TOPAS
installation (wherever tc.exe/TA.EXE live, or any ancestor directory of
it), and this module searches under it -- once per process, cached -- to
find:
  - the directory containing topas.inc (enables macro-arity checking in
    check_inp_syntax.py and library-macro expansion in
    expand_inp_macros.py)
  - individual example .inp/.out files by relative path (e.g.
    "cf/alvo4a.inp", matching the paths used in references/examples-
    index.md), matched by parent-folder-name + filename first (the
    example set has same-named files in different subfolders -- there
    are three different "alvo4a.inp"s across a real install), falling
    back to a bare-filename match only when that's unambiguous.

If TOPAS_DIR is unset, not a real directory, or a specific file can't be
found under it, these functions return a path that simply doesn't exist
(callers already check os.path.isfile/isdir and degrade gracefully -- see
check_inp_syntax.py's and expand_inp_macros.py's own warning messages).
There is deliberately no bundled fallback copy: set TOPAS_DIR to restore
full functionality. See SKILL.md's "Locating your TOPAS installation"
section for the full explanation.

Usable as a library:
    import topas_install
    inc_dir, found = topas_install.get_inc_dir()
    example_path, found = topas_install.resolve_example("cf/alvo4a.inp")
    schema_html, found = topas_install.get_kernel_schema_html()
    macro_browser_html, found = topas_install.get_macro_browser_html()
    ref_pdf, found = topas_install.get_technical_reference_pdf()
    keyword_tree_html, found = topas_install.get_keyword_tree_html()

Or as a CLI (handy for Claude to shell out to before reading a file):
    python3 topas_install.py --inc-dir
    python3 topas_install.py --example cf/alvo4a.inp
    python3 topas_install.py --kernel-schema-html
    python3 topas_install.py --macro-browser-html
    python3 topas_install.py --technical-reference-pdf
    python3 topas_install.py --keyword-tree-html

kernel_structure_tree.html (the "Show Schema" page, pre-rendered from
TOPAS's internal kernel data-structure listing -- see
scripts/kernel_structure_tree.py) is resolved the same TOPAS_DIR-search
way: the source it's built from (the kernel's own internal type dump,
exx.txt) is never distributed, only the rendered HTML, which ships
inside each real TOPAS install (wherever the release process places it
under TOPAS_DIR) rather than inside this skill.
"""

import os
import sys
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# These paths intentionally do NOT exist -- there is no bundled fallback
# copy (see module docstring). They exist only as stable "not found"
# placeholders so callers can keep using their existing os.path.isdir/
# isfile checks without special-casing None.
NO_INC_DIR_PLACEHOLDER = os.path.join(SCRIPT_DIR, "..", "references", "system-files", "inc")
NO_EXAMPLES_DIR_PLACEHOLDER = os.path.join(SCRIPT_DIR, "..", "references", "examples")
NO_KERNEL_SCHEMA_HTML_PLACEHOLDER = os.path.join(SCRIPT_DIR, "..", "references", "kernel_structure_tree.html")
NO_MACRO_BROWSER_HTML_PLACEHOLDER = os.path.join(SCRIPT_DIR, "..", "references", "macro_browser.html")
NO_TECHNICAL_REFERENCE_PDF_PLACEHOLDER = os.path.join(SCRIPT_DIR, "..", "references", "Technical_Reference.pdf")
NO_KEYWORD_TREE_HTML_PLACEHOLDER = os.path.join(SCRIPT_DIR, "..", "references", "topas_keyword_tree.html")

KERNEL_SCHEMA_HTML_BASENAME = "kernel_structure_tree.html"
MACRO_BROWSER_HTML_BASENAME = "macro_browser.html"
TECHNICAL_REFERENCE_PDF_BASENAME = "technical_reference.pdf"
KEYWORD_TREE_HTML_BASENAME = "topas_keyword_tree.html"

# Safety cap on how many files a walk will look at, so an unexpectedly
# huge or unusual TOPAS_DIR (e.g. pointed at a whole drive by mistake)
# can't make a run hang.
MAX_WALK_FILES = 60000

_cache = None  # lazily built; see _get_cache()


def _walk_topas_dir(topas_dir):
    inc_dir = None
    kernel_schema_html = None
    macro_browser_html = None
    technical_reference_pdf = None
    keyword_tree_html = None
    by_relkey = {}   # "parentdirname/filename.ext" (lowercased) -> [full paths]
    by_basekey = {}  # "filename.ext" (lowercased) -> [full paths]
    count = 0
    for root, dirs, files in os.walk(topas_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d.lower() not in ("__pycache__", "node_modules", ".git", ".svn")]
        for fname in files:
            count += 1
            if count > MAX_WALK_FILES:
                break
            lower = fname.lower()
            fpath = os.path.join(root, fname)
            if lower == "topas.inc" and inc_dir is None:
                inc_dir = root
            if lower == KERNEL_SCHEMA_HTML_BASENAME.lower() and kernel_schema_html is None:
                kernel_schema_html = fpath
            if lower == MACRO_BROWSER_HTML_BASENAME.lower() and macro_browser_html is None:
                macro_browser_html = fpath
            if lower == TECHNICAL_REFERENCE_PDF_BASENAME and technical_reference_pdf is None:
                technical_reference_pdf = fpath
            if lower == KEYWORD_TREE_HTML_BASENAME.lower() and keyword_tree_html is None:
                keyword_tree_html = fpath
            if lower.endswith((".inp", ".out", ".inc", ".txt")):
                parent = os.path.basename(root).lower()
                relkey = f"{parent}/{lower}"
                by_relkey.setdefault(relkey, []).append(fpath)
                by_basekey.setdefault(lower, []).append(fpath)
        if count > MAX_WALK_FILES:
            break
    return inc_dir, kernel_schema_html, macro_browser_html, technical_reference_pdf, keyword_tree_html, by_relkey, by_basekey


def _get_cache():
    global _cache
    if _cache is not None:
        return _cache
    topas_dir = os.environ.get("TOPAS_DIR", "").strip()
    if not topas_dir or not os.path.isdir(topas_dir):
        _cache = {"topas_dir": None, "inc_dir": None, "kernel_schema_html": None,
                  "macro_browser_html": None, "technical_reference_pdf": None, "keyword_tree_html": None,
                  "by_relkey": {}, "by_basekey": {}}
        return _cache
    inc_dir, kernel_schema_html, macro_browser_html, technical_reference_pdf, keyword_tree_html, by_relkey, by_basekey = _walk_topas_dir(topas_dir)
    _cache = {"topas_dir": topas_dir, "inc_dir": inc_dir, "kernel_schema_html": kernel_schema_html,
              "macro_browser_html": macro_browser_html, "technical_reference_pdf": technical_reference_pdf,
              "keyword_tree_html": keyword_tree_html, "by_relkey": by_relkey, "by_basekey": by_basekey}
    return _cache


def get_topas_dir():
    """
    Returns (path, found) for the raw TOPAS_DIR root itself (not the .inc
    subdirectory -- see get_inc_dir for that). Used to resolve TOPAS's
    built-in `ROOT` reserved word, which the running kernel substitutes
    for its own install directory WITH a trailing separator already
    included (e.g. `ROOT` + "lam\\cuka5.lam" -> "<TOPAS_DIR>\\lam\\cuka5.lam"
    -- confirmed against a real install). `ROOT` itself never appears as
    literal text in topas.inc (it's a runtime substitution, not a
    #define/macro), so this needs its own accessor rather than reusing
    the harvested macro tables.
    """
    cache = _get_cache()
    if cache["topas_dir"]:
        return cache["topas_dir"], True
    return "", False


def get_inc_dir():
    """
    Returns (path, found). If TOPAS_DIR is set and a real topas.inc was
    found under it, path is that live directory and found is True.
    Otherwise path is a placeholder that does not exist and found is
    False -- there is no bundled fallback; set TOPAS_DIR to fix this.
    """
    cache = _get_cache()
    if cache["inc_dir"]:
        return cache["inc_dir"], True
    return NO_INC_DIR_PLACEHOLDER, False


def get_kernel_schema_html():
    """
    Returns (path, found). If TOPAS_DIR is set and a real
    kernel_structure_tree.html was found under it (placed there by the
    TOPAS release process -- see module docstring), path is that live
    file and found is True. Otherwise path is a placeholder that does not
    exist and found is False -- there is no bundled fallback copy (the
    generator that produces this page is not part of this skill either;
    only the rendered HTML shipped inside a real TOPAS install can
    satisfy this).
    """
    cache = _get_cache()
    if cache["kernel_schema_html"]:
        return cache["kernel_schema_html"], True
    return NO_KERNEL_SCHEMA_HTML_PLACEHOLDER, False


def get_macro_browser_html():
    """
    Returns (path, found). If TOPAS_DIR is set and a macro_browser.html
    was found under it, path is that live file and found is True.
    Otherwise path is a placeholder that does not exist and found is
    False. Unlike the kernel schema page, this skill DOES include the
    generator for this page (scripts/generate_macro_browser.py) -- but
    the rendered HTML itself lives under TOPAS_DIR, not inside the
    skill, since it can be large and is meant to be regenerated
    per-install (a --docx flag pulls in descriptions from the user's own
    copy of Technical_Reference.docx, which isn't bundled either).
    """
    cache = _get_cache()
    if cache["macro_browser_html"]:
        return cache["macro_browser_html"], True
    return NO_MACRO_BROWSER_HTML_PLACEHOLDER, False


def get_technical_reference_pdf():
    """
    Returns (path, found). Technical_Reference.pdf (unlike the .docx
    editing copy) ships with a real TOPAS install, so it's resolved the
    same TOPAS_DIR-search way as everything else here -- used by
    scripts/generate_macro_browser.py as its default source of §21.2
    descriptions when no --docx is given.
    """
    cache = _get_cache()
    if cache["technical_reference_pdf"]:
        return cache["technical_reference_pdf"], True
    return NO_TECHNICAL_REFERENCE_PDF_PLACEHOLDER, False


def get_keyword_tree_html():
    """
    Returns (path, found). Like macro_browser.html, topas_keyword_tree.html
    lives under TOPAS_DIR rather than inside the skill -- generated by
    scripts/topas_keyword_tree.py, which defaults its own output path
    here and skips regenerating if a copy already exists (pass --force
    to regenerate anyway).
    """
    cache = _get_cache()
    if cache["keyword_tree_html"]:
        return cache["keyword_tree_html"], True
    return NO_KEYWORD_TREE_HTML_PLACEHOLDER, False


def resolve_example(rel_path):
    """
    rel_path is like "cf/alvo4a.inp" (as used throughout references/
    examples-index.md). Returns (resolved_path, from_live).

    Matching is parent-folder-name + filename first (the example set has
    same-named files in different subfolders -- there are three
    different "alvo4a.inp"s across a real install -- so a bare filename
    match alone would be ambiguous/wrong). Falls back to a bare-filename
    match only when that's unambiguous (exactly one file with that name
    anywhere under TOPAS_DIR). If TOPAS_DIR isn't set or nothing matches,
    returns a placeholder path that does not exist -- there is no
    bundled fallback copy.
    """
    cache = _get_cache()
    rel_path_norm = rel_path.replace("\\", "/").strip("/")
    parts = rel_path_norm.split("/")
    fname = parts[-1].lower()
    parent = parts[-2].lower() if len(parts) > 1 else None

    if cache["topas_dir"]:
        if parent:
            candidates = cache["by_relkey"].get(f"{parent}/{fname}", [])
            if len(candidates) == 1:
                return candidates[0], True
        candidates = cache["by_basekey"].get(fname, [])
        if len(candidates) == 1:
            return candidates[0], True
        # ambiguous (multiple same-named files, none matching the parent
        # hint) or simply not present under the live install -- fall
        # through to the not-found placeholder below rather than guessing.

    placeholder_path = os.path.normpath(os.path.join(NO_EXAMPLES_DIR_PLACEHOLDER, rel_path_norm))
    return placeholder_path, False


def main():
    parser = argparse.ArgumentParser(
        description="Resolve TOPAS install file paths via TOPAS_DIR (no bundled fallback -- set TOPAS_DIR)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inc-dir", action="store_true",
                        help="Print the resolved .inc macro library directory.")
    group.add_argument("--example", metavar="REL_PATH",
                        help='Resolve an example file, e.g. "cf/alvo4a.inp" (path style used in references/examples-index.md).')
    group.add_argument("--kernel-schema-html", action="store_true",
                        help="Print the resolved kernel_structure_tree.html path (the pre-rendered 'Show Schema' page shipped inside a real TOPAS install).")
    group.add_argument("--macro-browser-html", action="store_true",
                        help="Print the resolved macro_browser.html path (generate it with scripts/generate_macro_browser.py if missing).")
    group.add_argument("--technical-reference-pdf", action="store_true",
                        help="Print the resolved Technical_Reference.pdf path (used by scripts/generate_macro_browser.py for §21.2 descriptions).")
    group.add_argument("--keyword-tree-html", action="store_true",
                        help="Print the resolved topas_keyword_tree.html path (generate it with scripts/topas_keyword_tree.py if missing).")
    args = parser.parse_args()

    topas_dir_set = bool(os.environ.get("TOPAS_DIR", "").strip())

    if args.inc_dir:
        path, found = get_inc_dir()
        print(path)
        if found:
            print("(found via TOPAS_DIR)", file=sys.stderr)
        elif topas_dir_set:
            print(f"(NOT FOUND -- TOPAS_DIR={os.environ['TOPAS_DIR']!r} was searched but no topas.inc "
                  f"turned up under it; check the path)", file=sys.stderr)
        else:
            print("(NOT FOUND -- TOPAS_DIR is not set; this skill has no bundled fallback copy. "
                  "Set TOPAS_DIR to your TOPAS install root.)", file=sys.stderr)
    elif args.kernel_schema_html:
        path, found = get_kernel_schema_html()
        print(path)
        if found:
            print("(found via TOPAS_DIR)", file=sys.stderr)
        elif topas_dir_set:
            print(f"(NOT FOUND -- TOPAS_DIR={os.environ['TOPAS_DIR']!r} was searched but no "
                  f"{KERNEL_SCHEMA_HTML_BASENAME} turned up under it; this skill has no bundled "
                  f"fallback copy and does not generate this page itself)", file=sys.stderr)
        else:
            print("(NOT FOUND -- TOPAS_DIR is not set; this skill has no bundled fallback copy and "
                  "does not generate this page itself. Set TOPAS_DIR to find the copy shipped with "
                  "your TOPAS install.)", file=sys.stderr)
    elif args.macro_browser_html:
        path, found = get_macro_browser_html()
        print(path)
        if found:
            print("(found via TOPAS_DIR)", file=sys.stderr)
        elif topas_dir_set:
            print(f"(NOT FOUND -- TOPAS_DIR={os.environ['TOPAS_DIR']!r} was searched but no "
                  f"{MACRO_BROWSER_HTML_BASENAME} turned up under it; generate one with "
                  f"scripts/generate_macro_browser.py [--docx path/to/Technical_Reference.docx])", file=sys.stderr)
        else:
            print("(NOT FOUND -- TOPAS_DIR is not set; this skill has no bundled fallback copy. "
                  "Set TOPAS_DIR to your TOPAS install root, then generate one with "
                  "scripts/generate_macro_browser.py.)", file=sys.stderr)
    elif args.technical_reference_pdf:
        path, found = get_technical_reference_pdf()
        print(path)
        if found:
            print("(found via TOPAS_DIR)", file=sys.stderr)
        elif topas_dir_set:
            print(f"(NOT FOUND -- TOPAS_DIR={os.environ['TOPAS_DIR']!r} was searched but no "
                  f"Technical_Reference.pdf turned up under it; this skill has no bundled fallback copy)",
                  file=sys.stderr)
        else:
            print("(NOT FOUND -- TOPAS_DIR is not set; this skill has no bundled fallback copy. "
                  "Set TOPAS_DIR to your TOPAS install root.)", file=sys.stderr)
    elif args.keyword_tree_html:
        path, found = get_keyword_tree_html()
        print(path)
        if found:
            print("(found via TOPAS_DIR)", file=sys.stderr)
        elif topas_dir_set:
            print(f"(NOT FOUND -- TOPAS_DIR={os.environ['TOPAS_DIR']!r} was searched but no "
                  f"{KEYWORD_TREE_HTML_BASENAME} turned up under it; generate one with "
                  f"scripts/topas_keyword_tree.py)", file=sys.stderr)
        else:
            print("(NOT FOUND -- TOPAS_DIR is not set; this skill has no bundled fallback copy. "
                  "Set TOPAS_DIR to your TOPAS install root, then generate one with "
                  "scripts/topas_keyword_tree.py.)", file=sys.stderr)
    else:
        path, found = resolve_example(args.example)
        if found:
            print(path)
            print("(found via TOPAS_DIR)", file=sys.stderr)
        elif topas_dir_set:
            print(path)
            print(f"(NOT FOUND -- TOPAS_DIR={os.environ['TOPAS_DIR']!r} was searched but "
                  f"{args.example!r} wasn't found there, or matched ambiguously)", file=sys.stderr)
        else:
            print(path)
            print("(NOT FOUND -- TOPAS_DIR is not set; this skill has no bundled fallback copy. "
                  "Set TOPAS_DIR to your TOPAS install root.)", file=sys.stderr)


if __name__ == "__main__":
    main()
