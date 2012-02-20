'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details

This is a stitching strategy where a regular input grid is assumed
I get this using my CNC microscope because the pictures *are* taken as fairly precise intervals
This allows considerable optimization since we know where all the picture are
'''

from image_coordinate_map import ImageCoordinateMap
import os
from common_stitch import *
import sys

class GridStitch(CommonStitch):
	def __init__(self):
		CommonStitch.__init__(self)
		self.coordinate_map = None
		self.set_regular(True)

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
	
	def init_failures(self):
		open_list = set()
		for (file_name, row, col) in self.coordinate_map.images():
			open_list.add(file_name)
		self.failures = FailedImages(open_list)
			
		
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
		n_pairs = len(list(self.coordinate_map.gen_pairs(1, 1)))
		print '***Pairs: %d***' % n_pairs
		print
		pair_index = 0
		for pair in self.coordinate_map.gen_pairs(1, 1):				
			pair_index += 1
			print 'pair raw: %s (%d / %d)' % (repr(pair), pair_index, n_pairs)
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
			if len(final_pair_project.get_text().strip()) == 0:
				raise Exception('Generated empty pair project')
			
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

