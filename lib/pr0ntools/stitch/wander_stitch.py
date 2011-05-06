'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details

This is a stitching strategy where images are adjacent, but unknown directions
The assumption is that for manual scanning you are going to zigzag
The positions aren't really 
'''

import os
import sys
from common_stitch import CommonStitch

class SubProject:
	# A PTOProject
	project = None
	# Maybe some position information?

class WanderStitch(CommonStitch):
	# So we don't compute the same match twice
	# (file name 1 , file_name 2) pairs
	# file name 1 < file_name 2
	tried_pairs = set()
	# of type SubProject
	# The projects we've already generated
	sub_projects = list()

	def __init__(self):
		CommonStitch.__init__(self)

	@staticmethod
	def from_file_names(image_file_names):
		engine = WanderStitch()
		engine.image_file_names = sorted(image_file_names)
		return engine
	
	def have_tried_pair(self, file_name_0, file_name_1):
		if file_name_0 < file_name_1:
			return (file_name_0, file_name_1) in self.tried_pairs 
		else:
			return (file_name_1, file_name_0) in self.tried_pairs 
	
	def mark_tried_pair(self, file_name_0, file_name_1):
		if file_name_0 < file_name_1:
			self.tried_pairs.add((file_name_0, file_name_1)) 
		else:
			self.tried_pairs.add((file_name_1, file_name_0)) 

	def stitch_images(self, file_names_pair):
		project = self.control_point_gen.generate_core(file_names_pair)
		self.sub_projects.append(project)
		self.mark_tried_pair(file_names_pair[0], file_names_pair[1])
		project.hugin_form()
		return project

	def analyze_image_pair(self, file_names_pair):
		'''
		Return various attributes given pair
		Computes control points and notes it so we don't re-compute
		'''
		
		project = self.stitch_images(file_names_pair)
		project.parse()

		image_0_points = set()
		image_1_points = set()
	
		# Assume that keep same ordering
		for control_point_line in project.control_point_lines:
			image_0_points.add((control_point_line.get_variable('x'), control_point_line.get_variable('y')))
			image_1_points.add((control_point_line.get_variable('X'), control_point_line.get_variable('Y')))

		print 'Output:'
		print [i[0] for i in image_0_points]
		image_0_x_average = sum([i[0] for i in image_0_points]) / len(image_0_points)
		image_0_y_average = sum([i[1] for i in image_0_points]) / len(image_0_points)
		image_1_x_average = sum([i[0] for i in image_1_points]) / len(image_1_points)
		image_1_y_average = sum([i[1] for i in image_1_points]) / len(image_1_points)

		image_0_x_proportion = image_0_x_average / project.image_lines[0].get_variable('w')
		image_0_y_proportion = image_0_y_average / project.image_lines[0].get_variable('h')
		image_1_x_proportion = image_1_x_average / project.image_lines[1].get_variable('w')
		image_1_y_proportion = image_1_y_average / project.image_lines[1].get_variable('h')
	
		x_delta = image_0_x_average - image_1_x_average
		y_delta = image_0_y_average - image_1_y_average
	
		print 'image 0, x: %f / %d (%f), y: %f / %d (%f)' % (image_0_x_average, project.image_lines[0].get_variable('w'), image_0_x_proportion, image_0_y_average, project.image_lines[0].get_variable('h'), image_0_y_proportion)
		print 'image 1, x: %f / %d (%f), y: %f / %d (%f)' % (image_1_x_average, project.image_lines[1].get_variable('w'), image_1_x_average / project.image_lines[1].get_variable('w'), image_1_y_average, project.image_lines[1].get_variable('h'), image_1_y_average / project.image_lines[1].get_variable('h'))
		print 'x delta: %f' % x_delta
		print 'y delta: %f' % y_delta
		print 'delta ratio'
		xy = x_delta / y_delta
		yx = y_delta / x_delta
		print '\tx/y: %f' % xy
		print '\ty/x: %f' % yx

		if abs(xy) > abs(yx):
			print 'x shift'
			if x_delta > 0:
				print 'right shift'
			elif x_delta < 0:
				print 'left shift'
			else:
				raise Exception("unlikely...somethings fishy")
		elif abs(xy) < abs(yx):
			print 'y shift'
			if y_delta > 0:
				print 'shift down'
			elif y_delta < 0:
				print 'shift up'
			else:
				raise Exception("unlikely...somethings fishy")
		else:
			raise Exception("unlikely...somethings fishy")

		return (x_delta, y_delta)

	def linear_pairs_gen(self):
		'''Generate each adjacent image pair allphabetically'''
		if len(self.image_file_names) <= 1:
			raise Exception('Not enough images')
		for i in range(0, len(self.image_file_names) - 1):
			yield (self.image_file_names[i], self.image_file_names[i + 1])

	def generate_control_points(self):
		'''
		Generate control points
		Generate to all neighbors to start with
		'''
		
		for pair in self.linear_pairs_gen():
			print 'Working on %s' % repr(pair)
			(x_delta, y_delta) = self.analyze_image_pair(pair)
			
		print 'pairs done, found %d' % len(self.sub_projects)
		
		self.project.merge_into(self.sub_projects)
		self.project.save()
		print 'Sub projects (full image):'
		for project in self.sub_projects:
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

