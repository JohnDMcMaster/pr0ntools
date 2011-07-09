'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import shutil
import os
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.execute import Execute
from util import print_debug

class Line:
	# Variables for the line as dict
	# If a value is not set, it should not have the key even present
	# If a key is present and value is None, indicates it is a key only variable
	variables = dict()
	# Original raw text as string
	text = None
	# Really does seem easiest to just have this here
	project = None
	# Comments that went above this line
	comments = list()
	
	# The following should be fixed for a type
	# The letter that identifies the line
	prefix = None
	# List which specifies order in which variables must be printed
	# Leftover is printed at end
	variable_print_order = None
	# No value, just a key
	key_variables = set()
	# Which variables are int values
	int_variables = set()
	float_variables = set()
	# Contains a quoted string
	# Quotes are needed to distinguish the data from the key
	string_variables = set()

	def __init__(self, text, project):
		self.text = text.strip()
		self.project = project
		self.reparse()
	
	# this doesn't distingiush between a key only and not present
	def get_variable(self, k):
		if not k in self.variables:
			return None
		ret = self.variables[k]
		if ret is None:
			raise Exception('should not have an empty value on a value fetch')
		return ret 
	
	def set_variable(self, k, v = None):
		'''
		if v is None:
			if k in self.variables:
				del self.variables[k]
		else:
			self.variables[k] = v
		'''
		self.variables[k] = v
		
	def remove_variable(self, k):
		self.variables[k] = None

	def update(self):
		'''If variables have relocations, update them'''
		pass

	def print_variable(self, k):
		if not k in self.variables:
			return ''
		
		# Single type?
		v = self.variables[k]
		if v is None:
			if not k in self.key_variables:
				raise Exception('not key variable')
			return k
		
		# Regular key/value type then
		if k in self.string_variables:
			return '%s"%s"' % (k, v)
		# Some other type, convert to string
		else:
			return '%s%s' % (k, v)

	def __repr__(self):
		'''The primary line, ie not including any comments'''
		
		self.update()
	
		print_debug()
		print_debug('original: %s' % self.text)
		print_debug('variables: %s' % self.variables)
	
		ret = self.prefix
		
		printed = set()
		if self.variable_print_order:
			for k in self.variable_print_order:
				if k in self.variables:
					v = self.variables[k]
					print_debug('k: %s, v: %s' % (repr(k), repr(v)))
					printed.add(k)
					ret += ' %s' % self.print_variable(k)
		else:
			print 'WARNING; no variable print order'
		
		for k in self.variables:
			if k in printed:
				continue
			ret += ' %s' % self.print_variable(k)
		
		print_debug('final: %s' % ret)
		
		return ret

	def get_tokens(self):
		'''
		Returns a list of (k, v) pairs
		If it has no v, v will be None
		
		Tokens can have quotes around them
		Ex:
		n"TIFF c:NONE r:CROP"
		
		Internally, we do not store these
		Instead, they will be re-added when writing
		'''
		tokens = list()
		i = 0
		while i < len(self.text):
			k = ''
			v = None
			
			# Find the key: keep going until we hit either ", number, or space
			while i < len(self.text):
				c = self.text[i]
				# End of this k/v?
				if c == ' ':
					i += 1
					break
				# A quoted value?
				elif c == '"':
					i += 1
					v = ''
					# Note we skip the "
					while True:
						if i >= len(self.text):
							raise Exception('Missing closing " on %s' % self.text)
						c = self.text[i]
						if c == '"':
							i += 1
							break
						v += c
						i += 1
					# Think we should have at most one quoted thingy
					break
				# A numeric value?
				elif c in '+-0123456789':
					v = ''
					# Note we include the original char
					while i < len(self.text):
						c = self.text[i]
						if c == ' ':
							i += 1
							break
						v += c
						i += 1
					break
				else:
					k += c
						
				i += 1

			# Discard extra spaces and some other corner cases
			if len(k) > 0 :
				tokens.append((k, v))
		print_debug(tokens)
		return tokens
		
	def reparse(self):
		self.variables = dict()
		first = True
		#for token in self.text.split(' '):
		for (k, v) in self.get_tokens():
			#print 'token: "%s"' % token
			#k = token[0]
			#v = token[1:]
			print_debug('k: %s, v: %s' % (repr(k), repr(v)))
			
			# We can still have empty string
			if not v is None and len(v) == 0:
				v = None
			if first:
				prefix = k
				if not v is None and len(v) > 0:
					print 'Line: %s' % self.text
					print 'ERROR: line type should not have value: %s' % repr(v)
					raise Exception('confused')
				first = False
				continue
			
			# Convert if possible
			try:
				if k in self.key_variables:
					pass
				elif k in self.int_variables:
					v = int(v)
				elif k in self.float_variables:
					v = float(v)
				elif k in self.string_variables:
					# Already in string form
					pass
				else:
					print 'WARNING: unknown data type on %s' % k
			except:
				print 'line: %s' % self.text
				print 'key: %s, value: %s' % (repr(k), repr(v))
				raise
				
			# Ready to roll
			self.set_variable(k, v)

