#!/usr/bin/env python
'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools.execute import Execute
from pr0ntools.pimage import PImage
import sys


'''
Others
celeste_standalone 
ptscluster
cpclean

 
autooptimiser: optimize image positions
autooptimiser version 2010.0.0.5045

Usage:  autooptimiser [options] input.pto
   To read a project from stdio, specify - as input file.

  Options:
     -o file.pto  output file. If obmitted, stdout is used.

    Optimisation options (if not specified, no optimisation takes place)
     -a       auto align mode, includes various optimisation stages, depending
               on the amount and distribution of the control points
     -p       pairwise optimisation of yaw, pitch and roll, starting from
              first image
     -n       Optimize parameters specified in script file (like PTOptimizer)

    Postprocessing options:
     -l       level horizon (works best for horizontal panos)
     -s       automatically select a suitable output projection and size
    Other options:
     -q       quiet operation (no progress is reported)
     -v HFOV  specify horizontal field of view of input images.
               Used if the .pto file contains invalid HFOV values
               (autopano-SIFT writes .pto files with invalid HFOV)

   When using -a -l and -s options together, a similar operation to the "Align"
    button in hugin is performed.
'''

class PositionOptimizer:
	def __init__(self, pto_project):
		self.pto_project = pto_project
	
	def optimize(self):
		# "autooptimiser -n -o project.pto project.pto"
		args = list()
		args.append("-n")
		args.append("-o")
		args.append(pto_project.get_a_file_name())
		args.append(pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("autooptimiser", args)
		if not rc == 0:
			raise Exception('failed position optimization')
		self.project.reopen()

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
def prepare_pto(pto):
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
			if il.get_variable(v) == None:
				il.set_variable(v, 0)
				#print 'setting var'
	
	fix_pl(pto.get_panorama_line())
	
	for il in pto.image_lines:
		fix_il(il)
		#print il
		#sys.exit(1)
	
	if 1:
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
			print 'Found variable val to be %s' % str(val)
			il.set_variable(v, val)
			print 'New IL: ' + str(il)
		print
	
class PTOptimizer:
	def __init__(self, pto_project):
		self.pto_project = pto_project
	
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
		
		# Copy project so we can trash it
		project = self.pto_project.to_ptoptimizer()
		prepare_pto(project)
		
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
		(rc, output) = Execute.with_output("PToptimizer", args)
		print output
		if not rc == 0:
			print
			print
			print 'Failed output:'
			print output
			print
			print
			print
			print
			print 'Failed project:'
			print pre_run_text
			print
			print
			raise Exception('failed position optimization')
		# API assumes that projects don't change under us
		project.reopen()
		print 'Parsed: %s' % str(project.parsed)

		print
		print
		print
		print 'Optimized project:'
		print project
	 	#sys.exit(1)
	 	print 'Optimized project parsed: %d' % project.parsed

		print 'Merging project...'
		merge_pto(project, self.pto_project)
		print self.pto_project

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

