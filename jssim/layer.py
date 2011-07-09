import xml.parsers.expat
from shapely.geometry import Polygon

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
		
	def add_member(self, member):
		self.members.add(member)
		
	def merge(self, other):
		for member in other.members:
			self.members.add(member)
		# Give us a net number if possible
		if self.number is None:
			self.number = other.number
		'''
		Any conflicting net status?
		Conflict
			VCC and GND
		Warning?
			PU/PD and VSS/GND
		Transition
			UNKNOWN and X: X
		'''
		# Expect most common case
		if self.potential == Net.UNKNOWN:
			self.potential == other.potential
		else:
			p1 = self.potential
			p2 = other.potential
			# Sort to reduce cases (p1 lower)
			if p1 > p2:
				p = p1
				p1 = p2
				p2 = p
			# Expect most common case
			if p1 == Net.UNKNOWN:
				pass
			elif p1 == Net.VDD and t2 == Net.GND:
				raise Exception("Supply shorted")
			elif (p1 == Net.VDD or p1 == Net.GND) and (p2 == Net.PU or p2 == Net.PD):
				print 'WARNING: eliminating pullup/pulldown status due to direct supply connection'
				self.potential = p1
			else:
				print p1
				print p2
				raise Exception('Unaccounted for net potential merge')
		
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

	def merge(self, new_net, old_net):
		'''Move data from old_net number into new_net number'''
		self.nets[new_net].merge(self.nets[old_net])
		del self.nets[old_net]
				
class Point:
	def __init__(self, x, y):			
		self.x = x
		self.y = y

'''
Head up: may need to be able to do transforms if the canvas is relaly large
which shouldn't be too uncommon
'''
class PolygonRenderer:
	def __init__(self, title=None):
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

	# Specify color to override default or None for current
	def add_polygon(self, polygon, color=None):
		if color:
			self.colors[polygon] = color
		self.targets.append(polygon)
		
	def add_layer(self, layer, color=None):
		for polygon in layer.polygons:
			self.add_polygon(polygon, color)

	def add_xlayer(self, color=None):
		for polygon in layer.xpolygons:
			self.add_polygon(polygon, color)
		
	# Call after setup
	def render(self):
		from Tkinter import *

		root = Tk()

		root.title('Canvas')
		canvas = Canvas(root, width =400, height=400)

		# Upper left origin origin just like us
		#points = [1,1,10,1,10,10,1,10]
		for polygon in self.targets:
			points = list()
			
			# Use override if given
			if polygon in self.colors:
				color = self.colors[polygon]
			else:
				color = polygon.color
			if color is None:
				# Default to black
				color = 'black'
				
			for point in polygon.points:
				#print dir(point)
				points.append(point.x)
				points.append(point.y)
			canvas.create_polygon(points, fill=color)

		canvas.pack()
		root.title(self.title)
		root.mainloop()

'''
Polygons are aware of anything need to draw them as well as their electrical properties
They are not currently aware of their material (layer) but probably need to be aware of it to figure out color
Currently color is pushed on instead of pulled
Final JSSim figures out color from layer and segdefs are pushed out on a layer by layer basis so its not necessary to store
'''
class UVPolygon:
	def __init__(self, points, color=None):
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
		
		if points:
			self.points = points
		
			self.polygon = Polygon([(point.x, point.y) for point in points])
			self.rebuild_xpolygon()
	
	def coordinates(self):
		'''return (JSSim style) single dimensional array of coordinates'''
		# return [i for i in [point.x,point.y) for point in self.points]
		# l = [(1, 2), (3, 4), (50, 32)]
		# print [i for i in [(x[0],x[1]) for x in l]]
		ret = list()
		for point in self.points:
			ret.append(point.x)
			ret.append(point.y)
		return ret
		
	@staticmethod
	def from_polygon(polygon):
		poly = UVPolygon(None)
		poly.polygon = polygon
		poly.net = None
		poly.rebuild_points()
		poly.rebuild_xpolygon()
		return poly
	
	def rebuild_points(self):
		self.points = list()
		for i in range(len(self.polygon.exterior.coords.xy[0]) - 1):
			x = self.polygon.exterior.coords.xy[0][i]
			y = self.polygon.exterior.coords.xy[1][i]
			#self.points.append((x, y))
			self.points.append(Point(x, y))
	
	def __repr__(self):
		ret = "<polygon points=\""
		first = True
		for point in self.points:
			# Space pairs to make it a little more readable
			if not first:
				ret += ', '
			ret += "%u,%u" % (point.x, point.y)
			first = False
		ret += '" />'
		return ret

	def rebuild_xpolygon(self):
		'''
		Rebuild extended polygon
		Trys to find neighboring polygons by stretching about the centroid
		which we will then try to overlap
		'''
		
		centroid = self.polygon.centroid
		
		xbounds = list()
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
		self.xpolygon = Polygon(xbounds)

	def intersects(self, polygon):
		# Check x intersect and y intersect
		# XXX: 
		return self.polygon.intersects(polygon.polygon)

	def intersection(self, polygon):
		return UVPolygon.from_polygon(self.polygon.intersection(polygon.polygon))

	@staticmethod
	def show_polygons(polygons):
		FIXME
	
	def show(self):
		from Tkinter import *

		root = Tk()

		root.title('Canvas')
		canvas = Canvas(root, width =400, height=400)

		# Upper left origin origin just like us
		#points = [1,1,10,1,10,10,1,10]
		points = list()
		for point in self.points:
			points.append(point.x)
			points.append(point.y)
		canvas.create_polygon(points, fill='white')

		canvas.pack()
		root.mainloop()
		

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
class LayerI:
	def __init__(self, layer1, layer2, polygons):
		self.layer1 = layer1
		self.layer2 = layer2
		self.polygons = polygons

	def show(self):
		#UVPolygon.show_polygons(xintersections)
		r = PolygonRenderer()
		r.add_layer(self.layer1, 'red')
		r.add_layer(self.layer2, 'green')
		# Render intersection last
		for polygon in self.polygons:
			r.add_polygon(polygon, 'blue')
		r.render()

	# So can be further intersected
	def to_layer(self):
		layer = Layer()
		layer.polygons = self.polygons
		layer.name = 'Intersection of %s and %s' % (self.layer1.name, self.layer2.name)
		# Why not
		layer.color = 'blue'
		return layer

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
		self.polygons = set()
		self.name = None
		# Default color if polygon doesn't have one
		self.color = None
		self.potential = Net.UNKNOWN

	@staticmethod
	def is_valid(layer_index):
		return layer_index >= 0 and layer_index <= 5

	@staticmethod
	def from_layers(layers, name=None):
		ret = Layer()
		for layer in layers:
			for polygon in layer.polygons:
				ret.polygons.add(polygon)
		ret.name = name
		return ret
		
	def assign_nets(self, netgen):
		for polygon in self.polygons:
			if polygon.net is None:
				polygon.net = netgen.get_net()
				# This polygon is the only member in the net so far
				polygon.net.add_member(polygon)
				# If the layer has a potential defined to it, propagate it
				polygon.net.potential = self.potential

	def __repr__(self):
		ret = ''
		for polygon in self.polygons:
			ret += polygon.__repr__() + '\n'
		return ret
		
	def get_name(self):
		return self.name

	def intersection(self, other, do_xintersection=True):
		# list of intersecting polygons
		xintersections = list()
		print 'Checking intersection of %s (%u) and %s (%u)' % (self.name, len(self.polygons), other.name, len(other.polygons))
		for self_polygon in self.polygons:
			for other_polygon in other.polygons:
				if do_xintersection:
					poly1 = self_polygon.xpolygon
					poly2 = other_polygon.xpolygon
				else:
					poly1 = self_polygon.polygon
					poly2 = other_polygon.polygon
				
				if False:
					print 'Checking:'
					print '\t%s: %s' % (self.name, poly1)
					print '\t%s: %s' % (other.name, poly2)
				
				if poly1.intersects(poly2):
					print 'Intersection!'
					print '%s %s vs %s %s' % (self.name, poly1, other.name, poly2)
					xintersection = UVPolygon.from_polygon(poly1).intersection(UVPolygon.from_polygon(poly2))
					# Tack on some intersection data
					xintersection.poly1 = self_polygon
					xintersection.poly2 = other_polygon
					xintersections.append(xintersection)
		return LayerI(self, other, xintersections)

	@staticmethod
	def from_svg(file_name):
		p = Layer()
		p.do_from_svg(file_name)
		p.name = file_name
		return p
				
	def do_from_svg(self, file_name):
		'''
		<rect
		   y="261.16562"
		   x="132.7981"
		   height="122.4502"
		   width="27.594412"
		   id="rect3225"
		   style="fill:#999999" />
		'''
		raw = open(file_name).read()
		print file_name
		
		print 'set vars'
		self._x_delta = 0.0
		self._y_delta = 0.0

		# 3 handler functions
		def start_element(name, attrs):
			print 'Start element:', name, attrs
			if name == 'rect':				
				#print 'Got one!'
				# Origin at upper left hand corner, same as PIL
				# Note that inkscape displays origin as lower left hand corner...weird
				# style="fill:#00ff00"
				color = None
				if 'style' in attrs:
					style = attrs['style']
					color = style.split(':')[1]
				self.add_rect(float(attrs['x']) + self._x_delta, float(attrs['y']) + self._y_delta, float(attrs['width']), float(attrs['height']), color=color)
			elif name == 'g':
				#transform="translate(0,-652.36218)"
				if 'transform' in attrs:
					transform = attrs['transform']
					self._x_delta = float(transform.split(',')[0].split('(')[1])
					self._y_delta = float(transform.split(',')[1].split(')')[0])
				else:
					self._x_delta = 0.0
					self._y_delta = 0.0
			elif name == 'svg':
			   self.width = int(attrs['width'])
			   self.height = int(attrs['height'])
			   print 'Width ' + str(self.width)
			   print 'Height ' + str(self.height)
		   	else:
		   		print 'Skipping %s' % name
				pass
		   
			
		def end_element(name):
			#print 'End element:', name
			pass
		def char_data(data):
			#print 'Character data:', repr(data)
			pass

	 	p = xml.parsers.expat.ParserCreate()

		p.StartElementHandler = start_element
		p.EndElementHandler = end_element
		p.CharacterDataHandler = char_data

		p.Parse(raw, 1)
	
	def add_rect(self, x, y, width, height, color=None):
		self.add_polygon(list([Point(x, y), Point(x + width, y), Point(x + width, y + height), Point(x, y + height)]), color=color)
		
	def add_polygon(self, points, color=None):
		self.polygons.add(UVPolygon(points, color=color))


