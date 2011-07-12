'''
This file is part of pr0ntools
Common "main" functionality
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import sys

class CommonDriver:
	def __init__(self):
		self.propagate_exceptions = True

	def help(self):
		self.program_name_help_line
		'Usage:'
		'%s [args]' % sys.argv[0]
		self.print_args()
		'--help: this message'

	def print_args(self):
		pass
		
	def parse_arg(self, arg):
		return False
		
	def parse_main(self, args = sys.argv):
		for arg_index in range (1, len(args)):
			arg = args[arg_index]
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
		
			if self.parse_arg(arg):
				pass
			elif arg_key == "help":
				self.help()
				sys.exit(0)
			else:
				'Unrecognized argument: %s' % arg
				self.help()
				sys.exit(1)
	
	def process(self):
		pass

