# GUI Functionality


## TOPAS is DPI aware

Monitors with a high number of Dots Per Inch (DPI), often display text that are too small. Windows can scale fonts using Windows font scaling to enlarge text. This scaling is carried through to TOPAS where fonts and bitmaps scale to the required size. Additionally, a thicker-text option ("Segoe UI Semibold") can be enabled if the TOPAS text appears too thin. The option is saved for subsequent TOPAS loads and is enabled/disabled from the View menu:


## Antialiasing and OpenGL

Enable Antialiasing on your graphics card to display smooth lines in OpenGL; this affects all OpenGL displays. Depending on the graphics card, Antialiasing can also be enabled in a program-specific manner.


## Scan-window viewing operations


|  | Operation |
| --- | --- |
| Mouse-Wheel | Scroll plots left/right |
| Shift Mouse-Wheel | Compress/expand x-axis |
| LMB forwards rectangle | Zoom |
| LMB backwards rectangle | Unzoom |
| LMB forwards/backwards rectangle towards 1st and 3rd quadrants | Change start/end of x-axis window depending on proximity to window limits. |
| RMB click | Context menu |
| RMB down and scroll | Panning, similar to scrolling using mouse wheel |
| LMB click on hkl tick mark or tick mark row | Highlight all tick marks from same phase. Display associated phase. |
| Mouse close to tick mark | Show hkl and d-spacing on screen |
| Mouse close to phase line | Highlights phase and associated tick marks. |


## Selecting files for display using grep regular expressions

Grep regular expressions can be used to simplify the selection of scans for display; this is useful when there are many patterns loaded. Grep can be accessed through the “Global/Filter scans for display” option in the TreeView pane as seen in the following:

In the above, every 100th scan is displayed using the regular expression of “_[1-9]00”.


## gui_text keyword now ignored by the kernel


| XDD(ceo2)    CuKa5(0.0001)     Full_Axial_Model(12, 20, 12, 5.1, sl 5)    Radius(173)    LP_Factor(17)    Divergence(1)    Slit_Width(0.1)    bkg  @ 0 0 0 0 0    Zero_Error(@, 0)    gui_text {       prm b0 0       prm b1 0       fit_obj = b0 + b1 (X2-X1) / 2;    }    str                space_group F_M_3_M       scale @ 0.001       Cubic(@ 5.410)        site Ce1                       occ Ce+4 1 beq 1       site O1  x 0.25 y 0.25 z 0.25  occ O-2  1 beq 1       CS_L(@, 100)       MVW(0,0,0) |
| --- |


## Displaying a phase with and without background

Phases can be plotted with or without background by cycling through the three states of the phase-display icon.


## How atoms are displayed in OpenGL

Atoms colours and radii are defined in the files ATOM_COLORS.DEF and ATOM_RADIUS.DEF respectively. A site defined as:

| site S1 occ S 1 beq 1 |
| --- |

will be displayed as a Sulphur atom. If the Site Name, minus the numbers, is not found in ATOM_COLOURS.DEF then the atom type defined at the first site occupancy is used. Thus, a site defined as:


| site S1 occ Al+3 1 beq 1 |
| --- |


| site _S1 occ Al+3 1 beq 1 |
| --- |

will be displayed as an Aluminium atom.


## Tracking atomic movements graphically


| [str…] [track_buffer !E]  [site… track !E] | Examples test_examples\alvo4a.inp |
| --- | --- |

Atomic movements can be tracked using the site dependent keyword track. For example, the following:


| site AL1 … track = Mod(Cycle_Iter, 2) == 0; |
| --- |

will store the Al1 site position every second iteration. Doing this for every site in AlVO4 produces:


## x_calculation_step deleted when constant x-axis step size detected

*.XY and *.XYE data files are converted to a constant x-axis step size when a constant step size is detected. When this occurs Version 7 removes the “Calc.Step” item from the GUI menus for the corresponding data file. A small calculation step size can still be used by increasing “Conv. Steps”. PRO files containing an x_calculation_step will still show an entry of x_calculation_step.


## hide_peak_sticks

A GUI option that toggles the display of peak sticks in the scan window; the option can be found at the Peaks phase level as follows:


## User defined phase colour, line width and point size (_clp)


| _clp #red #green #blue #line_width #point_size | Examples test_examples\zro2.inp |
| --- | --- |

The colour, line width and data point size of phase plots can be entered in INP files using the phase or bkg dependent keyword _clp. The first three numbers correspond to red, green and blue colour weightings with value ranging between 0 and 1. #line_wdith and #point_size can be between 0 and 15. The file colours.inc contains standard colours. Example usage is as follows:


| #include colours.inc bkg … _clp 0.5 0.5 0.5 3 2 ‘ Grey with a line width of 3 and a data point size of 2 str… _clp 0.2 0.2 1 1 0   ‘ Blueish with a line width of 1 and a data point size of 0 	fit_obj !fs  = 1000 X;  Plot_Fit_Obj(fs, Some_bkg) 	_clp Blue 2 2 ‘ Blue colour from colours.inc |
| --- |


## Highlighting/displaying phases and hkl tick marks

Displaying phase names on the right of the plot window and moving the mouse over the phase name.

Clicking on the row of the hkl tick marks. This displays the associated phase and tick marks highlighted, for example:

If individual phases are displayed using , then moving the mouse over the pattern highlights the pattern as well as ticks marks associated with the phase.

If there are too many tick rows, then the program displays all phase ticks from all patterns in one row. Moving the mouse close to a tick mark, displays tick mark information on the screen as well as displaying the associated range name on the status bar. Additionally, clicking the left mouse button on a phase tick mark, highlights all tick marks associated with that phase and displays the phase pattern highlighted; for example: hkl tick marks are also now displayed in 2D-Offset mode as seen in the following:

In 2D-offset mode, ticks marks from a particular pattern are placed on a common tick mark row. Clicking on an individual tick mark, highlights all ticks marks from the corresponding phase and highlights and displays the corresponding phase pattern. As in the non-2D-offset mode, a phase pattern and its associated tick marks are highlighted when the mouse is close to the phase pattern.


## TOF x-axis can be displayed as d-spacing, Q or tof

The x-axis of TOF data can be displayed as either tof, d-spacing or Q by cycling the x-axis button.


## Surface plots – 2D with offsets

This icon displays scans offset from one another, for example (see files in the directory test_examples\3d\):

The Quickzoom window is operational in all 2D-offset plots.

Pressing the Middle Mouse Button and moving the mouse changes the x and y offsets. This movement greatly assists in determining the curvature of the surface. The QuickZoom display is not offset allowing for two views of the same data.


### Display hkl ticks on Surface plots

hkl ticks with z-axis height can be displayed on surface plots as seen in the following for \test_examples\je-para\d8_02999_35_annotate_04.inp:

And in PlanView:


### hkl ticks are now corrected for zero errors

The display of hkl ticks in Surface or 1D plots are now corrected for th2_offset or transform_X. The corrected PlanView plot shown above, when uncorrected, looks like:


### Inserting peaks and identifying scans

Peaks can be inserted by pressing the Ctrl-Key and clicking the RMB. When the Ctrl key is pressed a solid circle is displayed on the scan closest to the mouse. The circle is coloured to match the scan lines and in addition the closest scan is displayed with a thickened line. Displayed at the bottom of the plot is the name of the scan as seen by the arrow below. Peaks as well as excluded regions move with the offsets.

When the Ctrl-Key is pressed the x and y axis values displayed on the status line are offset to match the closest scan. Similarly, when the “For LAM Cursor” option is selected the LAM cursor is changed to match the axis of the closest scan.


### 2D-offset Surface plots

2D-offset plots can be displayed as a 3D-Surface, for example:

These plots can be manipulated in real time; the 871 file test_examples\je-para\d8_02999.raw with over 4 million data points can be easily manipulated:

Pressing the Shift key whilst performing a Zoom (forming a box using the mouse) zooms into a region. Zooming in this manner deselects scans for display. An unzoom is performed by performing an Unzoom whilst holding down the Shift key. Colour schemes can be changed by using the Colours options:

Contour-Orange-15 looks like:


### 2D-offset Planview plots

Moving the y-offset such that it's at a maximum automatically produces a Planview; a Kaleidoscope colour scheme gives:

The Standard colour scheme gives:

Zooming gives:

Planview can also have x-axis offsets with line scans overlain:

These line scans can include the calculated and/or difference patterns as well as patterns for individual phases. Beneath the displayed line scans are their shadows. Colours are blended across scans as well as across the x-axis to sharpen images.


### OpenGL Surface plots

OpenGL surface plots can be displayed alongside 2D-offset plots:

The scans displayed in the chart area are displayed to the right as a surface plot. Use RMB on the surface plot for options; these are:

The OpenGL surface plot respects the 2D x-axis and y-axis display options. It is also aware of the QuickZoom window and scrolling. Scrolling can be performed from either the 2D or 3D displays using the Mouse Wheel. Navigation in the OpenGL window is as follows:

RMB-Pressed and moving zooms.

Pressing ‘x’ whilst rotating allows rotation around an axis vertical to the screen.

Pressing ‘y’ whilst rotating allows rotation around an axis horizontal to the screen.

Pressing ‘z’ whilst rotating allows rotation around an axis perpendicular to the screen.

Pressing the Mouse Wheel button (as opposed to rotating the mouse wheel) moves the object and hence the centre of rotation.

When the Mouse is close to the Left or Right borders of the OpenGL window then rotation is around an axis perpendicular to the computer screen. Very useful for positioning 3D objects.

Opening the OpenGL Text Dialog and clicking on the 3D surface writes text into the Text Dialog; this text comprises the names of the two files bordering the polygon that has been clicked and the average x and y values of the polygon.


### OpenGL – Weighted difference for colours

The RMB “Weight difference for colours” option displays colours corresponding to:

WtDiff = Abs(YobsYcalc) / Weighting


## Normalizing scans within a Scan Window

Displayed scans can be normalized using the option “Yobs Normalize” which is activated using the RMB on the Scan window. Normalizing scales displayed scans such that the maximum values of the displayed data are all equal. Normalizing is temporary and can be toggled on/off by executing the “Yobs Normalize”. The following shows scans normalized:


## Plotting phases above background

```
[fit_obj E [min_X !E] [max_X !E] ]...
    [fo_transform_X !E]
    [fit_obj_phase !E]
```

By default, phases are plotted on top of background where background comprises fit_obj’s+bkg. The xdd dependent gui_add_bkg and the fit_obj dependent fit_obj_phase can be used to change the defaults, for example,


| xdd ... gui_add_bkg !E fit_obj ... fit_obj_phase !E |
| --- |


## Plotting fit_objs

fit_obj’s can be plotted using the following macros:


| macro Plot_Fit_Obj(p, name) {    dummy_str       phase_name name       scale = p; } | macro Plot_Fit_Obj(name) {    dummy_str       phase_name name } |
| --- | --- |

See test_examples\voigt-approx\fit-obj.inp for example; i.e.


| xdd ... fit_obj !f1 = ... Plot_Fit_Obj(f1, “Fit Obj”) |
| --- |

Plotting is via a dummy_str with the scale parameter set to the name given to the fit_obj, which in this case is f1. At the plotting stage the dummy_str borrows the calculated pattern from the fit_obj. The scale parameter of the dummy_str has some intelligence built into it such that if scale is not a function of a fit_obj name then it will search the place of the item it is a function of for a calculated pattern. For example, in the following:


| xdd ... Plot_Fit_Obj(a, “Fit Obj”) fit_obj = a ... prm a ... |
| --- |

the ‘a’ parameter lives locally to the fit_obj as it is defined after the fit_obj. Defining the scale parameter of the dummy_str in terms of ‘a’ therefore allows the dummy_str to determine where to find the calculated pattern to display. In this way macros such as the PV macro can be used and plotted without having to define a name for the fit_obj, see test_examples\pvs.inp. Sometimes the fit_obj has no name and no parameter that belongs to it; instead of naming the fit_obj or rearranging prm definitions the second Plot_Fit_Obj macro can be used:


| xdd ...  fit_obj = ... Plot_Fit_Obj(“plot previously defined fit_obj”) |
| --- |

Here the fit_obj defined prior to Plot_Fit_Obj is plotted.


## Display of Normalized SigmaYobs^2

This icon displays normalized SigmaYobs2; useful for checking anomalies from VCT or XYE files; here’s an example:

The normalization is as follows:

SigmaYobs^2 displayed = SigmaYobs^2 Sum[ Yobs ] / Sum[ SigmaYobs^2]

This puts the display of SigmaYobs^2 on a similar scale to Yobs. For normal x-ray data SigmaYobs = Sqrt(Yobs) and hence nothing is done as the displayed plot would simply be equal to Yobs. On some data sets, TOF for example, the magnitude of SigmaYobs can be small; therefore, when refining on multiple data sets from different sources, the weighting schemes may need modification to give the desired weight to the data sets.


## Cumulative Chi2

A kernel operation that results in the following graphical display: Uses the weighting from the kernel which can be User defined or otherwise. SigmaYobs is used in the weighting if it exists. The Cumulative Chi2 is normalized to have the maximum intensity of Yobs within the display window. Data is obtained from the kernel; excluded regions are ignored as shown in the plot above. Tabs for Cumulative Chi2 has been included in the appropriate GUI tabs, i.e.


## Correlation Matrix display

A Correlation matrix window activated from the Fit Dialog; it operates in Launch and GUI modes. Example output is as follows:

Both the A-matrix and the correlation matrix include penalties/restraints depending on whether do_errors_include_penalties and/or do_errors_include_restraints are defined. The display of the matrix can be zoomed using Ctrl-MouseWheel, here’s an example:

MouseMove over the correlation matrix displays a Hint comprising the corresponding parameter name, value and error. Left Mouse button down and dragging translates the matrix.


## Fading a structure

The intensity of atom colours displayed in OpenGL can be adjusted using the Fade spin button of the OpenGL grid options, for example:


## Normals Plot

```
[normals_plot !E]...
    [normals_plot_min_d !E]
```

An OpenGL plot of lattice plane Normals with Normals lengths defined by normals_plot. For example:


| normals_plot = Abs(H * K + L^2) + 1; normals_plot_min_d 0.3 |
| --- |

normals_plot_min_d is optional; small values (ie. 0.1) could lead to millions of points and Users could blow up their computers. Here’s output from the test example clay.inp:

The slider in the plot is activated by clicking on the  button. This slider multiplies the length of the normals_plot equation before generating the surface. The exact formulation for the multiplications is as follows.

Definitions:

s = multiplier which has a value (not shown to the user) that varies from 0 and 1.

N = diffraction vector directions with lengths given by the normals_plot equation.

N = Sqrt(N . N) = magnitude of N

Nmax = maximum N

Before generating the shape, N is multiplied by:


| For s < 0.25 For 0.25 ≤ s < 0.5 For 0.5 < s ≤ 0.75 For 0.75 < s ≤ 1 | : ((N / Nmax)^(4*s)) * N max / N : ((N / Nmax)^(4*(0.5-s))) * Nmax / N : (4*(0.5-s)) * Nmax / N + (1-s) : (((4*(0.75-s)) + Nmax / N |
| --- | --- |


## Improvements to the Grid

Data can be sorted by double clicking on column headings. Sorting alternates between ascending and descending order. On leaving a grid, the column most recently sorted is remembered. On re-entry of that grid, the data is again sorted according to the saved state. A small < or > sign is displayed to the left of the column heading name. Sorting works for all grids that display data with rows that are similar in Type; i.e. Peak data, sites etc... Val and Error columns are sorted numerically. Hkls, F^2 and other obvious numeric columns are also sorted numerically. However, Min and Max are sorted using strings as they can be equations and hence their fields are strings.

CTRL-MouseWheel zooms/un-zooms the text of a grid.

MouseDownMouseMove for Panning.


## Mouse operation in OpenGL Graphics

First some definitions

LMB = Left Mouse Button

RMB = Right Mouse Button

MID = Mouse Wheel or Middle button on Laptops

MM = Mouse Moving

WM = Wheel moving

LMB-D = Left Mouse Button Down

RMB-D = Right Mouse Button Down

MW-D = Mouse Wheel Down

Image rotation/translation operations are:

LMB-D- MM rotates the image.

LMB-D- MM and quick release initiates continuous rotation.

LMD-D-MM on the first 10% of the viewport from the left, or, the last 10% from the right rotates around an axis perpendicular to the screen. This is another way of doing what Shift-LMB-D-MM does but without the need for keyboard input.

MW zooms in addition to the usual RMB-D-MM.

MID-D-MM translates the image in the plane of the screen.

Images are rotated around the centre of gravity (or centre of unit cell) unless there’s a change using the RMB-D options.
