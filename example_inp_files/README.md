# Curated worked examples

Real, working `.inp` files bundled directly in this folder (no `TOPAS_DIR` needed to read them, unlike the skill's larger ~280-file corpus indexed in `references/examples-index.md`). Prefer one of these as a starting point before writing from scratch — copy its structure and adapt names/values.

**Every file documents itself**: each has its own header comment (`/* ... */` or `'`-comments) explaining what it demonstrates, and templates additionally carry a "WHAT TO CHANGE" checklist. Read that header first — this README is a lookup index pointing at it, not a duplicate of it.

**Adding a new example**: add one row to the table below (type + one line on what's distinctive about it, taken from the file's own header comment) and, if it forms a pair/derives from another file here, a line under "Relationships." Nothing else in this file needs touching.

| File | Type | Distinctive |
|---|---|---|
| `bragg_brentano_template.inp` | Rietveld (template) | Clean lab Bragg-Brentano fundamental-parameters instrument skeleton (Ge(111) monochromator, Cu Kα1). Commented-out optional extras: preferred orientation, Stephens broadening, `CS_L`/`Strain_L`. |
| `tof_template.inp` | Rietveld (template) | The only neutron time-of-flight example — `TOF_XYE`/`TOF_LAM`/`TOF_x_axis_calibration`/`TOF_Exponential`/`TOF_PV` macro family. Same template/checklist structure as `bragg_brentano_template.inp`, for TOF geometry instead. |
| `y2o3_demo_stage3.inp` | Rietveld (real fit) | Real fully-refined single-phase cubic Y2O3 fit: preferred orientation (March-Dollase), Stephens anisotropic broadening, artifact-peak exclusion, CIF export, full `C_matrix_normalized` correlation matrix. |
| `rutile_sim_01.inp` | Simulation (`iters 0`, no refinement) | Shortest file — forward pattern simulation from a CIF-derived structure (TOPAS-Editor's "Simulate pattern from CIF"). |
| `tio2_peak_fit_01.inp` | Deconvolution / peak-fitting | Real lab data, one shared peak shape, no structural model — extracts peak positions/intensities. Documents the GUI peak-search → paste-into-file workflow. |
| `tio2_index.inp` | Indexing | Peak list taken directly from `tio2_peak_fit_01.inp`'s output. All six Bravais-lattice search macros left active. |
| `d8_01612_vt_reel_02.inp` | Rietveld (multi-phase, variable-temperature, sequential) | Most complex file here: ~68-pattern VT sequence through 4 real phases of a topotactic transition, spherical-harmonics anisotropic broadening, `MVW` quant, plus a custom scripted output pipeline (Reel/`.xyy`/external Python). |
| `parametric_06.inp` | Rietveld (parametric, multi-pattern) | Cell parameters/angles as explicit physical functions of temperature via `fn` macros, list-driven multi-pattern factory, coordinate-restraint macros, conditional compilation. |

**Relationships:**
- `tio2_peak_fit_01.inp` → `tio2_index.inp`: a worked peak-fit-then-index pipeline on the same TiO2 lab pattern.
- `y2o3_demo_stage3.inp` → `bragg_brentano_template.inp`: the template is the stripped-down, generic version of this real fit's instrument block.
