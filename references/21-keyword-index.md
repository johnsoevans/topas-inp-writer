# Keywords


## Data structures

The following describes keyword dependencies. Trailing ‘...’ implies that more than one node of that type can be inserted under its parent. Items enclosed in square brackets are optional. Items beginning with a capital T corresponds to keyword groups analogous to complex types in XML.

**How to read this tree:** a name with no indentation starts a new type's definition (e.g. `Ttop`, `Txdd`, `Tcomm_2` each get their own definition block below). Every indented line under it is a member of that type — either a literal keyword in `[bracket]` notation, or another `T`-prefixed type name, which means "insert everything defined under *that* type's own heading here too" (a mixin/include, not a nested sub-object unless the type is genuinely a child object like `[xdd ...]` containing `[str ...]`). The same `T`-type can be (and often is) included under several different parents — that's exactly how a keyword like `lam` (defined once, under `Tcomm_2`) ends up valid at the top level, the xdd level, *and* the phase level simultaneously: `Ttop`, `Txdd`, and every phase container (via `Tcomm_1_2_phase_1_2`) all include `Tcomm_2` as a member. When debugging "is keyword X valid here," trace which type(s) X is defined under, then check every place those type(s) get included — not just the first match.

```
Ttop
    Tcomm_1
    Tcomm_2
    Ttop_xdd
    Tglobal
    Txdd
    Txdd_scr
    Tindexing
    Tcharge_flipping

Ttop_xdd
    [convolution_step #1]
    [Rp !E] [Rs !E]
    [x_calculation_step !E]

Trwp
    [r_p #] [r_wp #] [r_exp #] [gof #] [r_p_dash #] [r_wp_dash #] [r_exp_dash #]
    [weighted_Durbin_Watson #]

TMinimization
    [line_min] [use_extrapolation] [no_normal_equations] [use_LU]
    [approximate_A]
        [A_matrix_memory_allowed_in_Mbytes !E]
        [A_matrix_elements_tollerance !E]
        [A_matrix_report_on]
    [approximate_A_check_for_must_be_zero #n]
    [chi2 !E]
    [chi2_convergence_criteria !E]
    [continue_after_convergence]
    [bootstrap_errors !Ecycles]
        [fraction_of_yobs_to_resample !E]
        [determine_values_from_samples]
        [resample_from_current_ycalc]
    [do_errors]
    [do_errors_include_restraints]
    [do_errors_include_penalties]
    [only_penalties]
    [percent_zeros_before_sparse_A #]
    [penalty !E]...
    [penalties_weighting_K1 !E]
    [pen_weight !E]
    [quick_refine !E [quick_refine_remove !E] ]
    [randomize_on_errors]
    [restraint !E]
    [save_best_chi2]
    [use_LU_for_errors]

Tglobal
    TMinimization
    Trwp
    [A_matrix] [C_matrix] [A_matrix_normalized] [C_matrix_normalized]
    [conserve_memory]
    [file_name_for_best_solutions $file]
    [force_positive_fwhm]
    [inp_text $name] …[inp_text_insert $name { … }]…
    [iters #]
    [no_LIMIT_warnings]
    [num_cycles #]
    [out_A_matrix $file]
    [out_refinement_stats]
    [out_rwp $file]
    [out_prm_vals_per_iteration $file]... | [out_prm_vals_on_convergence $file]...
    [out_prm_vals_on_end $file]…
    [process_times]
    [randomise_file_out_normal $file]
    [seed [#]]
    [suspend_writing_to_log_file #1]
    [temperature !E]...
    [use_tube_dispersion_coefficients]
    [verbose #1]

Txdd
    [xdd $file [{$data}] [range #] [xye_format] [gsas_format] [fullprof_format] ]...
        Ttop_xdd
        Txdd_comm_1
        Tcomm_1
        Tcomm_2
        Tmin_max_rc
        Trwp
        [gui_add_bkg !E]
        [xdd_sum !E] and [xdd_array !E]
        [cross_corr $name #value
            cross_corr_s !E
        [user_y $name { #include $file }]... | [user_y $name $file]...
            [xye_format]
            [rebin_with_dx_of !E]
            [user_y_hat E]...
            [user_y_gauss_fwhm E]...
            [user_y_lor_fwhm E]...
            [user_y_exp_conv_const E [user_y_exp_limit E]]...
        [xo_Is]...
            [xo E  I E]...
            Tcomm_1_2_phase_1_2
        [d_Is]...
            [d E  I E]...
            Tcomm_1_2_phase_1_2
            [lebail #]
        [hkl_Is]...
            [lp_search !E]
            [I_parameter_names_have_hkl $start_of_parameter_name]
            [hkl_m_d_th2 # # # # # #  E I E]...
            Tspace_group
            Tcomm_1_2_phase_1_2
            Thkl_lat
            [lebail #]
        [str | dummy_str]...
            Tstr_details
            Thkl_lat
            Tcomm_1_2_phase_1_2
            Tmin_max_rs
            [rigid]...
            Tspace_group

Tcomm_1_2_phase_1_2
    Tcomm_1
    Tcomm_2
    Tphase_1
    Tphase_2

Txdd_scr
    [xdd_scr $file] ...
        Txdd_comm_1
        Tcomm_2
        Ttop_xdd
        Tmin_max_r
        [str]...
            Tstr_details
            Tphase_1
            Tcomm_2
            Thkl_lat
            Tmin_max_r
            [rigid]...
            Tspace_group
            Tscr_1

Tscr_1
    [Flack E]
    [i_on_error_ratio_tolerance #]
    [num_highest_I_values_to_keep #]

Txdd_comm_1
    [bkg [@] # # #...]
    [degree_of_crystallinity #]
    [d_spacing_to_energy_in_eV_for_f1_f11 !E]
    [exclude #ex1 #ex2]...
    [extra_X_left !E] [extra_X_right !E]
    [fit_obj E [min_X !E] [max_X !E] ]...
    [neutron_data]
    [rebin_with_dx_of !E]
    [smooth #]
    [start_X !E] [finish_X !E]
    [weighting !E [recal_weighting_on_iter] ]
    [xdd_out $file [append] ]...
        Tout_record
    [yobs_eqn !N E]
    [yobs_to_xo_posn_yobs !E]

Tcomm_1
    [axial_conv]...
    [capillary_diameter_mm E]...
        capillary_u_cm_inv E
        [capillary_convergent_beam] [capillary_divergent_beam] [capillary_parallel_beam]
        [capillary_focal_length_mm E]
        [capillary_xy_n #]
    [lpsd_th2_angular_range_degrees E]...
    [circles_conv E]...
    [exp_conv_const E  [exp_limit E] ]...
    [ft_conv E]...
    [ft_conv_re_im]...
        [ft_conv_re E]
        [ft_conv_im E]
        [ft_min !E]
        [ft_x_axis_range !E]
    [gauss_fwhm E]...
    [h1 E  h2 E  m1 E  m2 E]
    [hat E [num_hats #1] ]...
    [modify_peak]
        [modify_peak_apply_before_convolutions]
        [modify_peak_eqn !E]
            [current_peak_min_x !E]
            [current_peak_max_x !E]
    [more_accurate_Voigt]
    [lor_fwhm E]...
    [numerical_lor_gauss_conv]
    [numerical_lor_ymin_on_ymax #0.0001]
    [one_on_x_conv E]...
    [pk_xo E]
    [push_peak]...
    [pv_lor E  pv_fwhm E]
    [spv_h1 E  spv_h2 E  spv_l1 E  spv_l2 E]
    [stacked_hats_conv [whole_hat E [hat_height E] ]...[half_hat E [hat_height E] ]...]...
    [th2_offset E]...
    [user_defined_convolution E min E max E]...
    [WPPM_ft_conv E]...
    [WPPM_ft_conv_re_im E]...
        [WPPM_ft_conv_re E]
        [WPPM_ft_conv_im E]
        WPPM_L_max E
        WPPM_th2_range E
        [WPPM_break_on_small !E]
        [WPPM_correct_Is]

Tcomm_2
    [f0_f1_f11_atom]...
        [f0 E] [f1 E] [f11 E]
    [lam [ymin_on_ymax #] [no_th_dependence] [Lam !E] [calculate_Lam] ]
    [scale_pks E]...
    [scale_phase_X E]
    [prm|local E [min !E][max !E][del !E][update !E][stop_when !E][val_on_continue !E]]...
    [existing_prm E]...
    [penalty !E]...
    [out $file [append] ]...
        Tout_record

Tphase_1
    [atom_out $file [append] ]...
        Tout_record
    [auto_scale !E]
    [del_approx !E]
    [phase_name $phase_name]
    [phase_out $file [append] ]...
    [phase_out_X $file [append] ] …
    [brindley_spherical_r_cm !E]
    [r_bragg #]
    [remove_phase !E]
    [scale E]

Tphase_2
    [peak_buffer_step  E [report_on] ]
    [peak_type $type]
    [numerical_area E]

Tstr_details
    [append_cartesian] [append_fractional  [in_str_format] ]
    [append_bond_lengths  [consider_lattice_parameters] ]
    [atomic_interaction N E] | [ai_anti_bump N]...
    [box_interaction [from_N #] [to_N #] [no_self_interaction]  $site_1 $site_2 N E]...
    [fourier_map !E]
    [grs_interaction [from_N #][to_N #][no_self_interaction] $site_1 $site_2 qi # qj # N E]...
    [hkl_plane $hkl]...
    [no_f11]
    [normalize_FCs]
    [occ_merge $sites [occ_merge_radius !E] ]...
    [p1_fractional_to_file $file] [in_str_format]...
    [site $site]...
        [adps] [u11 E] [u22 E] [u33 E] [u12 E] [u13 E] [u23 E]
        Tmin_r_max_r
    [sites_distance N] | [sites_angle N] | [sites_flatten N [sites_flatten_tol !E] ]...
    [sites_geometry N]...
    [siv_s1_s2 # #]
    [report_on_str]
    [view_structure]

Thkl_lat
    [a E] [b E] [c E] [al E] [be E] [ga E]
    [normals_plot !E]...
    [phase_penalties $sites N [hkl_Re_Im #h #k #l #Re #Im]...]...
    [spherical_harmonics_hkl $name]...
    [str_hkl_angle N h k l]...
    [omit_hkls !E]

Tout_record
    [out_record]...

Tmin_r_max_r
    [min_r #] [max_r #]

Tspace_group
    [space_group $symbol]

Miscellanous
    [aberration_range_change_allowed !E]
    [default_I_attributes !E]
    load, move_to, for
```

## Alphabetical listing of keywords

[a E] [b E] [c E] [al E] [be E] [ga E]

Lattice parameters in Å and lattice angles in degrees.

[adps] [u11 E] [u22 E] [u33 E] [u12 E] [u13 E] [u23 E]

adps generates the unn atomic displacement parameters with considerations made for special positions (see test_exampleS\single-crystal\AE14-ADPS.INP). On termination of refinement the adps keyword is replaced with the unn parameters; see example ae1-adps.inp. Instead of using the adps keyword the unn parameters can be manually entered. The unn matrix can be kept positive definite with the site dependent macro of ADPs_Keep_PD; this can stabilize refinement. The ADPs_Keep_PD macro can be used after the unn parameters are created. For determining adp constraints the 3x3 eigen value determination routine of Kopp (2006) has been used.

[[amorphous_phase]]

In the calculation of degree_of_crystallinity, phases with amorphous_phase are treated as amorphous in the calculation.

[A_matrix] [C_matrix] [A_matrix_normalized] [C_matrix_normalized]

[append_cartesian] [append_fractional [in_str_format] ]

Appends site fractional coordinates in Cartesian or fractional coordinates respectively to the *.OUT file at the end of a refinement. For the case of append_fractional, in_str_format produces output in INP format.

[append_bond_lengths [consider_lattice_parameters] ]

Y1:0    O1:0    2.23143

O2:0    2.23143    88.083

O3:0    2.28045    109.799    99.928

[atomic_interaction N E] |  [ai_anti_bump N]...

ai_sites_1 $sites_1 ai_sites_2 $sites_2

[ai_no_self_interation]

[ai_closest_N !E]

[ai_radius  !E]

[ai_exclude_eq_0]

[ai_only_eq_0]

Defines an atomic interaction with the name N between sites identified by $site_1 and $site_2. For atomic_interaction, E is the site interaction equation that can be a function of R and Ri. R returns the distance in Å between two atoms; these distances are updated when dependent fractional atomic coordinates are modified. The name of the atomic_interaction N can be used in equations including penalty equations. For ai_anti_bump, an internal c++ anti-bump interaction equation is used. For anti-bumping only, ai_anti_bump is faster than using atomic_interaction. The AI_Anti_Bump macro uses ai_anti_bump. no_self_interaction prevents interactions between equivalent positions of a site. This is useful when a general position is used to describe a special position.

ai_closest_N: interactions between $sites_1 and $sites_2 are sorted by distance and only the first ai_closest_N number of interactions are considered.

When ai_radius and ai_closest_N are both defined then interactions from both sets of corresponding interaction are considered.


| atomic_interaction ... ai_exclude_eq_0 ai_sites_1 Pb ai_sites_2 “O1 O2” |
| --- |

the following interactions are considered:

Pb:0 and O1:n      (n  0)

Pb:0 and O2:n      (n  0)

where the number after the ‘:’ character corresponds to the equivalent positions of the sites. ai_only_eq_0: only interactions between equivalent positions 0 are considered.

Functions

The atomic_interaction equation can be a function of the following functions:

AI_R(#ri): Returns the distance between the current site and the atom defined with Ri=#ri.

AI_R_CM: A function of no arguments that returns the geometric center of the current atom and the atoms defined in $sites_2.

AI_Flatten(#toll): A function that returns the sum of distances of the current atom and those defined in $sites_2 to an approximate plane of best fit.

AI_Cos_Angle(#ri1, #ri2): Returns the Cos of the angle between the atom define as Ri=#ri1, the current atom and the atom defined as Ri=#ri2.

AI_Angle(#ri1, #ri2): Similar-to AI_Cos_Angle except that the value returned is the angle in degrees.

Examples benzene_ai1.inp, benzene_ai2.inp and benzene_ai3.inp demonstrates the use of the atomic_interation functions. atomic_interaction’s are used to apply geometric restraints. For example, anti-bumping between molecules for the first ten iterations of a refinement cycle can be formulated as follows:


| atomic_interaction ai1 = If(R < 3, (R-3)^2, 0); ai_exclude_eq_0 ai_sites_1 C* ai_sites_2 C*  ai_radius 3 penalty = If(Cycle_Iter < 10, ai1, 0); |
| --- |

[atom_out $file [append] ]...

Used for writing site dependent details to file. See out for a description of out_record. The Out_CIF_STR macro uses atom_out

[axial_conv]...

filament_length E sample_length E receiving_slit_length E

[primary_soller_angle E]

[secondary_soller_angle E]

[axial_n_beta !E]

[bkg [@] # # # ...]

Defines a Chebyshev polynomial where the number of coefficients is equal to the number of numeric values appearing after bkg.

[box_interaction [from_N #] [to_N #] [no_self_interaction] $site_1 $site_2 N E]...

Defines a site interaction with the name N between sites identified by $site_1 and $site_2. E represents the site interaction equation which can be a function of R and Ri. R returns the distance in Å between two atoms; these distances are updated when dependent fractional atomic coordinates are modified. The name of the box_interaction N can be used in equations including penalty equations. When either from_N or to_N are defined, the interactions between $site_1 and $site_2 are sorted by distance and only the interactions between the from_N and to_N are considered. no_self_interaction prevents any interactions between equivalent positions of the same site. This is useful when a general position is used to describe a special position. For example, the following could be used to iterate from the nearest atom to the third atom from a site called Si1:


| str site Si1 ...  site O1 ... site O2 ... site O3 ... box_interaction Si1 O* to_N 2 !si1o = (R-2)^2; penalty = !si1o; |
| --- |

In this example the nearest three oxygen atoms are soft constrained to a distance of 2 Å by use of the penalty function. Counting starts at zero and thus to_N is set to 2 to iterate up to the third nearest atom.

The wild card character ‘*’ used in “O*” means that sites with names starting with ‘O’ are considered. In addition to using the wild card character, the site names can be explicitly written within double quotation marks, for example:


| box_interaction Si1 “O1 O2 O3” to_N 3 etc... |
| --- |

Interactions between Si1 and the three oxygen atoms O1, O2, O3 may not all be included, for example, if Si1 has as its nearest neighbours the following:

Si1-O1,1 at a distance of 1.0 Å

Si1-O2,3 at a distance of 1.1 Å

Si1-O2,1 at a distance of 1.2 Å

Si1-O1,2 at a distance of 1.3 Å

then two equivalent positions of site O1 and two equivalent positions of O2 would be included in the interaction equation; thus, interactions between Si1-O3 are not considered. To ensure that each of the three oxygens has Si1 included in an interaction equation then the following could be used:


| box_interaction “O1 O2 O3” Si1 to_N 0 etc... |
| --- |

Thus, the order of $site_1 and $site_2 is important when either from_N or to_N is defined. The reserved parameters Ri and Break can also be used in interaction equations when either from_N or to_N is defined. Ri returns the index of the current interaction being operated on with the first interaction starting at Ri = 0.

box_interaction is used for example by the Anti_Bump macro.

[brindley_spherical_r_cm !E]

Applies the Brindley correction for spherical particles. The macro Apply_Brindley_Spherical_R_PD is defined as:


| macro Apply_Brindley_Spherical_R_PD(& R, & PD) { brindley_spherical_r_cm = R PD; } |
| --- |

R is the radius of the particle in cm and PD is the packing density. Here’s an example:


| xdd ... str Apply_Brindley_Spherical_R_PD(R, PD) MVW(0,0,0) str Apply_Brindley_Spherical_R_PD(R, PD) MVW(0,0,0) |
| --- |


| xo_Is Apply_Brindley_Spherical_R_PD(0.002, 0.6) MVW(654, 230, 0) phase_MAC 200 |
| --- |

[capillary_diameter_mm E]...

capillary_u_cm_inv E

[capillary_convergent_beam] [capillary_divergent_beam] [capillary_parallel_beam]

[capillary_focal_length_mm E]

[capillary_xy_n #]

Examples for the capillary convolution (Coelho & Rowles, 2017) are lab6-stoe.inp and lab6-d8.inp as found in the directory test_examples\capillary. If using a str phase then capillary_u_cm_inv can be set to the calculated linear absorption coefficient multiplied by a packing density, for example:


| prm packing_density 0.31208 capillary_diameter_mm @ 0.57313 capillary_u_cm_inv  = Get(mixture_MAC) Get(mixture_density_g_on_cm3) packing_density; capillary_focal_length_mm @ 197.89657 capillary_convergent_beam |
| --- |

If not defined, capillary_focal_length_mm defaults to the diffractometer radius Rs.

[circles_conv E]...

Defines m in the convolution function:

(1  m / ½)          for  = 0 to m

that is convoluted into phase peaks. m can be greater than or less than zero. circles_conv is used for example by the Simple_Axial_Model macro.

[cloud $sites]...

[cloud_population !E]

[cloud_save $file]

[cloud_save_xyzs $file]

[cloud_load_xyzs $file]

[cloud_load_xyzs_omit_rwps !E]

[cloud_formation_omit_rwps !E]

[cloud_try_accept !E]

[cloud_gauss_fwhm !E]

[cloud_extract_and_save_xyzs $file]

[cloud_number_to_extract !E]

[cloud_atomic_separation !E]

cloud allows for the tracking of atoms defined in $sites in three dimensions. It can be useful for determining the average positions of heavy atoms or rigid bodies during refinement cycles. For example, a dummy atom, “site X1” say, can be placed at the center of a benzene ring and then tracked as follows:


| continue_after_convergence ... cloud “X1” cloud_population 100 cloud_save SOME_FILE.CLD |
| --- |

On termination of refinement the CLD file is saved; it can be viewed using the rigid body editor of the GUI; see examples ae14-12.inp for a cloud example. cloud_population is the maximum number of population members. Each population member comprises the fractional coordinates of $sites and an associated Rwp value.

cloud_save_xyzs saves a cloud population to file.


| cloud_try_accept = And(Cycle, Mod(Cycle, 50)); cloud_try_accept = T == 10; |
| --- |

cloud_gauss_fwhm is the full width at half maximum of a three-dimensional Gaussian that is used to fill the cloud.

cloud_extract_and_save_xyzs searches the three-dimensional cloud for high densities and extracts xyz positions; these are then saved to $file. cloud_number_to_extract defines the number of positions to extract and cloud_atomic_separation limits the atomic separation during the extraction. The actual number of positions extracted may be less than cloud_number_to_extract depending on the cloud.

[conserve_memory]

Deletes temporary arrays used in intermediate calculations as often as possible; memory savings of up to 70% can be expected on some problems with subsequent lengthening of execution times by up to 40%. When approximate_A is used on dense matrices then conserve_memory can reduce memory usage by up to 90%.

[convolution_step #1]

An integer defining the number of calculated data points per measured data point. Increasing convolution_step when the measurement step is large improves convolution accuracy. Only when the measurement step is greater than about 0.03 degrees 2Th or when high precision is required is it necessary to increase convolution_step.

[default_I_attributes E]

Changes the attributes of the I parameter, for example:


| xo_Is... 	default_I_attributes 0 min 0.001 val_on_continue 1 |
| --- |

Useful when randomizing lattice parameters during Le Bail refinements with continue_after_convergence.

[degree_of_crystallinity #]

[crystalline_area  #]

[amorphous_area  #]

Reports on the degree of crystallinity which is calculated as follows:

100 * Get(crystalline_area) / (Get(crystalline_area) + Get(amorphous_area))

[d_Is]...

[d E  I E]...

Defines a phase type that uses d-spacing values for generating peak positions. d corresponds to the peak position in d-space in Å and I is the intensity parameter before applying any scale_pks equations.

[d_spacing_to_energy_in_eV_for_f1_f11 !E]


| ‘ E(eV) = 10^5 / (8.065541 Lambda(A)) prm !detector_angle_in_radians = 7.77 Deg_on_2; prm wavelength = 2 D_spacing Sin(detector_angle_in_radians); prm energy_in_eV = 10^5 / (8.065541 wavelength); pk_xo = 10^-3 energy_in_eV + zero;  d_spacing_to_energy_in_eV_for_f1_f11 = energy_in_eV; |
| --- |

[exclude #x1 #x2]...

Excludes an x-axis region between #x1 and #x2. The macro Exclude simplifies usage; see example ceo2.inp.

[exp_conv_const E  [exp_limit E] ]...

Defines m in the aberration function:

A = Exp(Ln(0.001) m)    for  = 0 to exp_limit

that is convoluted into phase peaks. Used by the Absorption and Absorption_With_Sample_Thickness_mm macros. The  range of A is:

(0 <  < limit)  for m < 0,         or,         (limit <  < 0)  for m > 0

where A(limit)= 0.001. Alternatively, limit can be defined using exp_limit.

[extra_X_left !E]  [extra_X_right !E]

[file_name_for_best_solutions $file]

Appends INP file details to $file during refinement with independent parameter values updated. The operation is performed when convergence results in the best Rwp.

[force_positive_fwhm]

Forces Lorentzian and/or Gaussian FWHM values to be positive. The following INP snippets are equivalent:


| force_positive_fwhm xdd ... str ... lor_fwhm = Rand(-1,1); | xdd ... str ... lor_fwhm = Abs(Rand(-1.1,)); |
| --- | --- |

[fit_obj E [min_X !E] [max_X !E] ]...

[fo_transform_X !E]

[fit_obj_phase !E]

Defines a User defined function added to Ycalc, see example pvs.inp. fit_obj’s can be a function of X. min_X and max_X define the x-axis range of the fit_obj; if min_X is omitted then the fit_obj is calculated from the start of the x-axis; similarly, if max_X is omitted then the fit_obj is calculated to the end of the x-axis. fo_transform_X is a dependent of fit_obj and it can be used to transform X used within the fit_obj.

[fourier_map !E]

[fourier_map_formula !E]

[extend_calculated_sphere_to !E]

[min_grid_spacing !E]

[correct_for_atomic_scattering_factors !E]

[f_atom_type $type f_atom_quantity !E]...

If fourier_map is non-zero then a Fourier map is calculated on refinement termination and shown in the OpenGL window; maps can be calculated for x-ray or neutron single crystal or powder data, see test examples fourier-map-ae14.inp and fourier-map-cime.inp. The type of map is determined by fourier_map_formula which can be a function of the reserved parameter names Fcalc, Fobs and D_spacing; here are some examples:


| fourier_map_formula = Fobs; ‘ The default fourier_map_formula = 2 Fobs - Fcalc; |
| --- |

For single crystal data, Fobs corresponds to the observed structure moduli; powder data Fobs is calculated from the Rietveld decomposition formula. Structure factor phases are determined from Fcalc. Reflections that are missing from within the Ewald sphere are included with Fobs set to Fcalc. If extend_calculated_sphere_to is defined, then the Ewald sphere is extended. scale_pks definitions are removed from Fobs. If scale_pks evaluates to zero for a particular reflection, then Fobs is set to Fcalc; the number of Fobs reflections set to Fcalc is reported on.

[gauss_fwhm E]...

Defines the FWHM of a Gaussian function convoluted into phase peaks; see CS_G and Strain_G macros.

[hkl_plane $hkl]...

Used by the OpenGL viewer to display hkl planes, see the CeO2.STR file in the rigid directory. Here are some examples:


| str ...  hkl_plane 1 1 1 hkl_plane “2 -2 0” |
| --- |

[grs_interaction [from_N #] [to_N #] [no_self_interaction] $site_1 $site_2 qi # qj # N E]...

Defines a GRS interaction with the name N between sites identified by $site_1 and $site_2. E represents the GRS interaction equation that can be a function of R; R returns the distance in Å between two atoms; these distances are updated when dependent fractional atomic coordinates are modified. The name N of the grs_interaction can be used in equations including penalty equations. When either from_N or to_N are defined, the interactions between $site_1 and $site_2 are sorted by distance and only the interactions between the from_N and to_N are considered. no_self_interaction prevents any interactions between equivalent positions of the same site. This is useful when a general position is used to describe a special position. qi and qj corresponds to the valence charges used to calculate the Coulomb sum for the $site_1 and $site_2 sites respectively. grs_interaction is typically used for applying electrostatic restraints in inorganic materials. The GRS_Interaction macro simplifies the use of grs_interaction.

[hat E [num_hats #1] ]...

Defines the x-axis extent of an impulse function that is convoluted into phase peaks. num_hats correspond to the number of hats to be convoluted. hat is used for example by the Slit_Width and Specimen_Tilt macros.

[hkl_Is]...

[lp_search !E]

[I_parameter_names_have_hkl $start_of_parameter_name]

[hkl_m_d_th2 # # # # # # I E]...

Defines a phase type that uses hkls for generating peak positions. lp_search uses an indexing algorithm that is independent of d-spacing extraction (bCoelho, 2017); see lp-search-pbso4.inp. lp_search minimizes on a figure of merit function that gives a measure of correctness for a particular set of lattice parameters. The method avoids difficulties associated with extracting d-spacings from complex patterns comprising heavily overlapped lines; the primary difficulty being that of ascertaining the number of lines present. I_parameter_names_have_hkl assigns names to generated Intensity parameters that start with $start_of_parameter_name and end with the corresponding hkl. The numbers after hkl_m_d_th2 define h k l m d and 2 values, where

h, k, l 			: Miller indices

m 				: multiplicity.

d and th2 		: d and 2 values.

I 				: Peak intensity parameter before applying any scale_pks.

If no hkl_m_d_th2 keywords are defined, then hkls are generated using the space group. Generated hkl_m_d_th2 details are placed after the space_group keyword on refinement termination. Intensity parameters are given an initial starting value of 1. If lebail is not defined, then the intensity parameters are given the code of @. For example, the following:


| xdd quartz.xdd ... hkl_Is     Hexagonal(4.91459, 5.40603)    space_group P_31_2_1 |
| --- |

generates in the OUT file the following:


| xdd quartz.xdd ... hkl_Is Hexagonal(4.91459, 5.40603) space_group P_31_2_1 load hkl_m_d_th2 I { 1   0   0   6    4.25635   20.85324 @ 3147.83321 1   0   1   6    3.34470   26.62997 @ 8559.23955 1   0  -1   6    3.34470   26.62997 @ 8559.23955  ... } |
| --- |

The Create_hklm_d_Th2_Ip_file macro creates an hkl file listing in the "load hkl_m_d_th2 I" format as shown above. Even though the structure would have no sites, weight_percent can still be used; it uses whatever value is defined by cell_mass to calculate weight_percent.

[inp_text $name] …

[inp_text_insert $name { … }]…

inp_text provides a means of defining INP text at one place in a file and having that text inserted at another place in the INP file, or in an #include file, using inp_text_insert. The inp_text is updated on refinement termination. inp_text is very useful for simplifying complicated INP files where placing control parameters at the top of the file is of benefit; see test_example INP-TEXT.INP. An example is as follows:


| inp_text back_ground { bkg @  17.365576`  14.5555883`  14.038067` } xdd … inp_text_insert back_ground |
| --- |

More than one inp_text can be of the same name; in such cases inp_text_insert will use the most recent inp_text.

[iters #]

The maximum number of refinement iterations, default is 109.

[lam [ymin_on_ymax #] [no_th_dependence] [Lam !E] [calculate_Lam]]

[la E  lo E  [lh E] | [lg E] [lo_ref] ]...

Defines an emission profile (see section 5) where each la determines an emission profile line, where:

la: 	Area under the emission profile line

lo: 	Wavelength in Å of the emission profile line

lh: 	HW in mÅ of a Lorentzian convoluted into the emission profile line.

lg: 	HW in mÅ of a Gaussian convoluted into the emission profile line.

ymin_on_ymax determines the x-axis extent to which an emission profile line is calculated; default value is 0.001. no_th_dependence defines an emission profile that is 2 independent; it allows use of non-X-ray data or fitting to negative 2 values. By default, the program calculates d-spacings using the wavelength of the emission profile line with the highest la parameter. However, if la parameters are refined the reference wavelength could change causing confusion. To avoid this lo_ref can be used to identify the reference wavelength.

Lam defines the value to be used for the reserved parameter Lam. When Lam is not defined then the reserved parameter Lam is defined as the wavelength of the emission profile line with the largest la value. Note that Lam is used to determine the Bragg angle.

calculate_Lam calculates Lam such that it corresponds to the wavelength at the peak of the emission profile. Lam needs to be set to an approximate value corresponding to the peak of the emission profile.

[lor_fwhm E]...

Defines the FWHM of a Lorentzian that is convoluted into phase peaks; see for example the CS_L and Strain_L macros.

[lpsd_th2_angular_range_degrees E]...

lpsd_equitorial_divergence_degrees E

lpsd_equitorial_sample_length_mm E

lpsd_th2_angular_range_degrees corresponds to the angular range of the LPSD in 2Th degrees. lpsd_equitorial_divergence_degrees is the equatorial divergence in degrees of the primary beam and lpsd_equitorial_sample_length_mm the length of the sample in the equatorial plane. lpsd_th2_angular_range_degrees corrects peak shapes, intensities and 2Th shifts, see example lpsd-simulated.inp.

[min_r #] [max_r #]

Defines the minimum and maximum radii for calculating bond lengths, defaults are 0 and 3.2 Å respectively.

[neutron_data]

Signals the use of neutron atomic scattering lengths. Scattering lengths for isotopes can be used by placing the isotope name after “occ” as in:


| occ 6Li 1 occ 36Ar 1 |
| --- |

Constant wavelength neutron diffraction requires a Lorentz correction using the Lorentz_Factor macro (defined in Topas.inc); it is defined as follows:


| scale_pks = 1 / (Sin(Th)^2 Cos(Th)); |
| --- |

[no_LIMIT_warnings]

Suppresses LIMIT_MIN and LIMIT_MAX warnings.

[normalize_FCs]

[numerical_area E]

Returns the numerically calculated area under the phase.

[num_cycles #]


| continue_after_convergence iters 1000000000 num_cycles 100 |
| --- |

[occ_merge $sites [occ_merge_radius !E]]...

Rewrites site occupancies of sites defined in $sites in terms of their fractional atomic coordinates (Favre-Nicolin and R. Cerny 2002). This is useful during structure solution for merging rigid bodies such as octahedra. It is also useful for identifying special positions as seen in the example pbso4-decompose.inp. In the present implementation $sites are thought of as spheres with a radius occ_merge_radius. When two atoms approach with a distance less than the sum of their respective occ_merge_radius’s then the spheres intersect. The occupancies of the sites, occ_xyz, become:

occ_xyz = 1 / (1 + Intersecting_fractional_volumes)

In this way any number of sites can be merged. Sites appearing in $sites cannot have their occupancies refined. On termination of refinement the occ parameter values are updated with their corresponding occ_xyz.

[omit_hkls !E]

Allows for the filtering of hkls using the reserved parameter names of H, K, L and D_spacing. More than one omit_hkls can be defined, for example:


| omit_hkls = If(And(H==0, K==0), 1, 0); omit_hkls = And(H==0, K==1); omit_hkls = D_spacing < 1; |
| --- |

[one_on_x_conv E]...

Defines m in the convolution function:

4 m  ½            for  = 0 to m

that is convoluted into phase peaks. m can be greater than or less than zero, see for example the Divergence macro.

[out_A_matrix $file]

[A_matrix_prm_filter $filter]

Outputs the least squares A matrix to the file $file; used in the macro Out_for_cf. Output can be limited by using A_matrix_prm_filter, here’s an example for outputting A matrix elements corresponding to parameters with names starting with ‘q’:


| out_A_matrix file.a A_matrix_prm_filter q* |
| --- |

[out $file [append] ]...

[out_record]

[out_eqn !E]

[out_fmt $c_fmt_string]

[out_fmt_err $c_fmt_string]...

Used for writing parameter details to a file. The details are appended to $file when append is defined. out_eqn defines the equation or parameter to be written to $file using the out_fmt. $c_fmt_string describes a format string in c syntax containing a single format specified for a double precision number. out_fmt_err defines the $c_fmt_string used for formatting the error of eqn. Both out_fmt and out_fmt_err requires an out_eqn definition. out_fmt can be used without out_eqn for writing strings. The order of out_fmt and out_fmt_err determines which is written to file first. The following illustrates the use of out using the Out macros (see out-1.inp):


| xdd ... out "sample output.txt" append str ... CS_L(cs_l, 1000) Out_String("\tCrystallite Size Results:\n") Out_String("\t=========================\n") Out(cs_l, "\tCrystallite Size (nm):\t%11.5f",            "\tError in Crystallite Size:\t%11.5f\n") |
| --- |

[out_rwp $file]

Outputs a list of Rwp values encountered during refinement to the file $file in XDD format.

[out_prm_vals_per_iteration $file [append]]... | [out_prm_vals_on_convergence $file [append]]...

[out_prm_vals_filter $filter]

[out_prm_vals_dependents_filter $filter_dependents]

Outputs refined independent parameter values per iteration or on convergence into the file $file. out_prm_vals_filter can be used to filter the parameters; $fliter can contain the wild card character ’*’ and the negation character ’!’, for example:


| out_prm_vals_per_iteration PRM_VALS.TXT out_prm_vals_filter "* !u*" |
| --- |

More than one out_prm_vals_per_iteration/out_prm_vals_on_convergence can be defined for outputting different parameters into different files depending on the corresponding out_prm_vals_filter. out_prm_vals_dependents_filter allows dependent parameters to be outputted according to $filter_dependents.

[out_prm_vals_on_end $file [append]]...

Allows for output only at the end of refinement, for example:


| str… prm wtp = Get(weight_percent); out_prm_vals_on_end aac2.txt append out_prm_vals_filter wtp out_prm_vals_dependents_filter wtp |
| --- |

The following example shows how to add items to the out_prm_vals_on_end file.


| #list Files { file1.xy file2.xy } num_runs #list_n Files do_errors out_prm_vals_on_end results.txt #if (Run_Number > 0) append #endif xdd Files(Run_Number) str… out results.txt append load out_record out_fmt out_eqn { "%d " = Run_Number; " %s  " = Files(Run_Number); } |
| --- |

The above will output the following into the file results.txt.


| Cycle Iter Rwp second_soll1FCF42E6640_ Err bkg1FCF3E90F18 Err ...     0      7  7.026593e+00  7.437574e+00  3.511447e-02  1.208843e+01 ...      0  file1.xy Cycle Iter Rwp second_soll1FCF42E6640_ Err bkg1FCF3E90F18 Err ...     0      7  7.026593e+00  7.437574e+00  3.511447e-02  1.208843e+01 ...     1  file2.xy |
| --- |

[p1_fractional_to_file $file] [in_str_format]

Structure dependent. Saves atomic positions corresponding to space group P1 to the file $file. The original space group can be any space group. If in_str_format is defined, then the structural data is saved in INP format.

[peak_type $type]

[pv_lor E  pv_fwhm E]

[h1 E  h2 E  m1 E  m2 E]

[spv_h1 E  spv_h2 E  spv_l1 E  spv_l2 E]

Sets the peak type for a phase, see section 5. The following peak_type’s are available:


| Peak type | $type | Parameters |
| --- | --- | --- |
| Fundamental  Parameters | fp |  |
| Pseudo-Voigt | pv | pv_lor: the Lorentzian fraction of the peak profile(s). pv_fwhm: the FWHM of the peak profile(s). |
| Split-PearsonVII | spvii | The sum of h1 and h2 gives the FWHM of the composite peak. m1, m2 are the PearsonVII exponents of the left and right composite peak. |
| Split-PseudoVoigt | spv | The sum of spv_h1 and spv_h2 gives the full width at half maximum of the composite peak. spv_l1, spv_l2 are the left and right Lorentzian fractions. |

[peak_buffer_step E [report_on]]

Peaks shapes typically change in a gradual manner over a short 2 range; a new peak shape, therefore, is calculated only if the position of the last peak shape calculated is more than the distance defined by peak_buffer_step. Various stretching and interpolation procedures are used to calculate in-between peaks, see also section 5.4. The default setting is as follows:

peak_buffer_step = 500*Peak_Calculation_Step.

When the reserved parameter names of H, K, L, M, or parameter names associated with sh_Cij_prm and hkl_angle, are used in peak convolution equations, then irregular peak shapes are possible over short 2 ranges. In such cases, separate peak shapes are calculated for each peak irrespective of peak_buffer_step. report_on displays the number of peaks in the peaks buffer.

A value of zero for peak_buffer_step forces the calculation of a separate peak shape for each peak.

[phase_out $file [append] ]...

Used for writing phase dependent details to file. See out for a description of out_record. The Create_hklm_d_Th2_Ip_file uses phase_out.

[phase_out_X $file [append] ]…

Phase dependent keyword that writes phase Ycalc details to a file. The out_eqn can contain reserved parameter names occurring in xdd_out as well as Get(phase_ycalc); for example:


| phase_out_X Phase.txt load out_record out_fmt out_eqn { " %9.0f" = Xi; 	" %11.5f" = X; 	" %11.5f" = Get(phase_ycalc); 	" %11.5f" = Ycalc; 	" %11.5f" = Yobs; 	" %11.5f\n" = Get(weighting); } |
| --- |

[pk_xo E]

Applied to all phase types except for xo_Is phases; provides a mechanism for transforming peak position to an x-axis position. For example, the peak position for neutron time-of-flight data is typically calculated in time-of-flight space, tof, or,

tof = t0 + t1 dhkl + t2 dhkl2

where t0 and t1 and t2 are diffractometer constants. See examples tof_balzar_sh1.inp and tof_balzar_br1.inp.

[phase_name $phase_name]

The name given to a phase; used for reporting purposes.

[phase_penalties $sites N]...[hkl_Re_Im #h #k #l #Re #Im]...

[accumulate_phases_and_save_to_file $file]

[accumulate_phases_when !E]

phase_penalties for a single hkl is defined as follows:

where s assigned phase, c = calculated phase, Ic = calculated intensity and d is the reflection d-spacing. The name N returns the sum of the phase_penalties and it can be used in equations and in particular penalty equations. c is calculated from sites identified in $sites.

#h, #k, #l are user defined hkls; they are used for formulating the phase penalties. #Re and #Im are the real and imaginary parts of s. An example usage of phase penalties (see examples ae14-12.inp and ae5-auto.inp) is as follows:


| penalty = pp1; phase_penalties * pp1 load hkl_Re_Im { 0   1   2   1  0 1   0  -2   1  0 1  -2  -1   1  0 } |
| --- |

hkls chosen for phase penalties should comprise those that are of high intensity, large d-spacing and isolated from other peaks to avoid peak overlap. Origin defining hkls are typically chosen.

accumulate_phases_and_save_to_file saves the average phases collected to $file. Phases are collected when accumulate_phases_when evaluates to true; accumulate_phases_when defaults to true. Here’s an example use:


| load temperature { 1 1 1 1 10 }    move_to_the_next_temperature_regardless_of_the_change_in_rwp accumulate_phases_and_save_to_file SOME_FILE.TXT accumulate_phases_when = T == 10; |
| --- |

Here phases with the best Rwp since the last accumulation are accumulated when the current temperature is 10.

[process_times]

Displays process times on termination of refinement.

[rand_xyz !E]

If continue_after_convergence is defined, then rand_xyz is executed at the end of a refinement cycle. It adds the vector u to the site fractional coordinate, the direction of which is random and the magnitude in Å is:

|u| = T rand_xyz

where T is the current temperature. To add a shift to an atom between 0 and 1 Å the following could be used:


| temperature 1 site... occ 1 C beq 1 rand_xyz = Rand(0,1); |
| --- |

Only fractional coordinates (x, y, z) that are independent parameters are considered.

[r_bragg #]

Reports on the R-Bragg value. R-Bragg is independent of hkl's and thus can be calculated for all phase types that contain phase peaks.

[rebin_with_dx_of !E]

[rebin_start_x_at !E]

Rebins the observed data (and SigmaYobs if it exists), see example clay.inp. It can be a function of the reserved parameter X as demonstrated in tof_bank2_1.inp. If rebin_with_dx_of evaluates to a constant, then the observed data is re-binned to equal x-axis steps. For observed data that is of unequal x-axis steps then re-binning provides a means of converting to equal x-axis steps. Some points about rebin_with_dx_of:

It changes the data.

It uses all data and uses it once.

Errors are similar if the fit to the new data is similar.

If a hat convolution is included in Ycalc then the fit is potentially the same.

rebin_with_dx_of creates a new x-axis with points determined by the rebin_with_dx_of equation, or,

x[i+1] = x[i] + rebin_with_dx_of

The new x-axis can be at x-axis intervals that are unequal. The position of the first x[i] value defaults to the start of the original x-axis; this can be changed using rebin_start_x_at. Intensities at the new x-axis are determined by the following integration:

Intensity at x[i] = Integrate Yobs from (x[i] + x[i-1])/2 to (x[i] + x[i+1])/2


| rebin_with_dx_of 0.02 hat 0.02 |
| --- |

[Rp #] [Rs #]

[scale E]

Rietveld scale factor; can be applied to all phase types.

[scale_pks E]...

Scales phase peaks; the following defines a Lorentz-Polarisation correction:


| scale_pks = (1 + Cos(c Deg)^2 Cos(2 Th)^2) / (Sin(Th)^2 Cos(Th)); |
| --- |

See LP_Factor, Preferred_Orientation and Absorption_With_Sample_Thickness_mm_Intensity macros.

[seed [#]]

Initializes the random number generator with a seed based on the computer clock. To initialize the random number generator at the pre-processor stage then use #seed.

[site $site [x E] [y E] [z E] ]...

[occ $atom E [beq E] [scale_occ E] ]...

[num_posns #] [rand_xyz !E] [inter !E #]

Defines a site where $site is a User defined string used to identify the site. x, y, and z define the fractional atomic coordinates, see also section 20.28. occ and beq defines the site occupancy factor and the equivalent isotropic temperature factor respectively. $atom corresponds to a valid atom symbol or isotope contained in the file ATMSCAT.TXT for x-ray data and NEUTSCAT.TXT for neutron_data. num_posns corresponds to the number of unique equivalent position generated from the space group; it is updated on refinement termination. inter corresponds to the sum of all GRS interactions which are a function of the site. The value of inter can represent the site electrostatic potential depending on the type of GRS interactions defined. A site fully occupied by Calcium is written as:


| site Al1  x 0       y 0    z 0.3521  occ Ca+2 1    beq 0.3 |
| --- |

A site occupied by two cations is:


| site Fe2  x 0.9283  y 0.25 z 0.9533  occ Fe+3 0.5  beq 0.25                                      occ Al+3 0.5  beq 0.25 |
| --- |


| occ Pb+2 1    prm q1 1 min 1e-6    prm q2 1 min 1e-6    prm q3 1 min 1e-6    prm q4 1 min 1e-6    scale_occ = q1 / D_spacing + 1 / (q2 H^2 + q3 K^2 + q4 L^2); |
| --- |


| site Pb occ Pb+2 1   beq 1 site Pb occ Pb+2 0.5 beq 1 scale_occ 2 |
| --- |

scale_occ works with magnetic data, neutron data, x-ray data etc. but not PDF data.

Symmetry: The user is responsible for obeying symmetry. If not working in P1 then the Multiplicities_Sum macro could be used. The spherical_harmonics_hkl keyword can also be used, for example:


| spherical_harmonics_hkl sh sh_order 6 site Pb occ Pb+2 1 beq 1 prm q 1 min 1e-6 scale_occ = q sh; |
| --- |

[sites_distance N] | [sites_angle N] | [sites_flatten N [sites_flatten_tol !E]]...

[site_to_restrain $site [ #ep [ #n1 #n2 #n3 ] ] ]...

When used in equations the name N of sites_distance and sites_angle returns the distance in Å between two sites and angle in degrees between three sites respectively. The sites considered are defined by site_to_restrain. N can be used in penalty equations to restrain bond lengths. N of sites_flatten returns a restraint term that decreases as the sites become coplanar; it is defined as follows:

where tol corresponds to sites_flatten_tol, n corresponds to the number of sites defined by site_to_restrain, b are Cartesian unit length vectors between the sites and the geometric center of the sites.

#eq, #n1, #n2 and #n3 correspond to the site equivalent position and fractional offsets to add to the sites. This is useful if the structure is already known and constraints are required, for example, in the bond length output (see append_bond_lengths):

Zr1:0  O1:20  0  0 -1  2.08772

O1:7   0 -1  0  2.08772  89.658

O1:10  0  0 -1  2.08772  90.342   90.342

O1:15 -1  0  0  2.08772  180.000  89.658   89.658

O1:18 -1  0  0  2.08772  90.342   89.658   180.000 90.342

P1:0   O1:4   0  0  0  1.52473

O1:8   0  0  0  1.52473  112.923

O1:0   0  0  0  1.52473  112.923  112.923

O2:0   0  0  0  1.59001  105.749  105.749  105.749

Example constraints using macros looks like:


| Angle_Restrain(O1 P1 O1 8, 112, 112.92311, 0, 0.001) Angle_Restrain(O1 18 -1 0 0 Zr1 O1 10 0 0 -1, 89, 89.65750, 0, 0.001) Distance_Restrain(Zr1 O1 20 0 0 -1, 2.08, 2.08772, 0, 1) |
| --- |

benzene.inp demonstrates the use of the restraint macros Distance_Restrain, Angle_Restrain and Flatten. OpenGL viewing is recommended. Note, for more than ~6 sites then sites_flatten becomes computationally expensive.

[sites_geometry $Name]...

[site_to_restrain $site [ #ep [ #n1 #n2 #n3 ] ] ]...


| sites_geometry some_name load site_to_restrain { C1 C2 C3 C4 } |
| --- |

If $Name contains only two sites, then only Sites_Geometry_Distance($Name) can be used. Three sites defined additionally allows the use of Sites_Geometry_Angle($Name) and four sites defined additionally allows the use of Sites_Geometry_Dihedral_Angle($Name).

[siv_s1_s2 # #]

Defines the s1 and s2 integration limits for the spherical interaction volume of the GRS series.

[smooth #num_pts_left_right]

Performs a Savitzky-Golay smoothing on the observed data. The smoothing encompasses (2 * #num_pts_left_right + 1) points.

[spherical_harmonics_hkl $name]...

[sh_Cij_prm $Yij E]...

[sh_alpha !E]

[sh_order #]

Defines a hkl dependent symmetrized spherical harmonics series (see section 20.30.1) with a name of $name. When $name is used in equations, it returns the value of the associated spherical-harmonics series.

sh_alpha corresponds to the angle in degrees between the polar axis and the scattering vector; sh_alpha defaults to zero degrees which is required for symmetric reflection as is the case for Bragg-Brentano geometry.

sh_order corresponds to the order of the spherical harmonic series which are even numbers ranging from 2 to 8 for non-cubic and from 2 to 10 for cubic systems.

The PO_Spherical_Harmonics macro simplifies the use of spherical_harmonics_hkl. clay.inp demonstrates the use of spherical_harmonics_hkl for describing anisotropic peak shapes.

[stacked_hats_conv [whole_hat E [hat_height E]]...[half_hat E [hat_height E]...]...

Defines hat sizes for generating an aberration function comprising a summation of hats. whole_hat defines a hat with an x-axis extent of whole_hat/2. half_hat defines a hat with an x-axis range of half_hat to zero if half_hat<0; or zero to half_hat if half_hat> 0. hat_height defines the height of the hat; it defaults to 1. stacked_hats is used for example to describe tube tails using the Tube_Tails macro.

[start_X !E] [finish_X !E]

Defines the start and finish x-axis region to fit to.

[str | dummy_str]...

Defines a new structure node.

[str_hkl_angle N #h #k #l]...

Defines a parameter name N and a vector normal to the plane defined by h, k and l. When the parameter name is used in an equation, it returns angles (in radians) between itself and the normal to the planes defined by hkls.

[suspend_writing_to_log_file #1]

When num_runs > 0, then, by default, output to TOPAS.LOG (or TC.LOG if running TC.EXE) is suspended after the first run (Run_Number == 0). suspend_writing_to_log_file changes this behaviour.

[temperature !E]...

[move_to_the_next_temperature_regardless_of_the_change_in_rwp]

[save_values_as_best_after_randomization]

[use_best_values]

A temperature regime has no effect unless the reserved parameter T is used in val_on_continue attributes, or, if the temperature dependent keywords rand_xyz or randomize_on_errors are used. randomize_on_errors automatically determine parameter displacements without the need for rand_xyz or val_on_continue. It performs well on a wide range of problems. The reserved parameter T returns the current temperature. The first temperature defined becomes the starting temperature; subsequent temperature(s) become the current temperature. If  increases relative to a previous cycle, then the temperature is advanced to the next temperature. If  decreases relative to previous temperatures of lesser values, then the current temperature is rewound to a previous temperature such that its previous is of a greater value. move_to_the_next_temperature_regardless_of_the_change_in_rwp forces the refinement to move to the next temperature regardless of the change in Rwp from the previous temperature. save_values_as_best_after_randomization saves the current set of parameters and gives them the status of “best solution”. Note, this does not change the global “best solution” which is saved at the end of refinement. use_best_values replaces the current set of parameters with those marked as “best solution”. The temperature regime defined in the Auto_T macro is sufficient for most problems. A typical temperature regime starts with a high value and then a series of annealing temperatures, for example:


| temperature 2 move_to_the_next_temperature_regardless_of_the_change_in_rwp temperature 1 temperature 1 temperature 1 |
| --- |

If the current temperature is the last one defined (the fourth one), and  decreased relative to the second and third temperatures, then the current temperature is set to the second temperature. The current temperature can be used in all equations using the reserved parameter T, for example:


| x @ 0.123 val_on_continue = Val + T Rand(-.1, .1); |
| --- |

The following temperature regime will allow parameters to randomly walk for the first temperature. At the second temperature the parameters are reset to those that gave the "best solution".


| temperature 1 temperature 1 use_best_values temperature 1 temperature 1 use_best_values temperature 1 temperature 10    save_values_as_best_after_randomization    move_to_the_next_temperature_regardless_of_the_change_in_rwp |
| --- |

Note, that when a "best solution" is found, the temperature is rewound to a position where the temperature decreased. For example, if the Rwp dropped at lines 2 to 5 then the next temperature will be set to "line 1". The following temperature regime will continuously use the "best solution" before randomisation; it has a tendency to remain in a false minimum.


| temperature 1 use_best_values |
| --- |

[th2_offset E]...

Used for applying 2 corrections to phase peaks. The following applies a sample displacement correction:


| th2_offset = -2 Rad (c) Cos(Th) / Rs; |
| --- |

th2_offset is used for example in the Zero_Error and Specimen_Displacement macros.

[user_defined_convolution E min E max E]...


| str ... prm k 10 min 0.001 max 100 user_defined_convolution = If(Abs(X) < 10^(-10), 1, (Sin(k X) /(k X))^2); min -3 max 3 |
| --- |

[use_tube_dispersion_coefficients]

Forces the use of Laboratory tube anomalous dispersion coefficients, see section 20.9.

[verbose #1]...

A value of 1 instructs the kernel to output in a verbose manner. A value of 0 reduces kernel output such that text output is initiated at the end of a refinement cycle. A value of -1 reduces kernel output further such that text output is initiated every second in time and only Rwp values at the end of a refinement cycle is kept. The Simulated_Annealing_1 macro has verbose set to -1; this ensures that long simulated annealing runs do not exhaust memory due to saving Rwp values in text output buffers.

[view_structure]

Informs the GUI to display the structure.

[weighting !E  [recal_weighting_on_iter]]

Used for calculating the xdd dependent weighting function in . Can be a function of the reserved parameter names X, Yobs, Ycalc and SigmaYobs. The default is as follows:


| weighting = 1 / Max(Yobs, 1); |
| --- |

In cases where weighting is a function of Ycalc then recal_weighting_on_iter can be used to recalculate the weighting at the start of refinement iterations. Otherwise, the weighting is recalculated at the start of each refinement cycle. Note that some goodness of fit indicators such as r_wp are a function of weighting, see Table 4-2.

[x_calculation_step !E]

Calculation step used in the generation of phase peaks and fit_obj’s. Peak_Calculation_Step is the actual step size used. For an x-axis with equidistant steps and x_calculation_step not defined then:

Peak_Calculation_Step =  “Observed data step size” / convolution_step

otherwise

Peak_Calculation_Step =  x_calculation_step / convolution_step

x_calculation_step can be a function of Xo and Th. In some situations, it may be computationally efficient to write x_calculation_step in terms of the function Yobs_dx_at and the reserved parameter Xo. It is also mandatory to define x_calculation_step for data with unequal x-axis steps (*.XY or *.XYE data files). Example usage:


| x_calculation_step 0.01 x_calculation_step = 0.02 (1 + Tan(Th)); x_calculation_step = Yobs_dx_at(Xo); |
| --- |

[xdd $file [{ $data }] [range #] [xye_format] [gsas_format] [fullprof_format] ]...

[gui_reload]

[gui_ignore]


| xdd pbso4.raw |
| --- |

The following will refine on the third range:


| xdd pbso4.raw range 3 |
| --- |

To read data directly from an INP file, the following can be used:


| xdd { 1 1 10  ‘ start, step and finish (equidistant data) 1 2 3 4 5 6 7 8 9 10  } |
| --- |


| xdd { _xy ‘ switch indicating x-y format 0.1 1   0.2 2   ... } |
| --- |

When in Launch mode; data files by default are not reloaded if already loaded. gui_reload forces the reload of the data file. Data files are loaded/reloaded into the GUI under the following circumstances:

The data file is not loaded into the GUI

Any of the following keywords have been used at the xdd level:

gui_reload, rebin_with_dx_of, smooth, yobs_eqn, yobs_to_xo_posn_yobs

[xdd_out $file [append] ]...

Used for writing xdd dependent details to file. The out_eqn can contain the reserved parameter names of X, Yobs, Ycalc and SigmaYobs. See out for a description of out_record. The Out_Yobs_Ycalc_and_Difference macro is a good example of using xdd_out.

[xdd_scr  $file] ...

[dont_merge_equivalent_reflections]

[dont_merge_Friedel_pairs]

[ignore_differences_in_Friedel_pairs]

[str]...

[auto_scale !E]

[i_on_error_ratio_tolerance #]

[num_highest_I_values_to_keep #num]

xdd_scr defines single crystal data from the file $file. The file can have extensions of *.HKL for ShelX HKL4 format or *.SCR for SCR format. All xdd and str keywords that are not dependent on powder data can be used by xdd_scr. Single crystal data is internally stored in 2 versus Fo2 format; this allows the use of start_X, finish_X and exclude keywords; a lam definition is required.

|Fo| >  i_on_error_ratio_tolerance | Sigma(Fo) |

num_highest_I_values_to_keep removes all hkl’s except for #num hkl’s with the highest Fo values. An example input segment for single crystal data refinement is as follows:


| xdd_scr ylidm.hkl MoKa2(0.001) finish_X 35 weighting = 1 / (Sin(X Deg / 2) Max(1, Yobs)); STR(P212121)    a  5.9636    b  9.0390    c  18.3955    scale @ 1.6039731906    i_on_error_ratio_tolerance 4    site S1  x @ 0.8090  y @ 0.1805  z @ 0.7402  occ S 1  beq 2    site O1  x @ 0.0901  y @ 0.8151  z @ 0.2234  occ O 1  beq 2    ... |
| --- |

The SCR format is white space delimited and consists of entries of h, k, l, m, d, 2, Fo2 which is the format outputted by the Create_hklm_d_Th2_Ip_file macro.

[xo_Is]...

[xo E  I E]...

Defines a phase type that uses x-axis space for generating peak positions, see example xois.inp. xo corresponds to the peak position, and I is the intensity parameter before applying scale_pks equations.

[yobs_eqn !N E min E max E del E]

Observed data is created via an equation; this is useful for approximating functions. The name !N given to the equation is used for identifying the plot in the GUI.

[yobs_to_xo_posn_yobs !E]


| yobs_to_xo_posn_yobs = Peak_Calculation_Step; |
| --- |
