'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import math
from pr0ntools.stitch.image_coordinate_map import ImageCoordinateMap
import os
import sys
from pr0ntools.pimage import PImage
try:
	import scipy
	from scipy import polyval, polyfit
except ImportError:
	scipy = None

'''
Second order linear system of the form:
r = c0 x0 + c1 x1 + c2

TODO: consider learning NumPy...
This is simple enough that its not justified yet
'''
"""
class LinearSystem2:
	def __init__(self, c0, c1, c2):
		self.c0 = c0
		self.c1 = c1
		self.c2 = c2
	
	def get(self, x0, x1):
		return self.c0 * x0 + self.c1 * x1 + self.c2
	
	@staticmethod
	def regression(points):
		'''Given a bunch of points return an object representing the system'''
		
		(c0, c1, c2) = polyfit(t,xn,1)

		
	@staticmethod
	def sorted_regression(points):
		'''Given a bunch of points return an object representing the system'''
"""

def regress_row(m, pto, rows, selector, allow_missing = False):
	# Discard the constants, we will pick a reference point later
	slopes = []
	for row in rows:
		'''
		For each column find a y position error
		y = col * c0 + c1
		'''
		cols = []
		deps = []
		for col in range(m.width()):
			fn = m.get_image(col, row)
			if fn is None:
				if allow_missing:
					continue
				raise Exception('c%d r%d not in map' % (col, row))
			il = pto.get_image_by_fn(fn)
			if il is None:
				raise Exception('Could not find %s in map' % fn)
			cols.append(col)
			selected = selector(il)
			if selected is None:
				raise Exception('Reference image line is missing x/y position: %s' % il)
			deps.append(selected)
		if len(cols) == 0:
			if not allow_missing:
				raise Exception('No matches')
			continue
		
		if 0:
			print 'Fitting polygonomial'
			print cols
			print deps
		
		# Find x/y given a col
		(c0, c1) = polyfit(cols, deps, 1)
		slopes.append(c0)
	if len(slopes) == 0:
		if not allow_missing:
			raise Exception('No matches')
		# No dependence
		return 0.0
	# XXX: should remove outliers
	return sum(slopes) / len(slopes)

def regress_col(m, pto, cols, selector, allow_missing = False):
	# Discard the constants, we will pick a reference point later
	slopes = []
	for col in cols:
		'''
		For each row find an y position
		y = row * c0 + c1
		'''
		rows = []
		deps = []
		for row in range(m.height()):
			fn = m.get_image(col, row)
			if fn is None:
				if allow_missing:
					continue
				raise Exception('c%d r%d not in map' % (col, row))
			il = pto.get_image_by_fn(fn)
			if il is None:
				raise Exception('Could not find %s in map' % fn)
			rows.append(row)
			deps.append(selector(il))
		
		if len(rows) == 0:
			if not allow_missing:
				raise Exception('No matches')
			continue
		(c0, c1) = polyfit(rows, deps, 1)
		slopes.append(c0)
	if len(slopes) == 0:
		if not allow_missing:
			raise Exception('No matches')
		# No dependence
		return 0.0
	# XXX: should remove outliers
	return sum(slopes) / len(slopes)

def regress_c0(m, pto, rows, allow_missing = False):
	# dependence of x on col in specified rows
	return regress_row(m, pto, rows, lambda x: x.x(), allow_missing)

def regress_c1(m, pto, cols, allow_missing = False):
	# dependence of x on row in specified cols
	return regress_col(m, pto, cols, lambda x: x.x(), allow_missing)

def regress_c3(m, pto, rows, allow_missing = False):
	# dependence of y on col in specified rows
	return regress_row(m, pto, rows, lambda x: x.y(), allow_missing)

def regress_c4(m, pto, cols, allow_missing = False):
	# cdependence of y on row in specified cols
	return regress_col(m, pto, cols, lambda x: x.y(), allow_missing)
	
def calc_constants(order, m_real, pto_ref,
		c0s, c1s, c3s, c4s,
		m_ref = None, allow_missing=False):
	if m_ref is None:
		m_ref = m_real
	
	ref_fns = pto_ref.get_file_names()
	
	c2s = []
	c5s = []
	for cur_order in range(order):
		this_c2s = []
		this_c5s = []
		for col in range(m_real.width()):
			for row in range(m_real.height()):
				fn = m_real.get_image(col, row)
				if not fn in ref_fns:
					continue
				if fn is None:
					if not allow_missing:
						raise Exception('Missing item')
					continue
				il = pto_ref.get_image_by_fn(fn)
				if il is None:
					raise Exception('%s should have been in ref' % fn)
				try:
					# x = c0 * c + c1 * r + c2
					row_order = row % order
					if row_order == cur_order:
						cur_x = cur_x = il.x() - c0s[row_order] * col - c1s[row_order] * row
						this_c2s.append(cur_x)
			
					# y = c3 * c + c4 * r + c5
					col_order = col % order
					if col_order == cur_order:
						cur_y = il.y() - c3s[col_order] * col - c4s[col_order] * row
						this_c5s.append(cur_y)
				
					#print '%s: x%g y%g' % (fn, cur_x, cur_y)
				
				except:
					print
					print il
					print c0s, c1s, c3s, c4s
					print col, row
					print 
					raise
		if 0:
			c2s.append(sum(this_c2s) / len(this_c2s))
			c5s.append(sum(this_c5s) / len(this_c5s))
		else:
			c2s.append(this_c2s[0])
			c5s.append(this_c5s[0])
	return (c2s, c5s)
	
def rms_errorl(l):
	return (sum([(i - sum(l) / len(l))**2 for i in l]) / len(l))**0.5
	
def rms_error_diff(l1, l2):
	if len(l1) != len(l2):
		raise ValueError("Lists must be identical")
	return (sum([(l2[i] - l1[i])**2 for i in range(len(l1))]) / len(l1))**0.5
	
def linear_reoptimize(pto, pto_ref = None, allow_missing = False, order = 2):
	'''Change XY positions to match the trend in a linear XY positioned project (ex from XY stage).  pto must have all images in pto_ref '''
	if scipy is None:
		raise Exception('Re-optimizing requires scipi')
	
	'''
	Our model should be like this:
	-Each axis will have some degree of backlash.  This backlash will create a difference between adjacent rows / cols
	-Axes may not be perfectly adjacent
		The naive approach would give:
			x = c * dx + xc
			y = r * dy + yc
		But really we need this:
			x = c * dx + r * dx/dy + xc
			y = c * dy/dx + r * dy + yc
		Each equation can be solved separately
		Need 3 points to solve each and should be in the expected direction of that line
		
		
	Perform a linear regression on each row/col?
	Might lead to very large y = mx + b equations for the column math
	'''
	
	if pto_ref is None:
		pto_ref = pto

	'''
	Phase 1: calculate linear system
	'''
	# Start by building an image coordinate map so we know what x and y are
	pto_ref.parse()
	ref_fns = pto_ref.get_file_names()
	real_fns = pto.get_file_names()
	print 'Files (all: %d, ref: %d):' % (len(real_fns), len(ref_fns))
	for fn in real_fns:
		if fn in ref_fns:
			ref_str = '*'
		else:
			ref_str = ' '
		print '  %s%s' % (ref_str, fn)
	m_ref = ImageCoordinateMap.from_tagged_file_names(ref_fns)
	m_real = ImageCoordinateMap.from_tagged_file_names(real_fns)
	#m.debug_print()
	
	'''
	Ultimately trying to form this equation
	x = c0 * c + c1 * r + c2
	y = c3 * c + c4 * r + c5
	
	Except that constants will also have even and odd varities
	c2 and c5 will be taken from reasonable points of reference, likely (0, 0) or something like that
	'''
	
	c0s = []
	c1s = []
	c3s = []
	c4s = []
	for cur_order in range(order):
		# Given a column find x (primary x)
		c0s.append(regress_c0(m_ref, pto_ref, xrange(cur_order, m_ref.height(), order), allow_missing))
		c1s.append(regress_c1(m_ref, pto_ref, xrange(cur_order, m_ref.width(), order), allow_missing))
		# Given a row find y (primary y)
		c3s.append(regress_c3(m_ref, pto_ref, xrange(cur_order, m_ref.height(), order), allow_missing))
		c4s.append(regress_c4(m_ref, pto_ref, xrange(cur_order, m_ref.width(), order), allow_missing))

	# Now chose a point in the center
	# it doesn't have to be a good fitting point in the old system, it just has to be centered
	# Fix at the origin
	
	'''
	Actually the even and the odd should have the same slope
	The only difference should be their offset
	'''
	c2 = None
	c5 = None
	
	if 0:
		print 'Solution found'
		print '  x = %g c + %g r + TBD' % (c0, c1)
		print '  y = %g c + %g r + TBD' % (c3, c4)
	

	# Verify the solution matrix by checking it against the reference project
	print
	print 'Verifying reference solution matrix....'
	(c2s_ref, c5s_ref) = calc_constants(order, m_ref, pto_ref, c0s, c1s, c3s, c4s, m_ref, allow_missing)
	#c1s = [c1 + 12 for c1 in c1s]
	# Print the solution matrx for debugging
	for cur_order in range(order):
		# XXX: if we really cared we could center these up
		# its easier to just run the centering algorithm after though if one cares
		print 'Reference order %d solution:' % cur_order
		print '  x = %g c + %g r + %g' % (c0s[cur_order], c1s[cur_order], c2s_ref[cur_order])
		print '  y = %g c + %g r + %g' % (c3s[cur_order], c4s[cur_order], c5s_ref[cur_order])
	calc_ref_xs = []
	calc_ref_ys = []
	ref_xs = []
	ref_ys = []
	for col in range(m_ref.width()):
		for row in range(m_ref.height()):
			fn = m_ref.get_image(col, row)
			if fn is None:
				continue
			il = pto_ref.get_image_by_fn(fn)
			col_eo = col % order
			row_eo = row % order
			x_calc = c0s[row_eo] * col + c1s[row_eo] * row + c2s_ref[row_eo]
			y_calc = c3s[col_eo] * col + c4s[col_eo] * row + c5s_ref[col_eo]
			calc_ref_xs.append(x_calc)
			calc_ref_ys.append(y_calc)
			x_orig = il.x()
			y_orig = il.y()
			ref_xs.append(x_orig)
			ref_ys.append(y_orig)
			print '  c%d r%d: x%g y%g' % (col, row, x_calc - x_orig, y_calc - y_orig)
	x_ref_rms_error = rms_error_diff(calc_ref_xs, ref_xs)
	y_ref_rms_error = rms_error_diff(calc_ref_ys, ref_ys)
	print 'Reference RMS error x%g y%g' % (x_ref_rms_error, y_ref_rms_error)
	print
	#exit(1)
	
	'''
	The reference project might not start at 0,0
	Therefore scan through to find some good starting positions so that we can calc each point
	in the final project
	'''
	print 'Anchoring solution...'
	'''
	Calculate the constant at each reference image
	Compute reference positions from these values
	'''
	(c2s, c5s) = calc_constants(order, m_real, pto_ref, c0s, c1s, c3s, c4s, m_ref, allow_missing)
	#c2s = [c2 + 30 for c2 in c2s]
		
	# Print the solution matrx for debugging
	for cur_order in range(order):
		# XXX: if we really cared we could center these up
		# its easier to just run the centering algorithm after though if one cares
		print 'Order %d solution:' % cur_order
		print '  x = %g c + %g r + %g' % (c0s[cur_order], c1s[cur_order], c2s[cur_order])
		print '  y = %g c + %g r + %g' % (c3s[cur_order], c4s[cur_order], c5s[cur_order])
	
	c2_rms = rms_errorl(c2s)
	c5_rms = rms_errorl(c5s)
	print 'RMS offset error x%g y%g' % (c2_rms, c5_rms)
	if c2_rms > c5_rms:
		print 'x offset varies most, expect left-right scanning'
	else:
		print 'y offset varies most, expect top-bottom scanning'
	#exit(1)
	'''
	We have the solution matrix now so lets roll
	'''
	for col in range(m_real.width()):
		for row in range(m_real.height()):
			fn = m_real.get_image(col, row)
			il = pto.get_image_by_fn(fn)

			if fn is None:
				if not allow_missing:
					raise Exception('Missing item')
				continue
			
			col_eo = col % order
			row_eo = row % order
			
			# FIRE!
			# take the dot product
			x = c0s[row_eo] * col + c1s[row_eo] * row + c2s[row_eo]
			y = c3s[col_eo] * col + c4s[col_eo] * row + c5s[col_eo]
			# And push it out
			#print '%s: c%d r%d => x%g y%d' % (fn, col, row, x, y)
			il.set_x(x)
			il.set_y(y)
			#print il



