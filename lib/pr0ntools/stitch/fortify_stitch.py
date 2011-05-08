'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details

This is a stitching strategy where we already have a project, but think we can add more pairs
'''

from common_stitch import CommonStitch
import spatial_map

class FortifyStitch(CommonStitch):
	
	def __init__(self):
		self.tried_pairs = set()
		self.sub_projects = list()

		# Project we will take stuff from
		self.input_project = None	
		# for now just take params from previous since parsing issues
		# If nothing else this speeds things up anyway
		self.image_file_names = None
		self.tried_pairs = None
		self.spatial_map = None
		CommonStitch.__init__(self)
	
	'''
	@staticmethod
	def from_project(project):
		engine = FortifyStitch()
		engine.input_project = project
		return engine
	'''
	
	@staticmethod
	def from_wander(project, image_file_names, tried_pairs, spatial_map):
		engine = FortifyStitch()
		engine.input_project = project
		engine.image_file_names = image_file_names
		engine.tried_pairs = tried_pairs
		engine.spatial_map = spatial_map
		return engine

	'''
	@staticmethod
	def from_project_file_name(project_file_name):
		engine = FortifyStitch()
		engine.input_project = PTOProject.from_existing(project_file_name)
		return engine
	'''
	
	def gen_overlaps(self):
		for image_file_name in self.image_file_names:
			overlap_set = self.spatial_map.find_overlap(image_file_name, True)
			# No previous data?
			#if overlap_set is None:
			#	raise Exception('die')
				
			#print '%s: %d overlaps @ %s w/ %s' % (image_file_name, len(overlap_set), repr(self.spatial_map.points[image_file_name].coordinates), repr(self.spatial_map.points[image_file_name].sizes))
			for overlap in overlap_set:
				yield (image_file_name, overlap)

	def generate_control_points(self):
		print
		print
		print
		# Start by figuring out which image pairs already have points
		print 'Computing already tried image pairs'
		# HACK: done
		# Images themselves can be got from hugin project (in theory...)
		
		# Now build a xy geometric map
		# HACK: done
				
		# Find adjacent pairs and generate control points
		n_overlaps = len(list(self.gen_overlaps()))
		print 'Checking %d images with %d overlaps' % (len(self.image_file_names), n_overlaps)

		cur_overlap = 0
		for (image_file_name, overlap) in self.gen_overlaps():
			cur_overlap += 1
			print 'file name: %s, overlap: %s, %d / %d' % (image_file_name, overlap, cur_overlap, n_overlaps)
			temp_s = set(self.tried_pairs)
			if overlap[0] > overlap[1]:
				raise Exception('die')
			if overlap in temp_s:
				print 'Skipping already tried pair %s' % repr(overlap)
				continue
			
			print 'Trying pair %s' % repr(overlap)
			project = self.control_point_gen.generate_core(overlap)
			# Was just a guess, might not actually generate a match
			if project is None:
				continue
			project.hugin_form()
			self.sub_projects.append(project)
			self.tried_pairs.add(overlap)
		
		#raise Exception('debug')
		print 'Fortify project file name: ', self.project.get_a_file_name()
		self.project.get_a_file_name()
		#self.project.save()
		self.project.merge_into(self.sub_projects + [self.input_project])
		#self.project.merge_into(self.sub_projects)
		#self.project.merge_into([self.input_project])
		
		print 'Final print:'
		print self.project.get_text()
		#raise Exception('debug')
		print 'Saving'
		self.project.save()
		
