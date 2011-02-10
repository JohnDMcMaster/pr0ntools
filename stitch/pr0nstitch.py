#!/usr/bin/python
'''
pr0nstitch: IC die image stitching
Copyright 2010 John McMaster <johnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

import sys 

VERSION = '0.1'

def help():
	print 'pr0nstitch version %s' % VERSION
	print 'Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>'
	print '--cp-engine=<engine>'
	print '\tautopano-sift-c: autopano-SIFT-c'
	print '\t\t--autopano-sift-c=<path>'
	print '\tautopano-aj: Alexandre Jenny\'s autopano'
	print '\t\t--autopano-aj=<path>'
	print '--pto-merger=<engine>'
	print '\tdefault: use pto_merge if availible'
	print '\tpto_merge: Hugin supported merge (Hugin 2010.2.0+)'
	print '\t\t--pto_merge=<path>'
	print '\tinternal: quick and dirty internal version'

project_file = 'panorama0.pto'
temp_project_file = '/tmp/pr0nstitch.pto'

AUTOPANO_SIFT_C = 1
autopano_sift_c = "autopano-sift-c"
AUTOPANO_AJ = 2
# I use this under WINE, the Linux version doesn't work as well
autopano_aj = "autopanoaj"


CONTROL_POINT_ENGINE = AUTOPANO_AJ

class ImageCoordinateMap:
	'''
	row  2		[0, 2]	[1, 2]	[2, 2]
	y    1		[0, 1]	[1, 1]	[2, 1]
	     0		[0, 0]	[1, 0]	[2, 0]
		       	0		1		2
				col/x
	'''
	# The actual imageimage_file_names position mapping
	# Maps rows and cols to image file names
	# would like to change this to managed PImages or something
	# layout[col/x][row/y]
	layout = None:
	# ie y in range(0, rows)
	rows = None
	# ie x in range(0, cols)
	cols = None
	def __init__(cols, rows):
		self.layout = [None] * (rows * cols)
	
	def get_image(self, col, row):
		return self.layout[row * cols + col]
	
	def set_image(self, col, row, img):
		self.layout[row * cols + col] = img

	@staticmethod
	from_dir(dir_file_name):
		file_names = list()
		first_parts = set()
		second_parts = set()
		for file_name in os.listdir(dir_file_name):
			# Skip dirs
			if not os.path.isfile(file_name):
				continue
			file_names.append(file_name)
			
			core_file_name = file_name.split('.')[0]
			first_parts.insert(core_file_name.split('_')[0])
			second_parts.insert(core_file_name.split('_')[1])
		
		# Assume X first so that files read x_y.jpg which seems most intuitive (to me FWIW)
		rows = len(first_parts)
		cols = len(seocnd_parts)
		print 'rows: %d, cols: %d' % (rows, cols)
		
		ret = ImageCoordinateMap(cols, rows)
		file_names = sorted(file_names)
		file_names_index = 0;		
		'''
		Since x/col is first, y/row will increment first and must be the inner loop
		'''
		for cur_col in range(0, cols):
			for cur_row in range(0, rows):
				# Not canonical, but resolved well enough
				full_file_name = dir_file_name + "/" + file_names[file_names_index]
				ret.set_image(cur_col, cur_row, full_file_name);
				file_names_index += 1
		return result;
		

print 'check'

if __name__ == "__main__":
	image_file_names = list()
	
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
		else:
			if 
		if arg_key == "help":
			help()
			sys.exit(0)
		if arg_key == "at-optimized-parameters":
			at_optmized_parameters = arg_values
		else:
			log('Unrecognized argument: %s' % arg)
			help()
			sys.exit(1)
	print 'post arg'
	
	'''
	Probably most intuitive is to have (0, 0) at lower left 
	like its presented in many linear algebra works and XY graph
	'''
	
