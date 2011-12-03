#!/usr/bin/python
'''
pr0ncnc: IC die image scan
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import sys
import time
import math
import numpy
import json
import os
#from pr0ntools.stitch.image_map import ImageMap 
from imager import DummyImager
import usbio
from usbio.controller import DummyController

VERSION = '0.1'

ACTION_GCODE = 1
ACTION_RENAME = 2
ACTION_JSON = 3

dry_run = False
# Coordinate seems to be accurate enough and more intuitive to work with
include_rowcol = False
include_coordinate = True
	


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


def genBasename(point, original_file_name):
	suffix = original_file_name.split('.')[1]
	row = point[3]
	col = point[4]
	rowcol = ''
	if include_rowcol:
		rowcol = 'c%04d_r%04d' % (col, row)
	coordinate = ''
	# 5 digits seems quite reasonable
	if include_coordinate:
		coordinate = "x%05d_y%05d" % (point[0] * 1000, point[1] * 1000)
	spacer = ''
	if len(rowcol) and len(coordinate):
		spacer = '__'
	return "%s%s%s%s" % (rowcol, spacer, coordinate, suffix)

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

class Planner:
	def __init__(self, progress_cb = None):
		self.progress_cb = progress_cb
	
		# Proportion of overlap on each image to adjacent
		overlap = 2.0 / 3.0
		# Maximum allowable overlap proportion error when trying to fit number of snapshots
		overlap_max_error = 0.05
		microscope_config_file_name = 'microscope.json'
		scan_config_file_name = 'scan.json'
		naked_arg_index = 0
		action = ACTION_GCODE
		
		microscope_config_file = open(microscope_config_file_name)
		microscope_config = json.loads(microscope_config_file.read())

		focus = FocusLevel()
		self.focus = focus
		try:
			focus.eyepiece_mag = float(microscope_config['microscope']['eyepiece'][0])
		except:
			focus.eyepiece_mag = 1.0
		# objective_config = microscope_config['microscope']['objective'].itervalues().next()
		objective_config = microscope_config['microscope']['objective'][0]
		focus.objective_mag = float(objective_config['mag'])
		focus.camera_mag = float(microscope_config['camera']['mag'])
		focus.camera_digital_mag = float(microscope_config['camera']['digital_mag'])
		# FIXME: this needs a baseline and scale it
		focus.x_view = float(objective_config['x_view'])
		focus.y_view = float(objective_config['y_view'])
	
		'''
		Planar test run
		plane calibration corner ended at 0.0000, 0.2674, -0.0129
		'''
	
		scan_config_file = open(scan_config_file_name)
		scan_config = json.loads(scan_config_file.read())

		self.z = True

		self.x_start = float(scan_config['start']['x'])
		self.y_start = float(scan_config['start']['y'])
		try:
			self.z_start = float(scan_config['start']['z'])
		except:
			self.z_start = None
			self.z = False
		self.start = [self.x_start, self.y_start, self.z_start]
	
		self.x_end = float(scan_config['end']['x'])
		self.y_end = float(scan_config['end']['y'])
		try:
			self.z_end = float(scan_config['end']['z'])
		except:
			self.z_end = None
			self.z = False
		self.end = [self.x_end, self.y_end, self.z_end]
	
		try:
			self.x_other = float(scan_config['other']['x'])
			self.y_other = float(scan_config['other']['y'])
			try:
				self.z_other = float(scan_config['other']['z'])
			except:
				self.z_other = None
				self.z = False
			self.other = [self.x_other, self.y_other, self.z_other]	
		except:
			self.other = None
		
		if not self.z:
			print 'WARNING: crudely removing Z since its not present or broken'
		
		full_x_delta = self.x_end - self.x_start
		full_y_delta = self.y_end - self.y_start
		if self.z_start is None or self.z_end is None:
			full_z_delta = None
		else:
			full_z_delta = self.z_end - self.z_start
		#print full_z_delta
	
		print 'Overlap: %f' % overlap
		print 'full x delta: %f, y delta: %f' % (full_x_delta, full_y_delta)
		print 'view x: %f, y: %f' % (focus.x_view, focus.y_view)
		x_images = full_x_delta / (focus.x_view * overlap)
		y_images = full_y_delta / (focus.y_view * overlap)
		print 'x images pre round: %f' % x_images
		print 'y images pre round: %f' % y_images
		x_images = round(x_images)
		y_images = round(y_images)
		print 'x images: %d' % x_images
		print 'y images: %d' % y_images
	
		#sys.exit(1)
	
		if self.z:
			self.z_backlash = float(microscope_config['stage']['z_backlash'])
		else:
			self.z_backlash = None
	
		self.x_step = self.x_end / x_images
		self.y_step = self.y_end / y_images
		print 'step x: %f, y: %f' % (self.x_step, self.y_step)
	
		if self.z and self.other:
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
			p0 = self.start
			p1 = self.end
			p2 = self.other

			# [a - b for a, b in zip(a, b)]
			# cross0 = p1 - p0
			cross0 = [t1 - t0 for t1, t0 in zip(p1, p0)]
			# cross1 = p2 - p0
			cross1 = [t2 - t0 for t2, t0 in zip(p2, p0)]
			self.normal = numpy.cross(cross0, cross1)
			# a x + b y + c z + d = 0 
			# z = -(a x + by) / c
			# dz/dy = -b / c
			self.dz_dy = -self.normal[1] / self.normal[2]
	
		self.pictures_to_take = 0
		#self.pictures_to_take = len(list(drange_at_least(self.x_start, self.x_end, self.x_step))) * len(list(drange_at_least(self.y_start, self.y_end, self.y_step)))
		for cur_x in drange_at_least(self.x_start, self.x_end, self.x_step):
			for cur_y in drange_at_least(self.y_start, self.y_end, self.y_step):
				self.pictures_to_take += 1
		self.pictures_taken = 0
		self.notify_progress()

	def notify_progress(self):
		if self.progress_cb:
			self.progress_cb(self.pictures_to_take, self.pictures_taken)

	def comment(self, s = ''):
		if len(s) == 0:
			print
		else:
			print '# %s' % s

	def calc_z(self, cur_x, cur_y):
		if not self.z:
			return None
			
		if False:
			return self.calc_z_simple(cur_x, cur_y)
		else:
			return self.calc_z_planar(cur_x, cur_y)
	
	def calc_z_simple(self, cur_x, cur_y):
		center_length = math.sqrt(self.x_end * self.x_end + self.y_end * self.y_end)
		projection_length = (cur_x * self.x_end + cur_y * self.y_end) / center_length
		cur_z = full_z_delta * projection_length / center_length
		# Proportion of entire sweep
		#print 'cur_z: %f, projection_length %f, center_length %f' % (cur_z, projection_length, center_length)
		return cur_z
	
	def calc_z_planar(self, cur_x, cur_y):
		# Plane is through origin, so x0 is (0, 0, 0) and dissapears, same goes for distance d
		# Now we just need to solve the equation for z
		# a x + b y + c z + d = 0 
		# z = -(a x + b y) / c
		cur_z = -(self.normal[0] * cur_x + self.normal[1] * cur_y) / self.normal[2]
		return cur_z
		
	def end_program(self):
		pass
	
	def pause(self, seconds):
		pass

	def take_picture(self):
		self.focus_camera()
		self.do_take_picture()
		self.pictures_taken += 1
		self.reset_camera()
		self.notify_progress()
	
	def do_take_picture(self):
		print 'Taking picture'
		pass
		
	def reset_camera(self):
		pass
		
	def focus_camera(self):
		pass
	
	def relative_move(self, x, y, z = None):
		print 'Relative move to (%f, %f, %s)' % (x, y, str(z))
		pass
	
	def getPoints(self):
		'''ret (x, y, z)'''
		for cur_x in drange_at_least(self.x_start, self.x_end, self.x_step):
			for cur_y in drange_at_least(self.y_start, self.y_end, self.y_step):
				cur_z = self.calc_z(cur_x, cur_y)
				yield (cur_x, cur_y, cur_z)

	def getPointsEx(self):
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
	
	def run(self):
		print
		print
		print
		self.comment('Generated by pr0ncnc %s on %s' % (VERSION, time.strftime("%d/%m/%Y %H:%M:%S")))
		focus = self.focus
		net_mag = focus.objective_mag * focus.eyepiece_mag * focus.camera_mag
		self.comment('objective: %f, eyepiece: %f, camera: %f, net: %f' % (focus.objective_mag, focus.eyepiece_mag, focus.camera_mag, net_mag))
		self.comment('x size: %f, y size: %f' % (self.x_end - self.x_start, self.y_end - self.y_start))
		self.comment('x fov: %f, y fov: %f' % (focus.x_view, focus.y_view))
		self.comment('x_step: %f, y_step: %f' % (self.x_step, self.y_step))
		
		z_backlash = self.z_backlash
		if z_backlash:
			if self.dz_dy > 0:
				# Then decrease and increase
				self.comment('increasing dz/dy backlash normalization')
				#relative_move(0.0, 0.0, -z_backlash)
				#relative_move(0.0, 0.0, z_backlash)
			else:
				# Then increase then decrease
				self.comment('decreasing dz/dy backlash normalization')
				#relative_move(0.0, 0.0, z_backlash)
				#relative_move(0.0, 0.0, -z_backlash)
		self.comment('pictures: %d' % self.pictures_to_take)
		self.comment()

		prev_x = 0.0
		prev_y = 0.0
		prev_z = 0.0

		# Because of the backlash on Z, its better to scan in same direction
		# Additionally, it doesn't matter too much for focus which direction we go, but XY is thrown off
		# So, need to make sure we are scanning same direction each time
		# err for now just easier I guess
		forward = True
		for cur_x in drange_at_least(self.x_start, self.x_end, self.x_step):
			first_y = True
			for cur_y in drange_at_least(self.y_start, self.y_end, self.y_step):
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
					if self.dz_dy > 0:
						# Then decrease and increase
						#self.comment('increasing dz/dy backlash normalization')
						z_backlash_delta = -z_backlash
					else:
						# Then increase then decrease
						#self.comment('decreasing dz/dy backlash normalization')
						z_backlash_delta = z_backlash

				print
				cur_z = self.calc_z(cur_x, cur_y)
				# print cur_z
				# print 'full_z_delta: %f, z_start %f, z_end %f' % (full_z_delta, z_start, z_end)
				self.comment('(%f, %f, %s)' % (cur_x, cur_y, str(cur_z)))

				#if cur_z < z_start or cur_z > z_end:
				#	print 'cur_z: %f, z_start %f, z_end %f' % (cur_z, z_start, z_end)
				#	raise Exception('z out of range')
				x_delta = cur_x - prev_x
				y_delta = cur_y - prev_y
				if self.z:
					z_delta = cur_z - prev_z
		
				z_param = None
				if self.z:
					z_param = z_delta + z_backlash_delta
				self.relative_move(x_delta, y_delta, z_param)
				if z_backlash_delta:
					self.relative_move(0.0, 0.0, -z_backlash_delta)
				self.take_picture()
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
			#raise Exception('break')

		self.cur_x = cur_x
		self.cur_y = cur_y
		self.home()
		self.end_program()

		print
		print
		print
		#self.comment('Statistics:')
		#self.comment('Pictures: %d' % pictures_taken)
		if not self.pictures_taken == self.pictures_to_take:
			raise Exception('pictures taken mismatch (taken: %d, to take: %d)' % (self.pictures_to_take, self.pictures_taken))
			
	def home(self):
		self.relative_move(-self.cur_x, -self.cur_y)

class GCodePlanner(Planner):
	'''
	M7 (coolant on): tied to focus / half press pin
	M8 (coolant flood): tied to snap picture
		M7 must be depressed first
	M9 (coolant off): release focus / picture
	'''
	
	def __init__(self):
		Planner.__init__(self)

	def do_take_picture(self):
		self.line('M8')
		self.pause(3)

	def reset_camera(self):
		# original needed focus button released
		self.line('M9')
	
	def absolute_move(self, x, y, z = None):
		self.do_move('G90', x, y, z)

	def relative_move(self, x, y, z = None):
		if not x and not y and not z:
			self.line('(omitted G91 for 0 move)')
			return
		self.do_move('G91', x, y, z)

	def do_move(self, code, x, y, z):
		x_part = ''
		if x:
			x_part = ' X%lf' % (x)
		y_part = ''
		if y:
			y_part = ' Y%lf' % (y)
		z_part = ''
		if z:
			z_part = ' Z%lf' % (z)

		self.line('%s G1%s%s%s F3' % (code, x_part, y_part, z_part))

	def comment(self, s = ''):
		if len(s) == 0:
			self.line()
		else:
			self.line('(%s)' % s)

	def focus_camera(self):
		self.line('M7')
		self.pause(2)

	# What was this?
	'''
	def fix_focus(self):
		# And just don't 
		#focus_camera()
		pass
	'''

	def line(self, s = ''):
		print s

	def end_program(self):
		self.line()
		self.line('(Done!)')
		#self.line('M2')

'''
Live control using an active Controller object
'''
class ControllerPlanner(Planner):
	def __init__(self, controller = None, imager = None):
		Planner.__init__(self)
		
		if controller is None:
			controller = DummyController()
		if imager is None:
			imager = DummyImager()
		
		self.controller = controller
		self.imager = imager


	def do_take_picture(self):
		#self.line('M8')
		#self.pause(3)
		# TODO: add this in once I move over to the windows machine
		time.sleep(0.5)
		pass

	def reset_camera(self):
		# original needed focus button released
		#self.line('M9')
		# suspect I don't need anything here
		pass
	
	def relative_move(self, x, y, z = None):
		if not x and not y and not z:
			print 'Omitting 0 move'
			return
		if x:
			self.controller.x.jog(x)
		if y:
			self.controller.y.jog(y)
		if z:
			self.controller.z.jog(z)

	def focus_camera(self):
		# no z axis control right now
		pass
		
	def end_program(self):
		print 'Done!'

