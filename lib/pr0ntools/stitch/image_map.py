'''
pr0ntools
Copyright 2010 John McMaster <johnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details

Manages a spacial layout of a collection of images
'''

class ImageMapPoint:
	file_name = None
	
	# Discrete version
	row = None
	col = None
	
	# Absolute version
	x = None
	y = None

class ImageMap:
	points = list()
	points_by_rowcol = dict()
	
	def add(self, image_map_point):
		self.points.append(image_map_point)
		if image_map_point.col and image_map_point.row:
			points_by_rowcol[(image_map_point.col, image_map_point.row)] = image_map_point

	def to_JSON(self):
		'''
		[
			{"x": 0.0000, "y": 0.0000, "z": 0.0000, "row": },
			{"x": 0.0000, "y": 0.0023, "z": 0.0003},
			...
			{"x": 0.2132, "y": 0.2131, "z": 0.0023},
		]
		'''
	
		mapper = ImageMap()
	
		print '{'
		comma = ''
		for point in getPointsEx():
			print '\t{"x": %f, "y": %f, "z": %f, "row": %d, "col": %d, "file_name": "%s"}%s' % \
					(point[0], point[1], point[2], point[3], point[4], genBasename(point, ".jpg"), comma)
			comma = ','
		print '}'

