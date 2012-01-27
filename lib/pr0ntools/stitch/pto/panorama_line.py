'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import line

class PanoramaLine(line.Line):
	def __init__(self, text, project):
		line.Line.__init__(self, text, project)

	def prefix(self):
		return 'p'
		
	def variable_print_order(self):
		return list(['w', 'h', 'f', 'v', 'n', 'u', 'k', 'b', 'd', 'E', 'R', 'T', 'S', 'P'])
	
	def key_variables(self):
		return set()
	def int_variables(self):
		return set(['w', 'h', 'f', 'v', 'u', 'k', 'b', 'd', 'R'])
	def float_variables(self):
		return set(['E'])
	def string_variables(self):
		return set(['n', 'T', 'P', 'S'])

		
	@staticmethod
	def from_line(line, pto_project):
		ret = PanoramaLine()
		ret.text = line
		return ret

