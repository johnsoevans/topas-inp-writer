# Molecular dynamics (MD)


| molecular_dynamics md_time_step !E   	(default = 0.002) md_time !E md_scale !E			(default = 1) Parameter attributes: _md_k !E			(default = 1) _mass !E			(default = 1) _md_force !E		(default = 0) | Examples test_examples\grs-alvo4\ md-1.inp md-2.inp md-3.inp md-4.inp grs-0.inp |
| --- | --- |


## Molecular dynamics in a general manner

Defining molecular_dynamics (MD) places the program in a non-refinement mode where parameters of any type can be updated in a time dependent manner. The Verlet (1967) algorithm is used for updating parameters. In the present implementation, parameters that are not typically associated with molecular dynamics can be updated in a MD manner. This is accomplished with the use of the parameter attributes of _md_k and _md_mass.

Force(k) = m a(k) = dRwp/dp

Velocity(k+1) = Velocity(k) + (dRwp(k)/dp) / m

In the Verlet algorithm, velocity is not considered explicitly and instead p is updated as follows:

p(k+1) 	= 2 p(k) – p(k-1) + a(k) t2

= 2 p(k) – p(k-1) + (1/m) (dRwp(k)/dp) t2

where t is the time step of the molecular dynamics. The mass m is set using _mass. To introduce flexibility, the present implementation allows modifications of p(k+1) as follows:

p(k+1) 	= (p(k) – p(k-1) + (_md_k / _mass) (dRwp(k)/dp) t2) md_scale + p(k)

This equates to the Verlet algorithm with the default value of 1 for _md_k, _mass and _md_scale. md_scale is a means of increasing or decreasing atomic movements (increasing or decreasing temperature).


## Molecular dynamics for atoms

In the absence of the _mass attribute, mass is determined from the masses found in the isotopes.txt file for site occupancies, as defined by the occ keyword, and weighted by the occ values. In the absence of the _md_k attribute, md_k is determined for x, y and z coordinate parameters as follows:

md_k for x = ax

md_k for y = by

md_k for z = cz

where 	ax = 1

bx = Cos(Get(ga) Deg)

by = Sin(Get(ga) Deg)

cx = Cos(Get(be) Deg)

cy = (Cos(Get(al) Deg) - cx bx) / by

cz = Sqrt(1.0 - cx^2 - cy^2)

The following two sites are therefore equivalent:


| site Al  x @ # _mass = 26.981; _md_k = ax;  y @ # _mass = 26.981; _md_k = by;  z @ # _mass = 26.981; _md_k = cz;  occ Al+3 1 ‘ and site Al x @ # y @ # z @ # occ Al+3 1 |
| --- |

md-1.inp operates in the P-1 space group; this can be changed to P1 by outputting the fractional coordinates in P1 as follows:


| p1_fractional_to_file aac.txt in_str_format 	in_cart 0 	na 2 nb 2 nc 2 |
| --- |

Here, a 2x2x2 unit cell is outputted in P1 to the aac.txt file. Md-2.inp describes such a unit cell comprising 288 atoms. One of the AL1 atoms is offset, and running the MD simulation results in the atom returning to its lowest energy configuration position. This return to the optimal position is due to the small offset of 2.92 Å. The following shows the starting configuration:

where the yellow atom is the Al1 atom’s offset, and the dark grey atom is the original position of the Al1 atom. It is informative to watch the yellow atom migrate to the dark grey atom. The INP text that produces the coloured Al1 sites is:


| track_buffer 100 site qAl1 x   0.37342 y   0.34930 z   0.20369  occ Al+3  1 ' original posn site Hi1  x @ 0.2     y @ 0.2     z @ 0.1  occ Al+3  1 track = Mod(Cycle_Iter, 20) == 0; |
| --- |

Note the last display has been disabled (item 84); it comprises all 288 atoms in the cell. Including line 84 produces:

md-3.inp moves the Al1 atom 4 Å from the original position and in a random direction; the pertinent INP text is:


| temperature 1 md_scale = If(Cycle_Iter < 2, 0.1, 1); site Hi1 x @  0.37342 y @  0.34930  z @ 0.20369  occ Al+3 1 rand_xyz 4 |
| --- |

Clicking on the Break icon; ie.

executes rand_xyz. Often the energy of the system (which is kept constant) is too great and the MD goes chaotic. This behaviour can be damped using md_scale as seen above. Also, repulsion terms such as 1/R9 can be very large when R is small; such small bond distances are unrealistic and modifying Uij to avoid large values is beneficial. In the present work the equation used for the grs_interaction, rewritten in terms of a yobs_eqn, is given in grs-0.inp, or,


| macro & n { 9 } macro & q { -1 } macro & ro { 2 }   ‘ x-axis value at the minimum  macro & rsm { 1 }   yobs_eqn aac.xy =     If (X < rsm, 		(Abs( q ) / n) (ro^(n-1)) ( (-n rsm^(-2 - n)/2) X^2 + rsm^(-n) + n/(2 rsm^n)), 		(Abs( q ) / n) (ro^(n-1)) / X^n + q / X      ); 	min 0.1 max 7 del 0.01 |
| --- |

Note, the rsm value of 1. For R < rsm, U is modified such that large values are not encountered. The following shows two views of the same yobs_eqn plot:


|  |  |
| --- | --- |


## Applying a force on atoms

The _md_force attribute can be used to apply a force to atoms. The MD simulation in such a case maintains energy conservation by adjusting the kinetic energy of the system. For the case of AlVO4 and for the crude potential used; it is interesting that for a force along the a-axis on an Al+3 atom, the structural integrity is maintained as seen below (see md-4.inp):

The structure, however, loses its integrity for a similar force along the c-axis.
