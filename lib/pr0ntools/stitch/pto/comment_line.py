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

class CommentLine(line.Line):
	
	def __init__(self, text, project):
		self.prefix = '#'
		self.variable_print_order = set([])
		self.key_variables = set([])
		self.int_variables = set([])
		self.float_variables = set([])
		self.string_variables = set([])

		line.Line.__init__(self, text, project)
		
	@staticmethod
	def from_line(line, pto_project):
		ret = CommentLine()
		ret.text = line
		return ret

