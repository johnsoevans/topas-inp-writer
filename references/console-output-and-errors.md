# Console Output and Real Error Messages

What TOPAS actually prints to the console/log during a run, taken from captured `tc.exe` sessions (TOPAS-64 Version 8.66, including a batch run of ~280 installation examples). Use it to recognize normal startup/progress output and genuine error messages rather than guessing at their wording.

Most installation examples have a paired `.out` file (205 of 283; resolve both via `python scripts/topas_install.py --example <path>`, once with `.inp` and once with `.out` — see SKILL.md's "Locating your TOPAS installation"). The `.out` is the INP rewritten with refined values: placeholder `0`s and starting values are replaced, each carrying its uncertainty after a backtick, e.g. `beq @ 0.19987`_0.00463`. Compare an example's `.inp` against its `.out` to see exactly what refining it changed.

## Startup sequence (every run)

```
TOPAS-64 Version 8.66 (c) 1992-2020 Alan A. Coelho
   Maximum number of threads 8
Loading c:\w\ta-web2\topas.inc
Time   0.00, INP file pre-processed
```

`topas.inc` (resolve via `python scripts/topas_install.py --inc-dir`) is loaded automatically before anything else. For structure-factor phases, lines like `Loading xyz's for p-1 from file ...\sg\p-1.sg` and `Loading atomic scattering factors from file atmscat.txt` follow — `atmscat.txt` (see `references/system-files-index.md`) is the file TOPAS reads for X-ray form factors.

Count lines commonly seen before iteration starts — `Num independent parameters`, `Num data files`, `Num peak-shape-objects`, `Num hkl_pk_dets`, `Num equiv posns for centrosymmetric ...` — are informational, not warnings.

## Rietveld/Pawley iteration log

```
  0  Time   0.01  Rwp   92.533    0.000 MC     0.00 0
Sparse matrix methods invoked - 66.6% of the A matrix elements are zero
  1  Time   0.02  Rwp   70.171  -22.362 MC     1.10 3
  2  Time   0.03  Rwp   39.709  -30.462 MC     1.39 1
```

Columns: iteration number, elapsed time (s), Rwp, change in Rwp from the previous iteration (negative = improving), an `MC` value (Marquardt constant — see the Levenberg–Marquardt summary in `paper-summaries.md`), and a trailing count. "Sparse matrix methods invoked - N% of the A matrix elements are zero" is informational, printed once when TOPAS decides sparse methods are worthwhile for the normal-equations matrix.

## Charge-flipping iteration log

```
  Iter    Time   R-fac  Scale     Del  %Flip  al-sum   Shift  Sym-Err    F000 %ED > H
     0     0.0   1.159  35.19    0.00  49.97   0.050  0  1  0   0.406   0.189  29.901
```

Columns: iteration, time, R-factor, Scale, Del, %Flip (percentage of charge flipped), al-sum, Shift, Sym-Err (three integers — symmetry-equivalent error counters), F000, and %ED > H (percentage of electron density above a threshold). A `Flip-R` column sometimes appears at the end depending on the charge-flipping variant (the installation's `cf/cf-ae9-poor.inp` shows it, `cf/cf-ae5.inp` doesn't).

On completion:
```
Best Fcalc saved to file c:\w\ta-web2\cf\ae5.Fc
Charge-flipping finished. Time: 0.34 seconds
```

## Simulated-annealing / cycle-based output

Files using cycle-based randomization (Monte Carlo/simulated annealing structure solution, `bootstrap_errors`, etc.) print a summary keyed on Cycle rather than plain Iter:
```
Cycle  N  T  X  Ti  Y  Best/Global  Z  Z
```
and a Chi2-tracking variant:
```
Iter Cycle Time T Ti Chi Best Scalar
```
Look for a `Cycle` column whenever the INP includes randomization/MC-style keywords.

## Indexing completion

Indexing runs print `Trying <spacegroup> <number>, Number of possibilities N` and `Time T Gof G Vol V Best B` progress lines. Successful runs also print the winning cell:
```
Volume: 925.92237 14.5195974 5.32623299 11.9729134 90 90 90
```
followed by `Trying to determine Extinction subgroup`, then the two output files:
```
c:\w\ta-web2\lp.log written to
File c:\w\ta-web2\...\name.ndx written to
```

## Completion banners and file I/O

```
File c:\w\ta-web2\cf\alvo4a.out updated
    with parameters from last iteration
```
is the default. With cycle/MC-based refinement, where the last iteration isn't necessarily the best one seen, it reads instead:
```
File X.out updated with parameters corresponding to best Rwp
File X.out updated with parameters corresponding to best Chi2
```
Rigid-body/restrained refinements additionally print `Bond lengths and angles calculated`, and errors, when calculated, are qualified:
```
Errors calculated
    without restraints/penalties included in A matrix
```
or `with restraints included in A matrix`.

CIF, FCF and NDX output follow a "written to" then "appended to" pattern when TOPAS writes a block then appends further blocks to the same file:
```
File X.cif written to.
File X.cif appended to.
File X.fcf written to.
File X.fcf appended to.
```
An in-INP shell command (via a `System(...)`-style macro call) is echoed verbatim before running, e.g. `System: copy alvo4a.inp alvo4a.backup`.

## `num_runs` and multi-run files

`num_runs #` re-runs the same INP # times with `tc.exe` staying resident in memory, using the reserved parameter `Run_Number` (0-indexed) to switch behavior between runs via `#if (Run_Number == 0) ... #elseif (Run_Number == 1) ... #endif` blocks — the mechanism behind the PDF-generation three-operation pipeline in `references/08-pdf-generation.md` and the `gr_to_fq` example. Each run is announced:
```
Suspending writing to log file after Run 0
Run: 1 -------------------
```
and only `Total time: 0.1693116` marks the end of the whole multi-run file.

`continue_after_convergence` is a different mechanism: it restarts refinement immediately after convergence within the *same* run, until `iters` (or `num_cycles`, one full convergence = one cycle) is reached — so an `.inp` with it and a large `iters`/`num_cycles` may run for a very long time by design. Before setting one up, see the bounded-run rule under "Running `tc.exe`" in SKILL.md.

## Phase auto-management

`remove-phase`-style INPs that drop insignificant phases during refinement print:
```
*** Deleting phase: Corundum ***
```
and, if a whole cycle removes nothing, terminate with:
```
No phases removed this Cycle, refinement terminated
```

## `approximate_A_check_must_be_zero`

Seen in a large XRD-CT (computed-tomography) example with thousands of data files:
```
approximate_A_check_must_be_zero On
...
approximate_A_check_must_be_zero: non-zero Aij elements now static
```
Printed mid-refinement once TOPAS has verified the sparsity assumption behind `approximate_A` and locked in the static (zero) elements — relevant when tuning performance on very large multi-pattern refinements (that example had ~150,000 unique hkl-sets across 2,000 data files).

## Error messages

Every unrecoverable error ends with `Abnormal program termination.` — a generic marker, not information about the cause; always read the line(s) immediately above it.

**`at LINE N`** counts lines in the macro-expanded file written to `tc.log`, not the raw `.inp`. The full rules for mapping it back to the source are in `references/macro-expansion-and-log-files.md`; `scripts/check_inp_syntax.py` reports plain editor line numbers, so treat its numbers as "look near here".

**Missing file** — a prerequisite output from an earlier stage (here an `.fc` structure-factor file) or an input data file:
```
 Cannot open file c:\w\ta-web2\cf\ae14-1.fc
 
Abnormal program termination.
```
```
 Cannot open file c:\w\ta-web2\test_examples\dispersion\disp.xy
 Cannot open file c:\w\ta-web2\test_examples\1000s-of-patterns\data.xdd
 Cannot open file c:\w\ta-web2\test_examples\ae14.hkl
 Cannot open file strs-200-2000.txt
```
Not necessarily a syntax error — check whether the `.inp` assumes a previous step already ran. With no directory prefix, the file is expected in the working directory. (`strs-200-2000.txt` is an example-set naming slip: the companion "create-sequences" step writes `sites-200-2000.txt`.)

**A valid keyword given an invalid parameter name:**
```
*** Error loading sstring_in
    at LINE 28
    See log file c:\w\ta-web2\tc.log
    Cannot locate iters_since_last_best from break_cycle_if_true in data structures
```
Names the reserved parameter it couldn't resolve (`iters_since_last_best`) and the keyword it was resolving it for (`break_cycle_if_true`). Check the spelling and that the parameter is valid for that keyword — cross-check `references/21-keyword-index.md` and the relevant chapter.

**An invalid keyword itself** (a typo, or a keyword from a different TOPAS version or scope):
```
*** Error loading sstring_in
    at { CF_Randomize_At } unknown or misplaced keyword.
    at LINE 44
```
Same shape for other bad keywords, e.g. `{ ycalc_out } unknown or misplaced keyword. at LINE 9`.

**Equation syntax error:**
```
*** Error loading sstring_in
    at LINE 3
    See log file c:\w\ta-web2\tc.log
    3. Equation error for V1~
```
The `N. Equation error for <name>` line names the offending equation/parameter reference — check that name's definition and any macro expansion feeding it.

**No matching macro overload:**
```
 Cannot find match for macro Beq
 Number of arguements 2
```
("arguements" is TOPAS's own spelling.) Several macros may share a name; TOPAS resolves them purely by argument count. This means no macro named `Beq` in scope takes 2 arguments — the call may be fine and the definition with that arity missing or not `#include`d. Find *every* `Beq` definition reachable from the INP (across all included `.inc` files) and check which arities exist.

**Solve-time failure with no line number** — the keyword parsed, but something it depends on doesn't resolve:
```
 Error in Sites_Geometry_Distance
```
```
 Cannot locate pk_to_Lam from top_prm_name_map in data structures
```
Both end in `Abnormal program termination.`

**Bare `Unhandled exception`**, with no message:
```
*** Warning: Atomic interaction, no S1 sites found
*** Warning: Atomic interaction, no S1 sites found
Unhandled exception
```
Treat it as a genuine crash (likely a bug or unsupported combination) rather than a fixable INP mistake. If a warning immediately precedes it, the warning is probably the root cause (here a site search that found nothing, then used anyway).

## Common warnings (not fatal)

```
*** Warning; Site 2 of phase Foo has one of its equivalent positions at a distance of 0 Angstroms
    Recurring fractional atomic coordinates such as 0.3333 should be entered as x = 1/3;
```
Very common: a recurring decimal (0.3333, 0.6667, …) entered as a literal rather than as `x = 1/3;`. The same warning appears with a small nonzero distance (e.g. `0.1697 Angstroms`) when the coordinate is merely imprecise.

```
*** Parameter(s) close to limit(s).
    Check for LIMIT_MIN and LIMIT_MAX
```
A refined parameter has hit (or nearly hit) a `min`/`max` bound — check its bounds; not necessarily a model error.

```
*** Errors cannot be calculated when approximate_A is ON.
    Try the Bootstrap method or remove approximate_A.
```
and, for penalties-only refinements, `Errors cannot be calculated for penalties only`. Both explain why `do_errors` output is skipped in those modes.

## Version 9: modulated structures and electron diffraction

Each of the two Version 9 chapters ends with a table of the messages a user will meet, taken from the Version 9 program: "Messages a user will meet" in `references/30-modulated-structures.md` and in `references/31-electron-diffraction.md`. Quote the user's message against those tables first.

The electron diffraction load lines look like nothing else in TOPAS (`qtz-dyn-0.inp` with `iters 0`):

```
ED: 17557 hkls in half of reciprocal space to |g| 4.2 for the structure factors
ED frame 1: 21 of 73 reflections (dropped: |g| > ed_g_max 0, D_Sg 49, S_g 0, R_Sg 3, |g| > 2.1 ed_g_max 0), 68 beams, 340 structure factors
   negative intensities set to zero: 4
...
ED crystal 1: ed_num_integration_steps_auto 28
  0  Time   1.79  Rwp   13.333    0.000 MC     0.00 0
```

`31-electron-diffraction.md` § "Beams and reflections, and what the console shows" explains each field.
