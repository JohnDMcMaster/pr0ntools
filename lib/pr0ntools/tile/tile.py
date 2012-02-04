#!/usr/bin/python
'''
pr0ntile: IC die image stitching and tile generation
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import sys 
import os.path
import pr0ntools.pimage
from pr0ntools.pimage import PImage
from pr0ntools.pimage import TempPImage
from pr0ntools.stitch.wander_stitch import WanderStitch
from pr0ntools.stitch.grid_stitch import GridStitch
from pr0ntools.stitch.fortify_stitch import FortifyStitch
from pr0ntools.execute import Execute

def from_multi(fn, max_level, min_level = 0):
	'''
	Stitch source images together and output tiles instead of a large panorama
	'''

def Tiler:
	def __init__(self, image, x0 = None, x1 = None, y0 = None, y1 = None, tw = 256, th = 256):
		self.image = image
		
		if x0 is None:
			x0 = 0
		self.x0 = x0
		if x1 is None:
			x1 = i.width()
		self.x1 = x1
		if y0 is None:
			y0 = 0
		self.y0 = y0
		if y1 is None:
			y1 = i.height()
		self.y1 = y1
		
		self.tw = tw
		self.th = th
		self.out_dir = None

	# FIXME / TODO: this isn't the google reccomended naming scheme, look into that more	
	# part of it was that I wanted them to sort nicely in file list view
	def get_name(self, row, col):
		out_dir = ''
		if self.out_dir:
			out_dir = '%s/' % self.out_dir
		return '%sy%03d_x%03d%s' % (out_dir, row, col, out_extension)
		
	def make_tile(self, x, y, row, col):
		xmin = x
		ymin = y
		xmax = min(xmin + self.tw, self.x1)
		ymax = min(ymin + self.th, self.y1)
		nfn = self.get_name(row, col)

		print '%s: (x %d:%d, y %d:%d)' % (nfn, xmin, xmax, ymin, ymax)
		ip = i.subimage(xmin, xmax, ymin, ymax)
		'''
		Images must be padded
		If they aren't they will be stretched in google maps
		'''
		if ip.width() != t_width or ip.height() != t_height:
			print 'WARNING: %s: expanding partial tile (%d X %d) to full tile size' % (nfn, ip.width(), ip.height())
			ip.set_canvas_size(t_width, t_height)
		ip.image.save(nfn)
		
	def run(self):
		'''
		Namer is a function that accepts the following arguments and returns a string:
		namer(row, col)
	
		python can bind objects to functions so a user parameter isn't necessary?
		'''
	
		if namer is None:
			namer = google_namer

		col = 0
		for x in xrange(self.x0, self.x1, self.tw):
			row = 0
			for y in xrange(self.y0, self.y1, self.th):
				self.make_tile(x, y, row, col)
				row += 1
			col += 1


def from_single(fn, max_level, min_level = 0, out_dir_base=None):
	t_width = 256
	t_height = 256
	out_extension = '.jpg'
	#out_extension = '.png'
	'''
	Expect that will not need images larger than 1 terapixel in the near future
	sqrt(1 T / (256 * 256)) = 3906, in hex = 0xF42
	so three hex digits should last some time
	'''
	if out_dir_base is None:
		out_dir_base = 'tiles_out/'
	
	'''
	Test file is the carved out metal sample of the 6522
	It is 5672 x 4373 pixels
	I might do a smaller one first
	'''
	i = PImage.from_file(fn)
	if os.path.exists(out_dir_base):
		os.system('rm -rf %s' % out_dir_base)
	os.mkdir(out_dir_base)
	for zoom_level in xrange(max_level, min_level - 1, -1):
		print
		print '************'
		print 'Zoom level %d' % zoom_level
		out_dir = '%s/%d' % (out_dir_base, zoom_level)
		if os.path.exists(out_dir):
			os.system('rm -rf %s' % out_dir)
		os.mkdir(out_dir)
		
		tiler = Tiler(i)
		tiler.run()
		
		if zoom_level != min_level:
			# Each zoom level is half smaller than previous
			i = i.get_scaled(0.5)
			if 0:
				i.save('test.jpg')
				sys.exit(1)


