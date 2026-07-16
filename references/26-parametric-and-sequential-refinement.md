# Sequential and Parametric (Surface) Refinement

Not documented in the TOPAS Technical Reference manual as a named technique — sourced from Dinnebier, Leineweber & Evans, *Rietveld Refinement: Practical Powder Diffraction Pattern Analysis using TOPAS* (2018), Chapter 12. The underlying keywords (`#list`, `num_runs`, `Run_Number`, `system_before_save_OUT`/`system_after_save_OUT`, `out_prm_vals_on_convergence`, `local`, `for xdds`/`for strs`, `val_on_continue`, `continue_after_convergence`) are all individually documented elsewhere in this skill (`references/01-syntax-and-parameters.md`, `references/05-reusing-objects-large-refinements.md`, `references/20-miscellaneous.md`) — what's new here is the *technique* that ties them together for analyzing a whole series of powder patterns collected as a function of an external variable (temperature, pressure, time, etc.), and the theory behind why one approach is often much better than the other. The skill's bundled `example_inp_files/parametric_06.inp` is a real worked example of the parametric approach described below.

## Two ways to analyze a series of patterns

- **Sequential refinement**: each pattern in the series is refined independently, using the *previous* pattern's converged parameter values as the starting point for the next. All structural/profile/background parameters are free to vary from pattern to pattern. Analysis of trends (e.g. fitting a smooth function to cell parameter vs. temperature) happens only *afterward*, as post-processing on the refined values.
- **Parametric (a.k.a. "surface") refinement**: all patterns in the series are refined *simultaneously in one combined least-squares refinement*, with selected parameters constrained to follow a single smooth functional form across the whole series (e.g. one cell-parameter-vs-temperature curve, not 100 independent cell parameters) rather than varying freely pattern-to-pattern.

Sequential refinement is simpler to set up and is the right choice when there's no reason to expect parameters to vary smoothly (e.g. right across an abrupt phase transition, or when you have no physical model for how a parameter should change). Parametric refinement is far more powerful — but only when a smooth physical model really does apply — because it can (1) reduce the total number of free parameters drastically, (2) let you refine physically meaningful *non-crystallographic* parameters (a transition temperature, a critical exponent, a kinetic rate constant, a temperature-calibration offset) that no single pattern could ever determine on its own, and (3) resolve strong correlations/near-degeneracies between candidate structural models by forcing one consistent physical story to fit the *whole* data surface at once, not just each noisy pattern individually.

## Simulating a series of patterns (building intuition/test data first)

A single simulated pattern uses `yobs_eqn` in place of `xdd` (the equation, usually just `= X;`, replaces the observed-data column entirely) with `iters 0` since nothing is being refined; `Out_X_Ycalc` saves the result. Realistic synthetic noise can be added with `Rand_Normal(Ycalc, Sqrt(Ycalc))` in place of `Ycalc` in an `xdd_out` block — this reproduces Poisson (counting-statistics) noise, the standard assumption for single-counter/point-detector data.

A *series* of simulated patterns uses the same `num_runs`/`Run_Number` machinery documented elsewhere in this skill, varying some parameter as a function of `Run_Number` (e.g. `lor_fwhm = 0.1 Run_Number Tan(Th);` to simulate increasing strain broadening across 10 runs) and using `Run_Number` in the output filename (`` yobs_eqn !aac##Run_Number##.xy ``) so each run's simulated pattern gets its own file.

**Dual GUI/command-line scripting trick**: a single INP file can be made to work both interactively in the GUI (`ta.exe`/`topas.exe`) and unattended from the command line (`tc.exe`) using:
```
#ifdef !GUI_LINES 'use these lines when in gui mode
   macro filename {d8_02339}
   macro rangeuse {12}
#endif
```
When run under the GUI, `GUI_LINES` is undefined, so this block supplies default macro values directly in the file. When run via `tc.exe` with `#define GUI_LINES` passed on the command line (along with the real `macro filename {...}` etc. also passed on the command line), this block is skipped and the command-line-supplied macros are used instead. This is a convenient way to keep one canonical INP file that works for both quick interactive testing and full batch/scripted processing of many files.

## Sequential refinement in TOPAS (v6+)

A one-dimensional array of data-file names is declared with `#list`:
```
#list File_Name
{
   file1.xy
   file2.xy
   file3.xy
}
```
`num_runs` sets how many runs to perform (usually the list length); `Run_Number` (0 to `num_runs`-1) is the running index, and `File_Name(Run_Number)` retrieves the current file — used directly as `xdd File_Name(Run_Number)`. Extra per-pattern metadata (e.g. temperature, if it isn't a simple function of `Run_Number`) can be added as further columns in the same `#list` block (`#list File_Name Temperature`) and read the same way.

**Carrying values forward between runs**: since sequential refinement means each run should start from the previous run's converged values, an OUT file must be written and then copied over the INP file before the next run starts:
```
out_file = Concat(String(INP_File), ".out");
system_after_save_OUT
{
   copy INP_File##.out INP_File##Run_Number##.out   ' keep a labeled copy for QC
   copy INP_File##.out INP_File##.inp               ' becomes the next run's input
}
```
(`system_before_save_OUT` is the same idea but executes before the OUT file is written, if ordering matters.)

**Collecting results across runs**: `out_prm_vals_on_convergence` writes every parameter in the model to a file (the least controlled option — useful for a first look, unwieldy for anything with many parameters). For a curated set of values, the `Append_0(file)` macro (creates the file fresh at `Run_Number`==0, appends thereafter) combined with `Out(...)` calls is the usual pattern; wrap optional/derived values in `if Prm_There(name) { Out(name, "%V") }` so the script doesn't fail if a particular parameter happens not to exist in every run's model (e.g. a phase that only appears in some temperature ranges).

**A real failure mode to know about**: in a multi-phase sequential series, a phase that's disappearing (its true weight fraction dropping toward zero) will frequently refine to unrealistically broad, diffuse peaks that "mop up" background or overlap with other phases, distorting the reported phase fractions right around the point where the phase is actually vanishing. Two standard mitigations:
- Impose a hard lower bound on that phase's crystallite size, e.g. `LVol_FWHM_CS_G_L(1, ..., 0.89, ..., csgc, csgv, cslc, @ 11.0 min lower_size_limit)` with `macro lower_size_limit { 11 }` (a physically-reasoned minimum in nm) — prevents the "infinitely broad" runaway directly.
- Automatically drop phases below a weight-percent threshold using the already-documented `Remove_Phase` macro: `for strs { Remove_Phase(0.7) }` (see `references/20-miscellaneous.md`).
- For step changes across the series (a phase that's present only in some temperature/pressure window), a preprocessor conditional can turn whole `str` blocks on/off as a function of the run's physical variable:
  ```
  #prm t = 100 + (Run_Number * 4);
  #if Or(t < 158, t > 226); #define Phase1
  #elseif And(t > 158, t < 198); #define Phase1 #define Phase2
  #elseif And(t > 198, t < 226); #define Phase2
  #endif
  ...
  #ifdef Phase1
     str ...
  #endif
  ```
  Parametric refinement (below) often removes the need for this kind of manual phase-boundary bookkeeping altogether, by fitting one consistent model across the whole series.

A real example in the book: a 348-pattern synchrotron series tracking α-Fe/Fe3C/Fe4N/Fe3O4 phase evolution and crystallite-size changes in carbonyl iron powder heated in flowing nitrogen — a completely ordinary sequential setup at the per-pattern level, automated end-to-end via exactly the `#list`/`out_file`/`system_after_save_OUT`/`Append_0` machinery above.

## Parametric (surface) refinement

Instead of letting a parameter vary freely pattern-to-pattern, it's constrained to a single smooth function of the external variable, with the function's *coefficients* — not per-pattern values — refined jointly from every pattern in the series in one combined least-squares fit. Typical functional forms (paraphrased from the book's Table 12.1 — pick the form that matches the actual physics, don't use these blindly):

| Quantity | Typical functional form | Notes |
|---|---|---|
| Cell parameter or ADP vs. temperature | Einstein-like: `a0 + c1*theta1/(Exp(theta1/T)-1)` | Refined: a0, c1, theta1. Naturally gives zero gradient at T=0 K — physically correct low-T behavior a plain polynomial wouldn't guarantee. |
| Fractional coordinate vs. temperature | Simple polynomial: `x0*(1 + c1*T + c2*T^2 + c3*T^3)` | |
| An order parameter near a phase transition | Critical/power-law: `c1*(1 - T/Tc)^beta` | For a site occupancy, magnetic moment, or other quantity that vanishes continuously at a critical temperature Tc with critical exponent beta. |
| Kinetic process vs. time | Simple rate law: `c1*(1 - Exp(-k*t)) + c2` | More complex evolution: `k*(t-t0)` or `k*(t-t0)^n` forms. |
| Zero-point error | Constant across the whole series: `czero` | Physically, instrument zero-shift shouldn't drift during one experiment — refining one shared value from all patterns is both more physical and far better determined than fitting it per-pattern. |
| Sample height vs. temperature | Polynomial: `h0*(1 + c1*T + c2*T^2)` | Models smooth thermal expansion of the sample mount in Bragg-Brentano geometry. |
| Furnace-vs-sample temperature offset | `c0*(1 + c1*Tset + c2*Tset^2)` | ΔT = Tsample − Tset; see the temperature-calibration application below. |

**Why this works, mechanically** (not just "fewer parameters"): forcing e.g. a phase's cell parameters to follow one smooth curve across the whole series prevents that phase's structural model from quietly distorting to absorb minor fitting discrepancies in temperature regions where the phase is barely present — if it did, the same distorted parameters would then fail to fit the (more reliable) data in regions where that phase dominates. The same logic applies to peak-shape parameters: constraining them to be consistent for a given phase across the series means they're effectively determined by the temperature/time regions where that phase actually has real, strong intensity, rather than being free to run away (e.g. to unrealistically huge FWHM) in regions where the phase is nearly absent and its peak shape is poorly constrained by the data.

**The key diagnostic**: compare the per-pattern R-factor from a parametric fit against the per-pattern R-factor from sequential refinement of the same data. If the parametric fit is dramatically worse for some patterns, the imposed functional form is probably not describing the real physics well in that region — the parametric approach's "weakness" (it's easy to get a visibly bad fit if the model is wrong) is actually a diagnostic strength, since sequential refinement can hide the same problem by letting each pattern's parameters silently drift to physically nonsensical values that still fit the local noise (Magdysyuk et al., 2014).

**A concrete before/after** (WO3 cooled 300→90 K through two displacive phase transitions, 100 patterns, 3 coexisting phases with very similar peak positions in places): sequential refinement (56 parameters × 100 patterns = 5600 total, each individually pushed to its lowest-Rwp solution via simulated annealing — i.e. "best possible" sequential fitting) still produced phase fractions and cell parameters with unphysical jumps and reversals with temperature. A parametric refinement of the *same data* — cell parameters via the Einstein-like form above, one consistent peak shape per phase across the whole series, atomic coordinates shared across all patterns — used only 1167 total parameters (refined simultaneously from all 100 patterns in one combined refinement) and produced phase fractions and cell volumes that varied smoothly and made direct physical sense (comparable thermal-expansion coefficients per phase), despite no smoothness being explicitly imposed on the phase fractions themselves.

## Non-crystallographic parameters

Because the parametric functional form's *coefficients* are the actual refined quantities, parametric refinement lets you refine physically meaningful values that no single pattern could ever determine:
- **Temperature calibration** (Stinton & Evans, 2007): mix an internal standard of known thermal expansion (Si, Al2O3, etc.) into the sample; instead of refining the standard's cell parameters freely, fix them to their literature Einstein-like/polynomial expansion curve, and refine a furnace-vs-sample temperature offset ΔT = f(Tset) instead. Any mismatch between the furnace's set temperature and the sample's real temperature shows up directly as a peak-position discrepancy for the standard, and gets absorbed into ΔT rather than corrupting the sample's own cell parameters. Applied to 871 datasets on ZrP2O7, this approach recovered both a genuine phase-transition temperature and cell parameters that agreed with independent DSC data far better than sequential refinement did.
- **Reaction kinetics**: refining a rate constant *k* (e.g. an Arrhenius temperature-dependence of k) directly from a whole time/temperature-resolved series (site occupancies or cell parameters following a simple rate law) — used to follow oxygen-migration kinetics in ZrWMoO8, and (per the book) an unpublished 4D (time+temperature) analysis of over 1000 patterns to extract an activation energy directly via Rietveld refinement, something no single pattern or even a per-pattern sequential analysis could deliver directly.

## Practical INP architecture for a large parametric refinement

A real parametric INP file for ~100 patterns can run to ~12,000 lines, but is manageable because it decomposes into six clearly separated, independently foldable (in jEdit) sections:
1. **Global refinement controls** — R-factor keywords, `continue_after_convergence`, `iters`, `#define` flags that switch behavior on/off elsewhere in the file (e.g. `#define param_cell` to switch a phase's cell parameters between the parametric functional form and ordinary free refinement; `#define write_out` to enable results logging).
2. **Per-dataset selection/metadata** — one line per pattern defining a `#define use_tNNNN` flag plus macros for that pattern's filename, temperature, and range number; commenting a line out excludes that pattern from the refinement entirely, similar in spirit to `#list` but with per-pattern `#ifdef` granularity.
3. **Per-dataset refinement instructions** — the bulk of the file: one `#ifdef use_tNNNN ... #endif` block per pattern, each structured identically to an ordinary single-pattern Rietveld INP (this is the section that's mechanically duplicated per dataset — see below).
4. **Overall cross-dataset parameters** — the shared coefficients of whatever functional forms are being used (the Einstein-model a0/c1/theta1 for each phase's cell edges, etc.) — these live *outside* any per-dataset block since they're shared by all patterns.
5. **`for xdds { ... for strs { ... } ... }` blocks** — anything common to every dataset/phase (instrument corrections, peak-shape macros, shared atomic coordinates) written once and automatically applied everywhere, exactly the object-sharing technique in `references/05-reusing-objects-large-refinements.md`, just applied at the "whole experiment" scale rather than within one pattern.
6. **Simplifying macros** — shared `min`/`max`/`val_on_continue` bounds-and-reset macros (useful for automatically pulling a parameter back to a sensible value if a refinement diverges) and output-formatting macros used by every per-dataset block.

**Generating the repetitive per-dataset section**: since section 3's content is identical for every pattern except for a per-pattern label (`t0001`, `t0002`, ...), the practical approach is to write it once as a template with a placeholder token, then mechanically substitute the real label for each pattern — e.g. via a Linux/WSL one-liner per dataset (`sed 's/t0000/t0001/g' single.riet`, repeated per pattern and concatenated), or an equivalent short Python/Perl script. This is standard practice for building these files, not something to write out by hand pattern-by-pattern.

## Plotting results

Both sequential and parametric refinement produce a results text file (one row per pattern) that needs plotting to sanity-check trends. The book recommends gnuplot for this (scriptable, fast, freely available) over point-and-click tools like Origin/Excel when there are many parameters/columns to check — a short gnuplot script can loop over every column of a results file and auto-generate one plot per parameter, which is much faster than manually re-configuring a GUI plotting tool for each one.

## Key references

- Stinton, G.W. & Evans, J.S.O. (2007). Parametric Rietveld refinement. *J. Appl. Cryst.* 40, 87–95.
- Magdysyuk, O.V., Müller, M., Dinnebier, R.E., Lipp, C. & Schleid, T. (2014). Parameterization of the coupling between strain and order parameter for LuF[SeO3]. *J. Appl. Cryst.* 47, 701–711.
- König, R. et al. (2017). The crystal structures of carbonyl iron powder – revised using in situ synchrotron XRPD. *Z. Kristallogr. – Cryst. Mater.* 232, 835–842. (Source of the sequential-refinement CIP worked example.)

Online tutorial referenced in the book (Durham University, John Evans's group): `topas_workshop/tutorial_surface_new.htm` (the WO3 parametric-refinement worked example).
