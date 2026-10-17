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
    python topas_install.py --inc-dir
    python topas_install.py --example cf/alvo4a.inp
    python topas_install.py --kernel-schema-html
    python topas_install.py --macro-browser-html
    python topas_install.py --technical-reference-pdf
    python topas_install.py --keyword-tree-html

kernel_structure_tree.html (the "Show Schema" page, pre-rendered from
TOPAS's internal kernel data-structure listing) is resolved the same
TOPAS_DIR-search way: the source it's built from (the kernel's own internal type dump,
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

    Deliberately does NOT go through _get_cache(): the root is just the
    environment variable, so walking the whole install to build the file
    index before handing it back would be pure waste. The check here is
    identical to the one _get_cache() applies (set, and a real directory),
    so the answer is the same either way. This matters because it is the
    most-travelled entry point in the script set -- symmetry_utils.py
    calls it, and that is imported by check_inp_syntax.py, cif_to_str.py,
    plot_str_3d.py, insert_adps.py and symmetrize_str.py.
    """
    topas_dir = os.environ.get("TOPAS_DIR", "").strip()
    if topas_dir and os.path.isdir(topas_dir):
        return topas_dir, True
    return "", False


def find_tc(why=""):
    """Path to tc.exe under TOPAS_DIR. Raises SystemExit, with `why` appended
    to the message, if it can't be found -- there is no fallback location."""
    root, found = get_topas_dir()
    if found:
        for exe in ("tc.exe", "TC.EXE", "tc"):
            p = os.path.join(root, exe)
            if os.path.exists(p):
                return p
    raise SystemExit(("Could not locate tc.exe -- set TOPAS_DIR to your TOPAS install root. "
                      + why).strip())


def tc_env(tc_path=None):
    """Environment for a tc.exe subprocess, with tc.exe's own directory on PATH.

    tc.exe calls helper programs such as sgcom6 by bare name. Without its
    install directory on PATH, any space group not already compiled to
    sg/*.sg aborts the run ("Cannot open file ...\\sg\\<group>.sg"). TOPAS-GUI
    sets PATH through its own batch files; a bare subprocess does not.
    """
    tc_dir = os.path.dirname(os.path.abspath(tc_path or find_tc()))
    env = os.environ.copy()
    env["PATH"] = tc_dir + os.pathsep + env.get("PATH", "")
    return env


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
    False. The page lives under TOPAS_DIR, not inside the skill.
    """
    cache = _get_cache()
    if cache["macro_browser_html"]:
        return cache["macro_browser_html"], True
    return NO_MACRO_BROWSER_HTML_PLACEHOLDER, False


def get_technical_reference_pdf():
    """
    Returns (path, found). Technical_Reference.pdf (unlike the .docx
    editing copy) ships with a real TOPAS install, so it's resolved the
    same TOPAS_DIR-search way as everything else here.
    """
    cache = _get_cache()
    if cache["technical_reference_pdf"]:
        return cache["technical_reference_pdf"], True
    return NO_TECHNICAL_REFERENCE_PDF_PLACEHOLDER, False


def get_keyword_tree_html():
    """
    Returns (path, found). Like macro_browser.html, topas_keyword_tree.html
    lives under TOPAS_DIR rather than inside the skill.
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
    # flag -> (lookup, help text, what to call it in a not-found message)
    lookups = {
        "inc_dir": (get_inc_dir, "Print the resolved .inc macro library directory.", "topas.inc"),
        "kernel_schema_html": (get_kernel_schema_html,
                               "Print the resolved kernel_structure_tree.html path (the pre-rendered "
                               "'Show Schema' page shipped inside a real TOPAS install).",
                               KERNEL_SCHEMA_HTML_BASENAME),
        "macro_browser_html": (get_macro_browser_html, "Print the resolved macro_browser.html path.",
                               MACRO_BROWSER_HTML_BASENAME),
        "technical_reference_pdf": (get_technical_reference_pdf,
                                    "Print the resolved Technical_Reference.pdf path.",
                                    "Technical_Reference.pdf"),
        "keyword_tree_html": (get_keyword_tree_html, "Print the resolved topas_keyword_tree.html path.",
                              KEYWORD_TREE_HTML_BASENAME),
    }
    parser = argparse.ArgumentParser(
        description="Resolve TOPAS install file paths via TOPAS_DIR (no bundled fallback -- set TOPAS_DIR)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    for dest, (_, help_text, _) in lookups.items():
        group.add_argument("--" + dest.replace("_", "-"), action="store_true", help=help_text)
    group.add_argument("--example", metavar="REL_PATH",
                        help='Resolve an example file, e.g. "cf/alvo4a.inp" (path style used in references/examples-index.md).')
    args = parser.parse_args()

    if args.example:
        path, found = resolve_example(args.example)
        what = repr(args.example)
    else:
        dest = next(d for d in lookups if getattr(args, d))
        lookup, _, what = lookups[dest]
        path, found = lookup()
    print(path)

    topas_dir = os.environ.get("TOPAS_DIR", "").strip()
    if found:
        print("(found via TOPAS_DIR)", file=sys.stderr)
    elif topas_dir:
        print(f"(NOT FOUND -- TOPAS_DIR={topas_dir!r} was searched but {what} wasn't found under it"
              f"{' or matched ambiguously' if args.example else ''}; this skill has no bundled "
              f"fallback copy)", file=sys.stderr)
    else:
        print("(NOT FOUND -- TOPAS_DIR is not set; this skill has no bundled fallback copy. "
              "Set TOPAS_DIR to your TOPAS install root.)", file=sys.stderr)


if __name__ == "__main__":
    main()
