'''
XXX
Use multipolygon + envolope to make some of the more stubborn polygons?
'''

using_tkinter = True

from pr0ntools.jssim.options import Options
import xml.parsers.expat
from shapely.geometry import Polygon, MultiPolygon
from shapely.geos import TopologicalError
if using_tkinter:
	from Tkinter import *
from pr0ntools.benchmark import Benchmark
from pr0ntools.util.geometry import PolygonQuadTree as PolygonQuadTreeBase

from pr0ntools.jssim.util import get_debug_width, get_debug_height

g_no_cache = True
#g_no_cache = False

class PolygonQuadTree(PolygonQuadTreeBase):
	def __init__(self, *args):
		PolygonQuadTreeBase.__init__(*args)
		
	def hit_polygon(self, uvpolygon):
		qtuvpolygon = QTUVPolygon(uvpolygon)
		ret = self.hit(qtuvpolygon)
		return ret

'''
Net should not know anything about polygons
'''
class Net:
	UNKNOWN = 0
	# V+
	VDD = 1
	VCC = 1
	# V-
	VSS = 2
	GND = 2
	# Pullup
	PU = 3
	# pulldown (unused)
	PD = 4
	
	def __init__(self, number=None):
		#self.polygons = set()
		# User definable set of objects in the net
		self.members = set()
		
		self.number = number
		self.potential = Net.UNKNOWN
		# Should not be changed
		# Report errors if something would overcome it
		self.explicit_potential = False
		# Nets can have multiple names
		self.names = set()
		
	def add_member(self, member):
		self.members.add(member)
	
	def remove_member(self, member):
		self.members.remove(member)
		
	def add_name_parsed(self, name, overwrite = False):
		self.add_name(name)
		
		potential = Net.UNKNOWN

		tu = name.upper()
		if tu.find('GND') >= 0:
			potential = Net.GND
		elif tu.find('VDD') >= 0 or tu.find('VSS') >= 0:
			potential = Net.VDD
			
		# Try to merge the potential in
		if not potential is Net.UNKNOWN:
			temp = Net()
			temp.potential = potential
			temp.explicit_potential = True
			self.merge(temp)
	
	def add_name(self, name):
		self.names.add(name)
		
	def merge(self, other):
		for member in other.members:
			self.members.add(member)
		# Give us a net number if possible
		if self.number is None:
			self.number = other.number
		'''
		Any conflicting net status?
		Conflict
			VCC and GNDcolor=None
		Warning?
			PU/PD and VSS/GND
		Transition
			UNKNOWN and X: X
		'''
		# Expect most common case
		#print 'net merge, potential = (self: %u, other: %u)' %(self.potential, other.potential)
		if self.potential == other.potential:
			pass
		elif self.potential == Net.UNKNOWN:
			self.potential = other.potential
		else:
			p1 = self.potential
			p2 = other.potential
			# Sort to reduce cases (want p1 lower)
			if p1 > p2:
				p = p1
				p1 = p2
				p2 = p
			# Expect most common case: both unknown
			if p2 == Net.UNKNOWN:
				pass
			# One known but not the other?
			elif p1 == Net.UNKNOWN:
				self.potential = p2
			elif p1 == Net.VDD and p2 == Net.GND:
				if True:
					r = PolygonRenderer(title='Shorted net', width = get_debug_width(), height=get_debug_height())
					for member in self.members:
						color = 'blue'
						if member.net == self:
							color = 'red'
						if member.net == other:
							color = 'orange'
						r.add_polygon(member, color=color)
					r.render()
				raise Exception("Supply shorted")
			elif (p1 == Net.VDD or p1 == Net.GND) and (p2 == Net.PU or p2 == Net.PD):
				print 'WARNING: eliminating pullup/pulldown status due to direct supply connection'
				self.potential = p1
			else:
				print p1
				print p2
				raise Exception('Unaccounted for net potential merge')
		#print 'End potential: %u' % self.potential
		for name in other.names:
			self.names.add(name)
		
	def pull_up(self):
		if self.potential == Net.UNKNOWN:
			self.potential = Net.PU
		# If alreayd at VCC pullup does nothing
		elif self.potential == Net.VDD:
			print 'WARNING: discarding pullup since at VDD'
			return
		elif self.potential == Net.GND:
			print 'WARNING: discarding pullup since at ground'
			return
		elif self.potential == Net.PD:
			raise Exception('Should not pull up and down')
		else:
			raise Exception('Unknown potential')
	
	def get_pullup(self):
		if self.potential == Net.PU:
			return '+'
		elif self.potential == Net.PD:
			raise Exception("not supported")
		else:
			return '-'
	
# Used in merging?
# decided to use map instead
'''
class NetProxy:
	def __init__(self, net):
		self.net = net
'''

class Nets:
	def __init__(self):
		# number to net object
		self.nets = dict()

	def __getitem__(self, net_number):
		return self.nets[net_number]

	def add(self, net):
		'''
		if not net.number in self.nets:
			s = set()
		else:
			s = self.nets[net.number]
		s.add(net)
		self.nets[net.number] = s
		'''
		self.nets[net.number] = net

	def remove(self, net):
		del self.nets[net.number]

	def merge(self, new_net, old_net):
		'''Move data from old_net number into new_net number'''
		self.nets[new_net].merge(self.nets[old_net])
		del self.nets[old_net]
				
class Point:
	def __init__(self, x, y):			
		self.x = x
		self.y = y


from threading import Thread

class PolygonRendererThread(Thread):
   def __init__ (self,ip):
      Thread.__init__(self)
      self.ip = ip
      self.status = -1
   def run(self):
      pingaling = os.popen("ping -q -c2 "+self.ip,"r")
      while 1:
        line = pingaling.readline()
        if not line: break
        igot = re.findall(testit.lifeline,line)
        if igot:
           self.status = int(igot[0])
           

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

# Layer intersection
# Intersection is arbitrary
# We may extend the actual layer polygon
# Don't make assumptions about how it relates to actual layers
# hmm turns out there is an almost_equals method
# TODO: make this a subclass of Layer?
# to_layer would take out intersection metadata
class LayerI:
	def __init__(self, layer1, layer2, polygons):
		# UVPolygon
		self.layer1 = layer1
		# UVPolygon
		self.layer2 = layer2
		# UVPolygon list
		self.polygons = polygons

	def show(self, title=None):
		#UVPolygon.show_polygons(xintersections)
		if title is None:
			title = 'red: %s, green: %s, blue: intersect' % (self.layer1.name, self.layer2.name)
		r = PolygonRenderer(title, width=self.layer1.width, height=self.layer1.height)
		r.add_layer(self.layer1, 'red')
		r.add_layer(self.layer2, 'green')
		# Render intersection last
		for polygon in self.polygons:
			r.add_polygon(polygon, 'blue')
		r.render()

	# So can be further intersected
	def to_layer(self):
		layer = Layer()
		layer.width = self.layer1.width
		layer.height = self.layer1.height
		layer.polygons = self.polygons
		layer.name = 'Intersection of %s and %s' % (self.layer1.name, self.layer2.name)
		# Why not
		layer.color = 'blue'
		return layer

class LayerSVGParser:
	@staticmethod
	def parse(layer, file_name):
		parser = LayerSVGParser()
		parser.layer = layer
		parser.file_name = file_name
		parser.do_parse()

	def process_transform(self, transform):
		x_delta = float(transform.split(',')[0].split('(')[1])
		y_delta = float(transform.split(',')[1].split(')')[0])
		self.x_deltas.append(x_delta)
		self.y_deltas.append(y_delta)

		self.x_delta += x_delta
		self.y_delta += y_delta
		
	def pop_transform(self):
		self.x_delta -= self.x_deltas.pop()
		self.y_delta -= self.y_deltas.pop()
		
	def do_parse(self):
		'''
		Need to figure out a better parse algorithm...messy
		'''
		
		'''
		<rect
		   y="261.16562"
		   x="132.7981"
		   height="122.4502"
		   width="27.594412"
		   id="rect3225"
		   style="fill:#999999" />
		'''
		#print self.file_name
		raw = open(self.file_name).read()
		
		#print 'set vars'
		self.x_delta = 0.0
		self.x_deltas = list()
		self.y_delta = 0.0
		self.y_deltas = list()
		self.flow_root = False
		self.text = None

		# 3 handler functions
		def start_element(name, attrs):
			#print 'Start element:', name, attrs
			if name == 'rect':				
				#print 'Got one!'
				# Origin at upper left hand corner, same as PIL
				# Note that inkscape displays origin as lower left hand corner...weird
				# style="fill:#00ff00"
				color = None
				if 'style' in attrs:
					style = attrs['style']
					color = style.split(':')[1]
				#if self.flow_root and self.text is None:
				#	raise Exception('Missing text')
				self.last_polygon = self.layer.add_rect(float(attrs['x']) + self.x_delta, float(attrs['y']) + self.y_delta, float(attrs['width']), float(attrs['height']), color=color)
			elif name == 'g':
				#transform="translate(0,-652.36218)"
				if 'transform' in attrs:
					transform = attrs['transform']
					self.process_transform(transform)
					self.g_transform = True
				else:
					self.g_transform = False
			elif name == 'svg':
			   self.layer.width = int(attrs['width'])
			   self.layer.height = int(attrs['height'])
			   #print 'Width ' + str(self.layer.width)
			   #print 'Height ' + str(self.layer.height)
			# Text entry
			elif name == 'flowRoot':
				'''
				<flowRoot
					transform="translate(15.941599,-0.58989212)"
					xml:space="preserve"
					id="flowRoot4100"
					style="font-size:12px;font-style:normal;font-variant:normal;font-weight:normal;font-stretch:normal;text-align:start;line-height:125%;writing-mode:lr-tb;text-anchor:start;fill:#000000;fill-opacity:1;stroke:none;display:inline;font-family:Bitstream Vera Sans;-inkscape-font-specification:Bitstream Vera Sans">
					<flowRegion id="flowRegion4102">
						<rect
							id="rect4104"
							width="67.261375"
							height="14.659531"
							x="56.913475"
							y="189.59261"
							style="fill:#000000" />
					</flowRegion>
					<flowPara id="flowPara4106">
						clk0
					</flowPara>
				</flowRoot>
				'''
				self.flow_root = True
				self.text = None
				
				if 'transform' in attrs:
					transform = attrs['transform']
					self.flowRoot_transform = True
					self.process_transform(transform)
				else:
					self.flowRoot_transform = False
					
			elif name == 'flowPara':
				#self.text = attrs
				#print 'TEXT: ' + repr(self.text)
				#sys.exit(1)
		  		pass
		  	else:
		  		#print 'Skipping %s' % name
				pass
		   
			
		def end_element(name):
			#print 'End element:', name
			
			if name == 'flowRoot':
				self.last_polygon.text = self.text

				self.flow_root = False
				self.text = None
				self.last_polygon = None
				if self.flowRoot_transform:
					self.pop_transform()
					self.flowRoot_transform = False
			elif name == 'g':
				if self.g_transform:
					self.pop_transform()
					self.g_transform = False
			pass
		def char_data(data):
			#print 'Character data:', repr(data)
			self.text = data
			pass

		p = xml.parsers.expat.ParserCreate()

		p.StartElementHandler = start_element
		p.EndElementHandler = end_element
		p.CharacterDataHandler = char_data

		p.Parse(raw, 1)

'''
Wrapper class to efficiently work with the quadtree
Don't keep recomputing these, just once
NOTE; we could invalidate the map by merging polygons, probably need to rebuild after?
'''
class QTUVPolygon:
	def __init__(self, uvpolygon):
		# |  bounds
		# |	  Returns minimum bounding region (minx, miny, maxx, maxy)
		self.uvpolygon = uvpolygon
		(self.left, self.top, self.right, self.bottom) = uvpolygon.polygon.bounds

# (Mask) layer
# In practice for now this is simply an SVG image
class Layer:
	METAL = 0
	DIFFUSION = 1
	PROTECTION = 2
	GROUNDED_DIFFUSION = 3
	POWERED_DIFFUSION = 4
	POLYSILICON = 5

	# unknown metal just in case
	UNKNOWN_METAL = 100
	# we figure this out, net given
	UNKNOWN_DIFFUSION = 101
	
	def __init__(self):
		self.index = None
		#self.pimage = PImage(image_file_name)
		# Set is faster but non-deterministic
		if False:
			self.polygons = set()
			self.remove_polygon = self.remove_polygon_s
			self.add_uvpolygon = self.add_uvpolygon_s
		else:
			self.polygons = list()
			self.remove_polygon = self.remove_polygon_l
			self.add_uvpolygon = self.add_uvpolygon_l
		self.name = None
		# Default color if polygon doesn't have one
		self.color = None
		self.potential = Net.UNKNOWN
		#self.virtual = False
		
		self.width = None
		self.height = None
		
		# Quadtree spatial index
		self.qt = None

	def enlarge(self, scalar = None, constant = None):
		for polygon in self.polygons:
			polygon.enlarge(scalar, constant)

	@staticmethod
	def from_sl_multi(sl_mp, name=None):
		if name is None:
			name = 'multipolygon'
		uvpl = UVPolygon.uv_polygon_list(sl_mp)
		return Layer.from_polygons(uvpl, name=name)
	
	def set_color(self, color):
		self.color = color
		for polygon in self.polygons:
			if polygon.color is None:
				polygon.color = color
	
	def get_width(self):
		if self.width is None:
			self.compute_wh()
		return self.width
		
	def get_height(self):
		if self.height is None:
			self.compute_wh()
		return self.height
		
	def keep_intersecting(self, uvpoly):
		to_remove = set()
		for self_uvpoly in self.polygons:
			if not self_uvpoly.intersects(uvpoly):
				to_remove.add(self_uvpoly)
		self.remove_polygons(to_remove)
		
	def compute_wh(self):
		# Useful for debugging
		#raise Exception('CIF should have computed %s wh' % self.name)
		# Include possibility of negative coordinates
		# Although code always assumes 0 origin, so maybe not that useful
		min_x = 0
		max_x = 0
		min_y = 0
		max_y = 0
		for polygon in self.polygons:
			# |  bounds
			# |	  Returns minimum bounding region (minx, miny, maxx, maxy)
			(minx, miny, maxx, maxy) = polygon.polygon.bounds
			min_x = min(minx, min_x)
			min_y = min(miny, min_y)
			max_x = max(maxx, max_x)
			max_y = max(maxy, max_y)
		if min_x < 0:
			print 'WARNING: min x < 0: %s' % repr(min_x)
			#raise Exception('Negative min x (untested)')
		if min_y < 0:
			print 'WARNING: min y < 0: %s' % repr(min_y)
			#raise Exception('Negative min y (untested)')
		self.width = max_x - min_x + 1
		self.height = max_y - min_y + 1

	@staticmethod
	def from_sl_mp(sl_mp):
		return Layer.from_polygons(UVPolygon.uv_polygon_list(sl_mp))

	@staticmethod
	def is_valid(layer_index):
		return layer_index >= 0 and layer_index <= 5

	@staticmethod
	def from_polygons(polygons, name=None):
		'''polygons = UV polygons'''
		ret = Layer()
		for polygon in polygons:
			ret.add_uvpolygon(polygon)
		ret.name = name
		return ret
		
	@staticmethod
	def from_layer(layer, name=None):
		return Layer.from_layers([layer], name)
		
	@staticmethod
	def from_layers(layers, name=None):
		ret = Layer()
		#ret.virtual = True
		for layer in layers:
			for polygon in layer.polygons:
				ret.add_uvpolygon(polygon)
		ret.name = name
		return ret
	
	def show(self, title=None):
		if title is None:
			title = self.name
		r = PolygonRenderer(title, width=self.get_width(), height=self.get_height())
		r.add_layer(self)
		r.render()

	def show_polygons(self, force_multicolor = True):
		if force_multicolor:
			UVPolygon.show_polygons(self.polygons)
		else:
			r = PolygonRenderer(title='Layers')
			colors = Options.color_wheel
			print 'item: ' + repr(layers.__class__)
			i = 0
			for polygon in self.polygons():
				r.add_polygon(polygon, colors[i % len(colors)])
				i += 1
			r.render()

	def gen_polygons(self):
		for polygon in self.polygons:
			yield polygon
		
	def remove_polygons(self, polygons):
		for polygon in polygons:
			self.remove_polygon(polygon)
	
	def remove_polygon_s(self, polygon):
		self.polygons.remove(polygon)
		
	def remove_polygon_l(self, polygon):
		self.polygons.remove(polygon)
		
	def assign_nets(self, netgen):
		for polygon in self.polygons:
			if polygon.net is None:
				polygon.net = netgen.get_net()
				# This polygon is the only member in the net so far
				polygon.net.add_member(polygon)
				# If the layer has a potential defined to it, propagate it
				polygon.net.potential = self.potential
				#print 'self potential: %u' % self.potential

	def __repr__(self):
		ret = 'Layer: '
		sep = ''
		for polygon in self.polygons:
			ret += polygon.__repr__() + sep
			sep = ', '
		return ret
		
	def get_name(self):
		return self.name
		
	def get_multipolygon(self):
		'''Return a shapely multipolygon representing this layer'''
		'''
		In [128]: d1 = Polygon( [(110.9072599999999937, 82.6502100000000155), (270.8686099999999897, 82.6502100000000155), (270.8686099999999897, 155.0855360000000189), (110.9072599999999937, 155.0855360000000189), (110.9072599999999937, 82.6502100000000155)] )
		In [130]: d2 = Polygon( [(178.3227500000000134, 34.3740499999999969), (203.3301850000000286, 34.3740499999999969), (203.3301850000000286, 155.0996000000000095), (178.3227500000000134, 155.0996000000000095), (178.3227500000000134, 34.3740499999999969)] )
		In [127]: mp = MultiPolygon([d1, d2])
		In [129]: print mp
		MULTIPOLYGON (((110.9072599999999937 82.6502100000000155, 270.8686099999999897 82.6502100000000155, 270.8686099999999897 155.0855360000000189, 110.9072599999999937 155.0855360000000189, 110.9072599999999937 82.6502100000000155)), ((178.3227500000000134 34.3740499999999969, 203.3301850000000286 34.3740499999999969, 203.3301850000000286 155.0996000000000095, 178.3227500000000134 155.0996000000000095, 178.3227500000000134 34.3740499999999969)))
		'''
		l_temp = [p.polygon for p in self.polygons]
		'''
		print
		print 'Getting multipoly...'
		print '\t' + repr(l_temp)
		for i in l_temp:
			print '\t' + repr(i)
		print
		'''
		ret = MultiPolygon(l_temp)
		return ret
		
	def subtract(self, other):
		'''
		Okay I'm really not impressed with shapeley / python's support for this
		or I'm doing something really wrong and its not obvious
		Trying to do any subtraction involving multipolygons seems to be hairy by producing
		null geometries which throws exceptions
		'''
		return self.subtract_by_int(other)
		#return self.subtract_by_single(other)
		# return self.subtract_by_multi(other)
		# return self.subtract_by_single_multi(other)
		return self.subtract_by_qt(other)
	
	def intersects_polygon(self, other_polygon):
		for self_polygon in self.polygons:
			if self_polygon.intersects(other_polygon):
				return True
		return False

	def subtract_by_int(self, other):
		intersection = self.intersection(other)
		i = 0
		for polygon in intersection.polygons:
			i += 1
			if False and self.intersects_polygon(polygon):
				print 'Bad subtract @ %d' % i
				raise Exception('Bad subtract')
			self.subtract_polygon(polygon)
			if False and i == 3:
				self.subtract_polygon(polygon)
				polygon.show()
				self.show()
				intersection.show()
				sys.exit(1)
		self.show()
		sys.exit(1)
		
	def subtract_polygon(self, other_polygon):
		new_polygons = list()
		#other_polygon.show()
		for self_polygon in self.polygons:
			#self_polygon.show(title='Orig')
			iter_new_polygons = self_polygon.subtract(other_polygon)
			print 'New polygons: %d' % len(iter_new_polygons)
			for polygon in iter_new_polygons:
				#polygon.show()
				new_polygons.append(polygon)
			#print 'debug break'
			#sys.exit(1)
		self.polygons = new_polygons
		
	def subtract_by_qt(self, other):
		'''
		If against ourself we only need one QT which we'll match itself
		Try one polygon at a time in an outter loop and keep a closed loop, never try matching again if come across
		'''
		# Filter out a special case thats pretty pointless
		if self == other:
			raise Exception('Are you SURE you wanted to subtract yourself?')
			
		print 'Checking (QT) subtraction of %s (%u) and %s (%u)' % (self.name, len(self.polygons), other.name, len(other.polygons))
		other.rebuild_qt()
		total_loops = len(self.polygons)
		loops = 0
		uvps = set()
		loop_factor = (total_loops / 10)
		if loop_factor is 0:
			loop_factor = 1
		for self_polygon in self.polygons:
			if self_polygon is None:
				raise Exception('None polygon')
			if loops % loop_factor == 0:
				print 'loops: %d / %d (%0.2f %%)' % (loops, total_loops, 100.0 * loops / total_loops)
			loops += 1
			
			'''
			We may split into many descendent polygons, but start with one
			'''
			working_polygons = set()
			working_polygons.add(self_polygon)
			for other_qtcandidate in other.qt.hit_polygon(self_polygon):
				# Any number of these can intersect
				
				# Don't interfere with the iteration, rework after
				changed = set()
				new_working_polygons = set()
						
				for working_polygon in working_polygons:
					if other_qtcandidate.uvpolygon.polygon.intersects(working_polygon.polygon):
						changed.add(working_polygon)
						# Go go go!
						new_working_polygons = new_working_polygons.union(set(working_polygon.subtract(other_qtcandidate.uvpolygon)))
				
				# Translate to output
				working_polygons = working_polygons.difference(changed)
				working_polygons = working_polygons.union(new_working_polygons)
			uvps = uvps.union(working_polygons)
			
		#ret = LayerI(self, other, uvpl)
		ret = Layer.from_polygons(uvps)
		ret.width = self.width
		ret.height = self.height
		ret.name = '%s - %s' % (self.name, other.name)
		if False:
			# If successful should not show any of the poly
			
			if True:
				r = PolygonRenderer(title='subtracted layer, b=source, r=subtracted, g=result')
				r.add_layer(other, color='red')
				r.add_layer(self, color='blue')
				r.add_layer(ret, color='green')
				r.render()
			else:			
				self.show()
				other.show()
				ret.show()
			sys.exit(1)
		return ret
	
	
	def subtract_by_single_multi(self, other, new_color=None):
		'''
		Not sure if this will work since we can't tag
		
		XXX: would this be faster if I used the quadtree?
		Don't think Shapeley uses spatial indexes
		'''
		# Seed and subtract until we stop intersecting
		# FIXME: looks like we can only subtract poly from multi, not multi from multi :(
		mp_temp = self.get_multipolygon()
		mp_other = other.get_multipolygon()
		first = None
		'''
		Outter loops need to be other since its fixed
		Can only subtract poly from multipoly, not multipoly from multipoly
		'''
		uvpl = list()
		total_loops = len(mp_other)
		print 'Beginning subtraction (%d elements)' % total_loops
		loops = 0
		for poly in mp_other:
			#print 'iter'
			if loops % (total_loops / 10) == 0:
				print 'loops: %d / %d (%0.2f %%)' % (loops, total_loops, 100.0 * loops / total_loops)
			loops += 1
			
			#UVPolygon.from_polygon(poly).show()
			#Layer.from_polygons(UVPolygon.uv_polygon_list(mp_temp)).show()
			
			old_size = len(mp_temp)
			#Layer.from_sl_mp(mp_temp).show()
			
			# Was expecting non-intersection to result in same thing, but it throws exception due to null geometry
			# Is it more efficient to check intersection and then only diff if exception
			# Or to try to differentiate and catch the null geometry exception?
			# Catching exception might be faster but checking intersect is more proper
			if True:
				if mp_temp.intersects(poly):
					# Hmm this is still generating null geometry exception
					# Maybe due to hairline intersection?
					try:
						#print 'start'
						test = mp_temp.intersection(poly)
						#print 'inter complete'
						#print test
						
						mp_temp = mp_temp.difference(poly)
					except:
						print 'Warning: topological error'
						
						r = PolygonRenderer(title='mp_temp exception, b=mp, r=subtracted')
						for polygon in mp_temp:
							r.add_polygon(UVPolygon.from_polygon(polygon), color='blue')
						r.add_polygon(UVPolygon.from_polygon(poly), color='red')
						r.render()
						
						pass
			else:
				print 'Beginning difference'
				try:
					mp_temp = mp_temp.difference(poly)
					print 'Differentiated'
				except(TopologicalError):
					print 'Warning: topological error'
					raise
					# This is actually OK
					if False:
						print 'mp_temp:'
						for polygon in mp_temp:
							print '\t' + repr(polygon)
						print poly
				
				
						r = PolygonRenderer(title='mp_temp exception, b=mp, r=subtracted')
						for polygon in mp_temp:
							r.add_polygon(UVPolygon.from_polygon(polygon), color='blue')
						r.add_polygon(UVPolygon.from_polygon(poly), color='red')
						r.render()
				
				
						raise
					continue
			if False:
				new_size = len(mp_temp)
				uvpl = UVPolygon.uv_polygon_list(mp_temp)
				for polygon in uvpl:
					if not len(polygon.get_points()) == 8:
						continue
					print '***'
					print 'Polygon 1: ' + repr(polygon)
					print polygon.polygon
					#polygon.show()
					print 'Polygon dir: ' + repr(dir(polygon.polygon))
					print '***'
					print polygon.to_cli()
				
					#import pdb; pdb.set_trace()

				print 'Iteration %d => %d (%d)' % (old_size, new_size, len(uvpl))
				#Layer.from_polygons(uvpl).show()
		
		#sys.exit(1)
		uvpl = UVPolygon.uv_polygon_list(mp_temp, new_color = new_color)
		print 'New polys: %d => %d' % (len(uvpl), len(uvpl))
		#sys.exit(1)
		
		'''
		XXX: need to preserve nets?
		Current requirements is blanket preservation, not precision
		'''
		for new_uvpoly in uvpl:
			found = False
			for old_uvpoly in self.polygons:
				if old_uvpoly.intersects(new_uvpoly):
					new_uvpoly.color = old_uvpoly.color
					new_uvpoly.net = old_uvpoly.net
					found = True
					# Each new should intersect at most one old
					break
			if not found:
				raise Exception('Could not match up new to old')
		
		
		
		ret = LayerI(self, other, uvpl)
		return ret
	
	def subtract_by_multi(self, other, new_color=None):
		'''
		Not sure if this will work since we can't tag
		'''
		# FIXME: looks like we can only subtract poly from multi, not multi from multi :(
		mp_self = self.get_multipolygon()
		mp_other = other.get_multipolygon()
		first = None
		'''
		
		'''
		for poly in mp_other:
			first = poly
		diff = mp_self.difference(first)
		
		uvpl = UVPolygon.uv_polygon_list(diff, new_color = new_color)
		
		return LayerI(self, other, uvpl)
		
	def subtract_by_single(self, other):
		return self.subtract_by_single1(other)
	
	def subtract_by_single1(self, other):
		'''
		Outer subtractand, inner source
		Polygons will not be subtracted by the same polygon twice, so we only need to subtrac against the remaining for that loop
		'''
		
		self.intersection(other).show()
	
		if self == other:
			raise Exception('Are you SURE you wanted to subtract yourself?')
			
		#self.show()
		#sys.exit(1)
			
		# list of intersecting polygons
		print 'Checking (basic) subtraction of %s (%u) and %s (%u)' % (self.name, len(self.polygons), other.name, len(other.polygons))
		total_loops = len(other.polygons)
		loops = 0
		uvps = set()
		working_self_set = self.polygons
		for other_polygon in other.polygons:
			next_working_self_set = set()
			if loops % (total_loops / 10) == 0:
				print 'loops: %d / %d (%0.2f %%)' % (loops, total_loops, 100.0 * loops / total_loops)
			loops += 1
			for self_polygon in working_self_set:
				if self_polygon is None:
					raise Exception('None polygon')

				if self_polygon.polygon.intersects(other_polygon.polygon):
					for polygon in self_polygon.subtract(other_polygon):
						next_working_self_set.add(polygon)
						
					'''
					r = PolygonRenderer(title='subtracted')

					r.add_polygon(self_polygon, color='green')
					r.add_polygon(working_polygon, color='blue')

					for polygon in self_polygon.subtract(working_polygon):
						r.add_polygon(polygon, color='red')
						next_working_set.add(polygon)
					r.render()
					sys.exit(1)
					'''
				else:
					next_working_self_set.add(self_polygon)
			working_self_set = next_working_self_set
			if True:
				#other_polygon.show()
				#Layer.from_polygons(working_self_set).show()
				
				r = PolygonRenderer(title='subtracted layer, b=source, r=subtracted, g=result')
				r.add_polygon(other_polygon, color='red')
				for polygon in working_self_set:
					r.add_polygon(polygon, color='green')
				r.render()
				
			if loops == 2:
				aslkjfds
			
		ret = Layer.from_polygons(working_self_set)
		ret.width = self.width
		ret.height = self.height
		ret.name = '%s - %s' % (self.name, other.name)
		print 'Subtract went from %d => %d polygons' % (len(self.polygons), len(ret.polygons))

		if True:
			# If successful should not show any of the poly
			
			if True:
				r = PolygonRenderer(title='subtracted layer, b=source, r=subtracted, g=result')
				#r.add_layer(self, color='blue')
				#r.add_layer(other, color='red')
				r.add_layer(ret, color='green')
				r.render()
			else:			
				self.show()
				other.show()
				ret.show()
			sys.exit(1)

		return ret
		
	def subtract_by_single2(self, other):
		'''
		Outer source, inner subtractand
		Outer polygons can be subtracted more than once so we need to maintain a working list within the iner loop
		'''
	
	
		if self == other:
			raise Exception('Are you SURE you wanted to subtract yourself?')
			
		#self.show()
		#sys.exit(1)
			
		# list of intersecting polygons
		print 'Checking (basic) subtraction of %s (%u) and %s (%u)' % (self.name, len(self.polygons), other.name, len(other.polygons))
		total_loops = len(self.polygons)
		loops = 0
		uvps = set()
		for self_polygon in self.polygons:
			if self_polygon is None:
				raise Exception('None polygon')
			if loops % (total_loops / 10) == 0:
				print 'loops: %d / %d (%0.2f %%)' % (loops, total_loops, 100.0 * loops / total_loops)
			loops += 1
			
			'''
			We may split into many descendent polygons, but start with one
			'''
			working_polygons = set()
			working_polygons.add(self_polygon)
			for other_polygon in other.polygons:
				# Any number of these can intersect
				
				# Don't interfere with the iteration, rework after
				changed = set()
				new_working_polygons = set()
				
				for working_polygon in working_polygons:
					if other_polygon.polygon.intersects(working_polygon.polygon):
						changed.add(working_polygon)
						# Go go go!
						descendent_polygons = set(working_polygon.subtract(other_polygon))
						new_working_polygons = new_working_polygons.union(descendent_polygons)
				
				# Translate to output
				working_polygons = working_polygons.difference(changed)
				working_polygons = working_polygons.union(new_working_polygons)
			uvps = uvps.union(working_polygons)
				
		ret = Layer.from_polygons(uvps)
		ret.width = self.width
		ret.height = self.height
		ret.name = '%s - %s' % (self.name, other.name)


		if True:
			# If successful should not show any of the poly
			
			if True:
				r = PolygonRenderer(title='subtracted layer, b=source, r=subtracted, g=result')
				r.add_layer(self, color='blue')
				r.add_layer(other, color='red')
				#r.add_layer(ret, color='green')
				r.render()
			else:			
				self.show()
				other.show()
				ret.show()
			sys.exit(1)

		return ret

	def rebuild_qt(self):
		bench = Benchmark()
		rect_l = list()
		for polygon in self.polygons:
			rect_l.append(QTUVPolygon(polygon))
		self.qt = PolygonQuadTree(rect_l)
		print 'Finished building %s quadtree (%d elements), took: %s' % (self.name, len(rect_l), repr(bench))
	
	def intersection(self, other, do_xintersection = False):
		#return self.intersection_brute_force(other, do_xintersection)
		return self.intersection_qt(other, do_xintersection)
		
	def get_pair_polygen(self, other):
		def gen_pairs_normal():
			'''Normal polygon generator where polygons don't repeat'''
			for self_polygon in self.polygons:
				for other_polygon in other.polygons:
					yield (self_polygon, other_polygon)
		
		def gen_pairs_same():
			'''Avoid comparing against self'''
			tried = set()
			polygons = list(self.polygons)
			# Trim off i = 0 case (range(0, 0) = [])
			for i in range(1, len(polygons)):
				for j in range(0, i):
					yield (polygons[i], polygons[j])
					
		if self == other:
			polygen = gen_pairs_same()
		else:
			total_loops = len(list(gen_pairs_normal()))
			polygen = gen_pairs_normal()
		return polygen
		
	def intersection_qt(self, other, do_xintersection = False):
		'''
		If against ourself we only need one QT which we'll match itself
		Try one polygon at a time in an outter loop and keep a closed loop, never try matching again if come across
		'''
		if self == other:
			# list of intersecting polygons
			xintersections = list()
			print 'Checking (QT) intersection of %s (%u) and %s (%u)' % (self.name, len(self.polygons), other.name, len(other.polygons))
			
			self.rebuild_qt()
			closed_list = set()
			total_loops = len(self.polygons)
			loops = 0		
			for polygon in self.polygons:
				if loops % (total_loops / 10) == 0:
					print 'loops: %d / %d (%0.2f %%)' % (loops, total_loops, 100.0 * loops / total_loops)
				loops += 1
				
				for qtcandidate in self.qt.hit_polygon(polygon):
					if qtcandidate.uvpolygon == polygon:
						continue
					xintersections_cur = self.attempt_intersection(other, polygon, qtcandidate.uvpolygon, do_xintersection)
					if xintersections:
						for xintersections_cur_polygon in xintersections_cur:
							xintersections.append(xintersections_cur_polygon)
					
				closed_list.add(polygon)
		
			return LayerI(self, other, xintersections)
		else:
			# list of intersecting polygons
			xintersections = list()
			print 'Checking (QT) intersection of %s (%u) and %s (%u)' % (self.name, len(self.polygons), other.name, len(other.polygons))
			self.rebuild_qt()
			total_loops = len(other.polygons)
			loops = 0
			'''
			Is there an advantage as to which set we build the QT
			and which we run the matches agains?
			QT will take longer to build, but matches will go faster
			Would take some benchmarking or order analysis to figure out
			'''
			loop_factor = (total_loops / 10)
			if loop_factor is 0:
				loop_factor = 1
			for other_polygon in other.polygons:
				if other_polygon is None:
					raise Exception('None polygon')
				if loops % loop_factor == 0:
					print 'loops: %d / %d (%0.2f %%)' % (loops, total_loops, 100.0 * loops / total_loops)
				loops += 1
				for self_qtcandidate in self.qt.hit_polygon(other_polygon):
					# No potential for matches against self, no check needed
					xintersections_cur = self.attempt_intersection(other, self_qtcandidate.uvpolygon, other_polygon, do_xintersection)
					for xintersection_cur in xintersections_cur:
						xintersections.append(xintersection_cur)
				
			return LayerI(self, other, xintersections)
		
	def attempt_intersection(self, other, self_polygon, other_polygon, do_xintersection):
		if do_xintersection:
			#print
			#print self_polygon
			#print self_polygon.polygon
			poly1 = self_polygon.get_xpolygon()
			poly2 = other_polygon.get_xpolygon()
		else:
			poly1 = self_polygon.polygon
			poly2 = other_polygon.polygon
		
		if not poly1.geom_type == 'Polygon':
			print 'WARNING: poly1 is %s' % poly1.geom_type
			raise Exception('abc')
		if not poly2.geom_type == 'Polygon':
			print 'WARNING: poly2 is %s' % poly2.geom_type
			raise Exception('abc')
		
		if False:
			print 'Checking:'
			print '\t%s: %s' % (self.name, poly1)
			print '\t%s: %s' % (other.name, poly2)
		
		if poly1.intersects(poly2):
			#print 'I',
			#print 'Intersection!'
			#print '%s %s vs %s %s' % (self.name, poly1, other.name, poly2)
			uvpoly1 = UVPolygon.from_polygon(poly1)
			uvpoly2 = UVPolygon.from_polygon(poly2)
			xintersection = uvpoly1.intersection(uvpoly2)
			if xintersection is None:
				raise Exception("not intersected")
			# Tack on some intersection data
			xintersections = list()
			for xintersection in xintersection:
				xintersection.poly1 = self_polygon
				xintersection.poly2 = other_polygon
				xintersections.append(xintersection)
			return xintersections
		else:
			return None
		
	def intersection_brute_force(self, other, do_xintersection = False):
		# list of intersecting polygons
		xintersections = list()
		print 'Checking intersection of %s (%u) and %s (%u)' % (self.name, len(self.polygons), other.name, len(other.polygons))
		
		polygen = self.get_pair_polygen(other)
		total_loops = len(self.polygons) * len(other.polygons)
		
		loops = 0		
		
		#print 'Start...'
		for (self_polygon, other_polygon) in polygen:
			if loops % 100000 == 0:
				print 'loops: %d / %d (%0.2f %%)' % (loops, total_loops, 100.0 * loops / total_loops)
			loops += 1
			xintersection = self.attempt_intersection(other, self_polygon, other_polygon, do_xintersection)
			if xintersection:
				xintersections.append(xintersection)
		return LayerI(self, other, xintersections)

	@staticmethod
	def from_svg(file_name):
		p = Layer()
		p.do_from_svg(file_name)
		p.name = file_name
		return p
				
	def do_from_svg(self, file_name):
		LayerSVGParser.parse(self, file_name)
	
	def add_rect(self, x, y, width, height, color=None):
		return self.add_polygon_by_points(list([Point(x, y), Point(x + width, y), Point(x + width, y + height), Point(x, y + height)]), color=color)
		
	def add_polygon_by_points(self, points, color=None):
		polygon = UVPolygon(points, color=color)
		self.polygons.add(polygon)
		return polygon

	def add_uvpolygon_s(self, polygon, color=None):
		#if polygon is None:
		#	raise Exception('Tried to add None')
		self.polygons.add(polygon)

	def add_uvpolygon_begin(self, polygon, color=None):
		self.polygons.insert(0, polygon)

	def add_uvpolygon_l(self, polygon, color=None):
		#if polygon is None:
		#	raise Exception('Tried to add None')
		self.polygons.append(polygon)
		
	@staticmethod
	def show_layers(layers):
		r = PolygonRenderer(title='Layers')
		colors = Options.color_wheel
		print 'item: ' + repr(layers.__class__)
		for i in range(0, len(layers)):
			r.add_layer(layers[i], colors[i % len(colors)])
		r.render()

