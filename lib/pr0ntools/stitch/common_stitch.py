'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details

Common code for various stitching strategies
'''

from image_coordinate_map import ImageCoordinateMap
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
	output_image_file_name = None
	project = None
	remapper = None
	photometric_optimizer = None
	cleaner = None
	# Used before init, later ignore for project.file_name
	output_project_file_name = None
	image_file_names = None
	control_point_gen = None

	def __init__(self):
		pass

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

