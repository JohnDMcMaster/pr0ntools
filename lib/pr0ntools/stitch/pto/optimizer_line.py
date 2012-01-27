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

class OptimizerLine(line.Line):
	def __init__(self, text, project):
		line.Line.__init__(self, text, project)
		
	def prefix(self):
		return 'o'
		
	def variable_print_order(self):
		return ['f', 'r', 'p', 'y', 'v', 'd', 'e', 'u', '+', '-']
	
	# o f0 r0 p0 y0 v51 d891633.755919 e-6050.673128 u10 +buf -buf
	def key_variables(self):
		return set()
	def int_variables(self):
		return set(['f', 'r', 'p', 'y', 'v', 'u'])
	def float_variables(self):
		return set(['d', 'e'])
	def string_variables(self):
		return set(['+', '-'])
		
		
	@staticmethod
	def from_line(line, pto_project):
		ret = Image()
		ret.text = line
		ret.reparse()
		return ret

	def get_index(self):
		i = 0
		for line in self.project.image_lines:
			if line is self:
				return i
			i += 1

