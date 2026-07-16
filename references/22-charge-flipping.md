# Charge-flipping

The charge-flipping method of Oszlányi & Süto (2004) has been implemented (Coelho, 2007) using the keywords shown in Table 24-2. Also included is the use of the tangent formula (Hauptman & Karle, 1956) within the iterative charge-flipping process. Equations appearing in charge-flipping keywords can be functions of the items shown in Table 24-1. At the end of a charge flipping process a file with the same name as that given by cf_hkl_file is created but with a *.FC extension. Almost all charge-flipping keywords can be equations, allowing for great flexibility in-regards to changing resolution etc... on the fly. Table 24-3 lists charge-flipping examples found in the CF directory.


| Table 24-1. Items that can be used in charge-flipping equations | Table 24-1. Items that can be used in charge-flipping equations |
| --- | --- |
| Get(Aij)  Get(alpha_sum)  Get(density) Get(cycles_since_last_best) Get(d_squared_inverse) Get(initial_phase) Get(iters_since_last_best) Get(F000) Get(max_density) Get(max_density_at_cycle_iter_0) Get(num_reflections_above_d_min) Get(phase_difference) Get(r_factor_1), Get(r_factor_2) Get(threshold) | These are updated internally each charge-flipping iteration or cycle or when needed. |
| Reserved parameter names: Cycle_Iter, Cycle, Iter, D_spacing | Reserved parameter names: Cycle_Iter, Cycle, Iter, D_spacing |
| Macros (see Topas.inc) Ramp, Ramp_Clamp, Cycle_Ramp, Tangent, Restart_CF, Pick, Pick_Best Out_for_cf(file) : Outputs the A matrix from a Pawley refinement for use in charge flipping; uses cf_in_A_matrix. See example cf-cime-pawley.inp. | Macros (see Topas.inc) Ramp, Ramp_Clamp, Cycle_Ramp, Tangent, Restart_CF, Pick, Pick_Best Out_for_cf(file) : Outputs the A matrix from a Pawley refinement for use in charge flipping; uses cf_in_A_matrix. See example cf-cime-pawley.inp. |


Table 24-2. Keywords that can be used in charge-flipping (order and nesting as in Technical_Reference.docx -- Word's own table cell indentation, checked directly, confirms `histogram_match_scale_fwhm` and `pick_atoms` each have real nested children, while "Electron density perturbations"/"Phase perturbations"/"Miscellaneous"/"GUI Related" are same-level group dividers within `charge_flipping`'s own flat member list, not additional nesting levels):

```
[charge_flipping]
    [a !E b !E c !E [al !E] [be !E] [ga !E] ]   ' default: al = be = ga = 90
    [cf_hkl_file $file]
    [cf_in_A_matrix $file]
    [scale_Aij !E]   ' default: Get(Aij)^2
    [break_cycle_if_true !E]
    [delete_observed_reflections !E]
    [extend_calculated_sphere_to !E]
    [f_atom_type $type f_atom_quantity !E]...
    [find_origin !E]   ' default: 1
    [fraction_density_to_flip !E]   ' default: 0.75
    [fraction_reflections_weak !E]   ' default: 0
    [min_d !E]   ' default: 0
    [min_grid_spacing !E]
    [neutron_data]
    [space_group $]   ' default: P1
    [use_Fc]
    Electron density perturbations
    [flip_equation !E]
    [flip_regime_2 !E]
    [flip_regime_3 !E]
    [histogram_match_scale_fwhm !E]
        [hm_size_limit_in_fwhm !E]   ' default: 1
        [hm_covalent_fwhm !E]   ' default: 1
    [pick_atoms $atoms]...
        [activate !E]   ' default: 1
        [choose_from !E]
        [choose_to !E]
        [choose_randomly !E]
        [omit !E]
        [displace !E]
        [insert !E]
    [scale_density_below_threshold !E]
    [symmetry_obey_0_to_1 !E]
    Phase perturbations
    [add_to_phases_of_weak_reflections !E]
    [randomize_phases_on_new_cycle_by !E]   ' default: 0
    [set_initial_phases_to $file]
    [modify_initial_phases !E]
    [tangent_num_h_read !E]
    [tangent_num_k_read !E]
    [tangent_num_h_keep !E]
    [tangent_max_triplets_per_h !E]   ' default: 30
    [tangent_min_triplets_per_h !E]   ' default: 1
    [tangent_scale_difference_by !E]   ' default: 1
    [tangent_tiny !E]   ' default: 0.01
    Miscellaneous
    [apply_exp_scale !E]   ' default: 1
    [correct_for_atomic_scattering_factors !E]   ' default: 1
    [correct_for_temperature_effects !E]   ' default: 1
    [hkl_plane $hkl]...
    [randomize_initial_phases_by !E]   ' default: Rand(-180,180)
    [scale_E !E]   ' default: 1
    [scale_F !E]   ' default: 1
    [scale_F000 !E]   ' default: 0
    [scale_weak_reflections !E]
    [user_threshold !E]
    [verbose #]   ' default: 1
    GUI Related
    [add_to_cloud_N !E [add_to_cloud_when !E]]
    [pick_atoms_when !E]
    [view_cloud !E]   ' default: 1
```


## Charge-flipping usage

CF works well on data at good resolution (<1Å resolution). For data at poor resolution or for difficult structures then inclusion of the tangent formula can facilitate solution and sharpen electron densities, see example cf-1a7y.inp. Powder diffraction data usually fall under the poor resolution/data quality category and as such additional symmetry restraints using symmetry_obey_0_to_1 can sharpen electron densities. Example cf-alvo4.inp demonstrates the use of the tangent formula on powder data.


| fraction_density_to_flip = Ramp(0.85, 0.8, 100); fraction_reflections_weak = Ramp(0.5, 0, 100); flip_regime_2 = Ramp(1, 0, 200); flip_regime_3 = Ramp(0.25, 0.5, 200); 	 symmetry_obey_0_to_1 = Ramp(0.5, 1, 100);  tangent_scale_difference_by = Ramp(0, 1, 100); |
| --- |


### Perturbations

Perturbations can be categorized as being of either phase, structure factor intensity or electron density perturbations as shown in Table 24-2. There are two built in flipping regimes, flip_regime_2 and flip_regime_3, and one user defined regime flip_equation. Only one can be used, and they all modify the electron density. In the absence of a flipping regime, the following is used where  corresponds to the electron density threshold.


|  | (24-1) |
| --- | --- |

Using the tangent formula on either difficult structures or on data at poor resolution often leads to uranium atom solutions. Uranium atom solutions can be avoided by modifying the electron density using a flipping regime that dampens high electron densities or by using pick_atoms.


### The Ewald sphere, weak reflections and CF termination

By default, CF uses the minimum observed d spacing to define the Ewald sphere; alternatively, min_d can be used. The Ewald sphere can be increased using extend_calculated_sphere_to; this inserts missing reflections and gives them the status of “weak”. Weak reflections are also inserted for missing reflections within the Ewald sphere. Weak reflection phases and structure factors can be modified using scale_weak_reflections and add_to_phases_of_weak_reflections.

Changing the space group is possible; changing the space group to a higher symmetry from that as implied in the input hkl file often makes sense. Changing the space group to a lower symmetry implies less symmetry and is useful for checking whether a significantly better R-factor is realized.

Typically, a fraction of observed reflections is given the status of “weak” using fraction_reflections_weak. When a solution is found and CF terminates, a *.FC file is saved; this file comprises structures factors that produced the best R-factor. A new CF process can be initiated with phase information saved in the *.FC file using the Restart_CF macro. To further complete the structure, the new CF process may for example reduce perturbations to sharpen the electron density.


### Powder data considerations

For powder data it is usually best to maximize the number of constraints due to poor data quality; it is also best to use *.A files as generated by a Pawley refinement and to then use cf_in_A_matrix. No weak observed reflections within the observed Ewald sphere should be assigned by setting fraction_reflections_weak to zero. Instead, weak reflections can be included by extending the Ewald sphere with something like:


| extend_calculated_sphere_to 1 add_to_phases_of_weak_reflections = 90 Ramp(1, 0, 100); |
| --- |

If the Ewald sphere is extended such that the weak reflections are many then some of these weak reflections could well be of high intensity. Subsequently offsetting high intensity weak reflections by a constant could lead to too much perturbation and thus the following may be preferential:


| extend_calculated_sphere_to 1 add_to_phases_of_weak_reflections = Rand(-180,180) Ramp(1, 0, 100); |
| --- |

In a Pawley refinement the calculated intensities at the low d-spacing edge are often in error to a large extent; it is therefore best to remove these reflections using delete_observed_reflections, for example:


| delete_observed_reflections = D_spacing < 1.134; |
| --- |

A typical first try INP file template for powders is as follows:


| macro Nr { 100 } charge_flipping cf_in_A_matrix PAWLEY_FILE.A space_group $ a # b # c al # be # ga # delete_observed_reflections = D_spacing < #; extend_calculated_sphere_to # add_to_phases_of_weak_reflections = 90 Ramp(1, 0, Nr); flip_regime_2 = Ramp(1, 0, Nr); symmetry_obey_0_to_1 = Ramp(0.5, 1, Nr); Tangent(0.3, 30) min_grid_spacing 0.3 load f_atom_type f_atom_quantity { ... } |
| --- |


#### Powder data, the A matrix and the Tangent formula

In the case of charge-flipping from powder data TOPAS uses the diagonally normalized A-matrix cf_in_A_matrix (see example cf\cf-cime.inp), which we will call D, from a Pawley refinement (see example cf\cf-cime-pawley.inp) to modify normalized structure factors Eh calculated during the charge-flipping process; this produces better results than using reflections output in a SHELX format (Whitfield & Coelho, 2016). Equation (24-2) shows how the structure factors are modified.

The subscripts h and k correspond to reflections h and k respectively and the summation in k is over all reflections. Icalc,k and Iobs,k correspond to observed and calculated intensities. Equation (1) modifies the calculated intensities to include intensities from overlapping peaks. When there's no overlap Di,i=1 and Di,j=0 and the calculated intensities as well as Eh are not modified. When using the direct-methods tangent formula within the charge-flipping process as described by Coelho (2007), the D matrix is also used to modify Eh values used in triple phase relationships as shown in equation (2).


| where | (24-2) |
| --- | --- |


| where | (24-3) |
| --- | --- |

Eobs,h and Ecalc,h corresponds to tangent formula Eh values calculated from the observed and calculated intensities respectively. Ecalc,h is typically not used in the tangent formula, however, intensities used for determining Eobs,h can be grossly in error due to peak overlap. Equation (2) therefore influences triple phase relationships by weighing Eobs,h by qh; when there's no overlap qh=1 resulting in no modification. When there's significant overlap then qh is small and the influence of triple phase relationships using the h reflection is reduced. Equation (2) also includes a (1-qh) portion of Ecalc,h thus stating that when there's significant overlap the calculated Eh is to be more trustworthy than the observed Eh. Equation (24-3) corrects for errors in Eh when Iobs is similar-to Icalc; this assists in reducing the goodness of fit value, thus enhancing the chances of solving the structure.


#### The algorithm of Oszlányi & Süto (2005) and F000

Normalized structure factors enhance the chances of finding a solution (Oszlányi & Süto, 2006) and are realized by inclusion of f_atom_type’s and when correct_for_temperature_effects is non-zero. Example cf-1a7y-gabor.inp implements the algorithm of Oszlányi & Süto (2005) with normalized structure factors. In the original algorithm the amount of charge flipped is a function of the maximum electron density; this can be realized using:


| user_threshold = 0.2 Get(max_density_at_cycle_iter_0); |
| --- |

Get(max_density_at_cycle_iter_0) is a different value at the start of each CF process as phases are chosen randomly. An alternative means of defining the threshold is:


| fraction_density_to_flip 0.83 |
| --- |

The CF process is sensitive to the threshold value. A value of 0.83 for fraction_density_to_flip is optimum for 1A7Y and produces a solution in ~1000 iterations. A solution is not found however at 0.75 or 0.85. To overcome this sensitivity the fraction_density_to_flip parameter could be ramped as a function of iteration from a high value to a low value, or,


| fraction_density_to_flip = Ramp(0.85, 0.8, 100); |
| --- |

Implementation of such a ramp solves 1a7y in ~2000 iterations.

F000 is allowed to float when scale_F000 is set to 1. In the Oszlányi & Süto (2005) algorithm, a floating F000 produces the best results for some structures but not for others (see section 24.2.3). When the electron density is perturbed then a floating F000 often produces unfavourable oscillations in R-factors. In general, the electron density is best left unperturbed when scale_F000 is non-zero. Example cf-1a7y-gabor.inp does not seem to solve at a lower resolution, try for example:


| delete_observed_reflections = D_spacing < 1.1; |
| --- |

On the other hand, when scale_F000 is zero then electron density perturbations are possible; cf_1a7y.inp solves 1a7y at 1.1 Angstrom (include “delete_observed_reflections = D_spacing < 1.1”); cf_1a7y.inp uses flip_regime_2 and the tangent formula.


## Charge-flipping Investigations / Tutorials

The effects of CF keywords can be investigated by inclusion/exclusion of keywords or by changing equations. This section lists some investigative examples and highlights the use of keywords necessary to solve examples found in the CF directory.


### Preventing uranium atom solutions using pick_atoms

Example cf-1a7y-omit.inp uses pick_atoms to modify the peaks of the highest intensity atoms, or,


| pick_atoms *		choose_to 5		omit = Rand(1, 1.1); |
| --- |

This example additionally uses the tangent formula and 1a7y solves in ~100 iterations and with a large contrast in R-factors before and at convergence. Another means to modify the peaks are:


| pick_atoms *		choose_to 5		insert = Rand(-.1, 1); |
| --- |

The insert case is slightly slower than the omit case as the 5 atoms are first omitted before insertion. Each case however solves 1a7y in a similar number of iterations.

Example cf-1a7y-no-tangent.inp is similar but without the tangent formula, 1a7y in this case solves in ~1000 iterations.


### The tangent formula on powder data

In cf-alvo4.inp comment out the Tangent line as follows:


| ‘ Tangent(.5, 50) |
| --- |

Run cf-alvo4.inp and turn on Octahedra viewing in the OpenGL window. Visual inspection of picked atoms should show electron densities that are not recognizable as correct solutions.

Include the Tangent line and rerun; after a minute or two and at the bottom of the Ramps visual inspection of picked atoms should show a well-defined solution.

Thus, use of the tangent formula assists in solving cf-alvo4.inp.


### Pseudo symmetry – 441 atom oxide

CF works well on pseudo symmetric structures (Oszlányi et al., 2006). Example cf-pn-02.inp is an oxide structure that contains 441 atoms in the asymmetric unit (Lister et al., 2004); run CF to convergence. Pick atoms and turn on Octahedra viewing; all polyhedra should be well formed. Thus, CF works extremely fast and trivializes the solving of such structures. The contents of the INP file is as follows:


| charge_flipping cf_hkl_file 020pn.hkl space_group Pn a 24.1332  b 19.5793  c 25.1091  be 99.962 fraction_reflections_weak 0.4 symmetry_obey_0_to_1 0.3 Tangent(0.25, 30) load f_atom_type f_atom_quantity { MO = 42 2; P  = (126 - 42) 2; O  = (441 - 126) 2;  } |
| --- |


| scale_F000 1 fraction_reflections_weak 0.4 add_to_phases_of_weak_reflections 90 user_threshold = 0.15 Get(max_density_at_cycle_iter_0); |
| --- |

Slow convergence is observed due to the use of F000. This is opposite to the case of 1a7y in cf-1a7y-gabor.inp where F000 is necessary. Setting scale_F000 to zero greatly increases the rate of convergence.


### Origin finding and symmetry_obey_0_to_1

When symmetry_obey_0_to_1 is defined origin finding is performed each iteration of charge flipping. Symmetry elements of the space group are used in finding an origin. On finding an origin the electron density is shifted to a position that best matches the symmetry of the space group. Additionally, a restraint is placed on the electron density pixels forcing symmetry to be obeyed.

Run cf-ae14.inp to convergence; notice the P-1 symmetry. Remove symmetry_obey_0_to_1 and run to convergence; the origin should now be arbitrary.


### symmetry_obey_0_to_1 on poor resolution data

Run cf-ae5.inp until a solution is found; terminate CF, this saves the phase information to the file ae5.fc. Copy ae5.fc to ae5-save.fc. Place the following lines into the file cf-ae5-poor.inp:


| set_initial_phases_to ae5-save.fc randomize_initial_phases_by 0 |
| --- |

This simply starts CF with optimum phase values. Also include the following line:


| symmetry_obey_0_to_1 0.75 |
| --- |

Run cf-ae5-poor.inp; the atom positions after picking should visually produce the correct result. Comment out symmetry_obey_0_to_1 and rerun cf-ae5-poor.inp. R-factors should diverge and picked atoms should show a non-solution. Thus, symmetry_obey_0_to_1 assists in solving cf-ae5-poor.inp.

Include symmetry_obey_0_to_1 and remove set_initial_phases_to and randomize_initial_phases_by and then rerun cf-ae5-poor.inp. A solution should be obtained in a few minutes. Note that in this example the default flipping regime leads to regular occurrences of uranium atom solutions; this can be trivially ascertained by viewing the electron density. To reduce the occurrences of uranium atom solutions the following flipping regime is used:


| flip_regime_3 0.5 |
| --- |


### Sharpening clouds - extend_calculated_sphere_to

Example cf-ae9-poor.inp demonstrates the limit to which the present CF implementation can operate. Single crystal data is purposely chosen to isolate resolution effects and not intensity errors. The tangent formula is critical where without it the CF process is extremely perturbed and unstable. ‘flip_regime_3 0.5’ is used due to occurrences of uranium atom solutions.

There are no ramps, instead the CF process is restarted when the R-factor fails to decrease for 100 consecutive iterations, or,


| break_cycle_if_true = Get(iters_since_last_best) > 100; randomize_phases_on_new_cycle_by = Rand(-180, 180); |
| --- |

Half of the observed reflections are considered weak and additionally missing reflections up to 1 Angstrom are included and considered weak using:


| fraction_reflections_weak 0.5 extend_calculated_sphere_to 1 |
| --- |

The intensities of weak reflections are left untouched and instead a Pi/2 phase shift is randomly applied to ~30% of weak reflections as follows:


| add_to_phases_of_weak_reflections = If(Rand(0, 1) < .3, 90, 0); |
| --- |

A symmetry_obey_0_to_1 of 0.7 is used not merely to find an origin but rather to prevent the electron density from straying.

Run cf-ae9-poor.inp and a solution should be clearly recognizable after a few minutes. Change/remove keywords and rerun to view effects. Examples cf-cime-poor.inp and cf-ae5-poor.inp are similar.


### A difficult powder, CF-SUCROSE.INP


| fraction_density_to_flip 0.83 scale_density_below_threshold 0 |
| --- |

The following can be used to omit 30% of atoms:


| pick_atoms * activate = Cycle_Iter == 0; insert = If(Rand(0, 1) > 0.3, 10, 0); |
| --- |

Note that atoms are inserted at an intensity that is 10 times the average intensity. This increases the weight of inserted atoms relative to electron density noise. It also initially gives more weight to weak reflections.

Use of scale_density_below_threshold often results in CF requiring more iterations to solution; a solution however is preferable to no solution.


### Increasing contrast in R-factors

The act of flipping introduces an appreciable amount of unwanted high frequencies in the structure factors. This effect can be reduced by dampening high frequencies using apply_exp_scale which is ON by default. apply_exp_scale changes R-factors and not phases, directions taken by CF are unchanged.

Run cf-1a7y.inp until convergence. The difference in R-factors before and at convergence should be ~0.39 (i.e. 0.81 and 0.42). Turn OFF apply_exp_scale by including the following line:


| apply_exp_scale 0 |
| --- |

Rerun cf-1a7y.inp until convergence. The difference in R-factors before and at convergence should now be ~0.29 (0.81 and 0.52). Thus apply_exp_scale increases contrast in R-factors. Note that most of the increase seems to be realized from d-spacings less than 1 Angstrom.


## Charge Flipping and neutron_data

neutron_data informs the charge flipping routine that neutron scattering lengths are to be used. It also results in the following default neutron flipping routine being used:


| flip_equation = If(And(Get(density)< Get(threshold),Get(density) > 0.4 Get(min_density)), -Get(density),  Get(density) ); |
| --- |

flip_neutron can be used to change the 0.4 value occurring in the above equation, for example:


| flip_neutron = 0.5; |
| --- |

The tangent formula is made less accurate due to the negative scattering of H atoms. However, if positive scattering lengths are dominant then the tangent formula can stabilize refinement. For example (see test_examples\cf\neutron-cime\cf-neutron.inp), try:


| Tangent(0.3, 30) tangent_scale_difference_by = Ramp(1, 0, Nc); |
| --- |


## Charge-flipping Examples


| Table 24-3. Examples found in the CF directory. Number of atoms corresponds to the number of non-hydrogen atoms within the asymmetric unit. | Table 24-3. Examples found in the CF directory. Number of atoms corresponds to the number of non-hydrogen atoms within the asymmetric unit. | Table 24-3. Examples found in the CF directory. Number of atoms corresponds to the number of non-hydrogen atoms within the asymmetric unit. |
| --- | --- | --- |
| Single crystal data | Num atoms in asymmetric unit | Space group |
| cf-1a7y.inp cf-1a7y-gabor.inp cf-1a7y-omit.inp cf-1a7y-no-tangent.inp | 314 | P1 |
| cf-ae14.inp | 43 | P-1 |
| cf-ae5.inp cf-ae5-poor.inp | 23 | C2/c |
| cf-ae9.inp cf-ae9-poor.inp | 53 | P-1 |
| cf-gebaa.inp | 17 | P41212 |
| cf-pn-02.inp | 441 | Pn |
| cf-ylidm.inp | 17 | P212121 |
| Powder data | Powder data | Powder data |
| cf-alvo4.inp cf-alvo4-pawley.inp | 18 | P-1 |
| cf-cime-pawley.inp cf-cime.inp cf-cime-histo.inp cf-cime-poor.inp cf-cime-poor-histo.inp | 17 | P21/a |
| cf-sucrose.inp cf-sucrose-pawley.inp | 23 | P21 |


## Keywords in detail

[add_to_cloud_N !E]

[add_to_cloud_when !E]

The current cloud is added to the GUI cloud creating a running average cloud for display purposes. add_to_cloud_N corresponds to the number of most recent clouds to include in the running average. add_to_cloud_when determines when the current cloud is to be included in the running average; here’s an example:


| add_to_cloud_N 10 add_to_cloud_when = Mod(Cycle_Iter, 2); |
| --- |

[add_to_phases_of_weak_reflections !E]

Allows for modification to phases of weak reflections. For example, to add /2 to the phases of weak reflections then the following could be used:


| add_to_phases_of_weak_reflections 90 |
| --- |

When add_to_phases_of_weak_reflections is defined then the intensities of weak reflections are not set to zero; instead they are left untouched meaning that their intensities are set to the values as determined by the inverse Fourier transform. See also scale_weak_reflections.

[apply_exp_scale !E]

Determines a and b each CF iteration such that the following is a minimum:

R-factor = ∑| a Exp(b / D_spacing^2) Fc – Fo |

where Fc and Fo are the calculated and observed moduli respectively. Use of apply_exp_scale corrects R-factors in case of an incorrect temperature factor correction as applied when normalizing structure factors. Use of apply_exp_scale typically increases the difference between R-factors prior to and at convergence. apply_exp_scale is used by default, setting it to zero prevents its use.

[cf_hkl_file $file]

Defines the input hkl file.

[cf_in_A_matrix $file [scale_Aij !E] ]

Data input is from a file created using out_A_matrix from a previous Pawley refinement. The correlations in $file are used to partition intensities during each iteration of charge-flipping. This partitioning is applied to structure factors as used by CF and as used by the tangent formula. scale_Aij can be used to modify the A matrix off-diagonal coefficients, here are some examples:


| scale_Aij = Get(Aij); scale_Aij = Get(Aij)^2; ‘ The default scale_Aij = 0;          ‘ Equivalent to using a Pawley generated hkl file |
| --- |

CF on powder data can also be initiated using standard hkl files.

[break_cycle_if_true !E]

Interrupts charge flipping to execute randomize_phases_on_new_cycle_by. Cycle_Iter is set to zero and Cycle is incremented.

[correct_for_atomic_scattering_factors !E]

Structure factors are normalized when correct_for_atomic_scattering_factors is non-zero and when f_atom_type’s are defined. Structure factors are normalized by default.

[correct_for_temperature_effects !E]

Attempts to remove isotropic temperature effects from the structure factors. correct_for_temperature_effects is ON by default, setting it to zero will prevent this correction. Normalized structure factors are realized when correct_for_temperature_effects is ON and the unit cell contents are defined using f_atom_type and f_atom_quantity.

[delete_observed_reflections !E]

Reflections are deleted before entering CF according to delete_observed_reflections; it can be a function of D_spacing, for example:


| delete_observed_reflections = D_spacing < 1.1; |
| --- |

Once deleted, observed reflections cannot be reinstated by changing min_d.

[extend_calculated_sphere_to !E]

Used to sharpen electron density clouds by filling in missing reflections; added reflections are given the status of “weak”. extend_calculated_sphere_to can be used in conjunction with scale_weak_reflections and add_to_phases_of_weak_reflections to modify “weak” reflection magnitudes and phases respectively (see section 24.2.6); here’s an example:


| extend_calculated_sphere_to 1 add_to_phases_of_weak_reflections = If(Rand(0, 1) < .3, 90, 0); |
| --- |

[f_atom_type $type f_atom_quantity !E]...

Defines atom types and number of atoms within the unit cell; used by the tangent formula in determining Eh values and by the OpenGL display for picking atoms. For the tangent formula then relative quantities are important.

[find_origin !E]

If defined and non-zero, then origin finding is turned ON. symmetry_obey_0_to_1 defines find_origin by default. symmetry_obey_0_to_1 can be used without find_origin by defining and setting find_origin to zero.

[flip_equation !E]

Allows for a user defined flip; here’s an example:


| flip_equation = If(Get(density)<Get(threshold),-Get(density), Get(density)); |
| --- |

[flip_regime_2 !E]

The electron density is modified according to Eq. (24-1) and then further modified using:

flip_regime_2 is typically ramped from 1 to 0.

[flip_regime_3 !E]

The electron density is modified according to Eq. (24-1) and then further modified using:

A value of 0.5 for flip_regime_3 introduces little perturbation whilst reducing the occurrence of uranium atom solutions. It is recommended that flip_regime_3 be used in cases where flip_regime_2 produces uranium atom solutions. An additional perturbation, such as “add_to_phases_of_weak_reflections=90;” may be necessary.

[fraction_density_to_flip !E]

The amount of charge flipped is fractionally based. A value of 0.6, for example, sets the threshold  such that the sign of the lowest 60% of charge is changed. Get(threshold) can be used to retrieve .

[fraction_reflections_weak !E]

Defines the fraction of observed reflections to flag as “weak”. When scale_weak_reflections, add_to_phases_of_weak_reflections and extend_calculated_sphere_to are all not defined then intensities of weak reflections are set to zero effectively removing them from the charge flipping process. Otherwise, intensities of weak reflections are not set to zero; instead, they are left untouched prior to scale_weak_reflections and add_to_phases_of_weak_reflections and space group family averaging.

[histogram_match_scale_fwhm !E]

[hm_size_limit_in_fwhm !E]

[hm_covalent_fwhm !E]

An implementation of Histogram Matching (Baerlocher et al., 2007) where the distribution of pixels within the unit cell is restrained to one that matches Gaussian atoms with intensities corresponding to the atoms defined by f_atom_type's. The Histogram matching operation is performed when histogram_match_scale_fwhm evaluates to a non-zero value. Subsequently the full width at half maximum (FWHM) of the Gaussians (obtained from the file atom_radius.def) is scaled by histogram_match_scale_fwhm. hm_size_limit_in_fwhm corresponds to the extent to which the Gaussians are calculated in units of FWHM. Covalent radii are used if hm_covalent_fwhm evaluates to a non-zero value otherwise ionic radii are used. Example usage is as follows:


| histogram_match_scale_fwhm = If(Mod(Cycle_Iter, 3), 0, 1); hm_size_limit_in_fwhm 1 hm_covalent_fwhm 1 |
| --- |

Reported on is the fraction of pixels modified; values of 1 for both histogram_match_scale_fwhm and hm_size_limit_in_fwhm seem optimal, where typically ~15 to 20% of pixels are modified. Use of histogram matching should produce R-factors at convergence that are equal to or less than R-factors produced when not using histogram matching. Histogram matching sharpens the electron density cloud for data at poor resolution (see examples cf-cime-histo.inp and cf-cime-poor-histo.inp).

[min_d !E]

Determines in Å the resolution of observed reflections to work with; only observed reflections with a d-spacing above min_d are considered. min_d is evaluated each CF iteration. Get(num_observed_reflections_above_d_min) is updated when a change in min_d is detected. See also extend_calculated_sphere_to and delete_observed_reflections.

[min_grid_spacing !E]

If defined, then the grid spacing used is set to the smaller of min_d/2 and min_grid_spacing; useful for obtaining many grid points for graphical purposes.

[neutron_data]

Signals that the input data is of neutron type. Used in the picking of atoms and additionally Eh values are not corrected from any defined f_atom_type and f_atom_quantity keywords.

[pick_atoms $atoms]...

[activate !E]

[choose_from !E]

[choose_to !E]

[choose_randomly !E]

[omit !E]

[displace !E]

[insert !E]

pick_atoms modifies the electron density based on picked atoms. $atom corresponds to the atom types to be operated on; it can contain the wild card character ‘*’ and the negation character ‘!’, see section 20.26 for details. The operations of pick_atoms are invoked when activate evaluates to a non-zero value, for example,


| pick_atoms “O C”  activate = Mod(Cycle_Iter, 20) == 0; |
| --- |

The picking routine attempts to locate the atom types found in $atom based on the intensities of picked atoms and the scattering power of the atoms defined in f_atom_type. For example,


| load f_atom_type f_atom_quantity { Ca 2 O 10 C 12 } pick_atoms “O C” |
| --- |

Here two Ca atoms are first picked and then 10 O atoms and then 12 C atoms. The picked atoms operated on will be the O and C atoms with the Ca atoms ignored.

choose_from and choose_to can be used to limit the number of atoms operated on. Note, that picked atoms within pick_atoms are sorted in decreasing intensity order. For example, to not operate on the first three O atoms and the last 2 C atoms then the following could be used:


| choose_from 4 choose_to 20 |
| --- |

choose_randomly further reduces the atoms operated on and is executed after choose_from and choose_to.

omit removes operated-on-atoms from the electron density. Atoms can be partially removed by setting omit to values less than 1. Values greater than 1 can also be used, the effect is to change the sign of the electron density. omit operating on a few of the highest intensity atoms is an extremely effective means of preventing the occurrence of uranium atom solutions, see cf-1a7y-omit.inp; for example:


| pick_atoms * choose_to 5 omit = Rand(1, 1.1); |
| --- |

Omitting atoms randomly is a technique referred to as “random omit maps” in ShelXD, (Schneider and Sheldrick, 2002).

insert inserts operated on atoms; a value of 1 inserts the atoms with an intensity that is equal to the average of the picked atoms. Values of less than 1 decreases the intensity of the inserted atoms. When insert is defined then omit is internally defined if it does not already exist. Thus, atoms are removed before insertion by default.

displace displaces in Å atom positions from their picked positions; it is evaluated before insert. For example, to randomly displace atoms by 0.3 Å then the following could be used:


| displace = Rand(0.4, 0.6); insert 1 |
| --- |

There can be more than one occurrence of pick_atoms, for example to limit uranium atom solutions then the following can be used:


| pick_atoms * choose_to 5 insert = Rand(-.1, 1); |
| --- |

To randomly remove a further ~33% of atoms then the following could be used:


| Break_cycle_if_true = Get(iters_since_last_best) > 10; pick_atoms * activate = Cycle_Iter == 0; insert = If(Rand(0, 1) > 0.33, 10, 0); |
| --- |

Note that in this example atoms are inserted at ten times the average picked intensity; this simply gives more weight to picked atoms relative to electron density noise. Additionally weak reflections are also given more weighting.

[pick_atoms_when !E]

Atoms are picked in the OpenGL display when pick_atoms_when evaluates to a non-zero value, here’s an example:


| pick_atoms_when = Mod(Cycle_Iter + 1, 10) == 0; |
| --- |

Note that picking can be manually initiated from the Cloud dialog of the OpenGL display. A text description of picked atoms can be obtained by opening the “Temporary output” text window of the OpenGL window.

[randomize_initial_phases_by !E]

Initializes phases. To start a process with already saved phase information then the following could be used:


| set_initial_phases_to aleady_saved.fc randomize_initial_phases_by 0 ‘ this has a default of 0 |
| --- |

[randomize_phases_on_new_cycle_by !E]


| randomize_phases_on_new_cycle_by = Rand(-180, 180); ‘ an example |
| --- |

[scale_density_below_threshold !E]

Electron density pixels that are less than the threshold value are scaled by scale_density_below_threshold. Values for scale_density_below_threshold that are less than 1 tends to sharpen the electron density and to reduce large oscillations in R-factors; the latter occurs for bad data, see example cf-sucrose.inp. A value of zero for scale_density_below_threshold results in “low density elimination” similar to that of Shiono & Woolfson (1992).

[scale_E !E]

Normalized structure factors (Eh values) are a function of correct_for_temperature_effects and unit cell contents. scale_E allows for an additional scaling of Eh values.

[scale_F !E]


| scale_F = Exp(-0.2 Get(d_squared_inverse)); |
| --- |

[scale_F000 !E]

Scale should be set to 1 for compliance with the algorithm of Oszlányi & Süto (2004). When scale_F000 is non_zero, modifications to the electron density produce unfavourable effects.

[scale_weak_reflections !E]

By default, weak reflection structure factors are set to zero; however, when either scale_weak_reflections or add_to_phases_of_weak_reflections is defined then weak reflection structure factors are instead modified accordingly, for example:


| scale_weak_reflections = Rand(-0.2, 0.4); |
| --- |

scale_weak_reflections or add_to_phases_of_weak_reflections can be a function of D_spacing.

[set_initial_phases_to $file]

[modify_initial_phases !E]

Sets initial phases to those appearing in $file. Typically, $file corresponds to a *.FC file saved in a previous charge-flipping process. modify_initial_phases is executed each CF iteration; it can be used to restrain the phases of $file. For example,


| modify_initial_phases = Get(initial_phase) + Min(Abs(Get(phase_difference)),45); |
| --- |

[space_group $]

If defined, then the cf_hkl_file is assumed to comprise merged hkls corresponding to the defined space group; otherwise, the cf_hkl_file is assumed to be of space group type P1.

[symmetry_obey_0_to_1 !E]

If a space group is defined, then symmetry is adhered to according to symmetry_obey_0_to_1. symmetry_obey_0_to_1 can be thought of as a real space electron density restraint; its value should range between 0 and 1. If 1 then symmetry is obeyed 100%; if 0 then for a particular set of equivalent grid points, as determined by the equivalent positions of the space group, an average density avg is obtained. The electron densities on the grid points are then adjusted as follows:

new =  (1  symmetry_obey_0_to_1) + symmetry_obey_0_to_1 avg

The text output 'symmetry error' as displayed when symmetry_obey_0_to_1 is used and is defined as follows:

where the summation is over all electron density grid points. symmetry_obey_0_to_1 defines find_origin by default. find_origin is applied before symmetry_obey_0_to_1. find_origin shifts the electron density such that an approximate error in 'symmetry error' is minimized; thus find_origin assists in the symmetry_obey_0_to_1 restraint.

[tangent_num_h_read !E]

[tangent_num_k_read !E]

[tangent_num_h_keep !E]

[tangent_max_triplets_per_h !E]

[tangent_min_triplets_per_h !E]

[tangent_scale_difference_by !E]

tangent_num_h_read and tangent_num_k_read defines the number of highest h and highest k reflections to read in determining triplets. tangent_num_h_keep defines the number of highest h reflections to include for tangent formula updating. tangent_max_triplets_per_h and tangent_min_triplets_per_h defines the maximum and minimum number of triplets per reflection h. Reflections with less than tangent_min_triplets_per_h are not included for tangent formula updating. tangent_scale_difference_by corresponds to S in the following:

[user_threshold !E]

By default, Get(threshold) is determined using fraction_density_to_flip. When defined then user_threshold overrides fraction_density_to_flip. Electron density pixels are normalized to have a maximum value of 1, thus typical values for user_threshold range between 0 and 0.1.

[use_Fc]

Sets initial phases to those saved in a previous *.FC file. The FC file used corresponds to the same name as the data file, defined using cf_hkl_file or cf_in_A_matrix, but with a FC extension. use_Fc is similar-to set_initial_phases_to except that the file is implied.

[verbose #]

A value of 1 outputs text in a verbose manner. A value of 0 outputs text when the R-factor is less that a previous value encountered within a particular Cycle.

[view_cloud !E]

Informs a detected GUI to display the electron density. Here are some examples:


| view_cloud 1 ‘ Update cloud every charge-flipping iteration view_cloud = Mod(Cycle_Iter, 10) == 0; |
| --- |
