'''
This file is part of pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

class Transistor:
	'''
	JSSim likes c1 more "interesting" than c2
	Try to make c1 be the variable connection and c2 constant if applicable
	'''
	
	def __init__(self, g=None, c1=None, c2=None):
		# These should be Net objects, not numbers
		# gate
		self.g = g
		# connection1
		self.c1 = c1
		# connection2
		self.c2 = c2
		
		# Rectangle (two Point's)
		self.rect_p1 = None
		self.rect_p2 = None
		self.weak = None
	
	def set_bb(self, point1, point2):
		self.rect_p1 = point1
		self.rect_p2 = point2

	def __repr__(self):
		return 'c1: %u, g: %u, c2: %u, weak: %s' % (self.c1.number, self.g.number, self.c2.number, repr(self.weak))
	
class Transistors:
	def __init__(self):
		# no particular order
		self.transistors = set()
	
	def add(self, transistor):
		self.transistors.add(transistor)


