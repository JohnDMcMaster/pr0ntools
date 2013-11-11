'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details

This is the most basic stitching strategy: throw every image at once into the tool
'''
import os
from pr0ntools.stitch.pto.util import fixup_i_lines, fixup_p_lines, optimize_xy_only
from common_stitch import CommonStitch
from pr0ntools.stitch.control_point import ajpto2pto_text_simple

class AllStitch(CommonStitch):
	def __init__(self):
		CommonStitch.__init__(self)
		self.canon2orig = dict()
		
	@staticmethod
	def from_file_names(image_file_names, depth = 1):
		engine = AllStitch()
		engine.image_file_names = image_file_names
		print 'Orig file names: %s' % str(image_file_names)
		
		'''
		Certain program take file names relative to the project file, others to working dir
		Since I like making temp files in /tmp so as not to clutter up working dir, this doesn't work well
		Only way to get stable operation is to make all file paths canonical
		'''
		file_names_canonical = list()
		for file_name in image_file_names:
			new_fn = os.path.realpath(file_name)
			engine.canon2orig[new_fn] = file_name
			file_names_canonical.append(new_fn)
		return engine
	
	@staticmethod
	def from_tagged_file_names(image_file_names):
		engine = AllStitch()
		engine.image_file_names = image_file_names
		print 'Orig file names: %s' % str(image_file_names)
		
		file_names_canonical = list()
		for file_name in image_file_names:
			new_fn = os.path.realpath(file_name)
			engine.canon2orig[new_fn] = file_name
			file_names_canonical.append(new_fn)
		
		return engine

	def generate_control_points(self):
		# Returns a pto project object
		self.control_point_gen.invalidate_on_ransac = False
		self.control_point_gen.print_output = True
		
		project = self.control_point_gen.generate_core(self.image_file_names)
		if project is None:
			raise Exception('stitch failed')
		oto_text = str(project)
		print oto_text
		# are we actually doing anything useful here?
		# The original intention was to make dead sure we had the right file order
		# but I'm pretty sure its consistent and we don't need to parse the comments
		self.project = ajpto2pto_text_simple(oto_text)
		if not self.project:
			raise Exception('Failed AJ pto conversion')
		
		print 'Images in project'
		for il in self.project.get_image_lines():
			print '  ' + il.get_name()
		
		print 'Post stitch fixup...'
		optimize_xy_only(self.project)
		fixup_i_lines(self.project)
		fixup_p_lines(self.project)
		
		'''
		# Fixup the canonical hack
		for can_fn in self.canon2orig:
			# FIXME: if we have issues with images missing from the project due to bad stitch
			# we should add them (here?) instead of throwing an error
			orig = self.canon2orig[can_fn]
			il = self.project.get_image_by_fn(can_fn)
			if il:
				il.set_name(orig)
			else:
				print 'WARNING: adding image without feature match %s' % orig
				self.project.add_image(orig)
		'''
		if self.output_project_file_name:
			self.project.set_file_name(self.output_project_file_name)
		self.project.save()
