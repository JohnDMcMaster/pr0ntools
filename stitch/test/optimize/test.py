#!/usr/bin/env python

from pr0ntools.stitch.optimizer import PTOptimizer
from pr0ntools.stitch.pto.project import PTOProject
import shutil
import unittest

class OptimizeTest(unittest.TestCase):
    def setUp(self):
		# Copy the project to be a little paranoid
		shutil.copyfile('raw.pto', 'in.pto')
		
    def test_load(self):
		project = PTOProject.parse_from_file_name('in.pto')
		#self.assertTrue(project.text != None)
		self.assertEqual(len(project.image_lines), 4)
    
    def test_optimize_conversion(self):
		project = PTOProject.parse_from_file_name('in.pto')
		pt = project.to_ptoptimizer()
		#self.assertTrue(pt.text)
		
    def test_optimize(self):
		print 'Loading raw project...'
		project = PTOProject.parse_from_file_name('in.pto')
		print 'Creating optimizer...'
		optimizer = PTOptimizer(project)
		#self.assertTrue(project.text != None)
		print 'Running optimizer...'
		optimizer.run()

if __name__ == '__main__':
    unittest.main()

