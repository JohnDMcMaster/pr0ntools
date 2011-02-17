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
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.temp_file import ManagedTempDir
from pr0ntools.stitch.control_point import ControlPointGenerator
from pr0ntools.stitch.pto import PTOProject
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
Grid coordinates
Not an actual image
'''
class ImageCoordinateMapPairing:
	col = None
	row = None
	
	def __init__(self, col, row):
		self.col = col
		self.row = row
		
	def __repr__(self):
		return '(col=%d, row=%d)' % (self.col, self.row)

	def __cmp__(self, other):
		delta = self.col - other.col
		if delta:
			return delta
			
		delta = self.row - other.row
		if delta:
			return delta

		return 0
		
class ImageCoordinatePair:
	# Of type ImageCoordinateMapPairing
	first = None
	second = None
	
	def __init__(self, first, second):
		self.first = first
		self.second = second

	def __cmp__(self, other):
		delta = self.first.__compare__(other.first)
		if delta:
			return delta
			
		delta = delta = self.second.__compare__(other.second)
		if delta:
			return delta

		return 0

	def __repr__(self):
		return '%s vs %s' % (self.first, self.second)

class ImageCoordinateMap:
	'''
				col/x
		       	0		1		2
	row  0		[0, 0]	[1, 0]	[2, 0]
	y    1		[0, 1]	[1, 1]	[2, 1]
	     2		[0, 2]	[1, 2]	[2, 2] 
	'''
	# The actual imageimage_file_names position mapping
	# Maps rows and cols to image file names
	# would like to change this to managed PImages or something
	# layout[col/x][row/y]
	layout = None
	# ie x in range(0, cols)
	cols = None
	# ie y in range(0, rows)
	rows = None
	def __init__(self, cols, rows):
		self.cols = cols
		self.rows = rows
		self.layout = [None] * (cols * rows)
	
	def get_image(self, col, row):
		return self.layout[self.cols * row + col]
	
	def get_images_from_pair(self, pair):
		# ImageCoordinatePair
		return (self.get_image(pair.first.col, pair.first.row), self.get_image(pair.second.col, pair.second.row))
	
	def set_image(self, col, row, file_name):
		self.layout[self.cols * row + col] = file_name

	@staticmethod
	def get_file_names(file_names_in, depth):
		file_names = list()
		first_parts = set()
		second_parts = set()
		for file_name_in in file_names_in:
			if os.path.isfile(file_name_in):
				if PImage.is_image_filename(file_name_in):
					file_names.append(file_name_in)
			elif os.path.isdir(file_name_in):			
				if depth:
					for file_name in os.listdir(file_name_in):
						file_names.append(get_file_names(os.path.join(file_name_in, file_name), depth - 1))
		return file_names
		
	@staticmethod
	def from_file_names(file_names_in, flip_col = False, flip_row = False, flip_pre_transpose = False, flip_post_transpose = False, depth = 1):
		file_names = ImageCoordinateMap.get_file_names(file_names_in, depth)
		'''
		Certain program take file names relative to the project file, others to working dir
		Since I like making temp files in /tmp so as not to clutter up working dir, this doesn't work well
		Only way to get stable operation is to make all file paths canonical
		'''
		file_names_canonical = list()
		for file_name in file_names:
			file_names_canonical.append(os.path.realpath(file_name))
		return ImageCoordinateMap.from_file_names_core(file_names_canonical, flip_col, flip_row, flip_pre_transpose, flip_post_transpose)
	
	@staticmethod
	def from_file_names_core(file_names, flip_col, flip_row, flip_pre_transpose, flip_post_transpose):
		first_parts = set()
		second_parts = set()
		for file_name in file_names:
			basename = os.path.basename(file_name)
			core_file_name = basename.split('.')[0]
			first_parts.add(core_file_name.split('_')[0])
			second_parts.add(core_file_name.split('_')[1])
		
		# Assume X first so that files read x_y.jpg which seems most intuitive (to me FWIW)
		cols = len(first_parts)
		rows = len(second_parts)
		print 'initial cols / X dim / width: %d, rows / Y dim / height: %d' % (cols, rows)
		
		# Make sure we end up with correct arrangement
		flips = 0
		if flip_pre_transpose:
			flips += 1
		if flip_post_transpose:
			flips += 1
		# Did we switch?
		if flips % 2 == 0:
			# No switch
			effective_cols = cols
			effective_rows = rows
		else:
			effective_cols = rows
			effective_rows = cols
		print 'effective initial cols / X dim / width: %d, rows / Y dim / height: %d' % (effective_cols, effective_rows)
		
		ret = ImageCoordinateMap(effective_cols, effective_rows)
		file_names = sorted(file_names)
		file_names_index = 0		
		'''
		Since x/col is first, y/row will increment first and must be the inner loop
		'''
		for cur_col in range(0, cols):
			for cur_row in range(0, rows):
				# Not canonical, but resolved well enough
				file_name = file_names[file_names_index]
				
				effective_col = cur_col
				effective_row = cur_row

				if flip_pre_transpose:
					temp = effective_row
					effective_row = effective_col
					effective_col = temp

				if flip_col:
					effective_col = effective_cols - effective_col - 1
					
				if flip_row:
					effective_row = effective_rows - effective_row - 1
				
				if flip_post_transpose:
					temp = effective_row
					effective_row = effective_col
					effective_col = temp
				
				if effective_col >= effective_cols or effective_row >= effective_rows:
					print 'effective_col %d >= effective_cols %d or effective_row %d >= effective_rows %d' % (effective_col, effective_cols, effective_row, effective_rows)
					raise Exception('die')
				
				ret.set_image(effective_col, effective_row, file_name)
				file_names_index += 1
		return ret
	
	def gen_pairs(self, row_spread = 1, col_spread = 1):
		'''Returns a generator of ImageCoordinatePair's, sorted'''
		for col_0 in range(0, self.cols):
			for col_1 in range(max(0, col_0 - col_spread), min(self.cols, col_0 + col_spread)):
				for row_0 in range(0, self.rows):
					# Don't repeat elements, don't pair with self, keep a delta of row_spread
					for row_1 in range(max(0, row_0 - row_spread), min(self.rows, row_0 + row_spread)):
						if col_0 == col_1 and row_0 == row_1:
							continue
						# For now just allow manhatten distance of 1
						if abs(col_0 - col_1) + abs(row_0 - row_1) > 1:
							continue
						
						to_yield = ImageCoordinatePair(ImageCoordinateMapPairing(col_1, row_1), ImageCoordinateMapPairing(col_0, row_0))
						yield to_yield

	def __repr__(self):
		ret = ''
		for row in range(0, self.rows):
			for col in range(0, self.cols):
				ret += '(col/x=%d, row/y=%d) = %s\n' % (col, row, self.get_image(col, row))
		return ret
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
	pto_project = None
	
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
Part of perl-Panotools-Script

Usage:
    ptoclean [options] --output better.pto notgood.pto

     Options:
      -o | --output     Filename of pruned project (can be the the same as the input)
      -n | --amount     Distance factor for pruning (default=2)
      -f | --fast       Don't run the optimiser for each image pair (similar to APClean)
      -v | --verbose    Report some statistics
      -h | --help       Outputs help documentation
'''
class PTOClean:
	def __init__(self, pto_project):
		self.pto_project = pto_project
	
	def run(self):
		args = list()
		args.append("-o")
		args.append(self.pto_project.get_a_file_name())
		args.append(self.pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("ptoclean", args)
		if not rc == 0:
			raise Exception('failed to clean control points')
		self.pto_project.reopen()
	
class PanoEngine:
	coordinate_map = None
	output_image_file_name = None
	project = None
	remapper = None
	photometric_optimizer = None
	cleaner = None
	# Used before init, later ignore for project.file_name
	output_project_file_name = None
	image_file_names = None

	def __init__(self):
		pass

	@staticmethod
	def from_file_names(image_file_names, flip_col = False, flip_row = False, flip_pre_transpose = False, flip_post_transpose = False, depth = 1):
		engine = PanoEngine()
		engine.image_file_names = image_file_names
		engine.coordinate_map = ImageCoordinateMap.from_file_names(image_file_names, flip_col, flip_row, flip_pre_transpose, flip_post_transpose, depth)
		print engine.coordinate_map
		if grid_only:
			print 'Grid only, exiting'
			sys.exit(0)
		return engine
	
	def set_output_project_file_name(self, file_name):
		self.output_project_file_name = file_name

	def set_output_image_file_name(self, file_name):
		self.output_image_file_name = file_name

	def run(self):
		if not self.output_project_file_name and not self.output_image_file_name:
			raise Exception("need either project or image file")
		#if not self.output_project_file_name:
			#self.project_temp_file = ManagedTempFile.get()
			#self.output_project_file_name = self.project_temp_file.file_name
		print 'output project file name: %s' % self.output_project_file_name
		print 'output image file name: %s' % self.output_image_file_name
		
		#sys.exit(1)
		'''
		Generate control points
		Generate to all neighbors to start with
		'''
		# Generate control points and merge them into a master project
		control_point_gen = ControlPointGenerator()
		# How many rows and cols to go to each side
		# If you hand took the pictures, this might suit you
		self.project = PTOProject.from_blank()
		if self.output_project_file_name:
			self.project.set_file_name(self.output_project_file_name)
			if os.path.exists(self.output_project_file_name):
				# Otherwise, we merge into it
				print 'WARNING: removing old project file: %s' % self.output_project_file_name
				os.remove(self.output_project_file_name)
		else:
			self.project.get_a_file_name(None, "_master.pto")
		
		temp_projects = list()
		subimage_control_points = True

		'''
		for pair in self.coordinate_map.gen_pairs(1, 1):
			print 'pair raw: ' + repr(pair)
			pair_images = self.coordinate_map.get_images_from_pair(pair)
			print 'pair images: ' + repr(pair_images)
		'''
		print
		print '***Pairs: %d***' % len([x for x in self.coordinate_map.gen_pairs(1, 1)])
		print
		for pair in self.coordinate_map.gen_pairs(1, 1):				
			print 'pair raw: ' + repr(pair)
			# Image file names as list
			pair_images = self.coordinate_map.get_images_from_pair(pair)
			print 'pair images: ' + repr(pair_images)

			if subimage_control_points:
				'''
				Just work on the overlap section, maybe even less
				'''
				overlap = 1.0 / 3.0
				
				images = [PImage.from_file(image_file_name) for image_file_name in pair_images]
				
				'''
				image_0 used as reference
				4 basic situations: left, right, up right
				8 extended: 4 basic + corners
				Pairs should be sorted, which simplifies the logic
				'''
				sub_image_0_x_delta = 0
				sub_image_0_y_delta = 0
				sub_image_1_x_end = images[1].width()
				sub_image_1_y_end = images[1].height()

				# image 0 left of image 1?
				if pair.first.col < pair.second.col:
					# Keep image 0 right, image 1 left
					sub_image_0_x_delta = int(images[0].width() * (1.0 - overlap))
					sub_image_1_x_end = int(images[1].width() * overlap)
				
				# image 0 above image 1?
				if pair.first.row < pair.second.row:
					# Keep image 0 top, image 1 bottom
					sub_image_0_y_delta = int(images[0].height() * (1.0 - overlap))
					sub_image_1_y_end = int(images[1].height() * overlap)
				
				print 'image 0 x delta: %d, y delta: %d' % (sub_image_0_x_delta, sub_image_0_y_delta)
				'''
				Note y starts at top in PIL
				'''
				sub_image_0 = images[0].subimage(sub_image_0_x_delta, None, sub_image_0_y_delta, None)
				sub_image_1 = images[1].subimage(None, sub_image_1_x_end, None, sub_image_1_y_end)
				sub_image_0_file = ManagedTempFile.get(None, '.jpg')
				sub_image_1_file = ManagedTempFile.get(None, '.jpg')
				print 'sub image 0: width=%d, height=%d, name=%s' % (sub_image_0.width(), sub_image_0.height(), sub_image_0_file.file_name)
				print 'sub image 1: width=%d, height=%d, name=%s' % (sub_image_1.width(), sub_image_1.height(), sub_image_0_file.file_name)
				#sys.exit(1)
				sub_image_0.image.save(sub_image_0_file.file_name)
				sub_image_1.image.save(sub_image_1_file.file_name)
				
				sub_pair_images = (sub_image_0_file.file_name, sub_image_1_file.file_name)
				# image index to subimage file name link (not symbolic link)
				index_to_sub_file_name = dict()
				imgfile_index = 0
				# subimage file name symbolic link to subimage file name
				# this should be taken care of inside of control point actually
				#sub_link_to_sub = dict()
				# subimage to the image it came from
				sub_to_real = dict()
				sub_to_real[sub_image_0_file.file_name] = pair_images[0]
				sub_to_real[sub_image_1_file.file_name] = pair_images[1]

				'''
				# Hugin project file
				# generated by Autopano

				# Panorama settings:
				p w8000 h1200 f2 v250 n"PSD_mask"

				# input images:
				#-imgfile 2816 704 "/tmp/pr0ntools_C21F246F52E9D691/AA9627DC60B39FC8.jpg"
				o f0 y+0.000000 r+0.000000 p+0.000000 u20 d0.000000 e0.000000 v70.000000 a0.000000 b0.000000 c0.000000
				#-imgfile 2816 704 "/tmp/pr0ntools_C21F246F52E9D691/EDE10C14171B2078.jpg"
				o f0 y+0.000000 r+0.000000 p+0.000000 u20 d0.000000 e0.000000 v70.000000 a0.000000 b0.000000 c0.000000

				# Control points:
				c n0 N1 x1024 y176 X555 Y119
				# Control Point No 0: 1.00000
				c n0 N1 x1047 y160 X578 Y105
				...




				autopano-sift-c style file
				
				# Hugin project file generated by APSCpp

				p f2 w3000 h1500 v360  n"JPEG q90"
				m g1 i0

				i w2816 h704 f0 a0 b-0.01 c0 d0 e0 p0 r0 v180 y0  u10 n"/tmp/pr0ntools_6691335AD228382E.jpg"
				i w2816 h938 f0 a0 b-0.01 c0 d0 e0 p0 r0 v180 y0  u10 n"/tmp/pr0ntools_64D97FF4621BC36E.jpg"

				v p1 r1 y1

				# automatically generated control points
				c n0 N1 x1142.261719 y245.074757 X699.189408 Y426.042661 t0
				c n0 N1 x887.417450 y164.602097 X1952.346197 Y921.975829 t0
				...
				c n0 N1 x823.803714 y130.802771 X674.596763 Y335.994699 t0
				c n0 N1 x1097.192159 y121.170416 X937.394996 Y329.998934 t0

				# :-)
				'''
				fast_pair_project = control_point_gen.generate_core(sub_pair_images)
				if fast_pair_project is None:
					print 'WARNING: failed to gen control points @ %s' % repr(pair)
					continue
				out = ''
				part_pair_index = 0
				for line in fast_pair_project.__repr__().split('\n'):
					if len(line) == 0:
						new_line = ''
					# This type of line is gen by autopano-sift-c
					elif line[0] == 'c':
						# c n0 N1 x1142.261719 y245.074757 X699.189408 Y426.042661 t0
						
						'''
						Okay def alphabetical issues
						# Not strictly related to this code, but close enough
						if not index_to_sub_file_name[0] == sub_image_0_file:
							print '0 index indicated file: %s, pair gen order expected %s' % (index_to_sub_file_name[0], sub_image_0_file)
							raise Exception('mismatch')
						if not index_to_sub_file_name[1] == sub_image_1_file:
							print '1 index indicated file: %s, pair gen order expected %s' % (index_to_sub_file_name[1], sub_image_1_file)
							raise Exception('mismatch')
						'''
						
						# Parse
						parts = line.split()
						if not parts[1] == 'n0':
							print parts[1]
							raise Exception('mismatch')
						if not parts[2] == 'N1':
							print parts[2]
							raise Exception('mismatch')
							
						x = float(parts[3][1:])								
						y = float(parts[4][1:])
						X = float(parts[5][1:])
						Y = float(parts[6][1:])
				
						#sub_image_1_x_end = image_1.width()
						#sub_image_1_y_end = image_1.height()

						# Adjust the image towards the upper left hand corner
						if index_to_sub_file_name[0] == sub_image_0_file.file_name:
							# normal adjustment
							x += sub_image_0_x_delta
							y += sub_image_0_y_delta
						elif index_to_sub_file_name[1] == sub_image_0_file.file_name:
							# they got flipped
							X += sub_image_0_x_delta
							Y += sub_image_0_y_delta
						else:
							print index_to_sub_file_name
							print 'index_to_sub_file_name[0]: %s' % repr(index_to_sub_file_name[0])
							print 'index_to_sub_file_name[1]: %s' % repr(index_to_sub_file_name[1])
							print 'sub_image_0_file: %s' % repr(sub_image_0_file)
							print 'sub_image_1_file: %s' % repr(sub_image_1_file)
							raise Exception("confused")
				
						# Write
						new_line = "c n0 N1 x%f y%f X%f Y%f t0" % (x, y, X, Y)
						out += new_line + '\n'
					# This type of line is generated by pto_merge
					elif line[0] == 'i':
						# i w2816 h704 f0 a0 b-0.01 c0 d0 e0 p0 r0 v180 y0  u10 n"/tmp/pr0ntools_6691335AD228382E.jpg"
						new_line = ''
						for part in line.split():
							t = part[0]
							if t == 'i':
								new_line += 'i'
							elif t == 'w':
								new_line += ' w%d' % images[0].width()
							elif t == 'h':
								new_line += ' w%d' % images[0].height()
							elif t == 'n':
								new_line += ' n%s' % pair_images[part_pair_index]
								part_pair_index += 1
							else:
								new_line += ' %s' % part
						print 'new line: %s' % new_line
					# These lines are generated by autopanoaj
					# The comment line is literally part of the file format, some sort of bizarre encoding
					# #-imgfile 2816 704 "/tmp/pr0ntools_2D24DE9F6CC513E0/pr0ntools_6575AA69EA66B3C3.jpg"
					# o f0 y+0.000000 r+0.000000 p+0.000000 u20 d0.000000 e0.000000 v70.000000 a0.000000 b0.000000 c0.000000
					elif line.find('#-imgfile') == 0:
						# Replace pseudo file names with real ones
						new_line = line
						index_to_sub_file_name[imgfile_index] = line.split('"')[1]
						imgfile_index += 1
					else:
						new_line = line
					out += new_line + '\n'
				else:
					out += line + '\n'

				
				for k in sub_to_real:
					v = sub_to_real[k]
					print 'Replacing %s => %s' % (k, v)
					out = out.replace(k, v)

				final_pair_project = PTOProject.from_text(out)
			else:
				final_pair_project = control_point_gen.generate_core(pair_images)
				
			if False:
				print
				print 'Final pair project'
				print final_pair_project.get_a_file_name()
				print
				print
				print final_pair_project
				print
				print
				print
				#sys.exit(1)
			
			temp_projects.append(final_pair_project)
			
		print 'pairs done, found %d' % len(temp_projects)
		
		self.project.merge_into(temp_projects)
		self.project.save()
		print 'Sub projects (full image):'
		for project in temp_projects:
			# prefix so I can grep it for debugging
			print '\tSUB: ' + project.file_name
		print
		print
		print 'Master project file: %s' % self.project.file_name		
		print
		print
		print self.project.text
		print
		print

		if False:
			self.photometric_optimizer = PhotometricOptimizer(self.project)
			self.photometric_optimizer.run()

		# Remove statistically unpleasant points
		if False:
			self.cleaner = PTOClean(self.project)
			self.cleaner.run()
		
		
		# XXX: move this to earlier if possible
		'''
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
		print 'Fixing up v (optimization variable) lines...'
		new_project_text = ''
		new_lines = ''
		for i in range(1, len(self.image_file_names)):
			# optimize d (x) and e (y) for all other than anchor
			new_lines += 'v d%d e%d \n' % (i, i)
		new_lines += 'v \n'
		for line in self.project.text.split('\n'):
			if line == '':
				new_project_text += '\n'				
			elif line[0] == 'v':
				# Replace once, ignore others
				new_project_text += new_lines
				new_lines = ''
			else:
				new_project_text += line + '\n'
		self.project.text = new_project_text
		print
		print
		print self.project.text
		print
		print

		print 'Fixing up i (image attributes) lines...'
		new_project_text = ''
		new_lines = ''
		for line in self.project.text.split('\n'):
			if line == '':
				new_project_text += '\n'				
			elif line[0] == 'i':
				# before replace
				# i Eb1 Eev0 Er1 Ra0.0111006880179048 Rb-0.00838561356067657 Rc0.0198899246752262 Rd0.0135543448850513 Re-0.0435801632702351 Va1 Vb0.366722181378024 Vc-1.14825880321425 Vd0.904996105280657 Vm5 Vx0 Vy0 a0 b0 c0 d0 e0 f0 g0 h2112 n"x00000_y00033.jpg" p0 r0 t0 v70 w2816 y0
				new_line = ''
				for part in line.split():
					if part[0] == 'i':
						new_line += part
					# Keep image file name
					elif part[0] == 'n':
						new_line += ' ' + part
					# Script is getting angry, try to slim it up
					else:
						print 'Skipping unknown garbage: %s' % part
				new_project_text += new_line + '\n'
			else:
				new_project_text += line + '\n'
		self.project.text = new_project_text
		print
		print
		print self.project.text
		print
		print

		'''
		f0: rectilinear
		f2: equirectangular
		# p f2 w8000 h24 v179  E0 R0 n"TIFF_m c:NONE"
		# p f0 w8000 h24 v179  E0 R0 n"TIFF_m c:NONE"
		'''
		print 'Fixing up single lines'
		new_project_text = ''
		for line in self.project.text.split('\n'):
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
		self.project.text = new_project_text
		print
		print
		print self.project.text
		print
		print
		
		
		print
		print '***PTO project final (%s / %s)***' % (self.project.file_name, self.output_project_file_name)
		print
		
		# Make dead sure its saved up to date
		self.project.save()
		# having issues with this..
		if self.output_project_file_name and not self.project.file_name == self.output_project_file_name:
			raise Exception('project file name changed %s %s', self.project.file_name, self.output_project_file_name)
		
		# Did we request an actual stitch?
		if self.output_image_file_name:
			print 'Stitching...'
			self.remapper = Remapper(self.project, self.output_image_file_name)
			self.remapper.run()
		else:
			print 'NOT stitching'
'''
Each picture may have lens artifacts that make them not perfectly linear
This distorts the images to match the final plane
And command line usage is apparantly inaccurate.  
It doesn't document the .pto input option...weird

nona: stitch a panorama image

nona version 2010.0.0.5045

 It uses the transform function from PanoTools, the stitching itself
 is quite simple, no seam feathering is done.
 only the non-antialiasing interpolators of panotools are supported

 The following output formats (n option of panotools p script line)
 are supported:

  JPG, TIFF, PNG  : Single image formats without feathered blending:
  TIFF_m          : multiple tiff files
  TIFF_multilayer : Multilayer tiff files, readable by The Gimp 2.0

Usage: nona [options] -o output project_file (image files)
  Options: 
      -c         create coordinate images (only TIFF_m output)
      -v         quiet, do not output progress indicators
      -t num     number of threads to be used (default: nr of available cores)
      -g         perform image remapping on the GPU

  The following options can be used to override settings in the project file:
      -i num     remap only image with number num
                   (can be specified multiple times)
      -m str     set output file format (TIFF, TIFF_m, TIFF_multilayer, EXR, EXR_m)
      -r ldr/hdr set output mode.
                   ldr  keep original bit depth and response
                   hdr  merge to hdr
      -e exposure set exposure for ldr mode
      -p TYPE    pixel type of the output. Can be one of:
                  UINT8   8 bit unsigned integer
                  UINT16  16 bit unsigned integer
                  INT16   16 bit signed integer
                  UINT32  32 bit unsigned integer
                  INT32   32 bit signed integer
                  FLOAT   32 bit floating point
      -z         set compression type.
                  Possible options for tiff output:
                   NONE      no compression
                   PACKBITS  packbits compression
                   LZW       lzw compression
                   DEFLATE   deflate compression
'''
'''
The final program
Takes a collection of images and produces final output image

Usage: enblend [options] [--output=IMAGE] INPUT...
Blend INPUT images into a single IMAGE.

INPUT... are image filenames or response filenames.  Response
filenames start with an "@" character.

Common options:
  -V, --version          output version information and exit
  -a                     pre-assemble non-overlapping images
  -h, --help             print this help message and exit
  -l, --levels=LEVELS    number of blending LEVELS to use (1 to 29);
                         negative number of LEVELS decreases maximum
  -o, --output=FILE      write output to FILE; default: "a.tif"
  -v, --verbose[=LEVEL]  verbosely report progress; repeat to
                         increase verbosity or directly set to LEVEL
  -w, --wrap[=MODE]      wrap around image boundary, where MODE is
                         NONE, HORIZONTAL, VERTICAL, or BOTH; default: none;
                         without argument the option selects horizontal wrapping
  -x                     checkpoint partial results
  --compression=COMPRESSION
                         set compression of output image to COMPRESSION,
                         where COMPRESSION is:
                         NONE, PACKBITS, LZW, DEFLATE for TIFF files and
                         0 to 100 for JPEG files

Extended options:
  -b BLOCKSIZE           image cache BLOCKSIZE in kilobytes; default: 2048KB
  -c                     use CIECAM02 to blend colors
  -d, --depth=DEPTH      set the number of bits per channel of the output
                         image, where DEPTH is 8, 16, 32, r32, or r64
  -g                     associated-alpha hack for Gimp (before version 2)
                         and Cinepaint
  --gpu                  use graphics card to accelerate seam-line optimization
  -f WIDTHxHEIGHT[+xXOFFSET+yYOFFSET]
                         manually set the size and position of the output
                         image; useful for cropped and shifted input
                         TIFF images, such as those produced by Nona
  -m CACHESIZE           set image CACHESIZE in megabytes; default: 1024MB


Mask generation options:
  --coarse-mask[=FACTOR] shrink overlap regions by FACTOR to speedup mask
                         generation; this is the default; if omitted FACTOR
                         defaults to 8
  --fine-mask            generate mask at full image resolution; use e.g.
                         if overlap regions are very narrow
  --smooth-difference=RADIUS
                         smooth the difference image prior to seam-line
                         optimization with a Gaussian blur of RADIUS;
                         default: 0 pixels
  --optimize             turn on mask optimization; this is the default
  --no-optimize          turn off mask optimization
  --optimizer-weights=DISTANCEWEIGHT[:MISMATCHWEIGHT]
                         set the optimizer's weigths for distance and mismatch;
                         default: 8:1
  --mask-vectorize=LENGTH
                         set LENGTH of single seam segment; append "%" for
                         relative value; defaults: 4 for coarse masks and
                         20 for fine masks
  --anneal=TAU[:DELTAEMAX[:DELTAEMIN[:KMAX]]]
                         set annealing parameters of optimizer strategy 1;
                         defaults: 0.75:7000:5:32
  --dijkstra=RADIUS      set search RADIUS of optimizer strategy 2; default:
                         25 pixels
  --save-masks[=TEMPLATE]
                         save generated masks in TEMPLATE; default: "mask-%n.tif";
                         conversion chars: %i: mask index, %n: mask number,
                         %p: full path, %d: dirname, %b: basename,
                         %f: filename, %e: extension; lowercase characters
                         refer to input images uppercase to the output image
  --load-masks[=TEMPLATE]
                         use existing masks in TEMPLATE instead of generating
                         them; same template characters as "--save-masks";
                         default: "mask-%n.tif"
  --visualize[=TEMPLATE] save results of optimizer in TEMPLATE; same template
                         characters as "--save-masks"; default: "vis-%n.tif"
'''
class Remapper:
	pto_project = None
	output_file_name = None
	managed_temp_dir = None
	
	def __init__(self, pto_project, output_file_name):
		self.pto_project = pto_project
		self.output_file_name = output_file_name
		#self.output_managed_temp_dir = ManagedTempDir(self.pto_project.get_a_file_name() + "__")
		self.managed_temp_dir = ManagedTempDir.get()
		
	def run(self):
		self.remap()
		# We now have my_prefix_0000.tif, my_prefix_0001.tif, etc
		self.merge()
		
	def remap(self):
		args = list()
		args.append("-m")
		args.append("TIFF")
		args.append("-z")
		args.append("LZW")
		#args.append("-g")
		args.append("-o")
		args.append(output_prefix)
		args.append(pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("nona", args)
		if not rc == 0:
			raise Exception('failed to remap')
		self.project.reopen()


	def merge(self):
		'''
		[mcmaster@gespenst 2X2-ordered]$ enblend -o my_prefix.tif my_prefix_000*
		enblend: info: loading next image: my_prefix_0000.tif 1/1
		enblend: info: loading next image: my_prefix_0001.tif 1/1

		enblend: excessive overlap detected; remove one of the images
		enblend: info: remove invalid output image "my_prefix.tif"
		'''
		args = list()
		args.append("-m")
		args.append("TIFF_m")
		args.append("-z")
		args.append("LZW")
		#args.append("-g")
		args.append("-o")
		args.append(pto_project.get_a_file_name())
		args.append(pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("enblend", args)
		if not rc == 0:
			raise Exception('failed to blend')
		self.project.reopen()
		
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

