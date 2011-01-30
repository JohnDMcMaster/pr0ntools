#!/usr/bin/python
# pr0ncnc: IC die image scan
# Copyright 2011 John McMaster <johnDMcMaster@gmail.com>

import sys
import time
import math
import numpy

VERSION = '0.1'

def help():
	print 'pr0ncnc version %s' % VERSION
	print 'Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>'
	print 'Usage:'
	print 'pr0nstitch <x1>,<y1>,<z1> [<x2>,<y2>,<z2>]' #[<x3>,<y3>,<z3> <x4>,<y4>,<z4>]]
	print 'if one set of points specified, assume 0,0,0 forms other part of rectangle'
	print 'If two points are specified, assume those as the opposing corners'
	# maybe support later if makes sense, closer to polygon support
	# print 'If four points are specified, use those as the explicit corners'

def end_program():
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
	eyepeice_mag = None
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

# Each seems roughly in line with mag upgrade, I guess thats good
# Each higher probably more accurate than those above it if extrapolated to above?
# If this is the case too, should just need to store some reference values and can extrapolate

canon_SD630_unitron_N_15XE_5XO = FocusLevel()
canon_SD630_unitron_N_15XE_5XO.eyepeice_mag = 15.0
canon_SD630_unitron_N_15XE_5XO.objective_mag = 5.0
canon_SD630_unitron_N_15XE_5XO.camera_mag = 3.0
canon_SD630_unitron_N_15XE_5XO.camera_digital_mag = 4.0
canon_SD630_unitron_N_15XE_5XO.x_view = 0.0350
canon_SD630_unitron_N_15XE_5XO.y_view = 0.0465

canon_SD630_unitron_N_15XE_10XO = FocusLevel()
canon_SD630_unitron_N_15XE_10XO.eyepeice_mag = 15.0
canon_SD630_unitron_N_15XE_10XO.objective_mag = 10.0
canon_SD630_unitron_N_15XE_10XO.camera_mag = 3.0
canon_SD630_unitron_N_15XE_10XO.camera_digital_mag = 4.0
canon_SD630_unitron_N_15XE_10XO.x_view = 0.0170
canon_SD630_unitron_N_15XE_10XO.y_view = 0.0240

canon_SD630_unitron_N_15XE_20XO = FocusLevel()
canon_SD630_unitron_N_15XE_20XO.eyepeice_mag = 15.0
canon_SD630_unitron_N_15XE_20XO.objective_mag = 10.0
canon_SD630_unitron_N_15XE_20XO.camera_mag = 3.0
canon_SD630_unitron_N_15XE_20XO.camera_digital_mag = 4.0
canon_SD630_unitron_N_15XE_20XO.x_view = 0.0170/2.0
canon_SD630_unitron_N_15XE_20XO.y_view = 0.0240/2.0

canon_SD630_unitron_N_15XE_40XO = FocusLevel()
canon_SD630_unitron_N_15XE_40XO.eyepeice_mag = 15.0
canon_SD630_unitron_N_15XE_40XO.objective_mag = 10.0
canon_SD630_unitron_N_15XE_40XO.camera_mag = 3.0
canon_SD630_unitron_N_15XE_40XO.camera_digital_mag = 4.0
canon_SD630_unitron_N_15XE_40XO.x_view = 0.0170/4.0
canon_SD630_unitron_N_15XE_40XO.y_view = 0.0240/4.0

if __name__ == "__main__":
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
		if arg_key == "at-optimized-parameters":
			at_optmized_parameters = arg_values
		else:
			log('Unrecognized argument: %s' % arg)
			help()
			sys.exit(1)
	
	focus = canon_SD630_unitron_N_15XE_5XO
	overlap = 2.0 / 3.0
	overlap_max_error = 0.05
	
	'''
	Planar test run
	plane calibration corner ended at 0.0000, 0.2674, -0.0129
	'''
	
	x_start = 0.0
	y_start = 0.0
	z_start = 0.0
	start = [x_start, y_start, z_start]
	
	x_end = 0.4056
	y_end = 0.4595
	z_end = 0.0140
	end = [x_end, y_end, z_end]
	
	x_other = 0.0171
	y_other = 0.4595
	z_other = 0.0018
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
	def calc_z():
		if False:
			return calc_z_simple()
		else:
			return calc_z_planar()
		
	def calc_z_simple():
		center_length = math.sqrt(x_end * x_end + y_end * y_end)
		projection_length = (cur_x * x_end + cur_y * y_end) / center_length
		cur_z = full_z_delta * projection_length / center_length
		# Proportion of entire sweep
		#print 'cur_z: %f, projection_length %f, center_length %f' % (cur_z, projection_length, center_length)
		return cur_z
		
	def calc_z_planar():
		p0 = start
		p1 = end
		p2 = other

		# [a - b for a, b in zip(a, b)]
		# cross0 = p1 - p0
		cross0 = [t1 - t0 for t1, t0 in zip(p1, p0)]
		# cross1 = p2 - p0
		cross1 = [t2 - t0 for t2, t0 in zip(p2, p0)]
		normal = numpy.cross(cross0, cross1)
		# Plane is through origin, so x0 is (0, 0, 0) and dissapears, same goes for distance d
		# Now we just need to solve the equation for z
		# a x + b y + c z + d = 0 
		# z = -(a x + b y) / c
		cur_z = -(normal[0] * cur_x + normal[1] * cur_y) / normal[2]
		return cur_z
	
	print
	print
	print
	print '(Generated by pr0nstitch %s on %s)' % (VERSION, time.strftime("%d/%m/%Y %H:%M:%S"))

	# Because of the play on Z, its better to scan in same direction
	# Additionally, it doesn't matter too much for focus which direction we go, but XY is thrown off
	# So, need to make sure we are scanning same direction each time
	# err for now just easier I guess
	forward = True
	for cur_x in drange(x_start, x_end, x_step, True):
		for cur_y in drange(y_start, y_end, y_step, True):
			'''
			Until I can properly spring load the z axis, I have it rubber banded
			Also, for now assume simple planar model where we assume the third point is such that it makes the plane "level"
				That is, even X and Y distortion
			'''
			
			print
			cur_z = calc_z()
			# print cur_z
			# print 'full_z_delta: %f, z_start %f, z_end %f' % (full_z_delta, z_start, z_end)
			print '(%f, %f, %f)' % (cur_x, cur_y, cur_z)
			#if cur_z < z_start or cur_z > z_end:
			#	print 'cur_z: %f, z_start %f, z_end %f' % (cur_z, z_start, z_end)
			#	raise Exception('z out of range')
			x_delta = cur_x - prev_x
			y_delta = cur_y - prev_y
			z_delta = cur_z - prev_z
			
			relative_move(x_delta, y_delta, z_delta)
			take_picture()
			prev_x = cur_x
			prev_y = cur_y
			prev_z = cur_z

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
	print
	print
	print '(Statistics:)'
	print '(Pictures: %d)' % pictures_taken

	end_program()
	
