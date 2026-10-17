# Peak-fitting and indexing workflow conventions

Strategy conventions for extracting peak positions from a powder pattern and indexing them.
These are defaults to apply automatically; deviate only if the user specifies otherwise.

**Two independent tag sequences.** `(FI1)`, `(FI2)`, ... cover **peak fitting**, from raw data
to a classified peak list. `(IN1)`, `(IN2)`, ... cover **indexing**, from that peak list to a
reported cell. Each runs sequentially with no gaps. Headings group rules for readability only.
New rules take the next free number in their own sequence and sit under the heading they belong
to, even if that puts them out of numeric order.

**The next free FI number is FI24 and the next free IN number is IN27.** Update this line whenever a rule is added or the file is renumbered.

**FI- and IN-numbers are confined to this file.** Elsewhere, refer to a rule by topic; citations
by number go stale silently when this file is renumbered. (`references/27-rietveld-workflow-conventions.md`
keeps its own `R`-sequence under the same rule.)

## Part 1 - Peak fitting

### Data preparation

**(FI1) Do not guess radiation or instrument corrections.** If not stated, ask. Apply `LP_Factor` to structure-factor intensities (`str`/`hkl_Is`), never to empirical peak areas (`xo_Is`).

**(FI2) Rachinger-strip Ka1/Ka2 data for the peak search only.** Every later stage uses the original data with the correct emission-profile macro.

**(FI3) Strip by fixed-point iteration on the background-subtracted signal.** Iterate `strip_{n+1}(x) = raw(x) - r*strip_n(x - d(x))`, vectorised, clipped at zero each pass, 6 passes, where `d(x)` is the predicted Ka1->Ka2 split in degrees 2theta (`d(x) = degrees(2 (lam2/lam1 - 1) tan(radians(x/2)))`). Use `predicted_doublet_split()` or the `--rachinger` flag of `scripts/peak_search.py` rather than re-deriving it. A single pass leaves a negative ghost of amplitude `r^2` at `+2d`; an in-place low-to-high sweep accumulates error and rings. Skip stripping where the split falls below ~1.5 data steps, and say it was skipped.

### Peak search

**(FI4) Run the peak search at the default `--sig-mult` 5, not raised, and use area, not height, as `I` in `load xo I { }`.** A raised threshold drops real lines, including lines above 10 sigma, which later stages do not reliably recover. `peak_search.py` reads text or a Bruker `.raw` (converted through `tc.exe`, needs `TOPAS_DIR`); convert other binary formats with the `Out_X_Yobs` recipe in `SKILL.md`.

### Stage 1 - shared-shape fit in TOPAS

**(FI5) Fit the unstripped data with one shared `TCHZ_Peak_Type` plus `Simple_Axial_Model()` by default, positions and areas free, over the region carrying usable peaks only.** For time-of-flight neutron data use the back-to-back exponential TOF shape instead, from `example_inp_files/tof_template.inp`. The strong resolved peaks fix the shared shape and the weak ones inherit it, leaving each weak peak two parameters. Start from `example_inp_files/peak_fit_shared_tchz.inp`.

**(FI6) Where a free per-peak FWHM is needed, refine it in two stages with `do_errors`, floored at an absolute limit.** First converge with positions and areas fixed; then release areas and FWHM together, positions held. Use `min = Max(0.005, 2 * step)` and a `max` of 2 degrees - not the main-phase width, since an impurity can be sharper. The width esd (about 3% on strong sharp lines, up to 50% on weak ones) is the weight width clustering uses (FI12).

**(FI7) A peak whose fitted area is within 3 esd of zero leaves the fitted model but stays in the reported list.** It adds a parameter that refines to noise; residual mining (FI8) re-finds it if it is real.

### Stage 2 - residual mining for missed peaks in TOPAS

**(FI8) Emit `Out_X_Ycalc` every run and locate misfit by residual, not by Rwp.** Add unexplained positive-residual features to the shared-shape group and refit until no coherent residual cluster remains.

**(FI9) Read the residual signature before acting on it.** A matched pair of positive clusters flanking a fitted peak (negative core, positive wings) means the model peak is too narrow - a broader population - and adding a peak there fits noise; the reverse means it is too broad. A one-sided cluster is likely a missing neighbour or a shoulder: test it with (FI10). An isolated cluster is a candidate outright unless it is markedly broader than the shared shape, which means a second width population; release per-peak widths (FI6) and re-cluster (FI12) rather than stacking spurious narrow peaks that would then index as real lines. A shoulder has no local maximum, so lowering `--sig-mult` will not find it.

### Stage 3 - classification

**(FI10) Decide "one broad peak or two close peaks" by fitting all three models, not by geometry.** With the shared TCHZ pinned, fit per window: (a) one peak, shared shape; (b) two peaks, shared shape; (c) one peak, free FWHM floored per (FI6). Compare weighted chi-squared over that window with an F-test penalty: accept (b) at 90% and (c) at 99%; where both pass, (b) wins. Separation-versus-sigma and profile asymmetry only choose which windows to test. `scripts/run_variants.py` provides the plumbing.

**(FI11) A free per-peak FWHM needs one `xo_Is` block per peak, with one `pv_lor` shared by all blocks.** `xo_Is` rows carry only `xo` and `I`; `peak_type`, `pv_lor` and `pv_fwhm` are block-level, so a third `load xo I pv_fwhm { }` column parses without error but never yields per-peak widths. Share `pv_lor` because it correlates strongly with FWHM on a single peak; refined per peak it tends to run to a limit, especially on weak or overlapped lines. Build from `example_inp_files/peak_fit_per_peak_fwhm.inp`, generating the blocks programmatically, with width limits per (FI6) (here for a 0.003 degree step):

```
prm plor 0.5 min 0.001 max 1
...
   xo_Is
      peak_type pv
      pv_lor = plor;
      pv_fwhm fw007 0.05 min 0.006 max 2
      load xo I { 24.83374  @ 128.38 }
```

**(FI12) Cluster widths in FWHM-squared versus tan(theta), never on raw FWHM, and fit trends on well-measured widths only.** Raw FWHM grows with angle within one population, so a raw-width split just returns the angle it was cut at. Define each trend from peaks with FWHM esd below ~10% of the width, weighted by 1/(esd^2 + intrinsic scatter^2); assign other peaks only where the two nearest trends differ by at least 2 sigma at that angle (own esd plus trend scatter); otherwise mark the peak AMBIGUOUS.

**(FI13) Move very broad peaks (over ~3x the median FWHM) to the mop-up group first, then choose the number of trends by information criterion.** The broadest features otherwise dominate the fit. Floor each trend's intrinsic scatter at a small fraction of the median esd and require at least 8 peaks per trend; a lone peak belongs in the mop-up group.

**(FI14) Check chi-squared per degree of freedom about each trend before sub-dividing it.** Near 1, the trend describes its widths. Far above 1, the widths carry unexplained structure (unresolved overlaps, or one shared `pv_lor` not fitting every profile) and a finer split would fit those systematics; report the value and treat trend boundaries as provisional.

**(FI15) Do not equate a width trend with a phase.** Broadening that depends on hkl spreads one phase over several trends, and a subtle distortion of a higher-symmetry parent broadens only the reflection classes it splits. Two well-crystallised phases of similar size and microstrain share one width curve; separate them by position when indexing.

**(FI16) Classify every line into three tiers - MAIN, AMBIGUOUS, IMPURITY - seeding MAIN from the trend carrying the largest total area, then classifying per line**, since one phase can span several trends. State which trend seeded MAIN and on what margin.

**(FI17) Reach IMPURITY only on corroborated evidence, never on width alone.** MAIN if the shared TCHZ fits the peak. IMPURITY only if variant (c) of (FI10) wins *and* the width lies on a second coherent trend with at least three other peaks. Otherwise AMBIGUOUS - including a lone peak, whether broader or sharper than the main phase. Weak lines need particular care: superlattice reflections are weak by definition and their widths are the least reliable in the list.

**(FI18) Check MAIN for Cu Kbeta and W Lalpha contamination last, and remove a line only when every test passes.** Both source lines fall at *lower* 2-theta than their Cu Ka1 parent: `sin(theta) = sin(theta_Ka1) * ratio`, ratio 0.9037 for Kbeta (1.39222 A) and 0.9583 for W Lalpha (1.47642 A). Remove only if the line matches within 0.10 degrees; its area is a few per cent of the parent's and never above ~5%; the parent is one of the strongest lines in the pattern; and at least one other strong parent shows its own satellite. **Never remove a strong line on this test**; a lone match against a modest parent means the line is real. An indexed contamination line forces a wrong cell.

**(FI19) A weak line on the flank of a much stronger one does not vote on the cell - hold it back as AMBIGUOUS, never delete it.** Screen the list going into `load index_th2 index_I { }`: any line under ~1% of the strongest, and any line within `max(0.5 deg, 1.6 x predicted Ka1->Ka2 split)` of a neighbour at least ~20x stronger (the split grows with tan(theta), so use `predicted_doublet_split()`). Ka2 stripping residue is the commonest source - it survives at 1-5% of strong parents, displaced ~1.2-1.4x the nominal split - and profile tails on Ka1-only data behave the same. A held-back superlattice line is recovered when a doubled cell explains it (IN16). Where a blanket floor would leave too few lines, test only the best candidate's own UNI lines instead (IN15).

### Stage 4 - final fit in TOPAS and export

**(FI20) The final model is several `xo_Is` groups in one `xdd`:** shared TCHZ for the main phase, a further TCHZ per further width population, and a free-width group floored per (FI6) for anything matching neither (broad, amorphous, or a sharper foreign phase). Save it and its outputs in the working directory - where the data lives, or where topilot-wizard says - never in a scratch or temporary directory.

**(FI21) Before finalising, reset the shared TCHZ to small starting values, re-refine, and compare Rwp with the staged result.** It is the same mandatory false-minimum check as for Rietveld (the false-minimum re-check rule in `references/27-rietveld-workflow-conventions.md`): correlated TCHZ terms can settle in a false minimum with no visible symptom. Run it even on a clean convergence and report it either way; adopt the reset run if it converges lower. Within ~0.1% Rwp prefer the physically valid shape, and never carry imaginary-Gaussian terms forward.

**(FI22) Export two files, with the fitting conditions recorded and the impurity areas fixed.** `*_impurity.inc` holds a drop-in `xo_Is` block per non-MAIN group (its TCHZ plus `load xo I { }`) for `#include` inside `xdd`; its header records the emission-profile macro, `Simple_Axial_Model` value, LP setting and 2-theta range, outside which the exported shape and areas are invalid. Write the areas fixed so they cannot absorb main-phase intensity in later stages; release them only in the final Rietveld. `*_peaks.json` carries every line (position, area, FWHM, `pv_lor`, group, tier, confidence), each group's TCHZ set, the wavelength and provenance.

### Reporting of peak fitting states

**(FI23) Produce a Rietveld-style overlay with one tick row per group, each in its own colour.** Plot `Out_X_Ycalc` of the final fit against the data with `scripts/plot_xy.py`; tick files are two-column `2theta intensity`, the `Create_2Th_Ip_file` format:

```
python scripts/plot_xy.py yobs.xy final_ycalc.xy --labels "Yobs,Ycalc" \
   --colors "blue,red" --diff "Yobs,Ycalc" \
   --ticks "MAIN|main.txt|#2e7d32,TREND2|t2.txt|#8a5ba6,MOPUP|mop.txt|#b5502f" \
   -o peakfit.html
```


## Part 2 - Indexing

### From peak fitting to indexing

**(IN1) Index the MAIN tier only, using the fitted positions.** Load the converged peak-fit 2-theta values of MAIN into `load index_th2 index_I { }` - never the peak-search estimates, which are limited to the data step - and only the low-angle subset of (IN2). Hold AMBIGUOUS lines back and test them against the cell once one is found (IN15). Leave any zero error to `index_zero_error`; do not pre-correct positions.

**(IN2) Index a finite low-angle subset, not every line.** Use the lowest-angle well-determined MAIN lines: about 20-30 for monoclinic or triclinic, fewer for higher symmetry (a cubic cell is fixed by ~8-10 lines). Low-angle lines are the least overlapped and carry the smallest indices; every added short d-spacing multiplies the calculated lines and brings in the least reliable positions - the TOPAS manual's most probable cause of indexing failure (`references/14-indexing.md`). Keep the rest to check the cell (IN15) and for the Pawley stage. Position accuracy matters more than count. Where too few lines exist for the cell's symmetry, widen the fitted range or re-mine residuals (FI8). The same floor applies to the IMPURITY tier: index it as a further phase only when it has enough lines to fix a cell on its own, otherwise report its lines as unindexed - an impurity cell from a handful of lines is not evidence of a second phase.

### Indexing setup

**(IN3) Run the unrestricted baseline first, but leave `Bravais_Triclinic_sgs` out of the first pass.** Use the correct `index_lam` (IN4), `seed`, `index_zero_error`, and the five non-triclinic macros: `Bravais_Cubic_sgs`, `Bravais_Trigonal_Hexagonal_sgs`, `Bravais_Tetragonal_sgs`, `Bravais_Orthorhombic_sgs`, `Bravais_Monoclinic_sgs`. Triclinic's six free parameters index many lists regardless of the true symmetry and crowd out higher-symmetry answers; add it back only once no non-triclinic system gives a reproducible, satisfactory, fully indexed candidate (`UNI`, the number of input lines a candidate leaves unindexed, is 0). Judge "satisfactory" on the GoF reached, not on `UNI=0` and reproducibility, which a wrong over-dense cell achieves easily (IN8). GoF has no fixed threshold and is not comparable between datasets. A best GoF in single figures calls for a closer check, not a verdict of failure: GoF also falls with line density (IN10), so a large or low-symmetry cell indexed from many lines can be correct at a single-figure GoF - settle it at the Pawley stage (IN19), where a fit explaining the whole pattern with no unexplained residual supports it. GoF is biased towards candidates with more reflections (IN8) and towards lower symmetry, whose extra parameters buy positional fit (IN17).

**(IN4) `index_lam` takes the Ka1 wavelength.** The peak fit models the full emission profile, so its positions are Ka1 positions. A weighted-average wavelength biases every cell edge by far more than the fit's positional precision.

**(IN5) Treat indexing as stochastic.** Retry intermittent failures 2-3 times before suspecting the input, and repeat difficult searches with different seeds; the same cell recurring is reassuring, while unrelated results mean indexing is probably failing. `tc.exe` can also crash intermittently on an indexing run, with no output; rerun it before changing the input.

**(IN6) Do not invent `x_scaler` or `x_angle_scaler` values.** `x_scaler` (below 1; larger values search more finely) defaults to cubic 0.99, hexagonal/trigonal and tetragonal 0.95, orthorhombic 0.89, monoclinic 0.85, triclinic 0.72. `x_angle_scaler` (default 0.1; smaller gives more angular steps) applies to monoclinic and triclinic. Change them only from a verified example.

### Interpreting candidates

**(IN7) Collapse the `.ndx` into lattice families with `scripts/group_cells.py` before choosing between candidates.** One lattice appears many times over (axis swaps, supplementary angles, with and without centring, slightly different refined values). `python scripts/group_cells.py result.ndx --top 20 --members` Niggli-reduces each row's primitive cell (centring from the space-group letter), groups rows related by an integer basis change within `--tol` (default 0.005 normalised metric difference, ~0.25% in length), and reports per family the member ranks, best GoF, lowest UNI, reduced cell, metric symmetry, and index-2 to -4 supercell relations to other families. **Compare families, never individual rows.** Few, often-recurring families mean a converged search; many one-off families mean the problem is upstream (IN13). Use the metric-symmetry column to catch metrically higher triclinic solutions (IN12) and the supercell list as input to (IN16). Optionally re-run at `--tol 0.01` and judge by hand families that merge only there. By default it reads only the best 300 rows by GoF (`--max-rows`), since grouping a full 3000-row `.ndx` can run for a very long time; `--top` limits printing only. Use `--all` only when a low-ranked row matters, and run it in the background. The script relates lattices but does not choose between them.

**(IN8) Read GoF together with UNI; `UNI>0` on an otherwise strong candidate is a question about the peak list, not the cell.** Scan the whole `.ndx`, not just rank 0, and choose on GoF within a crystal system. Do not filter on `UNI=0`, which is neither necessary nor sufficient: the number of reflections above `d_min` goes as ~(4*pi/3)*V/d_min^3, so `UNI=0` can favour whichever candidate has the most reflections to absorb a bad line. Density rises by enlarging the cell or by dropping centring at the same cell - a spurious `P` answer at the right dimensions is the same failure as a supercell. When a high-GoF candidate of smaller primitive volume is blocked by a few lines, find those lines in the peak fit first (FI19, IN15).

**(IN9) Group candidates by reduced lattice; primitive volume is a screen, not a proof.** Primitive volume is conventional volume over centring multiplicity (`P=1`, `A/B/C/I=2`, `F=4`, `R=3` for hexagonal axes only). Unrelated lattices can agree in primitive volume to within a fraction of a per cent; rows are the same lattice only when their Niggli-reduced cells map onto one another (IN7). Distinct lattices at equal primitive volume are metric re-descriptions, which need intensities - Pawley, Le Bail or structure solution - to separate.

**(IN10) Compute predicted in-range reflections per observed line, use it when selecting candidates, and report it for every candidate carried forward.** Unlike GoF it is comparable between datasets and is the quantitative guard against the over-dense cell. Near 2 is well constrained; above ~15 almost any list indexes and the figure carries no evidence. It also sets how many noise lines index by chance - roughly the number of suspect lines times the fraction of the 2-theta range within the matching tolerance of a calculated line - so a list that over-determines a cell at a low figure cannot be noise as a whole, though individual weak lines can still be chance hits.

**(IN11) When the user supplies a candidate cell or structure, search the whole `.ndx` for it,** allowing axis permutations and looking below rank 0. Its absence from the top of the list is not evidence against it.

**(IN12) Test both metric and supercell pseudosymmetry.** For a higher-symmetry metric, inspect sensitive peak splitting; if none is resolved, report the higher-symmetry cell but state that a lower-symmetry distortion is unresolved, naming any lower-symmetry candidate the `.ndx` holds on the identical metric (for example C-orthorhombic with a/b = √3 under a hexagonal answer). For an integer primitive-volume ratio, run the supercell test (IN16) rather than judging by eye. Log a pseudosymmetry or centring signal the moment it is noticed and resolve it before the final report.

**(IN13) Diagnose inconclusive searches in order.** A cell that indexes part of MAIN and leaves the rest as UNI lines is expected when MAIN holds two phases, but first check the UNI lines for superlattice reflections (IN16) and artefacts (IN15, FI19), and index leftovers separately only when there are enough to fix a cell (IN2). A recurring low-symmetry candidate with a modest GoF can reflect an unremoved impurity: re-read the width classification (FI12-FI17), remembering a width trend is not necessarily a phase (FI15). Treat a low GoF ceiling, mostly triclinic results or sentinel GoF values as prompts to check (IN3). Then: overlay `Out_X_Ycalc` on the data and confirm no MAIN line sits on an unfitted or mis-centred feature; retry with other seeds; re-index on the strongest low-angle lines; apply a justified restriction (IN14). If no candidate stands out (all GoF near 1), the positions themselves are untrustworthy and the strong-subset retry is mandatory: run two or three subset sizes - a cell that holds while GoF falls as lines are added marks the added lines as the unreliable ones.

**(IN14) Restrict the Bravais search only after the unrestricted baseline (IN3), and only on evidence.** Grounds are near-equal axes or special angles, recurring volume or cell relationships, near-tied same-cell candidates, a non-repeating low-symmetry swarm, or a disproportionate search-space count. A restriction narrows the search; it does not establish the cell.

**(IN15) After indexing, match each UNI line to the peak-fit `.out`, and check the indexed residuals.** Remove a line only when the fit independently shows it is an artefact, and only after checking it is not a superlattice reflection; test the held-back AMBIGUOUS lines (IN1) here too. In the per-solution `.ndx` table, look for a systematic trend in 2Tho-2Thc: a one-sided or angle-dependent drift points to a wrong cell or an uncorrected offset even when every line indexes. A constant offset is zero error, which `index_zero_error` absorbs; one varying as cos(theta) is sample displacement, which it does not absorb and which biases the cell.

### Superlattice protection

**(IN16) Test simple supercells before accepting any cell, and treat weak reflections as potentially decisive.** Thresholds, width screening and refinement can all remove superlattice reflections and leave a clean but undersized cell. Run `python scripts/compare_cells.py yobs.xy --lam wavelength --cell cell1 a b c al be ga --centering cell1 P --cell cell2 a2 b2 c2 al2 be2 ga2 --centering cell2 F` with doubled variants and, for centred candidates, the primitive and centred alternatives; this is mandatory for a suspiciously clean small cell or when any peaks were dropped. Observed reflections unique to the larger cell support it; absent ones do not prove the smaller cell. The script reads raw counts, so tails, Ka2 and impurity lines can give a false "decisive" verdict: check it on a Pawley baseline of the larger cell (IN19), comparing the superlattice reflections its space group allows with those it forbids (the noise floor) rather than pooling them. Run both every time; a false positive on one dataset is no reason to skip the script on the next. **Re-apply the test to the winner** until a halving stops being supported.

### Perform Pawley

The Pawley rules form one ladder: **(a)** per-candidate fits *screen* (IN17); **(b)** one shared "no absences" baseline, read by absence tabulation, is the *default decision* (IN19, IN20); **(c)** Bayesian extinction-symbol scoring is the *escalation* when (b) is close (IN23).

**(IN17) Step (a) - screen the best few non-equivalent candidates with per-candidate Pawley fits, including the best fully indexed candidate of every other crystal system.** Run it whenever more than one non-equivalent candidate survives and absences have not settled the choice. Do not let one high-GoF family crowd out the others: GoF is not comparable across systems, since a lower-symmetry cell out-scores a more constrained one on positional fit alone. Fit e.g. the best five, initially to about 60 degrees 2theta for Cu (or an equivalent moderate range), and compare overlap, residuals and Rwp; use the main topas-inp-writer skill for file construction. **Exclude any reflection outside the fitted range** - it carries no data and acts as an edge fudge. Ask the user first only when the work is heavy (wide range, many candidates, large dataset).

**(IN18) Start each Pawley fit from the peak fit's own shape and impurity model.** Take the MAIN group's TCHZ parameters from the converged peak fit, and `#include` the exported `*_impurity.inc` (FI22) inside `xdd`; otherwise impurity lines are absorbed into whichever candidate has a reflection nearby, rewarding the over-dense cell. Where no peak fit exists (a supplied `.ndx`), refine the shape on the baseline itself but keep it physical: an imaginary-Gaussian TCHZ (FI21) breaks every width-based step downstream.

**(IN19) Step (b) - decide on one shared "no absences" Pawley baseline. This is the default decision step.** Fit the primitive group carrying the full point symmetry of the lattice and no absences - P-1, P2/m, Pmmm, P4/mmm, P6/mmm (also for R lattices on hexagonal axes) or Pm-3m - so every candidate's absences, centring included, are read off one fit by the tabulation of (IN20). Prefer it to comparing Rwp across separately parameterised candidate fits: more allowed reflections improve Rwp mechanically even where the extra intensities refine to near zero, so Rwp ratchets towards too little symmetry. Run it even when the per-candidate fits are done, and report both when they disagree, with the reasoning.

**(IN20) Establish whether candidates differ in *which* positions are allowed or only in how intensity is *partitioned* among shared positions, then tabulate absences.** A Pawley fit sees only the total at each position, so it settles absence differences and is blind to partition-only ones: adding or removing a centre of symmetry (Friedel's law), obverse against reverse `R` settings (paired reflections coincide in d), and metric re-descriptions at equal primitive volume (IN9), such as hexagonal `P` against C-orthorhombic with `a = sqrt(3) b`. Report a partition-only difference as unresolved (IN25); a fewer-parameters criterion picks the wrong side. For an absence difference, tabulate on the shared baseline the fitted intensities of the reflections each candidate declares absent, within the fitted range, and require them all at noise level. Treat reflections whose intensities correlate by more than ~40% (`C_matrix_normalized`, a by-product of the `do_errors` the tabulation needs anyway) as one unit, clustering them by union-find: a unit tests a candidate only when every member is declared absent. A candidate with fewer reflections reaching a *lower* Rwp than the baseline means the baseline has not converged (usually unstable overlaps), not that the candidate is confirmed.

**(IN21) Choose the space group with the extinction-subgroup table in `references/14-indexing.md`, giving an answer with a caveat rather than hedging.** Groups are positionally indistinguishable only when they share an extinction row; do not infer it from similar symbols. Within a row, take the highest-symmetry member first and descend only if subsequent structure solution fails. A supergroup sharing a subgroup's absences may be missing from the search output, so its absence is not evidence against it; its standard setting may permute a/b/c. An empty diagnostic class bounds those intensities but does not establish the higher member - a slight distortion breaks the symmetry in proportion - so report the subgroup as not excluded and quote the bound. The choice between centric and acentric members of a row is partition-only (IN20); (IN22) gives a soft hint. Where two rows tie because no testable reflection separates them (all coincident, overlapped or out of range), report the more restrictive row - the one with more conditions, as TOPAS's extinction-subgroup ranking orders them - and say the choice is untested. Where the choice rests on one or two informative reflections, report the better-supported row and say an accidental absence would reverse it.

**(IN22) Use ⟨|E²−1|⟩ only as a soft hint between the centric and acentric members of an extinction row.** Compute it from independently determined Pawley intensities (correlation below ~20% with any other reflection), divided by multiplicity and LP and normalised in resolution shells: it is ~0.97 centric and ~0.74 acentric, so a value well below ~0.75 favours the acentric member. It needs ~20 such reflections, special positions distort it in small high-symmetry structures, and it never overrides other evidence.

**(IN23) Step (c) - escalate to Bayesian extinction-symbol scoring when step (b) leaves the symbol open.** A razor-thin margin in the tabulation is exactly this case. It is the ladder's one heavy step: ask the user before running it, but do not settle silently for step (b) either. For each candidate symbol, combine per-reflection closed-form log-probability ratios over the classes it predicts absent (Gaussian against Wilson-exponential likelihood of the fitted intensity, symbol against the no-absences baseline). Score each correlated unit of (IN20) on its summed intensity and esd, the esd floored at its largest member's. This is a simplified, independence-assuming version of Markvardsen, David, Johnson & Shankland (2001), *Acta Cryst.* A57, 47-54; build it fresh each time from the dataset's own reflection conditions (International Tables Vol. A, Table 3.2) and its own extinction-symbol enumeration. Distrust the ranking when many scores fall back to treating correlated reflections as independent (restricting to ~60 degrees helps), when a reflection-condition rule is incompletely derived, when several symbols tie exactly (no reflection distinguishes them), or when the top symbol contradicts an already robust conclusion such as the centring; then report the run as inconclusive. It does not diagnose a wrong axis setting of a correct space group.

### Reporting

**(IN24) Before reporting, spend one fixed pass trying to break the leader - especially when it looks right.** Attack it on overlooked centring or misleading `UNI` (IN8); subcell or supercell ambiguity (IN16, IN12); a higher member of the same extinction row or a non-standard setting (IN21); an equal-primitive-volume rival in another system (IN9, IN17); over-read GoF (IN3); calculated-against-observed drift or an uncorrected offset (IN15); and re-indexing on the strongest lines alone (IN13). Report the strongest argument for and against, the best alternative, anything worth reviving, a verdict with confidence, and what evidence is missing - recorded whether or not it changes the answer.

**(IN25) Report the cell, crystal system, unresolved alternatives, UNI status and the evidence that rejected competitors.** Give the cell and space group in the standard (International Tables) setting, with any literature or legacy setting alongside. State which groups share the extinction row, label the reported name as representative when it is not unique, and separate conclusions resting on positions from those needing intensities or structure solution; say what remains indeterminate and why. Report each candidate in one shape - rank, cell with GoF/UNI/zero, supporting and contradicting evidence, confidence - with M20 or F_N beside the TOPAS GoF for the reported cell and any close alternative; unlike GoF they are comparable across datasets.

**(IN26) Treat chemistry and identity as secondary evidence only.** Where a formula, permitted Z or expected density is supplied (by the user or the wizard's non-standard-instructions field), compute V/Z and the calculated density for each surviving candidate and compare; never invent them, never reject a diffraction-supported candidate on this alone, and when nothing is supplied skip the check without asking but record that it was not assessed, neither rewarding nor penalising any candidate. Filename, formula, mineral or refcode hints corroborate at most; they never replace peak, metric or extinction evidence, and database numbers are not space-group numbers.
