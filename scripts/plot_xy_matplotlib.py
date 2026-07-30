#!/usr/bin/env python3
"""
plot_xy_matplotlib.py -- render the same XY(E) diffraction data plot_xy.py
plots interactively, as a static PNG/JPG image (matplotlib) instead of an
HTML canvas page. Use this specifically when a plot needs to be embedded in
a document that can't run JS/HTML -- e.g. a report .docx via
build_report_docx.py's `images` parameter. For anything viewed in a browser
(an artifact, a quick look at a fit), prefer plot_xy.py -- it has pan/zoom/
hover/toggle-visibility that this script deliberately does not reimplement.

Reuses plot_xy.py's own file-parsing and color-scheme logic (parse_xy_file,
--phases color scheme, --diff interpolation) so a fix to how a .xy/.xye file
is parsed only has to happen in one place.

Difference curves and reflection ticks are placed on the SAME axis as the
main pattern (not a separate subplot), each stacked as a fixed data-space
offset -- OFFSET_FRACTION (5%) of the main series' own Y-range -- below the
band above it: diff curves sit 5% below the lowest main-series value, and
each tick-mark row sits a further 5% below the lowest diff value. This is a
static approximation of plot_xy.py's own live, screen-space diff offset
(which recomputes on every pan/zoom/toggle -- not meaningful for a fixed
PNG), confirmed against the user's own stacking convention.

Usage: same flags as plot_xy.py's overlay/diff/phases/ticks/stats options,
output is PNG (or .jpg by extension) instead of HTML.

    python3 plot_xy_matplotlib.py obs.xy calc.xy --labels "Yobs,Ycalc" --diff "Yobs,Ycalc" -o fit.png
    python3 plot_xy_matplotlib.py --phases "CeO2|obs.xy|calc.xy" --stats "Rwp=7.36%,GoF=2.40" -o fit.png
    python3 plot_xy_matplotlib.py obs.xy calc.xy --diff "Yobs,Ycalc" --ticks "CeO2|ticks.txt" -o fit.png --dpi 200
"""

import sys
import os
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from plot_xy import (
    parse_xy_file, parse_tick_reflection_file, compute_diff_series,
    build_phase_series, build_tick_groups, parse_stats,
    DEFAULT_PALETTE, DEFAULT_DIFF_COLOR,
)


OFFSET_FRACTION = 0.05  # each band (diff, then ticks) sits this fraction of the
                         # main-series Y-range below the band above it


def render(series, title, out_path, ticks=None, stats=None, dpi=150):
    fig, ax = plt.subplots(figsize=(10, 5.6))

    main_series = [s for s in series if s.get("kind") != "diff"]
    diff_series = [s for s in series if s.get("kind") == "diff"]

    main_ys = [y for s in main_series for y in s["y"]]
    main_min, main_max = (min(main_ys), max(main_ys)) if main_ys else (0.0, 1.0)
    span = (main_max - main_min) or 1.0

    for s in main_series:
        ax.plot(s["x"], s["y"], "-", color=s["color"], label=s["name"], linewidth=1.1)

    # Diff curves share one offset (mirrors plot_xy.py's live screen-space
    # placement, but as a fixed data-space fraction since this is a static
    # render): shifted down so the highest point among all diff curves sits
    # OFFSET_FRACTION of the main Y-range below the lowest main-series value.
    diff_min = main_min
    if diff_series:
        diff_max_raw = max(y for s in diff_series for y in s["y"])
        diff_offset = (main_min - OFFSET_FRACTION * span) - diff_max_raw
        for s in diff_series:
            shifted = [y + diff_offset for y in s["y"]]
            ax.plot(s["x"], shifted, "--", color=s["color"], label=s["name"], linewidth=1.1)
        diff_min = min(y + diff_offset for s in diff_series for y in s["y"])

    ax.set_ylabel("Intensity")
    ax.legend(fontsize=8, loc="upper right", frameon=False)
    subtitle = ""
    if stats:
        subtitle = "  (" + ", ".join(f"{k}={v}" for k, v in stats) + ")"
    ax.set_title(title + subtitle, fontsize=11)
    ax.set_xlabel("2θ (°)")

    # Tick marks: one row per group, stacked further below the diff band by
    # the same OFFSET_FRACTION-of-main-span rule, each row occupying a small
    # fixed slice of that same fraction so multiple groups don't collide.
    if ticks:
        row_h = (OFFSET_FRACTION * span) / max(len(ticks), 1)
        row_top = diff_min - OFFSET_FRACTION * span
        for grp in ticks:
            row_bottom = row_top - row_h * 0.8
            ax.vlines(grp["x"], row_bottom, row_top, color=grp["color"], linewidth=1.2)
            ax.text(1.0, (row_top + row_bottom) / 2, grp["name"], fontsize=7,
                    color=grp["color"], ha="left", va="center",
                    transform=ax.get_yaxis_transform(), clip_on=False)
            row_top -= row_h

    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xy_files", nargs="*", help="one or more XY(E) data files to overlay (not used with --phases)")
    parser.add_argument("-o", "--output", help="output image path, extension sets format (default: <first file>_xy_plot.png)")
    parser.add_argument("--title", help="plot title (default: the file name(s))")
    parser.add_argument("--labels", help="comma-separated series labels, parallel to xy_files")
    parser.add_argument("--colors", help="comma-separated series colors, parallel to xy_files")
    parser.add_argument("--diff", action="append", help="add a LABEL_A,LABEL_B difference series (A - B); repeatable")
    parser.add_argument("--diff-labels", help="comma-separated labels, parallel to --diff")
    parser.add_argument("--diff-colors", help="comma-separated colors, parallel to --diff")
    parser.add_argument("--phases", help="'NAME1|obs1.xy|calc1.xy,...' -- see plot_xy.py's own --phases docs")
    parser.add_argument("--ticks", help="'NAME1|positions1.xy[|color1],...' -- see plot_xy.py's own --ticks docs")
    parser.add_argument("--stats", help="'Label1=value1,Label2=value2,...' shown in the title")
    parser.add_argument("--dpi", type=int, default=150, help="output resolution (default 150)")
    args = parser.parse_args()

    ticks = build_tick_groups(args.ticks) if args.ticks else None
    stats = parse_stats(args.stats) if args.stats else None

    if args.phases:
        if args.xy_files or args.labels or args.colors or args.diff:
            print("--phases cannot be combined with xy_files/--labels/--colors/--diff", file=sys.stderr)
            sys.exit(1)
        series = build_phase_series(args.phases)
        title = args.title or "all phases"
        out_path = args.output or "combined_xy_plot.png"
        render(series, title, out_path, ticks=ticks, stats=stats, dpi=args.dpi)
        print(f"Written to {out_path}", file=sys.stderr)
        return

    if not args.xy_files:
        print("Provide at least one XY file, or use --phases", file=sys.stderr)
        sys.exit(1)

    labels = [s.strip() for s in args.labels.split(",")] if args.labels else None
    colors = [s.strip() for s in args.colors.split(",")] if args.colors else None

    series = []
    for i, path in enumerate(args.xy_files):
        xs, ys = parse_xy_file(path)
        if not xs:
            print(f"No numeric (x, y) data found in {path}", file=sys.stderr)
            sys.exit(1)
        name = labels[i] if labels and i < len(labels) else os.path.splitext(os.path.basename(path))[0]
        color = colors[i] if colors and i < len(colors) else DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)]
        series.append({"name": name, "color": color, "x": xs, "y": ys})

    if args.diff:
        diff_labels = [s.strip() for s in args.diff_labels.split(",")] if args.diff_labels else None
        diff_colors = [s.strip() for s in args.diff_colors.split(",")] if args.diff_colors else None
        series_by_name = {s["name"]: s for s in series}
        for i, spec in enumerate(args.diff):
            parts = [s.strip() for s in spec.split(",")]
            if len(parts) != 2:
                print("--diff expects exactly two comma-separated labels, e.g. --diff Yobs,Ycalc", file=sys.stderr)
                sys.exit(1)
            name_a, name_b = parts
            if name_a not in series_by_name or name_b not in series_by_name:
                print(f"--diff labels must match --labels (have: {list(series_by_name)})", file=sys.stderr)
                sys.exit(1)
            diff_label = diff_labels[i] if diff_labels and i < len(diff_labels) else f"{name_a} - {name_b}"
            diff_color = diff_colors[i] if diff_colors and i < len(diff_colors) else DEFAULT_DIFF_COLOR
            series.append(compute_diff_series(series_by_name, name_a, name_b, diff_label, diff_color))

    title = args.title or " / ".join(os.path.basename(p) for p in args.xy_files)
    out_path = args.output
    if not out_path:
        base, _ = os.path.splitext(args.xy_files[0])
        out_path = base + "_xy_plot.png"

    render(series, title, out_path, ticks=ticks, stats=stats, dpi=args.dpi)
    print(f"Written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
