"""
compare_cells.py -- decide between metrically-related candidate cells from the
raw pattern where they disagree, rather than from a figure of merit.

A sub-cell and its supercell fit the surviving line list equally well by
construction, so no position-based figure of merit (GoF, M20, F30) separates
them. Where superlattice reflections have been lost before indexing -- below the
search threshold, rejected as width outliers, or inside an exclusion window --
an indexing run can return a clean, high-GoF, UNI=0 substructure cell with
nothing in the result to reveal the error.

Classification
--------------
Cells are compared through the density of their LATTICE POINTS, i.e. primitive
cell volume (conventional volume / centering multiplicity, where P=1,
A/B/C/I=2, R=3, F=4). A denser direct lattice has a sparser reciprocal lattice
and predicts fewer lines.

  SAME LATTICE (equal primitive volumes) -- an exact metric re-description.
      Any hexagonal lattice (a=b, gamma=120) can always be re-described as a
      C-centred orthorhombic cell with b_o = sqrt(3)*a_h and twice the
      conventional volume; any A/B/C/I-centred cell has a primitive sub-cell at
      half volume. Such pairs predict identical positions, so a GoF difference
      between them reflects how many reflections each predicts, not evidence.
      Choosing between them is choosing a point group and requires intensities:
      Pawley/Le Bail at each candidate symmetry, or structure solution. The
      script reports this and stops.

  SUPERCELL / SUBSTRUCTURE (primitive volumes differ by an integer factor).
      The sparser-direct-lattice cell predicts extra reflections. The script
      checks the raw data at exactly those positions.

      The test is one-sided:
      -  Extra reflections PRESENT  => decisive for the larger cell. Centering
         cannot create a reflection, so an observed line the smaller cell cannot
         index is evidence of the larger lattice.
      -  Extra reflections ABSENT   => not evidence for the smaller cell. Glide
         and screw extinctions of the larger cell's space group produce the same
         absences, as does a genuinely weak superstructure. Distinguishing
         "wrong lattice" from "right lattice, extinct by symmetry" is what
         TOPAS's extinction-subgroup search is for. The script declines to call
         it and reports why.

  UNRELATED cells (non-integer primitive-volume ratio) -- no comparison made.

Usage:
    python compare_cells.py yobs.xy --lam 1.540596 \
        --cell A 5.59 5.59 5.59 90 90 90 --centering A P \
        --cell B 11.18 11.18 11.18 90 90 90 --centering B F

    Cells are named so centering can be attached to each. Centering is one of
    P I F A B C R (R = obverse rhombohedral on hexagonal axes). Any number of
    cells may be given; every pair is compared.

Only lattice centering is applied, never glide/screw conditions: centering is
the part that follows from the lattice itself, which is what this script reasons
about. See the one-sidedness note above for why that is sufficient.
"""
from __future__ import annotations

import argparse
import itertools
import sys

import numpy as np

# hkl allowed iff predicate is True; multiplicity = lattice points per conventional cell.
CENTERING = {
    "P": (lambda h, k, l: True, 1),
    "I": (lambda h, k, l: (h + k + l) % 2 == 0, 2),
    "A": (lambda h, k, l: (k + l) % 2 == 0, 2),
    "B": (lambda h, k, l: (h + l) % 2 == 0, 2),
    "C": (lambda h, k, l: (h + k) % 2 == 0, 2),
    "R": (lambda h, k, l: (-h + k + l) % 3 == 0, 3),  # obverse, hexagonal axes
    "F": (lambda h, k, l: (h + k) % 2 == 0 and (h + l) % 2 == 0 and (k + l) % 2 == 0, 4),
}


def metric_tensor(a, b, c, alpha, beta, gamma):
    """Direct-space metric tensor G; cell in Angstrom and degrees."""
    al, be, ga = np.radians([alpha, beta, gamma])
    return np.array([
        [a * a, a * b * np.cos(ga), a * c * np.cos(be)],
        [a * b * np.cos(ga), b * b, b * c * np.cos(al)],
        [a * c * np.cos(be), b * c * np.cos(al), c * c],
    ])


def conventional_volume(cell):
    return float(np.sqrt(np.linalg.det(metric_tensor(*cell))))


def primitive_volume(cell, centering):
    """Volume per lattice point -- the quantity that fixes reciprocal-lattice density."""
    return conventional_volume(cell) / CENTERING[centering][1]


def predicted_two_theta(cell, centering, lam, tth_min, tth_max, hkl_max=12, tol=1e-3):
    """All distinct 2theta predicted by `cell` with `centering`, within range.

    Returns {2theta: representative (h,k,l)}. Reflections coinciding in d-spacing
    collapse to one entry, which is what a powder pattern actually shows.
    """
    Gstar = np.linalg.inv(metric_tensor(*cell))
    allowed = CENTERING[centering][0]
    smin, smax = (np.sin(np.radians(t / 2.0)) for t in (tth_min, tth_max))
    out: dict[float, tuple[int, int, int]] = {}
    rng = range(-hkl_max, hkl_max + 1)
    for h, k, l in itertools.product(rng, rng, rng):
        if h == 0 and k == 0 and l == 0 or not allowed(h, k, l):
            continue
        v = np.array([h, k, l])
        inv_d2 = float(v @ Gstar @ v)
        if inv_d2 <= 0:
            continue
        s = lam * np.sqrt(inv_d2) / 2.0  # sin(theta)
        if smin <= s <= smax:
            tth = 2.0 * np.degrees(np.arcsin(s))
            out.setdefault(round(tth / tol) * tol, (h, k, l))
    return out


def observe(x, y, tth, half_width, bkg_half_width=0.9, bkg_pct=20):
    """Observed max, local background and net intensity at a predicted position."""
    m = (x >= tth - half_width) & (x <= tth + half_width)
    if not m.any():
        return None
    bm = (x >= tth - bkg_half_width) & (x <= tth + bkg_half_width)
    bkg = float(np.percentile(y[bm], bkg_pct)) if bm.any() else 0.0
    obs = float(y[m].max())
    return obs, bkg, obs - bkg


def classify(vp1, vp2, tol=0.02):
    """Relationship between two lattices from their primitive volumes.

    Returns (kind, factor) with kind in {'same', 'integer', 'unrelated'}.
    """
    lo, hi = sorted((vp1, vp2))
    ratio = hi / lo
    if abs(ratio - 1.0) <= tol:
        return "same", 1.0
    nearest = round(ratio)
    if nearest >= 2 and abs(ratio - nearest) <= tol * nearest:
        return "integer", float(nearest)
    return "unrelated", ratio


def report_unique(label, positions, source, other_name, x, y, args):
    """Print the observed intensity at reflections unique to one cell."""
    print(f"\n  --- {len(positions)} positions predicted by {label} but NOT by {other_name} ---")
    print(f"  {'2theta':>9} {'hkl':>12} {'obs':>10} {'bkg':>9} {'net':>9}   verdict")
    n_present = n_checked = 0
    for tth in positions:
        got = observe(x, y, tth, args.peak_half_width)
        if got is None:
            continue
        obs, bkg, net = got
        n_checked += 1
        present = net >= args.present_threshold * max(np.sqrt(max(bkg, 1.0)), 1.0)
        n_present += present
        print(f"  {tth:9.3f} {str(source[tth]):>12} {obs:10.1f} {bkg:9.1f} {net:9.1f}   "
              f"{'PRESENT' if present else 'absent'}")
    return n_present, n_checked


def compare_pair(name1, cell1, cent1, name2, cell2, cent2, x, y, args):
    vc1, vc2 = conventional_volume(cell1), conventional_volume(cell2)
    vp1, vp2 = primitive_volume(cell1, cent1), primitive_volume(cell2, cent2)

    print(f"\n{'=' * 78}\n{name1} vs {name2}\n{'=' * 78}")
    for nm, ct, vc, vp in ((name1, cent1, vc1, vp1), (name2, cent2, vc2, vp2)):
        print(f"  {nm}: {ct}-centred   V_conv={vc:9.2f}   V_primitive={vp:9.2f} A^3")
    print(f"  conventional-volume ratio = {max(vc1, vc2) / min(vc1, vc2):.4f}")
    print(f"  PRIMITIVE-volume  ratio   = {max(vp1, vp2) / min(vp1, vp2):.4f}   <- the one that matters")

    kind, factor = classify(vp1, vp2)

    if kind == "same":
        print("""
  VERDICT: SAME LATTICE -- exact metric re-description (case 2).
  These cells contain lattice points at identical density and predict the SAME
  reflection positions. They are two conventional descriptions of one lattice,
  not competing hypotheses. No GoF / M20 / F30 value can discriminate between
  them; a GoF difference is an artefact of how many reflections each predicts.
  Deciding between them is choosing a POINT GROUP, which requires INTENSITIES:
  run a Pawley/Le Bail refinement at each candidate symmetry and compare, or
  solve the structure. Until then report the LATTICE as determined and the
  SPACE GROUP as an explicitly unresolved set.""")
        return

    if kind == "unrelated":
        print(f"\n  VERDICT: cells are not simply related (primitive-volume ratio {factor:.4f}\n"
              "  is not an integer). This script has nothing to add; use the normal criteria.")
        return

    # Integer ratio: the sparser direct lattice predicts the extra reflections.
    big_is_1 = vp1 > vp2
    big_name, big_cell, big_cent = (name1, cell1, cent1) if big_is_1 else (name2, cell2, cent2)
    small_name = name2 if big_is_1 else name1
    print(f"\n  VERDICT: SUPERCELL / SUBSTRUCTURE relationship (case 1), factor {factor:g}.\n"
          f"  {big_name} has the sparser direct lattice, so it predicts the extra\n"
          f"  (superlattice) reflections. {small_name} indexes a substructure of it.")

    p_big = predicted_two_theta(big_cell, big_cent, args.lam, args.tth_min, args.tth_max, args.hkl_max)
    small_cell, small_cent = (cell2, cent2) if big_is_1 else (cell1, cent1)
    p_small = predicted_two_theta(small_cell, small_cent, args.lam, args.tth_min, args.tth_max, args.hkl_max)
    small_pos = list(p_small)
    only_big = sorted(t for t in p_big if not any(abs(t - p) <= args.match_tol for p in small_pos))

    if not only_big:
        print("  (No superlattice positions fall in the measured range -- nothing to test.)")
        return

    n_present, n_checked = report_unique(big_name, only_big, p_big, small_name, x, y, args)
    if not n_checked:
        return

    frac = n_present / n_checked
    print(f"\n  {n_present}/{n_checked} ({frac:.0%}) of the superlattice reflections unique to "
          f"{big_name} are present.")
    if frac >= args.decide_frac or n_present >= args.min_present:
        print(f"""
  => DECISIVE FOR {big_name}. Centering can never create a reflection, so lines
     that {small_name} cannot index but which are observed are direct evidence of
     the larger lattice. Adopt {big_name} and re-run indexing with these lines
     included in the peak list.""")
    else:
        print(f"""
  => NOT DECIDED, and deliberately so. Few/no superlattice reflections are
     observed, but that is NOT evidence for {small_name}: glide and screw
     extinctions of {big_name}'s space group produce exactly the same absences,
     as does a genuinely weak superstructure. Distinguishing "wrong lattice"
     from "right lattice, extinct by symmetry" is what TOPAS's extinction-
     subgroup search does -- use its ranking, not this script, for that call.
     What you CAN conclude: nothing here forces the larger cell.""")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("yobs_file")
    ap.add_argument("--lam", type=float, default=1.540596, help="wavelength (A), default Cu Ka1")
    ap.add_argument("--cell", nargs=7, action="append", metavar="V",
                    required=True, help="NAME a b c alpha beta gamma (repeatable)")
    ap.add_argument("--centering", nargs=2, action="append", metavar="V",
                    help="NAME P|I|F|A|B|C|R (default P for any cell not listed)")
    ap.add_argument("--tth-min", type=float, help="default: data min")
    ap.add_argument("--tth-max", type=float, help="default: data max")
    ap.add_argument("--hkl-max", type=int, default=12)
    ap.add_argument("--match-tol", type=float, default=0.05,
                    help="two predicted positions are the same line within this many degrees "
                         "(default 0.05)")
    ap.add_argument("--peak-half-width", type=float, default=0.10,
                    help="half-width of the window searched for an observed peak (default 0.10)")
    ap.add_argument("--present-threshold", type=float, default=3.0,
                    help="net must exceed this many sqrt(bkg) to count as PRESENT (default 3.0)")
    ap.add_argument("--decide-frac", type=float, default=0.6,
                    help="fraction of superlattice reflections present before calling it "
                         "(default 0.6)")
    ap.add_argument("--min-present", type=int, default=3,
                    help="this many unambiguously present superlattice reflections is decisive "
                         "regardless of fraction (default 3)")
    args = ap.parse_args(argv)

    data = np.loadtxt(args.yobs_file)
    x, y = data[:, 0], data[:, 1]
    if args.tth_min is None:
        args.tth_min = float(x.min())
    if args.tth_max is None:
        args.tth_max = float(x.max())

    cents = {n: c.upper() for n, c in (args.centering or [])}
    cells = {}
    for entry in args.cell:
        name, vals = entry[0], [float(v) for v in entry[1:]]
        cells[name] = tuple(vals)
        cents.setdefault(name, "P")
        if cents[name] not in CENTERING:
            ap.error(f"unknown centering {cents[name]!r} for cell {name}")
    if len(cells) < 2:
        ap.error("give at least two --cell entries to compare")

    print(f"# {args.yobs_file}: {len(x)} points, {x.min():.2f}-{x.max():.2f} deg, "
          f"lambda = {args.lam} A")
    for n1, n2 in itertools.combinations(cells, 2):
        compare_pair(n1, cells[n1], cents[n1], n2, cells[n2], cents[n2], x, y, args)


if __name__ == "__main__":
    sys.exit(main())
