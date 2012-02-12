# Makes second UL part show
BOX_MAX = 200
BOX_MAX = None
box_limit = 0

g_print_result = False

if False:
	from pr0ntools.jssim.layer import UVPolygon, Net, Nets, PolygonRenderer, Point
	
	#g_print_result = True

	clip_x_min = 250
	clip_x_max = 360
	clip_y_min = 150
	clip_y_max = 250
	
	# Flip since working coordinate system in flipped?
	if True:
		width = 1319
		height = 820
		clip_y_min = height - clip_y_min
		clip_y_max = height - clip_y_max
	
	g_limit_polygon = UVPolygon.from_rect_ex(clip_x_min, clip_y_min, clip_x_max - clip_x_min + 1, clip_y_max - clip_y_min + 1)
	g_limit_polygon.color = 'white'
else:
	g_limit_polygon = None
	
g_default_scalar = 0.007
#g_default_scalar = 1.0

class Layer:
	# FIGURE B.1 CIF layer names for MOS processes.

	# NM 	nMOS metal
	NM = 'NM'
	# NP 	nMOS polysilicon
	NP = 'NP'
	# ND 	nMOS diffusion
	ND = 'ND'
	# NC 	nMOS contact
	NC = 'NC'
	# NI 	nMOS implant
	NI = 'NI'
	# NB 	nMOS buried
	NB = 'NB'
	# NG 	nMOS overglass
	NG = 'NG'
	# CMF 	CMOS metal 1
	CMF = 'CMF'
	# CMS 	CMOS metal 2
	CMS = 'CMS'
	# CPG 	CMOS polysilicon
	CPG = 'CPG'
	# CAA 	CMOS active
	CAA = 'CAA'
	# CSG 	CMOS select
	CSG = 'CSG'
	# CWG 	CMOS well
	CWG = 'CWG'
	# CC 	CMOS contact
	CC = 'CC'
	# CVA 	CMOS via
	CVA = 'CVA'
	# COG 	CMOS overglass
	COG = 'COG'

	def __init__(self):
		self.boxes = list()
		self.id = None

	@staticmethod
	def str2id(s):
		# Simple mapping right now
		return s.upper()
	
	def add_box(self, width, height, xpos, ypos, rotation = None):
		box = Box(width, height, xpos, ypos, rotation)
		self.boxes.append(box)

class Statement:
	def __init__(self):
		pass

class Subroutine:
	def __init__(self):
		self.number = None
		# Strings, reparse every time
		self.statements = list()
		
		self.scale_numerator = None
		self.scale_denominator = None
		
	def add(self, statement):
		self.statements.append(statement)
		
	def call(self, parser):
		scalar = self.scale_numerator / self.scale_denominator
		for statement in self.statements:
			parser.parse_statement(statement, scalar)

class Label:
	def __init__(self, text = None, x = None, y = None, layer_id = None):
		self.x = x
		self.y = y
		self.text = text
		self.layer_id = layer_id

class Box:
	def __init__(self, width, height, xpos, ypos, rotation = None):
		if width == 0:
			raise Exception('0 width')
		if height == 0:
			raise Exception('0 height')
		self.width = width
		self.height = height
		self.xpos = xpos
		self.ypos = ypos
		self.rotation = rotation
		
class Parser:
	'''
	Initially created to parse 4003.cif
	Makes use of the following constructs:
	-(): comment
	-Layers
		-L ND: nMOS diffusion
		-L NP: nMOS poly
		-L NC: nMOS contact
		-L NM: nMOS metal
	-Procedural
		-DS: def start
		-DF def finish
		-C call def
	-B: box
	-9: Cell name
	-94: Label
	-E: end
	'''

	def __init__(self):
		global g_default_scalar
	
		# maximized for 4003 on 1680 X 1040 screen...
		# need to implement scrolling or something
		self.scalar = g_default_scalar
	
		#self.generator = None
		self.file_name = None
		# File object
		self.f = None
		self.cell_name = None

		# layer ID => layer object
		self.layers = dict()

		# Transform into more polygon friendly form
		self.corner_coordinates = True

		# number => object
		self.subroutines = dict()
		# Being parsed, not running
		self.cur_subroutine = None
		self.labels = list()
		self.active_layer = None
		
		# Figure these out as we go along
		self.width = 0
		self.height = 0

	def add_box(self, width, height, xpos, ypos, rotation = None):
		self.width = max(self.width, xpos + width)
		self.height = max(self.height, ypos + height)
		self.active_layer.add_box(width, height, xpos, ypos, rotation)

	def add_label(self, text, x, y, layer_id):
		self.width = max(self.width, x)
		self.height = max(self.height, y)
		
		l = Label(text, x, y, layer_id)
		self.labels.append(l)	
	
	@staticmethod	
	def parse(file_name):
		parser = Parser()
		#parser.generator = generator()
		parser.file_name = file_name
		parser.run()
		return parser
	
	def remove_comments(self, text):
		# ( CIF conversion of visual6502 polygon data );
		while True:
			start = text.find('(')
			if start < 0:
				break
			end = text.find(')')
			if end < 0:
				raise Exception('Malformed CIF: cannot locating ending ) on %s' % text)
			text = text[0:start] + text[end + 1:]
		#print 'filtered: ' + text
		return text
	
	def next_statement(self):
		ret = ''
		while True:
			c = self.f.read(1)
			if len(c) == 0:
				if len(ret) == 0:
					return None
				break
			if c == ';':
				break
			ret += c
		return self.remove_comments(ret).strip()
	
	def parse_statement(self, statement, scalar = None):
		'''Must be comment free and stripped of extra spaces.  Return True on end'''
		global box_limit
		global g_limit_polygon

		# Skip blanks
		if statement == '':
			return False
		if False:
			scalar = 1.0
			self.scalar = 1.0

		#print 'Parising %s' % statement
		
		parts = statement.split()
		key = parts[0].upper()
		
		print_orig = g_print_result
		
		if self.cur_subroutine:
			if key == "DF":
				if self.cur_subroutine is None:
					raise Exception('DF without DS')
				# Note that we correctly drop the old routine if unneeded
				self.subroutines[self.cur_subroutine.number] = self.cur_subroutine
				# Not sure if this is true, but it seems logical anyway
				self.active_layer = None
				self.cur_subroutine = None
				return False
			else:			
				self.cur_subroutine.add(statement)
				return False
		
		ret = False
		if key == "E":
			ret = True
		elif key == "L":
			layer_id = Layer.str2id(parts[1])
			# Hmm can you switch layers?  Probably
			if layer_id in self.layers:
				self.active_layer = self.layers[layer_id]
			else:
				self.active_layer = Layer()
				self.active_layer.id = layer_id
			 	self.layers[layer_id] = self.active_layer
		 	if BOX_MAX:
		 		box_limit = 0
		elif key == "C":
			'''
			Call a subroutine
			
			Syntax:
			C <number>
			'''
			self.subroutines[int(parts[1])].call(self)
			print_orig = False
		elif key == "DS":
			'''
			Define the start of a subroutine
			
			Syntax:
			DS <number> <scale numerator> <scale demon>
			'''
			subroutine = Subroutine()
			subroutine.number = int(parts[1])
			subroutine.scale_numerator = int(parts[2])
			subroutine.scale_denominator = int(parts[3])
			self.cur_subroutine = subroutine
			print_orig = False
		elif key == "B":
			print_orig = False
					
			if BOX_MAX:
				if box_limit == BOX_MAX:
					print 'Last accepted box: ' + repr(statement)
				if box_limit > BOX_MAX:
					return False
				box_limit += 1
			
			'''
			Syntax:	
			B <length> <width> <xpos> <ypos> [rotation] ;
			'''
			if self.active_layer is None:
				raise Exception('Must be in layer to use box')
			'''
			 B length width xpos ypos [rotation] ;
			a box the center of which is at (xpos, ypos) and is length across in x and width tall in y.
			
			However, I don't like dealing with that so I'm translating
			'''
			
			width_orig = int(parts[1])
			height_orig = int(parts[2])

			xpos_orig = int(parts[3])
			ypos_orig = int(parts[4])

			
			width = width_orig * self.scalar
			height = height_orig * self.scalar
			xpos = xpos_orig * self.scalar
			ypos = ypos_orig * self.scalar
		
			# Lambda design rules FTW
			if not scalar is None:
				xpos *= scalar
				ypos *= scalar
				width *= scalar
				height *= scalar
			
			xpos_corner = xpos - width / 2.0
			ypos_corner = ypos - height / 2.0
			
			perform_action = True
			if g_limit_polygon:
				feature_poly = UVPolygon.from_rect_ex(xpos_corner, ypos_corner, width, height)
				if not g_limit_polygon.intersects(feature_poly):
					perform_action = False
			if perform_action:			
				# Should truncate to int?  Don't do it unless it becomes a problem
				
				rotation = None
				if len(parts) >= 6:
					rotation = int(parts[5])
				
				if self.corner_coordinates:
					self.add_box(width, height, xpos_corner, ypos_corner, rotation)
				else:
					self.add_box(width, height, xpos, ypos, rotation)
					
				if g_print_result:
					rotation_str = ''
					if not rotation is None:
						rotation_str = ' %d' % rotation
					width_i = int(width)
					height_i = int(height)
					# Skip invalid geometries
					if not width_i == 0 and not height_i == 0:
						print 'B %d %d %d %d%s;' % (width_i, height_i, int(xpos + width / 2.0), int(ypos + height / 2.0), rotation_str)
		elif key == "9":
			'''
			Cell name
			
			Syntax:
			9 <text>
			
			Ignore, unused for now
			'''
			self.cell_name = statement[2:]
		elif key == "94":
			'''
			Label
			
			Syntax:
			94 <label token> <x> <y> [layer]
			'''
			text = parts[1]
			x = int(int(parts[2]) * self.scalar)
			y = int(int(parts[3]) * self.scalar)
			# Lambda design rules FTW
			if not scalar is None:
				x *= scalar
				y *= scalar

			layer_id = None
			if len(parts) >= 5:
				layer_str = parts[4]
				layer_id = layer_id = Layer.str2id(layer_str)
			self.add_label(text, x, y, layer_id)
			if g_print_result:
				print_orig = False
				layer_str = ''
				if not layer_id is None:
					printed_layer_str = ' %s' % layer_str
				print '94 %s %d %d%s;' % (text, x, y, printed_layer_str)
		else:
			raise Exception("Couldn't parse statement %s" % statement)

		if print_orig:
			print statement + ';'

		return ret
	
	def run(self):
		'''
		http://en.wikipedia.org/wiki/Caltech_Intermediate_Form
		
		
		0 x y layer N name; 	Set named node on specified layer and position
		0V x1 y1 x2 y2 ... xn yn; 	Draw vectors
		2A "msg" T x y; 	Place message above specified location
		2B "msg" T x y; 	Place message below specified location
		2C "msg" T x y; 	Place message centered at specified location
		2L "msg" T x y; 	Place message left of specified location
		2R "msg" T x y; 	Place message right of specified location
		4A lowx lowy highx highy; 	Declare cell boundary
		4B instancename; 	Attach instance name to cell
		4N signalname x y; 	Labels a signal at a location
		9 cellname; 	Declare cell name
		91 instancename; 	Attach instance name to cell
		94 label x y; 	Place label in specified location
			Need to support this to assign nets
		95 label length width x y; 	Place label in specified area
		FIGURE B.5 Typical user extensions to CIF.
		'''
		
		self.f = open(self.file_name, 'r')
		while True:
			l = self.next_statement()
			if l is None:
				break
			if self.parse_statement(l):
				break
			
		import sys
		#print 'Debug break'
		#sys.exit(1)

