'''
This file is part of pr0ntools
Projection profile utility class
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under GPL V3+
'''

'''
Bits: 8 X 32 X 8
	 0           1            2     .... 		7
	8 bits		8 bits		8 bits
0
	8 bits		8 bits		8 bits
	8 bits		8 bits		8 bits
1
	8 bits		8 bits		8 bits
	8 bits		8 bits		8 bits
2	
	...
29	
	8 bits		8 bits		8 bits
	8 bits		8 bits		8 bits
30
	8 bits		8 bits		8 bits
	8 bits		8 bits		8 bits
31
	8 bits		8 bits		8 bits	

Passes
	Read raw bits
	Rearrange into actual ROM bit order
'''

import sys
import util
import profile

class ProjectionProfile:
	def __init__(self, pimage):
		self.pimage = pimage
	
	def get_grayscale_horizontal_profile(self):
		'''get horizontal projection profile'''
		raw_profile = [0] * self.pimage.width()
		for cur_width in range(0, self.pimage.width()):
			for cur_height in range(0, self.pimage.height()):
				raw = self.pimage.get_pixel(cur_width, cur_height)
				brightness = self.pimage.pixel_to_brightness(raw)
				raw_profile[cur_width] += brightness				 
		return profile.Profile(raw_profile)

	def get_grayscale_vertical_profile(self):
		profile = [0] * self.pimage.height()
		for cur_height in range(0, self.pimage.height()):
			for cur_width in range(0, self.pimage.width()):
				profile[cur_height] += self.pimage.pixel_to_brightness(self.pimage.get_pixel(cur_width, cur_height))
		return profile.Profile(profile)

	'''
	Debugging related
	'''
		
	def print_horizontal_profile(self):
		profile = self.get_grayscale_horizontal_profile()
		profile.display_profile('horizontal profile', 'X')

	def print_vertical_profile(self):
		def letter_row_callback(key, value):
			'''key is profile (Y) index, value is profile value'''
			return '  ' + self.pimage.debug_row_string(key, 40)
		
		callback = None
		profile = self.get_grayscale_vertical_profile()
		# This is only readable on single letters
		if print_vertical_profile_leading_image:
			callback = letter_row_callback
		profile.display_profile('vertical profile', 'Y', callback)
		profile.derrivative().display_profile('vertical derrivative profile', 'Y', callback)

