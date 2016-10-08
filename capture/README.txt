01_octagon
Simple threshold test on an octagon

02_liner
Inkscape plugin test related to drawing a line on a polygon and trying to guess
the best polygon associated with it

03_polifier
think this was trying to guess polygons and put them into inkscape layers
idea was that user would be able to quickly sift out good matches from the layers
which would rank them by confidence

04_bestpoly
think this tried to take in some training data to better guess unknown polygons

05_momentum
problem: strong polygons may be subset of real shape we want due to
component crossing
goal: figure out ways to join to the larger target polygon

06_halfer
a problem of above was that some regions it was difficult to use canny edge
detector to find the lines because it was more of a texture difference than
a real line
this was to explore ways of detecting these "edges"



TODO:
-Revisit momentum.  Idea was to get all polygons and then connect polygons
based on guesses as to which polygons should be attached based on adjacent
polygon crossing
-Revisit liner.  This time have the lines cross polygon intersections
to give it a hint as to how the polygons should be joined
-Play with gridding the image to guess where 
-Eventually this will need to scale but don't worry about it for now
    -Tile based approach would be nice
 
