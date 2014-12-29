'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import line

'''
p f0 w921 h681 v89  E0 R0 S233,891,57,670 n"TIFF_m c:NONE"

S: crop
	S<left>,<right>,<top>,<bottom>
'''
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

	def set_fov(self, v):		
		self.set_variable('v', v)
		
	def fov(self):
		return self.get_variable('v')
		
	def set_crop(self, crop):
		self.set_variable('S', '%d,%d,%d,%d' % tuple(crop))
	
	def get_crop(self):
		'''Return (left, right, top, bottom) or None'''
		c = self.get_variable('S')
		#print 'got c to %s' % str(c)
		if c is None:
			return None
		c  = c.split(',')
		if len(c) != 4:
			raise Exception('Malformed S line')
		ret = [int(i) for i in c]
		return ret
		
	def width(self):
		c = self.get_crop()
		return c[0] - c[1]
	
	def left(self):
		c = self.get_crop()
		if c is None:
			return 0
		return c[0]
	
	def set_left(self, left):
		c = self.get_crop()
		c[0] = left
		self.set_crop(c)
		
	def right(self):
		c = self.get_crop()
		if c is None:
			return self.getv('w')
		return c[1]
	
	def set_right(self, right):
		c = self.get_crop()
		c[1] = right
		self.set_crop(c)
		
	def height(self):
		c = self.get_crop()
		return c[2] - c[3]
	
	def top(self):
		c = self.get_crop()
		if c is None:
			return 0
		return c[2]
	
	def set_top(self, top):
		c = self.get_crop()
		c[2] = top
		self.set_crop(c)
		
	def bottom(self):
		c = self.get_crop()
		if c is None:
			return self.getv('h')
		return c[3]
	
	def set_bottom(self, bottom):
		c = self.get_crop()
		c[3] = bottom
		self.set_crop(c)
	
	@staticmethod
	def from_line(line, pto_project):
		ret = PanoramaLine()
		ret.text = line
		return ret


