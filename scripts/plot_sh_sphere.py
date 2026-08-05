#!/usr/bin/env python3
"""Render a `spherical_harmonics_hkl` series from a TOPAS .inp as an
interactive 3D pole figure (self-contained HTML, no dependencies).

*** NOT EXTENSIVELY TESTED -- verify anything you rely on. Also shown on
*** the page.

Values are never re-derived here: harmonic conventions differ between
sources, so a hand-built basis can look right yet be wrong. Instead tc.exe
runs at `iters 0` on a scratch copy with
Create_hklm_d_Th2_Ip_file(<file>, <name>), inheriting TOPAS's convention
exactly. Cost: the series is only sampled where reflections exist.

General for all space groups/settings, no Laue class hardcoded:
    direction  d*_cart = (A^-1)^T . (h,k,l), normalized   (A = cell_matrix)
    orbit      R_cart = A . R_frac . A^-1, unioned with its negatives
Working in Cartesian makes R_cart a true rotation, so no convention need be
chosen for how Miller indices transform -- the likeliest silent error.
Operators from symmetry_utils.resolve_sg_operators() (TOPAS's database).

Two self-checks run every invocation: |B.hkl| must equal 1/d (TOPAS reports
d alongside, so this validates the metric for any cell with no reference
values); and two families on one direction with different values means the
Laue group was too big. Both warn, never silently average.

Dots are raw -- one per direction TOPAS evaluated. --surface interpolates
an icosphere mesh between them, so a smooth patch in a sparse gap is an
artifact; sampling density is warned on above ~12 deg separation.

Page toggles: radius proportional to value (on), dots, surface,
iso-contours, reciprocal triad (on), unit cell + direct triad (off). Both
triads differ for non-cubic cells. The cell aids reading a texture
direction (R31); the plot is directions, not positions.

Usage:
    python3 plot_sh_sphere.py file.inp
    python3 plot_sh_sphere.py file.inp --surface
    python3 plot_sh_sphere.py file.inp --phase 2 -o texture.html
    python3 plot_sh_sphere.py file.inp --surface --mesh-level 4
"""

import sys
import os
import re
import json
import math
import shutil
import argparse
import tempfile
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import check_inp_syntax as cis
import symmetry_utils
import remove_errors
import topas_install
from plot_str_3d import (
    extract_cell_params,
    cell_matrix,
    mat3_mul,
    mat3_inverse,
    mat3_transpose,
)


# ---------------------------------------------------------------------------
# Locating the harmonics series in the file
# ---------------------------------------------------------------------------

# PO_Spherical_Harmonics expands to spherical_harmonics_hkl, and a file
# with its .out copied back carries the expanded form -- so match either.
PO_MACRO_RE = re.compile(r"\bPO_Spherical_Harmonics\s*\(\s*([A-Za-z_]\w*)?\s*,")
SH_KEYWORD_RE = re.compile(r"\bspherical_harmonics_hkl\s+([A-Za-z_]\w*)")


def find_sh_name(block_clean):
    """Return (name, how_found) for the harmonics series in this str block,
    or (None, reason) if there isn't one we can address by name."""
    m = SH_KEYWORD_RE.search(block_clean)
    if m:
        return m.group(1), "spherical_harmonics_hkl"
    m = PO_MACRO_RE.search(block_clean)
    if m:
        if m.group(1):
            return m.group(1), "PO_Spherical_Harmonics"
        return None, (
            "This phase uses the anonymous PO_Spherical_Harmonics(, order) form, whose "
            "series name is auto-generated internally by the macro and cannot be "
            "referenced from an output statement. Give it an explicit name -- e.g. "
            "PO_Spherical_Harmonics(sh, 6) -- and re-run."
        )
    return None, (
        "No spherical_harmonics_hkl / PO_Spherical_Harmonics found in this phase. "
        "This script plots an existing fitted harmonics series; add one and refine "
        "it first."
    )


# ---------------------------------------------------------------------------
# Asking TOPAS for the series' value at every reflection
# ---------------------------------------------------------------------------

def _find_tc():
    root, found = topas_install.get_topas_dir()
    if found:
        for exe in ("tc.exe", "TC.EXE", "tc"):
            p = os.path.join(root, exe)
            if os.path.exists(p):
                return p
    raise SystemExit(
        "Could not locate tc.exe -- set TOPAS_DIR to your TOPAS install root. "
        "This script needs a real TOPAS run to evaluate the harmonics series."
    )


def _rewrite_xdd_paths(text, data_dir):
    """Make relative data-file paths absolute so a scratch copy run from a
    temp directory still finds the pattern (TOPAS resolves a relative xdd
    path against the .inp's own directory)."""
    def repl(m):
        kw, quote, path = m.group(1), m.group(2) or "", m.group(3)
        if os.path.isabs(path):
            return m.group(0)
        return f'{kw} "{os.path.join(data_dir, path)}"'
    return re.sub(
        r'\b(xdd|xdd_scr)\s+(")?([^\s"\n]+)(?(2)")',
        repl, text,
    )


OUTPUT_NAMES = (
    "Out_X_Yobs", "Out_X_Ycalc", "Out_X_Difference", "Out_X_Ycalc_Ydiff",
    "Create_hklm_d_Th2_Ip_file", "Create_hklm_d_Th2_IScaled_file",
    "Create_2Th_Ip_file", "Create_2Th_IScaled_file", "Create_d_Ip_file",
    "Create_d_IScaled_file", "Out_CIF_STR", "Out_CIF_ADPs", "Out_pdCIF",
    "Out_FCF", "Out_Prm_Vals", "Out_XDD_xy", "Out_XDD_Start_Step",
    # raw keyword forms, which carry a `load ... { ... }` body
    "xdd_out", "phase_out", "out",
)


def _strip_output_macros(text):
    """Remove output-writing statements from the scratch copy: a relative
    output path would resolve against the temp dir and abort the run, an
    absolute one would clobber the real refinement's files. The raw
    xdd_out/phase_out/out forms carry a `{ }` body, so consume through the
    matching brace rather than just the first line.
    """
    lines = text.split("\n")
    out_lines = []
    i = 0
    while i < len(lines):
        stripped = lines[i].lstrip()
        matched = any(stripped.startswith(n + "(") or stripped.startswith(n + " ")
                      or stripped == n for n in OUTPUT_NAMES)
        if not matched:
            out_lines.append(lines[i])
            i += 1
            continue
        # Consume this statement, including any brace body that opens on
        # this line or on following lines before any other statement.
        depth = lines[i].count("{") - lines[i].count("}")
        i += 1
        while depth > 0 and i < len(lines):
            depth += lines[i].count("{") - lines[i].count("}")
            i += 1
    return "\n".join(out_lines)


def run_topas_for_sh(inp_path, sh_name, phase_index, keep_scratch=False):
    """Build a scratch `iters 0` copy that dumps H K L M d 2th <sh> for the
    chosen phase, run tc.exe, and return the parsed rows."""
    tc = _find_tc()
    src_dir = os.path.dirname(os.path.abspath(inp_path))
    with open(inp_path, encoding="utf-8") as f:
        raw = f.read()

    # Refined-value error suffixes parse fine in TOPAS itself, so they are
    # left alone here -- unlike the plotting path, this text goes back to
    # TOPAS rather than to our own number parser.
    text = _strip_output_macros(raw)
    text = _rewrite_xdd_paths(text, src_dir)

    # Force a no-refinement evaluation: we want the file's own already-fitted
    # coefficients reported back, not a fresh fit.
    text = re.sub(r"^\s*iters\s+\d+\s*$", "iters 0", text, flags=re.MULTILINE)
    if not re.search(r"^\s*iters\s+0\s*$", text, flags=re.MULTILINE):
        text = "iters 0\n" + text
    # do_errors triples the runtime and we only want reported values.
    text = re.sub(r"^\s*do_errors\s*$", "", text, flags=re.MULTILINE)

    tmpdir = tempfile.mkdtemp(prefix="sh_sphere_")
    out_txt = os.path.join(tmpdir, "sh_values.txt")
    scratch = os.path.join(tmpdir, "sh_probe.inp")

    # Offsets from `clean` index `text` directly because
    # strip_comments_and_strings is length-preserving (blanks in place
    # rather than deleting) -- same assumption as plot_str_3d.py. `clean`
    # comes from the already-rewritten `text`, so the two stay in step.
    clean = cis.strip_comments_and_strings(text)
    blocks = cis.find_str_blocks(clean)
    if not blocks:
        raise SystemExit("No 'str' phase block found in this file.")
    if phase_index < 1 or phase_index > len(blocks):
        raise SystemExit(
            f"--phase {phase_index} is out of range (this file has {len(blocks)} str block(s))."
        )
    _content_start, content_end = blocks[phase_index - 1]
    emit = f'\n   Create_hklm_d_Th2_Ip_file("{out_txt}", {sh_name})\n'
    text = text[:content_end] + emit + text[content_end:]

    with open(scratch, "w", encoding="utf-8") as f:
        f.write(text)

    proc = subprocess.run([tc, scratch], capture_output=True, text=True)
    if not os.path.exists(out_txt):
        tail = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()][-6:]
        detail = "\n    ".join(tail) if tail else "(tc.exe produced no output)"
        raise SystemExit(
            "TOPAS did not produce the hkl/sh file. Its last output was:\n    "
            + detail
            + f"\n\nScratch file kept for inspection: {scratch}"
        )

    rows = []
    with open(out_txt, encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 7:
                continue
            try:
                h, k, l = int(parts[0]), int(parts[1]), int(parts[2])
                d_spacing = float(parts[4])
                two_th = float(parts[5])
                sh = float(parts[6])
            except ValueError:
                continue
            rows.append((h, k, l, two_th, sh, d_spacing))

    if not keep_scratch:
        shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        print(f"Scratch kept: {tmpdir}", file=sys.stderr)

    if not rows:
        raise SystemExit("TOPAS produced the hkl file but it had no parsable rows.")
    return rows


# ---------------------------------------------------------------------------
# hkl -> Cartesian direction, and the Cartesian Laue group
# ---------------------------------------------------------------------------

def reciprocal_basis_cart(cell):
    """B = (A^-1)^T -- columns are a*, b*, c* in Cartesian. d*_cart = B.(h,k,l)."""
    a, b, c, al, be, ga = cell
    A = cell_matrix(a, b, c, al, be, ga)
    A_inv = mat3_inverse(A)
    if A_inv is None:
        raise SystemExit("Cell matrix is singular -- check the cell parameters.")
    return A, A_inv, mat3_transpose(A_inv)


CELL_EDGES = [
    (0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3),
    (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7),
]


def cell_geometry(A, B, clearance=1.38):
    """Direct-cell wireframe + both axis triads, centred and scaled so the
    surface sits inside the box. Centre-to-(100)-face distance is 0.5/|a*|,
    so scaling by s = 2*clearance*max(|a*|,|b*|,|c*|) puts the nearest face
    at `clearance` -- clear of the surface's 1.22 maximum radius.
    """
    cols_A = [(A[0][j], A[1][j], A[2][j]) for j in range(3)]   # a, b, c
    cols_B = [(B[0][j], B[1][j], B[2][j]) for j in range(3)]   # a*, b*, c*
    recip_norms = [math.sqrt(sum(x * x for x in v)) for v in cols_B]
    s = 2.0 * clearance * max(recip_norms)

    corners = []
    for ix in (0, 1):
        for iy in (0, 1):
            for iz in (0, 1):
                f = (ix - 0.5, iy - 0.5, iz - 0.5)
                corners.append([
                    s * (A[0][0] * f[0] + A[0][1] * f[1] + A[0][2] * f[2]),
                    s * (A[1][0] * f[0] + A[1][1] * f[1] + A[1][2] * f[2]),
                    s * (A[2][0] * f[0] + A[2][1] * f[1] + A[2][2] * f[2]),
                ])

    direct_axes = [[s * v[0], s * v[1], s * v[2]] for v in cols_A]
    recip_axes = []
    for v in cols_B:
        n = math.sqrt(sum(x * x for x in v))
        recip_axes.append([v[0] / n, v[1] / n, v[2] / n] if n > 1e-12 else [0, 0, 0])
    return corners, CELL_EDGES, direct_axes, recip_axes


def hkl_to_unit_cart(B, h, k, l):
    v = (
        B[0][0] * h + B[0][1] * k + B[0][2] * l,
        B[1][0] * h + B[1][1] * k + B[1][2] * l,
        B[2][0] * h + B[2][1] * k + B[2][2] * l,
    )
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if n < 1e-12:
        return None
    return (v[0] / n, v[1] / n, v[2] / n)


def cartesian_laue_group(symops, A, A_inv):
    """Rotation parts of the space group, mapped into Cartesian and unioned
    with their negatives (Friedel). Translations are irrelevant to a
    direction and are dropped."""
    seen = {}
    for rows, _translation in symops:
        r_frac = tuple(tuple(float(x) for x in row) for row in rows)
        r_cart = mat3_mul(mat3_mul(A, r_frac), A_inv)
        for sign in (1.0, -1.0):
            m = tuple(tuple(sign * r_cart[i][j] for j in range(3)) for i in range(3))
            key = tuple(round(m[i][j], 6) + 0.0 for i in range(3) for j in range(3))
            if key not in seen:
                seen[key] = m
    return list(seen.values())


def apply_mat(m, v):
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def check_reciprocal_metric(rows, B, warnings, rel_tol=2e-3):
    """|B.(h,k,l)| is the scattering-vector length and must equal 1/d, which
    TOPAS reports in the same file -- so this validates the (A^-1)^T
    transform for any cell with no reference values. A failure means the
    directions are wrong and the plot is untrustworthy.
    """
    worst = 0.0
    worst_hkl = None
    checked = 0
    for (h, k, l, _tt, _sh, d) in rows:
        if d <= 0:
            continue
        v = (
            B[0][0] * h + B[0][1] * k + B[0][2] * l,
            B[1][0] * h + B[1][1] * k + B[1][2] * l,
            B[2][0] * h + B[2][1] * k + B[2][2] * l,
        )
        mag = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
        expected = 1.0 / d
        if expected <= 0:
            continue
        rel = abs(mag - expected) / expected
        checked += 1
        if rel > worst:
            worst, worst_hkl = rel, (h, k, l)
    if checked and worst > rel_tol:
        warnings.append(
            f"RECIPROCAL METRIC CHECK FAILED: |B.hkl| disagrees with TOPAS's own "
            f"d-spacing by up to {worst * 100:.2f}% (worst at hkl {worst_hkl}). The "
            f"plotted directions are probably wrong -- do not trust this figure."
        )
    return worst, checked


def expand_to_sphere(rows, B, laue, warnings, sh_conflict_tol=0.02):
    """Expand every reflection to its full orbit of directions. Returns
    (points, families_used, conflicts) where points is a list of
    (x, y, z, sh, h, k, l)."""
    grid = {}
    conflicts = 0
    families = 0
    for (h, k, l, _two_th, sh, _d) in rows:
        v = hkl_to_unit_cart(B, h, k, l)
        if v is None:
            continue
        families += 1
        for m in laue:
            w = apply_mat(m, v)
            key = (round(w[0], 4) + 0.0, round(w[1], 4) + 0.0, round(w[2], 4) + 0.0)
            prev = grid.get(key)
            if prev is None:
                grid[key] = (w[0], w[1], w[2], sh, h, k, l)
            elif abs(prev[3] - sh) > sh_conflict_tol:
                # Two genuinely different reflection families landing on one
                # direction with different values means the Laue group used
                # was larger than the real one.
                conflicts += 1
    if conflicts:
        warnings.append(
            f"{conflicts} direction(s) received conflicting sh values from different "
            f"reflection families (differing by more than {sh_conflict_tol}). This "
            f"suggests the symmetry expansion over-symmetrized -- the plot may be "
            f"wrong. Please report this along with the space group used."
        )
    return list(grid.values()), families, conflicts


def median_nn_angle_deg(points, sample_cap=400):
    """Median nearest-neighbour angular separation, as a sampling-density
    measure. Sampled rather than exhaustive to stay cheap on large sets."""
    n = len(points)
    if n < 2:
        return None
    step = max(1, n // sample_cap)
    probe = points[::step]
    seps = []
    for p in probe:
        best = -2.0
        for q in points:
            if q is p:
                continue
            d = p[0] * q[0] + p[1] * q[1] + p[2] * q[2]
            if d > best:
                best = d
        best = max(-1.0, min(1.0, best))
        seps.append(math.degrees(math.acos(best)))
    seps.sort()
    return seps[len(seps) // 2]


# ---------------------------------------------------------------------------
# Interpolated surface mesh (only built with --surface)
# ---------------------------------------------------------------------------

def icosphere(level):
    t = (1.0 + math.sqrt(5.0)) / 2.0
    verts = [
        (-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
        (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
        (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1),
    ]
    verts = [_norm(v) for v in verts]
    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]
    for _ in range(level):
        midpoint = {}
        new_faces = []

        def mid(i, j):
            key = (min(i, j), max(i, j))
            if key in midpoint:
                return midpoint[key]
            a, b = verts[i], verts[j]
            m = _norm(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2))
            verts.append(m)
            idx = len(verts) - 1
            midpoint[key] = idx
            return idx

        for (i, j, k) in faces:
            a, b, c = mid(i, j), mid(j, k), mid(k, i)
            new_faces += [(i, a, c), (j, b, a), (k, c, b), (a, b, c)]
        faces = new_faces
    return verts, faces


def _norm(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    return (v[0] / n, v[1] / n, v[2] / n)


def interpolate_to_mesh(verts, points, sigma_deg):
    """Angular-Gaussian-weighted average of the sampled directions at each
    mesh vertex. Because `points` is already symmetry-expanded, the result
    inherits the correct symmetry automatically."""
    sigma = math.radians(max(sigma_deg, 1e-3))
    cutoff_cos = math.cos(min(math.radians(sigma_deg * 3.0), math.pi))
    out = []
    for v in verts:
        num = 0.0
        den = 0.0
        best_d, best_val = -2.0, None
        for p in points:
            d = v[0] * p[0] + v[1] * p[1] + v[2] * p[2]
            if d > best_d:
                best_d, best_val = d, p[3]
            if d < cutoff_cos:
                continue
            ang = math.acos(max(-1.0, min(1.0, d)))
            w = math.exp(-(ang / sigma) ** 2)
            num += w * p[3]
            den += w
        out.append(num / den if den > 1e-12 else best_val)
    return out


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<title>__TITLE__</title>
<style>
  :root{
    --bg:#f4f2ee; --panel:#fff; --ink:#1c1a17; --muted:#6b655c; --rule:#dedad2;
    --blue-far:#0d366b; --blue-mid:#3987e5; --neutral:#f0efec; --red-mid:#e34948; --red-far:#8f1f1f;
    --warn-bg:#fdf3e3; --warn-ink:#7a5320; --warn-rule:#e8cf9f; --axis:#4a7c59;
    --mono:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;
    --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
  }
  :root[data-theme="dark"]{
    --bg:#181715; --panel:#221f1b; --ink:#f1ede6; --muted:#a89e8f; --rule:#3a352e;
    --blue-far:#5fa1ea; --blue-mid:#3987e5; --neutral:#383835; --red-mid:#e66767; --red-far:#ff8b7a;
    --warn-bg:#2e2415; --warn-ink:#e8c98d; --warn-rule:#5c4a2a; --axis:#7fc79a;
  }
  @media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
    --bg:#181715; --panel:#221f1b; --ink:#f1ede6; --muted:#a89e8f; --rule:#3a352e;
    --blue-far:#5fa1ea; --blue-mid:#3987e5; --neutral:#383835; --red-mid:#e66767; --red-far:#ff8b7a;
    --warn-bg:#2e2415; --warn-ink:#e8c98d; --warn-rule:#5c4a2a; --axis:#7fc79a;
  }}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);padding:24px 18px 36px}
  .wrap{max-width:1040px;margin:0 auto}
  .eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin:0 0 6px}
  h1{font-size:clamp(20px,2.6vw,27px);margin:0 0 10px;font-weight:650;letter-spacing:-.01em;text-wrap:balance}
  .dek{max-width:66ch;color:var(--muted);font-size:14px;line-height:1.55;margin:0}
  .warn{background:var(--warn-bg);border:1px solid var(--warn-rule);color:var(--warn-ink);
        border-radius:8px;padding:10px 13px;margin:16px 0 0;font-size:12.5px;line-height:1.5}
  .warn b{font-weight:650}
  .panel{background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:16px;margin-top:16px}
  .row{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}
  .stage{position:relative;flex:1 1 540px;min-width:290px}
  canvas{width:100%;aspect-ratio:1/1;display:block;border-radius:8px;cursor:grab;touch-action:none;
         background:radial-gradient(circle at 38% 32%,color-mix(in srgb,var(--panel) 88%,var(--ink) 3%),var(--panel) 72%)}
  canvas:active{cursor:grabbing}
  .hint{position:absolute;bottom:9px;left:9px;font-family:var(--mono);font-size:10px;color:var(--muted);
        background:color-mix(in srgb,var(--panel) 80%,transparent);padding:3px 7px;border-radius:5px;pointer-events:none}
  .side{flex:0 0 235px;display:flex;flex-direction:column;gap:13px}
  .label{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
  .value{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:14px;margin-top:2px}
  .bar{height:12px;border-radius:6px;border:1px solid var(--rule);
       background:linear-gradient(90deg,var(--blue-far),var(--blue-mid),var(--neutral),var(--red-mid),var(--red-far))}
  .bar-lab{display:flex;justify-content:space-between;font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:4px;font-variant-numeric:tabular-nums}
  .controls{display:flex;flex-direction:column;gap:7px;border-top:1px solid var(--rule);padding-top:12px}
  .controls label{display:flex;align-items:center;gap:7px;font-size:12.5px;cursor:pointer}
  .controls select{font-family:var(--sans);font-size:12.5px;padding:3px 5px;border-radius:5px;
                   border:1px solid var(--rule);background:var(--panel);color:var(--ink)}
  .note{font-size:12px;line-height:1.5;color:var(--muted);border-top:1px solid var(--rule);padding-top:11px}
  table{border-collapse:collapse;font-family:var(--mono);font-size:11.5px;width:100%}
  td{padding:1px 0}
  td:last-child{text-align:right;font-variant-numeric:tabular-nums}
  footer{margin-top:16px;font-size:11.5px;color:var(--muted)}
  .warnlist{margin:10px 0 0;padding-left:18px;font-size:12.5px;color:var(--warn-ink);line-height:1.5}
</style>

<div class="wrap">
  <p class="eyebrow">__EYEBROW__</p>
  <h1>__H1__</h1>
  <p class="dek">__DEK__</p>

  <div class="warn">
    <b>Not extensively tested.</b> This visualization routine is new and has had limited
    validation. The plotted values come directly from TOPAS (no harmonics were re-derived here),
    but the symmetry expansion and rendering should be sanity-checked before you rely on them.
    __EXTRA_WARN__
  </div>

  <div class="panel">
    <div class="row">
      <div class="stage">
        <canvas id="cv" width="920" height="920"></canvas>
        <div class="hint">drag to orbit &middot; scroll to zoom</div>
      </div>
      <div class="side">
        <div>
          <div class="label">Series</div>
          <div class="value">__SH_NAME__</div>
        </div>
        <div>
          <div class="label">Value range</div>
          <div class="value">__SH_MIN__ &ndash; __SH_MAX__</div>
        </div>
        <div>
          <div class="label">Sampling</div>
          <div class="value">__NFAM__ families &rarr; __NPTS__ dirs</div>
        </div>
        <div>
          <div class="label">Colour scale</div>
          <div class="bar"></div>
          <div class="bar-lab"><span>__SH_MIN__</span><span>1.000</span><span>__SH_MAX__</span></div>
        </div>
        <div class="controls">
          <label><input type="checkbox" id="cbRadius" checked> Radius &prop; value</label>
          <label><input type="checkbox" id="cbDots" checked> Reflection dots (raw)</label>
          <label><input type="checkbox" id="cbSurf" __SURF_CHECKED__ __SURF_DISABLED__> Interpolated surface</label>
          <label><input type="checkbox" id="cbIso" __SURF_DISABLED__> Iso-contour lines</label>
          <label>Contours:
            <select id="selIso" __SURF_DISABLED__>
              <option value="5">5 levels</option>
              <option value="9" selected>9 levels</option>
              <option value="15">15 levels</option>
            </select>
          </label>
        </div>
        <div class="controls">
          <label><input type="checkbox" id="cbRecip" checked> Reciprocal axes a*, b*, c*</label>
          <label><input type="checkbox" id="cbCell"> Unit cell + a, b, c</label>
        </div>
        __COEFF_BLOCK__
      </div>
    </div>
  </div>
  __WARN_BLOCK__
  <footer>__FOOTER__</footer>
</div>

<script>
(function(){
const PTS=__POINTS__, MESH=__MESH__, SH_MIN=__SH_MIN_RAW__, SH_MAX=__SH_MAX_RAW__;
const CELL=__CELL__;
const cv=document.getElementById('cv'), ctx=cv.getContext('2d');
let rotX=-0.45, rotY=0.62, zoom=1, drag=false, lx=0, ly=0;
let isoCache=null, isoCacheKey='';

// Zoom-out floor from the cell's own extent, since an oblique corner
// reaches much further than a near-orthogonal one (triclinic ~4.4 vs cubic
// ~2.4), and one constant would clip the former or over-zoom the latter.
// A point at distance d fully fits when zoom <= 1.1875/d; /1.25 adds slack.
const MIN_ZOOM=(function(){
  if(!CELL) return 0.5;
  let dmax=0;
  for(const p of CELL.corners) dmax=Math.max(dmax,Math.hypot(p[0],p[1],p[2]));
  const o=CELL.corners[0];
  for(const v of CELL.direct)
    dmax=Math.max(dmax,Math.hypot(o[0]+v[0],o[1]+v[1],o[2]+v[2]));
  if(!(dmax>0)) return 0.5;
  return Math.min(0.5,(1.1875/dmax)/1.25);
})();

function cssVar(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
function hex2rgb(h){h=h.replace('#','');if(h.length===3)h=h.split('').map(c=>c+c).join('');
  const n=parseInt(h,16);return [(n>>16)&255,(n>>8)&255,n&255];}
function mix(a,b,t){return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];}

function ramp(){return {bf:hex2rgb(cssVar('--blue-far')),bm:hex2rgb(cssVar('--blue-mid')),
  nu:hex2rgb(cssVar('--neutral')),rm:hex2rgb(cssVar('--red-mid')),rf:hex2rgb(cssVar('--red-far'))};}

function colorFor(v,R){
  let t,c1,c2;
  if(v<=1){const s=1-SH_MIN, f=s>1e-9?(1-v)/s:0;
    if(f<0.5){t=f/0.5;c1=R.nu;c2=R.bm;}else{t=(f-0.5)/0.5;c1=R.bm;c2=R.bf;}}
  else{const s=SH_MAX-1, f=s>1e-9?(v-1)/s:0;
    if(f<0.5){t=f/0.5;c1=R.nu;c2=R.rm;}else{t=(f-0.5)/0.5;c1=R.rm;c2=R.rf;}}
  const c=mix(c1,c2,Math.max(0,Math.min(1,t)));
  return 'rgb('+(c[0]|0)+','+(c[1]|0)+','+(c[2]|0)+')';
}

function rot(p){
  const cy=Math.cos(rotY), sy=Math.sin(rotY);
  const x1=p[0]*cy+p[2]*sy, z1=-p[0]*sy+p[2]*cy;
  const cx=Math.cos(rotX), sx=Math.sin(rotX);
  return [x1, p[1]*cx-z1*sx, p[1]*sx+z1*cx];
}

// Per-frame state, refreshed once in draw(). Read inside the hot loops, so
// hitting the DOM here would cost ~20k getElementById calls per frame.
let RADIUS_ON=true, MAX_R=1.22;

function radiusScale(v){
  if(!RADIUS_ON) return 1;
  const span=Math.max(SH_MAX-SH_MIN,1e-9);
  return 0.72+0.5*((v-SH_MIN)/span);
}

function buildIso(levels){
  // Marching triangles on the mesh: linear crossings along each edge.
  if(!MESH) return [];
  const segs=[];
  for(let li=0; li<levels.length; li++){
    const L=levels[li];
    for(const f of MESH.faces){
      const vs=[MESH.verts[f[0]],MESH.verts[f[1]],MESH.verts[f[2]]];
      const ws=[MESH.vals[f[0]],MESH.vals[f[1]],MESH.vals[f[2]]];
      const cross=[];
      for(let e=0;e<3;e++){
        const a=ws[e], b=ws[(e+1)%3];
        if((a-L)*(b-L)<0){
          const t=(L-a)/(b-a);
          const p=vs[e], q=vs[(e+1)%3];
          cross.push([p[0]+(q[0]-p[0])*t, p[1]+(q[1]-p[1])*t, p[2]+(q[2]-p[2])*t, L]);
        }
      }
      if(cross.length===2) segs.push(cross);
    }
  }
  return segs;
}

function isoLevels(n){
  const out=[];
  for(let i=1;i<=n;i++) out.push(SH_MIN+(SH_MAX-SH_MIN)*i/(n+1));
  return out;
}

let W,H;
function resize(){
  const dpr=window.devicePixelRatio||1, r=cv.getBoundingClientRect();
  W=r.width;H=r.height;cv.width=W*dpr;cv.height=H*dpr;
  ctx.setTransform(dpr,0,0,dpr,0,0);draw();
}
window.addEventListener('resize',resize);
cv.addEventListener('pointerdown',e=>{drag=true;lx=e.clientX;ly=e.clientY;cv.setPointerCapture(e.pointerId);});
cv.addEventListener('pointerup',()=>{drag=false;});
cv.addEventListener('pointermove',e=>{if(!drag)return;
  rotY+=(e.clientX-lx)*0.008;rotX+=(e.clientY-ly)*0.008;
  rotX=Math.max(-1.5,Math.min(1.5,rotX));lx=e.clientX;ly=e.clientY;draw();});
cv.addEventListener('wheel',e=>{e.preventDefault();
  zoom*=(e.deltaY<0)?1.08:0.93;zoom=Math.max(MIN_ZOOM,Math.min(3.5,zoom));draw();},{passive:false});
for(const id of ['cbDots','cbSurf','cbIso','cbRadius','selIso','cbRecip','cbCell'])
  document.getElementById(id).addEventListener('change',draw);

// Hidden = behind the surface and inside its silhouette. MAX_R is a
// conservative constant; slight over-occlusion beats lines floating over
// the front of the surface.
function occluded(p){
  return p[2] < 0 && Math.sqrt(p[0]*p[0]+p[1]*p[1]) < MAX_R;
}

// Draw a 3D line as short segments so it can be hidden piecewise where it
// passes behind the surface, rather than all-or-nothing.
function line3d(ctx,cx,cy,R0,p,q,color,width,dashHidden){
  const N=26;
  for(let i=0;i<N;i++){
    const t0=i/N, t1=(i+1)/N;
    const A=[p[0]+(q[0]-p[0])*t0,p[1]+(q[1]-p[1])*t0,p[2]+(q[2]-p[2])*t0];
    const B=[p[0]+(q[0]-p[0])*t1,p[1]+(q[1]-p[1])*t1,p[2]+(q[2]-p[2])*t1];
    const ra=rot(A), rb=rot(B);
    const mid=[(ra[0]+rb[0])/2,(ra[1]+rb[1])/2,(ra[2]+rb[2])/2];
    const hid=occluded(mid);
    if(hid && !dashHidden) continue;
    ctx.globalAlpha=hid?0.18:0.95;
    ctx.strokeStyle=color; ctx.lineWidth=width;
    ctx.beginPath();
    ctx.moveTo(cx+ra[0]*R0,cy-ra[1]*R0);
    ctx.lineTo(cx+rb[0]*R0,cy-rb[1]*R0);
    ctx.stroke();
  }
  ctx.globalAlpha=1;
}

function arrowHead(ctx,cx,cy,R0,tip,dir,color){
  const t=rot(tip);
  if(occluded(t)) return;
  const back=[tip[0]-dir[0]*0.09,tip[1]-dir[1]*0.09,tip[2]-dir[2]*0.09];
  const b=rot(back);
  const sx=cx+t[0]*R0, sy=cy-t[1]*R0;
  const bx=cx+b[0]*R0, by=cy-b[1]*R0;
  const dx=sx-bx, dy=sy-by, L=Math.hypot(dx,dy)||1;
  const ux=dx/L, uy=dy/L, px=-uy, py=ux, w=L*0.42;
  ctx.fillStyle=color; ctx.globalAlpha=0.95;
  ctx.beginPath();
  ctx.moveTo(sx,sy);
  ctx.lineTo(bx+px*w,by+py*w);
  ctx.lineTo(bx-px*w,by-py*w);
  ctx.closePath(); ctx.fill();
  ctx.globalAlpha=1;
}

// Label with a surface-coloured halo so it stays readable over the plot.
function label3d(ctx,cx,cy,R0,pos,text,color,size){
  const p=rot(pos);
  if(occluded(p)) return;
  const x=cx+p[0]*R0, y=cy-p[1]*R0;
  ctx.font='600 '+size+'px '+cssVar('--sans');
  ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.lineWidth=3.5; ctx.strokeStyle=cssVar('--panel');
  ctx.strokeText(text,x,y);
  ctx.fillStyle=color; ctx.fillText(text,x,y);
  ctx.textAlign='start'; ctx.textBaseline='alphabetic';
}

function drawTriad(ctx,cx,cy,R0,vecs,names,color,len,size){
  for(let i=0;i<3;i++){
    const v=vecs[i];
    const n=Math.hypot(v[0],v[1],v[2])||1;
    const u=[v[0]/n,v[1]/n,v[2]/n];
    const tip=[u[0]*len,u[1]*len,u[2]*len];
    line3d(ctx,cx,cy,R0,[0,0,0],tip,color,1.6,true);
    arrowHead(ctx,cx,cy,R0,tip,u,color);
    label3d(ctx,cx,cy,R0,[u[0]*(len+0.13),u[1]*(len+0.13),u[2]*(len+0.13)],
            names[i],color,size);
  }
}

function draw(){
  ctx.clearRect(0,0,W,H);
  const cx=W/2, cy=H/2, R0=Math.min(W,H)*0.40*zoom, RA=ramp();
  RADIUS_ON=document.getElementById('cbRadius').checked;
  MAX_R=RADIUS_ON?1.22:1.0;
  const showDots=document.getElementById('cbDots').checked;
  const showSurf=MESH && document.getElementById('cbSurf').checked;
  const showIso=MESH && document.getElementById('cbIso').checked;

  if(!showSurf){
    ctx.strokeStyle=cssVar('--rule');ctx.lineWidth=1;
    ctx.beginPath();ctx.arc(cx,cy,R0,0,Math.PI*2);ctx.stroke();
  }

  if(showSurf){
    const tris=[];
    for(const f of MESH.faces){
      const a=MESH.verts[f[0]],b=MESH.verts[f[1]],c=MESH.verts[f[2]];
      const va=MESH.vals[f[0]],vb=MESH.vals[f[1]],vc=MESH.vals[f[2]];
      const vm=(va+vb+vc)/3;
      const pa=rot([a[0]*radiusScale(va),a[1]*radiusScale(va),a[2]*radiusScale(va)]);
      const pb=rot([b[0]*radiusScale(vb),b[1]*radiusScale(vb),b[2]*radiusScale(vb)]);
      const pc=rot([c[0]*radiusScale(vc),c[1]*radiusScale(vc),c[2]*radiusScale(vc)]);
      tris.push({pa,pb,pc,vm,d:(pa[2]+pb[2]+pc[2])/3});
    }
    tris.sort((p,q)=>p.d-q.d);
    for(const t of tris){
      const shade=0.55+0.45*((t.d+1)/2);
      ctx.globalAlpha=shade;
      ctx.fillStyle=colorFor(t.vm,RA);
      ctx.beginPath();
      ctx.moveTo(cx+t.pa[0]*R0,cy-t.pa[1]*R0);
      ctx.lineTo(cx+t.pb[0]*R0,cy-t.pb[1]*R0);
      ctx.lineTo(cx+t.pc[0]*R0,cy-t.pc[1]*R0);
      ctx.closePath();ctx.fill();
      // hairline of the same colour closes the seams between triangles
      ctx.strokeStyle=ctx.fillStyle;ctx.lineWidth=0.6;ctx.stroke();
    }
    ctx.globalAlpha=1;
  }

  if(showIso){
    // Segments are built on the unit mesh carrying their own level value
    // and scaled at draw time, so the cache depends only on level count.
    const n=parseInt(document.getElementById('selIso').value,10);
    const key=String(n);
    if(isoCacheKey!==key){isoCache=buildIso(isoLevels(n));isoCacheKey=key;}
    ctx.lineWidth=1.1;
    for(const s of isoCache){
      const s0=s[0], s1=s[1];
      const r0=radiusScale(s0[3]), r1=radiusScale(s1[3]);
      const p=rot([s0[0]*r0,s0[1]*r0,s0[2]*r0]);
      const q=rot([s1[0]*r1,s1[1]*r1,s1[2]*r1]);
      if((p[2]+q[2])/2 < -0.15) continue;   // hide back-face contours
      ctx.globalAlpha=0.75;
      ctx.strokeStyle=cssVar('--ink');
      ctx.beginPath();
      ctx.moveTo(cx+p[0]*R0,cy-p[1]*R0);
      ctx.lineTo(cx+q[0]*R0,cy-q[1]*R0);
      ctx.stroke();
    }
    ctx.globalAlpha=1;
  }

  if(showDots){
    const proj=PTS.map(p=>{
      const r=radiusScale(p[3]);
      const q=rot([p[0]*r,p[1]*r,p[2]*r]);
      return {x:cx+q[0]*R0, y:cy-q[1]*R0, d:q[2], v:p[3]};
    });
    proj.sort((a,b)=>a.d-b.d);
    for(const p of proj){
      ctx.globalAlpha=(showSurf?0.85:1)*(0.45+0.55*((p.d+1)/2));
      ctx.fillStyle=colorFor(p.v,RA);
      const rr=(showSurf?1.9:2.6)+1.1*((p.d+1)/2);
      ctx.beginPath();ctx.arc(p.x,p.y,rr,0,Math.PI*2);ctx.fill();
    }
    ctx.globalAlpha=1;
  }

  if(CELL && document.getElementById('cbCell').checked){
    const col=cssVar('--muted');
    for(const e of CELL.edges)
      line3d(ctx,cx,cy,R0,CELL.corners[e[0]],CELL.corners[e[1]],col,1.1,true);
    // Direct axes drawn from the cell origin corner (index 0 = -a/2,-b/2,-c/2)
    const o=CELL.corners[0];
    const names=['a','b','c'];
    for(let i=0;i<3;i++){
      const v=CELL.direct[i];
      const tip=[o[0]+v[0],o[1]+v[1],o[2]+v[2]];
      line3d(ctx,cx,cy,R0,o,tip,cssVar('--ink'),2.0,true);
      const n=Math.hypot(v[0],v[1],v[2])||1;
      arrowHead(ctx,cx,cy,R0,tip,[v[0]/n,v[1]/n,v[2]/n],cssVar('--ink'));
      label3d(ctx,cx,cy,R0,[o[0]+v[0]*1.10,o[1]+v[1]*1.10,o[2]+v[2]*1.10],
              names[i],cssVar('--ink'),13);
    }
  }

  if(CELL && document.getElementById('cbRecip').checked){
    drawTriad(ctx,cx,cy,R0,CELL.recip,['a*','b*','c*'],cssVar('--axis'),
              MAX_R+0.16,13);
  }
}
resize();
})();
</script>
"""


def build_html(points, mesh, sh_name, sh_min, sh_max, n_families, cell, symbol,
               title, coeffs, warnings, phase_index, phase_total, surface_on,
               sampling_deg, cell_geom=None):
    pts_compact = [[round(p[0], 4), round(p[1], 4), round(p[2], 4), round(p[3], 5)]
                   for p in points]
    if mesh is not None:
        mesh_json = json.dumps({
            "verts": [[round(v[0], 4), round(v[1], 4), round(v[2], 4)] for v in mesh[0]],
            "faces": mesh[1],
            "vals": [round(v, 5) for v in mesh[2]],
        }, separators=(",", ":"))
    else:
        mesh_json = "null"

    if cell_geom is not None:
        corners, edges, direct_axes, recip_axes = cell_geom
        cell_json = json.dumps({
            "corners": [[round(v, 5) for v in p] for p in corners],
            "edges": edges,
            "direct": [[round(v, 5) for v in p] for p in direct_axes],
            "recip": [[round(v, 5) for v in p] for p in recip_axes],
        }, separators=(",", ":"))
    else:
        cell_json = "null"

    a, b, c, al, be, ga = cell
    cell_str = (f"a={a:.5f} b={b:.5f} c={c:.5f} "
                f"al={al:.3f} be={be:.3f} ga={ga:.3f}")

    if coeffs:
        rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in coeffs)
        coeff_block = (f'<div><div class="label">Refined coefficients</div>'
                       f'<table>{rows}</table></div>')
    else:
        coeff_block = ""

    extra = ""
    if mesh is not None:
        extra = ("The surface and contour modes are <b>interpolated between</b> the sampled "
                 "reflection directions, not an analytic evaluation of the harmonic; smooth "
                 "regions inside a sparsely-sampled gap are interpolation artifacts.")

    if warnings:
        items = "".join(f"<li>{w}</li>" for w in warnings)
        warn_block = f'<div class="warn"><b>Warnings from this run</b><ul class="warnlist">{items}</ul></div>'
    else:
        warn_block = ""

    phase_note = f" &middot; phase {phase_index} of {phase_total}" if phase_total > 1 else ""
    dek = (f"Value of the <code>{sh_name}</code> spherical-harmonics series over every "
           f"crystallographically distinct direction, evaluated by TOPAS itself and expanded "
           f"across the Laue group derived from space group {symbol}. Red = above 1 (the series "
           f"increases the quantity it scales), blue = below 1. Drag to orbit, scroll to zoom.")

    html = HTML_TEMPLATE
    for needle, val in [
        ("__TITLE__", f"{sh_name} spherical-harmonics surface -- {title}"),
        ("__EYEBROW__", f"{title}{phase_note} &middot; spherical harmonics"),
        ("__H1__", f"{sh_name}: spherical-harmonics pole figure"),
        ("__DEK__", dek),
        ("__EXTRA_WARN__", extra),
        ("__SH_NAME__", sh_name),
        ("__NFAM__", str(n_families)),
        ("__NPTS__", str(len(points))),
        ("__COEFF_BLOCK__", coeff_block),
        ("__WARN_BLOCK__", warn_block),
        ("__SURF_CHECKED__", "checked" if (mesh is not None and surface_on) else ""),
        ("__SURF_DISABLED__", "" if mesh is not None else "disabled"),
        ("__POINTS__", json.dumps(pts_compact, separators=(",", ":"))),
        ("__MESH__", mesh_json),
        ("__CELL__", cell_json),
        ("__SH_MIN_RAW__", repr(sh_min)),
        ("__SH_MAX_RAW__", repr(sh_max)),
        ("__SH_MIN__", f"{sh_min:.3f}"),
        ("__SH_MAX__", f"{sh_max:.3f}"),
        ("__FOOTER__", f"Space group {symbol} &middot; {cell_str} &middot; "
                        f"median sampling {sampling_deg:.1f}&deg;" if sampling_deg
                        else f"Space group {symbol} &middot; {cell_str}"),
    ]:
        html = html.replace(needle, val)
    return html


# ---------------------------------------------------------------------------

COEFF_ROW_RE = re.compile(r"^\s*(k\d+|y\d+[pm]?)\s+!?([A-Za-z_]\w*)\s+(-?[\d.]+(?:[eE][-+]?\d+)?)",
                          re.MULTILINE)


def extract_coefficients(block_values):
    """Pull the refined sh_Cij_prm rows out for display, if present."""
    m = re.search(r"load\s+sh_Cij_prm\s*\{(.*?)\}", block_values, re.DOTALL)
    if not m:
        return []
    out = []
    for cm in COEFF_ROW_RE.finditer(m.group(1)):
        out.append((cm.group(1), cm.group(3)))
    return out


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inp_file")
    parser.add_argument("-o", "--output",
                        help="write HTML here instead of <input>_sh_sphere.html")
    parser.add_argument("--phase", type=int, default=1,
                        help="1-indexed str block to use if the file has more than one (default 1)")
    parser.add_argument("--surface", action="store_true",
                        help="also build the interpolated surface mesh (enables the "
                             "surface/contour/radius toggles on the page)")
    parser.add_argument("--mesh-level", type=int, default=3,
                        help="icosphere subdivision level for --surface (default 3 = 642 "
                             "vertices; 4 = 2562, slower)")
    parser.add_argument("--keep-scratch", action="store_true",
                        help="keep the temporary TOPAS probe file for inspection")
    args = parser.parse_args()

    warnings = []

    with open(args.inp_file, encoding="utf-8") as f:
        raw = f.read()
    stripped = remove_errors.ERROR_SUFFIX_RE.sub("", raw)
    clean = cis.strip_comments_and_strings(stripped)
    values = cis.strip_comments_only(stripped)

    blocks = cis.find_str_blocks(clean)
    if not blocks:
        raise SystemExit("No 'str' phase block found in this file.")
    if args.phase < 1 or args.phase > len(blocks):
        raise SystemExit(f"--phase {args.phase} is out of range "
                          f"(this file has {len(blocks)} str block(s)).")
    cs, ce = blocks[args.phase - 1]
    block_clean = clean[cs:ce]
    block_values = values[cs:ce]

    sh_name, how = find_sh_name(block_clean)
    if sh_name is None:
        raise SystemExit(how)

    sg_m = re.search(r"\bspace_group\b\s*(\"[^\"]*\"|\S+)", block_values)
    if not sg_m:
        raise SystemExit("This str block has no space_group -- can't determine symmetry.")
    symbol = sg_m.group(1).strip('"')
    symops, _hdr, msg = symmetry_utils.resolve_sg_operators(symbol)
    if not symops:
        raise SystemExit(f"Could not resolve symmetry operators for space_group {symbol!r}: {msg}")

    first_site = re.search(r"\bsite\b", block_clean)
    preamble = block_clean[:first_site.start()] if first_site else block_clean
    cell = extract_cell_params(preamble)
    if cell is None:
        raise SystemExit("Could not resolve this str block's cell parameters.")

    rows = run_topas_for_sh(args.inp_file, sh_name, args.phase,
                            keep_scratch=args.keep_scratch)

    A, A_inv, B = reciprocal_basis_cart(cell)
    rmt_worst, rmt_checked = check_reciprocal_metric(rows, B, warnings)
    laue = cartesian_laue_group(symops, A, A_inv)
    points, n_families, _conflicts = expand_to_sphere(rows, B, laue, warnings)

    sh_vals = [p[3] for p in points]
    sh_min, sh_max = min(sh_vals), max(sh_vals)
    if abs(sh_max - sh_min) < 1e-9:
        warnings.append("The series is constant over all sampled directions "
                        "(no anisotropy to show).")

    sampling = median_nn_angle_deg(points)
    if sampling and sampling > 12:
        warnings.append(
            f"Sparse sampling: median nearest-neighbour separation is {sampling:.1f} degrees. "
            f"The dots are still exact, but an interpolated surface across gaps this wide "
            f"should not be over-interpreted."
        )

    mesh = None
    if args.surface:
        sigma = max(sampling or 6.0, 3.0)
        verts, faces = icosphere(args.mesh_level)
        vals = interpolate_to_mesh(verts, points, sigma)
        mesh = (verts, faces, vals)

    coeffs = extract_coefficients(block_values)
    geom = cell_geometry(A, B)
    title = os.path.basename(args.inp_file)
    html = build_html(points, mesh, sh_name, sh_min, sh_max, n_families, cell,
                      symbol, title, coeffs, warnings, args.phase, len(blocks),
                      args.surface, sampling, cell_geom=geom)

    out_path = args.output or (os.path.splitext(args.inp_file)[0] + "_sh_sphere.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Series '{sh_name}' ({how}), space group {symbol}: "
          f"{n_families} reflection families -> {len(points)} directions "
          f"({len(laue)} Laue operations).", file=sys.stderr)
    print(f"Value range {sh_min:.5f} .. {sh_max:.5f}"
          + (f", median sampling {sampling:.1f} deg" if sampling else ""), file=sys.stderr)
    if rmt_checked:
        print(f"Reciprocal-metric self-check: |B.hkl| vs TOPAS d-spacing agrees to "
              f"{rmt_worst * 100:.4f}% worst case over {rmt_checked} reflections.",
              file=sys.stderr)
    for w in warnings:
        print(f"Note: {w}", file=sys.stderr)
    print(f"Written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
