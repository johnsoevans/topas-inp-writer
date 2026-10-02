# Electron Diffraction: dynamical refinement of 3D ED data

> **TOPAS-Academic Version 9 only.** Every keyword in the tree below was added
> in Version 9, apart from `f0_f1_f11_atom`, an older keyword whose meaning for
> electron data is new in Version 9. The first line of every run gives the version, for example
> `TOPAS-64 Version 9.3 (c) 1992-2026 Alan A. Coelho`. An earlier version does
> not know these keywords and refuses the INP file. Check the version before
> writing any of them, and ask the user when it is not known.

```
[ed_crystal $file]...                  ' one crystal: the data of one .cif_pets file
    [ed_g_max !E]                      ' default 1.9 Å⁻¹
    [ed_sg_max !E]                     ' default 0.05 Å⁻¹
    [ed_sg_bethe !E]                   ' Bethe potentials; default 0.008 Å⁻¹ for frames > 80 beams, else 0
    [ed_rsg_max !E]                    ' default 0.75
    [ed_dsg_min !E]                    ' default 0.0015 Å⁻¹
    [ed_num_integration_steps !E]      ' fixes the number of steps; without it the number is found
    [ed_num_integration_steps_auto #]  ' the number of steps found, returned to the .out file
    [ed_integration_tolerance !E]      ' default 0.2
    [ed_num_precession_steps !E]       ' default 24
    [ed_max_beams !E]                  ' default 400
    [ed_orient_search !E]              ' search range in degrees; default 0, no search
    [ed_invert_hand !E]                ' 1 fits the inverted structure; default 0
    [ed_abs_symmetric !E]              ' 0 always uses the general solver; default 1
    [r_f #]
    [xdd_ed $file]...                  ' one virtual frame; xdd_ed = Get(ed_file); takes the file of its ed_crystal
        [ed_frame_number !E]           ' the frame in the file; required
        [ed_alpha !E]                  ' goniometer angle of the frame; not used in the calculation
        [ed_thickness E]               ' crystal thickness in Å; default 500
        [ed_absorption E]              ' absorptive potential as a fraction of the potential; default 0
        [ed_frame_rotate_x E]          ' orientation correction in degrees; default 0
        [ed_frame_rotate_y E]          ' orientation correction in degrees; default 0
        [ed_data]                      ' electron scattering factors; implied by xdd_ed
[f0_f1_f11_atom $atom]...              ' older keyword; for electron data, in the shared str_dets: f1 is the charge q, f11 the absorption fraction
[#inp_from_cif_pets $file]             ' writes an ed_crystal and one xdd_ed for every frame
' Reserved for equations
    ed_num_beams                       ' the number of beams in a frame, for ed_sg_bethe equations
```

## What it does

In three dimensional electron diffraction (3D ED) the crystal is rotated in
the electron beam and diffraction images, called frames, are recorded while it
turns. With continuous rotation, PETS2 combines consecutive frames into virtual
frames. Electrons scatter strongly and many times within the crystal, and a
measured intensity depends on other reflections, the thickness and the frame
orientation. The kinematical approximation, intensity proportional to |F|², is
poor.

Each frame is refined separately with the Bloch wave form of the dynamical
theory, following Palatinus, Petříček & Antunes Corrêa (2015) and Klar et al.
(2023). One data set is an `ed_crystal`, and each of its virtual frames an
`xdd_ed`. Every frame uses one shared `str_dets` and one shared `lat_prms`,
the arrangement used for XRD-CT refinements:

```
str_dets s1 { space_group ... site ... }
lat_prms l1 { a 5.4 b 5.4 c 5.4 ... }
ed_crystal ...
   xdd_ed ... use { s1 l1 }
   xdd_ed ... use { s1 l1 }
   ...
```

Within the shared `str_dets`, `rigid`, `occ_merge`, penalties and restraints
all work in the usual way.

## Setting up the INP file

The data come from PETS2, which writes one `.cif_pets` file per crystal: the
cell, the wavelength, the orientation matrix UB, the zone axis and angles of
each frame, and the reflections, each tagged with its frame number.
`#inp_from_cif_pets` reads that file and writes the `ed_crystal` and one
`xdd_ed` per frame into the INP file. A complete file, the quartz example:

```
iters 10

str_dets ed_str_dets {
   space_group P3221
   site Si1 x 1.000000 y 0.470511 z = 5/6; occ Si 1 ADPs { 0.005939 0.006824 0.002087 0.002969 0.001812 0.000906 }
   site O1  x 0.852633 y 0.586703 z 0.619428 occ O 1 ADPs { 0.004981 0.016649 0.013874 0.005758 -0.002919 0.003662 }
}
lat_prms ed_lat_prms { a 4.9226 b 4.9226 c 5.4003 al 90 be 90 ga 120 }

#inp_from_cif_pets "../quartz_dyn/200603-02-iEDT-1.00_dyn_s1m2.cif_pets"
ed_g_max 2
ed_sg_max 0.01
ed_rsg_max 0.85
ed_dsg_min 0.0014
```

Rules for that layout:

- The generated frames use a `str_dets` named `ed_str_dets` and a `lat_prms`
  named `ed_lat_prms`. Both must be defined in the INP file.
- Settings written after `#inp_from_cif_pets` apply to the crystal it creates.
- Write recurring fractions of special positions in equation form (`z = 5/6;`).
  A value like 0.833333 misses the special position and the site counts twice.
- A frame with no reflections in the file is not written.

For this file `#inp_from_cif_pets` writes a thickness parameter and an
absorption parameter named after the file, the `ed_crystal` line, and then one
`xdd_ed` per frame:

```
prm ed_t_200603_02_iEDT_1_00_dyn_s1m2 500 min 20 max 5000
prm !ed_a_200603_02_iEDT_1_00_dyn_s1m2 0 min 0 max 1
ed_crystal "../quartz_dyn/200603-02-iEDT-1.00_dyn_s1m2.cif_pets"
xdd_ed = Get(ed_file);
   lam la 1 lo 0.0251
   ed_frame_number 1
   ed_alpha -49.197
   ed_thickness = ed_t_200603_02_iEDT_1_00_dyn_s1m2;
   ed_absorption = ed_a_200603_02_iEDT_1_00_dyn_s1m2;
   ed_frame_rotate_x 0
   ed_frame_rotate_y 0
   str use { ed_str_dets ed_lat_prms }
      scale @ 1
' and the same for every other frame
```

After a run the `.out` file holds the expanded form: the directive turns into a
comment, followed by the parameters, the `ed_crystal` and every `xdd_ed`. That
form can be edited by hand, for example to leave frames out (`gly-dyn-1.inp` is
`gly-dyn-0.inp` expanded without frames 75 and 76). Each `xdd_ed` needs its `lam` with the electron wavelength, its
`ed_frame_number` and exactly one `str`. `xdd_ed = Get(ed_file);` takes the
file of its `ed_crystal`; a file name in quotes works too.

Start with `iters 0` to check the frames, the beams and the first Rwp.

## The settings

| keyword | default | meaning |
|---|---|---|
| `ed_g_max` | 1.9 Å⁻¹ | largest \|g\| of a beam or a fitted reflection; structure factors are calculated to 2.1 `ed_g_max` |
| `ed_sg_max` | 0.05 Å⁻¹ | a reflection is a beam when its excitation error is within ±`ed_sg_max` at some integration step, or it crosses the Ewald sphere within the frame |
| `ed_rsg_max` | 0.75 | largest allowed RSg = \|Sg\| / (DSg + \|Sg\|) |
| `ed_dsg_min` | 0.0015 Å⁻¹ | smallest allowed DSg, the distance of the reflection from the Ewald sphere at the nearer end of the frame |
| `ed_num_integration_steps` | found | fixes the number of integration steps; without it the number is found (see "Integration over a virtual frame") |
| `ed_num_integration_steps_auto` | | returns the number of steps found to the `.out` file; the value written after it is not used |
| `ed_integration_tolerance` | 0.2 | the integration tolerance, in units of σ(I) |
| `ed_num_precession_steps` | 24 | azimuths around the precession cone, for precession data |
| `ed_max_beams` | 400 | most beams per frame |
| `ed_sg_bethe` | see below | beams further than this from the Ewald sphere are weak and enter through Bethe potentials |
| `ed_orient_search` | 0 | range in degrees of a search for each frame's orientation |
| `ed_invert_hand` | 0 | 1 fits the inverted structure; see "The absolute structure" |
| `ed_abs_symmetric` | 1 | 0 always uses the general eigen solver with absorption |

`ed_g_max`, `ed_sg_max`, `ed_dsg_min` and `ed_rsg_max` take
the same meaning they have in Jana2020, and the examples use the Jana2020
values of each data set.

## Beams and reflections, and what the console shows

For each frame, the beams of the calculation and the measured reflections to fit are chosen. A measured reflection is fitted when |g| ≤ `ed_g_max` and it
passes the DSg and RSg tests; in a still frame, with no angular range and no
precession, when its excitation error at the frame centre is within ±`ed_sg_max`. A frame holds at most `ed_max_beams` beams: the
incident beam, every fitted reflection, and the reflections nearest the Ewald
sphere among the rest. The beams are chosen before refinement and stay fixed,
which keeps the calculated intensities smooth while the frame rotations
refine. Negative measured intensities are set to zero.

The load prints one line per frame:

```
ED: 17557 hkls in half of reciprocal space to |g| 4.2 for the structure factors
ED frame 1: 21 of 73 reflections (dropped: |g| > ed_g_max 0, D_Sg 49, S_g 0, R_Sg 3, |g| > 2.1 ed_g_max 0), 68 beams, 340 structure factors
   negative intensities set to zero: 4
...
ED crystal 1: ed_num_integration_steps_auto 28
```

21 of the frame's 73 reflections are fitted. The counts in brackets are the
reflections removed by each test: beyond `ed_g_max`, DSg below `ed_dsg_min`,
excitation error beyond `ed_sg_max` (still frames only), RSg above
`ed_rsg_max`, and beyond the structure factor range. Then the beams and the
structure factors used; the number of integration steps is added when
`ed_num_integration_steps` fixes it. Once for each crystal, before the first
calculation, a line gives the number of integration steps found.

When the incident beam and the fitted reflections alone exceed
`ed_max_beams`, all are kept and a warning is printed:
`measured reflections exceed ed_max_beams; all are kept as beams`. A frame
left with no reflections after the filters is removed, unless its `xdd` holds a
`prm`, `local` or penalty, in which case the run stops and asks for the frame to be removed from the INP file.

## Bethe potentials

At each integration step a beam is strong when it is the incident beam, a
fitted reflection, or within ±`ed_sg_bethe` of the Ewald sphere. The other
beams are weak and enter the strong beams' calculation through Bethe potentials.
Only the strong beams are diagonalised; a large `ed_sg_max` then adds little
cost. `ed_sg_bethe 0` makes every beam strong and the calculation exact.

`ed_sg_bethe` may be an equation of `ed_num_beams`, evaluated for each frame at
the start. The default is

```
ed_sg_bethe = If(Get(ed_num_beams) > 80, 0.008, 0);
```

which uses Bethe potentials for frames with more than 80 beams and calculates
smaller frames exactly. The console reports it per frame, here for glycine
(`gly-dyn-0.inp`):

```
ED frame 1: ed_sg_bethe 0.008 from its equation, 148 beams, Bethe: 67 strong a step
```

On glycine, 74 frames at `ed_sg_max 0.05`, refinement took 652 s without Bethe
potentials and 19.6 s with `ed_sg_bethe 0.008`, with a negligible change in Rwp
and coordinates within 10⁻⁵.

## Integration over a virtual frame

A virtual frame divides an angular range into Ns equal parts and calculates
the intensity at the centre of each part. For continuous rotation data PETS2
writes the half width of each virtual frame in the precession angle column.

By default Ns is found for each crystal before the first calculation. Starting
from 15, each frame is calculated with Ns and 2Ns steps, and Ns is the smallest
number, to within a tenth, for which the rms change in the calculated intensities, in units of
σ(I), is below `ed_integration_tolerance` (0.2 by default). Every frame of the
crystal uses the largest Ns found among its frames. The number is printed, and
written to the `.out` file when `ed_num_integration_steps_auto` is given; the
value written after it is not used. `ed_num_integration_steps` fixes Ns
instead, and only one of the two can be given. The number found grows with the
thickness: 22 for glycine at 402 Å and 28 at 500 Å; 35, 22 and 18 for the three
albite crystals.

For precession data the average is taken over `ed_num_precession_steps`
azimuths around the precession cone.

## Thickness, scale and absorption

**Thickness.** `ed_thickness` is per frame, and `#inp_from_cif_pets` ties every
frame of a crystal to one refinable parameter. When the starting Rwp is poor,
refine the frame scales at a series of fixed thicknesses, every 100 Å for
example, then refine `ed_thickness` from the best of them.

**Scale.** A calculated intensity is a fraction of the incident beam, orders
of magnitude below the measured counts. At the first calculation each frame's
intensities are multiplied by a factor that brings its refined scale near one;
the factor then stays fixed. Each frame has its own `scale`.

**Absorption.** `ed_absorption` κ, per frame and refinable, sets the absorptive
potential to κ times the potential: every Ug becomes (1 + iκ) Ug. It takes two
to three times longer to calculate. On quartz κ refined from zero to 0.087 and
Rwp went from 13.17 to 13.01; absorption matters for heavy atoms in thick
crystals. `ed_abs_symmetric 0` forces the general solver for absorbing frames.

## Scattering factors, ions and partial charges

`ed_data` selects electron scattering factors, the way `neutron_data` selects
neutron scattering lengths, and `xdd_ed` implies it. They are read from
`edscat.txt` (International Tables Vol. C, Table 4.3.2.2). An ion named with
the sign first, `O-2` or `Si+4`, takes its electron scattering factor from the
Mott formula on the X-ray factors of the ion and the atom; the charge dominates
at small sin θ/λ. The degree of ionisation can be refined by splitting the
occupancy:

```
prm qf 0.1 min -0.5 max 1.5
site Si1 x 1.000000 y 0.470511 z = 5/6;
   occ Si   = 1 - qf; ADPs { 0.005939 0.006824 0.002087 0.002969 0.001812 0.000906 }
   occ Si+4 = qf;     ADPs { 0.005939 0.006824 0.002087 0.002969 0.001812 0.000906 }
' and the same for O1, with O and O-2
```

**`f0_f1_f11_atom`**, written inside the shared `str_dets`, sets three things
for one atom type in electron data:

| | meaning |
|---|---|
| `f0` | replaces the electron scattering factor fe |
| `f1` | q, the partial charge of the atom type in units of the electron charge; a positive q removes electrons. fe becomes fe + qΔ(s), with Δ(s) the change in fe per unit charge from the ion scattering factors |
| `f11` | κt, the absorption of the atom type, a fraction of its scattering factor (f′ = κt fe) |

q and κt can be refined. κt equal to κ for every atom type with
`ed_absorption 0` reproduces `ed_absorption κ`.

- Use the neutral atom name with `f1`: `O`, not `O-2`.
- `f1` cannot be used for C, N, P, S, B and Se, which have no ion in `atmscat.txt`.
- One `f0_f1_f11_atom` per atom type.
- `f11` cannot be used with layers, modulation, magnetism, protein sites or
  `scale_occ`, and a `str_dets` with `f11` cannot also be used by X-ray or
  neutron data.
- Refined independently, charges drift apart (on quartz q reached +0.66 for Si
  and −1.89 for O). Keep the cell neutral: write each charge with an equation
  of one refined parameter:

```
prm q_Si 0.4 min -2 max 4
str_dets ed_str_dets {
   space_group P3221
   f0_f1_f11_atom Si f1 = q_Si;      f11 @ 0.1
   f0_f1_f11_atom O  f1 = -q_Si / 2; f11 @ 0.1
   site Si1 x 1.000000 y 0.470511 z = 5/6; occ Si 1
      ADPs { 0.005939 0.006824 0.002087 0.002969 0.001812 0.000906 }
   site O1  x 0.852633 y 0.586703 z 0.619428 occ O 1
      ADPs { 0.004981 0.016649 0.013874 0.005758 -0.002919 0.003662 }
}
```

On 20 frames of quartz, neutral atoms gave Rwp 15.373, formal charges +4 and −2
gave 16.584, and a refined q for Si of 0.43 gave 15.347.

## Frame orientations

The frame orientations from PETS2 are often out by 0.1 to 0.25°.
`ed_frame_rotate_x` rotates the crystal about the goniometer axis, and
`ed_frame_rotate_y` about the axis perpendicular to the beam and the goniometer
axis; both are in degrees and refinable per frame. Rotation about the beam
does not change the intensities.

Least squares refinement of the rotations is slow, because reflections enter
and leave the frame. `ed_orient_search R` instead searches each frame's
orientation, first on a coarse grid over ±R degrees, then more finely around
the best points; the result can move up to 1.25 R. Each trial is scored by the
frame's weighted sum of squares with its scale fitted, and the beams are chosen
again for the orientation found. A rotation given by an equation is not
searched; one that is not refined keeps the value found, and the `.out` file
records it. On glycine at 42 steps, least squares took Rwp from 16.09 to 14.85
in twelve cycles, while `ed_orient_search 0.4` reached 12.18 in 20 s.

## Several crystals, and other data

Write one `#inp_from_cif_pets` per crystal. Crystals that share a `str_dets`
must share one `lat_prms` and have the same wavelength and the same `ed_g_max`.

X-ray or neutron data, powder or single crystal, can be refined together with
the crystals, but they need a `str` of their own: a `str_dets` used by
electron diffraction frames cannot also be used by other `str`s. Tie the two
structures together through named parameters.

## What can be refined

Structural parameters, two rotations per frame, a scale per frame, thickness
and absorption, and the charge and absorption of each atom type. Lattice
parameters are not refined. `bkg` and `fit_obj` work on frames. A structure can
be written in a `str`, or in a named `str_dets` for shared use; `rigid`,
`occ_merge`, `scale_pks` and penalties work in the usual way, with two limits:
`scale_pks` cannot use the intensity of a frame, and a `scale_occ` that changes
from reflection to reflection cannot be used.

The derivatives are analytical and exact for centrosymmetric and acentric
structures. In an acentric structure that uses layers, magnetism, modulation
or `scale_occ` they are approximate, a warning is printed, and coordinates may converge
more slowly.

## R(F)

`r_f`, written after an `ed_crystal`, returns the R(F) of that crystal to the
`.out` file: 100 Σ|√Io − √Ic| / Σ√Io, summed over the reflections of its
frames. Rwp measures the fit, the same way it does for any other data.

## The absolute structure: `ed_invert_hand`

Dynamical intensities depend on the hand of an acentric structure. A structure
and its inverse give different intensities, whereas their kinematical
intensities are identical. Electron diffraction data can therefore decide the
absolute structure.

`ed_invert_hand 1` calculates the intensities of the inverted structure by
using F*, the complex conjugate of the structure factor, in place of F. The
coordinates, the displacement parameters and every other parameter stay the
way they are written, in the INP file and in the `.out` file, while the frames
are fitted by the inverse of that structure. To obtain the structure actually
fitted, invert the coordinates: x, y, z become −x, −y, −z. In an enantiomorphic
pair of space groups, for example P3₁21 and P3₂21, the space group also
changes to its partner.

`ed_invert_hand` is a setting of an `ed_crystal` and applies to every frame of
that crystal; with several crystals it is given to each. It changes nothing
for a centrosymmetric structure, whose inverse is the same structure. It
applies only to electron diffraction frames: X-ray or neutron data refined
together with them are calculated from the structure written.

The absolute structure is found by refining both hands. Refine the structure
to convergence, then refine it again with `ed_invert_hand 1` written after the
settings of each crystal:

```
#inp_from_cif_pets "../quartz_dyn/200603-02-iEDT-1.00_dyn_s1m2.cif_pets"
ed_g_max 2
ed_invert_hand 1      ' the other hand
```

Each hand is refined fully, including the structure, the scales and the
thickness, and the hand with the lower Rwp is the absolute structure. This is
done once, at the end of the refinement. For quartz, `qtz-dyn-0.inp` gives an
Rwp of 13.17 with the coordinates of O1 refined for the published hand, and
15.57 with `ed_invert_hand 1`.

Flack is not used with `xdd_ed`; comparing the two hands replaces it.

## Refinement strategy

1. `iters 0` to check the frames, the beams and the first Rwp.
2. When the starting Rwp is poor, refine the frame scales at a series of fixed
   thicknesses, then refine `ed_thickness` from the best.
3. Correct the frame orientations with `ed_orient_search 0.4` to `0.5`; refine
   `ed_frame_rotate_x` and `ed_frame_rotate_y` afterwards.
4. Refine the structure.
5. For an acentric crystal, refine each hand, the second with
   `ed_invert_hand 1`, and keep the hand with the lower Rwp.

## Messages a user will meet

| message (printed text, or its start) | cause |
|---|---|
| `xdd_ed: a lam with the electron wavelength is needed` | an `xdd_ed` without `lam` |
| `xdd_ed: an electron diffraction frame must have exactly one str` | |
| `xdd_ed: frames that share a str_dets must share one lattice (use one lat_prms)` | crystals with different `lat_prms` on one `str_dets` |
| `xdd_ed: frames that share a str_dets must use the same wavelength` | |
| `xdd_ed: frames that share a str_dets must use the same ed_g_max` | |
| `xdd_ed: a str_dets used by electron diffraction frames cannot also be used by other strs` | an X-ray or neutron `str` using the ED `str_dets`; give it its own |
| `xdd_ed: a str_dets with f11 used by electron diffraction frames cannot also be used by other strs` | the same, with `f11` |
| `xdd_ed: f11 (the absorptive form factor) cannot be used with ...` | layers, modulation, magnetism, protein sites or `scale_occ` |
| `xdd_ed: no frame has reflections left after the excitation error filters` | the settings remove everything; loosen `ed_dsg_min` or `ed_rsg_max` |
| `... so it cannot be removed; remove the frame from the INP ...` | an emptied frame whose `xdd` holds a `prm`, `local` or penalty |
| `measured reflections exceed ed_max_beams; all are kept as beams` | warning; raise `ed_max_beams` or lower `ed_g_max` |
| `xdd_ed: the eigen-decomposition did not converge for frame ...` | |
| `xdd_ed: scale_pks cannot use the intensity of an electron diffraction frame` | |
| `scale_occ that varies from reflection to reflection cannot be used with single crystal or ED data` | |
| `scale_occ cannot be used on an atom whose f0, f1 or f11 is refined` | |
| `xdd_ed: Flack is not used with dynamical electron diffraction` | |
| `Cannot have multiple f0_f1_f11_atom for atom ...` | |
| `f1 (the partial charge for electrons) needs a neutral atom name, not ...` | `f1` on an ion name |
| `f1 (the partial charge for electrons): atmscat.txt has no ion of ...` | `f1` on C, N, P, S, B or Se |
| `cif_pets: a .cif_pets file is read by its name` | |
| `ed_num_integration_steps and ed_num_integration_steps_auto cannot both be used` | only one of the two in a crystal |
| `ed_integration_tolerance must be positive` | |
| `xdd_ed: frame ... is not in ...` | `ed_frame_number` missing (it then reads 0) or not a frame of the file |
| `unknown or misplaced keyword` at an `ed_sg_max_refine` line | the keyword no longer exists; delete the line |
| `cif_pets: no _refln loop in ...`, `cif_pets: no _diffrn_radiation_wavelength in ...` | an incomplete `.cif_pets` file |
| `... the structural derivatives are approximate, and coordinates may converge slowly.` | acentric structure with layers, magnetism, modulation or `scale_occ` |

## Worked examples (`test_examples\ed` of a Version 9 installation)

| file | shows |
|---|---|
| `quartz\topas\qtz-dyn-0.inp` | quartz, acentric: thickness and frame scales refined on 99 frames; Rwp 13.3 at 477 Å |
| `glycine\topas\gly-dyn-0.inp` | glycine: the first calculation with `iters 0`; Rwp 15.96 on 75 frames |
| `glycine\topas\gly-dyn-1.inp` | the same expanded without frames 75 and 76, the 74 frames Jana2020 uses; Rwp 16.08 at 402 Å |
| `test-0.inp` | a synthetic test of the refinement of frame orientations: 20 quartz frames whose intensities were calculated with the model at 500 Å, 300 integration steps and every rotation at zero; the rotations are refined from starting offsets of up to ±0.25° |

Refined further, glycine reached Rwp 13.0 at 429 Å, with the largest atomic
shift from the Jana2020 model 0.013 Å. Three albite crystals refined together
(152 frames, `ed_orient_search 0.5`, `ed_sg_max 0.02`, `ed_sg_bethe 0.005`,
35, 22 and 18 integration steps found) gave an `r_f` of 16.3 over all
reflections, against 15.9 from Jana2020.

The data and the Jana2020 refinements are those of Klar et al. (2021), Zenodo,
doi 10.5281/zenodo.7185657, published under CC BY 4.0. The `.cif_pets` files
are not part of the TOPAS installation; download them from that deposit.

## Limitations

- An absorptive form factor f′ calculated from each atom's displacement
  parameters is not implemented. `ed_absorption` sets f′ = κ fe for every atom
  and `f11` sets f′ = κt fe per atom type. (In electron diffraction f′ is the
  imaginary part of the scattering factor from thermal diffuse scattering, not
  the anomalous dispersion f′ of X-rays.)
- Flack cannot be used; compare the two hands instead.
- Lattice parameters are not refined against frames.

## References

- Palatinus, L., Petříček, V. & Antunes Corrêa, C. (2015). Acta Cryst. A71, 235-244.
- Klar, P. B., Krysiak, Y., Xu, H., Steciuk, G., Cho, J., Zou, X. & Palatinus, L. (2023). Nature Chemistry 15, 848-855.
- Klar, P. B., Krysiak, Y., Xu, H., Steciuk, G., Cho, J., Zou, X. & Palatinus, L. (2021). Raw data and JANA refinement files. Zenodo, doi 10.5281/zenodo.7185657.
- Palatinus, L., Brázda, P., Jelínek, M., Hrdá, J., Steciuk, G. & Klementová, M. (2019). Acta Cryst. B75, 512-522 (PETS2).
- Bethe, H. (1928). Annalen der Physik 392, 55-129.
- Colmey, B., Doherty, T. A. S., Malik, S. A. & Midgley, P. A. (2026). The role of absorption in three-dimensional electron diffraction dynamical structure refinement. arXiv:2602.08935.
- International Tables for Crystallography Vol. C, section 4.3.
