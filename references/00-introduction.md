# Introduction

This document describes the TOPAS-Academic kernel and its macro language. The kernel is written in ANSI C++, with internal data organised as a tree similar to an XML representation, where each node corresponds to a C++ object. Input is read from an INP file (*.INP) containing keywords and macros; macros are named groupings of keywords. Before execution, the kernel pre-processes the INP file, expanding all macros and writing the result to TOPAS.LOG; it then parses this expanded file to build its internal data structures. The main tree-node objects are:


| xdd... bkg str... xo_Is... d_Is... hkl_Is... fit_obj... | : Background. : Structure information for Rietveld refinement. : 2-I values for single line or whole powder pattern fitting. : d-I values for single line or whole powder pattern fitting. : Lattice information for Le Bail or Pawley fitting. : User defined fit models. |
| --- | --- |

str, xo_Is, d_Is and hkl_Is are referred to as "phases" and the peaks of these "phase peaks". A listing of the data structures is given in section 21.1.


## Running TOPAS in high priority mode

Modern Windows security settings increasingly prevent executables from running in high-priority mode, which can slow TOPAS significantly during large refinements — particularly those with high memory usage. Running TOPAS in high-priority mode resolves this. The example below shows a factor of 10 or more improvement in run time when executing xrd-ct-1.inp with tc.exe.


### Running TA.EXE in high priority mode (TOPASH.BAT)

Run the following from the command line:

start "" /high "ta"

Or, run the batch file TOPAS-HIGH-PRIORITY.BAT or TAH.BAT.


### Running TC.EXE in high priority mode

From the command prompt, use the following to start the command prompt:

start /high "cmd"

Or, run the command as an administrator from the start menu by typing ‘command’ and then choose the “Run as administrator”.


## Conventions

Keywords look like this.

Macros look like this.

Keywords enclosed in square brackets [ ] are optional.

Keywords ending in ... indicate that multiple keywords of that type are allowed.

Text beginning with the character # corresponds to a number.

Text beginning with the character $ corresponds to a string.

E after keyword: corresponds to an equation (i.e. = a+b;) or constant (i.e. 1.245) or a parameter name with a value (i.e. lp 5.4013) that can be refined.

!E after keyword: corresponds to an equation or constant or a parameter name with a value that cannot be refined.

To avoid input errors, it is useful to differentiate between keywords, macros, parameter names, and reserved parameter names. The conventions followed are:


| Keywords : Parameter names : Macro names : Reserved parameter names : | all lower case first letter in lower case first letter in upper case first letter in upper case |
| --- | --- |


## Input file example (INP format)

The following is an example input file for Rietveld refinement of corundum and fluorite:


| ‘ Rietveld refinement comprising two phases xdd File_Name.xy CuKa5(0.001)                           ‘ Emission profile Radius(217.5)                          ‘ Diffractometer radius LP_Factor(26.4)                        ‘ Lorentz polarization Slit_Width(0.1)                        ‘ Receiving slit width Divergence(1)                          ‘ Equatorial divergence Full_Axial_Model(12, 15, 12, 2.3, 2.3) ‘ Axial divergence Zero_Error(@, 0)               bkg @ 0 0 0 0 0 0 STR(R-3C, "Corundum Al2O3") Trigonal(@ 4.759, @ 12.992) site Al x 0         y 0  z @ 0.3521  occ Al+3 1  beq @ 0.3 site O  x @ 0.3062  y 0  z   0.25    occ O-2  1  beq @ 0.3 scale @ 0.001 CS_L(@, 100) r_bragg 0 STR(Fm-3m, Fluorite) Cubic(@ 5.464) site Ca    x 0      y 0     z 0      occ Ca 1   beq @ 0.5 site F     x 0.25   y 0.25  z 0.25   occ F  1   beq @ 0.5 scale @ 0.001 CS_L(@, 100) r_bragg 0 |
| --- |

The format is case sensitive. Optional indentation can be used to indicate tree dependencies, though the placement of keywords within a tree level is otherwise unimportant. For example, the keyword str signifies that all information occurring between it and the next keyword of the same type belongs to that str. All input text streams support line and block comments. A line comment begins with ' and runs to the end of the line; a block comment is delimited by /* and */ and may be nested. For example:


| ‘ This is a line comment space_group C2/c ‘ This is also a line comment /* This is a block comment. A block comment can comprise any number of lines. */ |
| --- |


## Test examples

The test_examples directory contains examples that can serve as templates for creating INP files. Charge-flipping examples are in the cf directory and indexing examples in the indexing directory.


## TC-INPS.BAT and the aac$ macro

The batch file tc-inps.bat runs over 180 test examples in a few minutes and plays an important role in program testing. Arguments passed via the command line can contain the aac$ macro, which, if defined, is expanded at the bottom of the INP file. For example, to terminate refinement after 100 iterations:

tc test_examples\pdf\alvo4\rigid "macro aac$ { iters 100 verbose 0 }"


## TOPAS is 64 bit

The command line tc.exe and the GUI ta.exe both run on the Windows 64-bit operating system.
