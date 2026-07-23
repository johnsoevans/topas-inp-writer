#!/usr/bin/env python3
"""
plot_xy.py -- Plot one or more two- (or three-) column XY(E) diffraction
data files (.xy, .xye, .dat, or any whitespace/comma-delimited x/y text
file) as a self-contained, interactive HTML page: drag to pan, scroll to
zoom (both centered on the cursor), a Sqrt(Y) / Linear Y-axis toggle, a
per-series visibility checkbox in the legend (click to hide/show any one
line), and a hover crosshair (a vertical guide line plus one colored
marker dot per currently-visible series at that X -- no floating text
box attached to the cursor).

No third-party dependencies -- rendering is a small hand-written vanilla-JS
canvas line plot (no CDN, no charting library), so the output works
offline or inside a strict-CSP viewer.

Usage:
    python3 plot_xy.py file.xy                        # -> file_xy_plot.html
    python3 plot_xy.py file.xy -o out.html
    python3 plot_xy.py file.xy --title "My pattern"

    # multiple series overlaid (e.g. observed vs. calculated):
    python3 plot_xy.py obs.xy calc.xy --labels "Yobs,Ycalc" --colors "blue,red" -o out.html

    # add a difference curve (first label minus second label):
    python3 plot_xy.py obs.xy calc.xy --labels "Yobs,Ycalc" --colors "blue,red" --diff "Yobs,Ycalc" -o out.html

    # combine multiple xdd/phases (each with their own Yobs/Ycalc/diff) in one plot:
    python3 plot_xy.py ceo2_obs.xy ceo2_calc.xy y2o3_obs.xy y2o3_calc.xy \\
        --labels "CeO2 Yobs,CeO2 Ycalc,Y2O3 Yobs,Y2O3 Ycalc" \\
        --diff "CeO2 Yobs,CeO2 Ycalc" --diff "Y2O3 Yobs,Y2O3 Ycalc" -o out.html

    # same, with the standard Yobs/Ycalc/diff color scheme auto-assigned per phase:
    python3 plot_xy.py --phases "CeO2|ceo2_obs.xy|ceo2_calc.xy,Y2O3|y2o3_obs.xy|y2o3_calc.xy" -o out.html

`--labels`/`--colors` are comma-separated, parallel to the file arguments.
Labels default to each file's base name; colors default to a small
categorical palette if not given. A legend (with a visibility checkbox per
series) is shown whenever more than one file is plotted.

`--phases "NAME1|obs1.xy|calc1.xy,NAME2|obs2.xy|calc2.xy,..."` (pipe-
separated, not colon -- a colon collides with a Windows drive letter in
an absolute path) is a convenience for the multi-xdd/"fit show in one
plot" case: for each named phase it adds a "NAME Yobs"/"NAME Ycalc"
series pair plus a "NAME Yobs - NAME Ycalc" diff series, with colors
auto-assigned to the
user's own standing scheme (confirmed directly, not guessed): every
phase's Ycalc is the identical fixed color RGB(255, 64, 0); each phase's
Yobs gets its own distinct hue at the same brightness/saturation as the
first phase's exact RGB(0, 128, 255) (hues spread by the golden angle,
137.508 degrees, so adding another phase never reshuffles earlier ones'
colors); each phase's diff curve reuses that same phase's Yobs hue at 0.7x
intensity ("multiply the RGB colours by 0.7", per the user's own words) --
see `yobs_phase_color`/`YCALC_COLOR`/`diff_color_from_yobs` below. Cannot
be combined with plain positional `xy_files`/`--labels`/`--colors` in the
same invocation (it builds the whole series list itself).

`--diff LABEL_A,LABEL_B` adds a computed `LABEL_A - LABEL_B` difference
series (e.g. Yobs - Ycalc, the standard Rietveld residual), referencing
two of the already-given series by their label. If both series share an
identical X grid (the common case -- TOPAS writes Out_X_Yobs/Out_X_Ycalc
on the same binning) the subtraction is direct; otherwise the second
series is linearly interpolated onto the first's X grid. `--diff` is
repeatable (once per xdd/phase when combining several into one plot).
`--diff-labels`/`--diff-colors` (comma-separated, parallel to the `--diff`
flags) override the default naming/color.

All difference curves share ONE offset (confirmed directly by the user,
replacing an earlier per-diff-stacked design): computed live in JS on
every draw (pan/zoom/resize/visibility-toggle all recompute it, since it's
inherently a screen-space quantity, not a fixed data-space number) so
that the HIGHEST point among all currently-visible difference curves sits
a constant ~5 CSS pixels below the LOWEST point among all currently-
visible non-diff ("main") series -- "the maximum of all the difference
plots is around 5 pixels below the minimum of all the Yobs," in the
user's own words (approximated here as the main-series minimum in
general, since a generic `--diff` call has no reliable way to know which
specific series is semantically "Yobs" -- only `--phases` names that
explicitly, and in practice Yobs/Ycalc track closely enough that this is
the same number either way). Because this is screen-space, all diff
curves visually sit in the same band and never drift apart on zoom the
way a data-space-fixed offset would.

Parsing: each non-blank, non-comment line ('#' or "'" leading, matching
TOPAS's own comment convention) is split on whitespace/commas; the first
two numeric tokens are taken as (x, y) -- a third numeric token (e.g. an
esd column in a .xye file) is read but not currently plotted. Lines that
don't parse as at least two numbers are skipped rather than raising, so a
stray header/footer line (or a '/* ... */' comment-delimiter pair) doesn't
abort the whole file.

`--stats "Label1=value1,Label2=value2,..."` adds refinement statistics
(e.g. Rwp, GoF, Rp) to the header meta line as plain text, e.g.
`--stats "Rwp=13.68%,GoF=1.64"`. Rendered in the same muted text-ink as the
existing point-count/X-range meta text -- a headline number is not a series
identity, so it deliberately gets no color/swatch of its own.

`--ticks "NAME1|positions1.xy[|color1],NAME2|positions2.xy[|color2],..."`
(pipe-separated fields, comma-separated groups -- same convention as
`--phases`) adds a row of Bragg-reflection tick marks, one row per named
group (e.g. one per phase), drawn INSIDE the plot frame just above the
X-axis line (each row is a fixed pixel height, so it eats a small,
constant slice of the curve area rather than growing the canvas -- this
is deliberately independent of the Y-axis data/autoscale/Sqrt(Y) toggle,
so hiding/showing curves never moves the tick rows). Each tick row gets
its own legend checkbox to toggle visibility, separate from the main
series legend. Hovering a tick shows a small floating tooltip labeled
with its h k l indices (if the source file provides them) or its
position otherwise.

Two source file formats are recognized per-line by column count, so a
single `--ticks` file works whichever TOPAS reporting macro produced it
(both documented in references/06-macros-and-include-files.md, added
inside a `str` block):
  - `Create_hklm_d_Th2_Ip_file(file)` -- 7 columns, "h k l m d 2Th I".
    Preferred: the tooltip shows the real h k l indices, and the tick
    position is the 2Th column (index 5, 0-based).
  - `Create_2Th_Ip_file(file)` -- 2 columns, "2Th I". Position-only; the
    tooltip falls back to showing the group name and position, no hkl.
"""

import sys
import os
import re
import json
import bisect
import argparse

NUM_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")

DEFAULT_PALETTE = ["#b5502f", "#3b6ea5", "#5c8a3a", "#8a5ba6", "#c98a2b"]
DEFAULT_DIFF_COLOR = "#6b6459"
DEFAULT_TICK_COLOR = "#6b6459"

# "--phases" color scheme, confirmed directly by the user: every phase's
# Ycalc is this identical fixed color; each phase's Yobs cycles through a
# fixed, hand-picked 8-color palette (not a computed hue rotation -- an
# earlier golden-angle-rotation version produced Yobs colors the user
# reported as "all the same colour," so this was replaced with a small
# explicit palette instead); each phase's diff reuses its own Yobs color
# at 0.7x intensity ("multiply the RGB colours by 0.7").
YCALC_COLOR = (255, 64, 0)
DIFF_INTENSITY = 0.7

# 8 hand-picked, visually distinct colors, first exactly the user's own
# RGB(0, 128, 255); cycles via modulo if more than 8 phases are plotted.
# Deliberately none red or near-red (confirmed directly by the user --
# Ycalc is always the fixed red-orange RGB(255, 64, 0), so a reddish Yobs
# would be hard to tell apart from it by color alone).
YOBS_PALETTE = [
    (0, 128, 255),  # blue
    (64, 200, 64),  # green
    (0, 190, 190),  # teal
    (180, 60, 220),  # purple
    (230, 190, 0),  # gold
    (230, 80, 180),  # pink/magenta
    (100, 100, 255),  # indigo
    (140, 220, 0),  # lime
]


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, c)) for c in rgb))


def yobs_phase_color(i):
    """The i-th phase's Yobs color (0-indexed), cycling through YOBS_PALETTE."""
    return YOBS_PALETTE[i % len(YOBS_PALETTE)]


def diff_color_from_yobs(yobs_rgb):
    return tuple(round(c * DIFF_INTENSITY) for c in yobs_rgb)


def parse_xy_file(path):
    xs = []
    ys = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped[0] in "'#":
                continue
            tokens = NUM_RE.findall(stripped)
            if len(tokens) < 2:
                continue
            try:
                x, y = float(tokens[0]), float(tokens[1])
            except ValueError:
                continue
            xs.append(x)
            ys.append(y)
    return xs, ys


def interp(xq, xs, ys):
    """Linear-interpolate ys(xs) at each point in xq. xs must be sorted
    ascending. Points outside [xs[0], xs[-1]] hold at the nearest edge
    value (no extrapolation) -- adequate for the two-diffraction-pattern
    overlap case this exists for, not a general-purpose interpolator."""
    out = []
    n = len(xs)
    for x in xq:
        i = bisect.bisect_left(xs, x)
        if i <= 0:
            out.append(ys[0])
        elif i >= n:
            out.append(ys[-1])
        else:
            x0, x1 = xs[i - 1], xs[i]
            y0, y1 = ys[i - 1], ys[i]
            t = (x - x0) / (x1 - x0) if x1 != x0 else 0.0
            out.append(y0 + t * (y1 - y0))
    return out


def compute_diff_series(series_by_name, name_a, name_b, label, color):
    """Compute a raw (un-offset) `name_a - name_b` difference series,
    tagged 'kind': 'diff'. Vertical placement is NOT decided here -- all
    diff curves share one live, screen-space offset computed in JS on
    every draw (see PAGE_TEMPLATE's computeDiffOffset), not a fixed
    data-space number baked in at generation time."""
    a = series_by_name[name_a]
    b = series_by_name[name_b]
    xs = a["x"]
    if len(xs) == len(b["x"]) and all(abs(p - q) < 1e-9 for p, q in zip(xs, b["x"])):
        yb = b["y"]
    else:
        yb = interp(xs, b["x"], b["y"])
    diff = [ya - yb_ for ya, yb_ in zip(a["y"], yb)]

    return {"name": label, "color": color, "x": xs, "y": diff, "kind": "diff"}


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
    --grid: #ddd8cf;
    --axis: #9a9284;
    --accent: #b5502f;
    --border: #e2ddd2;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #1b1a18;
      --panel: #242220;
      --ink: #ece7de;
      --ink-muted: #a39a8c;
      --grid: #3a362f;
      --axis: #6e6656;
      --accent: #e8875f;
      --border: #38342c;
    }}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--ink);
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; padding: 20px 24px 32px; }}
  h1 {{ font-size: 1.05rem; font-weight: 600; margin: 0 0 2px; letter-spacing: 0.01em; }}
  .meta {{ color: var(--ink-muted); font-size: 0.82rem; margin-bottom: 14px; }}
  .panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 14px 16px 18px; }}
  .controls {{ display: flex; align-items: center; gap: 18px; margin-bottom: 10px;
    font-size: 0.85rem; flex-wrap: wrap; }}
  .controls label {{ display: flex; align-items: center; gap: 6px; cursor: pointer;
    user-select: none; }}
  button {{ font: inherit; font-size: 0.82rem; background: var(--bg); color: var(--ink);
    border: 1px solid var(--border); border-radius: 6px; padding: 5px 11px; cursor: pointer; }}
  button:hover {{ border-color: var(--accent); color: var(--accent); }}
  .hint {{ color: var(--ink-muted); font-size: 0.78rem; margin-left: auto; }}
  .legend {{ display: flex; gap: 16px; font-size: 0.82rem; flex-wrap: wrap; }}
  .legend .item {{ display: flex; align-items: center; gap: 5px; cursor: pointer; user-select: none; }}
  .legend .item input {{ margin: 0; cursor: pointer; }}
  .legend .item.off {{ opacity: 0.4; }}
  .legend .swatch {{ width: 12px; height: 3px; border-radius: 2px; }}
  .legend .swatch.tick {{ width: 2px; height: 12px; border-radius: 0; }}
  #tickControls {{ margin-top: -4px; }}
  canvas {{ display: block; width: 100%; touch-action: none; cursor: grab; }}
  canvas.dragging {{ cursor: grabbing; }}
  .canvas-holder {{ position: relative; }}
  .tick-tooltip {{ position: absolute; pointer-events: none; background: var(--panel);
    border: 1px solid var(--border); border-radius: 4px; padding: 2px 6px; font-size: 11px;
    color: var(--ink); white-space: nowrap; transform: translate(-50%, calc(-100% - 6px));
    box-shadow: 0 2px 6px rgba(0,0,0,0.18); z-index: 5; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{title_escaped}</h1>
  <div class="meta">{npoints} points &middot; X range {xmin_disp} to {xmax_disp}{stats_html}</div>
  <div class="panel">
    <div class="controls">
      <label><input type="checkbox" id="sqrtToggle"> Sqrt(Y) scale</label>
      <button id="resetBtn">Reset view</button>
      <div class="legend" id="legend"></div>
      <span class="hint">drag to pan &middot; scroll to zoom &middot; hover for crosshair</span>
    </div>
    <div class="controls" id="tickControls" style="display:none;">
      <span class="hint" style="margin-left:0;">Reflections:</span>
      <div class="legend" id="tickLegend"></div>
    </div>
    <div class="canvas-holder">
      <canvas id="plot" width="1140" height="560"></canvas>
      <div class="tick-tooltip" id="tickTooltip" style="display:none;"></div>
    </div>
  </div>
</div>
<script>
const SERIES = {series_json};
const TICKS = {ticks_json};

const canvas = document.getElementById('plot');
const ctx = canvas.getContext('2d');
const sqrtToggle = document.getElementById('sqrtToggle');
const resetBtn = document.getElementById('resetBtn');
const legendEl = document.getElementById('legend');
const tickControls = document.getElementById('tickControls');
const tickLegendEl = document.getElementById('tickLegend');
const tickTooltipEl = document.getElementById('tickTooltip');

SERIES.forEach(s => {{ if (s.visible === undefined) s.visible = true; }});
TICKS.forEach(g => {{ if (g.visible === undefined) g.visible = true; }});

if (SERIES.length > 1) {{
  legendEl.innerHTML = SERIES.map((s, i) =>
    '<label class="item" data-idx="' + i + '"><input type="checkbox" class="seriesToggle" checked>' +
    '<span class="swatch" style="background:' + s.color + '"></span>' + s.name + '</label>'
  ).join('');
  legendEl.querySelectorAll('.item').forEach((el) => {{
    const idx = +el.getAttribute('data-idx');
    const cb = el.querySelector('.seriesToggle');
    cb.addEventListener('change', () => {{
      SERIES[idx].visible = cb.checked;
      el.classList.toggle('off', !cb.checked);
      draw();
    }});
  }});
}}

if (TICKS.length) {{
  tickControls.style.display = 'flex';
  tickLegendEl.innerHTML = TICKS.map((g, i) =>
    '<label class="item" data-idx="' + i + '"><input type="checkbox" class="tickToggle" checked>' +
    '<span class="swatch tick" style="background:' + g.color + '"></span>' + g.name + '</label>'
  ).join('');
  tickLegendEl.querySelectorAll('.item').forEach((el) => {{
    const idx = +el.getAttribute('data-idx');
    const cb = el.querySelector('.tickToggle');
    cb.addEventListener('change', () => {{
      TICKS[idx].visible = cb.checked;
      el.classList.toggle('off', !cb.checked);
      hoverTick = null;
      updateTickTooltip();
      draw();
    }});
  }});
}}

const DATA_XMIN = Math.min(...SERIES.map(s => s.x.length ? s.x[0] : Infinity));
const DATA_XMAX = Math.max(...SERIES.map(s => s.x.length ? s.x[s.x.length - 1] : -Infinity));

let viewXMin = DATA_XMIN;
let viewXMax = DATA_XMAX;
let yMode = 'linear';

const MARGIN = {{ left: 62, right: 18, top: 16, bottom: 40 }};
const TICK_ROW_H = 9;
const TICK_BAND_PAD = 4;

// Tick rows live INSIDE the plot frame, stacked just above the X-axis
// line -- they eat a fixed-pixel slice of the existing curve area rather
// than growing the frame, so panning/zooming/toggling series never moves
// them, but the curve area itself is correspondingly a bit shorter
// whenever a tick group is visible. Capped at 40% of the plot height so
// a large number of groups can't crowd out the curves entirely.
function tickBandH() {{
  const visibleGroups = TICKS.filter(g => g.visible !== false).length;
  if (!visibleGroups) return 0;
  return Math.min(visibleGroups * TICK_ROW_H + TICK_BAND_PAD, plotHeight() * 0.4);
}}

function curveHeight() {{
  return plotHeight() - tickBandH();
}}

// The Y-position (in canvas pixels) of each visible tick group's own
// row, stacked from the top of the tick band down to just above the
// X-axis line. Shared by drawing and hover hit-testing so they can never
// disagree about where a row actually is.
function visibleTickRows() {{
  const rows = [];
  if (!TICKS.length) return rows;
  const tbh = tickBandH();
  let rowY = MARGIN.top + plotHeight() - tbh + 2;
  for (const grp of TICKS) {{
    if (grp.visible === false) continue;
    rows.push({{ grp, top: rowY, bottom: rowY + TICK_ROW_H - 3 }});
    rowY += TICK_ROW_H;
  }}
  return rows;
}}

function transformY(y) {{
  if (yMode === 'sqrt') {{
    return Math.sign(y) * Math.sqrt(Math.abs(y));
  }}
  return y;
}}

function invTransformY(ty) {{
  if (yMode === 'sqrt') {{
    return Math.sign(ty) * ty * ty;
  }}
  return ty;
}}

// binary search for the first index in arr with arr[i] >= target
function lowerBound(arr, target) {{
  let lo = 0, hi = arr.length;
  while (lo < hi) {{
    const mid = (lo + hi) >> 1;
    if (arr[mid] < target) lo = mid + 1; else hi = mid;
  }}
  return lo;
}}

const DIFF_GAP_PX = 5;

function scanRange(predicate) {{
  let yMin = Infinity, yMax = -Infinity;
  for (const s of SERIES) {{
    if (s.visible === false || !predicate(s)) continue;
    const i0 = Math.max(0, lowerBound(s.x, viewXMin) - 1);
    const i1 = Math.min(s.x.length, lowerBound(s.x, viewXMax) + 1);
    for (let i = i0; i < i1; i++) {{
      const ty = transformY(s.y[i]);
      if (ty < yMin) yMin = ty;
      if (ty > yMax) yMax = ty;
    }}
  }}
  return [yMin, yMax];
}}

// All difference curves share ONE offset, recomputed live on every draw
// (it's inherently screen-space, not a fixed data-space number): the
// HIGHEST point among all visible diff curves is placed DIFF_GAP_PX below
// the LOWEST point among all visible main (non-diff) series -- "the
// maximum of all the difference plots is around 5 pixels below the
// minimum of all the Yobs," per the user's own words.
function computeDiffOffset(mainYMin, mainYMax, plotH) {{
  const [, diffMaxTy] = scanRange(s => s.kind === 'diff');
  if (!isFinite(diffMaxTy) || !isFinite(mainYMin)) return 0;
  const dataPerPx = (mainYMax - mainYMin) / (plotH || 1) || 1;
  return (mainYMin - DIFF_GAP_PX * dataPerPx) - diffMaxTy;
}}

// Reserved clearance (CSS px) between the lowest visible curve point (main
// series or diff, whichever is lower) and the tick band, whenever any tick
// group is visible. This REPLACES the proportional 8% pad on the bottom
// edge only (top edge keeps the proportional pad) -- using Math.max(pad,
// fixed) was wrong: on a pattern with a tall strong peak, the proportional
// 8% pad is itself huge (thousands of counts on the Y axis), so it always
// won regardless of this constant, producing a large gap above the tick
// row instead of the small fixed one intended. A small FIXED pixel gap is
// what "ticks sit just above the axis, close under the diff curve" means
// -- it must not scale with the data range at all.
const TICK_CLEARANCE_PX = 10;

function visibleYRange() {{
  const [mainYMin, mainYMax] = scanRange(s => s.kind !== 'diff');
  const diffOffset = computeDiffOffset(mainYMin, mainYMax, curveHeight());

  let yMin = mainYMin, yMax = mainYMax;
  const [diffMinTy, diffMaxTy] = scanRange(s => s.kind === 'diff');
  if (isFinite(diffMinTy)) {{
    yMin = Math.min(yMin, diffMinTy + diffOffset);
    yMax = Math.max(yMax, diffMaxTy + diffOffset);
  }}

  if (!isFinite(yMin) || !isFinite(yMax)) {{ yMin = 0; yMax = 1; }}
  if (yMin === yMax) {{ yMin -= 1; yMax += 1; }}
  const pad = (yMax - yMin) * 0.08;
  let bottomPad = pad;
  if (TICKS.length) {{
    const dataPerPx = (yMax - yMin) / (curveHeight() || 1) || 1;
    bottomPad = TICK_CLEARANCE_PX * dataPerPx;
  }}
  return {{ yMin: yMin - bottomPad, yMax: yMax + pad, diffOffset }};
}}

function plotWidth() {{ return canvas.width - MARGIN.left - MARGIN.right; }}
function plotHeight() {{ return canvas.height - MARGIN.top - MARGIN.bottom; }}

function xToPx(x) {{
  return MARGIN.left + (x - viewXMin) / (viewXMax - viewXMin) * plotWidth();
}}
function pxToX(px) {{
  return viewXMin + (px - MARGIN.left) / plotWidth() * (viewXMax - viewXMin);
}}
function yToPx(ty, yMin, yMax) {{
  return MARGIN.top + (1 - (ty - yMin) / (yMax - yMin)) * curveHeight();
}}

function niceStep(range, targetTicks) {{
  const raw = range / targetTicks;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  let step;
  if (norm < 1.5) step = 1;
  else if (norm < 3) step = 2;
  else if (norm < 7) step = 5;
  else step = 10;
  return step * mag;
}}

function styleVar(name) {{
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}}

function draw() {{
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const {{ yMin, yMax, diffOffset }} = visibleYRange();
  const grid = styleVar('--grid');
  const axis = styleVar('--axis');
  const ink = styleVar('--ink');
  const inkMuted = styleVar('--ink-muted');

  // gridlines + ticks
  ctx.strokeStyle = grid;
  ctx.fillStyle = inkMuted;
  ctx.font = '11px -apple-system, Segoe UI, Helvetica, Arial, sans-serif';
  ctx.lineWidth = 1;

  const xStep = niceStep(viewXMax - viewXMin, 8);
  const xStart = Math.ceil(viewXMin / xStep) * xStep;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (let x = xStart; x <= viewXMax; x += xStep) {{
    const px = xToPx(x);
    ctx.beginPath();
    ctx.moveTo(px, MARGIN.top);
    ctx.lineTo(px, MARGIN.top + plotHeight());
    ctx.stroke();
    ctx.fillText(x.toFixed(xStep < 1 ? 2 : 0), px, MARGIN.top + plotHeight() + 8);
  }}

  const yStep = niceStep(yMax - yMin, 6);
  const yStart = Math.ceil(yMin / yStep) * yStep;
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (let ty = yStart; ty <= yMax; ty += yStep) {{
    const py = yToPx(ty, yMin, yMax);
    ctx.beginPath();
    ctx.moveTo(MARGIN.left, py);
    ctx.lineTo(MARGIN.left + plotWidth(), py);
    ctx.stroke();
    const label = yMode === 'sqrt' ? invTransformY(ty) : ty;
    ctx.fillText(formatY(label), MARGIN.left - 8, py);
  }}

  // axes
  ctx.strokeStyle = axis;
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(MARGIN.left, MARGIN.top);
  ctx.lineTo(MARGIN.left, MARGIN.top + plotHeight());
  ctx.lineTo(MARGIN.left + plotWidth(), MARGIN.top + plotHeight());
  ctx.stroke();

  // reflection tick marks, one row per visible group -- INSIDE the plot
  // frame, stacked just above the X-axis line (see visibleTickRows/
  // tickBandH), independent of the Y-axis data/autoscale so hiding/
  // showing curves or toggling Sqrt(Y) never moves them.
  ctx.lineWidth = 1.3;
  for (const row of visibleTickRows()) {{
    ctx.strokeStyle = row.grp.color;
    const i0 = Math.max(0, lowerBound(row.grp.x, viewXMin) - 1);
    const i1 = Math.min(row.grp.x.length, lowerBound(row.grp.x, viewXMax) + 1);
    ctx.beginPath();
    for (let i = i0; i < i1; i++) {{
      const px = xToPx(row.grp.x[i]);
      ctx.moveTo(px, row.top);
      ctx.lineTo(px, row.bottom);
    }}
    ctx.stroke();
  }}

  // data lines, one per series
  for (const s of SERIES) {{
    if (s.visible === false) continue;
    const i0 = Math.max(0, lowerBound(s.x, viewXMin) - 2);
    const i1 = Math.min(s.x.length, lowerBound(s.x, viewXMax) + 2);
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    let started = false;
    const off = s.kind === 'diff' ? diffOffset : 0;
    for (let i = i0; i < i1; i++) {{
      const px = xToPx(s.x[i]);
      const py = yToPx(transformY(s.y[i]) + off, yMin, yMax);
      if (!started) {{ ctx.moveTo(px, py); started = true; }}
      else ctx.lineTo(px, py);
    }}
    ctx.stroke();
  }}

  ctx.fillStyle = ink;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'alphabetic';
  ctx.font = '12px -apple-system, Segoe UI, Helvetica, Arial, sans-serif';
  ctx.fillText(yMode === 'sqrt' ? 'Sqrt(Y)' : 'Y', 6, 14);

  drawCrosshair(yMin, yMax, diffOffset);
}}

function formatY(v) {{
  if (Math.abs(v) >= 1000) return v.toFixed(0);
  if (Math.abs(v) >= 10) return v.toFixed(1);
  return v.toFixed(2);
}}

let hoverPx = null;
let hoverTick = null;  // {{ grp, idx, rowTop }} or null

// Distinct from the crosshair's own "no floating text" rule above (that
// rule is specifically about curve/series values at the cursor X): a
// hovered TICK gets a small floating tooltip pinned to the tick's own
// position, since there's no other way to surface its h k l label.
function updateTickHover(mouseX, mouseY) {{
  hoverTick = null;
  for (const row of visibleTickRows()) {{
    if (mouseY < row.top - 4 || mouseY > row.bottom + 4) continue;
    const dataX = pxToX(mouseX);
    const i = lowerBound(row.grp.x, dataX);
    let best = -1, bestDist = Infinity;
    for (const cand of [i - 1, i]) {{
      if (cand < 0 || cand >= row.grp.x.length) continue;
      const dist = Math.abs(xToPx(row.grp.x[cand]) - mouseX);
      if (dist < bestDist) {{ bestDist = dist; best = cand; }}
    }}
    if (best >= 0 && bestDist <= 5) {{
      hoverTick = {{ grp: row.grp, idx: best, rowTop: row.top }};
    }}
    break;
  }}
}}

function updateTickTooltip() {{
  if (!hoverTick) {{ tickTooltipEl.style.display = 'none'; return; }}
  const {{ grp, idx, rowTop }} = hoverTick;
  const label = grp.labels && grp.labels[idx] ? grp.labels[idx] : null;
  const pos = grp.x[idx];
  tickTooltipEl.textContent = label
    ? (grp.name + ': ' + label)
    : (grp.name + ' @ ' + pos.toFixed(3));
  tickTooltipEl.style.left = xToPx(pos) + 'px';
  tickTooltipEl.style.top = rowTop + 'px';
  tickTooltipEl.style.display = 'block';
}}

// Crosshair only: a vertical guide line plus one colored marker dot per
// visible series at the hovered X -- no floating text box attached to the
// cursor (removed directly at the user's request).
function drawCrosshair(yMin, yMax, diffOffset) {{
  if (hoverPx === null) return;
  const dataX = pxToX(hoverPx);
  const px = xToPx(dataX);

  ctx.save();
  ctx.strokeStyle = styleVar('--axis');
  ctx.setLineDash([3, 3]);
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(px, MARGIN.top);
  ctx.lineTo(px, MARGIN.top + plotHeight());
  ctx.stroke();
  ctx.setLineDash([]);

  for (const s of SERIES) {{
    if (s.visible === false) continue;
    const idx = Math.min(s.x.length - 1, Math.max(0, lowerBound(s.x, dataX)));
    const off = s.kind === 'diff' ? diffOffset : 0;
    const py = yToPx(transformY(s.y[idx]) + off, yMin, yMax);
    ctx.fillStyle = s.color;
    ctx.beginPath();
    ctx.arc(xToPx(s.x[idx]), py, 3.2, 0, Math.PI * 2);
    ctx.fill();
  }}
  ctx.restore();
}}

// --- interaction: drag to pan, wheel to zoom ---
let dragging = false;
let dragStartPx = 0;
let dragStartXMin = 0;
let dragStartXMax = 0;

canvas.addEventListener('mousedown', (e) => {{
  dragging = true;
  canvas.classList.add('dragging');
  dragStartPx = e.offsetX;
  dragStartXMin = viewXMin;
  dragStartXMax = viewXMax;
  hoverTick = null;
  updateTickTooltip();
}});
window.addEventListener('mouseup', () => {{
  dragging = false;
  canvas.classList.remove('dragging');
}});
canvas.addEventListener('mouseleave', () => {{
  hoverPx = null;
  hoverTick = null;
  updateTickTooltip();
  draw();
}});
canvas.addEventListener('mousemove', (e) => {{
  if (dragging) {{
    const dxPx = e.offsetX - dragStartPx;
    const dxData = dxPx / plotWidth() * (dragStartXMax - dragStartXMin);
    viewXMin = dragStartXMin - dxData;
    viewXMax = dragStartXMax - dxData;
    clampView();
    draw();
  }} else {{
    hoverPx = e.offsetX;
    updateTickHover(e.offsetX, e.offsetY);
    updateTickTooltip();
    draw();
  }}
}});

canvas.addEventListener('wheel', (e) => {{
  e.preventDefault();
  const factor = Math.pow(1.0016, e.deltaY);
  const cursorX = pxToX(e.offsetX);
  viewXMin = cursorX + (viewXMin - cursorX) * factor;
  viewXMax = cursorX + (viewXMax - cursorX) * factor;
  clampView();
  draw();
}}, {{ passive: false }});

function clampView() {{
  const fullRange = DATA_XMAX - DATA_XMIN;
  let range = viewXMax - viewXMin;
  const minRange = fullRange / 5000;
  if (range < minRange) {{
    const c = (viewXMin + viewXMax) / 2;
    viewXMin = c - minRange / 2;
    viewXMax = c + minRange / 2;
    range = minRange;
  }}
  if (range > fullRange) {{
    viewXMin = DATA_XMIN;
    viewXMax = DATA_XMAX;
    return;
  }}
  if (viewXMin < DATA_XMIN) {{ viewXMin = DATA_XMIN; viewXMax = viewXMin + range; }}
  if (viewXMax > DATA_XMAX) {{ viewXMax = DATA_XMAX; viewXMin = viewXMax - range; }}
}}

sqrtToggle.addEventListener('change', () => {{
  yMode = sqrtToggle.checked ? 'sqrt' : 'linear';
  draw();
}});
resetBtn.addEventListener('click', () => {{
  viewXMin = DATA_XMIN;
  viewXMax = DATA_XMAX;
  draw();
}});

function resizeCanvas() {{
  const holder = canvas.parentElement;
  const w = Math.max(320, holder.clientWidth);
  canvas.width = w;
  canvas.height = Math.round(w * 0.49);
  draw();
}}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();
</script>
</body>
</html>
"""


def build_stats_html(stats):
    """Render '--stats' label=value pairs as extra `middot`-separated text
    in the header meta line -- plain text-ink, no color/series styling,
    since a stat like Rwp/GoF is a headline number, not a series identity
    (see dataviz skill: color follows the entity, text stays in ink)."""
    if not stats:
        return ""
    escaped = (
        f"{label.replace('<', '&lt;').replace('>', '&gt;')} {value.replace('<', '&lt;').replace('>', '&gt;')}"
        for label, value in stats
    )
    return " &middot; " + " &middot; ".join(escaped)


def build_html(series, title, ticks=None, stats=None):
    ticks = ticks or []
    all_x = [x for s in series for x in s["x"]]
    xmin_disp = f"{min(all_x):.4g}" if all_x else "n/a"
    xmax_disp = f"{max(all_x):.4g}" if all_x else "n/a"
    npoints = " + ".join(str(len(s["x"])) for s in series) if len(series) > 1 else str(len(series[0]["x"]) if series else 0)
    return PAGE_TEMPLATE.format(
        title_escaped=title.replace("<", "&lt;").replace(">", "&gt;"),
        npoints=npoints,
        xmin_disp=xmin_disp,
        xmax_disp=xmax_disp,
        stats_html=build_stats_html(stats),
        series_json=json.dumps(series),
        ticks_json=json.dumps(ticks),
    )


def build_phase_series(phases_spec):
    """Parse '--phases NAME1:obs1.xy:calc1.xy,NAME2:obs2.xy:calc2.xy,...'
    into a full series list (Yobs/Ycalc pair + diff per phase), colors
    auto-assigned per the user's standing scheme -- see the module
    docstring and yobs_phase_color/YCALC_COLOR/diff_color_from_yobs."""
    series = []
    diff_specs = []  # (name_a, name_b, label, color), applied after all phases are built
    for i, spec in enumerate(phases_spec.split(",")):
        parts = [s.strip() for s in spec.split("|")]
        if len(parts) != 3:
            print(f"--phases entry {spec!r} must be NAME|obs.xy|calc.xy", file=sys.stderr)
            sys.exit(1)
        name, obs_path, calc_path = parts
        yobs_rgb = yobs_phase_color(i)
        yobs_hex = rgb_to_hex(yobs_rgb)
        ycalc_hex = rgb_to_hex(YCALC_COLOR)
        diff_hex = rgb_to_hex(diff_color_from_yobs(yobs_rgb))

        obs_xs, obs_ys = parse_xy_file(obs_path)
        if not obs_xs:
            print(f"No numeric (x, y) data found in {obs_path}", file=sys.stderr)
            sys.exit(1)
        calc_xs, calc_ys = parse_xy_file(calc_path)
        if not calc_xs:
            print(f"No numeric (x, y) data found in {calc_path}", file=sys.stderr)
            sys.exit(1)

        obs_label, calc_label = f"{name} Yobs", f"{name} Ycalc"
        series.append({"name": obs_label, "color": yobs_hex, "x": obs_xs, "y": obs_ys})
        series.append({"name": calc_label, "color": ycalc_hex, "x": calc_xs, "y": calc_ys})
        diff_specs.append((obs_label, calc_label, f"{obs_label} - {calc_label}", diff_hex))

    series_by_name = {s["name"]: s for s in series}
    for name_a, name_b, label, color in diff_specs:
        series.append(compute_diff_series(series_by_name, name_a, name_b, label, color))
    return series


def parse_tick_reflection_file(path):
    """Parse a reflection-tick source file into a list of
    {'x': float, 'label': str|None} entries, one per reflection, sorted
    by position. Each line is judged independently by its own numeric
    token count so the two recognized TOPAS output formats can't be
    confused with each other and a stray malformed line doesn't abort
    the rest:
      - >=7 tokens: Create_hklm_d_Th2_Ip_file's own "h k l m d 2Th I"
        columns -- position is column index 5 (2Th), label is 'h k l'
        (h/k/l rounded to the nearest integer -- TOPAS writes them as
        floats, e.g. '1' or '-2', but they're always integral).
      - 2-6 tokens: a plain "position intensity [...]" file (e.g.
        Create_2Th_Ip_file) -- position is the first column, no label.
    """
    entries = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped[0] in "'#":
                continue
            tokens = NUM_RE.findall(stripped)
            if len(tokens) >= 7:
                try:
                    h, k, l = (int(round(float(t))) for t in tokens[:3])
                    x = float(tokens[5])
                except ValueError:
                    continue
                entries.append({"x": x, "label": f"{h} {k} {l}"})
            elif len(tokens) >= 2:
                try:
                    x = float(tokens[0])
                except ValueError:
                    continue
                entries.append({"x": x, "label": None})
    entries.sort(key=lambda e: e["x"])
    return entries


def parse_stats(stats_spec):
    """Parse '--stats Label1=value1,Label2=value2,...' into an ordered
    list of (label, value) string pairs, preserving the order given."""
    pairs = []
    for spec in stats_spec.split(","):
        spec = spec.strip()
        if not spec:
            continue
        if "=" not in spec:
            print(f"--stats entry {spec!r} must be Label=value", file=sys.stderr)
            sys.exit(1)
        label, value = spec.split("=", 1)
        pairs.append((label.strip(), value.strip()))
    return pairs


def build_tick_groups(ticks_spec):
    """Parse '--ticks NAME1|positions1.xy[|color1],NAME2|positions2.xy[|color2],...'
    into a list of {name, color, x, labels} tick-mark groups (see
    parse_tick_reflection_file for the two recognized file formats)."""
    groups = []
    for spec in ticks_spec.split(","):
        parts = [s.strip() for s in spec.split("|")]
        if len(parts) not in (2, 3):
            print(f"--ticks entry {spec!r} must be NAME|positions.xy[|color]", file=sys.stderr)
            sys.exit(1)
        name, path = parts[0], parts[1]
        color = parts[2] if len(parts) == 3 else DEFAULT_TICK_COLOR
        entries = parse_tick_reflection_file(path)
        if not entries:
            print(f"No numeric tick positions found in {path}", file=sys.stderr)
            sys.exit(1)
        groups.append({
            "name": name,
            "color": color,
            "x": [e["x"] for e in entries],
            "labels": [e["label"] for e in entries],
        })
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xy_files", nargs="*", help="one or more XY(E) data files to overlay (not used with --phases)")
    parser.add_argument("-o", "--output", help="output HTML path (default: <first file name>_xy_plot.html)")
    parser.add_argument("--title", help="plot title (default: the file name(s))")
    parser.add_argument("--labels", help="comma-separated series labels, parallel to xy_files")
    parser.add_argument("--colors", help="comma-separated series colors (CSS color names or hex), parallel to xy_files")
    parser.add_argument(
        "--diff",
        action="append",
        help="add a LABEL_A,LABEL_B difference series (A - B). Repeatable (e.g. once per xdd/phase "
        "when combining several into one plot) -- all diff curves share one live, screen-space offset "
        "below the main pattern (see the module docstring), so they never overlap it or each other.",
    )
    parser.add_argument("--diff-labels", help="comma-separated labels, parallel to --diff (default: 'A - B' per pair)")
    parser.add_argument("--diff-colors", help="comma-separated colors, parallel to --diff")
    parser.add_argument(
        "--phases",
        help="'NAME1|obs1.xy|calc1.xy,NAME2|obs2.xy|calc2.xy,...' (pipe-separated) -- convenience for "
        "the multi-xdd case, auto-building Yobs/Ycalc/diff series with the standard color scheme per "
        "phase (see the module docstring). Cannot be combined with xy_files/--labels/--colors/--diff.",
    )
    parser.add_argument(
        "--ticks",
        help="'NAME1|positions1.xy[|color1],NAME2|positions2.xy[|color2],...' (pipe-separated fields, "
        "comma-separated groups) -- adds a row of Bragg-reflection tick marks per named group below "
        "the main plot (see the module docstring). Combinable with either xy_files or --phases.",
    )
    parser.add_argument(
        "--stats",
        help="'Label1=value1,Label2=value2,...' (comma-separated) -- refinement statistics (e.g. "
        "Rwp/GoF/Rp) shown as plain text in the header meta line, e.g. --stats \"Rwp=13.68%%,GoF=1.64\". "
        "Not a series/color -- a headline number, not an identity, so it's rendered in the same "
        "muted text-ink as the point-count/X-range meta text. Combinable with xy_files or --phases.",
    )
    args = parser.parse_args()

    ticks = build_tick_groups(args.ticks) if args.ticks else None
    stats = parse_stats(args.stats) if args.stats else None

    if args.phases:
        if args.xy_files or args.labels or args.colors or args.diff:
            print("--phases cannot be combined with xy_files/--labels/--colors/--diff", file=sys.stderr)
            sys.exit(1)
        series = build_phase_series(args.phases)
        title = args.title or "all phases"
        out_path = args.output or "combined_xy_plot.html"
        html = build_html(series, title, ticks=ticks, stats=stats)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
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
    html = build_html(series, title, ticks=ticks, stats=stats)

    out_path = args.output
    if not out_path:
        base, _ = os.path.splitext(args.xy_files[0])
        out_path = base + "_xy_plot.html"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
