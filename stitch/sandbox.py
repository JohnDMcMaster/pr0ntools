#!/usr/bin/python
'''
pr0npto: .pto file tests
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

def calc_centroid():
	image_0_points = set()
	image_1_points = set()
	
	# Assume that keep same ordering
	for control_point_line in project.control_point_lines:
		image_0_points.add((control_point_line.get_variable('x'), control_point_line.get_variable('y')))
		image_1_points.add((control_point_line.get_variable('X'), control_point_line.get_variable('Y')))

	print 'Output:'
	print [i[0] for i in image_0_points]
	image_0_x_average = sum([i[0] for i in image_0_points]) / len(image_0_points)
	image_0_y_average = sum([i[1] for i in image_0_points]) / len(image_0_points)
	image_1_x_average = sum([i[0] for i in image_1_points]) / len(image_1_points)
	image_1_y_average = sum([i[1] for i in image_1_points]) / len(image_1_points)

	image_0_x_proportion = image_0_x_average / project.image_lines[0].get_variable('w')
	image_0_y_proportion = image_0_y_average / project.image_lines[0].get_variable('h')
	image_1_x_proportion = image_1_x_average / project.image_lines[1].get_variable('w')
	image_1_y_proportion = image_1_y_average / project.image_lines[1].get_variable('h')
	
	x_delta = image_0_x_average - image_1_x_average
	y_delta = image_0_y_average - image_1_y_average
	
	print 'image 0, x: %f / %d (%f), y: %f / %d (%f)' % (image_0_x_average, project.image_lines[0].get_variable('w'), image_0_x_proportion, image_0_y_average, project.image_lines[0].get_variable('h'), image_0_y_proportion)
	print 'image 1, x: %f / %d (%f), y: %f / %d (%f)' % (image_1_x_average, project.image_lines[1].get_variable('w'), image_1_x_average / project.image_lines[1].get_variable('w'), image_1_y_average, project.image_lines[1].get_variable('h'), image_1_y_average / project.image_lines[1].get_variable('h'))
	print 'x delta: %f' % x_delta
	print 'y delta: %f' % y_delta
	print 'delta ratio'
	xy = x_delta / y_delta
	yx = y_delta / x_delta
	print '\tx/y: %f' % xy
	print '\ty/x: %f' % yx

	if abs(xy) > abs(yx):
		print 'x shift'
		if x_delta > 0:
			print 'right shift'
		elif x_delta < 0:
			print 'left shift'
		else:
			raise Exception("unlikely...somethings fishy")
	elif abs(xy) < abs(yx):
		print 'y shift'
		if y_delta > 0:
			print 'shift down'
		elif y_delta < 0:
			print 'shift up'
		else:
			raise Exception("unlikely...somethings fishy")
	else:
		raise Exception("unlikely...somethings fishy")

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

	project = PTOProject.from_file_name('panorama0.pto')
	project.parse()
	
	calc_centroid()
	sys.exit(1)
	
	project.regen()
	print
	print
	print
	print project.get_text()
	#project.save_as('out_reparsed.pto')
	print
	print
	print
	
	print 'Done!'

