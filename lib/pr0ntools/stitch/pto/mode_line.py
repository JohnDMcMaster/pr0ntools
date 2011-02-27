'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

import line

class ModeLine(line.Line):
	def __init__(self, text, project):
		self.prefix = 'm'
		self.variable_print_order = list(['g', 'i', 'm', 'p', 's'])
		self.key_variables = set([])
		self.int_variables = set(['i', 'm', 's'])
		self.float_variables = set(['g', 'p'])
		self.string_variables = set([])

		line.Line.__init__(self, text, project)
		
	@staticmethod
	def from_line(line, pto_project):
		ret = ModeLine()
		ret.text = line
		return ret

