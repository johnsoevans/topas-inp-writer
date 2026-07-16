# PDF refinement


```
[xdd]...
    [pdf_data]
    [scale_phase_X1 E]...
    [fit_obj1 E]...
    [start_X #] [finish_X #]
    [rebin_with_dx_of1 !E]
        [rebin_start_x_at !E]
    [weighting !E]
    [Tpdf_convolute]...
    [str]...
        [scale_phase_X1 E]...
        [scale E]
        [view_structure]
        [rigid]...
        [occ_merge $sites]...
        [pdf_scale_simple]
        [pdf_zero1 E]
        [pdf_ymin_on_ymax 0.001]
        [pdf_info]
        [Tpdf_convolute]...
        [pdf_for_pairs $sites_1 $sites_2]...
            [pdf_only_eq_0]
            [pdf_gauss_fwhm1 E]
            [Tpdf_convolute]...
        [pdf_partial_1 $sites]
        [pdf_partial_2 $sites]
        [pdf_partial_when !E1]

Tpdf_convolute
    [pdf_convolute1 E]...
        [min_X !E]
        [max_X !E]
        [convolute_X_recal !E]
```

Note the `1` suffix seen on several keywords above (`scale_phase_X1`, `fit_obj1`, `rebin_with_dx_of1`, `pdf_zero1`, `pdf_gauss_fwhm1`) is the manual's own footnote-style marker — see footnote (1) below: "Can be a function of the reserved parameter name X; X corresponds to r for PDF data." — not a literal part of the keyword name.

Examples — INP files (`test_examples\pdf\`): `beq-2.inp`, `beq-2-create.inp`, `beq-3.inp`, `beq-3-create.inp`, `pdf-1.inp`, `pdf-2.inp`; (`alvo4\`): `structure-solution-create.inp`, `structure-solution.inp`, `rigid.inp`; (`occ-merge-pbso4\`): `create.inp`, `occ-merge-test.inp`, `occ-merge.inp`. Data files (`test_examples\pdf\`): `beq-2.xy`, `beq-3.xy`, `alvo4\alvo4.xy`, `occ-merge-pbso4\pbso4.xy`.

G(r) = s1 S(r) / r – s2 r


| pdf_for_pairs "V* Al* !O2" * |
| --- |

The ‘!’ character excludes the O2 sequence from the wild card string, see section 20.26. Multiple pdf_for_pairs can be defined. pdf_only_eq_0 informs the parent pdf_for_pairs that only equivalent position 0 is to be considered. pdf_gauss_fwhm is used to write the width equation for the pairs selected by pdf_for_pairs. If all pairs are described by pdf_for_pairs then the associated beq’s are not used; the user is informed of unused beq’s. Consider the following abbreviated INP segment:


| site Al1 ... beq 1 site O1  ... beq 1 pdf_for_pairs Al1 Al1 pdf_only_eq_0 pdf_gauss_fwhm 0.1 ‘ Line A pdf_for_pairs Al1 O1  pdf_only_eq_0 pdf_gauss_fwhm 0.2 ‘ Line B pdf_for_pairs Al1 O1                pdf_gauss_fwhm 0.3 ‘ Line C |
| --- |

The FWHMs of the interactions are as follows:

Al1-O1  : Interactions for equivalent-position-0 described using Line B.

Al1-O1  : Interactions excluding equivalent-position-0 described using Line C.

O1-O1   : Interactions described using beq’s.

pdf_info displays the interactions in matrix form; for the above INP segment we have:


| pdf_info { - = No pdf_for_pairs defined hence beq’s used 0 = pdf_for_pairs defined with pdf_only_eq_0 1 = pdf_for_pairs defined without pdf_only_eq_0 2 = two pdf_for_pairs defined, one with and one without pdf_only_eq_0     Al1    -2    O1     2- } |
| --- |

The matrix is in purple. pdf_for_pairs together with beq defaults offer great flexibility in describing peak widths. See pdf-1.inp, pdf-2.inp, beq-3.inp. scale_phase_X can be used to describe Gaussian dampening, for example:


| prm damp_fwhm 50 min 1e-6 max 200 prm damp = Gauss(0, damp_fwhm); scale_phase_X = damp; |
| --- |


## Displaying partial PDFs

Partial PDFs can be dynamically displayed each iteration of refinement or at the end of refinement. A dummy structure mechanism is used as follows:


| str… ‘ main PDF phase 	dummy_str 		phase_name "Al1 Al2 O1 O2 O3" 		pdf_partial_1 "Al1 Al2 O1 O2 O3" 		pdf_partial_2 "Al1 Al2 O1 O2 O3" pdf_partial_when 0 ' Only at end of refinement 	dummy_str 		phase_name "V1 O4" 		pdf_partial_1 "V1 O4" 	pdf_partial_2 "V1 O4"						 pdf_partial_when = Mod(Cycle_Iter, 2); |
| --- |


## pdf_only_eq_0

Consider the space group P-1 with two equivalent positions, E0 and E1:

E0) 	x, y, z

E1) 	-x, -y, -z

The PDF comprises interactions between all atomic pairs; by symmetry, only interactions between E0 and the remaining atoms need be calculated. For a two-atom structure in P-1 with atoms A and B, the unique interactions are:

A0-A0, A0-A1, A0-B0, A0-B1, B0-B0, B0-B1, B0-A1

Each interaction can be defined separately using a combination of beq and pdf_for_pairs. If the following is defined:


| site A beq = a; site B beq = b; pdf_for_pairs A B                 pdf_gauss_fwhm = ab; pdf_for_pairs B B pdf_only_eq_0   pdf_gauss_fwhm = b0b0; |
| --- |

then the 7 types of interactions would have broadening as follows:


| Pair | Gauss FWHM |
| --- | --- |
| A0-A0 | Sqrt(a 2 Ln(2) / Pi^2) |
| A0-A1 | Sqrt(a 2 Ln(2) / Pi^2) |
| A0-B0 | ab |
| A0-B1 | ab |
| B0-B0 | b0b0 |
| B0-B1 | Sqrt(b 2 Ln(2) / Pi^2) |
| B0-A1 | ab |

For equivalent-position-0 and for distances within 10 Å then the following is required:


| pdf_for_pairs * * pdf_only_eq_0 pdf_gauss_fwhm = If(X < 10, something, 0); |
| --- |

pdf_info can be useful for specifying what is being used. Consider three sites A, B, C. For three sites there are (N^2+N)/2=6 types of atom-atom interactions:

A-A, A-B, A-C, B-B, B-C, C-C

Each of these can have broadening defined in three different ways, take A-A for example:


| site A ... beq  pdf_for_pairs A A  pdf_for_pairs A A pdf_only_eq_0 |
| --- |

Use of pdf_only_eq_0 results in three types of A-A interactions:

interaction where none are equivalent position zero.

interaction where both are equivalent position zero.

interaction where one is equivalent position zero and the other not.

If case (2) is used then (i), (ii) and (iii) all use case (2); for example:


| site A ... beq ... pdf_for_pairs A A ... |
| --- |

If case (3) is used, then beq is used for (i) and (iii) and case (3) is used for (ii); for example:


| site A ... beq ... pdf_for_pairs A A pdf_only_eq_0... |
| --- |

If both case (2) and (3) are used then beq is ignored and case (2) is used (i) and (iii), and case (3) for (ii); for example:


| site A ... beq ...  pdf_for_pairs A A...               ‘ (i) and (iii) pdf_for_pairs A A pdf_only_eq_0... ‘ (ii) |
| --- |


## Inter and Intra molecule FWHMs

pdf_for_pairs can be used to assign different interaction types between molecules. For example, to set bond lengths for atom Al1 of AlVO4 at equivalent position 0 only (see pdf-2.inp):


| prm intra_molec 0.01 min 1e-6 pdf_for_pairs Al1 "O1 O2 O3 O4 O5 O6" pdf_only_eq_0  pdf_gauss_fwhm = intra_molec; |
| --- |

The calculated pattern from pdf-2.inp therefore becomes:

Notice the 6 spikes; they correspond to the Al1 bonds with narrow FWHMs. If we wanted Al1 bonds that are not equivalent-position-0 to be different to the beq’s then we could use:


| prm inter_molec 0.1  min 1e-6 prm intra_molec 0.01 min 1e-6 pdf_for_pairs Al1 "O1 O2 O3 O4 O5 O6" pdf_only_eq_0  pdf_gauss_fwhm = intra_molec; pdf_for_pairs Al1 "O1 O2 O3 O4 O5 O6" pdf_gauss_fwhm = inter_molec; |
| --- |

This gives the following calculated pattern where we see the various Al1 bonds.

The corresponding output from pdf_info becomes:


| pdf_info { - = No pdf_for_pairs defined 0 = pdf_for_pairs defined with pdf_only_eq_0 1 = pdf_for_pairs defined without pdf_only_eq_0 2 = two pdf_for_pairs defined, one with pdf_only_eq_0 and one without pdf_only_eq_0     Al1    ------222222------    Al2    ------------------    Al3    ------------------    V1     ------------------    V2     ------------------    V3     ------------------    O1     2-----------------    O2     2-----------------    O3     2-----------------    O4     2-----------------    O5     2-----------------    O6     2-----------------    O7     ------------------    O8     ------------------    O9     ------------------    O10    ------------------    O11    ------------------    O12    ------------------ } |
| --- |

An exception is thrown if the same interaction is referenced in more than one pdf_for_pairs, for example, the following will throw an exception as Al1-O1 is referenced twice:


| pdf_for_pairs Al1 "O1 O2 O3 O4 O5 O6" pdf_only_eq_0 ... pdf_for_pairs Al1 O1 pdf_only_eq_0 ... |
| --- |

The following will not throw an exception:


| pdf_for_pairs Al1 "O1 O2 O3 O4 O5 O6" pdf_only_eq_0 ... pdf_for_pairs Al1 O1 ... |
| --- |


## Instrument Sinc function sinc-1.inp

In sinc-1.inp, pdf_convolute is used at the xdd level to convolute a Sinc function into phases:


| pdf_convolute = Sin(Qmax X+q3)/If(Abs(X) < 0.5 Step_Size, If(X < 0,-q2,q2),X);    min_X = -conv_max;    max_X =  conv_max; |
| --- |

sinc-1.inp also uses an xo_Is phase defined as:


| xo_Is    NoThDependence(0.0001)    xo 10 I @ 100    peak_type pv       pv_lor 0.5       pv_fwhm 2 |
| --- |

pdf_convolute operates on PDF-type phases only; the xo_Is phase is unaffected. Note the phase dependent use of an emission profile as defined in the NoThDependence macro. Multiple pdf_convolute’s can be described at the global, xdd, str and pdf_for_pairs levels. Using pdf_convolute as a dependent of pdf_for_pairs is slower than at other levels, so it should be placed outside pdf_for_pairs where possible.


## Q-resolution damping, Fourier-truncation ripples, and PDFfit2-style ADPs

Not documented in the TOPAS Technical Reference manual — sourced from Dinnebier, Leineweber & Evans (2018), Chapter 11 ("Total scattering methods"). These four items commonly appear together in a real PDF-refinement `xdd`/`str` block (e.g. the book's Ni-standard worked example) but are otherwise undocumented anywhere in this skill.

**`dQ_damping(name, value)`** — applied at the `xdd`/`pdf_data` level. Real total-scattering data has finite Q-space resolution, which causes G(r) peaks to damp out (decay in amplitude) at high r — a purely instrumental effect, not a physical property of the sample. `dQ_damping` applies a Gaussian damping envelope in r-space parametrized by the Q-resolution `dQ`, so this instrumental decay can be modeled and refined rather than mistaken for real structural disorder at high r.

**`convolute_Qmax_Sinc(name, Qmax)`** — applied at the `xdd`/`pdf_data` level, alongside `dQ_damping`. A real measurement only extends to some finite Qmax before it's truncated (rather than continuing to Q=∞ as the ideal Fourier transform assumes); this abrupt cutoff produces sinc-function "termination ripples" in the resulting G(r) (a Fourier-transform consequence of multiplying the ideal, infinite S(Q) by a box function of width Qmax). `convolute_Qmax_Sinc` convolutes this sinc ripple directly into the calculated G(r) using the actual data's Qmax, so the calculated pattern reproduces the same termination-ripple artifacts the real data has, instead of looking artificially smoother than the observed pattern. Typical lab-source Qmax values worth knowing as sanity checks: Cu-Kα1 ≈ 8 Å⁻¹, Mo-Kα1 ≈ 17 Å⁻¹, Ag-Kα1 ≈ 22 Å⁻¹ (the highest of the common lab sources), versus >50 Å⁻¹ achievable at synchrotron or neutron time-of-flight sources — real-space resolution in a PDF is limited by Qmax (roughly Δr ≈ π/Qmax), so a low-Qmax lab measurement will have visibly poorer real-space resolution than a synchrotron/neutron one, though pushing Qmax higher stops helping once it exceeds `π/Sqrt(<u²>)` (the mean-square atomic displacement) since thermal smearing dominates beyond that point.

**`beq_PDFfit2(uiso, uiso_v, rcut, rcut_v, sratio, sratio_v, delta1, delta1_v, delta2, delta2_v, qbroad, qbroad_v)`** — a site-level alternative to TOPAS's native `beq`/ADP machinery that instead maps directly onto the parametrization used by the widely-used external program PDFfit2, so a model or literature values from that program can be reproduced/compared directly. The named parameters map onto specific physical effects: `uiso` is the isotropic displacement parameter; `rcut` and `sratio` describe a "sharpening ratio" correction for correlated motion of nearby bonded atoms at short r (near-neighbor pairs move together, so their peak should be sharper than the uncorrelated-motion assumption would predict); `delta1`/`delta2` are correlated-motion correction terms (inverse-r and inverse-r² dependent, respectively) from the same PDFfit2 formalism; `qbroad` is an additional Q-dependent peak-broadening term. A concrete refined example from the book (Ni standard): `beq_PDFfit2(uiso, 0.00632, !rcut, 0.0, !sratio, 1.0, delta1, 0.82068, !delta2, 0.0, qbroad, 0.01422)`.

**`convolute_SoperLorch(name, value)`** — a companion correction needed specifically when a Lorch-type (or Soper-Lorch-type) smoothing function has been applied to F(Q) before the Fourier transform to G(r). Lorch-type smoothing functions are a standard technique (used in external PDF-generation programs) to reduce Fourier-truncation ripples by damping the F(Q) tail before transforming — this removes ripples but degrades real-space resolution, making closely-spaced pair distances harder to distinguish. If a Lorch/Soper-Lorch smoothing was used to *produce* the G(r) data being refined against, `convolute_SoperLorch` must be applied to the *calculated* pattern too, so the calculated and observed patterns are treated consistently (same resolution degradation on both sides) — omitting it would compare an over-sharp calculated pattern against an intentionally-softened observed one.

**A caveat worth knowing**: TOPAS's standard `weight_percent`/`MVW`-based weight-fraction reporting (documented in `references/11-quantitative-analysis.md`, built for ordinary Rietveld refinement) should **not** be relied on for multi-phase PDF fits — it isn't designed for the PDF case and can give misleading weight fractions there.


## Weighting of PDF and 2-Theta type data

PDF and 2 data can be of very different intensities; xdd_sum can be used to modifying the weighing of these data to give approximately similar weights to the patterns. For example:


| xdd file1.xy    xdd_sum !sum1 = Abs(Yobs);    weighting = 1 / sum1; xdd file2.xy    xdd_sum !sum2 = Abs(Yobs);    weighting = 1 / sum2;    pdf_data |
| --- |


## Test_examples\pdf\beq-2.inp

beq-2-create.inp generates a simulated pattern for beq-2.inp which:

comprises the structure of AlVO4,

3 types of beq parameters,

beq is a function of X (ie. X = r) and hence peak widths are a function of X,

demonstrates the use of pdf_zero,

demonstrates the use of rebin_with_dx_of and rebin_start_x_at.


## Test_examples\pdf\beq-3.inp

beq-3-create.inp generates a simulated pattern for beq-3.inp; it demonstrates the use of pdf_for_pairs.


## Speeding up refinement with rebin_with_dx_of

Increasing the x-axis step size of PDF data can speed up refinements (see beq-2.inp). Step sizes must be uniform, and the x-axis start must be an integral multiple of the step size. To increase the step size, rebin the data as follows:


| macro Rebin_Step	 { 0.015 } rebin_with_dx_of Rebin_Step rebin_start_x_at Rebin_Step |
| --- |

Rebinning is equivalent to collecting the data at a larger step size. All data is retained: total counts after rebinning equal total counts before rebinning, and the esd's associated with the data are rebinned accordingly. rebin_start_x_at can be used to align the start of the data with an integral multiple of the step size. In beq-2.inp, parameters such as scale are written in terms of the rebinned step size, reflecting the change in data scaling caused by rebinning.


## Refining on beq parameters

Modify the BB macro so that its empty as in the following:


| macro BB {  } ' Enter ! to not refine, beq including low angle fwhm sharpening |
| --- |

This results in refinement of four independent beq parameters including the low angle sharpening parameter of erf_a as seen in the following:


| macro Beq(c, v) { #m_argu c If_Prm_Eqn_Rpt(c, v, min 1e-6 max 10 val_on_continue = Rand(.1, 2); ) beq = CeV(c, v) Erf_Approx( erf_a X); } |
| --- |

The Rwp plot is:

This type of convergence is indicative of correct derivative calculation. Convergence for coordinates, occupancies, lattice parameters and pdf_zero are similar.


## Refining on ADPs in PDF refinement – Uij parameters


| site… occ Zr 1 u11 @ .01  u22 @ .01  u33 @ .01  u12 @ 0  u13 @ 0  u23 @ 0 adps_scale @ 1 |
| --- |

ADPs can now be used and refined in PDF refinement. The syntax is similar to reciprocal space refinement where the apds keyword, when used, generates the ADP parameters, for example, the following:


| site Zr1 x # y # z # occ Zr 1 apds |
| --- |

becomes:


| site Zr1 x # y # z # occ Zr 1 ADPs { u11 # u22 # u33 # u12 # u13 # u23 # } |
| --- |

This implementation is similar to PDFgui (Farrow et al., 2007), in which peaks are Gaussian even at low r. ADPs therefore correct for peak width but not asymmetry. Asymmetry does occur, however, and becomes noticeable when atomic displacement geometry is extreme.

adps_scale allows for the scaling of the Uij parameters and it can be a function of X where X corresponds to the distance between atoms.


| prm !delt1 0.75 min 1e-6 max 5 prm !delt2 0 min 1e-5 max 1   prm !Qb  0.05 min 1e-6 max 1 prm aa 1 min 1 _v = Rand(0.5, 1.5); adps_scale = 2 aa (Abs(1 - delt1 / X - delt2 / X^2 + (Qb^2) X^2)); |
| --- |

The FWHM of a PDF peak for atom i and j is given by:

FWHMij = Sqrt(adp_scalei Ucart,i + adp_scalej Ucart,j)

where Ucart is Uij in cartesian coordinates. _v is an alternative to val_on_continue.


## Multiatom approach to ADPs in PDF refinement


| macro ADP_5 and ADP_7  See file PDF-adps.inc | Examples test_examples\pdf-adps\ approx-1.inp Fit_to_gr.inp |
| --- | --- |

In many cases, anisotropic displacement parameters in PDF refinement can be described using 5 or 7 beq-type sites; we call these descriptions ADP_5 and ADP_7. ADP_5 comprises 7 parameters rather than the usual 6 Uij parameters. These ADP_5 parameters can be transformed into Uij parameters by fitting Uij parameters to a pattern generated from the ADP_5 parameters. The fit is reasonable given that the Uij model has only 6 parameters. Some main points when using ADP_5 in PDF refinement:

Number of ADP parameters become 7 instead of 6.

Broadening due to ADPs in G(r) is implied.

Asymmetry at low r is implied.

This approach works in Version 7 (albeit slower)

Asymmetry at low r is typically difficult to model, but the ADP_n approach captures it implicitly. Computational effort increases, as there are 7 atoms per ADP site; this is offset by the very fast calculation of PDF patterns using beq-type sites. The file PDF-adps.inc contains the macros needed to describe ADP_7. Approx-1.inp demonstrates the ADP_7 approach's ability to describe Uij models in reciprocal space. It has three modes of operation:

CREATE_USING_unns: creates a simulated single crystal pattern from normal unn parameters for one atom. neutron_data is to negate the effects of atomic scattering factors.

FIT_USING_ADPs_5: fits to the simulated pattern using the ADPs-7 approach. This refinement then saves the calculated ADPs-7 pattern created to a file called sim-2.hkl.

DETERMINE_unns_FROM_ADPs_5: fits normal unn parameters to sim-2.hkl.

ADP_5 sites are described in the ADP_5 macro, and it looks like:


| macro ADP_5_0(s, &x0, &y0, &z0, atom, &o, &x1, &y1, &z1, &x2, &y2, &z2, &bo) { site s x = x0;  y = y0;  z = z0;  occ atom = 0.2 o; beq = bo; local #m_unique ns = Get(num_posns); site s##_1p x = x0+x1; y = y0+y1; z = z0+z1; occ atom = 0.2 (ns / Get(num_posns)) o; beq = bo; site s##_2p x = x0+x2; y = y0+y2; z = z0+z2; occ atom = 0.2 (ns / Get(num_posns)) o; beq = bo; site s##_1m x = x0-x1; y = y0-y1; z = z0-z1; occ atom = 0.2 (ns / Get(num_posns)) o; beq = bo; site s##_2m x = x0-x2; y = y0-y2; z = z0-z2; occ atom = 0.2 (ns / Get(num_posns)) o; beq = bo; } |
| --- |

Two extreme cases have been performed; results for the first case - the refined and original Uij parameters are:

| ADPs {  0.39524 0.39690  0.40143 -0.18277 -0.19009 -0.19268	} ' refined    ADPs {  0.4     0.4      0.4     -0.19    -0.19	   -0.19 }   ' original |
| --- |

The refined values, from the DETERMINE_unns_FROM_ADPs_7 operation, show good agreement with the original values. The FIT_USING_ADPs_7 operation produces a fit that looks like:

A further extreme example is:


| ADPs {  0.39524 0.39690  0.40143 -0.18277 -0.19009 -0.19268	} ' refined    ADPs {  0.4     0.4      0.4     -0.19    -0.19	   -0.19 }   ' original |
| --- |

The FIT_USING_ADPs_5 operation produces a fit that looks like:


#### Multiatom approach to ADPs – fitting to G(r) patterns

This section generates a reciprocal space pattern using Uij parameters, then generates a G(r) pattern from the simulated data, and fits it using either ADP_5 or Uij parameters. A reciprocal space pattern is then simulated using the fitted ADP_5 parameters, and the loop is completed by fitting Uij parameters to that reciprocal space pattern. The final Uij parameters should match the original Uij parameters reasonably well. The control parameters are as follows:


| #prm generate_recip_space_pattern = 1; #prm generate_Gr_created_from_sine_transform = 0; #prm generate_Gr_calc_using_Uij = 0; #prm ADP_5_fit_to_Gr_calc_using_Uij = 0; #prm ADPs_fit_to_Gr_calc_using_Uij = 0; #prm ADP_5_fit_to_Gr_created_from_sine_transform = 0; #prm ADPs_fit_to_Gr_created_from_sine_transform = 0; #prm create_recip_ADP_5_fit_to_Gr_calc_using_Uij = 0; #prm create_recip_ADP_5_fit_to_Gr_created_from_sine_transform = 0; #prm Fit_create_recip_ADP_5_fit_to_Gr_calc_using_Uij = 0; #prm Fit_create_recip_ADP_5_fit_to_Gr_created_from_sine_transform = 0; macro Append_to_File_Name { 1 } ‘ anything here to identify output files created #prm include_resolution_broadening = 1; |
| --- |

These need to be executed one at a time, in sequence; they should be self-explanatory. The main point is that the sine transform pattern created using generate_Gr_created_from_sine_transform exhibits asymmetry, whereas the calculated G(r) created using generate_Gr_calc_using_Uij does not. The former can be considered the "true" G(r) pattern. Also important is that the pattern created using generate_Gr_created_from_sine_transform is generally better fit using ADP_5 (or ADP_7) than using Uij parameters (ADPs_fit_to_Gr_created_from_sine_transform). The reason is that the latter does not account for asymmetry.


## Structure Solution, Simulated Annealing

pdf\alvo4\structure-solution-create.inp creates a simulated pattern for structure-solution.inp. It’s a simulated annealing refinement with all coordinates starting at zero and with anti-bump penalties applied using:


| AI_Anti_Bump(O* , O* , 2.4, 1, 5) AI_Anti_Bump(Al*, O* , 1.6, 1, 5) AI_Anti_Bump(Al*, Al*, 2.8, 1, 5) |
| --- |

The correct solution is found as seen in the following:

The range of convergence for atomic coordinates is smaller than in reciprocal space, as in normal Rietveld refinement. This is because, in the PDF case, coordinates change peak positions rather than peak intensities, and the former has a narrower range of convergence. It may be possible to increase the range of convergence for the PDF case by increasing the peak widths; this, however, comes at the expense of resolution and may also result in an even smaller range of convergence.


## Rigid bodies with PDF data

pdf\alvo4\rigid.inp operates on simulated data created by structure-solution-create.inp. It demonstrates the use of rigid bodies with PDF data.


## Occupancy merging with PDF data

pdf\occ-merge-pbso4\occ-merge.inp operates on simulated data created by create.inp. It demonstrates the use of occ_merge with PDF data.


## Equivalence of pdf_gauss_fwhm and beq for one atom type

pdf\si1.inp comprises an option to use beq or pdf_gauss_fwhm. For the beq case we have:


| beq = width; |
| --- |

and for pdf_gauss_fwhm we have:


| pdf_gauss_fwhm = Sqrt(width 2 Ln(2) / Pi^2); |
| --- |

The above cases are equivalent when all atoms are of the same type.
