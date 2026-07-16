# System Include Files & Data Tables

TOPAS ships with a set of `.inc` macro libraries and `.txt`/data files that most INP files rely on implicitly — either included automatically by the program, or loaded internally when a keyword references them (e.g. a space group name, a scattering-factor lookup, an isotope mass). These are bundled here so the skill can check exact macro definitions and data-table contents rather than guessing.

## `references/system-files/inc/` — macro include files

| File | Purpose |
| --- | --- |
| `topas.inc` | The default macro library, included automatically by TOPAS at the start of every INP file (per the manual's threading/GUI chapter). Defines fundamental macros like `Pi`, `Deg`, and many of the standard macros referenced throughout the manual and worked examples (e.g. peak-shape and stacking-fault helper macros). Check here first if a macro is used in an example but never defined locally — it's very likely defined in `topas.inc`. |
| `local.inc` | An empty user-customization hook. `topas.inc` does `#include local.inc` near its top; users add their own personal macros/overrides here (e.g. `pdf.inc`'s own header comments show the convention of adding an `#include "path\to\file.inc"` line to `local.inc`). Bundled empty as-is — the point is that it's meant to be edited per-installation, not that it has fixed content. |
| `interface.inc` | GUI-facing macro/keyword interface definitions (e.g. `#delete_macros` blocks), mostly relevant to how the TOPAS-GUI exposes functionality rather than command-line INP authoring. |
| `Charge_Flipping.inc` | Macros supporting charge-flipping structure solution (e.g. `ATP` for randomizing phases of weak/non-weak reflections) — companion to `references/22-charge-flipping.md` and `references/examples/cf/`, `references/examples/cf-protein/`. |
| `PDF-Generate-0.inc`, `PDF-Generate.INC`, `PDF-Generate-Common.inc`, `GUI_PDF.inc`, `PDF-adps.inc`, `pdf.inc` | The PDF-generation/refinement macro family — Q-from-2theta conversions, ADP_5/ADP_7 site macros, fit/generate mode switches (`fit_to_data`, `generate_fq_gr_from_fit`, `fit_to_gr`). Companion to `references/08-pdf-generation.md`, `references/09-pdf-refinement.md`, and `references/examples/pdf*/`. Note `pdf.inc` is attributed to Phil Chater in its header comment, not part of the core `topas.inc` set — it's an optional include. |
| `Colours.inc` | Simple named-colour macros (`Black`, `Blue`, `DkGray`, etc.) used for graphical display keywords. |

## `references/system-files/data/` — data tables TOPAS reads

| File | Purpose |
| --- | --- |
| `sgcom5.txt` | The space-group generator table — defines every space group TOPAS recognizes (by number, computer-adapted symbol, and alternate settings), per its own header comment ("Space-group generator (c) 2000 Alan A. Coelho"). This is the authoritative source for valid `space_group` values and their accepted symbol variants. |
| `sgrots3.txt` | Space-group rotation matrices (e.g. `rotation_matrix 1A { 1 0 0 / 0 1 0 / 0 0 1 }`), used internally alongside `sgcom5.txt`. |
| `atmscat.txt` | X-ray atomic scattering factor table (Waasmaier–Kirfel form factors). |
| `anomdisp.txt` | Anomalous dispersion (f', f'') values by wavelength/element, keyed to standard characteristic emission lines (Ti Ka1, Cr Ka1, Fe Ka1, etc.). |
| `neutscat.txt` | Neutron scattering lengths by element/isotope (sourced from the CCP14 neutron scattering length tables per its header comment). |
| `isotopes.txt` | Atomic weights and isotopic composition data (NIST-sourced per its header comment). |
| `shubnikovgroups.txt` | Magnetic Shubnikov group definitions — referenced in the manual's Magnetic Structure Refinement chapter (`references/12-magnetic-structure-refinement.md`) as the source for magnetic space-group symmetry. |
| `help-1.txt` | Short plain-text help snippet for TOPAS-GUI 2D scan-window mouse/keyboard operations — GUI usage reference, not INP syntax. |

## Not included

Two other files in the same folder were deliberately left out: `aac.txt`, which turned out to be a stale `dir` command's text output (a directory listing), not a TOPAS reference file; and `info.txt`, which is the TOPAS-GUI's internal session-state file (recently-opened file paths, window positions, colour picker state) — it contains file paths from other people's projects and isn't reference material, so it was excluded rather than bundled into something meant for distribution. Several other `.txt`/`.inc` files in that folder were empty 0-byte state/config placeholders (`MaxNumThreads.txt`, `launch_file.txt`, `seed-tb.txt`, `seed-tc.txt`, `ver.txt`, `ver-new.txt`) and were skipped since there was no content to bundle.
