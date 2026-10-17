"""Build z-matrix rigid bodies for TOPAS from a CIF.

Deliberately split into separate commands, because only SOME of this job is mechanical:

  --analyse <cif>    Does the arithmetic and reports it.  Decides nothing.
  --build <spec>     Emits the `rigid` block from a spec YOU write.  Infers nothing.
  --verify <spec>    Runs the two checks that actually catch a wrong rigid body.
  --risk <cif>       Advisory special-position precision audit.  Alters nothing.

The split is the point.  `--build` will not accept the output of `--analyse` directly:
choosing which fragments are rigid, what to exclude, and how much placement freedom
symmetry plus rigidity really permit are judgement calls that need a look at the
structure.  What this script owns is the arithmetic that is easy to get wrong by hand
and that produces a plausible-looking .inp when it IS wrong:

  * the local frame, orthonormal and derived from the 3rd z-matrix atom rather than a
    fragment-wide best-fit plane (see the atom-3 placement corollary in
    references/28-z-matrix-rigid-body-conventions.md)
  * TOPAS's dihedral sign convention
  * the azimuth reference ordered as the first real atom placed
  * snapping an in-plane atom's dihedral to exactly 0 or 180
  * 12-decimal-place output, and a FRACTIONAL translate so a component fixed on a
    special plane stays there when the cell refines
  * the `load z_matrix { }` wrapper
  * a round-trip assertion against the source coordinates

Symmetry analysis and CIF parsing are reused from symmetry_utils.py / cif_to_str.py
rather than reimplemented, so this agrees with `cif_to_str.py`'s own Wyckoff
derivation by construction.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import cif_to_str as c2s
import symmetry_utils as su
import topas_install

TOL = 1e-4
DIH_SIGN = -1.0   # TOPAS convention, verified against tc.exe/Out_CIF_STR


def note(*a):
    """Diagnostics go to stderr so that --build's stdout stays pure .inp text and
    can be pasted or redirected straight into a file."""
    print(*a, file=sys.stderr)

# approximate covalent radii, for connectivity only -- not bond-length analysis
COV = {
    "H": 0.31, "B": 0.84, "C": 0.76, "N": 0.71, "O": 0.66, "F": 0.57, "Si": 1.11,
    "P": 1.07, "S": 1.05, "Cl": 1.02, "Br": 1.20, "I": 1.39, "Se": 1.20, "As": 1.19,
    "Li": 1.28, "Na": 1.66, "K": 2.03, "Rb": 2.20, "Cs": 2.44, "Be": 0.96,
    "Mg": 1.41, "Ca": 1.76, "Sr": 1.95, "Ba": 2.15,
}
COV_DEFAULT = 1.40      # generous, so a metal-ligand contact is seen and can be judged

METALS = set("""Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo
Tc Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re
Os Ir Pt Au Hg Tl Pb Bi Fr Ra Ac Th Pa U Np Pu""".split())


# --------------------------------------------------------------------------
# vector helpers
# --------------------------------------------------------------------------
def sub(a, b): return tuple(a[i] - b[i] for i in range(3))
def add(a, b): return tuple(a[i] + b[i] for i in range(3))
def mul(a, s): return tuple(x * s for x in a)
def dot(a, b): return sum(a[i] * b[i] for i in range(3))
def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def norm(a): return math.sqrt(dot(a, a))
def unit(a):
    n = norm(a)
    if n < 1e-12:
        raise ValueError("cannot normalise a zero-length vector")
    return tuple(x / n for x in a)


def cell_vectors(a, b, c, al, be, ga):
    """ref 13: x || a, y in the a-b plane, z along a x b."""
    al, be, ga = (math.radians(v) for v in (al, be, ga))
    va = (a, 0.0, 0.0)
    vb = (b*math.cos(ga), b*math.sin(ga), 0.0)
    cx = c*math.cos(be)
    cy = c*(math.cos(al) - math.cos(be)*math.cos(ga))/math.sin(ga)
    cz = math.sqrt(max(c*c - cx*cx - cy*cy, 0.0))
    return va, vb, (cx, cy, cz)


def make_converters(cell):
    va, vb, vc = cell_vectors(*cell)
    M = [[va[0], vb[0], vc[0]], [va[1], vb[1], vc[1]], [va[2], vb[2], vc[2]]]
    det = (M[0][0]*(M[1][1]*M[2][2]-M[1][2]*M[2][1])
           - M[0][1]*(M[1][0]*M[2][2]-M[1][2]*M[2][0])
           + M[0][2]*(M[1][0]*M[2][1]-M[1][1]*M[2][0]))

    def to_cart(f):
        return tuple(f[0]*va[i] + f[1]*vb[i] + f[2]*vc[i] for i in range(3))

    def to_frac(p):
        def cof(i, j):
            m = [[M[r][cc] for cc in range(3) if cc != j] for r in range(3) if r != i]
            return ((-1)**(i+j))*(m[0][0]*m[1][1]-m[0][1]*m[1][0])
        return tuple(sum(cof(j, i)*p[j] for j in range(3))/det for i in range(3))

    return to_cart, to_frac, (va, vb, vc)


def rotv(v, ax, deg):
    t = math.radians(deg)
    c_, s_ = math.cos(t), math.sin(t)
    return add(add(mul(v, c_), mul(cross(ax, v), s_)), mul(ax, dot(ax, v)*(1-c_)))


# --------------------------------------------------------------------------
# CIF ingestion -- reuses cif_to_str/symmetry_utils so the symmetry analysis
# agrees with `cif_to_str.py` by construction rather than by coincidence
# --------------------------------------------------------------------------
def load_cif(path):
    lines = c2s.read_cif_lines(path)

    def scalar(*tags):
        for t in tags:
            v = c2s.find_scalar_tag(lines, t)
            if v is not None:
                return v
        return None

    cell = [float(c2s.strip_cif_uncertainty(scalar("_cell_length_" + k)))
            for k in ("a", "b", "c")]
    angles = [float(c2s.strip_cif_uncertainty(scalar("_cell_angle_" + k)))
              for k in ("alpha", "beta", "gamma")]
    sg = scalar("_symmetry_space_group_name_H-M", "_space_group_name_H-M_alt")
    sg = (sg or "").strip().strip("'\"")

    ops = None
    for key in ("_symmetry_equiv_pos_as_xyz", "_space_group_symop_operation_xyz"):
        _tags, loop = c2s.parse_cif_loop(lines, [key])
        if loop:
            ops = [su.parse_symop_string(r[key].strip().strip("'\"")) for r in loop]
            ops, added = su.complete_centering_operators(ops, sg, angles)
            if added:
                note("  note: %d centering-translated operators added to the CIF's "
                      "own list" % added)
            break
    if not ops:
        ops = su.resolve_sg_operators(sg)
        if isinstance(ops, tuple):
            ops = ops[0]
    if not ops:
        raise SystemExit("could not resolve symmetry operators for space group %r" % sg)

    _tags, rows = c2s.parse_cif_loop(
        lines, ["_atom_site_label", "_atom_site_fract_x",
                "_atom_site_fract_y", "_atom_site_fract_z"])
    rows = rows or []
    atoms = []
    for r in rows:
        lab = r["_atom_site_label"].strip()
        try:
            p = tuple(c2s.parse_fract_coord(r["_atom_site_fract_" + k])
                      for k in ("x", "y", "z"))
        except Exception:
            continue
        el = (r.get("_atom_site_type_symbol") or "").strip() or \
            c2s.guess_element_symbol(lab)
        el = re.sub(r"[^A-Za-z].*$", "", el).capitalize()
        occ = r.get("_atom_site_occupancy", "1")
        try:
            occ = float(c2s.strip_cif_uncertainty(occ))
        except Exception:
            occ = 1.0
        atoms.append(dict(label=lab, elem=el, frac=p, occ=occ))

    # drop symmetry duplicates: a CIF often lists every copy of a fragment under
    # its own label.  Keep the first of each orbit.
    kept, dup_of = [], {}
    for a in atoms:
        hit = None
        for k in kept:
            if k["elem"] != a["elem"]:
                continue
            for op in ops:
                q = su.apply_symop(op[0], op[1], k["frac"])
                if su.points_equal_mod1(q, a["frac"], 2e-3):
                    hit = k["label"]
                    break
            if hit:
                break
        if hit:
            dup_of[a["label"]] = hit
        else:
            kept.append(a)

    for a in kept:
        stab = su.find_stabilizer(a["frac"], ops, TOL)
        a["stabilizer"] = stab
        a["mult"] = su.check_multiplicity(a["frac"], ops, stab)
    return dict(path=path, cell=tuple(cell + angles), sg=sg, ops=ops,
                atoms=kept, dup_of=dup_of, general_mult=len(ops))


# --------------------------------------------------------------------------
# connectivity, across symmetry (a ring may close through an operator)
# --------------------------------------------------------------------------
def bonds(info, scale=1.20):
    to_cart, _, (va, vb, vc) = make_converters(info["cell"])
    atoms = info["atoms"]
    out = {}
    for i, a in enumerate(atoms):
        for j, b in enumerate(atoms):
            if j < i:
                continue
            best, via = None, None
            for op in info["ops"]:
                q0 = su.apply_symop(op[0], op[1], b["frac"])
                for sx in (-1, 0, 1):
                    for sy in (-1, 0, 1):
                        for sz in (-1, 0, 1):
                            q = (q0[0]+sx, q0[1]+sy, q0[2]+sz)
                            d = norm(sub(to_cart(a["frac"]), to_cart(q)))
                            if d < 0.4:
                                continue
                            if best is None or d < best:
                                best, via = d, (op, (sx, sy, sz))
            if best is None:
                continue
            cut = scale*(COV.get(a["elem"], COV_DEFAULT) + COV.get(b["elem"], COV_DEFAULT))
            if best <= cut:
                out[(a["label"], b["label"])] = (best, via)
    return out


def components(labels, bond_keys):
    parent = {l: l for l in labels}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in bond_keys:
        if u in parent and v in parent:
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
    groups = {}
    for l in labels:
        groups.setdefault(find(l), []).append(l)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]))


def op_str(op):
    rows, t = op
    names = "xyz"
    out = []
    for i in range(3):
        s = ""
        for j in range(3):
            c = rows[i][j]
            if abs(c) < 1e-9:
                continue
            sign = "-" if c < 0 else ("+" if s else "")
            mag = "" if abs(abs(c) - 1) < 1e-9 else "%g" % abs(c)
            s += "%s%s%s" % (sign, mag, names[j])
        tv = float(t[i]) % 1.0
        if tv > 1e-9:
            _snapped, exact = su.snap_to_fraction(tv)
            s += "+" + (str(exact) if exact is not None else "%.4f" % tv)
        out.append(s or "0")
    return ",".join(out)


# --------------------------------------------------------------------------
# --analyse
# --------------------------------------------------------------------------
def analyse(path, exclude=None):
    info = load_cif(path)
    excl = resolve_exclusions(info, exclude or [])
    to_cart, _, _ = make_converters(info["cell"])
    a, b, c, al, be, ga = info["cell"]

    print("=" * 78)
    print("rigid-body analysis: %s" % os.path.basename(path))
    print("=" * 78)
    print("space group %s   general-position multiplicity %d" % (info["sg"], info["general_mult"]))
    print("cell  a=%.5f b=%.5f c=%.5f  al=%.4f be=%.4f ga=%.4f" % (a, b, c, al, be, ga))
    if info["dup_of"]:
        print("\n%d CIF rows dropped as symmetry duplicates (a CIF often lists every copy"
              % len(info["dup_of"]))
        print("of a fragment under its own label); kept label shown second:")
        items = sorted(info["dup_of"].items())
        for k in range(0, len(items), 6):
            print("   " + "  ".join("%s>%s" % (x, y) for x, y in items[k:k+6]))

    print("\n--- asymmetric unit: %d sites -------------------------------------" % len(info["atoms"]))
    print("%-7s %-3s %9s %9s %9s %5s %5s  %s"
          % ("site", "el", "x", "y", "z", "mult", "|stab|", "stabilising operators"))
    for at in info["atoms"]:
        ops = [o for o in at["stabilizer"]]
        shown = ", ".join(op_str(o) for o in ops[:3])
        if len(ops) > 3:
            shown += ", +%d more" % (len(ops) - 3)
        print("%-7s %-3s %9.5f %9.5f %9.5f %5s %5d  %s"
              % (at["label"], at["elem"], at["frac"][0], at["frac"][1], at["frac"][2],
                 at["mult"], len(ops), shown))

    bl = bonds(info)
    labels = [x["label"] for x in info["atoms"]]
    comps = components(labels, bl.keys())

    print("\n--- connectivity ------------------------------------------------")
    print("bonds found (distance criterion over all operators and +-1 cells);")
    print("cross-check against the CIF's own _geom_bond loop before trusting it:")
    bb = sorted(bl.items(), key=lambda kv: kv[1][0])
    for k in range(0, len(bb), 4):
        print("   " + "  ".join("%s-%s %.2f" % (u, v, d)
                                for (u, v), (d, _) in bb[k:k+4]))

    print("\n--- connected components, all sites ------------------------------")
    for n, g in enumerate(comps, 1):
        els = sorted({next(x["elem"] for x in info["atoms"] if x["label"] == l) for l in g})
        print("  %d. %2d sites  elements %-18s  %s"
              % (n, len(g), "/".join(els), " ".join(g)))

    print("\n--- flags (candidates only: NOT applied) ------------------------")
    metals = [x["label"] for x in info["atoms"] if x["elem"] in METALS]
    if metals:
        print("  metal atoms present: %s" % " ".join(metals))
        print("    -> usually excluded from a rigid body, but that is a bonding")
        print("       judgement, not an element test.  Exclusion by element gets a")
        print("       covalently-bound heavy atom wrong (an aryl-I belongs IN the body,")
        print("       an iodide counter-ion does not).")
    singles = [g for g in comps if len(g) == 1]
    if singles:
        print("  single-atom components (ions / lone solvent O): %s"
              % " ".join(g[0] for g in singles))
    waters = [x["label"] for x in info["atoms"]
              if x["elem"] == "O" and sum(1 for (u, v) in bl
                                          if (u == x["label"] or v == x["label"])) <= 2]
    if waters:
        print("  possible solvent/water oxygens: %s" % " ".join(waters))
    if excl:
        print("  exclusions you passed, as resolved: %s" % " ".join(sorted(excl)))

    # Re-run connectivity on the INCLUDED sites only.  This matters: removing a metal
    # usually splits one component into several independent ligands, which is the whole
    # reason for excluding it.  Filtering the old component list would hide that.
    kept = [l for l in labels if l not in excl]
    frags = [g for g in components(kept, [(u, v) for (u, v) in bl
                                          if u not in excl and v not in excl])
             if len(g) >= 2]
    print("\n--- candidate RIGID BODIES (connectivity recomputed after exclusions) ---")
    if excl:
        print("  %d site(s) excluded -> %d component(s) became %d fragment(s) of >=2 atoms"
              % (len(excl), len(comps), len(frags)))
    for n, g in enumerate(frags, 1):
        els = sorted({next(x["elem"] for x in info["atoms"] if x["label"] == l) for l in g})
        print("  %d. %2d sites  elements %-18s  %s"
              % (n, len(g), "/".join(els), " ".join(g)))
    lone = [l for l in kept if not any(l in g for g in frags)]
    if lone:
        print("  (left over as single atoms, not rigid-body material: %s)" % " ".join(lone))

    print("\n--- what symmetry permits, per candidate fragment ---------------")
    for n, g in enumerate(frags, 1):
        report_dof(info, g, n, bl)

    print("\nNothing above has been decided for you.  Write a --build spec from it;")
    print("`--build` will not infer one.  Run `--verify` on the result.")
    return info


def report_dof(info, group, n, bl):
    """Report the symmetry situation of one fragment.  Does NOT pick the DOF."""
    atoms = {x["label"]: x for x in info["atoms"]}
    # operators fixing EVERY atom of the fragment individually
    common = None
    for l in group:
        s = {op_str(o) for o in atoms[l]["stabilizer"]}
        common = s if common is None else (common & s)
    common = common or set()
    # does the molecule continue through an operator that is NOT in `common`?
    # if so this fragment is a FRACTION of a molecule, and any placement DOF that
    # moves the fraction differently from its image is an internal distortion.
    to_cart, _, _ = make_converters(info["cell"])
    extends = []
    for op in info["ops"]:
        if op_str(op) in common:
            continue
        for l in group:
            q0 = su.apply_symop(op[0], op[1], atoms[l]["frac"])
            for sx in (-1, 0, 1):
                for sy in (-1, 0, 1):
                    for sz in (-1, 0, 1):
                        q = (q0[0]+sx, q0[1]+sy, q0[2]+sz)
                        if any(su.points_equal_mod1(q, atoms[m]["frac"], 2e-3)
                               for m in group):
                            continue
                        for m in group:
                            d = norm(sub(to_cart(atoms[m]["frac"]), to_cart(q)))
                            cut = 1.20*(COV.get(atoms[m]["elem"], COV_DEFAULT)
                                        + COV.get(atoms[l]["elem"], COV_DEFAULT))
                            if 0.4 < d <= cut:
                                extends.append((op_str(op), l, m, d))
                                break
                        else:
                            continue
                        break
                    else:
                        continue
                    break
                else:
                    continue
                break
            if extends and extends[-1][0] == op_str(op):
                break
    mults = sorted({atoms[l]["mult"] for l in group})
    print("  %d. %d sites, multiplicities %s" % (n, len(group), mults))
    print("     operators fixing every atom: %s"
          % (", ".join(sorted(common)) if common else "identity only"))
    if len(mults) > 1:
        print("     MIXED multiplicities -- only part of this fragment is on the special")
        print("     element.  Build the on-element atoms with dihedral exactly 0/180 and")
        print("     the rest with real dihedrals, in the SAME body (28.md: exact-placement rule, last case).")
    nested = [l for l in group
              if len({op_str(o) for o in atoms[l]["stabilizer"]}) > max(len(common), 1)]
    if nested and len(common) >= 1:
        print("     NESTED: %s sit on more symmetry than the fragment shares"
              % " ".join(nested[:8]))
        print("     -> removes further DOF beyond the shared element (28.md: nested-symmetry rule).")
    if extends:
        seen = {}
        for o, l, m, d in extends:
            seen.setdefault(o, (l, m, d))
        print("     molecule CONTINUES through: %s"
              % "; ".join("%s (%s-%s %.2f A)" % (o, v[0], v[1], v[2])
                          for o, v in list(seen.items())[:3]))
        print("     -> this fragment is a FRACTION of a molecule.  Any placement DOF")
        print("        that moves it differently from its image through that operator")
        print("        is an internal distortion, not a rigid motion -- exclude it.")
    else:
        print("     molecule does not continue through any other operator: this is a")
        print("     whole molecule, so the usual DOF for its site symmetry apply.")


def find_special_position_risk(info, window=1e-9, tol=0.002):
    """Flag special-position atoms whose constrained coordinate is an APPROXIMATE
    arithmetic result rather than an exact one (28.md: precision-window rules).  Advisory only: returns a
    list of findings and alters nothing.

    Two signals, both of which bite in practice:
      * a coordinate the site symmetry fixes, whose CIF value sits near an exact
        fraction but not ON it.  A published value is typically good to ~1e-4, against
        the ~1e-9 window TOPAS needs, so it must be snapped to the operator's own exact
        value before a z-matrix is built from it -- not used as given.
      * a coordinate the symmetry TIES to another (y = x, y = 2x ...) where the two CIF
        values disagree by more than the window.
    """
    out = []
    for at in info["atoms"]:
        stab = at["stabilizer"]
        if len(stab) <= 1:
            continue
        cls = su.classify_coordinates(at["frac"], stab)
        idx = {"x": 0, "y": 1, "z": 2}
        for ax in "xyz":
            con = cls.get(ax)
            if not con:
                continue
            kind = con[0]
            v = at["frac"][idx[ax]]
            if kind == "fixed":
                _snap, exact = su.snap_to_fraction(v, tol)
                if exact is None:
                    out.append((at["label"], ax, "fixed at %.6f, not near any common "
                                "fraction -- confirm against the operator itself" % v))
                else:
                    resid = abs(v - float(exact))
                    if resid > window:
                        out.append((at["label"], ax,
                                    "fixed; CIF gives %.6f, exact value %s, residual "
                                    "%.1e > %.0e window -- SNAP before building"
                                    % (v, exact, resid, window)))
            elif kind == "tied":
                other, sign, offset = con[1], con[2], con[3]
                want = sign*at["frac"][idx[other]] + offset
                resid = abs(((v - want + 0.5) % 1.0) - 0.5)
                if resid > window:
                    out.append((at["label"], ax,
                                "tied to %s (%s = %+g*%s %+g); CIF values disagree by "
                                "%.1e > %.0e window -- SNAP before building"
                                % (other, ax, sign, other, offset, resid, window)))
            elif kind == "complex":
                out.append((at["label"], ax, "constraint too complex to express -- "
                            "derive it from the operator by hand"))
    return out


def risk_cmd(path):
    info = load_cif(path)
    found = find_special_position_risk(info)
    print("special-position risk audit: %s" % os.path.basename(path))
    print("general-position multiplicity %d, %d sites in the asymmetric unit\n"
          % (info["general_mult"], len(info["atoms"])))
    if not found:
        print("no at-risk coordinates: every symmetry-fixed coordinate sits on its")
        print("exact value to within 1e-9.  (Advisory only -- this does not check a")
        print("built rigid body; for that run --verify.)")
        return
    for lab, ax, msg in found:
        print("  %-7s %s: %s" % (lab, ax, msg))
    print("\nAdvisory only; nothing was altered.  Per 28.md, derive the exact position")
    print("from the operator's own coefficients and snap onto it BEFORE building the")
    print("z-matrix -- and do NOT simply nudge the coordinate.")


def is_mirror(op):
    """True for a reflection, with the axis it negates ('a'|'b'|'c'), else None.
    Restricted to axis-aligned mirrors: the local frame has to be reachable by
    rotating onto a Cartesian axis (28.md: last limit of the construction)."""
    rows = op[0]
    neg = None
    for i in range(3):
        for j in range(3):
            if i == j:
                if abs(rows[i][j] - 1) > 1e-9 and abs(rows[i][j] + 1) > 1e-9:
                    return None
                if rows[i][j] < 0:
                    if neg is not None:
                        return None          # two negated axes: a 2-fold, not a mirror
                    neg = "abc"[i]
            elif abs(rows[i][j]) > 1e-9:
                return None                  # off-diagonal: diagonal mirror, unsupported
    return neg


def derive_normal(info, group):
    """The mirror shared by the largest subset of the fragment. Returns
    (axis_letter, n_atoms_sharing, ambiguous_alternatives)."""
    atoms = {x["label"]: x for x in info["atoms"]}
    tally = {}
    for op in info["ops"]:
        ax = is_mirror(op)
        if not ax:
            continue
        n = sum(1 for l in group
                if any(op_str(o) == op_str(op) for o in atoms[l]["stabilizer"]))
        if n >= 3:
            tally[ax] = max(tally.get(ax, 0), n)
    if not tally:
        return None, 0, []
    best = max(tally.items(), key=lambda kv: kv[1])
    alts = [k for k, v in tally.items() if k != best[0]]
    return best[0], best[1], alts


def derive_plane(info, group, axis):
    """Atoms whose stabiliser contains the mirror normal to `axis`."""
    atoms = {x["label"]: x for x in info["atoms"]}
    want = [op for op in info["ops"] if is_mirror(op) == axis]
    out = [l for l in group
           if any(op_str(o) == op_str(w) for o in atoms[l]["stabilizer"] for w in want)]
    return out


def derive_root(info, group, plane):
    """Prefer an atom sitting on MORE symmetry than the fragment shares: its position
    then comes straight from `translate` and can be fixed exactly (28.md: exact-placement rule)."""
    atoms = {x["label"]: x for x in info["atoms"]}
    if not plane:
        return None
    base = min(len(atoms[l]["stabilizer"]) for l in plane)
    nested = sorted([l for l in plane if len(atoms[l]["stabilizer"]) > base],
                    key=lambda l: (-len(atoms[l]["stabilizer"]), l))
    return nested[0] if nested else None


def image_bonds(info, group, fracs=None):
    """Bonds from an atom of `group` to the IMAGE of another under a symmetry
    operator -- i.e. the bonds that hold the molecule together across the operator.
    Returns [(op_string, l, m, distance)].  These lengths are the test of whether a
    declared placement DOF is a rigid motion: a rigid motion cannot change them,
    an internal distortion does."""
    atoms = {x["label"]: x for x in info["atoms"]}
    f = fracs or {k: v["frac"] for k, v in atoms.items()}
    to_cart, _, _ = make_converters(info["cell"])
    out = []
    for op in info["ops"]:
        for l in group:
            if l not in f:
                continue
            q0 = su.apply_symop(op[0], op[1], f[l])
            for sx in (-1, 0, 1):
                for sy in (-1, 0, 1):
                    for sz in (-1, 0, 1):
                        q = (q0[0]+sx, q0[1]+sy, q0[2]+sz)
                        if any(su.points_equal_mod1(q, f[m], 2e-3) for m in group
                               if m in f):
                            continue
                        for m in group:
                            if m not in f:
                                continue
                            d = norm(sub(to_cart(f[m]), to_cart(q)))
                            cut = 1.20*(COV.get(atoms[m]["elem"], COV_DEFAULT)
                                        + COV.get(atoms[l]["elem"], COV_DEFAULT))
                            if 0.4 < d <= cut:
                                out.append((op_str(op), l, m, d))
    return out


def axis_point(op):
    """A point on the invariant axis of a proper rotation: solve (R-I)p = -t.
    Returns None for the identity or when no solution exists. Needed because a
    fragment arranged AROUND a rotation axis must be rooted ON that axis -- a
    rotation about its own centroid is not a rigid motion of the whole molecule."""
    rows, t = op[0], [float(v) for v in op[1]]
    A = [[rows[i][j] - (1 if i == j else 0) for j in range(3)] for i in range(3)]
    if all(abs(A[i][j]) < 1e-9 for i in range(3) for j in range(3)):
        return None                                  # identity
    b = [-v for v in t]
    M = [A[i][:] + [b[i]] for i in range(3)]
    piv = []
    r = 0
    for c in range(3):
        k = max(range(r, 3), key=lambda i: abs(M[i][c]))
        if abs(M[k][c]) < 1e-9:
            continue
        M[r], M[k] = M[k], M[r]
        d = M[r][c]
        M[r] = [v / d for v in M[r]]
        for i in range(3):
            if i != r and abs(M[i][c]) > 1e-12:
                f = M[i][c]
                M[i] = [M[i][j] - f * M[r][j] for j in range(4)]
        piv.append(c)
        r += 1
        if r == 3:
            break
    for i in range(r, 3):
        if abs(M[i][3]) > 1e-6:
            return None                              # inconsistent: no fixed point
    p = [0.0, 0.0, 0.0]
    for i, c in enumerate(piv):
        p[c] = M[i][3]
    return tuple(v - math.floor(v + 1e-9) if abs(v) > 1e-9 else 0.0 for v in p)


def rotation_axes_through(info, group):
    """Proper rotations (not the identity, not a reflection) that the molecule
    continues through, with a point on each axis."""
    out = []
    for o in continues_through(info, group):
        for op in info["ops"]:
            if op_str(op) != o or is_mirror(op):
                continue
            rows = op[0]
            det = (rows[0][0]*(rows[1][1]*rows[2][2]-rows[1][2]*rows[2][1])
                   - rows[0][1]*(rows[1][0]*rows[2][2]-rows[1][2]*rows[2][0])
                   + rows[0][2]*(rows[1][0]*rows[2][1]-rows[1][1]*rows[2][0]))
            if det < 0:
                continue
            p = axis_point(op)
            if p is not None:
                out.append((o, p))
            break
    return out


def continues_through(info, group):
    """Operators the molecule continues through -- i.e. this fragment is a fraction
    of a molecule. Reused by the DOF cross-check."""
    atoms = {x["label"]: x for x in info["atoms"]}
    to_cart, _, _ = make_converters(info["cell"])
    hits = set()
    for op in info["ops"]:
        for l in group:
            q0 = su.apply_symop(op[0], op[1], atoms[l]["frac"])
            for sx in (-1, 0, 1):
                for sy in (-1, 0, 1):
                    for sz in (-1, 0, 1):
                        q = (q0[0]+sx, q0[1]+sy, q0[2]+sz)
                        if any(su.points_equal_mod1(q, atoms[m]["frac"], 2e-3)
                               for m in group):
                            continue
                        for m in group:
                            d = norm(sub(to_cart(atoms[m]["frac"]), to_cart(q)))
                            cut = 1.20*(COV.get(atoms[m]["elem"], COV_DEFAULT)
                                        + COV.get(atoms[l]["elem"], COV_DEFAULT))
                            if 0.4 < d <= cut:
                                hits.add(op_str(op))
    return hits


AX_TO_Q = {"a": "x", "b": "y", "c": "z"}


def dof_lines(frag, info, res, name, axis, indent="      "):
    """Turn the DECLARED dof into correct rotate/translate lines.

    This is deliberately not left to the caller: a free translate component makes
    every atom of the body a general position, and a Cartesian component on a special
    plane stops tracking that plane once the cell refines (28.md: fixed-translate and
    fractional-translate rules).  Both are
    mechanical, so they are generated here rather than hand-written."""
    L = []
    rot = frag.get("free_rotation", [])
    if rot == ["normal"]:
        rot = [AX_TO_Q.get(axis, "z")] if axis else []
    for q in rot:
        L.append(indent + "   rotate %s_rot%s 0 min -10 max 10 q%s 1" % (name, q, q))
    free = frag.get("free_translation", [])
    of = res["origin_frac"]
    L.append(indent + "   translate")
    for i, ax in enumerate("abc"):
        if ax in free:
            L.append(indent + "      t%s %s_t%s %.12f min = Val-0.05; max = Val+0.05;"
                     % (ax, name, ax, of[i]))
        else:
            _snap, exact = su.snap_to_fraction(of[i] % 1.0)
            in_cell = abs(of[i] - (of[i] % 1.0)) < 1e-9
            if exact is not None and in_cell and exact.denominator != 1:
                # A fraction MUST be written as an equation: TOPAS reads a bare
                # `ta 1/2` as a syntax error ("fractions such as 1/3 should be
                # entered as =1/3;"), the same rule as for a site coordinate.
                # Keeping it exact rather than decimal is what makes the component
                # cell-independent (28.md: fractional-translate rule).
                L.append(indent + "      t%s = %s;   ' FIXED, exact fraction "
                         "(cell-independent)" % (ax, exact))
            elif exact is not None and in_cell:
                L.append(indent + "      t%s %s   ' FIXED (exact)"
                         % (ax, exact))
            else:
                L.append(indent + "      t%s %.12f   ' FIXED" % (ax, of[i]))
    return L


def split_exclusions(spec):
    """Accept a list, or a string separated by commas and/or whitespace.  The wizard's
    own field is free text and 'Si Cl' is as natural to type as 'Si, Cl'; splitting on
    commas alone turned the first real input into one unmatchable token and silently
    excluded nothing."""
    if spec is None:
        return []
    if isinstance(spec, str):
        return [t for t in re.split(r"[,;\s]+", spec) if t]
    out = []
    for item in spec:
        out.extend(t for t in re.split(r"[,;\s]+", str(item)) if t)
    return out


def resolve_exclusions(info, tokens):
    """A token is an ELEMENT symbol only if it matches a known element AND no site
    carries that exact label; otherwise it is a site label.  Ambiguity is reported."""
    labels = {x["label"] for x in info["atoms"]}
    elems = {x["elem"] for x in info["atoms"]}
    out = set()
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if t in labels:
            out.add(t)
            if t in elems:
                note("  note: %r read as a SITE LABEL (a site has that exact label); "
                      "to exclude the element, no site may share its name." % t)
        elif t.capitalize() in elems:
            hit = [x["label"] for x in info["atoms"] if x["elem"] == t.capitalize()]
            out.update(hit)
            note("  note: %r read as an ELEMENT -> %s" % (t, " ".join(hit)))
        else:
            note("  WARNING: exclusion %r matched no site label and no element present"
                  % t)
    return out


# --------------------------------------------------------------------------
# geometry kernel -- ported unchanged from the version validated this session
# against Cmmm, Pm, P4/mcc, Cccm and P-62c (5 fragments, all exact to <5e-16)
# --------------------------------------------------------------------------
def build_fragment(cell, atoms, plane_labels, normal_axis, root_label=None,
                   origin_frac=None):
    """atoms: [(label, frac3), ...].  plane_labels: the atoms ON the special plane
    (or, at a general position, any >=3 defining a construction plane).
    normal_axis: 'a'|'b'|'c' for the special-plane normal, or None at a general
    position.  root_label: a real atom to use as the z-matrix root -- needed when an
    atom must sit on a nested constraint, since its position then comes straight
    from `translate` and can be fixed exactly."""
    to_cart, to_frac, (va, vb, vc) = make_converters(cell)
    pos = {l: to_cart(f) for l, f in atoms}
    src = dict(atoms)

    if normal_axis is not None:
        n = unit({"a": va, "b": vb, "c": vc}[normal_axis])
    else:
        cen0 = mul([sum(pos[l][i] for l in plane_labels) for i in range(3)],
                   1.0/len(plane_labels))
        best, n = -1.0, None
        for i in range(len(plane_labels)):
            for j in range(i+1, len(plane_labels)):
                cj = cross(sub(pos[plane_labels[i]], cen0), sub(pos[plane_labels[j]], cen0))
                if norm(cj) > best:
                    best, n = norm(cj), unit(cj)

    if root_label:
        origin = pos[root_label]
    elif origin_frac is not None:
        # explicit origin: needed when the fragment is arranged AROUND a rotation
        # axis, so the refinable rotation has to be about that axis and not about
        # the fragment's own centroid
        origin = to_cart(tuple(origin_frac))
    else:
        origin = mul([sum(pos[l][i] for l in plane_labels) for i in range(3)],
                     1.0/len(plane_labels))
        if normal_axis is not None:
            origin = sub(origin, mul(n, dot(sub(origin, pos[plane_labels[0]]), n)))

    cand = [l for l in plane_labels if l != root_label]
    a3 = max(cand, key=lambda l: norm(sub(pos[l], origin)))
    # TOPAS puts the 3rd z-matrix point EXACTLY in the local x-z plane, so the frame
    # must be derived from a3 and the chosen local z -- never from a best-fit normal,
    # which leaves a3's azimuth at 180+-delta and shifts every other atom.
    uraw = sub(pos[a3], origin)
    ez = unit(cross(n, uraw))
    ex = mul(unit(sub(uraw, mul(ez, dot(uraw, ez)))), -1.0)
    ey = cross(ez, ex)

    order = ([root_label] if root_label else []) + [a3] + \
            [l for l, _ in atoms if l not in (root_label, a3)]
    rows = []
    for lab in order:
        d = sub(pos[lab], origin)
        lx, ly, lz = dot(d, ex), dot(d, ey), dot(d, ez)
        r = math.sqrt(lx*lx + ly*ly + lz*lz)
        if r < 1e-9:
            rows.append(dict(label=lab, r=0.0, ang=0.0, az=0.0, dih=0.0, is_root=True))
            continue
        rows.append(dict(label=lab, r=r,
                         ang=math.degrees(math.acos(max(-1.0, min(1.0, lz/r)))),
                         az=math.degrees(math.atan2(ly, lx)), is_root=False))
    az3 = next(rw["az"] for rw in rows if rw["label"] == a3)
    for rw in rows:
        if rw.get("is_root"):
            continue
        dih = DIH_SIGN*(rw["az"] - az3)
        while dih <= -180.0:
            dih += 360.0
        while dih > 180.0:
            dih -= 360.0
        if abs(dih) < 1e-9:
            dih = 0.0
        elif abs(abs(dih) - 180.0) < 1e-9:
            dih = 180.0
        rw["dih"] = dih

    R = [[ex[0], ey[0], ez[0]], [ex[1], ey[1], ez[1]], [ex[2], ey[2], ez[2]]]
    cosang = max(-1.0, min(1.0, (R[0][0]+R[1][1]+R[2][2] - 1.0)/2.0))
    afix = math.degrees(math.acos(cosang))
    s = 2.0*math.sin(math.radians(afix))
    if abs(s) < 1e-12:
        axis = (1.0, 0.0, 0.0) if cosang > 0 else unit((R[0][0]+1, R[1][0], R[2][0]))
    else:
        axis = unit(((R[2][1]-R[1][2])/s, (R[0][2]-R[2][0])/s, (R[1][0]-R[0][1])/s))

    worst, worst_lab = 0.0, None
    for rw in rows:
        if rw.get("is_root"):
            p = (0.0, 0.0, 0.0)
        else:
            a_ = math.radians(rw["ang"])
            d_ = math.radians(DIH_SIGN*rw["dih"] + az3)
            p = (rw["r"]*math.sin(a_)*math.cos(d_),
                 rw["r"]*math.sin(a_)*math.sin(d_), rw["r"]*math.cos(a_))
        f = to_frac(add(rotv(p, axis, afix), origin))
        dv = max(abs(((f[i]-src[rw["label"]][i]+0.5) % 1.0)-0.5) for i in range(3))
        if dv > worst:
            worst, worst_lab = dv, rw["label"]

    degen = [rw["label"] for rw in rows if not rw.get("is_root")
             and abs(math.sin(math.radians(rw["ang"]))) < 1e-6]
    return dict(rows=rows, axis=axis, afix=afix, origin_frac=to_frac(origin),
                a3=a3, root=root_label, worst=worst, worst_label=worst_lab,
                degenerate=degen,
                offplane=[rw["label"] for rw in rows if not rw.get("is_root")
                          and rw["dih"] not in (0.0, 180.0)])


def emit_rigid(res, name, dummy=("X1", "X2"), indent="      "):
    """Emit the `rigid` block.  translate is FRACTIONAL (28.md: fractional-translate rule)."""
    if res["worst"] > 1e-11:
        raise SystemExit("round-trip %.2e at %s -- refusing to emit a body that does "
                         "not reproduce its own source coordinates"
                         % (res["worst"], res["worst_label"]))
    if res["degenerate"]:
        raise SystemExit("atoms on the local z axis (undefined azimuth): %s -- choose "
                         "a different reference" % " ".join(res["degenerate"]))
    root = res["root"] or dummy[0]
    x2 = dummy[1]
    L = [indent + "rigid", indent + "   load z_matrix {"]
    if not res["root"]:
        L.append(indent + "      " + dummy[0])
    else:
        L.append(indent + "      " + root)
    L.append(indent + "      %-6s %-6s 1.000000000000" % (x2, root))
    started = False
    for rw in res["rows"]:
        if rw.get("is_root"):
            continue
        if not started:
            L.append(indent + "      %-6s %-6s %16.12f   %-6s %17.12f"
                     % (rw["label"], root, rw["r"], x2, rw["ang"]))
            started = True
        else:
            L.append(indent + "      %-6s %-6s %16.12f   %-6s %17.12f   %-6s %17.12f"
                     % (rw["label"], root, rw["r"], x2, rw["ang"],
                        res["a3"], rw["dih"]))
    L.append(indent + "   }")
    ax, af, of = res["axis"], res["afix"], res["origin_frac"]
    L.append(indent + "   rotate !%s_align %.12f qx %.12f qy %.12f qz %.12f"
             % (name, af, ax[0], ax[1], ax[2]))
    L.append(indent + "   ' origin (fractional): a=%.12f b=%.12f c=%.12f"
             % of)
    return "\n".join(L)


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--analyse", metavar="CIF")
    g.add_argument("--build", metavar="SPEC_JSON")
    g.add_argument("--verify", metavar="SPEC_JSON")
    g.add_argument("--risk", metavar="CIF",
                   help="advisory special-position precision audit (28.md)")
    ap.add_argument("--exclude", default="",
                    help="comma-separated site labels and/or element symbols")
    a = ap.parse_args()
    if a.analyse:
        analyse(a.analyse, split_exclusions(a.exclude))
    elif a.build:
        build_cmd(a.build)
    elif a.risk:
        risk_cmd(a.risk)
    else:
        verify_cmd(a.verify, a.exclude)


def auto_fragments(info, excl):
    bl = bonds(info)
    kept = [x["label"] for x in info["atoms"] if x["label"] not in excl]
    return [g for g in components(kept, [(u, v) for (u, v) in bl
                                         if u not in excl and v not in excl])
            if len(g) >= 2]


def build_cmd(spec_path):
    spec = json.load(open(spec_path))
    info = load_cif(spec["cif"])
    excl = resolve_exclusions(info, split_exclusions(spec.get("exclude")))
    frags = spec.get("fragments")

    # Template mode: no fragments, or any fragment missing its DOF.  Everything
    # derivable is filled in; the two judgement fields are left null and `--build`
    # refuses to emit until they are set.
    need_template = not frags or any(
        f.get("free_rotation") is None or f.get("free_translation") is None
        for f in frags)
    if need_template:
        auto = frags or [{"atoms": g} for g in auto_fragments(info, excl)]
        out = {"cif": spec["cif"], "exclude": sorted(excl), "fragments": []}
        print("TEMPLATE -- derived fields filled in; set free_rotation and")
        print("free_translation per fragment, then re-run --build.\n")
        for i, f in enumerate(auto, 1):
            grp = f["atoms"]
            axis, nshare, alts = derive_normal(info, grp)
            plane = derive_plane(info, grp, axis) if axis else grp
            root = derive_root(info, grp, plane)
            cont = continues_through(info, grp)
            out["fragments"].append({
                "name": f.get("name", "rb%d" % i),
                "atoms": grp,
                "normal": axis,
                "root": root,
                "free_rotation": None,
                "free_translation": None,
            })
            print("  fragment %d (%s): %d atoms" % (i, f.get("name", "rb%d" % i), len(grp)))
            print("     normal %-4s shared by %d atoms%s"
                  % (axis, nshare, "  AMBIGUOUS, also: %s" % alts if alts else ""))
            print("     %d of %d atoms lie on that mirror; %d off it"
                  % (len(plane), len(grp), len(grp)-len(plane)))
            print("     root %s%s" % (root, "  (sits on nested symmetry -- its position"
                  " comes from translate and can be fixed exactly)" if root else
                  "  (none nested; a dummy at the plane centroid will be used)"))
            if cont:
                print("     molecule continues through %s -> a FRACTION of a molecule."
                      % ", ".join(sorted(cont)[:3]))
                print("     Placement DOF that move it differently from its image are"
                      " internal")
                print("     distortions; this usually means free_rotation [].")
            ax_pts = rotation_axes_through(info, grp)
            if ax_pts and not root:
                o, p = ax_pts[0]
                out["fragments"][-1]["origin"] = [round(v, 12) for v in p]
                print("     arranged AROUND the rotation axis of %s, which passes through"
                      " (%.4f, %.4f, %.4f)." % ((o,) + p))
                print("     origin set there, NOT the fragment centroid: a rotation must"
                      " be about")
                print("     that axis to be a rigid motion of the whole molecule.")
        print("\n" + json.dumps(out, indent=2))
        raise SystemExit(0)

    pos = {x["label"]: x["frac"] for x in info["atoms"]}
    used, blocks = 0, []
    for i, frag in enumerate(frags, 1):
        grp = frag["atoms"]
        axis = frag.get("normal") or derive_normal(info, grp)[0]
        plane = frag.get("plane") or (derive_plane(info, grp, axis) if axis else grp)
        root = frag.get("root", "__auto__")
        if root == "__auto__":
            root = derive_root(info, grp, plane)
        name = frag.get("name", "rb%d" % i)
        # cross-check the DECLARED dof against the symmetry analysis
        cont = continues_through(info, grp)
        if cont and frag.get("free_rotation"):
            note("' WARNING %s: free_rotation %s declared, but the molecule continues"
                  % (name, frag["free_rotation"]))
            note("'   through %s, so this fragment is a fraction of a molecule and a"
                  % ", ".join(sorted(cont)[:2]))
            note("'   rotation is likely an internal distortion. Verify deliberately.")
        if axis and axis in frag.get("free_translation", []):
            note("' WARNING %s: free_translation includes %r, the mirror normal --"
                  % (name, axis))
            note("'   a free component along it makes every atom of this body a"
                  " general position.")
        dummies = ("X%d1" % i, "X%d2" % i)
        res = build_fragment(info["cell"], [(l, pos[l]) for l in grp], plane, axis,
                             root, frag.get("origin"))
        blocks.append(emit_rigid(res, name, dummies))
        blocks.append("\n".join(dof_lines(frag, info, res, name, axis)))
        used += 1
    print("' %d rigid body/bodies. Dummy frame atoms need occ 0 site lines:" % used)
    print("'   " + "  ".join("X%d1 X%d2" % (i, i) for i in range(1, used+1)))
    print("\n\n".join(blocks))


SITE_RE = re.compile(r"^(\s*site\s+(\S+)\s+)(.*?)(\s+occ\s+.*)$")


def _site_name(line):
    m = SITE_RE.match(line)
    return m.group(2) if m else None


def _blank_coords(line):
    """Replace a site's x/y/z with placeholders: its position comes from the rigid
    body instead."""
    m = SITE_RE.match(line)
    return m.group(1) + "x 0  y 0  z 0" + m.group(4) if m else line


#  NOTE on the refine sigil, since it is an easy thing to get wrong here.
#  `cif_to_str.py` already emits coordinates correctly: `@` appears ONLY on genuinely
#  free coordinates, while a symmetry-constrained one is a bare value or an exact
#  `= 1/2;` equation (e.g. on a z=0 mirror it writes `x @ .. y @ .. z 0`).  28.md's
#  fixed-translate rule is about a free coordinate along a CONSTRAINED direction; a free coordinate
#  along an unconstrained one is both correct and required.  A/B tested on a
#  test structure: stripping `@` leaves every num_posns identical (8/8/.../2/2), so the
#  control is used exactly as `convert()` produces it rather than being rewritten.


AUDIT_BLOCK = '''      atom_out "%s"
         load out_record out_fmt out_eqn
         {
            "\\n%%-8s"   = Get_From_String(Get(current_atom), site);
            " %%3.0f"   = Get_From_String(Get(current_atom), num_posns);
            " %%23.18f" = Get_From_String(Get(current_atom), x);
            " %%23.18f" = Get_From_String(Get(current_atom), y);
            " %%23.18f" = Get_From_String(Get(current_atom), z);
         }
'''

COMMON_HEAD = '''iters 0
yobs_eqn !aa = 1; min 5 max 90 del 0.02
CuKa2_analyt(0.0001)
LP_Factor(!th2_monochromator, 0)
   str
'''

COMMON_TAIL = '''      scale 0.0001
      TCHZ_Peak_Type(!pku, 0.0001, !pkv, 0.0001, !pkw, 0.005, !pkz, 0, !pkx, 0.01, !pky, 0.0001)
      Create_hklm_d_Th2_Ip_file("%s")
'''


def _read_ticks(path):
    out = {}
    for ln in open(path).read().splitlines()[1:]:
        p = ln.split()
        if len(p) >= 7:
            out[(int(p[0]), int(p[1]), int(p[2]))] = (float(p[5]), float(p[6]))
    return out


def _read_audit(path):
    out = {}
    for ln in open(path):
        p = ln.split()
        if len(p) == 5:
            out[p[0]] = (int(float(p[1])),
                         tuple(float(v) for v in p[2:5]))
    return out


def verify_cmd(spec_path, _unused=""):
    """Build the rigid body AND a plain-`site` control from the same CIF, force them
    to agree in every non-structural respect, run both, and diff.

    This is the check 28.md calls stronger than `num_posns`: at the source geometry a
    correct rigid body must produce an IDENTICAL calculated pattern to the same atoms
    written as ordinary sites.  Both files are generated here rather than supplied,
    because the comparison is only meaningful if cell, scale, peak shape, ADPs,
    occupancies, 2-theta range and refine flags are matched -- mismatch any of them
    and this reports a confident false failure."""
    tcexe = topas_install.find_tc()
    tcenv = topas_install.tc_env(tcexe)
    spec = json.load(open(spec_path))
    info = load_cif(spec["cif"])
    frags = spec.get("fragments") or []
    if not frags or any(f.get("free_rotation") is None for f in frags):
        raise SystemExit("spec has no fragments with DOF set -- run --build first")

    strblock, warns = c2s.convert(spec["cif"])
    head_lines, site_lines = [], []
    for ln in strblock.splitlines():
        if re.match(r"\s*site\s+\S+", ln):
            site_lines.append(ln)
        elif ln.strip() and not ln.strip().startswith("str"):
            head_lines.append(ln)

    rb_labels = []
    for f in frags:
        rb_labels.extend(f["atoms"])
    known = {_site_name(l) for l in site_lines}
    missing = [l for l in rb_labels if l not in known]
    if missing:
        raise SystemExit("spec names sites absent from the CIF conversion: %s"
                         % " ".join(missing))

    workdir = os.path.dirname(os.path.abspath(spec_path)) or "."
    pos = {x["label"]: x["frac"] for x in info["atoms"]}
    # the rigid blocks, and the dummy frame atoms they need
    blocks, dummies = [], []
    for i, frag in enumerate(frags, 1):
        grp = frag["atoms"]
        axis = frag.get("normal") or derive_normal(info, grp)[0]
        plane = frag.get("plane") or (derive_plane(info, grp, axis) if axis else grp)
        root = frag.get("root", "__auto__")
        if root == "__auto__":
            root = derive_root(info, grp, plane)
        name = frag.get("name", "rb%d" % i)
        dn = ("X%d1" % i, "X%d2" % i)
        res = build_fragment(info["cell"], [(l, pos[l]) for l in grp], plane, axis,
                             root, frag.get("origin"))
        blocks.append(emit_rigid(res, name, dn))
        blocks.append("\n".join(dof_lines(frag, info, res, name, axis)))
        dummies.extend(d for d in dn if not root or d != dn[0])

    dummy_sites = ["      site %-8s num_posns 0  x 0  y 0  z 0  occ C 0  beq !bq%s 1"
                   % (d, d) for d in dummies]
    # num_posns zeroed in BOTH files so the .out reports only what TOPAS computed
    zero = lambda l: re.sub(r"num_posns\s+\S+", "num_posns 0", l)

    ctl = (COMMON_HEAD + "\n".join(head_lines) + "\n"
           + "\n".join(zero(l) for l in site_lines) + "\n"
           + COMMON_TAIL % "ctl_ticks.txt" + AUDIT_BLOCK % "ctl_audit.txt")
    rb = (COMMON_HEAD + "\n".join(head_lines) + "\n"
          + "\n".join(dummy_sites) + "\n"
          + "\n".join(zero(_blank_coords(l)) if _site_name(l) in rb_labels
                      else zero(l) for l in site_lines) + "\n"
          + "\n".join(blocks) + "\n"
          + COMMON_TAIL % "rb_ticks.txt" + AUDIT_BLOCK % "rb_audit.txt")

    fails = []
    for tag, txt in (("ctl", ctl), ("rb", rb)):
        p = os.path.join(workdir, "_verify_%s.inp" % tag)
        open(p, "w", encoding="utf-8").write(txt)
        r = subprocess.run([tcexe, p], cwd=workdir, capture_output=True, text=True,
                           timeout=1200, env=tcenv)
        if "Abnormal program termination" in (r.stdout or ""):
            note(r.stdout[-900:])
            raise SystemExit("tc.exe failed on the %s file (%s)" % (tag, p))

    ca, ra = (_read_audit(os.path.join(workdir, f))
              for f in ("ctl_audit.txt", "rb_audit.txt"))
    ct, rt = (_read_ticks(os.path.join(workdir, f))
              for f in ("ctl_ticks.txt", "rb_ticks.txt"))

    print("=" * 74)
    print("verify: rigid body vs plain-`site` control, %s" % os.path.basename(spec["cif"]))
    print("=" * 74)

    # 1. multiplicities, each against the independent computation AND each other
    print("\n--- num_posns ---------------------------------------------------")
    indep = {x["label"]: x["mult"] for x in info["atoms"]}
    print("%-9s %8s %8s %8s" % ("site", "analyse", "control", "rigid"))
    for lab in sorted(ra):
        if lab.startswith("X") and lab not in indep:
            continue
        e, c, r_ = indep.get(lab), ca.get(lab, (None,))[0], ra[lab][0]
        bad = (e is not None and r_ != e) or (c is not None and r_ != c)
        if bad:
            fails.append("num_posns %s: analyse %s, control %s, rigid %s"
                         % (lab, e, c, r_))
        print("%-9s %8s %8s %8s %s" % (lab, e, c, r_, "<-- MISMATCH" if bad else ""))

    # 2. coordinates
    print("\n--- coordinates (rigid vs control) ------------------------------")
    worst, wl = 0.0, None
    for lab in ra:
        if lab not in ca:
            continue
        d = max(abs(((ra[lab][1][i] - ca[lab][1][i] + 0.5) % 1.0) - 0.5)
                for i in range(3))
        if d > worst:
            worst, wl = d, lab
    print("worst |fractional difference| %.2e at %s" % (worst, wl))
    if worst > 1e-9:
        fails.append("coordinates differ by %.2e at %s (special-position window is ~1e-9)"
                     % (worst, wl))

    # 3. the calculated pattern itself
    print("\n--- calculated pattern ------------------------------------------")
    print("reflections: control %d, rigid %d" % (len(ct), len(rt)))
    if set(ct) != set(rt):
        fails.append("reflection LISTS differ (%d vs %d) -- the two models do not "
                     "share a cell or symmetry" % (len(ct), len(rt)))
    shared = set(ct) & set(rt)
    scale = max([ct[k][1] for k in shared] or [1.0])
    diffs = [(abs(ct[k][1] - rt[k][1]), k) for k in shared]
    big = [(d, k) for d, k in diffs if d > 0.01 * scale]
    print("max |I_rigid - I_control| = %.4g  (%.3f%% of the strongest reflection)"
          % (max([d for d, _ in diffs] or [0]),
             100.0 * max([d for d, _ in diffs] or [0]) / scale))
    if big:
        fails.append("%d reflection(s) differ by >1%% of the strongest: %s"
                     % (len(big), ", ".join(str(k) for _, k in sorted(big,
                                                                     reverse=True)[:5])))

    # 4. perturbation test: nudge every free placement parameter and confirm the
    #    special positions AND the across-operator bond lengths survive.  Stages 1-3
    #    only see the starting geometry, so they cannot catch a DOF that is not a
    #    rigid motion -- a rotation about the wrong axis, or a translate that drifts
    #    off a special plane once the cell moves.  That error appears only on
    #    refinement, which is exactly when it is expensive to discover.
    print("\n--- perturbation test (is each declared DOF a rigid motion?) -----")
    pert = rb
    n_p = 0
    for m in re.finditer(r"(rotate\s+)(\w+_rot\w*)(\s+)([-\d.]+)", rb):
        pert = pert.replace(m.group(0), "%s%s%s%.6f"
                            % (m.group(1), m.group(2), m.group(3),
                               float(m.group(4)) + 3.0))
        n_p += 1
    for m in re.finditer(r"(t[abc]\s+)(\w+_t[abc])(\s+)([-\d.]+)", rb):
        pert = pert.replace(m.group(0), "%s%s%s%.12f"
                            % (m.group(1), m.group(2), m.group(3),
                               float(m.group(4)) + 0.01))
        n_p += 1
    if not n_p:
        print("no free placement parameters declared -- nothing to perturb")
    else:
        pert = pert.replace('"rb_ticks.txt"', '"pt_ticks.txt"') \
                   .replace('"rb_audit.txt"', '"pt_audit.txt"')
        pp = os.path.join(workdir, "_verify_pert.inp")
        open(pp, "w", encoding="utf-8").write(pert)
        r = subprocess.run([tcexe, pp], cwd=workdir, capture_output=True,
                           text=True, timeout=1200, env=tcenv)
        if "Abnormal program termination" in (r.stdout or ""):
            fails.append("the perturbed model will not even run -- the declared DOF "
                         "produces an invalid geometry")
        else:
            pa = _read_audit(os.path.join(workdir, "pt_audit.txt"))
            print("perturbed %d free parameter(s) (rotations +3 deg, translations "
                  "+0.01 frac)" % n_p)
            broke = [l for l in pa if l in ra and pa[l][0] != ra[l][0]]
            if broke:
                fails.append("perturbing the free DOF changed num_posns for %s -- a "
                             "free parameter is moving atoms off a special position "
                             "(28.md: fixed- and fractional-translate rules)" % " ".join(sorted(broke)[:6]))
                print("  num_posns CHANGED for: %s" % " ".join(sorted(broke)[:8]))
            else:
                print("  num_posns unchanged for every site")
            # across-operator bonds must keep their length under a rigid motion
            f0 = {k: v[1] for k, v in ra.items()}
            f1 = {k: v[1] for k, v in pa.items()}
            allrb = [l for f in frags for l in f["atoms"]]
            b0 = {(o, l, m): d for o, l, m, d in image_bonds(info, allrb, f0)}
            b1 = {(o, l, m): d for o, l, m, d in image_bonds(info, allrb, f1)}
            common = set(b0) & set(b1)
            if not common:
                print("  no across-operator bonds to test (fragment is a whole molecule)")
            else:
                chg = sorted(((abs(b1[k]-b0[k]), k) for k in common), reverse=True)
                print("  %d across-operator bond(s); largest length change %.2e A"
                      % (len(common), chg[0][0]))
                # a genuine rigid motion cannot change these AT ALL: the good case
                # measures exactly 0 to float precision, so the bar is numerical
                # noise, not a chemical tolerance.
                if chg[0][0] > 1e-3:
                    fails.append("a declared DOF changes across-operator bond %s-%s "
                                 "through %s by %.2e A -- that is an internal "
                                 "distortion, not a rigid motion"
                                 % (chg[0][1][1], chg[0][1][2], chg[0][1][0],
                                    chg[0][0]))
                    for d, k in chg[:4]:
                        print("     %s  %s-%s  changed %.2e A" % (k[0], k[1], k[2], d))
                lost = set(b0) - set(b1)
                if lost:
                    fails.append("%d across-operator bond(s) BROKE entirely under the "
                                 "declared DOF: %s" % (len(lost),
                                 ", ".join("%s-%s" % (k[1], k[2])
                                           for k in list(lost)[:4])))

    print("\n" + "=" * 74)
    if fails:
        print("FAILED -- %d problem(s):" % len(fails))
        for f in fails:
            print("  * " + f)
        print("\nFiles kept for inspection: _verify_ctl.inp, _verify_rb.inp")
        raise SystemExit(1)
    print("PASS: the rigid body reproduces the plain-site model exactly.")
    print("      multiplicities agree with the independent computation, coordinates")
    print("      to <1e-9, and the calculated patterns are identical.")


if __name__ == "__main__":
    main()
