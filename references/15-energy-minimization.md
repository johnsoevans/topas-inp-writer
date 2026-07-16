# Energy Minimization


## Reporting on the Madelung constant


```
[str]...
    [madelung #]
```

Examples: `test_examples\Madelung.inp`

The madelung keyword reports on the Madelung constant of a structure (Madelung, 1918). It uses the method of Coelho & Cheary (1997) for calculating the electrostatic potentials. Atomic charges are from the occ keyword, see madelung.inp. #define show_GRS in Madelung.inp creates an XY file with (S2-S1) of the GRS series set to 0.01. This is a small value that shows the behaviour of the GRS series which is as follows (blue line):


## Reporting on the Coulomb potential at a site


```
[site]...
    [co #]
```

The site dependent keyword co reports on the Coulomb potential at a site. The sum of all co values equates to the Madelung constant. From observation, atoms of the same species seem to have similar co values in an ionic crystal. Note, both the co and madelung keywords are independent of the grs_interaction keyword.


## Enhancements to the grs_interaction


```
[site]...
    [g !N] [q E] [s E]
[repulsion_refine]
[grs_interaction [qi !E qj !E] $s1 $s2 c !E]...
    [no_coulomb]
[penalty = Get(grs_lp_rep);]
[penalty = Get(grs_lp_refine);]
```

Examples: `test_examples\alvo4-grs-auto.inp`, `grs-alvo4\solve-1.inp`, `grs-alvo4\Rep-1.inp`, `grs-alvo4\Rep-2.inp`

When repulsion_refine is defined, then all grs_interactions are placed in a “repulsion refine” mode. In this mode, grs_interactions return the sum of the derivatives squared of the grs_interactions, with respect to the atomic coordinates, or, in pseudo code:

Sum(dgrs_interaction/dfi, i)2

where fi corresponds to the x, y and z coordinates of the sites associated with the grs_interaction. In this manner, a refinement will adjust repulsion parameters such that the derivatives of the grs_interactions with respect to independent repulsion parameters are a minimum.

Repulsion parameters include qi, qj, q, s and any other parameters defined in the grs_interaction equation. The new site dependent keyword, s, scales the equation part of grs_interactions. This simplifies the setting up of grs_interactions; consider the following:


| grs_interaction qi = 3; qj = -2; Al* O* p1 = B1 / R^7; penalty = p1; grs_interaction qi = 5; qj = -2; V*  O* p2 = B2 / R^7; penalty = p2; grs_interaction qi = 3; qj =  5; Al* V* p3 = B3 / R^7; penalty = p3; |
| --- |

Here, there are three parameters B1, B2 and B3. In the repulsion_refine mode, fractional coordinates are not refined. However, their derivatives with respect to the grs_interaction equations are expensive and are required. The site dependent s parameters can be used to avoid this recalculation as follows:


| site Al … q  3 s s1 1 site V …  q  5 s s2 1 site O …  q -2 s s3 1 repulsion_refine grs_interaction * * c = 1/R^9;  penalty = c; |
| --- |

B1 = s1 s3

B2 = s2 s3

B3 = s1 s2

These parameters are related to the minimum distance Ro between two isolated atoms i and j, and for the case of opposite q charges, as follows:

Uij = qi qj / R + si sj / Rn

Setting the derivative to zero:

dUij(R=Ro)/dR = 0

we get:

Ro =  [ (n-1) si sj / (qi qj) ] 1/(n-1)


## Including lattice parameter in grs_interaction(s)

The default is to not include lattice parameters when repulsion_refine is defined. To include the minimization of derivatives of the grs_interactions with respect to the lattice parameters, the following can be used:


| penalty = Get(grs_lp_rep); : 0 |
| --- |

For normal refinement (repulsion_refine not defined), lattice parameters, flagged for refinement, are included in the derivatives of grs_interactions if the following is included:


| penalty = Get(grs_lp_refine); : 0 |
| --- |


## Ignoring the Coulomb part of the grs_intercation

U = A / R6 + B/R12


| site... q  1 s @ 1 site... q -1 s @ 1 grs_interaction … = 1 /R^4; no_coulomb grs_interaction … = 1 /R^9; no_coulomb |
| --- |

Here, 1/R^4 and 1/R^9 values are stored in lookup tables which are calculated once at the start of refinement. This potential is used in describing the partly ionic structure of AlVO4, see grs-alvo4\rep-2.inp.

The grs_interaction equation can also be set to zero. This may be useful when looking at dipole properties of a molecule where the centre of the electron cloud is at a different position from the nucleus, for example:


| site Al1       x x1 # y y1 # z z1 # …  site Al1_shift x = dx1 x1; y = dy1 + y1; z = dz1 + z1; …  grs_interaction … Al1 = 0;                       ‘ No repulsion equation grs_interaction … Al1_shift = 1 /R^9; no_coulomb ‘ No Coulomb potential |
| --- |


## _rem attribute - Removing/inserting parameters from refinement

The _rem parameter attribute is an equation that is evaluated at the start of a refinement iteration (note: attribute equations cannot be named). If non-zero, the associated parameter is removed from refinement for the duration of the iteration. The parameter can be reinstated in subsequent iterations if _rem evaluates to zero; for example, to reinstate the parameter after convergence and into a new Cycle, the following could be used:


| prm a 1 _rem = Mod(Cycle, 2); |
| --- |


## Using ok_to_continue and _rem


| macro qal { 3 } ‘ Charge of Al+3  macro qv  { 5 } ‘ Charge of V+5  macro exp { 9 } ‘ Repulsion exponent   macro ro_al { 1.65 } ‘ Ro values from bond distances macro ro_v  { 1.5 } macro ro_oo { 2.4 }  ‘ Change Ro values to s values prm !so  = Sqrt((4 ro_oo^(exp-1)) / exp); :  22.1184 prm !sal = ((ro_al^(exp-1)) 6 / exp   ) / so; :  1.65587133 prm !sv  = ((ro_v^(exp-1)) 10 / exp) / so; :  1.28746033  macro S_ { If(Get(q) == qal, sal, sv) } macro OCC { If(Get(q) == qal, 1, 1.85) } macro VV { rand_xyz 1 } ‘ Randomize sites at start of cycle macro VQ { _rem 1 val_on_continue = If(Mod(Cycle,10), If(Rand(0,1)<0.5,qal,qv), Val); } prm q1 qal VQ prm q2 qal VQ prm q3 qal VQ prm q4 qv  VQ prm q5 qv  VQ prm q6 = 3 qal + 3 qv - q1 - q2 - q3 - q4 - q5;  ‘ Ensure scattering power equals 3*Al sites plus 3*V sites ok_to_continue = Or(q6 == qal, q6 == qv);   Grs_(*, *, exp, 0) ‘ grs_interaction penalty  site Al   x @  0.0  y @  0.9  z @  0.8 occ Al+3 = OCC; q = q1; s = S_; VV site Al   x @  0.1  y @  0.0  z @  0.9 occ Al+3 = OCC; q = q2; s = S_; VV site Al   x @  0.2  y @  0.1  z @  0.0 occ Al+3 = OCC; q = q3; s = S_; VV site Al   x @  0.3  y @  0.2  z @  0.1 occ Al+3 = OCC; q = q4; s = S_; VV site Al   x @  0.4  y @  0.3  z @  0.2 occ Al+3 = OCC; q = q5; s = S_; VV site Al   x @  0.5  y @  0.4  z @  0.3 occ Al+3 = OCC; q = q6; s = S_; VV  site O1   x @  0.6  y @  0.5  z @  0.4 occ O-2 1 q -2 s = so; VV site O2   x @  0.7  y @  0.6  z @  0.5 occ O-2 1 q -2 s = so; VV site O3   x @  0.8  y @  0.7  z @  0.6 occ O-2 1 q -2 s = so; VV site O4   x @  0.9  y @  0.8  z @  0.7 occ O-2 1 q -2 s = so; VV site O5   x @  0.0  y @  0.9  z @  0.8 occ O-2 1 q -2 s = so; VV site O6   x @  0.1  y @  0.0  z @  0.9 occ O-2 1 q -2 s = so; VV site O7   x @  0.2  y @  0.1  z @  0.0 occ O-2 1 q -2 s = so; VV site O8   x @  0.3  y @  0.2  z @  0.1 occ O-2 1 q -2 s = so; VV site O9   x @  0.4  y @  0.3  z @  0.2 occ O-2 1 q -2 s = so; VV site O10  x @  0.5  y @  0.4  z @  0.3 occ O-2 1 q -2 s = so; VV site O11  x @  0.6  y @  0.5  z @  0.4 occ O-2 1 q -2 s = so; VV site O12  x @  0.7  y @  0.6  z @  0.5 occ O-2 1 q -2 s = so; VV |
| --- |

The above will change the scattering power on the Al* sites every 10th Cycle as defined in the VQ macro. Note, there’s only one grs_interaction and the Grs_ macro looks like:


| macro Grs_(s1, s2, & n, v) { grs_interaction s1 s2 #m_unique c =  If (R < rsm, ((-n rsm^(-2 - n)/2) R^2 + rsm^(-n) + n/(2 rsm^n)), 1 / R^n ); penalty = c; : v } |
| --- |

Solve-1.inp operates in three modes which can be chosen by the two control parameters (in Red) in the INP text at the top of the file and is as follows:


| continue_after_convergence #prm penalties_only_start_at_Rietveld_positions = 1; #if penalties_only_start_at_Rietveld_positions; 	only_penalties 	verbose 1	 	temperature 0.5 use_best_values #else #prm solve_using_real_data_and_penalties = 1; #prm solve_using_penalties_only = solve_using_real_data_and_penalties == 0; verbose -1	 num_runs 10  ' Solve structure 10 times, change to 1 to see solution  #if solve_using_real_data_and_penalties;  ' Minimum energy at 5% temperature = If(Mod(Cycle, 200), 0.7, 10); iters = If(And(Cycle_Iter > 2, Get(r_wp) < 8), 0, 1000000000); #endif #if solve_using_penalties_only;  ' Minimum energy at -423.5 only_penalties temperature = If(Mod(Cycle, 200), Rand(0.35, 0.7), 10); iters = If(And(Cycle_Iter > 2, Get(r_wp) < -423), 0, 1e9); #endif #endif |
| --- |

Running solve-1.inp with penalties_only_start_at_Rietveld_positions=1 refines on the atomic coordinated with only_penalties defined. It also displaces the atomic positions by an amount of rand_xyz*temperature, or, 0.5 Å in a random direction at the start of each cycle. As can be seen whilst running, the structure returns to the Rietveld refined values after each cycle.

Running solve-1.inp with solve_using_real_data_and_penalties=1 solves the structure 10 times and the Rwp plot looks like:

This is similar to AlVO4-grs-auto.inp, which refines on occupancies. ok_to_continue is evaluated at the start of each iteration. If it evaluates to zero, then val_on_continue of its independent parameters are executed. The process is repeated until all ok_to_continue(s) evaluates to non-zero. Note, more than one ok_to_continue can be defined.


## Energy minimization-only resulting in the observed structure of AlVO4

Running solve-1.inp with solve_using_real_data_and_penalties=0, achieves a minimum energy configuration that matches the Rietveld refined structure. only_penalties are refined; lattice parameters are not included. Even though AlVO4 is partly ionic, the maximum atomic displacement at the energy minimum compared to the Rietveld refined positions is relatively small at ~0.22 Å with an average movement of ~0.14 Å. In other words, the energy minimization “pseudo-solved” the structure from a crude atomic interaction model.

Including lattice parameters as refinable parameters results in non-sensical atomic coordinates which means that the atomic interaction model is inadequate in a physical sense.


## Determining repulsion parameters for AlVO4

Rep-1.inp performs three types of operations/refinements as seen by the self-explanatory control statements at the top of the file of:


| #prm determine_repulsion_parameters = 0;  #prm test_rep_prms = 0; #prm bond_length_differences = 0; |
| --- |

Setting determine_repulsion_parameters=1 fixes the atomic coordinates to Rietveld refined values and then minimizes dUij/dfi=0 for AlVO4 by varying three s repulsion parameters of sal, sv and so where:

Uij = qi qj / R + si sj / R9

As seen in Rep-1.inp, the sum of the derivatives squared of dU/dfi (where fi is a fractional atomic coordinate) do not refine to zero. This is seen in the lines:


| Grs_(*, *, 9, 0.465098047`)  penalty = Get(grs_lp_rep); :  2.6397897` |
| --- |

Also, seen in REP-1.INP is that the Ro values (distance between two isolated atoms) seem too large as in:


| prm !ro_alo = ( (exp-1) Abs(sal so qal qo) )^(1/(exp-1)); :  2.18729482       prm !ro_vo  = ( (exp-1) Abs(sv  so qv  qo) )^(1/(exp-1)); :  2.4673052       prm !ro_oo  = ( (exp-1) Abs(so  so qo  qo) )^(1/(exp-1)); :  2.73559269 |
| --- |

Performing another refinement with the three determined repulsion parameters sal, sv and so fixed, and instead refining on the atomic coordinates (test_rep_prms=1) results in a structure with average atomic movements of 0.14 Å from the Rietveld coordinates. The movement can be seen in the following Al octahedron (lighter atoms are the Rietveld determined positions):

Setting test_rep_prms=1 and output_U_vs_a=1 executes the INP code of:


| #if And(output_U_vs_a, test_rep_prms);    verbose 1    num_runs 100    iters 0    a = Ramp_Run_Number(6.54131-3, 6.54131+3, Get(num_runs));    out a.xy append       Out(Get(a))       Out_String(" ")       Out(Get(non_fit, r_wp))       Out_String("\n") #else                    a  6.54131 #endif |
| --- |

This produces the XY file of:

Here we see that the observed a lattice parameter of 6.54131 Å is far from the minimum; this was evident from the non-zero value for Get(grs_lp_rep) as seen above. Note the use of Get(non_fit, r_wp) instead of Get(r_wp); the former gets the global Rwp and the latter the xdd dependent Rwp. Use of only_penalties does not update xdd dependent Rwp(s); hence the need to Get the global r_wp.

Lattice parameters were not refined in performing the test_rep_prms=1 operation; they could have been with the inclusion of the line:


| penalty = Get(grs_lp_refine); : 0 |
| --- |

The refinement in such a case would have produced very incorrect results as indicated by the U versus a plot above. This demonstrates that a simple Coulomb sum and 1/R^9 repulsion term does not fully describe AlVO4 and that another model is needed.


## A non-ionic model for AlVO4

Instead of using the Coulomb sum, a 1/R^4 term was used for atoms of opposite charge (Al-O and V-O) and a 1/R^9 for like charges, or,

Uij = Aij / R4 + Bij/R9

This U choice was a guess and there may well be more physically meaningful models available. The following however does highlight the ability to quickly model such cases. The Rep-2.inp test example uses this potential and it has three operational/refinement modes:


| #prm repulsion_refine = 0;         ‘ set to 0 or non-zero    #prm bond_length_differences = 0;  ‘ set to 0 or non-zero #prm test_repulsion_prms = repulsion_refine == 0; |
| --- |

Refining with repulsion_refine=1 results in a low value for grs_lp_rep and for grs_interactions:


| penalty = Get(grs_lp_rep); : 0.000423118927` Grs_(Al*,  O*, ea,  -a_alo, 0.000824217622`) Grs_(V*,   O*, ea,  -a_vo,  0.00103650359`) Grs_(O*,   O*, ea,  a_oo,   0.000721564661`) Grs_(Al*, Al*, ea,  a_alal, 0.000102652961`) Grs_(Al*,  V*, ea,  a_alv,  0.000417591887`) Grs_(V*,   V*, ea,  a_vv,   0.000314938926`) Grs_(Al*,  O*, er,  b_alo,  0.000824217622) Grs_(V*,   O*, er,  b_vo,   0.00103650359) Grs_(O*,   O*, er,  b_oo,   0.000721564661) Grs_(Al*, Al*, er,  b_alal, 0.000102652961) Grs_(Al*,  V*, er,  b_alv,  0.000417591887) Grs_(V*,   V*, er,  b_vv,   0.000314938926) |
| --- |

These are low values compared to those obtained for rep-1.inp and it indicates near zero values for (dgrs_interaction/dfi)2 where fi is a fractional atomic coordinate or lattice parameter. The difference in lattice parameters between the observed values from Rietveld refinement and the energy minimization of rep-2.inp is:


| Δa  = 0.353377, Δb  = 0.387755,  Δc = 0.501125 Δal = -0.92222, Δbe = -0.32539, Δga = -0.77862 |
| --- |

The maximum bond length difference is 0.18 Å with an average difference of 0.08 Å.
