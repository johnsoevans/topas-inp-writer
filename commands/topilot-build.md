Build — and, if the job says so, run — the TOPAS refinement described by a job file. `$ARGUMENTS` is the path to a `<stem>_job.json`.

If no path was given, look for the most recently modified `*_job.json` in the working directory and say which one you picked. If there is none, stop and ask.

## 1. Build the `.inp`

Read the JSON, then invoke the **topas-inp-writer** skill and follow its conventions.

**`workflows` is a list of stages, in the order they must run** (`schema` 2). Apply each stage's conventions file in turn; one job can carry several:

- `peak_fitting` — `references/29-indexing-workflow-conventions.md`: peak search, single-phase screening, two-stage peak fitting, the unrestricted Bravais baseline, the Pawley check.
- `solve` — structure solution from the `solve` key (`method` is `simulated_annealing` or `charge_flipping`; `cell_from: "peak_fitting"` means the cell comes from the stage before it).
- `rietveld` — `references/27-rietveld-workflow-conventions.md`; the `rules` key (`rietveld` | `quantitative`) says which subset.
- `pdf` — G(r) refinement.

`sequential`, when present, is a **modifier, not a stage**: it wraps the refinement (`mode` is `list`, `per_dataset` or `parametric`) over the datasets. `data_files` is present in folder mode only; in list mode the file named by `data` is the record — parse it.

If a stage's conventions file is not in `references/` yet, use the main skill and **say in the report which stage ran without one** — do not guess at a file that does not exist.

Do not re-derive any of that here.

- Ground the file on the closest match in `example_inp_files/`; for a lab Rietveld job that is `tio2_lab_bragg_brentano_rietveld.inp`.
- `str` blocks come from `scripts/cif_to_str.py`.
- **`rigid_body: true` on a phase** — build it with `scripts/rigid_body_builder.py`, never by hand, following `references/28-z-matrix-rigid-body-conventions.md`. Four steps, in order:
  1. `--analyse <cif> --exclude "<rigid_exclude>"`, and **read it**. It gives the asymmetric unit with symmetry duplicates collapsed, each site's multiplicity and stabilising operators, the fragments that remain after exclusions, and what each fragment's symmetry permits. `rigid_exclude` absent means propose the exclusions yourself from its flags.
  2. Make the two calls it deliberately does not make: which fragments become rigid bodies, and each one's `free_rotation`/`free_translation`. `--build` on a spec missing those prints a template with every derivable field already filled and refuses to emit. Do not skip the read and guess — the DOF differed for every fragment in the set this was validated against.
  3. `--build <spec>` emits the `rigid` block on stdout (diagnostics go to stderr, so it redirects cleanly).
  4. `--verify <spec>` — **mandatory, not advisory.** It generates a plain-`site` control from the same CIF, matches everything non-structural, and fails on any disagreement in multiplicity, coordinates, calculated pattern, or whether a declared DOF is actually a rigid motion. A wrong rigid body still produces a plausible `.inp` and a clean convergence log; this is the only step that catches that.

  This is distinct from `solve.structure: "molecular"`, which carries a user-supplied fragment (`fragment_file`/`fragment_text`) as the *input* to a simulated anneal. If a job has both, the solve stage's own z-matrix is already the fragment — **reuse it for the rietveld stage rather than re-deriving one**, and do not expect the phase's `path` to point at a CIF that exists before solving.

  Site lines still come from `cif_to_str.py` — the rigid body supplies x/y/z, so those become placeholders. **Report the fragmentation**: which atoms ended up in which body and what was excluded. The user cannot otherwise tell whether the exclusion was right, and it is not decidable by element alone (a covalently bound heavy atom belongs in the body; the same element as a counter-ion does not).
- An **absent key means you decide** — it is not "off". A key that is present is binding and used as given.
- `variable_slits` absent: ask, per the skill's rule. Present: use it, and state which mode in the report. Absent because `radiation_kind` is `tof`, or because the instrument has no divergence slit: it does not apply — say so instead of asking.
- **The folder `out` names is the whole job's home.** The `.inp`, its `_job.json`, `_start.inp`/`_prev.inp`/`_history.tsv`, tick files, plots and any workings/scratch folder all go there — the workings folder inside it, not beside it. Write nothing into the data folder.

Then run `scripts/check_inp_syntax.py` and fix any FAIL. Open the file with `code <path>`, and point `launch_file.txt` at it (the skill's rule on that file — do it at creation, not only at end-of-session, since a create-only job never reaches one).

## 2. Run it

Only when `mode` is `create_and_run`. When `mode` is `continue`, **skip section 1 entirely** — the `.inp` exists and must not be regenerated — and start here on the file named in `out`.

Follow the skill's "Run and plot" workflow, with three deliberate overrides:

1. **The `.inp` is the master file.** `tc.exe` runs it in place and the `.out` is copied back over it after each cycle, so one file accumulates the refinement. This replaces the skill's default of running a scratch copy — do not restore it.
2. **Copy `<base>.inp` to `<base>_prev.inp` immediately before each copy-back**, and refuse the copy-back only if the `.out` is corrupt — missing, truncated, no `r_wp` line, or carrying a `nan`/`inf` **value**. Match those word-boundary anchored (`nan`, `inf`, plus MSVC's `1.#INF`/`1.#QNAN`) and ignore comment lines: a bare substring search hits the word "information" in the file's own header, and since comments survive copy-back by design, that would deadlock every future cycle of that refinement with no visible cause. A worse Rwp or a pinned parameter is reported loudly and copied back anyway; some of the skill's own checks require runs that legitimately converge worse.
3. **Append a line to `<base>_history.tsv`** each cycle: cycle, timestamp, Rwp, GoF, Npar, what changed. Nothing else survives the copy-back.

## 3. Report

Output path, phases, what refines, any assumption you made (name the slit mode explicitly), Rwp and GoF if it ran, and the change in Rwp against the previous cycle from the history file.
