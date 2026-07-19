---
name: topas-inp-writer
description: Write, edit, and debug TOPAS-Academic (Bruker AXS) .inp refinement scripts for X-ray/neutron powder diffraction, PDF, indexing, charge-flipping, and stacking-fault analysis. Use this skill whenever the user mentions TOPAS, a .inp file, Rietveld/Pawley/Le Bail refinement, structure/PDF/quantitative-phase refinement scripting, or pastes TOPAS syntax (site, str, hkl_Is, xdd, prm, macro, Rwp, beq, occ, etc.) and wants it written, explained, fixed, or extended. Make sure to trigger this even if the user only pastes a fragment of TOPAS syntax or an error message without explicitly naming "TOPAS" or "INP file" — recognizable keywords or diffraction-refinement context are enough.
---

# TOPAS INP Writer

TOPAS-Academic is Bruker's diffraction-analysis program. Its input language (the "INP" format) is a macro-driven scripting language for describing samples, refinement objects, and equations, built on nested `{ }` blocks of keyword/value pairs. This skill packages the TOPAS Technical Reference Manual as a set of reference files so you can write correct, idiomatic INP syntax and debug existing scripts without guessing at keyword names or semantics.

This skill was distilled from a full copy of the Technical Reference; it captures the syntax rules and worked examples faithfully, but the reference files are prose-extracted from the manual, so equations that were originally typeset (e.g. as embedded math objects) may render as plain text approximations. When precision matters (e.g. an exact functional form), say so and flag the uncertainty rather than presenting it as verbatim manual text.

## How to use this skill

1. **Identify what the user is actually trying to do** before writing anything — the same keyword can behave differently depending on which data structure (`str`, `hkl_Is`, `xdd_Is`, Pawley, indexing, PDF) it's used in. When starting a brand-new `.inp` from scratch (no existing file to extend) and the run type isn't already obvious from context, ask — see "Starting a new INP file from scratch" below.
2. **Check `example_inp_files/README.md` first** for a hand-picked, carefully annotated, real working `.inp` file close to the task — these are curated for clean layout and heavy inline commenting and are a better style/structure model than a bare syntax demo. If nothing there is close enough, fall back to `references/examples-index.md` for a real, complete INP script close to the task, then resolve and read the actual file via `TOPAS_DIR` (see "Locating your TOPAS installation") — this skill does not bundle those example files themselves, only this curated index of what each one demonstrates. A real worked example is almost always a better starting point than writing from scratch — copy its structure and adapt names/values/macros to the user's case. To read one: `python3 scripts/topas_install.py --example <relative-path-from-the-index>` (e.g. `cf/alvo4a.inp`) prints its resolved location on disk, which you then open with `Read`/`Grep`. Most examples (198 of 280) have a matching `.out` file alongside the `.inp` (resolve the same way, with a `.out` extension) — read both together to see exactly what refining changes: placeholder values get replaced with refined ones, each carrying an uncertainty via a trailing backtick (e.g. `beq @ 0.19987`_0.00463`). If `TOPAS_DIR` isn't set or the file doesn't resolve, say so plainly rather than inventing file content.
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

**Set the `TOPAS_DIR` environment variable to the root of your TOPAS installation** (wherever `tc.exe`/`TA.EXE` live, or any ancestor directory). `scripts/topas_install.py` searches under it (once per session, cached) to resolve:

```
python3 scripts/topas_install.py --inc-dir                  # the real .inc macro library directory
python3 scripts/topas_install.py --example cf/alvo4a.inp    # a specific example file's real path
python3 scripts/topas_install.py --kernel-schema-html        # the pre-rendered "Show Schema" page
python3 scripts/topas_install.py --macro-browser-html        # a generated macro-browser page, if one exists yet
python3 scripts/topas_install.py --technical-reference-pdf   # the manual PDF (used for §21.2 macro descriptions)
python3 scripts/topas_install.py --keyword-tree-html         # a generated keyword-hierarchy page, if one exists yet
```

`check_inp_syntax.py` and `expand_inp_macros.py` both call this automatically and print a one-line note to stderr confirming they found your install.

**Without `TOPAS_DIR` set**, six things degrade cleanly rather than silently: `check_inp_syntax.py`'s macro-arity check (its other checks are unaffected); `expand_inp_macros.py`'s expansion of library macros (macros defined in the file itself still expand); reading the literal content of a worked example (the index's topic descriptions remain available, just not the source to copy from); "Show Schema" (no bundled fallback at all); `generate_macro_browser.py` (exits immediately, needs the real `.inc` library); `topas_keyword_tree.py` (needs `-o` given explicitly). If a colleague doesn't have `TOPAS_DIR` set, tell them plainly what it unlocks rather than guessing at file contents.

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

**Curated worked examples (bundled directly with this skill, no `TOPAS_DIR` needed):**
- `example_inp_files/README.md` — a lookup table of the real, working `.inp` files kept in that same folder (Rietveld templates and real fits, indexing, peak-fitting, simulation, parametric/variable-temperature multi-pattern refinement), each self-documented in its own header comment. Check this before the bundled-install examples below.

**Worked examples (real, complete INP scripts — require `TOPAS_DIR`):**
- `references/examples-index.md` — a categorized table describing all 280 example files by relative path, grouped by folder, with heuristically-detected topics per file. Start here to find a close analog, then resolve via `python3 scripts/topas_install.py --example <path>`. Includes dedicated `cf/` (charge-flipping), `cf-protein/`, and `indexing/` folders. Folder names are often a strong hint about the refinement type.
- `references/console-output-and-errors.md` — what TOPAS actually prints during a run: startup sequence, Rietveld/Pawley/charge-flipping iteration-log columns, two real captured error messages with causes, and the difference between `num_runs` (re-running with `Run_Number` switching) and `continue_after_convergence` (restarting within the same run until `iters`/`num_cycles` — by design, not a bug, if it runs long).
- `references/restraints-and-penalties.md` — `Distance_Restrain`/`Angle_Restrain` as the first restraint macros to reach for; how to read `append_bond_lengths`' SHELX-style bond/angle output matrix and turn it into correct `LABEL opidx offx offy offz` restraint arguments (space-separated, not colon-joined — a common silent-failure trap); a distance-vs-angle restraint weighting rule of thumb; and `penalties_weighting_K1` for balancing restraints against the diffraction data as a whole.
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

- `scripts/topas_install.py` — resolves file paths against the real TOPAS installation via `TOPAS_DIR`. Used internally by the other scripts and directly by you when reading an example file:
  ```
  python3 scripts/topas_install.py --inc-dir
  python3 scripts/topas_install.py --example cf/alvo4a.inp
  ```

- `scripts/check_inp_syntax.py` — a heuristic syntax checker. Run it against any `.inp` file or directory before handing it over:
  ```
  python3 scripts/check_inp_syntax.py path/to/file.inp
  python3 scripts/check_inp_syntax.py path/to/directory/    # recurses
  python3 scripts/check_inp_syntax.py path/to/file "macro FILE { file.xy }"   # tc.exe-style extra command-line text
  ```
  To run it automatically against the file open in VS Code, see `references/vscode-integration.md` for a `tasks.json` setup.

  A bare path with no extension resolves the same way `tc.exe` does (tried as-is, then with `.inp`/`.INP` appended), and a trailing token that isn't itself a file/directory is treated as extra text appended to the checked file's content, mirroring `tc file.inp "macro FILE { file.xy }"` — this matters because `check_symmetry_constraints` and `#ifdef`-branch stripping are `#define`-aware, so a file that only becomes valid once a CLI `#define` is injected needs that flag passed the same way to be checked correctly.

  It catches thirteen mechanical mistakes: unbalanced `{ }`/`( )`; an equation that never reaches its terminating `;` before the enclosing scope changes (including the case where a *later* equation's own `;` would otherwise mask an earlier missing one — it restarts the scan at any fresh top-level `=` found before a `;`); any identifier that isn't a real keyword/macro name, a name the file itself declares, or a token consumed by a keyword's own known multi-token argument grammar — flagged whether or not it resembles a known name, with no minimum length (TOPAS keywords/macros/parameter names are case-sensitive, so matching is exact-case). The checker resolves this without a full parser by understanding each keyword/macro's own argument grammar directly: multi-token forms (`z_matrix` atom labels, `space_group` symbols with embedded hyphens/digits, macro/`fn` parameter names used inside their own body, keyword-prefixed data-block tables like `load site x y z occ beq layer { ... }` or `ADPs { u11C1 0.01 ... }`, two-tag keywords like `occ`/`element_weight_percent`, hyphenated bare filenames, TOPAS's `##` token-pasting and `_LIMIT_MIN_`/`_LIMIT_MAX_` value suffixes, `def NAME1, NAME2;` forward declarations, the reserved parameter names in Table 2-2/2-4 of `01-syntax-and-parameters.md`) are all recognized and exempted from the typo check, so only a genuinely unrecognized token is flagged. Known blind spots: it doesn't resolve locally-`#include`d macros (flagged as a checker gap, not a file mistake), and it can't catch an entirely invented keyword that doesn't resemble any real one (e.g. a version-specific or removed keyword — see `references/console-output-and-errors.md` for that error class). The macro-arity check (arities harvested from the file itself plus the real `.inc` library) has one known blind spot: a file-local macro reusing a name already defined with a different arity by a system `#include` can fail to resolve correctly at runtime even though the argument count matches a known definition — a clean pass means "matches a documented arity," not an ironclad guarantee.

  Other checks: macro calls whose argument count doesn't match any known definition; a keyword value split by a stray space into two tokens (e.g. `space_group P_31_ 2_1`); a value-report `:` dropped after a `;`; a refined `prm`/`local` given a bare value with no `min`/`max` (a best-practice warning — `prm`/`local` carry no built-in default bounds the way subject-specific keywords do; this check understands a project-local macro that sets `min`/`max` indirectly, e.g. `prm cs_g1_ 30 MM(3, 1000)`); a stray extra bare number after a single-value keyword's value, or after a keyword that takes NO value at all (e.g. `str  123123`); a `@` (auto-name sigil) not immediately followed by a numeric value or `=` — three legitimate exceptions are recognized rather than flagged: `@` as a bare macro-call argument (`CS_L(@, 300)`), `@` directly concatenated with a name (`TOF_PV(@pv6, ...)`), and a macro body that's just a bare `@`/`@name` (a common toggle-macro idiom); a bare `x`/`y`/`z` site coordinate suspiciously close to 1/3 or 2/3 (should be `x = 1/3;`) — flagged as a warning, since a large hit count on a big multi-atom/simulated-supercell file is usually intentional grid placement, not a bug; a UTF-8 byte-order-mark at the start of the file (a hard error — a leading BOM makes TOPAS choke on the very first token with no visual clue in most editors); and an ADP tensor component or lattice parameter that violates what the file's own declared space group requires (see `check_symmetry_constraints` below).

  **`check_symmetry_constraints`** validates an existing `.inp`'s ADP and lattice-parameter constraints against what its own declared space group requires, reusing the same crystallography engine as `cif_to_str.py` (`scripts/symmetry_utils.py`) in the opposite direction. Needs `TOPAS_DIR` (space-group operators come from TOPAS's own `sgcom6.exe`/`sg/` database); silently produces no findings if unavailable. Built-in lattice macros (`Cubic`/`Tetragonal`/etc.) are recognized and cross-checked against the space group's own computed crystal system, so e.g. `Cubic(...)` on an actually-tetragonal group is flagged. **Site coordinate (x/y/z) independence is deliberately never flagged** — this was built once, then removed at the explicit direction of TOPAS-Academic's author: writing a coordinate independently (no `!`) is not an accidental omission risking special-position drift, it IS the deliberate signal that the site should be treated as a general position, regardless of its current numeric value (e.g. `x xti1 0 y yti1 0 z zti1 0`, all unfixed, is a general position even though the values happen to be `(0,0,0)`; only all-`!`-fixed coordinates are an enforced special position). ADP and lattice-length checks are unaffected by this and remain always-on, since an ADP's required value is derived purely from the site's position (not its own written number the way a coordinate's is), so a numerically-wrong ADP is a real, always-flagged data error regardless of refinement status. One known residual gap: a str block's own literal `space_group` is always resolved correctly, but the less common `for strs N to M { space_group ... }` idiom (assigning keywords to a range of already-declared str objects by index) is left unresolved rather than guessed at for objects it doesn't literally touch.

  `Get()` has confirmed, non-obvious scope-walking behavior worth knowing when writing or debugging any equation: **`Get()` cannot reach a plain `prm`/`local` by name** — `beq = Get(b1);` where `b1` is a `prm` fails with `Cannot locate b1 from beq in data structures`, even though the bare form `beq = b1;` works fine. `Get(keyword)` only walks up to the **nearest enclosing object that owns an actual structural keyword slot of that name** (`x`/`y`/`z`/`u11`..`u23`/`occ`/`beq` for a site; `a`/`b`/`c`/`al`/`be`/`ga`/`scale`/`space_group` for a `str`), not arbitrary declared names — confirmed empirically against a live `tc.exe`, matching the manual's own `fn lat(h,k,l) = h Get(a) + k Get(b) + l Get(c);` example. `GET_TIE_RE`/`resolve_site_coordinates` support an optional multiplier (explicit `* 0.99`/`/ 100`, or implicit bare juxtaposition `Get(x) .99` for multiplication only — confirmed valid TOPAS syntax via `tc.exe`) and an additive offset, but this is still not a general equation evaluator: multi-term sums of different `Get()`s, nested functions, and external `prm` references are unresolved and skipped with a note, never guessed at. Practical implication: only wrap a reference in `Get()` when targeting an actual structural keyword slot; reference a `prm`/`local` by bare name instead.

- `scripts/expand_inp_macros.py` — expands `macro` calls in an `.inp` file to approximate what TOPAS writes to `tc.log` (the literal, fully-expanded text fed to the kernel), without running TOPAS. Useful for seeing what a macro-heavy file actually does, or tracking down a `tc.log` "at LINE N" error against the macro-based source.
  ```
  python3 scripts/expand_inp_macros.py path/to/file.inp
  python3 scripts/expand_inp_macros.py path/to/file.inp -o expanded.inp
  python3 scripts/expand_inp_macros.py path/to/file.inp --run-number 1   # for files with Run_Number-dependent #if
  ```
  Resolves `#include`s of the `.inc` library, statically prunes `#define`/`#ifdef`/`#if`/`#endif` branches where it safely can, and recursively expands `macro` calls with overload-by-argument-count resolution, `@`-parameter auto-naming, and TOPAS's internal `#m_argu`/`#m_ifarg`/`#m_else`/`#m_endif` directive family.

  **Implements TOPAS's `&` macro syntax** (manual: "Superfluous parentheses and the '&' Type for macros"): `&` before a macro's own name (`macro & CeV(c, v) { ... }`) wraps the entire expansion result in parens at every call site; `&` before an argument name in the parameter list (`macro & Gauss(& xo, & fwhm) { ... }`) wraps that argument's substituted value in parens everywhere referenced inside the body. This isn't cosmetic — per the manual's own example, `divide(a + b, c - d)` without `&` wrongly expands to the precedence-broken `a + b / c - d` — and real `topas.inc` combines both forms extensively (`Gauss`, `Lorentzian`, `PO_eqn`, `Ramp`, `Limit`, and more).

  Macro expansion is multi-pass (fixed-point, capped at 60 passes), so a macro calling another macro fully resolves through every level. Brace-nesting inside a macro body is tracked correctly (including skipping over `"..."` string interiors, so a literal `}` inside a quoted filename doesn't truncate the body early). Resolves `#ingest` (like `#include` but for project files rather than the system library) and understands `#external_INP` (TOPAS does NOT merge these into the parent's own output, so this tool leaves the directive line untouched and appends each linked file's own expansion as a separate labeled section). A `#include` of a dynamically-built path (e.g. wavelength `.lam` files loaded by `CuKa5`) has its target's content actually inlined, not just its path resolved. Known gaps: `fn`-defined and built-in equation functions (`Cos`, `Gauss`, ...) are left untouched (evaluated by TOPAS's equation engine, not macro substitution); output line numbers do not match `tc.log`'s own numbering (see `references/macro-expansion-and-log-files.md` for those rules).

  **`#include` resolution rule, confirmed directly by TOPAS-Academic's author: "#include operates from the INP file directory unless the full path is given in the #include."** This applies to both the system `.inc` library and project-local files (a `.inc` or any other extension sitting next to the main `.inp`) — resolution tries the referencing file's own directory first, falling back to the system library only for a bare filename not found there, recursively for nested includes. This is a common real pattern (a project split across `main.inp` + `myrigidbodies.inp` + local `.inc` helper files), not an edge case.

- `scripts/find_refined_params.py` — **run this whenever the user asks for the independent/refinable parameters in a `.inp` file**. Lists every INDEPENDENT refined parameter: named (or auto-named via bare `@`), not `!`-prefixed, and — if written as a named equation — evaluating to a plain numeric constant rather than a function of other parameters (a DEPENDENT parameter, per Technical_Reference.pdf section 2.9).
  ```
  python3 scripts/find_refined_params.py file.inp
  python3 scripts/find_refined_params.py file.inp -o report.txt
  ```
  Fully macro-expands the file first and scans the expanded text (needed because a macro call's bare `@` argument doesn't sit textually next to the number it binds to until after expansion). Combines several signals: explicit `prm`/`local NAME ...` declarations (`local` is genuinely re-scoped per xdd/phase per the manual, so never deduplicated by name; bare `prm` has no such re-scoping and is deduplicated); the `@` sigil on keywords that carry it straight in the kernel (`a`/`b`/`c`/`al`/`be`/`ga`/`scale`/`bkg`); the `ADPs` macro's own expansion to `load u11 u22 u33 u12 u13 u23 { ... }`; and a curated list of other directly-written named keyword values (`beq`, ADP components, lattice parameters), deduplicated by name since TOPAS enforces one shared value per parameter name. Deliberately does NOT report bare, unnamed, un-`@` numeric values (e.g. a rigid body's computed-output site x/y/z) since there's no reliable way to distinguish an independently-refinable bare value from a computed/reported one by text pattern alone. Known limitations: a handful of directly-written keywords outside the curated lists could still be missed; expanded-text line numbers do not match the original file's for macro-generated content.

  **`for xdds { ... }`/`for strs [N to M] { ... }` loop repetition is accounted for, with a specific, non-obvious, empirically-confirmed rule: only ANONYMOUS/unnamed declarations get multiplied by the loop's iteration count, never bare NAMED ones.** TOPAS's kernel-enforced "same name = same value" rule (section 2.4) applies regardless of for-loop context, so a bare named `prm` inside a loop stays ONE shared parameter across every iteration, while an anonymous `@` genuinely gets a fresh instance each time — confirmed with minimal test files (`for xdds { prm test_named_prm ... }` on 2 xdds reports 1 independent parameter; the same test with `prm @ ...` reports 2). Anonymous `direct_at`/`adp_loads` entries and `local` (already re-scoped per iteration) are multiplied; named `prm`/`named_direct` entries never are. A bare (no-range) `for strs { ... }` nested inside another for-loop is deliberately left unmultiplied since its real scope (whole file again per outer iteration, or just the current xdd's own strs?) isn't confirmed — better to undercount than risk a wild overcount. `param_dependency_trees.py`'s independent-parameter badge reuses this exact same rule.

- `scripts/param_dependency_trees.py` — **run this whenever the user asks for a parameter dependency tree/graph, or says "do trees"** (a standing trigger phrase — run against the relevant/currently-open `.inp` file and let it open its own report). **"do trees" defaults to the interactive HTML form** (`-o <name>.html`, opened in the browser); only fall back to plain-text/VS-Code if the user explicitly asks for text. Builds the full computation graph (not just the independent-parameter list `find_refined_params.py` stops at) and renders it as two views:
  ```
  python3 scripts/param_dependency_trees.py file.inp -o report.html     # "do trees" default: interactive page, opens in browser
  python3 scripts/param_dependency_trees.py file.inp                    # both trees, to stdout
  python3 scripts/param_dependency_trees.py file.inp --tree dependent   # tree 1 only
  python3 scripts/param_dependency_trees.py file.inp --tree independent # tree 2 only
  python3 scripts/param_dependency_trees.py file.inp -o report.txt      # write + auto-open in VS Code
  python3 scripts/param_dependency_trees.py file.inp -o report.txt --no-open
  ```
  When `-o` is given, opens/focuses the written report afterward — VS Code for text, the default browser for `.html`/`.htm` (the general rule this skill follows: plain-text reports open in VS Code, HTML visualizations open in the browser). Both trees render as click-to-expand node lists, color-coded by kind (green = independent/refined, blue = dependent, grey = fixed), with a live search box. **Tree 1**: every DEPENDENT parameter/keyword as a root, its referenced parameters as children, recursed to independent/fixed leaves. **Tree 2**: every INDEPENDENT (refined) parameter as a root, with the dependents that reference it as children — the reverse-edge view. A bare `@`-flagged value with no name of its own is labeled with its keyword instead.

  Macro-expands the file first and scans for equations in `prm`/`local` (including `!`-prefixed ones, unlike `find_refined_params.py`, since this needs the full graph regardless of refined status) and a curated keyword list (site `x`/`y`/`z`/`occ`/`beq`/`u11..u23`, lattice `a`/`b`/`c`/`al`/`be`/`ga`/`scale`, `rotate`/`translate`, rigid-body Z-matrix `ta`/`tb`/`tc`). The header's stat badge shows the count of refineable independent parameters (same definition as `find_refined_params.py`, including its for-loop multiplier rule). `local` re-scoping is handled the same way (same name in multiple `local` statements = genuinely different parameters, resolved to the nearest preceding declaration). Rigid-body `z_matrix` rows are parsed for their own bond/angle/torsion equations in both TOPAS `z_matrix` syntax forms (block form and inline form). **Deliberately shows the FULL computation graph, not the independent-leaf-collapsed view TOPAS's own `out_dependences`/`out_dependences_for` gives** — this script's output is a strict superset, traceable node-by-node, by design.

- `scripts/topas_keyword_tree.py` — **run this whenever the user asks to see/visualize the TOPAS keyword hierarchy itself** (a browsable map of the language's own keywords, as opposed to `param_dependency_trees.py` which graphs one file's actual parameters). Two sources in one two-panel page: `references/21-keyword-index.md`'s "Data structures" fenced block (rendered as the Tree panel, rooted at `Ttop`, where a bare `Txxx` member line means "insert everything that type defines here too"), and every other reference chapter's own keyword mentions (indexing, charge-flipping, stacking faults, minimization, PDF, quant, rigid bodies, magnetic, protein, GUI, misc, ...), shown as additional "by topic" groups.
  ```
  python3 scripts/topas_keyword_tree.py                    # -> <TOPAS_DIR>/topas_keyword_tree.html (skipped + reopened if it already exists)
  python3 scripts/topas_keyword_tree.py --force             # regenerate even if the output file already exists
  python3 scripts/topas_keyword_tree.py -o out.html         # custom output path (works without TOPAS_DIR)
  python3 scripts/topas_keyword_tree.py --no-open
  ```
  Since this tree only depends on this skill's own bundled reference files, a plain rerun with no flags skips regeneration and reopens the existing file; pass `--force` after editing a reference chapter. Opens in the default browser (never VS Code), matching this skill's HTML-visualization convention. Chapter numbering and root-level ordering are sourced from the real manual's own chapter numbers and document order (not this skill's own `00`-`26` filename scheme or alphabetical order). Known limitation: a rigid body's `z_matrix { ... }` block is not parsed internally (its rows put an atom label, not a keyword, before `=`); `KEYWORD_EQ_LIST`-equivalent keyword lists used for by-topic extraction are curated, not exhaustive.

- **"Show Schema" is a standing trigger phrase** for displaying TOPAS's internal kernel data-structure page (`kernel_structure_tree.html`) — an interactive tree of the kernel's own `Txxx` complex types, distinct from `topas_keyword_tree.py` (which browses the documented keyword hierarchy, not the kernel's internal schema). This page isn't generated by this skill — only the pre-rendered HTML travels with each TOPAS release. Resolve and open it with:
  ```
  python3 scripts/topas_install.py --kernel-schema-html
  ```
  If `TOPAS_DIR` isn't set or the file isn't found, say so plainly — there is no bundled fallback.

- `scripts/c_matrix_heatmap.py` — renders a `C_matrix_normalized { ... }` block (the normalized parameter-correlation matrix TOPAS writes after `do_errors`) as a heatmap, diverging blue (negative)/red (positive) with a gray zero midpoint. Two formats, via `--format {png,html}` (or inferred from `-o`'s extension; defaults to `png`):
  ```
  python3 scripts/c_matrix_heatmap.py path/to/file.inp                          # -> file_c_matrix.png
  python3 scripts/c_matrix_heatmap.py path/to/file.out -o heatmap.png --cell-size 30
  python3 scripts/c_matrix_heatmap.py path/to/file.inp --format html            # -> file_c_matrix.html
  ```
  `png`: zero third-party dependencies (hand-encoded via stdlib `zlib`, bundled bitmap font); axis ticks are the 1-based index only, full names printed to stdout. `html`: self-contained interactive page with full parameter names, hover tooltips — generally the better default unless a static image is specifically needed. Both parse the block as plain text (no macro expansion needed), so it works on a literal block in a `.inp` or a real `.out` result.

- `scripts/generate_macro_browser.py` — builds an interactive HTML browser for every `macro`/`macro &` definition across the real `.inc` library (discovered by directory scan, not a hardcoded list).
  ```
  python3 scripts/generate_macro_browser.py                                    # -> <TOPAS_DIR>/macro_browser.html
  python3 scripts/generate_macro_browser.py --docx path/to/Technical_Reference.docx   # use a .docx instead of the auto-resolved PDF
  python3 scripts/generate_macro_browser.py --no-pdf                           # skip §21.2 descriptions entirely
  python3 scripts/topas_install.py --macro-browser-html                        # resolve (and open) an already-generated one
  ```
  Ground truth for name/argument list/arity/body is always the real `.inc` source; §21.2 descriptions are an optional best-effort explanation layer, auto-resolved from the manual PDF by default (`--docx` if you have the live editing copy, which takes priority). A macro with no §21.2 match is shown in full, honestly labeled "not in §21.2" rather than fabricating or borrowing a description from a neighboring entry. Each macro's detail panel has an "Open in editor" button (`vscode://file/...`); the TOPAS install directory is entered once and cached in the browser's `localStorage`.

- `scripts/plot_str_3d.py` — **run this whenever the user asks for a 3D plot/view of a `str` phase's crystal structure**. Renders one `str` block as a self-contained interactive HTML page (drag to orbit, scroll to zoom, a perspective slider, an off-by-default site-labels checkbox) — unit cell as a wireframe box, every site symmetry-expanded across the cell as colored spheres, cation-anion bonds by covalent-radius-sum cutoff. No third-party dependencies (hand-written vanilla-JS canvas 3D engine, works offline/in a strict-CSP viewer).
  ```
  python3 scripts/plot_str_3d.py file.inp                # -> file_str3d.html
  python3 scripts/plot_str_3d.py file.inp --phase 2       # pick the Nth str block (1-indexed) if more than one
  python3 scripts/plot_str_3d.py file.inp --no-bonds
  python3 scripts/plot_str_3d.py file.inp --bond-tolerance 1.3
  ```
  Reuses this skill's existing engine: `check_inp_syntax.py`'s site/coordinate parsing, `symmetry_utils.resolve_sg_operators`, `expand_inp_macros.py`'s macro-argument parsing for lattice macros. Cell parameters come from literal `a`/`b`/`c`/`al`/`be`/`ga` (with simple `Get()` ties resolved) or a built-in lattice macro (argument-to-parameter mapping read from the live install's `topas.inc`). A site's fractional point is mapped through every space-group operator, reduced mod 1 and deduplicated for its orbit/multiplicity; a point on a cell face/edge/corner is additionally mirrored so the box looks visually complete. Element colors/covalent radii are an approximate built-in table (~70 elements) for visual aid, not scientific bond-length analysis. **Bonds are restricted to different-element pairs** — a same-element cutoff produced hundreds of nonsensical same-species bonds on a real fluorite test file. Known limitations: occupancy/site-mixing not visualized (drawn as the first species only); only sites whose x/y/z all resolve to a concrete number are plotted; a cell parameter written as a more complex equation won't resolve.

  A site whose `u11..u23` all resolve to concrete numbers is drawn as an oriented 50%-probability thermal ellipsoid instead of a plain sphere. TOPAS's `u11..u23` (the standard IUCr/CIF U_cif convention) are converted to a Cartesian tensor via the standard transform, and each symmetry-equivalent image of a site gets its own correctly reoriented tensor (verified directly on a rutile test file with deliberately asymmetric ADPs: images related by the space group's screw axis show the expected sign-flip/rotation signature). ADP resolution also handles the common per-site-tagged naming convention (`u11C1`, `u22C1`, ...), needed since TOPAS's global "same name = same value" rule means a many-atom refinement must give each site's `u_ij` a distinct name. Nothing about this is space-group-specific (verified across cubic, orthorhombic, monoclinic, and triclinic test files).

- `scripts/plot_xy.py` — **run this whenever the user asks to plot a raw XY(E) data file** (`.xy`, `.xye`, `.dat`, or `Out_X_Yobs`/`Out_X_Ycalc` output). Renders a self-contained interactive HTML page: drag to pan, scroll to zoom (both cursor-centered), a per-series visibility checkbox in the legend, a hover crosshair (no floating tooltip box), and a Sqrt(Y)/Linear toggle for compressing dynamic range.
  ```
  python3 scripts/plot_xy.py file.xy                # -> file_xy_plot.html
  python3 scripts/plot_xy.py file.xy --title "My pattern"
  ```
  No third-party dependencies. Parsing skips blank/comment lines and lines with fewer than two numeric tokens rather than raising. Y-axis autoscaling recomputes from only the currently visible X window on every pan/zoom. The Sqrt(Y) transform is signed (`sign(y)*sqrt(abs(y))`) to degrade gracefully on background-subtracted data with small negative values.

  **Supports multiple overlaid series and a computed difference/residual curve:**
  ```
  python3 scripts/plot_xy.py obs.xy calc.xy --labels "Yobs,Ycalc" --colors "blue,red" --diff "Yobs,Ycalc" -o out.html
  python3 scripts/plot_xy.py --phases "CeO2|ceo2_obs.xy|ceo2_calc.xy,Y2O3|y2o3_obs.xy|y2o3_calc.xy" -o out.html
  ```
  `--labels`/`--colors` are comma-separated, parallel to the file arguments; an explicit user color instruction is used literally. `--diff LABEL_A,LABEL_B` adds a `LABEL_A - LABEL_B` series (direct subtraction on a shared X grid, else linear interpolation); repeatable per phase. **All difference curves share one live-computed screen-space offset**: the highest point among visible diff curves sits ~5 CSS pixels below the lowest point among visible main series, recomputed on every draw so it never drifts on zoom. `--phases "NAME|obs.xy|calc.xy,..."` (pipe-separated, since `:` collides with Windows drive letters) auto-builds a combined multi-phase plot with a standing color scheme: every phase's Ycalc is the same fixed red-orange; each phase's Yobs cycles through a fixed 8-color palette (deliberately none red/near-red, to stay distinguishable from Ycalc); each diff curve reuses its own phase's Yobs color at 0.7x intensity. Cannot be combined with plain positional file args in the same invocation.

  **"Run and plot [file]" is a standing workflow**: (1) run the file via `tc.exe` on a scratch copy, never the original in place; (2) if `Out_X_Ycalc(...)`/`Out_X_Yobs(...)` aren't already present, warn and add them to the scratch copy; (3) plot Yobs, Ycalc, and their difference together; (4) if the file has more than one `xdd` block, produce one plot per `xdd` by default — unless the user says **"fit show in one plot"**, in which case combine every phase via `--phases`. Two general facts worth remembering for any multi-phase file: TOPAS enforces one shared value per parameter name globally (reusing e.g. `CS_L(csl, ...)` at different values across two phases aborts the run with `Parameter csl is defined more than once...`); and a plain relative data filename in a `DAT`/`XDD`/`RAW` macro call resolves relative to the referencing `.inp` file's own directory (same rule as `#include`), so a scratch copy run from elsewhere needs its data file alongside it.

- `scripts/cif_to_str.py` — converts a CIF file's structure into a TOPAS `str { }` block, deriving Wyckoff-position coordinate constraints directly from the CIF's own `_symmetry_equiv_pos_as_xyz` operator loop. Preferred over `cif1.exe` — see "Converting a CIF file to `str` format" below.
  ```
  python3 scripts/cif_to_str.py input.cif                   # print to stdout
  python3 scripts/cif_to_str.py input.cif -o output.txt      # write to file
  python3 scripts/cif_to_str.py input.cif --tolerance 0.002  # coordinate-match tolerance (default 0.0015)
  ```
- `scripts/symmetry_utils.py` — not a standalone tool, a shared library. Holds the crystallography engine (symmetry-operator parsing, `sgcom6.exe`/`sg/`-database resolution, per-site Wyckoff/ADP constraint derivation, per-lattice-system angle/length constraint derivation) used by both `cif_to_str.py` (CIF → `str`) and `check_inp_syntax.py`'s `check_symmetry_constraints` (`.inp` → warnings) — extracted into one shared module so a crystallography fix in one is a fix in both.

- `scripts/fix_columns.py` — **run this whenever the user says "fix columns"** (or asks to column-align/tidy up `site` statements). Column-aligns consecutive `site` lines so their keywords (`x`/`y`/`z`/`occ`/`beq`/`u11`..`u23`) start at the same character column, with exactly one space between a padded value and the next keyword, e.g.:
  ```
  site Ce1 x  0.25 y   0.5 z  0.25 occ Ce+4 1 beq = b1;
  site Ce2 x     0 y   0.5 z   0.5 occ Ce+4 1 beq = b1;
  ```
  A plain numeric value is right-aligned within its column (so digits/decimal points line up down the page in a fixed-width font); a column mixing a bare number with an equation stays left-aligned. `occ`'s two-token `TYPE N` form gets its own two independently-aligned sub-columns. Also column-aligns consecutive `la ... lo ... lh ...` emission-profile lines inside a `lam { }` context, forcing them (and `ymin_on_ymax`) one indent level deeper than the nearest preceding `lam` line, per the real keyword hierarchy (Technical_Reference p.209).
  ```
  python3 scripts/fix_columns.py file.inp              # rewrite in place, whole file
  python3 scripts/fix_columns.py file.inp --check      # preview to stdout, don't write
  python3 scripts/fix_columns.py file.inp --lines 26-31 # only touch lines 26-31 (1-indexed, inclusive)
  ```
  Whitespace-only — still run `check_inp_syntax.py` afterward. `--lines` computes column widths from the whole file but only rewrites lines in range — translate an active IDE text selection directly into this flag rather than fixing the whole file. Correctly handles a `Get(x)`/`Get(y)`/`Get(z)` reference inside another coordinate's own equation (e.g. `z = Get(x) + 0.1625;`) without mistaking the inner reference for a new keyword boundary.

- `scripts/format_inp_hierarchy.py` — **run this whenever the user asks to reindent/reformat a `.inp` file "hierarchically"**. Reindents a whole file to reflect its structural nesting, 3 spaces per level; a line with multiple keywords packed onto it is never split.
  ```
  python3 scripts/format_inp_hierarchy.py file.inp              # rewrite in place
  python3 scripts/format_inp_hierarchy.py file.inp --check      # preview to stdout, don't write
  python3 scripts/format_inp_hierarchy.py file.inp --no-open    # skip reopening in VS Code afterward
  ```
  Reopens the file in VS Code after writing (skip with `--no-open`). Collapses excess whitespace on most lines (never inside a quoted string/comment, or inside a `C_matrix_normalized { ... }` block). Runs `fix_columns.py`'s own alignment first, so `site`/`la`/`lo`/`lh` lines end up correctly aligned as part of the same pass. Because a large part of TOPAS's real hierarchy has no `{ }` at all (an `xdd`/`str` block just runs until the next phase/`str` keyword or EOF), indentation is derived directly from the manual's own keyword-hierarchy schema (`21-keyword-index.md`'s Data-structures block) rather than a hand-picked keyword list: only keywords with a non-empty resolved children set become section-openers, and a "wide" section (reaches `prm`, e.g. `xdd`/`str`) is only closed by another section-opener it doesn't recognize as a child, while a "narrow" section (e.g. `site`, `lam`) is closed by any keyword that isn't one of its own children. One narrow, explicitly-documented exception: `la`'s connection to `lam` is only inferable from prose, not schema, so it's a hand-coded supplement.

- `scripts/remove_errors.py` — **run this whenever the user says "remove errors"**. Strips every trailing `` `_<error> `` refined-value-error suffix in one regex pass — see "Stripping refined-value errors" below.

- `scripts/insert_adps.py` — **run this whenever the user says "insert adps"**, replacing a `beq` clause on selected `site` line(s) with symmetry-constrained anisotropic displacement parameters (`u11`/`u22`/`u33`/`u12`/`u13`/`u23`) instead of hand-deriving the constraints each time.
  ```
  python3 scripts/insert_adps.py file.inp --lines 26-28   # only site(s) touching these lines
  python3 scripts/insert_adps.py file.inp                 # every site with a beq, whole file
  python3 scripts/insert_adps.py file.inp --check          # preview to stdout, don't write
  ```
  Same `--lines` convention as `fix_columns.py`. Reuses the same parsing/crystallography engine as `plot_str_3d.py`/`check_symmetry_constraints`/`cif_to_str.py`, so output uses identical formatting conventions throughout a file mixing CIF-converted and script-converted sites. A site's space group always comes from TOPAS's own database via the file's own `space_group` line, never guessed; silently produces no conversions without `TOPAS_DIR`. The starting value seeded into each newly-free `u11`/`u22`/`u33` is derived from the site's old `beq` (`Uiso = Beq/8π²`), with a fallback chain if `beq` is itself an equation: its own numeric value, then a same-named `prm`/`local` elsewhere in the file, then another site's own `beq NAME value` tag; a free off-diagonal component with no isotropic equivalent starts at 0; an unresolvable `beq` falls back to a generic `0.01` with an explicit warning. Also runs `fix_columns()` over its result afterward, scoped to the same `--lines` range, so newly-inserted `u11`/`u22`/... columns are aligned immediately.

- `scripts/find_example.py` — **run this whenever the user asks for a template/example/starting point for some refinement topic**, e.g. "tof template" — searches the curated ~197-file regression corpus for real, working `.inp` files matching the query.
  ```
  python3 scripts/find_example.py tof
  python3 scripts/find_example.py "tof template"              # trailing filler words are stripped
  python3 scripts/find_example.py pawley -n 5                  # show up to 5 matches (default 8)
  python3 scripts/find_example.py "charge flipping" --open     # also open the top match in VS Code
  ```
  Two matching passes: (1) whole-word (not bare-substring — "tof" no longer false-positives inside "tofullprofmono") path match against corpus folder/file names, which are usually topic-named; (2) a content match against a curated topic-synonym list (Pawley, Le Bail, indexing, PDF, charge-flipping, quant, stacking faults, rigid bodies, deconvolution, magnetic, protein, single-crystal, TOF, parametric/sequential) for queries naming a concept the corpus only abbreviates (e.g. "charge flipping" → `cf/`). Deliberately does NOT auto-genericize a found example into a placeholder-filled template — deciding what's an instrument constant to keep vs. a sample-specific value to placeholder-ize needs real per-topic judgment; `example_inp_files/tof_template.inp` is what that judgment call looks like once applied by hand.

## Core syntax cheat sheet

- Blocks are delimited with `{ }`; comments use `'` to end-of-line.
- A parameter gets a name (letters, digits, underscore, must not start with a digit) so it can be tracked/refined; prefix `!` to fix it (exclude from refinement); prefix `@` to auto-generate a unique internal name.
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
  `iters 0` skips refinement (pure format conversion); works for any format TOPAS's `xdd` reads natively. Run via `tc.exe path/to/conversion.inp`.

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
python3 scripts/remove_errors.py file.inp                 # rewrite in place, whole file
python3 scripts/remove_errors.py file.inp --check          # preview to stdout, don't write
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

**Preferred: `python3 scripts/cif_to_str.py input.cif`** — a Wyckoff-constraint-aware converter, not a hand-derived field-by-field mapping and not `cif1.exe` (see below for why). Derives each site's coordinate constraints directly from the CIF's own `_symmetry_equiv_pos_as_xyz` operator loop — no external space-group table needed — distinguishing three cases per coordinate:

- **Free** (general position, or the one independent coordinate of a partial special position): emitted as `x @ 0.34131` (refined).
- **Fixed** (a symmetry operator pins it to an exact constant): emitted as a bare value, or as an exact `z = 5/6;` equation when it snaps to a common fraction — writing a rounded decimal instead (e.g. `z 0.833333`) produces a real TOPAS warning about the equivalent-position distance being off by a tiny but nonzero amount, so the exact-fraction form matters, not just style.
- **Tied to another coordinate of the same site** (e.g. a site on a mirror or 3-fold axis): emitted as `y = Get(x);`, the same mechanism `Cubic(cv)` uses internally (`b = Get(a); c = Get(a);`).

A hand- or tool-converted CIF that just writes three independent `x @ / y @ / z @` values for every site is silently wrong whenever a site sits on a special position — refinement is then free to pull tied coordinates apart, breaking the CIF's own symmetry. Validated (each cross-checked via `tc.exe` + `Out_CIF_STR`) against a fully-fixed cubic case, a Pa-3 case mixing fully-fixed/fully-general/3-fold-axis sites (correctly avoiding a circular `x=Get(y); y=Get(z); z=Get(x);` tie by picking one free representative), and a P3121 case requiring the general `(R-I)p ≡ -T (mod 1)` per-operator-row derivation rather than a naive "row i constrains coordinate i" heuristic (an operator's x-output row can actually constrain y alone).

**Lattice angles/lengths forced to specific values by the crystal class are handled the same way**: an angle crystallographically forced to exactly 90° is omitted entirely (relying on TOPAS's own 90° default) rather than written explicitly, determined from the rotation parts of the CIF's own operators (proper 3-fold count ≥8 → cubic; a 4-fold → tetragonal; a single 3-fold → trigonal/hexagonal, fixing `al`/`be` but not `ga`, since 120° isn't the default; axis-aligned 2-folds/mirrors → orthorhombic/monoclinic) — only actually applied if the CIF's own stated value already agrees within tolerance, never silently forced. Lengths forced equal get the identical `Get()`-tie treatment (`b = Get(a); c = Get(a);` for cubic; only `b` for tetragonal/hexagonal-axes-trigonal). **Known limitation**: the method generalizes by crystal class from the CIF's own operators (not a per-space-group table), but has only been empirically verified against cubic and standard-hexagonal-axes-trigonal test cases, not all 230 space groups or every alternate axis setting `sgcom5.txt` lists — in particular, rhombohedral-axes settings (`a=b=c`, `al=be=ga` mutually equal but not 90°) require disambiguating from the standard hexagonal-axes setting using the CIF's own angle values, since a single 3-fold axis's rotation matrices alone can't tell the two apart; this disambiguation exists for lengths but not yet for the fact that the three oblique rhombohedral angles are tied to each other.

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

Usage (needs the resolved TOPAS install dir, `python3 scripts/topas_install.py --inc-dir`):

```
cif1.exe input.cif output.inp
```

Two things worth knowing about its output: `volume` is a real, valid (if undocumented in this skill's own keyword index) TOPAS keyword — confirmed by running raw `cif1.exe` output through `tc.exe` with zero error; and `phase_name` can inherit garbage straight from an under-filled CIF field (e.g. the literal string `"?CeO2?"`, CIF's own "value not specified" placeholder carried through verbatim) — check and clean this up by hand rather than trusting it blindly. `cif1.exe`'s output is deliberately generic: explicit `a`/`b`/`c`/`al`/`be`/`ga` rather than a symmetry-shorthand macro, and no `scale` at all (left for you to add).

## Updating `references/paper-summaries.md` from new algorithm papers (PDFs)

If someone points you at a folder of the actual journal-paper PDFs behind TOPAS's algorithms and asks you to read/summarize them (rather than the Technical Reference manual):

**PDF text extraction**: the `Read` tool's PDF-page-rendering path depends on `pdftoppm` (poppler-utils); if unavailable, fall back to `python -m pip install pypdf` and extract per-page text with `PdfReader(path).pages[i].extract_text()`. This is plain-text extraction (no OCR/layout awareness) — sufficient for prose/equations-as-text but will mangle any originally-typeset math object, the same limitation as the DOCX manual. Extract to a scratch directory, never into the skill itself.

**Don't assume filenames map 1:1 to distinct papers.** Check title/author/abstract of every file before trusting a citation — a folder can contain a non-paper (e.g. a conference certificate), a pre-typesetting draft alongside the same paper's published version under a different filename, or exact duplicate copies.

**A paper's own header is the authoritative citation, and can catch existing errors** — IUCr/Acta Cryst reprints print the real `J. Appl. Cryst. (YYYY). VOL, PAGES` on the cover and in the article header. Re-derive citations from the source rather than trusting one already recorded in `paper-summaries.md`.

**Summaries should carry the paper's concrete numbers, not just its abstract-level claim** — a full read of the body usually turns up specific default parameter values, correlation/accuracy caveats, and worked-example numbers that are exactly what someone debugging a `.inp` script needs, worth a second pass even when the first-pass summary isn't wrong, just shallow.

## Updating this skill from a revised Technical Reference (DOCX or PDF)

These reference files were built from *TOPAS-Academic Technical Reference* (Alan Coelho), cross-checked against both a PDF export and the source `.docx`. If a newer edition shows up in a future session, this is the accumulated playbook for updating the skill from it.

**Get the file open correctly.** For a large `.docx`, pull just `word/document.xml` (`unzip -p file.docx word/document.xml > document.xml`) rather than unpacking the whole archive; only unpack fully if you need to edit and repackage. Parse with `lxml.etree` and the WordprocessingML namespace, not regex — a naive regex against raw OOXML can silently leak XML into extracted text when it hits a self-closing `<w:t/>` element.

**Re-resolve chapter/section numbers by heading text, not by an assumed running number.** Chapter numbering drifts between editions/exports (a duplicated heading in one copy can shift every subsequent number). Walk `Heading1`–`Heading4` paragraphs and match by the heading's actual text. This skill's own `00`–`26` filename prefixes are an independent scheme and intentionally don't track the manual's own chapter numbers.

**Keywords are marked by a Word character style, not just a color.** `AacKeyword1` (orange, italic) and `AacKeywordHyperLink` (blue, bold+italic, for cross-reference-linked mentions — about 7% of all keyword mentions) are both real keyword styles; a color-only scan would miss the second. Macro names use `AacMacro`, reserved parameter names `AacReservedParameters`, filenames `AacFile`. One trap: a run can carry the `AacKeyword1` style tag with an explicit `<w:color w:val="auto"/>` override, rendering as ordinary black text — leftover formatting from an edit, not a real keyword instance; filter these out.

**Reconstructing keyword-dependency hierarchy requires indentation, which hides behind two different mechanisms**: paragraph-level `w:ind`/`@left` (twips — ~357–360 ≈ one level, ~714–720 ≈ two, ~1068–1074 ≈ three), or literal leading `<w:tab/>` elements with no `w:ind` at all. Check both per paragraph. A bare `T`-prefixed name (`Ttop`, `Tcomm_2`, ...) starts a new type's own definition; the same name appearing as a member elsewhere is a mixin/include ("insert everything that type defines here too"), not a nested child, unless it's genuinely a child object with further bracketed keywords. Not every chapter has real nesting to lose — check actual indent values before assuming a flat list needs rebuilding into a tree, and don't mistake ordinary code-example indentation (a macro body, a C++ snippet) for keyword hierarchy.

**Verify any suspected content difference or typo two independent ways** (DOCX vs. an independent PDF extraction, or vice versa) before reporting it as a genuine manual error rather than an extraction artifact. Confirmed real findings fixed in these references include a mistyped keyword name (`out_dependents_for` → `out_dependences_for`), missing/doubled parentheses in worked examples, and a wrong file extension in prose (`ATMSCAT.CPP` → the manual's actual `ATMSCAT.TXT`). Conversely, don't "fix" the manual's own deliberate conventions — `...` meaning "content omitted for brevity" is not broken code.

**`check_inp_syntax.py` can run at scale across extracted snippets, but expect real false positives** from the `...` omission convention, non-INP content with brackets/parens (results tables, space-group symbols), and ordinary English words coincidentally resembling a keyword. Hand-verify every flag against the source before reporting it.

**This environment has occasionally reverted a file to an earlier state between turns** — after a long edit chain, spot-check that a sample of earlier fixes are still present before declaring the update complete, rather than assuming persistence.

**The single dominant failure mode found during a full re-verification pass: a `##`/`###` heading kept its own text but its body prose was silently dropped**, while surrounding tables/code blocks survived — showing up as a whole empty subsection, a multi-branch list missing 1-2 branches, or a keyword's bracket signature with no description sentence below it. When re-verifying in future, grep each chapter's paragraph *count* against the source rather than only checking for specific known strings, since a dropped paragraph produces no error, just silence — and don't assume a past confirmed fix stayed fixed; re-check it too (one such fix was found to have regressed by the time of a later pass).
