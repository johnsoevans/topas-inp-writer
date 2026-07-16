# Macros and Include files

Macros appearing in INP files are expanded by the pre-processor. The pre-processor comprises two types of directives, global types and types that are invoked on macro expansion; directives begin with the character # and are:

Directives with global scope:

macro $user_defined_macro_name { ... }

#include $user_defined_macro_file_name

#delete_macros { $macros_to_be_deleted }

#define, #undef, #if, #ifdef, #ifndef, #else, #elseif, #endif, #prm

#seed – initializes the random number generator at the pre-processor stage.

Directives invoked on macro expansion:

#m_if, #m_ifarg, #m_elseif, #m_else, #m_endif

#m_code, #m_eqn, #m_code_refine, #m_one_word

#m_argu, #m_first_word, #m_unique_not_refine


## The macro directive

Macros are defined using the macro directive; here's an example:


| macro Cubic(cv) { a cv b = Get(a); c = Get(a); } |
| --- |

Macros can have multiple arguments or none; the Cubic macro above has one argument; here are some example uses of Cubic:


| Cubic(4.50671) Cubic(a_lp 4.50671  min 4.49671  max 4.52671) Cubic(!a_lp 4.50671) |
| --- |

The first instance defines the a, b and c lattice parameters without a parameter name. The second defines the lattice parameters with a name indicating refinement of the a_lp parameter. In the third example, the a_lp parameter is preceded by the ! character. This indicates that the a_lp parameter is not to be refined; it can however be used in equations. The definition of macros need not precede its use. For example, in the segment:


| xdd... Emission_Profile ‘ this is expanded macro Emission_Profile { CuKa2(0.001) } |
| --- |

Even though the Emission_Profile macro has been defined after its use, Emission_Profile is expanded to "CuKa2(0.001)".


### Directives with global scope

#include $user_defined_macro_file_name


| #include "my include file.inc" |
| --- |

inserts the text within "my include file.inc" at the position of the #include directive. The standard macro file Topas.inc is always included by default.

### Macro overloading by argument count

Multiple macros can share the same name as long as they take different numbers of arguments — TOPAS resolves which one to expand at a call site purely by matching the argument count, not by argument type or name. For example, two macros both named `Beq` can coexist, one defined to take 2 arguments and another to take 3; a call site with 2 arguments always expands the 2-argument definition, regardless of what else is defined with that name elsewhere. If a call doesn't match any defined arity for that name, TOPAS reports it at runtime as (verbatim): `Cannot find match for macro Beq` / `Number of arguements 2` (TOPAS's own spelling of "arguments"), followed by `Abnormal program termination.`. When debugging this error, don't assume there's a single definition of the macro to compare against — search every `#include`d `.inc` file for *all* definitions sharing that name and check which argument counts are actually defined and in scope for the call.

Macros can also expand to macro names. For example, the Crystallite_Size macro expands to CS and since CS is a macro then the CS macro is expanded.

#delete_macros { $macros_to_be_deleted }

Macros can be deleted using #delete_macros, for example the following


| #delete_macros { LP_Factor SW ZE } |
| --- |

will delete previously defined macros, irrespective of the number of arguments, with the names LP_Factor, SW and ZE.

#define, #undef, #ifdef, #ifndef, #else, #endif


| #ifdef STANDARD_MACROS  xdd ... #endif |
| --- |

will expand to contain the xdd keyword if STANDARD_MACROS has been previously defined using a #define directive. The following will also expand to contain the xdd keyword if STANDARD_MACROS has not been defined using a #define directive,


| #ifdef !STANDARD_MACROS     #define STANDARD_MACROS    xdd ... #endif |
| --- |

or,


| #ifndef STANDARD_MACROS     #define STANDARD_MACROS    xdd ... #endif |
| --- |

Note the use of the ‘!’ character placed before STANDARD_MACROS which means if STANDARD_MACROS is not defined.


### Pre-processor equations and #prm, #if, #elseif, #out

Pre-processor parameters, called hash parameters, are defined using the #prm directive. #prm’s can be a function of other #prm’s and they can be used in #if, #elseif, #m_if and #m_elseif pre-processor statements. #prm’s are only evaluated at the pre-processor stage of loading INP files (see test_examples\hash_prm.inp); they are therefore unknown to the kernel and are totally separate to parameters defined using prm. Pre-processed output can be found in the TOPAS.LOG file, when running TA.EXE, or TC.LOG when running TC.EXE.


| #prm a = Constant(Rand(0,1)); #out a |
| --- |

will output a random number between 0 and 1 into the pre-processed file at the position of #out. INP files can therefore be manipulated with #prm’s and #if statements with a means of identifying the manipulation carried out. The following:


| macro Ex1(a) { #m_if a == "b"; Yes b #m_elseif a == “c”; Yes c #m_endif } Ex1("b") |
| --- |

expands to:


| Yes b |
| --- |

In the following:


| #prm ran = Constant(Rand(0,1)); #if ran < 0.5; view_structure #endif #if ran < 0.5; view_structure #endif #if ran < 0.5; view_structure #endif |
| --- |

each call to ‘ran’ in the #if statements would return the same value because of the use of Constant. More complicated INP file manipulation is shown in the following:


| #prm space_group_number = 4;  #if And(space_group_number >= 75, space_group_number <= 142);  ... #elseif And(space_group_number >= 16, space_group_number <= 74);  ... #endif |
| --- |


### A macro that repeats text using #out

A macro that repeats and modifies text can be formulated as follows:


| macro Repeat(& n) {    #if (n > 0)       A n       Repeat(n-1)    #endif  } Repeat(10) |
| --- |

Output from the above looks like:

A (10) A ((10)-1) A (((10)-1)-1) A ((((10)-1)-1)-1) A (((((10)-1)-1)-1)-1) A ((((((10)-1)-1)-1)-1)-1) A (((((((10)-1)-1)-1)-1)-1)-1) A ((((((((10)-1)-1)-1)-1)-1)-1)-1) A (((((((((10)-1)-1)-1)-1)-1)-1)-1)-1) A ((((((((((10)-1)-1)-1)-1)-1)-1)-1)-1)-1)

This output may be intended. However, what is often intended is:


| macro Repeat(& n) {    #if (n > 0)       #prm a = n;       #prm am1 = n - 1;       A #out a       Repeat(#out am1)    #endif  } Repeat(10) |
| --- |

and the output is as follows:

A 10  A 9  A 8  A 7  A 6  A 5  A 4  A 3  A 2  A 1

More succinctly again is to use the Numeric macro as follow:


| macro Numeric(& n) {    #prm a = n; #out a } macro Repeat(& n) {    #if (n > 0)       A Numeric(n)       Repeat(Numeric(n-1))    #endif  } Repeat(10) |
| --- |


### Directives invoked on macro expansion

#m_if, #m_ifarg, #m_elseif, #m_else, #m_endif, #m_if, #m_out

These are conditional directives that are invoked on macro expansion. #m_ifarg operates on two statements immediately following its use; the first must refer to a macro argument and the second can be any of the following: #m_code, #m_eqn, #m_code_refine, #m_one_word and “some string”. #m_ifarg evaluates to true according to the rules of Table 22-1.


| Table 22-1. #m_ifarg syntax and meaning. | Table 22-1. #m_ifarg syntax and meaning. |
| --- | --- |
|  | Evaluates to true if the following is true |
| #m_ifarg c #m_code | If the macro argument c has a letter or the character ! as the first character and if it is not an equation. |
| #m_ifarg c #m_eqn | If the macro argument c is an equation. |
| #m_ifarg c #m_code_refine | If the macro argument c has a letter as the first character and if it is not an equation. |
| #m_ifarg c “some_string” | If the macro argument c == “some_string”. |
| #m_ifarg v #m_one_word | If the macro argument v consists of one word. |

#m_argu, #m_first_word, #m_unique_not_refine

These operate on one macro argument with the intention of changing the value of the argument according to the rules of Table 22-2.


| Table 22-2. Directives that change the value of a macro argument. | Table 22-2. Directives that change the value of a macro argument. |
| --- | --- |
| #m_argu c | Changes the macro argument c to a unique parameter name if it has @ as the first character. |
| #m_unique_not_refine c | Changes the macro argument c to a unique parameter name that is not to be refined. |
| #m_first_word $v | Replace the string macro argument $v with the first word occurring in $v. |


### Defining unique parameters within macros

#m_unique $string assigns a unique parameter name to $string within a macro. This allows new unique parameters to be defined within macros whilst avoiding name clashes. In the example:


| macro Some_macro(v) { prm #m_unique a = Cos(Th); : v } |
| --- |

'a' is assigned a unique parameter name and it has the scope of the macro body text. The Robust_Refinement and TCHZ_Peak_Type macros are good examples of its use, where for example, the former is defined as:


| macro Robust_Refinement { ‘ Robust refinement algorithm  prm #m_unique test = Get(r_exp); prm #m_unique N = 1 / test^2; prm #m_unique p0 = 0.40007404; prm #m_unique p1 = -2.5949286; prm #m_unique p2 = 4.3513542; prm #m_unique p3 = -1.7400101; prm #m_unique p4 = 3.6140845e-1; prm #m_unique p5 = -4.45247609e-2; prm #m_unique p6 = 3.5986364e-3; prm #m_unique p7 = -1.8328008e-4; prm #m_unique p8 = 5.7937184e-6; prm #m_unique p9 = -1.035303e-7; prm #m_unique p10 = 7.9903166e-10; prm #m_unique t = (Yobs - Ycalc) / SigmaYobs; weighting = If( t < 0.8, 	N / Max(SigmaYobs^2, 1), 	If( t < 21, N ((((((((((p10 t + p9) t + p8) t + p7) t + p6) t + p5) t + p4) t + p3) t + p2) t + p1) t + p0) / (Yobs - Ycalc)^2, N (2.0131 Ln(t) + 3.9183) / (Yobs - Ycalc)^2)); recal_weighting_on_iter } |
| --- |


### Superfluous parentheses and the '&' Type for macros

The pre-processor is an un-typed language meaning that it knows nothing about the type of text passed as macro arguments. This is flexible but problematic. For example, the following:


| macro divide(a, b) { a / b } prm e = divide(a + b, c - d); |
| --- |

expands to the unintended result of:


| prm e = a + b / c - d; |
| --- |

The writer of the macro could solve this problem by rewriting the macro with parentheses:


| macro divide(a, b) { (a) / (b) } |
| --- |

Alternatively, macro arguments can be prefixed with the & character signalling that the argument is of an equation type, for example:


| macro divide(& a, & b) { a / b } prm e = divide(a + b, c - d); |
| --- |

The program inspects &-type arguments and parentheses are included as needed. This results in the correct expansion of:


| prm e = (a + b) / (c - d); |
| --- |

Even with the use of &-types for arguments, the following:


| macro divide(& a, & b) { a / b } prm e = divide(a + b, c - d)^2; |
| --- |

expands to the unintended:


| prm e = (a + b) / (c - d)^2; |
| --- |

The writer of the macro could again rewrite the macro to include more parentheses:


| macro divide(a, b) {  ((a) / (b))  } |
| --- |

Or define the expansion of the macro itself to have an &-type by placing the & character before the macro name itself:


| macro & divide(& a, & b) {  a / b  } |
| --- |

Expansion of prm e = divide(a + b, c - d)^2 now becomes the intended:


| prm e = ((a + b) / (c - d))^2; |
| --- |

With the use of the &-type, macros such as Ramp defined in Version 4 as:


| macro Ramp(x1, x2, n) { ((x1)+((x2)-(x1)) Mod(Cycle_Iter,(n))/((n)-1)) } |
| --- |

can be written with less parentheses as follows:


| macro & Ramp(& x1,& x2,& n) { x1 + (x2 - x1) Mod(Cycle_Iter, n) / (n-1) } |
| --- |


## Overview

The file Topas.inc is included in INP files by default; it contains commonly used standard macros. The meaning of the macro arguments in Topas.inc can be readily determined from the following conventions:

Arguments called "c" correspond to a parameter name.

Arguments called "v" correspond to a parameter value.

Arguments called "cv" correspond to a parameter name and/or value.

For example, the Cubic(cv) macro requires a value and/or a parameter name as an argument, i.e.


| Cubic(a_lp 10.604)  Cubic(10.604) Cubic(@ 10.604  min 10.59 max 10.61) |
| --- |

Here are examples for the Slit_Width macro:


| SW(@, 0.1) SW(sw, 0.1  min = Val-.02; max = Val+.02;) SW((ap+bp)/cp, 0) ‘ where ap, bp and cp are parameters defined elsewhere |
| --- |


### xdd macros


| RAW(path_no_ext) RAW(path_no_ext, range_num) DAT(path_no_ext) XDD(path_no_ext) XY(path_no_ext, calc_step) XYE(path_ext) SCR(path_no_ext) SHELX_HKL4(path_no_ext) |
| --- |


### Lattice parameters


| Cubic(cv) Tetragonal(a_cv, c_cv) Hexagonal(a_cv, c_cv) Rhombohedral(a_cv, al_cv) |
| --- |


### Emission profile macros


| No_Th_Dependence CuKa1(yminymax) CuK1sharp(yminymax) CuKa2_analyt(yminymax) CuKa2(yminymax) CuKa4_Holzer(yminymax) CuKa5(yminymax) CuKa5_Berger(yminymax) CoKa3(yminymax) CoKa7_Holzer(yminymax) CrKa7_Holzer(yminymax) | FeKa7_Holzer(yminymax) MnKa7_Holzer(yminymax) NiKa5_Holzer(yminymax) MoKa2(yminymax) CuKb4_Holzer(yminymax) CoKb6_Holzer(yminymax) CrKb5_Holzer(yminymax) FeKb4_Holzer(yminymax) MnKb5_Holzer(yminymax) NiKb4_Holzer(yminymax) |
| --- | --- |


### Instrument and instrument convolutions

Radius(rp, rs)

Primary and secondary instrument radii (mm). For most diffractometers rp = rs.

Specimen_Tilt(c, v)

Specimen tilt in mm.

Slit_Width(c, v) or SW(c, v)

Aperture of the receiving slit in the equatorial plane in mm.

Sample_Thickness(dc, dv)

Sample thickness in mm in the direction of the scattering vector.

Divergence(c, v)

Horizontal divergence of the beam in degrees in the equatorial plane.

Variable_Divergence(c, v)

Variable_Divergence_Shape(c, v)

Variable_Divergence_Intensity

Constant illuminated sample length in mm for variable slits (i.e. variable beam divergence). This Variable_Divergence macro applies both a shape and intensity correction.

Simple_Axial_Model(c, v)

Receiving slit length mm for describing peak asymmetry due to axial divergence.

Full_Axial_Model(filament_cv, sample_cv, detector_cv, psol_cv, ssol_cv)

Accurate model for describing peak asymmetry due to axial divergence of the beam.

[filament_cv]: Tube filament length in [mm].

[sample_cv]: Sample length in axial direction in [mm].

[detector_cv]: Length of the detector (= receiving) slit in [mm].

[psol_cv, ssol_cv]: Aperture of the primary and secondary Soller slit in [°].

Finger_et_al(s2, h2)

Finger et al. 1994. model for describing peak asymmetry due to axial divergence.

[s2, h2]: Sample length, receiving slit length.

Tube_Tails(source_width_c, source_width_v, z1_c, z1_v, z2_c, z2_v, 1z2_h_c, z1z2_h_v)

Model for description of tube tails (Bergmann, 2000).

[source_width_c, source_width_v]: Tube filament width in [mm].

[z1_c, z1_v]: Effective width of tube tails in the equatorial plane perpendicular to the X-ray beam - negative z-direction [mm].

[z2_c, z2_v]: Effective width of tube tails in the equatorial plane perpendicular to the X-ray beam - positive z-direction [mm].

[z1_z2_h_c, z1_z2_h_v]: Fractional height of the tube tails relative to the main beam.

UVW(u, uv, v, vv, w, wv)

Cagliotti relation (Cagliotti et al., 1958).

[u, v, w]: Parameter names.

[uv, vv, wv]: Halfwidth value.


### Phase peak_type's

PV_Peak_Type(ha, hav, hb, hbv, hc, hcv, lora, lorav, lorb, lorbv, lorc, lorcv)

TCHZ_Peak_Type(u, uv, v, vv, w, wv, z, zv, x, xv, y, yv)

PVII_Peak_Type(ha, hav, hb, hbv, hc, hcv, ma, mav, mb, mbv, mc, mcv)

Pseudo-Voigt, TCHZ pseudo-Voigt and PearsonVII functions. For the definition of the functions and function parameters refer to section 5.2.


### Quantitative Analysis

Apply_Brindley_Spherical_R_PD( R, PD)

Applies the Brindley correction for quantitative analysis (Brindley, 1945).

MVW(m_v, v_v, w_v)

Returns cell mass, cell volume and weight percent.


### 2Th Corrections

Zero_Error or ZE(c, v)

Zero point error.

Specimen_Displacement(c, v) or SD(c, v)

Specimen displacement error.


### Intensity Corrections

LP_Factor(c, v)

Lorentz and Lorentz-Polarisation factor.

[c, v]: Monochromator angle in [°2]

Values for most common monochromators (Cu radiation) are:

Ge			: 27.3°

Graphite	: 26.4°

Quartz		: 26.6°

Lorentz_Factor

Lorentz factor for fixed wavelength neutron data.

Surface_Roughness_Pitschke_et_al(a1c, a1v, a2c, a2v)

Surface_Roughness_Suortti(a1c, a1v, a2c, a2v)

Suortti and Pitschke et al. intensity corrections each with two parameters a1 and a2.

Preferred_Orientation(c, v, ang, hkl) or PO(c, v, ang, hkl)

Preferred orientation correction based on March (1932).

[c, v]: March parameter value.

[ang, hkl]: Lattice direction.

**The March-Dollase ratio parameter and the texture (J) index** (not in the Technical Reference manual — sourced from Dinnebier, Leineweber & Evans, 2018, §2.3.7): the refined March parameter is a ratio between the correction factor applied to crystallites oriented with the chosen `hkl` perpendicular to the preferred-orientation axis versus those oriented parallel to it — a value of 1 means no preferred orientation (random powder), values below 1 describe increasing platy/needle-like alignment. Beyond looking at the raw parameter value, the standard scalar severity metric used in the literature to summarize "how much preferred orientation is present" (regardless of which model — March-Dollase or spherical harmonics — was used to correct for it) is the **texture index J**, always ≥1, with J=1 meaning a perfectly random powder and larger J meaning more severe texture; this is the number worth quoting/comparing across refinements or samples, rather than the raw March ratio or spherical-harmonic coefficients directly, which aren't directly comparable to each other.

PO_Two_Directions(c1, v1, ang1, hkl1, c2, v2, ang2, hkl2,  w1c, w1v)

Preferred orientation correction based on March (1932) considering two preferred orientation directions.

[c1, v1]: March parameter value for the first preferred orientation direction.

[ang1, hkl1]: Parameter name and lattice plane for the first preferred orientation direction.

[c2, v2]: March parameter value for the second preferred orientation direction.

[ang2, hkl2]: Lattice direction for the second preferred orientation direction.

[w1c, w1v]: Fraction of crystals oriented into first preferred orientation direction.

PO_Spherical_Harmonics(sh, order)

Preferred orientation correction based on spherical harmonics according to Järvinen (1993).

[(sh, order)]: Parameter name, spherical harmonics order.


### Bondlength penalty functions

Anti_Bump(ton, s1, s2, ro, wby)

AI_Anti_Bump(s1, s2, ro, wby, num_cycle_iters), AI_Anti_Bump(s1, s2, ro, wby)

Applies a penalty function as a function of the distance between atoms. The closer the atoms are the higher the penalty is.

[ton]: Sets to_N of box_interaction.

[s1, s2]: Sites.

[ro]: Distance.

[wby]: Relative weighting given to the penalty function.

For more details refer to box_interaction and ai_anti_bump.

Parabola_N(n1, n2, s1, s2, ro, wby)

Applies a penalty function as a function of the distance between atoms. The closer the atoms are the higher the penalty is.

[n1]: The closest n1 number of atoms of type s2 is soft constrained to a distance ro away from s1 .

[n2]: The closest n2 number of atoms of type s2 (excluding the closest n1 number of atoms of type s2) is repelled from s1, for distances between s1 and s2 less than ro.

[s1, s2]: Sites.

[ro]: Distance.

[wby]: Relative weighting given to the penalty function.

Grs_Interaction(s1, s2, wqi, wqj, c, ro, n)

Penalty function applying the GRS series according to Coelho & Cheary (1997).

[s1, s2]: Sites.

[wqi, wqj]: Valence charge of the atoms.

[c]: Name of the GRS.

[ro]: Distance.

[n]: The exponent of the repulsion part of the Lennard-Jones potential.

For more details refer to grs_interaction.

Grs_No_Repulsion(s1, s2, wqi, wqj, c)

Used for calculating the Madelung constants.

[s1, s2]: Sites.

[wqi, wqj]: Valence charge of the atoms.

[c]: Name of the GRS.

Grs_BornMayer(s1, s2, wqi, wqj, c, ro, b)

Uses the GRS series with a Born-Mayer equation for the repulsion term.

[s1, s2]: Sites.

[wqi, wqj]: Valence charge of the atoms.

[c]: Name of the GRS.

[ro]: Mean distance.

[b]: b-constant for the repulsion part of the Born-Mayer potential.

Distance_Restrain(sites, t, t_calc, tol, wscale)

Angle_Restrain(sites, t, t_calc, tol, wscale)

Flatten(sites, t_calc, tol, wscale)

Distance_Restrain_Keep_Within(sites, r, wby, num_cycle_iters)

Distance_Restrain_Keep_Out(sites, r, wby, num_cycle_iters)

Applies penalties restraining distances and angles between sites. 'sites' must comprise two sites for the distance restraints and three for the angle restraints. For Flatten, 'sites' must contain more than three sites. wby is a scaling constant applied to the penalty.

Keep_Atom_Within_Box(size).

Applies min/max constraints such that the present site cannot more outside of a box with a length of 2*size.


### Reporting macros

Create_2Th_Ip_file(file)

Creates a file with positions (2) and intensities.

Create_d_Ip_file(file)

Creates a file with positions (d) and intensities.

Create_hklm_d_Th2_Ip_file(file)

Creates a file with the following information for each peak: h, k, l, multiplicity, positions d and 2 and intensities.

Out_Yobs_Ycalc_and_Difference(file)

Outputs the x-axis, Yobs, Ycalc and difference.

Out_X_Yobs(file), Out_X_Ycalc(file), Out_X_Difference(file)

Outputs the x-axis, Yobs, Ycalc and difference to files.

Out_F2_Details(file), Out_A01_A11_B01_B11(file)

Outputs structure factor details, see section 20.9.2.

Out_FCF(file)

Outputs a CIF file representation of structure factor details suitable for generating Fourier maps using ShelX.

Out_CIF_STR(file)

Outputs structure details in CIF format.

Absorption_With_Sample_Thickness_mm_Shape_Intensity(u, uv, d, dv)

Corrects the peak intensity for absorption effects.

[u, uv]: Parameter name, absorption coefficient in cm-1.

[d, dv]: Parameter name, sample thickness in [mm].

CS_L(c,v) or Crystallite_Size(c, v) or CS(c, v)

Applies a Lorentzian convolution with a FWHM that varies according to the relation lor_fwhm = 0.1 Rad Lam / (c Cos(Th)).

[c, v]: Parameter name, crystallite size in [nm].

**Physical background** (not in the Technical Reference manual — sourced from Dinnebier, Leineweber & Evans, 2018, §1.3/§2.5): this `1/Cos(Th)` size-broadening dependence is the Scherrer relation. Its physical origin is the same finite-crystal-size argument behind the Laue interference function: a finite crystallite means the interference condition isn't satisfied by exactly one direction in reciprocal space but by a small volume around it, and that volume's angular extent scales inversely with crystallite dimension — smaller crystals give broader peaks. The refined `c` here is a *volume-weighted mean column height*, not a literal particle diameter — the two coincide only for a specific idealized shape/shape-constant assumption (the FWHM-based Scherrer shape constant `kf` defaults to 0.89, appropriate for a sphere; see `LVol_FWHM_CS_G_L` below for where this constant is actually applied). A common debugging mistake: comparing a `CS_L`/`CS_G`-derived size directly against an independent measurement (e.g. TEM/SEM particle size) without accounting for (a) the IRF not having been fully subtracted first, (b) `fwhm` being in radians in the underlying formula despite being entered/reported in degrees elsewhere, or (c) the shape-constant mismatch above — any of these can make a Scherrer-derived size look "wrong" when the refinement itself is fine.

CS_G(c, v)

Applies a Gaussian convolution with a FWHM that varies according to the relation


| gauss_fwhm = 0.1 Rad Lam / (c Cos(Th)); |
| --- |

[c, v]: Parameter name, crystallite size in [nm].

Strain_L(c, v) or Microstrain(c, v) or MS(c, v)

Applies a Lorentzian convolution with a FWHM that varies according to the relation lor_fwhm = c Tan(Th).

Strain_G(c, v)

Applies a Gaussian convolution with a FWHM that varies according to the relation gauss_fwhm = c Tan(Th).

LVol_FWHM_CS_G_L(k, lvol, kf, lvolf, csgc, csgv, cslc, cslv)

Calculates FWHM and IB (integral breadth) based volume-weighted column heights (LVol). For details refer to section 20.13.

[k, lvol]: shape factor (fixed to 1), integral breadth based LVol.

[kf, lvolf]: shape factor (defaults to 0.89), FWHM based LVol.

[csgc, csgv]: Parameter name, Gaussian component.

[cslc, cslv]: Parameter name, Lorentzian component.

**`Stephens_triclinic`, `Stephens_monoclinic`, `Stephens_orthorhombic`, `Stephens_tetragonal_low`, `Stephens_tetragonal_high`, `Stephens_trigonal_low`, `Stephens_trigonal_high`, `Stephens_trigonal_high_2`, `Stephens_hexagonal`, `Stephens_cubic`** — this family is not documented in the TOPAS Technical Reference manual at all; it's sourced from Dinnebier, Leineweber & Evans, *Rietveld Refinement: Practical Powder Diffraction Pattern Analysis using TOPAS* (2018), §4.3.2, which covers the underlying theory in more depth than can be reproduced here.

One macro exists per Laue class (trigonal macros assume the hexagonal cell setting; there is no ready-made macro for rhombohedral cells, though the symmetry-invariant polynomial approach still applies and can be written out by hand). Each implements the anisotropic-microstrain model of Stephens (1999) — a generalization of Popa (1998)/Rodriguez-Carvajal et al. (1991) — in which the microstrain-broadening contribution to a reflection's fwhm is not simply `Strain_L`/`Strain_G`'s single isotropic constant times `Tan(Th)`, but instead a **direction-dependent quantity that varies from reflection to reflection according to the Miller indices H, K, L**, because real microstrain distributions are frequently anisotropic (e.g. a material strained much more along one crystallographic axis than another).

Calling convention (illustrated for the tetragonal-high Laue class, 4/mmm, which needs 4 sHKL coefficients):
```
Stephens_tetragonal_high(zeta, 1.0, s400, 336.5, s004, 10.4, s220, -670.0, s202, 25.5)
```
The first pair (`zeta`, its value) is the usual Gaussian/Lorentzian mixing parameter (zeta=0 pure Gaussian, zeta=1 pure Lorentzian — same convention as elsewhere in TOPAS). Each subsequent pair is one **sHKL parameter** (a refinable coefficient name plus starting value) — the number of sHKL parameters needed is fixed by the Laue class (4/mmm needs 4: s400, s004, s220, s202; other Laue classes need a different number, since the polynomial must be invariant under that Laue class's own symmetry). Internally, the macro builds a 4th-order symmetry-invariant polynomial in H, K, L (called `mhkl`) from the sHKL coefficients — for 4/mmm:
```
mhkl = s400 (H^4 + K^4) + s004 L^4 + s220 H^2 K^2 + s202 (H^2 L^2 + K^2 L^2)
```
and applies broadening as `pp = D_spacing^2 * Sqrt(Max(mhkl,0)) Tan(Th) 0.0018/Pi`, split between `gauss_fwhm = pp (1-zeta)` and `lor_fwhm = pp zeta` — i.e. the same physical `Tan(Th)`-scaling as ordinary isotropic microstrain, just multiplied by an hkl-dependent factor instead of a constant.

**Practical notes:**
- `mhkl` should mathematically be ≥0 for every H,K,L actually present in the pattern (it's a variance-like quantity) — the `Max(mhkl,0)` guard is a pragmatic way to avoid a domain error during refinement rather than a fix for the underlying issue; if refined sHKL values imply `mhkl<0` for some real reflection, that's a sign the model or starting values need attention, not something to paper over silently.
- The direction dependence of the resulting strain broadening is usually visualized as a 3D polar plot of `fwhm_eps(hkl)` via TOPAS's `normals_plot` keyword (see `references/20-miscellaneous.md`) — this is the standard way to sanity-check whether a refined anisotropic-strain model looks physically reasonable (e.g. correctly near-zero along a direction known from other evidence to be nearly strain-free) rather than just checking Rwp improved.
- An alternative, dimensionless Cartesian-tensor parametrization of the same physical model (using `zE_ijpq` parameters instead of `sHKL`) exists specifically because isotropy of the strain broadening is not easy to recognize directly from sHKL coefficient values (Leineweber 2006, 2011) — the two parametrizations are mathematically equivalent (one-to-one convertible) and give identical fit quality, so the choice is about interpretability, not accuracy.
- `spherical_harmonics_hkl` (see `references/20-miscellaneous.md`) can alternatively describe anisotropic broadening and is more general, but the Stephens macros are the standard, ready-made choice for this specific well-established phenomenological model.

References: Stephens, P.W. (1999). Phenomenological model of anisotropic peak broadening in powder diffraction. *J. Appl. Cryst.* 32, 281–289. Popa, N.C. (1998). *J. Appl. Cryst.* 31, 176–180. Rodriguez-Carvajal, J. et al. (1991). *J. Phys. Condens. Matter* 3, 3215–3234. Leineweber, A. (2006). Anisotropic diffraction-line broadening due to microstrain distribution: parametrization opportunities. *J. Appl. Cryst.* 39, 509–518. Leineweber, A. (2011). Understanding anisotropic microstrain broadening in Rietveld refinement. *Z. Kristallogr.* 226, 905–923.


### Neutron TOF

TOF_XYE(path, calc_step), TOF_GSAS(path, calc_step)

Includes the neutron_data keyword and the calculation step size.

TOF_LAM(w_ymin_on_ymax)

Defines a simple emission profile suitable for TOF data

TOF_x_axis_calibration(t0, t0v, t1, t1v, t2, t2v)

Writes the pk_xo equation in terms of the three calibration constants t0, t1, t2 converting d-spacing to x-axis space.

TOF_Exponential(a0, a0v, a1, a1v, wexp, t1, lr)

An exponential convolution applied to the TOF peaks - see example tof_bank2_1.inp.

TOF_CS_L(c, v, t1), TOF_CS_G(c, v, t1)

Lorentzian and Gaussian components for crystallite size. t1 is the calibration constant appearing in the argument of the macro TOF_x_axis_calibration.

TOF_PV(fwhm, fwhmv, lor, lorv, t1)

A pseudo-Voigt used to describe the instrumental broadening t1 is the calibration constant appearing in the argument of the macro TOF_x_axis_calibration, see examples tof_balzar_br1.inp and tof_balzar_sh1.inp.


### Miscalleneous

Temperature_Regime

Defines a temperature regime. See the temperature keyword.

STR(sg)

Signals the start of structure information with a space group of sg.

Exclude

Defines excluded regions. See exclude.

Decompose(diff_toll)

Decompose a diffraction pattern comprising data points at peak positions only. Data points closer than diff_toll to another data point are not included. Decompose also sets x_calculation_step to the value of diff_toll.

ADPs_Keep_PD

Mixture_LAC_1_on_cm(mlac)

Phase_Density_g_on_cm3(pd)

Phase_LAC_1_on_cm(u)

Gauss(xo, fwhm), Lorentzian(xo, fwhm)

An equation defines a unit area Gaussian or Lorentzian with a position of xo and a FWHM of fwhm
