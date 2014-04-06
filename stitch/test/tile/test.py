#!/usr/bin/env python

from pr0ntools.geometry import floor_mult, ceil_mult
from pr0ntools.stitch.tiler import Tiler
from pr0ntools.stitch.optimizer import PTOptimizer
from pr0ntools.stitch.pto.project import PTOProject
import shutil
import unittest
import os

class PtoTileTest(unittest.TestCase):
	def setUp(self):
		self.clean()
		# Copy the project to be a little paranoid
		shutil.copyfile('source.pto', 'in.pto')
		
	def tearDown(self):
		#self.clean()
		pass
		
	def clean(self):
		if os.path.exists('out'):
			shutil.rmtree('out')
		
	def test_floor_mult(self):
		self.assertEqual(floor_mult(0, 256), 0)
		self.assertEqual(floor_mult(1, 256), 0)
		self.assertEqual(floor_mult(2, 256), 0)
		self.assertEqual(floor_mult(255, 256), 0)
		self.assertEqual(floor_mult(256, 256), 256)
		self.assertEqual(floor_mult(257, 256), 256)
		self.assertEqual(floor_mult(258, 256), 256)
		
		
		self.assertEqual(floor_mult(1, 256, 1), 1)
		self.assertEqual(floor_mult(2, 256, 1), 1)
		self.assertEqual(floor_mult(3, 256, 1), 1)
		self.assertEqual(floor_mult(256, 256, 1), 1)
		self.assertEqual(floor_mult(257, 256, 1), 257)
		self.assertEqual(floor_mult(258, 256, 1), 257)
		self.assertEqual(floor_mult(259, 256, 1), 257)
		
	def test_ceil_mult(self):
		self.assertEqual(ceil_mult(0, 256), 0)
		self.assertEqual(ceil_mult(1, 256), 256)
		self.assertEqual(ceil_mult(2, 256), 256)
		self.assertEqual(ceil_mult(255, 256), 256)
		self.assertEqual(ceil_mult(256, 256), 256)
		self.assertEqual(ceil_mult(257, 256), 512)
		self.assertEqual(ceil_mult(258, 256), 512)
		
		
		self.assertEqual(ceil_mult(0, 256, 1), 1)
		self.assertEqual(ceil_mult(1, 256, 1), 1)
		self.assertEqual(ceil_mult(2, 256, 1), 257)
		self.assertEqual(ceil_mult(3, 256, 1), 257)
		self.assertEqual(ceil_mult(256, 256, 1), 257)
		self.assertEqual(ceil_mult(257, 256, 1), 257)
		self.assertEqual(ceil_mult(258, 256, 1), 513)
		self.assertEqual(ceil_mult(259, 256, 1), 513)
		
	def test_tile_dry(self):
		'''
		Inputs are 1632 x 1224
		a 3 x 3 grid allows testing edge boundary conditions as well as internal
		The reference fully stitched image is 3377 x 2581
		'''
		project = PTOProject.parse_from_file_name('in.pto')
		print 'Creating tiler'
		t = Tiler(project, 'out', st_scalar_heuristic=2)
		#iw = 1632
		#ih = 1224
		#t.set_size_heuristic(iw, ih)
		'''
		Should make 4 tiles with 3 X 3
		'''
		#t.super_tw = 2 * iw
		#t.super_th = 2 * ih
		'''
		Each supertile should cover two images as setup
		There will be some overlap in the center and unique area on all four edges
		'''
		self.assertEqual(len(list(t.gen_supertiles())), 4)
		print 'Unit test running tiler (real)'
		t.dry = True
		t.run()

	def test_tile_real(self):
		project = PTOProject.parse_from_file_name('in.pto')
		print 'Creating tiler'
		t = Tiler(project, 'out', st_scalar_heuristic=2)
		self.assertEqual(len(list(t.gen_supertiles())), 4)
		print 'Unit test running tiler (real)'
		t.run()
			
if __name__ == '__main__':
	unittest.main()

