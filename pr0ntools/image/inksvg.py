'''
Filter to iterate over an InkSVG and remove all layers with images
'''
class RemoveImages:
	def __init__(self, ink):
		self.ink = ink
	
	def run(self):
		self.flow_root = False
		self.text = None
		
		self.cur_layer = None
		self.image_layers = set()

		# 3 handler functions
		def start_element(name, attrs):
			if name == 'image':
				if not self.cur_layer or not self.in_image_layer:
					raise Exception('Unexpected image in layer %s' % self.cur_layer)
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
				if 'inkscape:label' in attrs:
					if self.cur_layer:
						raise Exception('Nester layer?')
					self.cur_layer = attrs['inkscape:label']
					self.in_image_layer = self.cur_layer.endswith('_img')
				else:
					self.cur_layer = True
					self.in_image_layer = False
					
		def end_element(name):
			if name == 'g':
				if self.in_image_layer:
					self.image_layers.add(self.cur_gropu)
				self.cur_layer = None


		self.cur_layer = None
		self.in_image_layer = False


		p = xml.parsers.expat.ParserCreate()

		p.StartElementHandler = start_element
		p.EndElementHandler = end_element
		p.CharacterDataHandler = char_data

		p.Parse(self.ink.text, 1)
		for layer in self.image_layers:
			print 'Image layer %s' % self.image_layer	
		self.ink.mark_dirty()

class InkSVG:
	def __init__(self, text):
		self.text = text
		self.mark_dirty()
		
	def mark_dirty(self):
		self._width = None
		self._height = None
		
	def width(self):
		if not self._width is None:
			return self._width
		self.reparse()
		return self._width
	
	def height(self):
		if not self._height is None:
			return self._height
		self.reparse()
		return self._height
		
	def reparse(self):
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
		raw = self.text
		
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
					color = style.split(':')[1].split(';')[0]
				points = path2points(attrs['d'])
				if len(points) != 0:
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
				self.images.add(attrs['xlink:href'])
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
					
				if 'inkscape:label' in attrs:
					if self.cur_layer:
						raise Exception('Nester layer?')
					layer_name = attrs['inkscape:label']
					print 'Found layer %s' % layer_name
					if layer_name in self.layers:
						raise Exception("Duplicate layer %s" % layer_name)
					self.cur_layer = Layer()
					self.cur_layer.name = layer_name
			elif name == 'svg':
			   self._width = int(attrs['width'])
			   self._height = int(attrs['height'])
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
				self.layers[self.cur_layer.name] = self.cur_layer
				self.cur_layer = None
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

		p.Parse(self.text, 1)
		

