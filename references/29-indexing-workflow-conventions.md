# Peak-fitting and indexing workflow conventions

Strategy conventions for extracting peak positions from a powder pattern and indexing them.
These are defaults to apply automatically; deviate only if the user specifies otherwise.

**This file carries two independent tag sequences.** `(FI1)`, `(FI2)`, ... cover **peak
fitting**, from raw data to a classified peak list. `(IN1)`, `(IN2)`, ... cover **indexing**,
from that peak list to a reported cell. Each runs sequentially with no gaps and the two never
interleave. Headings group rules for readability only and do not gate or reset the numbering.
New rules take the next free number in their own sequence and sit under the heading they belong
to, even if that puts them out of numeric order.

**The next free FI number is FI37 and the next free IN number is IN20.** Update this line whenever a rule is added or the file is renumbered.

**FI- and IN-numbers are confined to this file.** Nothing else in the skill cites a rule by
number; such citations go stale silently when this file is renumbered. Elsewhere refer to a rule
by topic and look the number up here. (`references/27-rietveld-workflow-conventions.md` keeps
its own `R`-sequence under the same rule.)

**Where the two sequences overlap, FI wins.** `check_single_phase.py` and `find_hidden_satellites.py` have been deleted; their roles are covered by the fitted-width clustering of FI22-FI26, Rachinger stripping (FI2-FI4) and the satellite tests of FI28-FI29.

## Part 1 - Peak fitting

### Data preparation

**(FI1) Do not guess radiation or instrument corrections.** If not stated in the instructions, ask. Apply `LP_Factor` to structure-factor intensities (`str`/`hkl_Is`), never to empirical observed peak areas (`xo_Is`).

**(FI2) Rachinger-strip Ka1/Ka2 data before the peak search only.** Every later stage uses the original data with the correct emission-profile macro.

**(FI3) Strip by fixed-point iteration on the background-subtracted signal.** Iterate `strip_{n+1}(x) = raw(x) - r*strip_n(x - d(x))` with `d(x) = 2 (lam2/lam1 - 1) tan(x/2)`, vectorised, clipped at zero each pass, 6 passes. A single pass leaves a negative ghost of amplitude `r^2` at `+2d` and is not sufficient; the in-place low-to-high sweep accumulates error and rings. Strip the background-subtracted signal - background is not doubled by Ka2.

**(FI4) Skip stripping where the predicted split falls below ~1.5 data steps.** Report that it was skipped rather than degrading. Zero error and sample displacement are negligible for the split magnitude and need no correction.

### Peak search

**(FI5) Run the peak search at the default `--sig-mult` 5, not raised.** A raised threshold drops real lines, including lines above 10 sigma, and the later stages do not reliably recover them. `peak_search.py` requires plain text, so convert a binary `.raw` first using the `Out_X_Yobs` recipe in `SKILL.md`.

**(FI6) Use area, not height, as `I` in `load xo I { }`.**

### Stage 1 - shared-shape fit in TOPAS

**(FI7) Fit the unstripped data with one shared `TCHZ_Peak_Type` plus `Simple_Axial_Model()`, positions and areas free.** The shared shape is determined by the strong resolved peaks and applied to the weak ones, leaving each weak peak two parameters. Start from `example_inp_files/peak_fit_shared_tchz.inp`.

**(FI8) Where a free per-peak FWHM is needed, refine it in two stages and with `do_errors`.** First converge with positions and areas fixed. Then release areas and FWHM together, holding positions at their Stage-1 values. Every free width carries a `min` and `max` per (FI17). `do_errors` is required, not optional: the esd on each width is what (FI22) weights by and what (FI23) tests against, and it ranges from about 3% of the width on strong sharp lines to 50% on weak ones.

**(FI9) Restrict `start_X`/`finish_X` to the region carrying usable peaks** before any variant testing.

**(FI10) Drop a candidate that refines to near-zero area from the fitted model, but keep it in the reported list.** Residual mining ((FI11)) re-finds it if it is real.

### Stage 2 - residual mining for missed peaks in TOPAS

**(FI11) Emit `Out_X_Ycalc` every run and locate misfit by residual, not by Rwp.** Add unexplained positive-residual features to the shared-shape group and refit; repeat until no coherent residual cluster remains.

**(FI12) Read the residual signature before deciding what a misfit is.** Negative core with positive wings means the model peak is too narrow for the data - a broader population. The reverse means too broad. A single-sided residual means a missing neighbour.

**(FI13) Classify each residual cluster by whether it sits on one side of an existing peak or on both.** A *matched pair* of positive clusters flanking a fitted position is peak-shape inadequacy; adding a peak there fits noise. A *one-sided* cluster beside a fitted peak is a missing neighbour or a shoulder and is tested with (FI14). An isolated cluster with no fitted peak nearby is a candidate outright. A shoulder has no local maximum, so no peak-search threshold finds it and lowering `--sig-mult` only adds noise.

### Stage 3 - classification

**(FI14) Decide "one broad peak or two close peaks" by running all three models, not by geometry.** With the shared TCHZ pinned, run per-window variants: (a) one peak, shared TCHZ; (b) two peaks, shared TCHZ; (c) one peak, free FWHM floored per (FI17). Compare weighted chi-squared over that window only, with an F-test penalty for the added parameters. `scripts/run_variants.py` provides the scripted-variants plumbing.

**(FI15) Use asymmetric F-test thresholds in (FI14): 90% to accept the split (b), 99% to accept the single free-width peak (c).** Where both pass, (b) wins. These thresholds are not yet validated against a case where the test decides the outcome.

**(FI16) Separation-versus-sigma and profile asymmetry propose splits; they do not decide them.** Use them to select which windows get the (FI14) test.

**(FI17) Floor a free FWHM at an absolute limit, not at the main-phase width.** An impurity can be sharper than the main phase. Use `min = Max(0.005, 2 * step)` in degrees and a `max` of 2 degrees.

**(FI18) A free per-peak FWHM needs one `xo_Is` block per peak.** `xo_Is` carries only `[xo E I E]`; peak shape is a property of the block, not of the row. A third `load xo I pv_fwhm { }` column parses but does **not** refine: TOPAS accepts the `@` silently and leaves every width at its starting value, with no `` ` `` error suffix in the `.out`. Build from `example_inp_files/peak_fit_per_peak_fwhm.inp` and generate the blocks programmatically. Working form:

```
prm plor 0.5 min 0.001 max 1
...
   xo_Is
      peak_type pv
      pv_lor = plor;
      pv_fwhm fw007 0.05 min 0.01 max 2
      load xo I { 24.83374  @ 128.38 }
```

**(FI19) Share `pv_lor` across all per-peak blocks.** Refining `pv_lor` and `pv_fwhm` together per peak saturates the mixing parameter at its limit on most peaks. Use one global `prm` referenced by every block.

### Stage 4 - final fit in TOPAS and export

**(FI20) Final model is several `xo_Is` groups in one `xdd`:** shared TCHZ (main phase), second/third/etc TCHZ (second/third/etc population), free-width group floored per (FI17) (anything matching neither trend - broad, amorphous, or a sharper foreign phase). Save this INP file and its outputs in the working directory - either where the data lives or where instructed by topilot-wizard (if used); never in a scratch or temporary directory.

**(FI21) Classify into three tiers, not two: MAIN, AMBIGUOUS, IMPURITY.**

**(FI22) Cluster widths in FWHM-squared versus tan(theta) space, never on raw FWHM, and fit the trends on well-measured widths only.** Raw FWHM grows with angle within a single population, so a raw-width split returns the angle at which it was cut. Define each trend using only peaks whose FWHM esd is below about 10% of the width, weighting by 1/(esd^2 + intrinsic scatter^2); a weak peak's width does not locate a trend but in an unweighted fit it pulls the curve as hard as a strong one. Then extend to the remaining peaks, assigning a peak only where the two nearest trend curves differ by at least 2 sigma at that angle, counting both its own esd and each trend's scatter. Where the curves converge, the peak is AMBIGUOUS. This is what stops one phase being split across two named trends.

**(FI23) Move very broad peaks to the mop-up group before clustering, then choose the number of trends by information criterion with two guards.** SSR and likelihood in FWHM-squared units are dominated by the broadest features, so separate anything wider than about 3x the median FWHM first. Floor each trend's intrinsic scatter at a small fraction of the median esd and require at least 8 peaks per trend: an unfloored component drives its scatter to zero, claims unbounded likelihood, and the criterion then rewards splitting until every trend is noise. A single peak alone in its own trend belongs in the mop-up group.

**(FI24) Check chi-squared per degree of freedom about each trend's own curve before sub-dividing it.** A value near 1 means the widths are described by that trend within their esds. A value far above 1 means the widths carry structure the model does not explain - unresolved overlaps, or one shared `pv_lor` failing to match every profile - and any finer split then fits those systematics rather than a phase boundary. Report the value and treat trend boundaries as provisional when it is large.

**(FI25) A width trend is not necessarily a phase, and two phases can be inseparable by width in principle.** hkl-dependent broadening or different 2-theta dependent broadening between phases could put one phase across several trends. Also a subtle distortion from a higher-symmetry parent splits some reflections and not others, and the split classes fit as broad. Conversely, width depends on crystallite size and strain, never on cell size, so two well-crystallised phases with similar size and strain share one width curve however good the data - they are separable only by position, at the indexing stage.

**(FI26) Seed MAIN from the trend carrying the largest total fitted area, then classify per line** under (FI27), since one phase can span several trends. State which trend seeded MAIN and on what margin.

**(FI27) Reach IMPURITY only on corroborated evidence.** MAIN if the shared TCHZ fits the peak. IMPURITY only if variant (c) of (FI14) wins at the (FI15) threshold *and* the fitted width lies on a second coherent Caglioti trend carrying at least three other peaks. AMBIGUOUS otherwise. A lone peak with no trend to join is AMBIGUOUS, not IMPURITY, whether it is broader or sharper than the main phase.

**(FI28) Never move a weak line to IMPURITY on width alone.** Superlattice reflections are weak by definition and their fitted widths are the least reliable in the list.

**(FI29) Check the MAIN list for W Lalpha and Cu Kbeta contamination as a final step.** Both are source lines, not sample reflections, and both fall at *lower* 2-theta than the Cu Kalpha1 peak they derive from: `sin(theta) = sin(theta_Ka1) * lam/lam_Ka1`, with lam_Kbeta = 1.39222 A (ratio 0.9037) and lam_W_Lalpha = 1.47642 A (ratio 0.9583). Indexing a contamination line forces a wrong cell.

**(FI30) Remove a line as W Lalpha or Cu Kbeta only when every test passes:** it matches within 0.10 degrees 2-theta; its area is a few percent of the parent's and never more than ~5%; the parent is one of the strongest lines in the pattern, not merely above average; and at least one other strong parent shows its own satellite. **Never remove a strong line on this test.** A lone match against a modest parent indicates the line is real.

**(FI31) Export two files.** `*_impurity.inc`, a drop-in `xo_Is` block per non-MAIN group (its TCHZ plus its `load xo I { }`) for `#include` inside `xdd`; and `*_peaks.json` carrying every line with position, area, FWHM, `pv_lor`, group, tier and confidence, the TCHZ parameter set of each group, wavelength and provenance.

**(FI32) Record the fitting conditions in the `.inc` header:** emission-profile macro, `Simple_Axial_Model` value, LP setting and 2-theta range. The exported shape parameters and areas are valid only against those.

**(FI33) Write exported impurity areas fixed.** These may be used in the simulated annealing or Rietveld stages so should be fixed so they don't absorb main-phase intensity. Release them only in the final Rietveld.

**(FI35) Drop any peak whose fitted area is within 3 sigma (esd) of zero from the final `.inp`.** It is not resolved from the background and only adds a parameter that refines to noise.

**(FI36) Before finalizing, reset the shared TCHZ to small starting values and re-refine, then compare Rwp against the staged result.** Same mandatory false-minimum check as Rietveld (`references/27-rietveld-workflow-conventions.md` R39): TCHZ's mutually-correlated terms can walk into a false minimum with no visible symptom during staged refinement. Run this unconditionally, even on a clean convergence. Adopt the reset run if it converges lower and say so; otherwise the staged result stands, but report that the check was run either way.


### Reporting of peak fitting states

**(FI34) Produce a Rietveld-style overlay with one tick row per group, each in its own colour.** `Out_X_Ycalc` from the final fit against the observed data. `scripts/plot_xy.py` does this directly; the tick files are two-column `2theta intensity`, the same format as `Create_2Th_Ip_file`:

```
python scripts/plot_xy.py yobs.xy final_ycalc.xy --labels "Yobs,Ycalc" \
   --colors "blue,red" --diff "Yobs,Ycalc" \
   --ticks "MAIN|main.txt|#2e7d32,TREND2|t2.txt|#8a5ba6,MOPUP|mop.txt|#b5502f" \
   -o peakfit.html
```


## Part 2 - Indexing

### From peak fitting to indexing

**(IN1) Index the MAIN tier only, using the fitted positions, and expect it to hold more than one phase.** Take the 2-theta values of the MAIN group from the converged peak fit into `load index_th2 index_I { }` - the fitted values, never the peak-search estimates, which are limited to the data step. The peak fit cannot separate phases of similar crystallite size and strain, so MAIN is a width family and may contain several phases. Hold AMBIGUOUS lines back and test them against the cell once one is found. Leave any zero error to `index_zero_error`; do not pre-correct the positions.

### Indexing setup

**(IN2) Run the unrestricted baseline first.** Use the correct dominant `index_lam`, `seed`, `index_zero_error`, and all six Bravais macros: `Bravais_Cubic_sgs`, `Bravais_Trigonal_Hexagonal_sgs`, `Bravais_Tetragonal_sgs`, `Bravais_Orthorhombic_sgs`, `Bravais_Monoclinic_sgs`, and `Bravais_Triclinic_sgs`.

**(IN3) Treat indexing as stochastic.** Retry intermittent failures 2-3 times before suspecting the input, and repeat difficult searches with different seeds. Consistent recurrence of the same cell is reassuring; unrelated results are evidence of non-convergence.

**(IN4) Do not invent `x_scaler` or `x_angle_scaler` values.** Both control how finely the search samples parameter space. `x_scaler` must be below 1, and larger values search more finely; the defaults fall with symmetry - cubic 0.99, hexagonal/trigonal and tetragonal 0.95, orthorhombic 0.89, monoclinic 0.85, triclinic 0.72. `x_angle_scaler` (default 0.1) sets the angular step count for monoclinic and triclinic; smaller values give more steps. Change them only from a verified example.

### Interpreting candidates

**(IN5) Read GoF together with UNI.** A high GoF with `UNI>0` is incomplete. Scan the full `.ndx` list for the best fully indexed candidate rather than accepting rank 0 automatically.

**(IN6) Compare metrically related candidates by primitive volume, not conventional volume or GoF.** Divide conventional volume by centering multiplicity (`P=1`, `A/B/C/I=2`, `R=3`, `F=4`); GoF is biased by reflection density. Equal primitive volumes are metric re-descriptions and require intensities, Pawley/Le Bail fits, or structure solution to distinguish.

**(IN7) Test both metric and supercell pseudosymmetry.** For higher-symmetry metrics, inspect sensitive peak splitting. If no splitting is resolved, the higher-symmetry cell may still be reported, but state that a lower-symmetry distortion is unresolved. For metrically related cells with an integer primitive-volume ratio, inspect extra reflections. Observed extras support the larger cell; absence is inconclusive.

**(IN8) Use the extinction-subgroup table in `references/14-indexing.md` for space-group comparisons.** Treat groups as positionally indistinguishable only when they share an extinction row; do not infer this from similar symbols or crystal systems. Within a row, take the highest-symmetry member first and descend only if structure solution fails there. A supergroup sharing a subgroup's absences may not appear in the search output at all, so its absence is not evidence against it; watch for its standard setting permuting a/b/c relative to the subgroup's axis choice.

**(IN9) Diagnose inconclusive searches in order.** A cell that indexes part of MAIN and leaves the rest as UNI lines is the expected result when MAIN holds more than one phase: take those UNI lines as the second phase's candidate set and index them separately. Otherwise treat low GoF, mostly triclinic results, or sentinel GoF values as warning signs. Re-check the peak fit - overlay `Out_X_Ycalc` against the data and confirm no MAIN line sits on an unfitted or mis-centred feature; retry with different seeds; repeat using the strongest/lowest-angle lines; apply a justified Bravais restriction. If no self-consistent candidate emerges, report the result as unresolved.

**(IN10) When the user supplies a candidate cell or structure, search the whole `.ndx` list for it.** Check the exact cell and space group, allowing axis permutations, below rank 0 as well. Absence of a supplied candidate from the top of the list is not evidence against it.

### Bravais-class restrictions

**(IN11) Restrict only after the unrestricted search.** Use a restriction only when supported by near-equal axes or special angles, recurring volume/cell relationships, near-tied same-cell candidates, a non-repeating low-symmetry swarm, or a clearly disproportionate search-space count.

**(IN12) Interpret restriction conservatively.** A clean metric degeneracy may make restriction decisive; a low-symmetry swarm may only become smaller and easier to review. Restriction alone does not establish the correct cell.

**(IN13) Check mixed phase before concluding genuine low symmetry.** A recurring low-symmetry candidate with a modest GoF can reflect an unremoved impurity. Re-read the width-trend classification ((FI22)-(FI27)) before accepting the cell - but note that a width trend is not necessarily a phase ((FI25)).

**(IN14) After indexing, match each `.ndx` UNI line to the peak-fit `.out`.** Remove a line only when the fit independently shows it is an artefact; check whether it is a superlattice reflection first. This is also where AMBIGUOUS lines held back by (IN1) are tested against the cell.

### Superlattice protection

**(IN15) Treat weak reflections as potentially decisive.** Peak thresholds, width screening and refinement can all remove superlattice reflections and leave a clean but undersized substructure. The peak-fitting stage therefore tiers rather than labels ((FI21)) and never moves a weak line out on width alone ((FI28)).

**(IN16) Test simple supercells before accepting any cell.** Run `python compare_cells.py yobs.xy --lam wavelength --cell A a b c al be ga --centering A P --cell B a2 b2 c2 al2 be2 ga2 --centering B F` with doubled variants and, for centred candidates, the corresponding primitive/centred alternatives; this is especially mandatory for a suspiciously clean small cell or when any peaks were dropped. Observed reflections unique to the larger cell support the larger cell; absent reflections do not prove the smaller cell.

### Reporting

**(IN17) Report the cell, crystal system, unresolved alternatives, UNI status, and the evidence used to reject competing candidates. State which space groups share an extinction row; label any reported space-group name as representative when it is not uniquely established; and distinguish conclusions supported by peak positions from those requiring intensities or structure solution.**

**(IN18) Use filename or database identity only as corroboration.** Check formula/mineral/refcode hints, but never use them as a substitute for peak, metric, or extinction evidence; database numbers are not space-group numbers.

### Perform Pawley

**(IN19) Pawley-test the best few plausible cells.** If asked to do so, perform a simple Pawley fit for e.g. the best five (or number prompted) non-equivalent candidates, initially to about 60 degrees 2theta for Cu radiation (or an equivalent moderate range). Compare peak overlap, residuals, and Rwp; use the main TOPAS skill for Pawley file construction and syntax.
