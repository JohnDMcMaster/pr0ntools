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
#from pr0ntiles.tile import Tiler as TilerCore

def floor_mult(n, mult):
	rem = n % mult
	if rem == 0:
		return n
	else:
		return n - rem

def ceil_mult(n, mult):
	rem = n % mult
	if rem == 0:
		return n
	else:
		return n + mult - rem

class PartialStitcher:
	def __init__(self, pto, bounds, out):
		self.pto = pto
		self.bounds = bounds
		self.out = out
		
	def run(self):
		'''
		Phase 1: remap the relevant source image areas onto a canvas
		'''
		if self.out.find('.') < 0:
			raise Exception('Require image extension')
		# Hugin likes to use the base filename as the intermediates, lets do the sames
		out_name_base = self.out[self.out.find('.')]
		
		pto = self.pto.copy()
		print 'Making absolute'
		pto.make_absolute()
		
		print 'Cropping...'
		#sys.exit(1)
		pl = pto.get_panorama_line()
		# It is fine to go out of bounds, it will be black filled
		#pl.set_bounds(x, min(x + self.tw(), pto.right()), y, min(y + self.th(), pto.bottom()))
		pl.set_crop(self.bounds)
		remapper = Remapper(pto)
		remapper.remap(out_name_base)
		
		'''
		Phase 2: blend the remapped images into an output image
		'''
		blender = Blender(remapper.get_output_files(), self.out)
		blender.run()

# For managing the closed list		

class Tiler:
	def __init__(self, pto, out_dir, tile_width=250, tile_height=250):
		img_width = 3224
		img_height = 2448
		
		self.pto = pto
		self.out_dir = out_dir
		self.tw = tile_width
		self.th = tile_height
		
		self.set_size_heuristic(img_width, img_height)
		# These are less related
		# They actually should be set as high as you think you can get away with
		# Although setting a smaller number may have higher performance depending on input size
		self.super_tw = img_width * 4
		self.super_th = img_height * 4
		
		# We build this in run
		self.map = None
		
		spl = self.pto.get_panorama_line()
		self.x0 = spl.left()
		self.x1 = spl.right()
		self.y0 = spl.top()
		self.y1 = spl.bottom()
		#print spl
	
	def set_size_heuristic(self, image_width, image_height):
		'''
		The idea is that we should have enough buffer to have crossed a safe area
		If you take pictures such that each picture has at least some unique area (presumably in the center)
		it means that if we leave at least one image width/height of buffer we should have an area where enblend is not extending to
		Ultimately this means you lose 2 * image width/height on each stitch
		so you should have at least 3 * image width/height for decent results
		'''
		self.clip_width = image_width
		self.clip_height = image_height
	
	def build_spatial_map(self):
		#image_file_names = self.pto.get_file_names()
		#self.map = ImageCoordinateMap.from_file_names(image_file_names)
		
		items = [PolygonQuadTreeItem(il.left(), il.right(), il.top(), il.bottom()) for il in self.pto.get_image_lines()]
		self.map = PolygonQuadTree(items)	
	
	def try_supertile(self, x0, x1, y0, y1):
		'''x0/1 and y0/1 are global absolute coordinates'''
		# First generate all of the valid tiles across this area to see if we can get any useful work done?
		# every supertile should have at least one solution or the bounds aren't good
		
		temp_file = ManagedTempFile.get(None, '.tif')

		bounds = [x0, x1, y0, y1]
		#out_name_base = "%s/r%03d_c%03d" % (self.out_dir, row, col)
		#print 'Working on %s' % out_name_base
		stitcher = PartialStitcher(self.pto, bounds, temp_file.file_name)
		stitcher.run()
		
		i = PImage.from_file(fn)
		new = 0
		
		'''
		There is no garauntee that our supertile is a multiple of our tile size
		This will particularly cause issues near the edges if we are not careful
		'''
		xt0 = ceil_mult(x0, self.tw)
		xt1 = floor_mult(x1, self.tw)
		if xt0 >= xt1:
			print 'Bad input x dimensions'
		yt0 = ceil_mult(y0, self.th)
		yt1 = floor_mult(y1, self.th)
		if yt0 >= yt1:
			print 'Bad input y dimensions'
			
			
		'''
		The ideal step is to advance to the next area where it will be legal to create a new 
		Slightly decrease the step to avoid boundary conditions
		Although we clip on both side we only have to get rid of one side each time
		'''
		txstep = self.tw - self.clip_width - 1
		tystep = self.th - self.clip_height - 1
		'''
		A tile is valid if its in a safe location
		There are two ways for the location to be safe:
		-No neighboring tiles as found on canvas edges
		-Sufficiently inside the blend area that artifacts should be minimal
		'''
		for x in xrange(xt0, xt1, txstep):
			# If this is an edge supertile skip the buffer check
			if x0 != self.left() and x1 != self.right():
				# Are we trying to construct a tile in the buffer zone?
				if xt0 < x0 + self.clip_width or xt1 >= x1 - self.clip_width:
					continue
				
			col = self.x2col(x)
			for y in xrange(yt0, yt1, tystep):
				if y0 != self.top() and y1 != self.bottom():
					# Are we trying to construct a tile in the buffer zone?
					if yt0 < y0 + self.clip_height or yt1 >= y1 - self.clip_height:
						continue
				# If we made it this far the tile can be constructed with acceptable enblend artifacts
				row = self.y2row(y)
				# Did we already do this tile?
				if self.is_done(row, col):
					# No use repeating it although it would be good to diff some of these
					continue
				
				# note that x and y are in whole pano coords
				# we need to adjust to our frame
				# row and col on the other hand are used for global naming
				self.make_tile(i, x - x0, y - y0, row, col)
	
	def get_name(self, row, col):
		out_dir = ''
		if self.out_dir:
			out_dir = '%s/' % self.out_dir
		return '%sy%03d_x%03d%s' % (out_dir, row, col, out_extension)
	
	def make_tile(self, i, x, y, row, col):
		'''Make a tile given an image, the upper left x and y coordinates in that image, and the global row/col indices'''
		xmin = x
		ymin = y
		xmax = min(xmin + self.tw, i.width())
		ymax = min(ymin + self.th, i.height())
		nfn = self.get_name(row, col)

		print '%s: (x %d:%d, y %d:%d)' % (nfn, xmin, xmax, ymin, ymax)
		ip = i.subimage(xmin, xmax, ymin, ymax)
		'''
		Images must be padded
		If they aren't they will be stretched in google maps
		'''
		if ip.width() != self.tw or ip.height() != self.th:
			print 'WARNING: %s: expanding partial tile (%d X %d) to full tile size' % (nfn, ip.width(), ip.height())
			ip.set_canvas_size(t_width, t_height)
		ip.image.save(nfn)
		
		self.mark_done(row, col)
				
	def x2col(self, x):
		return int((x - self.x0) / self.tw)
	
	def y2row(self, y):
		return int((y - self.y0) / self.th)
	
	def is_done(self, row, col):
		return (row, col) in self.closed_list()
	
	def mark_done(self, row, col):
		self.closed_list.insert((row, col))
	
	def left(self):
		return self.x0
		
	def right(self):
		return self.x1
	
	def top(self):
		return self.y0
	
	def bottom(self):
		return self.y1
	
	def gen_supertiles(self):
		# 0:256 generates a 256 width pano
		# therefore, we don't want the upper bound included
		#col = 0
		x_done = False
		for x in xrange(self.left(), self.right(), self.super_tw):
			x0 = x
			x1 = x + self.super_tw
			# If we have reached the right side align to it rather than truncating
			# This makes blending better to give a wider buffer zone
			if x1 >= self.right():
				x_done = True
				x0 = self.right() - self.super_tw
				x1 = self.right()
			
			#row = 0
			y_done = False
			for y in xrange(self.top(), self.bottom(), self.super_th):
				y0 = y
				y1 = y + self.super_th
				if y1 >= self.bottom():
					y_done = True
					y0 = self.bottom() - self.super_th
					y1 = self.bottom()
				
				yield [x0, x1, y0, y1]
				#row +=1 	
				if y_done:
					break
			#col += 1
			if x_done:
				break

	def run(self):
		'''
		if we have a width of 256 and 1 pixel we need total size of 256
		If we have a width of 256 and 256 pixels we need total size of 256
		if we have a width of 256 and 257 pixel we need total size of 512
		'''
		print 'Tile width: %d, height: %d' % (self.tw, self.th)
		print 'Left: %d, right: %d, top: %d, bottom: %d' % (self.left(), self.right(), self.top(), self.bottom())
		
		os.mkdir(self.out_dir)
		# in form (row, col)
		self.closed_list = set()
		
		print 'Generating %d supertiles' % len(list(self.gen_supertiles()))
		#temp_file = 'partial.tif'
		for supertile in self.gen_supertiles():
			[x0, x1, y0, y1] = supertile
			self.try_supertile(x0, x1, y0, y1)
				
