# Magnetic Structure Refinement


```
[str]...
    [mag_only_for_mag_sites]
    [mag_space_group $symbol]
    [site]...
        [mlx E] [mly E] [mlz E] [mg E]
        [mag_only]
        ' Site dependent macros
        MM_CrystalAxis_Display(mxc, myc, mzc)
        MM_CrystalAxis_Refine(mxc, mxv, myc, myv, mzc, mzv, mlx_v, mly_v, mlz_v)
        MM_Cartesian_Display(mxc, myc, mzc)
        MM_Cartesian_Refine(mxc, mxv, myc, myv, mzc, mzv, mlx_v, mly_v, mlz_v)
```

Thanks to Branton Campbell and John Evans for expert assistance during the implementation of magnetic structure refinement. Magnetic refinement is implemented using the keywords mlx, mly, mlz, mg and mag_space_group. See examples in the test_examples\mag directory as well as the tutorial by John Evans at:

http://www.dur.ac.uk/john.evans/topas_workshop/tutorial_lamno3_magnetic.htm

The Magnetic intensity is given by (* denotes conjugate gradient):

Magnetic intensity = Fmagcperp . Fmagcperp* = |Fmagcperp|

Fmagcperp = Fmagc - (Fmagc . Qhat) Qhat

Or in words, Fmagcperp is the component of the magnetic vector in the direction perpendicular to the scattering vector Q, where:

Q = (L-1)T * h

Qhat = Q / |Q|

L is the Cartesian lattice parameters in 3x3 matrix form

h is the Miller indices in vector form

* denotes matrix multiplication

Superscript -1 denotes matrix inverse

Superscript T denotes matrix transpose

(L-1)T = reciprocal lattice parameters

Fmagc in terms of the Cartesian lattice parameters is:

Fmagc = L * Fmag

Fmag for the plane h for a single site is:

Fmag = ∑j (Bj * m) Exp(2π i Uj)

where the summation is over the equivalent positions j and:

Uj = h.Rj x + h.tj

x = { x, y, z } = site fractional coordinates

m = { mlx, mly, mlz } = magnetic moment

Rj = rotation part of space group operator

tj = translational part of space group operator

dj = sj determinant(Rj) = sj det(Rj)

Bj = sj det(Rj)  Rj = magnetic transformation matrix

The file MAGDATA.DAT (a GSAS file — permission for use granted by Robert Von Dreele, author of GSAS) comprises data for calculating magnetic form factors. The Lande splitting factor can be refined using the site-dependent parameter mg; defaults for mg are obtained from MAGDATA.DAT. Shubnikov groups are obtained from the file shubnikovgroups.txt. When mag_only is defined, the non-magnetic component to intensity for the site in question is ignored. When mag_only_for_mag_sites is defined, the non-magnetic component to intensity for all magnetic sites for the str in question is ignored.

**Magnetic form factor falls off faster than the X-ray form factor** (not in the Technical Reference manual — sourced from Dinnebier, Leineweber & Evans, 2018, §9.2): because the electrons responsible for a magnetic moment are concentrated in outer-shell, higher-quantum-number orbitals, the magnetic form factor S(s) decays with sin(θ)/λ noticeably faster than the ordinary X-ray atomic form factor does. Concretely, for Mn2+ at sinθ/λ=0.32 (60° 2θ for λ=1.54 Å), the X-ray and magnetic form factors have fallen to about 60% and 20% of their θ=0 value respectively — and since magnetic *intensity* depends on the square of the form factor, the effect on intensity is even more dramatic: Mn2+ magnetic intensity typically falls to 50% by sinθ/λ≈0.15 (~27° 2θ for λ=1.54 Å). Practically, this means magnetic scattering is concentrated at low angle and falls off quickly — if magnetic peaks seem to vanish well before nuclear peaks of similar d-spacing do, that's the expected behavior, not necessarily a sign of a modeling problem.


## Magnetic symmetry and Shubnikov groups (why the two magnetic-refinement workflows exist)

Not in the Technical Reference manual — sourced from Dinnebier, Leineweber & Evans (2018), §9.3. This section explains the crystallographic reasoning behind keywords already documented above and elsewhere in this file.

**A magnetic moment is an axial vector, not a polar vector** — it behaves *oppositely* to an ordinary vector under mirror reflection. Picture a magnetic moment as arising from a current loop: a moment perpendicular to a mirror plane is preserved by the mirror, while a moment parallel to the mirror plane gets flipped — the reverse of how a normal (polar) vector, like an atomic displacement, transforms under the same mirror. This single fact is the direct reason the two warning messages above exist: whether a given site's mlx/mly/mlz component can contribute to (or be refined from) the magnetic structure factor at all depends on how that component transforms under the site's local symmetry, which is different from how an ordinary displacement parameter would transform under the same symmetry.

**Time reversal (spin reversal, "1′")** is an additional symmetry operator beyond the ordinary 230 crystallographic space groups — it flips a spin's direction (equivalently, reverses the current loop's direction) without any accompanying rotation/translation in space. Combining the 230 crystallographic space groups with time reversal produces the 1651 **magnetic space groups** (Shubnikov groups, historically called "two-colour" or "black-white" groups since each site's colour — black or white — corresponds to whether the operations mapping to it involve a spin flip). These fall into four types (labelling the crystallographic space group F and the magnetic space group G):
- **Type 1**: no operator involves time reversal; G = F exactly (the magnetic structure has the full symmetry of the crystallographic space group, with all moments related by ordinary symmetry operations alone).
- **Type 2** ("grey"): time reversal 1′ itself is a symmetry operator (G = F + F1′) — this describes the *paramagnetic* (disordered/zero-average-moment) case, not an ordered magnetic structure.
- **Type 3** ("black-white, first kind" / equi-translation): the magnetic cell is the *same size* as the crystallographic cell; some but not all point-group operations are combined with time reversal.
- **Type 4** ("black-white, second kind" / equi-class): translational symmetry elements themselves are coupled with time reversal, producing a "coloured lattice" whose magnetic cell is *larger* than the crystallographic cell.

**This directly explains the choice between the skill's two documented magnetic-refinement workflows** (see the LaMnO3-style worked examples referenced above): a Type 3 magnetic space group (same-size magnetic and nuclear cells) is naturally handled with a *single* `mag_space_group` phase carrying both nuclear and magnetic scattering, whereas a Type 4 magnetic space group (magnetic cell larger than the nuclear cell) is naturally handled as *separate* nuclear and magnetic phases (the magnetic phase using `mag_only_for_mag_sites` in its own, larger cell) — the crystallography, not just convenience, determines which workflow fits a given real structure.

**Naming caveat**: magnetic space groups are labelled under two different historical conventions, BNS (Belov–Neronova–Smirnova) and OG (Opechowski–Guccione), which can assign different serial numbers and symbols to the *same* magnetic space group (e.g. BNS `Camma`, serial 67.509, TOPAS symbol `C_amma`, is the identical group to OG `Pcmmm′`, serial 47.11.357). **`mag_space_group` expects the BNS serial number specifically** — external references (the Bilbao Crystallographic Server, the ISO-mag database, Litvin's electronic *Magnetic Space Groups* book) commonly list both conventions side by side, so double-check you're reading off the BNS number, not the OG one, when looking up a group from the literature. `shubnikovgroups.txt` (mentioned above) lists BNS numbers alongside their BNS symbols.


## Ambiguities in magnetic structure determination

Not in the Technical Reference manual — sourced from Dinnebier, Leineweber & Evans (2018), §9.4. Powder diffraction data is inherently low-information-content, and this is especially true for magnetic scattering (few reflections, concentrated at low sinθ/λ, often overlapped) — some real named pitfalls worth knowing before over-interpreting a refined magnetic model:

- **Genuinely degenerate models**: two magnetic structures that look completely different — e.g. a "block" arrangement with identical moments on every site ordered ↑↑↓↓↑↑↓↓... versus an arrangement with zero moment on every second site and ↑0↓0↑0↓0... ordering on the rest — can produce *identical* powder magnetic diffraction patterns differing only by a scale factor (specifically, if the second structure's moment is √2 times larger than the first's). No amount of refinement against powder data alone can distinguish these; distinguishing them requires other evidence (e.g. bulk magnetic measurements, single-crystal data, or a physical argument about which is chemically sensible).
- **Multi-k structures** (magnetic structures needing more than one propagation vector to describe): the spin configuration cannot be uniquely determined from powder diffraction data alone in this case — symmetry constraints or an assumption of equal moment magnitude on all sites can narrow the possibilities but can't fully resolve the ambiguity from powder data by themselves.
- **Shirane's rule** (Shirane, 1959) — for *collinear* magnetic structures, how well powder data can pin down the moment *direction* depends on the crystal system: no information at all is available for cubic systems; for tetragonal, rhombohedral, and hexagonal systems only the angle between the moment and the unique (c) axis is determinable, with no information on orientation within the ab-plane; full moment-direction information is only really recoverable for orthorhombic-or-lower symmetry. The same practical ambiguity can reappear even in orthorhombic/monoclinic/triclinic samples if the true metric symmetry is only slightly distorted from a higher-symmetry cell (peak overlap reintroduces the same information loss).

These are genuine information-content limits of the powder magnetic diffraction experiment itself, not modeling mistakes — worth keeping in mind before concluding a refined moment direction or magnitude is more precisely determined than the data actually supports.


## Magnetic refinement warnings/exceptions

The following two messages:

Warning: Magnetic moment mlx of site Fe has no contribution to Fmag

Magnetic moment mlx of site Fe cannot be refined as it has no derivative

arise when, for each group of equivalent positions of a special position, the first row of the matrix ∑jBj*m is zero where the j's sum over the equivalent positions of a special position group. Similar messages for mly and mlz are given. Note, even though mlx, mly, mlz may not be refined, the warning in (1) is still given, depending on associated constraints. Refinement terminates in the case of message (2) when mlx is being refined. (See "Magnetic symmetry and Shubnikov groups" above for the crystallographic reason this class of warning arises at all: it's a direct consequence of a magnetic moment being an axial rather than polar vector.)


## Displaying Magnetic moments

Magnetic moments (Occupancy Bj*m) are displayed graphically when view_structure is defined.  In cases where the atom balls mask the display of the magnetic moment arrows, the "Atom size" can be varied, as shown in the following:


## ‘Decomposing’ Fmag for speed

When using magnetic space groups, equivalent positions for groups other than 1.1 are written in terms of other equivalent positions.

Let	Cj = cos(Uj),

Sj = sin(Uj)

Exp( i U) = Cj + i Sj = Euler's formulae

For two equivalent positions of a special position, we have:

U1 = U2 = U


| Fmag1 + Fmag2 | = s1 det(R1)  R1 m Exp(i U) + s2 det(R2)  R2 m Exp(i U) = (s1 det(R1) R1 + s2 det(R2) R2) m Exp(i U) = c m Exp(i U) |
| --- | --- |

c is independent of x. Note, a particular special position could have many equivalent positions.

If for two equivalent positions R1  = -R2 and t1  = -t2 then:

U1 = -U2 = U


| Fmag1 + Fmag2 = Now, or, For s1 = s2, For s1 = -s2, | s1 det(R) R m Exp(i U) + s2 det(-R) (-R) m Exp(-i U) det(R) R = det(-R) (-R) Fmag1 + Fmag2 = det(R) R m (s1 Exp(i U) + s2 Exp(-i U)) Fmag1 + Fmag2 = s1 det(R) R m 2 C Fmag1 + Fmag2 = s1 det(R) R m (2 i S) |
| --- | --- |

If for two equivalent positions R1 = R2, then:

Fmag1 + Fmag2 	= s1 det(R) R m Exp(i h. R x) Exp(i h.t1) +

s2 det(R) R m Exp(i h. R x) Exp(i h.t2)

= det(R) R m (s1 Exp(i h.t1) + s2 Exp(i h.t2)) Exp(i h. R x)

= c Exp(i h. R x)

c is independent of x and is calculated only once. Many R's can be the same for a particular space group with only the t's changing.

Calculating C and S:

Exp(i (h . R x + h. t)) = Exp(i h . R x) Exp( i h . t)

Exp(i h . t) is constant for a particular h and is calculated only once.

Only unique Exp(i h . R x) are calculated.

Trigonometric recurrence is used to calculate sines and cosines resulting in three cosine and three sine operations per unique equivalent r. In other words, a sin and cos are not calculated for each h; also a sin or cos function is equivalent to approximately 40 to 60 multiplies.
