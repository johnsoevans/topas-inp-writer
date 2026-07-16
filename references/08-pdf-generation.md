# PDF-Generation


```
[xdd...]
    [rebin_with_dx_of  !E]
    [pdf_generate {
        [dr  !E]
        [r_max  !E]
        [gr_sst_file  = "File";]
        [hat !E [ num_hats !E]
        [gr_to_fq !E]
    }]
```
Examples: `test_examples\PDF\GENERATE\` — `Fullerene\DECON.INP`, `LIFEPO4\DECON.INP`, `Silicon\DECON.INP`, `Tungsten\DECON.INP`

PDF generation applies an inverse sine transform to an ideal diffraction pattern in which background is absent, atomic scattering factors are constant, and 2θ and peak shapes are symmetric. The task is therefore to correct real data to match this ideal pattern as closely as possible. Corrections include background determination, atomic scattering factors (for X-ray data), Lorentz polarisation, and peak shape asymmetry; for details see Coelho et al. (2021). A deconvolution process similar to that described in section 7 is used, allowing corrections in reciprocal space for peak asymmetry, instrument and emission profile aberrations, Lorentz polarisation, and atomic scattering factors. The process comprises two operations defined in a single INP file:

0) Fit to the reciprocal space diffraction pattern - (Operation 0)

1) Generate G(r) - (Operation 1)

1.0) Generate ideal pattern Ideal (2q) from the parameters determined in step 0.

1.1) Convert Ideal (2q) to Q space to form Ideal(Q).

1.2) Fit a polynomial to Ideal(Q) and save F(Q) = Ideal(Q) – Poly)

1.3) Generate G(r) from F(Q)


## PDF-Generating - LiFePO4

Operation 0 fits the pattern following the deconvolution process of Coelho (2018). Lattice parameters are not required. A peak is placed at each data point together with a background and appropriate penalty functions. Approximate peak shapes from a preliminary peak-fitting analysis (using a standard, for example) are recommended; once determined, peak shapes are not refined. The data-entry section of a typical INP file (see LiFePO4\decon.inp) is as follows:


| Include_PDF_Generate '------------------------------------------------------ '              START USER INPUT SECTION '------------------------------------------------------ macro Data_File         { LFP_0-8Kcap_AgFGM_2x4soll_Eiger1D_8h.xy } macro Capillary_Scan    { capillary.xy }   macro Capillary_Rebin   { 0.1 } ' Smooth the capillary scan. Zero means no smoothing. #prm operation = 0; ' Set to 0 to fit to reciprocal space data                     ' Set to 1 to generate F(Q) and G(r)                     ' Set to 2 to fit structure to G(r) #prm use_narrow_peak_shape  = 1; ' A 0 means use full peak shapes in generating G(r) '------------------------------------------------------ ' Inputs for reciprocal space fit, operation = 0 macro & Average_f           { f0_Li + f0_Fe + f0_P + 4 f0_O } ' formula of unit cell #prm lab_no_monochromator   = 1; ' Set to 1 if using Laboratory instrument. #prm use_Xo_Is_phase        = 1; ' Set to 0 if not fitting peaks #prm use_bkg_penalty        = 1; #prm use_simple_bkg_penalty = 1; ' Set to 1 if counting statistics is not right,                                   ' or, maybe when there's Fluorescence. macro & Bkg_Weighting               { 1 } macro & Intensity_Penalty_Weighting { 1 } macro & Scale_Peaks   { 1 } ' Useful if capillary absorption is inhibiting fitting. macro & Scale_Yobs_By { 1 } ' Useful if data does not obey counting statistics. prm pc0  1   ‘ Poly_Capillary coefficients; comment out if prm pc1  0   ' not using Capillary as background. inp_text fluorescence_bkg    {       bkg @ 3.49160163` -0.96682842`  0.292687899`    } inp_text fit_extra     {       penalty = 10000 (Bkg_at(X2) + (pc0 + pc1) Value_at_X(cap_, X2) - Yobs_at(X2))^2;    } macro Start_X       { 2.4  } macro Finish_X      { 103  } macro Step_X        { 0.02 } ' Set to zero to use measured step size.                               ' Set to non-zero if scale_yobs_by is used.                              ' Set to non-zero if unequal x-axis steps. ‘-------------------------------------------------------------- ' Inputs for generating F(Q), operation = 1 #prm poly_fq = 7;  ' Number of parameters for Poly when fitting Poly to F(Q).                    ' View F(Q) plot, it needs to look right. macro & Qmin                  { 0.1 } macro & Qmax                  { 17.5 } macro & Soper_Lorch_Constant  { 0 } ' best not to use macro & Exp_Constant          { 0 } ' best not to use macro & Lorch_Constant        { 0 } ' best not to use inp_text fq_poly     {       bkg @  0 0 0 0 0 0 0 0  0    } macro FQ_Bkg_Penalty    {       weighting = If(X > (X2 - 1), 10, 1); ' Weigh the F(Q) data more at Qmax       penalty   = Bkg_at(X1)^2;            ' Restrain F(Q=0) to 0    } ‘-------------------------------------------------------------- ' Inputs for generating G(r) from F(Q), operation = 1 macro R_Max         { 100 } macro dR            { 0.01 } macro Num_Hats      { 3 } ' Best smoothing function for speed and accuracy macro & Hat_Size    { 4.4934 / Qmax }    ‘-------------------------------------------------------------- ' Reciprocal space peak details, operation = 0 macro Full_Emmision_Profile    {       lam ymin_on_ymax 0.001          la 1 lo 0.5609 lg 1e-6          la 0.55150 lo 0.5649441 lg 1e-6    } macro Deconvoluted_Emmision_Profile    {       lam ymin_on_ymax 0.0005 la 1 lo 0.5609 lg 1e-6    } macro Full_Peak_Shape_Specimen     {       CS_G(, 70)       CS_L(, 45)       Strain_L(, 0.042)       Strain_G(, 0.42)    } macro Full_Peak_Shape    {       Full_Peak_Shape_Specimen       Full_Axial_Model(10,10,10, 2.3, 5.73430)    } macro Deconvoluted_Peak_Shape    {       Deconvoluted_Emmision_Profile       #if (use_Xo_Is_phase == 0)          ' Using (Yobs - background); ie. no peak shape       #elseif (use_narrow_peak_shape)          ' Use Narrow peak shape          ZE(, -0.00730929318) ‘ Set to negative of Rietveld fit          gauss_fwhm 0.05       #else ‘ Use Full peak shape specimen          Full_Peak_Shape_Specimen          ZE(, -0.00730929318) ‘ Set to negative of Rietveld fit       #endif    } macro & LP_Factor_    {       #if (lab_no_monochromator)          (1 + Cos(X Pi/ 180)^2)       #endif       1 / (Sin(X Pi/360)^2 Cos(X Pi/360)) ' Lorentz factor    } '------------------------------------------------------ '              END USER INPUT SECTION '------------------------------------------------------ Include_PDF_Generate_Common '------------------------------------------------------ #if (And(use_Xo_Is_phase, Run_Number == 0, Or(fit_to_data, generate_fq_gr_from_fit)))    xo_Is       PDF_Generation_Intensity_Penalty(a,dfn, Intensity_Penalty_Weighting, Scale_Peaks) #endif '------------------------------------------------------ |
| --- |

Input is required for items such as data file names. It is best to create a new directory for each data file. The PDF-Generate.INC file, included via the Include_PDF_Generate macro, contains PDF-generation-specific macros. Capillary_Scan is the name of the file corresponding to a scan of the empty capillary holder. As the capillary scan is typically collected quickly and has poor counting statistics, Capillary_Rebin can be used to smooth it. Setting the #prm operation to 1 instructs the program to perform the fitting process. Setting use_narrow_peak_shape to 1 uses narrow peaks in the generation of Ideal(2θ) (operation 1.0), removing peak broadening as a function of 2θ.


### Operation 0 – Fitting peaks to the diffraction pattern

Background = Poly_Capillary * Capillary_Scan + Poly_Fluorescence

(Poly_Capillary(X2) * Capillary_Scan(X2) + Poly_Fluorescence(X2) – Yobs_at(X2))2

X2 is the reserved parameter name corresponding to the end of the diffraction pattern. Poly_Capillary at X2 is simply (pc0 + pc1), see the X0_ macro in PDF-Generate_Common.INC, and Poly_Fluorescence(X2) corresponds to Bkg_at(X2). The penalty therefore looks like:


| inp_text fit_extra     {       penalty = 10000 (Bkg_at(X2) + (pc0 + pc1) Value_at_X(cap_, X2) - Yobs_at(X2))^2;    } |
| --- |

The fit for LiFePO4 looks like:


| user_y data_file Data_File yobs_eqn data.sst = data_file Scale_Yobs_By; min = Start_X; max = Finish_X; del = Step_X; |
| --- |

Note, user_y can also be a function of the reserved parameter X. The input created for the Kernel can be viewed in TOPAS.LOG.


### Operation 1 – Generation G(r) from the fitted peaks

The Average_f macro is used to calculate the average atomic scattering factor <f> for operation 1.0. For X-ray data, a rough estimate of the atomic species is helpful; for neutron data an estimate is not required. Applying smoothing functions on F(Q) such as the Lorch and Soper-Lorch functions is not recommended. Instead, applying three hat convolutions directly to G(r) is faster and more accurate. At operation 1.1 the ideal pattern is converted to Q space. Operation 1.2 generates F(Q) by fitting a polynomial to Ideal(Q) where:

F(Q) = Ideal(Q) – Poly_FQ

Changing fq_poly and rerunning operation 1 updates the four plots; this updating is achieved using the keyword gui_reload. Using the structure of LiFePO4, the generated G(r) can be fitted-to by setting operation=2. With use_narrow_peak_shape=0 we get:

The grey line at the center of the plot is a correction added to the calculated G(r) using:


| fit_obj = a1 Cos(a2 X + a3) / X; |
| --- |

If this grey line is significant in intensity, then the value of F(Q=0) is incorrect. Controlling the behaviour of F(Q) at the start and end of the Q range can be done from the FQ_Bkg_Penalty macro. For example, F(Q=0)=0 can be set using the following penalty:


| penalty = Bkg_at(X1)^2; |
| --- |

For operation 1; intermediate pre-processed text fed to the kernel can be sent to TOPAS.LOG (or TC.LOG) for viewing by setting suspend_writing_to_log_file to 0. For the current example, TOPAS.LOG for the operation 1.0 part is as follows (comments added):


| iters 0 yobs_eqn aac.sst = 1; min 0.01 max = 103; del 0.0025    gui_ignore     Out_XDD_SST(decon.sst) ‘ Not expanded for clarity       ‘ Output Ycalc / (polarization * <f>)       = Ycalc / (( (1 + Cos(X 3.14159265358979/ 180)^2) 1 / (Sin(X 3.14159265358979/360)^2 Cos(X 3.14159265358979/360))) (f0__( 0.974637,0.158472,0.811855,0.262416,0.790108,0.002542,4.334946,0.342451,97.102966,201.363831,1.409234 ) + f0__( 12.311098,1.876623,3.066177,2.070451,6.975185,-0.304931,5.009415,0.014461,18.743040,82.767876,0.346506 ) + f0__( 1.950541,4.146930,1.494560,1.522042,5.729711,0.155233,0.908139,27.044952,0.071280,67.520187,1.981173 ) + 4 f0__( 2.960427,2.508818,0.637853,0.722838,1.142756,0.027014,14.182259,5.936858,0.112726,34.958481,0.390240 ))^2);     lam ymin_on_ymax 0.0005 la 1 lo 0.5609 lg 1e-6    th2_offset = (-0.00730929318);     gauss_fwhm 0.05 ‘ Use narrow deconvoluted peak    xo_Is       extra_X_left = Max(X1 - Max(X1 - 1, 0.1), 0);        extra_X_right = Max(Min(X2 + 1, 179.9) - X2, 0);        fn dfn (x, a0, a1) = (a0 - a1)^2 / Max(a0 + a1, 1e-6);        default_I_attributes 1e-6 min 0 val_on_continue = Val Rand(0.5, 2) + 1e-4;        create_pks_fn dfn create_pks_name $ a       xo 1.40009871 I a50_ 0.0178524321`       xo 1.42009871 I a50_ 0.0178524321`       xo 1.44009871 I a50_ 0.0178524321`       … |
| --- |

The actual generation of G(r) occurs when Run_Number = 3; its INP text looks like:


| iters 0 	xdd fq.sst 		gui_reload 		lam ymin_on_ymax 0.0005 la 1 lo 0.5609 lg 1e-6 		rebin_with_dx_of 0.001 		pdf_generate { 			dr = 0.01; 			r_max = 100; 			gr_sst_file = "gr"; 			hat = 4.4934 / (17.5); num_hats = 3; 		} |
| --- |


### Correcting the PDF due to a zero error in reciprocal space


### Generating F(Q) from G(r) - gr_to_fq

The LIFEPO4\GR-TO-FQ.INP file creates G(r) from an F(Q) file at Run_Number 0, then in Run_Number 1 it uses the newly created G(r) to reproduce the original F(Q) using gr_to_fq. The INP file is as follows:


| num_runs 3  #if (Run_Number == 0)      xdd fq-original.sst        rebin_with_dx_of 0.005       lam ymin_on_ymax 0.0005 la 1 lo 0.5609 lg 1e-6       pdf_generate {           dr = 0.01;           r_max = 300;           gr_sst_file = "gr-from-fq";        }  #elseif (Run_Number == 1)      xdd gr-from-fq.sst        gui_ignore       lam ymin_on_ymax 0.0005 la 1 lo 0.5609 lg 1e-6       pdf_generate {           dr = 0.00125;           r_max = 17.5;           gr_sst_file = "fq-from-gr";           gr_to_fq 1       }  #elseif (Run_Number == 2)      xdd fq.sst        rebin_with_dx_of 0.01       user_y fq_from_gr fq-from-gr.sst                prm a 1 min 1e-6        fit_obj = fq_from_gr a;  #endif |
| --- |

Run_Number 3 fits the newly created F(Q) to the original F(Q); the result showing the reproduced F(Q) (in red) and the original F(Q) (in blue) has a small difference plot as seen in the following:


### PDF-Generation - Fullerene

In this example G(r) from TOPAS is compared to G(r) from GudrunX for Fullerene. The INP file is:


| Include_PDF_Generate '------------------------------------------------------ '              START USER INPUT SECTION '------------------------------------------------------ macro Data_File        { i15-1-20401_tth_det2_0.xy } macro Capillary_Scan   { i15-1-20398_tth_det2_0.xy} macro Capillary_Rebin  { 0 } ' Smooth the capillary scan. Zero means no smoothing #prm operation = 1; ' Set to 0 to fit to reciprocal space data                     ' Set to 1 generate F(Q) and G(r)                     ' Set to 2 to fit structure to G(r)  #prm use_narrow_peak_shape  = 1; ' Use narrow peak shapes in the generating G(r) '------------------------------------------------------ ' Inputs for reciprocal space fit, operation == 0 #prm lab_no_monochromator   = 0; ' Set to 1 if using Laboratory instrument #prm use_Xo_Is_phase        = 0; ' Set to 0 if not fitting peaks #prm use_bkg_penalty        = 1; #prm use_simple_bkg_penalty = 1; ' Set to 1 if counting statistics is not right                                  ' or maybe when there's Fluorescence macro & Bkg_Weighting               { 1 } macro & Intensity_Penalty_Weighting { 1 } macro & Scale_Peaks   { 1 } ' Useful if capillary absorption is inhibiting fitting. macro & Scale_Yobs_By { 1 } ' Useful if data does not obey counting statistics.  prm pc0  1.09673044`     ‘ Multiplies Capillary by (pc0 + pc1 x0) prm pc1  0.146927936     ' Comment out if not using Capillary as background. inp_text fluorescence_bkg { } inp_text fit_extra    {       penalty = 10000 (Bkg_at(X2) + (pc0 + pc1) Value_at_X(cap_, X2) - Yobs_at(X2))^2;    } macro Start_X       { 0.6    } macro Finish_X      { 59.9   } macro Step_X        { 0.02 } ' Set to 0 to use measured step size.                              ' Set to non-zero if scale_yobs_by is use.                              ' Set to non-zero if unequal x-axis. '------------------------------------------------------ ' Input for generating F(Q) - operation == 1 macro & Average_f             { f0_C } macro & Qmin                  { 0.5 } macro & Qmax                  { 25  } macro & Soper_Lorch_Constant  { 1.1 } ' Used for comparison purposes macro & Exp_Constant          { 0 }     macro & Lorch_Constant        { 0 }     inp_text fq_poly     {       bkg @  0 0 0 0 0 0 0 0 0    } macro FQ_Bkg_Penalty  { } '------------------------------------------------------ ' Inputs for generating G(r) from F(Q), operation == 1 macro R_Max         { 50 } macro dR            { 0.01 } macro Num_Hats      { 0 } ' Best smoothing funcion for speed and accuracy macro & Hat_Size    { 4.4934 / Qmax } '------------------------------------------------------ ' Reciprocal space peak details, operation == 0 macro Full_Emmision_Profile    {       lam ymin_on_ymax 0.0005 la 1 lo 0.161669 lg 1e-6    } macro Deconvoluted_Emmision_Profile     {       Full_Emmision_Profile    } macro Full_Peak_Shape_Specimen { } macro Full_Peak_Shape { } macro Deconvoluted_Peak_Shape    {       Deconvoluted_Emmision_Profile       #if (use_Xo_Is_phase == 0)          ' Using (Yobs - background); ie. no peak shape       #elseif (use_narrow_peak_shape)          ' Use Narrow peak shape          gauss_fwhm 0.05       #else          ' Use Full peak shape          Full_Peak_Shape_Specimen       #endif    } macro & LP_Factor_    {       #if (lab_no_monochromator) (1 + Cos(X Pi/ 180)^2) #endif       1 / (Sin(X Pi/360)^2 Cos(X Pi/360)) ' Lorentz factor    } '------------------------------------------------------ '              END USER INPUT SECTION '------------------------------------------------------ Include_PDF_Generate_Common '---------------------------------------------------- |
| --- |

In this example, peaks are not fitted, so use_Xo_Is_phase=0 and use_simple_bkg_penalty=1. fluorescence_bkg is left empty as fluorescence is absent. fit_extra applies a penalty equating the bkg_tot to the Yobs value at the end of the diffraction pattern (note the use of the Value_at_X). In this example bkg_tot comprises a fit_obj which corresponds to (pc0 + pc1 X)*Capillary. In this example the Soper_Lorch_Constant was used to match GudrunX. The resulting G(r) for TOPAS (in red) and GudrunX (in Blue) is as follows:
