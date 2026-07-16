# Stacking faults


```
[site $name]...
    [layer $layer]
[stack $layer]...
    [sx E] [sy E] [sz E]
    [generate_these $sites]
        [generate_name_append $append_to_site_name]
```

The supercell approach to stacking faults has been implemented. layer identifies a site as belonging to a layer called $layer; stack applies a stacking vector {sx, sy, sz} to the named layer. Structure factors are generated in the usual manner, with a shift applied corresponding to the stacking vector. stack operates in any space group. Sites that do not belong to a layer are treated as un-stacked, and their structure factors are generated in the usual manner. generate_these generates the sites found in $sites for the stack, with coordinates reflecting the original $sites positions plus the stacking vector. generate_name_append appends $append_to_site_name to the generated site. The generated sites have occupancies set to zero, which signals a dummy site. Dummy sites do not take part in structure factor calculations, so speed is not affected. The dummy sites allow for graphical display of the layers, i.e.

Importantly, penalties can operate on dummy sites which allow for restraints such as Distance_Restrain. The following rules govern the behaviour of sites marked with layer:

A site marked with layer cannot take part in restraints.

A site marked with layer is not displayed graphically.

A site generated using generate_these can take part in restraints.

A site not marked with layer can take part in restraints.

For example:


| space_group P1 site O1 ... layer A site O2 ... layer A stack A sx ... generate_these O1 generate_name_append _1 append_fractional in_str_format |
| --- |

will output for append_fractional the following:


| site O1 ... site O2 ... site O1_1 ... occ O 0 |
| --- |


## Types of stacking faults (a naming taxonomy)

Not in the Technical Reference manual — sourced from Dinnebier, Leineweber & Evans (2018), §10.2/§10.3/§10.4. Knowing this vocabulary helps identify which TOPAS mechanism (a discrete `generate_stack_sequences` transition-probability matrix vs. a continuous random `Δ` term added to the stacking vector) actually matches a given real material's disorder, and helps recognize the disorder type from the diffraction pattern itself before ever writing an INP file.

**Where the stacking vector comes from**: for a close-packed structure, each layer-to-layer transition is described by a stacking vector `S = (sx, sy, sz)`; for simple close packing there are only two distinct vectors available (e.g. the familiar ccp/hcp case), which is the geometric origin of the `1/3`, `-1/3` fractions seen as `a_add`/`b_add` values in the worked `generate_stack_sequences` examples elsewhere in this file — they aren't arbitrary, they're the actual in-plane displacement between adjacent close-packed layers expressed in fractional coordinates of the (often transformed, pseudo-orthorhombic/pseudo-trigonal) cell.

**Named fault types**, in increasing order of how much of the stacking sequence they disrupt:
- **Twinning**: the stacking vector switches from one orientation (e.g. S1, giving αβγ-type ccp stacking) to the other (S2, giving γβα stacking) at an interface and *stays* switched — the two differently-oriented domains meeting at that interface are related by twinning, and the interface itself locally looks like the alternate (e.g. hcp-like βγβ) stacking.
- **A single local fault**: the stacking vector switches from S1 to S2 and then immediately back to S1 — a single hcp-like interruption in an otherwise-continuous ccp stacking sequence (or vice versa), rather than a permanent domain switch.
- **Extended intergrowth**: several consecutive layer transitions use the alternate stacking vector before switching back — i.e. a genuine, crystallographically-real intergrowth of the two stacking motifs (a run of hcp-like stacking embedded in a ccp crystal), not just a single-layer glitch. This is the general case `generate_stack_sequences`'s transition-probability-matrix machinery is built to describe statistically.
- **Turbostratic disorder**: layers are randomly displaced within their own plane (or rotated within their own plane — rotations don't generate any new reflections in the diffraction pattern, so only the translational part matters in practice) with **no change in interlayer spacing** (Δz=0). Unlike the fault types above, this isn't a *discrete* choice between a finite set of stacking vectors — it's a continuous random in-plane shift (Δx, Δy) added on top of the ideal stacking vector, and needs a genuinely different INP modeling approach than a discrete transition matrix (a random `Δ` term rather than `generate_stack_sequences`' finite set of named transitions).
- **Interstratification**: an inhomogeneous intercalation of ions/molecules between layers (seen e.g. in brucite-type Mg/Ni hydroxides) that instead randomizes the **z-component** of the stacking vector — the opposite emphasis from turbostratic disorder (which specifically fixes Δz=0) — and frequently co-occurs with turbostratic-like in-plane disorder in the same real material. Distinguishing turbostratic disorder from interstratification in a real sample is a matter of checking which component(s) of the stacking vector are actually randomized.

**Recognizing turbostratic disorder from the diffraction pattern itself** (Warren, 1941): because a 2D (turbostratically disordered) layer's reciprocal lattice becomes continuous rods perpendicular to the layer (not sharp 3D reciprocal-lattice points), the resulting powder pattern has a characteristic, recognizable signature: 00l reflections stay sharp (unaffected — they don't depend on the in-plane stacking at all), while hkl (h,k ≠ 0) reflections become diffuse and anisotropically broadened, with a specific asymmetric **triangular/saw-tooth peak shape that is always skewed toward higher 2θ** — a distinctive enough shape that it's often recognizable by eye before any modeling is attempted. If a pattern shows this signature, a turbostratic-disorder (continuous Δx,Δy) model is the appropriate approach rather than a discrete `generate_stack_sequences` transition matrix.

**A vocabulary note for anyone coming from the DIFFaX program**: TOPAS's `generate_stack_sequences` with `number_of_sequences` set to average over many generated sequences corresponds to DIFFaX's "recursive" statistical-averaging mode; using a single generated sequence (just a bare `Transition(...)` plus `number_of_stacks_per_sequence`, no averaging over multiple generated sequences) corresponds to DIFFaX's "explicit" mode.


## Fitting to a Debye-formulae pattern using ‘stack’

A test pattern was generated using the Debye scattering equation. The structure comprised a single atom in an orthorhombic unit cell with 40 layers (40×40×40 unit cells) in the a-b plane, shifted according to {Round(Rand(0,2))/3, Round(Rand(0,2))/3, 0}. The blue line below is the generated pattern, comprising the average of 30 runs of the Debye scattering equation. The red line corresponds to a Rietveld fit of 6 supercell structures (1×1×40), showing that the supercell approach is a good approximation to the Debye formula for this example.

The example stacking-faults\debye-new.inp corresponds to the Rietveld fit using the layer and stack keywords. The debye-old.inp file corresponds to the same Rietveld fit, but without the layer and stack keywords; instead, layers are explicitly defined using site in an enlarged unit cell.

There are two time-consuming bottlenecks dealt with:

Summing peaks to Ycalc

Calculating structure factors for the stacked layers

The phase dependent [del_approx #] groups peaks from the peaks buffer whilst summing peaks to Ycalc; the peaks are grouped such that their 2Th positions all lie within:

(–del_approx  Peak_Calculation_Step) <  2 Th <  (del_approx Peak_Calculation_Step)

Once the group is found, only the two peaks with the smallest and largest 2Th are kept. The in-between peaks have their intensities apportioned to the kept peaks. The peak-buffering routines have also been optimized for both accuracy and speed. The following points should be noted when working with large supercells:

The layer and stack keywords increase computational speed and reduce memory usage.

del_approx increase computation speed at a relatively small cost to accuracy; a value between 1 and 3, dependent on Peak_Calculation_Step, is typically acceptable.

The graphical display of 10s of 1000s of hkl ticks (there are 51584 hkls in each phase of the debye-new.inp) is time consuming; turning the graphical hkl-ticks option Off is worthwhile.


## Fitting to Kaolinite data

stacking-faults\kaolinite.inp demonstrates the application of stack and layer with the following fit:

In this example the stacking vectors are refined in a simulated annealing process.


## Stacking faults and generating sequences of layers


```
[generate_stack_sequences]{
    [number_of_sequences !E]
    [number_of_stacks_per_sequence !E]
    [save_sequences $file]
    [save_sequences_as_strs $file]
    [user_defined_starting_transition $transition_name]
    [layers_tol !#0.5]
    [n_avg !E]
    [num_unique_vx_vy !N]
    [match_transition_matrix_stats {...}]
    [transition $transition_name]...
        [use_layer $layer]
        [height E]
        [n !N]
        [to $to_transition_name !E]...
            [ta E] [tb E] [tz E]
            [a_add E] [b_add E] [z_add E]
}
' Get(generated_c)
```

Examples: `test_examples\stacking_faults\fit-1.inp`, `fit-2.inp`, `fit-3.inp`, `rietveld-generate\create-sequences.inp`, `rietveld-generate.inp`, `fit-to-rietveld-generated.inp`, `rietveld-generated-200-2000.xy`, `strs-200-2000.txt`

Stacking-fault generation and refinement can now be performed at speeds that make routine analysis possible (Coelho et al., 2016). generate_stack_sequences generates sequences of stacks from the transition matrix described by the transition keyword. The opening and closing braces of { ... } correspond to a block within which keywords local to generate_stack_sequences can be used; outside the braces, these keywords cannot be used. After the sequences are generated, Get(generated_c) is updated with the average thickness of the generated sequences and can be used to set the c lattice parameter.

On termination of refinement, num_unique_vx_vy reports the number of unique {sx, sy} stacking vector coordinates for all layer types. transition defines a "from" transition with the name $transition_name; the transition uses the layer defined in use_layer. to defines the "to" transition; $to_transition_name must be a defined $transition_name. n returns the number of transitions generated for the corresponding "to" transition. height can be used instead of the z_add keyword. ta, tb define the stacking vector's x and y coordinates in terms of the crystallographic a and b axes. a_add, b_add define the stacking vector's x and y coordinates relative to the previous stacking vector, in terms of the crystallographic a and b axes. tz defines the stacking vector's z coordinate along the crystallographic c axis, in Å. add_z defines the stacking vector's z coordinate along the crystallographic c axis, in Å, relative to the previous stacking vector.

user_defined_starting_transition: if used, stacking begins at the transition named $transition_name; otherwise, stacking begins at the transition with the greatest probability according to the probability density matrix. layer_tol corresponds to q of Fig. 1 in the paper (Coelho, 2016); it describes the termination condition when generating the stacking sequence.


### Generating the same stacking sequences each run

The random number generator can be seeded with a constant value using seed, to generate the same set of stacking sequences on each run, for example:


| seed #number |
| --- |

#number is a constant integer; each #number generates its own unique set of random numbers. Generating identical sets of stacking sequences is useful when changes in Rwp that exclude stacking-sequence variation are desired.


### The SF_Smooth macro

Stacking faulted calculated patterns can contain ripples when the peak shapes are small or when there are too few layers stacked. The SF_Smooth macro, defined in Topas.inc smooths these ripples such that small supercells can approximate large supercells; this increases computation speed and reduces memory usage. All stacking fault examples use SF_Smooth; typical usage is:


| SF_smooth(@, 1, 1) |
| --- |

The refined parameter adjusts the width of a Gaussian convolution that depends on the hkls and intensities of the reflections. The last argument (the "1") can be used to adjust the tolerance of peak_buffer_based_on used in the SF_Smooth macro; the latter is defined as:


| peak_buffer_based_on = idl;  peak_buffer_based_on_tol = Max(0.01 idl, Peak_Calculation_Step 0.5 s); |
| --- |

Reducing s increases the number of peaks in the peaks buffer and increases the accuracy of the calculated pattern. s=1 is typically sufficient.


### Fitting to DIFFaX test diamond data

fit-1.inp uses generate_stack_sequences to fit to data generated from the DIFFaX suite (Treacy, 1991); the INP segment that generates the sequences looks like:


| generate_stack_sequences {       number_of_sequences Nseqs 200       number_of_stacks_per_sequence Nv 200       num_unique_vx_vy  6       Transition(1, lpc)          to 1 = pa;     a_add = 2/3;  b_add = 1/3;   n !n1  349984          to 2 = 1-pa;   a_add = 0;    b_add = 0;     n !n2  149781       Transition(2, lpc)          to 1 = 1-pa;   a_add = 0;    b_add = 0;     n !n3  149781          to 2 = pa;     a_add = -2/3; b_add = -1/3;  n !n4  350254    } |
| --- |

The generated probability parameter pa can be determined using the n values as follows:


| prm !pa_gen = (n1+n3)/(n1+n2+n3+n4); : 0.699974874 |
| --- |

The fit to the DIFFaX data looks like:


### Stacking faults from layers of different layer heights

Layers of different thicknesses can be accurately modelled, with fast refinement. Here's a fit to simulated data (fit-2.inp) for two different layer heights of 5 and 6Å.


### Rietveld-Generated example

The files in the rietveld-generate directory can be used to create a stacking faulted test pattern using Rietveld refinement, which can then be refined against. create-sequences.inp creates the INP-format stacking sequences and places the result in the file strs-200-2000.txt. The file rietveld-generate.inp can be used to create the test pattern rietveld-generated-200-2000.xy. This test pattern can be fitted-to using fit-to-rietveld-generated.inp; this INP file uses generate_stack_sequences and demonstrates the accuracy and speed of the stacking fault averaging procedure. The fit to the Rietveld generated stacking faulted pattern looks like this:


### Refining on layer heights

Layer heights can be refined by refining parameters that are a function of the add_z or height keywords. The fit-3.inp example refines three height parameters, as well as the z fractional atomic coordinates of the sites comprising the layers. It also lists six types of transitions operating on three unique layer types; the transitions point to the unique layer types using use_layer. The c lattice parameter is defined and refined as follows:


| prm qq 0 c = Get(generated_c) + 0.0001 qq; : 1828.085117 |
| --- |

Get(generated_c) is also used to initialize the z fractional coordinates of the sites as follows:


| prm height_Se01 7.49691  prm !zSe01 = height_Se01 / Get(generated_c); site Se01 x 0.5 y 0 z = zSe01; occ Se 1 beq !bval 1 layer cd00 |
| --- |

The fit to the test data looks like:
