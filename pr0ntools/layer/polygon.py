from pr0ntools.jssim.options import Options
import xml.parsers.expat
from shapely.geometry import Polygon, MultiPolygon
from shapely.geos import TopologicalError
try:
	from Tkinter import *
	using_tkinter = True
except ImportError as e:
	using_tkinter = False

from pr0ntools.jssim.util import get_debug_width, get_debug_height
from pr0ntools.layer.point import Point
from pr0ntools.layer.layer import Layer


g_no_cache = True
#g_no_cache = False



'''
Head up: may need to be able to do transforms if the canvas is relaly large
which shouldn't be too uncommon
'''
class PolygonRenderer:
	def __init__(self, title=None, width=None, height=None, fork=False):
		width = width or get_debug_width() or 400
		height = height or get_debug_height() or 400
		
		print 'Render width: %d, height: %d' % (width, height)
		
		self.width = width
		self.height = height
		self.fork = fork
				
		# In render order
		# (polygon, color)
		self.targets = list()
		# Polygon color overrides
		# [polygon] = color
		# Make this usually not take up memory but can if you really want it
		self.colors = dict()
		self.title = title
		if self.title is None:
			self.title = 'Polygon render'
		self.wireframe = False

	# Specify color to override default or None for current
	def add_polygon(self, polygon, color=None):
		if color:
			self.colors[polygon] = color
		self.targets.append(polygon)

	def add_layer(self, layer, color=None):
		colori = 0
		for polygon in layer.polygons:
			color_temp = color or polygon.color or layer.color
			if color_temp is None:
				color_temp = Options.color_wheel[colori % len(Options.color_wheel)]
				colori += 1
			self.add_polygon(polygon, color_temp)

	def add_xlayer(self, color=None):
		for polygon in layer.xpolygons:
			self.add_polygon(polygon, color)
		
	# Call after setup
	def render(self):
		if not using_tkinter:
			raise Exception("require tkinter")
			
		#print 'render width: %d, height: %d' % (self.width, self.height)
		
		root = Tk()

		root.title(self.title)
		canvas = Canvas(root, width=self.width, height=self.height)

		# Upper left origin origin just like us
		#points = [1,1,10,1,10,10,1,10]
		total_loops = len(self.targets)
		loops = 0
		for polygon in self.targets:
			if total_loops > 10:
				if loops % (total_loops / 10) == 0:
					print 'Render progress: %d / %d (%0.2f %%)' % (loops, total_loops, 100.0 * loops / total_loops)
				loops += 1
			
			points = list()
			
			# Use override if given
			if polygon in self.colors:
				color = self.colors[polygon]
			else:
				color = polygon.color
			if color is None:
				# Default to black
				color = 'black'
			
			if self.wireframe:
				first_point = None
				points = list(polygon.get_points())
				for i in range(0, len(points) - 1):
					canvas.create_line(points[i].x, points[i].y, points[i + 1].x, points[i + 1].y)
				canvas.create_line(points[0].x, points[0].y, points[len(points) - 1].x, points[len(points) - 1].y)
			else:
				for point in polygon.get_points():
					#print dir(point)
					points.append(point.x)
					points.append(point.y)
				if len(points) < 3:
					print 'WARNING: skipping invalid points list ' + repr(points)
					continue
				canvas.create_polygon(points, fill=color)


		canvas.pack()
		#root.title(self.title)
		root.mainloop()

'''
Usually layer is sufficient / mirrors features
Maybe a layer should really contain a multipolygon though?
This might assist in some of the shapely multipolygon stuff...or maybe just complicate things
class UVMultiPolygon:
	def __init__(self):
		# UVPolygons
		self.polygons = set() 

	def add_sl_polygons(self, l):
		for sl_polygon in l:
			self.add_sl_polygon(sl_polygon)
			
	def add_sl_polygon(self, poly):
		
	def add_sl_polygon(self, poly):
'''

'''
Polygons are aware of anything need to draw them as well as their electrical properties
They are not currently aware of their material (layer) but probably need to be aware of it to figure out color
Currently color is pushed on instead of pulled
Final JSSim figures out color from layer and segdefs are pushed out on a layer by layer basis so its not necessary to store

Debating whether or not to support multipolygon
Maybe users uses at own risk philosiphy?
Does mean that other people can't be gauranteed simple polygon though

Intended to be immutable.  Will build up supporting data (may cache) but shouldn't change object itself
If you do, call clear_cache
'''
class UVPolygon:
	def __init__(self, points = None, color = None):
		'''
		To make display nicer
		Vaguely defined...HTML like
		Can either be a human color like red or green or HTML like #602030
		Consider making this external to a map so that we can compress a usually identical layer
		WARNING: this is for debugging and has nothing to do with render color in JSSim
		'''
		self.color = color
		# Number not the object
		self.net = None
		self.xpolygon = None
		self.points = None
		self.polygon = None
		
		if points:
			self.set_polygon(Polygon([(point.x, point.y) for point in points]))
	
	def clear_cache(self):
		self.xpolygon = None
		self.points = None
	
	def set_polygon(self, polygon):
		self.polygon = polygon
		self.clear_cache()
		#self.rebuild_points()
		#self.rebuild_xpolygon()
		#self.show("show self")
	
	def get_points(self):
		if g_no_cache or self.points is None:
			self.rebuild_points()
		return self.points
	
	def get_xpolygon(self):
		if g_no_cache or self.xpolygon is None:
			self.rebuild_xpolygon()
		return self.xpolygon
	
	def coordinates(self):
		'''return (JSSim style) single dimensional array of coordinates (WARNING: UL coordinate system)'''
		# return [i for i in [point.x,point.y) for point in self.points]
		# l = [(1, 2), (3, 4), (50, 32)]
		# print [i for i in [(x[0],x[1]) for x in l]]
		ret = list()
		for point in self.get_points():
			ret.append(point.x)
			ret.append(point.y)
		return ret
	
	@staticmethod
	def from_rect_ex(x, y, width, height, color = None, flip_height = 0):
		'''
		|------|
		|      |
		|------|
		
		flip_height: only y positions (y) changes
		
		'''
		if flip_height:
			y = flip_height - y - height
		return UVPolygon.from_polygon(Polygon(list([(x, y),   (x + width, y),   (x + width, y + height),   (x, y + height)])), color=color)
		
	@staticmethod
	def from_rect(x, y, width, height, color = None):
		return UVPolygon.from_polygon(Polygon(list([(x, y),   (x + width, y),   (x + width, y + height),   (x, y + height)])), color=color)
		
	#@staticmethod
	#def from_points_1d(self, points):
	#	return UVPolygon.from_polygon(Polygon(points))
	
	def from_points_2d(self, points):
		return UVPolygon.from_polygon(Polygon(points))
		
	@staticmethod
	def from_polygon(polygon, net = None, color = None):
		poly = UVPolygon(None)
		poly.color = color
		poly.polygon = polygon
		poly.net = net
		#poly.rebuild_points()
		#poly.rebuild_xpolygon()
		return poly
	
	def flip_horizontal(self, height = None):
		'''Flip upside-down'''
		temp = list()
		new_points = list()
		for point in self.get_points():
			new_points.append((point.x, height - point.y))
		self.set_polygon(Polygon(new_points))
	
	def flip_veritcal(self, width = None):
		'''Flip left-right'''
		temp = list()
		new_points = list()
		for point in self.get_points():
			new_points.append((width - point.x, point.y))
		self.set_polygon(Polygon(new_points))
	
	def rebuild_points(self):
		self.points = list()
		#print
		#print
		#print 'self.polygon: ' + repr(self.polygon)
		if self.polygon.geom_type == 'MultiLineString':
			return
		#print 'Exterior coords: ' + repr(self.polygon.exterior.coords)
		for i in range(len(self.polygon.exterior.coords.xy[0]) - 1):
			x = self.polygon.exterior.coords.xy[0][i]
			y = self.polygon.exterior.coords.xy[1][i]
			#self.points.append((x, y))
			self.points.append(Point(x, y))
	
	def to_cli(self):
		# Polygon( [(110.9072599999999937, 82.6502100000000155), (270.8686099999999897, 82.6502100000000155), (270.8686099999999897, 155.0855360000000189), (110.9072599999999937, 155.0855360000000189), (110.9072599999999937, 82.6502100000000155)] )
		ret = "Polygon( ["
		sep = ""
		for point in self.get_points():
			ret += sep
			ret += "(%u, %u)" % (point.x, point.y)
			sep = ', '
		ret += '] )'
		return ret
	
	def __repr__(self):
		ret = "<polygon points=\""
		first = True
		for point in self.get_points():
			# Space pairs to make it a little more readable
			if not first:
				ret += ', '
			ret += "%u,%u" % (point.x, point.y)
			first = False
		ret += '" />'
		return ret
		
	'''
	intersection: return areas that are in both polygons
	union: return areas that are in either polygon
	difference: return areas that are in first but not second
	'''
	
	@staticmethod
	def sl_polygon_list(obj):
		if obj.geom_type == 'Polygon':
			return [obj]
		elif obj.geom_type == 'MultiPolygon':
			l = list()
			for poly in obj:
				l.append(poly)
			return l
		else:
			print 'unknown type %s' % obj.geom_type
			raise Exception("dead")
	
	
	@staticmethod
	def uv_polygon_list(obj, new_color = None):
		'''
		elif obj.geom_type == 'MultiPolygon':
			#print '*multi'
			l = list()
			for poly in obj.geoms:
				l.append(UVPolygon.from_polygon(poly, color = new_color))
			return l
		'''
		if obj.geom_type == 'Polygon':
			#print '*single'
			return [UVPolygon.from_polygon(obj, color = new_color)]
		elif obj.geom_type == 'MultiPolygon' or obj.geom_type == 'GeometryCollection':
			if len(obj) == 0:
				return list()
			else:
				l = list()
				for o in obj:
					l += UVPolygon.uv_polygon_list(obj)
				return l
		else:
			from pprint import pprint

			
			print 'unknown type %s' % obj.geom_type
			print dir(obj)
			pprint(list(obj))
			print len(obj)

			raise Exception("dead")
	
	def subtract(self, other, new_color = None):
		'''Returns array of UV polygons'''
		#print 'Other: ' + repr(other)
		#print 'Self: ' + repr(self)
		#print 'other_poly =' + other.to_cli()
		#print 'self_poly =' + self.to_cli()

		diff_poly = self.polygon.difference(other.polygon)
		print 'Difference: ' + repr(diff_poly)
		ret = UVPolygon.uv_polygon_list(diff_poly, new_color = new_color )
		
		#self.show(title='Subtract poly orig', wireframe=True)
		#other.show(wireframe=True)
		for poly in ret:
			#print poly
			#poly.show(wireframe=True)
			if len(poly.polygon.interiors) > 0:
				print 'Complex ring / hole geometries not supported'
				print 'Self: ' + repr(self)
				print 'Other: ' + repr(other)
				print poly.polygon
				
				r = PolygonRenderer(title='Polygons')
				r.add_polygon(self, color='blue')
				r.add_polygon(other, color='red')
				r.render()
				
				if True:
					# For my purposes I should be able to ignore these and assume the solid shape
					# although it could have collatoral damage
					print 'WARNING: ignoring bad geometry'
				else:
					raise Exception('Complex ring / hole geometries not supported')
		
		#print 'dying'
		#sys.exit(1)
		
		# Detect but don't support
		return ret
	
	def union(self, other):
		poly = self.polygon.union(other.polygon)
		return UVPolygon.from_polygon(poly)

	def enlarge(self, scalar = None, constant = None):
		if not scalar is None:
			raise Exception('Scalar is not supported')
		self.polygon = self.build_xpolygon(increase=constant)
		self.clear_cache()

	def rebuild_xpolygon(self):
		self.xpolygon = self.build_xpolygon()
	
	def build_xpolygon(self, increase = None):
		'''
		Rebuild extended polygon
		Trys to find neighboring polygons by stretching about the centroid
		which we will then try to overlap
		
		XXX: there is an approx match method
		we may not need this
		'''
		centroid = self.polygon.centroid
		#print dir(self.polygon)
		#print dir(centroid)
		
		#self.show()
		
		xbounds = list()
		if increase is None:
			increase = 2.0
		#print self.polygon.bounds
		# start and end are the same
		# Tech it will work though: optional in constructor
		for i in range(len(self.polygon.exterior.coords.xy[0]) - 1):
			#print i
			#print self.polygon.exterior.coords.xy
			x = self.polygon.exterior.coords.xy[0][i]
			y = self.polygon.exterior.coords.xy[1][i]
		
			#print x
			#print y
		
			if x - centroid.x < 0:
				x -= increase
			if x - centroid.x > 0:
				x += increase
			if y - centroid.y < 0:
				y -= increase
			if y - centroid.y > 0:
				y += increase
			xbounds.append((x, y))
		
		#print xbounds
		return Polygon(xbounds)

	def intersects(self, polygon):
		# Check x intersect and y intersect
		# XXX: 
		return self.polygon.intersects(polygon.polygon)

	'''
	XXX: this can produce a multipolygon
	'''
	def intersection(self, polygon):
		intersected = self.polygon.intersection(polygon.polygon)
		if False and intersected.geom_type == 'MultiLineString':
			# Err actually should not get multipoly here?
			# Boundary condition: infetismal hairline intersection
			print 'intersected: %s' % repr(intersected)
			print '\t' + repr(self.polygon.intersects(polygon.polygon))
			#self.show()
			#polygon.show()
		
		if intersected.is_empty:
			return None
		return UVPolygon.uv_polygon_list(intersected)

	@staticmethod
	def show_polygons(polygons):
		r = PolygonRenderer(title='Polygons')
		colors = Options.color_wheel
		for i in range(0, len(polygons)):
			r.add_polygon(polygons[i], colors[i % len(colors)])
		r.render()
		
	def width(self):
		# bounds: Returns minimum bounding region (minx, miny, maxx, maxy)
		return self.polygon.bounds[2]
	
	def height(self):
		# bounds: Returns minimum bounding region (minx, miny, maxx, maxy)
		return self.polygon.bounds[3]
	
	def show(self, title=None, width = None, height = None, color=None, wireframe=False):
		if width is None:
			width = self.width()
		if height is None:
			height = self.height()
		
		if self.polygon.geom_type == 'MultiPolygon':
			if title is None:
				title = 'MultiPolygon'
			Layer.from_sl_multi(self.polygon).show(title=title, width=width, height=height)
		else:
			if title is None:
				title = 'Polygon'
			r = PolygonRenderer(title=title, width=width, height=height)
			r.wireframe=wireframe
			r.add_polygon(self, color=color)
			r.render()

	def points(self):
		ret = list()
		for i in range(len(self.polygon.exterior.coords.xy[0]) - 1):
			x = self.polygon.exterior.coords.xy[0][i]
			y = self.polygon.exterior.coords.xy[1][i]
			ret.append((x, y))
		return ret


# Intersected polygon
class UVPolygonI(UVPolygon):
	def __init__(self, points, poly1, poly2, color=None):
		UVPolygon.__init__(self, points, color)
		self.poly1 = poly1
		self.poly2 = poly2


