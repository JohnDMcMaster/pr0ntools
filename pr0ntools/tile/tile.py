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
from PIL import Image
from pr0ntools.stitch.image_coordinate_map import ImageCoordinateMap
import shutil
import math

def calc_max_level_from_image(image, zoom_factor=None):
	return calc_max_level(image.height(), image.width(), zoom_factor)

def calc_max_level(height, width, zoom_factor=None):
	if zoom_factor is None:
		zoom_factor = 2
	'''
	Calculate such that max level is a nice screen size
	Lets be generous for small viewers...especially considering limitations of mobile devices
	'''
	fit_width = 640
	fit_height = 480
	
	width_levels = math.ceil(math.log(width, zoom_factor) - math.log(fit_width, zoom_factor))
	height_levels = math.ceil(math.log(height, zoom_factor) - math.log(fit_height, zoom_factor))
	max_level = int(max(width_levels, height_levels, 0))
	# Take the number of zoom levels required to fit the entire thing on screen
	print 'Calc max zoom level for %d X %d screen: %d (wmax: %d lev / %d pix, hmax: %d lev / %d pix)' % (fit_width, fit_height, max_level, width_levels, width, height_levels, height)
	return max_level

'''
Take a single large image and break it into tiles
'''
class ImageTiler:
	def __init__(self, image, x0 = None, x1 = None, y0 = None, y1 = None, tw = 250, th = 250):
		self.verbose = False
		self.image = image
		self.progress_inc = 0.10
		
		if x0 is None:
			x0 = 0
		self.x0 = x0
		if x1 is None:
			x1 = image.width()
		self.x1 = x1
		if y0 is None:
			y0 = 0
		self.y0 = y0
		if y1 is None:
			y1 = image.height()
		self.y1 = y1
		
		self.tw = tw
		self.th = th
		self.out_dir = None

		self.set_out_extension('.jpg')
		
	def set_out_extension(self, s):
		self.out_extension = s
		
	# FIXME / TODO: this isn't the google reccomended naming scheme, look into that more	
	# part of it was that I wanted them to sort nicely in file list view
	def get_name(self, row, col):
		out_dir = ''
		if self.out_dir:
			out_dir = '%s/' % self.out_dir
		return '%sy%03d_x%03d%s' % (out_dir, row, col, self.out_extension)
		
	def make_tile(self, x, y, row, col):
		xmin = x
		ymin = y
		xmax = min(xmin + self.tw, self.x1)
		ymax = min(ymin + self.th, self.y1)
		nfn = self.get_name(row, col)

		if self.verbose:
			print '%s: (x %d:%d, y %d:%d)' % (nfn, xmin, xmax, ymin, ymax)
		ip = self.image.subimage(xmin, xmax, ymin, ymax)
		'''
		Images must be padded
		If they aren't they will be stretched in google maps
		'''
		if ip.width() != self.tw or ip.height() != self.th:
			if self.verbose:
				print 'WARNING: %s: expanding partial tile (%d X %d) to full tile size' % (nfn, ip.width(), ip.height())
			ip.set_canvas_size(self.tw, self.th)
		#print 'Saving...' 
		ip.image.save(nfn)
		#print 'Image done' 
		
	def run(self):
		'''
		Namer is a function that accepts the following arguments and returns a string:
		namer(row, col)
	
		python can bind objects to functions so a user parameter isn't necessary?
		'''
	
		'''
		if namer is None:
			namer = google_namer
		'''

		col = 0
		next_progress = self.progress_inc
		processed = 0
		n_images = len(range(self.x0, self.x1, self.tw)) * len(range(self.y0, self.y1, self.th))
		for x in xrange(self.x0, self.x1, self.tw):
			row = 0
			for y in xrange(self.y0, self.y1, self.th):
				self.make_tile(x, y, row, col)
				row += 1
				processed += 1
				if self.progress_inc:
					cur_progress = 1.0 * processed / n_images
					if cur_progress >= next_progress:
						print 'Progress: %02.2f%% %d / %d' % (cur_progress * 100, processed, n_images)
						next_progress += self.progress_inc
			col += 1

'''
Creates smaller tiles from source tiles
'''
class TileTiler:
	def __init__(self, file_names, max_level, min_level = 0, out_dir_base=None):
		self.verbose = False
		self.map = ImageCoordinateMap.from_tagged_file_names(file_names)
		#self.map.debug_print()
		self.max_level = max_level
		self.min_level = min_level
		self.out_dir_base = out_dir_base
		#self.set_out_extension('.png')
		self.set_out_extension('.jpg')
		self.zoom_factor = 2
		self.t_width = 250
		self.t_height = 250
		# JPEG quality level, 1-100 or something
		self.quality = 90
		# Fraction of 1 to print each progress level at
		# None to disable
		self.progress_inc = 0.10

	def set_out_extension(self, s):
		self.out_extension = s

	def prep_out_dir_base(self):
		if self.out_dir_base is None:
			self.out_dir_base = 'tiles_out/'
		if os.path.exists(self.out_dir_base):
			os.system('rm -rf %s' % self.out_dir_base)
		os.mkdir(self.out_dir_base)

	def get_old(self, row, col):
		# Because we are shrinking there isn't necessarily an old tile around the edges
		return self.map.get_image_safe(col, row)

	def get_fn(self, row, col):
		return '%s/%d/y%03d_x%03d%s' % (self.out_dir_base, self.zoom_level, row, col, self.out_extension)

	def run(self):
		self.prep_out_dir_base()
		
		for self.zoom_level in xrange(self.max_level, self.min_level - 1, -1):
			print
			print '************'
			print 'Zoom level %d' % self.zoom_level
			out_dir = '%s/%d' % (self.out_dir_base, self.zoom_level)
			if os.path.exists(out_dir):
				os.system('rm -rf %s' % out_dir)
			os.mkdir(out_dir)
			
			next_progress = self.progress_inc
			processed = 0
			# For the first level we copy things over
			if self.zoom_level == self.max_level:
				print 'Not resizing on first zoom level'
				n_images = self.map.n_images()
				for (img_fn, row, col) in self.map.images():
					dst = self.get_fn(row, col)
					if 0:
						print 'Direct copying %s => %s' % (img_fn, dst)
						shutil.copy(img_fn, dst)
					# This allows to do type conversions if needed
					# Presumably the conversion process for jps should be lossless although I haven't verified
					else:
						if self.verbose:
							print 'Basic conversion %s => %s w/ quality %u' % (img_fn, dst, self.quality)
						pi = PImage.from_file(img_fn)
						# I could actually set with / height here but right now this is
						# coming up fomr me accidentially using 256 x 256 tiles when the 
						# standard is 250 x 250
						if self.t_width is None:
							self.t_width = pi.width()
						if self.t_height is None:
							self.t_height = pi.height()
						if pi.width() != self.t_width or pi.height() != self.t_height:
							raise Exception('Source image incorrect size')
						pi.save(dst, quality=self.quality)
					processed += 1
					if self.progress_inc:
						cur_progress = 1.0 * processed / n_images
						if cur_progress >= next_progress:
							print 'Progress: %02.2f%% %d / %d' % (cur_progress * 100, processed, n_images)
							next_progress += self.progress_inc
					
			# Additional levels we take the image coordinate map and shrink
			else:
				# Prepare a new image coordinate map so we can form the next tile set
				new_cols = int(math.ceil(1.0 * self.map.width() / self.zoom_factor))
				new_rows = int(math.ceil(1.0 * self.map.height() / self.zoom_factor))
				print 'Shrink by %s: cols %s => %s, rows %s => %s' % (str(self.zoom_factor), self.map.width(), new_cols, self.map.height(), new_rows)
				if 0:
					print
					self.map.debug_print()
					print
				new_map = ImageCoordinateMap(new_cols, new_rows)
				todo = new_rows * new_cols
				this = 0
				next_progress = self.progress_inc
				for new_row in xrange(new_rows):
					old_row = new_row * self.zoom_factor
					for new_col in xrange(new_cols):
						this += 1
						old_col = new_col * self.zoom_factor
						#print
						if self.verbose:
							print 'z%d %d/%d: transforming row %d => %d, col %d => %d w/ quality %u' % (self.zoom_level, this, todo, old_row, new_row, old_col, new_col, self.quality)
						# Paste the old (4) images together
						imgp = PImage.from_fns([[self.get_old(old_row + 0, old_col + 0), self.get_old(old_row + 0, old_col + 1)],
								[self.get_old(old_row + 1, old_col + 0), self.get_old(old_row + 1, old_col + 1)]], tw=self.t_width, th=self.t_height)
						if imgp.width() != self.t_width * self.zoom_factor or imgp.height() != self.t_height * self.zoom_factor:
							print 'New image width %d, height: %d from tile width %d, height %d' % (imgp.width(), imgp.height(), self.t_width, self.t_height)
							raise Exception('Combined image incorrect size')
						scaled = imgp.get_scaled(0.5, filt=Image.ANTIALIAS)
						if scaled.width() != self.t_width or scaled.height() != self.t_height:
							raise Exception('Scaled image incorrect size')
						new_fn = self.get_fn(new_row, new_col)
						scaled.save(new_fn, quality=self.quality)
						#sys.exit(1)
						new_map.set_image(new_col, new_row, new_fn)
						if self.progress_inc:
							cur_progress = 1.0 * this / todo
							if cur_progress >= next_progress:
								print 'Progress: %02.2f%% %d / %d' % (cur_progress * 100, this, todo)
								next_progress += self.progress_inc
				# Next shrink will be on the previous tile set, not the original
				if self.verbose:
					print 'Shrinking the world for future rounds'
				self.map = new_map
# replaces from_single
class SingleTiler:
	def __init__(self, fn, max_level = None, min_level = None, out_dir_base=None):
		self.fn = fn
		self.max_level = max_level
		self.min_level = min_level
		self.out_dir_base = out_dir_base
		self.set_out_extension('.jpg')
		self.progress_inc = 0.10

	def set_out_extension(self, s):
		self.out_extension = s

	def run(self):
		fn = self.fn
		max_level = self.max_level
		min_level = self.min_level
		out_dir_base = self.out_dir_base

		if min_level is None:
			min_level = 0
		i = PImage.from_file(fn)
		if max_level is None:
			max_level = calc_max_level_from_image(i)
	
		t_width = 250
		t_height = 250
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
		
			tiler = ImageTiler(i)
			tiler.progress_inc = self.progress_inc
			tiler.out_dir = out_dir
			tiler.run()
		
			if zoom_level != min_level:
				# Each zoom level is half smaller than previous
				i = i.get_scaled(0.5, filt=Image.ANTIALIAS)
				if 0:
					i.save('test.jpg')
					sys.exit(1)

