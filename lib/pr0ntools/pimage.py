'''
This file is part of pr0ntools
Image utility class
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

import Image
import sys
from temp_file import TempFile
from temp_file import ManagedTempFile

'''
images are indexed imageInstance[x][y]

		  width = 5
				x = ...
			0 1 2 3 4
height = 4
y = 0		0 0 0 0 0
y = 1		1 1 1 1 1
y = 2		1 0 0 0 0
y = 3		1 0 0 0 0				

Ex:
imageInstance[3, 0] = 0
imageInstance[0, 2] = 1


Image.getdata() uses linear indexing:
			width / x
			0 1 2 3
height / y	4 5 5 6
			7 8 9 10
pos = width * y + x


0 represents white
1 represents black
Currently code treats 0 as white and non-0 as black
'''
class PImage:
	# A PIL Image object
	image = None
	temp_file = None
	
	# We do not copy array, so be careful with modifications
	def __init__(self, image):
		if image is None:
			raise Exception('cannot construct on empty image')
		self.image = image
	
	def debug_print(self, char_limit = None, row_label = False):
		for y in range(0, self.height()):
			row_label_str = ''
			if row_label:
				row_label_str = '%02d: ' % y
			print row_label_str + self.debug_row_string(y, char_limit, row_label_str)
	
	def debug_row_string(self, y, char_limit = None, row_label = None):
		if row_label is None:
			row_label = ''
		ret = row_label
		x_max = self.width()
		for x in range(0, x_max):
			if not x == 0:
				ret += " "
			ret += "% 4s" % repr(self.get_pixel(x, y))
			if char_limit and len(ret) > char_limit:
				ret = ret[0:char_limit]
				break

		return ret

	def debug_show(self):
		return self.to_image().show()

	# To an Image
	def to_image(self):
		return self.image
	
	'''
	First step in scaling is to take off any whitespace
	This normalizes the spectra
	Returns a new image that is trimmed
	'''
	def trim(self):
		(image, x_min, x_max, y_min, y_max) = self.trim_verbose()
		return image
		
	def trim_verbose(self):
		#print 'Trimming: start'
		# Set to lowest set pixel
		# Initially set to invalid values, we should replace them
		# I'm sure there are more effient algorithms, but this "just works" until we need to up performance
		# What we probably should do is scan in from all sides until we hit a value and then stop
		x_min = self.width()
		x_max = -1
		y_min = self.height()
		y_max = -1
		for y in range(0, self.height()):
			for x in range(0, self.width()):
				# print "%s != %s" % (self.get_pixel(x, y), self.white())
				# if set, we have a value influencing the result
				if self.get_pixel(x, y) != self.white():
					x_min = min(x_min, x)
					y_min = min(y_min, y)
					x_max = max(x_max, x)
					y_max = max(y_max, y)
	
		#print (x_min, x_max, y_min, y_max)
		#print 'Trimming: doing subimage'
		return (self.subimage(x_min, x_max, y_min, y_max), x_min, x_max, y_min, y_max)

	'''
	Given exclusive end array bounds (allows .width() convenience)
	returns a new image trimmed to the given bounds
	Truncates the image if our array bounds are out of range
		Maybe we should throw exception instead?
	'''
	def subimage(self, x_min, x_max, y_min, y_max):
		if x_min is None:
			x_min = 0
		if x_max is None:
			x_max = self.width()
		if y_min is None:
			y_min = 0
		if y_max is None:
			y_max = self.height()
		#print 'subimage: start.  x_min: %d: x_max: %d, y_min: %d, y_max: %d' % (x_min, x_max, y_min, y_max)

		if x_min < 0 or y_min < 0 or x_max < 0 or y_max < 0:
			print x_min, y_min, x_max, y_max
			raise Exception('out of bounds')

		# Did we truncate the whole image?
		if x_min > x_max or y_min > y_max:
			return self.from_array([], self.get_mode(), self.get_mode())
		
		'''
		height = y_max - y_min + 1
		width = x_max - x_min + 1

		array_out = [[0 for i in range(width)] for j in range(height)]
		for cur_height in range(0, height):
			for cur_width in range(0, width):
				array_out[cur_height][cur_width] = self.get_pixel(cur_height + y_min, cur_width + x_min)

		#print 'subimage: beginning from array'
		return self.from_array(array_out, self.get_mode(), self.get_mode())
		'''
		# 4-tuple (x0, y0, x1, y1)
		print 'x_min: %d, y_min: %d, x_max: %d, y_max: %d' % (x_min, y_min, x_max, y_max)
		# This is exclusive, I want inclusive
		return PImage.from_image(self.image.crop((x_min, y_min, x_max, y_max)))

	def copy(self):
		return self.subimage(self, None, None, None, None)

	def width(self):
		return self.image.size[0]
	
	def height(self):
		return self.image.size[1]
	
	def set_pixel(self, x, y, pixel):
		self.image.putpixel((x, y), pixel)
	
	def get_pixel(self, x, y):
		try:
			return self.image.getpixel((x, y))
		except:
			print 'bad pixel values, x: %d, y: %d' % (x, y)
			raise
	
	# The following are in case we change image mode
	def black(self):
		'''return the instance's representation of black'''
		mode = self.get_mode()
		if mode == "1":
			return 1
		if mode == "L":
			return 0
		if mode == "RGB":
			return (255, 255, 255)
		raise Exception('Bad mode %s' % mode)
	
	def white(self):
		'''return the instance's representation of white'''
		mode = self.get_mode()
		if mode == "1":
			return 0
		if mode == "L":
			return 255
		if mode == "RGB":
			return (0, 0, 0)
		raise Exception('Bad mode %s' % mode)
	
	def get_RGB(self, pixel):
		'''return an instance specific pixel representation from an RGB pixel'''
		(R, G, B) = pixel
		if mode == "1":
			return round(self.pixel_to_brightness(pixel))
		if mode == "L":
			# This is just a quick estimate, it could be horribly wrong
			# We have white as 0 and RGB saturates to 0 for full values, so we take compliment
			# define as set as the proportion of RGB we have set
			return 1.0 - (1.0 * (R + G + B) / (256 * 3))
		if mode == "RGB":
			return pixel

		raise Exception('Bad mode %s' % mode)
	
	def pixel_to_brightness(self, pixel):
		'''Convert pixel to brightness value, [0.0, 1.0] where 0 is white and 1 is black'''
		# The above range was chosen somewhat arbitrarily as thats what old code did (think because thats what "1" mode does)
		# Also, it makes it convenient for summing up "filled" areas as we usually assume (infinite) white background
		mode = self.get_mode()
		if mode == "1":
			# TODO: double check this is correct, that is 0 is white and 1 is black
			return pixel * 1.0
		if mode == "L":
			# 255 is white
			return 1.0 - (1 + pixel) / 256.0
		if mode == "RGB":
			# RGB represents (255, 255, 255) as white since all colors are at max
			# Also scale to the range correctly by adding 3 and then invert to make it luminescence
			return 1.0 - (pixel[0] + pixel[1] + pixel[2] + 3) / (256.0 * 3)
		raise Exception('Bad mode %s' % mode)
	
	def to_array(self):
		'''returns array[Y/height][X/width] indexed data structure'''
		width = self.image.size[0]
		height = self.image.size[1]
		# I guess people expect to index x first?
		# think matlab does y first
		# so we are doing index height (y) first since thats what old code did
		array = [[0 for i in range(width)] for j in range(height)]
		for cur_height in range(0, height):
			for cur_width in range(0, width):
				array[cur_height][cur_width] = self.image.getdata()[cur_height * width + cur_width]
		return array

	def get_mode(self):
		# FIXME
		#return PImage.get_default_mode()
		return self.image.mode

	@staticmethod
	def from_file(path):
		'''
		I'm having difficulty dealing with anything paletted, so convert everything right off the bat
		'''
		img = Image.open(path)
		if img is None:
			raise Exception("Couldn't open image file: %s" % path)
		if False:
			img_converted = img.convert('L')
			return PImage.from_image(img_converted)
		else:
			return PImage.from_image(img)

	@staticmethod
	def from_image(image):
		return PImage(image)
	
	@staticmethod
	def from_unknown(image):
		if isinstance(image, str):
			return PImage.from_file(image).trim()
		elif isinstance(image, PImage):
			return image
		elif isinstance(image, image.Image):
			return PImage.from_image(image).trim()
		else:
		   raise Exception("unknown parameter: %s" % repr(image))

	@staticmethod
	def get_default_mode():
		'''
		WARNING: not all functions support all modes
		I can't find concrete documentation on the meaning of these, so gathered from misc sources
			http://www.pythonware.com/library/pil/handbook/image.htm
			http://www.pythonware.com/library/pil/handbook/introduction.htm			
		The first three some the most portable across the functions
		Original code (XOR/comparison) used binary images, but it seems we are trying to move towards grayscale
		
		"1"
			A bilevel image
			Stored as single ingeter on [0, 1]?
		"L"
			luminance
			for greyscale images
			Stored as single integer on [0, 256]?
		"RGB"
			for true colour images
			Stored as tuple ([0-255], [0-255], [0-255])?
			Image formats I've seen return this
				png
		"RGBA"
		"RGBX"
		"CMYK"
			for pre-press images.
		"P"
			Pallete?
			Image formats I've seen return this
				bmp
		'''
		return "L"

	@staticmethod
	def get_pixel_mode(pixel):
		'''Tries to guess pixel mode.  Hack to transition some old code, don't use this'''
		# FIXME: make sure array mode matches our created image
		if type(pixel) == type(0):
			return PImage.get_default_mode()
		if len(pixel) == 3:
			return 'RGB'
		else:
			return PImage.get_default_mode()
			
	@staticmethod
	def from_array(array, mode_in = None, mode_out = None):
		'''
		array[y][x]
		'''
		#print 'from_array: start'
		# Make a best guess, we should probably force it though
		if mode_in is None:
			mode_in = PImage.get_pixel_mode(array[0][0])
		if mode_out is None:
			mode_out = mode_in
			
		ret = None
		height = len(array)
		if height > 0:
			width = len(array[0])
			if width > 0:
				# (Xsize, Ysize)
				# Feed in an arbitrary pixel and assume they are all encoded the same
				# print 'width: %d, height: %d' % (width, height)
				ret = PImage(Image.new(mode_out, (width, height), "White"))
				for y in range(0, height):
					for x in range(0, width):
						# print 'x: %d, y: %d' % (x, y)
						ret.set_pixel(x, y, array[y][x])
		if ret is None:
			ret = PImage(Image.new(mode_out, (0, 0), "White"))
		#print 'from_array: end'
		return ret

	@staticmethod
	def is_image_filename(filename):
		return filename.find('.tif') > 0 or filename.find('.jpg') > 0 or filename.find('.png') > 0 or filename.find('.bmp') > 0

class TempPImage:
	file_name = None
	pimage = None
	
	def __init__(self, file_name):
		if file_name:
			self.file_name = file_name
		else:
			self.file_name = TempFile.get()
	
	def get_a_file_name(self):
		pass
	
	@staticmethod
	def get(prefix = None, suffix = None):
		return ManagedTempFile(TempFile.get(prefix, suffix))

	@staticmethod
	def from_existing(file_name):
		return ManagedTempFile(file_name)

	def __del__(self):
		os.rm(self.file_name)

