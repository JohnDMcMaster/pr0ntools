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

class ProjectionProfile:
	def __init__(self, pimage):
		self.pimage = pimage
	
	def get_grayscale_horizontal_profile(self):
		'''get horizontal projection profile'''
		profile = [0] * self.pimage.width()
		for cur_width in range(0, self.pimage.width()):
			for cur_height in range(0, self.pimage.height()):
				raw = self.pimage.get_pixel(cur_width, cur_height)
				brightness = self.pimage.pixel_to_brightness(raw)
				profile[cur_width] += brightness				 
		return profile

	def get_grayscale_vertical_profile(self):
		profile = [0] * self.pimage.height()
		for cur_height in range(0, self.pimage.height()):
			for cur_width in range(0, self.pimage.width()):
				profile[cur_height] += self.pimage.pixel_to_brightness(self.pimage.get_pixel(cur_width, cur_height))
		return profile

	def derrivative(self, profile):
		'''return a simple derrivative, x[i + 1] - x[i]'''
		'''
		-----
		12				+12
		8	   =>		-4
		100			  +92
		-----		   -100
		'''
		if len(profile) == 0:
			# Profile of length 1 would be len=2, so len=1 for 0 seems reasonable
			return [0]

		# We aren't scaling by array length since its usually relative values and so doesn't matter
		d = [0] * (len(profile) + 1)
		# Previous value is 0 and can be important if we have a large spike at the end
		d[0] = profile[0]
		for i in range(1, len(profile)):
			d[i - 1] = profile[i] - profile[i - 1]
		d[len(profile)] = -profile[len(profile) - 1]
		return d

	'''
	Debugging related
	'''

	def display_profile(self, name, key_label, profile, callback = None):
		def bar_graph(value):
			# I could use gnuplot, but I don't like popups
			if value < 0:
				bar_pad = bar_graph_chars * ' '
				bar_part = int((1.0 * abs(value) / bar_graph_max) * bar_graph_chars) * '='
				bar_part = curse(bar_part, RED_START)
				bar_raw = bar_pad + bar_part
			elif value > 0:
				bar_raw = int((1.0 * value / bar_graph_max) * bar_graph_chars) * '='
			else:
				bar_pad = bar_graph_chars * ' '
				bar_part = "|"
				bar_part = curse(bar_part, BLUE_START)
				bar_raw = bar_pad + bar_part
			return '  ' + util.rjust_str(bar_raw, bar_graph_chars)
		
		def display_profile_row(key, value):
			# The value width isn't being calculated correctly..oh well, fix once it overflows
			display_profile_row_core((('%% %dd' % key_width) % key), (('%% %df' % value_width) % value), bar_graph(value))
			if callback:
				sys.stdout.write(callback(key, value))
			print

		def display_profile_row_core(key, value, other = ""):
			sys.stdout.write('\t%s | %s%s' % ((('%% %ds' % key_width) % key), (('%% %ds' % value_width) % value), other))
			# print '%s,%s' % (key, value)
			
		bar_graph_max = 0
		bar_graph_chars = 40
		key_width = 4
		value_width = 12

		for item in profile:
			bar_graph_max = max(bar_graph_max, item)

		print name
		display_profile_row_core(key_label, 'value', '  graph')
		print
		print '\t%s%s' % ('-' * (key_width + len(' | ') + value_width), bar_graph(bar_graph_max))
		i = 0
		for item in profile:
			display_profile_row(i, item)
			i += 1
		
	def print_horizontal_profile(self):
		profile = self.get_grayscale_horizontal_profile()
		self.display_profile('horizontal profile', 'X', profile)

	def print_vertical_profile(self):
		def letter_row_callback(key, value):
			'''key is profile (Y) index, value is profile value'''
			return '  ' + self.pimage.debug_row_string(key, 40)
		
		callback = None
		profile = self.get_grayscale_vertical_profile()
		# This is only readable on single letters
		if print_vertical_profile_leading_image:
			callback = letter_row_callback
		self.display_profile('vertical profile', 'Y', profile, callback)
		self.display_profile('vertical derrivative profile', 'Y', self.derrivative(profile), callback)

