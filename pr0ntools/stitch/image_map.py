'''
pr0ntools
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details

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

'''
def genBasename(self, point, original_file_name, rowcol=True, coord=False):
    ret = ''
    
    suffix = original_file_name.split('.')[1]
    row = point[3]
    col = point[4]
    
    rowcol = ''
    if include_rowcol:
        rowcol = 'c%04d_r%04d' % (col, row)

    coordinate = "x%03d_y%03d" % (point[0] * 1000, point[1] * 1000)
    spacer = ''
    if len(rowcol) and len(coordinate):
        spacer = '__'
    return "%s%s%s%s" % (rowcol, spacer, coordinate, suffix)

'''

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

