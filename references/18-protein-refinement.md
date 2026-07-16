# Protein Refinement


## Reading Protein Data Bank (PDB) CIF files


```
[pdb_cif_to_str_file $file] ...
    [pdb_ignode_adps !E0]
    [pdb_cif_sites $sites]
    [pdb_cif_to_str #0]
```
Examples: `CF-PROTEIN\2pvb-p212121\gen.inp`, `CF-PROTEIN\2pvb-p212121\match.inp`, `CF-PROTEIN\6y84-c121\Refinement.inp`

Protein Data Bank (PDB) PDBx/mmCIF fles from https://www.rcsb.org/ can be downloaded and converted to INP text using pdb_cif_to_str_file. The operation is performed when pdb_cif_to_str is 1; on termination of refinement pdb_cif_to_str is set to 0 in the OUT file. The INP text generated is placed in the INP file after the pdb_cif_to_str keyword, or:


| pdb_cif_to_str_file cif.cif pdb_ignode_adps  1  pdb_cif_to_str   0 xdd_scr sf.cif lam lo 0.9096 str scale @ 1 a 51.03 b 49.81 c 34.57 space_group P212121 site ACE_C_0_1_HETATM    x  0.07354 y  0.35529 z  0.47637 occ C  1.00 beq  6.24 site ACE_O_0_2_HETATM    x  0.06210 y  0.34246 z  0.50194 occ O  1.00 beq  7.96 site ACE_CH3_0_3_HETATM  x  0.06198 y  0.35666 z  0.43651 occ C  1.00 beq  8.20 site SER_N_1_4_ATOM      x  0.09557 y  0.36858 z  0.48319 occ N  1.00 beq  6.66 site SER_CA_1_5_ATOM     x  0.10676 y  0.36880 z  0.52155 occ C  0.46 beq  8.09 ... rigid point_for_site SER_N_1_4_ATOM    ux  -1.40900 uy  0.28011 uz  -1.21189  point_for_site SER_CA_1_5_ATOM   ux  -0.83800 uy  0.29111 uz   0.11411  point_for_site SER_CA_1_6_ATOM   ux  -0.70700 uy  0.20011 uz   0.04411  ... Rotate_about_axies(@ 0 RX_, @ 0 RY_, @ 0 RZ_) translate tx @    6.28600 ty @   18.07889 tz @   17.91589 |
| --- |

A rigid body is generated for each residue with coordinates set relative to its geometric center. Refinement can proceed on the generated INP text by setting the file name of xdd_scr to the name of the structure factor file 2Pvb-sf.CIF, also downloaded from https://www.rcsb.org/. Running 2pvb\gen.inp produces gen.out; setting gen.inp to gen.out and running produces a fit.

pdb_cif_sites considers sites with names matching the site identifying string $sites. This can be used, for example, to extract all residues of the same type. The translate keywords of the rigid bodies can then be set to zero and the individual sites of the residues penalized such that sites of the same name are brought together; example INP text to do this is as follows:


| macro Match(s)   			{   				atomic_interaction s = R^2;   					ai_sites_1 s*   					ai_sites_2 s*   					ai_closest_N 1   					ai_only_eq_0   				penalty = s;   			}   		Match(LYS_N_)   		Match(LYS_CA_)   		Match(LYS_C_)   		Match(LYS_O_)   		Match(LYS_CB_)   		Match(LYS_CG_)   … |
| --- |

Running example 2pvb\match.inp produces the following showing overlay of LYS residues:


## Protein Refinement, 6y84, SARS-CoV-2 main protease

The structure factors and PDBx/mmCIF files for 6y84 can be downloaded from the PDB. To generate an initial INP file then create an INP file with the following (see 6y84-c121\Refinement.inp):


| pdb_cif_to_str_file cif.cif  	pdb_ignode_adps  1   	pdb_cif_to_str 0 |
| --- |

After refinement, the INP file can be updated with the structure generated from the CIF file. Refining on the updated INP file gives:
