# Automatic phase identification as samples are measured on diffractometer

## General instructions for TOPilot examples
1. Forget any previous work you've done on this example and start from scratch.
1. Use the minimum number of prompts this session, allow anything you can.  
1. Don't look at other files on this computer which may have previous examples of the problem.
1. Don't look on the internet for specific earlier examples of this problem.

## Information auto-extracted from diffractometer logbook

| Data file | Structure believed present | Fit range |
|---|---|---|
| d7_29050_EgyptianBlue.raw | Egyptian_Blue.cif | 10-70 |
| d7_29051_HanBlue.raw | Han_Blue.cif | 10-70 |
| d7_29052_HanPurple.raw | Han_Purple.cif | 10-70 |

## Specific instructions for this example

1. This is an automatic pipeline for checking the id of phases present in datafiles measured on the diffractometer.
1. Use Rietveld analysis but there is no need to do a structure refinement unless you think necessary (e.g. no coordinate refinement needed)
1. The data filenames and cif files of structures expected to be present are in the table above.
1. Data were collected on a diffractomer with Cu Ka1/Ka2 radiation and no monochromator.   
1. Please check if each pattern contains the expected phase.  Suggest any issues across the series.
1. Create the main inp files in this directory and open as soon as possible. 
1. Store other files in a folder pigment_workings.


