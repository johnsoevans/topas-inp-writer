# Parameters


## When is a parameter refined

A parameter is flagged for refinement by giving it a name. The first character can be an upper or lower-case letter. Subsequent characters can include the underscore character '_' and the numbers 0 through 9. For example:


| site Zr x 0 y 0 z 0 occ Zr+4 1 beq b1 0.5 |
| --- |

Here b1 is the name given to the beq parameter. No restrictions are placed on the length of parameter names. The character ! placed before b1, as in !b1, signals that b1 is not to be refined, for example:


| site Zr x 0 y 0 z 0 occ Zr+4 1 beq !b1 0.5 |
| --- |

A parameter can also be flagged for refinement by placing the @ character at the start of its name. Internally the parameter is given a unique name and treated as an independent parameter. The b1 text in the following is ignored:


| site Zr x 0 y 0 z 0 occ Zr+4 1 beq @ 0.5 or,	site Zr x 0 y 0 z 0 occ Zr+4 1 beq @b1 0.5 |
| --- |


## User defined parameters - the prm/local keywords

The [prm|local E] keywords defines a new parameter. For example:


| prm b1 0.2 ‘ b1 is the name given to this parameter             ‘ 0.2 is the initial value  site Zr x 0 y 0 z 0 occ Zr+4 0.5  beq = 0.5 + b1;                     occ Ti+4 0.5  beq = 0.3 + b1; |
| --- |

Here b1 is a new parameter that will be refined; this example demonstrates adding a constant to a set of beq's. Note the use of the '=' sign after the beq keyword; this indicates that the parameter is in the form of an equation. In the following example, b1 is used but not refined:


| prm !b1 0.2 site Zr x 0 y 0 z 0 occ Zr+4 0.5  beq = 0.5 + b1;                     occ Ti+4 0.5  beq = 0.3 + b1; |
| --- |


## Parameter attributes

The following optional parameter attributes can be assigned to a parameter:

[min !E]  [max !E]  [del !E]  [update !E]  [stop_when !E]  [val_on_continue !E] [_rem !E]

_rem is described in section 15.6. Attributes are equations and cannot have a parameter name; they can however be a function of other parameter names. The min and max attributes can be used to limit parameter values during refinement, for example:


| prm a 0.1 min 0 max = 10; prm b 0.2 min = a; max = 10; |
| --- |

Here b is constrained to within the range 0.1 and 10. Limits are effective in refinement stabilization. del is used for calculating numerical derivatives with respect to the calculated pattern; typically, internal default del values are adequate in most circumstances. Parameter values are updated at the end of an iteration as follows:

new_Val = old_Val + Change

When update is defined then the following is used:

new_Val = “update equation”

update can also be a function of the reserved parameter names Change and Val, and does not negate min and max. stop_when is a conditional stopping criterion: convergence is determined when stop_when evaluates to non-zero for all defined stop_when attributes and the chi2_convergence_criteria condition has been met. val_on_continue is evaluated when continue_after_convergence is defined, and provides a means of changing parameter values after convergence:

new_Val = val_on_continue

Here are example attribute equations as applied to the x parameter:


| x @ 0.1234  min       = Val - 0.2; max       = Val + 0.2; update    = Val + Rand(0, 1) Change; stop_when = Abs(Change) < 0.000001; |
| --- |


## Parameter constraints

Equations can be a function of parameter names; this provides a mechanism for introducing linear and non-linear constraints, for example:


| site Zr x 0 y 0 z 0 occ Zr+4 zr 1    beq 0.5                     occ Ti+4 = 1-zr; beq 0.3 |
| --- |

Here the zr parameter is used in the equation "= 1-zr;"; this equation defines the Ti+4 site occupancy. Note, equations start with an equal sign and end in a semicolon. Limiting zr with min/max can be performed as follows:


| site Zr x 0 y 0 z 0 occ Zr+4 zr 1 min 0 max 1  beq 0.5                     occ Ti+4 = 1 - zr;         beq 0.3 |
| --- |

Here zr will be constrained to within 0 and 1. An example constraining the lattice parameters a, b, c to the same value as required for a cubic lattice is as follows:


| a lp 5.4031	b lp 5.4031	c lp 5.4031 |
| --- |

Parameters with the same name must have the same value — an exception is thrown if the lp parameters above were defined with differing values. Another way to constrain three lattice parameters to the same value is to define lp once as an equation:


| a lp 5.4031 	b = lp;		c = lp; |
| --- |

More general again is the use of the Get function as used in the Cubic macro:


| a @ 5.4031 	b = Get(a); 	c = Get(a); |
| --- |

Here the constraints are formulated without the need for a parameter name.


## Try and use parameter attributes

Using prm to define the lattice parameter, as in a bare `prm` plus assignment equation, is not preferred. Subject-specific parameters, not just lattice parameters, carry default attributes such as min/max, and these attributes are lost when prm is used. Where the use of prm is unavoidable, it should be defined with min/max attributes.


## The local keyword

The local keyword is used for defining parameters as local to the top, xdd or phase level; local can simplify complex INP files. The following code fragment:


| xdd		local a 1 xdd		local a 2 |
| --- |

has two 'a' parameters; one dependent on the first xdd and the other dependent on the second xdd. Internally two independent parameters are generated, one for each of the 'a' parameters; this is necessary as the parameters require separate positions in the A matrix for minimization, correlation matrix, errors etc... In the code fragment:


| local a 1              ‘ top level xdd gauss_fwhm = a;    ‘ 1st xdd xdd gauss_fwhm = a;    ‘ 2nd xdd       local a 2        ‘ xdd level |
| --- |

The first xdd is convolved with a Gaussian of FWHM 1 and the second with a Gaussian of FWHM 2. In other words, the first gauss_fwhm equation uses the top-level ‘a’ parameter, and the second uses the ‘a’ parameter defined in the second xdd — analogous to scoping rules in c. The following is invalid because b1 is defined twice in incompatible ways:


| xdd		local a 1	prm b1 = a; xdd		local a 2	prm b1 = a; |
| --- |

The following comprises 4 separate parameters and is valid:


| xdd		local a 1	local b1 = a; xdd		local a 2	local b1 = a; |
| --- |


## Defining local parameters using $

The $ character can also be used to signal that a parameter is local. The following two lines are similar but not entirely equivalent:


| xdd … local sc 0.01 min 1e-10 scale = sc; xdd … scale $sc 0.01 |
| --- |

Using $ retains the default min, max, and del attributes of the scale parameter. It can also be used with the prm keyword to define a parameter as local. The following two lines are equivalent:


| prm $cs 100 local cs 100 |
| --- |

Use of $ also simplifies the writing of macros when using “for { }” loops. For example, the following:


| for strs { CS_L(@, 100) } |
| --- |

expands to:


| for strs { prm m67cff550_1 100 min .3 max = Min(Val 2 + .3, 10000);    lor_fwhm = 0.1 57.2957795130823 Lam / (Cos(Th) (m67cff550_1)); } |
| --- |

Here there is only one CS_L parameter, named m67cff550_1, shared across all strs in the loop. To instead assign a unique CS_L to each str:


| for strs { CS_L($cs, 100) } |
| --- |

which expands to:


| for strs { prm $cs 100 min .3 max = Min(Val 2 + .3, 10000);    lor_fwhm = 0.1 57.2957795130823 Lam / (Cos(Th) ($cs)); } |
| --- |

Here each str has a unique cs parameter due to the $ character. The drawback is that only one cs value is written to the OUT file — the rest are lost. This can be remedied with the load_save_locals keyword.


## Reporting on equation values

The value of the equation can be obtained by placing " : 0" after the equation, for example:


| occ Ti+4 = 1-zr; : 0 |
| --- |

After refinement, the '0' is replaced by the value of the equation. The associated error is also reported when do_errors is defined.


## Naming of equations

Equations can be given a parameter name, for example:


| prm !a1 = a2 + a3/2; : 0 |
| --- |

Here a1 represents the equation a2 + a3/2. If this evaluates to a constant, a1 is an independent parameter and will be refined unless preceded by !; otherwise it is treated as a dependent parameter. The following equation is valid without a parameter name — its value and error are reported on termination of refinement.


| prm = 2 a1^2 + 3; : 0 |
| --- |

Equations in general are not evaluated sequentially, the following:


| prm a2 = 2 a1; : 0 prm a1 = 3; |
| --- |

gives on termination of refinement:


| prm a2 = 2 a1; : 6 prm a1 = 3; |
| --- |

Parameters with the same name must have identical values or equations. This allows for non-sequential evaluation of parameters. The following leads to redefinition errors:


| prm a1 = 2;     prm a1 = 3;  ‘ redefinition error prm b1 = 2 b3;  prm b1 = b3; ‘ redefinition error |
| --- |


## existing_prm

[existing_prm E]...

Evaluated sequentially and allows for the modification of an existing prm/local parameters, see for example the macro K_Factor_WP in Topas.inc. The following:


| local a 1 existing_prm a += 1; existing_prm a /= 2; existing_prm a = 3 (a + 1); prm = a; : 0 |
| --- |

gives:


| prm = a; : 6.00000 |
| --- |

Allowed operators for existing_prm are +=, -=, *-, /= and ^=.


## String, Concat, To_String and To_Prm functions

String assigns a string attribute to text that would otherwise be a parameter. To_String evaluates a parameter and converts it to a string. To_Prm converts a string to a parameter name. Together these macros provide flexibility in constructing INP files. Concat(a, b, c, …) concatenates strings; its arguments like those of To_Prm can be parameters or strings, with parameter values automatically converted to strings. For example, the following are all equivalent:


| prm abc = 7; prm  = To_Prm(a, b, c); :  7 	 prm  = To_Prm(a, "b", "c"); :  7 	 prm  = To_Prm(Concat(“a”, "b", "c")); :  7  prm  = To_Prm(Concat(a, "b", "c")); :  7 	 prm  = To_Prm(String(abc)); :  7 	 prm  = To_Prm("abc"); :  7 |
| --- |


## Starting a parameter with a random number

The pre-processor #out command (see section 22.1.2) can be used to start parameters at random values, for example:


| #prm a_start = Rand(5.4, 5.6); a @ #out a_start |
| --- |

This is pre-processed to (as seen in TOPAS.LOG):


| a @ 5.58537511 |
| --- |


## Using the % equation character to define a parameter name

A parameter name can be defined using a % equation as seen in the following:


| Create_XDDs(3) prm i 1 for xdds { xdd_file = Concat("ceo2-", i, ".xdd") … str site  Ce1                       occ Ce+4  1 beq %Concat("bCe", i); 0.2 site  O1  x 0.25 y 0.25 z 0.25  occ O-2   1 beq %Concat("bO", i);  0.4 existing_prm i += 1; … } |
| --- |

The above loads three xdds ceo2-1.xdd, ceo2-2.xdd and ceo2-3.xdd. Each has a structure with two beq parameters created using the %Concat sequence; the names created are bCe1, bO1, bCe2, bO2, bCe3 and bO3. These can be used in equations as normal. If the bCe_ parameters were the same as the bO_ parameters then the following could be used:


| site  Ce1                       occ Ce+4  1 beq %Concat("b1", i); 0.2       site  O1  x 0.25 y 0.25 z 0.25  occ O-2   1 beq %Concat("b1", i); 0.2 |
| --- |

or, using To_Prm:


| site  Ce1                       occ Ce+4  1 beq %Concat("b1", i); 0.2       site  O1  x 0.25 y 0.25 z 0.25  occ O-2   1 beq = To_Prm(Concat("b1", i)); |
| --- |


## dummy and dummy_prm keywords

dummy reads a word from the input stream; dummy_prm is similar but reads parameter dependent text. For example, the following purple text is loaded by dummy_prm and ignored by the Kernel.


| load xo dummy_prm I     {        10   = 1/Max(0.00023, 0.0001); min 10 max = Val 2; @ 100       ... |
| --- |


## Parameter errors and correlation matrix

When do_errors is defined, errors for independent parameters and the correlation matrix are generated at the end of refinement, see also section 4.9. Errors are appended to parameter values as follows:


| a lp 5.4031_0.0012 |
| --- |

Here the error in lp is 0.0012. The correlation matrix is identified by C_matrix_normalized; it is appended to the OUT file if it does not already exist, or updated if it does exist.

Errors for dependent parameters are also evaluated. Consider the independent parameters of a,b,c and a dependent parameter D which is a function of a, b and c; or

D = f(a, b, c)

The error in D is given by:

Error(D)^2 = GOF (dD_da^2 Cov(a,a) + dD_db^2 Cov(b,b) + dD_dc^2 Cov(c,c) +

2 dD_da dD_db Cov(a,b) + 2 dD_da dD_dc Cov(a,c) + 2 dD_db dD_dc Cov(b,c))


## Default lattice angle value: al/be/ga default to 90 degrees if omitted

Confirmed directly by the user (TOPAS-Academic's author): if `al`, `be`, or `ga` is left out of a `str` entirely -- not given any value, refined or fixed -- TOPAS defaults it to 90 degrees. This holds regardless of `space_group`, including low-symmetry settings like `P1`/`P_1` where the space group itself imposes no metric constraint on the angles. There is therefore no need to explicitly write `al 90 be 90 ga 90` for a cell that happens to be orthogonal (cubic, tetragonal, orthorhombic -- or a P1 cell that is numerically orthogonal even though the space group doesn't require it) -- simply omit the angle keywords and let the default apply. This is a distinct fact from the min/max *refinement bound* defaults in Table 2-1 below (which only matter once an angle parameter is actually declared and refined); it concerns the *starting value* used when the keyword is absent altogether.

## Default parameter limits and LIMIT_MIN / LIMIT_MAX

Parameters with internal default min/max attributes are listed in Table 2-1. These limits serve two purposes: they avoid invalid numerical operations and stabilize refinement by directing minimization towards lower  values. Hard limits are avoided where possible; instead parameter values move within a range during a iteration. User defined min/max limits override the defaults and prm/local parameters should be defined with them. Much of this functionality is realized through the standard macros defined in Topas.inc – an important file to study - almost all of which include min/max limits. For example, the CS_L macro defines a crystallite size parameter with a min/max of 0.3 and 10000 nm respectively. On termination, independent parameters that refined close to their limits are flagged with "_LIMIT_MIN_#" or "_LIMIT_MAX_#" appended to the parameter value, where '#' corresponds to the limiting value. These warnings can be suppressed with no_LIMIT_warnings.


| Table 2-1.  Default parameter limits. | Table 2-1.  Default parameter limits. | Table 2-1.  Default parameter limits. |
| --- | --- | --- |
| Parameter | min | max |
| la | 1e-5 | 2 Val + 0.1 |
| lo | Max(0.01, Val-0.01) | Min(100, Val+0.01) |
| lh, lg | 0.001 | 5 |
| a, b, c | Max(1.5, 0.995 Val - 0.05) | 1.005 Val + 0.05 |
| al, be, ga | Max(1.5, Val - 0.2) | Val + 0.2 |
| scale | 1e-11 |  |
| sh_Cij_prm | -2 Abs(Val) - 0.1 | 2 Abs(Val) + 0.1 |
| occ | 0 | 2 Val + 1 |
| beq | Max(-10, Val-10) | Min(20, Val+10) |
| pv_fwhm, h1, h2, spv_h1, spv_h2 | 1e-6 | 2 Val + 20 Peak_Calculation_Step |
| pv_lor, spv_l1, spv_l2 | 0 | 1 |
| m1, m2 | 0.75 | 30 |
| d | 1e-6 |  |
| xo | Max(X1, Val - 40 Peak_Calculation_Step) | Min(X2, Val + 40 Peak_Calculation_Step) |
| I | 1e-11 |  |
| z_matrix distance | Max(0.5, Val .5) | 2 Val |
| z_matrix angles | Val – 90 | Val + 90 |
| rotate | Val – 180 | Val + 180 |
| x, ta, qa, ua | Val - 1/Get(a) | Val + 1/Get(a) |
| y, tb, qb, ub | Val - 1/Get(b) | Val + 1/Get(b) |
| z, tc, qc, uc | Val - 1/Get(c) | Val + 1/Get(c) |
| u11, u22, u33 | Val If(Val < 0, 2, 0.5) - 0.05 | Val If(Val < 0,0.5,2) + 0.05 |
| u12, u13, u23 | Val If(Val < 0, 2, 0.5) - 0.025 | Val If(Val < 0,0.5,2) + 0.025 |
| filament_length | 0.0001 | 2 Val + 1 |
| sample_length, receiving_slit_length, primary_soller_angle, secondary_soller_angle | sample_length, receiving_slit_length, primary_soller_angle, secondary_soller_angle | sample_length, receiving_slit_length, primary_soller_angle, secondary_soller_angle |

**Interpreting a refined `beq`/ADP that looks physically wrong** (not in the Technical Reference manual — sourced from Dinnebier, Leineweber & Evans, 2018, §2.2.3): a displacement parameter refining to a negative value, or to an implausibly large one, is a common symptom worth a specific debugging heuristic rather than just widening `min`/`max` further. Typical "normal" ranges are roughly 0.1–1.5 Å² (as `Biso`; TOPAS's `beq` is on the same physical scale) for simple inorganic structures, up to a few Å² for flexible coordination compounds/organics — values well outside that range usually mean `beq` is silently absorbing some *other*, unmodeled systematic error (uncorrected absorption, surface roughness, an incorrectly assigned/occupied atom, overspill, a geometry that violates the flat-plate infinite-thickness assumption used by the standard 2θ-dependent intensity corrections) rather than reflecting genuine atomic motion. Treat an anomalous `beq` as a diagnostic pointing at a missing correction elsewhere in the model, not just a parameter to bound more tightly. For anisotropic displacement parameters, the three inequalities that keep a U_ij tensor positive-definite (physically meaningful — a real thermal ellipsoid can't have "negative" extent along some direction) are what `ADPs_Keep_PD` (see `references/06-macros-and-include-files.md`) enforces.


## Reserved parameter names

and Table 2-4 lists reserved parameter names that are internally updated as needed; Table 2-3 details dependences for certain reserved parameter names. An exception is thrown when a reserved parameter name is used for a user-defined parameter name. The following example uses the reserved parameter names Yobs, Ycalc and X for weighting:


| weighting = Abs(Yobs-Ycalc) / (Max(Yobs+Ycalc,1) Max(Yobs,1) Sin(X Deg / 2)); |
| --- |


| Table 2-2. Reserved parameter names. | Table 2-2. Reserved parameter names. | Table 2-2. Reserved parameter names. |
| --- | --- | --- |
| Name | Description | Description |
| A_star, B_star, C_star | Corresponds to the lengths of the reciprocal lattice vectors. | Corresponds to the lengths of the reciprocal lattice vectors. |
| Change | Returns the change in a parameter at the end of a refinement iteration. Change can only appear in the equations update and stop_when. | Returns the change in a parameter at the end of a refinement iteration. Change can only appear in the equations update and stop_when. |
| D_spacing | Corresponds to the d-spacing of phase peaks in Å. | Corresponds to the d-spacing of phase peaks in Å. |
| H, K, L, M | hkl and multiplicity of phase peaks. | hkl and multiplicity of phase peaks. |
| Iter, Cycle, Cycle_Iter | Returns the current iteration, the current cycle and the current iteration within the current cycle respectively. Can be used in all equations. | Returns the current iteration, the current cycle and the current iteration within the current cycle respectively. Can be used in all equations. |
| Lam | Corresponds to the wavelength lo of the emission profile line with the largest la value. | Corresponds to the wavelength lo of the emission profile line with the largest la value. |
| Lpa, Lpb, Lpc | Corresponds to the a, b and c lattice parameters respectively. | Corresponds to the a, b and c lattice parameters respectively. |
| Mi | An iterator used for multiplicities. See the PO macro of Topas.inc for an example of its use. | An iterator used for multiplicities. See the PO macro of Topas.inc for an example of its use. |
| Peak_Calculation_Step | Return the calculation step for phase peaks, see x_calculation_step. | Return the calculation step for phase peaks, see x_calculation_step. |
| QR_Removed,  QR_Num_Times_Consecutively_Small | QR_Removed,  QR_Num_Times_Consecutively_Small | Can be used in the quick_refine_remove equation. |
| R, Ri | The distance between two sites R and an iterator Ri. Used in the equation part of atomic_interaction, box_interaction and grs_interaction. | The distance between two sites R and an iterator Ri. Used in the equation part of atomic_interaction, box_interaction and grs_interaction. |
| Rp, Rs | Primary and secondary diffractometer radius respectively. | Primary and secondary diffractometer radius respectively. |
| T | Corresponds to the current temperature, can be used in all equations. | Corresponds to the current temperature, can be used in all equations. |
| Th | Corresponds to the Bragg angle (in radians) of hkl peaks. | Corresponds to the Bragg angle (in radians) of hkl peaks. |
| X, X1, X2 | Corresponds to the measured x-axis, the start and the end of the x-axis respectively. X is used in fit_obj's equations and the weighting equation. X1 and X2 can be used in all xdd dependent equation. | Corresponds to the measured x-axis, the start and the end of the x-axis respectively. X is used in fit_obj's equations and the weighting equation. X1 and X2 can be used in all xdd dependent equation. |
| Xo | Corresponds to the current peak position; this corresponds to 2Th degrees for x-ray data. | Corresponds to the current peak position; this corresponds to 2Th degrees for x-ray data. |
| Val | Returns the value of the corresponding parameter. | Returns the value of the corresponding parameter. |
| Yobs, Ycalc, SigmaYobs | Observed, Calculated and estimated standard deviation in Yobs; can be used in the weighting equation. | Observed, Calculated and estimated standard deviation in Yobs; can be used in the weighting equation. |


| Table 2-3. Parameters that operate on phase peaks; dependencies are not shown. | Table 2-3. Parameters that operate on phase peaks; dependencies are not shown. | Table 2-3. Parameters that operate on phase peaks; dependencies are not shown. |
| --- | --- | --- |
| Keywords that can be a function of H, K, L, M, Xo, Th and D_spacing. | Keywords that can be a function of H, K, L, M, Xo, Th and D_spacing. | Keywords that can be a function of H, K, L, M, Xo, Th and D_spacing. |
| lor_fwhm gauss_fwhm hat one_on_x_conv exp_conv_const circles_conv stacked_hats_conv | user_defined_convolution th2_offset scale_pks h1, h2, m1, m2 spv_h1, spv_h2, spv_l1, spv_l2 pv_lor, pv_fwhm pk_xo | phase_out, phase_out_X scale_top_peak set_top_peak_area |
| lor_fwhm gauss_fwhm hat one_on_x_conv exp_conv_const circles_conv stacked_hats_conv | user_defined_convolution th2_offset scale_pks h1, h2, m1, m2 spv_h1, spv_h2, spv_l1, spv_l2 pv_lor, pv_fwhm pk_xo | ymin_on_ymax la, lo, lh, lg modify_peak_eqn current_peak_min_x current_peak_max_x |


| Table 2-4. Phase intensity reserved parameter names. | Table 2-4. Phase intensity reserved parameter names. |
| --- | --- |
| Name | Description |
| A01, A11, B01, B11 | Used for reporting structure factor details as defined in equations (20-5a) and (20-5b), see the macros Out_F2_Details and Out_A01_A11_B01_B11. |
| Iobs_no_scale_pks Iobs_no_scale_pks_err | Returns the observed integrated intensity of a phase peak and its associated error without any scale_pks applied. Iobs_no_scale_pks for phase peak p is calculated using the Rietveld decomposition formulae, or, 1Iobs_no_scale_pks = Get(scale)   where Px,p is the phase peak p calculated at the x-axis position x. The summation x extends over the x-axis extent of the peak p. A good fit to the observed data results in an Iobs_no_scale_pks being approximately equal to I_no_scale_pks. |
| I_no_scale_pks | The Integrated intensity without scale_pks equations, or,  1I_no_scale_pks = Get(scale) I |
| I_after_scale_pks | The Integrated intensity with scale_pks equations applied. 1I_after_scale_pks  = Get(scale) I Get(all_scale_pks) returns the cumulative value of all scale_pks equations applied to a phase. |
| 1) I corresponds to I of hkl_Is, xo_Is and d_Is phases or (M Fobs2) for str phases. | 1) I corresponds to I of hkl_Is, xo_Is and d_Is phases or (M Fobs2) for str phases. |


## Val and Change reserved parameter names

Val is a reserved parameter name for numeric value of a parameter during refinement. Change is a reserved parameter name for the change in a parameter at the end of an iteration as determined by non-linear least squares. Val can only be used in the attribute equations min, max, del, update, stop_when and val_on_continue. Change can only be used in the attribute equations update and stop_when. For example:


| min 0.0001 max = 100; max = 2 Val + 0.1; del = Val 0.1 + 0.1; update = Val + Rand(0,1) Change; stop_when = Abs(Change) < 0.000001; val_on_continue = Val + Rand(-Pi, Pi); x @ 0.1234 update = Val + 0.1 ArcTan(Change 10); min=Val-.2; max=Val+.2; |
| --- |


### The "load { }" keyword and attribute equations

"load { }" allows for loading keywords of the same type by typing the keywords once, for example, exclude in the following input segment:


| xdd   exclude 20 22   exclude 32 35   exclude 45 47 |
| --- |

can be rewritten using "load { }" as follows:


| xdd   load exclude { 20 22 32 35 45 47 } |
| --- |

In some cases, attribute equations are loaded by the parameter itself. For example, in the following:


| prm t 0.01  val_on_continue = Rand(-Pi, Pi); min 0.4 max 0.5 |
| --- |

the prm will load the attribute. In the following, however, load will load the min/max attributes:


| load sh_Cij_prm {    y00 !sh_c00 1     y20  sh_c20 0.26202642  min 0 max 1    y40  sh_c40 0.06823548    ...  } |
| --- |

In this case load does not contain min/max and the parameter will load its attributes.

### Custom positional field order — load KEYWORD field1 field2 ... { }

Beyond the two forms above (flat value list; repeated name+value+attribute lines), `load` also supports declaring a fixed per-entry field order right after the keyword name, e.g. `load site x y z occ beq { ... }`. Each subsequent line in the block is then read positionally as `<site-name> <x> <y> <z> <occ-atom> <occ-value> <beq-name> <beq-value>`, letting many similarly-structured entries (e.g. `site`) be written as bare values instead of the full verbose form.

This is **not** one of the two worked examples in the Technical Reference's section 2.18.1 (`exclude`, `sh_Cij_prm`) — it is a further generalization of the same `load { }` device, confirmed here by direct comparison of real `.inp` files rather than quoted from the manual's prose. Evidence:

- `test_examples/simple.inp` (line 16-19): `site Ce1 ... occ Ce+4 1 beq b1 0.222...` immediately followed by `load site x y z occ beq { O1 0.25 0.25 0.25 O-2 1 b2 0.441... }` — the compact `O1` line expands to exactly `site O1 x 0.25 y 0.25 z 0.25 occ O-2 1 beq b2 0.441...`.
- The same real-world pattern appears in `stacking-faults/kaolinite.inp` (`load site x y z occ beq layer { ... }`).

Treat this positional-template form as confirmed-by-corpus-evidence rather than manual-cited when explaining it.

### The "move_to $keyword" keyword

move_to provides a means of entering parameter attributes without having to first load the parameter (see Keep_Atom_Within_Box macro). The site dependent ADPs_Keep_PD macro, defines min/max limits; here is part of that macro:


| move_to u12 min = -Sqrt(Get(u11) Get(u22)); max =  Sqrt(Get(u11) Get(u22)); |
| --- |

$keyword of move_to can be any object in the internal data tree.


## Automatically saving and loading parameters - load_save_locals


| [load_save_locals] | Examples test_examples\load-save-locals \lsl.inp |
| --- | --- |

Parameters given unique names via local within “for {}” loops can be automatically saved and reloaded for subsequent refinements using the load_save_locals keyword. For example,


| load_save_locals xdd… str… phase_name p1 str…  phase_name p2 for strs { site Ca1 x $ca1x 0.123 … } |
| --- |

Here are two str’s and two local x coordinate parameters defined using the $ character, but only one value is saved to the OUT file. load_save_locals can be used to save both values to a file called INP_File.out_sl (note the out_sl file extension). On rerunning the INP file, the program checks for inp_file.sl and, if found, reads parameter values from it.  The GUI copies inp_file.out_sl to inp_file.sl when parameter values are kept after refinement. Parameters are identified by the xdd file name and the phase name; for raw files, the range number is also saved. Alternatively, the xdd dependent keyword xdd_tag can be used to identify the parameters instead of the xdd file name/range number. This is useful when xdd file names are the same as in the following:


| XDD(..\ceo2) finish_X 50 … XDD(..\ceo2) start_X  50 … ‘ Same file name as first xdd, need to use xdd_tag prm i 0 for xdds { xdd_tag = Load_Eval(i); existing_prm i += 1; … } |
| --- |

Phase names within a given xdd must be unique. Load_Eval evaluates the parameter i at load time and places the result into the xdd dependent xdd_tag. A more complete example, load-save-locals \lsl.inp, defines all refined values as local:


| load_save_locals do_errors XDD(..\ceo2) finish_X 50 str phase_name p1 str phase_name p2 XDD(..\ceo2) start_X  50 str phase_name p3 str phase_name p4 prm i 0 for xdds { xdd_tag = Load_Eval(Concat("tag", i)); ‘ Evaluate on load existing_prm i += 1; CuKa2(0.0001) Radius(173) LP_Factor(17) Full_Axial_Model(12, 20, 12, 5.1, $sl 5) Divergence(1) Slit_Width(0.1) Zero_Error($ze, 0) bkg $bkg  0 0 0 0 0 One_on_X($onex, 0) ‘ This is a fit_obj phase which owns the its locals for strs { space_group FM3M scale $sc 0.001 Cubic($a 5.4102) site  Ce1                       occ Ce+4  1 beq $b1  0.5 site  O1  x 0.25 y 0.25 z 0.25  occ O-2   1 beq $b1  0.5 CS_L($cs, 100) } } |
| --- |

The above is the simplest way of refining on many similar xdds.


## Using local to assist in using “for ... {}” loops

The following parameters have global scope:


| march_dollase $Name spherical_harmonics_hkl $Name sites_geometry $Name sites_distance $Name sites_angle $Name sites_flatten $Name |
| --- |

The march_dollase parameter, as used in the PO macro, can be constrained to the same value across two or more structures by giving them the same name. To use two independent parameters instead, $ can be used to make the parameter local to each str, see po-constrained-create.inp and po-for.inp in the test_examples\po-constrained directory, for example:


| str… str… for strs { PO($po1, 0.8, , 1 0 4) } |
| --- |

The $Name in spherical_harmonics_hkl is local but the spherical harmonics coefficients are global. In the following:


| PO_Spherical_Harmonics(sh2, 8 load sh_Cij_prm { 		k00   !sh2_c00  1.0000 		k41   sh2_c41   0.1000 		k61   sh2_c61  -0.2000 		k62   sh2_c62   0.3000 		k81   sh2_c81  -0.4000 } ) |
| --- |

the sh2 parameter is local to the str and the coefficients k00, k41 etc... are global. This allows the constraining of coefficients across different structures within ‘for strs’; see posh-constrained-create.inp and posh-for.inp in the test_examples\po-constrained directory.


## out_dependences and out_dependences_for

[out_dependences $user_string]

[out_dependences_for $user_string $object_name]

out_dependences outputs dependences for the most previously defined prm or local. For example, the following:


| iters 1 prm d 1 prm e 1 prm f 1 prm c = e + f; prm b = d + e; prm a = b + c; out_dependences a_tag penalty = a^2; |
| --- |

produces on refinement termination the following in standard output:

out_dependences a_tag prm_10

Object name followed by prm name

prm_10   e

prm_10   f

prm_10   d

out_dependences_for is similar except that it names an object that is not a parameter, for example, the following lists independent refined parameters associated with the most recently defined rigid body:


| rigid ...	out_dependences_for tag_1 rigid |
| --- |

Many $object_name’s can be tagged, these include x, y, z, occ, beq, u11, u22, u33, u12, u13, u23, a, b, c, al, be, ga, etc. In addition, non-parameters can be tagged, these include site, rigid, sites_restrain, lat_prms, gauss_conv, lor_conv, all_scale_pks, th2_offset_eqn etc.


## The num_runs keyword and preprocessor specifics


| [num_runs #] [out_file = $E] [system_before_save_OUT { $system_commands } ]… [system_after_save_OUT { $system_commands } ]… |
| --- |


| num_runs 10  yobs_eqn aac##Run_Number##.xy = Gauss(Run_Number, 1 + Run_Number);  min -2 max 20 del 0.01 |
| --- |

produces on execution the following:


| out_file   aac.out  ‘ This will throw an exception out_file = aac.out; ‘ This will throw an exception out_file = "aac.out"; out_file = String(aac.out); out_file = If(Get(r_wp) < 10, "aac.out", ""); out_file = If(Get(r_wp) < 10, Concat(String(INP_File), ".OUT"), ""); |
| --- |

The standard macro Save_Best uses out_file as follows:


| macro Save_Best {       #if (Run_Number == 0)          prm Best_Rwp_ = 9999;       #else          prm Best_Rwp_ = #include Best_Rwp_.txt;       #endif       out Best_Rwp_.txt Out(If(Get(r_wp) < Best_Rwp_, Get(r_wp), Best_Rwp_))       out_file = If(Get(r_wp) < Best_Rwp_, Concat(String(INP_File),".OUT"), ""); } |
| --- |


| macro Backup_INP {    system_before_save_OUT {        copy INP_File##.inp INP_File##.backup    } } |
| --- |

system_after_save_OUT executes the system commands defined in $system_commands just after the *.OUT file is updated.


### Reserved macro names

The following are internally generated macros that can be used in INP files.

ROOT : Returns the root directory of the program.

INP_File : Returns current INP file name without a path or extension.

Run_Number : Returns the current run number.

File_Can_Open($file) : Returns 1 if $file can be opened, or 0 of it can't be opened.

Running an INP file called aac.inp from tc.exe where aac.inp comprises:


| ROOT INP_File Run_Number File_Can_Open(aac.xy) |
| --- |

and aac.xy exists will produce in tc.log the following:

c:\topas-6\ aac 0 1


### The #list directive – creating arrays of macros


| #list File_Name & Temperature(, & la) Time {    File0001.xy 300 0.0    { File0002 .xy } 320 10.2     ‘ Line with curly brackets    File0003.xy 340 21.0    File0017.xy { 360 + la } 28.9 ‘ Line with curly brackets    File0107.xy 380 101.2 } |
| --- |

The macro invoked depends on its first argument, which is implied for File_Name and Time. For Temperature, the first argument is also the implied argument. When invoked, the first argument is a #type equation evaluating to an integer; for example, for File_Name:


| xdd File_Name(Run_Number) |
| --- |

Curly brackets, as seen in the above #list, can be used as delimiters; the following:


| File_Name(1) Temperature(1,) Temperature(3, Get(la) + 0.01) |
| --- |

produces on expansion:


| File0002 .xy (320) (360 + (Get(la) + 0.01)) |
| --- |


### Getting the number of items in a #list using #list_n

During the pre-processor phase of loading INP files, #list_n returns the number of items in a #list; for example:


| #list Files { file1.xdd file2.xdd file3.xdd } Create_XDDs(#list_n Files) |
| --- |


### The File_Variable and File_Variables macro

The File_Variable macro runs a series of refinements with initial parameters values changing in a user-defined manner between runs; it is defined in Topas.inc as:


| macro File_Variable(c, x_start, dx) {    #if (Run_Number == 0)       #prm c = x_start;     #else       #prm c = #include c##.txt;     #endif    #prm c##_next = c + dx;    out c##.txt Out(#out c##_next) } |
| --- |

Using File_Variable as follows:


| File_Variable(occ, 0, 0.1) |
| --- |

will generate a file called occ.txt for each Run with values ranging from 0.1 to 1 in steps of 0.1. A #prm is defined each run with the corresponding values. #out can be used to place the #prm in the INP file, for example, the following:


| iters 0 num_runs 11 File_Variable(occ, 0, 0.1) macro Out_File { Occ##Run_Number##.Out } out_file system_after_save_OUT {    #if (Run_Number)       type Out_File >> aac.out    #else       type Out_File > aac.out    #endif } yobs_eqn !aac.xy = 1;    min 10 max 50 del 0.01    CuKa1(0.0001)    Out_X_Ycalc( occ##Run_Number##.xy )    STR(F_M_3_M)       scale @ 0.0014503208       Cubic(5.41)       site  Ce1                       occ Ce+4 = #out occ; beq  0.2028        site  O1  x 0.25 y 0.25 z 0.25  occ O-2  1           beq  0.5959 |
| --- |

results in eleven *.XY files each generated with a different occupancy for the Ce1 site as determined by the occ #prm. The names of the files would be occ0.xy to occ10.xy. Additionally, using system_after_save_OUT the file AAC.OUT will contain a concatenation of all the *.OUT files. To iterate over two variables, pa and pb say, then the File_Variables macro, defined in Topas.inc as:


| macro File_Variables(a, a1, a2, da, b, b1, b2, db) {    #if (Run_Number == 0)       #prm a = a1;        #prm b = b1;     #else       #prm a = #include a##.txt;        #prm b = #include b##.txt;     #endif    #prm a##_next = If(b >= b2, a + da, a);    #prm b##_next = If(b >= b2, b1, b + db);    out a##.txt Out(#out a##_next)    out b##.txt Out(#out b##_next) } |
| --- |

can be used as follows:


| iters 0 num_runs 36 File_Variables(pa, 0, 1, 0.2, pb, 0, 1, 0.2) prm !pa = #out pa; prm !pb = #out pb; out papb.txt append     out_record out_eqn = pa; out_fmt "(%.1f, "    out_record out_eqn = pb; out_fmt "%.1f) "    #if (pb == 1) Out_String("\n") #endif |
| --- |

On running the above the papb.txt file contains:

(0.0, 0.0) (0.0, 0.2) (0.0, 0.4) (0.0, 0.6) (0.0, 0.8) (0.0, 1.0)

(0.2, 0.0) (0.2, 0.2) (0.2, 0.4) (0.2, 0.6) (0.2, 0.8) (0.2, 1.0)

(0.4, 0.0) (0.4, 0.2) (0.4, 0.4) (0.4, 0.6) (0.4, 0.8) (0.4, 1.0)

(0.6, 0.0) (0.6, 0.2) (0.6, 0.4) (0.6, 0.6) (0.6, 0.8) (0.6, 1.0)

(0.8, 0.0) (0.8, 0.2) (0.8, 0.4) (0.8, 0.6) (0.8, 0.8) (0.8, 1.0)

(1.0, 0.0) (1.0, 0.2) (1.0, 0.4) (1.0, 0.6) (1.0, 0.8) (1.0, 1.0)


## Ingesting files into an INP file using #ingest


| [#ingest $file] |  |
| --- | --- |


| xdd…     str… #ingest common_str.txt |
| --- |

The output file will contain the ingested text with refined parameters updated. In other words, ingested files are treated as part of the original INP file. Ingested files can be nested. $file can be a function of macros.


## #external_INP - using external INP files


| [#external_INP $file] | Examples test_examples\external_INP\ext_inp.inp |
| --- | --- |


| xdd… 	#external_INP instrument.inp 	#external_INP str.inp |
| --- |

#external_INP can be nested – that is, an #external_INP file may itself contain #external_INP commands. $file can be a function of macros. When running Launch mode from the GUI (TA.EXE), all #external_INP OUT files are renamed to INP files if the prompt on refinement termination is answered affirmatively.
