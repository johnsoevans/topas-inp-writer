# Peak Generation and "peak_type"

Convolution implies integration: a function that is analytically integrated is exact, whereas numerical integration is an approximation whose accuracy depends on the step size used. Accurate numerical convolution is used when analytical convolution is not possible, making it feasible to include complex functions in the generation of peak shapes. Laboratory instrument aberration functions mostly require numerical convolution. This convolution process, from a fundamental-parameters perspective (Cheary & Coelho, 1992; Cheary et al., 2004), is itself an approximation; second-order effects and higher are typically neglected. These approximations hold except in extreme cases unlikely to occur in practice, for example, axial divergence with Soller-slit acceptance angles greater than about 12 degrees.


## Source emission profiles

Generation of the emission profile is the first step in peak generation. It comprises EM lines, EMk, each a Voigt comprising the parameters la, lo, lh and lg. The reserved parameter name Lam is assigned the lo value of the EMk line with the largest la value, this EMk is referred to as EMREF and is used to calculate d-spacings. The interpretation of EM data is dependent on peak_type. For all peak types, the position 2k calculated for an emission line for a Bragg position of 2 is determined as:


|  | where |  |
| --- | --- | --- |

2 for xo_Is phases corresponds to the xo parameter. 2 for d_Is phases is given by the Bragg equation 2 = ArcSin(Lam/(2 d)) 360/Pi where d corresponds to the value of the d parameter. 2 values for str and hkl_Is phases are calculated from the lattice parameters. The FWHWk, in °2, for an EMk line is determined from the relations provided in Table 5-1. When no_th_dependence is defined then the calculation of 2k is determined from:

2k = 2 + EM(lo, i)

The macro No_Th_Dependence can be used when refining on non-X-ray data or fitting to negative 2 values (see example negx.inp). The x-axis extent (x1, x2) to which an EM line is calculated is determined by:

The default value for ymin_on_ymax is 0.001. Emission profile data have been taken from Hölzer et al. (1997) and are stored in *.LAM files in the LAM directory.


| Table 5-1. FWHWk in °2 for an EMk line for the different peak types. | Table 5-1. FWHWk in °2 for an EMk line for the different peak types. |
| --- | --- |
| FP peak type |  |
| PV peak type |  |
| SPVII peak type |  |
| SPV peak type |  |


## Peak generation and peak types

Phase peaks P are generated as follows:


| P = Get(scale) Get(all_scale_pks) EM(peak_type)  Convolutions | (5-1) |
| --- | --- |

where the emission profile (EM) is generated first, with emission profile lines of type peak_type; the symbol  denotes convolution. Peaks are then convoluted with any defined convolutions, multiplied by the scale parameter, multiplied by any defined scale_pks, and then multiplied by an intensity parameter. For xo_Is, d_Is and hkl_Is phases, the intensity is given by the I parameter. For str phases it corresponds to the square of the structure factor F2(hkl). Convolutions are normalized and do not change the area under a peak except for the capillary_diameter_mm and lpsd_th2_angular_range_degrees convolutions. The area under the emission profile is determined by the sum of the la parameters, which typically add up to 1. The definitions of the pseudo-Voigt and PearsonVII functions are provided in Table 5-2.


| Table 5-2. Unit area peak types. x corresponds to (22k) where 2k is the position of the kth reflection. fwhm corresponds to the Full Width at Half Maximum.  is the PV mixing parameter. The ‘1’ and ‘2’ subscripts correspond to the left and right of the split functions. | Table 5-2. Unit area peak types. x corresponds to (22k) where 2k is the position of the kth reflection. fwhm corresponds to the Full Width at Half Maximum.  is the PV mixing parameter. The ‘1’ and ‘2’ subscripts correspond to the left and right of the split functions. |
| --- | --- |
| Gaussian |  |
| Lorentzian |  |
| PseudoVoigt |  |
| Split PearsonVII  SPVII | ) ) |
| Split PseudoVoigt  SPV | ) ) |

Lorentzian and Gaussian convolutions using lor_fwhm and gauss_fwhm equations are analytically convoluted with the FP and PV peak types and numerically convoluted with the SPVII and SPV peak types. These numerical convolutions are highly accurate, as they comprise analytical Lorentzian and Gaussian functions convolved with straight line segments. For FP and PV peak types, the first defined hat convolution is convoluted analytically; additional hat convolutions, for all peak types, are convolved numerically. For classic analytical full-pattern fitting, the macros PV_Peak_Type, PVII_Peak_Type, TCHZ_Peak_Type can be used. These macros use the following relationships to describe profile width as a function of 2.


| PV_Peak_Type fwhm = ha + hb tan() + hc/cos()  = lora + lorb tan()+ lorc/cos() where ha, hb, hc, lora, lorb, lorc are refineable parameters. | PV_Peak_Type fwhm = ha + hb tan() + hc/cos()  = lora + lorb tan()+ lorc/cos() where ha, hb, hc, lora, lorb, lorc are refineable parameters. | PVII_Peak_Type fwhm1 = fwhm2 = ha + hb tan() + hc/cos() m1 = m2 = 0.6 + ma + mb tan() + mc/cos() where ha, hb, hc, ma, mb, mc are refineable parameters. |
| --- | --- | --- |
| TCHZ_Peak_Type: The modified Thompson-Cox-Hastings pseudo-Voigt "TCHZ" is defined as (e.g. Young, 1993, see example alvo4_tch.inp):  = 1.36603 q - 0.47719 q2 + 0.1116 q3 | TCHZ_Peak_Type: The modified Thompson-Cox-Hastings pseudo-Voigt "TCHZ" is defined as (e.g. Young, 1993, see example alvo4_tch.inp):  = 1.36603 q - 0.47719 q2 + 0.1116 q3 | TCHZ_Peak_Type: The modified Thompson-Cox-Hastings pseudo-Voigt "TCHZ" is defined as (e.g. Young, 1993, see example alvo4_tch.inp):  = 1.36603 q - 0.47719 q2 + 0.1116 q3 |
| where | q = L /   = (G5 + AG4L + BG3L2 + CG2L3 + DGL4 + L5)0.2 = fwhm A = 2.69269, B = 2.42843, C = 4.47163, D = 0.07842 G = (U tan2 + V tan + W + Z / cos2)0.5  L = X tan +Y / cos with U, V, W, X, Y, Z as refined parameters. | q = L /   = (G5 + AG4L + BG3L2 + CG2L3 + DGL4 + L5)0.2 = fwhm A = 2.69269, B = 2.42843, C = 4.47163, D = 0.07842 G = (U tan2 + V tan + W + Z / cos2)0.5  L = X tan +Y / cos with U, V, W, X, Y, Z as refined parameters. |


## Convolution and the peak generation stack

The emission profile of a peak, P0, of a certain peak type (i.e. FP, PV etc…) is first calculated and placed onto a ‘Peak calculation stack’. P0 analytically includes the lor_fwhm and gauss_fwhm convolutions for FP and PV peak types, and additionally one hat convolution, if defined; the hat convolution is included analytically only if its corresponding num_hats has a value of 1 and if it does not take part in stack operations. Further defined convolutions are convolved with the top member of the stack. The last convolution should leave the stack with a single entry representing the final peak shape. The following keywords allow for manipulation of the Peak calculation stack:

[push_peak]...

[bring_2nd_peak_to_top]...

[bring_n_peak_to_top !E]...

[add_pop_1st_2nd_peak]...

[scale_top_peak E]...

[set_top_peak_area E]...

push_peak duplicates the top of the stack; bring_2nd_peak_to_top brings the second entry to the top of the stack, bring_n_peak_to_top brings the nth peak to the top (n=0 corresponds to the top of the stack) and add_pop_1st_2nd_peak adds the top entry to the second most recent entry and then pops the stack. scale_top_peak scales the peak at the top of the stack. As an example, consider the generation of back-to-back exponentials as required by GSAS time of flight peak shape 3:


| push_peak    prm a0  481.71904 del = 0.05 Val + 2;    prm a1 -241.87060 del = 0.05 Val + 2;    exp_conv_const = a0 + a1 / D_spacing; bring_2nd_peak_to_top    prm b0 -3.62905 del = 0.05 Val + 2;    prm b1  6.44536 del = 0.05 Val + 2;    exp_conv_const = b0 + b1 / D_spacing^4; add_pop_1st_2nd_peak |
| --- |

The first statement push_peak pushes P0 onto the stack leaving two peaks on the stack:

Stack = P0, P0

The top member is then convoluted by the first exp_conv_const convolution, or,

Stack = P0, P0  exp_conv_const

where  denotes convolution. bring_2nd_peak_to_top results in the following:

Stack = P0  exp_conv_const, P0

and the next convolution results in:

Stack = P0  exp_conv_const, P0   exp_conv_const

Thus, the stack contains two peaks convoluted with exponentials. The last statement add_pop_1st_2nd_peak produces:

Stack = P0  exp_conv_const + P0   exp_conv_const

Convolutions applied to peaks are normalized after convolution. Thus, the following, from WIF David’s macro wifd_mic_moderator, will give unintended peak shapes:


| push_peak                          ‘ first peak scale_top_peak = 1 - storage  bring_2nd_peak_to_top              ‘ second peak exp_conv_const = -Ln(0.001) / (taus_0 + taus_1 / lam^2);  scale_top_peak = storage;    add_pop_1st_2nd_peak |
| --- |

where the ratio of the areas of the first peak to the second peak won’t be (1-storage)/storage. This can be remedied by normalizing the exp_conv_const aberration as follows:


| push_peak  scale_top_peak = 1 - storage;  bring_2nd_peak_to_top  exp_conv_const = -Ln(0.001) / (taus_0 + taus_1 / lam^2);  scale_top_peak = storage Yobs_dx_at(Xo);    add_pop_1st_2nd_peak |
| --- |

However, not all aberrations are easily normalized; set_top_peak_area overcomes this problem by normalizing the area itself in situ. The INP segment can now be written as:


| push_peak set_top_peak_area = 1 - storage;  bring_2nd_peak_to_top  exp_conv_const = -Ln(0.001) / (taus_0 + taus_1 / lam^2);  set_top_peak_area = storage;    add_pop_1st_2nd_peak |
| --- |


## Speed / Accuracy and peak_buffer_step

For computational efficiency, phase peaks are calculated at predefined 2 intervals in a “peaks buffer”; peaks in between are determined by stretching and interpolating. Use of the peaks buffer dramatically reduces the number of peaks that need to be calculated. Typically, no more than 50 to 100 peaks are necessary to accurately describe peaks across a whole diffraction pattern. The following keywords affect the accuracy of phase peaks:

```
[str | hkl_Is | xo_Is | d_Is]...
    [peak_buffer_step !E]
```

[convolution_step #1]

[ymin_on_ymax #]

[aberration_range_change_allowed !E]

Default values for these are typically adequate. peak_buffer_step determines the maximum x-axis spacing between peaks in the peaks buffer, it has a default value of 500*Peak_Calculation_Step. A value of zero will force the calculation of a new peak in the peaks buffer for each peak of the phase. Note that peaks are not calculated for x-axis regions that are void of phase peaks. convolution_step defines an integer corresponding to the number of calculated data points per measurement data point used to calculate the peaks in the peaks buffer, see x_calculation_step. Increasing the value for convolution_step improves accuracy for data with large step sizes or for peaks that have less than 7 data points across the FWHM. ymin_on_ymax determines the x-axis extents of a peak (see also section 5.1). aberration_range_change_allowed describes the maximum allowed change in the x-axis extent of a convolution aberration before a new peak is calculated for the peaks buffer. For example, in the case of axial_conv the spacing between peaks in the peaks buffer should be small at low angles and large at high angles. aberration_range_change_allowed is a dependent of the peak type parameters and convolutions as shown in . Small values for aberration_range_change_allowed reduces the spacing between peaks in the peaks buffer and subsequently increase the number of peaks in the peaks buffer.


| Table 5-3. Default values for aberration_range_change_allowed. | Table 5-3. Default values for aberration_range_change_allowed. |
| --- | --- |
| Parameter | Default aberration_range_change_allowed |
| m1, m2 | 0.05 |
| pv_lor, spv_l1, spv_l2 | 0.01 |
| h1, h2, pv_fwhm, spv_h1, spv_h2 | Peak_Calculation_Step |
| hat, axial_conv, whole_hat, half_hat | Peak_Calculation_Step |
| one_on_x_conv, exp_conv_const, circles_conv | Peak_Calculation_Step |
| lor_fwhm, gauss_fwhm | Peak_Calculation_Step |


## The peaks buffer, speed and memory considerations

Anisotropic peak shapes result in the peaks-buffer holding as many peaks as there are hkls. For problems with 100,000s of peaks the calculation time and storage of the peaks-buffer can be prohibitive. This situation can be mitigated using the phase dependent peak_buffer_based_on:

[str | hkl_Is | xo_Is | d_Is]

[peak_buffer_based_on !E [peak_buffer_based_on_tol !E] ]...

When peak_buffer_based_on is defined, the usual means of determining the size of the peak buffer is over-ruled. Instead, peaks are grouped according to the peak_buffer_based_on criterion. For example, to insert a peak into the peak buffer at x-axis intervals of 1 then the following can be used:


| peak_buffer_based_on = Xo; peak_buffer_based_on_tol 1 |
| --- |

Thus, peaks with similar Xo’s, as defined by peak_buffer_based_on_tol, are grouped. Occasionally peaks that are a function of hkls have groups of hkls that are of the same peak shape and at a similar x-axis position. The following demonstrates how to group these peaks such that a single peak shape is calculated.


| peak_buffer_based_on = Xo; peak_buffer_based_on_tol 0.01 peak_buffer_based_on = sh; peak_buffer_based_on_tol 1e-7 |
| --- |

where sh can be a spherical harmonics parameter or an equation describing hkl dependence or a march_dollase parameter. When more than one peak_buffer_based_on is defined then peak groups obey all of the peak_buffer_based_on‘s. peak_buffer_based_on disables the peak stretching procedures and any defined aberration_range_change_allowed. peak_buffer_based_on can be a function of the reserved parameters H, K, L, M, D_spacing, X, Xo, Th.

Depending on the problem, smaller values such as 1e-7 can significantly reduce the number of peaks stored in the peaks buffer (a factor of 15 at times) without significantly affecting Rwp. A negative value for peak_buffer_based_on_tol will force a calculation for each peak resulting in independent hkl peak shapes, for example:


| peak_buffer_based_on 1 peak_buffer_based_on_tol -1 |
| --- |


## An Accurate Voigt

[more_accurate_Voigt] can be used to override the default Pseudo-Voigt approximation to the Voigt. It decreases the error (Voigt_approx – Voigt_true) by a factor of ~100. Defining G as the FWHM of a Gaussian and L as the FWHM of a Lorentzian; the screen shots below show fits to a range of G convoluted with L, resulting in Voigts, with L varying from 0.01 to 0.09 and G+L=1. Fitting to the Voigts using pseudo-Voigts we get

Fitting to the Voigts using the accurate calibration results in the small difference plots seen in the following:

The more_accurate_Voigt calibration is accurate and fast. It fits to each true Voigt the following:


| fit_obj = a1 (2 Sqrt(Ln(2) / Pi) / f1) Exp(-4 Ln(2)(X / f1)^2); fit_obj = a2 (2 Sqrt(Ln(2) / Pi) / f2) Exp(-4 Ln(2)(X / f2)^2); fit_obj = a3 (2 / (Pi f3)) / (1 + 4 (X / f3)^2); fit_obj = a4 (4 / (Pi f4)) / (1 + 4 (X / f4)^2)^2; |
| --- |

One thousand sets of a0, a1, a2, a3, f0, f1, f2, f3 parameters were determined by fitting to 1000 true Voigts with L varying from 0 to 1 in steps of 0.001.

TOPAS uses an FFT to perform the double summation of the convolution. However, for lor > 500, the convolution itself comprises an analytical Lorentzian with a Gaussian comprising straight line segments. For lor < 500 then an analytical Gaussian is convoluted with a Lorentzian comprising straight line segments.

The file fit-pv.inp fits a pseudo-Voigt to the generated true Voigt.

The file fit-more.inp fits to the generated true Voigt using equivalent fit_obj’s.

The file fit-obj.inp fits fit_obj's to the generated true Voigt.

The difference plot from fit-pv.inp is in the order of 500 to 1000 times larger than the difference plot from fit-more.inp.


## CS_L / CS_G: FWHM is proportional to 1/value, so sensitivity fades above ~500

Confirmed directly by the user (TOPAS-Academic's author). Both crystallite-size macros compute their FWHM contribution as an inverse function of the size value `v` (confirmed directly in `topas.inc`):

```
CS_L(c, v) { ... lor_fwhm   = 0.1 Rad Lam / (Cos(Th) CeV(c,v)); }
CS_G(c, v) { ... gauss_fwhm = 0.1 Rad Lam / (Cos(Th) CeV(c,v)); }
```

Because `FWHM ∝ 1/v`, the derivative `d(FWHM)/dv ∝ -1/v²` shrinks rapidly as `v` grows -- past roughly **500 (nm)**, further increases in `csl`/`csg` change the calculated peak shape only slightly, so the refinement has little leverage to pin the value down precisely. This is not just a theoretical concern: a real refined example (`test_examples/simple.inp`) showed `csg` refining to `2166.5 ± 765.7` (a ~35% relative error) while flagged `_LIMIT_MIN_0.3`, strongly anti-correlated with `csl` (`C_matrix_normalized` showed -65% correlation) -- the classic symptom of a parameter the data can no longer usefully constrain once it's pushed well past the ~500 threshold. When summarizing or reviewing an INP file, flag any `CS_L`/`CS_G` value (or `csl`/`csg`-named `prm`) larger than roughly 500 as poorly-determined/low-sensitivity, and check the `C_matrix_normalized` block (if present) for a large anti-correlation between `csl` and `csg` as corroborating evidence -- this is often a sign the model doesn't actually need both a Lorentzian and Gaussian size-broadening term simultaneously.

## Stretching peaks


```
[str]...
    [stretch_pks E]
```

Examples: `stretch-pks\stretch-1.inp`


| CS_G(@, 100) CS_L(@, 100) |
| --- |

When the values of the lor_fwhm and gauss_fwhm parameters are approximately known, then the shapes of the peaks can be approximated by stretching. For symmetric peaks the approximation is almost exact; asymmetric peaks, peaks with asymmetric convolutions, are not exact but if the values aren’t too far off optimal values then the approximation can be good. The benefit of such an approximation is speed, where, using stretch_pks in the stretch-1.inp example speeds up refinement by a factor of 4.1. The usage of stretch_pks is as follows:


| CS_L(100) ‘ not refined CS_G(100) ‘ not refined stretch_pks @ 1 min 0.001 max 10 |
| --- |

The limits of a stretched peak, x1_s and x2_s, in terms of the unstretched limits x1 and x2, and the peak position Xo are:

x1_s = x0 – (Xo – x1) Get(stretch_pks)

x2_s = x0 + (x2 – Xo) Get(stretch_pks)


## transform_x without recalculating patterns


```
[str | hkl_Is | xo_Is | d_Is]...
    [transform_X E]
```

Examples: `transform_X\tpx.inp`

The transform_x keyword stretches a calculated phase pattern to form a final phase calculated pattern without recalculating peaks or summing peaks to Ycalc. The following:


| prm tpx 0 transform_x = X + tpx Sin(X Pi / 360); |
| --- |

is an approximation to:


| prm tpx 0 th2_ffset = tpx Sin(X Pi/ 360); |
| --- |

This approximation is accurate when the change in transform_X is smooth and when its largest value is in the order of what is expected from XRD-CT data. For two common strs residing in different xdds, then if th2_offset were to be used then two th2_offsets would need to be defined and the formation of the summation of the peaks to the calculated pattern performed twice. transform_X on the other hand allows for the reuse of a common calculated str pattern. A further description is given in section 6.
