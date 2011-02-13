'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

import random
import os

class TempFile:
	@staticmethod
	def default_prefix():
		return "/tmp/pr0ntools_"

	@staticmethod
	def rand_str(length):
		ret = ''
		for i in range(0, length):
			ret += "%X" % random.randint(0, 15)
		return ret

	@staticmethod
	def get(prefix = None, suffix = None):
		if not prefix:
			prefix = TempFile.default_prefix()
		if not suffix:
			suffix = ""
		# Good enough for now
		return prefix + TempFile.rand_str(16) + suffix

class ManagedTempFile:
	file_name = None
	
	def __init__(self, file_name):
		if file_name:
			self.file_name = file_name
		else:
			self.file_name = TempFile.get()
	
	def __repr__(self):
		return self.file_name
	
	@staticmethod
	def get(prefix = None, suffix = None):
		return ManagedTempFile(TempFile.get(prefix, suffix))

	@staticmethod
	def from_existing(file_name):
		return ManagedTempFile(file_name)

	def __del__(self):
		try:
			if os.path.exists(self.file_name):
				# os.remove(self.file_name)
				print 'Deleted temp file %s' % self.file_name
			else:
				print "Didn't delete inexistant temp file %s" % self.file_name
		# Ignore if it was never created
		except:
			print 'WARNING: failed to delete temp file: %s' % self.file_name

class TempFileSet:
	prefix = None
	
	@staticmethod
	def get(prefix = None):
		if not prefix:
			prefix = TempFile.default_prefix()
		self.prefix = prefix


