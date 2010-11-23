'''
This file is part of pr0ntools
Projection profile utility class
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under GPL V3+
'''

import sys
import util

class Profile:
	def __init__(self, profile):
		self.profile = profile

	def derrivative(self):
		'''return a simple derrivative, x[i + 1] - x[i]'''
		'''
		-----
		12				+12
		8	   =>		-4
		100			  +92
		-----		   -100
		'''
		if len(self.profile) == 0:
			# Profile of length 1 would be len=2, so len=1 for 0 seems reasonable
			return [0]

		# We aren't scaling by array length since its usually relative values and so doesn't matter
		d = [0] * (len(self.profile) + 1)
		# Previous value is 0 and can be important if we have a large spike at the end
		d[0] = self.profile[0]
		for i in range(1, len(self.profile)):
			d[i - 1] = self.profile[i] - self.profile[i - 1]
		d[len(self.profile)] = -self.profile[len(self.profile) - 1]
		return d

	def next_max(self, pos):
		pass
		
	def next_min(self, pos):
		pass

	def display_profile(self, name, key_label, callback = None):
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

		for item in self.profile:
			bar_graph_max = max(bar_graph_max, item)

		print name
		display_profile_row_core(key_label, 'value', '  graph')
		print
		print '\t%s%s' % ('-' * (key_width + len(' | ') + value_width), bar_graph(bar_graph_max))
		i = 0
		for item in self.profile:
			display_profile_row(i, item)
			i += 1

