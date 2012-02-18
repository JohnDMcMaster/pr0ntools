from pr0ntools.stitch.image_coordinate_map import ImageCoordinateMap
from pr0ntools.pimage import PImage
import os
import shutil

class Object():
	pass

def rotate_tiles(src_dir, dst_dir, degrees, force = False):
	self = Object()

	if src_dir[-1] == '/':
		src_dir = src_dir[0:-1]
	if dst_dir is None:
		dst_dir = src_dir + "-rotated"

	if os.path.exists(dst_dir):
		if force:
			shutil.rmtree(dst_dir)
		else:
			raise Exception('Output alrady exists, must set force')
	if not os.path.exists(dst_dir):
		os.mkdir(dst_dir)

	if degrees == 0:
		print 'WARNING: rotate got 0 degrees, aborting'
		return
	
	# And that only if the tiles are the same width and height	
	# which is not required but the usual
	#if not degrees in (90, 180, 270):
	if not degrees in [180]:
		raise Exception('Only right angle degrees currently supported')
	
	print 'Rotating dir %s to dir %s %d degrees' % (src_dir, dst_dir, degrees)
	icm = ImageCoordinateMap.from_dir_tagged_file_names(src_dir)
	
	# Verify uniform size
	print "Verifying tile size...."
	self.tw = None
	self.th = None
	# For the first level we copy things over
	for (src, row, col) in icm.images():
		pi = PImage.from_file(src)
		# I could actually set with / height here but right now this is
		# coming up fomr me accidentially using 256 x 256 tiles when the 
		# standard is 250 x 250
		if self.tw is None:
			self.tw = pi.width()
		if self.th is None:
			self.th = pi.height()
		if pi.width() != self.tw or pi.height() != self.th:
			raise Exception('Source image incorrect size')
		
	for (src, src_row, src_col) in icm.images():
		extension = '.jpg'
		extension = '.' + src.split('.')[-1]
		
		if degrees == 180:
			dst_row = icm.height() - src_row - 1
			dst_col = icm.width() - src_col - 1
		else:
			dst_row = src_row
			dst_col = src_col
		
		dst = os.path.join(dst_dir, 'y%03d_x%03d%s' % (dst_row, dst_col, extension))
		pi = PImage.from_file(src)
		pip = pi.rotate(degrees)
		print '%s => %s' % (src, dst)
		pip.save(dst)
	

#def rotate_map(dir):




