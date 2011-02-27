'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

import line

class PanoramaLine(line.Line):
	def __init__(self, text, project):
		self.prefix = 'p'
		self.variable_print_order = list(['w', 'h', 'f', 'v', 'n', 'u', 'k', 'b', 'd', 'E', 'R', 'T', 'S', 'P'])
		self.key_variables = set([])
		self.int_variables = set(['w', 'h', 'f', 'v', 'u', 'k', 'b', 'd', 'R'])
		self.float_variables = set(['E'])
		self.string_variables = set(['n', 'T', 'P', 'S'])

		line.Line.__init__(self, text, project)
		
	@staticmethod
	def from_line(line, pto_project):
		ret = PanoramaLine()
		ret.text = line
		return ret

