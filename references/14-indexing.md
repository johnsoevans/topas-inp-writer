# Indexing

The following algorithm is based on the iterative method of Coelho (2003). Unlike lp_serach it requires the extraction of d-spacings. The indexing directory contains example INP files, example usage is as follows:


| index_zero_error try_space_groups "2 75"  load index_d {    8.912    7.126    4.296    ...  } |
| --- |

Individual space groups can be tried or for simplicity all Bravais lattices can be tried using standard macros as follows:


| Bravais_Cubic_sgs Bravais_Trigonal_Hexagonal_sgs Bravais_Tetragonal_sgs Bravais_Orthorhombic_sgs Bravais_Monoclinic_sgs Bravais_Triclinic_sgs |
| --- |

To try all unique extinction subgroup space-groups, a more exhaustive approach, then the following macros can be used:


| Unique_Cubic_sgs Unique_Trigonal_Hexagonal_sgs Unique_Tetragonal_sgs Unique_Orthorhombic_sgs Unique_Monoclinic_sgs Unique_Triclinic_sgs |
| --- |

On termination of Indexing a *.NDX file is created, with a name corresponding to the name of the INP file and placed in the same directory as the INP file. The *.NDX file contains solutions as well as a detailed summary of the best 20 solutions. Here’s an example of an NDX file:


| ‘ Indexing method - Alan Coelho (2003), J. Appl. Cryst. 36, 86-95 ‘ Time: 2.015 seconds      ‘Sg     Status UNI      Vol       Gof     Zero      Lps ... Indexing_Solutions_With_Zero_Error_2 {    0) P42/nmc    3   0    1187.321    38.82   0.0000    11.1924  ...    1) P42/nmc    3   0    1187.057    38.64   0.0000    11.1896  ...    2) P42/nmc    3   0    1187.458    38.61   0.0000    11.1914  ... ... } /* ======================================================================    0) P-1         0     985.652    30.80   0.0111     7.0877  ...        h   k   l       dc       do    do-dc     2Thc     2Tho   2Tho-2Thc    0   0   1   15.857   15.830   -0.027    5.569    5.578    0.009    0   1   0    8.765    8.750   -0.015   10.084   10.101    0.017 ... */ |
| --- |


## Figure of merit

The figure of merit M used in indexing is as follows:


| where | (14-1) |
| --- | --- |


| where | (14-2) |
| --- | --- |


## Extinction subgroup determination

At the end of an indexing run, further indexing runs are internally performed across extinction subgroups (see "Space groups with identical absences – Extinction subgroups" below) to determine the most likely subgroup. These internal runs are seeded with already determined lattice parameters, and in most cases the correct extinction subgroup is obtained without the need for Qi in Eq. (14-1). Extinction subgroups can be explicitly searched using the macros defined Topas.inc, see for example Unique_Orthorhombic_sgs.


## Reprocessing solutions - DET files

Details of solutions can be obtained at a later stage by including solution lines, found in the NDX file, in the INP file. For example, supposing details of solutions 50 and 51 were sought then the following (see example indexing\ex10.inp) could be used:


| index_lam 1.540596  index_zero_error       try_space_groups 2  Indexing_Solutions_With_Zero_Error_2 {   50) P-1        1   0    2064.788     9.74   0.0000   ...   51) P-1        3   0    3128.349     9.61   0.0115   ... } load index_d {    15.83 good     8.75      7.91      ...  } |
| --- |

After running this INP file, a *.DET file is created containing details of the supplied solutions.


## Keywords and data structures


```
Tindexing
    [index_lam  !E1.540596]
    [index_min_lp !E2]  [index_max_lp !E]
    [index_max_Nc_on_No !E5]
    [index_max_number_of_solutions #3000]
    [index_max_th2_error !E0.05]
    [index_max_zero_error #0.2]
    [index_th2  !E | index_d !E]...
        [index_I  E1 [good] ]
    [index_x0 !E]
    [index_zero_error]
    [no_extinction_subgroup_search]
    [seed [#]]
    [try_space_groups $]...
        [x_angle_scaler #0.1]
        [x_scaler #]
```

Values for most keywords are automatically determined or have defaults (appearing as numbers to the right) adequate for difficult indexing problems. In the following example from UPPW (service provided by Armel Le Bail to the SDPD mailing list at http://sdpd.univ-lemans.fr/uppw/), only a few keywords are necessary. Also note the use of dummy; this allows for the exclusion of 2 and I values without having to edit the columns of data.


| seed index_lam  0.79776 index_zero_error     index_max_Nc_on_No 6 try_space_groups 3 load index_th2 dummy dummy index_I dummy  { ‘ d (A)  2Theta     Height      Area     FWHM 1.724  26.50645    2758.3   23303.7    0.0450 2.646  17.27733  150393.8  747063.6    0.0250 3.235  14.13204   98668.8  493153.7    0.0250 3.417  13.37776   11102.6   53185.0    0.0250 5.190   8.80955     782.7    3910.9    0.0250 ... } |
| --- |


## Keywords in detail

[index_lam  !E1.540596]

Defines the wavelength in Å.

[index_min_lp !E2.5] [index_max_lp !E]

Defines the minimum and maximum allowed lattice parameters. The maximum is typically automatically determined.

[index_max_Nc_on_No !E5]

Determines the maximum ratio of the number of calculated to observed lines. The value of 6 allows for up to 83% of missing lines.

[index_max_number_of_solutions #1000]

The number of best solutions to keep.

[index_max_th2_error !E0.05]

Used for determining impurity lines (un-indexed lines UNI in *.NDX). Large values, 1 for example, forces the consideration of more observed input lines. For example, if it is known that there are none or maybe just one impurity line then a large value for index_max_th2_error will speed up the indexing procedure.

[index_max_zero_error !E0.2]

Excludes solutions with zero errors greater than index_max_zero_error.

[index_th2  !E | index_d !E]...

[index_I  E1 [good]]

index_th2 or index_d defines a reflection entry in 2 degrees or d-spacing in Å. index_I is typically set to the area under the peak; it is used to weight the reflection. good signals that the corresponding d-spacing is not an impurity line. A single use of good on a large d-spacing decreases the number of possible solutions and hence speeds up the indexing process (see example indexing\ex10.inp).

[index_x0 !E]

Defines Xhh in the reciprocal lattice equation of (14-1). In a triclinic lattice the largest d-spacing can probably be indexed as 100 or 200 etc. Thus


| index_x0 = 1/(dmax)^2; |
| --- |

speeds up the indexing process (if, in this case, the first line can be indexed as 100) and additionally the chance of finding the correct solution is enhanced, see ex13.inp. Note, if the data is in 2Th degrees then the following can be used:


| index_x0 = (2 Sin(2Thmin Pi/360) / wavelength)^2; |
| --- |

The two macros Index_x0_from_d and Index_x0_from_th2 simplify the use of index_x0.

[index_zero_error]

Includes a zero error.

[no_extinction_subgroup_search]

By default, extinction subgroup determination is performed at the end of an indexing run; this can be negated by defining no_extinction_subgroup_search.

[seed [#]]

Seeds the random number generator.

[try_space_groups $]...

[x_angle_scaler #0.1]

[x_scaler #]


| Search | Use |
| --- | --- |
| Primitive monoclinic | try_space_groups 3 |
| Monoclinic Bravais lattices of lowest symmetry | Bravais_Monoclinic_sgs |
| C-centered monoclinic of lowest symmetry | try_space_groups 5 |
| All orthorhombic space groups individually | Unique_Orthorhombic_sgs |

x_scaler is a scaling factor used for determining the number of steps to search in parameter space. x_scaler needs to be less than 1. Increasing x_scaler searches parameter space in finer detail. Default values are as follows:


| Cubic 						 0.99 Hexagonal/Trigonal		 0.95 Tetragonal 				 0.95 | Orthorhombic 		0.89 Monoclinic 		0.85 Triclinic 			0.72 |
| --- | --- |

x_angle_scaler is a scaling factor for determining the number of angular steps for monoclinic and triclinic space groups. Small values, 0.05 for example, increases the number of angular steps. The default value of 0.1 is usually adequate.


## Identifying dominant zones

Here are two example output lines from an NDX file.

0) P42/nmc 3 0 1187.124  38.82 0.000 11.1904 11.1904 9.4799 90.00 90.00 90.00 ‘ ===  24 19

6) P-421c  3 0 1187.124  35.67 0.000 11.1904 11.1904 9.4799 90.00 90.00 90.00 ‘ ===  24 19

The 1st column corresponds to the rank of the solution.

The 2nd corresponds to the space group.

The 3rd corresponds to the Status of the solution as follows:


|  | Status 1: | Weighting applied as defined in Coelho (2003). |
| --- | --- | --- |
|  | Status 2: | Zero error attempt applied. |
|  | Status 3: | Zero error attempt successful and impurity lines removal successful. |
|  | Status 4: | Impurity line(s) removed. |

The 4th column corresponds to the number of un-indexed lines.

The 5th column corresponds to the volume of the lattice.

The 6th corresponds to the goodness of fit value.

The 7th corresponds to the zero error if index_zero_error is included.


|  | X0 | X1 | X2 | X3 | X4 | X5 |
| --- | --- | --- | --- | --- | --- | --- |
| Cubic | h2+k2+l2 |  |  |  |  |  |
| Hexagonal, Trigonal | h2+k2+h k | l2 |  |  |  |  |
| Tetragonal | h2+k2 | l2 |  |  |  |  |
| Orhtorhombic | h2 | k2 | l2 |  |  |  |
| Monoclinic | h2 | k2 | l2 | h l |  |  |
| Triclinic | h2 | k2 | l2 | h k | h l | k l |


## *** Probable causes of Failure ***

The most probable cause of failure is the inclusion of too many d-spacings. If it is assumed that the smallest lattice parameter is greater than 3Å then it is problematic to include d-spacings with values less than about 2.5Å when there are already 30 to 40 reflections with d values greater than 2.5Å. Some of the problems caused by very low d-spacings are:

The number of calculated lines increases dramatically and thus index_max_Nc_on_No will need to be increased.

The low d-spacings are probably inaccurate due to peak overlap.

A situation where it is necessary to include low d-spacings is when there are only a few d-spacings available as in higher symmetry lattices.


## Space groups with identical absences – Extinction subgroups


| Space group numbers with identical hkls | Space group symbols with identical hkls |
| --- | --- |
| Triclinic | Triclinic |
| 1 2 | P1 P-1 |
| Monoclinic | Monoclinic |
| 9 15 | Cc C2/c |
| 5 8 12 | C2 Cm C2/m |
| 14 | P21/c |
| 7 13 | Pc P2/c |
| 4 11 | P21 P21/m |
| 3 6 10 | P2 Pm P2/m |
| Orthorhombic | Orthorhombic |
| 70 | Fddd |
| 43 | Fdd2 |
| 22 42 69 | F222 Fmm2 Fmmm |
| 68 | Ccca |
| 73 | Ibca |
| 37 66 | Ccc2 Cccm |
| 45 72 | Iba2 Ibam |
| 41 64 | Aba2 Cmca |
| 46 74 | Ima2 Imma |
| 36 40 63 | Cmc21 Ama2 Cmcm |
| 39 67 | Abm2 Cmma |
| 20 | C2221 |
| 23 24 44 71 | I222 I212121 Imm2 Immm |
| 21 35 38 65 | C222 Cmm2 Amm2 Cmmm |
| 52 | Pnna |
| 56 | Pccn |
| 60 | Pbcn |
| 61 | Pbca |
| 48 | Pnnn |
| 54 | Pcca |
| 50 | Pban |
| 33 62 | Pna21 Pnma |
| 34 58 | Pnn2 Pnnm |
| 32 55 | Pba2 Pbam |
| 30 53 | Pnc2 Pmna |
| 29 57 | Pca21 Pbcm |
| 27 49 | Pcc2 Pccm |
| 31 59 | Pmn21 Pmmn |
| 26 28 51 | Pmc21 Pma2 Pmma |
| 19 | P212121 |
| 18 | P21212 |
| 17 | P2221 |
| 16 25 47 | P222 Pmm2 Pmmm |
| Tetragonal | Tetragonal |
| 142 | I41/acd |
| 110 | I41cd |
| 141 | I41/amd |
| 109 122 | I41md I-42d |
| 108 120 140 | I4cm I-4c2 I4/mcm |
| 88 | I41/a |
| 80 98 | I41 I4122 |
| 79 82 87 97 107 119 121 139 | I4 I-4 I4/m I422 I4mm I-4m2 I-42m I4/mmm |
| 130 | P4/ncc |
| 126 | P4/nnc |
| 133 | P42/nbc |
| 103 124 | P4cc P 4/mcc |
| 104 128 | P4nc P 4/mnc |
| 106 135 | P42bc P 42/mbc |
| 137 | P42/nmc |
| 138 | P42/ncm |
| 134 | P42/nnm |
| 125 | P4/nbm |
| 114 | P-421c |
| 105 112 131 | P42mc P-42c P42/mmc |
| 102 118 136 | P42nm P-4n2 P42/mnm |
| 101 116 132 | P42cm P-4c2 P42/mcm |
| 100 117 127 | P4bm P-4b2 P4/mbm |
| 86 | P42/n |
| 85 129 | P4/n P4/nmm |
| 92 96 | P41212 P43212 |
| 94 | P42212 |
| 76 78 91 95 | P41 P43 P4122 P4322 |
| 77 84 93 | P42 P 42/m P4222 |
| 90 113 | P4212 P-421m |
| 75 81 83 89 99 111 115 123 | P4 P-4 P4/m P422 P4mm P-42m P-4m2 P4/mmm |
| Trigonal & Hexagonal | Trigonal & Hexagonal |
| 161 167 | R3c R-3c |
| 146 148 155 160 166 | R3 R-3 R32 R3m R-3m |
| 184 192 | P6cc P6/mcc |
| 159 163 186 190 194 | P31c P-31c P63mc P-62c P63/mmc |
| 158 165 185 188 193 | P3c1 P-3c1 P63cm P-6c2 P63/mcm |
| 169 170 178 179 | P61 P65 P6122 P6522 |
| 144 145 151 152 153 154 171 172 180 181 | P31 P32 P3112 P3121 P3212 P3221 P62 P64 P6222 P6422 |
| 173 176 182 | P63 P63/m P6322 |
| 143 147 149 150 156 157 162 164 168 174 175 177 183 187 189 191 | P3 P-3 P312 P321 P3m1 P31m P-31m P-3m1 P6 P-6 P6/m P622 P6mm P-6m2 P-62m P6/mmm |
| Cubic | Cubic |
| 228 | Fd-3c |
| 219 226 | F-43c Fm-3c |
| 203 227 | Fd-3 Fd-3m |
| 210 | F4132 |
| 196 202 209 216 225 | F23 Fm-3 F432 F-43m Fm-3m |
| 230 | Ia-3d |
| 220 | I-43d |
| 206 | Ia-3 |
| 214 | I4132 |
| 197 199 204 211 217 229 | I23 I213 Im-3 I432 I-43m Im-3m |
| 222 | Pn-3n |
| 218 223 | P-43n Pm-3n |
| 201 224 | Pn-3 Pn-3m |
| 205 | Pa-3 |
| 212 213 | P4332 P4132 |
| 198 208 | P213 P4232 |
| 195 200 207 215 221 | P23 Pm-3 P432 P-43m Pm-3m |


## Indexing Equations - Background

a, b and c lattice vectors can be converted to Cartesian coordinates with a collinear with the Cartesian x axis and b coplanar with the Cartesian x-y plane as follows:


| a = ax i | b = bx i + by j | c = cx i + cy j  + cz k | (14-3) |
| --- | --- | --- | --- |

where

ax = a

bx = b cos(),   by = b sin()

cx = c cos(),   cy =  c (cos() – cos() cos()) / sin(),   cz2 = c2  (cx)2– (cy)2

a, b, c are the lattice parameters and ,, the lattice angles. The reciprocal lattice vectors A, B, and C calculated from the lattice vectors of Eq. (14-3) become:


| A = Ax i + Ay j  + Az k | B = By j + Bz k | C = Cz k |
| --- | --- | --- |

The equation relating d-spacing dhkl to hkl in terms of the reciprocal lattice parameters is:


|  |  |  | (14-4) |
| --- | --- | --- | --- |
| where | where | where | where |
|  |  |  |  |
