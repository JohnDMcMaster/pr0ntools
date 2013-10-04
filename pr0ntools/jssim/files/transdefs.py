'''
This file is part of pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools.jssim.options import Options
from util import get_js_file_header

class Transdef:
	'''
	WARNING: needs coordinates in lower left, standard is upper left
	
	(Ijor's?) comment from 6800's transdefs:
	/*
	 * The format here is
	 *   name
	 *   gate,c1,c2
	 *   bb (bounding box: xmin, xmax, ymin, ymax)
	 *   geometry (unused) (width1, width2, length, #segments, area)
	 *   weak (boolean) (marks weak transistors, whether pullups or pass gates)
	 *
	 * Note: the geometry is of the MOSFET channel: the two widths are
	 * the lengths of the two edges where the poly is crossing the active
	 * area. These will be equal if the channel is straight or makes an
	 * equal number of right and left turns. The number of segments should
	 * be 1 for a rectangular channel, or 2 for an L shape, 3 for a Z
	 * or U, and will allow for taking into account corner effects.
	 * 
	 * At time of writing JSSim doesn't use transistor strength information
	 * except to discard weak transistors and to treat pullups as
	 * described in segdefs.js specially.
	 *
	 */
	'''
	
	def __init__(self, name=None, gate=None, c1=None, c2=None, bb=None, geometry=None, weak=None):
		# string
		self.name = name
		# int
		self.gate = gate
		# int
		self.c1 = c1
		# int
		self.c2 = c2
		# 4 element list
		self.bb = bb
		# list / structure
		self.geometry = geometry
		# boolean
		self.weak = weak
	
		self.run_DRC()
		
	def run_DRC(self):
		pass

	def __repr__(self):
		#['t1',4,2,3,[176,193,96,144],[415,415,11,5,4566],false],
		ret = '['
		ret += "'%s',%u,%u,%u" % (self.name, self.gate, self.c1, self.c2)
		ret += ",[%u,%u,%u,%u]" % (self.bb[0], self.bb[1], self.bb[2], self.bb[3])
		ret += ",[%u,%u,%u,%u,%u]" % (self.geometry[0], self.geometry[1], self.geometry[2], self.geometry[3], self.geometry[4])
		if self.weak:
			ret += ",true"
		else:
			ret += ",false"
		ret += ']'
		return ret
		
class Transdefs:
	def __init__(self):
		self.transdefs = list()

	def __repr__(self):
		ret = get_js_file_header(Options.JS_FILE_TRANSDEFS, Options.TRANSDEFS_VER)
		ret += 'var segdefs_ver = "%s";\n' % Options.SEGDEFS_VER
		
		ret += 'var transdefs = [\n'
		for transdef in self.transdefs:
			# Having , at end is acceptable
			ret += repr(transdef) + ',\n'
		ret += ']\n'
		
		return ret
	
	def add(self, transdef):
		self.transdefs.append(transdef)
	
	def write(self):
		f = open(Options.JS_FILE_TRANSDEFS, 'w')
		f.write(self.__repr__())
		f.close()

