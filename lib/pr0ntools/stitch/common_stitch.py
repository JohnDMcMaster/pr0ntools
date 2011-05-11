'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details

Common code for various stitching strategies
'''

from pr0ntools.image.soften import Softener
from pr0ntools.stitch.control_point import ControlPointGenerator
from pr0ntools.stitch.pto.project import PTOProject
from pr0ntools.stitch.remapper import Remapper
import os
from pr0ntools.pimage import PImage
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.temp_file import ManagedTempDir
import sys

class CommonStitch:
	def __init__(self):
		self.output_image_file_name = None
		self.project = None
		self.remapper = None
		self.photometric_optimizer = None
		self.cleaner = None
		# Used before init, later ignore for project.file_name
		self.output_project_file_name = None
		self.image_file_names = None
		self.control_point_gen = None

		# Images have predictable separation?
		self.regular = False
		# Only used if regular image
		self.subimage_control_points = True
		self.x_overlap = 1.0 / 3.0
		self.y_overlap = 1.0 / 3.0

	def set_regular(self, regular):
		self.regular = regular

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


		# Generate control points and merge them into a master project
		self.control_point_gen = ControlPointGenerator()
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
		
		self.project.image_file_names = self.image_file_names

		'''
		Generate control points
		'''
		self.generate_control_points()

		if False:
			self.photometric_optimizer = PhotometricOptimizer(self.project)
			self.photometric_optimizer.run()

		# Remove statistically unpleasant points
		if False:
			self.cleaner = PTOClean(self.project)
			self.cleaner.run()
		
		self.project.optimize_xy_only()

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
						# Force lense type 0 (rectilinear)
						# Otherwise, it gets added as -2 if we are unlucky ("Error on line 6")
						# or 2 (fisheye) if we are lucky (screwed up image)
						new_line += ' f0'
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
		print '***PTO project final (%s / %s) data length %d***' % (self.project.file_name, self.output_project_file_name, len(self.project.get_text()))
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

	def control_points_by_subimage(self, pair, pair_images):
		# pair: pair of row/col or coordinate positions (used to determine relative positions)
		# (0, 0) at upper left
		# pair_images: pair of image file names
		
		'''
		Just work on the overlap section, maybe even less
		'''
		
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
			sub_image_0_x_delta = int(images[0].width() * (1.0 - self.x_overlap))
			sub_image_1_x_end = int(images[1].width() * self.x_overlap)
		
		# image 0 above image 1?
		if pair.first.row < pair.second.row:
			# Keep image 0 top, image 1 bottom
			sub_image_0_y_delta = int(images[0].height() * (1.0 - self.y_overlap))
			sub_image_1_y_end = int(images[1].height() * self.y_overlap)
		
		'''
		print 'image 0 x delta: %d, y delta: %d' % (sub_image_0_x_delta, sub_image_0_y_delta)
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
		fast_pair_project = self.control_point_gen.generate_core(sub_pair_images)
		if fast_pair_project is None:
			print 'WARNING: failed to gen control points @ %s' % repr(pair)
			return None
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
		return final_pair_project

	def try_control_points_with_position(self, pair, pair_images):
		if self.regular and self.subimage_control_points:
			return self.control_points_by_subimage(pair, pair_images)
		else:
			return self.control_point_gen.generate_core(pair_images)

	# Control point generator wrapper entry
	def generate_control_points_by_pair(self, pair, pair_images):
		soften_iterations = 3
	
		if True:
			# Try raw initially
			ret_project = self.try_control_points_with_position(pair, pair_images)
			if ret_project:
				return ret_project
		
		print 'WARNING: bad project, attempting soften...'

		soften_image_file_0_managed = ManagedTempFile.from_same_extension(pair_images[0])
		soften_image_file_1_managed = ManagedTempFile.from_same_extension(pair_images[1])

		softener = Softener()
		first_run = True

		for i in range(0, soften_iterations):
			# And then start screwing with it
			# Wonder if we can combine features from multiple soften passes?
			# Or at least take the maximum
			# Do features get much less accurate as the soften gets up there?
		
			print 'Attempting soften %d / %d' % (i + 1, soften_iterations)

			if first_run:			
				softener.run(pair_images[0], soften_image_file_0_managed.file_name)
				softener.run(pair_images[1], soften_image_file_1_managed.file_name)
			else:
				softener.run(soften_image_file_0_managed.file_name)
				softener.run(soften_image_file_1_managed.file_name)			
			
			pair_soften_image_file_names = (soften_image_file_0_managed.file_name, soften_image_file_1_managed.file_name)
			ret_project = self.try_control_points_with_position(pair, pair_soften_image_file_names)
			# Did we win?
			if ret_project:
				# Fixup the project to reflect the correct file names
				text = ret_project.__repr__()
				print
				print 'Before sub'
				print
				print ret_project.__repr__()
				print
				print
				print
				print '%s => %s' % (soften_image_file_0_managed.file_name, pair_images[0])
				text = text.replace(soften_image_file_0_managed.file_name, pair_images[0])
				print '%s => %s' % (soften_image_file_1_managed.file_name, pair_images[1])
				text = text.replace(soften_image_file_1_managed.file_name, pair_images[1])

				ret_project.set_text(text)
				print
				print 'After sub'
				print
				print ret_project.__repr__()
				print
				print
				print
				#sys.exit(1)
				return ret_project
				
			first_run = False

		print 'WARNING: gave up on generating control points!' 
		return None
		#raise Exception('ERROR: still could not make a coherent project!')

