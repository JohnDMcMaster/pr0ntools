#!/usr/bin/python
'''
pr0nstitch: IC die image stitching
Copyright 2010 John McMaster <johnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details

Command refernece:
http://wiki.panotools.org/Panorama_scripting_in_a_nutshell
Some parts of this code inspired by Christian Sattler's tool
(https://github.com/JohnDMcMaster/csstitch)
'''

import sys 
import os.path
import pr0ntools.pimage
from pr0ntools.pimage import PImage
from pr0ntools.pimage import TempPImage
from pr0ntools.stitch.engine import PanoEngine
from pr0ntools.execute import Execute

VERSION = '0.1'

project_file = 'panorama0.pto'
temp_project_file = '/tmp/pr0nstitch.pto'
allow_overwrite = True

AUTOPANO_SIFT_C = 1
autopano_sift_c = "autopano-sift-c"
AUTOPANO_AJ = 2
# I use this under WINE, the Linux version doesn't work as well
autopano_aj = "autopanoaj"
grid_only = False

CONTROL_POINT_ENGINE = AUTOPANO_AJ

'''
cpclean: remove wrong control points by statistic method
cpclean version 2010.0.0.5045

Usage:  cpclean [options] input.pto

CPClean uses statistical methods to remove wrong control points

Step 1 optimises all images pairs, calculates for each pair mean 
       and standard deviation and removes all control points 
       with error bigger than mean+n*sigma
Step 2 optimises the whole panorama, calculates mean and standard deviation
       for all control points and removes all control points with error
       bigger than mean+n*sigma

  Options:
     -o file.pto  Output Hugin PTO file. Default: '<filename>_clean.pto'.
     -n num   distance factor for checking (default: 2)
     -p       do only pairwise optimisation (skip step 2)
     -w       do optimise whole panorama (skip step 1)
     -h       shows help
'''

'''
Usage:
ptovariable [options] project.pto

 Options:
	   --positions          Optimise positions
	   --roll               Optimise roll for all images except anchor if --positions not set
	   --pitch              Optimise pitch for all images except anchor if --positions not set
	   --yaw                Optimise yaw for all images except anchor if --positions not set
	   -r <num> <num> <..>  Optimise roll for specified images
	   -p <num> <num> <..>  Optimise pitch for specified images
	   -y <num> <num> <..>  Optimise yaw for specified images
	   --view               Optimise angle of view
	   --barrel             Optimise barrel distortion
	   --centre             Optimise optical centre
	   --vignetting         Optimise vignetting
	   --vignetting-centre  Optimise vignetting centre
	   --response           Optimise camera response EMoR parameters
	   --exposure           Optimise exposure (EV)
	   --white-balance      Optimise colour balance
  -o | --output OUTFILE     Specify output file default is to overwrite input       
  -h | --help               Outputs help documentation
'''
class PhotometricOptimizer:
	pto_project = None
	
	def __init__(self, pto_project):
		self.pto_project = pto_project
	
	def run(self):
		# Make sure its syncd
		self.pto_project.save()
	
		'''
		Setup variables for optimization
		'''	
		args = list()
		# Defect where brightness varies as we move towards the outside of the lens
		args.append("--vignetting")
		# ?
		args.append("--response")
		# ?
		args.append("--exposure")
		# ?
		args.append("--white-balance")
		# Overwrite input
		args.append(self.pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("ptovariable", args)
		if not rc == 0:
			raise Exception('failed photometric optimization setup')
		# Reload now that we overwrote
		self.pto_project.reopen()

		'''
		Do actual optimization
		'''	
		args = list()
		args.append("-o")
		args.append(self.pto_project.get_a_file_name())
		args.append(self.pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("vig_optimize", args)
		if not rc == 0:
			raise Exception('failed photometric optimization')
		# Reload now that we overwrote
		self.pto_project.reopen()		
	
print 'check'

def help():
	print 'pr0nstitch version %s' % VERSION
	print 'Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>'
	print 'Usage:'
	print 'pr0nstitch [args] <files>'
	print 'files:'
	print '\timage file: added to input images'
	print '--result=<file_name> or --out=<file_name>'
	print '\t--result-image=<image file name>'
	print '\t--result-project=<project file name>'
	print '--cp-engine=<engine>'
	print '\tautopano-sift-c: autopano-SIFT-c'
	print '\t\t--autopano-sift-c=<path>, default = autopano-sift-c'
	print '\tautopano-aj: Alexandre Jenny\'s autopano'
	print '\t\t--autopano-aj=<path>, default = autopanoaj'
	print '--pto-merger=<engine>'
	print '\tdefault: use pto_merge if availible'
	print '\tpto_merge: Hugin supported merge (Hugin 2010.2.0+)'
	print '\t\t--pto_merge=<path>, default = pto_merge'
	print '\tinternal: quick and dirty internal version'
	print 'Grid formation options (col 0, row 0 should be upper left):'
	print '--grid-only[=<bool>]: only construct/print the grid map and exit'
	print '--flip-col[=<bool>]: flip columns'
	print '--flip-row[=<bool>]: flip rows'
	print '--flip-pre-transpose[=<bool>]: switch col/row before all other flips'
	print '--flip-post-transpose[=<bool>]: switch col/row after all other flips'
	print '--no-overwrite[=<bool>]: do not allow overwrite of existing files'

def arg_fatal(s):
	print s
	help()
	sys.exit(1)

if __name__ == "__main__":
	input_image_file_names = list()
	output_project_file_name = None
	output_image_file_name = None
	flip_col = False
	flip_row = False
	flip_pre_transpose = False
	flip_post_transpose = False
	depth = 1
	
	for arg_index in range (1, len(sys.argv)):
		arg = sys.argv[arg_index]
		arg_key = None
		arg_value = None
		if arg.find("--") == 0:
			arg_value_bool = True
			if arg.find("=") > 0:
				arg_key = arg.split("=")[0][2:]
				arg_value = arg.split("=")[1]
				if arg_value == "false" or arg_value == "0" or arg_value == "no":
					arg_value_bool = False
			else:
				arg_key = arg[2:]

			if arg_key == "help":
				help()
				sys.exit(0)
			elif arg_key == "result" or arg_key == "out":
				if arg_value.find('.pto') > 0:
					output_project_file_name = arg_value
				elif PImage.is_image_filename(arg_value):
					output_image_file_name = arg_value
				else:
					arg_fatal('unknown file type %s, use explicit version' % arg)
			elif arg_key == "grid-only":
				grid_only = arg_value_bool
			elif arg_key == "flip-row":
				flip_row = arg_value_bool
			elif arg_key == "flip-col":
				flip_col = arg_value_bool
			elif arg_key == "flip-pre-transpose":
				flip_pre_transpose = arg_value_bool
			elif arg_key == "flip-post-transpose":
				flip_post_transpose = arg_value_bool
			elif arg_key == 'no-overwrite':
				allow_overwrite = not arg_value_bool
			else:
				arg_fatal('Unrecognized arg: %s' % arg)
		else:
			if arg.find('.pto') > 0:
				output_project_file_name = arg
			elif os.path.isfile(arg) or os.path.isdir(arg):
				input_image_file_names.append(arg)
			else:
				arg_fatal('unrecognized arg: %s' % arg)

	print 'post arg'
	print 'output image: %s' % output_image_file_name
	print 'output project: %s' % output_project_file_name
	
	'''
	Probably most intuitive is to have (0, 0) at lower left 
	like its presented in many linear algebra works and XY graph
	'''
	engine = PanoEngine.from_file_names(input_image_file_names, flip_col, flip_row, flip_pre_transpose, flip_post_transpose, depth)
	if grid_only:
		print 'Grid only, exiting'
		sys.exit(0)
	engine.set_output_project_file_name(output_project_file_name)
	engine.set_output_image_file_name(output_image_file_name)
	if not allow_overwrite:
		if output_project_file_name and os.path.exists(output_project_file_name):
			print 'ERROR: cannot overwrite existing project file: %s' % output_project_file_name
			sys.exit(1)
		if output_image_file_name and os.path.exists(output_image_file_name):
			print 'ERROR: cannot overwrite existing image file: %s' % output_image_file_name
			sys.exit(1)	
	
	engine.run()
	print 'Done!'

