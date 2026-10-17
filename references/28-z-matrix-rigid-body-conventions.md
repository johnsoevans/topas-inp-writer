# Z-matrix rigid-body conventions — findings from refinement sessions

This document contains empirically-verified conventions for building `z_matrix` rigid bodies against real CIF
fragments, distilled from real refinement sessions (not the Technical Reference manual's own prose
— see `references/13-rigid-bodies.md` for that). 

**Every rule carries a stable citable tag** (`ZM1`, `ZM2`, …) in one increasing sequence, confined to
this file only — a `ZM`-number means nothing outside `28-z-matrix-rigid-body-conventions.md`. Never
cite a `ZM` number in `SKILL.md`, other `references/*.md`, `scripts/*.py`, or any `.inp`/report —
refer to the rule by topic and look the number up here, since it renumbers independently of other documents.

**The next free ZM number is ZM19.** Update this line whenever a rule is added.

## Geometry construction

**(ZM1) TOPAS's `z_matrix` dihedral is the negative of the standard atan2 extraction formula.**
If building a z-matrix from real 3D coordinates
with a standard geometry library/formula, either negate at the point the value is extracted (so
every value handled afterwards, including the NeRF reconstruction — Natural Extension Reference Frame, the standard
algorithm that rebuilds Cartesian coordinates from a z-matrix one atom at a time — used for a
self-consistency check, stays in TOPAS's own convention throughout), or negate only at the point of writing the
`.inp` — but not both, and not neither. Getting this backwards produces the mirror-image
(enantiomeric) placement of everything past the 3rd atom — a reflection through the plane of the
first three. A self-check cannot catch it: extraction and reconstruction share the same sign, so
the round trip agrees with itself to machine precision. The reliable check is comparing
`Out_CIF_STR`'s own computed coordinates against the source CIF atom by atom, or the plain-`site`
control (ZM6).

**(ZM2) The z-matrix's literal 3rd atom is placed along `normalize(cross(global_Y_axis, bc))`**,
not an arbitrary projection of the y-axis, where `bc = normalize(bond_parent_pos - angle_ref_pos)`
— *this atom's own* bond-parent and angle-reference positions, not fixed atom1/atom2 roles. In the
common case (3rd atom's bond-parent is the 2nd-placed atom, angle-reference is the root), this
reduces to `bc = normalize(atom2 - atom1)`. But when the 3rd atom instead bonds back to the root
(common for a high-connectivity root), `bc` uses that same pair the other way round and flips
sign — applying the `atom2 - atom1` form unconditionally in that swapped case silently rotates the
whole fragment 180° about the 1–2 bond (indistinguishable from a mirror image only for a
planar fragment). This is the precise, empirically-confirmed formula behind
TOPAS's own qualitative atom-3 placement rule (`references/13-rigid-bodies.md`: atom 1 at the
origin, atom 2 on +z, atom 3 in the x-z plane — its syntax section says x-y, but x-z is correct). **Corollary: that atom's azimuth is not yours to
choose** — TOPAS sets it to exactly 0/180, so derive the local frame from that atom and the chosen
local z, never from a fragment-wide best-fit plane. A best-fit normal on a slightly non-planar
fragment will put every atom ~1e-3 out while a self-consistent round-trip will still read 2e-16.

**(ZM3) A ring built with a dummy atom at its real Cartesian centroid** (synthetic bonds to every
real ring atom, no change to the true bond graph) is the conventional approach and gives
the tree-builder a chemically-central reference point instead of an arbitrary other ring atom.
Consequence, inherent to the idiom rather than any specific implementation: with a centroid dummy,
every ring atom's parent becomes the dummy, so true ring C–C (etc.) bond lengths never appear as
z_matrix parameters and cannot be restrained directly — a spanning tree cannot express ring closure
either way.

**(ZM4) A z-matrix reference (angle or dihedral) does not need to be a real bonded neighbour** —
only already-placed. Prefer an already-placed bonded neighbour of the previous reference where one
exists (keeps the angle/dihedral chemically meaningful), falling back to that reference's own
ancestor chain, then to any other already-placed atom — mirroring how a real hand-built z-matrix
uses a dummy or distant atom as a geometric anchor.

**(ZM5) Skip (don't select) a reference atom that would make the (great-grandparent `ggp`,
grandparent `gp`, parent) triple collinear**
— collinearity makes the dihedral numerically degenerate (zero cross product). A real
trap at branch points off a 3-coordinate hub (e.g. a Cp* ring's own ipso carbons). If every
candidate is collinear, TOPAS itself will reject a resulting 3-term z_matrix line for an atom
preceded by three or more points; raise rather than emit it.

## Special positions and rigid bodies — a real precision trap

**(ZM6) `num_posns` is the single most direct check that a rigid body placed its special-position atoms correctly.**
TOPAS only echoes `num_posns` for a site that already carried a `num_posns` token, so
put a placeholder (`num_posns 0` is fine) on any site you want to audit, then compare the value in
the `.out` against the true Wyckoff multiplicity. **The Kabsch RMSD cannot see this (~1e-14) and
neither can an `Out_CIF_STR` coordinate round-trip (~1e-7) — both pass while the pattern is wrong.**
The `.out` site echo gives 5 dp; for `num_posns` and full-precision coordinates together use
`atom_out` with an explicit C format, e.g. `" %23.18f" = Get_From_String(Get(current_atom), x);`.

**Stronger still: refine the same atoms as plain `site` lines as a control.** At the source
geometry a correct rigid body must give an *identical* calculated pattern — same reflection count,
same intensities, same Rwp. This catches what `num_posns` cannot (wrong ADP form, wrong occupancy,
a frame mismatch of ~1e-3): `num_posns` can pass a wrong model; the control cannot.

**If auditing through the GUI rather than `tc.exe`, keep a pristine copy of the input.** `tc.exe`
writes only the `.out`, so the `.inp` is untouched and re-runnable. The GUI (`ta.exe`)
writes results back into the `.inp` itself on termination, so it overwrites the `num_posns`
placeholder — a second run of an already-run file is no longer testing the original input, and a
file that has been through the GUI once may already carry a computed (possibly invalid) multiplicity
that looks like something you typed.

**(ZM7) TOPAS's ~1e-9 (fractional) special-position window is narrower than the ~1e-8 residue a rigid body's z-matrix → NeRF → `rotate` → `translate` chain accumulates.**
An atom meant to sit exactly on a special position can therefore miss it and create incorrect symmetry copies. One diagnostic signature is a `num_posns` that isn't a divisor of the general-position multiplicity (e.g. `6` where the general position is `8` — 6 does not divide 8, which is the giveaway) — some symmetry copies merged, some didn't.

- Risk is per-atom and per-construction: it applies wherever the special coordinate is an *approximate*
  arithmetic result rather than an *exact* one.
- Do NOT nudge the coordinate — TOPAS then legitimately generates more copies, swapping one wrong answer
  for another.

`scripts/rigid_body_builder.py`'s `find_special_position_risk()` implements this detection — advisory only,
it flags at-risk atoms without altering anything.

**(ZM8) A source CIF's own reported coordinate for a special-position atom usually isn't precise
enough to satisfy (ZM7)'s window** — ordinary rounding from the original refinement leaves it
accurate to only ~1e-4 fractional, far short of the ~1e-9 needed. Don't build the z-matrix from the
atom's reported value directly: derive the exact required position algebraically from the
symmetry operator's own exact/rational coefficients and snap the target onto it first.

**(ZM9) Write z_matrix bond/angle/dihedral values to ~12 decimal places, not ~6.** A z-matrix that lands inside (ZM7)'s window at 12 dp can miss it at 6 dp on a
deep-chain atom — a distinct cause from (ZM8) (output rounding vs. input target precision),
landing in the same failure mode.

**(ZM10) One fix for (ZM7) is to place the atoms exactly by construction: choose the local frame so the constrained coordinate
is 0, restrict the rotation so it cannot change that, and fix the translate component at the special
value.** Three cases to consider:

- **≥3 atoms on one mirror:**
  1. *Frame:* they become z_matrix atoms 1–3, which TOPAS puts in the local *y* = 0 plane; every
     further such atom then takes a dihedral of exactly 0 or 180.
  2. *Rotation:* a FIXED, geometry-derived rotation carries the local plane normal (local *y*)
     onto the Cartesian axis parallel to the mirror normal; the refinable rotation is then about
     that axis alone.
  3. *Translate:* fix the translate component along that normal.
- **2 atoms on one mirror:**
  1. *Frame:* they become z_matrix atoms 1–2, which sit on the local z axis (local x = y = 0) — a
     line, not a plane, so unlike the ≥3-atom case there's no symmetry-fixed target direction to
     rotate onto; the required in-plane direction of the 1–2 bond comes from the actual geometry.
  2. *Rotation:* a rotation about local z cannot move the pair, so that isn't the fix — instead use
     a FIXED, geometry-derived rotation to carry local z onto that real Cartesian direction (lying
     in the mirror plane), then restrict the refinable rotation to the Cartesian axis parallel to
     the mirror normal alone (the same single degree of freedom as the ≥3-atom case above).
  3. *Translate:* fix the translate component along that normal.
- **Atoms on a rotation axis (2 exact coordinates; a point fixing all three is (ZM14)'s nested case):**
  1. *Frame:* the first atom becomes the z_matrix root, so its position comes straight from
     `translate`; a second becomes z_matrix atom 2, which sits on the local z axis.
  2. *Rotation:* a FIXED, geometry-derived rotation carries local z onto the axis; restrict the
     refinable rotation to it.
  3. *Translate:* fix both translate components.
  4. *Third atom and beyond:* place an off-axis atom next — it and the two axial atoms define a
     plane containing the axis, so each further axial atom returns to the axis with a dihedral of
     exactly 0 or 180 and an angle that is the exact supplement of the reference angle (the two sum to 180°) —
     written as an equation, `= 180 - angB;`, so it stays exact while the reference angle refines.

- **Only PART of the fragment on the mirror** (the commonest real case): same body, in-mirror atoms at dihedral exactly 0/180, off-mirror
  atoms carrying real dihedrals. The mirror then regenerates the far side of the substituent.

Residue is then ~1e-16 fractional, and holds while the placement and internal geometry refine.

**(ZM11) Every translate component along a constrained direction must be fixed.** A coordinate free to
refine is not treated as a special position at all: on a plain site `x 0.75` returns the special
multiplicity while `x @ 0.75` — the same value — returns the general one. In a rigid body, one free
component makes every atom of that body general.

**(ZM12) Fix translate as a FRACTIONAL (`ta`/`tb`/`tc`), never Cartesian (`tx`/`ty`/`tz`).** A
Cartesian value is right only at the starting cell: once the cell refines, the special plane moves
and the fragment slides off it — `num_posns` silently wrong, Rwp diverging. An equation does not
rescue it: `tz = Get(c)/4;`, or the same through any `prm` tied to the cell, returns c × 0.9998,
the cell parameter's own derivative perturbation contaminating the equation where TOPAS's symmetry
check reads it. A fractional constant (1/4, 1/2) is cell-independent.

**(ZM13) Limits of the construction.**

- A dihedral holding an atom in the plane is not refinable: 180° → 178° takes it off, and the error
  compounds down the z_matrix chain. Bond lengths and angles refine normally, so a free torsion must
  involve only atoms off the special position.
- Rotational freedom is reduced by design (a mirror or a single axis leaves one rotation; an inversion centre
  alone leaves all three; symmetry elements along two or more directions leave none), so the alignment rotation is derived, not obtained from an
  unconstrained Kabsch fit.
- A collinear chain cannot be written directly: a 180° *angle* is degenerate and tc.exe rejects it
  (ZM5). Use the off-axis reference above instead. The supplement must be exact — an angle error δ
  (radians) puts the atom r·δ off the axis, r being the bond length: 1e-4° on a 1.5 Å bond is
  ~3e-6 Å, ~1e-7 fractional in a 20 Å cell, two orders of magnitude outside ZM7's window.
- It assumes the constrained direction can be reached by rotating the local frame onto a Cartesian
  axis — direct for an orthorhombic cell, or a monoclinic mirror ⊥ **b**.

**(ZM14) A subset of a special-position rigid body's atoms can sit on a second, more restrictive
symmetry element nested inside the one (ZM6)–(ZM13) already detect.** Check every special-position
atom's full stabilizer set, not just the operator shared by the whole group — a nested extra
constraint on a subset removes further DOF. An inner element lying in the mirror plane (mm2)
leaves no rotation and one in-plane translation component (not two); one parallel to the mirror
normal (a 2/m point) leaves the rotation about the normal but no translation — the atom is a
true special point with exact fractional coordinates.

## Safe refinement strategy for a whole-fragment rigid body

**(ZM15) Keep every `z_matrix` value fixed (`!name value`, no `@`) at the source geometry, and refine
only the `rotate`/`translate` components symmetry leaves free (ZM10–ZM14)** — the correct default
when the source CIF already gives the fragment's true internal geometry and only its placement in
the cell needs to come from the fit: treat the whole fragment as genuinely rigid, refining nothing
internal to it, unless torsional flexibility is specifically wanted.

**(ZM16) Use whatever thermal factors the source actually provides — anisotropic if the CIF gives
`u11..u23`, `beq`/`Biso` if that is what it has.** Do not collapse real anisotropy to an isotropic
equivalent: it can be large (u33 10x u11 is not rare). Site ADPs do not co-rotate with a refining
`rotate`; from a correct start the rotation stays small and this is negligible, and site-symmetry
constraints on the tensor are unaffected, since they act on the site, not the body. **With no CIF, or a CIF carrying no thermal data (e.g. during structure solution),
default to one Biso rather than inventing anisotropy** — that avoids over-fitting from the start.

**(ZM17) Deciding which z_matrix dihedrals are genuine, independently-determinable torsions** (as
opposed to fixed scaffolding) is a three-stage problem: (1) a geometric/chemical filter on the pivot
bond (must be a real, non-ring, non-terminal, formally-single bond, not a metal–ligand bond, and not
the redundant direction when the tree branches on both sides of the same bond — refining both
directions of one physical bond over-parameterises against the body's own `rotate`); (2) a
scattering-weighted sensitivity ranking (`S = sqrt(sum Z_i^2 d_i^2)` over the moving subtree,
d_i = perpendicular distance from the axis) that drops hydrogen-only movers and symmetric rotors
(CH3/CF3/NO2/aryl-flip type); (3) letting simulated annealing decide empirically which Stage-2
survivors actually cluster to a well-determined value across independent SA solutions.

## Syntax

**(ZM18) A z_matrix line sharing a pivot with an already-named torsion (`name value min .. max ..`) becomes
an equation offset from it (`= name + offset;`), not a second independent parameter** — otherwise the
fragment distorts while only a rotation was intended.
