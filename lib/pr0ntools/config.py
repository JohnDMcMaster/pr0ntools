'''
pr0ntools
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import json
import os

class Config:
	def __init__(self, fn = None):
		if fn is None:
			fn = Config.get_default_fn()
		self.json = json.loads(open(fn).read())
	
	@staticmethod
	def get_default_fn():
		return os.getenv('HOME') + '/' + '.pr0nrc'
	
	def get(self, k, default = None):
		if k in self.json:
			return self.json[k]
		else:
			return default
	
	def keep_temp_files(self):
		return self.get('keep_temp', 0)

config = Config()

