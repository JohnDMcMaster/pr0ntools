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
from pr0ntools.stitch.blender import Blender
from pr0ntools.stitch.pto.project import PTOProject
from image_coordinate_map import ImageCoordinateMap
from pr0ntools.config import config
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.temp_file import ManagedTempDir
#from pr0ntiles.tile import Tiler as TilerCore
from pr0ntools.pimage import PImage
from pr0ntools.benchmark import Benchmark
from pr0ntools.util.geometry import floor_mult, ceil_mult
import os
import math
import shutil


class PartialStitcher:
	def __init__(self, pto, bounds, out):
		self.pto = pto
		self.bounds = bounds
		self.out = out
		
	def run(self):
		'''
		Phase 1: remap the relevant source image areas onto a canvas
		
		Note that nona will load ALL of the images (one at a time)
		but will only generate output for those that matter
		Each one takes a noticible amount of time but its relatively small compared to the time spent actually mapping images
		'''
		print
		print 'Supertile phase 1: remapping (nona)'
		if self.out.find('.') < 0:
			raise Exception('Require image extension')
		# Hugin likes to use the base filename as the intermediates, lets do the sames
		out_name_base = self.out[0:self.out.find('.')].split('/')[-1]
		print "out name: %s, base: %s" % (self.out, out_name_base)
		#ssadf
		if out_name_base is None or len(out_name_base) == 0 or out_name_base == '.' or out_name_base == '..':
			raise Exception('Bad output file base "%s"' % str(out_name_base))

		# Scope of these files is only here
		# We only produce the single output file, not the intermediates
		managed_temp_dir = ManagedTempDir.get()
		# without the slash they go into the parent directory with that prefix
		out_name_prefix = managed_temp_dir.file_name + "/"
		
		pto = self.pto.copy()
		print 'Making absolute'
		pto.make_absolute()
		
		print 'Cropping...'
		#sys.exit(1)
		pl = pto.get_panorama_line()
		# It is fine to go out of bounds, it will be black filled
		#pl.set_bounds(x, min(x + self.tw(), pto.right()), y, min(y + self.th(), pto.bottom()))
		pl.set_crop(self.bounds)
		remapper = Remapper(pto, out_name_prefix)
		remapper.remap()
		
		'''
		Phase 2: blend the remapped images into an output image
		'''
		print
		print 'Supertile phase 2: blending (enblend)'
		blender = Blender(remapper.get_output_files(), self.out)
		blender.run()
		# We are done with these files, they should be nuked
		if not config.keep_temp_files():
			for f in remapper.get_output_files():
				os.remove(f)
		
		print 'Supertile ready!'

# For managing the closed list		

class Tiler:
	def __init__(self, pto, out_dir, tile_width=250, tile_height=250, st_scalar_heuristic=4, dry=False, super_tw=None, super_th=None):
		img_width = None
		img_height = None
		self.dry = dry
		
		# TODO: this is a heuristic just for this, uniform input images aren't actually required
		for i in pto.get_image_lines():
			w = i.width()
			h = i.height()
			if img_width is None:
				img_width = w
			if img_height is None:
				img_height = h
			if img_width != w or img_height != h:
				raise Exception('Require uniform input images for size heuristic')
		
		self.pto = pto
		self.out_dir = out_dir
		self.tw = tile_width
		self.th = tile_height
		
		# Delete files in the way?
		self.force = False
		
		self.set_size_heuristic(img_width, img_height)
		# These are less related
		# They actually should be set as high as you think you can get away with
		# Although setting a smaller number may have higher performance depending on input size
		if super_tw is None:
			self.super_tw = img_width * st_scalar_heuristic
		else:
			self.super_tw = super_tw
		if super_th is None:
			self.super_th = img_height * st_scalar_heuristic
		else:
			self.super_th = super_th
		
		
		
		'''
		We won't stitch any tiles in the buffer zone
		We don't stitch on the right to the current supertile and won't stitch to the left on the next supertile
		So, we must take off 2 clip widths to get a safe area
		We probably only have to take off one tw, I haven't thought about it carefully enough
		
		If you don't do this you will not stitch anything in the center that isn't perfectly aligned
		Will get worse the more tiles you create
		'''
		if 0:
			self.super_t_xstep = self.super_tw
			self.super_t_ystep = self.super_th
		else:
			self.super_t_xstep = self.super_tw - 2 * self.clip_width - 2 * self.tw
			self.super_t_ystep = self.super_th - 2 * self.clip_height - 2 * self.th
		
		
		
		print 'Input images width %d, height %d' % (img_width, img_height)
		print 'Output to %s' % self.out_dir
		print 'Super tile width %d, height %d from scalar %d' % (self.super_tw, self.super_th, st_scalar_heuristic)
		print 'Super tile x step %d, y step %d' % (self.super_t_xstep, self.super_t_ystep)
		print 'Supertile clip width %d, height %d' % (self.clip_width, self.clip_height)
		
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
		
		However if we do assume its on the center the center of the image should be unique and thus not a stitch boundry
		'''
		self.clip_width = image_width / 2
		self.clip_height = image_height / 2
	
	def build_spatial_map(self):
		#image_file_names = self.pto.get_file_names()
		#self.map = ImageCoordinateMap.from_file_names(image_file_names)
		
		items = [PolygonQuadTreeItem(il.left(), il.right(), il.top(), il.bottom()) for il in self.pto.get_image_lines()]
		self.map = PolygonQuadTree(items)	
	
	def try_supertile(self, x0, x1, y0, y1):
		'''x0/1 and y0/1 are global absolute coordinates'''
		# First generate all of the valid tiles across this area to see if we can get any useful work done?
		# every supertile should have at least one solution or the bounds aren't good
		
		print
		print
		print "Creating supertile %d / %d with x%d:%d, y%d:%d" % (self.n_supertiles, self.n_expected_supertiles, x0, x1, y0, y1)
		bench = Benchmark()
		
		temp_file = ManagedTempFile.get(None, '.tif')

		bounds = [x0, x1, y0, y1]
		#out_name_base = "%s/r%03d_c%03d" % (self.out_dir, row, col)
		#print 'Working on %s' % out_name_base
		stitcher = PartialStitcher(self.pto, bounds, temp_file.file_name)
		if self.dry:
			print 'Dry: skipping partial stitch'
			stitcher = None
		else:
			stitcher.run()
		
		
		print
		print 'Phase 3: loading supertile image'
		if self.dry:
			print 'Dry: skipping loading PTO'
			img = None
		else:
			img = PImage.from_file(temp_file.file_name)
			print 'Supertile width: %d, height: %d' % (img.width(), img.height())
		new = 0
		
		'''
		There is no garauntee that our supertile is a multiple of our tile size
		This will particularly cause issues near the edges if we are not careful
		'''
		xt0 = ceil_mult(x0, self.tw, align=self.x0)
		xt1 = floor_mult(x1, self.tw, align=self.x0)
		if xt0 >= xt1:
			print 'Bad input x dimensions'
		yt0 = ceil_mult(y0, self.th, align=self.y0)
		yt1 = floor_mult(y1, self.th, align=self.y0)
		if yt0 >= yt1:
			print 'Bad input y dimensions'
			
			
		txstep = self.tw
		tystep = self.th
		
		'''
		A tile is valid if its in a safe location
		There are two ways for the location to be safe:
		-No neighboring tiles as found on canvas edges
		-Sufficiently inside the blend area that artifacts should be minimal
		'''
		gen_tiles = 0
		print
		print 'Phase 4: chopping up supertile, step(x: %d, y: %d)' % (txstep, tystep)
		print 'x in xrange(%d, %d, %d)' % (xt0, xt1, txstep)
		print 'y in xrange(%d, %d, %d)' % (yt0, yt1, tystep)
		if txstep <= 0 or tystep <= 0:
			raise Exception('Bad step values')
			
		skip_xl_check = False
		skip_xh_check = False
		# If this is an edge supertile skip the buffer check
		if x0 == self.left():
			print 'X check skip (%d): left border' % x0
			skip_xl_check = True
		if x1 == self.right():
			print 'X check skip (%d): right border' % x1
			skip_xh_check = True
			
		skip_yl_check = False
		skip_yh_check = False
		if y0 == self.top():
			print 'Y check skip (%d): top border' % y0
			skip_yl_check = True
		if y1 == self.bottom():
			print 'Y check skip (%d): bottom border' % y1
			skip_yh_check = True
			
		for y in xrange(yt0, yt1, tystep):
			# Are we trying to construct a tile in the buffer zone?
			if (not skip_yl_check) and y < y0 + self.clip_height:
				print 'Rejecting tile @ y%d, x*: yl clip' % (y)
				continue
			if (not skip_yh_check) and y + self.th >= y1 - self.clip_height:
				print 'Rejecting tile @ y%d, x*: yh clip' % (y)
				continue
			# If we made it this far the tile can be constructed with acceptable enblend artifacts
			row = self.y2row(y)
			for x in xrange(xt0, xt1, txstep):			 	
				# Are we trying to construct a tile in the buffer zone?
				if (not skip_xl_check) and x < x0 + self.clip_width:
					print 'Rejecting tiles @ y%d, x%d: xl clip' % (y, x)
					continue
				if (not skip_xh_check) and x + self.tw >= x1 - self.clip_width:
					print 'Rejecting tiles @ y%d, x%d: xh clip' % (y, x)
					continue
				
				col = self.x2col(x)
				
				# Did we already do this tile?
				if self.is_done(row, col):
					# No use repeating it although it would be good to diff some of these
					print 'Rejecting tile x%d, y%d / r%d, c%d: already done' % (x, y, row, col)
					continue
				
				# note that x and y are in whole pano coords
				# we need to adjust to our frame
				# row and col on the other hand are used for global naming
				self.make_tile(img, x - x0, y - y0, row, col)
				gen_tiles += 1
		bench.stop()
		print 'Generated %d new tiles for a total of %d in %s' % (gen_tiles, len(self.closed_list), str(bench))
		if gen_tiles == 0:
			raise Exception("Didn't generate any tiles")
		# temp_file should be automatically deleted upon exit
	
	def get_name(self, row, col):
		out_extension = '.jpg'
		#out_extension = '.png'
		out_dir = ''
		if self.out_dir:
			out_dir = '%s/' % self.out_dir
		return '%sy%03d_x%03d%s' % (out_dir, row, col, out_extension)
	
	def make_tile(self, i, x, y, row, col):
		'''Make a tile given an image, the upper left x and y coordinates in that image, and the global row/col indices'''	
		if self.dry:
			print 'Dry: not making tile w/ x%d y%d r%d c%d' % (x, y, row, col)
		else:
			xmin = x
			ymin = y
			xmax = min(xmin + self.tw, i.width())
			ymax = min(ymin + self.th, i.height())
			nfn = self.get_name(row, col)

			print 'Subtile %s: (x %d:%d, y %d:%d)' % (nfn, xmin, xmax, ymin, ymax)
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
		return (row, col) in self.closed_list
	
	def mark_done(self, row, col):
		self.closed_list.add((row, col))
	
	def tiles_done(self):
		return len(self.closed_list)
	
	def gen_open_list(self):
		open_list = set()
		for y in xrange(self.rows()):
			for x in xrange(self.cols()):
				if not self.is_done(y, x):
					yield (y, x)
	
	def dump_open_list(self):
		print 'Open list:'
		for (row, col) in self.gen_open_list():
			print '  r%d c%d' % (row, col)
			
	def rows(self):
		return int(math.ceil(self.height() / self.th))
	
	def cols(self):
		return int(math.ceil(self.width() / self.tw))
			
	def height(self):
		return abs(self.top() - self.bottom())
	
	def width(self):
		return abs(self.right() - self.left())
	
	def left(self):
		return self.x0
		
	def right(self):
		return self.x1
	
	def top(self):
		return self.y0
	
	def bottom(self):
		return self.y1
	
	def optimize_step(self):
		'''
		TODO: even out the steps, we can probably get slightly better results
		
		The ideal step is to advance to the next area where it will be legal to create a new 
		Slightly decrease the step to avoid boundary conditions
		Although we clip on both side we only have to get rid of one side each time
		'''
		#txstep = self.super_tw - self.clip_width - 1
		#tystep = self.super_th - self.clip_height - 1
		pass
	
	def gen_supertiles(self):
		# 0:256 generates a 256 width pano
		# therefore, we don't want the upper bound included
			
		#row = 0
		y_done = False
		for y in xrange(self.top(), self.bottom(), self.super_t_ystep):
			y0 = y
			y1 = y + self.super_th
			if y1 >= self.bottom():
				y_done = True
				y0 = self.bottom() - self.super_th
				y1 = self.bottom()
				
			#col = 0
			x_done = False
			for x in xrange(self.left(), self.right(), self.super_t_xstep):
				x0 = x
				x1 = x + self.super_tw
				# If we have reached the right side align to it rather than truncating
				# This makes blending better to give a wider buffer zone
				if x1 >= self.right():
					x_done = True
					x0 = self.right() - self.super_tw
					x1 = self.right()
				
				yield [x0, x1, y0, y1]
				
				#col += 1
				if x_done:
					break
			#row +=1 	
			if y_done:
				break
		print 'All supertiles generated'
		
	def run(self):
		if not self.dry:
			self.dry = True
			print
			print
			print
			print '***BEGIN DRY RUN***'
			self.run()
			print '***END DRY RUN***'
			print
			print
			print
			self.dry = False
	
		'''
		if we have a width of 256 and 1 pixel we need total size of 256
		If we have a width of 256 and 256 pixels we need total size of 256
		if we have a width of 256 and 257 pixel we need total size of 512
		'''
		print 'Tile width: %d, height: %d' % (self.tw, self.th)
		print 'Net - left: %d, right: %d, top: %d, bottom: %d' % (self.left(), self.right(), self.top(), self.bottom())
		
		if os.path.exists(self.out_dir):
			if self.force:
				if not self.dry:
					shutil.rmtree(self.out_dir)
			else:
				raise Exception("Must set force to override output")
		if not self.dry:
			os.mkdir(self.out_dir)
		# in form (row, col)
		self.closed_list = set()
		
		self.n_expected_supertiles = len(list(self.gen_supertiles()))
		print 'Generating %d supertiles' % self.n_expected_supertiles
		
		x_tiles = math.ceil(self.width() / self.tw)
		y_tiles = math.ceil(self.height() / self.th)
		net_tiles = x_tiles * y_tiles
		print 'Expecting to generate x%d, y%d (%d) basic tiles' % (x_tiles, y_tiles, net_tiles)
		
		#temp_file = 'partial.tif'
		self.n_supertiles = 0
		for supertile in self.gen_supertiles():
			self.n_supertiles += 1
			[x0, x1, y0, y1] = supertile
			self.try_supertile(x0, x1, y0, y1)

		if self.tiles_done() != net_tiles:
			print 'ERROR: expected to do %d basic tiles but did %d' % (net_tiles, self.tiles_done())
			self.dump_open_list()
			raise Exception('State mismatch')

