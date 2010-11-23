'''
This file is part of pr0ntools
mask ROM utilities
Copyright 2010 John McMaster
Licensed under GPL V3+
'''

import common_driver
import sys
import pimage
import projection_profile

class MROM:
	def __init__(self, pimage):
		self.pimage = pimage
		self.threshold_0 = 0.3
		self.threshold_1 = 0.3

	def print_bits(self):
		print self.get_bits()

	def get_bits(self):
		'''
		1: confident is a 1
		0: confident is a 0
		X: unknown value
		'''
		
		pprofile = projection_profile.ProjectionProfile(self.pimage)
		pprofile.print_horizontal_profile()

		return '10101100'

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

