'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import line

'''
m g1 i0 f0 m2 p0.00784314
'''

class ModeLine(line.Line):
	def __init__(self, text, project):
		line.Line.__init__(self, text, project)
		
	def prefix(self):
		return 'm'
		
	def variable_print_order(self):
		return list(['g', 'i', 'f', 'm', 'p', 's'])
	
	def key_variables(self):
		return set()
	def int_variables(self):
		return set(['i', 'f', 'm', 's'])
	def float_variables(self):
		return set(['g', 'p'])
	def string_variables(self):
		return set()


	@staticmethod
	def from_line(line, pto_project):
		ret = ModeLine()
		ret.text = line
		return ret

