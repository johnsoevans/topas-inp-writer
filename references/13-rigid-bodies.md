# Rigid bodies


```
[rigid]...
    [point_for_site $site [ux | ua E] [uy | ub E] [uz | uc E] ]...
        [in_cartesian] [in_FC]
    [z_matrix atom_1 [atom_2 E] [atom_3 E] [atom_4 E] ]...
    [rotate E [qx | qa E] [qy | qb E] [qz | qc E] ]...
        [operate_on_points $sites]
        [in_cartesian] [in_FC]
    [translate [tx | ta E] [ty | tb E] [tz | tc E] ]...
        [operate_on_points $sites]
        [in_cartesian] [in_FC]
        [rand_xyz !E]
        [start_values_from_site $unique_site_name]
```

Rietveld or Pair Distribution Function refinement can comprise rigid bodies. Rigid bodies comprise points in space defined using z_matrix or point_for_site keywords or both simultaneously. Operations can be performed on these points using rotate and translate. Rigid body operations include:

Translating a rigid body or part of a rigid body.

Rotating a rigid body or part of a rigid body around a point.

Rotating a rigid body or part of a rigid body around a line.

ua, ub, uc, ta, tb, tc, qa, qb, qc and the parameters of z_matrix are all refinable parameters which can comprise parameter attributes such as min/max. The directory rigid contains rigid body examples in *.RGD files. These files can be viewed and modified using the Rigid-Body-Editor of the GUI.

rigid defines the start of a rigid body. point_for_site defines a point in space with Cartesian coordinates given by the parameters ux, uy uz. Fractional equivalents can be defined using ua, ub and uc. $site is the site that the point_for_site represents. z_matrix defines a point in space with coordinates given in Z-matrix format as follows:

E can be an equation, constant or a parameter name with a value.

atom_1 specifies the site that the new Z-matrix point represents.

The E after atom_2 specifies the distance in Å between atom_2 and atom_1. atom_2 must exist if atom_1 is preceded by at least one point.

The E after atom_3 specifies the angle in degrees between atom_3, atom_2 and atom_1. atom_3 must exist if atom_1 is preceded by at least two points.

The E atom_4 specifies the dihedral angle in degrees between the plane formed by atom_3-atom_2-atom_1 and the plane formed by atom_4-atom_3-atom_2. This angle is drawn using the righthand rule with the thumb pointing in the direction atom_3 to atom_2. atom_4 must exist if atom_1 is preceded by at least three sites of the rigid body.

If atom_1 is the first point of the rigid body then it is placed at Cartesian (0, 0, 0). If atom_1 is the second point of the rigid body then it is placed on the positive z-axis at Cartesian (0, 0, E) where E corresponds to the E in [atom_2 E]. If $atom_1 is the third point of the rigid-body then it is placed in the x-y plane.

rotate rotates point_for_site’s an amount as defined by the rotate E equation around the vector defined by the Cartesian vector qx, qy, qz. The vector can instead be defined in fractional coordinates using qa, qb and qc. translate performs a translation of point_for_site’s an amount in Cartesian coordinates equal to tx, ty, tz. The amount can instead be defined in fractional coordinates using ta, tb and tc. rotate and translate operates on any previously defined point_for_site’s; alternatively, point_for_site’s operated-on can be identified using operate_on_points. operate_on_points must refer to previously defined point_for_site’s (see section 20.26 for a description of how to identify sites). in_cartesian or in_FC can be used to signal coordinates are in Cartesian or fractional atomic coordinates respectively. When continue_after_convergence is defined, rand_xyz processes are initiated after convergence. It introduces a random displacement to the translate fractional coordinates (tx, ty, tz) that are independent parameters. The size of the random displacement is given by the current temperature multiplied by #displacement where #displacement is in Å. start_values_from_site initializes the values ta, tb, tc with corresponding values taken from the site named $unique_site_name.


## Fractional, Cartesian and Z-matrix coordinates

Rigid bodies can be formulated using fractional or Cartesian coordinates. A Benzene ring without Hydrogens can be formulated as follows:


| prm a 1.3 min 1.2 max 1.4 rigid    point_for_site C1 ux =  a Sqrt(3) .5; uy =  a .5;    point_for_site C2 ux =  a Sqrt(3) .5; uy = -a .5;    point_for_site C3 ux = -a Sqrt(3) .5; uy =  a .5;    point_for_site C4 ux = -a Sqrt(3) .5; uy = -a .5;    point_for_site C5 uy =  a;    point_for_site C6 uy = -a;    Rotate_about_axies(@ 0, @ 0, @ 0) ‘ rotate previously defined points    Translate(@ 0.1, @ 0.2, @ 0.3)    ‘ translate previously defined points |
| --- |

The last two statements rotate and translates the rigid body as a whole; their inclusion is implied if absent. A formulation of any complexity can be obtained from a) databases of existing structures using fractional or Cartesian coordinates of structure fragments or b) from sketch programs for drawing chemical structures. A Z-matrix representation of a rigid body explicitly defines the rigid body in terms of bond lengths and angles. A Benzene ring is typically formulated using two dummy atoms X1 and X2 as follows:


| str ... site X1 ... occ C 0 site X2 ... occ C 0 rigid load z_matrix { X1 X2   X1  1.0 C1   X2  1.3   X1  90 C2   X2  1.3   X1  90  C1  60 C3   X2  1.3   X1  90  C2  60 C4   X2  1.3   X1  90  C3  60 C5   X2  1.3   X1  90  C4  60 C6   X2  1.3   X1  90  C5  60  } |
| --- |


| rigid point_for_site X1 load z_matrix { X2   X1  1.0 C1   X2  1.3   X1  90 ... } |
| --- |

Z-matrix parameters are like any other parameter; they can be equations and parameter attributes can be assigned. For example, the 1.3 bond distance can be refined as follows:


| rigid point_for_site X1 load z_matrix { X2   X1  1.0 C1   X2  c1c2 1.3 min 1.2 max 1.4  X1  90 C2   X2  = c1c2;   X1  90  C1  60 C3   X2  = c1c2;   X1  90  C2  60 C4   X2  = c1c2;   X1  90  C3  60 C5   X2  = c1c2;   X1  90  C4  60 C6   X2  = c1c2;   X1  90  C5  60   } |
| --- |


## Translating part of a rigid body


| rigid    load z_matrix {       X1       X2   X1  1.0       C1   X2  1.3   X1  90       C2   X2  1.3   X1  90  C1  60       C3   X2  1.3   X1  90  C2  60       C4   X2  1.3   X1  90  C3  60       C5   X2  1.3   X1  90  C4  60       C6   X2  1.3   X1  90  C5  60    }    translate       tx @ 0 min -0.1 max 0.1       ty @ 0 min -0.1 max 0.1       tz @ 0 min -0.1 max 0.1       operate_on_points "C1 C2" |
| --- |

where the additional statements are in purple. The Cartesian coordinate representation allows an additional means of shifting the C1 and C2 atoms by refining on the ux, uy and uz coordinates directly, or,


| prm a 1.3 min 1.2 max 1.4 prm t1 0 min -0.1 max 0.1 prm t2 0 min -0.1 max 0.1 prm t3 0 min -0.1 max 0.1 rigid    point_for_site C1 ux = a Sqrt(3) 0.5 + t1; uy =  a 0.5 + t2; uz = t3;    point_for_site C2 ux = a Sqrt(3) 0.5 + t1; uy = -a 0.5 + t2; uz = t3;    point_for_site C3 ux =-a Sqrt(3) 0.5;      uy =  a 0.5;    point_for_site C4 ux =-a Sqrt(3) 0.5;      uy = -a 0.5;    point_for_site C5                          uy =  a;    point_for_site C6                          uy = -a; |
| --- |


## Rotating part of a rigid body around a point

Many situations require the rotation of part of a rigid body around a point. An octahedra (Fig. 13-1), for example, typically rotates around the central atom with three degrees of freedom. To implement such a rotation requires setting the origin at the central atom before rotation and then resetting the origin after rotation. This is achieved using the Translate_point_amount macro as follows:


| prm r 2 min 1.8 max 2.2 rigid point_for_site A0 point_for_site A1 ux =  r; point_for_site A2 ux = -r; point_for_site A3 uy =  r; point_for_site A4 uy = -r; point_for_site A5 uz =  r; point_for_site A6 uz = -r;  Translate_point_amount(A0, -) operate_on_points "A* !A0" rotate @ 0 qa 1 operate_on_points "A* !A0" rotate @ 0 qb 1 operate_on_points "A* !A0" rotate @ 0 qc 1 operate_on_points "A* !A0" Translate_point_amount(A0, +) operate_on_points "A* !A0" |
| --- |

The point_for_site keywords could just as well be z_matrix keywords with the appropriate Z-matrix parameters. The first Translate_point_amount statement translates the specified points (A1 to A6) an amount equivalent to the negative position of A0. This sets the origin for these points to A0. The second resets the origin back to A0. If the A0 atom happens to be at Cartesian (0, 0, 0) then there would be no need for the Translate_point_amount statements.


|  | Fig. 13-1  Model of an ideal octahedron. |
| --- | --- |

Further distortions are possible by refining on different bond-lengths between the central atom and selected outer atoms. For example, the following macro describes an orthorhombic bipyramid:


| macro Orthorhombic_Bipyramide(s0, s1, s2, s3, s4, s5, s6, r1, r2) {    point_for_site s0    point_for_site s1 ux   r1    point_for_site s2 ux  –r1    point_for_site s3 uy   r1    point_for_site s4 uy  –r1    point_for_site s5 uz   r2    point_for_site s6 uz  –r2 } |
| --- |

Note the two different lengths r1 and r2; with r1 = r2 this macro would describe a regular octahedron.


## Rotating part of a rigid body around a line

Instead of explicitly entering fractional or Cartesian coordinates, rigid bodies can be created using the rotate and translate keywords. For example, two connected Benzene rings, a schematic without Hydrogens is shown in Fig. , can be formulated as follows:


| prm r 1.3 min 1.2 max 1.4 rigid    point_for_site C1 ux = r;    load point_for_site ux rotate qz operate_on_points {       C2 =r; 60  1 C2       C3 =r; 120 1 C3       C4 =r; 180 1 C4       C5 =r; 240 1 C5       C6 =r; 300 1 C6    }    point_for_site C7 ux = r;    load point_for_site ux rotate qz operate_on_points {       C8  =r; 60  1 C8       C9  =r; 120 1 C9       C10 =r; 300 1 C10    }    translate tx = 1.5 r; ty = r Sin(60 Deg);       operate_on_points "C7 C8 C9 C10" |
| --- |

The points of the second ring can be rotated around the line connecting C1 to C2 with the following:


| Rotate_about_points(@ 50 min -60 max 60, C1, C2, "C7 C8 C9 C10") |
| --- |

The min/max statements limit the rotations to 30 degrees. C5 can be rotated around the line connecting C4 and C6 with the following:


| Rotate_about_points(@ 40 min -50 max 50, C4, C6, C5) |
| --- |

Similar Rotate_about_points statements for each atom would allow for distortions of the Benzene rings without changing bond distances.


|  | Fig. 13-2. Model of two connected Benzene rings |
| --- | --- |

Another means of generating Fig. 13-2 and the one that requires the least thought is by using the Duplicate_Point and Duplicate_rotate_z macros as follows:


| prm r 1.3 min 1.2 max 1.4 rigid point_for_site C1 ux = r; Duplicate_rotate_z(C2, C1, 60) Duplicate_rotate_z(C3, C2, 60) Duplicate_rotate_z(C4, C3, 60) Duplicate_rotate_z(C5, C4, 60) Duplicate_rotate_z(C6, C5, 60) Duplicate_Point(C7,  C3) Duplicate_Point(C8,  C4) Duplicate_Point(C9,  C5) Duplicate_Point(C10, C6) Rotate_about_points(180, C1, C2, "C7 C8 C9 C10") |
| --- |


### Using Z-matrix together with rotate and translate

Cyclopentadienyl (C5H5) is a well-defined molecular fragment which shows slight deviations from a perfect five-fold ring (Fig. ). The rigid body definition using point_for_site keywords is as follows:


| prm r1 1.19 prm r2 2.24 rigid load point_for_site ux { C1 =r1; C2 =r1; C3 =r1; C4 =r1; C5 =r1; } load point_for_site ux { H1 =r2; H2 =r2; H3 =r2; H4 =r2; H5 =r2; } load rotate qz operate_on_points { 72 1 C2  144 1 C3 216 1 C4 288 1 C5 } load rotate qz operate_on_points { 72 1 H2  144 1 H3 216 1 H4 288 1 H5 } |
| --- |

and using a typical Z-matrix representation:


| rigid load z_matrix { X1 X2   X1 1 C1   X2 1.19   X1  90 C2   X2 1.19   X1  90   C1  72 C3   X2 1.19   X1  90   C2  72 C4   X2 1.19   X1  90   C3  72 C5   X2 1.19   X1  90   C4  72 X3   C1 1      X2  90   X1   0 H1   C1 1.05   X3  90   X2 180 H2   C2 1.05   C1 126   X2 180 H3   C3 1.05   C2 126   X2 180 H4   C4 1.05   C3 126   X2 180 H5   C5 1.05   C4 126   X2 180 } |
| --- |

This Z-matrix representation is typically used for Cyclopentadienyl; it allows for various torsion angles but does not allow for all possibilities. For example, no adjustment of a single Z-matrix parameter allows for displacement of the C1 atom without changing the C1-C2 and C1-C3 bond distances. The desired result however is possible using the Rotate_about_points macro:


| Rotate_about_points(@ 0, C2, C3, "C1 H1") |
| --- |

Thus, the ability to include rotate and translate together with z_matrix gives great flexibility in defining rigid bodies.


|  | Fig. 13-3. Model of the idealized cyclopentadienyl anion (C5H5). |
| --- | --- |


## The simplest of rigid bodies

The simplest rigid body comprises an atom constrained to move within a sphere; for a radius of 1, this can be achieved as follows:


| rigid point_for_site Ca uz @ 0 min -1 max 1 rotate r1 10 qx 1 rotate r2 10 qx = Sin(Deg r1); qy = -Cos(Deg r1); |
| --- |


| In Z-matrix form: | rigid z_matrix A                             ‘ line 1 z_matrix B A 2                         ‘ line 2 rotate @ 20 qa 1                       ‘ line 3 rotate @ 20 qb 1                       ‘ line 4 translate ta @ 0.1 tb @ 0.2 tc @ 0.3   ‘ line 5 |
| --- | --- |


| In Cartesian form: | rigid point_for_site A                      ‘ line 1 point_for_site B uz 2                 ‘ line 2 rotate @ 20 qa 1                      ‘ line 3 rotate @ 20 qb 1                      ‘ line 4 translate ta @ 0.1 tb @ 0.2 tc @ 0.3  ‘ line 5 |
| --- | --- |


| Set_Length(A, B, 2, @, @, @, @ 30, @ 30) |
| --- |


| Set_Length(A, B, @ 2 min 1.9 max 2.1, @, @, @, @ 30, @ 30) |
| --- |

Note, this macro defines the distance between the two sites as a parameter that can be refined.


## Generation of rigid bodies

A rigid body is constructed by the sequential processing of z_matrix, point_for_site, rotate and translate operations. The body is then converted to fractional atomic coordinates and then the symmetry operations of the space group applied. The conversion of Z-matrix coordinates to Cartesian is as follows:

The first atom is paced at the origin.

The second atom, if defined, is placed on the positive z-axis.

The third atom, if defined, is placed in the x-z plane.

For Cartesian to fractional coordinates, in terms of the lattice vectors, we have:

x-axis in the same direction as the a lattice vector.

y-axis in the a-b plane.

z-axis in the direction defined by the cross product of a and b.

Rotation operations are not commutative; the rotation of point A about the vector B-C and then about D-E is not the same as the rotation of A about D-E and then about B-C. By default, rotate and translate operate on all previously defined point_for_site’s. Alternatively point_for_site’s can be explicitly defined using operate_on_points. operate_on_points must refer to previously defined point_for_site’s and it can refer to many sites at once by enclosing the site names in quotes and using the wild card character ‘*’ or the negation character ‘!’ (see section 20.26), for example:


| operate_on_points "Si* O* !O2" |
| --- |


## Rigid body parameter errors propagated to fractional coordinates

Errors for fractional coordinates for sites defined as part of a rigid body are propagated to the site fractional coordinates. The example rigid-errors\aniline_i_100k_x.inp (by Simon Parsons) demonstrates the equivalence of two refinements 1) using a rigid body, and 2) hand coding the fractional coordinates in terms of rigid body parameters but not in fact using a rigid body. Errors and convergence behaviour in both cases are identical. Case (2), which has many computer algebra equations, takes approximately the same time per iteration as case (1); this demonstrates that computer algebra often does not noticeably affect computational speed even in cases where its use is plentiful.


## Z-matrix collinear error information

The Z-matrix collinear points exception can be deciphered using information displayed on detection of the error. The collinear error is due to three atoms on a z-matrix line which are collinear. The information displayed includes a snapshot of the rigid body operations pertaining to the error. The following is an example of the information displayed:

DB_x_CB Zero dot product - Z-matrix possible collinear points at atoms

O10

C16 8.91631604e-016 1.0912987e-014 5.2

C15 3.72315026e-016 1.0912987e-014 3.9

C11 0 0 0

Partial z-matrix in error:

rigid

z_matrix C11

z_matrix C12 C11 1.3

z_matrix C13 C12 1.3 C11 120

z_matrix C14 C13 1.3 C12 120 C11 180

z_matrix C15 C14 1.3 C13 120 C11 0

z_matrix C16 C15 1.3 C14 120 C11 180

z_matrix O10 C16 1   C15 108 C11 120

The rigid body fragment can be copied to the Rigid-body editor to investigate why the error occurs, i.e.

The O10 line is commented out as it is the line causing the error. Looking at the O10 line (using the OpenGL window), we see that atoms C16, C15, C11 lie on a straight line; this is invalid as it becomes impossible to form a dihedral angle in a non-degenerate manner. The best way to think about a z-matrix line with 4 atoms A, B, C, D, i.e.


| z_matrix A B # C # D # |
| --- |


## Functions allowing access to rigid-body fractional coordinates


| rigid point_for_site O1  translate tx 1  point_for_site O2 ux = Point(O1, rx); ‘ Point here returns 1 translate tx 2  point_for_site O3 ux = Point(O1, rx); ‘ Point here returns 3 |
| --- |


| macro Point_ua(site_name) { Point_rx_to_ua(Point(site_name)) } macro Point_ub(site_name) { Point_ry_to_ub(Point(site_name)) } macro Point_uc(site_name) { Point_rz_to_uc(Point(site_name)) } |
| --- |

These macros can return many different values for the same point in question depending on when they are called during the rigid body calculation.


## Determining the orientation of a known fragment

test_examples\rigid\match.inp determines rotation and translation parameters for a known fragment. The known fragment is in fractional coordinates. To do the same for a fragment in Cartesian coordinates then change the lattice angles to 90 degrees and adjust the lattice parameter lengths. Also, see:

http://topas.dur.ac.uk/topaswiki/doku.php?id=rigid_body_-_matching_to_a_known_fragment


## TLS matrices — anisotropic thermal motion of a rigid body

Not documented in the TOPAS Technical Reference manual — sourced from Dinnebier, Leineweber & Evans (2018), §6.3.10, and Halasz & Dinnebier (2010), *Mat. Sci. Forum* 651, 65–69 (which gives the actual TOPAS macros for this, applied to crystalline naphthalene).

In most Rietveld refinements a single overall isotropic `beq` per rigid body is enough. For high-quality data, a rigid body's collective thermal motion can instead be described anisotropically using **TLS matrices** (Willis & Pryor, 1975; Downs, 1989) — far more economical than assigning independent anisotropic displacement parameters (`u11`...`u23`) to every atom in the body.

The physical picture: the displacement **u** of any point in a rigid body is split into a translational part **t** (the same everywhere in the body) and a librational part **λ**×**r** (a small rotation about an axis **λ** — direction = rotation axis, magnitude = angle of rotation — acting on the point's position vector **r** from some chosen origin):

```
u = t + λ × r
```

Averaging the outer product ⟨u⊗u⟩ over the thermal motion decomposes the body's overall displacement-tensor behavior into three matrices: **T** (translational), **L** (librational), and **S** (a screw/coupling term mixing translation and libration). These three matrices — not six independent `u_ij` per atom — are what gets refined; TOPAS itself has no dedicated `TLS` keyword, so this is implemented via user-written macros (see Halasz & Dinnebier 2010 for a working set) built on the same rigid-body/Z-matrix machinery documented elsewhere in this file, rather than a distinct language feature.

**Practical rules of thumb** for keeping a TLS refinement stable (from the book, based on experience refining real rigid bodies against powder data):

- If the rigid body's chosen origin coincides with its center of mass, the **S** matrix (the translation/libration coupling term) can usually be fixed to zero — this is the common case and removes the most failure-prone part of the model.
- Refining only the diagonal elements of **T** (constrained equal to each other) with **L** = **S** = 0 is equivalent to refining a single overall isotropic `beq` for the whole rigid body — i.e. this is the simplest non-trivial TLS model and a good starting point.
- Refining all independent elements of **T** alone (**L** = **S** = 0) is equivalent to refining a single overall anisotropic ADP for the whole rigid body.
- For flat/planar molecules (e.g. six-membered rings), it's often sufficient to refine the full **T** matrix plus only the diagonal elements of **L** — the off-diagonal librational terms rarely add real information for a planar fragment.
- If the rigid body sits on a crystallographic symmetry element, some matrix elements must be fixed to zero (or constrained to each other) according to that site symmetry, exactly as ordinary ADPs are constrained on special positions.

A real validation case (naphthalene, Halasz & Dinnebier 2010): TLS-derived ADPs from laboratory powder X-ray data, refined with the rigid-body origin at the center of mass and **S**=0, closely reproduced the ADP ellipsoids obtained independently from single-crystal neutron diffraction — evidence that a properly-constrained TLS model can recover genuine anisotropic thermal-motion information from powder data alone, not just an isotropic average. Automated tools exist to generate a TOPAS TLS description directly from a CIF (e.g. routines by Jacco van der Streek distributed via the TOPAS wiki), similar in spirit to how ISODISTORT generates symmetry-mode `.STR` files (see `references/25-symmetry-mode-refinement.md`).


## Rigid body macros

Set_Length(s0, s1, r, xc, yc, zc, cva, cvb)

Fixes the distance between two sites.

[s0, s1]: Site names.

[r]: Distance in Å.

[xc, yc, zc]: The parameter names for the coordinates of s0.

[cva, cvb]: Parameter names and values for rotations about the x and y axes

Set_Lengths(s0, s1, s2, r, xc, yc, zc, cva1, cvb1, cva2, cvb2)

Set_Lengths(s0, s1, s2, s3, r, xcv, ycv, zcv, cva1, cvb1, cva2, cvb2, cva3, cvb3)

Sets the distance between two and three sites, respectively. The two sites case is defined as:


| macro Set_Lengths(s0, s1, s2, r, xc, yc, zc,cva1, cvb1, cva2, cvb2) {    Set_Length(s0, s1, r, xc, yc, zc, cva1, cvb1)    Set_Length(s0, s2, r, xc, yc, zc, cva2, cvb2) } |
| --- |

Triangle(s1, s2, s3, r)

Triangle(s0, s1, s2, s3, r)

Triangle(s0, s1, s2, s3, r, xc, yc, zc, cva, cvb, cvc)

Defines a regular triangle without and with a central atom (s0).

[s0, s1, s2, s3]: Site names. s0 is the central atom of the triangle.

[r]: Distance in Å.

[xc, yc, zc]: Parameter names for the coordinates for the central atom.

[cva, cvb, cvc]: Parameter names and values for rotations about the x, y and z axes.

Tetrahedra(s0, s1, s2, s3, s4, r, xc, yc, zc, cva, cvb, cvc)

Defines a tetrahedra with a central atom.

[s0, s1, s2, s3, s4]: Site names. s0 is the central atom of the tetrahedra.

[r]: Distance in Å.

[xc, yc, zc]: Parameter names for the coordinates for the central atom.

[cva, cvb, cvc]: Parameter names and values for rotations about the x, y and z axes.

Octahedra(s0, s1, s2, s3, s4, s5, s6, r)

Octahedra(s0, s1, s2, s3, s4, s5, s6, r, xc, yc, zc, cva, cvb, cvc)

Defines an octahedra with a central atom.

[s0, s1, s2, s3, s4, s5, s6]: Site names. s0 is the central atom of the octahedra.

[r]: Distance in Å.

[xc, yc, zc]: Parameter names for the coordinates for the central atom.

[cva, cvb, cvc]: Parameter names and values for rotations about the x, y and z axes.

Hexagon_sitting_on_point_in_xy_plane(s1, s2, s3, s4, s5, s6, a)

Hexagon_sitting_on_side_in_xy_plane(s1, s2, s3, s4, s5, s6, a)

Defines a regular hexagon, where the hexagon is sitting on a point or on a side in the x-y plane, respectively.

[s1, s2, s3, s4, s5, s6]: Site names.

[a]: Distance in Å.

Translate(acv, bcv, ccv)

Translate(acv, bcv, ccv, ops)

Performs a translation of the rigid body.

[acv, bcv, ccv]: Amount of the translation in fractional coordinates.

[ops]: Operates on previously defined sites in “ops”.

Translate_with_site_start_values(s0, xc, yc, zc)

Performs a translation using the coordinates of s0 as start values.

[s0]: Site name.

[xc, yc, zc]: Parameter names for the coordinates of s0.

Rotate_about_points(cv, a, b)

Rotate_about_points(cv, a, b, pts)

Performs a rotation about a rotation vector specified by two sites.

[cv]: Amount the rigid body is rotated about the specified rotation vector in degrees.

[a, b]: Rotation vector defined by the sites a and b.

[pts]: Operates on previously defined point_for_site(s).

Note: Do not include points rotated about in the “operate on points” list of the Rotate_about_points macro. For example, in


| Rotate_about_points(@ 1 0, C1, C2, " C3 C4 C5 C6 ") |
| --- |

the points C1 and C2 are not included in the “points operated on” list. Note also that Rotate_about_points without a “points operated on” list will operate on all previously defined point_for_site(s). Therefore, when an “operate on points” list is not defined then it is necessary to place the “points rotated about” after the Rotate_about_points macro. It is best to specify an “operate on points” list when in doubt.

Rotate_about_these_points(cv, a, b, ops)

Performs a rotation about a rotation vector specified by two sites.

[cv]: Amount the rigid body is rotated about the specified rotation vector in degrees.

[a, b]: Rotation vector defined by the sites a and b.

[ops]: Operates on previously defined point_for_site(s).

Rotate_about_axies(cva, cvb)

Rotate_about_axies(cva, cvb, cvc)

Performs a rotation about the axes.
