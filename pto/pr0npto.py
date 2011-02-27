#!/usr/bin/python
'''
pr0npto: .pto file manipulation
Copyright 2010 John McMaster <johnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

from pr0ntools.stitch.pto.project import PTOProject
import sys 
import os.path

VERSION = '0.1'


def help():
	print 'pr0npto version %s' % VERSION
	print 'Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>'
	print 'Usage:'
	print 'pr0npto [args] <files>'
	print '--result=<file_name> or --out=<file_name>'

def arg_fatal(s):
	print s
	help()
	sys.exit(1)

if __name__ == "__main__":
	image_file_names = list()
	project_file_names = list()
	
	for arg_index in range (1, len(sys.argv)):
		arg = sys.argv[arg_index]
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

			if arg_key == "help":
				help()
				sys.exit(0)
			else:
				arg_fatal('Unrecognized arg: %s' % arg)
		else:
			if arg.find('.pto') > 0:
				project_file_names.append(arg)
			elif os.path.isfile(arg) or os.path.isdir(arg):
				image_file_names.append(arg)
			else:
				arg_fatal('unrecognized arg: %s' % arg)

	project = PTOProject.from_file_name('out.pto')
	project.parse()
	project.regen()
	print project.get_text()
	project.save_as('out_reparsed.pto')
	
	print 'Done!'

