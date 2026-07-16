#!/usr/bin/env python3
"""
remove_errors.py -- Strip every trailing refined-value error suffix
(`` `_<error> ``, e.g. `48.0611197`_1.21585437` -> `48.0611197`) from a
TOPAS .inp file, so a file with fitted results reads like a fresh,
unrefined starting INP.

Each occurrence has a different numeric error, so there's no common
literal substring to search-and-replace on -- this is a single regex
pass instead (the same pattern documented in this skill's SKILL.md under
"Stripping refined-value errors"):

    `_-?\\d+\\.?\\d*(?:[eE][-+]?\\d+)?

This does not validate or change TOPAS semantics beyond removing these
suffixes -- run scripts/check_inp_syntax.py afterward as usual.

Usage:
    python3 remove_errors.py file.inp                 # rewrite in place, whole file
    python3 remove_errors.py file.inp -o out.inp       # write elsewhere
    python3 remove_errors.py file.inp --check          # print the result to stdout, don't write
"""

import argparse
import re
import sys

ERROR_SUFFIX_RE = re.compile(r"`_-?\d+\.?\d*(?:[eE][-+]?\d+)?")


def remove_errors(text):
    return ERROR_SUFFIX_RE.subn("", text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inp_file")
    parser.add_argument("-o", "--output", help="write to this file instead of overwriting the input")
    parser.add_argument("--check", action="store_true", help="print the result to stdout instead of writing any file")
    args = parser.parse_args()

    with open(args.inp_file, encoding="utf-8") as f:
        text = f.read()

    stripped, count = remove_errors(text)

    if args.check:
        print(stripped)
        print(f"{count} error suffix(es) would be removed", file=sys.stderr)
        return

    out_path = args.output or args.inp_file
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(stripped)
    print(f"Written to {out_path} ({count} error suffix(es) removed)", file=sys.stderr)


if __name__ == "__main__":
    main()
