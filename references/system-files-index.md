# System Include Files & Data Tables

TOPAS ships a set of `.inc` macro libraries and `.txt` data files that most INP files rely on implicitly — included automatically, or loaded when a keyword references them (a space group name, a scattering-factor lookup, an isotope mass). This skill does not bundle them; they live in the TOPAS install root. Find it with `python scripts/topas_install.py --inc-dir`, and read the real file rather than guessing a macro's definition or a table's contents. The lists below describe what each file holds; which files are present varies by version and installation.

## Macro include files (`.inc`)

| File | Purpose |
| --- | --- |
| `topas.inc` | The default macro library, included automatically by TOPAS at the start of every INP file. Defines fundamental macros like `Pi` and `Deg` and most of the standard macros used in the manual and worked examples (peak-shape, restraint and stacking-fault helpers, etc.). Check here first if a macro is used in an example but never defined locally. |
| `local.inc` | An empty user-customization hook. `topas.inc` does `#include local.inc` near its top; users add their own macros, or `#include` lines for optional libraries, there. |
| `interface.inc` | GUI-facing macro/keyword interface definitions (e.g. `#delete_macros` blocks), mostly relevant to how TOPAS-GUI exposes functionality rather than command-line INP authoring. |
| `Charge_Flipping.inc` | Macros supporting charge-flipping structure solution (e.g. `ATP` for randomizing phases of weak/non-weak reflections) — companion to `references/22-charge-flipping.md` and the installation's `cf/` and `cf-protein/` examples. |
| `PDF-Generate-0.inc`, `PDF-Generate-Common.inc`, `GUI_PDF.inc`, `PDF-adps.inc`, `pdf.inc` (some versions also `PDF-Generate.INC`) | The PDF-generation/refinement macro family — Q-from-2theta conversions, ADP_5/ADP_7 site macros, fit/generate mode switches (`fit_to_data`, `generate_fq_gr_from_fit`, `fit_to_gr`). Companion to `references/08-pdf-generation.md` and `references/09-pdf-refinement.md`. `pdf.inc` is attributed to Phil Chater in its header — an optional include, not part of the core `topas.inc` set. |
| `WPPM_macros.inc` | Whole Powder Pattern Modelling macros by Scardi, Perez-Demydenko & Azanza Ricardo (e.g. `WPPM_Sphere`), for any space group. Optional include. |
| `cif.inc` | CIF-output macros by Matthew Rowles. Optional include: its header says to add `#include cif.inc` to `local.inc`. |
| `Colours.inc` | Simple named-colour macros (`Black`, `Blue`, `DkGray`, etc.) used for graphical display keywords. |

## Data tables TOPAS reads (`.txt`)

| File | Purpose |
| --- | --- |
| `sgcom5.txt` | The space-group generator table — every space group TOPAS recognizes (by number, computer-adapted symbol, and alternate settings). The authoritative source for valid `space_group` values and their accepted symbol variants. |
| `sgrots3.txt` | Space-group rotation matrices (e.g. `rotation_matrix 1A { 1 0 0 / 0 1 0 / 0 0 1 }`), used internally alongside `sgcom5.txt`. |
| `atmscat.txt` | X-ray atomic scattering factor table (Waasmaier–Kirfel form factors). |
| `anomdisp.txt` | Anomalous dispersion (f', f'') values by wavelength/element, keyed to standard characteristic emission lines (Ti Ka1, Cr Ka1, Fe Ka1, etc.). |
| `neutscat.txt` | Neutron scattering lengths by element/isotope (from the CCP14 neutron scattering length tables). |
| `isotopes.txt` | Atomic weights and isotopic composition data (NIST-sourced). |
| `shubnikovgroups.txt` | Magnetic Shubnikov group definitions — the source of magnetic space-group symmetry (`references/12-magnetic-structure-refinement.md`). |
| `help-1.txt` | Short plain-text help for TOPAS-GUI 2D scan-window mouse/keyboard operations — GUI usage, not INP syntax. |
