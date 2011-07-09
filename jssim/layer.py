import xml.parsers.expat
from shapely.geometry import Polygon

class Net:
	def __init__(self):
		self.polygons = set()
		self.number = None
		
	def merge(self, other):
		self.polygons.add(other.polygons)
		# Give us a net number if possible
		if self.number is None:
			self.number = other.number

# Used in merging
class NetProxy:
	def __init__(self, net):
		self.net = net

class Point:
	def __init__(self, x, y):
		self.x = x
		self.y = y

'''
Head up: may need to be able to do transforms if the canvas is relaly large
which shouldn't be too uncommon
'''
class PolygonRenderer:
	def __init__(self):
		# In render order
		# (polygon, color)
		self.targets = list()
		# Polygon color overrides
		# [polygon] = color
		# Make this usually not take up memory but can if you really want it
		self.colors = dict()

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
				print dir(point)
				points.append(point.x)
				points.append(point.y)
			canvas.create_polygon(points, fill=color)

		canvas.pack()
		root.mainloop()

class UVPolygon:
	def __init__(self, points, color=None):
		'''
		To make display nicer
		Vaguely defined...HTML like
		Can either be a human color like red or green or HTML like #602030
		'''
		self.color = color
		
		if points:
			self.points = points
		
			self.net = None
			self.polygon = Polygon([(point.x, point.y) for point in points])
			self.rebuild_xpolygon()
	
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

# (Mask) layer
# In practice for now this is simply an SVG image
class Layer:
	def __init__(self):
		#self.pimage = PImage(image_file_name)
		self.polygons = set()
		self.name = None
		# Default color if polygon doesn't have one
		self.color = None

	def assign_nets(self, netgen):
		for polygon in self.polygons:
			if polygon.net is None:
				polygon.net = netgen.get_net()

	def __repr__(self):
		ret = ''
		for polygon in self.polygons:
			ret += polygon.__repr__() + '\n'
		return ret
		
	def get_name(self):
		return self.name

	def intersection(self, other):
		xintersections = list()
		for poly_polygon in self.polygons:
			for diff_polygon in other.polygons:
				poly1 = poly_polygon.xpolygon
				poly2 = diff_polygon.xpolygon
				if poly1.intersects(poly2):
					print 'Intersection!'
					print 'poly %s vs diff %s' % (poly1, poly2)
					xintersection = UVPolygon.from_polygon(poly1).intersection(UVPolygon.from_polygon(poly2))
					xintersections.append(xintersection)
		return LayerI(self, other, xintersections)

	@staticmethod
	def from_layers(layers):
		l = Layer()
		for layer in layers:
			for polygon in layer.polygons:
				l.polygons.add(polygon)
		return l

	@staticmethod
	def from_svg(file_name):
		p = Layer()
		p.do_from_svg(file_name)
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
		
		self.x_delta = 0.0
		self.y_delta = 0.0


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
				self.add_rect(float(attrs['x']), float(attrs['y']), float(attrs['width']), float(attrs['height']), color=color)
			elif name == 'g':
				#transform="translate(0,-652.36218)"
				if 'transform' in attrs:
					transform = attrs['transform']
					self.x_delta = float(transform.split(',')[0].split('(')[1])
					self.y_delta = float(transform.split(',')[1].split(')')[0])
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
		x += self.x_delta
		y += self.y_delta
		self.add_polygon(list([Point(x, y), Point(x + width, y), Point(x + width, y + height), Point(x, y + height)]), color=color)
		
	def add_polygon(self, points, color=None):
		self.polygons.add(UVPolygon(points, color=color))


