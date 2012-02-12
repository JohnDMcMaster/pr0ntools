'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
It seems width and heigth must be set to actual image width and heigh, ie can't be used for scaling like on the p line
Changing in source file, opening in Hugin, re-saving puts back the old values
Hugin doesn't seem to do anything different rendering the images if they are truncated either
It is possible nona does differently but I haven't tried


http://search.cpan.org/~bpostle/Panotools-Script/lib/Panotools/Script/Line/Image.pm

  w1000
  h500     nona requires the width and height of input images wheras PTStitcher/mender don't

  f0           projection format,
                   0 - rectilinear (normal lenses)
                   1 - Panoramic (Scanning cameras like Noblex)
                   2 - Circular fisheye
                   3 - full-frame fisheye
                   4 - PSphere, equirectangular
                   7 - Mirror (a spherical mirror)
                   8 - Orthographic fisheye
                  10 - Stereographic fisheye
                  21 - Equisolid fisheye

  v82          horizontal field of view of image (required)
  y0           yaw angle (required)
  p43          pitch angle (required)
  r0           roll angle (required)
  a,b,c        lens correction coefficients (optional)
                   (see http://www.fh-furtwangen.de/~dersch/barrel/barrel.html)
  d,e          initial lens offset in pixels(defaults d0 e0, optional).
                   Used to correct for offset from center of image
                   d - horizontal offset,
                   e - vertical offset
  g,t          initial lens shear.  Use to remove slight misalignment
                   of the line scanner relative to the film transport
                   g - horizontal shear
                   t - vertical shear
  j            stack number

  Eev          exposure of image in EV (exposure values)
  Er           white balance factor for red channel
  Eb           white balance factor for blue channel

  Ra           EMoR response model from the Computer Vision Lab at Columbia University
  Rb           This models the camera response curve
  Rc
  Rd
  Re

  TiX,TiY,TiZ  Tilt on x axis, y axis, z axis
  TiS           Scaling of field of view in the tilt transformation

  TrX,TrY,TrZ  Translation on x axis, y axis, z axis

  Te0,Te1,Te2,Te3  Test parameters

  Vm           vignetting correction mode (default 0):
                   0: no vignetting correction
                   1: radial vignetting correction (see j,k,l,o options)
                   2: flatfield vignetting correction (see p option)
                   4: proportional correction: i_new = i / corr.
                        This mode is recommended for use with linear data.
                        If the input data is gamma corrected, try adding g2.2
                        to the m line.

                       default is additive correction: i_new = i + corr

                     Both radial and flatfield correction can be combined with the
                      proportional correction by adding 4.
                  Examples: i1 - radial polynomial correction by addition.
                                  The coefficients j,k,l,o must be specified.
                            i5 - radial polynomial correction by division.
                                  The coefficients j,k,l,o must be specified.
                            i6 - flatfield correction by division.
                                  The flatfield image should be specified with the p option

  Va,Vb,Vc,Vd  vignetting correction coefficients. (defaults: 0,0,0,0)
                ( 0, 2, 4, 6 order polynomial coefficients):
                 corr = ( i + j*r^2 + k*r^4 + l*r^6), where r is the distance from the image center
               The corrected pixel value is calculated with: i_new = i_old + corr
               if additive correction is used (default)
                           for proportional correction (h5): i_new = i_old / corr;

  Vx,Vy        radial vignetting correction offset in pixels (defaults q0 w0, optional).
                  Used to correct for offset from center of image
                   Vx - horizontal offset
                   Vy - vertical offset

  S100,600,100,800   Selection(l,r,t,b), Only pixels inside the rectangle will be used for conversion.
                        Original image size is used for all image parameters
                        (e.g. field-of-view) refer to the original image.
                        Selection can be outside image dimension.
                        The selection will be circular for circular fisheye images, and
                        rectangular for all other projection formats

  nName        file name of the input image.

  i f2 r0   p0    y0     v183    a0 b-0.1 c0  S100,600,100,800 n"photo1.jpg"
  i f2 r0   p0    y180   v183    a0 b-0.1 c0  S100,600,100,800 n"photo1.jpg"
'''

import os
import shutil
from pr0ntools.pimage import PImage
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.execute import Execute
import line

# I'm really tempted to write this as a map...but I dunno
class ImageLine(line.Line):
	'''
	#-hugin  cropFactor=6.05334
	i w2816 h2112 f0 Eb1 Eev0 Er1 Ra0 Rb0 Rc0 Rd0 Re0 Va1 Vb0 Vc0 Vd0 Vx0 Vy0 a0 b-0.01 c0 d0 e-964.732609921273 g0 p0 r90 t0 v18.6619860596508 y12  Vm5 u10 n"data/c0_r0.jpg"
	
	i w3264 h2448 f0 v51 Ra0 Rb0 Rc0 Rd0 Re0 Eev0 Er1 Eb1 r0 p0 y0 TrX0 TrY0 TrZ0 j0 a0 b0 c0 d-0 e-0 g-0 t-0 Va1 Vb0 Vc0 Vd0 Vx-0 Vy-0  Vm5 n"c0000_r0000.jpg"
		where did TrX,.. entries come from?
	
	to script creation
	"i w h f Eb Eev Er Ra Rb Rc Rd Re Va Vb Vc Vd Vx Vy a b c d e g p r t v y Vm u n".split()
	'''
	
	# Parameters that I don't feel like tracking or haven't seen
	#other = map()
	
	"""
	# nona requires the width and height of input images wheras PTStitcher/mender don't
	# Width, int
	w = None
	# Height, int
	h = None
	# f0           projection format,
	# 0 - rectilinear (normal lenses)
	f = None
	
	# Photometrics
	# Eb           white balance factor for blue channel
	Eb = None
	# Eev          exposure of image in EV (exposure values)
	Eev = None
	# Er           white balance factor for red channel
	Er = None

	# EMoR photometrics
	# ?, int
	Ra = None
	# ?, int
	Rb = None
	# ?, int
	Rc = None
	# ?, int
	Rd = None
	# ?, int
	Re = None

	# Vignetting
	# ?, int
	Va = None
	# ?, int
	Vb = None
	# ?, int
	Vc = None
	# ?, int
	Vd = None
	# ?, int
	Vx = None
	# ?, int
	Vy = None
	
	# a,b,c        lens correction coefficients (optional)
	# ?, int
	a = None
	# ?, signed with decimal
	b = None
	# ?, int
	c = None

	# d,e          initial lens offset in pixels(defaults d0 e0, optional).
	# These are the center of the image (as opposed to, say upper left)
	# ?, int
	d = None
	# ?, signed with decimal
	e = None

	# g,t          initial lens shear.  Use to remove slight misalignment
	# ?, int
	g = None
	# ?, int
	t = None

	# j            stack number

	# p43          pitch angle (required)
	p = None
	# r0           roll angle (required)
	r = None
	# v82          horizontal field of view of image (required)
	'''
	http://hugin.sourceforge.net/tutorials/scans/en.shtml
	We don't know the FOV (Field of view) of this imaginary camera,
	but it doesn't matter since the picture is the same regardless
	(setting any mid-range value between 5 and 40 degrees would
	probably be ok). Just enter 10 in the HFOV(v)	
	'''
	v = None
	# y0           yaw angle (required)
	y = None
	# ?, int
	Vm = None
	# ?, int
	u = None
	# Image file name
	n = None
	
	# Entire line
	text = None
	"""

	def __init__(self, text, project):
		line.Line.__init__(self, text, project)
		self.image = None
		
	def prefix(self):
		return 'i'
		
	def variable_print_order(self):
		# i w2816 h2112 f0 Eb1 Eev0.463243792953809 Er1 Ra0 Rb0 Rc0 Rd0 Re0 Va1 Vb0.460215357389621 Vc-0.596925841345566 Vd0.120459501533104 Vx-0 Vy-0 a0 b0 c0 d-0 e-0 g-0 p0 r0 t-0 v51 y0  Vm5 u10 n"x00022_y00339.jpg"
		return list(['w', 'h', 'f', 'Eb', 'Eev', 'Er', 'Ra', 'Rb', 'Rc', 'Rd', 'Re', 'Va', 'Vb', 'Vc', 'Vd', 'Vx', 'Vy', 'j', 'a', 'b', 'c', 'd', 'e', 'g', 'p', 'r', 't', 'v', 'y', 'TrX', 'TrY', 'TrZ', 'Vm', 'u', 'n'])
	
	def key_variables(self):
		return set()
	def int_variables(self):
		return set(['w', 'h', 'f', 'g', 't', 'Vm', 'u', 'TrX', 'TrY', 'TrZ', 'j'])
	def float_variables(self):
		return set(['Eb', 'Eev', 'Er', 'Ra', 'Rb', 'Rc', 'Rd', 'Re', 'Va', 'Vb', 'Vc', 'Vd', 'Vx', 'Vy', 'a', 'b', 'c', 'd', 'e', 'p', 'r', 'v', 'y'])
	def string_variables(self):
		return set(['n'])
		
	@staticmethod
	def from_line(line, pto_project):
		ret = Image()
		ret.text = line
		ret.reparse()
		return ret

	'''
	In short upper left is the positive quadrant..no idea why this convention was adapted
		Did I flip some variable somewhere?  Like I should use a negative fov?
	Higher y moves the image up on the screen
	Higher x moves the image left on the screen
	'''
	
	def shift(dx, dy):
		self.set_x(self.x() + dx)
		self.set_y(self.y() + dy)

	def set_x(self, x):
		self.set_variable('d', x)
	
	def set_y(self, y):
		self.set_variable('e', y)

	def get_name(self):
		return self.get_variable('n')
	
	def set_name(self, name):
		return self.set_variable('n', name)

	def make_absolute(self, to):
		'''Make image path absolute.  Location is assumed to be working dir unless otherwise specified'''
		if to is None:
			to = os.getcwd()
		path = to + "/" + os.path.basename(self.get_name())
		#print 'Making absolute image name: %s' % path
		self.set_name(path)
		
	def make_relative(self, to):
		'''Make image path relative'''
		if to is None:
			to = ''
		else:
			to = to + '/'
		self.set_name(to + os.path.basename(self.get_name()))

	def left(self):
		return self.x() - self.width() / 2.0
		
	def right(self):
		return self.x() + self.width() / 2.0

	def top(self):
		return self.y() - self.height() / 2.0
		
	def bottom(self):
		return self.y() + self.height() / 2.0
	
	def x(self):
		'''Center of image x position'''
		return self.get_variable('d')
		
	def y(self):
		'''Center of image y position'''
		return self.get_variable('e')

	def width(self):
		return self.get_variable('w')

	def height(self):
		return self.get_variable('h')
		
	def fov(self):
		'''Returns angle (field) of view in degrees'''
		return self.get_variable('v')			
		
	def get_index(self):
		i = 0
		for line in self.project.image_lines:
			if line is self:
				return i
			i += 1
		raise Exception('Image is no in panorama')

	def get_image(self):
		if self.image is None:
			self.image = PImage.from_file(self.get_name())
		return self.image

