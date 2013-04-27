'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import math
from pr0ntools.stitch.image_coordinate_map import ImageCoordinateMap
import os
import sys
from pr0ntools.pimage import PImage

def print_debug(s = None):
	if False:
		print 'DEBUG: %s' % s

def calc_center(pto):
	pto.parse()
	
	xbar = 0.0
	ybar = 0.0
	n = len(pto.get_image_lines())
	for i in pto.get_image_lines():
		x = i.x()
		y = i.y()
		# first check that we have coordinates for all of the images
		if x is None or y is None:
			raise Exception('Require positions to center panorama, missing on %s', pt.get_image())
		xbar += x
		ybar += y
	xbar /= n
	ybar /= n
	return (ybar, xbar)

def image_fl(img):
	'''Get rectilinear image focal distance'''
	'''
	We have image width, height, and fov
	Goal is to find FocalLength
		Full )> = FOV
	    /|\
	   / | \
	  /  |  \
	 /   |FL \
	/    |    \
	-----------
	|--width--|
	
	tan(FoV / 2) = (size / 2) / FocalLength
	FocalLength = (size / 2) / tan(FoV / 2)
	'''
	# images can have flexible fov but pano is fixed to int
	print 'Width: %d, fov: %s' % (img.width(), str(img.fov()))
	if img.fov() is None or not (img.fov() > 0 and img.fov() < 180):
		raise Exception('Require valid fov, got %s' % (img.fov()))
	return (img.width() / 2) / math.tan(img.fov() / 2)

def center(pto):
	'''Center images in a pto about the origin'''
	'''
	Note the following:
	-c lines are relative to images, not absolute coordinates
	-i lines determinte the image position
	-an i line coordinate is from the center of an image
	'''
	dbg = False
	
	print 'Centering pto'
	pto.assert_uniform_images()
	# We require the high level representation
	pto.parse()
	
	if dbg:
		print 'lines old:'
		for i in range(3):
			il = pto.get_image_lines()[i]
			print il
		
		
	(ybar, xbar) = calc_center(pto)	
	print 'Center adjustment by x %f, y %f' % (xbar, ybar)
	# If they were already centered this should be 0
	for i in pto.get_image_lines():
		i.set_x(i.x() - xbar)
		i.set_y(i.y() - ybar)
	
	if dbg:
		print 'lines new:'
		for i in range(3):
			il = pto.get_image_lines()[i]
			print il
	#import sys
	#sys.exit(1)
	
	# Adjust pano crop if present
	pl = pto.get_panorama_line()
	if pl.get_crop():
		# FIXME: this math isn't right although it does seem to generally improve things...
		print 'Adjusting crop'
		refi = pto.get_image_lines()[0]
		print refi
		#iw = refi.width()
		#ih = refi.height()
		# Take the ratio of the focal distances
		pfl = image_fl(pl)
		ifl = image_fl(refi)
		scalar = pfl / ifl
		
		print 'Crop scalar: %f' % scalar
		
		pxbar = xbar * scalar
		l = pl.left() - pxbar
		r = pl.right() - pxbar
		pl.set_left(l)
		pl.set_right(r)
		
		pybar = ybar * scalar
		t = pl.top() - pybar
		b = pl.bottom() - pybar
		pl.set_top(t)
		pl.set_bottom(b)
		
	else:
		print 'No crop to adjust'
	
def anchor(pto, i_in):
	from pr0ntools.stitch.pto.variable_line import VariableLine
	
	'''anchor pto image number i or obj for xy'''
	if type(i_in) is int:
		i = pto.get_image(i_in)
	else:
		i = i_in
		
	def process_line(l, iindex):
		lindex = l.index()
		if lindex is None:
			raise Exception("Couldn't determine existing index")			
		#print '%d vs %d' % 
		# The line we want to optimize?
		#print '%d vs %d' % (lindex, iindex)
		if lindex == iindex:
			print 'Removing old anchor'
			l.remove_variable('d')
			l.remove_variable('e')
			print 'new line: %s' % l
		else:
			# more than likely they are already equal to this
			l.set_variable('d', lindex)
			l.set_variable('e', lindex)
	
	iindex = i.get_index()
	print 'Anchoring to %s (%d)' % (i.get_name(), iindex)
	closed_set = set()
	# Try to modify other parameters as little as possible
	# Modify only d and e parmaeters so as to not disturb lens parameters
	for l in list(pto.get_variable_lines()):
		# There is one line that is just an empty v at the end...not sure if it actually does anything
		lindex = l.index()
		if lindex is None:
			continue
		process_line(l, iindex)
		#print 'L is now %s' % l
		closed_set.add(lindex)
		# If we just anchored the line clean it out
		if l.empty():
			pto.variable_lines.remove(l)
	'''
	This could be any number of values if it was empty before
	'''
	for i in xrange(pto.nimages()):
		if not i in closed_set and i != iindex:
			print 'Index %d not in closed set' % i
			'''
			Expect this to be the old anchor, if we had one at all
			As a heuristic put it in its index
			If it was organized its in place
			if it wasn't who cares
			note that for empty project we will keep appending to the end
			'''
			v = VariableLine('v d%d e%d' % (i, i), pto)
			pos = min(i, len(pto.variable_lines))
			pto.variable_lines.insert(pos, v)
	
def center_anchor_by_de(pto):
	'''Centering technique that requires an already optimized project, limited use'''
	# I used this for experimenting with anchor choice with some pre-optimized projects
	
	# We require the high level representation
	pto.parse()
	(ybar, xbar) = calc_center(pto)

	print 'xbar: %f, ybar: %f, images: %d' % (xbar, ybar, len(pto.get_image_lines()))

	for i in pto.get_image_lines():
		x = i.x()
		y = i.y()
		# since from center we want "radius" not diameter
		xd = abs(x - xbar)
		xref = i.width() / 2.0
		yd = abs(y - ybar)
		yref = i.height() / 2.0
		#print 'x%d, y%d: %f <= %f and %f <= %f' % (x, y, xd, xref, yd, yref)
		if xd <= xref and yd <= yref:
			# Found a suitable anchor
			#anchor(pto, i.get_index())
			anchor(pto, i)
			return
			
	raise Exception('Center heuristic failed')

def center_anchor_by_fn(pto):
	'''Rely on filename to make an anchor estimate'''
	pto.parse()
	m = ImageCoordinateMap.from_tagged_file_names(pto.get_file_names())
	# Chose a decent center image
	fn = m.get_image(int(m.width() / 2), int(m.height() / 2))
	print 'Selected %s as anchor' % fn
	anchor(pto, pto.get_image_by_fn(fn))

def center_anchor(pto):
	'''Chose an anchor in the center of the pto'''
	from pr0ntools.stitch.pto.variable_line import VariableLine

	'''
	There is a "chicken and the egg" type problem
	We want to figure out where the panorama is centered to optimize its positions nicely
	but typically don't know positions until its optimized
	
	If it is already optimized we can 
	'''
	
	print 'Centering anchor'

	if 0:
		return center_anchor_by_de(pto)
	else:
		return center_anchor_by_fn(pto)

def optimize_xy_only(self):
	# XXX: move this to earlier if possible
	from pr0ntools.stitch.pto.variable_line import VariableLine
	'''
	NOTE:
	Hugin uses the line:
	#hugin_optimizeReferenceImage 54
	But PToptimizer only cares about the v variables, or at least as far as i can tell
	
	Added by pto_merge or something
	v Ra0 Rb0 Rc0 Rd0 Re0 Vb0 Vc0 Vd0
	v Eb1 Eev1 Er1
	v Eb2 Eev2 Er2
	v Eb3 Eev3 Er3
	v
	
	
	Need something like (assume image 0 is anchor)
	v d1 e1 
	v d2 e2 
	v d3 e3 
	v 

	
	After saving, get huge i lines
	#-hugin  cropFactor=1
	i w2816 h2112 f-2 Eb1 Eev0 Er1 Ra0 Rb0 Rc0 Rd0 Re0 Va1 Vb0 Vc0 Vd0 Vx-0 Vy-0 a0 b0 c0 d-0 e-0 g-0 p0 r0 t-0 v51 y0  Vm5 u10 n"x00000_y00033.jpg"
	'''
	print_debug('Fixing up v (optimization variable) lines...')
	if self.parsed:
		self.variable_lines = []
		for i in range(1, len(self.get_file_names())):
			line = 'v d%d e%d \n' % (i, i)
			self.variable_lines.append(VariableLine(line, self))
		return
		
	new_project_text = ''
	new_lines = ''
		
	# This gives us "something" but more than likely
	# code later will run a center rountine to place this better
	for i in range(1, len(self.get_file_names())):
		# optimize d (x) and e (y) for all other than anchor
		new_lines += 'v d%d e%d \n' % (i, i)
	new_lines += 'v \n'
	for line in self.get_text().split('\n'):
		if line == '':
			new_project_text += '\n'				
		elif line[0] == 'v':
			# Replace once, ignore others
			new_project_text += new_lines
			new_lines = ''
		else:
			new_project_text += line + '\n'
	self.set_text(new_project_text)
	if 0:
		print
		print
		print_debug(self.text)
		print
		print

"""
def optimize_xy_only_for_images(pto, image_fns):
	'''Same as above except only for specific images'''
	for fn in image_fns:
"""
		

def fixup_p_lines(self):
	'''
	f0: rectilinear
	f2: equirectangular
	# p f2 w8000 h24 v179  E0 R0 n"TIFF_m c:NONE"
	# p f0 w8000 h24 v179  E0 R0 n"TIFF_m c:NONE"
	'''
	print 'Fixing up single lines'
	new_project_text = ''
	for line in self.get_text().split('\n'):
		if line == '':
			new_project_text += '\n'				
		elif line[0] == 'p':
			new_line = ''
			for part in line.split():
				if part[0] == 'p':
					new_line += 'p'
				elif part[0] == 'f':
					new_line += ' f0'
				else:
					new_line += ' ' + part

			new_project_text += new_line + '\n'
		else:
			new_project_text += line + '\n'
	self.set_text(new_project_text)
	if 0:
		print
		print
		print self.text
		print
		print

def fixup_i_lines(self):
	print 'Fixing up i (image attributes) lines...'
	new_project_text = ''
	new_lines = ''
	for line in self.get_text().split('\n'):
		if line == '':
			new_project_text += '\n'				
		elif line[0] == 'i':
			# before replace
			# i Eb1 Eev0 Er1 Ra0.0111006880179048 Rb-0.00838561356067657 Rc0.0198899246752262 Rd0.0135543448850513 Re-0.0435801632702351 Va1 Vb0.366722181378024 Vc-1.14825880321425 Vd0.904996105280657 Vm5 Vx0 Vy0 a0 b0 c0 d0 e0 f0 g0 h2112 n"x00000_y00033.jpg" p0 r0 t0 v70 w2816 y0
			new_line = ''
			for part in line.split():
				if part[0] == 'i':
					new_line += part
					# Force lense type 0 (rectilinear)
					# Otherwise, it gets added as -2 if we are unlucky ("Error on line 6")
					# or 2 (fisheye) if we are lucky (screwed up image)
					new_line += ' f0'
				# Keep image file name
				elif part[0] == 'n':
					new_line += ' ' + part
				elif part[0] in 'whv':
					new_line += ' %s' % part
				# Script is getting angry, try to slim it up
				else:
					print 'Skipping unknown garbage: %s' % part
			new_project_text += new_line + '\n'
		else:
			new_project_text += line + '\n'
	self.set_text(new_project_text)
	if 0:
		print
		print
		print self.text
		print
		print

def make_basename(pto):
	'''Convert image file names to their basenames'''
	for il in pto.get_image_lines():
		orig = il.get_name()
		new = os.path.basename(orig)
		if orig != new:
			print '%s => %s' % (orig, new)
		il.set_name(new)

def resave_hugin(pto):
	from pr0ntools.stitch.merger import Merger
	from pr0ntools.stitch.pto.project import PTOProject
	
	# pto_merge -o converted.pto out.pto out.pto
	blank = PTOProject.from_blank()
	m = Merger([blank])
	m.pto = pto
	new = m.run(to_pto=True)
	if new != pto:
		raise Exception('Expected self merge')
	print 'Merge into self'

def calc_il_dim(il):
	name = il.get_name()
	pimage = PImage.from_file(name)
	il.set_width(pimage.width())
	il.set_height(pimage.height())

def fixup_image_dim(pto):
	for il in pto.get_image_lines():
		calc_il_dim(il)
		print 'With size info: %s' % il


