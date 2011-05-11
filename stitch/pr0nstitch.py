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
from pr0ntools.stitch.wander_stitch import WanderStitch
from pr0ntools.stitch.grid_stitch import GridStitch
from pr0ntools.stitch.fortify_stitch import FortifyStitch
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

def help():
	print 'pr0nstitch version %s' % VERSION
	print 'Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>'
	print 'Usage:'
	print 'pr0nstitch [args] <files>'
	print 'files:'
	print '\timage file: added to input images'
	print '\tdirectory: added to input image directories'
	print '\t.pto file: assumed to be project file'
	print '--result=<file_name> or --out=<file_name>'
	print '\t--result-image=<image file name>'
	print '\t--result-project=<project file name>'
	print '--input-project=<project file name>'
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
	print '--algorithm=<algorithm>'
	print '\tgrid: assume input is a regular grid'
	print '\twander: assume input is contiguous. Use for back and forth pattern (default)'
	# Did hacks, not supported externally
	#print '\tfortify: use input-project and try to fill in additional control points'
	# Consider supporting
	#print '\tauto: poke around at images and then do stitch after figuring out layout (computationally expensive!)'
	print 'Grid formation options (col 0, row 0 should be upper left):'
	print '--grid-only[=<bool>]: only construct/print the grid map and exit'
	print '--flip-col[=<bool>]: flip columns'
	print '--flip-row[=<bool>]: flip rows'
	print '--flip-pre-transpose[=<bool>]: switch col/row before all other flips'
	print '--flip-post-transpose[=<bool>]: switch col/row after all other flips'
	print '--no-overwrite[=<bool>]: do not allow overwrite of existing files'
	print '--regular[=<bool>]: images are separated by regular intervals like CNC would produce'

def arg_fatal(s):
	print s
	help()
	sys.exit(1)

ALGORITHM_GRID = "grid"
ALGORITHM_WANDER = "wander"
ALGORITHM_FORTIFY = "fortify"

if __name__ == "__main__":
	input_image_file_names = list()
	input_project_file_name = None
	output_project_file_name = None
	output_image_file_name = None
	alt_rows = False
	alt_cols = False
	n_rows = None
	n_cols = None
	flip_col = False
	flip_row = False
	flip_pre_transpose = False
	flip_post_transpose = False
	depth = 1
	algorithm = None
	# CNC like precision?
	regular = False
	x_overlap = None
	y_overlap = None
	
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
			elif arg_key == "algorithm":
				algorithm = arg_value
			elif arg_key == "n-rows":
				n_rows = int(arg_value)
			elif arg_key == "n-cols":
				n_cols = int(arg_value)
			elif arg_key == "alt-rows":
				alt_rows = arg_value_bool
			elif arg_key == "alt-cols":
				alt_cols = arg_value_bool
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
			elif arg_key == 'regular':
				regular = arg_value_bool
			elif arg_key == 'x-overlap':
				x_overlap = float(arg_value)
			elif arg_key == 'y-overlap':
				y_overlap = float(arg_value)
			else:
				arg_fatal('Unrecognized arg: %s' % arg)
		else:
			if arg.find('.pto') > 0:
				output_project_file_name = arg
			elif os.path.isfile(arg) or os.path.isdir(arg):
				input_image_file_names.append(arg)
			else:
				arg_fatal('unrecognized arg: %s' % arg)

	if algorithm is None:
		algorithm = ALGORITHM_WANDER

	print 'post arg'
	print 'output image: %s' % output_image_file_name
	print 'output project: %s' % output_project_file_name
	
	if algorithm == ALGORITHM_GRID:
		'''
		Probably most intuitive is to have (0, 0) at lower left 
		like its presented in many linear algebra works and XY graph
		...but image stuff tends to to upper left, so thats what things use
		'''

		engine = GridStitch.from_file_names(input_image_file_names, flip_col, flip_row, flip_pre_transpose, flip_post_transpose, depth,
				alt_rows, alt_cols, n_rows, n_cols)
		if grid_only:
			print 'Grid only, exiting'
			sys.exit(0)
	elif algorithm == ALGORITHM_WANDER:
		engine = WanderStitch.from_file_names(input_image_file_names)
	elif algorithm == ALGORITHM_FORTIFY:
		if len(input_image_file_names) > 0:
			raise Exception('Cannot use old project and image files')
		if input_project_file_name is None:
			raise Exception('Requires input project')
		engine = ForitfyStitch.from_existing_project_file_name(input_project_file_name)
	else:
		raise Exception('need an algorithm / engine')

	engine.set_output_project_file_name(output_project_file_name)
	engine.set_output_image_file_name(output_image_file_name)
	engine.set_regular(regular)
	
	if x_overlap:
		engine.x_overlap = x_overlap
	if y_overlap:
		engine.y_overlap = y_overlap
	
	if not allow_overwrite:
		if output_project_file_name and os.path.exists(output_project_file_name):
			print 'ERROR: cannot overwrite existing project file: %s' % output_project_file_name
			sys.exit(1)
		if output_image_file_name and os.path.exists(output_image_file_name):
			print 'ERROR: cannot overwrite existing image file: %s' % output_image_file_name
			sys.exit(1)	
	
	engine.run()
	print 'Done!'

