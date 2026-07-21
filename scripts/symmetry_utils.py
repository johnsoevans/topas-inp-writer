#!/usr/bin/env python3
"""
symmetry_utils.py -- shared crystallography engine used by both
cif_to_str.py (CIF -> str conversion) and check_inp_syntax.py's
check_symmetry_constraints (validating an existing .inp's site/lattice
constraints against what its own space group requires). Not a standalone
tool -- imported as a library only.

Covers:
  - Parsing symmetry-operator strings ('x+1/2, -y, z' -> rotation+translation)
  - Resolving a space group's operators via TOPAS's own database
    (sgcom6.exe / the sg/ directory) when no operator list is available
    directly (e.g. an .inp file only ever has a space_group symbol, never
    its own operator loop the way a CIF can)
  - Per-site Wyckoff constraint derivation (fixed / tied-via-Get() / free)
    for both position (classify_coordinates) and the ADP tensor
    (classify_adps -- u11/u22/u33/u12/u13/u23, via R U R^T = U rather than
    the affine position transformation)
  - Per-lattice-system angle/length constraint derivation (which of
    al/be/ga are forced to 90 or 120, which of b/c are tied to a)

See cif_to_str.py's own module docstring for the crystallographic reasoning
behind each piece (equation derivation, rhombohedral-axes disambiguation,
etc.) -- kept there rather than duplicated here since that's where it was
originally developed and verified.
"""

import os
import re
import subprocess
from fractions import Fraction

import topas_install


# ---------------------------------------------------------------------------
# Symmetry operator parsing: 'x+1/2, -y, z' -> (3x3 rotation, 3-translation)
# ---------------------------------------------------------------------------

def parse_symop_component(expr):
    """
    Parse one comma-separated component of a symmetry-operator string, e.g.
    '-y', 'x+1/2', '1/2-x', 'z' into (coeff_x, coeff_y, coeff_z, translation).
    """
    expr = expr.replace(" ", "").lower()
    coeffs = {"x": 0, "y": 0, "z": 0}
    translation = Fraction(0)
    terms = re.findall(r"[+-]?[^+-]+", expr)
    for term in terms:
        if term == "":
            continue
        sign = 1
        body = term
        if body[0] == "+":
            body = body[1:]
        elif body[0] == "-":
            sign = -1
            body = body[1:]
        if body in ("x", "y", "z"):
            coeffs[body] += sign
        elif "/" in body:
            num, den = body.split("/")
            translation += sign * Fraction(int(num), int(den))
        elif body != "":
            translation += sign * Fraction(body)
    return (coeffs["x"], coeffs["y"], coeffs["z"], translation)


def parse_symop_string(op_str):
    """'x, y+1/2, -z' -> ((r00,r01,r02, r10,r11,r12, r20,r21,r22), (t0,t1,t2))"""
    parts = op_str.split(",")
    if len(parts) != 3:
        raise ValueError(f"Symmetry operator does not have 3 components: {op_str!r}")
    rows = []
    translation = []
    for part in parts:
        cx, cy, cz, t = parse_symop_component(part)
        rows.append((cx, cy, cz))
        translation.append(t)
    return rows, translation


def apply_symop(rows, translation, p):
    """Apply a parsed symop to a point p=(x,y,z) of floats or Fractions."""
    out = []
    for (cx, cy, cz), t in zip(rows, translation):
        val = cx * p[0] + cy * p[1] + cz * p[2] + float(t)
        out.append(val)
    return tuple(out)


def mod1(v, tol=1e-6):
    r = v % 1.0
    if r > 1 - tol:
        r -= 1.0
    return r


def points_equal_mod1(p, q, tol):
    for a, b in zip(p, q):
        d = abs(mod1(a - b, tol))
        if d > tol and abs(d - 1.0) > tol:
            return False
    return True


# ---------------------------------------------------------------------------
# Fallback: resolve symmetry operators via TOPAS's own space-group database
# (sgcom6.exe / the sg/ directory) -- used whenever operators aren't
# available directly from the source (a CIF missing its own
# _symmetry_equiv_pos_as_xyz loop, or an .inp file, which never carries its
# own operator list at all -- only a space_group symbol).
# ---------------------------------------------------------------------------

def strip_rhombohedral_axes_suffix(symbol):
    """
    CIF's rhombohedral-axes-choice annotation (':H' hexagonal axes, ':R'
    rhombohedral axes -- e.g. 'R_3_2_:H', 'R_-3_c_:H') is dropped entirely
    by sgcom6.exe/tc.exe, which resolve the bare symbol straight to the
    hexagonal-axes .sg file either way (confirmed empirically for two
    independent symbols: 'R_-3_c_:H' -> r-3c.sg, 'R_3_2_:H' -> r32.sg --
    NOT 'r-3c:h.sg'/'r32:h.sg' as a naive concatenation would predict).
    Deliberately narrow: only ':H'/':R' are handled this way. CIF's other
    colon-suffix convention, the origin-choice qualifier on centrosymmetric
    groups like P4/n (':1'/':2', e.g. 'P_4/n_b_m_:1'), is NOT touched here
    -- sgcom6 renders those under its own unpredictable naming (confirmed
    empirically to NOT be a simple 'append the digit' or 'drop it' rule),
    and guessing wrong there risks silently resolving the WRONG origin
    setting relative to the CIF's own atom coordinates, which is worse
    than an honest failure.
    """
    return re.sub(r":\s*[HhRr]\s*$", "", symbol)


def sg_filename_for_symbol(symbol):
    """
    Predicts the .sg filename sgcom6.exe writes for a given space-group
    symbol: lowercased, whitespace/underscores stripped, and '/' replaced
    with 'o' (confirmed empirically -- sgcom6 can't put a literal '/' in a
    Windows filename, e.g. symbol 'p21/n' -> file 'p21on.sg'; the stored
    `symbol` field *inside* the file keeps the real '/' unchanged).
    """
    symbol = strip_rhombohedral_axes_suffix(symbol)
    s = re.sub(r"[\s_]", "", symbol).lower()
    return s.replace("/", "o") + ".sg"


def parse_sg_file(path):
    """
    Parse a TOPAS .sg file's `xyzs { ... }` block into the same
    (rows, translation) operator format parse_symop_string produces, plus
    the `space_group { ... }` header fields (point_group, unique_axis,
    rhombohedral_hexagonal) as a dict. Comment lines inside `xyzs` (starting
    with `'`, e.g. "' +(-1/3, 1/3, 1/3) ---") are skipped.
    """
    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    header = {}
    header_match = re.search(r"space_group\s*\{(.*?)\}", text, re.DOTALL)
    if header_match:
        for line in header_match.group(1).splitlines():
            line = line.strip()
            if not line or line.startswith("'"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                header[parts[0]] = parts[1].strip()

    symops = []
    xyzs_match = re.search(r"xyzs\s*\{(.*?)\}", text, re.DOTALL)
    if xyzs_match:
        for line in xyzs_match.group(1).splitlines():
            line = line.strip()
            if not line or line.startswith("'"):
                continue
            try:
                symops.append(parse_symop_string(line))
            except ValueError:
                continue

    return symops, header


def resolve_sg_operators(symbol):
    """
    Resolve symmetry operators for `symbol` via TOPAS's own space-group
    database: read the .sg file if it already exists under TOPAS_DIR/sg
    (the common case -- 100+ are typically already generated from prior
    real refinement runs), otherwise generate it with `sgcom6.exe SYMBOL
    -dir sg` (run from TOPAS_DIR, which sgcom6 requires -- it looks for
    sgcom5.txt relative to its own working directory, confirmed directly:
    invoking it from any other cwd fails with "Cannot open file
    sgcom5.txt").

    Returns (symops, header_dict, message). On failure (TOPAS_DIR unset,
    sgcom6.exe missing, or the symbol doesn't resolve to a real space
    group), returns ([], {}, <explanation>) rather than raising -- this is
    a best-effort fallback, not a hard requirement.
    """
    topas_dir, found = topas_install.get_topas_dir()
    if not found:
        return [], {}, "TOPAS_DIR is not set -- cannot resolve symmetry operators via sgcom6.exe."

    sgcom6_path = os.path.join(topas_dir, "sgcom6.exe")
    sg_dir = os.path.join(topas_dir, "sg")
    if not os.path.isfile(sgcom6_path):
        return [], {}, f"sgcom6.exe not found under TOPAS_DIR ({topas_dir})."

    filename = sg_filename_for_symbol(symbol)
    sg_path = os.path.join(sg_dir, filename)

    if not os.path.isfile(sg_path):
        try:
            subprocess.run(
                [sgcom6_path, symbol, "-dir", "sg"],
                cwd=topas_dir, capture_output=True, timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as e:
            return [], {}, f"Failed to run sgcom6.exe for symbol {symbol!r}: {e}"

    if not os.path.isfile(sg_path):
        return [], {}, (
            f"sgcom6.exe did not produce a .sg file for symbol {symbol!r} "
            f"(expected {sg_path}) -- the symbol likely isn't in a form "
            f"sgcom6.exe recognizes (it wants the concise form, e.g. "
            f"'fm-3m' or 'p21/n', not CIF's underscore-spaced style)."
        )

    symops, header = parse_sg_file(sg_path)
    return symops, header, f"Resolved via TOPAS's own space-group database: {sg_path}"


# ---------------------------------------------------------------------------
# Site-symmetry / Wyckoff-constraint derivation
# ---------------------------------------------------------------------------

COORD_NAME = ["x", "y", "z"]


def find_stabilizer(point, symops, tol):
    """Return the list of (rows, translation) operators that fix `point` mod 1."""
    stab = []
    for rows, translation in symops:
        img = apply_symop(rows, translation, point)
        if points_equal_mod1(img, point, tol):
            stab.append((rows, translation))
    return stab


def classify_coordinates(point, stabilizer):
    """
    Returns a dict coord -> constraint, where constraint is one of:
      ('free', None)
      ('fixed', value)              -- value taken from the known point itself
      ('tied', other_coord, sign, offset)   -- coord = sign*other_coord + offset
      ('complex', ...)              -- constraint this simple model can't express

    Derivation: each non-identity stabilizing operator (R, T) contributes, for
    each row i, the equation (R-I)_i . p == -T_i (mod 1) -- NOT an equation
    "about coordinate i" in general. Which coordinate(s) it actually
    constrains is read off the *nonzero positions of (R-I)_i*, which can
    differ from i itself (e.g. an operator whose x-output is "x - y" gives
    (R-I)_x = (0,-1,0), a constraint purely on y, not on x).

    A row with exactly one nonzero entry at position j fixes coordinate j to
    a constant (solved directly from the known numeric value, not
    symbolically). A row with exactly two nonzero entries at positions j,k
    (with |coefficient|==1 on at least one of them) ties those two
    coordinates together. Three-or-more-entry rows, or two-entry rows where
    neither coefficient is +-1, are flagged 'complex' rather than guessed at.

    Because a genuine tie can form a CYCLE with no fixed anchor at all (e.g.
    a site on a 3-fold body-diagonal axis, x=y=z, all three mutually tied
    and none individually pinned to a constant -- see ZrW2O8's W1/W2/O4),
    ties are resolved per connected component: if any member of a tied
    component is independently fixed, the whole component is fixed.
    Otherwise the free representative is whichever member every other
    coordinate can be validly expressed FROM (see tie_adj below for why
    that's not always the alphabetically-first one), with ties among
    multiple valid representatives broken alphabetically.
    """
    fixed_idx = set()
    # tie_adj[j] = list of (k, sign, offset) meaning p_j = sign*p_k + offset
    # (mod 1) -- j is DEPENDENT, k is the side it's expressed in terms of.
    # DIRECTED: only added on the side being solved FOR (the variable with
    # unit coefficient in the pair). A relation like `x - 2y = 0` only has
    # one algebraically valid direction, x = 2*y -- "solving" the reverse,
    # y = x/2 (mod 1), is multi-valued (both x/2 and x/2+1/2 satisfy it) and
    # not added. Only when BOTH coefficients have unit magnitude (e.g.
    # x - y = 0) is the relation genuinely invertible, and only then is a
    # reverse edge added too.
    tie_adj = {0: [], 1: [], 2: []}
    complex_idx = {}

    for rows, translation in stabilizer:
        for i in range(3):
            row = rows[i]
            unit = tuple(1 if k == i else 0 for k in range(3))
            diff = tuple(row[k] - unit[k] for k in range(3))
            if diff == (0, 0, 0):
                continue  # this row says nothing about any coordinate
            nonzero = [(k, v) for k, v in enumerate(diff) if v != 0]
            rhs = -float(translation[i])
            if len(nonzero) == 1:
                j, _ = nonzero[0]
                fixed_idx.add(j)
            elif len(nonzero) == 2:
                (j, cj), (k, ck) = nonzero
                if abs(cj) == 1:
                    # solves for p_j: p_j = -cj*ck*p_k + cj*rhs
                    sign = int(-cj * ck)
                    offset = cj * rhs
                    tie_adj[j].append((k, sign, offset))
                    if abs(ck) == 1:
                        # also invertible the other way: p_k = sign*p_j - offset/...
                        # (sign is self-inverse since |sign|==1 here)
                        tie_adj[k].append((j, sign, sign * (-offset)))
                elif abs(ck) == 1:
                    sign = int(-ck * cj)
                    offset = ck * rhs
                    tie_adj[k].append((j, sign, offset))
                    if abs(cj) == 1:
                        tie_adj[j].append((k, sign, sign * (-offset)))
                else:
                    complex_idx[i] = (row, float(translation[i]))
            else:
                complex_idx[i] = (row, float(translation[i]))

    # A pair (j, k) can receive MULTIPLE tie contributions -- one per
    # distinct stabilizing operator row that happens to relate them -- and
    # those contributions aren't guaranteed to agree (e.g. Al2O3's Al1 at
    # (0,0,z) under R-3c: one operator implies y=-x, another y=2x). Both can
    # only be true when x=y=0, i.e. the pair isn't a genuine one-parameter
    # tied line at all -- it's jointly FIXED at the point's own value, the
    # same way classify_adps's homogeneous system resolves an
    # over-determined case by solving everything together rather than
    # picking one equation. Detected by checking every pair of tie
    # contributions for the same (j, k) agree (within tolerance) on both
    # sign and offset; a disagreement marks BOTH coordinates fixed (their
    # tie edges dropped) rather than trusting an arbitrary one.
    conflicted = set()
    for j in range(3):
        seen = {}
        for (k, sign, offset) in tie_adj[j]:
            prior = seen.get(k)
            if prior is not None:
                prior_sign, prior_offset = prior
                if prior_sign != sign or abs(prior_offset - offset) > 1e-6:
                    conflicted.add(j)
                    conflicted.add(k)
            else:
                seen[k] = (sign, offset)
    if conflicted:
        fixed_idx |= conflicted
        for i in conflicted:
            tie_adj[i] = [(k, s, o) for (k, s, o) in tie_adj[i] if k not in conflicted]

    constraint = {}
    visited = set()

    # Connectivity (which coordinates are related, for grouping) is the
    # undirected closure of tie_adj's directed edges (see its own comment
    # above). But the free REPRESENTATIVE of a component must be a
    # coordinate every other member can be expressed FROM -- a node with a
    # directed path *into* it from every dependent -- not just any member,
    # since tie_adj[dependent] -> ... -> repr must actually exist.
    def related(a, b, seen=None):
        if seen is None:
            seen = set()
        seen.add(a)
        for (k, _, _) in tie_adj[a]:
            if k == b:
                return True
            if k not in seen and related(k, b, seen):
                return True
        return False

    def undirected_component(start):
        comp = {start}
        changed = True
        while changed:
            changed = False
            for a in range(3):
                if a in comp:
                    continue
                for b in list(comp):
                    if related(a, b) or related(b, a):
                        comp.add(a)
                        changed = True
                        break
        return comp

    def resolve_relative(node, root, seen=None):
        """Walk tie_adj[node] -> ... -> root, composing sign/offset, so
        p_node = sign*p_root + offset. Returns (sign, offset) or None if no
        directed path from node to root exists."""
        if node == root:
            return (1, 0.0)
        if seen is None:
            seen = set()
        seen.add(node)
        for (k, sign_nk, offset_nk) in tie_adj[node]:
            if k == root:
                return (sign_nk, offset_nk)
            if k in seen:
                continue
            sub = resolve_relative(k, root, seen)
            if sub is not None:
                sub_sign, sub_offset = sub
                return (sign_nk * sub_sign, sign_nk * sub_offset + offset_nk)
        return None

    for i in range(3):
        coord = COORD_NAME[i]
        if i in visited:
            continue
        if i in complex_idx:
            row, t = complex_idx[i]
            constraint[coord] = ("complex", row, t)
            visited.add(i)
            continue
        comp = undirected_component(i)
        visited |= comp
        comp_fixed = any(k in fixed_idx for k in comp)
        if len(comp) == 1 and i not in fixed_idx:
            constraint[coord] = ("free", None)
        elif comp_fixed or i in fixed_idx:
            for k in comp:
                constraint[COORD_NAME[k]] = ("fixed", point[k])
        else:
            # Pick the alphabetically-first coordinate that every other
            # member can be validly expressed FROM (see docstring).
            candidates = []
            for repr_idx in sorted(comp, key=lambda k: COORD_NAME[k]):
                rels = {}
                ok = True
                for k in comp:
                    if k == repr_idx:
                        continue
                    rel = resolve_relative(k, repr_idx)
                    if rel is None:
                        ok = False
                        break
                    rels[k] = rel
                if ok:
                    candidates.append((repr_idx, rels))
                    break
            if not candidates:
                # No coordinate in this component can express all the
                # others directly (shouldn't happen for a 2-member tie, but
                # guard rather than crash) -- fall back to marking the
                # whole component fixed at its known values.
                for k in comp:
                    constraint[COORD_NAME[k]] = ("fixed", point[k])
                continue
            repr_idx, rels = candidates[0]
            constraint[COORD_NAME[repr_idx]] = ("free", None)
            for k, (sign, offset) in rels.items():
                constraint[COORD_NAME[k]] = ("tied", COORD_NAME[repr_idx], sign, offset)

    return constraint


def check_multiplicity(point, symops, stabilizer):
    """Orbit size = (order of full operator list) / (order of stabilizer)."""
    return len(symops) // len(stabilizer)


# ---------------------------------------------------------------------------
# Anisotropic displacement parameter (ADP / Uij tensor) constraint
# derivation -- mirrors classify_coordinates, but for the site's ADP tensor
# rather than its position. TOPAS's own `adps` keyword already does this
# internally at runtime ("adps generates the unn atomic displacement
# parameters with considerations made for special positions... On
# termination of refinement the adps keyword is replaced with the unn
# parameters" -- references/21-keyword-index.md) using "the 3x3 eigenvalue
# determination routine of Kopp (2006)"; this is an independent derivation
# for use ahead of an actual refinement run (e.g. converting a CIF's own
# _atom_site_aniso_U_11..23 values, or validating an existing .inp's u11..
# u23 against what site symmetry requires), not a replacement for it.
# ---------------------------------------------------------------------------

ADP_NAMES = ["u11", "u22", "u33", "u12", "u13", "u23"]
# Each name's (row, col) position in the symmetric 3x3 tensor (0-indexed).
ADP_PAIRS = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]


def adp_transform_matrix(rows):
    """
    Build the 6x6 matrix T such that, for the 6-vector of unique tensor
    components u = [u11,u22,u33,u12,u13,u23], the ADP tensor transformed by
    rotation matrix `rows` (U' = R U R^T) has unique components T @ u.
    Computed directly from the transformation (not a hand-derived formula)
    by transforming each of the 6 symmetric basis matrices in turn --
    avoids the bug risk of deriving R U R^T's index algebra by hand.
    """
    T = [[0] * 6 for _ in range(6)]
    for l, (c, d) in enumerate(ADP_PAIRS):
        e = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        e[c][d] = 1
        e[d][c] = 1
        re = [[sum(rows[i][k] * e[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
        rer = [[sum(re[i][k] * rows[j][k] for k in range(3)) for j in range(3)] for i in range(3)]
        for k, (a, b) in enumerate(ADP_PAIRS):
            T[k][l] = rer[a][b]
    return T


def _rref(rows, num_cols, column_order):
    """
    Reduced row-echelon form over exact Fraction arithmetic, seeking pivots
    in `column_order` (not necessarily left-to-right) rather than the
    standard column order -- lets the caller bias which variables end up as
    pivots (dependent) vs free. Returns (rref_rows, {pivot_col: row_index}).
    """
    rows = [[Fraction(x) for x in r] for r in rows]
    n = len(rows)
    pivot_row = 0
    pivot_map = {}
    for col in column_order:
        sel = None
        for i in range(pivot_row, n):
            if rows[i][col] != 0:
                sel = i
                break
        if sel is None:
            continue
        rows[pivot_row], rows[sel] = rows[sel], rows[pivot_row]
        pv = rows[pivot_row][col]
        rows[pivot_row] = [x / pv for x in rows[pivot_row]]
        for i in range(n):
            if i != pivot_row and rows[i][col] != 0:
                factor = rows[i][col]
                rows[i] = [a - factor * b for a, b in zip(rows[i], rows[pivot_row])]
        pivot_map[col] = pivot_row
        pivot_row += 1
        if pivot_row == n:
            break
    return rows, pivot_map


def classify_adps(stabilizer):
    """
    Returns a dict adp_name -> constraint, where constraint is one of:
      ('free', None)
      ('fixed', Fraction(0))               -- always exactly zero (see below)
      ('tied', [(coeff, other_name), ...])  -- linear combination of one or
                                                more free components

    Derivation: for each NON-IDENTITY stabilizing operator's rotation part
    R (translation is irrelevant -- a tensor property at a fixed point
    doesn't depend on it), the ADP tensor must satisfy R U R^T = U. This
    gives up to 6 linear equations (T - I) u = 0 in the 6 unique tensor
    components, accumulated across every stabilizing operator and solved
    together via Gaussian elimination (unlike classify_coordinates, a
    hand-rolled pairwise model isn't sufficient here -- a single 3-fold
    rotation already mixes 3 components, e.g. u11/u22/u12, in one
    equation).

    Unlike position constraints, ADP constraints are always HOMOGENEOUS (no
    translation/affine part) -- there's no physical "location" for a
    tensor, just linear relationships among its components. So a component
    with no free-variable dependence in its solved row is always fixed at
    exactly zero, never some other constant (a real difference from
    classify_coordinates's 'fixed' case, which takes the constant from the
    site's own position).

    Pivot columns (the dependent variables) are chosen in REVERSE of
    ADP_NAMES order (u23, u13, u12, u33, u22, u11) so that, when there's a
    choice, the diagonal Uii components stay free/independent -- matching
    standard crystallographic convention (diagonal terms are the "primary"
    refined ADPs; off-diagonal terms are more often the ones tied or zeroed
    by symmetry). Verified against real CIF data (ZrW2O8's Zr1 and W1 sites,
    both on 3-fold body-diagonal axes in Pa-3): both show U11=U22=U33 (one
    group of three equal diagonal components) and U12=U13=U23 (a second
    group of three equal off-diagonal components) in the actual refined
    values, matching this derivation's classification exactly.
    """
    identity = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    equations = []
    for rows, _t in stabilizer:
        if tuple(tuple(r) for r in rows) == identity:
            continue
        T = adp_transform_matrix(rows)
        for k in range(6):
            row = [T[k][l] - (1 if l == k else 0) for l in range(6)]
            if any(v != 0 for v in row):
                equations.append(row)

    if not equations:
        return {name: ("free", None) for name in ADP_NAMES}

    column_order = [5, 4, 3, 2, 1, 0]
    rref_rows, pivot_map = _rref(equations, 6, column_order)

    free_cols = [c for c in range(6) if c not in pivot_map]
    constraint = {ADP_NAMES[c]: ("free", None) for c in free_cols}
    for col, row_idx in pivot_map.items():
        row = rref_rows[row_idx]
        terms = [(-row[fc], ADP_NAMES[fc]) for fc in free_cols if row[fc] != 0]
        constraint[ADP_NAMES[col]] = ("tied", terms) if terms else ("fixed", Fraction(0))
    return constraint


def format_adp_tie(terms):
    """
    'terms' is a list of (Fraction coeff, other_adp_name) from
    classify_adps's 'tied' result -- format as a TOPAS equation RHS, e.g.
    a single term [(1, 'u11')] -> 'Get(u11)', [(-1, 'u12')] -> '-Get(u12)',
    a fractional coefficient [(Fraction(1,2), 'u11')] -> 'Get(u11) / 2', or
    a genuine multi-term combination (rare, but the general linear-algebra
    derivation can produce one) -> 'Get(u12) + Get(u13)' style. Shared by
    cif_to_str.py (generation) and check_inp_syntax.py (validation
    messages), so both describe a required tie identically.
    """
    parts = []
    for i, (coeff, other) in enumerate(terms):
        neg = coeff < 0
        mag = abs(coeff)
        if mag.denominator == 1:
            body = f"Get({other})" if mag == 1 else f"{mag.numerator} * Get({other})"
        elif mag.numerator == 1:
            body = f"Get({other}) / {mag.denominator}"
        else:
            body = f"{mag.numerator} * Get({other}) / {mag.denominator}"
        if i == 0:
            parts.append(("-" if neg else "") + body)
        else:
            parts.append((" - " if neg else " + ") + body)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Crystal-system / lattice-parameter constraint derivation
# ---------------------------------------------------------------------------

def classify_crystal_system(symops):
    """
    Classify the lattice's crystal system from the rotation parts of the
    symmetry operators -- no external space-group table needed. Returns one
    of: 'cubic', 'tetragonal', 'hexagonal_or_trigonal', 'orthorhombic',
    'monoclinic_a'/'monoclinic_b'/'monoclinic_c' (unique-axis variants),
    'triclinic'.

    Method: classify each operator's rotation matrix by (determinant, trace)
    -- the standard crystallographic invariants for rotation order (identity
    trace=3, 2-fold trace=-1, 3-fold trace=0, 4-fold trace=1, 6-fold
    trace=2, each also possible improper/rotoinverted at det=-1). Cubic is
    identified by >=8 proper 3-folds (four body-diagonal axes); a single
    3-fold axis (2 operators) is trigonal/hexagonal (both fix al=be=90,
    ga=120 and a=b in the standard hexagonal-axes setting); a 4-fold means
    tetragonal. Otherwise, axis-aligned (diagonal-matrix) 2-folds/mirrors
    are counted by which principal axis they lie along: three distinct axes
    is orthorhombic, exactly one is monoclinic (recorded by which axis is
    unique), none beyond identity/inversion is triclinic.
    """
    def det3(r):
        return (r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1])
                - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
                + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]))

    proper_3fold = 0
    has_4fold = False
    diag_axes = set()

    for rows, _t in symops:
        r = rows
        d = det3(r)
        tr = r[0][0] + r[1][1] + r[2][2]
        if d == 1 and tr == 0:
            proper_3fold += 1
        if (d == 1 and tr == 1) or (d == -1 and tr == -1):
            has_4fold = True
        is_diag = all(r[i][j] == 0 for i in range(3) for j in range(3) if i != j)
        if is_diag:
            if d == 1 and tr == -1:
                axis = [i for i in range(3) if r[i][i] == 1][0]
                diag_axes.add(axis)
            elif d == -1 and tr == 1:
                axis = [i for i in range(3) if r[i][i] == -1][0]
                diag_axes.add(axis)

    if proper_3fold >= 8:
        return "cubic"
    elif proper_3fold >= 2:
        return "hexagonal_or_trigonal"
    elif has_4fold:
        return "tetragonal"
    elif len(diag_axes) >= 3:
        return "orthorhombic"
    elif len(diag_axes) == 1:
        axis = next(iter(diag_axes))
        return ["monoclinic_a", "monoclinic_b", "monoclinic_c"][axis]
    else:
        return "triclinic"


ANGLE_CONSTRAINTS_BY_SYSTEM = {
    "cubic": {"al": 90, "be": 90, "ga": 90},
    "tetragonal": {"al": 90, "be": 90, "ga": 90},
    "hexagonal_or_trigonal": {"al": 90, "be": 90, "ga": 120},
    "orthorhombic": {"al": 90, "be": 90, "ga": 90},
    "monoclinic_a": {"be": 90, "ga": 90},
    "monoclinic_b": {"al": 90, "ga": 90},
    "monoclinic_c": {"al": 90, "be": 90},
    "triclinic": {},
}

# Which of b/c are tied to a (b = Get(a), c = Get(a)) by the crystal system's
# own symmetry -- e.g. cubic forces a=b=c, tetragonal/hexagonal/trigonal
# force a=b (c independent). Orthorhombic/monoclinic/triclinic force no
# length relationship at all in the standard axis setting.
LENGTH_TIES_BY_SYSTEM = {
    "cubic": {"b": "a", "c": "a"},
    "tetragonal": {"b": "a"},
    "hexagonal_or_trigonal": {"b": "a"},
    "orthorhombic": {},
    "monoclinic_a": {},
    "monoclinic_b": {},
    "monoclinic_c": {},
    "triclinic": {},
}


def determine_fixed_angles(symops, cell_angles, tol=0.05):
    """
    Which of al/be/ga are forced to exactly 90 (deg) by the crystal system.
    Only confirmed if the actual angle value is also within `tol` of 90 --
    guards against a misclassification (e.g. an unusual axis setting) ever
    silently claiming an angle that doesn't actually match. Does NOT confirm
    a required 120 (hexagonal ga) the same way -- callers that need to
    detect a *missing* 120 (which would wrongly default to TOPAS's own 90)
    should use classify_crystal_system + ANGLE_CONSTRAINTS_BY_SYSTEM
    directly instead.
    """
    fixed = ANGLE_CONSTRAINTS_BY_SYSTEM.get(classify_crystal_system(symops), {})
    names = {"al": cell_angles[0], "be": cell_angles[1], "ga": cell_angles[2]}
    confirmed = set()
    for name, expected in fixed.items():
        actual = names[name]
        if actual is not None and abs(actual - expected) < tol and expected == 90:
            confirmed.add(name)
    return confirmed


def determine_length_ties(symops, cell_lengths, cell_angles=None, tol_rel=0.001, tol_deg=0.05):
    """
    Determine which of b/c should be expressed as `= Get(a);` rather than an
    independent value, based on the crystal system derived from the
    symmetry operators (see classify_crystal_system). Only applied if the
    actual stated lengths agree to within `tol_rel` (relative) of each
    other -- guards against ever silently tying two lengths the data itself
    disagrees on (e.g. a mis-set axes convention). Returns a dict like
    {'b': 'a', 'c': 'a'} (cubic) or {'b': 'a'} (tetragonal/hexagonal/
    trigonal) or {} (nothing tied).

    Rhombohedral-axes disambiguation: a single 3-fold axis (rotation-only
    classification 'hexagonal_or_trigonal') is ambiguous between the
    standard hexagonal-axes setting (a=b, al=be=90, ga=120 -- ties only b to
    a) and the rhombohedral-axes setting (a=b=c, al=be=ga, generally != 90 --
    confirmed as a real, TOPAS-supported case by `sgcom5.txt`'s separate
    `r3r`/`r-3r`/`r32r`/... entries for every rhombohedral space group, and
    by topas.inc's own `Rhombohedral(a_cv, al_cv)` macro, which ties all of
    b=Get(a); c=Get(a); be=Get(al); ga=Get(al);). Rotation matrices alone
    can't distinguish the two settings; the actual angle values can -- if
    al/be/ga are mutually equal but not close to the hexagonal (90, 90, 120)
    pattern, this is the rhombohedral-axes case, and c is tied to a as well
    (the angle values themselves are left explicit and independent here,
    not tied to each other -- only lengths are in scope in this function).
    """
    system = classify_crystal_system(symops)
    ties = dict(LENGTH_TIES_BY_SYSTEM.get(system, {}))
    if system == "hexagonal_or_trigonal" and cell_angles is not None:
        al, be, ga = cell_angles
        if al is not None and be is not None and ga is not None:
            is_hex_axes = abs(al - 90) < tol_deg and abs(be - 90) < tol_deg and abs(ga - 120) < tol_deg
            is_rhombohedral_axes = abs(al - be) < tol_deg and abs(be - ga) < tol_deg
            if not is_hex_axes and is_rhombohedral_axes:
                ties = {"b": "a", "c": "a"}
    a, b, c = cell_lengths
    values = {"a": a, "b": b, "c": c}
    confirmed = {}
    for dependent, independent in ties.items():
        v1, v2 = values[dependent], values[independent]
        if v1 is not None and v2 is not None and abs(v1 - v2) / v2 < tol_rel:
            confirmed[dependent] = independent
    return confirmed


# ---------------------------------------------------------------------------
# Fraction-snapping for coordinate values (display only)
# ---------------------------------------------------------------------------

COMMON_FRACTIONS = [Fraction(n, d) for d in (1, 2, 3, 4, 6, 8, 12) for n in range(d)]


def snap_to_fraction(value, tol=0.0015):
    """Returns (snapped_float, Fraction_or_None). The Fraction is only
    returned when `value` sits within `tol` of it AND the integer part is 0
    (i.e. a plain fractional coordinate) -- callers use it to emit an exact
    'coord = N/D;' equation instead of a rounded decimal, which is both more
    precise and matches this skill's own check_xyz_near_one_third guidance."""
    frac = value % 1.0
    for f in COMMON_FRACTIONS:
        if abs(frac - float(f)) < tol:
            snapped = float(f) + (value - frac)
            exact = f if abs(value - frac) < 1e-9 else None
            return snapped, exact
    return value, None
