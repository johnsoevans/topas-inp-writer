# Console Output and Real Error Messages

This file documents what TOPAS actually prints to the console/log during a run, taken from a real captured session (`tc.exe`, TOPAS-64 Version 8.66) running several files from `references/examples/cf/`. Use this to recognize what normal startup/progress output looks like, and to recognize genuine error messages rather than guessing at their wording.

Every `.inp` file also has a paired `.out` file alongside it (available for 205 of the 283 examples; resolve both via `python3 scripts/topas_install.py --example <path>`, once with the `.inp` extension and once with `.out` — see SKILL.md's "Locating your TOPAS installation") — the `.out` file is what TOPAS writes back into the INP file itself: placeholder `0`s and un-annotated starting values get replaced with refined values, each carrying its uncertainty via a trailing backtick, e.g. `beq @ 0.19987`_0.00463`. Compare an example's `.inp` against its `.out` to see exactly what refining it changed.

## Startup sequence (every run)

```
TOPAS-64 Version 8.66 (c) 1992-2020 Alan A. Coelho
   Maximum number of threads 8
Loading c:\w\ta-web2\topas.inc
Time   0.00, INP file pre-processed
```

`topas.inc` (resolve via `python3 scripts/topas_install.py --inc-dir`) is loaded automatically before anything else, confirming the manual's description of it as the default macro library. For structure-factor phases, lines like `Loading xyz's for p-1 from file ...\sg\p-1.sg` and `Loading atomic scattering factors from file atmscat.txt` follow — the latter confirms `atmscat.txt` (described in `references/system-files-index.md`) is exactly the file TOPAS reads for X-ray form factors.

Diagnostic count lines commonly seen before iteration starts: `Num independent parameters`, `Num data files`, `Num peak-shape-objects`, `Num hkl_pk_dets`, `Num equiv posns for centrosymmetric ...`. These are informational, not warnings.

## Rietveld/Pawley iteration log

```
  0  Time   0.01  Rwp   92.533    0.000 MC     0.00 0
Sparse matrix methods invoked - 66.6% of the A matrix elements are zero
  1  Time   0.02  Rwp   70.171  -22.362 MC     1.10 3
  2  Time   0.03  Rwp   39.709  -30.462 MC     1.39 1
```

Columns: iteration number, elapsed time (s), Rwp, change in Rwp from the previous iteration (negative = improving), an `MC` value (Marquardt constant — see the Levenberg–Marquardt summary in `paper-summaries.md`), and a trailing count. "Sparse matrix methods invoked - N% of the A matrix elements are zero" is informational, printed once when TOPAS decides sparse methods are worthwhile for the normal-equations matrix — not an error.

On successful completion:
```
File c:\w\ta-web2\cf\alvo4a.out updated
    with parameters from last iteration
```

## Charge-flipping iteration log

Charge flipping has its own distinct column layout, quite different from Rietveld/Pawley refinement:

```
  Iter    Time   R-fac  Scale     Del  %Flip  al-sum   Shift  Sym-Err    F000 %ED > H
     0     0.0   1.159  35.19    0.00  49.97   0.050  0  1  0   0.406   0.189  29.901
```

Columns: iteration, time, R-factor, Scale, Del, %Flip (percentage of charge flipped), al-sum, Shift, Sym-Err (three integers — symmetry-equivalent error counters), F000, and %ED > H (percentage of electron density above a threshold). A `Flip-R` column sometimes also appears at the end depending on the exact charge-flipping variant in use (compare `references/examples/cf/cf-ae5.inp` vs `references/examples/cf/cf-ae9-poor.inp`'s console output — the ae9-poor run includes it, ae5 doesn't).

On completion:
```
Best Fcalc saved to file c:\w\ta-web2\cf\ae5.Fc
Charge-flipping finished. Time: 0.34 seconds
```

## Real error messages seen

**Missing dependent file**, when an `.inp` references a file (here an `.fc` structure-factor file from a previous run) that doesn't exist yet:
```
 Cannot open file c:\w\ta-web2\cf\ae14-1.fc
 
Abnormal program termination.
```
This is not necessarily a syntax error in the INP — it can simply mean a prerequisite file (from an earlier stage/run) hasn't been generated yet. Check whether the `.inp` assumes a previous step already ran.

**Reference to a keyword/parameter that isn't a valid target in this context**:
```
*** Error loading sstring_in
    at LINE 28
    See log file c:\w\ta-web2\tc.log
    Cannot locate iters_since_last_best from break_cycle_if_true in data structures
```
TOPAS reports the exact line number in the INP file and names the specific reserved parameter it couldn't resolve (`iters_since_last_best`) and the keyword context it was trying to resolve it for (`break_cycle_if_true`). When debugging a similar error, check that the reserved parameter name is spelled correctly and is actually valid for the keyword it's being used with — cross-check against `references/21-keyword-index.md` and the relevant chapter.

Both errors end with `Abnormal program termination.` — this is the generic marker for any unrecoverable error, not specific information about the cause; always look at the line(s) immediately above it for the actual reason.

**A note on TOPAS's own `at LINE N` numbering.** TOPAS's `at LINE N` refers to a line number in the macro-expanded form of the file (what's written to `tc.log`), not the raw `.inp` as seen in a text editor — this was originally inferred by cross-checking `sites_geometry_1.inp`'s reported `at LINE 9` against its physical file (a 7-line block comment early in the file accounts for the offset), and has since been directly confirmed by diffing real `tc.log` output against source. **See `references/macro-expansion-and-log-files.md` for the full, precisely-confirmed set of expansion/line-numbering rules** (block comments collapse to exactly 1 line; `#ifdef`/`#else`/`#endif` untaken branches vanish with zero placeholder lines while the bounding directives each keep 1; runtime `if {} else {}` is never pruned; macro definitions collapse to 1 line; macro argument substitution and `@`-parameter auto-naming mechanics). `scripts/check_inp_syntax.py` reports plain physical line numbers (matching a text editor), not TOPAS's internal count — treat its numbers as "look near here," not an exact match to TOPAS's own `at LINE N` output.

## `num_runs` and multi-run INP files

Some `.inp` files define `num_runs #`. This re-runs the same INP file # times with `tc.exe` staying resident in memory between runs (rather than restarting the process), using the reserved parameter `Run_Number` (0-indexed) to switch behavior between runs via `#if (Run_Number == 0) ... #elseif (Run_Number == 1) ... #endif` blocks — this is the mechanism behind the PDF-generation three-operation pipeline in `references/08-pdf-generation.md` and the `gr_to_fq` example. `continue_after_convergence` is a different, unrelated mechanism: it restarts refinement immediately after convergence within the *same* run, and keeps doing so until `iters` (or `num_cycles`, one full convergence = one cycle) is reached — so an `.inp` with `continue_after_convergence` and a large `iters`/`num_cycles` value may run for a very long time by design, not because anything is wrong.

## Update: patterns confirmed from a full 19,000-line batch log (`aac.txt`)

The section below was added after the user supplied the complete console output of a single batch run (`aac.bat`) that exercised roughly 280 `.inp` files across `cf/`, `cf-protein/`, `indexing/`, `rigid/`, and ~30 subfolders of `test_examples/`. It confirms the patterns above and adds many real formats/errors not seen in the smaller sample.

### More real error messages

**Unknown or misplaced keyword** (a keyword that doesn't exist, or is used in a scope where it isn't valid):
```
*** Error loading sstring_in
    at { CF_Randomize_At } unknown or misplaced keyword.
    at LINE 44
```
Same shape seen for other bad keywords, e.g. `{ ycalc_out } unknown or misplaced keyword. at LINE 9`. Distinguish this from the `Cannot locate X from Y in data structures` error (previous section) — that one is a *valid* keyword given an *invalid parameter name*; this one is an *invalid keyword itself* (typo, or a keyword from a different TOPAS version/context).

**Equation syntax error**, reported with the specific bad reference:
```
*** Error loading sstring_in
    at LINE 3
    See log file c:\w\ta-web2\tc.log
    3. Equation error for V1~
```
The `N. Equation error for <name>` line names the offending equation/parameter reference — check that name's definition and any macro expansion feeding it.

**No matching overload for a macro**:
```
 Cannot find match for macro Beq
 Number of arguements 2
```
(Note: "arguements" is TOPAS's own spelling, not a transcription typo.) Important: TOPAS allows several distinct macros to share the same name — overload resolution is done purely by matching the number of arguments at the call site, not by argument type or name. This error means none of the macros named `Beq` in scope accept a call with 2 arguments; it does not necessarily mean the call site is wrong, it can just as easily mean the macro definition with that arity is missing or hasn't been `#include`d (e.g. a `_create`-suffixed variant of an example calls a differently-aritied `Beq` than the one pulled in by its `#include`s). When debugging, find *every* macro definition named `Beq` reachable from the INP (across all included `.inc` files) and check which arg-counts are actually defined, rather than assuming there's only one `Beq` to compare against.

**Geometry/derived-parameter failure with no line number**, a plainer error shape than the ones above:
```
 Error in Sites_Geometry_Distance
```
and, from a different data-structure lookup:
```
 Cannot locate pk_to_Lam from top_prm_name_map in data structures
```
Both still end in `Abnormal program termination.`. These read as "the keyword parsed fine, but something it depends on at solve-time doesn't exist/doesn't resolve" — different from a pure parse-time error.

**Bare `Unhandled exception`** — no accompanying message at all. Seen after a preceding warning in one case:
```
*** Warning: Atomic interaction, no S1 sites found
*** Warning: Atomic interaction, no S1 sites found
Unhandled exception
```
Treat a bare `Unhandled exception` as a genuine crash (likely a bug or an unsupported combination) rather than a fixable INP mistake — if a warning immediately precedes it, the warning is probably the root cause (e.g. a site-search that found nothing then got used anyway).

**Missing input data file** (as opposed to a missing prerequisite `.fc`/output file) — same "Cannot open file" wording, just naming a `.xy`/`.xdd`/`.hkl`/`.txt` data file instead:
```
 Cannot open file c:\w\ta-web2\test_examples\dispersion\disp.xy
 Cannot open file c:\w\ta-web2\test_examples\stretch-pks\data.xy
 Cannot open file c:\w\ta-web2\test_examples\1000s-of-patterns\data.xdd
 Cannot open file c:\w\ta-web2\test_examples\ae14.hkl
```
And occasionally with no directory prefix at all when the missing file is expected in the working directory:
```
 Cannot open file strs-200-2000.txt
```
(this one is a naming/order mismatch — the companion "create-sequences" step actually writes `sites-200-2000.txt`, not `strs-...`; worth flagging as an example-set inconsistency rather than a general TOPAS behavior.)

### Common warnings (not fatal)

```
*** Warning; Site 2 of phase Foo has one of its equivalent positions at a distance of 0 Angstroms
    Recurring fractional atomic coordinates such as 0.3333 should be entered as x = 1/3;
```
Extremely common across the example set — printed whenever a symmetry-equivalent-position calculation lands on a coordinate that's a recurring decimal (0.3333, 0.6667, etc.) entered as a literal rather than a fraction/equation. Not an error; TOPAS is suggesting `x = 1/3;`-style equations instead of typed-in decimals for exactness. The same warning appears with a small nonzero distance (e.g. `0.1697 Angstroms`) when the coordinate is merely imprecise rather than exactly recurring.

```
*** Parameter(s) close to limit(s).
    Check for LIMIT_MIN and LIMIT_MAX
```
Printed after refinement whenever a refined parameter has hit (or nearly hit) a `min`/`max` bound — check the parameter's bounds, not necessarily an error in the model.

```
*** Errors cannot be calculated when approximate_A is ON.
    Try the Bootstrap method or remove approximate_A.
```
and, separately, for penalties-only refinements:
```
Errors cannot be calculated for penalties only
```
Both explain why `do_errors`/error columns are silently skipped in certain refinement modes rather than being a bug.

### `num_runs` banner text (confirmed verbatim)

```
Suspending writing to log file after Run 0
Run: 1 -------------------
```
...repeating per run, and at the very end of the whole INP (all runs complete):
```
Total time: 0.1693116
```
This confirms `Run_Number` increments silently between banners and only `Total time:` marks the very end of a multi-run file.

### Simulated-annealing / cycle-based output (distinct from the plain iteration log)

Files using cycle-based randomization (Monte Carlo/simulated annealing structure solution, `bootstrap_errors`, etc.) print a different summary table keyed on Cycle rather than plain Iter:
```
Cycle  N  T  X  Ti  Y  Best/Global  Z  Z
```
and a Chi2-tracking variant:
```
Iter Cycle Time T Ti Chi Best Scalar
```
Look for a `Cycle` column whenever the INP includes randomization/MC-style keywords — the log shape changes accordingly.

### Structure/phase auto-management

`remove-phase`-style INPs that automatically drop insignificant phases during refinement print:
```
*** Deleting phase: Corundum ***
```
and, if a whole cycle removes nothing, terminate with:
```
No phases removed this Cycle, refinement terminated
```

### Indexing (`Lp-Search`) completion detail

Beyond the `Trying <spacegroup> <number>, Number of possibilities N` / `Time T Gof G Vol V Best B` lines already documented, successful runs also print the winning cell directly:
```
Volume: 925.92237 14.5195974 5.32623299 11.9729134 90 90 90
```
followed by `Trying to determine Extinction subgroup`, then the two output files:
```
c:\w\ta-web2\lp.log written to
File c:\w\ta-web2\...\name.ndx written to
```

### Completion-banner variants

`File X.out updated with parameters from last iteration` is the default, but two other variants appear depending on refinement mode:
```
File X.out updated with parameters corresponding to best Rwp
File X.out updated with parameters corresponding to best Chi2
```
(best-Rwp/best-Chi2 saving happens with cycle/MC-based refinement, where the "last" iteration isn't necessarily the best one seen). Rigid-body/restrained refinements additionally print:
```
Bond lengths and angles calculated
```
and errors, when calculated, are qualified:
```
Errors calculated
    without restraints/penalties included in A matrix
```
or `with restraints included in A matrix`.

### File I/O confirmations

CIF, FCF, and NDX output all follow a two-line "written to" then "appended to" pattern when TOPAS writes a block then appends further blocks to the same file:
```
File X.cif written to.
File X.cif appended to.
File X.fcf written to.
File X.fcf appended to.
```
An in-INP shell command (via a `System(...)`-style macro call) is also echoed to the console verbatim before running, e.g.:
```
System: copy alvo4a.inp alvo4a.backup
```
— confirms that macro-driven OS commands are logged, not silent.

### `approximate_A_check_must_be_zero` (new keyword, not previously documented)

Seen in a large XRD-CT (computed-tomography) example with thousands of data files:
```
approximate_A_check_must_be_zero On
...
approximate_A_check_must_be_zero: non-zero Aij elements now static
```
Prints mid-refinement once TOPAS has verified the sparsity assumption behind `approximate_A` and locked in the static (zero) elements — relevant when tuning performance on very large multi-pattern refinements (this example had ~150,000 unique hkl-sets across 2,000 data files).

### Practical takeaway on "are the .out/console files helpful for learning?"

Yes — very much so. The batch log confirms the manual-derived documentation was accurate for the common paths, but it also surfaced roughly a dozen genuinely new error/warning shapes (above) that don't appear anywhere in the Technical Reference text, plus a genuine dependency-ordering slip in the example set (`.fc`/data-file naming mismatch in stacking-faults) and a couple of `Unhandled exception` crashes worth flagging separately as possible TOPAS bugs rather than INP-writing mistakes — the macro-overload-not-found case turned out to be expected TOPAS behavior (same-named macros are resolved by argument count) rather than an example-set bug. Real execution logs catch exactly the class of error that reading the manual alone cannot: keyword typos, argument-count mismatches, and missing-file dependency ordering.
