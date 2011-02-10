'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

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
			prefix = default_prefix()
		if not suffix:
			suffix = ""
		# Good enough for now
		return prefix + rand_str(16) + suffix

class ManagedTempFile:
	file_name = None
	
	def __init__(self, file_name):
		if file_name:
			self.file_name = file_name
		else:
			self.file_name = TempFile.get()
	
	@staticmethod
	def get(prefix = None, suffix = None):
		return ManagedTempFile(TempFile.get(prefix, suffix))

	@staticmethod
	def from_existing(file_name):
		return ManagedTempFile(file_name)

	def __del__(self):
		os.rm(self.file_name)

class TempFileSet:
	prefix = None
	
	@staticmethod
	def get(prefix = None):
		if not prefix:
			prefix = TempFile.default_prefix()
		self.prefix = prefix


