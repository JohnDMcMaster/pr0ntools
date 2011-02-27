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

class VariableLine(line.Line):
	# Need to know image index to write these
	image = None
	
	def __init__(self, text, project):
		# We need to parse this
		#self.image = image

		self.prefix = 'v'
		self.variable_print_order = list(['d', 'e', 'p', 'r', 'x', 'y'])
		self.key_variables = set([])
		self.int_variables = set(['d', 'e', 'p', 'r', 'x', 'y'])
		self.float_variables = set([])
		self.string_variables = set([])

		line.Line.__init__(self, text, project)
		
	@staticmethod
	def from_line(line, project):
		return VariableLine(line, project)

	def update(self):
		# Update to the correct indexes
		# Wonder if this can all go on a single line?
		# Would validate my k/v paradigm
		if not self.image:
			# See if we can parse it then
			image_index = None
			# All index should be consistent
			for k in self.variables:
				v = self.variables[k]
				if image_index is None:
					image_index = v
				else:
					if not image_index == v:
						raise Exception("index mismatch")
			# Maybe one of those dumb (useless I think) empty v lines Hugin puts out
			if image_index is None:
				# In this case, there is nothing to update
				return None
			self.image = self.project.index_to_image(image_index)
		
			# Since we just parsed, we should already be in sync
			return
			
		for k in self.variables:
			self.set_variable(k, self.image.get_index())

