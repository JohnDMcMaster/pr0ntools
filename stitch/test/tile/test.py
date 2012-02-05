#!/usr/bin/env python

from pr0ntools.stitch.tiler import Tiler
from pr0ntools.stitch.optimizer import PTOptimizer
from pr0ntools.stitch.pto.project import PTOProject
import shutil
import unittest
import os

class PtoTileTest(unittest.TestCase):
	def setUp(self):
		# Copy the project to be a little paranoid
		shutil.copyfile('source.pto', 'in.pto')
		
	def clean(self):
		if os.path.exists('out'):
			shutil.rmtree('out')
		
	def test_tile(self):
		'''
		Input should be 640 x 640
		This should result in 2.5 x 2.5 tiles which will be rounded up to 3 x 3 = 9 tiles
		'''
		self.clean()
		project = PTOProject.parse_from_file_name('in.pto')
		print 'Creating tiler'
		t = Tiler(project, 'out', 256, 256)
		print 'Running tiler'
		t.run()
		self.clean()

if __name__ == '__main__':
	unittest.main(verbosity=2)

