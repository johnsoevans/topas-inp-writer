# Restraints and `append_bond_lengths` output

**`Distance_Restrain`/`Angle_Restrain` should be the first restraint macros reached for** whenever the geometry to enforce is a plain bond length or bond angle. Reserve `Flatten`/rigid-body `z_matrix`/other restraint machinery (see `13-rigid-bodies.md`) for genuinely different jobs — ring/fragment planarity, torsions, or a whole rigid fragment moved as a unit — that a simple distance/angle restraint can't express.

## Reading `append_bond_lengths` output (SHELX-style bond/angle matrix)

`append_bond_lengths` (a `Tstr_details` keyword, see `21-keyword-index.md` §"Tstr_details") writes a block like:

```
Zr1:0     O1:5       0   0  -1   2.00106
          O1:9      -1   0   0   2.00106  90.032
          O1:10      0  -1   0   2.00106  90.032   90.032
          O2:5       0   1  -1   2.04919  86.715   92.024   176.152
          O2:10      1  -1   0   2.04919  91.341   176.152  86.715   92.024
          O2:9      -1   0   1   2.04919  91.341   91.341   92.024   176.152  86.715
```

**Format, the same convention as SHELX's own bond-list tables:**

- Each block starts with a **pivot atom** line: `PIVOT_LABEL:opidx  NEIGHBOR_LABEL:opidx  offx offy offz  distance`. The pivot stays fixed for every row underneath it until the next pivot line starts a new block.
- Every following indented row is another neighbor of the *same* pivot: `NEIGHBOR_LABEL:opidx  offx offy offz  distance  [angle1  angle2  angle3  ...]`.
- `LABEL:opidx` identifies which of the space group's symmetry-equivalent copies of that site is meant; `opidx` is TOPAS's own internal operator index (1 = identity), not a hand-derived one — always get it from a real `append_bond_lengths` run, never guess it from a CIF's own (differently-ordered) `_symmetry_equiv_pos_as_xyz` list or any other independently-ordered operator table.
- `offx offy offz` are integer unit-cell offsets applied to that equivalent position (same convention `Distance_Restrain`/`Angle_Restrain` themselves expect — see below).
- The **first number after the offsets is always the pivot–neighbor distance** (Å).
- **Every number after the distance is an angle (degrees), neighbor–pivot–neighbor**, i.e. the angle subtended at the pivot between *this* row's neighbor and one of the neighbor rows listed *above* it in the same block. The angle columns grow by one with each new row, ordered left-to-right in the same top-to-bottom order the earlier neighbor rows appear:
  - Row *k* (0-indexed from the first neighbor after the pivot line) has exactly *k* angle values.
  - Its *j*-th angle column (0-indexed) is the angle neighbor_k–pivot–neighbor_j.
  - Concretely, from the block above (pivot `Zr1:0`, neighbors in listed order `O1:5, O1:9, O1:10, O2:5, O2:10, O2:9`): row `O1:9`'s one angle (`90.032`) is the O1:5–Zr1–O1:9 angle. Row `O1:10`'s two angles (`90.032, 90.032`) are O1:5–Zr1–O1:10 then O1:9–Zr1–O1:10. Row `O2:5`'s three angles (`86.715, 92.024, 176.152`) are O1:5–Zr1–O2:5, O1:9–Zr1–O2:5, O1:10–Zr1–O2:5, in that order.
- A second-shell pivot line further down the same block (e.g. `O1:0  W1:0  0 0 0  1.87830`) means TOPAS is now also reporting bonds/angles centered on `O1:0` as its own pivot — the same site can appear as both a neighbor under one pivot and a pivot in its own right later on; these are independent sub-blocks, not a continuation of the same angle table.

## From the report to actual restraints

1. Add `append_bond_lengths` inside the `str` block and run once (`iters 0` is enough) — read the generated block back from the resulting `.out` file. This is the **only** reliable source for each bond's real `LABEL:opidx offx offy offz` codes. Do not hand-derive `opidx` from a CIF's own symmetry-operator list — TOPAS's internal operator ordering (from its own `sgcom6`/`sg/*.sg` database) very often does not match a CIF's own operator order, and a wrong `opidx` silently produces a kernel-side `Uninitialized_Variable in equation` failure rather than a clear "bad operator" message.
2. Feed each wanted pivot–neighbor pair into `Distance_Restrain`/`Angle_Restrain` using **space-separated** tokens for the label/operator/offset group — `LABEL opidx offx offy offz`, **not** `LABEL:opidx` — e.g. `Distance_Restrain(Zr1 0   O1 5   0 0 -1, name, target, current, tol, weight)`. The colon in the report's own printed output is just its display formatting; the macro call itself wants six space-separated tokens (confirmed against a real working refinement file for a ZrW2O8 structure/instrument — the colon-joined form silently reaches the kernel as a malformed reference and fails the same uninitialized-variable way).
3. `Angle_Restrain`'s three-site form takes two full `LABEL opidx offx offy offz` neighbor groups plus the bare pivot label in the middle: `Angle_Restrain(NEIGHBOR_A opidx offx offy offz  PIVOT  NEIGHBOR_B opidx offx offy offz, target, current, tol, weight)`.

## Weighting distance vs. angle restraints

As a starting rule of thumb, weight distance restraints roughly **2000x looser** than angle restraints (i.e. the angle restraint's `wscale` weight is ~2000x the distance restraint's, for comparable restraint tightness). Angles in degrees and distances in Å sit on very different numeric scales, and without this rebalancing one restraint family tends to dominate the penalty function and starve the other of any real refining pressure. Treat 2000x as a reasonable starting ratio to tune per-structure, not a hard constant.

## Balancing restraints against the diffraction data

Use the global `penalties_weighting_K1` keyword to scale how strongly the summed penalty/restraint terms compete against the profile chi-square during minimization — this is the correct lever for "restraints vs. data" balance as a whole, distinct from the distance-vs-angle internal balance above. Tune it so restraints nudge the model toward chemical sense without visibly fighting a genuinely well-fit region of the pattern.
