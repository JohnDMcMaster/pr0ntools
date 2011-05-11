'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details

This is a stitching strategy where a regular input grid is assumed
I get this using my CNC microscope because the pictures *are* taken as fairly precise intervals
This allows considerable optimization since we know where all the picture are
'''

from image_coordinate_map import ImageCoordinateMap
from pr0ntools.stitch.control_point import ControlPointGenerator
from pr0ntools.stitch.pto.project import PTOProject
from pr0ntools.stitch.remapper import Remapper
import os
from pr0ntools.pimage import PImage
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.temp_file import ManagedTempDir
from common_stitch import CommonStitch
import sys

class GridStitch(CommonStitch):
	def __init__(self):
		CommonStitch.__init__(self)
		self.coordinate_map = None

	@staticmethod
	def from_file_names(image_file_names, flip_col = False, flip_row = False, flip_pre_transpose = False, flip_post_transpose = False, depth = 1,
			alt_rows = False, alt_cols = False, rows = None, cols = None):
		engine = GridStitch()
		engine.image_file_names = image_file_names
		engine.coordinate_map = ImageCoordinateMap.from_file_names(image_file_names,
				flip_col, flip_row, flip_pre_transpose, flip_post_transpose, depth,
				alt_rows, alt_cols, rows, cols)
		print engine.coordinate_map
		return engine
	
	def generate_control_points(self):
		'''
		Generate control points
		Generate to all neighbors to start with
		'''
		temp_projects = list()

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


			final_pair_project = self.generate_control_points_by_pair(pair, pair_images)
			
			if not final_pair_project:
				print 'WARNING: bad project @ %s, %s' % (repr(pair), repr(pair_images))
				continue
			
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

