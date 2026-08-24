"""
peak_search.py -- numerical peak search, substituting for TOPAS-GUI's
View/Search Peaks -> Add Peaks, which is not scriptable.

Pipeline
--------
1. Optional Rachinger Ka2 strip (--rachinger), for the search pass only.
2. Light Savitzky-Golay smoothing; unsmoothed step-scan counts are Poisson-noisy
   and yield many single-point maxima.
3. Rolling local background: a low percentile over a moving window, so the
   significance test is relative to local background rather than an absolute
   level.
4. Peaks by prominence relative to local Poisson noise, sqrt(local background),
   with a minimum-width filter rejecting single-point spikes.
5. Area by background-subtracted trapezoid integration, over a window clamped so
   it cannot reach into a neighbouring peak.

Output columns: pos2th  height  localbkg  area  flank

    AREA (column 4) is the intensity to use in a TOPAS `load xo I { }` block,
    not HEIGHT (column 2). Height is 5-10x too large and the peak shape then
    refines to an implausibly narrow width to reproduce it.

    FLANK (column 5) is each candidate's net height divided by that of the
    strongest candidate within 0.5 deg. Savitzky-Golay smoothing of a steep,
    high-dynamic-range tail rings slightly, so a strong reflection can throw
    small spurious maxima down a flank. A flank ratio below about 0.02 beside a
    much stronger line is usually tail structure of that line. The column is
    reported, never applied: every automatic filter tried against it also
    removed real lines, including weak superlattice reflections.

Usage
-----
    python peak_search.py yobs.xy [options]        # see --help

Threshold
---------
Run at the default --sig-mult 5. A raised threshold drops real lines, including
lines above 10 sigma, and the later fitting stages do not reliably recover them.
Weak lines matter disproportionately: superlattice reflections of a genuine
supercell are weak by definition, so a threshold tuned to reject noise rejects
the reflections that prove the true cell. If indexing succeeds suspiciously
cleanly on a small cell, re-run with a lower --sig-mult and check the extra
lines with scripts/compare_cells.py.

The peak positions produced here are limited to the data step and are search
estimates only. Accurate positions come from the TOPAS peak fit that follows;
see the peak-fitting rules in references/29-indexing-workflow-conventions.md.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
from scipy.ndimage import percentile_filter
from scipy.signal import find_peaks, savgol_filter

# numpy >= 2.0 renamed trapz -> trapezoid; support both.
_trapz = getattr(np, "trapezoid", None) or np.trapz

# Cu Ka2 / Ka1, matching CuKa2_analyt's dominant satellite pair.
CU_KA2_KA1 = 1.544426 / 1.540596


def rolling_percentile_bkg(y, step_deg, window_deg, pct=10):
    """Local background as a moving low percentile.

    Uses scipy's C-level percentile_filter: O(N*w) rather than the O(N^2) of a
    per-point boolean mask over the whole array, which dominated runtime on
    4000+ point scans.
    """
    size = max(3, int(round(window_deg / step_deg)))
    if size % 2 == 0:
        size += 1
    return percentile_filter(y, percentile=pct, size=size, mode="nearest")


def integration_half_widths(positions, default_half, step_deg):
    """Per-peak integration half-width, clamped to avoid neighbouring peaks.

    Where two peaks sit closer together than twice a fixed window, the integral
    of the weaker one bleeds into its stronger neighbour and returns an area
    several times too large. Each window is therefore limited to half the
    distance to the nearest detected neighbour, with a floor of three data steps
    so very close pairs still get an approximate area.
    """
    pos = np.asarray(positions, dtype=float)
    n = len(pos)
    half = np.full(n, float(default_half))
    if n > 1:
        gaps = np.diff(pos)
        neighbour = np.empty(n)
        neighbour[0], neighbour[-1] = gaps[0], gaps[-1]
        if n > 2:
            neighbour[1:-1] = np.minimum(gaps[:-1], gaps[1:])
        half = np.minimum(half, 0.5 * neighbour)
    return np.maximum(half, 3.0 * step_deg)


def trapezoid_area(x, ysm, bkg, center, half_width):
    mask = (x >= center - half_width) & (x <= center + half_width)
    if mask.sum() < 2:
        return 0.0
    net = np.clip(ysm[mask] - bkg[mask], 0.0, None)
    return float(_trapz(net, x[mask]))


def predicted_doublet_split(two_theta_deg, lam_ratio):
    """Ka1->Ka2 separation in degrees 2theta, from Bragg's law.

    Differentiating lambda = 2 d sin(theta) at fixed d:
        delta(2theta) = 2 * (delta_lambda / lambda) * tan(theta)
    """
    th = np.radians(two_theta_deg / 2.0)
    return np.degrees(2.0 * (lam_ratio - 1.0) * np.tan(th))


def rachinger_strip(x, y, lam_ratio=CU_KA2_KA1, i_ratio=0.5, n_iter=6,
                    bkg_window=2.0, bkg_percentile=10, min_split_steps=1.5):
    """Remove the Ka2 component, returning (stripped_y, first_stripped_2theta).

    Solved as a FIXED-POINT ITERATION, not as the textbook low-to-high recursive
    sweep:

        s_{n+1}(x) = net(x) - r * s_n(x - d(x))

    Two reasons. First, a single subtraction pass is not enough: writing the
    observed net as a1(x) + r*a1(x-d), one pass leaves -r^2*a1(x-2d), a NEGATIVE
    ghost of amplitude 0.25 at +2d from every strong peak -- large enough to
    swallow a genuine weak reflection. The iteration converges geometrically at
    ratio r, so six passes leave under 1%. Second, the in-place sweep propagates
    each point's error into every later point and rings; each pass here is an
    independent vectorised interpolation over the whole array, so nothing
    accumulates, and clipping at zero between passes stops negative excursions
    spreading.

    Operates on the BACKGROUND-SUBTRACTED signal. The background is not doubled
    by the Ka2 line, so stripping raw counts would scale a sloping background by
    (1-r) and tilt it.

    Below the angle where the predicted split falls under `min_split_steps` data
    steps the strip is meaningless and only adds noise, so it is not applied
    there; the crossover angle is returned so the caller can report it.
    """
    step = float(np.median(np.diff(x)))
    bkg = rolling_percentile_bkg(y.astype(float), step, bkg_window, pct=bkg_percentile)
    net = y.astype(float) - bkg

    d = predicted_doublet_split(x, lam_ratio)
    active = d >= min_split_steps * step
    first = float(x[active][0]) if active.any() else float("inf")

    # Interpolation is done on the unsmoothed net: the iteration amplifies noise
    # by only ~15% here, and smoothing first would blunt exactly the weak
    # shoulders the strip is meant to expose.
    s = net.copy()
    for _ in range(n_iter):
        shifted = np.interp(x - d, x, s, left=0.0)
        s = np.clip(net - i_ratio * shifted * active, 0.0, None)
    return s + bkg, first


def merge_doublets(cands, lam_ratio, step_deg, lo_frac=0.5, hi_frac=1.8):
    """Merge each Ka2 companion into its Ka1 parent.

    A companion qualifies when it lies at roughly the predicted splitting for its
    angle and is the weaker of the pair. The predicted splitting is used rather
    than a fixed or linearly-growing window: the true separation varies as
    tan(theta), from ~0.05 deg at 20 deg 2theta to ~0.28 deg at 90 deg for Cu, so
    a single window wide enough at high angle over-merges genuinely distinct
    reflections at low angle.
    """
    merged = []
    i = 0
    while i < len(cands):
        pos, height, lb, area = cands[i]
        split = predicted_doublet_split(pos, lam_ratio)
        tol_lo = max(lo_frac * split, 2.0 * step_deg)
        tol_hi = max(hi_frac * split, 3.0 * step_deg)
        while i + 1 < len(cands):
            gap = cands[i + 1][0] - pos
            if tol_lo <= gap <= tol_hi and cands[i + 1][1] < height:
                area += cands[i + 1][3]
                i += 1
            else:
                break
        merged.append([pos, height, lb, area])
        i += 1
    return merged


def flank_ratios(cands, neighbourhood=0.5):
    """Net height of each candidate relative to the strongest candidate near it.

    Reported, never applied as a filter -- see the FLANK note in the module
    docstring for how to read it and why it is not automatic.
    """
    pos = np.array([c[0] for c in cands])
    net = np.array([c[1] - c[2] for c in cands])
    out = []
    for i, p in enumerate(pos):
        near = np.abs(pos - p) <= neighbourhood
        strongest = net[near].max()
        out.append(net[i] / strongest if strongest > 0 else 1.0)
    return out


def search(x, y, *, bkg_window=2.0, sig_mult=5.0, smooth_pts=9, min_width_pts=3,
           merge_doublet=False, lam_ratio=CU_KA2_KA1, area_half_width=0.25,
           bkg_percentile=10, rachinger=False, i_ratio=0.5):
    """Run the peak search. Returns (candidates, smooth_pts_used, strip_from).

    `strip_from` is the 2theta above which Rachinger stripping was applied, or
    None if it was not requested.
    """
    step = float(np.median(np.diff(x)))

    strip_from = None
    if rachinger:
        y, strip_from = rachinger_strip(
            x, y, lam_ratio=lam_ratio, i_ratio=i_ratio,
            bkg_window=bkg_window, bkg_percentile=bkg_percentile)
        # The Ka2 companion is gone, so the doublet merge has nothing left to
        # do and would only merge genuinely distinct reflections.
        merge_doublet = False

    if smooth_pts >= 5:
        smooth_pts += smooth_pts % 2 == 0  # savgol needs an odd window
        ysm = savgol_filter(y, smooth_pts, 3)
    else:
        ysm = y.astype(float, copy=True)

    bkg = rolling_percentile_bkg(ysm, step, bkg_window, pct=bkg_percentile)
    net = ysm - bkg
    noise = np.sqrt(np.maximum(bkg, 1.0))

    idx, _ = find_peaks(net, prominence=sig_mult * noise, width=min_width_pts)
    if len(idx) == 0:
        return [], smooth_pts, strip_from

    positions = x[idx]
    halves = integration_half_widths(positions, area_half_width, step)
    cands = [
        [float(x[i]), float(y[i]), float(bkg[i]), trapezoid_area(x, ysm, bkg, x[i], h)]
        for i, h in zip(idx, halves)
    ]
    cands.sort(key=lambda row: row[0])

    if merge_doublet:
        cands = merge_doublets(cands, lam_ratio, step)
    return cands, smooth_pts, strip_from


def load_pattern(path):
    """Read a 2-column-or-more text pattern, or convert a binary one via TOPAS.

    Bruker .RAW is a binary container, not text. Rather than reimplement its
    several format generations, it is converted by the program that already
    reads all of them: a zero-iteration tc.exe run writing Out_X_Yobs. The
    converted .xy is cached next to the original, so the conversion happens once.
    """
    import os
    import subprocess
    import tempfile

    with open(path, "rb") as fh:
        head = fh.read(4)
    if not head.startswith(b"RAW"):
        data = np.loadtxt(path)
        return data[:, 0], data[:, 1]

    xy = os.path.splitext(path)[0] + "_yobs.xy"
    if not os.path.exists(xy):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from topas_install import get_topas_dir
        topas_dir, found = get_topas_dir()
        if not found:
            raise SystemExit(
                f"{path} is a binary Bruker RAW file and TOPAS_DIR is not set, so it "
                "cannot be converted. Set TOPAS_DIR, or supply a text .xy/.xye instead.")
        inp = os.path.join(tempfile.mkdtemp(), "conv.inp")
        with open(inp, "w") as fh:
            fh.write("\n".join([
                "iters 0",
                'xdd "' + os.path.abspath(path) + '"',
                "\tbkg 0",
                '\tOut_X_Yobs("' + xy + '")',
                "",
            ]))
        r = subprocess.run([os.path.join(topas_dir, "tc.exe"), inp[:-4]],
                           capture_output=True, text=True)
        if not os.path.exists(xy):
            raise SystemExit("tc.exe could not convert " + path + ":\n"
                             + r.stdout + r.stderr)
        print(f"Converted {os.path.basename(path)} -> {os.path.basename(xy)} via tc.exe")
    data = np.loadtxt(xy)
    return data[:, 0], data[:, 1]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("yobs_file")
    ap.add_argument("--bkg-window", type=float, default=2.0,
                    help="width (deg) of the rolling background window (default 2.0)")
    ap.add_argument("--sig-mult", type=float, default=5.0,
                    help="prominence threshold in units of sqrt(local background); LOWER finds "
                         "weak lines such as superlattice reflections (default 5.0)")
    ap.add_argument("--smooth-pts", type=int, default=9,
                    help="Savitzky-Golay window in points, <5 disables (default 9)")
    ap.add_argument("--min-width-pts", type=int, default=3,
                    help="reject maxima narrower than this many points (default 3)")
    ap.add_argument("--merge-doublet", action="store_true",
                    help="merge Ka2 companions into their Ka1 parent. Off by default: Rachinger\n"
                         "stripping (--rachinger) supersedes it for Ka1/Ka2 data, and monochromated\n"
                         "or single-wavelength data has no companion to merge. Use it only for\n"
                         "Ka1/Ka2 data left unstripped.")
    ap.add_argument("--lam-ratio", type=float, default=CU_KA2_KA1,
                    help=f"satellite/main wavelength ratio for the doublet merge "
                         f"(default {CU_KA2_KA1:.7f}, Cu Ka2/Ka1). Monochromated or "
                         f"single-wavelength data should use --no-merge-doublet.")
    ap.add_argument("--area-half-width", type=float, default=0.25,
                    help="maximum half-width (deg) for area integration; automatically "
                         "reduced near neighbouring peaks (default 0.25)")
    ap.add_argument("--rachinger", action="store_true",
                    help="strip the Ka2 component before searching (Ka1/Ka2 data only). "
                         "Implies --no-merge-doublet. Use the ORIGINAL data for every "
                         "later fitting stage -- this is a search aid, not a correction.")
    ap.add_argument("--i-ratio", type=float, default=0.5,
                    help="Ka2/Ka1 integrated intensity ratio for --rachinger (default 0.5). "
                         "Real tubes run 0.49-0.52; too high leaves a negative dip on the "
                         "high-2theta flank that the search may read as structure.")
    ap.add_argument("--bkg-percentile", type=float, default=10,
                    help="percentile taken as background within the window (default 10)")
    ap.add_argument("-o", "--out", help="write to this file instead of stdout")
    args = ap.parse_args(argv)

    x, y = load_pattern(args.yobs_file)
    cands, smooth_used, strip_from = search(
        x, y,
        bkg_window=args.bkg_window, sig_mult=args.sig_mult, smooth_pts=args.smooth_pts,
        min_width_pts=args.min_width_pts, merge_doublet=args.merge_doublet,
        lam_ratio=args.lam_ratio, area_half_width=args.area_half_width,
        bkg_percentile=args.bkg_percentile, rachinger=args.rachinger,
        i_ratio=args.i_ratio,
    )

    step = float(np.median(np.diff(x)))
    lines = [
        f"# {args.yobs_file}: step={step:.5f} deg, smooth={smooth_used}, "
        f"sig_mult={args.sig_mult}, {len(cands)} candidate peaks",
    ]
    if strip_from is not None:
        lines.append(
            f"# Ka2-stripped (Rachinger, r={args.i_ratio}) above {strip_from:.3f} deg; below "
            f"that the predicted split is under 1.5 data steps and no strip was applied. "
            f"Positions only -- refit on the ORIGINAL data.")
    lines += [
        "# pos2th      height      localbkg    area         flank",
        "#   (use AREA as I in load xo I { }; flank < ~0.02 next to a much stronger",
        "#    line is probably tail structure of that line -- inspect, do not auto-drop)",
    ]
    fl = flank_ratios(cands)
    lines += [f"{p:10.4f}  {h:10.2f}  {b:10.2f}  {a:12.3f}  {r:8.4f}"
              for (p, h, b, a), r in zip(cands, fl)]
    text = "\n".join(lines) + "\n"

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
        print(f"Wrote {len(cands)} candidate peaks to {args.out}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    sys.exit(main())
