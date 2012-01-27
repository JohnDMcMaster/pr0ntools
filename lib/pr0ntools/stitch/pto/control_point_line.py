'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import os
import shutil
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.execute import Execute
import line

class ControlPointLine(line.Line):
	# c n0 N1 x1444.778035 y233.742619 X1225.863118 Y967.737131 t0
	# Both of type ControlPointLineImage
	# Coordinates are increasing from upper left of image
	lower_image = None
	upper_image = None

	def __init__(self, text, project):
		line.Line.__init__(self, text, project)

	def prefix(self):
		return 'c'
		
	def variable_print_order(self):
		return list(['n', 'N', 'x', 'y', 'X', 'Y', 't'])
	
	def key_variables(self):
		return set()
	def int_variables(self):
		return set(['n', 'N', 't'])
	def float_variables(self):
		return set(['x', 'y', 'X', 'Y'])
	def string_variables(self):
		return set()

	@staticmethod
	def from_line(line, pto_project):
		ret = ControlPointLine()
		ret.text = line
		ret.reparse()
		return ret
	
	def update(self):
		# Do we not have the image entry?
		if not self.lower_image:
			print 'Missing lower image, creating'
			# Then get/create one
			self.lower_image = self.project.index_to_image(self.get_variable('n'))
		else:
			self.set_variable('n', self.lower_image.get_index())
			# whats with these lines?
			#self.set_variable('x', self.lower_image.x())
			#self.set_variable('y', self.lower_image.y())

		if not self.upper_image:
			self.upper_image = self.project.index_to_image(self.get_variable('N'))
		else:
			self.set_variable('N', self.upper_image.get_index())
			#self.set_variable('X', self.upper_image.x())
			#self.set_variable('Y', self.upper_image.y())

		if self.get_variable('n') == self.get_variable('N'):
			raise Exception('Cannot have point match self')

