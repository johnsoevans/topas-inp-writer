# Reusing objects in large refinements


| lat_prms $name { … } str_dets $name { … } phase_dets $name { … } use { … } | Examples Test_examples\xrd-ct\xrd-ct-0.inp Test_examples\xrd-ct\xrd-ct-1.inp |
| --- | --- |

The keywords lat_prms, str_dets and phase_dets defines sets of lattice parameters, structural details and phase details that can be reused across phases without recalculation. This substantially reduces memory usage and speeds up refinement when hundreds of thousands of phases are present; derivatives of the common item are likewise calculated only once.

For phases with similar lattice parameters, a common set of hkls can be shared. Similarly, if two phases have identical structure factors but different (yet similar) lattice parameters, a common set of structure factors can be used. Without these keywords, the program automatically searches for common items globally but with restrictions - for example, strs with non-identical hkls cannot share a common str. Defining the structural details in a str_dets object, however, allows a common structure even when the normally generated hkl sets would differ significantly.

xrd-ct-0.inp is a two str and two xdd example that highlights the use of the above keywords. It looks like:


| ' Change case_ to 0, 1 #prm case_ = 1; iters 0 lam la 1 lo !lam 1 lg 0.3  ymin_on_ymax 0.001 str_dets s0 {    space_group i41/amd:2    site Zr x 0 y =3/4;      z =1/8;      occ Zr+4 1 beq !b1 1    site Si x 0 y =1/4;      z =3/8;      occ Si   1 beq !b2 1    site O  x 0 y !y1 0.066  z !z1 0.1951 occ O-2  1 beq !b3 2 } lat_prms l0 { Tetragonal( 6, 4) } lat_prms l1 { Tetragonal( 5, 7) }  prm !lor_ = Constant(0.1 Rad lam) / Cos(Th); phase_dets pd0 { prm !cs0 140 min 10 max 500 lor_fwhm = lor_ / cs0; } phase_dets pd1 { prm !cs1 100 min 10 max 500 lor_fwhm = lor_ / cs1; }  prm o10 0.01 min -0.1 max 0.1 prm o20 0.02 min -0.1 max 0.1 prm o11 0.03 min -0.1 max 0.1 prm o21 0.04 min -0.1 max 0.1 phase_dets ze0 { transform_X = o10 + o20 X + X; } phase_dets ze1 { transform_X = o11 + o21 X + X; }  yobs_eqn aac1.xy = 1; min 30 max 60 del 0.01    out_sfn4_ycalc = "xrd-ct-00.sfn4";    bkg @ 100 -20 10    #if case_ == 0;       str scale @ 1 load use { l0 s0 pd0 ze0 }    #elseif case_ == 1;       str scale @ 1 load use { l0 s0 pd0 ze0 }    #endif										    yobs_eqn aac2.xy = 1; min 10 max 60 del 0.01    out_sfn4_ycalc = "xrd-ct-01.sfn4";    bkg @ 100 -20 10    #if case_ == 0;       str scale @ 1 load use { l1 s0 pd1 ze1 }    #elseif case_ == 1;       str scale @ 1 load use { l1 s0 pd0 ze1 }    #endif |
| --- |

In the above, there are two strs and two xdds. In a real-world example this could extended to 100s of 1000s of xdds and strs resulting in an INP file comprising millions of lines. It is therefore efficient to define things once as is the case of lam. Modifying the preprocessor case_ #prm at the top of the file demonstrates capabilities. The case_=1 scenario is for the following:

Two xdds  each with one str

The two strs use a common str_dets resulting in only one set of hkls being generated and on set of structure factors.

The lattice parameters for the two strs are different and therefore two sets are used.

The zero errors (transform_X) are different and therefore two sets are used.

The lor_fwhm peak shape convolutions (crystallite size) are different and therefore two sets are used.

case_=1 is an unrealistic example where the lattice parameters and x-axis of the two xdds are vastly different. The power of reusing object becomes apparent in a real-world sense where lattice parameters, amongst similar structures, are expected to be more similar. Important output from refinement for case_=1 is as follows:

Num data files: 2

Num hkl-sets/unique: 2 1

Num structure-factors-sets/unique: 2 1

Num m4_d2_inv unique: 1

Num peak buffers unique: 2

Num xo_ds unique: 2

Num bkg derivs unique: 2

Num transform_X/unique: 2 2

Num peak-shape-objects: 8

Num hkl_pk_dets/unique: 2 2

Num pk_sum_limits unique: 2

*** Warning: Lattice parameters not similar

but using the same structure factors

a 6 and 5

b 6 and 5

c 4 and 7

al 90 and 90

be 90 and 90

ga 90 and 90

The unique items are shown in Red. Notice the warning which is due to the vastly different lattice parameters. case_=2 sets the peak shapes to be the same for the two phases, and the output now looks like:

Num hkl-sets/unique: 2 1

Num peak buffers unique: 1

Num m4_d2_inv unique: 1

Num structure-factors-sets/unique: 2 1

Here we see one common peak buffer, and thus only one is generated, and derivatives calculated only for its parameters. Also seen is that one set of hkls is generated. The minimum/maximum x-axis values, used for the generation of the common hkls, corresponds to the minimum/maximum values of the start_X/finish_X and extra_X_left/extra_X_right of all the common strs.

The example xrd-ct-1.inp refines on simulated data comprising 150,000 strs and 163,150 independent parameters. 20 iterations are completed in ~60s on an 8-core laptop. A few points to note when running xrd-ct-1.inp:

Turn off animated fitting in the GUI, it cannot cope with 2000 xdd files and 150,000 strs.

Run first with “#define CREATE_” to create the simulated data. The data files are created using the out_sfn4_ycalc keyword. This keyword outputs binary format files with a SFN4 extension. XY formats can also be outputted as well if desired.

Do a first run with “#define SUBSET_” to see how things look (animated graphics can be turned on here).

Then remove the #define and turn off animated graphics.

3.1 Gbytes of memory is used.

Output from the refinement looks like:

TOPAS-64 Version 8.38 (c) 1992-2020 Alan A. Coelho

Maximum number of threads 8

Time   0.25, INP file pre-processed

approximate_A_check_must_be_zero On

Loading xyz's for fm-3m from file C:\w\sg\fm-3m.sg

Num hkls generated for C:\w\sg\fm-3m.sg 50

Loading xyz's for fm3m from file C:\w\sg\fm3m.sg

Num hkls generated for C:\w\sg\fm3m.sg 55

Loading xyz's for i41/amd:2 from file C:\w\sg\i41oamdq2.sg

Num hkls generated for C:\w\sg\i41oamdq2.sg 313

Num hkl-sets/unique: 150000 3

Num peak buffers unique: 3

Num independent parameters: 163150

Num data files: 2000

Num m4_d2_inv unique: 3

Num xo_ds unique: 3000

Num bkg derivs unique: 1

Num transform_X/unique: 150000 75

Num structure-factors-sets/unique: 150000 3

Num peak-shape-objects: 600000

Num stretch_pks/unique: 150000 3000

Num hkl_pk_dets/unique: 150000 3000

Num phase Ycalcs/unique (ignoring transform_X): 150000 3000

Num phase Ycalcs/unique derivs (ignoring transform_X): 150000 3000

Num pk_sum_limits unique: 3000

Num equiv posns for centrosymmetric fm-3m: 192

Num equiv posns for centrosymmetric fm3m: 192

Num equiv posns for centrosymmetric i41/amd:2: 32

0  Time   5.37  Rwp   58.064    0.000 MC     0.00 0

1  Time   7.12  Rwp   50.740   -7.325 MC     0.00 0

2  Time  11.90  Rwp   45.643   -5.096 MC    11.10 3

3  Time  15.77  Rwp   45.507   -0.137 MC   115.50 1

4  Time  19.61  Rwp   43.351   -2.155 MC    30.34 1

approximate_A_check_must_be_zero: non-zero Aij elements now static

5  Time  23.53  Rwp   25.599  -17.752 MC     8.31 1

6  Time  26.62  Rwp   24.143   -1.457 MC    30.92 2

7  Time  29.22  Rwp   14.654   -9.488 MC     8.05 1

8  Time  32.26  Rwp   14.560   -0.094 MC   269.97 2

9  Time  34.86  Rwp   14.480   -0.080 MC    68.26 1

10  Time  37.48  Rwp   13.241   -1.239 MC    17.30 1

11  Time  40.14  Rwp    5.025   -8.216 MC     4.67 1

12  Time  43.23  Rwp    4.814   -0.211 MC    19.50 2

13  Time  45.90  Rwp    4.097   -0.718 MC     5.18 1

14  Time  48.98  Rwp    4.045   -0.051 MC    18.59 2

15  Time  51.65  Rwp    3.783   -0.262 MC     4.85 1

16  Time  54.30  Rwp    3.557   -0.226 MC     1.72 1

17  Time  56.93  Rwp    3.512   -0.044 MC     3.51 1

18  Time  59.62  Rwp    3.464   -0.048 MC    14.20 1

19  Time  62.27  Rwp    3.374   -0.090 MC     3.29 1

--- 62.270 seconds ---

File C:\w\test_examples\xrd-ct\xrd-ct-1.out updated

with parameters corresponding to best Rwp

Note the numbers in red. This is a large refinement that would not be possible without reusing objects and without the keyword approximate_A_check_must_be_zero. This refinement cannot be tested against Version 7 as the number of hkls alone, 62,700,000, would exhaust much of memory.

Objects reused are:

hkls

lattice parameters

Ycalc

Peak buffers

Structure factors

th2_offset

transform_X

stretch_pks

gauss_fwhm

and many other common arrays such as (Sin(Th)/Lam)^2.

derivatives for common refined parameters.
