'''
This file is part of pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools.jssim.options import Options
from util import get_js_file_header

class NodeName:
	def __init__(self, name=None, net=None):
		# string
		self.name = name
		# int
		self.net = net

	def run_DRC(self):
		pass
	
	def __repr__(self):
		# clk0: 4,
		return '%s: %u' % (self.name, self.net)

class NodeNames:
	def __init__(self):
		self.nodenames = list()
	
	def run_DRC(self):
		names = set(['gnd', 'vcc', 'clk0', 'reset'])
		found = set()
		for nodename in self.nodenames:
			name = nodename.name
			print 'Node %s => %u' % (name, nodename.net)
			if name in names:
				found.add(name)
		
		if not 'gnd' in found:
			raise Exception('Missing gnd node name')
		if not 'vcc' in found:
			raise Exception('Missing vcc node name')
		# Not strictly necessary but in all the designs I've done so far
		if not 'clk0' in found:
			raise Exception('Missing clk0 node name')
		if not 'reset' in found:
			print 'WARNING: missing reset node name'
			#raise Exception('Missing reset node name')
		
		pass
		
	def add(self, nodename):
		self.nodenames.append(nodename)
	
	def __repr__(self):
		'''Return nodenames.js content'''

		'''
		var nodenames ={
		gnd: 2,
		vcc: 1,
		out1: 3,
		in1: 4,
		clk0: 4,
		}
		'''

		ret = get_js_file_header(Options.JS_FILE_NODENAMES, Options.NODENAMES_VER)
		ret += 'var nodenames_ver = "%s";\n' % Options.NODENAMES_VER

		ret += 'var nodenames = {\n'				
		for nodename in self.nodenames:
			# Having , at end is acceptable
			ret += repr(nodename) + ',\n'		
		ret += '}\n'
		
		return ret

	def write(self):
		f = open(Options.JS_FILE_NODENAMES, 'w')
		f.write(self.__repr__())
		f.close()

