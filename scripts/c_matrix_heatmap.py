#!/usr/bin/env python3
"""
Render a TOPAS `C_matrix_normalized { ... }` block (the normalized parameter
correlation matrix) as a PNG heatmap. Zero third-party dependencies -- PNG
bytes are hand-encoded with the standard library's zlib module, so this runs
on any stock Python 3 install with no pip install required.

Usage:
    python c_matrix_heatmap.py <path/to/file.inp or .out> [-o output.png] [--cell-size N]

The matrix block is located and parsed as plain text (it does not need to be
macro-expanded first) -- this works equally on a .inp file that already has a
literal C_matrix_normalized block pasted into it, or on a real TOPAS .out
refinement result.

Row/column axes on the image are labeled with their 1-based index only (kept
to the bundled digit-only bitmap font); the full parameter name for each
index is printed to stdout as a legend, matching TOPAS's own convention of
prefixing each matrix row with "<name> <index>:" in the source text.
"""
import argparse
import os
import re
import struct
import sys
import zlib

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def extract_matrix(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    m = re.search(r"C_matrix_normalized\s*\{", text)
    if not m:
        raise ValueError(f"No C_matrix_normalized block found in {path}")

    # Walk forward from the opening brace to find its matching close, so we
    # don't depend on the block being the last thing in the file.
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    body = text[start:i - 1]

    lines = [ln for ln in body.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("C_matrix_normalized block is empty")

    # First line: column indices header, e.g. "1   2   3 ... 22" -- gives us
    # the expected column count.
    header_tokens = lines[0].split()
    ncols = len(header_tokens)
    if not all(tok.isdigit() for tok in header_tokens):
        raise ValueError(f"Unexpected header line in C_matrix_normalized: {lines[0]!r}")

    labels = []
    matrix = []
    pending = []  # values accumulated across wrapped continuation lines

    row_start_re = re.compile(r"^(\S+)\s+(\d+):\s*(.*)$")
    # TOPAS's own fixed-width column formatting can print two adjacent
    # negative values with no separating space at all when both reach 3+
    # digits (e.g. "-73-100", confirmed directly in a real refined .out) --
    # plain str.split() can't recover the boundary since there's no
    # whitespace to split on. Match signed-integer tokens explicitly instead,
    # so "-73-100" tokenizes as ["-73", "-100"] rather than failing int().
    int_token_re = re.compile(r"-?\d+")

    for ln in lines[1:]:
        row_match = row_start_re.match(ln.strip())
        if row_match and not pending:
            label, _idx, rest = row_match.groups()
            labels.append(label)
            pending = int_token_re.findall(rest)
        else:
            # continuation of a wrapped row (no "<label> N:" prefix)
            pending.extend(int_token_re.findall(ln))

        if len(pending) >= ncols:
            values = [int(v) for v in pending[:ncols]]
            matrix.append(values)
            pending = []

    if len(matrix) != ncols or any(len(row) != ncols for row in matrix):
        raise ValueError(
            f"Parsed matrix shape ({len(matrix)}x{len(matrix[0]) if matrix else 0}) "
            f"doesn't match header column count ({ncols}); the block may use a "
            f"layout this parser doesn't handle."
        )

    return labels, matrix


# ---------------------------------------------------------------------------
# 3x5 digit-only bitmap font (covers everything an index/value needs to show)
# ---------------------------------------------------------------------------

FONT = {
    "0": ["111", "101", "101", "101", "111"],
    "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"],
    "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"],
    "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"],
    "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"],
    "9": ["111", "101", "111", "001", "111"],
    "-": ["000", "000", "111", "000", "000"],
    " ": ["000", "000", "000", "000", "000"],
}
GLYPH_W, GLYPH_H = 3, 5


def text_width(s, scale, spacing=1):
    return len(s) * (GLYPH_W * scale + spacing) - spacing if s else 0


def draw_text(buf, width, x0, y0, s, color, scale=1, spacing=1):
    """Blit a string into an RGB byte buffer (mutated in place)."""
    x = x0
    for ch in s:
        glyph = FONT.get(ch, FONT[" "])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit != "1":
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        px = x + gx * scale + sx
                        py = y0 + gy * scale + sy
                        set_pixel(buf, width, px, py, color)
        x += GLYPH_W * scale + spacing


def set_pixel(buf, width, x, y, color):
    if x < 0 or y < 0:
        return
    idx = (y * width + x) * 3
    if idx < 0 or idx + 3 > len(buf):
        return
    buf[idx:idx + 3] = bytes(color)


def fill_rect(buf, width, x0, y0, w, h, color):
    row = bytes(color) * w
    for y in range(y0, y0 + h):
        idx = (y * width + x0) * 3
        buf[idx:idx + len(row)] = row


def rect_outline(buf, width, x0, y0, w, h, color, thickness=1):
    for t in range(thickness):
        fill_rect(buf, width, x0 + t, y0 + t, w - 2 * t, 1, color)
        fill_rect(buf, width, x0 + t, y0 + h - 1 - t, w - 2 * t, 1, color)
        fill_rect(buf, width, x0 + t, y0 + t, 1, h - 2 * t, color)
        fill_rect(buf, width, x0 + w - 1 - t, y0 + t, 1, h - 2 * t, color)


# ---------------------------------------------------------------------------
# Color scale: blue <-> red diverging, gray midpoint (matches the palette
# used for the equivalent HTML/artifact heatmap of this same data)
# ---------------------------------------------------------------------------

POLE_NEG = (0x2A, 0x78, 0xD6)   # blue
POLE_POS = (0xE3, 0x49, 0x48)   # red
MID = (0xF0, 0xEF, 0xEC)        # neutral gray
INK_DARK = (0x0B, 0x0B, 0x0B)
INK_LIGHT = (0xFF, 0xFF, 0xFF)
SURFACE = (0xFC, 0xFC, 0xFB)
GRIDLINE = (0xE1, 0xE0, 0xD9)


def cell_color(value):
    t = min(abs(value) / 100.0, 1.0)
    pole = POLE_POS if value >= 0 else POLE_NEG
    return tuple(round(MID[i] + (pole[i] - MID[i]) * t) for i in range(3))


def relative_luminance(rgb):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ---------------------------------------------------------------------------
# PNG encoding (stdlib-only: zlib for DEFLATE, struct for chunk framing)
# ---------------------------------------------------------------------------

def write_png(path, width, height, rgb_buf):
    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB

    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter type: None
        raw.extend(rgb_buf[y * stride:(y + 1) * stride])
    idat = zlib.compress(bytes(raw), 9)

    with open(path, "wb") as f:
        f.write(sig)
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", idat))
        f.write(chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_heatmap(labels, matrix, cell_size=26, pad=16, legend_h=40):
    n = len(labels)
    max_index_w = text_width(str(n), scale=2)
    margin_left = max_index_w + 14
    margin_top = 24

    grid_w = n * cell_size
    grid_h = n * cell_size
    width = pad * 2 + margin_left + grid_w
    height = pad * 2 + margin_top + grid_h + legend_h

    buf = bytearray(SURFACE * (width * height))

    gx0 = pad + margin_left
    gy0 = pad + margin_top

    # column index labels
    for c in range(n):
        s = str(c + 1)
        tx = gx0 + c * cell_size + (cell_size - text_width(s, 2)) // 2
        ty = pad + (margin_top - GLYPH_H * 2) // 2
        draw_text(buf, width, tx, ty, s, INK_DARK, scale=2)

    # row index labels
    for r in range(n):
        s = str(r + 1)
        tx = pad + margin_left - text_width(s, 2) - 6
        ty = gy0 + r * cell_size + (cell_size - GLYPH_H * 2) // 2
        draw_text(buf, width, tx, ty, s, INK_DARK, scale=2)

    # cells
    for r in range(n):
        for c in range(n):
            value = matrix[r][c]
            color = cell_color(value)
            cx = gx0 + c * cell_size
            cy = gy0 + r * cell_size
            fill_rect(buf, width, cx, cy, cell_size, cell_size, color)
            rect_outline(buf, width, cx, cy, cell_size, 1, GRIDLINE)  # top edge
            rect_outline(buf, width, cx, cy, 1, cell_size, GRIDLINE)  # left edge
            if r == c:
                rect_outline(buf, width, cx, cy, cell_size, cell_size, INK_DARK, thickness=1)

            text_ink = INK_LIGHT if relative_luminance(color) < 0.5 else INK_DARK
            s = str(value) if value != 0 else "0"
            tw = text_width(s, 1)
            tx = cx + (cell_size - tw) // 2
            ty = cy + (cell_size - GLYPH_H) // 2
            draw_text(buf, width, tx, ty, s, text_ink, scale=1)

    # bottom border of grid
    rect_outline(buf, width, gx0, gy0, grid_w, grid_h, GRIDLINE, thickness=1)

    # legend gradient bar: -100 .. 0 .. 100
    bar_x0 = gx0
    bar_y0 = gy0 + grid_h + 16
    bar_w = min(220, grid_w)
    bar_h = 10
    for i in range(bar_w):
        t = i / (bar_w - 1)
        value = -100 + 200 * t
        color = cell_color(value)
        fill_rect(buf, width, bar_x0 + i, bar_y0, 1, bar_h, color)
    rect_outline(buf, width, bar_x0, bar_y0, bar_w, bar_h, GRIDLINE)

    for label, frac in (("-100", 0.0), ("0", 0.5), ("100", 1.0)):
        tw = text_width(label, 1)
        tx = bar_x0 + int(frac * bar_w) - tw // 2
        tx = max(bar_x0, min(tx, bar_x0 + bar_w - tw))
        draw_text(buf, width, tx, bar_y0 + bar_h + 4, label, INK_DARK, scale=1)

    return width, height, buf


# ---------------------------------------------------------------------------
# Interactive HTML rendering (self-contained: inline CSS/JS, no CDN, no
# external files -- open directly in any browser, no server needed)
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>C_matrix_normalized heatmap</title>
<style>
  :root {
    --surface-1: #fcfcfb; --page: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --text-muted: #898781; --gridline: #e1e0d9;
    --border: rgba(11,11,11,0.10); --pole-neg: #2a78d6; --pole-pos: #e34948;
    --mid: #f0efec; --diag-ring: #0b0b0b;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #ffffff;
      --text-secondary: #c3c2b7; --text-muted: #898781; --gridline: #2c2c2a;
      --border: rgba(255,255,255,0.10); --pole-neg: #3987e5; --pole-pos: #e66767;
      --mid: #383835; --diag-ring: #ffffff;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         background: var(--page); color: var(--text-primary); }
  .wrap { padding: 28px 20px 40px; }
  h1 { font-size: 17px; font-weight: 600; margin: 0 0 2px; }
  .subtitle { font-size: 13px; color: var(--text-secondary); margin: 0 0 20px; }
  .panel { background: var(--surface-1); border: 1px solid var(--border);
           border-radius: 10px; padding: 20px; max-width: 100%; }
  .scroll { overflow-x: auto; padding-bottom: 6px; }
  .matrix-grid { display: grid; width: max-content; position: relative; }
  .cell { display: flex; align-items: center; justify-content: center;
          font-size: 9px; font-variant-numeric: tabular-nums;
          border-right: 1px solid var(--gridline); border-bottom: 1px solid var(--gridline);
          cursor: default; user-select: none; }
  .cell.diag { box-shadow: inset 0 0 0 1.5px var(--diag-ring); }
  .rowlabel, .collabel { color: var(--text-secondary); font-size: 10px; white-space: nowrap; }
  .rowlabel { display: flex; align-items: center; justify-content: flex-end;
              padding-right: 10px; border-right: 1px solid var(--gridline);
              border-bottom: 1px solid var(--gridline); }
  .collabel { position: relative; border-bottom: 1px solid var(--gridline); }
  .collabel span { position: absolute; left: 50%; bottom: 6px;
                    transform-origin: left bottom; transform: rotate(-45deg) translateX(-4px); }
  .corner { border-right: 1px solid var(--gridline); border-bottom: 1px solid var(--gridline); }
  .cell:hover, .rowlabel.active, .collabel.active span {
    outline: 2px solid var(--text-primary); outline-offset: -2px;
    color: var(--text-primary); font-weight: 600;
  }
  .legend { display: flex; align-items: center; gap: 10px; margin-top: 18px;
            font-size: 11px; color: var(--text-secondary); }
  .legend-bar { height: 10px; width: 220px; border-radius: 4px;
                background: linear-gradient(to right, var(--pole-neg), var(--mid) 50%, var(--pole-pos));
                border: 1px solid var(--border); }
  .legend-ticks { display: flex; justify-content: space-between; width: 220px;
                  font-size: 10px; color: var(--text-muted); margin-top: 2px; }
  .legend-col { display: flex; flex-direction: column; }
  #tooltip { position: fixed; pointer-events: none; background: var(--text-primary);
             color: var(--surface-1); font-size: 11px; padding: 6px 9px; border-radius: 6px;
             line-height: 1.4; box-shadow: 0 4px 14px rgba(0,0,0,0.25); opacity: 0;
             transition: opacity 0.08s ease; z-index: 10; max-width: 260px; }
  #tooltip.show { opacity: 1; }
  #tooltip b { font-weight: 600; }
</style>
</head>
<body>
<div class="wrap">
  <h1>C_matrix_normalized</h1>
  <p class="subtitle">Normalized parameter correlation matrix &mdash; __SOURCE__ (__N__ refined parameters, values in %)</p>
  <div class="panel">
    <div class="scroll"><div class="matrix-grid" id="grid"></div></div>
    <div class="legend">
      <div class="legend-col">
        <div class="legend-bar"></div>
        <div class="legend-ticks"><span>&minus;100</span><span>&minus;50</span><span>0</span><span>50</span><span>100</span></div>
      </div>
      <span>correlation (%) &mdash; diagonal = self-correlation (100)</span>
    </div>
  </div>
</div>
<div id="tooltip"></div>
<script>
const labels = __LABELS_JSON__;
const matrix = __MATRIX_JSON__;
const n = labels.length;

function lerp(a, b, t) { return a + (b - a) * t; }
function lerpColor(c1, c2, t) {
  return [Math.round(lerp(c1[0],c2[0],t)), Math.round(lerp(c1[1],c2[1],t)), Math.round(lerp(c1[2],c2[2],t))];
}
function hexToRgb(hex) {
  const v = hex.replace('#','');
  return [parseInt(v.slice(0,2),16), parseInt(v.slice(2,4),16), parseInt(v.slice(4,6),16)];
}
function rgbToHex([r,g,b]) { return '#' + [r,g,b].map(x => x.toString(16).padStart(2,'0')).join(''); }
function relLuminance([r,g,b]) {
  const s = [r,g,b].map(c => { c/=255; return c<=0.03928 ? c/12.92 : Math.pow((c+0.055)/1.055,2.4); });
  return 0.2126*s[0] + 0.7152*s[1] + 0.0722*s[2];
}
function cellColor(value) {
  const root = getComputedStyle(document.documentElement);
  const neg = hexToRgb(root.getPropertyValue('--pole-neg').trim());
  const pos = hexToRgb(root.getPropertyValue('--pole-pos').trim());
  const mid = hexToRgb(root.getPropertyValue('--mid').trim());
  const t = Math.min(Math.abs(value) / 100, 1);
  return value >= 0 ? lerpColor(mid, pos, t) : lerpColor(mid, neg, t);
}

const grid = document.getElementById('grid');
const tooltip = document.getElementById('tooltip');
grid.style.gridTemplateColumns = '150px repeat(' + n + ', 27px)';
grid.style.gridTemplateRows = '110px repeat(' + n + ', 27px)';

const corner = document.createElement('div');
corner.className = 'corner';
grid.appendChild(corner);

labels.forEach((label, c) => {
  const div = document.createElement('div');
  div.className = 'collabel';
  div.id = 'col-' + c;
  const span = document.createElement('span');
  span.textContent = label;
  div.appendChild(span);
  grid.appendChild(div);
});

labels.forEach((rowLabel, r) => {
  const rl = document.createElement('div');
  rl.className = 'rowlabel';
  rl.id = 'row-' + r;
  rl.textContent = rowLabel;
  grid.appendChild(rl);

  matrix[r].forEach((value, c) => {
    const cell = document.createElement('div');
    cell.className = 'cell' + (r === c ? ' diag' : '');
    const rgb = cellColor(value);
    cell.style.background = rgbToHex(rgb);
    cell.style.color = relLuminance(rgb) < 0.5 ? '#ffffff' : '#0b0b0b';
    cell.textContent = value;

    cell.addEventListener('mouseenter', () => {
      document.getElementById('row-' + r).classList.add('active');
      document.getElementById('col-' + c).classList.add('active');
      tooltip.innerHTML = '<b>' + rowLabel + '</b> &times; <b>' + labels[c] + '</b><br>correlation: ' + value + '%';
      tooltip.classList.add('show');
    });
    cell.addEventListener('mousemove', (e) => {
      tooltip.style.left = (e.clientX + 14) + 'px';
      tooltip.style.top = (e.clientY + 14) + 'px';
    });
    cell.addEventListener('mouseleave', () => {
      document.getElementById('row-' + r).classList.remove('active');
      document.getElementById('col-' + c).classList.remove('active');
      tooltip.classList.remove('show');
    });

    grid.appendChild(cell);
  });
});
</script>
</body>
</html>
"""


def render_html(labels, matrix, source_name):
    import json
    html = HTML_TEMPLATE
    html = html.replace("__SOURCE__", source_name)
    html = html.replace("__N__", str(len(labels)))
    html = html.replace("__LABELS_JSON__", json.dumps(labels))
    html = html.replace("__MATRIX_JSON__", json.dumps(matrix))
    return html


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="TOPAS .inp or .out file containing a C_matrix_normalized block")
    ap.add_argument("-o", "--output", help="output path (default: <input>_c_matrix.<ext>)")
    ap.add_argument("--format", choices=["png", "html"], default=None,
                     help="output format (default: inferred from -o's extension, else png). "
                          "html produces a self-contained interactive page (hover tooltips, "
                          "full parameter names, no server needed) -- open it directly in a browser.")
    ap.add_argument("--cell-size", type=int, default=26, help="pixel size of each matrix cell, PNG only (default: 26)")
    args = ap.parse_args()

    labels, matrix = extract_matrix(args.input)

    fmt = args.format
    if fmt is None and args.output:
        ext = os.path.splitext(args.output)[1].lower()
        fmt = "html" if ext in (".html", ".htm") else "png"
    if fmt is None:
        fmt = "png"

    out_path = args.output
    if not out_path:
        base = os.path.splitext(args.input)[0]
        out_path = base + "_c_matrix." + ("html" if fmt == "html" else "png")

    if fmt == "html":
        html = render_html(labels, matrix, os.path.basename(args.input))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Wrote interactive heatmap to {out_path}")
        print("Open it directly in a browser (double-click, or 'start " + out_path + "' on Windows).")
    else:
        width, height, buf = render_heatmap(labels, matrix, cell_size=args.cell_size)
        write_png(out_path, width, height, buf)
        print(f"Wrote {width}x{height} heatmap to {out_path}")

    print()
    print("Legend (axis index -> parameter name):")
    for i, label in enumerate(labels, start=1):
        print(f"  {i:>2}: {label}")


if __name__ == "__main__":
    main()
