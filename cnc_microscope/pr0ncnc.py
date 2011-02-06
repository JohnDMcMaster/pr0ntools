#!/usr/bin/python
# pr0ncnc: IC die image scan
# Copyright 2011 John McMaster <johnDMcMaster@gmail.com>

import sys
import time
import math
import numpy
import json
import os

VERSION = '0.1'

ACTION_GCODE = 1
ACTION_RENAME = 2
ACTION_JSON = 3

dry_run = False

def end_program():
	print
	print '(Done!)'
	print 'M2'
	
def pause(seconds):
	print 'G4 P%d' % seconds

def take_picture():
	focus_camera()
	do_take_picture()
	reset_camera()

def focus_camera():
	print 'M7'
	pause(2)

def fix_focus():
	# And just don't 
	focus_camera()

pictures_taken = 0
def do_take_picture():
	global pictures_taken

	pictures_taken += 1
	print 'M8'
	pause(3)

def reset_camera():
	print 'M9'
	
def absolute_move(x, y, z = None):
	do_move('G90', x, y, z)

def relative_move(x, y, z = None):
	if not x and not y and not z:
		print '(omitted G91 for 0 move)'
		return
	do_move('G91', x, y, z)

def do_move(code, x, y, z):
	x_part = ''
	if x:
		x_part = ' X%lf' % (x)
	y_part = ''
	if y:
		y_part = ' Y%lf' % (y)
	z_part = ''
	if z:
		z_part = ' Z%lf' % (z)

	print '%s G1%s%s%s F3' % (code, x_part, y_part, z_part)

def drange(start, stop, step, inclusive = False):
	r = start
	if inclusive:
		while r <= stop:
			yield r
			r += step
	else:
		while r < stop:
			yield r
			r += step

def drange_at_least(start, stop, step):
	'''Garauntee max is in the output'''
	r = start
	while True:
		yield r
		if r > stop:
			break
		r += step

'''
I'll move this to a JSON, XML or something format if I keep working on this

Canon SD630

15X eyepieces
	Unitron WFH15X
Objectives
	5X
	10X
	20X
	40X
	
Intel wafer
upper right: 0, 0, 0
lower left: 0.2639,0.3275,-0.0068

'''

class CameraResolution:
	width = 1280
	height = 1024
	pictures = 500

class Camera:
	vendor = "canon"
	model = "SD630"
	resolutions = list()
	memory = None
	
	def __init__():
		#resolutions.append(
		set_memory("4GB")

	def set_memory(s):
		memory = 4000000000

class FocusLevel:
	# Assume XY isn't effected by Z
	eyepiece_mag = None
	objective_mag = None
	# Not including digital
	camera_mag = None
	# Usually I don't use this, I'm not sure if its actually worth anything
	camera_digital_mag = None
	# Rough estimates for now
	# The pictures it take are actually slightly larger than the view area I think
	# Inches, or w/e your measurement system is set to
	x_view = None
	y_view = None
	
	def __init__(self):
		pass

include_rowcol = True
include_coordinate = True
def doRename():
	'''
	src: IMG_7937.JPG
	dest: c0000_r0000.jpg
		c0000_r0001.jpg
		...
		c0232_r0121.jpg
	Since we arbitrarily decided to primarily scan along y (inner loop),
	make cols first so it sorts alphabeticlly
	Looking back, x might have been more intuitive?  w/e
	Would be good to provide an option to do either anyway
	
	Composite screen: 0,0 is upper right
	Laptop: 0,0 is lower right and goes upward as y increases
	The important thing is to keep movements on x related to col changes and y movements to row changes
	
	No idea what happens at wrap around, but its coming up...
	I should reset the image seq before then
	'''
	
	image_files = []
	image_dir = '.'
	for file_name in os.listdir(image_dir):
		if file_name.lower().find('.jpg') >= 0:
			image_files.append(file_name)
	if not len(image_files) == pictures_to_take:
		raise Exception('Images: %d, expected images: %d' % (len(image_files), pictures_to_take))
	
	points = list(getPointsEx())
	if not len(points) == len(image_files):
		raise Exception('Images: %d, points: %d' % (image_files, len(points)))
	
	image_files = sorted(image_files)
	for i in range(0, pictures_to_take):
		source_file_name = image_dir + '/' + image_files[i]
		point = points[i]
		row = point[3]
		col = point[4]
		rowcol = ''
		if include_rowcol:
			rowcol = 'c%04d_r%04d' % (col, row)
		coordinate = ''
		if include_coordinate:
			coordinate = "x%05d_y%05d" % (point[0] * 1000, point[1] * 1000)
		spacer = ''
		if len(rowcol) and len(coordinate):
			spacer = '__'
		dest_file_name = '%s/%s%s%s.jpg' % (image_dir, rowcol, spacer, coordinate)
		print '%s -> %s' % (source_file_name, dest_file_name)
		if not dry_run:
			if os.path.exists(dest_file_name):
				raise Exception('path exists: %s' % dest_file_name)
			os.rename(source_file_name, dest_file_name)
		
def doJSON():
	'''
	[
		{"x": 0.0000, "y": 0.0000, "z": 0.0000, "row": },
		{"x": 0.0000, "y": 0.0023, "z": 0.0003},
		...
		{"x": 0.2132, "y": 0.2131, "z": 0.0023},
	]
	'''
	
	print '{'
	comma = ''
	for point in getPointsEx():
		print '\t{"x": %f, "y": %f, "z": %f, "row": %d, "col": %d}%s' % (point[0], point[1], point[2], point[3], point[4], comma)
		comma = ','
	print '}'
	
def doGCode():
	print ''

def getPoints():
	'''ret (x, y, z)'''
	for cur_x in drange_at_least(x_start, x_end, x_step):
		for cur_y in drange_at_least(y_start, y_end, y_step):
			cur_z = calc_z(cur_x, cur_y)
			yield (cur_x, cur_y, cur_z)

def getPointsEx():
	'''ret (x, y, z, row, col)'''
	last_x = None
	row = 0
	col = -1
	for point in getPoints():
		if not last_x == point[0]:
			col += 1
			row = 0
		yield (point[0], point[1], point[2], row, col)
		last_x = point[0]
		row += 1

# Each seems roughly in line with mag upgrade, I guess thats good
# Each higher probably more accurate than those above it if extrapolated to above?
# If this is the case too, should just need to store some reference values and can extrapolate

def help():
	print 'pr0ncnc version %s' % VERSION
	print 'Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>'
	print 'Usage:'
	print 'pr0ncnc <x1>,<y1>,<z1> [<x2>,<y2>,<z2>]' #[<x3>,<y3>,<z3> <x4>,<y4>,<z4>]]
	print 'if one set of points specified, assume 0,0,0 forms other part of rectangle'
	print 'If two points are specified, assume those as the opposing corners'
	print 'z_backlash=<val>: correction for z axis imperfections'
	print 'overlap=<val>: proportion of overlap on each image to adjacent'
	print 'overlap-max-error=<val>: max allowable overlap proportion error'
	print '--g-code: generate g-code (default)'
	print '--rename: rename images in current dir to have row/col meanings'
	print '--json: generate json with image information'
	print '--dry-run: if an actual action would be performed, don"t do it'
	print '--rowcol: include row/col in renamed files'
	print '--coordinate: include coordinate in renamed files'

	# maybe support later if makes sense, closer to polygon support
	# print 'If four points are specified, use those as the explicit corners'

if __name__ == "__main__":
	# How much to move z to ensure we aren't in a deadzone
	z_backlash = 0.01
	# Proportion of overlap on each image to adjacent
	overlap = 2.0 / 3.0
	# Maximum allowable overlap proportion error when trying to fit number of snapshots
	overlap_max_error = 0.05
	microscope_config_file_name = 'microscope.json'
	scan_config_file_name = 'scan.json'
	naked_arg_index = 0
	action = ACTION_GCODE
	
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
			if arg_key == "overlap":
				overlap = float(arg_val)
			elif arg_key == "overlap-max-error":
				overlap_max_error = float(arg_val)
			elif arg_key == "z-backlash":
				if len(z_backlash) == 0:
					z_backlash = None
				else:
					z_backlash = float(z_backlash)
			elif arg_key == "g-code":
				action = ACTION_GCODE
			elif arg_key == "rename":
				action = ACTION_RENAME
			elif arg_key == "json":
				action = ACTION_JSON
			elif arg_key == "dry-run":
				dry_run = arg_value_bool
			elif arg_key == "rowcol":
				include_rowcol = arg_value_bool
			elif arg_key == "coordinate":
				include_coordinate = arg_value_bool
			else:
				log('Unrecognized argument: %s' % arg)
				help()
				sys.exit(1)
		else:
			if naked_arg_index == 0:
				microscope_config_file_name = arg
			else:
				log('too many undecorated args: %s' % arg)
				help()
				sys.exit(1)
	
	microscope_config_file = open(microscope_config_file_name)
	microscope_config = json.loads(microscope_config_file.read())

	focus = FocusLevel()
	focus.eyepiece_mag = float(microscope_config['microscope']['eyepiece'][0])
	# objective_config = microscope_config['microscope']['objective'].itervalues().next()
	objective_config = microscope_config['microscope']['objective'][0]
	focus.objective_mag = float(objective_config['mag'])
	focus.camera_mag = float(microscope_config['camera']['mag'])
	focus.camera_digital_mag = float(microscope_config['camera']['digital_mag'])
	# FIXME: this needs a baseline and scale it
	focus.x_view = float(objective_config['x_view'])
	focus.y_view = float(objective_config['y_view'])
	
	z_backlash = float(microscope_config['stage']['z_backlash'])
	
	'''
	Planar test run
	plane calibration corner ended at 0.0000, 0.2674, -0.0129
	'''
	
	scan_config_file = open(scan_config_file_name)
	scan_config = json.loads(scan_config_file.read())

	x_start = float(scan_config['start']['x'])
	y_start = float(scan_config['start']['y'])
	z_start = float(scan_config['start']['z'])
	start = [x_start, y_start, z_start]
	
	x_end = float(scan_config['end']['x'])
	y_end = float(scan_config['end']['y'])
	z_end = float(scan_config['end']['z'])
	end = [x_end, y_end, z_end]
	
	x_other = float(scan_config['other']['x'])
	y_other = float(scan_config['other']['y'])
	z_other = float(scan_config['other']['z'])
	other = [x_other, y_other, z_other]	
	
	full_x_delta = x_end - x_start
	full_y_delta = x_end - y_start
	full_z_delta = z_end - z_start
	#print full_z_delta
	
	x_images = full_x_delta / (focus.x_view * overlap)
	y_images = full_y_delta / (focus.y_view * overlap)
	x_images = round(x_images)
	y_images = round(y_images)
	
	x_step = x_end / x_images
	y_step = y_end / y_images
	
	prev_x = 0.0
	prev_y = 0.0
	prev_z = 0.0

	'''
	To find the Z on this model, find projection to center line
	Projection of A (position) onto B (center line) length = |A| cos(theta) = A dot B / |B| 
	Should I have the z component in here?  In any case it should be small compared to others 
	and I'll likely eventually need it
	'''
	
	'''			
	planar projection
	
	Given two vectors in plane, create orthagonol basis vectors
	Project vertex onto plane to get vertex coordinates within the plane
	http://stackoverflow.com/questions/3383105/projection-of-polygon-onto-plane-using-gsl-in-c-c
	
	Constraints
	Linear XY coordinate system given
	Need to project point from XY to UV plane to get Z distance
	UV plane passes through XY origin
	
	
	Eh a simple way
	Get plane in a x + b y + c z + d = 0 form
	If we know x and y, should be simple
	d = 0 for simplicity (set plane intersect at origin)
	
	Three points
		(0, 0, 0) implicit
		(ax, ay, az) at other end of rectangle
		(bx, by, bz) somewhere else on plane, probably another corner
	Find normal vector, simple to convert to equation
		nonzero normal vector n = (a, b, c)
		through the point x0 =(x0, y0, z0)
		n * (x - x0) = 0, 
		yields ax + by + cz + d = 0 
	"Converting between the different notations in 3D"
		http://www.euclideanspace.com/maths/geometry/elements/plane/index.htm
		Convert Three points to normal notation
		N = (p1 - p0) x (p2 - p0)
		d = -N * p02
		where:
			* N = normal to plane (not necessarily unit length)
			* d = perpendicular distance of plane from origin.
			* p0,p1 and p2 = vertex points
			* x = cross product
	'''
	p0 = start
	p1 = end
	p2 = other

	# [a - b for a, b in zip(a, b)]
	# cross0 = p1 - p0
	cross0 = [t1 - t0 for t1, t0 in zip(p1, p0)]
	# cross1 = p2 - p0
	cross1 = [t2 - t0 for t2, t0 in zip(p2, p0)]
	normal = numpy.cross(cross0, cross1)
	# a x + b y + c z + d = 0 
	# z = -(a x + by) / c
	# dz/dy = -b / c
	dz_dy = -normal[1] / normal[2]

	def calc_z(cur_x, cur_y):
		if False:
			return calc_z_simple(cur_x, cur_y)
		else:
			return calc_z_planar(cur_x, cur_y)
		
	def calc_z_simple(cur_x, cur_y):
		center_length = math.sqrt(x_end * x_end + y_end * y_end)
		projection_length = (cur_x * x_end + cur_y * y_end) / center_length
		cur_z = full_z_delta * projection_length / center_length
		# Proportion of entire sweep
		#print 'cur_z: %f, projection_length %f, center_length %f' % (cur_z, projection_length, center_length)
		return cur_z
		
	def calc_z_planar(cur_x, cur_y):
		# Plane is through origin, so x0 is (0, 0, 0) and dissapears, same goes for distance d
		# Now we just need to solve the equation for z
		# a x + b y + c z + d = 0 
		# z = -(a x + b y) / c
		cur_z = -(normal[0] * cur_x + normal[1] * cur_y) / normal[2]
		return cur_z
	
	pictures_to_take = 0
	for cur_x in drange_at_least(x_start, x_end, x_step):
		for cur_y in drange_at_least(y_start, y_end, y_step):
			pictures_to_take += 1

	if action == ACTION_RENAME:
		doRename()
	elif action == ACTION_JSON:
		doJSON()
	elif action == ACTION_GCODE:	
		print
		print
		print
		print '(Generated by pr0ncnc %s on %s)' % (VERSION, time.strftime("%d/%m/%Y %H:%M:%S"))
		print '(x_step: %f, y_step: %f)' % (x_step, y_step)
		net_mag = focus.objective_mag * focus.eyepiece_mag * focus.camera_mag
		print '(objective: %f, eyepiece: %f, camera: %f, net: %f)' % (focus.objective_mag, focus.eyepiece_mag, focus.camera_mag, net_mag)
		if z_backlash:
			if dz_dy > 0:
				# Then decrease and increase
				print '(increasing dz/dy backlash normalization)'
				#relative_move(0.0, 0.0, -z_backlash)
				#relative_move(0.0, 0.0, z_backlash)
			else:
				# Then increase then decrease
				print '(decreasing dz/dy backlash normalization)'
				#relative_move(0.0, 0.0, z_backlash)
				#relative_move(0.0, 0.0, -z_backlash)
		print '(pictures: %d)' % pictures_to_take
		print


		# Because of the backlash on Z, its better to scan in same direction
		# Additionally, it doesn't matter too much for focus which direction we go, but XY is thrown off
		# So, need to make sure we are scanning same direction each time
		# err for now just easier I guess
		forward = True
		for cur_x in drange_at_least(x_start, x_end, x_step):
			first_y = True
			for cur_y in drange_at_least(y_start, y_end, y_step):
				'''
				Until I can properly spring load the z axis, I have it rubber banded
				Also, for now assume simple planar model where we assume the third point is such that it makes the plane "level"
					That is, even X and Y distortion
				'''
			
				z_backlash_delta = 0.0
				if first_y and z_backlash:
					# Reposition z to ensure we aren't getting errors from axis backlash
					# Taking into account y slant to make sure we will be going in the same direction
					# z increasing as we scan along y?
					if dz_dy > 0:
						# Then decrease and increase
						#print '(increasing dz/dy backlash normalization)'
						z_backlash_delta = -z_backlash
					else:
						# Then increase then decrease
						#print '(decreasing dz/dy backlash normalization)'
						z_backlash_delta = z_backlash

				print
				cur_z = calc_z(cur_x, cur_y)
				# print cur_z
				# print 'full_z_delta: %f, z_start %f, z_end %f' % (full_z_delta, z_start, z_end)
				print '(%f, %f, %f)' % (cur_x, cur_y, cur_z)

				#if cur_z < z_start or cur_z > z_end:
				#	print 'cur_z: %f, z_start %f, z_end %f' % (cur_z, z_start, z_end)
				#	raise Exception('z out of range')
				x_delta = cur_x - prev_x
				y_delta = cur_y - prev_y
				z_delta = cur_z - prev_z
			
				relative_move(x_delta, y_delta, z_delta + z_backlash_delta)
				if z_backlash_delta:
					relative_move(0.0, 0.0, -z_backlash_delta)
				take_picture()
				prev_x = cur_x
				prev_y = cur_y
				prev_z = cur_z
				first_y = False

			'''
			if forward:
				for cur_y in range(y_start, y_end, y_step):
					inner_loop()
			else:
				for cur_y in range(y_start, y_end, y_step):
					inner_loop()
			'''
			forward = not forward
			print

		end_program()

		print
		print
		print
		#print '(Statistics:)'
		#print '(Pictures: %d)' % pictures_taken
		if not pictures_taken == pictures_to_take:
			raise Exception('pictures taken mismatch (taken: %d, to take: %d)' % (pictures_to_take, pictures_taken))
	else:
		print 'bad action: %d' % action
		sys.exit(1)
	
