#!/usr/bin/env python3
"""
find_example.py -- find real, working .inp examples matching a topic
query (e.g. "tof", "pawley", "charge flipping", "stacking faults").

Corpus: every .inp under the live TOPAS install (TOPAS_DIR, resolved via
topas_install.py) plus this skill's own example_inp_files/. Matches are
ranked in three tiers:

  0. example_inp_files/
  1. install examples listed in references/examples-index.md
  2. everything else under TOPAS_DIR

Tier breaks ties on match score; it does not override it. Scratch files
(0-byte, temp.inp/temp8.inp, "... - Copy.inp") are dropped.

--bat replaces the TOPAS_DIR walk with a tcinps-2.bat tc-list, if one is
available. Not bundled with this skill; no default path.

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

# subprocess/shutil are imported inside the --open branch: together they
# cost ~21 ms of the ~113 ms run, and only that branch uses them.

import topas_install

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
BUNDLED_EXAMPLES_DIR = os.path.join(SKILL_DIR, "example_inp_files")
EXAMPLES_INDEX = os.path.join(SKILL_DIR, "references", "examples-index.md")

TIER_BUNDLED, TIER_INDEXED, TIER_OTHER = 0, 1, 2

# Path matches at or above this count skip the content pass, which has
# to read every file in the corpus.
PATH_MATCH_ENOUGH = 5

# Scratch files under a real install, dropped from the corpus.
JUNK_RE = re.compile(r"(?:^|[\\/])(?:temp\d*\.inp|.+ - copy\.inp)$", re.IGNORECASE)

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


def load_index_basenames():
    """Lowercased basenames of the .inp files listed in
    references/examples-index.md. Empty set if it isn't readable."""
    try:
        with open(EXAMPLES_INDEX, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return set()
    return {os.path.basename(p.replace("\\", "/")).lower()
            for p in re.findall(r"`([^`\n]+\.inp)`", text)}


def is_junk(path, size):
    """size < 0 means unknown (a path from --bat that isn't on disk);
    such a path is kept so main() can flag it as [FILE NOT FOUND]."""
    return size == 0 or bool(JUNK_RE.search(path))


def walk_inp_files(root):
    """Yields (path, size) for every .inp under root. scandir rather
    than os.walk + getsize: the size comes from the directory entry, so
    no second stat call per file."""
    stack = [root]
    while stack:
        try:
            entries = list(os.scandir(stack.pop()))
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                elif entry.name.lower().endswith(".inp"):
                    yield entry.path, entry.stat().st_size
            except OSError:
                continue


def build_corpus(bat_path=None):
    """[(path, tier)] for the whole searchable corpus, plus a list of
    human-readable source descriptions for the not-found message."""
    corpus = []
    sources = []
    seen = set()

    def add(path, size, tier):
        key = os.path.normcase(os.path.abspath(path))
        if key in seen or is_junk(path, size):
            return
        seen.add(key)
        corpus.append((path, tier))

    def install_tier(path, index_names):
        return TIER_INDEXED if os.path.basename(path).lower() in index_names else TIER_OTHER

    if os.path.isdir(BUNDLED_EXAMPLES_DIR):
        before = len(corpus)
        for p, size in walk_inp_files(BUNDLED_EXAMPLES_DIR):
            add(p, size, TIER_BUNDLED)
        sources.append(f"{len(corpus) - before} in example_inp_files/")

    if bat_path:
        before = len(corpus)
        index_names = load_index_basenames()
        for p in parse_tcinps(bat_path):
            try:
                size = os.path.getsize(p)
            except OSError:
                size = -1
            add(p, size, install_tier(p, index_names))
        sources.append(f"{len(corpus) - before} from {bat_path}")
        return corpus, sources

    topas_dir, found = topas_install.get_topas_dir()
    if found:
        before = len(corpus)
        index_names = load_index_basenames()
        for p, size in walk_inp_files(topas_dir):
            add(p, size, install_tier(p, index_names))
        sources.append(f"{len(corpus) - before} under TOPAS_DIR ({topas_dir})")

    return corpus, sources


def query_words(query):
    words = [w for w in re.split(r"[^a-z0-9]+", query.lower()) if w]
    return [w for w in words if w not in FILLER_WORDS] or words


def path_tokens(path):
    """Path split on every non-alphanumeric character, so 'tof' is a
    token of both 'tof\\tof_bank2_1.inp' and 'HRPD_tof_rietveld.inp' but
    not of 'jsoe_fit_cc2c_tofullprofmono_01.inp'. A `\\b` regex can't do
    this: `_` is a word character, so `\\btof\\b` misses 'HRPD_tof_'."""
    return {t for t in re.split(r"[^a-z0-9]+", path.lower()) if t}


def path_match(corpus, words, wants_template):
    """Whole-token match against each path. A query naming a template
    scores +1 for any path with a "template" token. Ties break by tier,
    then path."""
    scored = []
    for p, tier in corpus:
        tokens = path_tokens(p)
        score = sum(1 for w in words if w in tokens)
        if score:
            if wants_template and "template" in tokens:
                score += 1
            scored.append((-score, tier, p))
    scored.sort()
    return [p for _, _, p in scored]


def content_match(corpus, query, words):
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
    for p, tier in corpus:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                text = f.read().lower()
        except OSError:
            continue
        score = sum(text.count(n) for n in needles if n)
        if score:
            scored.append((-score, tier, p))
    scored.sort()
    return [p for _, _, p in scored]


def find_examples(query, bat_path=None):
    """Returns (matches, stage, sources). stage is 'path' or 'content'
    for which pass produced the result, 'none' if nothing matched, or
    'no-corpus' if there was nothing to search."""
    corpus, sources = build_corpus(bat_path)
    if not corpus:
        return [], "no-corpus", sources

    words = query_words(query)
    wants_template = bool(re.search(r"\btemplates?\b", query.lower()))

    matches = path_match(corpus, words, wants_template)
    if len(matches) >= PATH_MATCH_ENOUGH:
        return matches, "path", sources

    # Thin path result -- supplement with a content pass, which reads
    # every file. Path matches keep their rank above content ones.
    seen = set(matches)
    extra = [p for p in content_match(corpus, query, words) if p not in seen]
    if matches:
        return matches + extra, ("path+content" if extra else "path"), sources
    if extra:
        return extra, "content", sources

    return [], "none", sources


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", help='topic to search for, e.g. "tof", "tof template", "charge flipping"')
    parser.add_argument("-n", "--max-results", type=int, default=8, help="max matches to show (default 8)")
    parser.add_argument("--bat", default=None, help="tcinps-2.bat tc-list to search instead of walking TOPAS_DIR")
    parser.add_argument("--open", action="store_true", help="also open the top match in VS Code")
    args = parser.parse_args()

    if args.bat and not os.path.isfile(args.bat):
        print(f"--bat file not found: {args.bat}", file=sys.stderr)
        sys.exit(1)

    matches, stage, sources = find_examples(args.query, args.bat)
    searched = ", ".join(sources) if sources else "nothing"

    if stage == "no-corpus":
        print("No examples to search: TOPAS_DIR is not set to a real directory and "
              "example_inp_files/ holds no .inp files. Set TOPAS_DIR to your TOPAS "
              "install root, or pass --bat <tcinps-2.bat>.", file=sys.stderr)
        sys.exit(1)

    if not matches:
        print(f"No match for {args.query!r} in {searched} -- try a broader term.", file=sys.stderr)
        sys.exit(1)

    print(f"{len(matches)} match(es) for {args.query!r} (via {stage} match; searched {searched}):", file=sys.stderr)
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
            import shutil
            import subprocess

            # Popen + DEVNULL, as in format_inp_hierarchy.py: VS Code gets the
            # file immediately, while the launcher takes ~1.3 s to exit and
            # would hold our stdout/stderr open for a caller capturing them.
            code_path = shutil.which("code") or shutil.which("code.cmd")
            if code_path:
                subprocess.Popen([code_path, top],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                print("Note: 'code' CLI not found on PATH -- couldn't open the file.", file=sys.stderr)
        else:
            print(f"Note: top match {top!r} doesn't exist on disk, nothing to open.", file=sys.stderr)


if __name__ == "__main__":
    main()
