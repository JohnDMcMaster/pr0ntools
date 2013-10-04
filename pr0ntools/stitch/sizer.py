'''
pr0ntools
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
This file aims to provide the ability to resize a panorama to fit optimal xy size

p line options are:
-v: FOV
	Corresponds to horizontal FOV in Hugin
-w: width
-h: height

I believe the parameters are related as following:
-fov specifies how much of the full image is avilible
	For rectilinear 180 is probably the max
	In particular it is cone of view, not separate vertical and horizontal FOV?
		There is only a v option, not separate
FOV is combined with the panorama width and height to determine the visible area
	Presumably it expands to fill the maximum availible, shrinking the maximum dimension shrinks the availible FOV


Doubling an individual image's FOV from 51 to 102 increased its size considerably
Setting project FOV v equal to an image FOV makes the image take up the entire width


hor: 104
vert: 86
Crop:
	S2304,6850,1640,5130
	left: 2304
	top: 1640
	right: 6850
	bottom: 5130
	


Playing with FOV in Hugin
FOV is directly proportional to optimal size for both width and height with the same scalar
In my project 1 FOV = 

'''

