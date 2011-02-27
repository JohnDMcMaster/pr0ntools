'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
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
		self.prefix = 'c'
		self.variable_print_order = list(['n', 'N', 'x', 'y', 'X', 'Y', 't'])
		self.key_variables = set([])
		self.int_variables = set(['n', 'N', 't'])
		self.float_variables = set(['x', 'y', 'X', 'Y'])
		self.string_variables = set([])

		line.Line.__init__(self, text, project)

	@staticmethod
	def from_line(line, pto_project):
		ret = ControlPointLine()
		ret.text = line
		ret.reparse()
		return ret
	
	def update(self):
		if not self.lower_image:
			self.lower_image = self.project.index_to_image(self.get_variable('n'))
		else:
			self.set_variable('n', self.lower_image.image.get_index())
			self.set_variable('x', self.lower_image.x)
			self.set_variable('y', self.lower_image.y)

		if not self.upper_image:
			self.upper_image = self.project.index_to_image(self.get_variable('n'))
		else:
			self.set_variable('N', self.upper_image.image.get_index())
			self.set_variable('X', self.upper_image.x)
			self.set_variable('Y', self.upper_image.y)

