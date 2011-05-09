'''
TODO: merge with image_coordinate_map
Mutated into similar object and originally wasn't inteded to be similar

Upper left hand coordinate system
Widths extends towards lower right

WARNING: coordinates can be negative
We are approximating an image layout and deltas are not accurate
'''

from pr0ntools.pimage import PImage

class SpatialPoint:
	def __init__(self, image_file_name, y, x, y_width, x_width):
		self.image_file_name = image_file_name
		self.coordinates = (y, x)
		self.sizes = (y_width, x_width)

	def __repr__(self):
		return "%s is %dh X %dw @ (%dy, %dx)" % (self.image_file_name, self.sizes[0], self.sizes[1], self.coordinates[0], self.coordinates[1])

	def height(self):
		return self.sizes[0]

	def width(self):
		return self.sizes[1]
	
	def y(self):
		return self.coordinates[0]
	
	def x(self):
		return self.coordinates[1]
		
class SpatialAxisList:
	def __init__(self, index):
		self.axis_index = index
		self.points = list()
		self.indexes = dict()
	
	def add(self, point):
		self.points.append(point)
		'''
		import traceback
		import sys
		import os
		import time
		print 'print stack'
		sys.stdout.flush()
		sys.stderr.flush()
		traceback.print_stack()
		sys.stdout.flush()
		sys.stderr.flush()
		print 'POINTS: ', len(self.points)
		print self.points
		print self
		sys.stdout.flush()
		sys.stderr.flush()
		if len(self.points) > 4:
			print self.points
			raise Exception('die')
		'''
		
	def sort(self):
		# Sort
		self.points = sorted(self.points, key=lambda point: point.coordinates[self.axis_index])

		# Rebuild reverse index
		self.indexes = dict()
		for i in range(0, len(self.points)):
			self.indexes[self.points[i]] = i

	def intersection(self, point, ignore_upper = False):
		# Find our index and then creep out
		# Assume sorted
		ret = set()
		index = self.indexes[point]

		# Creep down
		#print 'Looking from index %d on size %d'% (index, len(self.points))
		#print self.points
		for cur_index in range(index - 1, -1, -1):
			cur_point = self.points[cur_index]
			#print '%s vs %s' % (repr(point), repr(cur_point))
			
			min_overlap = max(point.sizes[self.axis_index], cur_point.sizes[self.axis_index]) * 0.1
			
			# Still in range?
			# CCCCC 
			#    PPPPP
			overlap = cur_point.coordinates[self.axis_index] + cur_point.sizes[self.axis_index] - point.coordinates[self.axis_index]

			was_rejected = overlap < min_overlap
			if was_rejected:
				rejected_str = 'REJECTED'
			else:
				rejected_str = 'KEEP'
			print 'overlap %d is %f from %s and %s: %s' % (self.axis_index, overlap, point, cur_point, rejected_str)
			
			if was_rejected:
				# Sorted so not continue
				break
				
			#print ret
			#print cur_point.image_file_name
			#print point.image_file_name
			ret.add(cur_point.image_file_name)
			
		# Creep up
		if not ignore_upper:
			for cur_index in range(index + 1, len(self.points)):
				cur_point = self.points[cur_index]
			
				# Still in range?
				# PPPPP
				#    CCCCC
				if point.coordinates[self.axis_index] + point.sizes[self.axis_index] <= cur_point.coordinates[self.axis_index]:
					break
			ret.add(cur_point.image_file_name)
		
		return ret
		
class SpatialMap:
	def __init__(self):
		self.y_list = SpatialAxisList(0)
		self.x_list = SpatialAxisList(1)
		self.points = dict()
		self.is_sorted = True

	def add_point(self, y, x, image_file_name):
		image = PImage.from_file(image_file_name)
		point = SpatialPoint(image_file_name, y, x, image.height(), image.width())
		if image_file_name in self.points:
			raise Exception("duplicate key")
		self.points[image_file_name] = point
		#print self.x_list
		#print self.y_list
		self.y_list.add(point)
		self.x_list.add(point)
		self.is_sorted = False
	
	def sort(self):
		self.y_list.sort()
		self.x_list.sort()
		self.is_sorted = True

	# Ignoring upper is automatic de-duplication and less work
	def find_overlap(self, image_file_name, ignore_upper = False):
		#print self.points
		
		if not self.is_sorted:
			self.sort()
		# Can happen for failed generation where we estimate position and continue
		#if not image_file_name in self.points:
		#	return None
		point = self.points[image_file_name]
		y_intersection = self.y_list.intersection(point, ignore_upper)
		x_intersection = self.x_list.intersection(point, ignore_upper)
		intersection = y_intersection.intersection(x_intersection)
		print 'insersection y raw: %d, x raw: %d, full: %d' % (len(y_intersection), len(x_intersection), len(intersection))
		# Now convert to pair list
		ret = list()
		for name in intersection:
			ret.append(tuple(sorted((image_file_name, name))))
		
		return ret
		
