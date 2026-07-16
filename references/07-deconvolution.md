# Deconvolution


```
[A0_matrix_is_constant]
[Xo_Is]...
    [create_pks_name $a_name]
[create_pks_fn $fn_name]
```

Examples: `test_examples\deconvolution\pbso4-decon.inp`

The deconvolution method of Coelho (2018) has been implemented using three macros in TOPAS.INC: Deconvolution_Init, Deconvolution_Bkg_Penalty and Deconvolution_Intensity_Penalty. The method refines linear parameters only; peak intensities and background parameters – whose derivatives are constant, so the A0 matrix does not change. The keyword A0_matrix_is_constant signals this to the program, causing the A0 matrix to be calculated only once. Using A0_matrix_is_constant with quick_refine, approximate_A, chi2, or non-linear parameters are being refined, will throw an exception.

create_pks_name is a xo_Is dependent keyword that creates a peak at each step x-axis step, with peak intensity parameter names prefixed by $a_name. Peaks are not created if they already exist for the xo_Is phase. If the '$' character is placed immediately after create_pks_name and if create_pks_name is within a macro, then the output from create_pks_name is placed after the macro. create_pks_fn additionally appends a penalty to each peak with the penalty being written in terms of a function called fn_name. The OUT file is updated with peaks resembling:

| xo 5.00 I a25_ 0.00217` penalty = dfn(5,a25_,a26_); xo 5.02 I a26_ 0.00000` penalty = dfn(5.02,a26_,a27_); xo 5.04 I a27_ 0.00000` penalty = dfn(5.04,a27_,a28_); |
| --- |

The dfn function takes as arguments the x-axis position of the peak and two intensity parameter names - one at the x-axis position and one at the next. These keywords and functions are used in macros as follows:


| Deconvolution_Init(0.5) xdd … Deconvolution_Bkg_Penalty(0.5) xo_Is Deconvolution_Intensity_Penalty(a, afn) |
| --- |

The deconvolution process comprises three separate refinement runs: 1) fitting the peaks to the diffraction pattern with peak shapes fixed to expected peak shapes; 2) creating a calculated pattern with a chosen peak shape, typically a peak shape comprising specimen contributions; and 3) a final run to produce a deconvoluted pattern with noise. The pbso4-decon.inp example is ready to run, it can be used as a template for other deconvolution processes; it is defined as:


| #define DO_REFINEMENT_      ' Step 1 ‘#define DO_SPECIMEN_OUT_    ' Step 2 ‘#define DO_FINAL_DECON_     ' Step 3 macro Data_File { Pbso4 }		 #ifdef DO_FINAL_DECON_ 	RAW(..\##Data_File) ' load for comparison purposes 	xdd Data_File##-decon-specimen.xy 		x_calculation_step 0.025 		user_y d1 Data_File##-decon-specimen.xy 		user_y d2 Data_File##-diff.xy 		fit_obj = d1 + d2; 		Out_X_Ycalc(Data_File##-decon-final.xy) ‘ Final deconvoluted pattern #else 	Deconvolution_Init(0.5) 	RAW(..\##Data_File) 		start_X 15 		bkg @ 0 0 0 0 0 0 0 		Deconvolution_Bkg_Penalty(0.5) 		‘LP_Factor(17) ‘ Do not include when doing deconvolution 		CS_L(262.73494) 		Strain_L(0.03785) 		#ifdef DO_SPECIMEN_OUT_ 			iters 0 			CuKa1(0.0001) 			Out_X_Ycalc(Data_File##-decon-specimen.xy) 		#else ' DO_REFINEMENT_ 			Out_X_Difference(Data_File##-diff.xy) 			CuKa5(0.0001) 			Radius(173) 			Full_Axial_Model(10, 10, 10, 4.13679, 4.13679) 			Divergence(1) 			Slit_Width(0.2) 		#endif 		xo_Is 			Deconvolution_Intensity_Penalty(a, dfn) 	#endif |
| --- |

Background should be less than all observed data and it should be graphically inspected during step 1. Background can be reduced by decreasing the c parameter of the Deconvolution_Bkg_Penalty macro; this parameter can range from 0.05 to 1. If the bases of the peaks do not match Yobs, the background is still too high. Steps 1 and 2 produce output XY files which are then used in step 3. The exclusion of LP_Factor, and similar peak scaling parameters, is important as peak intensities are used in a penalty inside the Deconvolution_Intensity_Penalty macro. The deconvolution process can be used for all types of data including neutron TOF; step (1) takes approximately 10 to 30 seconds on present laptops; steps (2) and (3) takes a trivial amount of time (< 1s). The deconvolution macros are as follows:


| macro Deconvolution_Init(c) { process_times A0_matrix_is_constant       ‘ All parameters are linear penalties_weighting_K1 = c; ‘ A value of 0.5 seems sufficient save_best_chi2              ‘ We want best Chi2; not best Rwp chi2_convergence_criteria 1e-5 continue_after_convergence  ‘ ~100 iterations is typically sufficient (~20s) pen_weight 1                ‘ Override the default  } macro Deconvolution_Intensity_Penalty(i_name, fn_name) { fn fn_name(x, a0, a1) = (a0 - a1)^2 / ((a0 + a1) Yobs_at(x) + 1e-6);  default_I_attributes 1e-6 min 0 val_on_continue = Val Rand(0.99, 1.01);  create_pks_fn fn_name create_pks_name $ i_name } macro Deconvolution_Bkg_Penalty(& c, & w_min) { xdd_sum #m_unique pen = (Yobs - Get(bkg))^2 / Max(Get(bkg) Yobs, w_min^2); penalty = pen c;  } macro Deconvolution_Bkg_Penalty(& c) { Deconvolution_Bkg_Penalty(c, 1) } |
| --- |

pen_weight over-rides the default; the default works but with slower convergence. Note, both the peak intensity and Bkg penalties are Yobs scale invariant where scaling of Yobs does not change the magnitude of the penalties relative to . Yobs_at is a new function that returns the value of Yobs at x. w_min in the Deconvolution_Bkg_Penalty macro allows for the setting of the expected minimum of Yobs*Bkg; a value of 1 for counting statistics. For XYE files, where Yobs is small and where SigmaYobs is used (tof data for example), then w_min should be reduced.


## Deconvolution – Simulated pattern

A simulated pattern was created with noise using sim-create.inp and the instrument contribution deconvoluted using sim-decon.inp; the latter INP file looks like:


| /*	Three runs to produce the deconvoluted pattern.  	The name of the final deconvoluted pattern is:  		pbso4-decon-final.xy  	Define one at a time in the following:  		#define DO_REFINEMENT_   ‘ Run 1 		#define DO_SPECIMEN_OUT_ ‘ Run 2 		#define DO_FINAL_DECON_  ‘ Run 3  */ #define DO_REFINEMENT_	 	' Step 1 ‘#define DO_SPECIMEN_OUT_	' Step 2 ‘#define DO_FINAL_DECON_	' Step 3, Clear the GUI first   macro Data_File { Sim }		 #ifdef DO_FINAL_DECON_ 	xdd Data_File##-calc-rand.xy ' load for comparision purposes  	xdd Data_File##-calc-narrow.xy 		user_y d1 Data_File##-decon-specimen.xy 		user_y d2 Data_File##-diff.xy 		fit_obj = d1 + d2; 		Out_X_Ycalc(Data_File##-decon-final.xy) #else						 	Deconvolution_Init(0.5) 	xdd Data_File##-calc-rand.xy 		bkg @  259.381081  89.8339877  31.6429117 -34.4743462   				 34.3097757 -55.7270435  30.631573 		Deconvolution_Bkg_Penalty(0.1)  		/* Specimen */ 		CS_L(300) 		CS_G(300) 		Strain_L(0.05) 		Strain_G(0.05)  		#ifdef DO_SPECIMEN_OUT_ 			iters 0 			CuKa1(0.001) 			Out_X_Ycalc(Data_File##-decon-specimen.xy) 		#else ' DO_REFINEMENT_ 			num_cycles 20 			Out_X_Difference(Data_File##-diff.xy)  			/* Instrument */ 			CuKa2(0.001) 			Radius(217) 			Full_Axial_Model(12, 12, 12, 2.3, 7) 			Divergence(1) 			Slit_Width(0.1) 			Absorption(60) 		#endif 		xo_Is 			Deconvolution_Intensity_Penalty(a, dfn) #endif |
| --- |

The following figure is the deconvoluted pattern (green line, bottom plot) compared with the expected deconvoluted pattern (red line on top of green line). The top plot (blue line) is the original simulated pattern with noise and without noise (red line on top of blue line).

Parameter errors determined from refinement using the deconvoluted pattern are almost identical to errors produced using the original pattern, see Coelho (2018).
