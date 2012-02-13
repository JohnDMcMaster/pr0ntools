#!/usr/bin/env python
'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
This file is used to optimize the size of an image project
It works off of the following idea:
-In the end all images must lie on the same focal plane to work as intended
-Hugin likes a default per image FOV of 51 degrees since thats a typical camera FOV
-With a fixed image width, height, and FOV as above we can form a natural focal plane
-Adjust the project focal plane to match the image focal plane


Note the following:
-Ultimately the project width/height determines the output width/height
-FOV values are not very accurate: only 1 degree accuracy
-Individual image width values are more about scaling as opposed to the total project size than their output width?
	Hugin keeps the closest 

A lot of this seems overcomplicated for my simple scenario
Would I be better off 

Unless I make the algorithm more advanced by correctly calculating all images into a focal plane (by taking a reference)
it is a good idea to at least assert that all images are in the same focal plane
'''

from pr0ntools.execute import Execute
from pr0ntools.pimage import PImage
from pr0ntools.stitch.pto.util import *
from pr0ntools.benchmark import Benchmark
import sys

def debug(s = ''):
	pass

'''
Convert output to PToptimizer form



http://wiki.panotools.org/PTOptimizer
	# The script must contain:
	# one 'p'- line describing the output image (eg Panorama)
	# one 'i'-line for each input image
	# one or several 'v'- lines listing the variables to be optimized.
	# the 'm'-line is optional and allows you to specify modes for the optimization.
	# one 'c'-line for each pair of control points



p line
	Remove E0 R0
		Results in message
			Illegal token in 'p'-line [69] [E] [E0 R0 n"PSD_mask"]
			Illegal token in 'p'-line [48] [0] [0 R0 n"PSD_mask"]
			Illegal token in 'p'-line [82] [R] [R0 n"PSD_mask"]
			Illegal token in 'p'-line [48] [0] [0 n"PSD_mask"]
	FOV must be < 180
		v250 => v179
		Results in message
			Destination image must have HFOV < 180
i line
	Must have FOV
		v51
		Results in message
			Field of View must be positive
	Must have width, height
		w3264 h2448
		Results in message
			Image height must be positive
	Must contain the variables to be optimized
		make sure d and e are there
		reference has them equal to -0, 0 seems to work fine



Converting back
Grab o lines and get the d, e entries
	Copy the entries to the matching entries on the original i lines
Open questions
	How does FOV effect the stitch?
'''
def prepare_pto(pto, reoptimize = True):
	'''Simply and modify a pto project enough so that PToptimizer will take it'''
	print 'Stripping project'
	if 0:
		print pto.get_text()
		print
		print
		print
	
	def fix_pl(pl):
		pl.remove_variable('E')
		pl.remove_variable('R')
		v = pl.get_variable('v') 
		if v == None or v >= 180:
			print 'Manipulating project field of view'
			pl.set_variable('v', 179)
			
	def fix_il(il):
		v = il.get_variable('v') 
		if v == None or v >= 180:
			il.set_variable('v', 51)

		if il.get_variable('w') == None or il.get_variable('h') == None:
			img = PImage.from_file(il.get_name())
			il.set_variable('w', img.width())
			il.set_variable('h', img.height())

		for v in 'd e'.split():
			if il.get_variable(v) == None or reoptimize:
				il.set_variable(v, 0)
				#print 'setting var'
	
	fix_pl(pto.get_panorama_line())
	
	for il in pto.image_lines:
		fix_il(il)
		#print il
		#sys.exit(1)
	
	if 0:
		print
		print	
		print 'prepare_pto final:'
		print pto
		print
		print
		print 'Finished prepping for PToptimizer'	
	#sys.exit(1)
			
def merge_pto(ptoopt, pto):
	'''Take a resulting pto project and merge the coordinates back into the original'''
	'''
	o f0 r0 p0 y0 v51 d0.000000 e0.000000 u10 -buf 
	...
	o f0 r0 p0 y0 v51 d-12.584355 e-1706.852324 u10 +buf -buf 
	...
	o f0 r0 p0 y0 v51 d-2179.613104 e16.748410 u10 +buf -buf 
	...
	o f0 r0 p0 y0 v51 d-2213.480518 e-1689.955438 u10 +buf 

	merge into
	

	# image lines
	#-hugin  cropFactor=1
	i f0 n"c0000_r0000.jpg" v51 w3264 h2448 d0 e0
	#-hugin  cropFactor=1
	i f0 n"c0000_r0001.jpg" v51 w3264 h2448  d0 e0
	#-hugin  cropFactor=1
	i f0 n"c0001_r0000.jpg" v51  w3264 h2448  d0 e0
	#-hugin  cropFactor=1
	i f0 n"c0001_r0001.jpg" v51 w3264 h2448 d0 e0
	
	note that o lines have some image ID strings before them but position is probably better until I have an issue
	'''
	
	# Make sure we are going to manipulate the data and not text
	pto.parse()
	
	base_n = len(pto.get_image_lines())
	opt_n = len(ptoopt.get_optimizer_lines())
	if base_n != opt_n:
		raise Exception('Must have optimized same number images as images.  Base pto has %d and opt has %d' % (base_n, opt_n))
	opts = list()
	print
	for i in range(len(pto.get_image_lines())):
		il = pto.get_image_lines()[i]
		ol = ptoopt.optimizer_lines[i]
		for v in 'd e'.split():
			val = ol.get_variable(v)
			debug('Found variable val to be %s' % str(val))
			il.set_variable(v, val)
			debug('New IL: ' + str(il))
		debug()
		
class PTOptimizer:
	def __init__(self, project):
		self.project = project
		self.debug = False
		# In practice I tend to get around 25 so anything this big signifies a real problem
		self.rms_error_threshold = 250.0
		# If set to true will clear out all old optimizer settings
		# If PToptimizer gets de values in it will use them as a base
		self.reoptimize = True
	
	def verify_images(self):
		first = True
		for i in self.project.get_image_lines():
			if first:
				self.w = i.width()
				self.h = i.height()
				self.v = i.fov()
				first = False
			else:
				if self.w != i.width() or self.h != i.height() or self.v != i.fov():
					raise Exception('Image %d does not match' % (i))
		
	def center_project(self):
		self.calc_bounds()
		xc = (self.xmin + self.xmax) / 2.0
		yc = (self.ymin + self.ymax) / 2.0
		for i in self.project.get_images():
			i.shift(xc, yc)
		
	def calc_bounds(self):
		# TODO: review pto coordinate system to see if this is accurate
		self.xmin = min([i.left() for i in self.project.get_images()])
		self.xmax = max([i.right() for i in self.project.get_images()])
		self.ymin = min([i.top() for i in self.project.get_images()])
		self.ymax = max([i.bottom() for i in self.project.get_images()])
		
	def calc_size(self):
		self.calc_bounds()
		self.width = xmax - xmin
		self.height = ymax - ymin
		
	def image_fl(self, img):
		return image_fl(img)
		
	def calc_v(self, fl, width):
		# Straight off of Hugin wiki (or looking above...)
		# FoV = 2 * atan(size / (2 * FocalLength))
		v = 2 * math.atan(width / (2 * fl))
		if 1:
			v = round(v)
			v = min(v, 179)
			v = max(v, 1)
		return v
		
	def calc_fov(self):
		'''
		Calculate the focal distance on a single image
		and then match the project to it using our net desired width and height
		'''
		# Step 1: calculate image focal length
		# Note that even if we had mixed image parameters they should already been normalized to be on the same focal plane
		self.fl = self.image_fl(self.project.get_images()[0])
		
		# Step 2: now use the focal distance to compute v, the angle (field) of view
		self.v = self.calc_v(self.fl, self.width)
		pl = self.project.get_panorama_line()
		pl.set_fov(self.v)
		
	def run(self):
		'''
		The base Hugin project seems to work if you take out a few things:
		Eb1 Eev0 Er1 Ra0 Rb0 Rc0 Rd0 Re0 Va1 Vb0 Vc0 Vd0 Vx-0 Vy-0
		So say generate a project file with all of those replaced
		
		In particular we will generate new i lines
		To keep our original object intact we will instead do a diff and replace the optimized things on the old project
		
		
		Output is merged into the original file and starts after a line with a single *
		Even Hugin wpon't respect this optimization if loaded in as is
		Gives lines out like this
		
		o f0 r0 p0 y0 v51 a0.000000 b0.000000 c0.000000 g-0.000000 t-0.000000 d-0.000000 e-0.000000 u10 -buf 
		These are the lines we care about
		
		C i0 c0  x3996.61 y607.045 X3996.62 Y607.039  D1.4009 Dx-1.15133 Dy0.798094
		Where D is the magnitutde of the distance and x and y are the x and y differences to fitted solution
		
		There are several other lines that are just the repeats of previous lines
		'''
		bench = Benchmark()
		
		# The following will assume all of the images have the same size
		self.verify_images()
		
		# Copy project so we can trash it
		project = self.project.to_ptoptimizer()
		prepare_pto(project, self.reoptimize)
		
		pre_run_text = project.get_text()
		if 0:
			print
			print
			print 'PT optimizer project:'
			print pre_run_text
			print
			print
				
		
		# "PToptimizer out.pto"
		args = list()
		args.append(project.get_a_file_name())
		#project.save()
		rc = Execute.show_output("PToptimizer", args)
		if not rc == 0:
			print
			print
			print 'Failed rc: %d' % rc
			print 'Failed project:'
			print pre_run_text
			print
			print
			raise Exception('failed position optimization')
		# API assumes that projects don't change under us
		project.reopen()
		
		'''
		Line looks like this
		# final rms error 24.0394 units
		'''
		rms_error = None
		for l in project.get_comment_lines():
			if l.find('final rms error') >= 00:
				rms_error = float(l.split()[4])
				break
		print 'Optimize: RMS error of %f' % rms_error
		# Filter out gross optimization problems
		if self.rms_error_threshold and rms_error > self.rms_error_threshold:
			raise Exception("Max RMS error threshold %f but got %f" % (self.rms_error_threshold, rms_error))
		
		if self.debug:
			print 'Parsed: %s' % str(project.parsed)

		if self.debug:
			print
			print
			print
			print 'Optimized project:'
			print project
		 	#sys.exit(1)
	 	print 'Optimized project parsed: %d' % project.parsed

		print 'Merging project...'
		merge_pto(project, self.project)
		if self.debug:
			print self.project
		
		bench.stop()
		print 'Optimized project in %s' % bench
		
		# These are beyond this scope
		# Move them somewhere else if we want them
		if 0:
			# The following will assume all of the images have the same size
			self.verify_images()
		
			# Final dimensions are determined by field of view and width
			# Calculate optimial dimensions
			self.calc_dimensions()
		
			print 'Centering project...'
			self.center_project()
		
			'''
			WARNING WARNING WARNING
			The panotools model is too advanced for what I'm doing right now
			The image correction has its merits but is mostly getting in the way to distort images
		
			Therefore, I'd like to complete this to understand the intended use but I suspect its not a good idea
			and I could do my own nona style program much better
			The only downside is that if / when I start doing lens model corrections I'll have to rethink this a little
		
			Actually, a lot of these problems go away if I trim to a single tile
			I can use the same FOV as the source image or something similar
			'''
			print 'Calculating optimial field of view to match desired size...'
			self.calc_fov()
			

def usage():
	print 'optimizer <file in> [file out]'
	print 'If file out is not given it will be file in'

if __name__ == "__main__":
	from pr0ntools.stitch.pto.project import PTOProject

	if len(sys.argv) < 2:
		usage()
		sys.exit(1)
	file_name_in = sys.argv[1]
	if len(sys.argv) > 2:
		file_name_out = sys.argv[2]
	else:
		file_name_out = file_name_in
	
	print 'Loading raw project...'
	project = PTOProject.parse_from_file_name(file_name_in)
	print 'Creating optimizer...'
	optimizer = PTOptimizer(project)
	#self.assertTrue(project.text != None)
	print 'Running optimizer...'
	print 'Parsed main pre-run: %s' % str(project.parsed)
	optimizer.run()
	print 'Parsed main: %d' % project.parsed
	print 'Saving...'
	project.save_as(file_name_out)
	print 'Parsed main done: %s' % str(project.parsed)

