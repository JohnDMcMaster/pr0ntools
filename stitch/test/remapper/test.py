#!/usr/bin/env python

import shutil
import unittest
import os
from pr0ntools.stitch.pto.project import PTOProject
from pr0ntools.stitch.remapper import Remapper

class RemapperTest(unittest.TestCase):
	def setUp(self):
		self.clean()
		# Copy the project to be a little paranoid
		shutil.copyfile('source.pto', 'in.pto')
	
	def tearDown(self):
		self.clean()

	def clean(self):
		if os.path.exists('out'):
			shutil.rmtree('out')
			
	def test_single(self):
		print 'Single test'
		project = PTOProject.parse_from_file_name('in.pto')
		remapper = Remapper(project)
		remapper.image_type = Remapper.TIFF_SINGLE
		remapper.run()	
		self.clean()
	
	def test_multi(self):
		print 'Multi test'
		project = PTOProject.parse_from_file_name('in.pto')
		remapper = Remapper(project)
		remapper.image_type = Remapper.TIFF_SINGLE
		remapper.run()	
		self.clean()

if __name__ == '__main__':
	unittest.main()

