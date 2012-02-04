'''
pr0ntools
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''
'''
This class takes in a .pto project and does not modify it or any of the perspective parameters it specifies
It produces a series of output images, each a subset within the defined crop area
Pixels on the edges that don't fit nicely are black filled

Crop ranges are not fully inclusive
	ex: 0:255 results in a 255 width output, not 256

Arbitrarily assume that the right and bottom are the ones that aren't



This requires the following to work (or at least well):
-Source images must have some unique portion
	If they don't there is no natural "safe" region that can be blended separately
This works by forming larger tiles and then splitting them into smaller tiles


New strategy
Construct a spatial map using all of the images
Define an input intermediate tile width, height
	If undefined default to 3 * image width/height
	Note however, the larger the better (of course full image is ideal)
Define a safe buffer zone heuristic
	Nothing in this area shared with other tiles will be kept
	It will be re-generated as we crawl along and the center taken out
	
	In my images 1/3 of the image should be unique
	The assumption I'm trying to make is that nona will not try to blend more than one image away
	The default should be 1 image distance
	
Keep a closed set (and open set?) of all of the tiles we have generated
Each time we construct a new stitching frame only re-generate tiles that we actually need
This should simplify a lot of the bookkeeping, especially as things get hairy
At the end check that all times have been generated and throw an error if we are missing any
Greedy algorithm to generate a tile if its legal (and safe)
'''

from pr0ntools.stitch.remapper import Remapper
from pr0ntools.stitch.pto.project import PTOProject
import os
from image_coordinate_map import ImageCoordinateMap
from pr0ntools.temp_file import ManagedTempFile

def ceil_mult(n, mult):
	rem = n % mult
	if rem == 0:
		return n
	else:
		return n + mult - rem

def PartialStitcher:
	def __init__(self, pto, bounds, out):
		self.pto = pto
		self.bounds = bounds
		self.out = out
		
	def run(self):
		'''
		Phase 1: remap the relevant source image areas onto a canvas
		'''
		
		pto = self.pto.copy()
		print 'Making absolute'
		pto.make_absolute()
		
		print 'Cropping...'
		#sys.exit(1)
		pl = pto.get_panorama_line()
		# It is fine to go out of bounds, it will be black filled
		#pl.set_bounds(x, min(x + self.tw(), pto.right()), y, min(y + self.th(), pto.bottom()))
		pl.set_crop(bounds)
		remapper = Remapper(pto)
		remapper.remap(out_name_base)
		
		'''
		Phase 2: blend the remapped images into an output image
		'''
		blender = Blender(remapper.get_output_files(), self.out)
		blender.run()


class Tiler:
	def __init__(self, pto, out_dir, tile_width=250, tile_height=250):
		self.pto = pto
		self.out_dir = out_dir
		self.tw = tile_width
		self.th = tile_height
		self.map = None
	
	def build_spatial_map(self):
		#image_file_names = self.pto.get_file_names()
		#self.map = ImageCoordinateMap.from_file_names(image_file_names)
		
		items = [PolygonQuadTreeItem(il.left(), il.right(), il.top(), il.bottom()) for il in self.pto.get_image_lines()]
		self.map = PolygonQuadTree(items)	
	
	def run(self):
		'''
		if we have a width of 256 and 1 pixel we need total size of 256
		If we have a width of 256 and 256 pixels we need total size of 256
		if we have a width of 256 and 257 pixel we need total size of 512
		'''
		spl = self.pto.get_panorama_line()
		print 'Tile width: %d, height: %d' % (self.tw, self.th)
		print spl
		print 'Left: %d, right: %d, top: %d, bottom: %d' % (spl.left(), spl.right(), spl.top(), spl.bottom())
		x0 = spl.left()
		x1 = ceil_mult(spl.right(), self.tw)
		y0 = spl.top()
		y1 = ceil_mult(spl.bottom(), self.th)
		
		os.mkdir(self.out_dir)
		
		#temp_file = 'partial.tif'
		temp_file = ManagedTempFile.get(None, '.tif')
		
		# 0:256 generates a 256 width pano
		# therefore, we don't want the upper bound included
		col = 0
		for x in xrange(x0, x1, self.tw):
			row = 0
			for y in xrange(y0, y1, self.th):
				out_name_base = "%s/r%03d_c%03d" % (self.out_dir, row, col)
				print 'Working on %s' % out_name_base
				bounds = [x, x + self.tw, y, y + self.th]
				stitcher = PartialStitcher(self.pto, bounds, temp_file)
				stitcher.run()
				
				row +=1 	
			col += 1
				
				
