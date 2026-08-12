---
name: topas-inp-writer
description: Write, edit, and debug TOPAS-Academic (Bruker AXS) .inp refinement scripts for X-ray/neutron powder diffraction, PDF, indexing, charge-flipping, and stacking-fault analysis. Use this skill whenever the user mentions TOPAS, a .inp file, Rietveld/Pawley/Le Bail refinement, structure/PDF/quantitative-phase refinement scripting, or pastes TOPAS syntax (site, str, hkl_Is, xdd, prm, macro, Rwp, beq, occ, etc.) and wants it written, explained, fixed, or extended. Make sure to trigger this even if the user only pastes a fragment of TOPAS syntax or an error message without explicitly naming "TOPAS" or "INP file" — recognizable keywords or diffraction-refinement context are enough.
---

# TOPAS INP Writer

TOPAS-Academic is Bruker's diffraction-analysis program. Its input language (the "INP" format) is a macro-driven scripting language for describing samples, refinement objects, and equations, built on nested `{ }` blocks of keyword/value pairs. This skill packages the TOPAS Technical Reference Manual as a set of reference files so you can write correct, idiomatic INP syntax and debug existing scripts without guessing at keyword names or semantics.

This skill was distilled from a full copy of the Technical Reference; it captures the syntax rules and worked examples faithfully, but the reference files are prose-extracted from the manual, so equations that were originally typeset (e.g. as embedded math objects) may render as plain text approximations. When precision matters (e.g. an exact functional form), say so and flag the uncertainty rather than presenting it as verbatim manual text.

**Running the scripts:** examples are written `python scripts/…` and need Python 3, but don't assume any one launcher exists on this machine. Settle it once at the start of a session and reuse the answer: run `python --version`; if that doesn't print a `Python 3.x` line, try `py`, then `python3`. A bare `python`/`python3` on Windows that prints no version line is a Microsoft Store execution alias rather than an interpreter — skip it instead of running scripts through it. Where more than one launcher works they may point at different point releases; any Python 3 is fine, so keep the one that answered first.

## How to use this skill

1. **Identify what the user is actually trying to do** before writing anything — the same keyword can behave differently depending on which data structure (`str`, `hkl_Is`, `xdd_Is`, Pawley, indexing, PDF) it's used in. When starting a brand-new `.inp` from scratch (no existing file to extend) and the run type isn't already obvious from context, ask — see "Starting a new INP file from scratch" below.
2. **Check `example_inp_files/example_inp_files_index.md` first** — hand-picked, heavily commented working `.inp` files, a better style/structure model than a bare syntax demo. If nothing fits, fall back to `references/examples-index.md` and resolve the real file via `TOPAS_DIR` (see "Locating your TOPAS installation"); the skill bundles the index, not those example files. A real worked example almost always beats writing from scratch — copy its structure, adapt names/values/macros. To read one: `python scripts/topas_install.py --example <path-from-the-index>` (e.g. `cf/alvo4a.inp`) prints its location on disk, which you open with `Read`/`Grep`. Most (198 of 280) have a matching `.out` alongside — read both to see what refining changes: placeholders become refined values, each with a trailing-backtick uncertainty (`beq @ 0.19987`_0.00463`). If `TOPAS_DIR` isn't set or the file doesn't resolve, say so plainly rather than inventing content.
3. **Read the relevant manual reference file(s) for the syntax rules themselves** — don't rely on general crystallography knowledge for TOPAS-specific keyword names, attribute lists, or macro behavior. Only open the file(s) that match the task instead of reading everything.
4. **Combine both sources**: the manual chapters explain *why* and the exact rules; the worked examples show *how it looks in a real, working file*. Cross-check a worked example against the manual when something in it looks unfamiliar.
5. **When debugging**, check the common-errors checklist near the end of this file first, then consult `references/01-syntax-and-parameters.md` and `references/02-equation-operators-and-functions.md`, and look for a similar worked example to compare against.
6. **State uncertainty plainly** rather than presenting a guess as documented behavior — this applies throughout (see also "When something isn't in the references").
7. **Before handing over a finished or edited `.inp` file, run it through `scripts/check_inp_syntax.py`** — it catches unbalanced braces/parens, missing-semicolon equations, and keyword typos mechanically, cheaper and more reliable than eyeballing a long file.
8. **When summarizing or reviewing an `.inp`/`.out` file, actively flag `CS_L`/`CS_G` (`csl`/`csg`) values larger than roughly 500** — confirmed directly by TOPAS-Academic's author: `FWHM ∝ 1/value` for both macros, so sensitivity to the true crystallite size fades rapidly past that point, often showing up as a large refined error and a strong `csl`↔`csg` anti-correlation in `C_matrix_normalized`. See `references/04-peak-generation-and-peak-type.md` § "CS_L / CS_G: FWHM is proportional to 1/value".

## Starting a new INP file from scratch — clarifying questions

Use this question set whenever a person asks for a brand-new `.inp` file (no existing file to extend/fix) and the run type isn't already clear from what they've said. Lead with the top-level branch (use `AskUserQuestion` if available); only ask the follow-ups for the branch they pick.

**1. What kind of run is this?**

| Answer | Covers | Primary reference(s) |
|---|---|---|
| Rietveld refinement (known structure) | Refine atomic coordinates/occupancies/ADPs against a known model | `01`, `03`, `04`, `05` |
| Pawley / Le Bail (cell known, structure unknown or intensity-only) | Extract intensities with only cell+symmetry, no atom positions | `01`, `04` (`hkl_Is`/`xdd_Is` vs `str`) |
| Indexing (cell unknown) | Determine the unit cell from peak positions | `14` |
| PDF — generation | Convert raw reciprocal-space data into G(r) | `08` |
| PDF — refinement | Refine a structure against G(r) you already have | `09` |
| Charge flipping / ab initio structure solution | Solve an unknown structure from single-crystal or powder data, no starting model | `22` |
| Quantitative phase analysis | Weight fractions across multiple known phases | `11` (usually layered onto a Rietveld fit) |
| Stacking faults | Layer/fault-sequence modeling | `10` |
| Rigid bodies | Molecular/ionic fragments moved as a unit | `13` (layered onto Rietveld or PDF) |
| Deconvolution | Separate instrumental broadening from sample broadening | `07` |
| Energy minimization / molecular dynamics | Structure optimization by potential energy, not diffraction data | `15`, `16` |
| Protein refinement | Charge-flipping or Rietveld at protein scale | `18`, `19` |
| Magnetic structure refinement | Magnetic scattering/ordering | `12` |

If the answer spans two of these (e.g. "index this pattern, then Rietveld-refine the result" or "generate a PDF then refine a structure against it"), plan for a multi-stage pipeline rather than picking one branch and dropping the rest (see the peak-search → peak-fit → indexing pipeline below, or the combined `Include_PDF_Generate` template in `08`/`09`).

**2. Follow-ups by branch:**

- **Rietveld:** Structure already known (CIF, or space group + atom list), or does it need to come from elsewhere first? Single phase or multi-phase? Data source — lab X-ray (which tube), synchrotron, or neutron (CW or TOF, which changes the peak-shape macro family, see `04`)? Full fundamental-parameters instrument description (`axial_conv`, `Radius`, `Slit_Width`, `LP_Factor`) or a simpler empirical peak shape (`TCHZ_Peak_Type`, plain PV)? Anything beyond a plain fit — preferred orientation, anisotropic broadening, rigid bodies, an amorphous background? `do_errors` on?
- **Pawley/Le Bail:** Starting lattice parameters and space group — from indexing, literature, or a rough estimate to refine?
- **Indexing:** Existing peak list, or does a peak search need to happen first (see the peak-picking pipeline below)? Prior knowledge to seed the search — max d-spacing, minimum lattice parameter, crystal system?
- **PDF (either branch):** Real-space r-range and Q_max? Lab or synchrotron/neutron source (affects `dQ_damping`/`convolute_Qmax_Sinc` need)? For refinement: `beq`/`pdf_for_pairs`-based broadening, or ADPs?
- **Charge flipping:** Single-crystal or powder data? Space group known or being determined too? Protein-scale?
- **Quant:** Which phases, layered onto an existing Rietveld fit or built fresh alongside it?
- **Stacking faults:** Layer types/count; testing a specific fault probability/sequence, or searching for one?

**3. Common to nearly every branch, ask once the type is settled:** data file path/format, radiation/wavelength if not already implied, output needs (`do_errors`, CIF/pdCIF, plots).

## Locating your TOPAS installation

This skill does not bundle copies of the `.inc`/`.txt` system files or the worked example `.inp`/`.out` files — those ship with every TOPAS release, and a bundled copy would go stale relative to the real install.

**Set the `TOPAS_DIR` environment variable to the root of your TOPAS installation** (wherever `tc.exe`/`TA.EXE` live, or any ancestor directory). `scripts/topas_install.py` searches under it to resolve:

```
python scripts/topas_install.py --inc-dir                  # the real .inc macro library directory
python scripts/topas_install.py --example cf/alvo4a.inp    # a specific example file's real path
python scripts/topas_install.py --kernel-schema-html        # the pre-rendered "Show Schema" page
python scripts/topas_install.py --macro-browser-html        # a generated macro-browser page, if one exists yet
python scripts/topas_install.py --technical-reference-pdf   # the manual PDF (used for §21.2 macro descriptions)
python scripts/topas_install.py --keyword-tree-html         # a generated keyword-hierarchy page, if one exists yet
```

**Running `tc.exe`:** invoke it as `<TOPAS_DIR>\tc.exe "<full path to the .inp>"` — both absolute. `tc.exe` is not on `PATH`, and it resolves a relative `.inp` (and any relative `xdd`/`#include` inside it) against the current working directory, not the file's own location.

`check_inp_syntax.py` and `expand_inp_macros.py` both call this automatically and print a one-line note to stderr confirming they found your install. **Don't pre-check `TOPAS_DIR` yourself (e.g. `echo $TOPAS_DIR`) before starting work — this note *is* the check.** Call the real tool you need first; only raise `TOPAS_DIR` status if a script actually reports it missing. The walk is cached per process only — there is no on-disk cache, so each shell-out re-walks `TOPAS_DIR`. It's fast enough not to plan around.

**Without `TOPAS_DIR` set**, four things degrade cleanly rather than silently: `check_inp_syntax.py`'s macro-arity check (its other checks are unaffected); `expand_inp_macros.py`'s expansion of library macros (macros defined in the file itself still expand); reading the literal content of a worked example (the index's topic descriptions remain available, just not the source to copy from); "Show Schema" (no bundled fallback at all). If a colleague doesn't have `TOPAS_DIR` set, tell them plainly what it unlocks rather than guessing at file contents.

## Reference file map

Open only what's relevant to the current task.

**Core syntax — read first for almost any INP-writing task:**
- `references/01-syntax-and-parameters.md` — parameter naming/refinement flags (`@`, `!`), `prm`/`local`, attributes (`min`, `max`, `del`, `update`, `stop_when`, `val_on_continue`), constraints and equations. Foundation of the whole language.
- `references/02-equation-operators-and-functions.md` — operators and built-in functions usable inside `= ... ;` equations.
- `references/06-macros-and-include-files.md` — how to define and use `macro`, `#include`, and `.inc` files.

**Refinement mechanics:**
- `references/03-minimization-and-convergence.md` — least-squares minimization, convergence criteria, `iters`, `num_cycles`, refinement stability.
- `references/04-peak-generation-and-peak-type.md` — how peaks are built: emission profiles, `peak_type` (FP, PV, SPVII, SPV, TCHZ), convolutions, the peaks buffer.
- `references/05-reusing-objects-large-refinements.md` — techniques for large/multi-phase refinements without duplicating objects.

**Specialized refinement types (open only the one matching the task):**
- `references/07-deconvolution.md`
- `references/08-pdf-generation.md` and `references/09-pdf-refinement.md` — pair distribution function work, ADP_5/ADP_7 beq-type sites. Two distinct entry points:
  - **Generating G(r) from raw reciprocal-space data** is the `Include_PDF_Generate` three-operation pipeline in `08` (operation 0 = fit the raw pattern, operation 1 = generate F(Q)/G(r)). Worked examples: `pdf-generate/*/decon.inp`.
  - **Refining a structure against G(r) you already have** is described in `09` using the `pdf_data` keyword directly on an xy/G(r) file — no `Include_PDF_Generate` needed. Worked examples: `pdf/beq-2.inp`, `pdf-1.inp`, `pdf-2.inp`.
  - The two aren't mutually exclusive: a single INP file (e.g. `pdf-generate/LiFePO4/decon.inp`) can do both via operations 0/1 then 2.
- `references/10-stacking-faults.md` — `layer`, `stack`, `generate_stack_sequences`, transition matrices.
- `references/11-quantitative-analysis.md` — QUANT, weight percents, `dummy_str`, elemental composition.
- `references/12-magnetic-structure-refinement.md`
- `references/13-rigid-bodies.md`
- `references/14-indexing.md`
- `references/15-energy-minimization.md` and `references/16-molecular-dynamics.md`
- `references/17-amazon-ec2-cloud-computing.md` — running TOPAS on AWS.
- `references/18-protein-refinement.md` and `references/19-solving-proteins-atomic-resolution.md`
- `references/22-charge-flipping.md`
- `references/25-symmetry-mode-refinement.md` — distortion-mode/symmetry-mode refinement for symmetry-lowering phase transitions (ISODISTORT-generated `.STR` code, mode amplitudes as order parameters, GA/inclusion-run/exhaustive-search techniques). Not in the Technical Reference manual — sourced from draft chapters of Dinnebier/Leineweber/Evans (2018).
- `references/26-parametric-and-sequential-refinement.md` — analyzing a whole series of patterns (variable-temperature/pressure/time): sequential refinement (each pattern independent, previous run's values as next run's start) vs. parametric/"surface" refinement (one smooth functional form's coefficients refined jointly from every pattern). Covers `#list`/`Run_Number` mechanics, the disappearing-phase failure mode and its fixes, Table-12.1-style functional forms, the R-factor-comparison diagnostic for a bad parametric model, and refining non-crystallographic parameters no single pattern could determine alone.
- `references/27-rietveld-workflow-conventions.md` — **read this for any Rietveld/Pawley/Quantitative session, and always before writing a final report.** Practical strategy conventions from real refinement sessions, not manual syntax: wavelength/monochromator handling, the four peak-shape families and how they pair with wavelength macros and `Simple_Axial_Model()`, 2-theta range and ADP strategy, staged-refinement sequencing, saturated peak-shape terms, a mandatory false-minimum re-check before finalizing any correlated peak shape, the Pawley-from-converged-`str` recipe, mandatory final-report formatting, and a quantitative-phase-analysis section (ADP exceptions, phase screening/elimination, `weight_percent`/`elemental_composition`, the final pie chart). **Every rule carries a stable citable tag** (`(R1)`, `(R2)`, …) in one increasing sequence, so a rule can be referenced or superseded precisely later — see that file's own intro. **Never cite a rule number outside that file** — not in `SKILL.md`, other `references/*.md`, `scripts/*.py`, `example_inp_files/` or `test_examples/` — since it renumbers independently and any number written elsewhere goes stale silently; refer to the rule by topic and look the number up there. Synchrotron and neutron (CW/TOF) headings are placeholders, not yet populated.

**Curated worked examples (bundled directly with this skill, no `TOPAS_DIR` needed):**
- `example_inp_files/example_inp_files_index.md` — a lookup table of the real, working `.inp` files kept in that same folder (Rietveld templates and real fits, indexing, peak-fitting, simulation, parametric/variable-temperature multi-pattern refinement, and an instrument-resolution-function → double-Voigt size/strain pair), each self-documented in its own header comment. Check this before the bundled-install examples below.

**Worked examples (real, complete INP scripts — require `TOPAS_DIR`):**
- `references/examples-index.md` — a categorized table describing all 280 example files by relative path, grouped by folder, with heuristically-detected topics per file. Start here to find a close analog, then resolve via `python scripts/topas_install.py --example <path>`. Includes dedicated `cf/` (charge-flipping), `cf-protein/`, and `indexing/` folders. Folder names are often a strong hint about the refinement type.
- `references/console-output-and-errors.md` — what TOPAS actually prints during a run: startup sequence, Rietveld/Pawley/charge-flipping iteration-log columns, two real captured error messages with causes, and the difference between `num_runs` (re-running with `Run_Number` switching) and `continue_after_convergence` (restarting within the same run until `iters`/`num_cycles` — by design, not a bug, if it runs long).
- `references/restraints-and-penalties.md` — `Distance_Restrain`/`Angle_Restrain` as the first restraint macros to reach for; how to read `append_bond_lengths`' SHELX-style bond/angle output matrix and turn it into correct `LABEL opidx offx offy offz` restraint arguments (space-separated, not colon-joined — a common silent-failure trap); **the mandatory zero-weight verification step for every `Angle_Restrain` target before refining — never hand-derive a 90°/180°-type target from the table by eye**; a distance-vs-angle restraint weighting rule of thumb; and `penalties_weighting_K1` for balancing restraints against the diffraction data as a whole.
- `references/macro-expansion-and-log-files.md` — what `tc.log` actually is (the INP after full macro/`#include`/preprocessor expansion), how TOPAS's `at LINE N` error numbering relates to physical source lines, confirmed macro-argument substitution mechanics, and the exact expansions of common built-in macros like `STR`, `XDD`, `LP_Factor`, `PV_Peak_Type`.

**Underlying algorithms/methodology (primary literature):**
- `references/paper-summaries.md` — original summaries of the papers behind TOPAS's algorithms: fundamental-parameters peak shapes, charge/band flipping, stacking-fault averaging, indexing, PDF methods, WPPM, the Marquardt/conjugate-gradient minimizers, axial divergence, capillary aberration, LPSD profiles, simulated-annealing structure solution, the TOPAS symbolic system. Use for *why* an algorithm works; consult the cited paper for exact equations/data. No papers are bundled as PDFs (see `references/papers-index.md` for why).

**Other sources:** Draft chapters from Dinnebier, Leineweber & Evans (2018), *Rietveld Refinement: Practical Powder Diffraction Pattern Analysis using TOPAS* (De Gruyter) were used to enrich the skill. If a future session reads draft chapters again, search each section for "not in the Technical Reference manual" to find what's already extracted.

**Core system files (require `TOPAS_DIR`):**
- `references/system-files-index.md` — describes each `.inc` macro library (including `topas.inc`, auto-included at the start of every INP file) and each `.txt` runtime data table (space groups in `sgcom5.txt`, scattering factors, anomalous dispersion, neutron scattering lengths, isotopes, Shubnikov groups) — description only, not the files themselves. Check the real `topas.inc` before assuming a macro is undefined.

**Lookup / catch-all:**
- `references/21-keyword-index.md` — structural index of keyword names grouped by data structure (`Ttop`, `Tglobal`, `Txdd`, `Tindexing`, `Tcharge_flipping`, etc.). Use to check whether a keyword exists and where it's valid; cross-reference the matching chapter for actual semantics.
- `references/20-miscellaneous.md` — magnetic form factors, protein data bank import, threading, background function stability, random-number seeding, other uncategorized topics.
- `references/23-gui-functionality.md` — TOPAS-GUI-specific behavior.
- `references/00-introduction.md` — general orientation if truly starting from scratch.
- `references/24-bibliography.md` — citations (e.g. Cheary & Coelho 1992, Coelho 2016/2018).

## Scripts

`fix_columns.py`, `format_inp_hierarchy.py`, `insert_adps.py` and `remove_errors.py` **rewrite the file in place with no backup** — preview with `--check` first unless the `.inp` was just copied from a `.out`.

- `scripts/topas_install.py` — resolves file paths against the real TOPAS installation via `TOPAS_DIR`. Used internally by the other scripts and directly by you when reading an example file:
  ```
  python scripts/topas_install.py --inc-dir
  python scripts/topas_install.py --example cf/alvo4a.inp
  ```

- `scripts/check_inp_syntax.py` — a heuristic syntax checker. Run it against any `.inp` file or directory before handing it over:
  ```
  python scripts/check_inp_syntax.py path/to/file.inp
  python scripts/check_inp_syntax.py path/to/directory/    # recurses
  python scripts/check_inp_syntax.py path/to/file "macro FILE { file.xy }"   # tc.exe-style extra command-line text
  ```
  To run it automatically against the file open in VS Code, see `references/vscode-integration.md` for a `tasks.json` setup.

  A bare path with no extension resolves the same way `tc.exe` does (tried as-is, then with `.inp`/`.INP` appended), and a trailing token that isn't itself a file/directory is treated as extra text appended to the checked file's content, mirroring `tc file.inp "macro FILE { file.xy }"` — this matters because `check_symmetry_constraints` and `#ifdef`-branch stripping are `#define`-aware, so a file that only becomes valid once a CLI `#define` is injected needs that flag passed the same way to be checked correctly. **Consequence: a mistyped second file path is not an error** — it gets appended as INP text instead. Check the `[+cmdline: ...]` tag in the output if a file seems unchecked.

  It catches thirteen mechanical mistakes: unbalanced `{ }`/`( )`; an equation that never reaches its `;` before the enclosing scope changes (the scan restarts at any fresh top-level `=` found before a `;`, so a later equation's own `;` can't mask an earlier missing one); and any identifier that isn't a real keyword/macro name, a name the file declares, or a token consumed by a keyword's own multi-token argument grammar — flagged regardless of resemblance or length (exact-case matching; TOPAS names are case-sensitive). It resolves this without a full parser by knowing each keyword/macro's argument grammar, exempting multi-token forms: `z_matrix` atom labels, `space_group` symbols with embedded hyphens/digits, macro/`fn` parameter names used inside their own body, keyword-prefixed tables like `load site x y z occ beq layer { ... }` or `ADPs { u11C1 0.01 ... }`, two-tag keywords like `occ`/`element_weight_percent`, hyphenated bare filenames, `##` token-pasting, `_LIMIT_MIN_`/`_LIMIT_MAX_` value suffixes, `def NAME1, NAME2;` forward declarations, and the Table 2-2/2-4 reserved parameter names in `01-syntax-and-parameters.md`. Blind spots: locally-`#include`d macros aren't resolved (a checker gap, not a file mistake); an entirely invented keyword resembling nothing real isn't caught (e.g. a removed/version-specific one — see `references/console-output-and-errors.md`); and a file-local macro reusing a system-`#include` name at a different arity can still fail at runtime, so a clean arity pass means "matches a documented arity", not a guarantee.

  Other checks: macro calls whose argument count doesn't match any known definition; a keyword value split by a stray space into two tokens (e.g. `space_group P_31_ 2_1`); a value-report `:` dropped after a `;`; a refined `prm`/`local` given a bare value with no `min`/`max` (a best-practice warning — `prm`/`local` carry no built-in default bounds the way subject-specific keywords do; this check understands a project-local macro that sets `min`/`max` indirectly, e.g. `prm cs_g1_ 30 MM(3, 1000)`); a stray extra bare number after a single-value keyword's value, or after a keyword that takes NO value at all (e.g. `str  123123`); a `@` (auto-name sigil) not immediately followed by a numeric value or `=` — three legitimate exceptions are recognized rather than flagged: `@` as a bare macro-call argument (`CS_L(@, 300)`), `@` directly concatenated with a name (`TOF_PV(@pv6, ...)`), and a macro body that's just a bare `@`/`@name` (a common toggle-macro idiom); a bare `x`/`y`/`z` site coordinate suspiciously close to 1/3 or 2/3 (should be `x = 1/3;`) — flagged as a warning, since a large hit count on a big multi-atom/simulated-supercell file is usually intentional grid placement, not a bug; a UTF-8 byte-order-mark at the start of the file (a hard error — a leading BOM makes TOPAS choke on the very first token with no visual clue in most editors); and an ADP tensor component or lattice parameter that violates what the file's own declared space group requires (see `check_symmetry_constraints` below).

  **`check_symmetry_constraints`** validates an existing `.inp`'s ADP and lattice-parameter constraints against what its own declared space group requires, reusing the same crystallography engine as `cif_to_str.py` (`scripts/symmetry_utils.py`) in the opposite direction. Needs `TOPAS_DIR` (space-group operators come from TOPAS's own `sgcom6.exe`/`sg/` database); silently produces no findings if unavailable. Built-in lattice macros (`Cubic`/`Tetragonal`/etc.) are recognized and cross-checked against the space group's own computed crystal system, so e.g. `Cubic(...)` on an actually-tetragonal group is flagged. **Site coordinate (x/y/z) independence is deliberately never flagged** — built once, then removed at the explicit direction of TOPAS-Academic's author: an unfixed coordinate (no `!`) isn't an omission risking special-position drift, it IS the signal to treat the site as a general position whatever its current value (`x xti1 0 y yti1 0 z zti1 0` is general even at `(0,0,0)`; only all-`!`-fixed coordinates enforce a special position). ADP and lattice-length checks stay always-on, since an ADP's required value comes purely from the site's position rather than its own written number — a numerically-wrong ADP is a real data error regardless of refinement status. Residual gap: a `str`'s own literal `space_group` always resolves, but the `for strs N to M { space_group ... }` idiom is left unresolved rather than guessed at.

  `Get()` has confirmed, non-obvious scope-walking behavior worth knowing when writing or debugging any equation: **`Get()` cannot reach a plain `prm`/`local` by name** — `beq = Get(b1);` where `b1` is a `prm` fails with `Cannot locate b1 from beq in data structures`, even though the bare form `beq = b1;` works fine. `Get(keyword)` only walks up to the **nearest enclosing object that owns an actual structural keyword slot of that name** (`x`/`y`/`z`/`u11`..`u23`/`occ`/`beq` for a site; `a`/`b`/`c`/`al`/`be`/`ga`/`scale`/`space_group` for a `str`), not arbitrary declared names — confirmed empirically against a live `tc.exe`, matching the manual's own `fn lat(h,k,l) = h Get(a) + k Get(b) + l Get(c);` example. `GET_TIE_RE`/`resolve_site_coordinates` support an optional multiplier (explicit `* 0.99`/`/ 100`, or implicit bare juxtaposition `Get(x) .99` for multiplication only — confirmed valid TOPAS syntax via `tc.exe`) and an additive offset, but this is still not a general equation evaluator: multi-term sums of different `Get()`s, nested functions, and external `prm` references are unresolved and skipped with a note, never guessed at. Practical implication: only wrap a reference in `Get()` when targeting an actual structural keyword slot; reference a `prm`/`local` by bare name instead.

- `scripts/expand_inp_macros.py` — expands `macro` calls in an `.inp` file to approximate what TOPAS writes to `tc.log` (the literal, fully-expanded text fed to the kernel), without running TOPAS. Useful for seeing what a macro-heavy file actually does, or tracking down a `tc.log` "at LINE N" error against the macro-based source.
  ```
  python scripts/expand_inp_macros.py path/to/file.inp
  python scripts/expand_inp_macros.py path/to/file.inp -o expanded.inp
  python scripts/expand_inp_macros.py path/to/file.inp --run-number 1   # for files with Run_Number-dependent #if
  ```
  Resolves `#include`s of the `.inc` library, statically prunes `#define`/`#ifdef`/`#if`/`#endif` branches where it safely can, and recursively expands `macro` calls with overload-by-argument-count resolution, `@`-parameter auto-naming, and TOPAS's internal `#m_argu`/`#m_ifarg`/`#m_else`/`#m_endif` directive family.

  **Implements TOPAS's `&` macro syntax** (manual: "Superfluous parentheses and the '&' Type for macros"): `&` before a macro's own name (`macro & CeV(c, v) { ... }`) wraps the entire expansion result in parens at every call site; `&` before an argument name in the parameter list (`macro & Gauss(& xo, & fwhm) { ... }`) wraps that argument's substituted value in parens everywhere referenced inside the body. This isn't cosmetic — per the manual's own example, `divide(a + b, c - d)` without `&` wrongly expands to the precedence-broken `a + b / c - d` — and real `topas.inc` combines both forms extensively (`Gauss`, `Lorentzian`, `PO_eqn`, `Ramp`, `Limit`, and more).

  Macro expansion is multi-pass (fixed-point, capped at 60 passes), so a macro calling another macro fully resolves through every level. Brace-nesting inside a macro body is tracked correctly (including skipping over `"..."` string interiors, so a literal `}` inside a quoted filename doesn't truncate the body early). Resolves `#ingest` (like `#include` but for project files rather than the system library) and understands `#external_INP` (TOPAS does NOT merge these into the parent's own output, so this tool leaves the directive line untouched and appends each linked file's own expansion as a separate labeled section). A `#include` of a dynamically-built path (e.g. wavelength `.lam` files loaded by `CuKa5`) has its target's content actually inlined, not just its path resolved. Known gaps: `fn`-defined and built-in equation functions (`Cos`, `Gauss`, ...) are left untouched (evaluated by TOPAS's equation engine, not macro substitution); output line numbers do not match `tc.log`'s own numbering (see `references/macro-expansion-and-log-files.md` for those rules).

  **`#include` resolution rule, confirmed directly by TOPAS-Academic's author: "#include operates from the INP file directory unless the full path is given in the #include."** This applies to both the system `.inc` library and project-local files (a `.inc` or any other extension sitting next to the main `.inp`) — resolution tries the referencing file's own directory first, falling back to the system library only for a bare filename not found there, recursively for nested includes. This is a common real pattern (a project split across `main.inp` + `myrigidbodies.inp` + local `.inc` helper files), not an edge case.

- `scripts/find_refined_params.py` — **run this whenever the user asks for the independent/refinable parameters in a `.inp` file**. Lists every INDEPENDENT refined parameter: named (or auto-named via bare `@`), not `!`-prefixed, and — if written as a named equation — evaluating to a plain numeric constant rather than a function of other parameters (a DEPENDENT parameter, per Technical_Reference.pdf section 2.9).
  ```
  python scripts/find_refined_params.py file.inp
  python scripts/find_refined_params.py file.inp -o report.txt
  ```
  Fully macro-expands the file first and scans the expanded text (needed because a macro call's bare `@` argument doesn't sit textually next to the number it binds to until after expansion). Combines several signals: explicit `prm`/`local NAME ...` declarations (`local` is genuinely re-scoped per xdd/phase per the manual, so never deduplicated by name; bare `prm` has no such re-scoping and is deduplicated); the `@` sigil on keywords that carry it straight in the kernel (`a`/`b`/`c`/`al`/`be`/`ga`/`scale`/`bkg`); the `ADPs` macro's own expansion to `load u11 u22 u33 u12 u13 u23 { ... }`; and a curated list of other directly-written named keyword values (`beq`, ADP components, lattice parameters), deduplicated by name since TOPAS enforces one shared value per parameter name. Deliberately does NOT report bare, unnamed, un-`@` numeric values (e.g. a rigid body's computed-output site x/y/z) since there's no reliable way to distinguish an independently-refinable bare value from a computed/reported one by text pattern alone. Known limitations: a handful of directly-written keywords outside the curated lists could still be missed; expanded-text line numbers do not match the original file's for macro-generated content.

  **`for xdds { ... }`/`for strs [N to M] { ... }` loop repetition is accounted for, with a specific, non-obvious, empirically-confirmed rule: only ANONYMOUS/unnamed declarations get multiplied by the loop's iteration count, never bare NAMED ones.** TOPAS's kernel-enforced "same name = same value" rule (section 2.4) applies regardless of for-loop context, so a bare named `prm` inside a loop stays ONE shared parameter across every iteration, while an anonymous `@` genuinely gets a fresh instance each time — confirmed with minimal test files (`for xdds { prm test_named_prm ... }` on 2 xdds reports 1 independent parameter; the same test with `prm @ ...` reports 2). Anonymous `direct_at`/`adp_loads` entries and `local` (already re-scoped per iteration) are multiplied; named `prm`/`named_direct` entries never are. A bare (no-range) `for strs { ... }` nested inside another for-loop is deliberately left unmultiplied since its real scope (whole file again per outer iteration, or just the current xdd's own strs?) isn't confirmed — better to undercount than risk a wild overcount. `param_dependency_trees.py`'s independent-parameter badge reuses this exact same rule.

- `scripts/run_variants.py` — **run this whenever several model variants of one `.inp` need comparing** (peak-shape families, PO orders/directions, background orders, ADP schemes, the mandatory false-minimum reset check, phase screening). Runs each variant on a scratch copy — the base file is never modified — and prints one comparison table:
  ```python
  import sys; sys.path.insert(0, r"<skill>/scripts")
  from run_variants import VariantRunner, add_to_str, add_to_xdd, set_bkg, comment_out

  r = VariantRunner("y2o3.inp", workdir="y2o3_workings")
  r.add("sh4",   lambda t: add_to_str(t, "PO_Spherical_Harmonics(sh, 4)"))
  r.add("sh6",   lambda t: add_to_str(t, "PO_Spherical_Harmonics(sh, 6)"))
  r.add("steph", lambda t: add_to_str(t, "Stephens_cubic(@,0.5, @,0.0001, @,0.0001)"))
  r.add("b16",   lambda t: set_bkg(t, 16))
  r.run()
  ```
  ```
  variant       Rwp     dRwp      GoF   Npar  limits
  base      12.3439        -   1.2080     20  -
  sh4       11.6927  -0.6512   1.1440     22  -
  sh6       11.5810  -0.7629   1.1330     24  -
  steph     12.8847  -0.4592   1.2600     23  steph_eta
  ```
  An unmodified `base` row is always run first and every other row reported as a delta against it. `Npar` is TOPAS's own `Num independent parameters:` count, so a variant's cost sits beside its gain; `limits` names any parameter carrying `_LIMIT_MIN_`/`_LIMIT_MAX_` in that variant's `.out`, flagging a gain that rests on a saturated term (see the peak-shape-term saturation rules in `references/27-rietveld-workflow-conventions.md`). A failed variant reports tc.exe's actual error in its row rather than dropping out.

  Per variant it strips any stale `C_matrix_normalized`, rewrites the `xdd` path to an absolute one, and **removes the recognized output-writing macro calls** (`Out_X_Yobs`, `Out_X_Ycalc`, `Out_X_Difference`, `Create_hklm_d_Th2_Ip_file`, `Create_hklm_d_Th2_IScaled_file`, `Out_CIF_STR`) — the comparison needs only the table, and on a 15k-point pattern each variant would otherwise write ~800 kB of Yobs/Ycalc that nothing reads. Pass `keep_outputs=True` to write them under per-variant filenames when a variant's fit actually needs plotting, or just re-run the single variant of interest afterwards. Scratch files are `v_<basestem>_<name>.inp`. Pass `data_dir=` when the base `.inp` is itself a scratch copy sitting somewhere other than next to its data; a missing data file is reported once, up front, instead of failing every variant identically. Text helpers are literal string surgery, not an `.inp` parser: `add_to_str`, `add_to_xdd`, `set_bkg(n)`, `comment_out(regex)` — write the transform inline for anything else. Chooses nothing and interprets nothing; it reports numbers.

- `scripts/param_dependency_trees.py` — **run this whenever the user asks for a parameter dependency tree/graph, or says "do trees"** (a standing trigger phrase — run against the relevant/currently-open `.inp` file and let it open its own report). **"do trees" defaults to the interactive HTML form** (`-o <name>.html`, opened in the browser); only fall back to plain-text/VS-Code if the user explicitly asks for text. Builds the full computation graph (not just the independent-parameter list `find_refined_params.py` stops at) and renders it as two views:
  ```
  python scripts/param_dependency_trees.py file.inp -o report.html     # "do trees" default: interactive page, opens in browser
  python scripts/param_dependency_trees.py file.inp                    # both trees, to stdout
  python scripts/param_dependency_trees.py file.inp --tree dependent   # tree 1 only
  python scripts/param_dependency_trees.py file.inp --tree independent # tree 2 only
  python scripts/param_dependency_trees.py file.inp -o report.txt      # write + auto-open in VS Code
  python scripts/param_dependency_trees.py file.inp -o report.txt --no-open
  ```
  When `-o` is given, opens/focuses the written report afterward — VS Code for text, the default browser for `.html`/`.htm` (the general rule this skill follows: plain-text reports open in VS Code, HTML visualizations open in the browser). Both trees render as click-to-expand node lists, color-coded by kind (green = independent/refined, blue = dependent, grey = fixed), with a live search box. **Tree 1**: every DEPENDENT parameter/keyword as a root, its referenced parameters as children, recursed to independent/fixed leaves. **Tree 2**: every INDEPENDENT (refined) parameter as a root, with the dependents that reference it as children — the reverse-edge view. A bare `@`-flagged value with no name of its own is labeled with its keyword instead.

  Macro-expands the file first and scans for equations in `prm`/`local` (including `!`-prefixed ones, unlike `find_refined_params.py`, since this needs the full graph regardless of refined status) and a curated keyword list (site `x`/`y`/`z`/`occ`/`beq`/`u11..u23`, lattice `a`/`b`/`c`/`al`/`be`/`ga`/`scale`, `rotate`/`translate`, rigid-body Z-matrix `ta`/`tb`/`tc`). The header's stat badge shows the count of refineable independent parameters (same definition as `find_refined_params.py`, including its for-loop multiplier rule). `local` re-scoping is handled the same way (same name in multiple `local` statements = genuinely different parameters, resolved to the nearest preceding declaration). Rigid-body `z_matrix` rows are parsed for their own bond/angle/torsion equations in both TOPAS `z_matrix` syntax forms (block form and inline form). **Deliberately shows the FULL computation graph, not the independent-leaf-collapsed view TOPAS's own `out_dependences`/`out_dependences_for` gives** — this script's output is a strict superset, traceable node-by-node, by design.

- **"Show Schema" is a standing trigger phrase** for displaying TOPAS's internal kernel data-structure page (`kernel_structure_tree.html`) — an interactive tree of the kernel's own `Txxx` complex types. This page isn't generated by this skill — only the pre-rendered HTML travels with each TOPAS release. Resolve and open it with:
  ```
  python scripts/topas_install.py --kernel-schema-html
  ```
  If `TOPAS_DIR` isn't set or the file isn't found, say so plainly — there is no bundled fallback.

- `scripts/c_matrix_heatmap.py` — renders a `C_matrix_normalized { ... }` block (the normalized parameter-correlation matrix TOPAS writes after `do_errors`) as a heatmap, diverging blue (negative)/red (positive) with a gray zero midpoint. Two formats, via `--format {png,html}` (or inferred from `-o`'s extension; defaults to `png`):
  ```
  python scripts/c_matrix_heatmap.py path/to/file.inp                          # -> file_c_matrix.png
  python scripts/c_matrix_heatmap.py path/to/file.out -o heatmap.png --cell-size 30
  python scripts/c_matrix_heatmap.py path/to/file.inp --format html            # -> file_c_matrix.html
  ```
  `png`: zero third-party dependencies (hand-encoded via stdlib `zlib`, bundled bitmap font); axis ticks are the 1-based index only, full names printed to stdout. `html`: self-contained interactive page with full parameter names, hover tooltips — generally the better default unless a static image is specifically needed. Both parse the block as plain text (no macro expansion needed), so it works on a literal block in a `.inp` or a real `.out` result.

- `scripts/plot_str_3d.py` — **run this whenever the user asks for a 3D plot/view of a `str` phase's crystal structure**. Renders one `str` block as a self-contained interactive HTML page (drag to orbit, scroll to zoom, a perspective slider, an off-by-default site-labels checkbox) — unit cell as a wireframe box, every site symmetry-expanded across the cell as colored spheres, cation-anion bonds by covalent-radius-sum cutoff. No third-party dependencies (hand-written vanilla-JS canvas 3D engine, works offline/in a strict-CSP viewer).
  ```
  python scripts/plot_str_3d.py file.inp                # -> file_str3d.html
  python scripts/plot_str_3d.py file.inp --phase 2       # pick the Nth str block (1-indexed) if more than one
  python scripts/plot_str_3d.py file.inp --no-bonds
  python scripts/plot_str_3d.py file.inp --bond-tolerance 1.3
  ```
  Reuses this skill's existing engine: `check_inp_syntax.py`'s site/coordinate parsing, `symmetry_utils.resolve_sg_operators`, `expand_inp_macros.py`'s macro-argument parsing for lattice macros. Cell parameters come from literal `a`/`b`/`c`/`al`/`be`/`ga` (with simple `Get()` ties resolved) or a built-in lattice macro (argument-to-parameter mapping read from the live install's `topas.inc`). A site's fractional point is mapped through every space-group operator, reduced mod 1 and deduplicated for its orbit/multiplicity; a point on a cell face/edge/corner is additionally mirrored so the box looks visually complete. Element colors/covalent radii are an approximate built-in table (~70 elements) for visual aid, not scientific bond-length analysis. **Bonds are restricted to different-element pairs** — a same-element cutoff produced hundreds of nonsensical same-species bonds on a real fluorite test file. Known limitations: occupancy/site-mixing not visualized (drawn as the first species only); only sites whose x/y/z all resolve to a concrete number are plotted; a cell parameter written as a more complex equation won't resolve.

  A site whose `u11..u23` all resolve to concrete numbers is drawn as an oriented 50%-probability thermal ellipsoid instead of a plain sphere. TOPAS's `u11..u23` (the standard IUCr/CIF U_cif convention) are converted to a Cartesian tensor via the standard transform, and each symmetry-equivalent image of a site gets its own correctly reoriented tensor (verified directly on a rutile test file with deliberately asymmetric ADPs: images related by the space group's screw axis show the expected sign-flip/rotation signature). ADP resolution also handles the common per-site-tagged naming convention (`u11C1`, `u22C1`, ...), needed since TOPAS's global "same name = same value" rule means a many-atom refinement must give each site's `u_ij` a distinct name. Nothing about this is space-group-specific (verified across cubic, orthorhombic, monoclinic, and triclinic test files).

- `scripts/plot_sh_sphere.py` — **run this whenever the user asks to see/plot/draw a spherical-harmonics series as a pole figure or 3D surface** — a preferred-orientation/texture correction (`PO_Spherical_Harmonics`) or any other `spherical_harmonics_hkl` use (e.g. the anisotropic-broadening form under hkl-dependent peak shapes in `references/27-rietveld-workflow-conventions.md`). Renders one `str` block's series as a self-contained interactive HTML pole figure (drag to orbit, scroll to zoom), no third-party dependencies. **Carries an on-page "not extensively tested" warning banner — keep it there until this has more mileage.**
  ```
  python scripts/plot_sh_sphere.py file.inp                     # -> file_sh_sphere.html, raw dots
  python scripts/plot_sh_sphere.py file.inp --surface           # + interpolated surface / contour / radius toggles
  python scripts/plot_sh_sphere.py file.inp --phase 2 -o tex.html
  python scripts/plot_sh_sphere.py file.inp --surface --mesh-level 4   # finer mesh, slower
  ```
  **Never re-derives the harmonics** — symmetrized-harmonic conventions differ between sources (normalization, and which real `Y_lm` combination a term like `k41` denotes), so a hand-derived basis risks a plot that looks right but is wrong in magnitude or orientation. Instead it runs `tc.exe` at `iters 0` on a scratch copy with `Create_hklm_d_Th2_Ip_file(<file>, <sh_name>)`, inheriting TOPAS's own convention exactly. Needs `TOPAS_DIR`. Reads `PO_Spherical_Harmonics(name, order)` or bare `spherical_harmonics_hkl name`; the anonymous `PO_Spherical_Harmonics(, order)` form fails with a clear message (its internal name isn't addressable).

  **General across all space groups/settings, no Laue class hardcoded.** Direction = `(A⁻¹)ᵀ·(h,k,l)` so the reciprocal metric is right for any cell (for monoclinic β≠90, a\* is *not* along a). Orbit expansion runs in Cartesian via `R_cart = A·R_frac·A⁻¹` (as `plot_str_3d.rotate_u_cart` already does), unioned with its negatives for Friedel — avoiding any convention choice for how Miller indices transform. Operators from `symmetry_utils.resolve_sg_operators`; that module was **not** modified. Two self-checks run every invocation: `|B·hkl|` vs TOPAS's own d-spacing (validates the metric numerically), and an over-symmetrization check (two families on one direction with different values ⇒ Laue group too big) — both warn rather than fail silently. Verified on cubic Ia-3 (reproduces an independently hand-built figure exactly), hexagonal, monoclinic and triclinic, metric agreeing to <0.001%.

  **Dots are raw; surface and contours are interpolated.** Each dot is a direction TOPAS actually evaluated; `--surface` adds an icosphere mesh with angular-Gaussian-weighted vertex values, so a smooth patch inside a sparse gap is an artifact. A warning fires above ~12° median nearest-neighbour separation (risky case: low symmetry + narrow 2θ).

  **Page toggles:** radius ∝ value (default on — makes an implied PO direction obvious) / dots / surface / iso-contours (5, 9, 15 levels) / reciprocal axes a\*b\*c\* (on) / unit cell + direct axes abc (off). Both triads are offered since they differ for non-cubic. The cell is scaled to contain the surface and the zoom-out limit is derived from its own extent so even a triclinic cell fits; it is a reading aid for the preferred-orientation rule's "does the harmonic imply a simple PO direction", not a claim the lobes occupy real space — the plotted quantity is directions, not positions.

- `scripts/plot_xy.py` — **run this whenever the user asks to plot a raw XY(E) data file** (`.xy`, `.xye`, `.dat`, or `Out_X_Yobs`/`Out_X_Ycalc` output). Renders a self-contained interactive HTML page: drag to pan, scroll to zoom (both cursor-centered), a per-series visibility checkbox in the legend, a hover crosshair (no floating tooltip box), a Sqrt(Y)/Linear toggle for compressing dynamic range, and an optional `--stats "Rwp=13.68%,GoF=1.64"` (comma-separated `Label=value` pairs) to show refinement statistics as plain text in the header next to the point-count/X-range meta line.
  ```
  python scripts/plot_xy.py file.xy                # -> file_xy_plot.html
  python scripts/plot_xy.py file.xy --title "My pattern"
  ```
  No third-party dependencies. Parsing skips blank/comment lines and lines with fewer than two numeric tokens rather than raising. Y-axis autoscaling recomputes from only the currently visible X window on every pan/zoom. The Sqrt(Y) transform is signed (`sign(y)*sqrt(abs(y))`) to degrade gracefully on background-subtracted data with small negative values.

  **Supports multiple overlaid series and a computed difference/residual curve:**
  ```
  python scripts/plot_xy.py obs.xy calc.xy --labels "Yobs,Ycalc" --colors "blue,red" --diff "Yobs,Ycalc" -o out.html
  python scripts/plot_xy.py --phases "CeO2|ceo2_obs.xy|ceo2_calc.xy,Y2O3|y2o3_obs.xy|y2o3_calc.xy" -o out.html
  ```
  `--labels`/`--colors` are comma-separated, parallel to the file arguments; an explicit user color instruction is used literally. `--diff LABEL_A,LABEL_B` adds a `LABEL_A - LABEL_B` series (direct subtraction on a shared X grid, else linear interpolation); repeatable per phase. **All difference curves share one live-computed screen-space offset**: the highest point among visible diff curves sits ~5 CSS pixels below the lowest point among visible main series, recomputed on every draw so it never drifts on zoom. `--phases "NAME|obs.xy|calc.xy,..."` (pipe-separated, since `:` collides with Windows drive letters) auto-builds a combined multi-phase plot with a standing color scheme: every phase's Ycalc is the same fixed red-orange; each phase's Yobs cycles through a fixed 8-color palette (deliberately none red/near-red, to stay distinguishable from Ycalc); each diff curve reuses its own phase's Yobs color at 0.7x intensity. Cannot be combined with plain positional file args in the same invocation.

  **"Run and plot [file]" is a standing workflow**: (1) run via `tc.exe` on a scratch copy, never the original in place; (2) if `Out_X_Ycalc(...)`/`Out_X_Yobs(...)` are missing, warn and add them to the scratch copy — for a Rietveld/Pawley fit also add `Create_hklm_d_Th2_Ip_file(ticks.txt)` inside the `str`/`hkl_Is` block, so tick marks with real h k l hover labels are available by default (see `references/27-rietveld-workflow-conventions.md`'s rule on default reflection ticks — one tick file per phase); (3) plot Yobs, Ycalc and their difference together, passing the run's own `r_wp`/`gof` (and `r_p` if relevant) from the `.out` via `--stats "Rwp=13.68%,GoF=1.64"` (same reference file's rule on plot stats) and the tick file(s) via `--ticks "NAME|ticks.txt,..."`; (4) for more than one `xdd`, one plot per `xdd` by default — unless the user says **"fit show in one plot"**, then combine via `--phases` (tick groups still combine via `--ticks`, one per phase). Two multi-phase facts worth remembering: TOPAS enforces one shared value per parameter name globally (reusing `CS_L(csl, ...)` at different values across two phases aborts with `Parameter csl is defined more than once...`); and a relative data filename in a `DAT`/`XDD`/`RAW` call resolves against the referencing `.inp`'s own directory (same rule as `#include`), so a scratch copy run elsewhere needs its data file alongside it.

- `scripts/build_report_docx.py` — **use this if the user wants the final refinement report as a `.docx` instead of (or alongside) plain markdown.** Fills the styles-only `templates/refinement_report_template.docx` (Arial 10pt body, styled headings, bordered/shaded tables, disclaimer style) so every report looks the same — don't hand-format a `.docx` or reach for `pandoc` (not guaranteed installed). Call `build_report(title, date, sections, out_path, images=..., plots=..., files=...)`; the script's module docstring has the argument shapes, content conventions (e.g. "Å" not "A") and a worked example. To restyle, edit the named styles in the template `.docx` in Word — the script refers to styles by name only, so no code change. Don't put visible content in the template: it's every report's base document, so anything in its body leaks into all of them (`scripts/_build_template.py` rebuilds it if needed). For an embedded fit image (not just a hyperlink), render with `scripts/plot_xy_matplotlib.py` (same flags as `plot_xy.py`, PNG/JPG instead of interactive HTML) and pass `images=[("caption", "fit.png")]`.

- `scripts/cif_to_str.py` — converts a CIF file's structure into a TOPAS `str { }` block, deriving Wyckoff-position coordinate constraints directly from the CIF's own `_symmetry_equiv_pos_as_xyz` operator loop. Preferred over `cif1.exe` — see "Converting a CIF file to `str` format" below.
  ```
  python scripts/cif_to_str.py input.cif                   # print to stdout
  python scripts/cif_to_str.py input.cif -o output.txt      # write to file
  python scripts/cif_to_str.py input.cif --tolerance 0.002  # coordinate-match tolerance (default 0.0015)
  ```
- `scripts/symmetry_utils.py` — not a standalone tool, a shared library. Holds the crystallography engine (symmetry-operator parsing, `sgcom6.exe`/`sg/`-database resolution, per-site Wyckoff/ADP constraint derivation, per-lattice-system angle/length constraint derivation) used by both `cif_to_str.py` (CIF → `str`) and `check_inp_syntax.py`'s `check_symmetry_constraints` (`.inp` → warnings) — extracted into one shared module so a crystallography fix in one is a fix in both.

- Two scripts here are **not chat-facing** — listed so they aren't rediscovered as unknowns: `scripts/symmetrize_str.py` (same symmetry engine as `check_symmetry_constraints`, but rewrites selected `site`/cell parameters to their canonical free/fixed/tied form and returns line/column edit spans — built for an editor extension to call as a child process) and `scripts/generate_space_group_browser.py` (regenerates `references/space_group_symbols.html` from the install's `sgcom5.txt`; that page isn't currently in `references/`, so run it once if wanted).

- `scripts/fix_columns.py` — **run this whenever the user says "fix columns"** (or asks to column-align/tidy up `site` statements). Column-aligns consecutive `site` lines so their keywords (`x`/`y`/`z`/`occ`/`beq`/`u11`..`u23`) start at the same character column, with exactly one space between a padded value and the next keyword, e.g.:
  ```
  site Ce1 x  0.25 y   0.5 z  0.25 occ Ce+4 1 beq = b1;
  site Ce2 x     0 y   0.5 z   0.5 occ Ce+4 1 beq = b1;
  ```
  A plain numeric value is right-aligned within its column (so digits/decimal points line up down the page in a fixed-width font); a column mixing a bare number with an equation stays left-aligned. `occ`'s two-token `TYPE N` form gets its own two independently-aligned sub-columns. Also column-aligns consecutive `la ... lo ... lh ...` emission-profile lines inside a `lam { }` context, forcing them (and `ymin_on_ymax`) one indent level deeper than the nearest preceding `lam` line, per the real keyword hierarchy (Technical_Reference p.209).
  ```
  python scripts/fix_columns.py file.inp              # rewrite in place, whole file
  python scripts/fix_columns.py file.inp --check      # preview to stdout, don't write
  python scripts/fix_columns.py file.inp --lines 26-31 # only touch lines 26-31 (1-indexed, inclusive)
  ```
  Whitespace-only — still run `check_inp_syntax.py` afterward. `--lines` computes column widths from the whole file but only rewrites lines in range — translate an active IDE text selection directly into this flag rather than fixing the whole file. Correctly handles a `Get(x)`/`Get(y)`/`Get(z)` reference inside another coordinate's own equation (e.g. `z = Get(x) + 0.1625;`) without mistaking the inner reference for a new keyword boundary.

- `scripts/format_inp_hierarchy.py` — **run this whenever the user asks to reindent/reformat a `.inp` file "hierarchically"**. Reindents a whole file to reflect its structural nesting, 3 spaces per level; a line with multiple keywords packed onto it is never split.
  ```
  python scripts/format_inp_hierarchy.py file.inp              # rewrite in place
  python scripts/format_inp_hierarchy.py file.inp --check      # preview to stdout, don't write
  python scripts/format_inp_hierarchy.py file.inp --no-open    # skip reopening in VS Code afterward
  ```
  Reopens the file in VS Code after writing (skip with `--no-open`). Collapses excess whitespace on most lines (never inside a quoted string/comment, or inside a `C_matrix_normalized { ... }` block). Runs `fix_columns.py`'s own alignment first, so `site`/`la`/`lo`/`lh` lines end up correctly aligned as part of the same pass. Because a large part of TOPAS's real hierarchy has no `{ }` at all (an `xdd`/`str` block just runs until the next phase/`str` keyword or EOF), indentation is derived directly from the manual's own keyword-hierarchy schema (`21-keyword-index.md`'s Data-structures block) rather than a hand-picked keyword list: only keywords with a non-empty resolved children set become section-openers, and a "wide" section (reaches `prm`, e.g. `xdd`/`str`) is only closed by another section-opener it doesn't recognize as a child, while a "narrow" section (e.g. `site`, `lam`) is closed by any keyword that isn't one of its own children. One narrow, explicitly-documented exception: `la`'s connection to `lam` is only inferable from prose, not schema, so it's a hand-coded supplement.

- `scripts/remove_errors.py` — **run this whenever the user says "remove errors"**. Strips every trailing `` `_<error> `` refined-value-error suffix in one regex pass — see "Stripping refined-value errors" below.

- `scripts/insert_adps.py` — **run this whenever the user says "insert adps"**, replacing a `beq` clause on selected `site` line(s) with symmetry-constrained anisotropic displacement parameters (`u11`/`u22`/`u33`/`u12`/`u13`/`u23`) instead of hand-deriving the constraints each time.
  ```
  python scripts/insert_adps.py file.inp --lines 26-28   # only site(s) touching these lines
  python scripts/insert_adps.py file.inp                 # every site with a beq, whole file
  python scripts/insert_adps.py file.inp --check          # preview to stdout, don't write
  ```
  Same `--lines` convention as `fix_columns.py`. Reuses the same parsing/crystallography engine as `plot_str_3d.py`/`check_symmetry_constraints`/`cif_to_str.py`, so output uses identical formatting conventions throughout a file mixing CIF-converted and script-converted sites. A site's space group always comes from TOPAS's own database via the file's own `space_group` line, never guessed; silently produces no conversions without `TOPAS_DIR`. The starting value seeded into each newly-free `u11`/`u22`/`u33` is derived from the site's old `beq` (`Uiso = Beq/8π²`), with a fallback chain if `beq` is itself an equation: its own numeric value, then a same-named `prm`/`local` elsewhere in the file, then another site's own `beq NAME value` tag; a free off-diagonal component with no isotropic equivalent starts at 0; an unresolvable `beq` falls back to a generic `0.01` with an explicit warning. Also runs `fix_columns()` over its result afterward, scoped to the same `--lines` range, so newly-inserted `u11`/`u22`/... columns are aligned immediately.

- `scripts/find_example.py` — **run this whenever the user asks for a template/example/starting point for some refinement topic**, e.g. "tof template". Searches a curated ~197-file subset of the TOPAS install's 1138-file `test_examples/` tree — a different, narrower list than `references/examples-index.md`'s 280 install examples. **The subset is a `tcinps-2.bat` tc-list file that is NOT bundled with this skill**; the default path (`c:\w\tcinps-2.bat`) is machine-specific, so pass `--bat <path>` or expect a "No match" exit. Fall back to `examples-index.md` when it can't run.
  ```
  python scripts/find_example.py tof
  python scripts/find_example.py "tof template"              # trailing filler words are stripped
  python scripts/find_example.py pawley -n 5                  # show up to 5 matches (default 8)
  python scripts/find_example.py "charge flipping" --open     # also open the top match in VS Code
  ```
  Two matching passes: (1) whole-word (not bare-substring — "tof" no longer false-positives inside "tofullprofmono") path match against corpus folder/file names, which are usually topic-named; (2) a content match against a curated topic-synonym list (Pawley, Le Bail, indexing, PDF, charge-flipping, quant, stacking faults, rigid bodies, deconvolution, magnetic, protein, single-crystal, TOF, parametric/sequential) for queries naming a concept the corpus only abbreviates (e.g. "charge flipping" → `cf/`). Deliberately does NOT auto-genericize a found example into a placeholder-filled template — deciding what's an instrument constant to keep vs. a sample-specific value to placeholder-ize needs real per-topic judgment; `example_inp_files/tof_template.inp` is what that judgment call looks like once applied by hand.

- `scripts/to_Reel_v1.py` — converts TOPAS `.xyd` Rietveld-fit output into `.xyy` files for viewing in Reel. The `.xyd` format itself is written by the `Write_Rietveld_xyd`/`Writephase` macro pair — see `example_inp_files/d8_01612_vt_reel_02.inp` for a full worked sequential/VT example that writes them. **Unlike the other scripts here, this one is not run directly from this folder** — copy it into the project's own working directory (next to the `.inp`) before running, since the normal way to invoke it is from inside the `.inp` itself via `system_after_save_OUT { python to_Reel_v1.py <results_dir> }`, which shells out relative to wherever `tc.exe` is running, not this skill's own path.
  ```
  python to_Reel_v1.py <directory_of_.xyd_files>
  ```
  Requires a `results.txt` in the **current working directory** (not the `<directory>` argument) with a header row containing at least `filename_reel`, `filename`, `r_wp`, `lam`, `Temperature` — case-sensitive, exact names. Metadata matching is a strict equality between a `.xyd` file's own stem (filename minus extension) and that row's `filename_reel` value, not a substring match, so the `.inp`'s own `filename_reel` macro must be built to produce exactly the same string as the `.xyd` basename it writes (see the `xydFileName`/`filename_reel` macros in the example above). A row that doesn't match prints a `WARNING` and that pattern's `.xyy` is written without metadata, rather than the run failing.

  Two module-level constants, editable only in the copied script: `delete_xyd` (default `True`) removes each source `.xyd` once its `.xyy` is written — including when the metadata lookup failed; and `write_background_subtracted` (default off) creates a hardcoded `data_background_subtracted/` directory in the cwd. Multiprocessed (`cpu_count()-1` workers), so a whole VT/sequential batch at once is fine.

## Core syntax cheat sheet

- Blocks are delimited with `{ }`; comments use `'` to end-of-line.
- A parameter gets a name (letters, digits, underscore, must not start with a digit) so it can be tracked/refined; prefix `!` to fix it (exclude from refinement); prefix `@` to auto-generate a unique internal name.
- **`bkg` (Chebyshev background) takes exactly one `@` in front of the whole coefficient list, not one per value.** `bkg @ 0 0 0 0 0 0` refines all six coefficients; `bkg @ 0 @ 0 @ 0 @ 0 @ 0 @ 0` is wrong syntax, a recurring mistake — don't repeat `@` per number here even though other multi-argument contexts (macro calls) do take one `@` per slot.
- **Naming a parameter explicitly: write the name plain, not glued after `@`.** `beq b1 0.5` is the idiomatic form for a named, refined parameter — no `@` needed, since giving it a name is itself what flags it for refinement (`01-syntax-and-parameters.md` § "When is a parameter refined"). `beq @b1 0.5` (name glued directly after `@`) is also accepted by TOPAS, but every real worked example in this skill uses the plain form (`beq bvalue 4.32439`, `a lpa 5.536662`) — reach for that, not `@name`, whenever a sensible/readable name is wanted. Reserve bare `@` (no name at all, e.g. `x @ 0.844`) for when an auto-generated internal name is fine and no explicit name is needed.
- `prm name value` declares a standalone named parameter; combine with attributes like `min`, `max`, `update`, `stop_when` as needed.
- **Prefer the subject-specific keyword over a bare `prm` for ANY refinable value that has one** — not just lattice parameters/`beq`/`occ`, a general rule. `topas.inc` itself supplies explicit `min`/`max` alongside essentially every genuinely refinable `prm` it declares (via the shared `If_Prm_Eqn_Rpt` helper), and many subject-specific keywords additionally carry a documented default `min`/`max` (Table 2-1 in `01-syntax-and-parameters.md`) that a bare `prm` + equation indirection silently discards. This applies just as much when manually expanding a macro to raw keywords — don't drop the bound the macro was silently supplying. If `topas.inc` isn't available to read the real bound, add a physically-reasoned placeholder and say plainly it's a placeholder. For a cubic cell with `a` refined:
  ```
  a prm_name 4.56
  b = Get(a);
  c = Get(a);
  ```
  not
  ```
  prm prm_name 4.56
  a = prm_name;
  b = prm_name;
  c = prm_name;
  ```
  If a bare `prm`/`local` genuinely is the right tool (no subject-specific keyword fits), define its own `min`/`max` explicitly rather than relying on TOPAS's generic fallback.
- Equations start with `=` and end with `;`. The `;` is mandatory even immediately before a `:` value-report — `prm bb = cs1 + cs2 : 0` (no `;`) is invalid; it must be `prm bb = cs1 + cs2; : 0`. See `01-syntax-and-parameters.md` § "Reporting on equation values"/"Naming of equations".
- A trailing `: 0` (or any placeholder number) after an equation's terminating `;` tells TOPAS to report that equation's evaluated value back into the file in place of the placeholder once refinement finishes (plus its error, if `do_errors` is set) — this also works on a bare, unnamed equation (`prm = 2 a1^2 + 3; : 0;`).
- Structures (`str { ... }`) contain `site` definitions with `x y z occ beq` etc.; intensity-only phases use `hkl_Is` or `xdd_Is` instead of a full structure.
- **`al`/`be`/`ga` default to 90 degrees if omitted from a `str` entirely**, regardless of `space_group` (including `P1`) — confirmed directly by TOPAS-Academic's author. Don't write `al 90 be 90 ga 90` just because the space group label no longer implies it. See `01-syntax-and-parameters.md` § "Default lattice angle value".
- Macros: `macro Name(args) { ... }`, invoked as `Name(actual_args)`. Prefer an existing macro pattern over raw repeated blocks.
- **Converting a binary data file (`.raw`, etc.) to plain-text `.xy`: use TOPAS itself via `Out_X_Yobs`**, not a custom parser:
  ```
  iters 0
  xdd pbso4.raw
  Out_X_Yobs(pbso4.xy)
  ```
  `iters 0` skips refinement (pure format conversion); works for any format TOPAS's `xdd` reads natively. Run via `<TOPAS_DIR>\tc.exe` with the conversion file's full path.

  **You rarely need this.** TOPAS reads `.raw`, `.xye`, `.brml` and every other format `xdd` supports natively, so never convert in order to *fit*, and never convert in order to *plot a fit* — the refinement file itself writes Yobs when run at `iters 0` (see the Yobs/Ycalc/tick-output and `start_X` rules in `27-rietveld-workflow-conventions.md`). Reach for a standalone conversion only when an external, non-TOPAS tool needs plain text and no `.inp` for that data exists yet.

## Common errors to check for when debugging

- Missing semicolon at the end of an equation — especially easy to drop right before a `:` value-report.
- Unbalanced `{ }` — the most common source of cryptic parse failures.
- Forgetting to flag a parameter for refinement (no name, or accidentally leaving `!` on a parameter that should vary).
- Declaring a refinable value with a bare `prm` + equation instead of its subject-specific keyword (see the cheat sheet above) — quietly loses that keyword's built-in default `min`/`max`; check for unbounded wandering before assuming the problem is elsewhere.
- Using `str` when the phase should be `hkl_Is`/`xdd_Is` (or vice versa) — changes which keywords are valid and how intensity is calculated.
- Referencing a parameter name before it's defined, or reusing a name across scopes unintentionally.
- Mismatched data structure context for a keyword — verify against `21-keyword-index.md` which structure (`Ttop`, `Tglobal`, `Txdd`, etc.) a keyword actually belongs to.
- A dependent file from an earlier stage doesn't exist yet (e.g. a `.fc` file a later run expects) — TOPAS reports `Cannot open file ...` then `Abnormal program termination.`; check whether a prerequisite run needs to happen first.
- An invalid reserved-parameter/keyword combination — TOPAS reports the exact line and name (`Cannot locate X from Y in data structures`). See `references/console-output-and-errors.md` for real examples.

## When something isn't in the references

Before handing back an edited `.inp`, run `scripts/check_inp_syntax.py` as a final mechanical check. If asked about behavior, a keyword, or an example file not covered here, say so directly rather than fabricating manual content.

## Stripping refined-value errors (` `_err `) from an INP

A common cleanup request ("remove errors" — a standing trigger phrase) is removing every trailing `` `_<error> `` suffix from refined values (e.g. `48.0611197`_1.21585437` → `48.0611197`). Each occurrence has a different numeric error, so literal old-string/new-string text editing can't do this in one call.

**Use `scripts/remove_errors.py`** (a single regex pass, `` `_-?\d+\.?\d*(?:[eE][-+]?\d+)? ``):

```
python scripts/remove_errors.py file.inp                 # rewrite in place, whole file
python scripts/remove_errors.py file.inp --check          # preview to stdout, don't write
```

Prints how many suffixes were removed either way. Verify afterward with `check_inp_syntax.py`.

## Peak-picking and peak-fitting for indexing (visual method)

When no automated Peak-Search result is available and peaks need to be picked by eye from a plotted pattern before a peak-fit → indexing pipeline, this is an iterative process, not one-pass:

**1. Pick peaks at the best resolution available, not from a wide overview.** A single plot spanning 30-35 degrees at once visually compresses distinct peaks into what looks like one bump or an ignorable shoulder. Re-examine the whole candidate range in ~5-degree-wide windows with fine (0.1 degree) gridlines before trusting a peak list as complete.

**2. Distinguish a genuine second peak from a Cu Kα1/Kα2 instrumental doublet before adding it.** A Kα-doublet wavelength macro (`CuKa2_analyt`, `CuKa5`, etc.) already models the split within a single peak entry. Check by predicting the Kα2 companion's position via Bragg's law (`sin(θ_Kα2) = sin(θ_Kα1) × λ_Kα2/λ_Kα1`, ratio ≈1.002485 for Cu), which always places it at *higher* 2θ, growing with angle. A shoulder matching that direction/magnitude is Kα2 splitting, not a second reflection; a shoulder on the *wrong* (lower-2θ) side is real evidence of a second peak.

**3. After fitting, generate the calculated pattern with `Out_X_Ycalc(file)` and overlay it against the observed data — don't trust Rwp alone.** Add inside the `xdd { }` block after the `xo_Is`/`load xo I {}` block:
```
Out_X_Ycalc(output.xy)
```
The overlay should show no observed peak without a matching calculated one; add any newly-found peaks and refit until clean. A deceptively reasonable Rwp can still hide missed peaks, since Rwp doesn't localize *where* a fit is wrong the way a direct overlay does.

**4. Restrict `start_X`/`finish_X` to the region with usable peaks, and stop `finish_X` before peaks become poorly resolved.**
```
xdd pbso4.raw
   start_X 15.94
   finish_X 65
```
This alone can improve Rwp substantially by removing featureless regions from the weighted residual. For the upper cutoff, extend the range while neighboring peaks are still individually distinguishable; stop once they visibly blend together with no clean baseline between them.

**The full loop, in order**: plot at high resolution → pick peaks → build/refit with `start_X`/`finish_X` bracketing just the picked peaks → add `Out_X_Ycalc` and re-run → overlay calculated against observed → fix unmatched peaks or confirm the range boundary → repeat until clean → feed the final peak list into indexing (`load index_th2 index_I {}`).

## Building a supercell (enlarging the unit cell by an integer factor)

Two non-obvious things, both verified by actually running `tc.exe` (not derived from the manual alone):

- **`scale` must be divided by the volume ratio squared, not left unchanged.** Doubling `a`/`b`/`c` (volume ×8 for a ×2×2×2 supercell) does not preserve the calculated pattern if `scale` is left at its original-cell value (Rwp badly wrong, e.g. ~5827% vs. the correct ~9%). The correct relationship is `scale_new = scale_old / (V_new/V_old)^2` — a naive `|F|²/V²` first-principles argument predicts no change is needed and is wrong; trust the empirical result instead. `MVW`'s `cell_mass`/`cell_volume` need the same volume-ratio scaling for reported quantities to stay correct (doesn't affect the fit itself).
- **Keeping the original (higher-symmetry) space group instead of expanding to `P1` requires finding the space group's actual symmetry orbits, not listing every supercell atom** (which auto-generates duplicates under the real operators). Compute the space group's real operators, partition the full supercell atom-position set into orbits, and use one representative per orbit as the explicit `site`. Verify with `Out_CIF_STR` — its reported multiplicities should exactly match the orbit sizes computed independently. Lower the symmetry label only when genuinely needed, not as a default way to sidestep working out the orbits.

If debugging a supercell that doesn't reproduce the original pattern, isolate which half is wrong first: build a parallel `P1` version with every atom listed explicitly and compare its `iters 0` Rwp against the reduced-space-group version. If they match (both wrong or both right), the bug is in something shared (like `scale`), not the site-generator/orbit reduction.

## Converting a CIF file to `str` format

**Preferred: `python scripts/cif_to_str.py input.cif`** — a Wyckoff-constraint-aware converter, not a hand-derived field-by-field mapping and not `cif1.exe` (see below for why). Derives each site's coordinate constraints directly from the CIF's own `_symmetry_equiv_pos_as_xyz` operator loop — no external space-group table needed — distinguishing three cases per coordinate:

- **Free** (general position, or the one independent coordinate of a partial special position): emitted as `x @ 0.34131` (refined).
- **Fixed** (a symmetry operator pins it to an exact constant): emitted as a bare value, or as an exact `z = 5/6;` equation when it snaps to a common fraction — writing a rounded decimal instead (e.g. `z 0.833333`) produces a real TOPAS warning about the equivalent-position distance being off by a tiny but nonzero amount, so the exact-fraction form matters, not just style.
- **Tied to another coordinate of the same site** (e.g. a site on a mirror or 3-fold axis): emitted as `y = Get(x);`, the same mechanism `Cubic(cv)` uses internally (`b = Get(a); c = Get(a);`).

A hand- or tool-converted CIF that just writes three independent `x @ / y @ / z @` values for every site is silently wrong whenever a site sits on a special position — refinement is then free to pull tied coordinates apart, breaking the CIF's own symmetry. Validated (each cross-checked via `tc.exe` + `Out_CIF_STR`) against a fully-fixed cubic case, a Pa-3 case mixing fully-fixed/fully-general/3-fold-axis sites (correctly avoiding a circular `x=Get(y); y=Get(z); z=Get(x);` tie by picking one free representative), and a P3121 case requiring the general `(R-I)p ≡ -T (mod 1)` per-operator-row derivation rather than a naive "row i constrains coordinate i" heuristic (an operator's x-output row can actually constrain y alone).

**Lattice angles/lengths forced by the crystal class are handled the same way**: an angle forced to exactly 90° is omitted entirely (relying on TOPAS's 90° default), the class determined from the rotation parts of the CIF's own operators (proper 3-folds ≥8 → cubic; a 4-fold → tetragonal; a single 3-fold → trigonal/hexagonal, fixing `al`/`be` but not `ga`, since 120° isn't the default; axis-aligned 2-folds/mirrors → orthorhombic/monoclinic) — applied only if the CIF's stated value already agrees within tolerance, never silently forced. Lengths forced equal get the same `Get()`-tie treatment (`b = Get(a); c = Get(a);` for cubic; only `b` for tetragonal/hexagonal-axes-trigonal). **Known limitation**: generalizing by crystal class from the operators (not a per-space-group table) is verified only against cubic and standard-hexagonal-axes-trigonal cases, not all 230 groups or every alternate setting in `sgcom5.txt`. In particular, rhombohedral-axes settings (`a=b=c`, `al=be=ga` equal but not 90°) must be told apart from hexagonal axes by the CIF's own angle values, since a single 3-fold's rotation matrices can't distinguish them — that disambiguation exists for lengths, but not yet for tying the three oblique angles together.

**Fallback when the CIF itself has no `_symmetry_equiv_pos_as_xyz` loop**: resolve operators via TOPAS's own space-group database (`sgcom6.exe`/the `sg/` directory: `sgcom6 SYMBOL -dir sg`, must run with cwd = `TOPAS_DIR`). Checks whether `TOPAS_DIR/sg/<symbol>.sg` already exists first; a `.sg` file's `xyzs { }` block is in the exact same operator format as a CIF's own loop, so the same parsing pipeline handles both. One filename quirk: `sgcom6.exe` substitutes `o` for a literal `/` in the output filename (`p21/n` → `p21on.sg`), though the symbol field stored inside the file keeps the real `/`. Best-effort, not guaranteed — the symbol must already be in `sgcom6.exe`'s own concise form (`fm-3m`, not CIF's `F_M_3_M`); a failed resolution degrades to the same "verify manually" per-site warning as before. Every fallback-resolved conversion carries an explicit warning naming the `.sg` file used.

**ADP tensor constraints** (`u11`/`u22`/`u33`/`u12`/`u13`/`u23`) get the tensor analogue of the coordinate-tie treatment: a site's ADP tensor U must satisfy `R U R^T = U` for every rotation R in its stabilizer (translation is irrelevant for a tensor property). Unlike a coordinate's fixed value (derived from its own written number), an ADP's required value comes purely from the site's position, so a component with no free-variable dependence is always fixed at exactly zero (never some other constant) — verified end-to-end against real CIF data (ZrW2O8's 3-fold-axis sites), reproducing the CIF's own refined U values bit-for-bit via `Out_CIF_ADPs`. **An all-zero `_atom_site_aniso_*` row is treated as an unused placeholder, not real data** — a common convention where the real thermal-motion data actually lives in `_atom_site_B_iso_or_equiv` instead; the converter falls back to `beq` in that case rather than emitting a physically meaningless Get()-tied-together-zero tensor. This is correct for every real case seen so far, but a genuine (if physically unusual) refinement that converged to isotropic-zero anisotropic displacement would be misread the same way — a nonzero `beq`/`B_iso_or_equiv` alongside an all-zero aniso row is the giveaway to check by hand.

**Known limitations of `cif_to_str.py`** (be upfront about these when using its output):
- Coordinate-tie detection assumes integer -1/0/1 rotation-matrix entries; a row with 3+ nonzero entries, or 2 entries where neither is ±1, is flagged `'complex'` (independent value + a "verify manually" comment) rather than guessed at.
- If `_atom_site_type_symbol` is missing, the element is guessed from the site label (stripping trailing digits) and flagged with a warning — verify against actual CIF chemistry.
- Cross-checks the CIF's stated site-symmetry multiplicity against the independently-computed orbit size; a mismatch scales the occupancy and warns (possible disorder/split site) rather than silently trusting either number.
- Not a general CIF-dictionary parser — built for the specific constructs a `str` conversion needs; unusual CIF formatting may not parse. Always verify via `check_inp_syntax.py` and a real `tc.exe` run with `Out_CIF_STR`.
- The `sgcom6.exe` fallback needs `TOPAS_DIR`; without it, a CIF missing its own operator loop degrades to the "can't derive constraints" per-site warning.

### `cif1.exe` (TOPAS's own bundled converter — fallback / comparison only)

A real, standalone utility bundled with every TOPAS install, doing a straightforward field-by-field CIF→`str` conversion — but **not Wyckoff-aware**, so it will happily emit three independent free values for a site that actually needs a `Get()`-based constraint. Prefer `cif_to_str.py`; fall back to `cif1.exe` only as a second opinion. (`pdb_cif_to_str_file`, `references/18-protein-refinement.md`, is a different tool again, built for protein-scale PDBx/mmCIF files from RCSB PDB, not general small-molecule/inorganic CIFs.)

Usage (needs the resolved TOPAS install dir, `python scripts/topas_install.py --inc-dir`):

```
cif1.exe input.cif output.inp
```

Two things worth knowing about its output: `volume` is a real, valid (if undocumented in this skill's own keyword index) TOPAS keyword — confirmed by running raw `cif1.exe` output through `tc.exe` with zero error; and `phase_name` can inherit garbage straight from an under-filled CIF field (e.g. the literal string `"?CeO2?"`, CIF's own "value not specified" placeholder carried through verbatim) — check and clean this up by hand rather than trusting it blindly. `cif1.exe`'s output is deliberately generic: explicit `a`/`b`/`c`/`al`/`be`/`ga` rather than a symmetry-shorthand macro, and no `scale` at all (left for you to add).

## Maintaining this skill

`references/maintenance.md` — playbooks for updating `references/paper-summaries.md` from new algorithm PDFs, and for rebuilding these reference files from a revised Technical Reference (DOCX/PDF extraction, keyword character styles, heading/indent recovery, verification traps). Only needed when revising the skill itself.
