# Miscellanous


## Outputting special characters

The characters ,(){}[] can be outputted to text files by enclosing them in double quotation marks. For example:


| out aac.txt Out_String("a,b}c(d") |
| --- |

To output a single apostrophe or double quote character, the escape sequences of %A and %B can be used respectively, for example, the following:


| do_errors prm b -0.61427_0.01048 out aac.txt out_record out_fmt "%V g[h%Bh" out_eqn = b; out_record out_fmt "\n%s%A (brack}et" out_eqn = "abc"; |
| --- |

produces in the aac.txt file:


| -0.614(10) g[h"h abc' (brack}et |
| --- |

The escape sequences themselves can be outputted by using two separate out_records. For example, to output %A use:


| Out_String(“%”) Out_String(“A”) |
| --- |


## Iterating over internal data-tree nodes using ‘for’

‘for’ can be used to iterate over all nodes of the internal data tree. For example, to iterate over the site_recs node the following can be used:


| for site_recs { beq @ 1 } |
| --- |


## Command prompt output during INP file loading using print

The keyword print is executed during the loading of INP files; it is useful for determining when an item is loaded for debugging purposes. For example:


| print(“Executed during the loading of INP files”) #prm a = 1.234; print(#out a) |
| --- |


## Sorting output by columns using _sort_dec or _sort_inc

Columns can be sorted in ascending or descending order using _sort_inc or _sort_dec respectively. For example, the following can be used to sort by d-spacing in descending order and then by I_no_scale_pks in ascending order:


| xdd...       str...          phase_out aac.txt             out_record                 out_fmt "  d = %9.5f"                 out_eqn = D_spacing; _sort_dec 1             out_record                 out_fmt "  I_no_scale_pks = %9.5f"                 out_eqn = I_no_scale_pks; _sort_inc 2             out_record                     out_fmt "  2Th = %9.5f\n"                 out_eqn = 2 Rad Th; |
| --- |


## Creating many xdds at once using new and xdd_file

The new keyword can be used to create many xdds at once, for example:


| macro Create_XDDs(n)  { move_to xdds move_to xdd_recs new(xdd, n) } |
| --- |

See section Error! Reference source not found. for usage of the macro Create_XDDs.


## seed, #seed_eqn, seed-tc.txt, seed-tb.txt, Rand

#seed_eqn seeds the random number generator at the preprocessor stage with the equation value; here are examples:


| #seed_eqn seed_1 = Rand(0,32767); prm value_fed_to_random_number_generator = #out seed_1; #seed_eqn seed_2 = Run_Number; |
| --- |

inline double Rand(double r1, double r2)

{

const double c0 = 1.0 / double(RAND_MAX);

const double c1 = 1.0 / (1.0 + double(RAND_MAX));

return (rand() + rand() * c0) * c1 * (r2 – r1) + r1;

}


## Threading

TOPAS is threaded, allowing the utilization of multiple processors and resulting in faster program execution. The degree of speedup is computer- and problem-dependent; for non-trivial problems, the gain is 2 to 4x on a 4-core i7 laptop PC. Attention is paid to reducing memory usage at the thread level, which is particularly apparent when using rigid bodies or occupancy merge. Except for a few penalties, all items are threaded, including: peak generation, all convolutions, all derivatives that are a function of Ycalc, equations that are a function of changing variables such as X, Th, D_spacing, etc., Pawley refinement, structure refinement, charge flipping, magnetic refinement, stacking faults, PDF refinement, the conjugate gradient solution method, and indexing.


### Setting the maximum number of threads

The program defaults to using the maximum number of threads available. The user can limit this behaviour by editing the file MaxNumThreads.txt. This file is read at program start-up and contains a single number — call it Max_Threads_File — that defines the maximum number of threads. Non-existence of the file, or a Max_Threads_File of zero, results in the program using the maximum number of threads available. If Max_Threads_File is negative, the maximum number of threads is set to the following:

Max_Number_Threads = Max(1, Max_Threads_File + Max_Threads_Available);


## Restraining background using the Bkg_at function

The Chebyshev background function, bkg, can sometimes misbehave during Pawley, Le Bail or deconvolution refinements. In the case of xdd deconvolution refinements, the Deconvolution_Bkg_Penalty macro stabilizes bkg in most cases. In cases of instability, however, the Bkg_at(x) function can be used in penalty functions to guide the shape of bkg. Bkg_at(x) returns the value of bkg at the x-axis position of x. Here’s an example use of Bkg_at as applied to TOF data:


| bkg  @  0.443519294`  0.0200324829`  0.0113774736` penalty = 1000000 (Bkg_at(2036)  - 0.43)^2; penalty = 1000000 (Bkg_at(9000)  - 0.50)^2; penalty = 1000000 (Bkg_at(14600) - 0.50)^2; |
| --- |

The first penalty restrains the value of bkg at x=2036 to 0.43. Typically, only two to three Bkg_at penalties are necessary. The values of 0.43, 0.5 and 0.5 can be determined graphically.


## Calculation of structure factors

The structure factor F for a site s with adps is the complex quantity:


| where  s corresponds to site s e corresponds to the equivalent position of site s a corresponds to atom a  corresponds to occupancy corresponds to the anisotropic temperature factor | (20-1) |
| --- | --- |

For a site with beq, F for a fixed  becomes:


| Let , | (20-2) |
| --- | --- |

Separating the real and imaginary parts we get:

Approximation  with the Bragg angle and dropping subscripts and defining:


| fo,s = a fo,a Oa,   fs' = a fa' Oa,   fs" = a fa" Oa | (20-3) |
| --- | --- |

we have:


| F = s (As + i Bs) (fo,s + fs'+ i fs") F = s (As (fo,s +fs')  Bs fs") + i s (As fs" + Bs (fo,s + fs')) or,  F = A + i B | (20-4) |
| --- | --- |

The intensity is proportional to the complex conjugate of the structure factor, or,


| F2 = A2 + B2 | (20-5a) |
| --- | --- |

or,


| F2 = A012 + B012 + A112 + B112 + 2 B01 A11 - 2 A01 B11 | (20-5b) |
| --- | --- |
| where A01= s As (fo,s + fs'),   A11 = s As fs" B01= s Bs (fo,s + fs'),   B11 = s Bs fs" and A = A01  B11,   B = B01 + A11 |  |

Atomic scattering factors, fo,a, comprise 11 values per atom and are found in the file ATMSCAT_11.TXT. Correspondingly 9 values per atom, obtained from the International Tables, are found in the file ATMSCAT_9.TXT. Use of either 9 or 11 values can be invoked by running the batch files use_9f0 and use_11f0 respectively. Dispersion coefficients, fa' and fa", are by default from http://www.cxro.lbl.gov/optical_constants/asf.html.


### Friedel pairs

For centrosymmetric structures, the intensities for a Friedel reflection pair are equivalent, or F2(h k l) = F2(-h-k-l). This holds true regardless of the presence of anomalous scattering and regardless of the atomic species present in the unit cell. This equivalence in F2 is due to B01 = B11 = 0 and thus:


| F = A01 + i A11   and   F2 = A012 + A112 | (20-6) |
| --- | --- |

For non-centrosymmetric structures and for the case of no anomalous scattering, or for the case where the unit cell comprises a single atomic species, then F2(h k l) = F2(-h-k-l). Or, for a single atomic species we have:


| B01 A11 = (f0 +f') (S BS) f" (S AS),   A01 B11 = (f0 +f') (S AS) f" (S BS) or B01 A11 = A01 B11 | (20-7) |
| --- | --- |

and thus, from cancellation in Eq. (20-5b) we get:


| F2(h) = F2(-h) = A012 + B012 + A112 + B112 | (20-8) |
| --- | --- |

For non-centrosymmetric structures and for the case of anomalous scattering and for a structure comprising more than one atomic species then F2(h)  F2(-h).


### Powder data

Friedel pairs are merged for powder diffraction data meaning that the multiplicities as determined by the hkl generator includes the reflections (h k l) and (-h -k -l); this improves computational efficiency. Eq. (20-5b) gives the correct intensity for unmerged Friedel pairs and thus it cannot be used for merged Friedel pairs. Using the fact that:


| A01(h) = A01(-h),	  A11(h) = A11(-h) B01(h) = B01(-h),       B11(h) = B11(-h) | (20-9) |
| --- | --- |

then F2 from Eq. (20-5b) in terms of B01(h) and B11(h) evaluates to:


| F2(h)  = Q1 + Q2 F2(-h)  = Q1 – Q2 where Q1 = A012 + B012 + A112 + B112 and Q2 = 2 (B01 A11 –  A01 B11) | (20-10) |
| --- | --- |

and for merged Friedel pairs we get:


| F2(h) + F2(-h) = 2 Q1 | (20-11) |
| --- | --- |


| F2(h)merged = Q1 | (20-12) |
| --- | --- |

The reserved parameter names of A01, A11, B01 and B11 can be used to obtain unmerged real, imaginary and F2 components and the merged F2. The following macros have been provided in Topas.inc:


| macro F_Real_positive { (A01-B11) } macro F_Real_negative { (A01+B11) } macro F_Imaginary_positive { (A11+B01) } macro F_Imaginary_negative { (A11-B01) } macro F2_positive { (F_Real_positive^2 + F_Imaginary_positive^2) } macro F2_negative { (F_Real_negative ^2 + F_Imaginary_negative^2) } macro F2_Merged { (A01^2 + B01^2 + A11^2 + B11^2) } |
| --- |

Note that F2_Merged = (F2_positive + F2_negative) / 2. The reserved parameters I_no_scale_pks and I_after_scale_pks for str phases are equivalent to the following:

I_no_scale_pks = Get(scale) M F2_Merged

I_after_scale_pks = Get(all_scale_pks) Get(scale) M F2_Merged

In addition, the macros Out_F2_Details and Out_A01_A11_B01_B11 can be used to output F2 details.


### Single crystal data

SHELX HKL4 single crystal data comprise unmerged equivalent reflections and thus Eq. (20-5b) is used for calculating F2. Equivalent reflections are merged by default and can be unmerged using dont_merge_equivalent_reflections. For centrosymmetric structures, merging includes the merging of Friedel pairs and thus Eq. (20-12) is used for calculating F2. For non-centrosymmetric structures, merging excludes the merging of Friedel pairs and thus (20-5b) is used for calculating F2. dont_merge_Friedel_pairs prevent merging of Friedel pairs. ignore_differences_in_Friedel_pairs forces the use of Eq. (20-12) for calculating F2. The reserved parameter name Mobs returns the number of observed reflections belonging to a family of reflections.

Merging of equivalent reflections reduces computational effort and is useful in the initial stages of structure refinement. Only a single intensity is calculated for a set of equivalent reflections even in the absence of merging. Thus, equivalent reflections and Friedel pairs are remembered, and intensities appropriated as required.

*.SCR data is typically generated from a powder pattern and comprises merged equivalent reflections including merged Friedel pairs. Consequently, Eq. (20-12) is used for calculating F2; definitions of dont_merge_equivalent_reflections, dont_merge_Friedel_pairs and ignore_differences_in_Friedel_pairs are ignored.


### The Flack parameter

[Flack E]

For single crystal data and for non-centrosymmetric structures the Flack parameter (Flack, 1983) scales F2(h) and F2(-h) as follows (see the test example ylidma.inp):


| F2(h)  = Q1 + (1 – 2 Flack) Q2 F2(-h)  = Q1 – (1 – 2 Flack) Q2 | (20-13) |
| --- | --- |


### Single Crystal Output

The macro Out_Single_Crystal_Details, see Topas.inc, outputs details for single crystal refinement, see test example ylidma.inp. Mobs corresponds to the number of observed reflections belonging to a family of planes. When Friedel Pairs are not merged then Mobs for h and –h will be different. Phase symmetry is considered in the values for A01, B01, A11 and B11.


### 2θ point by point calculation of f0 and beq

Structure factors for powder diffraction data typically write beq and the atomic scattering factor fo as a function of the Bragg angle 2θo. A more accurate description can be realized using the str dependent point_by_point_beq_fo_etc, which writes the structure factor in terms of 2θ. This calculates fo and beq on a 2θ point-by-point basis rather than 2θo. In routine Rietveld refinement the difference in structure factor values is small and difficult to detect. It can, however, be useful for analysing nanoparticles when extreme accuracy is required. The keyword only works with X-ray powder data and results in a slight increase in computational effort of ~5%. Reported structure factor values using the reserved parameter names of A01, B01, A11 and B11 are still written in terms of the Bragg angle 2θo and are therefore unchanged.


## Convolution


### Instrument and sample convolutions

Diffractometer instrument and sample aberration functions used in peak profile synthesis are generated from generic convolutions. For example, the ‘simple’ axial divergence model is described using the generic convolution circles_conv as defined in the Simple_Axial_Model macro. Table 20-1 lists instrument convolutions. In addition, the full axial divergence model of Cheary & Coelho (1998a, 1998b) is supported.


| Table 20-1. Instrument and sample aberration functions in terms of , where 2 is the measured angle and 2k the Bragg angle. RP and RS correspond to the primary and secondary radius of the diffractometer respectively. | Table 20-1. Instrument and sample aberration functions in terms of , where 2 is the measured angle and 2k the Bragg angle. RP and RS correspond to the primary and secondary radius of the diffractometer respectively. | Table 20-1. Instrument and sample aberration functions in terms of , where 2 is the measured angle and 2k the Bragg angle. RP and RS correspond to the primary and secondary radius of the diffractometer respectively. |
| --- | --- | --- |
| Aberrations | Name | Aberration function Fn() |
| Instrument | Instrument | Instrument |
| Equatorial divergence (fixed divergence slits) | EDFA  [] |  |
| Equatorial divergence (variable divergence slits) | EDFL (mm) |  |
| Size of source in the equatorial plane | TA  (mm) | where |
| Specimen tilt; thickness of sample surface as projected onto the equatorial plane | ST  (mm) | Where |
| Receiving slit length in the axial plane | SL  (mm) |  |
| Width of the receiving slit in the equatorial plane | SW  (mm) | where |
| Sample | Sample | Sample |
| Linear absorption coefficient | AB  (cm-1) |  |


### Convolutions in general

TOPAS performs convolution in various ways and the terms “FFT convolution” (Fast Fourier Transform) or “direct convolution” are simplifications. Typically, convolutions are broken down into double summations that can be calculated either directly or by using an FFT. The program uses the method that is fastest as determined by calculating the number of operations required by each.

Response functions that are known to the program are treated analytically. Response functions that are unknown to the program (such as user defined convolutions) are treated as straight-line segments. Convolution therefore can be i) between two sets of line segments ii) one set of line segments and an analytical expression, or iii) simply done analytically. When straight-line segments are used, for a response function with Nr data points and a peak comprising Np points, the extra cost of the piece wise integration is approximately 3 (Nr+Np) operations. This is a small number of operations, and it produces a high degree of accuracy. Apart from lor_fwhm and gauss_fwhm, the convolutions described below have discontinuities in 2Th space; associated Fourier transforms are therefore difficult to describe, and hence convolution is performed in 2Th space. Response functions that are treated as line segments are:

user_defined_convolution, capillary_diameter_mm, lpsd_th2_angular_range_degrees

Response functions that are analytically convoluted with line segments are:

exp_conv_const, hat, stacked_hats_conv

Response functions that comprise a mixture of analytical and straight-line segments are:

axial_conv, one_on_x_conv, circles_conv

lor_fwhm and gauss_fwhm convolutions are convoluted analytically with the emission profile to form the base profile. Convolutions are calculated with an x-axis step size of:

Peak_Calculation_Step = x_calculation_step / convolution_step

For efficiency x_calculation_step should not be defined for data with equal x-axis steps; instead rebin_with_dx_of should be used. The following response functions are calculated at smaller step sizes without changing Peak_Calculation_Step or Nr:


| axial_conv | : Step = Peak_Calculation_Step / 2 |
| --- | --- |
| lpsd_th2_angular_range_degrees | : Step = Peak_Calculation_Step / 3 |
| capillary_diameter_mm | : Step = Peak_Calculation_Step / 1 to 3 |

In this manner a high degree of accuracy is maintained and Np*Nr is left unchanged. Typically, a laboratory diffraction pattern can be accurately synthesized with a Peak_Calculation_Step of 0.02 degrees 2Th. The next step to increasing accuracy would be to increase convolution_step to 2 and so on. The computational effort for direct convolution scales by (Nr * Np). Convolutions that scale by (Nr+Np) are very fast and are:

exp_conv_const, hat, stacked_hats_conv

Calculating derivatives of parameters that are a function of a convolution can be demanding. Most convolutions however that have multiple dependent parameters require only one recalculation of the convolution; exceptions are ft_conv, WPPM_ft_conv and user_defined_convolution. In the case of convolutions that comprise multiple convolution parameters, for example, axial_conv with its convolution parameters of primary_soller_angle etc..., then a recalculation for each of the convolution parameters is required. The following is an overview of convolutions and associated aberrations:


| axial_conv | Full Axial divergence model |
| --- | --- |
| one_on_x_conv | Equatorial Divergence |
| circles_conv | Simple axial model |
| capillary_diameter_mm | Capillary sample |
| lpsd_th2_angular_range_degrees | LPSD detector |
| exp_conv_const | Sample penetration |
| hat | Receiving slit width, sample tilt |
| stacked_hats_conv | Tube tails |


### Capillary convolution for a focusing convergent beam

The capillary convolution has been extended to include a focusing convergent beam (Coelho & Rowles, 2017); syntax is as follows:

```
[Tcomm_1]
    [capillary_diameter_mm E]
        capillary_u_cm_inv E
        [capillary_convergent_beam] [capillary_divergent_beam] [capillary_parallel_beam]
        [capillary_focal_length_mm E]
        [capillary_xy_n #]
```

See examples lab6-stoe.inp and lab6-d8.inp in the directory test_examples\capillary. If using a str phase then capillary_u_cm_inv can be set to the calculated linear absorption coefficient multiplied by a packing density, for example:


| prm packing_density 0.31208 capillary_diameter_mm @ 0.57313 capillary_u_cm_inv  = Get(mixture_MAC) Get(mixture_density_g_on_cm3) packing_density; capillary_focal_length_mm @ 197.89657 capillary_convergent_beam |
| --- |

If capillary_focal_length_mm is not defined, then it defaults to the diffractometer radius Rs.


### ft_conv


```
[Tcomm_1]
    [ft_conv_re_im]...
        [ft_conv_re E]
        [ft_conv_im E]
        [ft_min !E]
        [ft_x_axis_range !E]
        ' Get(ft_0)
        ' FT_Break
```

Examples: `test_examples\ft\alvo4a.inp`, `test_examples\ft\voigt.inp`

Fourier Transform (FT) of a response function that is convoluted into phase peaks using a Fast Fourier Transform (FFT); for example, to convolute a Voigt into a phase, the following can be used:


| ft_conv = Exp(-(Pi FT_K gfwhm)^2 / (4 Ln(2)) - Pi FT_K lfwhm); ft_min = 1e-8; ‘ this is the default; ft_min is optional ft_x_axis_range = 40 lfwhm; |
| --- |


| ft_conv = If (FT_K > D, FT_Break, Sphere(FT_K, D)); |
| --- |

Here the calculation of the FT is terminated when FT_K>D using FT_Break. Get(ft_0) returns FT(k=0) and can be used within the ft_conv equation, for example:


| ft_conv = { def a = Exp(-Pi FT_K lf); return If(a < 1e-6 Get(ft_0), FT_Break, a); } |
| --- |

ft_conv integrates with convolutions that are performed in direct space. It can be used within peak stack operations, and it can be a function of the reserved parameter names:

H, K, L, M, Th, Xo, D_spacing, FT_K

ft\alvo4a.inp compares the use of spherical_harmonics_hkl with and without ft_conv as follows.


| prm csl 50 min 3 max = Min(Val 2 + 0.1, 10000); prm csg 50 min 3 max = Min(Val 2 + 0.1, 10000); prm csl_fwhm = 0.1 Rad Lam / (csl Cos(Th)); prm csg_fwhm = 0.1 Rad Lam / (csg Cos(Th)); if 1 { 	‘ Spherical Harmonics spherical_harmonics_hkl sh 	sh_order 2  load sh_Cij_prm { y00   !sh_c00  1 	y20   sh_c20   0	 	y21p  sh_c21p  0	 	y21m  sh_c21m  0	 	y22p  sh_c22p  0	 	y22m  sh_c22m  0	 	} 	existing_prm csl_fwhm *= sh; 	existing_prm csg_fwhm *= sh; } if 0 { 	‘ use analytical Lorentzian and Gaussian convolution 	lor_fwhm = csl_fwhm; 	gauss_fwhm = csg_fwhm; } else { 	‘ use Fourier Transform convolution ft_conv = Exp(-(Pi FT_K csg_fwhm)^2 / (4 Ln(2)) - Pi FT_K csl_fwhm); 	ft_x_axis_range = 45 csl_fwhm + 4 csg_fwhm; } |
| --- |


#### ft_conv compared to user_defined_convolution

ft\lorentzian.inp

tof\tof_bank2_2.inp

wppm\gamma.inp

udefa.inp

udefa.inp shows how to convolute a function with discontinuities, i.e.


| user_defined_convolution = Exp(-20 X^2); min = -.2; max = .5; |
| --- |

The FT for functions with such discontinuities often cannot be described analytically.


#### FFT versus direct summation

P    0 0 0 1 1 1 1 1 0 0 0

R      - - x

R        - x x

R          x x x

R            x x x

R              x x x

R                x x -

R                  x - -

In this representation each 'x' can be considered a multiply; in direct convolution this makes a total of 15 multiplies (Nr*Np) and not N2 where N/2≤(Nr+Np)≤N. To perform such a convolution using an FFT, the number of operations is approximately 4*16*log216=256 multiplies, where 16 is the closest power of 2 to Nr+Np. Of course, FFT routines typically also have special cases for small N; nonetheless N=256 to 512 is not small, and many peaks in XRD work typically comprise less points and many of the response functions have a small Nr; these include axial divergence, equatorial divergence, receiving slit width, capillary convolution, LPSD convolution and often sample penetration. Another factor favouring direct convolution for modest Nr and Np is the fact that modern processors such as the Intel i7 are very fast when data in cache memory are arranged sequentially and accessed sequentially. In fact, non-sequential operations can be as much as 8 times slower than for the sequential case.


### WPPM


```
[Tcomm_1]
    [WPPM_ft_conv_re_im E]...
        [WPPM_ft_conv_re E]
        [WPPM_ft_conv_im E]
        WPPM_L_max E
        WPPM_th2_range E
        [WPPM_break_on_small !E]
        [WPPM_correct_Is]
```

Examples: `test_examples\WPPM\gamma.inp`, `gamma-fit-obj.inp`, `sphere-fit-obj.inp`, `super-lorentzian.inp`, `compare-1.inp`, `s-sphere-1.inp`, `cube-ln-normal-1.inp`, `ln-normal-1.inp`

WPPM_ft_conv is equal to [WPPM_ft_conv_re_im WPPM_ft_conv_re].


#### WPPM in 2Th space

The WPPM microstructure analysis (Scardi & Leoni, 2001; Leoni et al. 2004; David et al. 2010) for domains comprising spheres and a gamma distribution can be implemented using user_defined_convolution operating in 2Th space as shown in gamma.inp.


#### WPPM using fit_obj(s)

For cases where microstructure broadening is far greater than instrument/emission profile broadening then fit_obj’s can be used to describe the peak shape (see gamma-fit-obj.inp and sphere-fit-obj.inp), for example:


| fn gamma_mu_variance(mu, v, xo) {          def s = 2 ( Sin( X Pi/360) - Sin(xo Pi/360) ) / lam;          def p0 = Pi s mu;          def p = If(Abs(p0) < 1e-10, 1, p0);          def q = 2 p / v;          return mu v / p^4             (                2 p^2 / (2 + v) + (v/(2+ 3 v + v^2)) (1 - (1 + q^2)^(-.5 v)                 Cos(v ArcTan(q)) - 2 p (1 + q^2)^(-.5 (v+1)) Sin( (1 + v)                 ArcTan(q)))             );       } |
| --- |


#### WPPM using WPPM_ft_conv


| WPPM_ft_conv = 1 - 1.5 WPPM_L / D + 0.5 (WPPM_L / D)^3; WPPM_L_max = D; WPPM_th2_range = 25 .1 Rad Lam / (D Cos(Th));  WPPM_break_on_small 1e-7 WPPM_correct_Is |
| --- |

The result is then interpolated back to 2Th space. Interpolations are scaled such that I(s)ds = I(q)dq when WPPM_correct_Is is defined; the effects of this scaling is typically small at low angles and becomes noticeable at very high angles reaching a maximum at 180 degrees 2Th where the derivative of Cos(Th) is at a maximum.

When multiple WPPM_ft_conv(s) are defined then the program will internally use the convolution theorem.

WPPL_L is a reserved parameter name that returns the transform parameter.

WPPM_L_max defines the maximum WPPL_L.

The calculation of the Fourier transform is terminated when WPPM_ft_conv_re is less than WPPM_break_on_small multiplied by the value of WPPM_ft_conv_re evaluated at WPPM_L = 0. If WPPM_break_on_small is not defined, then no check is made to terminate the transform.

The tails of WPPM peaks extend for almost the whole diffraction pattern; they can be shortened using WPPM_th2_range; in the above example, this range has been written in terms of the fwhm as defined in the Scherrer equation. WPPM_ft_conv can be a function of the following reserved parameter names:

H, K, L, M, Th, Xo, D_spacing, WPPM_L

Example s-sphere-1.inp uses WPPM_ft_conv to fit to a synthesized WPPM generated peak with identical results. Example cube-ln-normal-1.inp can be used to test these macros. Lattice parameters appearing within the macros are made constant using Constant; these convolutions are therefore made independent of lattice parameter changes and hence separate convolutions are not initiated whilst calculating lattice parameter derivatives.

WPPM_Ln_k is a reserved parameter name that returns Ln of an integer and is used to calculate Ln(Kc WPPM_L) in a fast manner.

The example ln-normal-1.inp can be used for visualizing a Ln normal distribution. It uses the Ln_Normal_x_at_CD function to determine the limit of the distribution.


### Microstructure convolutions

The Double-Voigt approach (Balzar, 1999) is supported for modelling microstructure effects. Crystallite size and strain comprise Lorentzian and Gaussian component convolutions varying in 2 as a function of 1/cos() and tan() respectively.


#### Preliminary equations

The following preliminary equations are based on the unit area Gaussian, GUA(x), Lorentzian, LUA(x), and pseudo-Voigt PVUA(x) functions as given in Table 5-2.

Height of GUA(x) and LUA(x) respectively:

GUAH = GUA(x=0) = g1 / fwhm

LUAH = LUA(x=0) = l1 / fwhm

Gaussian and Lorentzian respectively with area A:

G(x) = A GUA(x)

L(x) = A LUA(x)

Height of G(x) and L(x) respectively:

GH = A GUA

LH = A LUAH

Integral breadth of Gaussian and Lorentzian respectively:

G = A / GH = 1 / GUAH = fwhm / g1

L = A / LH = 1 / LUAH = fwhm / l1

Unit area Pseudo Voigt, PVUA:

PVUAH =  LUAH + (1-) GUAH

PV = 1 / PVUAH

A Voigt is the result of a Gaussian convoluted by a Lorentzian:

V = G(fwhmG)  L(fwhmL)

where "" denotes convolution and fwhmG and fwhmL are the FWHM of the Gaussian and Lorentzian components. A Voigt can be approximated using a Pseudo Voigt. This is done numerically where:

V(x) = G(fwhmG)  L(fwhmL) = PVUA(x, fwhmPV)

By changing units to s (Å-1):

s = 1/d = 2 sin() /

and differentiating and approximating ds/d = s / we get:

s = (2 cos() / ) 

thus:

fwhm(s) = fwhm(2) cos() /

IB(s) = IB(2) cos() /


#### Crystallite size and strain

Crystallite Size: Gaussian and Lorentzian component convolutions are:

fwhm(2) of Gaussian = (180/)  / (cos() CS_G)

fwhm(2) of Lorentzian= (180/)  / (cos() CS_L)

(2) of Gaussian = (180/)  / (cos() CS_G g1)

(2) of Lorentzian = (180/)  / (cos() CS_L l1)

or, according to Balzar (1999), in terms of s, GS and CS:

fwhm(s) of Gaussian = (180/) / CS_G

fwhm(s) of Lorentzian = (180/) / CS_L

GS(s) =(s) of Gaussian =  (180/) / (CS_G g1)

CS(s) =(s) of Lorentzian = (180/) / (CS_L l1)

The macros CS_L and CS_G are used for calculating the CS_L and CS_G parameters respectively. Determination of the volume weighted mean column height LVol, LVol-IB and LVol-FWHM is as follows:

LVol-IB = k / Voigt_Integral_Breadth_GL (1/CS_G, 1/CS_L)

LVol-FWHM = k / Voigt_FWHM_GL(1/CS_G, 1/CS_L)

The macro LVol_FWHM_CS_G_L is used for calculating LVol-IB and LVol-FWHM.

Strain: Strain_G and Strain_L parameters corresponds to the fwhm(2) of a Gaussian and a Lorentzian that is convoluted into the peak, or,

fwhm(2) of Gaussian = Strain_G tan()

fwhm(2) of Lorentzian= Strain_L tan()

(2) of Gaussian = Strain_G tan() / g1

(2) of Lorentzian = Strain_L tan() / l1

or, according to Balzar (1999), in terms of s, CD and GD:

fwhm(s) of Gaussian = Strain_G sin() /  = Strain_G s / 2

fwhm(s) of Lorentzian = Strain_L sin() /  = Strain_L s / 2

GD(s)/s0 s = (s) of Gaussian = (Strain_G / g1) s / 2

CD(s)/s0 s = s) of Lorentzian = (Strain_L / l1) s / 2

The macros Strain_L and Strain_G are used for calculating the Strain_L and Strain_G parameters respectively. From these equations we get:

GD(s) = s0 Strain_G / (2 g1)

CD(s) = s0 Strain_L / (2 l1)

According to Balzar (1999), equation (34):

e = D(2) / (4 tan())

where D(2) is the fwhm of a Voigt comprising a Gaussian with a fwhm = Strain_G Tan() and a Lorentzian with a fwhm = Strain_L Tan(). The value for e0 is given by:

4 e0 Tan()	= FWHM of the Voigt from Strain_G and Strain_L

= Voigt_FWHM_GL(Strain_G, Strain_L) Tan()

or,

e0 = Voigt_FWHM_GL(Strain_G, Strain_L) ( / 360)  / 4

The macro e0_from_Strain calculates e0 using the equation function Voigt_FWHM_GL.


## Loading of INP files


### if {} else if {} else {}

‘if’ operates during the loading of pre-processed INP files, syntax is as follows (see test_examples\zro2.inp):


| if expression { } else if expression { } else expression { } |
| --- |

expression can be any valid TOPAS equation without the semicolon; in addition, expression can contain the functions Prm_There(prm_name) and Obj_There(obj_name). The following is equivalent to a /* */ block comment:


| if 0 { ... } |
| --- |

A more complex construct could look something like:


| xdd	 	local aaa 1 	str ... 		local aaa 2 	str ... 		local aaa 3 	hkl_Is 		if Prm_There(aaa) { 			Out(aaa, "\nThis is the aaa at the xdd level %-1.6f") 			if aaa == 2 { Out_String("\nNot written to file as aaa at the xdd level is 1") 			} 		} else if Obj_There(hkl_Is) { 			Out_String("\nYes this is a hkl_Is phase") 		} else { 			Out_String("\naaa is not there and this is not a hkl_Is phase") 		} for xdds { if And(Obj_There(neutron), Obj_There(pk_xo)) {  ‘ Neutron TOF } } |
| --- |


## Functions – fn, def, return, noinline

Functions can be defined using fn; here’s an example of a recursive function:


| fn factorial(x) { return If(x == 1, 1, x factorial(x-1)); } prm = factorial(5); : 120 |
| --- |

There’s also the simple form where the return statement is implied:


| fn factorial(x) = If(x == 1, 1, x factorial(x-1)); |
| --- |

The equation part of prm objects can have a function body (see the Robust_Refinement macro in Topas.inc), for example:


| prm = { def a = 2; return a; } |
| --- |

Most importantly, functions can reference parameters defined using prm; this simplifies the writing of prm equations and additionally memory usage can be greatly reduced when noinline is used. Equations called def objects can be used and defined within non-simple functions. Here’s an example:


| fn gauss(a, x, f, g) { def a1 = 2 Sqrt(Ln(2) / Pi) / f; def a2 = 4 Ln(2); def a3 = (x / f); return a1 Exp(-a2 a3^2);  } |
| --- |

A def object must be defined prior to its use. They can be assigned to other def objects but not to objects of prm type. In other words, prm objects are write-protected within functions. The arguments to functions can be def or prm objects. c-style braces can be used to scope variables; the following will throw an exception due to the attempted use of an uninitialized def object:


| fn foo(x) { def a; { def a = x; } return a; } prm = foo(3); : 0 ‘ Exception thrown |
| --- |


| Fn a(x) = x undefined_name 0; prm = a(3); : 0 |
| --- |

Functions can be nested, for example:


| fn foo() {  	def a, b; 	a = 3; b = 2; 	fn nested(x, y) { return Sqrt(x^2 + y^2); } 	return nested(a, b); } prm = foo(); : 3.60555 |
| --- |

def and prm objects have scope which determines the actual object used.

Here def ‘a’ is returned:


| fn a(a) { def a = 2; return a; } prm = a(1); : 2 |
| --- |

Here prm ‘a’ is returned:


| prm a = 2; fn a() = a; prm = a(); : 2 |
| --- |

Here the argument ‘a’ is returned:


| prm a = 2; fn a(a) = a; prm = a(3); : 3 |
| --- |

Function specifics:

fn's are a kernel operation and not a pre-processor operation.

fn's must be defined prior to their use.

fn arguments are optional but parentheses must be used.

a fn cannot be defined with a name of a previously defined fn name.

fn's are inlined by default.

Non-nested fn’s can be prevented from being inlined with the noinline prefix.

nested functions cannot be prefixed with noinline.


| fn my_max(a, b, c) = Max(a, b, c); macro & my_max(& a, & b, & c) { Max(a, b, c) } |
| --- |

The macro, by definition, is inlined in the pre-processed INP file. In the case of fn, the program will inline ‘my_max’. Prefixing fn with noinline prevents in-lining, for example:


| noinline fn gauss(x, f)=(2 Sqrt(Ln(2)/Pi)/f) Exp(-4 Ln(2)((X-x)/f)^2); |
| --- |


| noinline fn a(b, c) = b^2 + c^2; prm  p1 1 prm !p2 1 prm  p3 1 prm !p4 1 prm  p5 = a(p1, p2) + a(p3, p4); : 0 |
| --- |

Without inlining, the simplification routines won’t see that p2 and p4 are constants inside the ‘a’ function and hence no simplification is performed; the ‘a’ function will be called twice, and the stack used twice. Note, stack here refers to the computer algebra stack. With inlining, p5 after simplification reduces to:


| prm p5 = p1^2 + p3^2 + 2; : 0 |
| --- |

In the case of large functions, not inlining may increase performance as the signalling of equation nodes for recalculation will be reduced. Inlined functions have scope allowing the use of the Get(…) function, for example:


| fn lat(h, k, l) = h Get(a) + k Get(b) + l Get(c); str ... lor_fwhm = lat(H, K, L) - lat(-H, -K, -L); |
| --- |


### Subject independent single crystal refinement

The example \functions\alvo4-fn.inp performs a single crystal refinement using computer algebra. No subject dependent keywords are used and instead only the following six keywords are used:

fn, noinline, def, return, prm, restraint

First pass equation statistics excluding attribute equations

Number of equations         : 534

Number of nodes             : 99751

Number of nodes if expanded : 12070283

Number of penalties/restraints: 532

Number of independent penalty/restraints parameters: 58

Number of penalties/restraints: 532

Number of independent penalty/restraints parameters: 58

Time   0.13

Second pass equation statistics excluding attribute equations

Before/After equation simplification

Number of equations         : 549  553

Number of nodes             : 99766  8354

Number of nodes if expanded : 12070298  228183

Number of objects taking part in refinement: 73

Number of dependent parameters with derivatives wrt to Ycalc: 15


### Computer algebra and out_refinement_stats

Second pass equation statistics excluding attribute equations

Before/After equation simplification

Number of equations         : 2707  3085

Number of nodes             : 22941  16671

Number of nodes if expanded : 1706390373  1070170132

Number of objects taking part in refinement: 2595

Number of dependent parameters with derivatives wrt to Ycalc: 2319


## CIF

The following macros and Get’s can be used to output data in CIF format:

Out_CIF_STR(file)

Out_CIF_ADPs(file)

Out_CIF_STR(file, with_id)

Out_CIF_Bonds_Angles(file)

Get(number_of_parameters)

Get(refine_ls_shift_on_su_max)

Get(weighting)

Xi = a reserved parameter name

refine_ls_shift_on_su_max 0.409610469 corresponds to parameter m501b939c_3 of object prm_10

Get(weighting) and Xi can be used as follows:


| xdd_out file append load out_record out_fmt out_eqn { 		" %9.0f" = Xi; 		" %11.5f" = X; 		" %11.5f" = Ycalc; 		" %11.5f" = Yobs; 		" %11.5f\n" = Get(weighting); 	} |
| --- |

Get(weighting) returns weighting as defined by the User; if weighting is not defined then the following is returned:

1 / Max(1, Yobs), 	     	if SigmaYobs does not exist

1 / SigmaYobs^2,  		if SigmaYobs does exist

Get(weighting) returns zero for x-axis regions that are excluded using exclude. If weighting is a function of Ycalc etc... then it returns the last weighting calculated depending on recal_weighting_on_iter.


## Laue refinement


| dont_merge_equivalent_reflections dont_merge_Friedel_pairs |
| --- |

and the following messages reported:

Equivalent reflections not merged

Friedel pairs not merged


## Learnt Shapes for Background or Otherwise


```
[xdd]...
    [user_y $name { #include $file }]... | [user_y $name $file]...
        [xye_format]
        [rebin_with_dx_of !E]
        [user_y_hat E]...
        [user_y_gauss_fwhm E]...
        [user_y_lor_fwhm E]...
        [user_y_exp_conv_const E [user_y_exp_limit E]]...
```

Examples: `test_examples\USER_Y\USER_Y_CONVOLUTION.INP`

1New user_y dependents. user_y_hat, user_y_gauss_fwhm, user_y_lor_fwhm and user_y_exp_conv_const are identical to the hat, gauss_fwhm and lor_fwhm and exp_conv_const convolutions except they are applied to user_y data.

user_y can be used to add, multiply and in general manipulate data files of different x-axis steps. For example, to add two data files, square the result and then multiply by the x-axis reserved parameter X, the following can be used:


| user_y f1 file1.xy user_y f2 file2.xy yobs_eqn result.sst = X (f1 + f2)^2; min 10 max 100 del 0.01 |
| --- |

The test example USER_Y\USER_Y.INP fits five fit objects to the quartz triplet using a learnt peak shape defined using user_y; the fit with the individual fit_obj’s displayed, using the Plot_Fit_Obj macro, looks like:

The test example USER_Y\USER_Y_CONVOLUTION.INP fits five fit objects to a simulated pattern using a learnt peak shape defined using user_y convoluted with user_y_exp_conv_const and user_y_gauss_fwhm; the INP file looks like:


| '#define CREATE_SIMULATED_   continue_after_convergence  macro FO_Peak(& p, & pe, & a, & x, & s)     {          fit_obj = a p;            min_X = -pe s + x; max_X = pe s + x; 			fo_transform_X = (X - x) / s;      }    prm !peak_extent 2  #ifdef CREATE_SIMULATED_   	iters 0 	user_y peak { _xy -0.01 0 0 100 0.01 0  } 		user_y_exp_conv_const @ 1    min 0.5 max 2 		user_y_gauss_fwhm     @ 0.1  min 0.1 max 2     yobs_eqn = 1; min 66 max 70 del 0.01 		gui_ignore ‘ don’t load data file into GUI 		Out_X_Ycalc(user_y_convolution.xy) #else 	' Fit to the simulated peak 	user_y peak { _xy -0.01 0 0 100 0.01 0  } 		user_y_exp_conv_const @ 1   min 0.5 max 2 val_on_continue = Rand(0.5, 2);  		user_y_gauss_fwhm     @ 0.1 min 0.1 max 1 val_on_continue = Rand(0.1, 1);  	xdd user_y_convolution.xy #endif       start_X  66       finish_X 70       bkg @ 100       prm a1 1000 min 1.0e-6 val_on_continue = Rand(1, 100);        prm a2 2000 min 1.0e-6 val_on_continue = Rand(1, 100);        prm a3 3000 min 1.0e-6 val_on_continue = Rand(1, 100);        prm a4 2000 min 1.0e-6 val_on_continue = Rand(1, 100);        prm a5 1500 min 1.0e-6 val_on_continue = Rand(1, 100);        prm x1 67.7 val_on_continue = Val + Rand(-0.01, 0.01) 5; min 67 max 69       prm x2 67.9 val_on_continue = Val + Rand(-0.01, 0.01) 5; min 67 max 69       prm x3 68.1 val_on_continue = Val + Rand(-0.01, 0.01) 5; min 67 max 69       prm x4 68.3 val_on_continue = Val + Rand(-0.01, 0.01) 5; min 67 max 69       prm x5 68.5 val_on_continue = Val + Rand(-0.01, 0.01) 5; min 67 max 69       prm s1 0.7 val_on_continue = Rand(0.5, 2); min 0.5 max 2       prm s2 0.9 val_on_continue = Rand(0.5, 2); min 0.5 max 2       prm s3 1.1 val_on_continue = Rand(0.5, 2); min 0.5 max 2       prm s4 1.0 val_on_continue = Rand(0.5, 2); min 0.5 max 2       prm s5 0.8 val_on_continue = Rand(0.5, 2); min 0.5 max 2       	        FO_Peak(peak, peak_extent, a1, x1, s1) Plot_Fit_Obj("user_y 1")       FO_Peak(peak, peak_extent, a2, x2, s2) Plot_Fit_Obj("user_y 2")       FO_Peak(peak, peak_extent, a3, x3, s3) Plot_Fit_Obj("user_y 3")       FO_Peak(peak, peak_extent, a4, x4, s4) Plot_Fit_Obj("user_y 4")       FO_Peak(peak, peak_extent, a5, x5, s5) Plot_Fit_Obj("user_y 5") |
| --- |


| user_y NAME { _x1_dx -1 1 /* start and step */ 0 1 0       /* the shape data */ } |
| --- |

Multiple user_y(s) can be defined, and each can be used any number of times in equations that can be a function of X. The test example user_y.inp loads a single shape and stretches and scales it five different ways onto a diffraction pattern to fit the Quartz triplet. Convergence is as fast as with any other refinement.


## Emission Profile with Absorption Edges


```
[Tcomm_1]
    [modify_peak]
        [modify_peak_apply_before_convolutions]
        [modify_peak_eqn !E]
            [current_peak_min_x !E]
            [current_peak_max_x !E]
    Get(current_peak)
    Get(current_peak_x)
```

Examples: `test_examples\absorption-edge\al2o3-pam.inp`, `SPINNEL-PAM.INP`

When no_th_dependence is defined then Get(current_peak_x) returns the x-axis of the point being calculated; when no_th_dependence is not defined then Get(current_peak_x) returns the wavelength of the point being calculated.


## scale_phase_X keyword


```
[xdd]...
    [scale_phase_X E]...
```

Examples: `test_examples\SCALE_PHASE_X.INP`

Scales Ycalc point by point. It can be used, for example, to define the Lorentz Polarization factor on an x-axis basis rather than on a peak basis as is the case for scale_pks. Some main points for scale_phase_X:

Can be a function of X

Multiple definitions allowed and each applied to the pattern.

Can occur at the xdd and/or phase level.

Here’s an example:


| xdd ... scale_phase_X ... str	   scale_phase_X ... hkl_Is	   scale_phase_X ... |
| --- |

The first str is multiplied by the first and second scale_phase_X; the hkl_Is phase is multiplied by the first and third scale_phase_X.


## Refining on f0, f’ and f”


```
[Tcomm_2]
    [f0_f1_f11_atom]...
        [f0 E] [f1 E] [f11 E]
```
Examples: `test_examples\f0-f1-f11\xray-powder.inp`, `test_examples\f0-f1-f11\tof.inp`
| --- | --- |

User defined atomic scattering factors, f0, and anomalous dispersion coefficients, f1 and f11. Example usage:


| report_on_str load f0_f1_f11_atom f1 f11 { Ba @ -0.160127754 2.3954287 Ge 0.184162081 1.86162161 } |
| --- |


| prm a1 25 min -50 max 50 load f0_f1_f11_atom f0 f11 { 	Pb+2 	= a1         Exp(1.058874   (-0.25) / D_spacing^2) + 	  16.496822  Exp(0.106305   (-0.25) / D_spacing^2) + 	  19.984501  Exp(6.708123   (-0.25) / D_spacing^2) + 	  6.813923   Exp(24.395554  (-0.25) / D_spacing^2) + 	  5.233910   Exp(1.058874   (-0.25) / D_spacing^2) + 	  4.065623; ‘ this is f0 for Pb 	  @ 5       ‘ this is f11 for Pb } |
| --- |

For X-ray data f0 is by default obtained from the file atmscat.TXT. For neutron data f0 corresponds to the neutron scattering length from the neutscat.TXT file. Neutron scattering lengths can be refined, see example tof.inp. no_f11 instructs the program to ignore f11. This increases speed with little change in Ycalc. report_on_str reports on f1 and f11, or neutron scattering lengths used. No values are reported when d_spacing_to_energy_in_eV_for_f1_f11 is used. To disable the effects of f0, f1 and f11, for say CeO2, then the following could be used:


| load f0_f1_f11_atom f0 f1 f11 { 	Ce+4 1 0 0 	O-2  1 0 0 } |
| --- |


### Using a user defined table to input f0 values via user_y

Atomic scattering factors f0 can be defined in a *.XY file and used via the user_y keyword as follows:


| xdd … user_y C_f0_table C_f0_table.xy ‘ x-axis are the D_spacings str load f0_f1_f11_atom f0 f1 f11 { C = C_f0_table; 0 0 } … |
| --- |

Here the C_f0_table.xy file comprises D_spacing and f0 value pairs which are used to describe f0 values for the C atoms within the structure. In the above example, f1 and f11 are set to zero.


## Invalid f1 and f11

The following message is displayed when there are no valid entries for f’ and f” in the corresponding NFF file:

Invalid f1 and f11 for O in file ...\ssf\o.nff

for the wavelength 0.399826.

Setting value(s) to zero

In such cases the user may choose to manually define f’ and f’’ using f1 and f11 respectively. Also useful is to view f’ and f’’ NFF files found in the ssf directory using the GUI Tools menu:


## Isotopes and Atom Names


| site ...  occ Mg ... site ...  occ Mg+2 ...  site ...  occ 24Mg ...  site ...  occ 26Mg ... site ...  occ 26Mg+2 ... |
| --- |

In the cases of ‘Mg’ and ‘Mg+2’ the atomic weight used is the ‘Standard Weight’ as defined in isotopes.txt. In the cases of ‘26Mg’ and ‘26Mg+2’ the atomic weight used is the isotope weight as defined in isotopes.txt. Note the ‘+2’ is dropped when searching that file. The atomic weight for 24Mg is not the same as that for Mg. When 24Mg is used then the isotope weight for 24Mg is used. When Mg is defined then the standard weight is used. The standard weight corresponds to the mean weight of the naturally occurring Mg isotopes.

In the case of x-rays:

atomic scattering factors used (from file atmscat.TXT) for 26Mg and 26Mg+2 corresponds to those of Mg or Mg+2 respectively. Numbers occurring at the start of the symbol are dropped when searching atmscat.TXT.

f’ and f’’ corrections (files in ssf directory) correspond to that for Mg. In other words, the numbers occurring at the start of the symbol as well as the charge (i.e. ‘+2’ in this case) are dropped.

In the case of neutrons:

scattering lengths used are from the neutscat.TXT file; the charge ‘+2’ is dropped when searching neutscat.TXT.

Internally the program converts ‘D’ and ‘T’ to ‘2H’ and ‘3H’ respectively.


## Atomic data files and associated sources


| Table 20-2. Files read when atomic data is sought. The references refer to the source of the data. In many cases the format of the data file corresponds to the original source format. |
| --- |
| anomdisp.TXT : f’ and f’’ for Laboratory X-ray tubes. File is read if there are no associated SSF\*.NFF file or if use_tube_dispersion_coefficients is defined. |
| atmscat.TXT : f0 or Elastic Photon-Atom Scattering, relativistic form factors; data from http://www.esrf.fr/computing/expg/subgroups/theory/DABAX/dabax.html |
| atom_colors.def : Red, Green, Blue (RGB) CPK atom colors from http://www.bio.cmu.edu/Courses/BiochemMols/Periodic/ElemList.htm. Used for assigning colors to atoms when displaying in OpenGL. |
| atom_radius.def : Atomic radii and Covalent radii from  http://www.esrf.fr/cgi-bin/periodic. |
| isotopes.txt : Atomic Weights and Isotopic Compositions for All Elements from http://physics.nist.gov/PhysRefData/Compositions/ |
| magdata.dat : Data from GSAS data file via the International tables. Data correction for V entry made by Robert Von Dreele. |
| neutscat.TXT : Neutron scattering lengths from http://www.ccp14.ac.uk/ccp/web-mirrors/neutrons/n-scatter/n-lengths/LIST~1.HTM |
| no_polyhedra.def : Disables drawing of polyhedral for atoms listed. |
| SSF\*.NFF : Anomalous scattering factors f’ and f’’ for a range of wavelengths from http://www-cxro.lbl.gov/optical_constants/asf.html The present data is in three columns “E(eV),f1,f2” where f'=f1–Z and f''= f2 and the conversion from wavelength to energy scale is: E(eV)=10^5/(8.065541*Lambda(Ang)). |
| MAC\Znn.html : X-Ray Mass Attenuation Coefficients from  http://www.nist.gov/pml/data/xraycoef/index.cfm |


## Removing Phases during refinement


```
[str | hkl_Is | xo_Is | d_Is]...
    [remove_phase !E]
```

Examples: `test_examples\REMOVE-PHASE.INP`

Allows for phase removal during refinement through use of the Remove_Phase macro. Typical usage is:


| for strs { Remove_Phase(0.3, 0.5) } |
| --- |

Here a phase is removed if its weight percent is below 0.3% and if the error in the weight percent is greater than 0.5 times the weight percent. The phase removal process is executed at the end of a Cycle. The following text is displayed on removal of a phase:

*** Deleting phase: Corundum ***

*** Deleting phase: Zincite ***

etc...

Refinement is terminated when no phases are removed during a Cycle.


## Numerical Lorentzian and Gaussian Convolutions

For fundamental and pseudo-Voigt peak types, Lorentzian and Gaussian convolutions are performed analytically during the calculation of the emission profile Voigt. Therefore, lor_fwhm and gauss_fwhm are still calculated at the emission profile level even when defined between push_peak and add_pop_1st_2nd_peak keywords.


## Space groups, hkls and symmetry operators

```
[str | hkl_Is]...
    [space_group $symbol]
```

Used to define the space group where $symbol can be any symbol (case insensitive) occurring in the file SGCOM5.TXT, it can also be a space group number; here are some examples:


| space_group "I a -3" space_group ia-3 space_group P_63_M_C space_group I_41/A_M_D space_group I_41/A_M_D:2 ‘ defines second setting of I_41/A_M_D space_group 206 space_group 222:2        ‘ defines second setting of 222 |
| --- |


### User defined rotational matrices

Space group generator - User defined rotational matrices can be added to the file sgrots3.TXT found in the main TA directory.


## Defining hkls using use_hklm

hkls are automatically generated for str phases. This behaviour can be changed using the use_hklm keyword such that hkls become User-defined; for example:


| str…       load use_hklm {   2   2   0  12    2   2   2   8           … } |
| --- |


## Cross correlation function


```
[xdd]...
    [cross_corr $name #value
        cross_corr_s !E
```

Examples: `cross-corr\cross.inp`

cross_corr calculates the cross-correlation function for a triangle of x-axis width cross_corr_s. cross_corr_s can be an equation that can be a function of Cycle_Iter which allows for changing the width of the triangle in situ. $name is a name that can be given to the function and #value is the value of the cross-correlation function. $name can be used in the chi2 keyword for obtaining lattice parameters. However, as can be seen in the example CROSS.INP, using normal refinement with a triangle convolution is much faster than using the cross-correlation function. CROSS.INP is an informative example and it looks like:


| #prm USE_CROSS_CORRELATION = 1; ‘ Set to zero to see normal refinement #prm INCLUDE_HATS = 1;          ‘ This is for normal refinement        macro DEL_ { Rand(-1, 1) 0.5 }  ‘ Change in lattice parameters at the start of a Cycle macro AA { }  continue_after_convergence verbose 1 iters 2000  RAW(..\pbso4)    rebin_with_dx_of 0.01    CuKa5(0.0001)    LP_Factor(17)    Radius(173)    Full_Axial_Model(10, 10, 10, !sol  3.77616`, !sol  3.77616`)    Divergence(1)    Slit_Width(0.2)    bkg AA -792.524948 767.974856 -305.050785 121.658117 -45.020282 18.2136589    One_on_X(AA, 22265.9137`)     ZE(AA,-0.0110740988)     finish_X 60    extra_X_right 10     #if (USE_CROSS_CORRELATION)       cross_corr corr 0          cross_corr_s 3       chi2 = -Ln(corr); : 0       macro SCALE_ {  }    #else       ' Normal refinement       #if (INCLUDE_HATS)          hat @ 1 val_on_continue 2 max 2 num_hats 2       #endif       macro SCALE_ { @ }    #endif     STR(P_b_n_m) ' PbSO4       space_group P_b_n_m       macro LP_(v) { v val_on_continue = v + DEL_; min = v - 3; max = v + 3;       a  @  LP_(6.962377)       b  @  LP_(8.483133)       c  @  LP_(5.400478)       site Pb x AA 0.16717 y  AA 0.18778 z 0.25       occ Pb+2 1 beq AA 1.47495       site S  x AA 0.18429 y  AA 0.43563 z 0.75       occ S    1 beq AA 0.85254       site O1 x AA 0.09441 y  AA 0.59667 z 0.75       occ O-2  1 beq AA 1.05681       site O2 x AA 0.03611 y  AA 0.31151 z 0.75       occ O-2  1 beq AA 1.63474       site O3 x AA 0.31549 y  AA 0.42069 z AA 0.97553 occ O-2  1 beq AA 1.49181        CS_L(AA, 274.77)       Strain_L(AA, 0.035898)       scale SCALE_  0.000335087199 |
| --- |

Running cross.inp with USE_CROSS_CORRELATION set to 1 gives an Rwp plot of:

Running cross.inp with USE_CROSS_CORRELATION set to 0 (normal refinement) gives an Rwp plot of:


## Site identifying strings

Keywords such as operate_on_points use a site identifying string which can contain the wild card character * and the negation character !. The wild card character * used in O* means that sites with names starting with O are considered. In addition to using the wild card character, site names can be written explicitly within double quotation marks. Table 20-3 shows some operate_on_points strings and the corresponding sites identified.


| Table 20-3. operate_on_points strings and corresponding sites identified. | Table 20-3. operate_on_points strings and corresponding sites identified. | Table 20-3. operate_on_points strings and corresponding sites identified. |
| --- | --- | --- |
| str    site Pb1 ...    site S1 ...    site O1 ...    site O2 ...    site O31 ...    site O32 ...    site O4 ... | $sites | Sites identified |
| str    site Pb1 ...    site S1 ...    site O1 ...    site O2 ...    site O31 ...    site O32 ...    site O4 ... | * | Pb1, S1, O1, O2, O31, O32, O4 |
| str    site Pb1 ...    site S1 ...    site O1 ...    site O2 ...    site O31 ...    site O32 ...    site O4 ... | Pb* | Pb1 |
| str    site Pb1 ...    site S1 ...    site O1 ...    site O2 ...    site O31 ...    site O32 ...    site O4 ... | “Pb1 S*” | Pb1, S1 |
| str    site Pb1 ...    site S1 ...    site O1 ...    site O2 ...    site O31 ...    site O32 ...    site O4 ... | O* | O1, O2, O31, O32, O4 |
| str    site Pb1 ...    site S1 ...    site O1 ...    site O2 ...    site O31 ...    site O32 ...    site O4 ... | “O* !O3*” | O1, O2, O4 |
| str    site Pb1 ...    site S1 ...    site O1 ...    site O2 ...    site O31 ...    site O32 ...    site O4 ... | “O* !O1 !O2” | O31, O32, O4 |


## Occupancies and symmetry operators

Only unique positions are generated from symmetry operators. Fully occupied sites therefore require site occupancy values of 1. A comparison of atomic positions is performed in the generation of the unique positions with a tolerance in fractional coordinates of 10-15. It is therefore necessary to enter fractions in the form of equations when entering fractional atomic coordinates that have recurring values such as 0.33333..., 0.66666... etc., for example:


| use: | x = 1/3;  y = 1/3;  z = 2/3; |
| --- | --- |
| instead of: | x 0.33333 y 0.33333 z 0.66666 |


## Pawley and Le Bail extraction

```
[hkl_Is]...
    [lebail #]
```

Use the following input segment for Le Bail intensity extraction (see example lebail1.inp):


| hkl_Is		space_group p-1	lebail 1 ... |
| --- |

Use the following input segment for Pawley intensity extraction (see example pawley1.inp):


| hkl_Is	   space_group p-1 ... |
| --- |

hkls are generated in the absence of hkl_m_d_th2 keywords. After refinement, details for the generated hkl’s are appended after the space_group keyword. For the Pawley method, once the hkl details are generated, parameter equations can be applied in the usual manner to the I parameters.


## Anisotropic refinement models

Keywords that can be a function of H, K, L and M, as shown in Table 2-3, allow for the refinement of anisotropic models including preferred orientation, and peak broadening. An important consideration when dealing with hkls in equations is whether to work with hkls or whether to work with their multiplicities. The Multiplicities_Sum macro can be used when working with multiplicities, for example:


| prm a 0 th2_offset = Multiplicities_Sum(If(Mod(L, 2) == 0, a Tan(Th), 0)); |
| --- |


### Spherical harmonics

spherical_harmonics_hkl can be applied to both peak shapes, for anisotropy, and intensities for a preferred orientation correction. Preferred orientation can be described using the PO_Spherical_Harmonics(sh, order) macro, where "sh" is the parameter name and "order" the order of the spherical harmonics. scale_pks is used to correct peak intensities as follows:


| macro PO_Spherical_Harmonics(sh, order) {    spherical_harmonics_hkl sh        sh_order order       scale_pks = sh;  } |
| --- |

Example clay.inp uses spherical_harmonics_hkl for describing anisotropic peak broadening using the exp_conv_const convolution as follows:


| str ...    spherical_harmonics_hkl sh       sh_order 8       exp_conv_const = (sh-1) Tan(Th); |
| --- |


### Miscellaneous models using User defined equations

Anisotropic Gaussian broadening as a function of L (see example ceo2hkl.inp):


| str ...    prm a 0.1 min 0.0001 max 5    prm b 0.1 min 0.0001 max 5    gauss_fwhm = If(L==0, a Tan(Th) + 0.2, b Tan(Th)); |
| --- |

Anisotropic peak shifts as a function of L (th2_offset):


| str ...    prm at 0.07 min 0.0001 max 1    prm bt 0.07 min 0.0001 max 1    th2_offset = If(L == 0, at Tan(Th), bt Tan(Th)); |
| --- |

Description of anisotropic peak broadening using the March (1932) relation and str_hkl_angle:


| str ...    str_hkl_angle ang1 1 0 0    prm p1 1    min 0.0001 max 2    prm p2 0.01 min 0.0001 max 0.1    lor_fwhm = p2 Tan(Th) Multiplicities_Sum(((p1^2 Cos(ang1)^2 +                Sin(ang1)^2 / p1)^(-1.5))); |
| --- |


## Simulated annealing and structure determination

Defining continue_after_convergence and a temperature regime is analogous to defining a simulated annealing process (Coelho, 2000). After convergence, a new refinement cycle is initiated with parameter values changed according to any defined val_on_continue attributes and rand_xyz or randomize_on_errors processes. Simulated annealing is therefore not specific to structure solution, see for example onlypena.inp and rosenbrock-10.inp. Convergence is determined when the change in  is less than chi2_convergence_criteria for three consecutive cycles and when all defined stop_when parameter attributes evaluate to true. Example:


| chi2_convergence_criteria = If(Cycle_Iter < 10, 0.001, 0.01); |
| --- |

For structure solution in real space, the need for computation efficiency is critical. In many cases computation speed can be increased by up to a factor of 20 or more with the appropriate choice of keywords. Keywords that facilitate speed are:


| chi2_convergence_criteria... quick_refine... yobs_to_xo_posn_yobs... |
| --- |

Another category is one that facilitate structure solution by changing the form of :


| penalties_weighting_K1... penalty... occ_merge... rigid... |
| --- |

Further keywords and processes typically used are:


| file_name_for_best_solutions seed temperature !E ...    move_to_the_next_temperature_regardless_of_the_change_in_rwp    save_values_as_best_after_randomization    use_best_values xdd ... or xdd_scr ...    str ...       site ... rand_xyz ... |
| --- |


### Penalties used in structure determination

Introducing suitable penalties can reduce the number of local minima in  and correspondingly increase the chances of obtaining a global minimum. The structure factor for a reflection with Miller indices 10 0 0 for a two-atom triclinic unit cell with fractional atomic coordinates of (0,0,0) and (x, 0,0) is given by 4 cos(hx)2; here there are 10 local minima for 0<x<1. If it was known that the bond length distance is half the distance of the a lattice parameter then a suitable penalty would reduce the number of minima to one. In this trivial example the number of minima increases as the Miller indices increase. For non-trivial structures and for the important d spacing range near inter-atomic distances of 1 to 2Å the number of local minima is very large. Bragg reflections with large Miller indices that are heavily weighted are expected to contain many false minima; by applying an appropriate weighting scheme to the diffraction data the search for the global minimum can be facilitated. For powder data the default weighting scheme is:


| weighting = If(Yobs <= 1, 1, 1 / Yobs); |
| --- |

For single crystal data the following, which is proportional to 1/d, works well:


| weighting = 1 / (Sin(X Deg / 2) Max(Yobs,1)); |
| --- |

A more elaborate scheme which also works well for single crystal data is:


| weighting = ( Abs(Yobs-Ycalc) / Abs(Yobs+Ycalc) + 1) / Sin(X Deg / 2); |
| --- |


|  | (20-14) |
| --- | --- |

where r0 is a bond length distance, rij the distance between atoms i and j including symmetry equivalent positions and the summation is over all atoms of type j. The ai_anti_bump and box_interaction keywords are used to implement the penalty of Eq. (20-15) using the AI_Anti_Bump and Anti_Bump macros respectively. Typically, Anti bump constraints are applied to heavy atoms; an overuse of such constraints can in fact hinder simulated annealing in finding the global minimum. Applying the constraint for the first few iterations of a refinement cycle can also be beneficial; this is achieved in the AI_Anti_Bump macro by writing the penalty in terms of the reserved parameter Cycle_Iter; see for example cime-decompose.inp.


|  | (20-15) |
| --- | --- |
| where |  |

where A = e2/(40) and 0 is the permittivity of free space, Qi and Qj are the ionic valences of atoms i and j, ri,j is the distance between atoms i and j and the summation is over all atoms to infinity. The repulsive constants Bi,j, n, ci,j and d is characteristic of the atomic species and their potential surrounds. The equation part of the grs_interaction is typically used to describe the repulsive terms.


### Bond length restraints

Example alvo4-grs-auto.inp defines a bond length restraint using the GRS series  between an Aluminum site and three Oxygen sites. Valence charges have been set to +3 and –2 for Aluminum and Oxygen, respectively. The expected bond length is 2 Å between for O-O bonds and 1.5 Å for Al-O bonds:


| site Al  x @ 0.7491  y @ 0.6981  z @ 0.4069  occ Al+3 1  beq 0.25 site O1  x @ 0.6350  y @ 0.4873  z @ 0.2544  occ  O-2 1  beq 1 site O2  x @ 0.2574  y @ 0.4325  z @ 0.4313  occ  O-2 1  beq 1 site O3  x @ 0.0450  y @ 0.6935  z @ 0.4271  occ  O-2 1  beq 1 Grs_Interaction(O*, O*, -2, -2, oo,  2.0, 5)  penalty = oo;  Grs_Interaction(Al, O*,  4, -2, alo, 1.5, 5)  penalty = alo; |
| --- |

The following example defines a bond length restraint using the AI_Anti_Bump macro between a Potassium site and three Carbon sites. The expected bond length is 4 Å between Potassium sites and 1.3 Å between Carbon sites.


| site K   x @ 0.14305  y @ 0.21812  z @ 0.12167  occ K 1  beq 1 site C1  x @ 0.19191  y @ 0.40979  z @ 0.34583  occ C 1  beq 1 site C2  x @ 0.31926  y @ 0.35428  z @ 0.32606  occ C 1  beq 1 site C3  x @ 0.10935  y @ 0.30991  z @ 0.39733  occ C 1  beq 1 AI_Anti_Bump(K , K , 4  , 1) AI_Anti_Bump(C*, C*, 1.3, 1) |
| --- |

Unlike the first example, there's no explicit definition of a penalty function as the AI_Anti_Bump macro includes the penalty function.


## Not saving extrapolated peaks when doing intensity derivatives


| str… [dont_save_extrapolated_pks] |  |
| --- | --- |

The process of adding peaks to a calculated profile from the peaks buffer can be computationally intensive. This process occurs many times during a refinement iteration when, for example, calculating the derivatives of a site fractional atomic coordinate. An in-between step is therefore performed where interpolated peak data is stored. The memory requirements for the interpolated data can be large and in cases where memory is an issue then the keyword dont_save_extrapolated_pks can be used.


## Applying lp_search to TOF data

lp_search cannot be directly applied to TOF data. However, it is relatively easy to convert the TOF data to 2Th data where lp_search can be used. The examples test_examples\tof\tof-to-q.inp is an example that converts the data to 2Th and then applies lp_search. The conversion is as follows:

I(Q) = Intensity(TOF) dTOF/dQ

Q = 2 Pi / d

d = 2 Pi / Q

TOF = t0 + t1 d + t2 d^2 = t0 + t1 2 Pi / Q + t2 (2 Pi)^2  / Q^2

dTOF/dd = t1 + 2 t2 d;

dd/dQ = -2 Pi / Q^2;

dTOF/dQ =  dTOF/dd dd/dQ

If t0 = t2 = 0 we get:

dTOF/dQ = -t1 2 Pi / Q^2 = -t1 D_spacing^2 / (2 Pi)

Or in INP format we have:


| xdd TOF-DATA.XY    x_calculation_step = Yobs_dx_at(Xo) .5;prm !t0 0    prm !t1 6171.89377    prm !t2 0    prm !d = X / t1;    prm !Q = 2 Pi / d;    prm !dtof_dd = t1 + 2 t2 d;    prm !dd_dQ = -2 Pi / Q^2;    prm !dtof_dQ = dtof_dd dd_dQ;    xdd_out TOF-to_Q.xy load out_record out_fmt out_eqn       {           " %11.6f  " = 2 Pi / d;           " %11.6f\n" = Yobs Abs(dtof_dQ);       } |
| --- |


## Correction for dispersion using modify_peak_eqn


| Example:   test_examples\dispersion\disp.inp |
| --- |

The shape of the emission profile changes with 2q due to dispersion such that:

I(lam) dlam = I(th) dth

or,

I(th) = I(lam) dlam_dth

Differentiating Bragg’s with respect to q we have:

dlam_dth = 2 d Cos(th)

or,

I(th) = I(lam) 2 d Cos(th)

Rearranging we get:

I(th) = lam I(lam) Cot(th)

The point by point intensity of the emission profile therefore changes as function of Cot(th). disp.inp show difference between correcting for and not correcting for dispersion as follows:

The peak shape of the above is as follows:


| hat 0.1 num_hats 3 ' specimen/instrument lam ymin_on_ymax 0.0000001 la 1 lo !lam_0 1.540596 lh 0.5 modify_peak_eqn = Get(current_peak) If (And(Get(current_peak_x)>(lam_0-1.5),Get(current_peak_x)<(lam_0+ 1.5)), 1 / Tan(ArcSin(Get(current_peak_x) / (2 D_spacing))), 0 ); |
| --- |


## File types and formats


| Table 20-4. File types. | Table 20-4. File types. | Table 20-4. File types. |
| --- | --- | --- |
| *.PRO | Project files. | Project files. |
| *.INP | Input file in INP format. | Input file in INP format. |
| *.OUT | Output file created on termination of refinement in INP format. | Output file created on termination of refinement in INP format. |
| *.STR | Structure data. Same format as *.INP. | Structure data. Same format as *.INP. |
| *.LAM | Source emission profile data. Same format as *.INP. | Source emission profile data. Same format as *.INP. |
| *.DEF | Program defaults. Same format as *.INP. | Program defaults. Same format as *.INP. |
| *.LOG | TOPAS.log and Tc.log. Useful for tracking input errors. | TOPAS.log and Tc.log. Useful for tracking input errors. |
| Measurement Data | Measurement Data | Measurement Data |
| *.SST | Implies an equal x-axis and has the format of “start, step, data points….” SST files can be used instead of *.XY files. As x-axis values are not used, they save space on creation as well as on loading. For equal x-axis data then the macro Out_XDD_SST can be used in the following manner: | Implies an equal x-axis and has the format of “start, step, data points….” SST files can be used instead of *.XY files. As x-axis values are not used, they save space on creation as well as on loading. For equal x-axis data then the macro Out_XDD_SST can be used in the following manner: |
| *.RAW | Bruker AXS binaries (DIFFRAC AT and DIFFRACplus) | Bruker AXS binaries (DIFFRAC AT and DIFFRACplus) |
| *.DAT, *.XDD, *.CAL, *.XY, *XYE, *.HDF5 | *.DAT, *.XDD, *.CAL, *.XY, *XYE, *.HDF5 | ASCII file formats, see Table 20-5 |
| *.SCR | ASCII file format comprising lines of h, k, l, m, d, 2, and Fo. | ASCII file format comprising lines of h, k, l, m, d, 2, and Fo. |
| *.HKL | ShelX HKL4 format. | ShelX HKL4 format. |
| Structure and structure factor data | Structure and structure factor data | Structure and structure factor data |
| *.CIF | Crystallographic Information File;  International Union for Crystallography. | Crystallographic Information File;  International Union for Crystallography. |
| *.FCF | CIF file representation of structure factor details suitable for generating Fourier maps using ShelX. | CIF file representation of structure factor details suitable for generating Fourier maps using ShelX. |


| Table 20-5. ASCII input data file formats. *.XY, *.XYE, *.XDD and *.CAL are white space delimited and can contain line and block comments. | Table 20-5. ASCII input data file formats. *.XY, *.XYE, *.XDD and *.CAL are white space delimited and can contain line and block comments. | Table 20-5. ASCII input data file formats. *.XY, *.XYE, *.XDD and *.CAL are white space delimited and can contain line and block comments. |
| --- | --- | --- |
| *.DAT, LHPM/RIET7/CSRIET | *.DAT, LHPM/RIET7/CSRIET | *.DAT, LHPM/RIET7/CSRIET |
|  | Line 1-4 | Comments |
|  | Line 5 | Start, Step and Finish angle |
|  | Line 6 … | Observed XRD data points |
| GSAS ("std - const", "alt - ralf"), use gsas_format | GSAS ("std - const", "alt - ralf"), use gsas_format | GSAS ("std - const", "alt - ralf"), use gsas_format |
|  | Line 1 | Legend |
|  | Line 2 | Item 3: Number of data points |
|  | Line 3 … | Depending on item10 and item5 |
|  | For item10 = "STD" and item5 = "CONST" xmin = item6/div step =item7/div read(10(i2,F6.0) iww(i),y(i)  i=1, npts sigma(i)=sqr(y(i)/iww(i)) i=1, npts For item10 = "ALT" and item5 = "RALF" xmin = item6/32 step = item7/32 read(4(F8.0,F7.4,F5.4) x(i), y(i), sigma(i)  i=1, npts x(i) = x(i)/32  i=1, npts do i = 1, npts-1      div = x(i+1)-x(i)      y(i) =1000 * y(i)/div      sigma(i) = 1000 * sigma(i)/div end do rk (constant wavelength data): div = 100 rk (time of flight data): 	div = 1 | For item10 = "STD" and item5 = "CONST" xmin = item6/div step =item7/div read(10(i2,F6.0) iww(i),y(i)  i=1, npts sigma(i)=sqr(y(i)/iww(i)) i=1, npts For item10 = "ALT" and item5 = "RALF" xmin = item6/32 step = item7/32 read(4(F8.0,F7.4,F5.4) x(i), y(i), sigma(i)  i=1, npts x(i) = x(i)/32  i=1, npts do i = 1, npts-1      div = x(i+1)-x(i)      y(i) =1000 * y(i)/div      sigma(i) = 1000 * sigma(i)/div end do rk (constant wavelength data): div = 100 rk (time of flight data): 	div = 1 |
| FullProf (INSTRM = 0: free format file), use fullprof_format | FullProf (INSTRM = 0: free format file), use fullprof_format | FullProf (INSTRM = 0: free format file), use fullprof_format |
|  | Line 1 | Start angle, step width, finish angle, comments |
|  | Line 2 … | Observed XRD data points (any number of rows) |
| *.XDD, *.CAL | Line 1 | Optional line for comments |
| *.XDD, *.CAL | Line 2 … | Start, Step and Finish angle |
| *.XDD, *.CAL |  | Next three numbers are unused |
| *.XDD, *.CAL |  | Observed XRD data points |
| *.XY |  | 2 and intensity data values |
| *.XYE |  | 2, intensity and intensity error values. |


### HDF5 file format Copyright notice

Copyright Notice and License Terms for HDF5 (Hierarchical Data Format 5) Software Library and Utilities

HDF5 (Hierarchical Data Format 5) Software Library and Utilities

Copyright 2006-2016 by The HDF Group.

NCSA HDF5 (Hierarchical Data Format 5) Software Library and Utilities

Copyright 1998-2006 by the Board of Trustees of the University of Illinois.

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted for any purpose (including commercial purposes) provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions, and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions, and the following disclaimer in the documentation and/or materials provided with the distribution.

3. Neither the name of The HDF Group nor the name of the University of Illinois may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND...


## Batch mode operation – TC.EXE

The command line program tc.exe provides for batch mode operation. Running tc.exe without arguments displays help information. Running an INP file called PBSO4.INP is as follows:

tc pbso4

Macros can be passed to the command line. Passing a file name to an INP file is as follows:

1)	Create a template.inp file with the required refinement details, this could look like the following:


| xdd FILE etc... |
| --- |

2)	template.inp is fed to tc.exe at the command line; the word FILE (within template.inp) is expanded to whatever the macro on the command line contains; for example:

tc ...\file_directory\template.inp "macro FILE { file.xy }"

The macro called FILE is described on the command line within quotation marks. On running tc.exe the word 'FILE' occurring in tempate.inp is expanded to 'file.xy'. More than one macro can be described on the command line. To process a whole directory of data files, say *.XY file for example, then:

Execute the following DOS command from the file directory:

dir *.xy > ...\main_ta_directory\xy.bat

The xy.bat file will then reside in the main TA directory.

2)	Edit ...\main_ta_directory\xy.bat to look like the following:

tc ...\file_directory\template "macro FILE { file1.xy }"

copy ...\file_directory\template.out ...\file_directory\file1.out

tc ...\file_directory\template.inp "macro FILE { file2.xy }"

copy ...\file_directory\template.out ...\file_directory\file2.out

etc...
