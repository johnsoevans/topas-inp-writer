---
name: topas-inp-writer
description: Write, edit, and debug TOPAS-Academic (Bruker AXS) .inp refinement scripts for X-ray/neutron powder diffraction, PDF, indexing, charge-flipping, stacking-fault analysis, and (Version 9) modulated/incommensurate structures and 3D electron diffraction. Use this skill whenever the user mentions TOPAS, a .inp file, Rietveld/Pawley/Le Bail refinement, structure/PDF/quantitative-phase refinement scripting, or pastes TOPAS syntax (site, str, hkl_Is, xdd, prm, macro, Rwp, beq, occ, etc.) and wants it written, explained, fixed, or extended. Make sure to trigger this even if the user only pastes a fragment of TOPAS syntax or an error message without explicitly naming "TOPAS" or "INP file" — recognizable keywords or diffraction-refinement context are enough.
---

# TOPAS INP Writer

TOPAS-Academic's INP format is a macro-driven language of nested `{ }` blocks of keyword/value pairs. This skill packages the Technical Reference Manual as reference files so you can write and debug INP syntax without guessing keyword names or semantics. The references are prose-extracted, so originally typeset equations may be approximate — when an exact functional form matters, flag the uncertainty rather than presenting it as verbatim manual text.

**Running the scripts:** examples are written `python scripts/…` (Python 3). Settle the launcher once per session: try `python --version`, then `py`, then `python3`, and keep the first that prints `Python 3.x`. A Windows `python`/`python3` that prints no version is a Microsoft Store alias — skip it.

## How to use this skill

1. **Identify the task first** — the same keyword behaves differently in `str`, `hkl_Is`, `xdd_Is`, Pawley, indexing or PDF. For a brand-new `.inp` whose run type isn't obvious, ask (see "Starting a new INP file from scratch").
2. **Check `example_inp_files/example_inp_files_index.md` first** (bundled, commented, working files), then `references/examples-index.md` (install examples, resolved via `python scripts/topas_install.py --example <path>`, e.g. `cf/alvo4a.inp`, then opened with `Read`/`Grep`). Copying a real example's structure beats writing from scratch. If `TOPAS_DIR` is unset or the file doesn't resolve, say so — never invent content.
3. **Read only the matching reference file(s)** for syntax rules; don't rely on general crystallography knowledge for TOPAS keyword names, attributes or macro behavior.
4. **Combine both**: manual chapters give the rules, examples show real usage; cross-check anything unfamiliar in an example against the manual.
5. **When debugging**, start with "Common errors" below, then `references/01-syntax-and-parameters.md` and `02-equation-operators-and-functions.md`, and compare against a similar example.
6. **State uncertainty plainly** rather than presenting a guess as documented behavior.
7. **Run `scripts/check_inp_syntax.py` before handing over any finished or edited `.inp`.**
8. **When summarizing/reviewing an `.inp`/`.out`, flag `CS_L`/`CS_G` (`csl`/`csg`) values above ~500**: FWHM ∝ 1/value, so sensitivity fades past that, typically showing as a large error and strong `csl`↔`csg` anti-correlation in `C_matrix_normalized` (`references/04-peak-generation-and-peak-type.md` § "CS_L / CS_G: FWHM is proportional to 1/value").

**Version 9 features.** Modulated structures (`references/30`) and electron diffraction (`references/31`) exist only in Version 9. Before writing their keywords, establish the version (first console line: `TOPAS-64 Version 9.x ...`); if earlier or unknown, say these need Version 9 rather than writing a file that will be refused.

## Starting a new INP file from scratch — clarifying questions

For a brand-new `.inp` whose run type isn't clear, ask the top-level branch first (`AskUserQuestion` if available), then only that branch's follow-ups.

**1. What kind of run is this?**

| Answer | Covers | Reference(s) |
|---|---|---|
| Rietveld (known structure) | Refine coordinates/occupancies/ADPs | `01`, `03`, `04`, `05` |
| Pawley / Le Bail | Intensities from cell + symmetry only | `01`, `04` (`hkl_Is`/`xdd_Is` vs `str`) |
| Indexing | Unit cell from peak positions | `14` |
| PDF — generation | Raw data → G(r) | `08` |
| PDF — refinement | Structure against existing G(r) | `09` |
| Charge flipping / ab initio | Solve with no starting model | `22` |
| Quantitative phase analysis | Weight fractions of known phases | `11` (usually on a Rietveld fit) |
| Stacking faults | Layer/fault-sequence modeling | `10` |
| Rigid bodies | Fragments moved as a unit | `13` (on Rietveld or PDF) |
| Deconvolution | Instrumental vs sample broadening | `07` |
| Energy minimization / MD | Optimization by potential energy | `15`, `16` |
| Protein refinement | Charge flipping or Rietveld at protein scale | `18`, `19` |
| Magnetic structure | Magnetic scattering/ordering | `12` |
| Modulated structure (V9) | Satellites, powder or single crystal | `30` |
| Electron diffraction, dynamical (V9) | 3D ED frames from PETS2, Bloch wave | `31` |

If the answer spans two (index then Rietveld; generate then refine a PDF), plan a multi-stage pipeline rather than dropping a stage (see the peak-picking section below, or `Include_PDF_Generate` in `08`/`09`).

**2. Follow-ups by branch:**

- **Rietveld:** structure known (CIF, or space group + atoms)? Single or multi-phase? Lab X-ray (which tube), synchrotron, or neutron CW/TOF (changes the peak-shape family, `04`)? Fundamental parameters (`axial_conv`, `Radius`, `Slit_Width`, `LP_Factor`) or empirical (`TCHZ_Peak_Type`, PV)? Extras — preferred orientation, anisotropic broadening, rigid bodies, amorphous background? `do_errors`?
- **Pawley/Le Bail:** starting cell and space group — from indexing, literature, or rough estimate?
- **Indexing:** existing peak list or peak search first? Prior knowledge — max d-spacing, min lattice parameter, crystal system?
- **PDF:** r-range and Q_max? Lab or synchrotron/neutron (affects `dQ_damping`/`convolute_Qmax_Sinc`)? For refinement: `beq`/`pdf_for_pairs` broadening or ADPs?
- **Charge flipping:** single crystal or powder? Space group known? Protein-scale?
- **Quant:** which phases; layered on an existing fit or built fresh?
- **Stacking faults:** layer types/count; testing a given fault probability/sequence or searching?
- **Modulated:** version 9? Powder or single crystal? Superspace group symbol, or a JANA/ISODISTORT CIF with operators? Number of modulation vectors and satellite order? What is modulated (displacement, occupancy, ADP, moment), any crenels?
- **Electron diffraction:** version 9? PETS2 `.cif_pets` file(s) and a starting model (CIF or JANA)? Continuous rotation or precession? One crystal or several? Acentric (then both hands are refined with `ed_invert_hand`)?

**3. Once the type is settled, for nearly every branch:** data file path/format, radiation/wavelength if not implied, outputs (`do_errors`, CIF/pdCIF, plots).

## Locating your TOPAS installation

The skill doesn't bundle the `.inc`/`.txt` system files or install examples (they'd go stale). **Set `TOPAS_DIR` to the TOPAS install root** (or any ancestor of `tc.exe`/`TA.EXE`); `scripts/topas_install.py` resolves:

```
python scripts/topas_install.py --inc-dir                  # .inc macro library directory
python scripts/topas_install.py --example cf/alvo4a.inp    # an example file's real path
python scripts/topas_install.py --kernel-schema-html        # the "Show Schema" page
python scripts/topas_install.py --technical-reference-pdf   # the manual PDF
python scripts/topas_install.py --macro-browser-html        # macro browser page
python scripts/topas_install.py --keyword-tree-html         # keyword tree page
```
The last three are found only if the install includes them.

**Running `tc.exe`:** `<TOPAS_DIR>\tc.exe "<full path to the .inp>"`, both absolute — it is not on `PATH` and resolves relative paths (the `.inp`, `xdd`, `#include`) against the cwd. **Put `TOPAS_DIR` on `PATH` for the run:** `tc.exe` calls `sgcom6` by bare name, so otherwise any space group not already compiled to `sg/*.sg` aborts with `Cannot open file ...\sg\<group>.sg`. Scripts that run `tc.exe` do this through `topas_install.tc_env()`. **One run at a time:** it is single-instance, so a second launch aborts (`This is a single instance application`) with no `.out`. Run batches in a serial loop, never in parallel, and wait for any run already in progress. **No dots in `.inp` names you generate:** TOPAS cuts output names at the first dot (`a_17.3.inp` writes `a_17.out`), so write `a_17p3.inp`.

**Don't pre-check `TOPAS_DIR` yourself** — `check_inp_syntax.py` and `expand_inp_macros.py` print a one-line stderr note confirming the install; call the tool you need and raise `TOPAS_DIR` only if a script reports it missing.

**Without `TOPAS_DIR`**, these degrade cleanly: `check_inp_syntax.py`'s macro-arity check (and, silently, its symmetry check); library-macro expansion in `expand_inp_macros.py` (file-local macros still expand); reading worked-example source (index descriptions remain); "Show Schema" (no fallback). Tell a colleague plainly what setting it unlocks.

## Reference file map

Open only what's relevant.

**Core syntax — almost any INP task:**
- `references/01-syntax-and-parameters.md` — naming, `@`/`!` flags, `prm`/`local`, attributes (`min`, `max`, `del`, `update`, `stop_when`, `val_on_continue`), constraints, equations.
- `references/02-equation-operators-and-functions.md` — operators and built-in functions in `= ... ;`.
- `references/06-macros-and-include-files.md` — `macro`, `#include`, `.inc` files.

**Refinement mechanics:**
- `references/03-minimization-and-convergence.md` — minimization, convergence, `iters`, `num_cycles`, stability.
- `references/04-peak-generation-and-peak-type.md` — emission profiles, `peak_type` (FP, PV, SPVII, SPV, TCHZ), convolutions, peaks buffer.
- `references/05-reusing-objects-large-refinements.md` — large/multi-phase refinements without duplication.

**Specialized (open only the matching one):**
- `07-deconvolution.md`
- `08-pdf-generation.md` / `09-pdf-refinement.md` — **generating** G(r) is `Include_PDF_Generate` in `08` (operation 0 = fit raw pattern, 1 = generate F(Q)/G(r); examples `pdf-generate/*/decon.inp`); **refining** against existing G(r) uses `pdf_data` directly (`09`; examples `pdf/beq-2.inp`, `pdf-1.inp`, `pdf-2.inp`). One file can do both via operations 0/1 then 2 (`pdf-generate/LiFePO4/decon.inp`). Also ADP_5/ADP_7 beq-type sites.
- `10-stacking-faults.md` — `layer`, `stack`, `generate_stack_sequences`, transition matrices.
- `11-quantitative-analysis.md` — QUANT, weight percents, `dummy_str`, elemental composition.
- `12-magnetic-structure-refinement.md`, `13-rigid-bodies.md`, `14-indexing.md`
- `15-energy-minimization.md`, `16-molecular-dynamics.md`
- `17-amazon-ec2-cloud-computing.md` — TOPAS on AWS.
- `18-protein-refinement.md`, `19-solving-proteins-atomic-resolution.md`, `22-charge-flipping.md`
- `25-symmetry-mode-refinement.md` — distortion/symmetry-mode refinement (ISODISTORT `.STR`, mode amplitudes, GA/inclusion/exhaustive search). From Dinnebier/Leineweber/Evans (2018) drafts, not the manual.
- `26-parametric-and-sequential-refinement.md` — sequential vs parametric ("surface") refinement of pattern series: `#list`/`Run_Number`, the disappearing-phase failure mode, functional forms, R-factor diagnostic for a bad parametric model.
- `27-rietveld-workflow-conventions.md` — **read for any Rietveld/Pawley/quant session, and always before a final report.** Practical conventions: wavelength/monochromator, peak-shape families with wavelength macros and `Simple_Axial_Model()`, 2θ range and ADP strategy, staged refinement, saturated terms, the mandatory false-minimum re-check, Pawley-from-converged-`str`, report formatting, quant (screening, `weight_percent`/`elemental_composition`, pie chart). Rules carry tags `(R1)`, `(R2)`, … — **never cite a rule number outside that file** (not in `SKILL.md`, other references, scripts, examples or tests); it renumbers, so refer by topic. The synchrotron section is thin and the neutron heading an unpopulated placeholder.
- `28-z-matrix-rigid-body-conventions.md` — z-matrix rigid-body building conventions (used with `scripts/rigid_body_builder.py`).
- `29-indexing-workflow-conventions.md` — **read for any peak-search/peak-fitting/indexing/Pawley session.** Same kind of file and same no-external-citation rule; two sequences, `(FI…)` peak fitting and `(IN…)` indexing.
- `30-modulated-structures.md` — **V9 only.** Modulation vectors, superspace symmetry (`mod_tau`, symbols, CIF operators), displacive/occupancy/ADP/moment modulation, crenel/sawtooth/Legendre, one str per satellite order, single-crystal files, twins, extinction, msCIF, messages.
- `31-electron-diffraction.md` — **V9 only.** Dynamical 3D ED from PETS2: `#inp_from_cif_pets`, `ed_crystal`/`xdd_ed`, beam selection, Bethe potentials, thickness, absorption, partial charges, frame orientation, `ed_invert_hand`, `r_f`, messages.

**Worked examples:**
- `example_inp_files/example_inp_files_index.md` — bundled, no `TOPAS_DIR` needed; check first.
- `references/examples-index.md` — install examples (V7–9) by path and topic (incl. `cf/`, `cf-protein/`, `indexing/`); needs `TOPAS_DIR`. Folder names hint at refinement type.

**Diagnostics and techniques:**
- `references/console-output-and-errors.md` — run output, iteration-log columns, real errors, `num_runs` vs `continue_after_convergence` (the latter running long is by design).
- `references/restraints-and-penalties.md` — `Distance_Restrain`/`Angle_Restrain`; turning `append_bond_lengths` output into `LABEL opidx offx offy offz` arguments (space-separated, not colon-joined); **mandatory zero-weight check of every `Angle_Restrain` target before refining — never hand-derive a 90°/180° target by eye**; weighting; `penalties_weighting_K1`.
- `references/macro-expansion-and-log-files.md` — `tc.log` as the fully expanded INP, `at LINE N` numbering, macro-substitution mechanics, expansions of `STR`, `XDD`, `LP_Factor`, `PV_Peak_Type`.
- `references/paper-summaries.md` — the papers behind TOPAS's algorithms (FP peak shapes, charge flipping, stacking faults, indexing, PDF, WPPM, minimizers, axial divergence, capillary, LPSD, simulated annealing, symbolic system). For *why*; no PDFs bundled (`papers-index.md`).
- Dinnebier, Leineweber & Evans (2018) draft chapters enriched the skill; search for "not in the Technical Reference manual" to see what's already extracted.

**Lookup:**
- `references/scripts.md` — full usage, options and limitations of every script in `scripts/`.
- `references/system-files-index.md` — what each `.inc` library (incl. auto-included `topas.inc`) and `.txt` data table contains; check the real `topas.inc` before assuming a macro is undefined.
- `references/21-keyword-index.md` — keywords by data structure (`Ttop`, `Tglobal`, `Txdd`, …): does it exist, where is it valid.
- `references/20-miscellaneous.md` (form factors, PDB import, threading, background stability, seeding), `23-gui-functionality.md`, `00-introduction.md`, `24-bibliography.md`.

## Scripts

**Full usage, options and limitations of every script are in `references/scripts.md` — read a script's entry there before its first use in a session.** Examples are run as `python scripts/<name>.py`.

`fix_columns.py`, `format_inp_hierarchy.py`, `insert_adps.py` and `remove_errors.py` **rewrite in place with no backup** — preview with `--check` unless the `.inp` was just copied from a `.out`.

**Always:**
- `check_inp_syntax.py` — run before handing over any `.inp`. **Pass all files in one invocation** (paths or a directory). A trailing token that isn't a file is appended as INP text, so **a mistyped second path is not an error** — check the `[+cmdline: ...]` tag.
- `cif_to_str.py` — every CIF → `str` conversion (see "Converting a CIF file to `str` format").
- `rigid_body_builder.py` — every rigid body (`--analyse`, `--build`, `--verify`, `--risk`), following `references/28-z-matrix-rigid-body-conventions.md`.
- `peak_search.py`, `group_cells.py`, `compare_cells.py` — peak search and indexing, following `references/29-indexing-workflow-conventions.md`.

**Standing triggers — run the script whenever the user:**

| User says / asks for | Script |
|---|---|
| the independent/refinable parameters in a `.inp` | `find_refined_params.py` |
| several model variants of one `.inp` compared (peak shapes, PO, background order, ADP schemes, the false-minimum reset check, phase screening) | `run_variants.py` — reports numbers, chooses nothing |
| a parameter dependency tree/graph, or "do trees" | `param_dependency_trees.py` — interactive HTML by default (`-o <name>.html`), text only if asked |
| "Show Schema" | `topas_install.py --kernel-schema-html`; if not found, say so — no bundled fallback |
| a 3D view of a `str` phase | `plot_str_3d.py` |
| a spherical-harmonics series as a pole figure or 3D surface | `plot_sh_sphere.py` — **keep its "not extensively tested" banner** |
| a plot of an XY(E) file | `plot_xy.py` (see "Run and plot" below) |
| the final report as `.docx` | `build_report_docx.py` — don't hand-format a `.docx` or use `pandoc` |
| "fix columns", or aligned `site` lines | `fix_columns.py` |
| a `.inp` reindented "hierarchically" | `format_inp_hierarchy.py` |
| "remove errors" | `remove_errors.py` (see "Stripping refined-value errors") |
| "insert adps" | `insert_adps.py` |
| a template/example/starting point ("tof template") | `find_example.py` |

**Other tools:** `expand_inp_macros.py` (approximate `tc.log` expansion without running TOPAS; for tracing `at LINE N`), `c_matrix_heatmap.py` (HTML is the better default), `plot_xy_matplotlib.py` (PNG/JPG for reports), `to_Reel_v1.py` (**copy it into the project directory first**), `topas_install.py` (install paths). `symmetry_utils.py` is a library; `symmetrize_str.py` and `generate_space_group_browser.py` are not chat-facing.

General rule: text reports open in VS Code, HTML in the browser.

**"Run and plot [file]" is a standing workflow** for looking at a fit without changing it. A refinement session instead copies the `.out` back over the `.inp` after every run (the copy-back rule in `27`). (1) Run `tc.exe` on a scratch copy, never the original; (2) if `Out_X_Ycalc`/`Out_X_Yobs` are missing, warn and add them to the copy, and for Rietveld/Pawley also `Create_hklm_d_Th2_Ip_file(ticks.txt)` inside each `str`/`hkl_Is` (one tick file per phase; see the default-ticks rule in `27`); (3) plot Yobs, Ycalc and difference with `--stats` from the `.out`'s `r_wp`/`gof` (and `r_p` if relevant) and `--ticks`; (4) one plot per `xdd` by default, unless the user says **"fit show in one plot"** — then combine via `--phases`. Multi-phase reminders: one value per parameter name globally (reusing `CS_L(csl, ...)` at different values aborts with `Parameter csl is defined more than once...`); a relative data filename in `DAT`/`XDD`/`RAW` resolves against the `.inp`'s directory, so a scratch copy elsewhere needs its data alongside.

## Core syntax cheat sheet

- Blocks use `{ }`; comments `'` to end of line.
- Parameter names: letters, digits, underscore, not starting with a digit. `!` fixes; `@` auto-names.
- **`bkg` takes one `@` for the whole list**: `bkg @ 0 0 0 0 0 0`, never `@` per value (unlike macro calls, which take one per slot).
- **Name a parameter plainly, not glued to `@`:** `beq b1 0.5` (naming flags it for refinement). `beq @b1 0.5` is accepted but unidiomatic. Use bare `@` (`x @ 0.844`) only when no readable name is wanted.
- `prm name value` declares a standalone parameter; add `min`, `max`, `update`, `stop_when` as needed.
- **Prefer the subject-specific keyword over a bare `prm`** for any refinable value that has one — keywords carry documented default `min`/`max` (Table 2-1 in `01`) that `prm` + equation discards, and `topas.inc` supplies bounds for its own `prm`s. Keep those bounds when hand-expanding a macro; if `topas.inc` can't be read, add a reasoned placeholder and say so. Cubic example: `a prm_name 4.56` / `b = Get(a);` / `c = Get(a);` — not `prm prm_name 4.56` with `a`/`b`/`c = prm_name;`. A genuinely needed bare `prm`/`local` gets explicit `min`/`max`.
- Equations start `=` and end `;` — mandatory even before a `:` report: `prm bb = cs1 + cs2; : 0`, not `prm bb = cs1 + cs2 : 0`.
- A trailing `: 0` after an equation's `;` makes TOPAS write back its value (and error with `do_errors`), even for an unnamed equation (`prm = 2 a1^2 + 3; : 0;`).
- `str { ... }` holds `site`s (`x y z occ beq`); intensity-only phases use `hkl_Is`/`xdd_Is`.
- **`al`/`be`/`ga` default to 90° in any `str`**, whatever the space group (incl. `P1`) — don't write `al 90 be 90 ga 90`.
- Macros: `macro Name(args) { ... }`, called as `Name(...)`; prefer an existing macro over repeated raw blocks.
- **`macro & Name(...)` wraps every expansion in parens; `& arg` wraps that argument's value.** Not cosmetic — without it `divide(a + b, c - d)` expands to `a + b / c - d`.
- **`#include` resolves from the INP file's own directory** unless a full path is given (recursively, for system and project files), falling back to the system library only for a bare name not found locally.
- **`Get(name)` reaches only the enclosing object's structural slot** (`x`/`y`/`z`/`u11`..`u23`/`occ`/`beq` on a site; `a`..`ga`/`scale`/`space_group` on a `str`) — **never a `prm`/`local`**: `beq = Get(b1);` fails (`Cannot locate b1 from beq in data structures`); write `beq = b1;`.
- **A coordinate without `!` is a general position whatever its value** (`x xti1 0` is general even at the origin); only all-`!`-fixed coordinates enforce a special position.
- **Binary → plain-text `.xy`: use TOPAS's `Out_X_Yobs`**, not a custom parser, run with `<TOPAS_DIR>\tc.exe` on the file's full path:
  ```
  iters 0
  xdd pbso4.raw
  Out_X_Yobs(pbso4.xy)
  ```
  **Rarely needed** — `xdd` reads `.raw`, `.xye`, `.brml` etc. natively, so never convert to fit or to plot a fit (the refinement writes Yobs at `iters 0`; see `27`). Only for an external tool needing text when no `.inp` exists yet.

## Common errors to check for when debugging

- Missing `;` ending an equation — especially before a `:` report.
- Unbalanced `{ }` — the commonest cause of cryptic parse failures.
- A parameter not flagged for refinement (no name, or a stray `!`).
- A bare `prm` + equation instead of the subject keyword — loses default bounds; check for unbounded wandering.
- `str` where `hkl_Is`/`xdd_Is` was needed, or vice versa.
- A name referenced before definition, or reused across scopes unintentionally.
- A keyword in the wrong data structure — check `21-keyword-index.md`.
- A prerequisite file from an earlier stage missing (e.g. a `.fc`): `Cannot open file ...` then `Abnormal program termination.`
- Invalid reserved-parameter/keyword combination: `Cannot locate X from Y in data structures` (`references/console-output-and-errors.md`).

## When something isn't in the references

Say so directly rather than fabricating manual content.

## Stripping refined-value errors (` `_err `) from an INP

"remove errors" (standing trigger) strips every `` `_<error> `` suffix (`48.0611197`_1.21585437` → `48.0611197`) in one regex pass; each error differs, so literal find/replace can't.

```
python scripts/remove_errors.py file.inp            # in place
python scripts/remove_errors.py file.inp --check    # preview
```

Reports the count; verify with `check_inp_syntax.py`.

## Peak-picking and peak-fitting for indexing (visual method)

The peak-fitting and indexing method — peak search, residual mining, classification, contamination checks, indexing, Pawley — is in `references/29-indexing-workflow-conventions.md`. When peaks must also be picked by eye:

1. **Pick at fine resolution** — re-examine the range in ~5° windows with 0.1° gridlines; a 30–35° overview merges distinct peaks.
2. **Don't add a Kα2 shoulder as a peak.** The doublet macro (`CuKa2_analyt`, `CuKa5`, …) already models it. Kα2 lies at *higher* 2θ: `sin θ_Kα2 = sin θ_Kα1 × 1.002485` (Cu), growing with angle. A lower-2θ shoulder is a real second peak.
3. **Cu Kβ and W Lα lines sit at *lower* 2θ** than their parent: `sin θ = sin θ_Kα1 × ratio`, Kβ 1.39222 Å (0.9037), W Lα 1.47642 Å (0.9583, aged tube). Remove one only on the corroboration tests in `29`; never remove a strong line on position alone.
4. **Bracket with `start_X`/`finish_X`** to the usable range, stopping `finish_X` once neighboring peaks blend with no clean baseline:
   ```
   xdd pbso4.raw
      start_X 15.94
      finish_X 65
   ```

Then fit and check the overlay as in `29`, and feed the list to indexing (`load index_th2 index_I {}`).

## Building a supercell (enlarging the unit cell by an integer factor)

Both verified by running `tc.exe`:

- **`scale_new = scale_old / (V_new/V_old)^2`** — leaving `scale` unchanged gives a badly wrong Rwp (naive `|F|²/V²` reasoning says no change; it's wrong). `MVW`'s `cell_mass`/`cell_volume` need the same scaling for reported quantities.
- **To keep the original space group (not `P1`), list one representative per symmetry orbit**, not every supercell atom (which duplicates under the operators). Verify with `Out_CIF_STR` multiplicities = orbit sizes. Lower symmetry only when genuinely needed.

To debug, compare `iters 0` Rwp of an explicit all-atom `P1` version against the reduced version: if they agree, the bug is shared (e.g. `scale`), not the orbit reduction.

## Converting a CIF file to `str` format

**Use `python scripts/cif_to_str.py input.cif`**, not a hand mapping or `cif1.exe`. It derives constraints from the CIF's `_symmetry_equiv_pos_as_xyz` loop, per coordinate:

- **Free** → `x @ 0.34131`.
- **Fixed** → bare value, or an exact fraction `z = 5/6;` (a rounded `0.833333` triggers a real TOPAS equivalent-position warning).
- **Tied** → `y = Get(x);` (as `Cubic(cv)` does internally).

Writing independent `x @ / y @ / z @` for a special-position site is silently wrong — refinement breaks the symmetry.

**Lattice:** angles forced to 90° are omitted; trigonal/hexagonal fixes `al`/`be` but writes `ga`; forced-equal lengths are tied (`b = Get(a); c = Get(a);` cubic; `b` only for tetragonal/hexagonal). Applied only if the CIF's values already agree. **Limitation:** verified for cubic and hexagonal-axes trigonal only; rhombohedral-axes settings get length ties but not yet the three oblique angles tied.

**No operator loop in the CIF:** falls back to TOPAS's database (`sgcom6 SYMBOL -dir sg`, cwd = `TOPAS_DIR`; reuses an existing `sg/<symbol>.sg`). `/` becomes `o` in the filename (`p21/n` → `p21on.sg`). Needs the concise symbol (`fm-3m`, not `F_M_3_M`); best-effort, warns naming the `.sg` used, and degrades to a per-site "verify manually" warning.

**ADPs** get the tensor analogue (`R U Rᵀ = U` over the site stabilizer; non-free components are exactly zero). **An all-zero `_atom_site_aniso_*` row is treated as a placeholder** and `beq` from `_atom_site_B_iso_or_equiv` is used instead — a nonzero `B_iso` beside an all-zero aniso row is the case to check by hand.

**Known limitations** (state them when using its output):
- Rotation rows with 3+ nonzero entries, or 2 with neither ±1, are flagged `'complex'` (independent value + "verify manually").
- Missing `_atom_site_type_symbol` → element guessed from the label, with a warning.
- A CIF multiplicity that disagrees with the computed orbit scales the occupancy and warns (possible disorder/split site).
- Not a general CIF parser; verify with `check_inp_syntax.py` and a `tc.exe` run with `Out_CIF_STR`.
- The `sgcom6.exe` fallback needs `TOPAS_DIR`.

### `cif1.exe` (TOPAS's own bundled converter — fallback / comparison only)

Field-by-field and **not Wyckoff-aware** (emits free values where `Get()` ties are needed) — second opinion only. (`pdb_cif_to_str_file`, `18-protein-refinement.md`, is for protein mmCIF.) Run from the install dir (`python scripts/topas_install.py --inc-dir`):

```
cif1.exe input.cif output.inp
```

Its `volume` keyword is valid; `phase_name` can carry CIF placeholder junk (`"?CeO2?"`) — clean it. Output uses explicit `a`..`ga` (no lattice macro) and no `scale` (add one).

## Maintaining this skill

`references/maintenance.md` — playbooks for updating `paper-summaries.md` from new PDFs and rebuilding references from a revised Technical Reference. Only for revising the skill itself.
