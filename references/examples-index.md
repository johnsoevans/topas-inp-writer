# Worked-Example Index

This indexes real TOPAS `.inp` example files bundled under `references/examples/`. These are complete, working refinement scripts (not manual excerpts) covering many refinement types. Before writing a new INP file from scratch, grep this folder or check the table below for an existing example close to the task at hand, and adapt its structure/macros rather than inventing syntax.

Detected topics are heuristic (regex-based keyword detection on the first ~20KB of each file) and may be incomplete or miss secondary topics in a file — treat them as a starting hint, not a definitive label. When unsure, open the file directly or grep for the exact keyword you need across the whole `examples/` folder.

**A note on pruned examples.** Three example files were removed after review because they were near-duplicates that added no new syntax/technique beyond a smaller sibling already in the corpus, saving about 8.3 MB with no loss of documented technique: `sp2/cholestane/cif2ta.inp` (identical `SHELX_HKL4`/restraint-list technique to `sp2/alanine/cif2ta.inp`, just ~10x more repetitive restraint lines for a bigger molecule), `pdf-generate/Silicon/decon.inp` (the same 3-operation `Include_PDF_Generate` pipeline already demonstrated by `LiFePO4/decon.inp`, `Fullerene/decon.inp`, and `Tungsten/decon.inp`, none of which are specifically discussed by name for Silicon in `references/08-pdf-generation.md`), and `sp/serine_i_evans_n_ta_bang_rot-z.inp` (identical to `sp/serine_i_evans_n_ta_bang_rot.inp` apart from one `#define USE_Z_MATRIX` flag — the z-matrix/rigid-body technique it toggles is already covered by the dedicated `rigid/` folder). Four `.out` files that were byte-identical to their own `.inp` (meaning the run changed nothing) were also removed as pure duplicates: `external_inp/instrument.out`, `PDF-adps/approx-1.out`, `xrd-ct/xrd-ct-1.out`, `grs-alvo4/solve-1.out` — their `.inp` counterparts remain and are identical in content. Genuinely-varied examples that merely look similar at a glance (e.g. the 18 `cf-protein/*/Solve.inp` charge-flipping recipes across different space groups, or `single-crystal/ae1-*.inp`'s different techniques applied to the same compound) were deliberately kept, since each demonstrates different tuning choices or a different keyword/technique, not the same lesson repeated.

## (root)/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `al2o3a.inp` | 0.6 KB | Rietveld/structure |  |
| `alvo4-decompose.inp` | 5.0 KB | Rietveld/structure |  |
| `alvo4-grs-auto.inp` | 4.2 KB | Rietveld/structure, Restraints/penalties |  |
| `alvo4-rigid.inp` | 3.8 KB | Rietveld/structure, Rigid bodies, Restraints/penalties | approximate_A |
| `alvo4_tch.inp` | 1.9 KB | Rietveld/structure |  |
| `alvo4a.inp` | 3.4 KB | Rietveld/structure, Restraints/penalties |  |
| `amor.inp` | 2.5 KB | Rietveld/structure, Quantitative analysis |  |
| `au111.inp` | 0.8 KB | (unclassified — open to inspect) |  |
| `bauxite.inp` | 5.6 KB | Rietveld/structure, Quantitative analysis | do_errors |
| `benzene.inp` | 2.4 KB | Rietveld/structure |  |
| `benzene_ai1.inp` | 1.4 KB | Rietveld/structure, Restraints/penalties |  |
| `benzene_ai2.inp` | 1.4 KB | Rietveld/structure, Restraints/penalties |  |
| `benzene_ai3.inp` | 1.5 KB | Rietveld/structure, Restraints/penalties |  |
| `bkg-straight-line.inp` | 0.7 KB | (unclassified — open to inspect) |  |
| `brucite.inp` | 0.9 KB | Rietveld/structure |  |
| `ceo2.inp` | 2.1 KB | Rietveld/structure, Quantitative analysis |  |
| `ceo2b.inp` | 1.0 KB | Rietveld/structure, Quantitative analysis |  |
| `ceo2hkl.inp` | 1.5 KB | Rietveld/structure | #define CREATE_ |
| `chi2-ceo2.inp` | 1.4 KB | Rietveld/structure |  |
| `cime-decompose.inp` | 9.2 KB | Rietveld/structure, Restraints/penalties |  |
| `cime-z-auto.inp` | 7.6 KB | Rietveld/structure, Rigid bodies, Restraints/penalties |  |
| `cime_pawley.inp` | 1.4 KB | Pawley, Rietveld/structure |  |
| `clay.inp` | 12.5 KB | Pawley, Rietveld/structure, Quantitative analysis |  |
| `cpd-4.inp` | 2.3 KB | Rietveld/structure, Quantitative analysis |  |
| `cr2o3.inp` | 0.8 KB | Rietveld/structure | do_errors |
| `cr2o3_out_f2.inp` | 0.9 KB | Rietveld/structure |  |
| `cylcorr.inp` | 1.3 KB | Rietveld/structure, Quantitative analysis |  |
| `divergence-sample-length.inp` | 1.2 KB | Rietveld/structure |  |
| `ed_si_pawley.inp` | 2.0 KB | Pawley, Rietveld/structure, TOF |  |
| `ed_si_str.inp` | 1.9 KB | Rietveld/structure |  |
| `fourier-map-ae14.inp` | 4.4 KB | Rietveld/structure |  |
| `fourier-map-cime.inp` | 2.4 KB | Rietveld/structure |  |
| `hash_prm.inp` | 2.0 KB | (unclassified — open to inspect) |  |
| `include-io.inp` | 0.1 KB | (unclassified — open to inspect) |  |
| `lab61.inp` | 1.0 KB | Rietveld/structure |  |
| `li025.inp` | 2.7 KB | Rietveld/structure, Quantitative analysis |  |
| `li250.inp` | 2.2 KB | Rietveld/structure, Quantitative analysis |  |
| `madelung.inp` | 0.9 KB | Rietveld/structure |  |
| `many.inp` | 1.3 KB | Rietveld/structure, Quantitative analysis |  |
| `md-test.inp` | 1.5 KB | Rietveld/structure, Energy minimization/MD | #define CREATE_ |
| `negx.inp` | 0.5 KB | (unclassified — open to inspect) | A macro that defines an emission profile that is 2Th independent |
| `occ-constrain.inp` | 2.0 KB | Rietveld/structure | #define CREATE_ |
| `occ-merge-test.inp` | 1.6 KB | Rietveld/structure | #define CREATE_ |
| `occ-merge.inp` | 2.3 KB | Rietveld/structure, Quantitative analysis |  |
| `out-1.inp` | 2.8 KB | Rietveld/structure |  |
| `out_prm_vals.inp` | 2.6 KB | Rietveld/structure |  |
| `pbso4a.inp` | 1.7 KB | Rietveld/structure, Quantitative analysis | do_errors approximate_A |
| `peak_buffer_step_1.inp` | 1.5 KB | Rietveld/structure |  |
| `pvs.inp` | 0.9 KB | (unclassified — open to inspect) |  |
| `quartz.inp` | 0.5 KB | Rietveld/structure |  |
| `quarz2_fpa.inp` | 0.8 KB | (unclassified — open to inspect) |  |
| `remove-phase.inp` | 4.1 KB | Rietveld/structure, Quantitative analysis |  |
| `robust.inp` | 0.5 KB | Rietveld/structure, Quantitative analysis |  |
| `scale_phase_X.inp` | 2.8 KB | Rietveld/structure, Quantitative analysis | #define CREATE_ |
| `sites_geometry_1.inp` | 1.4 KB | Rietveld/structure, Rigid bodies, Restraints/penalties |  |
| `sites_geometry_2.inp` | 1.6 KB | Rietveld/structure, Restraints/penalties |  |
| `spv.inp` | 0.6 KB | (unclassified — open to inspect) |  |
| `spvii.inp` | 0.3 KB | (unclassified — open to inspect) |  |
| `titanate.inp` | 1.2 KB | Rietveld/structure | continue_after_convergence |
| `tube-tails.inp` | 1.5 KB | Rietveld/structure | #define CREATE_ |
| `udefa.inp` | 0.6 KB | (unclassified — open to inspect) | #define CREATE_ |
| `var_div_y2o3.inp` | 0.6 KB | Rietveld/structure |  |
| `xois.inp` | 0.7 KB | (unclassified — open to inspect) | Both xdd's will use the following |
| `xy.inp` | 6.0 KB | Rietveld/structure |  |
| `y2o3a.inp` | 1.9 KB | Rietveld/structure, Quantitative analysis |  |
| `zhu3a.inp` | 2.1 KB | Rietveld/structure |  |
| `zro2.inp` | 3.8 KB | Rietveld/structure, Quantitative analysis |  |

## 1000s-of-patterns/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `1000s-of-patterns/fit.inp` | 3.2 KB | Rietveld/structure | #define CREATE__ |

## 3d/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `3d/a_to_g_surface_05d.inp` | 517.9 KB | Rietveld/structure, Stacking faults, Quantitative analysis | Input file to fit cubic to gamma SnMo2O8 phase transition Sample slowly heated to 390 K then held is |

## Capillary/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `Capillary/lab6-d8.inp` | 3.4 KB | Rietveld/structure | #define SEMI_EMPIRICAL ' Sabine |
| `Capillary/lab6-stoe.inp` | 3.6 KB | Rietveld/structure, Quantitative analysis | #define SEMI_EMPIRICAL ' Sabine |

## Deconvolution/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `Deconvolution/pbso4-decon.inp` | 1.7 KB | Deconvolution |  |

## Linear-PSD/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `Linear-PSD/lpsd-simulated.inp` | 1.4 KB | Rietveld/structure |  |

## PDF-adps/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `PDF-adps/Fit_to_Gr.inp` | 9.7 KB | Rietveld/structure, PDF |  |
| `PDF-adps/approx-1.inp` | 3.1 KB | Rietveld/structure, PDF | #define FIT_USING_ADPs_5 #define DETERMINE_unns_FROM_ADPs_5 |

## absorption-edge/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `absorption-edge/al2o3-pam.inp` | 0.9 KB | Rietveld/structure |  |
| `absorption-edge/ni-lab6.inp` | 1.2 KB | Rietveld/structure |  |
| `absorption-edge/rutile-anatase-ni.inp` | 2.3 KB | Rietveld/structure, Quantitative analysis |  |
| `absorption-edge/rutile-anatase.inp` | 2.1 KB | Rietveld/structure, Quantitative analysis |  |
| `absorption-edge/spinel-pam.inp` | 0.9 KB | Rietveld/structure |  |

## cf/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `cf/alvo4a.inp` | 5.4 KB | Rietveld/structure | do_errors |
| `cf/cf-ae14.inp` | 0.5 KB | Rietveld/structure, Charge flipping |  |
| `cf/cf-ae5-poor.inp` | 0.8 KB | Rietveld/structure, Charge flipping |  |
| `cf/cf-ae5.inp` | 0.5 KB | Rietveld/structure, Charge flipping |  |
| `cf/cf-ae9-poor.inp` | 0.7 KB | Rietveld/structure, Charge flipping |  |
| `cf/cf-ae9.inp` | 0.6 KB | Rietveld/structure, Charge flipping |  |
| `cf/cf-alvo4-pawley.inp` | 0.5 KB | Pawley, Rietveld/structure |  |
| `cf/cf-alvo4.inp` | 1.5 KB | Pawley, Rietveld/structure, Charge flipping |  |
| `cf/cf-cime-histo.inp` | 1.0 KB | Pawley, Rietveld/structure, Charge flipping |  |
| `cf/cf-cime-pawley.inp` | 65.5 KB | Pawley, Rietveld/structure |  |
| `cf/cf-cime-poor-histo.inp` | 1.0 KB | Pawley, Rietveld/structure, Charge flipping |  |
| `cf/cf-cime-poor.inp` | 0.9 KB | Pawley, Rietveld/structure, Charge flipping |  |
| `cf/cf-cime.inp` | 1.2 KB | Pawley, Rietveld/structure, Charge flipping |  |
| `cf/cf-gebaa.inp` | 0.8 KB | Rietveld/structure, Charge flipping |  |
| `cf/cf-pn-02.inp` | 0.5 KB | Rietveld/structure, Charge flipping |  |
| `cf/cf-sucrose-pawley.inp` | 42.6 KB | Pawley, Rietveld/structure |  |
| `cf/cf-sucrose.inp` | 1.2 KB | Rietveld/structure, Charge flipping |  |
| `cf/cf-ylidm.inp` | 0.7 KB | Rietveld/structure, Charge flipping, Single crystal |  |
| `cf/cime.inp` | 1.8 KB | Rietveld/structure |  |

## cf-protein/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `cf-protein/1A7Y-P1/Solve.inp` | 1.2 KB | Charge flipping |  |
| `cf-protein/1AHO-P212121/Solve.inp` | 0.9 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1B0Y-P212121/Solve.inp` | 0.5 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1BYZ-P1/Solve.inp` | 0.6 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1C75-P212121/1-atom.inp` | 1.2 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1C75-P212121/Solve.inp` | 0.8 KB | Rietveld/structure, Charge flipping | iters 1000 |
| `cf-protein/1CKU-P212121/1-atom.inp` | 1.0 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1CKU-P212121/Solve.inp` | 1.0 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1CTJ-R3R/1-atom.inp` | 1.1 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1CTJ-R3R/Solve.inp` | 0.8 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1DY5-P21/Solve.inp` | 2.6 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1HHZ-P3221/Solve.inp` | 1.3 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1MC2-C2/Solve.inp` | 0.8 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/1SWZ-P3221/Solve.inp` | 1.4 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/2ERL-C2/Solve.inp` | 1.0 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/2KNT-P21/Solve.inp` | 1.0 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/2PVB-P212121/1-atom.inp` | 0.6 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/2PVB-P212121/Solve.inp` | 0.8 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/2PVB-P212121/gen.inp` | 0.1 KB | (unclassified — open to inspect) |  |
| `cf-protein/2PVB-P212121/match.inp` | 27.7 KB | Rietveld/structure, Rigid bodies, Restraints/penalties |  |
| `cf-protein/2WFI-P212121/1-atom.inp` | 1.5 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/2WFI-P212121/Solve.inp` | 0.8 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/4LZT-P1/2-atoms.inp` | 1.1 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/4LZT-P1/solve.inp` | 0.8 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/5DA6-R32/1-atom.inp` | 2.3 KB | Rietveld/structure, Charge flipping |  |
| `cf-protein/5DA6-R32/Solve.inp` | 1.0 KB | Rietveld/structure, Charge flipping | For testing |
| `cf-protein/6Y84-C121/Refinement.inp` | 528.2 KB | Rietveld/structure |  |

## cross-corr/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `cross-corr/cross.inp` | 1.9 KB | Rietveld/structure |  |

## dispersion/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `dispersion/disp.inp` | 1.1 KB | (unclassified — open to inspect) |  |

## external_inp/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `external_inp/ext_inp.inp` | 0.3 KB | Quantitative analysis |  |
| `external_inp/instrument.inp` | 0.1 KB | (unclassified — open to inspect) |  |
| `external_inp/str.inp` | 0.3 KB | Rietveld/structure |  |

## f0-f1-f11/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `f0-f1-f11/tof.inp` | 1.1 KB | Rietveld/structure, TOF | #define CREATE_ |
| `f0-f1-f11/xray-powder.inp` | 2.4 KB | Rietveld/structure | #define CREATE_ |

## ft/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `ft/alvo4a.inp` | 2.8 KB | Rietveld/structure |  |
| `ft/create-voigt.inp` | 3.4 KB | (unclassified — open to inspect) |  |
| `ft/gaussian.inp` | 1.0 KB | (unclassified — open to inspect) |  |
| `ft/lorentzian.inp` | 0.9 KB | (unclassified — open to inspect) |  |
| `ft/voigt.inp` | 1.4 KB | (unclassified — open to inspect) |  |

## function-approximation/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `function-approximation/gaussian_with_hats.inp` | 0.3 KB | (unclassified — open to inspect) |  |
| `function-approximation/gaussian_with_poly.inp` | 0.3 KB | (unclassified — open to inspect) |  |
| `function-approximation/pvii_with_2pvs.inp` | 0.6 KB | (unclassified — open to inspect) |  |
| `function-approximation/xa_exp_bx_with_exp_convolutions.inp` | 0.8 KB | (unclassified — open to inspect) |  |

## functions/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `functions/alvo4-fn.inp` | 43.1 KB | Rietveld/structure, Restraints/penalties |  |
| `functions/alvo4-normal.inp` | 2.6 KB | Rietveld/structure |  |

## grs-alvo4/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `grs-alvo4/grs-0.inp` | 0.3 KB | (unclassified — open to inspect) |  |
| `grs-alvo4/md-1.inp` | 2.8 KB | Rietveld/structure, Energy minimization/MD, Restraints/penalties |  |
| `grs-alvo4/md-2.inp` | 20.2 KB | Rietveld/structure, Energy minimization/MD, Restraints/penalties |  |
| `grs-alvo4/md-3.inp` | 20.3 KB | Rietveld/structure, Energy minimization/MD, Restraints/penalties |  |
| `grs-alvo4/md-4.inp` | 21.5 KB | Rietveld/structure, Energy minimization/MD, Restraints/penalties |  |
| `grs-alvo4/rep-1.inp` | 5.5 KB | Rietveld/structure, Restraints/penalties |  |
| `grs-alvo4/rep-2.inp` | 5.9 KB | Rietveld/structure, Restraints/penalties |  |
| `grs-alvo4/solve-1.inp` | 5.5 KB | Rietveld/structure, Restraints/penalties |  |

## indexing/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `indexing/cime.inp` | 1.2 KB | (unclassified — open to inspect) |  |
| `indexing/ex1.inp` | 0.6 KB | (unclassified — open to inspect) |  |
| `indexing/ex10.inp` | 1.0 KB | (unclassified — open to inspect) | #define DO_DETAILS ' uncomment this line to reprocess the following solutions |
| `indexing/ex11.inp` | 2.1 KB | (unclassified — open to inspect) |  |
| `indexing/ex12.inp` | 1.8 KB | (unclassified — open to inspect) |  |
| `indexing/ex13.inp` | 1.7 KB | (unclassified — open to inspect) |  |
| `indexing/ex14.inp` | 0.6 KB | (unclassified — open to inspect) |  |
| `indexing/ex2.inp` | 0.8 KB | Protein/macromolecule | index_zero_error |
| `indexing/ex3.inp` | 0.5 KB | (unclassified — open to inspect) |  |
| `indexing/ex4.inp` | 0.5 KB | (unclassified — open to inspect) |  |
| `indexing/ex5.inp` | 0.7 KB | (unclassified — open to inspect) |  |
| `indexing/ex6.inp` | 0.6 KB | (unclassified — open to inspect) |  |
| `indexing/ex7.inp` | 0.6 KB | (unclassified — open to inspect) |  |
| `indexing/ex8.inp` | 1.7 KB | (unclassified — open to inspect) |  |
| `indexing/ex9.inp` | 0.6 KB | (unclassified — open to inspect) |  |
| `indexing/template.inp` | 0.8 KB | (unclassified — open to inspect) | All crystal systems |

## k-factor/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `k-factor/k-factor.inp` | 71.4 KB | Pawley, Rietveld/structure, Quantitative analysis | -------------Connor, Raven and Neubauer method for amorphous phase quantification-------- |

## laue/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `laue/laue.inp` | 5.2 KB | Rietveld/structure |  |

## load-save-locals/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `load-save-locals/lsl.inp` | 0.7 KB | Rietveld/structure |  |

## lp-search/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `lp-search/lp-search-pbso4.inp` | 1.1 KB | Pawley, Rietveld/structure, Indexing, Restraints/penalties |  |
| `lp-search/lpder1.inp` | 0.9 KB | Pawley, Rietveld/structure, Indexing |  |

## mag/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `mag/JohnEvans/jsoe_fit_cc2c_tofullprofmono_01.inp` | 3.5 KB | Rietveld/structure, Magnetic | Simulate magnetic scatter for Fe in plane in monoclinic setting in P1 JSOE 18/6/2012 |
| `mag/JohnEvans/jsoe_fit_cc2c_top1ortho_01.inp` | 3.5 KB | Rietveld/structure, Magnetic | Simulate magnetic scatter for Fe in plane in monoclinic setting in P1 JSOE 18/6/2012 |
| `mag/JohnEvans/jsoe_fit_p1_tofullproftric_01.inp` | 2.9 KB | Rietveld/structure, Magnetic | Simulate magnetic scatter for Fe in plane in monoclinic setting in P1 JSOE 18/6/2012 |
| `mag/al2/fe3c51694prm-magn_monoklin.inp` | 7.7 KB | Rietveld/structure, Quantitative analysis, Magnetic, TOF | Input File for simple tof Rietveld Refinement Use save/set current button then run with F6 in topas |
| `mag/al2/fe3c51694prm-magn_orth.inp` | 6.4 KB | Rietveld/structure, Quantitative analysis, Magnetic, TOF | Input File for simple tof Rietveld Refinement Use save/set current button then run with F6 in topas |
| `mag/al2/fe3c51694prm-magn_triklin.inp` | 7.7 KB | Rietveld/structure, Quantitative analysis, Magnetic, TOF | Input File for simple tof Rietveld Refinement Use save/set current button then run with F6 in topas |
| `mag/mag-2.inp` | 1.0 KB | Rietveld/structure, Magnetic | #define CREATE_ |
| `mag/mag-only.inp` | 1.2 KB | Rietveld/structure, Magnetic | #define CREATE_ |
| `mag/mag.inp` | 1.8 KB | Rietveld/structure, Magnetic | #define CREATE_ |
| `mag/maglamno3_magnetic.inp` | 2.1 KB | Rietveld/structure, Magnetic | continue_after_convergence randomize_on_errors |
| `mag/occ-merge.inp` | 1.8 KB | Rietveld/structure, Magnetic | #define CREATE_ |

## pdf/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `pdf/alvo4/rigid.inp` | 3.2 KB | Rietveld/structure, Rigid bodies, Restraints/penalties | iters 10 approximate_A |
| `pdf/alvo4/structure-solution-create.inp` | 4.0 KB | Rietveld/structure |  |
| `pdf/alvo4/structure-solution.inp` | 2.0 KB | Rietveld/structure |  |
| `pdf/beq-2-create.inp` | 2.4 KB | Rietveld/structure |  |
| `pdf/beq-2.inp` | 4.0 KB | Rietveld/structure, Quantitative analysis | Macro switches - Insert/remove @ to refine or not refine approximate_A |
| `pdf/beq-3-create.inp` | 2.0 KB | Rietveld/structure |  |
| `pdf/beq-3.inp` | 3.5 KB | Rietveld/structure | Macro switches to refine or or not refine |
| `pdf/occ-merge-pbso4/create.inp` | 0.7 KB | Rietveld/structure |  |
| `pdf/occ-merge-pbso4/occ-merge-test.inp` | 0.8 KB | Rietveld/structure |  |
| `pdf/occ-merge-pbso4/occ-merge.inp` | 0.9 KB | Rietveld/structure |  |
| `pdf/pdf-1.inp` | 1.5 KB | Rietveld/structure, PDF | #define CREATE_ |
| `pdf/pdf-2.inp` | 2.7 KB | Rietveld/structure, PDF | #define CREATE_ |

## pdf-generate/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `pdf-generate/Fullerene/decon.inp` | 203.0 KB | Restraints/penalties | START USER INPUT SECTION Zero means no smoothing |
| `pdf-generate/LiFePO4/decon.inp` | 404.9 KB | Rietveld/structure, Restraints/penalties | START USER INPUT SECTION Zero means no smoothing |
| `pdf-generate/LiFePO4/gr-to-fq.inp` | 0.7 KB | (unclassified — open to inspect) |  |
| `pdf-generate/Tungsten/decon.inp` | 6.2 KB | Rietveld/structure, Restraints/penalties | === START USER INPUT SECTION === Zero means no smoothing |

## peak-intensity-extraction/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `peak-intensity-extraction/cr2o3hkl.inp` | 0.4 KB | Pawley, Rietveld/structure |  |
| `peak-intensity-extraction/lebail1.inp` | 0.7 KB | Pawley, Rietveld/structure |  |
| `peak-intensity-extraction/pawley1.inp` | 1.4 KB | Pawley, Rietveld/structure | Uncomment the following to view the effects of quick_refine_remove |
| `peak-intensity-extraction/zhu3lebail.inp` | 1.0 KB | Pawley, Rietveld/structure | #define USE_PAWLEY '  Comment this line out for Lebail |

## penalties-restraints/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `penalties-restraints/hock.inp` | 1.7 KB | Restraints/penalties |  |
| `penalties-restraints/onlypena.inp` | 0.7 KB | Restraints/penalties |  |
| `penalties-restraints/rastrigin.inp` | 0.4 KB | Restraints/penalties |  |
| `penalties-restraints/rosenbrock-10-restraint.inp` | 1.9 KB | Restraints/penalties |  |
| `penalties-restraints/rosenbrock-10.inp` | 1.5 KB | Restraints/penalties |  |

## po-constrained/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `po-constrained/po-constrained-create.inp` | 2.0 KB | Rietveld/structure, Quantitative analysis |  |
| `po-constrained/po-for.inp` | 1.4 KB | Rietveld/structure, Quantitative analysis | #define TEST_ |
| `po-constrained/posh-constrained-create.inp` | 3.0 KB | Rietveld/structure, Quantitative analysis |  |
| `po-constrained/posh-for.inp` | 1.3 KB | Rietveld/structure, Quantitative analysis | #define TEST_ |

## pvem/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `pvem/pvem-1.inp` | 1.6 KB | Rietveld/structure |  |

## quant/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `quant/quant-1.inp` | 3.0 KB | Rietveld/structure, Quantitative analysis |  |
| `quant/quant-2.inp` | 1.5 KB | Rietveld/structure, Quantitative analysis |  |
| `quant/quant-3.inp` | 1.8 KB | Rietveld/structure, Quantitative analysis |  |
| `quant/quant-4.inp` | 2.8 KB | Pawley, Rietveld/structure, Quantitative analysis |  |
| `quant/quant-5.inp` | 2.5 KB | Rietveld/structure, Quantitative analysis |  |
| `quant/quant-6.inp` | 3.1 KB | Pawley, Rietveld/structure, Quantitative analysis |  |
| `quant/quant-7-create.inp` | 0.6 KB | Rietveld/structure |  |
| `quant/quant-7.inp` | 2.1 KB | Rietveld/structure, Quantitative analysis |  |
| `quant/quant-8.inp` | 0.1 KB | (unclassified — open to inspect) |  |
| `quant/zro2-restraint-wt.inp` | 1.8 KB | Rietveld/structure, Quantitative analysis, Restraints/penalties | Example of restraining weight percent to a known value |
| `quant/zro2-restraint-xrf-zr.inp` | 6.2 KB | Rietveld/structure, Quantitative analysis, Restraints/penalties | Example of restraining elemental weight percent of Zr to a known value (ie. XRF for example) |

## rigid/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `rigid/adn_glass-84k_vct#2_p1a1_ref.inp` | 5.6 KB | Rietveld/structure, Quantitative analysis, Rigid bodies | Auto_T(10) |
| `rigid/rigida-1.inp` | 1.4 KB | Rietveld/structure, Rigid bodies | #define CREATE_ |
| `rigid/rigida-2.inp` | 1.8 KB | Rietveld/structure, Rigid bodies | #define CREATE_ |
| `rigid/rigida-3.inp` | 0.8 KB | Rietveld/structure, Rigid bodies | #define CREATE_ |
| `rigid/rigidb.inp` | 5.4 KB | Rietveld/structure, Rigid bodies |  |

## rigid-errors/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `rigid-errors/aniline_i_100k_x.inp` | 106.7 KB | Rietveld/structure, Quantitative analysis, Rigid bodies |  |

## single-crystal/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `single-crystal/ae1-adps.inp` | 3.9 KB | Rietveld/structure |  |
| `single-crystal/ae1-approx-a.inp` | 4.0 KB | Rietveld/structure |  |
| `single-crystal/ae1-auto.inp` | 2.7 KB | Rietveld/structure, Single crystal, Restraints/penalties |  |
| `single-crystal/ae1-manual.inp` | 3.6 KB | Rietveld/structure, Single crystal, Restraints/penalties |  |
| `single-crystal/ae14-adps.inp` | 6.3 KB | Rietveld/structure, Single crystal |  |
| `single-crystal/ae14-approx-a.inp` | 5.8 KB | Rietveld/structure, Single crystal |  |
| `single-crystal/ae5-auto.inp` | 2.8 KB | Rietveld/structure, Single crystal, Restraints/penalties |  |
| `single-crystal/gebaa.inp` | 2.0 KB | Rietveld/structure, Single crystal |  |
| `single-crystal/pn_02_2.inp` | 314.8 KB | Rietveld/structure, Restraints/penalties | trying to solve Mo2P4O15 in pn file from atoms_07 on 20/4/04 |
| `single-crystal/ylidma.inp` | 4.1 KB | Rietveld/structure, Single crystal |  |

## sp/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `sp/serine_i_evans_n_ta_bang_rot.inp` | 526.0 KB | Rietveld/structure, Rigid bodies, Single crystal |  |

## sp2/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `sp2/alanine/cif2ta.inp` | 56.5 KB | Rietveld/structure, Restraints/penalties |  |

## stacking-faults/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `stacking-faults/Rietveld-Generate/Create-Sequences.inp` | 1.6 KB | Rietveld/structure, Stacking faults |  |
| `stacking-faults/Rietveld-Generate/Fit-to-Rietveld-Generated.INP` | 1.4 KB | Rietveld/structure, Stacking faults |  |
| `stacking-faults/Rietveld-Generate/Rietveld-Generate.inp` | 1.2 KB | Rietveld/structure |  |
| `stacking-faults/debye-new.inp` | 1.4 KB | Rietveld/structure, Stacking faults, Quantitative analysis |  |
| `stacking-faults/debye-old.inp` | 1.4 KB | Rietveld/structure, Stacking faults, Quantitative analysis |  |
| `stacking-faults/fit-1.inp` | 1.5 KB | Rietveld/structure, Stacking faults, Quantitative analysis |  |
| `stacking-faults/fit-2.inp` | 2.0 KB | Rietveld/structure, Stacking faults | #define CREATE_ num_runs 10 |
| `stacking-faults/fit-3.inp` | 4.2 KB | Rietveld/structure, Stacking faults | #define CREATE_ |
| `stacking-faults/kaolinite.inp` | 5.5 KB | Rietveld/structure, PDF, Stacking faults, Quantitative analysis | #define TEST_1_ |

## stretch-pks/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `stretch-pks/stretch-1.inp` | 1.0 KB | Rietveld/structure | #define CREATE_ |

## tof/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `tof/tof-to-Q.inp` | 3.0 KB | Rietveld/structure, TOF | #define CONVERT_TEST_TOF_PATTERN_TO_Q #define FIT_TO_CONVERTED_PATTERN |
| `tof/tof_balzar_br1.inp` | 1.2 KB | Rietveld/structure, TOF |  |
| `tof/tof_balzar_sh1.inp` | 1.1 KB | Pawley, Rietveld/structure, TOF |  |
| `tof/tof_bank2_1.inp` | 2.0 KB | Rietveld/structure, Quantitative analysis, TOF |  |
| `tof/tof_bank2_2.inp` | 1.9 KB | Rietveld/structure |  |

## transform_x/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `transform_x/tpx.inp` | 3.1 KB | Rietveld/structure | #define CREATE_ |

## user_y/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `user_y/user_y.inp` | 1.7 KB | (unclassified — open to inspect) | Fit a user defined peak shape to Quartz triplet #define CREATE_SIMULATED_ |
| `user_y/user_y_convolution.inp` | 2.4 KB | (unclassified — open to inspect) | #define CREATE_SIMULATED_ |

## voigt-approx/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `voigt-approx/create.inp` | 3.4 KB | (unclassified — open to inspect) |  |
| `voigt-approx/fit-more.inp` | 0.4 KB | (unclassified — open to inspect) |  |
| `voigt-approx/fit-obj.inp` | 1.7 KB | (unclassified — open to inspect) |  |
| `voigt-approx/fit-pv.inp` | 0.6 KB | (unclassified — open to inspect) |  |

## wppm/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `wppm/compare-1.inp` | 0.8 KB | (unclassified — open to inspect) |  |
| `wppm/cube-ln-normal-1.inp` | 3.6 KB | Pawley, Rietveld/structure | #define TEST_ |
| `wppm/gamma-fit-obj.inp` | 1.9 KB | (unclassified — open to inspect) |  |
| `wppm/gamma.inp` | 2.2 KB | Pawley, Rietveld/structure |  |
| `wppm/s-sphere-1.inp` | 1.2 KB | (unclassified — open to inspect) |  |
| `wppm/s-sphere-2.inp` | 3.1 KB | (unclassified — open to inspect) |  |
| `wppm/sphere-fit-obj.inp` | 1.3 KB | (unclassified — open to inspect) |  |
| `wppm/sphere-gamma-compare-1.inp` | 4.2 KB | (unclassified — open to inspect) | #define CREATE_ |
| `wppm/sphere-gamma-compare-2.inp` | 2.7 KB | (unclassified — open to inspect) | #define CREATE_ |
| `wppm/sphere-gamma-compare-3.inp` | 2.7 KB | (unclassified — open to inspect) | #define CREATE_ |
| `wppm/super-lorentzian.inp` | 0.8 KB | (unclassified — open to inspect) |  |

## xrd-ct/

| File | Size | Detected topics | Notes |
| --- | --- | --- | --- |
| `xrd-ct/xrd-ct-0.inp` | 1.3 KB | Rietveld/structure | Change case_ to 0, 1, or 2 |
| `xrd-ct/xrd-ct-1.inp` | 19.4 KB | Rietveld/structure | #define CREATE_ |

