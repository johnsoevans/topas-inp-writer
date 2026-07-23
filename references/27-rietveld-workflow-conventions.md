# Rietveld/Pawley workflow conventions

Practical strategy conventions for running Rietveld/Pawley refinements, learned from real refinement sessions with John rather than the manual itself. These are defaults to apply automatically, not options to re-weigh each time — deviate only if the user specifies otherwise.  Note that others may not agree with these conventions!

Every concrete rule below carries a stable tag like `(R7)` so it can be cited, changed, or superseded precisely in a future session — e.g. "change R7" or "add a rule after R14". Numbers are grouped under topic headings purely for readability — the heading doesn't gate or reset the numbering. **Renumbered to be sequential (R1-R43, no gaps) on 2026-07-23** — before that date, R24-R43 had drifted out of order as rules were added piecemeal; any citation to an R-number from before that date may no longer point at the same rule. Going forward, new rules should still just continue from the next free number (currently R44) rather than being inserted mid-sequence, to avoid needing another renumbering pass.

## Wavelength and instrument setup

**(R1) Never guess the wavelength.** If the radiation/wavelength isn't clear from what the user has said, ask before proceeding — don't infer it from the data or assume a common default.

**(R2) `LP_Factor()` is mandatory for every `xdd` fitted, with no exceptions** — even with no monochromator, include it with the angle fixed at 0 (`LP_Factor(!th2_monochromator, 0)`). **Never guess the monochromator angle.** If not stated explicitly, ask the user, optionally offering common real values as a shortlist. Intensity Corrections, for Cu radiation: Ge 27.26°, Graphite 26.4°, Quartz 26.6°. For Mo radiation: Ge 12.46°. Still confirm which applies (or that there is none) rather than assuming.

**(R3) Peak-shape family determines the wavelength/emission macro — this pairing is conditional, not a blanket default:**
- TCHZ (refined, or fixed as an instrument resolution function) with unmonochromated lab Cu Kα1/Kα2 data → `CuKa2_analyt(yminymax)`. This loads the analytical Kα1/Kα2 emission profile TCHZ needs to reproduce the doublet correctly; plain `CuKa2` (a simpler two-line approximation) gives a subtly wrong peak shape when paired with TCHZ.
- Fundamental parameters, or plain empirical size/microstrain broadening with no TCHZ at all → use `CuKa5()` or `CuKa2()` instead.
- A monochromator is present → a single-wavelength macro like `CuKa1` is appropriate.
- This applies identically whether the phase is `str` (Rietveld) or `hkl_Is` (Pawley/Le Bail) — see the matched pair `tio2_lab_bragg_brentano_rietveld.inp` / `tio2_lab_bragg_brentano_pawley.inp` in `example_inp_files/`.

**(R4) Seed a placeholder statistics line as the very first line of content** in any brand-new `.inp` written from scratch:
```
r_wp  0 r_exp  0 r_p  0 weighted_Durbin_Watson  0 gof  0 r_wp_dash 0 r_p_dash 0
```
TOPAS overwrites these with real values in the `.out` it produces — but only if the line already exists in the file being refined. Without it, statistics are only visible in the console log and get lost once that scrolls away. Preserve this line (don't strip it) every time a `.out` is copied back over the `.inp`.

## Peak-shape strategy — the four families

**(R5) `Simple_Axial_Model()` for axial-divergence asymmetry is the standing default in every peak-shape family below EXCEPT fundamental parameters.** Fundamental parameters derives axial divergence from the actual instrument geometry itself, so `Simple_Axial_Model()` is not layered on top of it. For every other family (TCHZ refined, TCHZ fixed-as-instrument, or plain empirical size/strain with no TCHZ), always include `Simple_Axial_Model()` as part of the standard block — not an optional extra to remember only sometimes. (For synchrotron data, confirm case-by-case whether it's still wanted — axial divergence is often much less significant there; not yet a settled rule.)

**(R6) Family (i): TCHZ empirical.** Always paired with `Simple_Axial_Model()` (R5) and `CuKa2_analyt` for unmonochromated lab Cu data (R3). TCHZ parameters commonly hit their limits — not necessarily a problem in itself (see R26-R28 on saturation and R29, the mandatory false-minimum check). If refinement struggles, consider resetting values and re-refining, or running cycles with `continue_after_convergence` from different sensible starting points.

**(R7) Family (ii): Gaussian + Lorentzian size/strain broadening, no TCHZ.** Also paired with `Simple_Axial_Model()` (R5). These terms correlate with TCHZ peak-shape parameters, so TCHZ must be removed or commented out entirely when using this approach — never combine both families in the same refinement.

**(R8) Family (iii): TCHZ fixed as the instrument resolution function, with per-`str` size/strain on top.** TCHZ here describes instrumental resolution only, fixed (`!`) at known instrument values that differ per instrument; each `str` then gets its own size/microstrain broadening. `Simple_Axial_Model()` (R5) still applies. Example — Durham Bruker D8 Bragg-Brentano, Cu Kα1/Kα2, no monochromator, LynxEye PSD (empirical, no physical meaning, instrument-specific — do not treat as universal):
```
TCHZ_Peak_Type(!pku, 0.00027, !pkv, -0.00053, !pkw, -6.17e-05, !pkz, 0.0000, !pky, 0.0269, !pkx, 0.0166)
```

**(R9) Family (iv): Fundamental parameters** — see `example_inp_files` for a template. Exception to R5: no `Simple_Axial_Model()` here, FP's own geometry-based model replaces it.

**(R10) Synchrotron data** typically needs a sharper empirical peak shape — a Voigt function is a common choice; see `example_inp_files`.

## 2-theta range strategy

**(R11) Start fitting to roughly 60-70° 2θ with Cu radiation and an equivalent range with other radiation** (a range with ~20-40 strong peaks), before extending to the full range. This prevents cell parameters refining to a false minimum among densely-spaced high-angle peaks — especially important for Pawley fitting and large-cell structures. **Always extend to the full range by the end of the refinement.** Follow a specific per-task instruction's own numbers if given; this is the fallback default otherwise.

## ADP (temperature factor) strategy

**(R12) Start with one shared ADP for all sites.** Once cell, peak shape, and coordinates have converged and the fit is good, move to one ADP per atom type. For high-quality data, one ADP per site may be appropriate. Anisotropic ADPs are usually only feasible with very high-quality data (synchrotron or neutron).

**(R13) A negative overall ADP early in a refinement** (e.g. right after refining heavy-atom coordinates) often signals absorption, surface roughness, or uncorrected variable slits on lab data. A slowly-refining/drifting background is another sign of the same underlying issue.  Either try a Variable_Divergence_Intensity correction or prompt the user about the experimental conditions.

**(R14) If temperature factors stay negative, warn the user but don't clamp at zero** — the negative value itself is diagnostic information worth surfacing, not an error to hide. A sensible bound is **-5 to +20 Å²** unless told otherwise.

## Overall refinement sequencing

**(R15) If the starting model is good, refining everything from the start is often safe.** For a more complex refinement, or whenever in doubt, use this staged order instead:

1. **(R16)** Refine cell parameters, scale factor, and a simple background first, to get good tick-mark/observed-peak overlap — some overlap is *required* for least-squares to converge at all.
2. **(R17)** If there's no overlap, scale factor may refine toward zero — temporarily set it manually so calculated strong peaks are similar in intensity to observed strong peaks.
3. **(R18)** Temporarily broadening peaks artificially (e.g. fake extra size broadening) early on can help overlap/convergence in difficult cases.
4. **(R19)** Background is normally a polynomial. If it rises at low 2θ, try `One_on_X`. A broad hump is often better modeled with a Gaussian/Lorentzian peak in the background than more polynomial terms — set its width so it doesn't fit real diffraction peaks (minimum ~1-2°). These checks matter when the peak-to-background ratio is low; skip/defer them when background is already low.
5. **(R20)** Always test a zero-point *or* sample-displacement correction next — never both together (they correlate/are redundant). Keep within sensible bounds. 
6. **(R21)** Sanity check: cell lengths changing by more than ~1% from the starting model, or angles by more than ~1-2°, is a warning sign something is wrong.
7. **(R22)** If the fit is reasonable, refine peak shape next. If peaks go too broad, reset to instrument-appropriate sharp values and fix temporarily.
8. Refine coordinates of strongly-scattering atoms next, as allowed by symmetry (atoms moving >0.5 Å in any direction would be unusual — consider min/max bounds relative to the original CIF coordinates if there are problems).
9. **For a metal oxide with X-ray data, oxygen coordinates should normally only be refined at the end of a refinement, after the range has been extended to the full range** — i.e. after both "refine coordinates last" and "extend to full range" have already happened, not before either.
10. For a complex organic molecule, refinement is normally only tractable with restrained bond distances/angles, or a rigid-body/z-matrix approach (see `test_examples`).
11. If a simplified peak shape was used early for stability (e.g. only one of Lorentzian-size/Lorentzian-strain/Gaussian-size/Gaussian-strain refining), revisit at the end and test whether freeing the other terms improves the fit — see also R29, the mandatory false-minimum check.
12. At the end of a Rietveld, it's useful to compare against a Pawley fit (see the recipe below); or use Pawley at the *start* to confirm cell/peak-shape before attempting Rietveld — but if the starting model has poor obs/calc overlap, Pawley is *less* likely to converge than Rietveld, since Pawley has no structural model to keep it anchored.  Ask the user about this just before the final summary.

**(R23) Output Yobs/Ycalc/Ydiff AND include `Create_hklm_d_Th2_Ip_file(...)` (or the phase-appropriate tick-generating line) from the very start of the refinement** Both must be in the `.inp` from stage 0 onward so every stage plot (not just the final one) has ticks with real hkl hover labels available, per R25. Treat "set up Yobs/Ycalc/ticks output" as one single setup step done once at the very beginning.

**(R24) When plotting a fit with `scripts/plot_xy.py`, pass the current Rwp/GoF (and Rp if relevant) via `--stats "Rwp=13.68%,GoF=1.64"`** so the refinement statistics for that specific plot appear directly in its header. Pull the values straight from the `.out`'s own `r_wp`/`gof`/`r_p` line for the plot being generated at that moment, not from a stale run.

**(R25) Default to including reflection tick marks (`--ticks`) on every Rietveld/Pawley fit plot, not just on request.** Add `Create_hklm_d_Th2_Ip_file(ticks_file.txt)` inside the `str`'s own block (or, for `hkl_Is`, directly inside the phase) so real h k l indices are available for the hover tooltip (preferred over `Create_2Th_Ip_file`, which is position-only, no hkl label) — for a multi-phase file, one tick-file/`--ticks` group per phase, so each phase's own reflection markers can be shown/hidden independently. This has to be generated by an actual `tc.exe` run (`iters 0` is enough if only the tick file is needed, no re-refinement) since it depends on the current structural model's calculated reflection positions/intensities, not just the observed data — factor that generation step into the plotting workflow rather than treating ticks as an afterthought added only if asked for.


## Peak-shape term saturation — what to do when a term stops contributing

**(R26) A CS_L/CS_G size term drifting very high** (not contributing real broadening information — see the ~500 FWHM-sensitivity threshold in `references/04-peak-generation-and-peak-type.md`, e.g. climbing past 1000+ while correlating with a strain term instead) **should be fixed at 9999**, not zero and not removed from the file — switch it to fixed (`!`) at that value so it stays visible/re-testable later rather than silently deleted. It is not normally necessary, but you could apply to any other peak-shape term that saturates high or low (e.g. a TCHZ term) — fix it at its own saturated value, in place.

**(R27) A Strain_L/Strain_G (or TCHZ) term pinned at its lower limit** (e.g. `LIMIT_MIN 0.0001`) should be fixed at that same limiting value the same way — left in the file, just fixed rather than refined.

**(R28) When fixing one saturated term, do not reset or re-seed the OTHER still-useful term's current value.** E.g. if a size term is fixed at 9999 because it stopped contributing, leave the paired strain term refining from its own already-converged value — don't reinitialize it or restart the pair from scratch. Only the saturated term itself gets frozen.

## Mandatory false-minimum check before finalizing any correlated peak shape

**(R29) Before treating a TCHZ (or other multi-term, mutually-correlated peak-shape family, e.g. combined Gaussian+Lorentzian size/strain) refinement as final, always reset its peak-shape terms to a flat starting value (e.g. all TCHZ terms at 0.0001) and re-refine, then compare the resulting Rwp against the staged result.** This is an automatic, unconditional, always-on final step — run it before every final write-up regardless of whether the staged convergence looked clean, with no limit warnings, no exception for "it looked fine." A clean convergence log is not proof of a genuine minimum: TCHZ and similar correlated families can walk into a false minimum during staged refinement with no visible symptom during the run itself. If the reset run converges lower, adopt it as the final answer instead and say so in the report; if it converges to the same or worse Rwp, the staged result stands — but report that the check was performed either way, don't skip reporting it just because nothing changed.


## Advanced topics

**(R30) Most refinements use hkl-independent peak shapes.** Where genuine hkl-dependence exists, test different models (see `references/04-peak-generation-and-peak-type.md` and `example_inp_files`). Diagnostic signature in the difference curve: some peaks go up-down-up ("M" shape — calculated too sharp), others go down-up-down ("W" shape — calculated too broad); a mixed M/W pattern across different peaks signals genuine hkl-dependent broadening, not a uniform peak-shape problem.  You can do your own test but **always** also try the Stephens model or a spherical harmonic strain correction.

**For the Stephens model use the crystal-system-specific `Stephens_cubic`/`Stephens_tetragonal_*`/`Stephens_hexagonal`/etc. macro** (defined directly in `topas.inc`) — it sets `gauss_fwhm`/`lor_fwhm` via `Stephens_lor_gauss`.  It is a microstrain model so will correlate with TCHZ parameters or other microstrain terms. Refine all the terms allowed by symmetry.  If a TCHZ peakshape model is used include the Stephens macro in the str section and add a note to the user about potential correlation. Don't remove the existing TCHZ without prompting.   If a macrostrain model is being used comment out the existing strain description and inform the user.  Check in example_inp_files for example usage os Stephens macro.

**(R31) Preferred orientation: March-Dollase is the safest default correction.** Guess the direction from which reflections show the largest deviation in the difference curve. Even if your tests are negative **always** try a spherical harmonic correction with order 4, 6 or 8, accepting the lowest order that works. The macro is `PO_Spherical_Harmonics(sh, order)`.  After fitting with spherical harmonics check the harmonic shape itself and see if it implies a simple preferred-orientation direction(s).  If so test the corresponding March-Dollase model.

**(R32) Difference-curve spikes only 1-2 data points wide** (narrower than any real reflection profile) are likely electronic spikes or other artifacts — best excluded from the model entirely, not fitted.

## Workflow mechanics

**(R33) Open the `.inp` file in VS Code as soon as it's created**, and keep it open, so the user can follow along live.

**(R34) Update the input file by literally copying the `.out` file back over the `.inp`** after every refinement run — never hand-edit the `.inp` with refined values yourself.

**(R35) No need to strip a stale `C_matrix_normalized` block from the `.inp` before the next refinement cycle** — TOPAS handles this fine as-is.

**(R36) Every plot/3D-view/correlation-heatmap HTML file prepared during a session must actually be opened for the user, not just written to disk.** Immediately after writing each plot/view file, publish/open it in the same step — don't batch multiple prepared files and open them only at the end. This applies to every stage plot during a refinement, not just the final fit/3D-view/correlation-matrix.

**(R37) Mandatory backup, regardless of R36: at the end of every refinement session, include a list of every plot/3D-view/correlation-heatmap generated during that session, each as a clickable link, in the final message or summary.** This does not replace opening each one live as it's produced — it's a safety net for whenever that slips, mechanical enough to get right by doing one pass over everything written during the session, rather than depending on having caught every individual step along the way. List them in the order generated, with a short label (e.g. "Stage 1 fit (10-65°)", "Final fit (10-150°)", "3D structure", "Correlation matrix") rather than just bare filenames/URLs.

## Generating a Pawley/Le Bail hkl list from a converged structural model

**(R38)** When a Rietveld (`str`) model has already converged and a Pawley (`hkl_Is`) fit is wanted for comparison (e.g. "how much of the residual is structural vs. peak-shape/background"), don't hand-derive or guess the reflection list — generate it directly from the converged model:

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

This reuses the cell refined by the Rietveld fit (fix or lightly constrain it in the Pawley run, since the point is isolating intensity-model quality, not re-deriving the cell) and the same instrument block, so the two Rwp values are a fair apples-to-apples comparison.

## Final report format (applies to any refinement, any instrumentation)

When asked to write a final report/summary of a Rietveld or Pawley refinement (as opposed to just running it), the report must:

**(R39)** Start with the date the analysis was performed.

**(R40)** Include a summary of the parameters refined, split into structural vs. non-structural counts. Structural = anything describing the crystal structure itself: lattice parameters (a, b, c, al, be, ga), atomic coordinates (x, y, z), occupancies, ADPs/beq/u11..u23. Non-structural = everything else: scale, background terms, peak-shape parameters (TCHZ's pku/pkv/pkw/pkx/pky/pkz etc., or CS_L/CS_G/Strain_L/Strain_G), zero-error/specimen-displacement/axial asymmetry, absorption, LP factor. State both counts explicitly (e.g. "27 parameters refined: 12 structural, 15 non-structural") rather than just a total — `scripts/find_refined_params.py` lists every independent refined parameter and can be used to build this count and split reliably rather than counting by eye.

**(R41)** If a structure was refined, include a table of fractional coordinates with errors in parentheses. One row per site: label, x, y, z (each as `value(error)`, e.g. `0.07393(128)`, using the digits already present in the `` `_error `` suffix — don't re-derive or round differently). Include occupancy and beq/ADP columns too if refined.

**(R42)** If the mandatory false-minimum check (R29) applies to this refinement, report which result (staged vs. reset) was adopted and why.

**(R43)** End with this exact line, verbatim, as its own final line:
```
This refinement was performed with TOPilot, it is the user's responsibility to judge its scientific content.
```

These requirements are independent of the instrument-specific sections above (Cu lab XRD, synchrotron, neutron) — apply them to every final report regardless of data source.

## Synchrotron X-ray data

*(Not yet populated beyond R10/R5's synchrotron notes — add conventions here when a synchrotron-source refinement session establishes them. Likely topics: monochromatic single-wavelength macros in place of `CuKa2_analyt`, `fundamental_parameters`/full FP peak shape vs. TCHZ, axial divergence from a bent/curved analyzer vs. `Simple_Axial_Model`.)*

## Neutron data (CW or TOF)

*(Not yet populated — add conventions here when a neutron refinement session establishes them. Likely topics: CW neutron peak-shape macro choices, TOF-specific peak-shape family (see `references/04-peak-generation-and-peak-type.md`), absence of a Kα1/Kα2 doublet so the R3 pairing does not apply.)*
