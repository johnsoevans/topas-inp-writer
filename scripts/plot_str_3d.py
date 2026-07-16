#!/usr/bin/env python3
"""
plot_str_3d.py -- Render one `str` phase from a TOPAS .inp file as a
self-contained, interactive 3D HTML page (drag to rotate, wheel/pinch to
zoom): the unit cell as a wireframe box, atoms as colored spheres
(symmetry-expanded across the whole cell from each written site), and
best-effort bonds drawn between atoms closer than a covalent-radius-sum
cutoff.

Method, reusing this skill's existing crystallography/parsing engine
rather than re-deriving it:
  - str-block/site extraction: check_inp_syntax.py's find_str_blocks,
    find_sites, extract_keyword_form, resolve_site_coordinates (the same
    code that already resolves 'x = 1/4;'-style equations and simple
    'y = Get(x) + offset;' ties for the Wyckoff-constraint checker).
  - Space-group operators: symmetry_utils.resolve_sg_operators (TOPAS's
    own sgcom6.exe / sg/ database via TOPAS_DIR -- an .inp never carries
    its own operator list the way a CIF can, so this is the only source).
  - Cell parameters: either literal a/b/c/al/be/ga (with simple Get()
    ties resolved the same way as site coordinates), or one of TOPAS's
    built-in Cubic/Tetragonal/Hexagonal/Trigonal/Rhombohedral lattice
    macros, whose exact argument-to-parameter mapping was read directly
    from the live install's topas.inc (Cubic(cv): a=b=c=cv; Tetragonal
    (a_cv,c_cv): a=b=a_cv,c=c_cv; Hexagonal/Trigonal(a_cv,c_cv): same
    plus ga=120; Rhombohedral(a_cv,al_cv): a=b=c=a_cv,al=be=ga=al_cv).
  - Symmetry expansion: every site's resolved fractional point is mapped
    through every operator in the space group, reduced mod 1, and
    deduplicated -- exactly the orbit that gives the site's multiplicity.
    A point lying on (or within tolerance of) a cell face/edge/corner
    (frac coordinate ~0) is additionally mirrored to the ~1 side so the
    unit cell box looks visually complete (atoms sit at all its corners/
    edges), matching common structure-viewer convention (e.g. VESTA).
  - Fractional -> Cartesian uses the standard triclinic cell matrix (a
    along x; standard crystallographic convention), so any crystal
    system renders correctly, not just orthogonal ones.

Element colors/covalent radii are an approximate built-in table (Jmol/
CPK-style colors, Cordero-style single-bond covalent radii) covering
common elements -- ~70 entries in ELEMENT_TABLE below -- meant as a
readable visual aid, NOT for scientific bond-length analysis. An
unrecognized element symbol falls back to gray with a generic radius.

Rendering is a small hand-written vanilla-JS canvas 3D engine (rotation
matrix + weak-perspective projection + painter's-algorithm depth
sorting) -- deliberately not three.js or any other CDN dependency, so
the output HTML is fully self-contained and works offline / inside a
strict-CSP viewer.

Known limitations, stated plainly:
  - Occupancy/site-mixing is not visualized (each site's FIRST scattering
    species is used for color/label; a partially-occupied or mixed site
    is drawn as if fully one species).
  - Only sites whose x/y/z all resolve to a concrete number (per
    resolve_site_coordinates -- bare/@ values, or simple 'Get(other)
    [+-offset];' ties) are plotted; anything referencing an external prm
    or a more complex equation is skipped with a note, not guessed at.
  - Bonds are a simple distance-cutoff heuristic (sum of covalent radii
    x --bond-tolerance) restricted to DIFFERENT-element pairs, not a real
    bonding/valence analysis -- same-element pairs are never bonded, since
    that mostly just draws a cluttered same-element sublattice network
    (e.g. Ce-Ce in fluorite CeO2) rather than anything chemically useful.

Usage:
    python3 plot_str_3d.py file.inp                # writes file_str3d.html next to the input
    python3 plot_str_3d.py file.inp -o out.html
    python3 plot_str_3d.py file.inp --phase 2       # pick the Nth str block (1-indexed) if more than one
    python3 plot_str_3d.py file.inp --no-bonds
    python3 plot_str_3d.py file.inp --bond-tolerance 1.3
"""

import sys
import os
import re
import json
import math
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import check_inp_syntax as cis
import symmetry_utils
from expand_inp_macros import parse_call_args


# ---------------------------------------------------------------------------
# Element table: symbol -> (color_hex, covalent_radius_angstrom)
# Approximate Jmol/CPK-style colors + Cordero-style covalent radii. A
# visual aid, not a scientific reference.
# ---------------------------------------------------------------------------
ELEMENT_TABLE = {
    "H": ("#FFFFFF", 0.31), "He": ("#D9FFFF", 0.28),
    "Li": ("#CC80FF", 1.28), "Be": ("#C2FF00", 0.96),
    "B": ("#FFB5B5", 0.84), "C": ("#909090", 0.76),
    "N": ("#3050F8", 0.71), "O": ("#FF0D0D", 0.66),
    "F": ("#90E050", 0.57), "Ne": ("#B3E3F5", 0.58),
    "Na": ("#AB5CF2", 1.66), "Mg": ("#8AFF00", 1.41),
    "Al": ("#BFA6A6", 1.21), "Si": ("#F0C8A0", 1.11),
    "P": ("#FF8000", 1.07), "S": ("#FFFF30", 1.05),
    "Cl": ("#1FF01F", 1.02), "Ar": ("#80D1E3", 1.06),
    "K": ("#8F40D4", 2.03), "Ca": ("#3DFF00", 1.76),
    "Sc": ("#E6E6E6", 1.70), "Ti": ("#BFC2C7", 1.60),
    "V": ("#A6A6AB", 1.53), "Cr": ("#8A99C7", 1.39),
    "Mn": ("#9C7AC7", 1.39), "Fe": ("#E06633", 1.32),
    "Co": ("#F090A0", 1.26), "Ni": ("#50D050", 1.24),
    "Cu": ("#C88033", 1.32), "Zn": ("#7D80B0", 1.22),
    "Ga": ("#C28F8F", 1.22), "Ge": ("#668F8F", 1.20),
    "As": ("#BD80E3", 1.19), "Se": ("#FFA100", 1.20),
    "Br": ("#A62929", 1.20), "Kr": ("#5CB8D1", 1.16),
    "Rb": ("#702EB0", 2.20), "Sr": ("#00FF00", 1.95),
    "Y": ("#94FFFF", 1.90), "Zr": ("#94E0E0", 1.75),
    "Nb": ("#73C2C9", 1.64), "Mo": ("#54B5B5", 1.54),
    "Tc": ("#3B9E9E", 1.47), "Ru": ("#248F8F", 1.46),
    "Rh": ("#0A7D8C", 1.42), "Pd": ("#006985", 1.39),
    "Ag": ("#C0C0C0", 1.45), "Cd": ("#FFD98F", 1.44),
    "In": ("#A67573", 1.42), "Sn": ("#668080", 1.39),
    "Sb": ("#9E63B5", 1.39), "Te": ("#D47FFF", 1.38),
    "I": ("#940094", 1.39), "Xe": ("#429EB0", 1.40),
    "Cs": ("#57178F", 2.44), "Ba": ("#00C900", 2.15),
    "La": ("#70D4FF", 2.07), "Ce": ("#FFFFC7", 2.04),
    "Pr": ("#D9FFC7", 2.03), "Nd": ("#C7FFC7", 2.01),
    "Sm": ("#8FFFC7", 1.98), "Eu": ("#61FFC7", 1.98),
    "Gd": ("#45FFC7", 1.96), "Tb": ("#30FFC7", 1.94),
    "Dy": ("#1FFFC7", 1.92), "Ho": ("#00FF9C", 1.92),
    "Er": ("#00E675", 1.89), "Tm": ("#00D452", 1.90),
    "Yb": ("#00BF38", 1.87), "Lu": ("#00AB24", 1.87),
    "Hf": ("#4DC2FF", 1.75), "Ta": ("#4DA6FF", 1.70),
    "W": ("#2194D6", 1.62), "Re": ("#267DAB", 1.51),
    "Os": ("#266696", 1.44), "Ir": ("#175487", 1.41),
    "Pt": ("#D0D0E0", 1.36), "Au": ("#FFD123", 1.36),
    "Hg": ("#B8B8D0", 1.32), "Tl": ("#A6544D", 1.45),
    "Pb": ("#575961", 1.46), "Bi": ("#9E4FB5", 1.48),
    "Th": ("#00BAFF", 2.06), "U": ("#008FFF", 1.96),
}
DEFAULT_ELEMENT = ("#B0B0B0", 0.90)

ELEMENT_SYMBOL_RE = re.compile(r"\bocc\s+([A-Za-z]{1,2})")

LATTICE_MACRO_ARGS = {"Cubic": 1, "Tetragonal": 2, "Hexagonal": 2, "Trigonal": 2, "Rhombohedral": 2}


# ---------------------------------------------------------------------------
# Cell parameter resolution
# ---------------------------------------------------------------------------

def _numeric_from_arg(arg):
    """Extract the trailing numeric token from a macro argument like
    '@ 10.820412', '!name 5.4', or a bare '5.4' -- the value is always
    the last whitespace-separated token in these built-in lattice macros."""
    toks = arg.strip().split()
    if not toks:
        return None
    try:
        return float(toks[-1])
    except ValueError:
        return None


def _resolve_direct_form(form, known):
    """Like resolve_site_coordinates's per-coordinate logic, but for a
    single a/b/c/al/be/ga keyword: returns a float or None."""
    if form is None:
        return None
    if form[0] == "value":
        return form[2]
    if form[0] == "equation":
        plain = cis.parse_plain_numeric_equation(form[1])
        if plain is not None:
            return plain
        tie_m = cis.GET_TIE_RE.match(form[1])
        if tie_m:
            other = tie_m.group("name")
            if other in known:
                return cis.get_tie_value(tie_m, known[other])
    return None


def extract_cell_params(preamble):
    """Returns (a, b, c, al, be, ga) in Angstrom/degrees, or None if the
    cell can't be resolved from this preamble."""
    macro_m = re.search(r"\b(Cubic|Tetragonal|Hexagonal|Trigonal|Rhombohedral)\s*\(", preamble)
    if macro_m:
        name = macro_m.group(1)
        paren_idx = macro_m.end() - 1
        args, _ = parse_call_args(preamble, paren_idx)
        vals = [_numeric_from_arg(a) for a in args]
        if any(v is None for v in vals[:LATTICE_MACRO_ARGS[name]]):
            return None
        if name == "Cubic":
            a = vals[0]
            return a, a, a, 90.0, 90.0, 90.0
        if name == "Tetragonal":
            a, c = vals[0], vals[1]
            return a, a, c, 90.0, 90.0, 90.0
        if name in ("Hexagonal", "Trigonal"):
            a, c = vals[0], vals[1]
            return a, a, c, 90.0, 90.0, 120.0
        if name == "Rhombohedral":
            a, al = vals[0], vals[1]
            return a, a, a, al, al, al
        return None

    known = {}
    # Resolve in an order where a direct 'a' is available before any
    # 'b'/'c' tie referencing it is processed (two passes is sufficient --
    # these ties never chain further than one hop in practice).
    for _round in range(2):
        for kw in ("a", "b", "c", "al", "be", "ga"):
            if kw in known:
                continue
            form = cis.extract_keyword_form(preamble, kw)
            v = _resolve_direct_form(form, known)
            if v is not None:
                known[kw] = v
    if "a" not in known:
        return None
    a = known["a"]
    b = known.get("b", a)
    c = known.get("c", a)
    al = known.get("al", 90.0)
    be = known.get("be", 90.0)
    ga = known.get("ga", 90.0)
    return a, b, c, al, be, ga


def cell_matrix(a, b, c, al, be, ga):
    """Standard triclinic fractional->Cartesian matrix (a along x)."""
    al_r, be_r, ga_r = math.radians(al), math.radians(be), math.radians(ga)
    cos_al, cos_be, cos_ga = math.cos(al_r), math.cos(be_r), math.cos(ga_r)
    sin_ga = math.sin(ga_r)
    v_sq = 1 - cos_al ** 2 - cos_be ** 2 - cos_ga ** 2 + 2 * cos_al * cos_be * cos_ga
    v = math.sqrt(max(v_sq, 0.0))
    m00, m01, m02 = a, b * cos_ga, c * cos_be
    m10, m11, m12 = 0.0, b * sin_ga, c * (cos_al - cos_be * cos_ga) / sin_ga
    m20, m21, m22 = 0.0, 0.0, c * v / sin_ga
    return ((m00, m01, m02), (m10, m11, m12), (m20, m21, m22))


def frac_to_cart(m, p):
    (m00, m01, m02), (m10, m11, m12), (m20, m21, m22) = m
    x, y, z = p
    return (
        m00 * x + m01 * y + m02 * z,
        m10 * x + m11 * y + m12 * z,
        m20 * x + m21 * y + m22 * z,
    )


# ---------------------------------------------------------------------------
# Site / symmetry expansion
# ---------------------------------------------------------------------------

def element_for_site(site_slice):
    m = ELEMENT_SYMBOL_RE.search(site_slice)
    if not m:
        return None
    sym = m.group(1)
    if sym in ELEMENT_TABLE:
        return sym
    sym1 = sym[:1]
    return sym1 if sym1 in ELEMENT_TABLE else sym


NEAR_ZERO_TOL = 1e-3


def expand_site_orbit(point, symops, tol=1e-4):
    """All symmetry-equivalent points of `point` reduced into [0,1), plus
    boundary-mirrored duplicates (a coordinate ~0 also gets a copy at ~1)
    so the unit cell box looks visually complete."""
    seen = []
    for rows, translation in symops:
        img = symmetry_utils.apply_symop(rows, translation, point)
        img = tuple(symmetry_utils.mod1(v) for v in img)
        if not any(symmetry_utils.points_equal_mod1(img, s, tol) for s in seen):
            seen.append(img)

    expanded = []
    for p in seen:
        near_zero_axes = [i for i in range(3) if p[i] < NEAR_ZERO_TOL or p[i] > 1 - NEAR_ZERO_TOL]
        base = [0.0 if p[i] < NEAR_ZERO_TOL or p[i] > 1 - NEAR_ZERO_TOL else p[i] for i in range(3)]
        variants = [list(base)]
        for axis in near_zero_axes:
            new_variants = []
            for v in variants:
                for val in (0.0, 1.0):
                    nv = list(v)
                    nv[axis] = val
                    new_variants.append(nv)
            variants = new_variants
        for v in variants:
            expanded.append(tuple(v))
    # de-dup exact (post-mirroring) duplicates
    uniq = []
    for p in expanded:
        if not any(all(abs(p[i] - q[i]) < 1e-6 for i in range(3)) for q in uniq):
            uniq.append(p)
    return uniq


def gather_atoms(inp_path, phase_index, warnings):
    with open(inp_path, encoding="utf-8") as f:
        raw = f.read()
    clean_text = cis.strip_comments_and_strings(raw)
    values_text = cis.strip_comments_only(raw)

    str_blocks = cis.find_str_blocks(clean_text)
    if not str_blocks:
        raise SystemExit("No 'str' phase block found in this file.")
    if phase_index < 1 or phase_index > len(str_blocks):
        raise SystemExit(f"--phase {phase_index} is out of range (this file has {len(str_blocks)} str block(s)).")
    content_start, content_end = str_blocks[phase_index - 1]
    if len(str_blocks) > 1:
        warnings.append(f"File has {len(str_blocks)} str blocks; showing phase {phase_index} "
                         f"(use --phase N to pick another).")

    block_clean = clean_text[content_start:content_end]
    block_values = values_text[content_start:content_end]

    sg_m = re.search(r"\bspace_group\b\s*(\"[^\"]*\"|\S+)", block_values)
    if not sg_m:
        raise SystemExit("This str block has no space_group -- can't determine symmetry.")
    symbol = sg_m.group(1).strip('"')

    symops, _header, msg = symmetry_utils.resolve_sg_operators(symbol)
    if not symops:
        raise SystemExit(f"Could not resolve symmetry operators for space_group {symbol!r}: {msg}")

    first_site_m = re.search(r"\bsite\b", block_clean)
    preamble_end = first_site_m.start() if first_site_m else len(block_clean)
    preamble = block_clean[:preamble_end]

    cell = extract_cell_params(preamble)
    if cell is None:
        raise SystemExit("Could not resolve this str block's cell parameters (a/b/c/al/be/ga or a "
                          "Cubic/Tetragonal/Hexagonal/Trigonal/Rhombohedral macro).")
    a, b, c, al, be, ga = cell
    m = cell_matrix(a, b, c, al, be, ga)

    str_scope = cis.resolve_str_scope_values(preamble)
    sites_clean = cis.find_sites(block_clean)
    sites_values = cis.find_sites(block_values)
    atoms = []
    for (name, slice_clean, _pos), (_n2, slice_values, _p2) in zip(sites_clean, sites_values):
        point, _forms = cis.resolve_site_coordinates(slice_clean, outer_known=str_scope)
        if point is None:
            warnings.append(f"Site '{name}': x/y/z didn't resolve to concrete numbers -- skipped.")
            continue
        element = element_for_site(slice_values)
        if element is None:
            warnings.append(f"Site '{name}': couldn't parse an element from its 'occ' -- shown as unknown.")
            element = "X"
        for frac in expand_site_orbit(point, symops):
            cart = frac_to_cart(m, frac)
            atoms.append({"label": name, "element": element, "frac": frac, "cart": cart})

    if not atoms:
        raise SystemExit("No plottable atoms found in this str block (see warnings).")

    corners = []
    for ix in (0, 1):
        for iy in (0, 1):
            for iz in (0, 1):
                corners.append(frac_to_cart(m, (float(ix), float(iy), float(iz))))

    return atoms, corners, symbol, (a, b, c, al, be, ga), phase_index, len(str_blocks)


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

CELL_EDGES = [
    (0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3),
    (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7),
]

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title} &middot; str viewer</title>
<style>
  :root {{
    --bg: #0a0d13;
    --panel: rgba(17, 21, 30, 0.82);
    --panel-border: #262e3d;
    --text: #ece8e0;
    --text-muted: #8992a6;
    --accent: #dfa458;
    --edge: rgba(140, 158, 216, 0.55);
    color-scheme: dark;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; height: 100%; background: var(--bg); overflow: hidden; }}
  body {{
    color: var(--text);
    font-family: ui-monospace, "SF Mono", "Cascadia Code", "Consolas", "Liberation Mono", monospace;
  }}
  #wrap {{ position: relative; width: 100%; height: 100%; }}
  canvas {{ display: block; width: 100%; height: 100%; cursor: grab; touch-action: none; }}
  canvas:active {{ cursor: grabbing; }}

  .panel {{
    position: absolute;
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    padding: 14px 16px;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
  }}
  .eyebrow {{
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 8px;
  }}
  #hud {{ top: 16px; left: 16px; min-width: 232px; pointer-events: none; }}
  #hud h1 {{
    font-family: system-ui, -apple-system, "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 15px;
    font-weight: 600;
    margin: 0 0 12px;
    color: var(--text);
    text-wrap: balance;
    word-break: break-word;
  }}
  .kv {{ display: grid; grid-template-columns: auto 1fr; gap: 4px 14px; margin: 0; font-size: 12px; font-variant-numeric: tabular-nums; }}
  .kv dt {{ color: var(--text-muted); }}
  .kv dd {{ margin: 0; text-align: right; }}

  #legend {{ bottom: 16px; left: 16px; }}
  #legend .row {{ display: flex; align-items: center; gap: 8px; font-size: 12px; padding: 2px 0; }}
  .swatch {{ width: 10px; height: 10px; border-radius: 50%; flex: none; box-shadow: 0 0 0 1px rgba(0,0,0,0.4) inset; }}

  #hint {{
    bottom: 16px; right: 16px; padding: 8px 12px;
    font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted);
  }}
  #controls {{
    bottom: 16px; left: 50%; transform: translateX(-50%);
    display: flex; align-items: center; gap: 10px; padding: 8px 14px;
  }}
  #controls label {{
    font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted);
  }}
  #controls input[type="range"] {{ accent-color: var(--accent); width: 130px; }}
  #controls output {{ font-size: 11px; color: var(--text); min-width: 2.4em; text-align: right; font-variant-numeric: tabular-nums; }}
  #controls .sep {{ width: 1px; align-self: stretch; background: var(--panel-border); }}
  #controls .check {{ display: flex; align-items: center; gap: 6px; }}
  #controls input[type="checkbox"] {{ accent-color: var(--accent); width: 13px; height: 13px; }}
  @media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
</style>
</head>
<body>
<div id="wrap">
  <canvas id="c"></canvas>
  <div id="hud" class="panel">
    <p class="eyebrow">Structure &middot; phase {phase_index} of {phase_total}</p>
    <h1>{title}</h1>
    <dl class="kv">
      <dt>space group</dt><dd>{symbol}</dd>
      <dt>a, b, c</dt><dd>{a:.4f}, {b:.4f}, {c:.4f} &Aring;</dd>
      <dt>&alpha;, &beta;, &gamma;</dt><dd>{al:.2f}&deg;, {be:.2f}&deg;, {ga:.2f}&deg;</dd>
      <dt>atoms shown</dt><dd>{n_atoms}</dd>
    </dl>
  </div>
  <div id="legend" class="panel">
    <p class="eyebrow">Elements</p>
    {legend_html}
  </div>
  <div id="hint" class="panel">drag to orbit &middot; scroll to zoom</div>
  <div id="controls" class="panel">
    <label for="perspRange">perspective</label>
    <input type="range" id="perspRange" min="0" max="0.05" step="0.001" value="0.012">
    <output id="perspOut">0.012</output>
    <div class="sep"></div>
    <div class="check">
      <input type="checkbox" id="labelsCheck">
      <label for="labelsCheck">site labels</label>
    </div>
  </div>
</div>
<script>
const ATOMS = {atoms_json};
const EDGES = {edges_json};
const CORNERS = {corners_json};
const BONDS = {bonds_json};

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
function resize() {{
  canvas.width = canvas.clientWidth * devicePixelRatio;
  canvas.height = canvas.clientHeight * devicePixelRatio;
}}
window.addEventListener('resize', resize);
resize();

let rotX = -0.5, rotY = 0.6, zoom = 1.0;
let dragging = false, lastX = 0, lastY = 0;
let perspectiveStrength = 0.012;

let showLabels = false;

const perspRange = document.getElementById('perspRange');
const perspOut = document.getElementById('perspOut');
perspRange.addEventListener('input', () => {{
  perspectiveStrength = parseFloat(perspRange.value);
  perspOut.textContent = perspectiveStrength.toFixed(3);
  draw();
}});

const labelsCheck = document.getElementById('labelsCheck');
labelsCheck.addEventListener('change', () => {{
  showLabels = labelsCheck.checked;
  draw();
}});

canvas.addEventListener('pointerdown', e => {{ dragging = true; lastX = e.clientX; lastY = e.clientY; canvas.setPointerCapture(e.pointerId); }});
canvas.addEventListener('pointerup', () => dragging = false);
canvas.addEventListener('pointercancel', () => dragging = false);
canvas.addEventListener('pointermove', e => {{
  if (!dragging) return;
  const dx = e.clientX - lastX, dy = e.clientY - lastY;
  lastX = e.clientX; lastY = e.clientY;
  rotY += dx * 0.008;
  rotX += dy * 0.008;
  draw();
}});
canvas.addEventListener('wheel', e => {{
  e.preventDefault();
  zoom *= Math.pow(1.001, -e.deltaY);
  zoom = Math.max(0.15, Math.min(zoom, 8));
  draw();
}}, {{ passive: false }});

function rotate(p) {{
  let [x, y, z] = p;
  let cy = Math.cos(rotY), sy = Math.sin(rotY);
  let x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
  let cx = Math.cos(rotX), sx = Math.sin(rotX);
  let y2 = y * cx - z1 * sx, z2 = y * sx + z1 * cx;
  return [x1, y2, z2];
}}

function project(p) {{
  const scale = Math.min(canvas.width, canvas.height) * 0.16 * zoom;
  const persp = 1 / (1 + p[2] * perspectiveStrength);
  return [
    canvas.width / 2 + p[0] * scale * persp,
    canvas.height / 2 - p[1] * scale * persp,
    p[2],
    persp,
  ];
}}

function centerOf(pts) {{
  let cx = 0, cy = 0, cz = 0;
  for (const p of pts) {{ cx += p[0]; cy += p[1]; cz += p[2]; }}
  return [cx / pts.length, cy / pts.length, cz / pts.length];
}}
const CENTER = centerOf(CORNERS.length ? CORNERS : ATOMS.map(a => a.cart));

function draw() {{
  ctx.fillStyle = '#0a0d13';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const rotPt = p => rotate([p[0] - CENTER[0], p[1] - CENTER[1], p[2] - CENTER[2]]);
  const cornersR = CORNERS.map(rotPt);
  const cornersP = cornersR.map(project);

  ctx.strokeStyle = 'rgba(140,158,216,0.55)';
  ctx.lineWidth = 1.4 * devicePixelRatio;
  for (const [i, j] of EDGES) {{
    ctx.beginPath();
    ctx.moveTo(cornersP[i][0], cornersP[i][1]);
    ctx.lineTo(cornersP[j][0], cornersP[j][1]);
    ctx.stroke();
  }}

  const atomsR = ATOMS.map(a => ({{ ...a, rot: rotPt(a.cart) }}));

  const drawables = [];
  for (const [ai, bi] of BONDS) {{
    const a = atomsR[ai], b = atomsR[bi];
    const depth = (a.rot[2] + b.rot[2]) / 2;
    drawables.push({{ type: 'bond', depth, a, b }});
  }}
  for (const a of atomsR) {{
    drawables.push({{ type: 'atom', depth: a.rot[2], a }});
  }}
  drawables.sort((p, q) => p.depth - q.depth);

  for (const d of drawables) {{
    if (d.type === 'bond') {{
      const pa = project(d.a.rot), pb = project(d.b.rot);
      const mx = (pa[0] + pb[0]) / 2, my = (pa[1] + pb[1]) / 2;
      ctx.lineWidth = 2.2 * devicePixelRatio * ((pa[3] + pb[3]) / 2);
      ctx.strokeStyle = d.a.color;
      ctx.beginPath(); ctx.moveTo(pa[0], pa[1]); ctx.lineTo(mx, my); ctx.stroke();
      ctx.strokeStyle = d.b.color;
      ctx.beginPath(); ctx.moveTo(mx, my); ctx.lineTo(pb[0], pb[1]); ctx.stroke();
    }} else {{
      const p = project(d.a.rot);
      const r = d.a.radius * Math.min(canvas.width, canvas.height) * 0.075 * zoom * p[3];
      const grad = ctx.createRadialGradient(p[0] - r * 0.35, p[1] - r * 0.35, r * 0.1, p[0], p[1], r);
      grad.addColorStop(0, '#ffffff');
      grad.addColorStop(0.25, d.a.color);
      grad.addColorStop(1, d.a.color);
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p[0], p[1], Math.max(r, 1), 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = 'rgba(0,0,0,0.35)';
      ctx.lineWidth = 1 * devicePixelRatio;
      ctx.stroke();

      if (showLabels) {{
        const fontPx = 11 * devicePixelRatio;
        ctx.font = `600 ${{fontPx}}px ui-monospace, "SF Mono", Consolas, monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.lineWidth = 3 * devicePixelRatio;
        ctx.strokeStyle = 'rgba(10,13,19,0.85)';
        ctx.strokeText(d.a.label, p[0], p[1]);
        ctx.fillStyle = '#f5f2ea';
        ctx.fillText(d.a.label, p[0], p[1]);
      }}
    }}
  }}
}}

draw();
</script>
</body>
</html>
"""


def build_html(atoms, corners, bonds, symbol, cell, title, phase_index, phase_total):
    a, b, c, al, be, ga = cell
    elements_used = sorted(set(atom["element"] for atom in atoms))
    legend_html = "".join(
        f'<div class="row"><span class="swatch" style="background:{ELEMENT_TABLE.get(el, DEFAULT_ELEMENT)[0]}"></span>{el}</div>'
        for el in elements_used
    )
    atoms_json = json.dumps([
        {
            "label": atom["label"],
            "element": atom["element"],
            "cart": list(atom["cart"]),
            "color": ELEMENT_TABLE.get(atom["element"], DEFAULT_ELEMENT)[0],
            "radius": ELEMENT_TABLE.get(atom["element"], DEFAULT_ELEMENT)[1],
        }
        for atom in atoms
    ])
    corners_json = json.dumps([list(p) for p in corners])
    edges_json = json.dumps(CELL_EDGES)
    bonds_json = json.dumps(bonds)
    return HTML_TEMPLATE.format(
        title=title, symbol=symbol, a=a, b=b, c=c, al=al, be=be, ga=ga,
        n_atoms=len(atoms), phase_index=phase_index, phase_total=phase_total,
        legend_html=legend_html, atoms_json=atoms_json, corners_json=corners_json,
        edges_json=edges_json, bonds_json=bonds_json,
    )


def compute_bonds(atoms, tolerance):
    """
    Only bonds atoms of DIFFERENT elements (e.g. cation-anion in an oxide/
    mineral structure). A same-element covalent-radius-sum cutoff tends to
    also connect same-element near-neighbors in ionic/metallic sublattices
    (Ce-Ce in fluorite CeO2, say) that aren't a "bond" in any useful visual
    sense and just clutter the render -- confirmed directly: allowing
    same-element pairs on a real CeO2 test file produced 496 bonds (mostly
    Ce-Ce/O-O) vs. a much more legible cation-anion-only result.
    """
    bonds = []
    n = len(atoms)
    for i in range(n):
        ri = ELEMENT_TABLE.get(atoms[i]["element"], DEFAULT_ELEMENT)[1]
        xi, yi, zi = atoms[i]["cart"]
        for j in range(i + 1, n):
            if atoms[i]["element"] == atoms[j]["element"]:
                continue
            rj = ELEMENT_TABLE.get(atoms[j]["element"], DEFAULT_ELEMENT)[1]
            xj, yj, zj = atoms[j]["cart"]
            d2 = (xi - xj) ** 2 + (yi - yj) ** 2 + (zi - zj) ** 2
            cutoff = (ri + rj) * tolerance
            if d2 <= cutoff * cutoff and d2 > 1e-6:
                bonds.append((i, j))
    return bonds


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inp_file")
    parser.add_argument("-o", "--output", help="write HTML to this path instead of <input>_str3d.html")
    parser.add_argument("--phase", type=int, default=1, help="1-indexed str block to plot if the file has more than one (default 1)")
    parser.add_argument("--no-bonds", action="store_true", help="skip bond rendering")
    parser.add_argument("--bond-tolerance", type=float, default=1.2, help="bond cutoff = (covalent radius sum) x this factor (default 1.2)")
    args = parser.parse_args()

    warnings = []
    atoms, corners, symbol, cell, phase_index, phase_total = gather_atoms(args.inp_file, args.phase, warnings)
    bonds = [] if args.no_bonds else compute_bonds(atoms, args.bond_tolerance)

    title = os.path.basename(args.inp_file)
    html = build_html(atoms, corners, bonds, symbol, cell, title, phase_index, phase_total)

    out_path = args.output or (os.path.splitext(args.inp_file)[0] + "_str3d.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    for w in warnings:
        print(f"Note: {w}", file=sys.stderr)
    print(f"{len(atoms)} atoms, {len(bonds)} bonds. Written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
