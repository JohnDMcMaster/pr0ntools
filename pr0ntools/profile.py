'''
This file is part of pr0ntools
Projection profile utility class
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
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
		return Profile(d)

	def next_max(self, pos):
		'''
		Max version of min, see min for details
		'''
		pass
		
	def decreases_in_range(self, start, end):
		'''
		From start to end, excluding end
		If start == end, returns False
		'''
		
		# Looks like we are at a min, but see if we are at a local min
		for pos in range(start, end):
			# Out of range?
			if pos >= len(self.profile):
				return False
		
			# Additional decrease?
			if self.profile[pos] < self.profile[pos - 1]:
				return True

	def get_mins(self, local_minmax_distance = 0):
		ret = list()
		cur = 0
		while True:
			cur = self.next_min(cur, local_minmax_distance)
			if cur is None:
				return ret
			ret.append(cur)

	def next_min(self, pos, look_ahead = 0):
		'''
		Returns next min index
		Equal value at same position does not count as min
		If at end and has decreased from original value, will be considered a min
		look_ahead: how many values to check ahead to make sure we are at a min
		'''
		has_decreased = False
		while True:
			pos += 1
			# Out of range?
			if pos >= len(self.profile):
				# If we were decreasing, consider it a min
				if has_decreased:
					return pos - 1
				else:
					return None
			if self.profile[pos] > self.profile[pos - 1]:
				if has_decreased:
					if not self.decreases_in_range(pos, pos + look_ahead):
						return pos - 1
			if self.profile[pos] < self.profile[pos - 1]:
				has_decreased = True

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

