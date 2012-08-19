'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

import math
import os
from pr0ntools.pimage import PImage

'''
Grid coordinates
Not an actual image
'''
class ImageCoordinateMapPairing:
	def __init__(self, col, row):
		self.col = col
		self.row = row
		
	def __repr__(self):
		return '(col=%d, row=%d)' % (self.col, self.row)

	def __cmp__(self, other):
		delta = self.col - other.col
		if delta:
			return delta
			
		delta = self.row - other.row
		if delta:
			return delta

		return 0
		
class ImageCoordinatePair:
	def __init__(self, first, second):
		# Of type ImageCoordinateMapPairing
		self.first = first
		self.second = second

	def adjacent(self):
		'''Return true if the two images are cow/col directly adjacent'''
		return abs(self.first.row - self.second.row) <= 1 and abs(self.first.col - self.second.col) <= 1

	def __cmp__(self, other):
		delta = self.first.__compare__(other.first)
		if delta:
			return delta
			
		delta = delta = self.second.__compare__(other.second)
		if delta:
			return delta

		return 0

	def __repr__(self):
		return '%s vs %s' % (self.first, self.second)

	@staticmethod
	def from_spatial_points(first, second):
		return ImageCoordinatePair(ImageCoordinateMapPairing(first.coordinates[1], first.coordinates[0]), ImageCoordinateMapPairing(second.coordinates[1], second.coordinates[0]))

def get_row_col(file_name):
	'''Return (row, col) tuple identify file name position'''
		
	row = None
	col = None
	
	basename = os.path.basename(file_name)
	core_file_name = basename.split('.')[0]
	parts = core_file_name.split('_')
	if len(parts) != 2:
		raise Exception('Expect files named like cXXXX_rXXXX.tif for automagic stitching, got %s' % file_name)
	
	p0 = parts[0]
	if p0.find('x') >= 0 or p0.find('c') >= 0:
		col = int(p0[1:])
	if p0.find('y') >= 0 or p0.find('r') >= 0:
		row = int(p0[1:])
	
	p1 = parts[1]
	if p1.find('x') >= 0 or p1.find('c') >= 0:
		if not col is None:
			raise Exception('conflicting row info')
		col = int(p1[1:])
	if p1.find('y') >= 0 or p1.find('r') >= 0:
		if not row is None:
			raise Exception('conflicting row info')
		row = int(p1[1:])

	#print '%s => r%d c%d' % (file_name, row, col)
	return (row, col)
	
class ImageCoordinateMap:
	'''
	Note that the values are undefined
	Original code used ImageCoordinatePair or something but later code just uses strings
	
				col/x
		       	0		1		2
	row  0		[0, 0]	[1, 0]	[2, 0]
	y    1		[0, 1]	[1, 1]	[2, 1]
	     2		[0, 2]	[1, 2]	[2, 2] 
	'''
	def __init__(self, cols, rows):
		# The actual imageimage_file_names position mapping
		# Maps rows and cols to image file names
		# would like to change this to managed PImages or something
		# layout[col/x][row/y]
		layout = None
		# ie x in range(0, cols)
		self.cols = cols
		# ie y in range(0, rows)
		self.rows = rows
		self.layout = [None] * (cols * rows)
	
	def images(self):
		'''Returns a generator giving (file name, row, col) tuples'''
		for i in range(0, len(self.layout)):
			yield (self.layout[i], i / self.cols, i % self.width())
	
	def width(self):
		'''Return number of cols'''
		return self.cols
		
	def height(self):
		'''Return number of rows'''
		return self.rows
	
	def debug_print(self):
		print 'height %d rows, width %d cols' % (self.height(), self.width())
		for row in range(self.height()):
			for col in range(self.width()):
				print '  [r%d][c%d] = %s' % (row, col, self.get_image(col, row))
	
	def get_image_safe(self, col, row):
		'''Returns none if out of bounds'''
		if col >= self.width() or row >= self.height():
			return None
		else:
			return self.get_image(col, row)
	
	def get_image(self, col, row):
		try:
			return self.layout[self.cols * row + col]
		except:
			print 'col %d row %d out of range for width %d height %d and length %d' % (col, row, self.width(), self.height(), len(self.layout))
			raise
	
	def get_images_from_pair(self, pair):
		# ImageCoordinatePair
		return (self.get_image(pair.first.col, pair.first.row), self.get_image(pair.second.col, pair.second.row))
	
	def set_image_rc(self, row, col, file_name):
		if row >= self.height() or col >= self.width():
			raise Exception('row %d, col %d are out of bounds height %d, width %d' % (row, col, self.height(), self.width()))
		try:
			self.layout[self.cols * row + col] = file_name
		except:
			print row, col
			raise
	
	def set_image(self, col, row, file_name):
		self.set_image_rc(row, col, file_name)

	@staticmethod
	def get_file_names(file_names_in, depth):
		file_names = list()
		first_parts = set()
		second_parts = set()
		for file_name_in in file_names_in:
			if os.path.isfile(file_name_in):
				if PImage.is_image_filename(file_name_in):
					file_names.append(file_name_in)
			elif os.path.isdir(file_name_in):			
				if depth:
					for file_name in os.listdir(file_name_in):
						file_names.append(get_file_names(os.path.join(file_name_in, file_name), depth - 1))
		return file_names
		
	@staticmethod
	def from_dir_tagged_file_names(dir, rows=None, cols=None):
		return ImageCoordinateMap.from_tagged_file_names([os.path.join(dir, f) for f in os.listdir(dir)], rows, cols)
		
	@staticmethod
	def from_tagged_file_names(file_names, rows=None, cols=None, partial=False):
		'''Partial: if set will allow gaps and consider it a smaller set'''
		
		print 'Constructing image coordinate map from tagged file names...'
		'''
		rows: hard code number input rows
		cols: hard code number input cols
		'''
		if rows is None and not cols is None:
			rows = math.ceil(len(file_names) / cols)
		if rows is None and not cols is None:
			cols = math.ceil(len(file_names) / rows)
		
		if rows is None or cols is None:
			print 'Row / col hints insufficient, guessing row / col layout from file names'
			row_parts = set()
			col_parts = set()			
			
			for file_name in file_names:
				(row, col) = get_row_col(file_name)
				row_parts.add(row)
				col_parts.add(col)
			
			# Assume X first so that files read x_y.jpg which seems most intuitive (to me FWIW)
			if cols is None:
				print 'Constructing columns from set %s' % str(col_parts)
				if partial:
					cols = len(col_parts)
				else:
					cols = max(col_parts) + 1
			if rows is None:
				print 'Constructing rows from set %s' % str(row_parts)
				if partial:
					rows = len(row_parts)
				else:
					rows = max(row_parts) + 1
		print 'initial cols / X dim / width: %d, rows / Y dim / height: %d' % (cols, rows)
		
		ret = ImageCoordinateMap(cols, rows)
		file_names = sorted(file_names)
		for file_name in file_names:
			# Not canonical, but resolved well enough
			(row, col) = get_row_col(file_name)
			if row is None or col is None:
				raise Exception('Bad file name %s' % file_name)
			ret.set_image_rc(row, col, file_name)
		
		return ret	
	
	@staticmethod
	def from_file_names(file_names_in, flip_col = False, flip_row = False, flip_pre_transpose = False, flip_post_transpose = False, depth = 1,
			alt_rows = False, alt_cols = False, rows = None, cols = None):
		return ImageCoordinateMap.from_file_names_core(file_names_in, flip_col, flip_row, flip_pre_transpose, flip_post_transpose,
				alt_rows, alt_cols, rows, cols)
	
	@staticmethod
	def from_file_names_core(file_names, flip_col, flip_row, flip_pre_transpose, flip_post_transpose,
			alt_rows = False, alt_cols = False, rows = None, cols = None):
		print 'Constructing image coordinate map from file names...'
		print 'Input rows hint: %s' % str(rows)
		print 'Input cols hint: %s' % str(cols)
		'''
		rows: hard code number input rows
		cols: hard code number input cols
		alt_rows: alternate second row and each other after
		alt_cols: alternate second col and each other after
		'''
		if rows is None and not cols is None:
			rows = len(file_names) / cols
		if rows is None and not cols is None:
			cols = len(file_names) / rows
		
		if rows is None or cols is None:
			'''
			this code seems to assume format col_row.tif
			I always tag them with either c001_r031.tif or x322_y32.tif type formatting
			so lets use that instead
			'''
			print 'Row / col hints insufficient, guessing row / col layout from file names'
			first_parts = set()
			second_parts = set()
			
			first_rows = 0
			first_cols = 0
			second_rows = 0
			second_cols = 0
			
			for file_name in file_names:
				basename = os.path.basename(file_name)
				core_file_name = basename.split('.')[0]
				parts = core_file_name.split('_')
				if len(parts) != 2:
					raise Exception('Expect files named like cXXXX_rXXXX.tif for automagic stitching')
				
				p0 = parts[0]
				if p0.find('x') >= 0 or p0.find('c') >= 0:
					first_cols += 1
				if p0.find('y') >= 0 or p0.find('r') >= 0:
					first_rows += 1
				first_parts.add(p0)
				
				p1 = parts[1]
				if p1.find('x') >= 0 or p1.find('c') >= 0:
					second_cols += 1
				if p1.find('y') >= 0 or p1.find('r') >= 0:
					second_rows += 1
				second_parts.add(p1)
					
			if first_rows != 0 and first_cols == 0 and second_rows == 0 and second_cols != 0:
				row_parts = first_parts
				col_parts = second_parts
			elif first_rows == 0 and first_cols != 0 and second_rows != 0 and second_cols == 0:
				row_parts = second_parts
				col_parts = first_parts
			else:
				raise Exception('Could not determine row/col source')
			
			# Assume X first so that files read x_y.jpg which seems most intuitive (to me FWIW)
			if cols is None:
				print 'Constructing columns from set %s' % str(col_parts)
				cols = len(col_parts)
			if rows is None:
				print 'Constructing rows from set %s' % str(row_parts)
				rows = len(row_parts)
		print 'initial cols / X dim / width: %d, rows / Y dim / height: %d' % (cols, rows)
		
		print 'Flip status = pre transpose: %d, post transpose: %d' % (flip_pre_transpose, flip_post_transpose)
		print 'Flip status = rows alt: %d, cols alt %d' % (alt_rows, alt_cols)
		# Make sure we end up with correct arrangement
		flips = 0
		if flip_pre_transpose:
			flips += 1
		if flip_post_transpose:
			flips += 1
		# Did we switch?
		if flips % 2 == 0:
			# No switch
			effective_cols = cols
			effective_rows = rows
		else:
			effective_cols = rows
			effective_rows = cols
		print 'effective initial cols / X dim / width: %d, rows / Y dim / height: %d' % (effective_cols, effective_rows)
		
		ret = ImageCoordinateMap(effective_cols, effective_rows)
		file_names = sorted(file_names)
		file_names_index = 0		
		'''
		Since x/col is first, y/row will increment first and must be the inner loop
		'''
		for cur_col in range(0, cols):
			for cur_row in range(0, rows):
				# Not canonical, but resolved well enough
				file_name = file_names[file_names_index]
				#print 'Assigning image name %s at raw col %d row %d' % (file_name, cur_
				
				effective_col = cur_col
				effective_row = cur_row

				if flip_pre_transpose:
					temp = effective_row
					effective_row = effective_col
					effective_col = temp

				flip_col_cur = flip_col
				flip_row_cur = flip_col
				if alt_cols and cur_row % 2 == 1:
					flip_col_cur = not flip_col_cur
				if alt_rows and cur_col % 2 == 1:
					flip_row_cur = not flip_row_cur

				if flip_col_cur:
					print 'flip col1: %d on %d' % (effective_col, effective_cols)
					effective_col = effective_cols - effective_col - 1					
					print 'flip col2: %d' % effective_col
				if flip_row_cur:
					effective_row = effective_rows - effective_row - 1
				
				if flip_post_transpose:
					temp = effective_row
					effective_row = effective_col
					effective_col = temp
						
				if effective_col >= effective_cols or effective_row >= effective_rows:
					print 'effective_col %d >= effective_cols %d or effective_row %d >= effective_rows %d' % (effective_col, effective_cols, effective_row, effective_rows)
					raise Exception('die')
				
				ret.set_image_rc(effective_row, effective_col, file_name)
				file_names_index += 1
		
		
		return ret
	
	def gen_set(self):
		'''Get all pairs that are actually in the map'''
		for col in range(self.cols):
			for row in range(self.rows):
				if self.get_image(col, row):
					yield (col, row)
	
	def gen_pairs(self, row_spread = 1, col_spread = 1):
		'''Returns a generator of ImageCoordinatePair's, sorted'''
		for col_0 in range(0, self.cols):
			for col_1 in range(max(0, col_0 - col_spread), min(self.cols, col_0 + col_spread)):
				for row_0 in range(0, self.rows):
					# Don't repeat elements, don't pair with self, keep a delta of row_spread
					for row_1 in range(max(0, row_0 - row_spread), min(self.rows, row_0 + row_spread)):
						if col_0 == col_1 and row_0 == row_1:
							continue
						# For now just allow manhatten distance of 1
						if abs(col_0 - col_1) + abs(row_0 - row_1) > 1:
							continue
						
						to_yield = ImageCoordinatePair(ImageCoordinateMapPairing(col_1, row_1), ImageCoordinateMapPairing(col_0, row_0))
						yield to_yield

	def __repr__(self):
		ret = ''
		for row in range(0, self.rows):
			for col in range(0, self.cols):
				ret += '(col/x=%d, row/y=%d) = %s\n' % (col, row, self.get_image(col, row))
		return ret

