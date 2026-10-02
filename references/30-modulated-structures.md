# Modulated Structures

> **TOPAS-Academic Version 9 only.** Every keyword and macro in this chapter
> was added in Version 9. The first line of every run gives the version, for
> example `TOPAS-64 Version 9.3 (c) 1992-2026 Alan A. Coelho`. An earlier
> version does not know these keywords and refuses the INP file.
> Check the version before writing any of them, and ask the user when it is
> not known.

```
[str]...
    [apply_rotation_matrix # # # # # # # # #]      ' not specific to modulation
    [p1_hkls]                                      ' not specific to modulation
    [mod_d_tolerance !E]
    [mod_qm $name]...
        [mod_qx E] [mod_qy E] [mod_qz E]
        [mod_m #]
        [mod_user_operators $operators]
        [mod_tau_from_cif $file]
        [mod_tau_symbol $symbol]                   ' synonym: space_group_ssg_name_IT
        [mod_tau_build_all]
        [mod_tau !E]...
        [mod_t0 E]
        [load_q_vector_type $type]
    [site $name]...
        [mod_x !E E E [qm !E]]...  [mod_y !E E E [qm !E]]...  [mod_z !E E E [qm !E]]...
        [mod_occ !E E E [qm !E]]...
        [mod_beq !E E E [qm !E]]...
        [mod_u11 !E E E [qm !E]]...  to  [mod_u23 !E E E [qm !E]]...
        [mod_mlx !E E E [qm !E]]...  [mod_mly !E E E [qm !E]]...  [mod_mlz !E E E [qm !E]]...
        [mod_crenel_width E [qm !E]]...
            [mod_crenel_center E]
            [mod_saw_x E] [mod_saw_y E] [mod_saw_z E]
            [mod_legendre_x !E E]...  [mod_legendre_y !E E]...  [mod_legendre_z !E E]...
    [move_to_site $site]
' On a modulation keyword, in place of its amplitudes:
    add_constraints
' Macros (topas.inc)
    Get_site(m, s)            copies site s from the str in the scope of prm m
    Get_sites(m)              copies every site from the str in the scope of prm m
    Get_modulated_sites(m)    copies the modulated sites from the str in the scope of prm m
    Get_mod_s(x), Get_mod_c(x)
    Out_CIF_STR(file), Out_msCIF(file)
' Equation functions
    Get_mod(mod_keyword)      within a modulation equation
    Get(mod_qms)              in an out record: the satellite orders of the current reflection
```

## What a modulated refinement is

A modulated structure is not periodic on its basic cell. Its departure from
the basic structure is a periodic function of position with its own period,
usually incommensurate with the cell. Reflections are indexed on the basic
cell plus integer multiples of one or more modulation wave vectors **q**:

```
Q = H + sum over a of  m_a q_a        H = h a* + k b* + l c*
```

Reflections with every `m_a = 0` are the main reflections; the others are
satellites, and `m` is the satellite order. Commensurate and incommensurate
modulations are written the same way; rational components of **q** simply
repeat after a whole number of cells.

Modulated structures work with rigid bodies, `occ_merge`, twins, magnetic
moments, powder data (X-ray and neutron, constant wavelength and time of
flight) and single crystal data. They cannot be combined with stacking faults
or with PDF data; both are refused.

## Declaring the modulation wave vector

With one modulation vector, write its components and the satellite order
directly under `str`:

```
str
   space_group P21
   a 6.425  b 6.522  c 22.716  al 90  be 90.739  ga 90
   mod_qx 0.14216  mod_qy 0  mod_qz 0.38390
   mod_m 1
   site ...
```

| keyword | meaning |
|---|---|
| `mod_qx` `mod_qy` `mod_qz` | components of **q** in reciprocal lattice units |
| `mod_m` | the satellite order this `str` generates |
| `mod_qm $name` | starts one modulation vector; needed only when there are several |
| `mod_d_tolerance` | d spacing tolerance for deciding when two generated satellites are one reflection |
| `load_q_vector_type $type` | which order column of a single crystal reflection file belongs to this vector |

With several vectors, give each its own `mod_qm` block and tell each site
keyword which vector it belongs to with a trailing `qm`:

```
   mod_qm 0 mod_m 1 mod_qx @ 0.21
   mod_qm 1 mod_m 1 mod_qy @ 0.14
   mod_qm 2 mod_m 1 mod_qz @ 0.11
   site Ce1 x 0.1234 y 0 z 0 occ Ce+3 1 beq 0.2
      mod_x   1 @ 0.1 0.2 qm 1
      mod_occ 1 @ 0.1 0.1 qm 1
```

Without `mod_qm` the vector takes the identifier 0, and `qm` on a site keyword
defaults to 0. `mod_qm` names must be unique within a `str`, and the short
form cannot be followed by `mod_qm` blocks in the same `str`. A `mod_qm` with
`mod_m 0` and no amplitude on any site contributes nothing, and a warning is printed.

## One str per satellite order

A `str` generates the reflections of one order. A pattern with main
reflections and satellites therefore needs several: one with `mod_m 0`, one
with `mod_m 1` for the first order satellites, and one more for each higher
order, with their sites tied together. Each `str` has its own peak shapes; the angle dependence of
peak shapes and intensities is applied automatically.

Satellites are generated for h ≥ 0. The Friedel partner of a satellite at
`Q = H + m q` is `-Q`, which is `-H` at order `-m`; a `str` with `mod_m n`
generates both `+n` and `-n`. Main reflections carry the usual multiplicity.

**Powder data.** One `str` per order `m`, all under the same `xdd`.

**Single crystal data.** One `xdd_scr` per order `|m|`, from 0 up to the
highest order present, each with its own `str`. A satellite and its Friedel
partner are one reflection and are always merged. Only the positive orders are
declared, and `dont_merge_Friedel_pairs` cannot be used. A modulated and an
unmodulated `str` cannot share one single crystal `xdd`. An order with no
reflections in the file stops the run with `No hkls for <file>`.

### Writing the structure once

The structure is written once and every other `str` points at it. Two
templates, for `m = 0, 1, 2`:

```
xdd ...
   str mod_m !m0_global 0 local !m0_local 0
      site S1 ...                  ' unmodulated
      site S2 ... mod_x ...        ' modulated
      site S3 ... mod_x ...        ' modulated
   str mod_m 1 ...
   str mod_m 2 ...
   for strs { ...
      if Prm_There(m0_local) == 0 {
         Get_modulated_sites(m0_global)
      }
   }
```

```
xdd ...
   str mod_m $m0 0 ...             ' m0 has local scope
   str mod_m m1 1 ...
   str mod_m m2 2 ...
   for strs { ...
      if Prm_There(m0) {
         site S1 ...               ' unmodulated sites only in m = 0
      }
      site S2 ... mod_x ...
      site S3 ... mod_x ...
   }
```

In the first, every site is defined in the `m = 0` str, and
`Get_modulated_sites` builds the modulated sites of the other strs with every
parameter pointing at the `m = 0` one. The `@` character can be used there,
because each parameter exists once. In the second, the sites are written in
the `for` loop.

**Inside `for strs { }` and `for xdds { }`, name every refined parameter.**
The loop copies its text into every `str`, and a bare `@` declares a new
anonymous parameter in each copy. Three orders then refine three independent
copies of what is meant to be one amplitude, and the refinement becomes
nearly singular. `Num independent parameters` in the console being a multiple
of what was expected is the sign. Write a name (`mod_x 1 mx1 0.01 mx2 0.01`) or
declare a `prm` outside the loop and use `= name;` inside it.

At the top level, with one `xdd_scr` per order, put `for strs` inside
`for xdds`:

```
xdd_scr data.hkl  str phase_name m0  mod_m 0  local !m0 0
xdd_scr data.hkl  str phase_name m1  mod_m 1
xdd_scr data.hkl  str phase_name m2  mod_m 2
for xdds {
   lam ymin_on_ymax 0.0001 la 1 lo 1.5418 lg 0.0001
   for strs {
      space_group P21
      a 6.425  b 6.522  c 22.716  al 90  be 90.739  ga 90
      if Prm_There(m0)      { scale sc_main 1 min 1e-11 max 1e11 }
      if Prm_There(m0) == 0 { scale sc_sat  1 min 1e-11 max 1e11 }
      mod_qx 0.14216  mod_qy 0  mod_qz 0.38390
      load_q_vector_type refln_index_m_1
      site ...
   }
}
```

`local !m0 0` on the `m = 0` str lets `Prm_There(m0)` pick out the main
reflections, which often need a scale of their own.

Refined values inside a macro body are not written back to the `.out` file.
A file that keeps its refined parameters in macros therefore cannot be rerun
from its `.out`. Prefer `for xdds` and `for strs` loops to a macro expanded once per
structure.

### `move_to_site`

`move_to_site $site` moves the loader back into a site that is already
defined. The modulation keywords can then be written at the end of the `str`:

```
   site S1 ...
   site S2 ...
   move_to_site S1 mod_x ...
   move_to_site S2 mod_y ...
```

## Superspace symmetry: `mod_tau`

A superspace group has three parts, and each reaches TOPAS by its own route:

| part of `Cmme(a,0,1/2)0s0` | written with |
|---|---|
| `Cmme` | `space_group` |
| `(a,0,1/2)` | `mod_qx` `mod_qy` `mod_qz` |
| `0s0` | `mod_tau`, one value per equivalent position |

`mod_tau` is the shift a symmetry operator applies along the internal
coordinate. It belongs to the operator, not to a site: one value per
equivalent position of the space group, in the order of the space group file,
and it is not refined. When absent every value is zero. A shift of 1/2 on a
centring operator changes the sign of the odd order satellites, and on a real
published structure leaving out a non zero `mod_tau` changed the calculated
pattern by more than a peak height. The error is invisible to a "simulate then
refine the same file" test, because both halves then use the same wrong group.

A wrong count is refused and the message gives the right one:

```
... mod_tau but the space group has 8 equivalent positions.
There must be one mod_tau per equivalent position, or none at all. See iso.byu.edu/ssg.php
```

There are four ways to supply it, and only one may be used on a `mod_qm`.

**1. From the superspace group symbol.** `mod_tau_symbol` takes the one line
msCIF symbol; `space_group_ssg_name_IT` is a synonym named after the msCIF item,
and the value can be copied straight from a CIF:

```
   mod_tau_symbol Cmme(a,0,1/2)0s0
   mod_tau_symbol 0s0
   space_group_ssg_name_IT "Cmma(a,0,1/2)0s0"
```

The symbol supplies `mod_tau`; the space group still comes from `space_group`
and **q** from `mod_qx/y/z`. Greek letters cannot be typed: write a Latin letter
in their place, for example `(a,0,1/2)` or `(0,0,g)`. The values used are echoed:

```
   mod_tau_symbol Cmma(a,0,1/2)0s0 loads mod_tau { 0 0 0.5 0.5 0.5 0.5 0 0 0 0 0.5 0.5 0.5 0.5 0 0 }
```

A symbol assumes the standard centring, with no shift on the centring
translations. For the other case add a centring string after a space, one
character per centring translation, `s` for a half and `0` for none. P takes
none; A, B, C and I take one; F takes three. Quotes are needed once a centring
string is present:

```
   space_group_ssg_name_IT "Cmma(a,0,1/2)0s0"      ' C centred, standard centring
   space_group_ssg_name_IT "Cmma(a,0,1/2)0s0 s"    ' C centred, a half on the centring
   space_group_ssg_name_IT "Immm(0,0,g)000 s"      ' I centred, one character
   space_group_ssg_name_IT "Fmmm(0,0,g)000 0s0"    ' F centred, a half on the middle centring
```

Trigonal, tetragonal and hexagonal groups are covered too. The characters
after the modulation vector are read left to right, one per direction of the
point group symbol. `N/m` takes two characters; a rotoinversion like `-3` or
`-6` takes one; a direction written `1` takes `0`. The characters are `0` (no
shift), `s`, `t`, `q`, `h` (a half, third, quarter, sixth) and `-t`, `-q`, `-h`
(two thirds, three quarters, five sixths):

```
mod_tau_symbol "P4(0,0,g)q"          ' the fourfold carries a quarter
mod_tau_symbol "P321(0,0,g)0s0"      ' a twofold on the second direction, a half
mod_tau_symbol "P31m(0,0,g)00s"      ' a mirror on the third direction
mod_tau_symbol "R-3(0,0,g)s"         ' a rotoinversion takes one character
mod_tau_symbol "P6/mmm(0,0,g)00ss"   ' 6/m is two characters, then a half on each mirror set
```

A cubic group has no single modulation vector that every operator maps onto
itself, and a cubic symbol cannot be resolved; enter `mod_tau` or use
`mod_user_operators` (below).

**2. Listing the possibilities.** When the trailing part is ambiguous, or with
`mod_tau_symbol ""` or `mod_tau_build_all`, every allowed series is written into a `#list` in the `.out` file and no refinement is performed. The listing covers
groups whose operators are all of order two; a higher symmetry group needs a
symbol. Each group appears twice, in two settings of the internal origin a
quarter apart. Refine them in turn:

```
#list Mod_Tau_Series {
   { 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 }                   ' Group 1 a
   { 0 0.5 0.5 0.5 0 0 0.5 0 0 0.5 0.5 0.5 0 0 0.5 0 }   ' Group 1 b
   ...
}
num_runs #list_n Mod_Tau_Series
load mod_tau { Mod_Tau_Series(Run_Number) }
```

**3. From a CIF.** `mod_tau_from_cif $file` reads the superspace operators of
a CIF, matches each to an operator of the space group and sets `mod_tau`. It
suits a structure solved elsewhere. `space_group` may be omitted. When the
file cannot be read or an operator has no match, the run stops and asks for
`mod_tau` to be entered directly.

```
   mod_tau_from_cif "ce2o2mnse2.cif"
```

**4. Operators written out.** `mod_user_operators` reads the superspace
operators from a string. Each operator has four parts, `x1,x2,x3,x4`; the first
three are the ordinary operator and the constant in the fourth is its
`mod_tau`. With `space_group` also given, the two must agree; without it the
operators define the equivalent positions and `space_group` is not needed.

```
   mod_user_operators {
      x1,x2,x3,x4
      x1,-x2,-x3,x3+x4+1/2
      -x1+1/2,x2,-x3,-x4+1/2
      -x1+1/2,-x2,x3,-x3-x4
      -x1,-x2,-x3,-x4
      ...
   }
```

It belongs to its `mod_qm`, but the x, y, z parts must be the same for every
`mod_qm` of a `str`. With several modulation vectors it is the way to enter a
star: a (3+2)D operator is written `x1,x2,x3,x4,x5`, one more part per vector,
and an operator may send one vector onto another.

**`mod_t0`** refines the origin of the internal coordinate. Two series in the
listing with the same group number are the same group at two origins, and
refining `mod_t0` with the amplitudes fixed finds the origin quickly. It cannot
turn one superspace group into another: a wrong series stays wrong.

## Site modulation keywords

The harmonic keywords take the harmonic number n (1 to 32), then a **sine**
amplitude, then a **cosine** amplitude:

```
   mod_x   n  <sin> <cos> [qm id]      displacement along a, fractional
   mod_y   n  <sin> <cos> [qm id]      along b
   mod_z   n  <sin> <cos> [qm id]      along c
   mod_occ n  <sin> <cos> [qm id]      occupancy
   mod_beq n  <sin> <cos> [qm id]      isotropic displacement parameter
   mod_u11 n  <sin> <cos> [qm id]      anisotropic; also mod_u22 mod_u33 mod_u12 mod_u13 mod_u23
   mod_mlx n  <sin> <cos> [qm id]      magnetic moment; also mod_mly mod_mlz
```

The two amplitudes are the parameters `isin` and `icos`, and each can be a
value, a refined parameter or an equation:

```
      mod_x 2   sx2 0.01   cx2 0.01
      mod_x 1  = ax; = bx;
```

msCIF lists the cosine before the sine; a converter must swap them.

Points worth knowing:

- Any number of harmonics per keyword. The same harmonic of the same keyword
  twice on one vector is an error; on two vectors it is two waves and allowed.
- `mod_beq` and `mod_u11` to `mod_u23` cannot both be used on one vector, the
  same rule that applies to static `beq` and `u11` to `u23`.
- `mod_mlx/mly/mlz` needs a static moment `mlx`, `mly` or `mlz` on the site.
- A modulated site must hold exactly one atom. For a compositional modulation,
  declare one site per species at the same coordinates, with `mod_occ` of
  opposite sign.
- Which orders a harmonic reaches depends on the quantity. `mod_occ` and
  `mod_mlx/y/z` are linear: harmonic n reaches orders ±n only, and a first
  harmonic occupancy on a `str` with `mod_m 2` contributes nothing and a warning is printed. `mod_x/y/z`, `mod_beq` and `mod_u` reach every multiple of n, and
  several harmonics reach every multiple of their greatest common divisor.
- With a single modulated site only the amplitude of each harmonic is
  determined, not its phase. A refinement can recover the right amplitude with
  the sine and cosine split differently from a published model; that is not a
  failure. A second modulated site fixes the origin.

### Crenel, sawtooth and Legendre functions

A crenel is an occupancy of 1 over a window of the internal coordinate and 0
outside it, for a site present over part of the modulation period.

```
   mod_crenel_width  0.5      ' starts the crenel; width as a fraction of the period, 0 < width <= 1
   mod_crenel_center 0.75     ' optional, default 0; must follow mod_crenel_width
   mod_saw_x 0.031            ' optional sawtooth: a displacement linear across the window
   mod_saw_y 0.017
   mod_saw_z -0.023
```

`mod_crenel_width` creates the crenel and must come before
`mod_crenel_center`. With several vectors the crenel names its vector with
`qm` after the width, vector 0 being the default:

```
   mod_crenel_width  0.22            ' vector 0
   mod_crenel_center 0.11
   mod_crenel_width  0.35  qm 2      ' a second crenel on vector 2
   mod_crenel_center 0.60
```

One crenel per vector per site. A crenel is the whole occupancy modulation of
its vector: it cannot be combined with `mod_occ`, and `mod_beq`, `mod_ml*` and
`mod_u*` are refused on that vector. It may carry `mod_x/y/z` for a
displacement over the full period.

The crenel supplies the average occupancy: a window of width 0.5 scatters at
`m = 0` like a site of occupancy 0.5. A published CIF usually also gives that
average in `_atom_site_occupancy`; set the site occupancy to 1 when a crenel
supplies it, or the two multiply.

Inside a window, displacements are better described by Legendre polynomials
than by harmonics. Sine and cosine are orthogonal over a full period but not
over part of one, and on a crenel the harmonic amplitudes correlate strongly;
Legendre polynomials are orthogonal on the window.

```
   mod_crenel_width  0.5
   mod_crenel_center 0.75
   mod_legendre_x 1  -0.0341     ' order, then one coefficient
   mod_legendre_x 3  -0.0162
```

`mod_legendre_x/y/z` take an order (1 or more) and a single coefficient, and
need a crenel on the same vector. Order 1 is the sawtooth: `mod_saw_x A` and
`mod_legendre_x 1 A/2` are the same model, and `mod_saw_*` and
`mod_legendre_*` cannot both be given on one vector. Orders 2 and above have no sawtooth
equivalent.

Outside a window use `mod_x/y/z`; inside one use `mod_legendre_*`.

## Special positions: `add_constraints`

A site on a special position has its modulation amplitudes restricted by its
site symmetry. Write `add_constraints` in place of the amplitudes; the restrictions are derived and written into the `.out` file:

```
site Ce1  x 0 y 0.25 z 0.13346  occ Ce+3 1 beq 0.3
   mod_y 1 add_constraints
   mod_x 2 add_constraints
' the .out then contains
   mod_y 1  @ 0.001000 = -Get(isin)*Tan(Pi*(Get(z))); : 0
   mod_x 2  @ 0.001000 = -Get(isin)*Tan(2*Pi*(Get(z))); : 0
```

Each amplitude comes back refined, fixed at zero, or tied to another by an
equation in the site coordinates. It works for `mod_x/y/z`, `mod_occ`,
`mod_beq`, `mod_mlx/y/z` and `mod_u11` to `mod_u23`; on any other keyword it is
an error. A displacement and a moment behave differently under inversion: on a
centrosymmetric site every displacive amplitude is forbidden and the moment
is not (`mod-mlx-constraints.inp`).

`Get_mod(mod_keyword)` in a modulation equation returns the parameter of that
keyword with the same harmonic and vector, which allows constraints across
axes:

```
   macro Get_mod_s(w) { Get(Get_mod(w), isin) }     ' both in topas.inc
   macro Get_mod_c(w) { Get(Get_mod(w), icos) }
   site ...
      mod_x 1  @ 0.001      = -0.123 Get(isin);
      mod_y 2  @ 0.001      = -0.456 Get_mod_s(mod_z);
      mod_z 2  @ = Get(icos);  = -0.567;
```

## Single crystal reflection files

A COD or JANA reflection file is read without conversion. Accepted names:

```
intensity   _refln_F_squared_meas   _refln_intensity_meas   _refln_F_meas_au   _refln_F_meas
esd         _refln_F_squared_sigma  _refln_intensity_sigma  _refln_F_meas_sigma_au   _refln_F_sigma
status      _refln_status           _refln_observed_status
```

`_refln_F_meas` is squared, with σ(F²) = 2 F σ(F). Only reflections marked `o`
(observed) are kept; `<` (an upper bound), `-` (systematically absent) and `x`
(excluded) are dropped.

`load_q_vector_type`, inside the `str`, names the order column of the vector.
The default is `refln_modulation_index_1`; a file using `_refln_index_m_1`
needs `load_q_vector_type refln_index_m_1`. When the column is not found, a line is printed containing `column - the whole file is taken as order`, and the
whole file loads into every order; read that line.

Lattice parameters and **q** cannot be refined against single crystal data:

```
Cannot refine on lattice parameters/mod_qxyz for single crystal data
```

Both come from peak positions, which are far more sensitive to them than
intensities. Against powder data **q** can be refined; it moves the satellites
in 2θ.

Equivalent reflections are merged by default and fitted against the summed
observed intensity. `dont_merge_equivalent_reflections` fits them unmerged,
except that a satellite and its Friedel partner are always merged.
`num_highest_I_values_to_keep` applies to single crystal data.

## Powder data notes

A satellite inside the observed range can have a parent reflection far
outside it. `extra_X_left` and `extra_X_right` extend the range of generated
reflections, which lets the tails of peaks just outside contribute.
Satellites are placed from their d spacings, and time of flight data need
nothing extra (`tof-mod-1.inp`). `p1_hkls` generates every reflection without merging
and is a check: a structure must give the same Ycalc with and without it.

## Twinning: `apply_rotation_matrix`

```
   apply_rotation_matrix 0 -1 0  1 0 0  0 0 1
```

Nine integers, a 3×3 matrix T by rows, written in a `str`; it is not specific
to modulation. T is applied to the space group operators and to **q**: the
whole structure rotates, while the site coordinates and amplitudes stay
exactly the way they are written. Do not transform them by hand. `mod_tau` needs no
attention. The determinant must be +1 or −1, otherwise
`Determinant of rotation matrix should be +-1`.

A twin is a second `str` for the same structure in another orientation, with
its own scale, and its sites taken from the first:

```
   str phase_name base   mod_m 0
      prm !base_global 0
      site Ce1 ...
   str phase_name twin   mod_m 0
      scale scale_twin 0.06
      apply_rotation_matrix 0 -1 0  1 0 0  0 0 1
      Get_sites(base_global)
```

No check is made that T is a twin law of the group. A matrix that is not
one runs and gives a plausible but wrong fit. When T sends **q** off its own
star, the twin's satellites share no reciprocal points with the parent's;
a message is printed (`apply_rotation_matrix takes q off its own star`), and with
only one `str` the refinement stops.

## Extinction

There is no extinction keyword. Apply it through a per reflection scale with
`scale_pks`, where `I_no_scale_pks` is the intensity before `scale_pks`:

```
   prm extinction 0.001 min 1e-10 max 100
   scale_pks = 1 / Sqrt(1 + 1e-5 extinction * I_no_scale_pks);
```

`Extinction(extinction, 0.001)` in `topas.inc` writes the same two lines. Each
`str` has its own; a twin has its own. Give the parameter a maximum and refine
the scale before releasing it: extinction and scale both reduce the strong
reflections, and with a free scale extinction barely moves.

## Rigid bodies and occupancy merging

Define the rigid body in the `m = 0` str. The satellite strs reach its sites
through `Get_modulated_sites`, and the rigid body parameters refine from the
satellite intensities too (`rigid-lp-mod_x.inp`). `occ_merge` works with
modulated sites (`occ-merge.inp`).

## R factors

`r_f` is written like `r_wp`, globally and per `xdd`:

```
r_f 0                      ' global
xdd_scr data.hkl  r_f 0    ' per xdd
```

It is `100 Σ|Fcalc − Fobs| / Σ Fobs` with F = √I, the R(F) (R1) that papers
quote. On single crystal data each point is one reflection and it is exactly
R(F). On powder data each point is a profile step, and the same sum is a
profile statistic, and a powder `r_f` is not a crystallographic R.
`r_bragg` is on intensities and is not comparable with `r_f`.

## Output

msCIF, one valid CIF containing the ordinary and the modulation categories:

```
   str
      ...
      Out_CIF_STR(mscif-out.cif)
      Out_msCIF(mscif-out.cif)
```

It holds the wave vectors, the Fourier terms of the displacements, occupancies
and displacement parameters, and the crenel and sawtooth functions. Three
differences from the dictionary: harmonic n is written with the vector n**q**
and referred to by its sequence id; the sawtooth takes the crenel's centre and
width; `_space_group_ssg_name` is not written.

The reflections with their satellite orders, one integer per vector in the
order the `mod_qm` blocks were declared, matching `_refln_index_m_1`,
`_refln_index_m_2` of an msCIF:

```
   phase_out file
      load out_record out_fmt out_eqn {
         "\n%4.0f" = H;
         " %4.0f"  = K;
         " %4.0f"  = L;
         " %s"     = Get(mod_qms);
         " %14.6g" = I_no_scale_pks;
      }
```

Put an `out` block last in its `str`, including the one the `Out_CIF_STR` and
`Out_msCIF` macros write; keywords after it are read into the `out` block.

## Refinement notes

- Every modulation amplitude, the crenel and sawtooth parameters and the
  components of **q** have analytic derivatives.
- The origin of the internal coordinate is free for each vector. Shifting it
  changes every `isin` and `icos` on that vector and leaves the intensities
  unchanged. With one modulated site, refining `mod_crenel_center` does
  nothing, and a warning is printed; with two, fix one centre and refine the other.

## Parameter limits

| parameter | min | max |
|---|---|---|
| `mod_qx` `mod_qy` `mod_qz` `mod_crenel_center` | none | none |
| `mod_x/y/z` `mod_legendre_x/y/z` `mod_occ` `mod_saw_x/y/z` | -1 | 1 |
| `mod_beq` `mod_mlx/y/z` | -20 | 20 |
| `mod_u12` `mod_u13` `mod_u23` | -10 | 10 |
| `mod_u11` `mod_u22` `mod_u33` `mod_crenel_width` | 1e-5 | 20 |

## Messages a user will meet

Each is a refusal with one cause; quoting it back usually identifies the fix.

| message (printed text, or its start) | cause |
|---|---|
| `... has modulation keywords but the str does not have mod_qx, mod_qy or mod_qz defined` | a modulated site with no **q** |
| `There must be one mod_tau per equivalent position, or none at all.` | wrong number of `mod_tau` values |
| `str: mod_tau and mod_tau_symbol cannot both be given on mod_qm` | two routes to `mod_tau`; the same holds for every pair of `mod_tau`, `mod_tau_symbol`, `mod_tau_from_cif`, `mod_user_operators`, `mod_tau_build_all` |
| `str: mod_tau_symbol needs a symbol for this higher-symmetry group on mod_qm` | a listing asked for on a trigonal, tetragonal or hexagonal group |
| `str: mod_tau_build_all covers order two operators only; enter mod_tau or give mod_tau_symbol on mod_qm` | the same, through `mod_tau_build_all` |
| `str: mod_qm names must be unique` | two `mod_qm` with one name |
| `harmonic must be in the range 1 to 32` | harmonic number out of range |
| `duplicate harmonic ...` | the same harmonic of a keyword twice on one vector |
| `a modulated site must have exactly one atom` | a mixed occupancy site with a modulation; split it |
| `mod_beq and mod_u on mod_qm ...` | both on one vector |
| `more than one mod_crenel on mod_qm ...` | two crenels on one vector of a site |
| `... must be greater than 0 and not greater than 1` | crenel width outside (0, 1] |
| `- a Legendre coefficient needs a mod_crenel on the same arm; with no window, use mod_x/y/z` | Legendre without a crenel |
| `- the sawtooth is the first Legendre order, so the two are exactly degenerate; use one or the other` | `mod_saw_*` with `mod_legendre_*` |
| `- a Legendre order must be 1 or more; order 0 is a constant shift of the site` | Legendre order 0 |
| `mod_mlx/mly/mlz needs mlx, mly or mlz` | moment modulation without a static moment |
| `Cannot refine on lattice parameters/mod_qxyz for single crystal data` | refining the cell or **q** on single crystal data |
| `Single crystal modulated data: dont_merge_Friedel_pairs cannot be used.` | see single crystal data above |
| `Single crystal data: Canot have a modulated strucure with an unmodulated str in the same xdd` | a modulated and an unmodulated `str` in one single crystal `xdd`; the spelling is the program's |
| `No hkls for <file>` | an order with no reflections in the file |
| `Determinant of rotation matrix should be +-1` | `apply_rotation_matrix` not a rotation |
| `str: apply_rotation_matrix takes q off its own star.` | the twin shares no satellites with the parent |
| `add_constraints is not available for ...` | `add_constraints` on an unsupported keyword |
| `Cannot use stacking faults with modulated structures.` | |
| `Cannot use PDF data with modulated structures.` | |

Warnings, not refusals: a linear modulation (`mod_occ`, `mod_ml*`) whose
harmonic cannot reach the `str`'s `mod_m`; refining `mod_crenel_center` with
only one modulated site; a `mod_qm` with `mod_m 0` and no amplitude on any
site.

## Worked examples (`test_examples\mod` of a Version 9 installation)

| file | shows |
|---|---|
| **single crystal** | |
| `org\mod.inp` | Wagner & Schönleber (2009): a published model against its published data (COD 2104352), orders to 4, five refined parameters, R(F) 3.69 % against the published 3.63 % on 24,813 reflections |
| `ce2o2mnse2\mod.inp` | Wang et al. (2015): an incommensurate twin with `apply_rotation_matrix`, a crenel with Legendre displacements, extinction, `mod_tau_from_cif`, satellites to fourth order |
| `ce2o2mnse2\manual-twin.inp` | the same twin written by hand, for comparison |
| **powder** | |
| `3-arm-cren.inp` | three modulation vectors, two crenels with sawtooths, twelve parameters including all three vectors |
| `mscif-out.inp` | writing msCIF |
| **constant wavelength neutron** | |
| `occ-merge.inp` | `occ_merge` with modulated sites |
| `rigid-lp-mod_x.inp` | a rigid body in the `m = 0` str reached through `Get_modulated_sites` |
| `example-1.inp` | moment modulation and a crenel together |
| `refine-all.inp` | 30 parameters of many kinds |
| `mlx-mod_occ-crenel.inp`, `mlx-mod_x-mod_mly.inp`, `mlx-mod_x-mod_mly-crenel.inp` | moment modulation combinations |
| `crenel-legendre.inp` | the sawtooth and Legendre order 1 giving the same pattern |
| `mod-mlx-constraints.inp` | `add_constraints` on a moment |
| **time of flight neutron** | |
| `tof-mod-1.inp` | satellites on a time of flight axis |

Most powder examples are self tests: run once with `#define CREATE__` to
simulate the data, then without to refine it.

## Where to find modulated data

**Crystallography Open Database**, `https://www.crystallography.net/cod/`:
structure and reflections are separate files, `NNNNNNN.cif` and
`NNNNNNN.hkl`. Entry 2104352 (C19H27NO3Si, `P21(α0γ)0`, q = (0.14216, 0, 0.38390),
orders −4 to +4) is the model of the tutorial paper by Wagner & Schönleber;
its reflection file carries `_refln_F_calc`, which allows a calculation to be
checked without refining.

**B-IncStrDB**, `https://www.cryst.ehu.eus/bincstrdb/`: view an entry at
`/bincstrdb/view/?incid=<ID>`, fetch its CIF at `/bincstrdb/create/?incid=<ID>`.
About 83 of its entries carry observed intensities inside the CIF itself.

A deposition can hold several `data_` blocks (an average structure, a
composite subsystem, modulated models); check which block a loop belongs to
before combining loops.

## References

- Petříček, V., Eigner, V., Dušek, M. & Čejchan, A. (2016). Z. Kristallogr. 231, 301-312. Crenel and sawtooth functions in Jana2006.
- van Smaalen, S. (2007). Incommensurate Crystallography. IUCr Monographs on Crystallography 21, Oxford University Press.
- Wagner, T. & Schönleber, A. (2009). Acta Cryst. B65, 249-268. A non-mathematical introduction to the superspace description of modulated structures.
- Wang, C., Ainsworth, C. M., Gui, D. Y., McCabe, E. E., Tucker, M. G., Evans, I. R. & Evans, J. S. O. (2015). Chem. Mater. 27, 3121-3134. The modulated structures of Ce2O2MnSe2 and (Ce0.78La0.22)2O2MnSe2.
