Plugin for calculating path loss between antenna and road.

Explanation of GUI:
Input file must be on .TIFF-format. When a file is selected, the result is written to file. If no file is selected, the layer is saved in memory. Meomory saved files will disappear from the screen if the canvas is zoomed. Therefore, it is recommended to choose a file for saving the results.

When the calculations are complete, default styles can be applied to visualise the results. These can be found in the Hybriddekning-folder.

Option Calculate signal:
Input must be the following:
-Terrain raster and surface raster. These should overlap. 
-Antenna layer. One or more antennas with the following attributes: ID (integer), Frequency in MHz (integer), Height above ground in meters (integer)
-Road layer. IMPORTANT: One or more links must be selected. The calculations will be done for selected links only.

The calculations will be done for each antenna visible in the Canvas. Therefore, a proper zoom level should be chosen. The calculations are time consuming for large areas. If in doubt, select a smaller area.

Option Optimize:
Inout must be following:
-Surface raster
-Road layer. IMPORTANT: One or more links must be selected. The calculations will be done for selected links only.

Very time consuming method. Not thoughourly tested. Use with care.


Option plot height profile:
Input must be the following:
-Raster 
-Point layer. Layer must have exactly two points.

A height profile between the two points is drawn, based on heights sampled from the rasterfile.

