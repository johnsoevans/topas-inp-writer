# Solving proteins at atomic resolution


```
Include_Charge_Flipping
charge_flipping
    [cf_plot_histo !E]
    [cf_plot_fit !E]
    [add_to_phases_of_non_weak_reflections !E] ...
    [scale_flipped !E]
    [cf_percent_ED_ge_H #]
    [pick_atoms $atom]...
        [choose_from !E]
        [choose_to !E]
        [choose_randomly !E]
        [with_symmetry !E]
        [omit !E]
        [insert !E]
        [pick_fwhm !E1]
        [omit_fwhm !E1]
        [insert_fwhm !E1]
    [insert_atoms {
        [activate !E1]
        [in_cartesian]
        [insert_atom] ...
            [x !E] [y !E] [z !E] [occ !E]
    }]...
    [cf_set_phases !E {
        #h #k #l #Re #im
    }]
    [prm N # val_on_continue !E] ...
```
Macros in `Charge_Flipping.INC`. Examples (`CF-PROTEIN\`): `1a7y-p1\solve.inp`, `2erl-C2\solve.inp`, `1byz-p1\solve.inp`, `2knt-p21\solve.inp`, `1aho-p212121\Solve.inp`, `4lzt-p1\solve.inp`, `1mc2-c121\Solve.inp`, `1dy5-p21\Solve.inp`, `2wfi-p212121\solve.inp`, `1hhz-p3221\Solve.inp`, `1c75-p212121\Solve.inp`, `1b0y-p212121\Solve.inp`, `1ctj-r3r\solve.inp`, `2pvb-p212121\solveinp`, `1cKu-p212121\solve.inp`, `1swz-p3221\solve.inp`, `5da6-R32\solve.inp`, `1ctj-r3r\1-atom.inp`, `2pvb-p212121\1-atom.inp`, `1c75-p212121\1-atom.inp`, `5da6-R32\1-atom.inp`, `1cKu-p212121\1-atom.inp`, `2wfi-p212121\1-atom.inp`, `4lzt-p1\2-atoms.inp`

The largest proteins ever solved ab initio at atomic resolution can be solved using modified charging flipping strategies, see Coelho (2021) for details. Difficult or large structures can be solved in minutes, rather than days using Amazon AWS Cloud computing. New/modified charge_flipping keywords are shown above. A single strategy does not solve all structures; a strategy successful on one structure is not necessarily successful on another. However, it will be shown that only two strategies can solve a large range of the most difficult structures. New keywords allow for a variety of strategies. scale_flipped scales flipped electron density (ED) charge; it is applied each charge-flipping iteration. insert_atom inserts atoms in the ED when activate is non-zero. val_on_continue for prm(s) is evaluated at the end of each charge-flipping iteration. cf_percent_ED_ge_H returns the percentage of ED pixels greater than 1 where the maximum of the ED is set to number of electrons in the heaviest atom defined by f_atom_type. Values less than 1 often signal a Uranium atom situation where a single ED peak dominates. cf_percent_ED_ge_H is displayed during charge flipping in the Fit Dialog. cf_plot_histo plots a frequency distribution of the electron density pixel intensity.

When cf_set_phases is non-zero, the phases for the family of reflections (#h, #k, #l) are set to the phase corresponding to #Re and #Im. cf_set_phases is useful when phases are known or for setting origin defining phases; for triclinic structures, three origin defining phases are possible. Additionally, intensities of the reflections are scaled by the value evaluated by cf_set_phases.

Table 19-1 show difficult benchmark structures, as listed by Elser et al. (2017) and Burla et al. (2011), that have been solved ab initio; see corresponding solve.inp files for details. It is best to do preliminary investigations on the local computer (non-Cloud) to determine which strategy might work best. Once a strategy is chosen, INP files can be fed to the Cloud for rapid structure solution. Up to 500 spot instance Virtual Machines (VMs) are easily obtained on the Amazon AWS system in Australia at a cost of ~0.035 USD cents per VM per hour, or, 3.40 USD per hour for 100 machines. These prices are Amazon AWS dependent. Prices are shown prior to the creation of the VMs. The times shown in Table 19-1 can be easily doubled when one considers the preliminary analysis taken to arrive at the appropriate strategy. Typically, strategies are tried on the local computer before migrating the problem to the Cloud. Also, the structure solution process is normally halted after the first solution is found; for the investigative purposes, however, the structures in Table 19-1 were each solved at least 5 times. The two strategies mentioned in Table 19-1 are:


| ‘ S0 strategy 	fraction_reflections_weak 0.5 	add_to_phases_of_weak_reflections 90 	fraction_density_to_flip  0.9 	scale_flipped 0.6 |
| --- |

S0 seems to work well for large structures with a relatively heavy atom. Non-triclinic structures with symmetry seems to succumb to the S1 strategy, or:


| ‘ S1 strategy fraction_reflections_weak 0.5 	add_to_phases_of_weak_reflections = Rand(-180, 180);  	fraction_density_to_flip  0.97 	scale_flipped 0.2 	pick_atoms * 		pick_fwhm 3 		choose_randomly = If(Mod(Cycle_Iter, 50), 0, 10); with_symmetry 1  		insert 10       ‘ Increase if the most dominant atom does not change symmetry_obey_0_to_1	0.25 find_origin 0 flip_regime_2 = Sine_Wave(10/4,-2,2,10); ‘ Used when there’s not enough perturbation |
| --- |

S1T extends the S1 strategy with the addition of the tangent formula, or the inclusion of:


| Tangent(0.5, 30) |
| --- |


| Table 19-1. Ab initio structure solution strategies. Time indicates time to solution on average. Each structure was solved at least 5 times. Num_VMs greater than 8 refers to the number of VMs used on the Cloud; Num_VMs=9 corresponds to an 8 core local computer (a laptop). Cost corresponds to the average Cloud cost to a solution using the strategy indicated. |
| --- |


| Solved | PDB code | Space group | N/Z | dmin (Å) | Time (min) | Num VMs | Cost USD | Strategy | Np |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| yes | 1a7y | P1 | 270 | 0.94 | 0.1 | 8 | - | S0 | - |
| yes | 2erl | C2 | 303 | 1.00 | 1 | 200 | 0.10 | S1 | 8 |
| yes | 1byz | P1 | 408 | 0.90 | 1 | 200 | 0.10 | S0 | - |
| yes | 2knt | P21 | 460 | 1.20 | 16 | 200 | 2.00 | S1T | 7 |
| yes | 1aho | P212121 | 500 | 0.96 | 1 | 200 | 0.10 | S1 | 8 |
| No | 1w7q | P65 | 828 | 1.10 | >240 | 200 | >28 | S0,S1 | 4 |
| yes | 4lzt | P1 | 1183 | 0.95 | 2 | 8 | - | S1 | 10 |
| yes | 1mc2 | C2 | 1254 | 0.80 | 2 | 200 | 0.20 | S1 | 10 |
| yes | 1dy5 | P21 | 1894 | 0.87 | 1 | 500 | 1.40 | S1 | 30 |
| yes | 2wfi | P212121 | 1920 | 0.75 | 18 | 500 | 5.10 | S1 | 15 |
| yes | 1hhz | P3221 | 354 | 0.99 | 7 | 200 | 1.00 | S1 | 6 |
| yes | 1c75 | P212121 | 1184 | 0.92 | 1 | 8 | - | S0 | - |
| yes | 1b0y | P212121 | 837 | 0.93 | 1 | 8 | - | S0 | - |
| yes | 1ctj | R3:R | 918 | 1.10 | 1 | 200 | 0.10 | S1 | 4 |
| yes | 2pvb | P212121 | 1096 | 0.91 | 3 | 200 | 0.35 | S1 | 5 |
| yes | 1cku | P212121 | 1599 | 1.20 | 1 | 200 | 0.15 | S1 | 8 |
| yes | 1swz | P3221 | 1254 | 1.06 | 50 | 200 | 5.80 | S1 | 15 |
| yes | 5da6 | R32 | 1390 | 1.05 | 5 | 500 | 1.40 | S1 | 15 |


| PDB code | Reference |
| --- | --- |
| 1a7y, 2erl, 1byz, 2knt, 1aho, 1w7q, 4lzt, 1mc2, 1dy5, 2wfi | Elser & Lan (2017) |
| 1hhz, 1c75, 1b0y, 1ctj, 2pvb, 1cku, 1swz | Burla et al. (2011) |
| 5da6 | Mooers (2016) |

PDB codes 1b0y, 1ctj, 1c75 and 1cku are easily solved (a few minutes) on a laptop using the S0 strategy. 2knt uses the tangent formula due to its relatively low-resolution data (1.2Å) as well as its relatively small number of non-hydrogen atoms in the asymmetric unit. 1w7q is a light element structure that was not solved ab initio after more than four hours. flip_regime_2 of S1 introduces perturbation and it should be used for cases where there the ED seems quiet during the charge flipping process; decreasing the absolute value of flip_regime_2 reduces perturbation. In the case of 1cm2, flip_regime_2 was set to oscillate between -1 and 1. Larger values clearly shows too much perturbation in the ED.

Graphically inspecting the ED or looking at the (%ED > H) output on the local can be used to determine if there’s too little or too much perturbation, during charge flipping. (%ED > H) should typically range from 1 to 5. For example, setting fraction_reflections_weak to 0.9 results in too much perturbation. Or, using the Tangent formula macro on P1 structures, without the mitigation strategy of Fix_Uranium_3, results in too little perturbation resulting in uranium atom solutions. The value set for Fix_Uranium_3 should be just high enough to prevent Uranium atom solutions; a value of 1 seem to work in most cases. The number used for insert of pick_atoms should be just high enough to change the position of the highest intensity ED peak every 40 to 50 iterations as defined by choose_randomly; note pick_atoms is executed when choose_randomly is greater than zero. add_to_phases_of_weak_reflections=90 results in a shifting origin and it should not be used with symmetry_obey_0_to_1; the latter prevents origin shifting. add_to_phases_of_weak_reflections should be set to Rand(-180,180) instead of 90 when using symmetry_obey_0_to_1. Further structure solution tips are:

Try the simple S0 strategy first for number of atoms less than about 300.

If a heavy atom is present, then try S0.

Inspect the ED graphically; if it does not show distinct atoms after a few iterations then change strategy.

Use S1 for large difficult structures.

Try the tangent formula when the number of non-hydrogen atoms in the asymmetric is less than ~500 atoms. The tangent formula reduces perturbation allowing lower resolution structure to be solved.

The range of convergence of structure factor phases can be investigated by loading optimum structure factor phases values, using set_initial_phases_to, and then adding to the optimal phases using randomize_initial_phases_by. High resolution data can have their optimal phases changed by an amount of 0.96*Rand(-180,180) whilst still being able to solve the structure within a few dozen charge flipping iterations. Most of the Solve.inp examples contain the following for investigating this range of convergence:


| #if (0) 		set_initial_phases_to optimal.fc 		randomize_initial_phases_by = Rand(-180, 180) 0.9; 	#endif |
| --- |


## Ab initio solution of triclinic 4lzt

PDB code 4lzt comprises 1183 non-hydrogen atoms in the unit cell and is considered difficult to solve, see Elser et al., 2017. 4lzt contains 10 Sulphur atoms and these are considered moderately heavy. If we were to insert ED peaks at positions corresponding to the highest two peaks of the optimum electron density, then charge flipping finds a solution and within a few iterations; 4lst\2-atoms.inp demonstrates this where an ED starting with the two highest optimal peaks, inserted using insert_atoms, produces and R-factor plot of:

In fact, any two of the five highest peaks produce similar R-factor plots. However, these optimal ED peak positions are unknown. The strategy that works therefore involves picking an atom randomly out of the 10 largest peaks in the electron density and setting the picked atom to a large density. The INP file looks like:


| fraction_reflections_weak 0.5 		add_to_phases_of_weak_reflections = Rand(-180, 180); 	fraction_density_to_flip 0.97      		scale_flipped 0.2                     	pick_atoms * 		pick_fwhm 5 omit_fwhm 1 insert_fwhm 1 		choose_randomly = If(Mod(Cycle_Iter, 50), 0, 10); 		insert 10 	Fix_Uranium_3(0.5) ATP(1000, 1) ‘ Totally randomize phases after 1000 iterations |
| --- |

pick_atoms picks atoms with a FWHM of 5 Å, as defined by pick_fwhm; this relatively large value ensures that the picked atoms are approximately 5 Å apart. Once picked, pick_atoms removes the atoms with a FWHM as defined by omit_fwhm, and then inserts atoms with a FWHM of insert_fwhm. A solution of 4lzt takes a minute or two on a laptop computer and a typical R-factor plot looks like:


## Solution of non-triclinic lattices using a known atomic position

Large non-triclinic structures with many origins are difficult to solve. However, because of symmetry, non-triclinic structures can often be solved when the position of a single atom is known within the ED. Atoms can be inserted in the ED using insert_atoms; for PDB code 2wfi we have:


| charge_flipping 	cf_hkl_file sf.cif ‘ Structure fact file from PDB 	space_group P212121 	a  37.544 	b  65.144 	c  69.680 	fraction_reflections_weak 0.5 		add_to_phases_of_weak_reflections = Rand(-180, 180); 	fraction_density_to_flip 0.97 		scale_flipped 0.2 	symmetry_obey_0_to_1 0.25 find_origin 0 	macro Occ_0 { 100 } 	insert_atoms { 		activate = Mod(Cycle_Iter, 100) == 0; 		load insert_atom x y z occ  { 			0.72697 0.77709 0.11312  100 ‘ Position of known atom 		} 	} |
| --- |

The x, y, z coordinates of insert_atom can be in Cartesian coordinates using the in_cartesian keyword at the insert_atoms level. The use of symmetry_obey_0_to_1 often assists in solution determination for non-triclinic structures. 2wfi can be solved ab initio; however, it can be easily solved if the position of one atom was known as seen by running 2wfi-p212121\1-atom.inp; it gives and R-factor plot that looks like:

The OpenGL plot (right) shows the solution.

Using any one of the first six highest optimal ED peaks results in a solution. Many structures can be solved from knowing the position of just one atom. 1-atom.inp files, similar-to the 2wfi case, are given for 1ctj, 2pvb, 1c75, 5da6, 1cku, 2wfi.


## Ab initio solution of 5da6 in space group R32

PDB code 5da6 comprises 1390 atoms in the asymmetric unit. Placing an ED peak at any of its potassium sites result in the correct solution (see 5da6-r32\1-atom.inp). 5da6 can also be solved ab initio using the following INP file (see 5da6-r32\solve.inp):


| charge_flipping 	cf_hkl_file sf.cif ‘ Structure factor file from PDB 	space_group R32 	a  42.890  b  42.890  c  266.936  ga 120.00 	fraction_reflections_weak 0.5 		add_to_phases_of_weak_reflections = Rand(-180, 180); 	fraction_density_to_flip 0.97 		scale_flipped 0.2 	symmetry_obey_0_to_1 0.25 find_origin 0 	pick_atoms * 		pick_fwhm 5 omit_fwhm 1 insert_fwhm 1 		choose_randomly = If(Mod(Cycle_Iter, 50), 0, 15); 		insert 10 	flip_regime_2 = Sine_Wave(50 / 4, -2, 2, 50); 	ATP(1000, 1) ‘ Randomize all phases every 1000 iterations |
| --- |

It takes approximately six hours on average to solve 5da6 using the above INP file on an 8-core laptop computer. This time is reduced to 5 minutes on the Cloud where the INP file is run simultaneously on 500 VMs. The best solution on each VM computer or the best solution overall can be viewed during the process. Here’s a typical Cloud run (right):
