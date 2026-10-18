# PDF fitting workflow conventions

**Draft rules:** these have not been developed in depth yet. Treat them as sensible starting suggestions rather than a tested workflow.

How-to suggestions for fitting a structural model to an existing PDF (G(r)/D(r)) in TOPAS. For keyword and macro syntax use `references/09-pdf-refinement.md` (the manual chapter); this file is the how-to. Note that others may not agree with these conventions.

Every rule carries a tag like `(PDF7)` so it can be cited or changed precisely ("change PDF7"). Numbers are sequential: a new rule takes the next free number.

**The next free PDF number is PDF22.** Update this line whenever a rule is added.

**PDF numbers are confined to this file.** Nothing else in the skill cites a rule by number, because those citations go stale silently if this file is renumbered. Elsewhere, refer to a rule by topic (e.g. "the Qmax rule in `references/32-pdf-workflow-conventions.md`").

The worked example is `example_inp_files/pdf_fitting_sno2_synchrotron.inp`. Ignore its header comment about needing Phil Chater's `PDF.inc`: in TOPAS v9 the macros it uses are in the standard `pdf.inc`, which `topas.inc` loads automatically.

**The workflow mechanics and the final-report format in `references/27-rietveld-workflow-conventions.md` also apply to PDF fits** (opening the `.inp`, copying the `.out` back, opening and listing plots, `launch_file.txt`, the report). For the report's structural/non-structural split, structural means cell parameters, coordinates, occupancies and the displacement-model parameters (beq, `beqlo`/`beqhi`/`radius`, uij); non-structural means scale, `pdf_zero`, Qdamp, Qmax/Lorch convolution parameters, `delt1`/`delt2`/`Qb` and particle size. The Rietveld false-minimum report item doesn't apply. Plot PDF fits with `--xlabel "r (Å)"` (`scripts/plot_xy.py` and `plot_xy_matplotlib.py`).

## PDF Fitting

**(PDF1) The `xdd` needs the `pdf_data` keyword** (plus `neutron_data` for neutron data), as in the SnO2 example.

**(PDF2) Qdamp and Qmax.** If they are not supplied, check the data file header first (PDFgetX3 writes Qmax there), then ask the user if one is available. Warn that Qdamp is instrument related and should normally be determined from a crystalline standard measured under the same conditions, then fixed at that value. Qdamp is introduced with `dQ_damping(!dQ, 0.001)` and Qmax with `convolute_Qmax_Sinc(!qmax, 25)   ' fixed at the Fourier Transform's actual Qmax (Å⁻¹)`. The 0.001 and 25 are placeholders, never left in a file unexplained. Use `convolute_Qmax_Sinc` even though the SnO2 example omits it and has `convolute_SoperLorch`.

**(PDF3) No Qmax found.** There won't always be a user to ask. If no Qmax value can be found, put the line in with an arbitrary Qmax of 100 but commented out, with a comment saying the real Qmax is unknown:
```
'  convolute_Qmax_Sinc(!qmax, 100) ' Qmax unknown - set to the G(r) transform's Qmax and uncomment
```

**(PDF4) No standard and Qdamp unknown:** fix it either at a low value or at an instrument-specific value if a reliable one is available, with a comment in the INP file saying which.

**(PDF5) Qbroad.** Some ADP models include an instrumental Qbroad term. In these cases, Qbroad should normally be determined from a standard and not refined. If unknown, fix it at its lowest allowed value (1e-9 in the snippets below).

**(PDF6) Qmax is never refined.** It is the Qmax used in the G(r) transformation, not the maximum Q of the original data collection.

**(PDF7) PDFgui Qdamp conversion.** TOPAS's `dQ_damping` takes a FWHM, PDFgui's Qdamp a Gaussian width: a PDFgui Qdamp of 0.001 is `dQ_damping(!dQ, 0.00235482)` in TOPAS (multiply by 2.35482).

**(PDF8) If Qdamp is refined** it correlates with e.g. the scale factor and size-related parameters.  Warn the user.

**(PDF9) If Qbroad is refined** it correlates with atomic displacement and related parameters. Warn the user.

**(PDF10) Unneeded Qdamp/Qbroad:** if their contributions are not needed to fit the data, fix them at their lowest allowed value (0.001 for `dQ_damping`). Do not delete the line from the INP file.  Alternatively comment the line out.

**(PDF11) `pdf_zero` is normally 0 and fixed.** Use a non-zero value only for a known data-processing artefact, with a comment in the INP file.  Warn if the value is more than a few data steps (the r spacing of the data) from zero.

**(PDF12) Low-r cutoff:** `start_X 0.5` (Å) by default, with zero weight below just under the shortest real bond, as in the SnO2 example: `weighting = If(X < 1.5, 0, 1);` (adjust 1.5 to the structure).

**(PDF13) Early stages.** Fit to e.g. 10 Å first, refining the scale only. If atomic displacement parameters are supplied, fix them initially. Fix cell parameters initially, then refine them.  Warn if a cell parameter changes by more than 1 %. Next try a single overall isotropic temperature factor, or one temperature factor per atom type. Fix fractional coordinates at this stage: they tend to be less stable than in a Rietveld refinement.

**(PDF14) Try different displacement models** to describe the r-dependence of peak widths. `beq_spherical()` as in the SnO2 example, with a single radius and one `beqlo`/`beqhi` per atom type, is a reasonable first model.

**(PDF15) PDFgui-like alternative.** PDFgui broadens peaks with delta1, delta2 and Qbroad: according to its manual `uij' = uij * Sqrt(1 - delt1/rij - delt2/rij^2 + Qbroad^2 rij^2)`. According to the TOPAS tutorial pages, the lines below give exactly the same broadening in TOPAS for beq sites or uij sites.
- Use the `Beqpdfgui2` macro below rather than the built-in `beq_PDFfit2` or `Beq` macros in `pdf.inc`. Put its definition in the INP file before the first site that uses it.
- `delt1`, `delt2` and `Qb` start fixed at small values, which switches them off. Turn on only one of `delt1` or `delt2` initially, not both: they correlate strongly (PDFgui guidance is delt2 for low temperature, delt1 for high temperature).
- Leave `Qb` fixed at its lowest allowed value unless a value from a standard is available.

Isotropic beq sites:
```
prm !delt1  0.001  min 1e-9 max 5
prm !delt2  0.001  min 1e-9 max 5
prm !Qb  1e-9 min 1e-9 max 100
macro Beqpdfgui2(c, v)
   {
      #m_argu c
      If_Prm_Eqn_Rpt(c, v, min 1e-6 max 5 val_on_continue = Val Rand(.1, 2); )
      beq = CeV(c, v)   (Abs(1 - delt1 /(1e-10+X) - delt2 /(1e-10+X)^2 + Qb^2 X^2));
   }
site O1 x   0.00000_ y   0.00000 z   0.00000 occ O 1 Beqpdfgui2(bval, 0.2368)
```

Uij sites need the `adps_scale` equation after each site:
```
prm !delt1  0.001  min 1e-9 max 5
prm !delt2  0.001  min 1e-9 max 5
prm !Qb  1e-9 min 1e-9 max 100
prm !aa 1   ' keep fixed: aa multiplies every Uij, so refining it with the Uij makes them fully correlated
adps_scale = 2 aa (Abs(1 - delt1 / X - delt2 / X^2 + (Qb^2) X^2));
```

**(PDF16) Coordinates.** Only refine coordinates once the range has been extended to e.g. 30 Å. Add min/max constraints to stop atoms moving too far. The order in which parameters are turned on for different sites mirrors Rietveld analysis. Exception: if the question is about local structure, refine coordinates against the short-r range and compare with the long-range fit.

**(PDF17) Nanoparticles.** PDF peaks die away faster with r than instrumental damping alone explains, because there are no atom pairs further apart than the particle diameter. Model this with a spherical particle-size envelope on the phase and refine the particle size. Warn the user that it correlates with Qdamp and scale, which is another reason to fix Qdamp from a standard.

**(PDF18) Anisotropic ADPs** — only once the model is already good.
1. Test the standard TOPAS uij approach first: replace each site's beq model (e.g. `beq_spherical(...)`) with a plain `beq <value>`, since `scripts/insert_adps.py` only converts a plain `beq`; then put explicit symmetry-constrained `u11`..`u23` on each site with `insert_adps.py`, add the `adps_scale` equation after each site, and refine.
2. Then try the ADP_5 approach: macro `ADP_5` in `PDF-adps.inc` splits each atom into 5 sub-sites (see `test_examples\PDF-adps`). It needs `#include ROOT##PDF-adps.inc` at the top of the INP file; `pdf.inc` is loaded automatically, `PDF-adps.inc` is not.
3. If ADP_5 fits better than uij, put the ADP_5 site coordinates into the uij model and re-refine, as a test of a false minimum.

**(PDF19) False minima.** PDF refinements can find false minima. Try several cycles of perturbing parameters and re-refining, using `continue_after_convergence` with `num_cycles N` (the bounded-run rule under "Running `tc.exe`" in SKILL.md). Only parameters with `val_on_continue` (or `randomize_on_errors`, or coordinates under `rand_xyz`) are perturbed between cycles. The `val_on_continue` in `Beqpdfgui2` already randomises its parameter; for other models, including `beq_spherical`, add `val_on_continue` to the key refined parameters or `rand_xyz` for coordinates, otherwise every cycle restarts from the same point.

## G(r) Generation

**(PDF20) PDF generation has not been fully tested in TOPilot.** Ask the user to supply a G(r) in `.xy` or `.xye` format if possible. If the TOPAS PDF generation procedure (`references/08-pdf-generation.md`) is needed, check that the files don't contain `continue_after_convergence` with an effectively unlimited number of cycles (the bounded-run rule in SKILL.md).

## Miscellaneous

**(PDF21) Closing warning.** At the end of a PDF refinement run (not after every reply), give exactly this warning to the user, immediately before the TOPilot version line that ends the report in `27`: "TOPilot has limited rules on PDF generation and model development.  All instrument- and model-related parameters must be checked by the user".
