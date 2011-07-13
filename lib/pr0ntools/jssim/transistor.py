'''
This file is part of pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

# FIXME: why don't the static constructors work from within the same class?
class TechnologyW:
	def __init__(self, has_nmos, has_pmos, has_bipolar):
		self.nmos = has_nmos
		self.pmos = has_pmos
		self.bipolar = has_bipolar

	def has_nmos(self):
		return self.nmos

	def has_pmos(self):
		return self.pmos
		
	def has_bipolar(self):
		return self.bipolar


class Technology:
	'''
	By no means a comprehensive list, just a start of what *might* be needed in near future
	'''
	
	# Just kidding
	# ROCK = TechnologyW(False, False, False)
	INVALID = None
	# Uses bipolar transistors (ex: TTL)
	BIPOLAR = TechnologyW(False, False, True)
	# N-channel MOS
	NMOS = TechnologyW(True, False, False)
	# P-channel MOS
	PMOS = TechnologyW(False, True, False)
	# N-channel and P-channel MOS on the same chip
	CMOS = TechnologyW(True, True, False)
	# BiCMOS: mix of bipolar and CMOS
	BICMOS = TechnologyW(True, True, True)
	
	@staticmethod
	def from_string(s):
		s = s.upper()
		if s == "BIPOLAR":
			return Technology.BIPOLAR
		elif s == "NMOS":
			return Technology.NMOS
		elif s == "PMOS":
			return Technology.PMOS
		elif s == "CMOS":
			return Technology.CMOS
		elif s == "BICMOS":
			return Technology.BICMOS
		else:
			return Technology.INVALID
'''
Not really needed for anything yet
class LogicFamily:
	INVALID = 0
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


