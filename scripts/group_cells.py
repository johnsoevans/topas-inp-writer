"""
group_cells.py -- collapse a TOPAS indexing .ndx list into lattice families.

An indexing run reports the same lattice many times over: in different settings
(axis swaps, sign flips giving supplementary angles, alternative triclinic
bases), with and without centring, and at slightly different refined values.
Ranked row by row, a 500-line .ndx looks like hundreds of competing answers
when it holds tens of distinct lattices. This script groups them.

Method
------
1. Every row is converted to its PRIMITIVE cell (centring taken from the first
   letter of the space-group symbol: P A B C I F R; R = obverse, hexagonal
   axes) and Niggli-reduced (Krivy-Gruber, epsilon-tolerant form of
   Grosse-Kunstleve et al. 2004, Acta Cryst. A60, 1-6).
2. Two rows are the SAME LATTICE when some unimodular integer matrix with
   entries in {-1, 0, 1} maps one reduced metric onto the other within
   --tol. Comparing through that matrix search rather than by reduced
   parameters directly avoids the discontinuities of Niggli reduction near its
   boundary conditions (angles near 90 deg, near-equal axes), where two noisy
   copies of one lattice can reduce to different-looking cells.
3. Each family's METRIC SYMMETRY (holohedry) is the group of such matrices that
   leave its own reduced metric unchanged within --sym-tol. A triclinic
   solution whose lattice is metrically monoclinic or higher shows up here.
4. Families whose primitive volumes differ by an integer factor n <= --max-index
   are tested for a SUPERCELL relation: every index-n sublattice of the
   smaller lattice (enumerated by Hermite normal form) is reduced and compared
   with the larger one. Only pairs involving a printed (--top) family are
   tested.

Speed
-----
Only the best --max-rows rows by GoF are read (default 300; --all for every
row). A full .ndx holds thousands of rows, most of them one-off low-GoF
lattices, and the family and supercell searches grow with the square of the
family count -- a 3000-row file can run for a very long time. The leading
families come from the top rows, so the cap does not change them; it can drop
low-ranked members (and so raise a family's minUNI). Progress goes to stderr.

What it does not do
-------------------
It says which rows are the same lattice and how distinct lattices are related.
It does not choose between genuinely different lattices -- that still needs
GoF, the supercell tests of compare_cells.py, and Pawley fits. Space-group
labels are kept per family, not merged: the same lattice reported as C2 and
P-1 is one lattice with two symmetry hypotheses.

Usage:
    python group_cells.py result.ndx
    python group_cells.py result.ndx --tol 0.003 --top 20 --members
    python group_cells.py result.ndx --all          # every row (slow on large files)
"""
from __future__ import annotations

import argparse
import bisect
import itertools
import re
import sys
from collections import Counter

import numpy as np

# Rows = primitive basis vectors in fractional coordinates of the conventional cell.
PRIMITIVE = {
    "P": np.eye(3),
    "A": np.array([[1, 0, 0], [0, .5, .5], [0, -.5, .5]]),
    "B": np.array([[.5, 0, .5], [0, 1, 0], [-.5, 0, .5]]),
    "C": np.array([[.5, .5, 0], [-.5, .5, 0], [0, 0, 1]]),
    "I": np.array([[-.5, .5, .5], [.5, -.5, .5], [.5, .5, -.5]]),
    "F": np.array([[0, .5, .5], [.5, 0, .5], [.5, .5, 0]]),
    "R": np.array([[2, 1, 1], [-1, 1, 1], [-1, -2, 1]]) / 3.0,  # obverse, hexagonal axes
}

# Order of the lattice point group -> holohedry.
HOLOHEDRY = {2: "triclinic", 4: "monoclinic", 8: "orthorhombic",
             12: "rhombohedral", 16: "tetragonal", 24: "hexagonal", 48: "cubic"}

# A solution row, across TOPAS versions. Two things vary with the writing version:
#   * an optional leading rank, "  0) P2 ..." (TOPAS 7) vs a bare "P2 ..." (TOPAS 9);
#   * an optional extra Status integer between the symbol and UNI -- the v7 header
#     reads "'Sg Status UNI Vol Gof Zero Lps..." where v9 omits Status.
# So capture only the space-group symbol here and let parse_ndx() decide the rest by
# column count. The pattern is deliberately loose, which means it also matches lines
# like "Indexing_Solutions_With_Zero_Error_2 {" -- parse_ndx() rejects those when the
# numeric conversion fails, rather than the pattern trying to exclude them.
ROW = re.compile(r"^\s*(?:\d+\)\s*)?([A-Za-z]\S*)\s+(.*)$")


def metric(a, b, c, al, be, ga):
    """Direct-space metric tensor; cell in Angstrom and degrees."""
    ca, cb, cg = np.cos(np.radians([al, be, ga]))
    return np.array([[a * a, a * b * cg, a * c * cb],
                     [a * b * cg, b * b, b * c * ca],
                     [a * c * cb, b * c * ca, c * c]])


def cell_params(G):
    a, b, c = np.sqrt(np.diag(G))
    al = np.degrees(np.arccos(G[1, 2] / (b * c)))
    be = np.degrees(np.arccos(G[0, 2] / (a * c)))
    ga = np.degrees(np.arccos(G[0, 1] / (a * b)))
    return a, b, c, al, be, ga


def niggli(G, rel_eps=1e-5):
    """Niggli-reduced metric (Krivy-Gruber on the G6 vector, epsilon-tolerant)."""
    A, B, C = G[0, 0], G[1, 1], G[2, 2]
    xi, eta, zeta = 2 * G[1, 2], 2 * G[0, 2], 2 * G[0, 1]
    eps = rel_eps * np.sqrt(abs(np.linalg.det(G))) ** (2 / 3)

    def sgn(x):
        return 1 if x > eps else (-1 if x < -eps else 0)

    for _ in range(1000):
        if A > B + eps or (abs(A - B) <= eps and abs(xi) > abs(eta) + eps):
            A, B, xi, eta = B, A, eta, xi
        if B > C + eps or (abs(B - C) <= eps and abs(eta) > abs(zeta) + eps):
            B, C, eta, zeta = C, B, zeta, eta
            continue
        # Axis sign flips change two of (xi, eta, zeta) at once, so only the sign of
        # the product is fixed: positive -> all positive, otherwise all non-positive.
        if sgn(xi) * sgn(eta) * sgn(zeta) == 1:
            xi, eta, zeta = abs(xi), abs(eta), abs(zeta)
        else:
            xi, eta, zeta = -abs(xi), -abs(eta), -abs(zeta)
        if abs(xi) > B + eps or (abs(xi - B) <= eps and 2 * eta < zeta - eps) \
                or (abs(xi + B) <= eps and zeta < -eps):
            s = np.sign(xi)
            C, eta, xi = B + C - xi * s, eta - zeta * s, xi - 2 * B * s
            continue
        if abs(eta) > A + eps or (abs(eta - A) <= eps and 2 * xi < zeta - eps) \
                or (abs(eta + A) <= eps and zeta < -eps):
            s = np.sign(eta)
            C, xi, eta = A + C - eta * s, xi - zeta * s, eta - 2 * A * s
            continue
        if abs(zeta) > A + eps or (abs(zeta - A) <= eps and 2 * xi < eta - eps) \
                or (abs(zeta + A) <= eps and eta < -eps):
            s = np.sign(zeta)
            B, xi, zeta = A + B - zeta * s, xi - eta * s, zeta - 2 * A * s
            continue
        t = xi + eta + zeta + A + B
        if t < -eps or (abs(t) <= eps and 2 * (A + eta) + zeta > eps):
            C, xi, eta = A + B + C + xi + eta + zeta, 2 * B + xi + zeta, 2 * A + eta + zeta
            continue
        break
    return np.array([[A, zeta / 2, eta / 2], [zeta / 2, B, xi / 2], [eta / 2, xi / 2, C]])


def _unimodular():
    m = np.array(list(itertools.product((-1, 0, 1), repeat=9))).reshape(-1, 3, 3)
    d = np.rint(np.linalg.det(m))
    return m[np.abs(d) == 1].astype(float)


UNIMODULAR = _unimodular()
UNIMODULAR_T = UNIMODULAR.transpose(0, 2, 1)


def transforms(G):
    """G under every small unimodular basis change."""
    return UNIMODULAR @ G @ UNIMODULAR_T


def mismatch(T1, G2):
    """Smallest normalised metric difference between G2 and any of transforms(G1)."""
    norm = np.sqrt(np.outer(np.diag(G2), np.diag(G2)))
    return np.abs((T1 - G2) / norm).max(axis=(1, 2)).min()


def metric_ops(G, tol):
    """Lattice point-group operations of G (integer matrices acting on row coefficients)."""
    T = transforms(G)
    norm = np.sqrt(np.outer(np.diag(G), np.diag(G)))
    return UNIMODULAR[np.abs((T - G) / norm).max(axis=(1, 2)) <= tol].astype(int)


# Small integer lattice vectors (coefficients in the reduced primitive basis).
_R = range(-4, 5)
SMALL = np.array([v for v in itertools.product(_R, _R, _R) if any(v)])

# Centring translations (conventional fractional coordinates) tested in this order.
CENTRING_TESTS = [("A", [0, .5, .5]), ("B", [.5, 0, .5]), ("C", [.5, .5, 0]),
                  ("I", [.5, .5, .5]), ("Robv", [2 / 3, 1 / 3, 1 / 3]),
                  ("Rrev", [1 / 3, 2 / 3, 1 / 3])]


def _order(M):
    X = np.eye(3, dtype=int)
    for k in range(1, 7):
        X = X @ M
        if (X == np.eye(3, dtype=int)).all():
            return k
    return 0


def _shortest(vs, G):
    return vs[np.argmin(np.einsum("ni,ij,nj->n", vs, G, vs))]


def _axis(M, G):
    """Shortest lattice vector along the rotation axis of M."""
    return _shortest(SMALL[(SMALL @ M == SMALL).all(axis=1)], G)


def _plane(M, G):
    """Lattice vectors perpendicular to the axis of rotation M, shortest first."""
    n = _order(M)
    s, X = np.zeros_like(SMALL), SMALL.copy()
    for _ in range(n):
        s, X = s + X, X @ M
    vs = SMALL[(s == 0).all(axis=1)]
    return vs[np.argsort(np.einsum("ni,ij,nj->n", vs, G, vs), kind="stable")]


def _centring(C):
    """Lattice-centring letter of conventional basis C (rows, in primitive coordinates)."""
    ok = {name for name, t in CENTRING_TESTS
          if np.allclose(np.array(t) @ C, np.rint(np.array(t) @ C), atol=1e-6)}
    if {"A", "B", "C"} <= ok:
        return "F"
    for name in ("C", "A", "B", "I", "Robv", "Rrev"):
        if name in ok:
            return name
    return "P"


def conventional_cell(G, ops, holo):
    """Conventional cell (centring, a b c al be ga) in the setting of the metric symmetry."""
    rot = [M for M in ops if round(np.linalg.det(M)) == 1]
    by_order = {k: [M for M in rot if _order(M) == k] for k in (2, 3, 4, 6)}
    G_ = G
    try:
        if holo == "monoclinic":
            M = by_order[2][0]
            b = _axis(M, G_)
            pl = _plane(M, G_)
            a = pl[0]
            c = next(v for v in pl[1:] if np.any(np.cross(a, v)))
            C = np.array([a, b, c])
            if a @ G_ @ c > 0:          # obtuse beta
                C[2] = -C[2]
        elif holo == "orthorhombic":
            axes = [_axis(M, G_) for M in by_order[2]]
            C = np.array(sorted(axes, key=lambda v: v @ G_ @ v))
        elif holo == "tetragonal":
            M = by_order[4][0]
            a = _plane(M, G_)[0]
            C = np.array([a, a @ M, _axis(M, G_)])
        elif holo in ("hexagonal", "rhombohedral"):
            M = by_order[6][0] @ by_order[6][0] if holo == "hexagonal" else by_order[3][0]
            a = _plane(M, G_)[0]
            C = np.array([a, a @ M, _axis(M, G_)])
        elif holo == "cubic":
            axes = []
            for M in by_order[4]:
                u = _axis(M, G_)
                if not any(np.all(u == w) or np.all(u == -w) for w in axes):
                    axes.append(u)
            C = np.array(axes[:3])
        else:
            C = np.eye(3, dtype=int)
    except (IndexError, StopIteration):
        return "?", cell_params(G)
    if np.linalg.det(C) < 0:
        # Right-handed basis: flip the vector whose sign leaves the angles unchanged.
        k = 1 if holo == "monoclinic" else 2
        C[k] = -C[k]
    cen = _centring(C)
    if cen == "Rrev":                   # rotate 180 deg about c: reverse -> obverse
        C[0], C[1] = -C[0], -C[1]
        cen = _centring(C)
    if holo == "monoclinic" and cen == "A":   # prefer the C-centred setting
        C = np.array([C[2], -C[1], C[0]])
        cen = _centring(C)
    return cen.replace("obv", "").replace("rev", ""), cell_params(C @ G @ C.T)


def hnf(n):
    """All Hermite-normal-form matrices of determinant n (index-n sublattices)."""
    out = []
    for a in range(1, n + 1):
        for c in range(1, n + 1):
            if n % (a * c):
                continue
            f = n // (a * c)
            # Off-diagonals are reduced modulo the pivot of their own column.
            for b in range(a):
                for d in range(a):
                    for e in range(c):
                        out.append(np.array([[a, 0, 0], [b, c, 0], [d, e, f]], float))
    return out


def parse_ndx(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for rank, line in enumerate(l for l in fh if ROW.match(l.split("'")[0])):
            m = ROW.match(line.split("'")[0])
            try:
                nums = [float(x) for x in m.group(2).split()]
            except ValueError:
                continue              # a header/brace line the loose ROW pattern let through
            if len(nums) == 11:       # Status UNI Vol GoF Zero + 6 lattice parameters (TOPAS 7)
                uni, vol, gof, zero, cell = nums[1], nums[2], nums[3], nums[4], nums[5:]
            elif len(nums) == 10:     # UNI Vol GoF Zero + 6 lattice parameters (TOPAS 9)
                uni, vol, gof, zero, cell = nums[0], nums[1], nums[2], nums[3], nums[4:]
            elif len(nums) == 9:      # UNI Vol GoF + 6, no zero-error column
                uni, vol, gof, zero, cell = nums[0], nums[1], nums[2], 0.0, nums[3:]
            else:
                continue
            rows.append(dict(rank=rank, sg=m.group(1), uni=int(uni),
                             vol=vol, gof=gof, zero=zero, cell=cell))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ndx")
    ap.add_argument("--tol", type=float, default=0.005,
                    help="max normalised metric difference for same lattice (default 0.005, "
                         "~0.25%% in length, ~0.3 deg in angle)")
    ap.add_argument("--sym-tol", type=float, default=0.005,
                    help="tolerance for metric (holohedry) symmetry (default 0.005)")
    ap.add_argument("--max-index", type=int, default=4,
                    help="largest supercell index tested between families (default 4)")
    ap.add_argument("--top", type=int, default=0, help="print only the top N families")
    ap.add_argument("--members", action="store_true", help="list the .ndx ranks in each family")
    ap.add_argument("--max-rows", type=int, default=300,
                    help="read only the best N rows by GoF (default 300; see Speed)")
    ap.add_argument("--all", action="store_true", help="read every row, ignoring --max-rows")
    args = ap.parse_args(argv)

    rows = parse_ndx(args.ndx)
    if not rows:
        sys.exit(f"No solution rows found in {args.ndx}")
    n_total = len(rows)
    if not args.all and args.max_rows and n_total > args.max_rows:
        # Keep the best rows by GoF, then restore file order so family numbering is unchanged.
        rows = sorted(sorted(rows, key=lambda r: -r["gof"])[:args.max_rows],
                      key=lambda r: r["rank"])
    print(f"grouping {len(rows)} of {n_total} rows ...", file=sys.stderr)

    families = []   # each: dict(G, vol, rows)
    by_vol = []     # (vol, family index), sorted, so only families of similar volume are tested
    for r in rows:
        P = PRIMITIVE.get(r["sg"][0].upper())
        if P is None:
            print(f"warning: unknown centring in {r['sg']!r}, rank {r['rank']}; treated as P",
                  file=sys.stderr)
            P = np.eye(3)
        G = niggli(P @ metric(*r["cell"]) @ P.T)
        vol = np.sqrt(np.linalg.det(G))
        r["G"], r["pvol"] = G, vol
        lo = bisect.bisect_right(by_vol, (vol * (1 - 3 * args.tol), -1))
        hi = bisect.bisect_left(by_vol, (vol * (1 + 3 * args.tol), len(families) + 1))
        for i in sorted(i for _, i in by_vol[lo:hi]):    # creation order, as a linear scan would
            fam = families[i]
            if abs(fam["vol"] - vol) / vol < 3 * args.tol and mismatch(fam["T"], G) <= args.tol:
                fam["rows"].append(r)
                break
        else:
            bisect.insort(by_vol, (vol, len(families)))
            families.append(dict(G=G, T=transforms(G), vol=vol, rows=[r]))

    for i, fam in enumerate(families, 1):
        fam["id"] = f"F{i}"
        fam["best"] = max(fam["rows"], key=lambda r: r["gof"])

    families.sort(key=lambda f: -f["best"]["gof"])
    shown = families[:args.top] if args.top else families
    for fam in shown:
        ops = metric_ops(fam["G"], args.sym_tol)
        fam["holo"] = HOLOHEDRY.get(len(ops), f"order {len(ops)}?")
        fam["conv"] = conventional_cell(fam["G"], ops, fam["holo"])

    # Supercell relations: only pairs involving a printed family.
    print(f"{len(families)} families; testing supercell relations for {len(shown)} ...",
          file=sys.stderr)
    shown_ids = {f["id"] for f in shown}
    relations = []
    for s, l in itertools.permutations(families, 2):
        if s["id"] not in shown_ids and l["id"] not in shown_ids:
            continue
        ratio = l["vol"] / s["vol"]
        n = round(ratio)
        if not 2 <= n <= args.max_index or abs(ratio - n) > n * 3 * args.tol:
            continue
        for H in hnf(n):
            if mismatch(l["T"], niggli(H @ s["G"] @ H.T)) <= args.tol:
                relations.append((l["id"], n, s["id"]))
                break

    capped = f" (best {len(rows)} of {n_total} rows by GoF; --all for every row)" \
        if len(rows) < n_total else ""
    print(f"{args.ndx}: {len(rows)} solutions -> {len(families)} distinct lattices "
          f"(tol {args.tol}, sym-tol {args.sym_tol}){capped}\n")
    hdr = (f"{'fam':>5} {'n':>4} {'bestGoF':>7} {'rank':>5} {'minUNI':>6} {'Vprim':>9}  "
           f"{'reduced primitive cell':<50} {'metric sym':<13} "
           f"{'conventional cell (metric-symmetry setting)':<54} space groups (count)")
    print(hdr)
    print("-" * len(hdr))
    for fam in shown:
        a, b, c, al, be, ga = cell_params(fam["G"])
        cen, (A, B, C, AL, BE, GA) = fam["conv"]
        sgs = Counter(r["sg"] for r in fam["rows"])
        sgtxt = ", ".join(f"{k}({v})" for k, v in sgs.most_common())
        print(f"{fam['id']:>5} {len(fam['rows']):>4} {fam['best']['gof']:>7.2f} "
              f"{fam['best']['rank']:>5} {min(r['uni'] for r in fam['rows']):>6} {fam['vol']:>9.1f}  "
              f"{a:7.3f} {b:7.3f} {c:7.3f} {al:7.2f} {be:7.2f} {ga:7.2f}   "
              f"{fam['holo']:<13} "
              f"{cen:<2}{A:8.3f}{B:8.3f}{C:8.3f}{AL:7.2f}{BE:7.2f}{GA:7.2f}      {sgtxt}")
        if args.members:
            print(f"{'':>6}ranks: {' '.join(str(r['rank']) for r in fam['rows'])}")

    if relations:
        print("\nSupercell relations (larger lattice = index-n sublattice of smaller):")
        best = {f["id"]: f["best"]["gof"] for f in families}
        for big, n, small in sorted(relations, key=lambda t: -max(best[t[0]], best[t[2]])):
            print(f"  {big} (GoF {best[big]:.2f}) is an index-{n} supercell of "
                  f"{small} (GoF {best[small]:.2f})")
    else:
        print(f"\nNo supercell relations up to index {args.max_index}.")


if __name__ == "__main__":
    main()
