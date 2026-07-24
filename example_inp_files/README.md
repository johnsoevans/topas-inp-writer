# Curated worked examples

Real, working `.inp` files bundled directly in this folder (no `TOPAS_DIR` needed, unlike the larger ~280-file corpus in `references/examples-index.md`). Prefer one of these as a starting point — copy its structure and adapt names/values.

Each file documents itself (`/* ... */` or `'`-comments); templates also carry a "WHAT TO CHANGE" checklist. Read that header first — this README just indexes it.

**Adding a new example**: add one row below (type + one distinctive line from its header) and, if it pairs with another file here, a Relationships line.

| File | Type | Distinctive |
|---|---|---|
| `bragg_brentano_fundamental_parameters.inp` | Rietveld (template) | Lab Bragg-Brentano fundamental parameters FP instrument skeleton (Ge(111) mono, Cu Kα1). Commented-out PO/Stephens/`CS_L`/`Strain_L` options. |
| `tof_template.inp` | Rietveld (template) | Only neutron TOF example — `TOF_XYE`/`TOF_LAM`/`TOF_x_axis_calibration`/`TOF_Exponential`/`TOF_PV`. Same checklist structure as the Bragg-Brentano template. |
| `y2o3_demo_stage3.inp` | Rietveld (real fit) | Fully-refined cubic Y2O3: March-Dollase preferred orientation, Commented out Spherical Harmonic preferred orientation, Stephens anisotropic broadening, artifact-peak exclusion, CIF export, full `C_matrix_normalized`. |
| `rutile_sim_01.inp` | Simulation (`iters 0`) | Shortest file — forward pattern simulation from a CIF-derived structure. |
| `tio2_peak_fit_01.inp` | Deconvolution/peak-fitting | Real lab data, one shared peak shape, no structural model. GUI peak-search → paste-into-file workflow. |
| `tio2_index.inp` | Indexing | Peak list from `tio2_peak_fit_01.inp`'s output; all six Bravais-lattice search macros active. |
| `d8_01612_vt_reel_02.inp` | Rietveld (multi-phase, VT, sequential) | Most complex file here: ~68-pattern VT sequence, 4 real phases of a topotactic transition, spherical-harmonics broadening, `MVW` quant, scripted Reel/`.xyy`/Python output. |
| `parametric_06.inp` | Rietveld (parametric, multi-pattern) | Cell parameters/angles as `fn`-based physical functions of temperature; list-driven multi-pattern factory; conditional compilation. |
| `glycine_cuka1_01_fit_01.inp` | Rigid bodies (Rietveld) | Only rigid-body/`z_matrix` example. 5 alternative rigid-body defs via `#define rigid_*` (0/1 refined torsion; CIF→Mercury→Babel route); both `z_matrix` syntax forms; `#define match_sites` fits a rigid body to target coords via an inline `Match_Site` macro. |
| `d8_00796_riet_01.inp` | Rietveld (restraint-based organic) | Only restraint-based (non-rigid-body) organic refinement: `Distance_Restrain`/`Angle_Restrain`/`Flatten` keep two benzene rings planar/regular; every coordinate independently `@`-refined (`Pna21`). Compare with `glycine_cuka1_01_fit_01.inp` for restraints-vs-rigid-bodies. |
| `tio2_lab_bragg_brentano_rietveld.inp` | Rietveld (real fit) | Default menu-driven TiO2 (rutile) lab fit (Durham `vscode_riet_pawley` tutorial). `CuKa2_analyt` + graphite-mono `LP_Factor`, `Simple_Axial_Model`, `Specimen_Displacement`, `TCHZ_Peak_Type` in a `for strs {}` loop, `do_errors`, full `C_matrix_normalized`. Deliberately low-quality data (Rwp ~13.7) — a plain "default fit" reference. |
| `tio2_lab_bragg_brentano_pawley.inp` | Pawley | Matched Pawley counterpart to the file above — same data/instrument/peak-shape macros, `hkl_Is` instead of `str`/sites. |

**Relationships:**
- `tio2_peak_fit_01.inp` → `tio2_index.inp`: peak-fit-then-index pipeline, same TiO2 pattern.
- `y2o3_demo_stage3.inp` → `bragg_brentano_template.inp`: template is the stripped-down version of this fit's instrument block.
- `tio2_lab_bragg_brentano_rietveld.inp` ↔ `tio2_lab_bragg_brentano_pawley.inp`: matched pair, same data/instrument — use for Rietveld-vs-Pawley model-quality comparison.
