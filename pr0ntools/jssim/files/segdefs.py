'''
This file is part of pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools.jssim.layer import Layer
from pr0ntools.jssim.options import Options
from util import get_js_file_header

class Segdef:
	'''
	WARNING: needs coordinates in lower left, standard is upper left
	
	defines an array segdefs[], with a typical element 
	[4,'+',1,4351,8360,4351,8334,4317,8334,4317,8360], 
	giving the 
		node number, 
		the pullup status, 
		the layer index 
		and a list of coordinate pairs for a polygon. 
		There is one element for each polygon on the chip, and therefore generally several elements for each node. The pullup status can be '+' or '-' and should be consistent for all of a node's entries - it's an historical anomaly that this information is in segdefs. Not all chip layers or polygons appear in segdefs, but enough layers appear for an appealing and educational display. 

	Format:
	[ 
		[0]: w: net/node name.  Can also be special ngnd and npwr?,
			ngnd = nodenames['gnd'];
			npwr = nodenames['vcc'];
		[1]: '+' if pullup,
		[2]: layer number,
		[3+]: segs array
	'''
	def __init__(self, net=None, pullup=None, layer_index=None, coordinates=None):
		# TODO: move these checks to DRCfrom util import get_js_file_header

		
		# Integer value
		self.net = net
		# Character ('+' or '-')
		self.pullup = pullup
		# Integer
		self.layer_index = layer_index
		# Integer array (not float)
		self.coordinates = coordinates
		
		self.run_DRC()

	def run_DRC(self):
		if self.net is None:
			raise Exception('Require net')
		if not type(self.net) is int:
			print self.net
			raise Exception('Require net as int')
			
		if self.pullup is None:
			raise Exception('Require pullup')
		if not (self.pullup == '+' or self.pullup == '-'):
			raise Exception('Require pullup +/-, got ' + self.pullup)
			
		if self.layer_index is None:
			raise Exception('Require layer index')
		if not Layer.is_valid(self.layer_index):
			raise Exception('Invalid layer index ' + repr(self.layer_index))

		if self.coordinates is None:
			raise Exception('Require coordinates')
		if len(self.coordinates) % 2 is not 0:
			raise Exception('Require even number of coordinates, got ' + self.coordinates)
		# Technically you can have negative coordinates, but you shouldn't be using them
		for coordinate in self.coordinates:
			if coordinate < 0:
				raise Exception('Prefer positive coordinates, got ' + coordinate)

	def __repr__(self):
		ret = ''
		#print 'net: ' + repr(self.net)
		ret += "[%u,'%c',%u" % (self.net, self.pullup, self.layer_index)
		for coordinate in self.coordinates:
			ret += ',%u' % coordinate
		ret += ']'
		return ret
		
class Segdefs:
	def __init__(self):
		self.segdefs = list()
	
	def run_DRC(self):
		for segdef in self.segdefs:
			segdef.run_DRC()
		
	def __repr__(self):
		'''Return segdefs.js content'''
		'''
		Should be written in the following layer order:
		-1: diffusion
		-3: grounded diffusion
		-4: powered diffusion
		-5: poly
		-0: metal (semi transparent)
		
		Since only metal is semi-transparent, its probably the only one that needs to be ordered (last)
		None of the other polygons should overlap (sounds like a DRC)
		'''
		
		ret = get_js_file_header(Options.JS_FILE_SEGDEFS, Options.SEGDEFS_VER)
		ret += 'var segdefs_ver = "%s";\n' % Options.SEGDEFS_VER
		
		ret += 'var segdefs = [\n'		
		for segdef in self.segdefs:
			# Having , at end is acceptable
			ret += segdef.__repr__() + ',\n'
		ret += ']\n'
		
		return ret

	def write(self):
		f = open(Options.JS_FILE_SEGDEFS, 'w')
		f.write(self.__repr__())
		f.close()

