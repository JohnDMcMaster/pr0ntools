#!/usr/bin/env python

from pr0ntools.stitch.pto.project import PTOProject
from pr0ntools.stitch.pto.util import *
import shutil
import unittest
import os

class StitchUtilTest(unittest.TestCase):
	def setUp(self):
		# Copy the project to be a little paranoid
		shutil.copyfile('source.pto', 'in.pto')
		
	def tearDown(self):
		#self.clean()
		pass
		
	def test_center(self):
		project = PTOProject.from_file_name('in.pto')
		center(project)
		(ybar, xbar) = calc_center(project)
		print 'Final xbar %f, ybar %f' % (ybar, xbar)
		project.save()
		
	def test_center_anchor(self):
		project = PTOProject.from_file_name('in.pto')
		center_anchor(project)
		'''
		Image 4 at (1, 1) is the correct answer
		'''
		#vl = project.get_variable_lines()[4]
		project.save()
		
			
if __name__ == '__main__':
	unittest.main()



