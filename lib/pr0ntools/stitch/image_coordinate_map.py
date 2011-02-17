import os
from pr0ntools.pimage import PImage

'''
Grid coordinates
Not an actual image
'''
class ImageCoordinateMapPairing:
	col = None
	row = None
	
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
	# Of type ImageCoordinateMapPairing
	first = None
	second = None
	
	def __init__(self, first, second):
		self.first = first
		self.second = second

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

class ImageCoordinateMap:
	'''
				col/x
		       	0		1		2
	row  0		[0, 0]	[1, 0]	[2, 0]
	y    1		[0, 1]	[1, 1]	[2, 1]
	     2		[0, 2]	[1, 2]	[2, 2] 
	'''
	# The actual imageimage_file_names position mapping
	# Maps rows and cols to image file names
	# would like to change this to managed PImages or something
	# layout[col/x][row/y]
	layout = None
	# ie x in range(0, cols)
	cols = None
	# ie y in range(0, rows)
	rows = None
	def __init__(self, cols, rows):
		self.cols = cols
		self.rows = rows
		self.layout = [None] * (cols * rows)
	
	def get_image(self, col, row):
		return self.layout[self.cols * row + col]
	
	def get_images_from_pair(self, pair):
		# ImageCoordinatePair
		return (self.get_image(pair.first.col, pair.first.row), self.get_image(pair.second.col, pair.second.row))
	
	def set_image(self, col, row, file_name):
		self.layout[self.cols * row + col] = file_name

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
	def from_file_names(file_names_in, flip_col = False, flip_row = False, flip_pre_transpose = False, flip_post_transpose = False, depth = 1):
		file_names = ImageCoordinateMap.get_file_names(file_names_in, depth)
		'''
		Certain program take file names relative to the project file, others to working dir
		Since I like making temp files in /tmp so as not to clutter up working dir, this doesn't work well
		Only way to get stable operation is to make all file paths canonical
		'''
		file_names_canonical = list()
		for file_name in file_names:
			file_names_canonical.append(os.path.realpath(file_name))
		return ImageCoordinateMap.from_file_names_core(file_names_canonical, flip_col, flip_row, flip_pre_transpose, flip_post_transpose)
	
	@staticmethod
	def from_file_names_core(file_names, flip_col, flip_row, flip_pre_transpose, flip_post_transpose):
		first_parts = set()
		second_parts = set()
		for file_name in file_names:
			basename = os.path.basename(file_name)
			core_file_name = basename.split('.')[0]
			first_parts.add(core_file_name.split('_')[0])
			second_parts.add(core_file_name.split('_')[1])
		
		# Assume X first so that files read x_y.jpg which seems most intuitive (to me FWIW)
		cols = len(first_parts)
		rows = len(second_parts)
		print 'initial cols / X dim / width: %d, rows / Y dim / height: %d' % (cols, rows)
		
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
				
				effective_col = cur_col
				effective_row = cur_row

				if flip_pre_transpose:
					temp = effective_row
					effective_row = effective_col
					effective_col = temp

				if flip_col:
					effective_col = effective_cols - effective_col - 1
					
				if flip_row:
					effective_row = effective_rows - effective_row - 1
				
				if flip_post_transpose:
					temp = effective_row
					effective_row = effective_col
					effective_col = temp
				
				if effective_col >= effective_cols or effective_row >= effective_rows:
					print 'effective_col %d >= effective_cols %d or effective_row %d >= effective_rows %d' % (effective_col, effective_cols, effective_row, effective_rows)
					raise Exception('die')
				
				ret.set_image(effective_col, effective_row, file_name)
				file_names_index += 1
		return ret
	
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

