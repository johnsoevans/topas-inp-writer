# Quantitative Analysis


```
[xdd]...
    [mixture_MAC #]
    [mixture_density_g_on_cm3 #]
    [weight_percent_amorphous !E]
    [elemental_composition]
    [element_weight_percent $atom $Name #]...
    [element_weight_percent_known $atom #]...
    [prm = Get(sum_smvs)...]
    [prm = Get(mixture_MAC)... ]
    [prm = Get(mixture_density_g_on_cm3) ... ]
    [Mixture_LAC_1_on_cm(0)]
    [str]...
        [cell_mass !E] [cell_volume !E] [weight_percent !E]
            [spiked_phase_measured_weight_percent !E] [corrected_weight_percent !E]
        [phase_MAC !E]
        [prm = Get(sum_smvs)... ]
        [prm = Get(smv)... ]
        [prm = Get(sum_smvs_minus_this)... ]
        [prm = Get_Element_Weight(atom)... ]
        [Phase_LAC_1_on_cm(0)]
        [Phase_Density_g_on_cm3(0)]
```
Examples in `test_examples\quant`


## Summary of Quant examples

quant-1.inp: shows the use of element_weight_percent_known etc.

quant-2.inp: uses the Known_Weight_Percent macro

quant-3.inp: uses elemental constraint using Get_Element_Weight

quant-4.inp: uses Known_Weight_Percent on a hkl_Is phase.

quant-5.inp: uses a dummy_str to describe an amorphous phase

quant-6.inp: uses a hkl_Is phase; links a dummy_str to the hkl_Is phase.

quant-7.inp: uses a fit_obj that is a function of a user_y object to describe a phase; links a dummy_str to a fit_obj to get QUANT info.

The QUANT implementation is, to a large extent, written internally using the TOPAS symbolic system, which allows great flexibility. Dependencies are determined automatically, and unnecessary recalculations are kept to a minimum. quant-1.inp uses many of the above keywords, and additionally writes equivalent terms in the form of equations, for example:


| prm = 100 Get(smv) / Get(sum_smvs); : 0 ‘ This is weight_percent  prm q = spiked_phase_measured_weight_percent /          spiked_phase_measured_weight_percent_wt; : 0  prm = q Get(weight_percent); : 0   ‘ This is corrected_weight_percent prm = 100 (1 - q); : 0             ‘ This is weight_percent_amorphous |
| --- |


## Elemental weight percent constraint

If an elemental weight percent were known, and three phases of the mixture comprised this element, then Get_Element_Weight could be used to get the weight of the element as a function of the structure, i.e.


| str ... prm z1 = Get_Element_Weight(Zr);  MVW(!m1 0, !v1 0,0)  str ... scale s2 0.001 prm z2 = Get_Element_Weight(Zr);  MVW(0, !v2 0,0)  str ... scale s3 0.001 prm z3 = Get_Element_Weight(Zr);  MVW(0, !v3 0,0) |
| --- |

Rearranging the formulae for element weight percent, the scale parameter of one of the phases, say the first one, can be written as:


| scale = (0.01 known_Zr Get(sum_smvs_minus_this) - s2 v2 z2 - s3 v3 z3)          / (v1 (z1 - 0.01 known_Zr m1)); |
| --- |

Get(sum_smvs_minus_this) returns the sum of SMVs minus the phase where it is defined. quant-3.inp demonstrates this constraint with good convergence; it comprises four phases, three of which comprise Zr atoms. quant-2.inp demonstrates constraining a weight percent to a known value using the macro:


| macro Known_Weight_Percent(& w)  { scale = (w / (100 - w)) Get(sum_smvs_minus_this) / (Get(cell_mass) Get(cell_volume)); } |
| --- |


## Elemental composition and Restraints

The xdd dependent elemental_composition reports on the elemental composition of atoms within the structures of the xdd, for example:


| ‘ Before refinement xdd ... elemental_composition | ‘ After refinement xdd ... elemental_composition  {                      Rietveld    AL             0.875`_0.021    O             26.135`_0.009    SI             0.090`_0.003    Y              6.289`_0.012    ZR            66.612`_0.029 } |
| --- | --- |

The xdd dependent elemental_weight_percent returns the weight percent of an element within the corresponding str’s of the xdd. Example usage:


| ‘ Before refinement penalties_weighting_K1 0.1 xdd ... element_weight_percent Zr+4 zr  0 restraint = (zr - 65); : 0 | ‘ After refinement penalties_weighting_K1 0.1 xdd ... element_weight_percent Zr+4 zr 65.027 restraint = (zr - 65); : 0.027525 |
| --- | --- |

In this example, zr is the name given to the element Zr+4, the restraint shows a known value of 65 (set for example by XRF results). The refinement obeys the restraint according to the value set for penalties_weighting_K1. A weight percent can be restrained using:


| xdd ... penalties_weighting_K1 0.2 restraint = (Cubic_Zirconia_wt_percent - 36); : 0 str ... MVW(0,0, !Cubic_Zirconia_wt_percent 0) |
| --- |

Note the name ‘Cubic_Zirconia_wt_percent’ which is given to weight_percent.


## Amorphous phase composition

If spiked_phase_measured_weight_percent is defined, elemental_composition will report on Rietveld values, Corrected values, and values from the original un-spiked sample. If element_weight_percent_known keywords are defined then elemental_composition will additionally report on the elemental contents of the amorphous phase, for example, from quant-1.inp we have:


| elemental_composition {              Rietveld        Corrected         Original           Other AL        1.176`_0.042     1.059`_0.000     0.000`_0.000    0.000`_0.000 O        26.271`_0.017    23.640`_0.832    23.162`_0.849    0.838`_0.849 SI        0.104`_0.004     0.094`_0.005     0.096`_0.005    0.000`_0.000 Y         6.182`_0.013     5.563`_0.204     5.676`_0.209    0.000`_0.000 ZR       66.267`_0.055    59.631`_2.185    60.847`_2.229    2.153`_2.229 Other     0.000`_0.000    10.015`_3.224    10.219`_3.290    7.228`_0.212 } |
| --- |

The "Rietveld" and "Corrected" columns correspond to elemental weight percents as determined for the spiked phase; the "Original" and "Other" columns correspond to elemental weight percents of the original phase. The "Rietveld", "Corrected", and "Original" columns sum to 100%. The last row of the "Corrected" column (purple number) corresponds to Get(weight_percent_amorphous). The last row of the "Other" column (red number) is the amount of sample that is undefined; it is the number in green minus the elements of the "Other" column. Note the zeros for Al (blue number); this is because the spiked phase (dummy test data) is the only phase containing Al.


## Using a dummy_str phase to describe amorphous content

If it is known that the amorphous content (purple number) in the above table comprises a known composition, say TiO2, then a dummy_str can be used to describe the amorphous content, thus:


| dummy_str phase_name "Amorphous" a 5 b 5 c 5 space_group 1 site Ti occ Ti 1 site O occ O 2 Known_Weight_Percent(10.0148) MVW(0, 0 ,0) |
| --- |

dummy_str's that are void of MVW take no part in quantitative analysis. However, if its lattice parameters and chemistry correspond to a real structure, then Mixture_LAC_1_on_cm and phase_LAC can be correctly calculated. When using the Brindley correction, these changed values will affect the quantitative results. The space group entry can differ from P1, so long as the chemistry is correct. Inclusion of the dummy_str produces:


| elemental_composition {                   Rietveld         Corrected          Original AL             1.059`_0.038      1.059`_0.000      0.000`_0.000 O             27.652`_0.015     27.652`_0.975     27.256`_0.995 SI             0.094`_0.003      0.094`_0.005      0.096`_0.005 TI             6.002`_0.000      6.002`_0.215      6.125`_0.219 Y              5.563`_0.012      5.563`_0.204      5.676`_0.209 ZR            59.631`_0.050     59.631`_2.185     60.847`_2.229 Other          0.000`_0.000      0.000`_3.583      0.000`_3.656 } |
| --- |

Note that the ‘Other’ row becomes zero as the amorphous content is now assigned to the dummy_str. The changes in mixture values are:

Without dummy_str:


| Mixture_LAC_1_on_cm( 557.47740`_0.58665) mixture_density_g_on_cm3  5.26713308`_0.00292681843 |
| --- |

With dummy_str:


| Mixture_LAC_1_on_cm( 608.85143`_0.76954) mixture_density_g_on_cm3  5.86601008`_0.00407998952 |
| --- |

If XRF results were entered for element_weight_percent_known, for example:


| element_weight_percent_known Zr 63 element_weight_percent_known O  24 |
| --- |

then we get:


| elemental_composition {              Rietveld        Corrected         Original           Other AL       1.059`_0.038     1.059`_0.000     0.000`_0.000    0.000`_0.000 O       27.652`_0.015    27.652`_0.975    27.256`_0.995   -3.256`_0.995 SI       0.094`_0.003     0.094`_0.005     0.096`_0.005    0.000`_0.000 TI       6.002`_0.000     6.002`_0.215     6.125`_0.219    0.000`_0.000 Y        5.563`_0.012     5.563`_0.204     5.676`_0.209    0.000`_0.000 ZR      59.631`_0.050    59.631`_2.185    60.847`_2.229    2.153`_2.229 Other    0.000`_0.000     0.000`_3.583     0.000`_3.656    1.103`_0.431 } |
| --- |

The negative elemental weight percent for O in the amorphous content reflects the fact that the measured XRF value for O is lower than the refinement's value (this example is for testing purposes; the XRF values here are fictitious).


## Quant using hkl_Is or other non-str phases

dummy_str's can be used to represent the quantitative results arising from non-str phases. For example, consider a phase where the structure is unknown but the chemistry is known. If a calibration constant has been determined relating the hkl_Is intensities to the scale parameter of the hkl_Is phase, a dummy_str can be written as follows (see quant-6.inp):


| dummy_str phase_name "Linked Cubic Zirconia" Cubic(5.137866) space_group F_M_-3_M site Zr x 0     y 0     z 0      occ  Zr  0.85                                  occ  Y   0.15 site O  x 0.25  y 0.25  z 0.25   occ  O   0.96 scale = hkl_scale; Phase_LAC_1_on_cm(0) Phase_Density_g_on_cm3(0) MVW(0, 0 ,0) |
| --- |

Note that, in this case, a space group has been entered with structural parameters resembling a known structure; this could, for example, occur where the structure is known in an ordered state, but the diffraction pattern comprises a disordered state. In other cases, the P1 space group may suffice, with site occupancies corresponding to the appropriate chemistry. The dummy_str is linked to the hkl_Is phase by assigning the scale parameter of the dummy_str to the scale parameter of the hkl_Is phase. quant-7.inp is similar, except that a fit_obj is linked to a dummy_str. Graphically, the linked dummy_str is plotted with the calculated pattern of the hkl_Is phase or fit_obj; for example, quant-7.inp produces:

Here, the blue line corresponds to the dummy_str, which plots the calculated pattern of the linked fit_obj, which in turn comprises a user_y object. The weight percent value determined by the dummy_str is also displayed.


## External standard method

The method of O’Connor and Raven (1988) has been implemented in both GUI and Launch modes using the macros (see test_examples\k-factor):


| macro K_Factor_MAC_K(mac, k, tot) { 	move_to xdd 	local !k_factor_mac_local_ mac 	local !k_factor_k_local_ k 	local !k_factor_sum_wps_ = 0; : tot } macro K_Factor_WP(result) { local k_factor_wp_ = 1.6605402 Get(smv) k_factor_mac_local_   / k_factor_k_local_; : result if Prm_There(k_factor_sum_wps_) { existing_prm k_factor_sum_wps_ += k_factor_wp_; } } |
| --- |


## PONCKS method

Not documented in the TOPAS Technical Reference manual at all — sourced from Dinnebier, Leineweber & Evans, *Rietveld Refinement: Practical Powder Diffraction Pattern Analysis using TOPAS* (2018), §5.5/§5.8.5.

**PONCKS** ("Partial Or No Crystal structure Known Standard") is a technique for quantifying a phase whose crystal structure is unknown, partially known, or too complex to model — but whose Bragg reflections are clearly identifiable in the pattern — by turning a Pawley or Le Bail intensity extraction of that phase into a reusable, calibrated "standard" that behaves like any other quantifiable phase in future refinements of similar samples. It's a middle ground between the external-standard method (needs a pure separately-measured reference) and the internal-standard method (needs a known-structure phase mixed in): PONCKS needs neither a known structure for the phase of interest, nor a spike added to every future sample — just one calibration measurement.

**How it works:**
1. Obtain (once) a sample where the target phase is present either in pure form, or mixed with known phases in a known amount (e.g. deliberately spiked with a calibrated internal standard).
2. Fit that target phase as a Pawley or Le Bail "pseudo-structure" (a group of extracted peak intensities, or a Pawley/Le Bail phase in an appropriate — possibly artificial — unit cell), with its overall `scale` fixed to exactly 1.0 and the Lorentz-polarization correction applied as normal (handled automatically by TOPAS's usual LP macros).
3. Using the known amount of the target phase (from the spike, or from being pure) together with an internal standard's known ZMV, back-calculate an *artificial* `(ZM)` value for the target phase. This value has **no direct physical meaning** — it isn't the real unit-cell contents or volume — it's purely a calibration constant that makes the standard-less QPA weight-fraction formula (`references/11-quantitative-analysis.md` above, `weight_percent`/`MVW`) come out with the correct weight fraction for this specific phase under this specific experimental configuration (wavelength, geometry, etc.). If the real density of the material is known independently, a "correct" (physically meaningful) ZM can instead be derived from `ZM = ρV/1.6604` — the same density-to-ZM relationship used elsewhere in quantitative analysis (see "Elemental composition" above) — but this isn't required for PONCKS to work.
4. Save this calibrated pseudo-phase (its extracted peak intensities, its fixed scale, and its derived ZM) as a new PONCKS phase for reuse.
5. In any future refinement of a similar sample, include the saved PONCKS phase with only its `scale` factor allowed to refine and all its peak intensities kept fixed — TOPAS's normal `weight_percent`/`corrected_weight_percent` machinery then reports the correct absolute weight fraction of that phase directly, with no further calibration needed.

**Practical requirements and caveats:**
- The calibration measurement (step 1-3) needs the target phase to be present either pure, or in a large/well-determined enough amount that its extracted intensities and derived ZM are reliable — a trace amount in a complex mixture is not a good calibration sample.
- A PONCKS-derived ZM (like an external standard's K-factor) is tied to the experimental conditions it was calibrated under (wavelength, geometry, etc.) — keep these constant across the series of samples being compared, exactly as for the external-standard method.
- Quantitative phase analysis in general becomes progressively less reliable as more unknown/uncalibrated phases are present in the same mixture; intensity-affecting systematic errors (absorption, overspill, preferred orientation) should be minimized regardless of which QPA method is used.
- A worked example in the book: an amorphous SiO2 "flour" mixed 50:50 with alumina was first quantified (via internal/external standard methods) at 18.73 wt% amorphous content; fitting it as a pseudo-orthorhombic Pawley phase (scale fixed to 1) and back-calculating ZM from that known 18.73% gave a reusable PONCKS ZM of ~1314 g/mol. That same saved PONCKS phase, dropped into a different mixture (5 wt% of the same amorphous SiO2 + 45 wt% quartz + 50 wt% alumina) with only its scale factor refined, immediately reproduced the correct ~5% weight fraction via `corrected_weight_percent` — demonstrating the calibrate-once, reuse-many-times workflow.


## QUANT Keywords

[cell_mass !E] [cell_volume !E] [weight_percent !E]

[spiked_phase_measured_weight_percent !E] [corrected_weight_percent !E]


|  | where  Np = Number of phases. Qp = SpMpVp/Bp Sp = Rietveld scale factor for phase p. Mp = Unit cell mass for phase p. Vp = Unit cell volume for phase p. Bp = Brindley correction for phase p, |
| --- | --- |

The Brindley correction is a function of brindley_spherical_r_cm and the phase and mixture linear absorption coefficients; the latter two are in turn functions of phase_MAC and mixture_MAC respectively, or,

Bp is function of :  (LACphaseMACmixture) brindley_spherical_r_cm

LACphase 	= linear absorption coefficient of phase p, packing density=1.

MACmixture= linear absorption coefficient of the mixture, packing density=1.

This makes Bp a function of the weight fractions wp of all phases and thus wp as written above cannot be solved analytically. Subsequently wp is solved numerically using an iterative procedure.

[mixture_density_g_on_cm3 #]

Calculates the density of the mixture assuming a packing density of 1, see also mixture_MAC.

[mixture_MAC #]

Calculates the mass absorption coefficient in cm2/g for a mixture as follows:

where wi and ( /)i is the weight percent and phase_MAC of phase i respectively. Errors are reported for phase_MAC and mixture_MAC. The following example calculates phase and mixture mass absorption coefficients.


| xdd ... mixture_MAC 0 str ... phase_MAC 0 |
| --- |


| xdd ... Mixture_LAC_1_on_cm(0) str ... Phase_Density_g_on_cm3(0) Phase_LAC_1_on_cm(0) |
| --- |

Errors for these quantities are also calculated. Mass absorption coefficients obtained from NIST at http://physics.nist.gov/PhysRefData/XrayMassCoef are used to calculate mixture_MAC and phase_MAC.

[phase_MAC !E]

Calculates the mass absorption coefficient in cm2/g for the current phase. See description for mixture_MAC.

[weight_percent_amorphous !E]

Determines the amorphous content in a sample. The phase dependent spiked_phase_measured_weight_percent needs to be defined for weight_percent_amorphous to be calculated.
