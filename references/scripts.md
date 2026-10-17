# Scripts — full reference

Usage, options, behaviour and limitations of every script in `scripts/`. `SKILL.md` keeps the triggers, warnings and the "Run and plot" workflow; read a script's entry here before its first use in a session.

`fix_columns.py`, `format_inp_hierarchy.py`, `insert_adps.py` and `remove_errors.py` **rewrite in place with no backup** — preview with `--check` unless the `.inp` was just copied from a `.out`.

- `scripts/topas_install.py` — resolves install paths (see `SKILL.md` "Locating your TOPAS installation"); used internally by other scripts. `find_tc()` and `tc_env()` locate `tc.exe` and give a subprocess `TOPAS_DIR` on `PATH`.

- `scripts/check_inp_syntax.py` — heuristic checker; run before handing over any `.inp`. **Pass all files in one invocation** (paths or a directory) — each run spends ~200 ms loading its corpus. VS Code task setup: `references/vscode-integration.md`.
  ```
  python scripts/check_inp_syntax.py file.inp
  python scripts/check_inp_syntax.py dir/                                    # recurses
  python scripts/check_inp_syntax.py file "macro FILE { file.xy }"           # tc.exe-style extra text
  ```
  An extensionless path resolves like `tc.exe` (as-is, then `.inp`/`.INP`). A trailing token that isn't a file is appended as INP text (so CLI `#define`s affect `#ifdef` stripping and symmetry checks) — **a mistyped second path is therefore not an error**; check the `[+cmdline: ...]` tag.

  Checks: unbalanced `{ }`/`( )`; an equation not reaching `;` before scope changes; any identifier that isn't a known keyword/macro, file-declared name, or part of a keyword's multi-token argument grammar (case-sensitive); macro argument counts vs known definitions; a value split by a stray space (`space_group P_31_ 2_1`); a `:` value-report missing its `;`; a refined `prm`/`local` with no `min`/`max` (warning; understands project macros that set bounds, e.g. `MM(3, 1000)`); a stray extra number after a keyword's value or after a no-value keyword (`str  123123`); a misplaced `@` (allowed: bare macro argument `CS_L(@, 300)`, glued `@pv6`, toggle-macro body `@`/`@name`); bare coordinates near 1/3 or 2/3 (warning — use `x = 1/3;`; many hits on a supercell are usually intentional); a UTF-8 BOM (hard error — TOPAS chokes on the first token); and ADP/lattice values violating the file's space group (below).

  Blind spots: locally-`#include`d macros aren't resolved; an invented keyword resembling nothing real isn't caught (e.g. a removed/version-specific one); a file-local macro reusing a system name at a different arity can still fail at runtime.

  **`check_symmetry_constraints`** (needs `TOPAS_DIR`; silent without it) validates ADPs and lattice parameters against the declared space group, and cross-checks lattice macros (`Cubic(...)` on a tetragonal group is flagged). **Site coordinates are deliberately never flagged**: an unfixed coordinate (no `!`) means "treat as a general position" whatever its value (`x xti1 0 y yti1 0 z zti1 0` is general even at the origin); only all-`!`-fixed coordinates enforce a special position. ADPs are always checked, since their required values depend only on site position. Gap: `for strs N to M { space_group ... }` is not resolved.

  **`Get()` scope rule:** `Get(name)` reaches only the nearest enclosing object's structural keyword slot (`x`/`y`/`z`/`u11`..`u23`/`occ`/`beq` on a site; `a`/`b`/`c`/`al`/`be`/`ga`/`scale`/`space_group` on a `str`) — **never a `prm`/`local`**: `beq = Get(b1);` fails (`Cannot locate b1 from beq in data structures`) where `beq = b1;` works. `Get(x) * 0.99`, implicit `Get(x) .99`, and an additive offset are valid TOPAS and understood by the checker; multi-`Get()` sums, nested functions and `prm` references are skipped with a note.

- `scripts/expand_inp_macros.py` — approximates the fully expanded `tc.log` text without running TOPAS; useful for macro-heavy files and tracing `at LINE N` errors.
  ```
  python scripts/expand_inp_macros.py file.inp
  python scripts/expand_inp_macros.py file.inp -o expanded.inp
  python scripts/expand_inp_macros.py file.inp --run-number 1   # Run_Number-dependent #if
  ```
  Resolves `#include`/`#ingest`, prunes `#define`/`#ifdef`/`#if` where safe, expands macros recursively (overload by arity, `@` auto-naming, `#m_argu`/`#m_ifarg`/`#m_else`/`#m_endif`). `#external_INP` lines are left in place with each linked file's expansion appended as a separate section (TOPAS doesn't merge them). `fn`/built-in functions are left untouched; output line numbers don't match `tc.log` (see `references/macro-expansion-and-log-files.md`).

  **TOPAS `&` macro syntax:** `macro & Name(...)` wraps every expansion in parens; `& arg` wraps that argument's substituted value. Not cosmetic — without it `divide(a + b, c - d)` expands to `a + b / c - d`.

  **`#include` resolves from the INP file's own directory unless a full path is given**, for both system `.inc` and project-local files (recursively), falling back to the system library only for a bare name not found locally.

- `scripts/find_refined_params.py` — **run whenever the user asks for the independent/refinable parameters in a `.inp`.** Lists named or `@`-auto-named, non-`!` parameters that aren't functions of other parameters (dependent ones excluded, manual §2.9).
  ```
  python scripts/find_refined_params.py file.inp [-o report.txt]
  ```
  Scans the macro-expanded text. `local` is re-scoped per xdd/phase (never deduplicated); `prm` and named keyword values are deduplicated by name (same name = same value). Bare unnamed un-`@` values (e.g. rigid-body output x/y/z) are not reported. **Loop rule:** in `for xdds`/`for strs [N to M]`, only anonymous `@` declarations (and `local`) multiply per iteration — a bare *named* `prm` stays one shared parameter. A bare `for strs` nested in another loop is left unmultiplied (scope unconfirmed). Limitations: keywords outside its curated lists can be missed; line numbers refer to expanded text.

- `scripts/run_variants.py` — **run whenever several model variants of one `.inp` need comparing** (peak shapes, PO, background order, ADP schemes, the false-minimum reset check, phase screening). Runs each on a scratch copy (base untouched) and prints one table:
  ```python
  import sys; sys.path.insert(0, r"<skill>/scripts")
  from run_variants import VariantRunner, add_to_str, add_to_xdd, set_bkg, comment_out

  r = VariantRunner("y2o3.inp", workdir="y2o3_workings")
  r.add("sh4",   lambda t: add_to_str(t, "PO_Spherical_Harmonics(sh, 4)"))
  r.add("steph", lambda t: add_to_str(t, "Stephens_cubic(@,0.5, @,0.0001, @,0.0001)"))
  r.add("b16",   lambda t: set_bkg(t, 16))
  r.run()
  ```
  ```
  variant       Rwp     dRwp      GoF   Npar  limits
  base      12.3439        -   1.2080     20  -
  sh4       11.6927  -0.6512   1.1440     22  -
  steph     12.8847  -0.4592   1.2600     23  steph_eta
  ```
  `base` runs first; others are deltas. `Npar` is TOPAS's independent-parameter count; `limits` lists parameters at `_LIMIT_MIN_`/`_LIMIT_MAX_` (a gain resting on a saturated term). A failed variant shows tc.exe's error in its row. Per variant it strips stale `C_matrix_normalized`, makes the `xdd` path absolute, and removes output macros (`Out_X_Yobs`, `Out_X_Ycalc`, `Out_X_Difference`, `Create_hklm_d_Th2_Ip_file`, `Create_hklm_d_Th2_IScaled_file`, `Out_CIF_STR`) — pass `keep_outputs=True` to keep them under per-variant names. Scratch files: `v_<basestem>_<name>.inp`. Pass `data_dir=` if the base is a scratch copy away from its data. Helpers (`add_to_str`, `add_to_xdd`, `set_bkg(n)`, `comment_out(regex)`) are literal string edits; write inline transforms for anything else. It reports numbers; it chooses nothing.

- `scripts/param_dependency_trees.py` — **run whenever the user asks for a parameter dependency tree/graph, or says "do trees"** (against the relevant/open `.inp`). **"do trees" defaults to interactive HTML** (`-o <name>.html`, opens in browser); text only if asked.
  ```
  python scripts/param_dependency_trees.py file.inp -o report.html     # default
  python scripts/param_dependency_trees.py file.inp                    # both trees to stdout
  python scripts/param_dependency_trees.py file.inp --tree dependent|independent
  python scripts/param_dependency_trees.py file.inp -o report.txt [--no-open]   # opens in VS Code
  ```
  General rule: text reports open in VS Code, HTML in the browser. Tree 1: each dependent parameter → what it references, down to independent/fixed leaves. Tree 2: each independent parameter → its dependents. Color-coded (green independent, blue dependent, grey fixed), with search. Includes `!`-fixed parameters, `rotate`/`translate`, and z-matrix equations (both syntax forms); the independent-count badge matches `find_refined_params.py`. Shows the full graph, a superset of TOPAS's `out_dependences`.

- **"Show Schema" is a standing trigger phrase**: open the install's pre-rendered kernel data-structure page via `python scripts/topas_install.py --kernel-schema-html`. If not found, say so — no bundled fallback.

- `scripts/c_matrix_heatmap.py` — renders a `C_matrix_normalized { ... }` block (from `.inp` or `.out`) as a blue/red heatmap.
  ```
  python scripts/c_matrix_heatmap.py file.inp                        # -> file_c_matrix.png
  python scripts/c_matrix_heatmap.py file.out -o heatmap.png --cell-size 30
  python scripts/c_matrix_heatmap.py file.inp --format html          # -> file_c_matrix.html
  ```
  `png`: no dependencies, index-only ticks (names printed to stdout). `html`: interactive with full names and hover — the better default unless a static image is needed.

- `scripts/plot_str_3d.py` — **run whenever the user asks for a 3D view of a `str` phase's structure.** Self-contained interactive HTML (orbit, zoom, perspective, optional labels): cell box, symmetry-expanded sites, different-element bonds by covalent-radius cutoff; sites with fully resolved `u11..u23` (incl. per-site names like `u11C1`) drawn as 50% thermal ellipsoids.
  ```
  python scripts/plot_str_3d.py file.inp                 # -> file_str3d.html
  python scripts/plot_str_3d.py file.inp --phase 2        # Nth str (1-indexed)
  python scripts/plot_str_3d.py file.inp --no-bonds
  python scripts/plot_str_3d.py file.inp --bond-tolerance 1.3
  ```
  Cell from literal `a`..`ga` (simple `Get()` ties) or a lattice macro. Colors/radii are approximate (visual aid only). Limitations: mixed occupancy drawn as first species; sites or cell parameters that don't resolve to numbers are skipped.

- `scripts/plot_sh_sphere.py` — **run whenever the user asks to see/plot a spherical-harmonics series as a pole figure or 3D surface** (`PO_Spherical_Harmonics` or any `spherical_harmonics_hkl`, e.g. anisotropic broadening). Self-contained interactive HTML. **Keep its on-page "not extensively tested" banner until it has more mileage.**
  ```
  python scripts/plot_sh_sphere.py file.inp                     # -> file_sh_sphere.html, raw dots
  python scripts/plot_sh_sphere.py file.inp --surface           # + surface/contour/radius toggles
  python scripts/plot_sh_sphere.py file.inp --phase 2 -o tex.html
  python scripts/plot_sh_sphere.py file.inp --surface --mesh-level 4   # finer, slower
  ```
  **Never re-derives the harmonics** (conventions differ between sources): it runs `tc.exe` at `iters 0` on a scratch copy with `Create_hklm_d_Th2_Ip_file(<file>, <sh_name>)`. Needs `TOPAS_DIR`. The anonymous `PO_Spherical_Harmonics(, order)` form fails with a message. Works for any space group; self-checks the metric and over-symmetrization and warns. **Dots are TOPAS-evaluated; surface and contours are interpolated** (warns above ~12° median spacing — low symmetry + narrow 2θ). Toggles: radius ∝ value, dots, surface, contours (5/9/15), a\*b\*c\* (on), cell + abc (off). It shows directions, not positions — a reading aid for spotting an implied PO direction.

- `scripts/plot_xy.py` — **run whenever the user asks to plot an XY(E) file** (`.xy`, `.xye`, `.dat`, `Out_X_Yobs`/`Out_X_Ycalc` output). Self-contained interactive HTML: pan/zoom, per-series toggles, crosshair, Sqrt(Y)/Linear toggle (signed sqrt), Y autoscaled to the visible window, optional `--stats "Rwp=13.68%,GoF=1.64"` in the header.
  ```
  python scripts/plot_xy.py file.xy [--title "My pattern"]        # -> file_xy_plot.html
  python scripts/plot_xy.py obs.xy calc.xy --labels "Yobs,Ycalc" --colors "blue,red" --diff "Yobs,Ycalc" -o out.html
  python scripts/plot_xy.py --phases "CeO2|ceo2_obs.xy|ceo2_calc.xy,Y2O3|y2o3_obs.xy|y2o3_calc.xy" -o out.html
  ```
  `--labels`/`--colors` parallel the files; a user's explicit colors are used literally. `--diff A,B` adds `A - B` (repeatable); difference curves share an offset that keeps them just below the data on any zoom. `--phases` (pipe-separated) builds a multi-phase plot with a fixed color scheme; it can't be mixed with positional files. `--ticks "NAME|ticks.txt,..."` adds reflection ticks.

  **"Run and plot [file]"**: the standing workflow is in `SKILL.md` ("Scripts").

- `scripts/build_report_docx.py` — **use if the user wants the final report as `.docx`.** Fills `templates/refinement_report_template.docx` (named styles) via `build_report(title, date, sections, out_path, images=..., plots=..., files=...)`; argument shapes, conventions ("Å" not "A") and an example are in its docstring. Don't hand-format a `.docx` or use `pandoc`. Restyle by editing the template's styles in Word; keep its body empty (it leaks into every report; `scripts/_build_template.py` rebuilds it). For an embedded fit image, render with `scripts/plot_xy_matplotlib.py` (same flags as `plot_xy.py`, PNG/JPG) and pass `images=[("caption", "fit.png")]`.

- `scripts/cif_to_str.py` — CIF → `str { }` with Wyckoff constraints; preferred over `cif1.exe` (see "Converting a CIF file to `str` format").
  ```
  python scripts/cif_to_str.py input.cif [-o output.txt] [--tolerance 0.002]   # default 0.0015
  ```
- `scripts/symmetry_utils.py` — shared crystallography library (operators, `sgcom6.exe`/`sg/` resolution, Wyckoff/ADP/lattice constraints) behind `cif_to_str.py`, `check_symmetry_constraints`, `insert_adps.py`, `plot_*`. Not a standalone tool.
- `scripts/rigid_body_builder.py` — z-matrix rigid bodies from a CIF: `--analyse`, `--build`, `--verify`, `--risk`; conventions in `references/28-z-matrix-rigid-body-conventions.md`.
- **Not chat-facing:** `scripts/symmetrize_str.py` (returns canonical site/cell edit spans for an editor extension) and `scripts/generate_space_group_browser.py` (regenerates `references/space_group_symbols.html` from `sgcom5.txt`; not currently present — run once if wanted).

- `scripts/fix_columns.py` — **run whenever the user says "fix columns"** (or asks to align `site` lines). Aligns consecutive `site` keywords (`x`/`y`/`z`/`occ`/`beq`/`u11`..`u23`) into columns, numbers right-aligned (left if a column mixes equations), `occ TYPE N` as two sub-columns; also aligns `la ... lo ... lh ...` lines under `lam`, one indent deeper than `lam`.
  ```
  site Ce1 x  0.25 y   0.5 z  0.25 occ Ce+4 1 beq = b1;
  site Ce2 x     0 y   0.5 z   0.5 occ Ce+4 1 beq = b1;
  ```
  ```
  python scripts/fix_columns.py file.inp [--check] [--lines 26-31]
  ```
  Whitespace-only; still run `check_inp_syntax.py`. `--lines` (1-indexed, inclusive) rewrites only that range — map an IDE selection to it.

- `scripts/format_inp_hierarchy.py` — **run whenever the user asks to reindent/reformat a `.inp` "hierarchically".** 3 spaces per level, never splits a line, collapses excess whitespace (not in strings, comments or `C_matrix_normalized`), runs `fix_columns` first, reopens in VS Code. Nesting comes from the manual's keyword hierarchy (`21-keyword-index.md`), since `xdd`/`str` sections have no braces.
  ```
  python scripts/format_inp_hierarchy.py file.inp [--check] [--no-open]
  ```

- `scripts/remove_errors.py` — **run whenever the user says "remove errors"** (see "Stripping refined-value errors").

- `scripts/insert_adps.py` — **run whenever the user says "insert adps"**: replaces `beq` on selected sites with symmetry-constrained `u11`..`u23` (space group from the file via TOPAS's database; no-op without `TOPAS_DIR`).
  ```
  python scripts/insert_adps.py file.inp [--lines 26-28] [--check]
  ```
  Starting `u11`/`u22`/`u33` = `Beq/8π²`, with `beq` resolved through its equation value, a same-named `prm`/`local`, or another site's `beq NAME value`; free off-diagonals start at 0; unresolvable → `0.01` with a warning. Re-aligns columns over the same range.

- `scripts/find_example.py` — **run whenever the user asks for a template/example/starting point** (e.g. "tof template"). Searches `.inp` files under `TOPAS_DIR` plus `example_inp_files/` (alone if unset), ranked bundled → `examples-index.md` → others (tier breaks score ties only); scratch files dropped. Pass 1 matches whole path tokens ("tof" matches `hrpd_tof_rietveld.inp`, not `tofullprof`); if <5 hits, pass 2 matches content against topic synonyms ("charge flipping" → `cf/`). `--bat <file>` searches a tc-list batch file instead, e.g. the install's own `tc-inps.bat`. It doesn't genericize results; `example_inp_files/tof_template.inp` shows what a hand-made template looks like.
  ```
  python scripts/find_example.py "tof template"           # trailing filler words stripped
  python scripts/find_example.py pawley -n 5              # default 8
  python scripts/find_example.py "charge flipping" --open # open top match in VS Code
  ```

- `scripts/to_Reel_v1.py` — converts `.xyd` output (from `Write_Rietveld_xyd`/`Writephase`; see `example_inp_files/d8_01612_vt_reel_02.inp`) to `.xyy` for Reel. **Copy it into the project directory first** — it's normally called from the `.inp` via `system_after_save_OUT { python to_Reel_v1.py <results_dir> }`, relative to tc.exe's cwd.
  ```
  python to_Reel_v1.py <directory_of_.xyd_files>
  ```
  Needs `results.txt` in the **cwd** with exact, case-sensitive headers `filename_reel`, `filename`, `r_wp`, `lam`, `Temperature`; a `.xyd` stem must equal its row's `filename_reel` exactly (unmatched → `WARNING`, `.xyy` written without metadata). Constants in the copied script: `delete_xyd` (default `True`, deletes even when metadata failed) and `write_background_subtracted` (default off; writes `data_background_subtracted/` in cwd). Multiprocessed — a whole batch at once is fine.

- `scripts/peak_search.py` — numerical peak search (a scriptable substitute for TOPAS-GUI's Search Peaks). Optional Rachinger Ka2 strip (`--rachinger`) for the search pass only; prominence against local Poisson noise (`--sig-mult`, default 5); output columns `pos2th height localbkg area flank` — use AREA, not height, as `I` in `load xo I { }`. Reads text, or a Bruker `.raw` converted once through `tc.exe` (needs `TOPAS_DIR`). Method and thresholds: `references/29-indexing-workflow-conventions.md` and the script's docstring.
  ```
  python scripts/peak_search.py yobs.xy [--rachinger] [-o peaks.txt]
  ```

- `scripts/group_cells.py` — collapses a TOPAS indexing `.ndx` into lattice families (Niggli-reduced primitive cells related by integer basis changes), with metric symmetry and index-2 to -4 supercell relations. Reads the best 300 rows by GoF by default (`--max-rows`; `--all` for every row, slow on large files); `--top` limits printing only. It relates lattices; it does not choose between them.
  ```
  python scripts/group_cells.py result.ndx --top 20 --members
  ```

- `scripts/compare_cells.py` — tests candidate cells (e.g. a cell and its supercell, or primitive vs centred) against the observed pattern, reporting reflections unique to each and whether the data show them. Reads raw counts, so check a "decisive" verdict on a Pawley baseline.
  ```
  python scripts/compare_cells.py yobs.xy --lam 1.540596 --cell c1 a b c al be ga --centering c1 P --cell c2 a2 b2 c2 al2 be2 ga2 --centering c2 F
  ```
