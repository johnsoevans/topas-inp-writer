# Find modulation vector

1. d7_06306.raw was recorded on an incommensurate material using Cu Ka2 rediation and variable divergence slits.
1. The strong peaks can all be described with a tetragonal unit cell with space group P4/nmm and cell parameters of a = 4.01 and c = 9.11 Angstroms.
1. There is a known impurity peak at around 28.75 degrees 2-theta.  I suggest excluding 28.5 to 29.0 from the fit.  There is significant background scatter below 8.5 degrees so I suggest using 8.5 to 50 degrees for the analysis.
1. Can you determine the modulation vector from the weak satellite peaks?  Try simple directions first then more complex ones. 
1. Just use information in the skill and don't look for previous examples of this specific material on this computer or on the internet.  Do not read any cif file in this directory.

# Set up X+N Rietveld fit

1. Based on this modulation vector I have used ISODISTORT to produce the cif file cefe0.5ose_01_q_0.08_0.08_0.5_s4_Cmma(a,0,0.5)0s0.cif.
1. I would like to try a combined Rietveld refinement against the X-ray data and a neutron powder diffraction pattern.  Only first order satellite reflections are observed.
1. The neutron data were collected on the GEM diffractometer.
1. The GEM instrument scientist suggested the following peak shape parameters and instrumental constants:
      wifd_mic_new(two_theta, =bank_two_theta;, !tspow, 2.75914,!tauf_0, 1.38544, !tauf_1, 1.05054, !taus_0, 0.02609, !taus_1, 0.01029, !t_eff, 233.59810, !hhh, 0.00257, !double_pulse, 0.01015) 
      TOF_x_axis_calibration(!t0_bank4,-2.6912, !difc_bank4, 4835.91, !difa_bank4,-0.7273`) 
      local !bank_two_theta 63.62 
1. Refine modulation amplitudes as allowed by symmetry.
1. Use a legendre approach for Mn occupancy modulation with a crenel center of 0.75 and width of 0.5.