from pr0ntools.layer.layer import *

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


def path2points(path):
	def isnum(part):
		c = part[0]
		return c >= '0' annd c <= '9' or c == '+' or c == '-'

	cur_x = None
	cur_y = None
	# Preprocess a bit
	# Spec says that commas are equivilent to whitespace
	path.upper().replace(',', ' ')
	
	# Since whitespace is not required its best to parse a token at a time rather than split on space
	# However inkscape is outputting a mix of commas and spaces so good enough for now
	tokens = path.split()
	action = None
	points = []
	# d="m 68.185297,3.7588384 -48.992399,0 0,156.0685716 46.467017,0 0,-53.53809 -14.647211,0 0,-58.08377 17.172593,0 z"
	for i in range(len(tokens)):
		part = tokens[i]
		# Move to
		if part == 'M':
			action = 'M'
			continue
		# Close path
		elif part == 'Z':
			# Multiple paths are allowed, return an multidimentional array of points if this starts to occur
			if i != len(tokens) - 1:
				raise Exception('Expect close path last element')
			return points
		elif not isnum(part):
			raise Exception('Unknown part %s' % part)
		
		# move to?
		if action == 'M':
			# (x, y)
			cur_x = tokens[i]
			i += 1
			cur_y = tokens[i]
			self.points.append(Point(cur_x, cur_y))
		else:
			raise Excetpion('Unknown cur action %s' % action)
	raise Exception('Path was not closed')

class MultilayerSVGParser:
	def __init__(self, file_name)
		# Dict of layer name to layer object
		# Adds a layer for every layer found in the source image
		self.layers = []
		self.file_name = file_name
		# Image files found in the SVG
		self.images = []

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
		
	def run(self):
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
		
		self.cur_layer = None

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
				self.last_polygon = self.cur_layer.add_rect(float(attrs['x']) + self.x_delta, float(attrs['y']) + self.y_delta, float(attrs['width']), float(attrs['height']), color=color)
			elif name == 'path':
				'''
				<path
				   style="fill:#00ff00;fill-opacity:1;stroke:none"
				   d="m 68.185297,3.7588384 -48.992399,0 0,156.0685716 46.467017,0 0,-53.53809 -14.647211,0 0,-58.08377 17.172593,0 z"
				   id="path3110"
				   inkscape:connector-curvature="0" />
				'''
				color = None
				if 'style' in attrs:
					style = attrs['style']
					color = style.split(':')[1]
				points = path2points(attrs['d'])
				self.last_polygon = self.cur_layer.add_polygon_by_points(points, color=color)
			elif name == 'image':
				'''
				<image
				   y="461.00504"
				   x="276.21426"
				   id="image3082"
				   xlink:href="file:///home/mcmaster/document/external/pr0ntools/capture/test/both_0.jpg"
				   height="177"
				   width="99" />
				'''
				self.images.append(attrs['xlink:href'])
			elif name == 'g':
				'''
				<g
					 inkscape:groupmode="layer"
					 id="layer2"
					 inkscape:label="active"
					 style="display:inline">
				 	...
				</g>
				'''
				#transform="translate(0,-652.36218)"
				if 'transform' in attrs:
					transform = attrs['transform']
					self.process_transform(transform)
					self.g_transform = True
				else:
					self.g_transform = False
					
				if 'id' in attrs:
					if self.cur_layer:
						raise Exception('Nester layer?')
					layer_name = attrs['id']
					if layer_name in self.layers:
						raise Exception("Duplicate layer %s" % layer_name)
					self.cur_layer = Layer()
					self.cur_layer.name = layer_name
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

