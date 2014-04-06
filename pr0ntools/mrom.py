'''
This file is part of pr0ntools
mask ROM utilities
Copyright 2010 John McMaster
Licensed under a 2 clause BSD license, see COPYING for details
'''

import common_driver
import sys
import pimage
import projection_profile
import profile
import util

class MROM:
	def __init__(self, pimage):
		self.pimage = pimage
		self.threshold_0 = 0.3
		self.threshold_1 = 0.3

	def print_bits(self):
		print self.get_bits()


	def process_adjacent_bits(self, pimage):
		'''
		Expects a thin strip containing only 1/0 bits with metal gaps (drak spots) in between
		
		1: confident is a 1
		0: confident is a 0
		X: unknown value
		
           2 |    12.925781  ========================================
           3 |    12.304688    ======================================
           4 |     9.988281            ==============================
           5 |     7.976562                  ========================
           6 |     5.769531                         =================
           7 |     4.167969                              ============
           8 |     3.324219                                ==========
           9 |     4.269531                             =============
          10 |     5.867188                        ==================
          11 |     8.164062                 =========================
          12 |    11.476562       ===================================
          13 |    12.003906     =====================================
          14 |    11.992188     =====================================
          15 |    11.476562       ===================================
          16 |     7.636719                   =======================
          17 |     4.960938                           ===============
          20 |     4.531250                            ==============
          18 |     2.796875                                  ========
          19 |     2.496094                                   =======
          21 |     6.664062                      ====================
          22 |    10.011719            ==============================
          23 |    11.234375        ==================================
          24 |    11.335938       ===================================
          25 |    11.332031       ===================================

		We are considering black 1 and white 0
		Data is where the lower spots are
		It is unknown which is 0 and which is a 1
		Arbitrarily call a 1 the higher/darker value and 0 the lower/lighter value
		'''
		
		ret = ''
		
		if True:
			'''
			small_just_bits.jpg
			Example 1's
		      47 |     2.484375                   =======================
		      26 |     2.167969                      ====================
		      57 |     2.144531                      ====================
		       5 |     1.781250                          ================

			Examle 0's
		      37 |     0.968750                                 =========
		      68 |     0.855469                                  ========
		      78 |     0.777344                                   =======
		      15 |     0.746094                                   =======
			'''
			threshold_0_min = 0.7
			threshold_0_max = 1.0
			threshold_1_min = 1.7
			threshold_1_max = 2.5			
		else:
			'''
			Because of lighting differences at the edge, it might be better to try to center on the values and
			then take a vertical projection profile derrivitive
			This will make similar edges have normalized bit behavior
		
			TODO: try k-means clustering on the high/low values
		
			small.jpg
			Example 1's
		      50 |     4.937500                           ===============
		      29 |     4.421875                             =============
		      60 |     4.328125                             =============
		       8 |     3.324219                                ==========

			Examle 0's
		      40 |     2.929688                                 =========
		      19 |     2.496094                                   =======
		      71 |     2.562500                                   =======
		      82 |     2.453125                                   =======		
			'''
			threshold_0_min = 2.3
			threshold_0_max = 3.0
			threshold_1_min = 3.1
			threshold_1_max = 5.0
		
		# How may pixels between bits
		bit_spacing = None
		pprofile = projection_profile.ProjectionProfile(pimage)
		hprofile = pprofile.get_grayscale_horizontal_profile()
		pprofile.print_horizontal_profile()
		

		local_minmax_distance = 3

		min_indexes = hprofile.get_mins(local_minmax_distance)

		# Presumably middle isn't effected by end spacing
		separation_profile = profile.Profile(min_indexes[1:-1]).derrivative()
		print separation_profile
		(separation_mean, separation_stddev) = util.mean_stddev(separation_profile.profile)
		print 'mean: %lf, stddev: %lf' % (separation_mean, separation_stddev)

		cur = 0
		while True:
			# TODO: base this off of peak spacing
			local_minmax_distance = 3
			cur = hprofile.next_min(cur, local_minmax_distance)
			if cur is None:
				break

			cur_val = hprofile.profile[cur]
			if cur_val >= threshold_0_min and cur_val <= threshold_0_max:
				next = '0'
			elif cur_val >= threshold_1_min and cur_val <= threshold_1_max:
				next = '1'
			else:
				next = 'X'

			print '%s: %s' % (cur, next)
			ret += next
		return ret
	
	def get_adjacent_bit_images(self):
		'''Generator to return the bits in sequence'''
		
		# Divide into column groups
		
		return [self.pimage]
		
	def get_bits(self):
		ret = ''
		for image in self.get_adjacent_bit_images():
			ret += self.process_adjacent_bits(image)
		return ret
		#return '10101100'

class Driver(common_driver.CommonDriver):
	def __init__(self):
		common_driver.CommonDriver.__init__(self)
		self.program_name_help_line = 'Mask ROM dumper'
		
		self.input_files = list()

	def print_args(self):
		print '--input: input file'
		print '--threshold-0: fraction of error to recognize 0, 0 being none 1 being severe'
		print '--threshold-1: fraction of error to recognize 1, 0 being none 1 being severe'

	def parse_arg(self, arg):
		arg_key = None
		arg_value = None
		if arg.find("--") == 0:
			arg_value_bool = True
			if arg.find("=") > 0:
				arg_key = arg.split("=")[0][2:]
				arg_value = arg.split("=")[1]
				if arg_value == "false" or arg_value == "0" or arg_value == "no":
					arg_value_bool = False
			else:
				arg_key = arg[2:]			
			
			if arg_key == '--input':
				self.input_files.append(arg_value)
			elif arg_key == '--threshold_0':
				self.threshold_0 = float(arg_value)
			elif arg_key == '--threshold_1':
				self.threshold_1 = float(arg_value)
			else:
				return False
		else:
			self.input_files.append(arg)
		
		return True

	def process(self):
		if len(self.input_files) == 0:
			print 'WARNING: no input files given, try --help'
			return
			
		for image_file_name in self.input_files:
			print 'Processing %s' % image_file_name
			image = pimage.PImage.from_file(image_file_name)
			mrom = MROM(image)

			try:
				mrom.print_bits()
			except:
				print 'Error printing bits'
				if self.propagate_exceptions:
					raise			

if __name__ == "__main__":
	driver = Driver()
	driver.parse_main()
	driver.process()
	sys.exit(0)

