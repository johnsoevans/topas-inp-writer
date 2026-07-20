# Lab XRD Rietveld/Pawley workflow conventions

Practical conventions for running Rietveld/Pawley refinements on **laboratory Cu-source X-ray data**, learned from real refinement sessions rather than the manual itself. These are defaults to apply automatically, not options to re-weigh each time — deviate only if the user specifies different instrumentation or asks for something else.

## Lab Cu data: TCHZ + CuKa2_analyt is the standing default

For a standard lab Bragg-Brentano diffractometer running **Cu Kα radiation with no monochromator** (Kα1/Kα2 doublet unresolved by the source itself), always pair:

- **Peak shape**: `TCHZ_Peak_Type` (pku, pkv, pkw, pkz, pkx, pky)
- **Wavelength/emission macro**: `CuKa2_analyt(yminymax)`, not plain `CuKa2` or `CuKa1`

`CuKa2_analyt` loads the analytical Kα1/Kα2 emission profile that TCHZ needs to reproduce the doublet peak shape correctly — using plain `CuKa2` (a simpler two-line approximation) with TCHZ gives a subtly wrong peak shape. Treat this pairing as the default for any lab Cu dataset unless the user says the source has a monochromator (in which case a single-wavelength macro like `CuKa1` is appropriate instead) or names different instrumentation entirely (see headings below) or uses a fundamental parameters peak shape approach.

This applies identically whether the phase is `str` (Rietveld) or `hkl_Is` (Pawley/Le Bail) — see the matched pair `tio2_lab_bragg_brentano_rietveld.inp` / `tio2_lab_bragg_brentano_pawley.inp` in `example_inp_files/`.

## Always seed r_wp/r_exp/r_p/gof at the top of a new INP

When writing a **brand-new** `.inp` from scratch (not editing an existing one), add a placeholder statistics line as the very first line of content, matching what TOPAS itself writes once a real `.out` exists:

```
r_wp  0 r_exp  0 r_p  0 weighted_Durbin_Watson  0 gof  0 r_wp_dash 0 r_p_dash 0
```

TOPAS overwrites these placeholder numbers with real values in the `.out` it produces after refinement — but only if the line already exists in the file being refined. Without it, the statistics are only visible in the console iteration log and get lost once that scrolls away; a reader opening the `.inp`/`.out` later has to hunt for Rwp instead of seeing it as the first line. Real worked examples in this skill's own `example_inp_files/` (e.g. `tio2_lab_bragg_brentano_rietveld.inp` line 8) follow this convention — copy it forward into every new file, and preserve it (don't strip it) when copying a `.out` back over an `.inp` per the user's own literal-copy workflow.

## Generating a Pawley/Le Bail hkl list from a converged structural model

When a Rietveld (`str`) model has already converged and you want a Pawley (`hkl_Is`) fit for comparison (e.g. "how much of the residual is structural vs. peak-shape/background"), don't hand-derive or guess the reflection list — generate it directly from the converged model:

1. Copy the converged `str` refinement to a scratch `.inp`, set `iters 0` (no refinement, just a single calculation pass), and strip the `` `_error `` suffixes to plain numbers (or leave them — TOPAS ignores the error tag on a fixed value).
2. Inside the `str`'s `for strs { }` block (or directly after the site list), add:
   ```
   Create_hklm_d_Th2_Ip_file(hkl_list.txt)
   ```
   This writes every generated reflection as `H K L M D_spacing 2Th I` (`I` = `I_no_scale_pks`, the structure-factor-derived intensity with the phase's own scale un-applied).
3. Run via `tc.exe`; `hkl_list.txt` now has one line per reflection.
4. Reformat each line into a Pawley `load hkl_m_d_th2 I { }` entry by prefixing the intensity column with `@` (making it independently refinable):
   ```
   H K L M D_spacing 2Th @ I
   ```
5. Build the Pawley `.inp`: same `xdd`/background/peak-shape/wavelength block as the Rietveld file, but replace the `str` block with:
   ```
   hkl_Is
       phase_name ...
       TCHZ_Peak_Type(...)   ' peak-shape macro goes directly inside hkl_Is, NOT inside a "for strs {}" wrapper — that wrapper is for str-phase loops only and errors on hkl_Is
       a ... b ... c ... al ... be ... ga ...
       space_group "..."
       load hkl_m_d_th2 I
       {
           ' the @-prefixed reflection lines from step 4
       }
   ```
6. Refine. Compare the converged Pawley Rwp against the Rietveld Rwp — a small gap (order 0.1 percentage points) indicates the structural model already explains essentially all of the intensity distribution; a large gap points to a structural problem (wrong space group, missing atoms, wrong site occupancy) rather than peak-shape/background inadequacy.

This reuses the cell refined by the Rietveld fit (fix or lightly constrain it in the Pawley run, since the point is isolating intensity-model quality, not re-deriving the cell) and the same TCHZ + `CuKa2_analyt` instrument block, so the two Rwp values are a fair apples-to-apples comparison.

## Final report format (applies to any refinement, any instrumentation)

When asked to write a final report/summary of a Rietveld or Pawley refinement (as opposed to just running it), the report must:

1. **Start with the date the analysis was performed.**
2. **Include a summary of the parameters refined, split into structural vs. non-structural counts.** Structural = anything describing the crystal structure itself: lattice parameters (a, b, c, al, be, ga), atomic coordinates (x, y, z), occupancies, ADPs/beq/u11..u23. Non-structural = everything else: scale, background terms, peak-shape parameters (TCHZ's pku/pkv/pkw/pkx/pky/pkz etc.), zero-error/specimen-displacement, absorption, LP factor. State both counts explicitly (e.g. "27 parameters refined: 12 structural, 15 non-structural") rather than just a total — `scripts/find_refined_params.py` lists every independent refined parameter and can be used to build this count and split reliably rather than counting by eye.
3. **If a structure was refined, include a table of fractional coordinates with errors in parentheses.** One row per site: label, x, y, z (each as `value(error)`, e.g. `0.07393(128)`, using the digits already present in the `` `_error `` suffix — don't re-derive or round differently). Include occupancy and beq/ADP columns too if refined.
4. **End with this exact line, verbatim, as its own final line:**
   ```
   This refinement was performed with TOPilot, it is the user's responsibility to judge its scientific content.
   ```

These four requirements are independent of the instrument-specific sections above (Cu lab XRD, synchrotron, neutron) — apply them to every final report regardless of data source.

## Synchrotron X-ray data

*(Not yet populated — add conventions here when a synchrotron-source refinement session establishes them. Likely topics: monochromatic single-wavelength macros in place of `CuKa2_analyt`, `fundamental_parameters`/full FP peak shape vs. TCHZ, axial divergence from a bent/curved analyzer vs. `Simple_Axial_Model`.)*

## Neutron data (CW or TOF)

*(Not yet populated — add conventions here when a neutron refinement session establishes them. Likely topics: CW neutron peak-shape macro choices, TOF-specific peak-shape family (see `references/04-peak-generation-and-peak-type.md`), absence of a Kα1/Kα2 doublet so `CuKa2_analyt`-equivalent pairing does not apply.)*
