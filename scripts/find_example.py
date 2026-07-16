#!/usr/bin/env python3
"""
find_example.py -- search this project's curated `tcinps-2.bat` file list
for real, working .inp examples matching a topic query (e.g. "tof",
"pawley", "charge flipping", "stacking faults"), so a real worked
example can be found and read before writing a new template from
scratch -- the same "copy a real example, adapt it" principle this
skill already follows for example_inp_files/ and references/examples-
index.md, just scoped to the ~197-file curated regression corpus
(references/tcinps-2.bat parsing convention, see
feedback_use_tcinps_for_verification.md) instead of the full 1138-file
test_examples/ tree.

Trigger: **"<topic> template"** (or "<topic> example") -- run this
whenever the user asks for a template/example/starting point for some
refinement topic, confirmed directly by the user as a standing workflow
after this script was first built to find `tof\tof_bank2_1.inp`/
`tof\tof_bank2_2.inp` for a "tof template" request. This script only
FINDS and (optionally) opens the real matching file(s) -- it deliberately
does NOT try to auto-genericize a found example into a clean, commented
template (deciding what's an instrument constant to keep vs. a sample-
specific value to placeholder-ize needs real judgment per topic, not a
one-size-fits-all script). After finding the right example(s), read them
and write the actual template by hand, the same way `example_inp_files/
tof_template.inp` was built directly from this script's own first
"tof" search result.

Matching, in order (stops at the first stage that finds anything):
  1. PATH match -- the query's own words as substrings of each
     candidate's resolved path (case-insensitive). Most folders in the
     corpus are themselves topic-named (tof/, pawley/, cf/, mag/,
     rigid/, pdf/, stacking-faults/, indexing/, quant/, single-crystal/,
     ...), so this alone resolves most real queries reliably and fast,
     with no file reads needed.
  2. CONTENT match -- for a query that doesn't match any path (e.g. a
     concept/keyword rather than a folder name, "anisotropic
     broadening"), read each candidate and check for the query text (or
     a small curated synonym -> real-keyword table, TOPIC_SYNONYMS
     below, covering the refinement-type vocabulary from this skill's
     own "Starting a new INP file from scratch" question set) appearing
     literally in the file.

Usage:
    python3 scripts/find_example.py tof
    python3 scripts/find_example.py "tof template"        # trailing filler words are stripped
    python3 scripts/find_example.py pawley -n 5             # show up to 5 matches (default 8)
    python3 scripts/find_example.py "charge flipping" --open   # also open the top match in VS Code
"""

import sys
import os
import re
import argparse
import subprocess
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BAT = r"c:\w\tcinps-2.bat"

# Trailing/filler words stripped off the raw query before matching --
# "tof template" / "a pawley example file" both reduce to their real
# topic words this way.
FILLER_WORDS = {"template", "templates", "example", "examples", "file",
                 "files", "inp", "refinement", "a", "an", "the", "for", "of"}

TC_RE = re.compile(r"^\s*tc\s+(\S+)")

# Small, curated fallback vocabulary for a query that names a CONCEPT
# rather than a folder -- deliberately short, matching this skill's own
# "Starting a new INP file from scratch" branch list (see SKILL.md)
# rather than trying to anticipate every possible phrase. Extend this
# only when a real query turns up nothing via path OR this table --
# don't pre-populate speculatively.
TOPIC_SYNONYMS = {
    "rietveld": ["str", "site"],
    "pawley": ["hkl_Is"],
    "lebail": ["lebail"],
    "le bail": ["lebail"],
    "indexing": ["load index_th2", "index_lam"],
    "pdf": ["pdf_data", "Include_PDF_Generate"],
    "charge flipping": ["charge_flipping"],
    "quant": ["weight_percent", "dummy_str"],
    "quantitative": ["weight_percent", "dummy_str"],
    "stacking fault": ["generate_stack_sequences", "layer"],
    "rigid body": ["rigid", "z_matrix"],
    "deconvolution": ["Deconvolution_Init"],
    "magnetic": ["magnetic_only_for", "Shubnikov"],
    "protein": ["cf-protein", "pdb_cif_to_str_file"],
    "single crystal": ["xdd_scr"],
    "tof": ["TOF_LAM", "TOF_x_axis_calibration", "neutron_data"],
    "neutron": ["neutron_data"],
    "parametric": ["#list", "Run_Number"],
    "sequential": ["#list", "Run_Number"],
}


def parse_tcinps(bat_path):
    """Resolved, deduplicated absolute .inp paths from a tcinps-2.bat-
    style file -- same parsing convention used by this skill's own
    verification scripts: 'tc <path> ["extra text"]' lines, 'rem'-
    prefixed lines skipped, '\\w\\' normalized to the real drive root,
    '.inp' appended if the path doesn't already end in it."""
    paths = []
    seen = set()
    with open(bat_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s.lower().startswith("rem"):
                continue
            m = TC_RE.match(line)
            if not m:
                continue
            p = m.group(1)
            if p.startswith("\\w\\"):
                p = "c:\\w\\" + p[3:]
            if not p.lower().endswith(".inp"):
                p += ".inp"
            key = p.lower()
            if key not in seen:
                seen.add(key)
                paths.append(p)
    return paths


def query_words(query):
    words = [w for w in re.split(r"[^a-z0-9]+", query.lower()) if w]
    return [w for w in words if w not in FILLER_WORDS] or words


def path_match(paths, words):
    """Word-boundary match (not a bare substring check) -- a bare `in`
    check on a short query word like "tof" false-positived on
    'jsoe_fit_cc2c_tofullprofmono_01.inp' (a real corpus file), since
    "tof" is a genuine substring of "tofullprofmono" despite not being
    the same word at all. `\\b` treats `_`/digits as word characters
    (matching Python's own `\\w`), so `\\btof\\b` still correctly matches
    a real 'tof_bank2_1' token (bounded by `\\` and `_`) while rejecting
    the false positive."""
    word_res = [re.compile(r"\b" + re.escape(w) + r"\b") for w in words]
    scored = []
    for p in paths:
        pl = p.lower()
        score = sum(1 for wre in word_res if wre.search(pl))
        if score:
            scored.append((score, p))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [p for _, p in scored]


def content_match(paths, query, words):
    # Build the set of literal strings to search for: the raw query
    # phrase itself, plus any TOPIC_SYNONYMS entry whose key is
    # contained in (or contains) the query.
    needles = {query.lower()}
    for key, terms in TOPIC_SYNONYMS.items():
        if key in query.lower() or query.lower() in key:
            needles.update(t.lower() for t in terms)
    if not needles:
        return []

    scored = []
    for p in paths:
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                text = f.read().lower()
        except OSError:
            continue
        score = sum(text.count(n) for n in needles if n)
        if score:
            scored.append((score, p))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [p for _, p in scored]


def find_examples(query, bat_path=DEFAULT_BAT):
    """Returns (matches, stage) -- stage is 'path' or 'content' saying
    which matching pass produced the result, or 'none' if nothing
    matched either way."""
    paths = parse_tcinps(bat_path)
    words = query_words(query)

    matches = path_match(paths, words)
    if matches:
        return matches, "path"

    matches = content_match(paths, query, words)
    if matches:
        return matches, "content"

    return [], "none"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", help='topic to search for, e.g. "tof", "tof template", "charge flipping"')
    parser.add_argument("-n", "--max-results", type=int, default=8, help="max matches to show (default 8)")
    parser.add_argument("--bat", default=DEFAULT_BAT, help="path to the curated tc-list file (default: c:\\w\\tcinps-2.bat)")
    parser.add_argument("--open", action="store_true", help="also open the top match in VS Code")
    args = parser.parse_args()

    matches, stage = find_examples(args.query, args.bat)

    if not matches:
        print(f"No match for {args.query!r} in {args.bat} -- try a broader term, "
              f"or check references/examples-index.md for the full (non-curated) corpus.", file=sys.stderr)
        sys.exit(1)

    print(f"{len(matches)} match(es) for {args.query!r} (via {stage} match):", file=sys.stderr)
    shown = matches[:args.max_results]
    for p in shown:
        exists = "" if os.path.exists(p) else "  [FILE NOT FOUND]"
        print(f"  {p}{exists}", file=sys.stderr)
    if len(matches) > len(shown):
        print(f"  ... and {len(matches) - len(shown)} more (use -n to show more)", file=sys.stderr)

    for p in shown:
        print(p)

    if args.open:
        top = shown[0]
        if os.path.exists(top):
            code_path = shutil.which("code") or shutil.which("code.cmd")
            if code_path:
                subprocess.run([code_path, top], check=False)
            else:
                print("Note: 'code' CLI not found on PATH -- couldn't open the file.", file=sys.stderr)
        else:
            print(f"Note: top match {top!r} doesn't exist on disk, nothing to open.", file=sys.stderr)


if __name__ == "__main__":
    main()
