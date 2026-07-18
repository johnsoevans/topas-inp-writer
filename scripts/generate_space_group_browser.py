#!/usr/bin/env python3
"""Regenerate references/space_group_symbols.html from TOPAS's sgcom5.txt.

Parses every space-group entry out of TOPAS_DIR/sgcom5.txt (TOPAS's own
space-group generator table) and rewrites the DATA array embedded in the
space group browser page, leaving the page's HTML/CSS/JS untouched.

Usage:
    python generate_space_group_browser.py [--sgcom5 PATH] [--out PATH]

By default reads sgcom5.txt from $TOPAS_DIR and writes to
references/space_group_symbols.html relative to the repo root.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "references" / "space_group_symbols.html"

SYSTEM_NAMES = {
    "Triclinic": "Triclinic",
    "Monoclinic": "Monoclinic",
    "Orthorhombic": "Orthorhombic",
    "Tetragonal": "Tetragonal",
    "Trigonal": "Trigonal",
    "Hexagonal": "Hexagonal",
    "Cubic": "Cubic",
}


def parse_sgcom5(text: str) -> list[dict]:
    """Parse sgcom5.txt into one record per space-group number.

    Each record is {"number": int, "system": str, "symbols": [str, ...]},
    with symbols de-duplicated (case-insensitively) and ordered as they
    first appear in the file.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)  # strip header comment block

    current_system = None
    entries = []
    buffer = ""
    for line in text.split("\n"):
        stripped = line.strip()
        m = re.match(r"^'\s*([A-Za-z]+)\s*$", stripped)
        if m and m.group(1) in SYSTEM_NAMES:
            current_system = SYSTEM_NAMES[m.group(1)]
            continue
        if re.match(r"^'\s*-+\s*$", stripped):
            continue
        if stripped == "":
            continue
        buffer += " " + line
        if buffer.count("{") > 0 and buffer.count("{") == buffer.count("}"):
            entry_text = buffer.strip()
            buffer = ""
            m2 = re.match(r"^(\d+)\s+(\S+)\s*\{(.*)\}\s*$", entry_text, re.S)
            if not m2:
                continue
            entries.append({
                "number": int(m2.group(1)),
                "system": current_system,
                "body": m2.group(3),
            })

    def extract_symbols(body: str) -> list[str]:
        raw = body.replace("=", " = ").replace("\t", " ")
        tokens = raw.split()
        symbols = []
        for tok in tokens:
            if tok in ("=", "-"):
                continue
            # bare space-group numbers ("58", "58:2") and their rhombohedral-setting
            # shorthand ("146r") are numeric aliases, not real HM symbols
            if re.match(r"^\d+(:\d+)?r?$", tok):
                continue
            symbols.append(tok)
        seen = set()
        out = []
        for s in symbols:
            key = s.lower()
            if key not in seen:
                seen.add(key)
                out.append(s)
        return out

    by_number: dict[int, dict] = {}
    for e in entries:
        rec = by_number.setdefault(e["number"], {
            "number": e["number"],
            "system": e["system"],
            "symbols": [],
        })
        existing_lower = {s.lower() for s in rec["symbols"]}
        for s in extract_symbols(e["body"]):
            if s.lower() not in existing_lower:
                existing_lower.add(s.lower())
                rec["symbols"].append(s)

    return sorted(by_number.values(), key=lambda r: r["number"])


def find_sgcom5(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    topas_dir = os.environ.get("TOPAS_DIR")
    if not topas_dir:
        sys.exit("TOPAS_DIR is not set and --sgcom5 was not given; cannot locate sgcom5.txt")
    return Path(topas_dir) / "sgcom5.txt"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sgcom5", help="Path to sgcom5.txt (default: $TOPAS_DIR/sgcom5.txt)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output HTML path")
    args = ap.parse_args()

    sgcom5_path = find_sgcom5(args.sgcom5)
    if not sgcom5_path.is_file():
        sys.exit(f"sgcom5.txt not found at {sgcom5_path}")

    records = parse_sgcom5(sgcom5_path.read_text(encoding="utf-8"))
    if len(records) != 230:
        print(f"warning: parsed {len(records)} space groups, expected 230", file=sys.stderr)

    data_json = json.dumps(records, separators=(",", ":"))

    out_path = Path(args.out)
    html = out_path.read_text(encoding="utf-8")
    new_html, n = re.subn(
        r"const DATA = \[.*?\];",
        "const DATA = " + data_json.replace("\\", "\\\\") + ";",
        html,
        count=1,
        flags=re.S,
    )
    if n != 1:
        sys.exit(f"could not find 'const DATA = [...];' in {out_path}")

    out_path.write_text(new_html, encoding="utf-8", newline="\n")
    total_symbols = sum(len(r["symbols"]) for r in records)
    print(f"Wrote {len(records)} space groups ({total_symbols} symbol variants) to {out_path}")


if __name__ == "__main__":
    main()
