'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
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
		return list(['w', 'h', 'f', 'Eb', 'Eev', 'Er', 'Ra', 'Rb', 'Rc', 'Rd', 'Re', 'Va', 'Vb', 'Vc', 'Vd', 'Vx', 'Vy', 'a', 'b', 'c', 'd', 'e', 'g', 'p', 'r', 't', 'v', 'y', 'Vm', 'u', 'n'])
	
	def key_variables(self):
		return set()
	def int_variables(self):
		return set(['w', 'h', 'f', 'g', 't', 'Vm', 'u'])
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

	def get_name(self):
		return self.get_variable('n')

	def x(self):
		return self.get_variable('x')
		
	def y(self):
		return self.get_variable('y')

	def get_index(self):
		i = 0
		for line in self.project.image_lines:
			if line is self:
				return i
			i += 1

	def get_image(self):
		if self.image is None:
			self.image = PImage.from_file(self.get_name())
		return self.image

