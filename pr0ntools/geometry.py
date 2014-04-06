'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
If align is given it specifies an origin
'''
def floor_mult(n, mult, align=0):
	'''Return the first number <= n that is a multiple of mult shifted by align'''
	rem = (n - align) % mult
	if rem == 0:
		return n
	else:
		return n - rem

def ceil_mult(n, mult, align=0):
	'''Return the first number >= n that is a multiple of mult shifted by align'''
	rem = (n - align) % mult
	if rem == 0:
		return n
	else:
		return n + mult - rem


class PolygonQuadTreeItem:
	def __init__(self, left, right, top, bottom):
		self.left = left
		self.right = right
		self.top = top
		self.bottom = bottom

'''
http://pygame.org/wiki/QuadTree
'''
class PolygonQuadTree(object):
	"""An implementation of a quad-tree.
 
	This QuadTree started life as a version of [1] but found a life of its own
	when I realised it wasn't doing what I needed. It is intended for static
	geometry, ie, items such as the landscape that don't move.
 
	This implementation inserts items at the current level if they overlap all
	4 sub-quadrants, otherwise it inserts them recursively into the one or two
	sub-quadrants that they overlap.
 
	Items being stored in the tree must possess the following attributes:
		(Upper left coordinate system)
 
		left - the x coordinate of the left edge of the item's bounding box.
		top - the y coordinate of the top edge of the item's bounding box.
		right - the x coordinate of the right edge of the item's bounding box.
		bottom - the y coordinate of the bottom edge of the item's bounding box.
 
		where left < right and top < bottom
		
	...and they must be hashable.
	
	Acknowledgements:
	[1] http://mu.arete.cc/pcr/syntax/quadtree/1/quadtree.py
	"""
	def __init__(self, items, depth=8, bounding_rect=None):
		"""Creates a quad-tree.
 
		@param items:
			A sequence of items to store in the quad-tree. Note that these
			items must possess left, top, right and bottom attributes.
			
		@param depth:
			The maximum recursion depth.
			
		@param bounding_rect:
			The bounding rectangle of all of the items in the quad-tree. For
			internal use only.
		"""
		# The sub-quadrants are empty to start with.
		self.nw = self.ne = self.se = self.sw = None
		
		# If we've reached the maximum depth then insert all items into this
		# quadrant.
		depth -= 1
		if depth == 0:
			self.items = items
			return
 
		# Find this quadrant's centre.
		if bounding_rect:
			l, t, r, b = bounding_rect
		else:
			# If there isn't a bounding rect, then calculate it from the items.
			l = min(item.left for item in items)
			t = min(item.top for item in items)
			r = max(item.right for item in items)
			b = max(item.bottom for item in items)
		cx = self.cx = (l + r) * 0.5
		cy = self.cy = (t + b) * 0.5
		
		self.items = []
		nw_items = []
		ne_items = []
		se_items = []
		sw_items = []
		
		for item in items:
			# Which of the sub-quadrants does the item overlap?
			in_nw = item.left <= cx and item.top <= cy
			in_sw = item.left <= cx and item.bottom >= cy
			in_ne = item.right >= cx and item.top <= cy
			in_se = item.right >= cx and item.bottom >= cy
				
			# If it overlaps all 4 quadrants then insert it at the current
			# depth, otherwise append it to a list to be inserted under every
			# quadrant that it overlaps.
			if in_nw and in_ne and in_se and in_sw:
				self.items.append(item)
			else:
				if in_nw: nw_items.append(item)
				if in_ne: ne_items.append(item)
				if in_se: se_items.append(item)
				if in_sw: sw_items.append(item)
			
		# Create the sub-quadrants, recursively.
		if nw_items:
			self.nw = PolygonQuadTree(nw_items, depth, (l, t, cx, cy))
		if ne_items:
			self.ne = PolygonQuadTree(ne_items, depth, (cx, t, r, cy))
		if se_items:
			self.se = PolygonQuadTree(se_items, depth, (cx, cy, r, b))
		if sw_items:
			self.sw = PolygonQuadTree(sw_items, depth, (l, cy, cx, b))
		
	'''
	def hit(self, x):
		r = object()
		r.left = 
		r.right = 
		r.top = 
		r.bottom = 
		return self.hit_core(r)
	'''
	def hit_bounds(self, bounds):
		'''Hit in form [left,right,top,bottom]'''
		return self.hit(PolygonQuadTreeItem(bounds[0], bounds[1], bounds[2], bounds[3]))
	
	def hit(self, rect):
		"""Returns the items that overlap a bounding rectangle.
 
		Returns the set of all items in the quad-tree that overlap with a
		bounding rectangle.
		
		@param rect:
			The bounding rectangle being tested against the quad-tree. This
			must possess left, top, right and bottom attributes.
		"""
		def overlaps(item):
			return rect.right >= item.left and rect.left <= item.right and \
				   rect.bottom >= item.top and rect.top <= item.bottom
		
		# Find the hits at the current level.
		hits = set (item for item in self.items if overlaps(item))
		
		# Recursively check the lower quadrants.
		if self.nw and rect.left <= self.cx and rect.top <= self.cy:
			hits |= self.nw.hit_core(rect)
		if self.sw and rect.left <= self.cx and rect.bottom >= self.cy:
			hits |= self.sw.hit_core(rect)
		if self.ne and rect.right >= self.cx and rect.top <= self.cy:
			hits |= self.ne.hit_core(rect)
		if self.se and rect.right >= self.cx and rect.bottom >= self.cy:
			hits |= self.se.hit_core(rect)
 
		return hits

