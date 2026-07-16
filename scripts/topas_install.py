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

Or as a CLI (handy for Claude to shell out to before reading a file):
    python3 topas_install.py --inc-dir
    python3 topas_install.py --example cf/alvo4a.inp
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

# Safety cap on how many files a walk will look at, so an unexpectedly
# huge or unusual TOPAS_DIR (e.g. pointed at a whole drive by mistake)
# can't make a run hang.
MAX_WALK_FILES = 60000

_cache = None  # lazily built; see _get_cache()


def _walk_topas_dir(topas_dir):
    inc_dir = None
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
            if lower.endswith((".inp", ".out", ".inc", ".txt")):
                parent = os.path.basename(root).lower()
                relkey = f"{parent}/{lower}"
                by_relkey.setdefault(relkey, []).append(fpath)
                by_basekey.setdefault(lower, []).append(fpath)
        if count > MAX_WALK_FILES:
            break
    return inc_dir, by_relkey, by_basekey


def _get_cache():
    global _cache
    if _cache is not None:
        return _cache
    topas_dir = os.environ.get("TOPAS_DIR", "").strip()
    if not topas_dir or not os.path.isdir(topas_dir):
        _cache = {"topas_dir": None, "inc_dir": None, "by_relkey": {}, "by_basekey": {}}
        return _cache
    inc_dir, by_relkey, by_basekey = _walk_topas_dir(topas_dir)
    _cache = {"topas_dir": topas_dir, "inc_dir": inc_dir, "by_relkey": by_relkey, "by_basekey": by_basekey}
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
