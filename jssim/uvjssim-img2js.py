#! /usr/bin/env python
'''
Generate segdefs.js and transdefs.js from layer images

Really what I should do is svg2polygon

Algorithm
We require the following input images to get a simulatable result:
-Poly image
-Metal image
You should also give the following:
-Diffusion image
Optional:
-Labels image
	Currently unused

Output
transdefs.js
segdefs.js
Transistors image

For now assume all data is rectangular
Maybe use Inkscape .svg or 


'''

from pr0ntools.pimage import PImage
import sys
from layer import UVPolygon, Net, Nets, PolygonRenderer, Point


DEFAULT_IMAGE_EXTENSION = ".svg"
DEFAULT_IMAGE_FILE_METAL_VCC = "metal_vcc" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_METAL_GND = "metal_gnd" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_METAL = "metal" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_POLYSILICON = "polysilicon" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_DIFFUSION = "diffusion" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_VIAS = "vias" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_BURIED_CONTACTS = "buried_contacts" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_TRANSISTORS = "transistors" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_LABELS = "labels" + DEFAULT_IMAGE_EXTENSION

JS_FILE_TRANSDEFS = "transdefs.js"
JS_FILE_SEGDEFS = "segdefs.js"

'''
Are these x,y or y.x?
Where is the origin?
Assume visual6502 coordinate system
	Origin in lower left corner of screen
	(x, y)

 <polygon points="2601,2179 2603,2180 2603,2181 2604,2183" />
'''

from layer import Layer

class NodeName:
	def __init__(self, name=None, net=None):
		# string
		self.name = name
		# int
		self.net = net

	def run_DRC(self):
		pass
	
	def __repr__(self):
		# clk0: 4,
		return '%s: %u' % (self.name, self.net)

class NodeNames:
	def __init__(self):
		self.nodenames = list()
	
	def run_DRC(self):
		pass
		
	def __repr__(self):
		'''Return nodenames.js content'''

		'''
		var nodenames ={
		gnd: 2,
		vcc: 1,
		out1: 3,
		in1: 4,
		clk0: 4,
		}
		'''

		ret = ''
		ret += 'var nodenames = {\n'
		
		for nodename in self.nodenames:
			# Having , at end is acceptable
			ret += rep(nodename) + ',\n'
		
		ret += '}\n'
		return ret

	def write(self):
		f = open(JS_FILE_SEGDEFS, 'w')
		f.write(self.__repr__())
		f.close()

class Segdef:
	'''
	WARNING: needs coordinates in lower left, standard is upper left
	
	defines an array segdefs[], with a typical element 
	[4,'+',1,4351,8360,4351,8334,4317,8334,4317,8360], 
	giving the 
		node number, 
		the pullup status, 
		the layer index 
		and a list of coordinate pairs for a polygon. 
		There is one element for each polygon on the chip, and therefore generally several elements for each node. The pullup status can be '+' or '-' and should be consistent for all of a node's entries - it's an historical anomaly that this information is in segdefs. Not all chip layers or polygons appear in segdefs, but enough layers appear for an appealing and educational display. 

	Format:
	[ 
		[0]: w: net/node name.  Can also be special ngnd and npwr?,
			ngnd = nodenames['gnd'];
			npwr = nodenames['vcc'];
		[1]: '+' if pullup,
		[2]: layer number,
		[3+]: segs array
	'''
	def __init__(self, net=None, pullup=None, layer_index=None, coordinates=None):
		# TODO: move these checks to DRC
		
		# Integer value
		self.net = net
		# Character ('+' or '-')
		self.pullup = pullup
		# Integer
		self.layer_index = layer_index
		# Integer array (not float)
		self.coordinates = coordinates
		
		self.run_DRC()

	def run_DRC(self):
		if self.net is None:
			raise Exception('Require net')
		if not type(self.net) is int:
			print self.net
			raise Exception('Require net as int')
			
		if self.pullup is None:
			raise Exception('Require pullup')
		if not (self.pullup == '+' or self.pullup == '-'):
			raise Exception('Require pullup +/-, got ' + self.pullup)
			
		if self.layer_index is None:
			raise Exception('Require layer index')
		if not Layer.is_valid(self.layer_index):
			raise Exception('Invalid layer index ' + repr(self.layer_index))

		if self.coordinates is None:
			raise Exception('Require coordinates')
		if len(self.coordinates) % 2 is not 0:
			raise Exception('Require even number of coordinates, got ' + self.coordinates)
		# Technically you can have negative coordinates, but you shouldn't be using them
		for coordinate in self.coordinates:
			if coordinate < 0:
				raise Exception('Prefer positive coordinates, got ' + coordinate)

	def __repr__(self):
		ret = ''
		#print 'net: ' + repr(self.net)
		ret += "[%u,'%c',%u" % (self.net, self.pullup, self.layer_index)
		for coordinate in self.coordinates:
			ret += ',%u' % coordinate
		ret += ']'
		return ret
		
class Segdefs:
	def __init__(self):
		self.segdefs = list()
	
	def run_DRC(self):
		for segdef in self.segdefs:
			segdef.run_DRC()
		
	def __repr__(self):
		'''Return segdefs.js content'''
		'''
		Should be written in the following layer order:
		-1: diffusion
		-3: grounded diffusion
		-4: powered diffusion
		-5: poly
		-0: metal (semi transparent)
		
		Since only metal is semi-transparent, its probably the only one that needs to be ordered (last)
		None of the other polygons should overlap (sounds like a DRC)
		'''
		
		ret = ''
		ret += 'var segdefs = [\n'
		
		for segdef in self.segdefs:
			# Having , at end is acceptable
			ret += segdef.__repr__() + ',\n'
		
		ret += ']\n'
		return ret

	def write(self):
		f = open(JS_FILE_SEGDEFS, 'w')
		f.write(self.__repr__())
		f.close()
	
class Transdef:
	'''
	WARNING: needs coordinates in lower left, standard is upper left
	
	(Ijor's?) comment from 6800's transdefs:
	/*
	 * The format here is
	 *   name
	 *   gate,c1,c2
	 *   bb (bounding box: xmin, xmax, ymin, ymax)
	 *   geometry (unused) (width1, width2, length, #segments, area)
	 *   weak (boolean) (marks weak transistors, whether pullups or pass gates)
	 *
	 * Note: the geometry is of the MOSFET channel: the two widths are
	 * the lengths of the two edges where the poly is crossing the active
	 * area. These will be equal if the channel is straight or makes an
	 * equal number of right and left turns. The number of segments should
	 * be 1 for a rectangular channel, or 2 for an L shape, 3 for a Z
	 * or U, and will allow for taking into account corner effects.
	 * 
	 * At time of writing JSSim doesn't use transistor strength information
	 * except to discard weak transistors and to treat pullups as
	 * described in segdefs.js specially.
	 *
	 */
	'''
	
	def __init__(self, name=None, gate=None, c1=None, c2=None, bb=None, geometry=None, weak=None):
		# string
		self.name = name
		# int
		self.gate = gate
		# int
		self.c1 = c1
		# int
		self.c2 = c2
		# 4 element list
		self.bb = bb
		# list / structure
		self.geometry = geometry
		# boolean
		self.weak = weak
	
		self.run_DRC()
		
	def run_DRC(self):
		pass

	def __repr__(self):
		#['t1',4,2,3,[176,193,96,144],[415,415,11,5,4566],false],
		ret = '['
		ret += "'%s',%u,%u,%u" % (self.name, self.gate, self.c1, self.c2)
		ret += ",[%u,%u,%u,%u]" % (self.bb[0], self.bb[1], self.bb[2], self.bb[3])
		ret += ",[%u,%u,%u,%u,%u]" % (self.geometry[0], self.geometry[1], self.geometry[2], self.geometry[3], self.geometry[4])
		if self.weak:
			ret += ",true"
		else:
			ret += ",false"
		ret += ']'
		return ret
		
class Transdefs:
	def __init__(self):
		self.transdefs = list()

	def __repr__(self):
		ret = ''
		ret += 'var transdefs = [\n'
		
		for transdef in self.transdefs:
			# Having , at end is acceptable
			ret += repr(transdef) + ',\n'
			
		ret += ']\n'
		return ret
	
	def add(self, transdef):
		self.transdefs.append(transdef)
	
	def write(self):
		f = open(JS_FILE_TRANSDEFS, 'w')
		f.write(self.__repr__())
		f.close()
	
class Transistor:
	'''
	JSSim likes c1 more "interesting" than c2
	Try to make c1 be the variable connection and c2 constant if applicable
	'''
	
	def __init__(self, g=None, c1=None, c2=None):
		# These should be Net objects, not numbers
		# gate
		self.g = g
		# connection1
		self.c1 = c1
		# connection2
		self.c2 = c2
		
		# Rectangle (two Point's)
		self.rect_p1 = None
		self.rect_p2 = None
		self.weak = None
	
	def set_bb(self, point1, point2):
		self.rect_p1 = point1
		self.rect_p2 = point2

	def __repr__(self):
		return 'c1: %u, g: %u, c2: %u, weak: %s' % (self.c1.number, self.g.number, self.c2.number, repr(self.weak))
	
class Transistors:
	def __init__(self):
		# no particular order
		self.transistors = set()
	
	def add(self, transistor):
		self.transistors.add(transistor)

class UVJSSimGenerator:
	def __init__(self, src_images = None):
		if src_images == None:
			src_images = dict()
			src_images['metal_gnd'] = DEFAULT_IMAGE_FILE_METAL_GND
			src_images['metal_vcc'] = DEFAULT_IMAGE_FILE_METAL_VCC
			src_images['metal'] = DEFAULT_IMAGE_FILE_METAL
			src_images['polysilicon'] = DEFAULT_IMAGE_FILE_POLYSILICON
			src_images['diffusion'] = DEFAULT_IMAGE_FILE_DIFFUSION
			src_images['vias'] = DEFAULT_IMAGE_FILE_VIAS
			src_images['labels'] = DEFAULT_IMAGE_FILE_LABELS
		
		# visual6502 net numbers seem to start at 1, not 0
		self.min_net_number = 1
				
		self.transdefs = Transdefs()
		
		self.reset_net_number()
		
		# Validate sizes
		self.verify_layer_sizes(src_images.values())
	
		self.vias = Layer.from_svg(src_images['vias'])
		# Vias have no layer
		
		self.metal_gnd = Layer.from_svg(src_images['metal_gnd'])
		self.metal_gnd.potential = Net.GND
		self.metal_gnd.index = Layer.METAL
		
		self.metal_vcc = Layer.from_svg(src_images['metal_vcc'])
		self.metal_vcc.potential = Net.VCC
		self.metal_vcc.index = Layer.METAL
		
		self.metal = Layer.from_svg(src_images['metal'])
		self.metal.index = Layer.METAL
		
		self.metals = Layer.from_layers([self.metal_gnd, self.metal_vcc, self.metal], name='metals')

		self.polysilicon = Layer.from_svg(src_images['polysilicon'])
		self.polysilicon.index = Layer.POLYSILICON

		self.diffusion = Layer.from_svg(src_images['diffusion'])		
		#self.diffusion.index = Layer.UNKNOWN_DIFFUSION

		self.labels = Layer.from_svg(src_images['labels'])

		#self.buried_contacts = Layer(DEFAULT_IMAGE_FILE_BURIED_CONTACTS)
		#self.transistors = Layer(DEFAULT_IMAGE_FILE_TRANSISTORS)
		self.transistors = Transistors()

		self.layers = [self.polysilicon, self.diffusion, self.vias, self.metal_vcc, self.metal_gnd, self.metal]
		self.verify_layer_sizes_after_load()
		
		# net to set of polygons
		# Used for merging nets
		# number to net object
		self.nets = Nets()
		#self.polygon_nets = dict()
		
		self.vdd = None
		self.vss = None

	def reset_net_number(self):
		self.last_net = self.min_net_number - 1

	def verify_layer_sizes_after_load(self):
		self.width = self.metal.width
		self.height = self.metal.height
		#self.metal.show()
		
		for layer in self.layers:
			if layer.width != self.width:
				raise Exception('layer width mismatch')
			if layer.height != self.height:
				raise Exception('layer height mismatch')
	
	def verify_layer_sizes(self, images):
		width = None
		height = None
		reference_layer = None
		
		print images		

		# Image can't read SVG
		# We could read the width/height attr still though
		for a_image in images:
			if a_image.find('.svg') < 0:
				raise Exception('Require .svg files, got %s' % a_image )
		return
		
		for image_name in images:
			this_image = PImage.from_file(image_name)
			this_width = this_image.width()
			this_height = this_image.width()
			if width == None:
				width = this_width
				height = this_height
				reference_image = this_image
				continue
			if this_width != width or this_height != height:
				print '%s size (width=%u, height=%u) does not match %s size (width=%u, height=%u)' % \
						(reference_image.file_name(), width, height, \
						this_image.file_name(), this_width, this_height)
				raise Exception("Image size mismatch")
		
	# Visible polygons
	def gen_segdefs_polygons(self):
		'''Non-intersecting layers'''
		# Not preserving grounded/powered/regular order, fix later if needed
		for polygon in self.diffusion:
			yield polygon
		for polygon in self.polysilicon:
			yield polygon
		# Must be last
		for polygon in self.metals:
			yield polygon
			
	def run_DRC(self):
		'''run a design rule check'''
		self.run_polygon_overlap_DRC()
		
	def run_polygon_overlap_DRC(self):
		'''Certain layers should not overlap (no polygons in same layer'''
		return
		# Don't have metal / diffusion rule correct, these can overlap
		
		# Only a rough overlap check, there is a lot more we could do
		# Actually letting polygons overlap in same layer might not be so bad?
		# Maybe rule should be not on net matches
		# Note xintersection is only on layers
		# Self aligned silicon: diffuson and poly should not overlap
					
		# won't scale well, need quadtree maps or something
		for polygon1 in gen_polygons():
			for polygon2 in gen_polygons():
				# Provide some fudge factor if they have a multipolygon
				if polygon1.net == polygon2.net:
					continue
				if polygon1.intersects(polygon2, False):
					print 'polygon1: ' + polygon1 
					print 'polygon2: ' + polygon2
					raise Exception('Failed overlap DRC')
								
	# assign_nets callback
	def get_net(self):
		return Net(self.get_net_number())
	
	def get_net_number(self):
		self.last_net += 1
		return self.last_net
	
	def assign_nets(self):
		'''Assign a unique net to every polygon'''
		
		self.nets = Nets()
		for layer in self.layers:
			layer.assign_nets(self)
			# Record the newly assigned nets
			for polygon in layer.polygons:
				net = polygon.net
				self.nets.add(net)
				print 'post potential: %u' % polygon.net.potential
					
	def reassign_nets(self):
		'''
		The merge process will probably leave holes in the nets
		There are a number of strategies we could use to improve this time
		Let n = number of nets, p = number of polygons in a net (assume even distribution)
		
		Gap filling (minimum changes)
		dict is not sorted, but could sort (n log(n))
		Start at beginning and end of list
		Continue from beginning until get a hole, switch something from the end to the hole
		Depending on how many gaps we have, this reduces the o(n * p) portion since we don't have to reassign everything
		
		Reassign all
		Iterate through all keys and just reassign each as we see fit
		o(n * p) since we will reassign every polygon
		Simpliest to implement
		'''
		self.reset_net_number()
		old_nets = self.nets
		# Let Nets rebuild its net mapping by copying over to a new instance
		self.nets = Nets()
		for old_net_num in old_nets.nets:
			net = old_nets.nets[old_net_num]
			net.number = self.get_net_number()
			# But net knows nothing about polygons knowing about nets so we have to remap those
			for polygon in net.members:
				polygon.net = net
			self.nets.add(net)
			
			'''
			if net.potential == Net.VDD:
				self.vdd = net
			elif net.potential == Net.GND:
				self.vss = net
			'''
	
	def find_pullups(self):
		'''Find pullup transistors, mark net as pullup, and remove from transistor list'''
		# FIXME
		for transistor in self.transistors.transistors:
			pass
			#if transistor.c2 == Net.VDD and 
	
	def print_important_nets(self):
		for net_number in self.nets.nets:
			net = self.nets.nets[net_number]
			
			if net.potential == Net.VDD:
				self.vdd = net
			elif net.potential == Net.GND:
				self.vss = net

		print 'VDD: %u' % self.vdd.number
		print 'GND: %u' % self.vss.number
	
	def find_transistors(self):
		'''
		Find / connect transistors
		Note that these aren't actually connected so they aren't merged
		Instead we create the transdefs
		Assume for now (with a check) that each poly proximity diffusion (some are used as wiring) has two connections
		These will form the sides of the transistor and maybe can take the extremes of that area to form the transistor
		polygon
		
		Notice that any funky split polysilicon polygons won't be detected correctly
		Could match at the net level?
		Complicated if multi poly gates
		Use this until it breaks
		
		Low priority since harder and not really used in simulation
		''' 
		
		print 'Finding transistors...'
		print 'Poly polygons: %u' % len(self.polysilicon.polygons)
		print 'Diff polygons: %u' % len(self.diffusion.polygons)
		layeri = self.polysilicon.intersection(self.diffusion)
		#layeri.show()

		# [polysilicon polygon objecty] = diffusion set
		# Try to find the two diffusion to each poly
		candidates = dict()
		for polygon in layeri.polygons:
			# poly1 is polysilicon, poly2 diffusion
			polysilicon_polygon = polygon.poly1
			diffusion_polygon = polygon.poly2
			if polysilicon_polygon in candidates:
				s = candidates[polysilicon_polygon]
			else:
				s = set()
			s.add(diffusion_polygon)
			candidates[polysilicon_polygon] = s
			
		print '%u transistor candidates' % len(candidates)
		# Now create transistor objects for each valid transistor
		for polysilicon_polygon in candidates:
			diffusion_polygons = candidates[polysilicon_polygon]
			if len(diffusion_polygons) != 2:
				raise Exception("Unexpected number of diffusion polygons intersecting polysilicon polygon")
			# Merge should have already ran
			
			transistor = Transistor()
			transistor.g = polysilicon_polygon.net
			cs = list(diffusion_polygons)
			transistor.c1 = cs[0].net
			transistor.c2 = cs[1].net
			# Try to optimize connections to make pullup / pulldown easier to detect (JSSim will also want this)
			if transistor.c1.potential == Net.VDD or transistor.c1.potential == Net.GND:
				temp = transistor.c1
				transistor.c1 = transistor.c2
				transistor.c2 = temp
			
			# rough approximation hack assuming square...fix later
			# we need to truncate to the region inside the bound box
			# slightly better: take points from opposite ends of the intersection to make a rectangle, intersection with poly
			transistor.set_bb(polysilicon_polygon.points[0], polysilicon_polygon.points[2])
			
			'''
			Pullup if c1 is high and c2 is connected to g
			(weak and pullup are treated identically)
			'''
			self.print_important_nets()
			transistor.weak = transistor.c2.potential == Net.VDD and (transistor.c1 == transistor.g)
			print 'trans: ' + repr(transistor)
			print 'direct weak: ' + repr(transistor.weak)
			#if transistor.weak:
			#	raise Exception('weak')
			
			print 'Adding transistor'
			self.transistors.add(transistor)
	
	def all_layers(self):
		'''All polygon layers including virtual layers but not metadata layers'''
		return self.layers + [self.metals]

	def remove_polygon(self, polygon):
		# TODO: for now this is for poly merge and we won't get a zombie net
		# we may need to delete the net entirely at some point in the future
		self.nets[polygon.net.number].remove_member(polygon)
		# Invalidate references?
		# del polygon
		#print
		for layer in self.all_layers():
			print 'Checking ' + layer.name
			if polygon in layer.polygons:
				print '***Removing polygon from ' + layer.name
				#polygon.show('Removing')
				#layer.show('Before (%s)' % layer.name)
				layer.remove_polygon(polygon)
				#layer.show('After (%s)' % layer.name)
		#print

	def merge_polygons(self, layeri):
		# And now we must make a single polygon
		# poly1 will be the new polygon
		# we must keep track of successors or we lose merge info
		# union will only work on true intersection, we must work with the xplogyons?
		# actually we only care about overlap so no we don't
		# [old] = new
		successors = dict()
		
		#layeri.show()
		
		print
		print
		print
		#print 'Checking polygons for self merge...'
		for polygon in layeri.polygons:
			poly1 = polygon.poly1
			poly2 = polygon.poly2
			
			# Avoid merging against self (should be optimized out of intersection)
			if poly1 == poly2:
				raise Exception('equal early')
				
			# Only worry if the actual polygons overlap, not the xpolygons
			# Note that we can safely do this check on the original polygon and not the new polygon (if applicable)
			if not poly1.polygon.intersects(poly2.polygon):
				print 'Rejecting xpolygon only match'
				continue
			
			# May have been merged, figure out what polygon it currently belongs to
			while poly1 in successors:
				poly1 = successors[poly1]
			while poly2 in successors:
				poly2 = successors[poly2]
			
			#union = poly1.polygon.union(poly2.polygon)
			union = poly1.union(poly2)
			# nets should be identical since we should have done net merge before
			#union.show('Union of %u and %u' % (poly1.net.number, poly2.net.number))
			print 'union: ' + repr(union)
			# Replace poly1's polygon and get rid of poly2
			# We may have 
			if poly1 == poly2:
				raise Exception('equal late')
			successors[poly2] = poly1

			#poly1.show("pre poly1")
			poly1.set_polygon(union.polygon)			
			#poly1.show("tranformed poly1")
			#sys.exit(1)
			
			self.remove_polygon(poly2)
	
		if True:
			print 'Polygon intersections: %u' % len(layeri.polygons)
			print
			print 'metals:'
			print self.metals
			#self.metals.show()
			print
			
			print 'metals polygons: %u' % len(self.metals.polygons)
			if len(self.metals.polygons) != 4:
				print 'FAILED'
			#sys.exit(1)

	def merge_nets(self, layeri):
#		self.merge_nets_core(layeri, False)
		
#	def merge_nets_core(self, layeri, same_layer):
		'''
		At the beginning of this function we have computed intersections (layeri)
		but not yet started a marge
		
		For each intersection merge the two nets
		Arbitrarily favor the lower net,
		we will probably have to renumber anyway, but it could help debugging and could make generally more predictable
		'''


		# Merge each intersection
		
		# We may eliminate a net and won't be able to merge into without following what it became
		successors = dict()
		for polygon in layeri.polygons:
			# Since these are real polygons their nets get updated as part of the merge
			poly1 = polygon.poly1
			poly2 = polygon.poly2
			
			n1 = poly1.net
			n2 = poly2.net
			'''
			while n1 in successors:
				n1 = successors[n1]
			while n2 in successors:
				n2 = successors[n2]
			'''
			if n1 in successors:
				raise Exception('bad net')
			if n2 in successors:
				raise Exception('bad net')
			
			# But only if they weren't already merged
			if not n1 == n2:
				# Add them to the 
				new_net = n1
				old_net = n2
				
				# Net knows nothing of polygon so we must copy ourself
				for polygon in self.nets[old_net.number].members:
					polygon.net = new_net
				self.nets.merge(new_net.number, old_net.number)
				successors[old_net] = new_net
	def condense_polygons(self):
		'''Merge polygons on same layer if they intersect'''
		#return
		
		print
		print
		print

		#for polygon in self.metal.polygons:
		#	self.show_net(polygon.net.number)

		#for layer in self.layers:
		#self.metal.show()
		# FIXME: to simplify debugging
		for layer in [self.metal]:
		#for layer in [self.metals]:
			layeri = layer.intersection(layer)
			print layeri
			if False:
				layeri.show()
				sys.exit(1)
			# Electically connect them
			self.merge_nets(layeri)
			# and visually merge them
			self.merge_polygons(layeri)
		
		#for polygon in self.metal.polygons:
		#	self.show_net(polygon.net.number)
		#sys.exit(1)
		
	def merge_poly_vias_layers(self):		
		print 'Metal polygons: %u' % len(self.metals.polygons)
		print 'Poly polygons: %u' % len(self.polysilicon.polygons)
		print 'Vias polygons: %u' % len(self.vias.polygons)

		# Start with two 
		polysilicon_layeri = self.polysilicon.intersection(self.vias)
		#polysilicon_layeri.show()
		self.merge_nets(polysilicon_layeri)
				
	def merge_diffusion_vias_layers(self):
		'''
		Three way merge.  In order for it to be a connection we need:
		-Diffusion area
		-Metal area
		-Contact area
		All on the same area
		Although really we can merge metal and diffusion and contact and metal by themsleves, just not very useful
		'''
		
		# Find / connect transistors
		print 'Metal polygons: %u' % len(self.metals.polygons)
		print 'Diff polygons: %u' % len(self.diffusion.polygons)
		print 'Vias polygons: %u' % len(self.vias.polygons)

		# Start with two 
		diffusion_layeri = self.diffusion.intersection(self.vias)
		#diffusion_layeri.show()
		self.merge_nets(diffusion_layeri)
		
	def merge_metal_vias(self):
		metals_layeri = self.metals.intersection(self.vias)
		#metals_layeri.show()
		self.merge_nets(metals_layeri)

	def find_and_merge_nets(self):
		# Combine polygons at a net level on the same layer
		# Only needed if you have bad input polygons
		# Really would be better to pre-process input to combine them
		self.condense_polygons()
		
		# Note that you cannot have diffusion and poly, via is for one or the other		
		self.merge_metal_vias()
		# Connected poly to metal
		self.merge_poly_vias_layers()
		# Connect diffusion to metal
		self.merge_diffusion_vias_layers()
		
	def polygon_coordinates(self, polygon):
		ret = polygon.coordinates()
		for i in range(1, len(ret), 2):
			ret[i] = self.y2jssim(ret[i])
		return ret
		
	def build_segdefs(self):
		segdefs = Segdefs()
		# Everything that needs rendering
		# Not preserving grounded/powered/regular order, fix later if needed
		for polygon in self.diffusion.polygons:
			net = polygon.net
			
			pullup = net.get_pullup()
			
			print 'Diffusion net potential: %u' % net.potential
			if net.potential == Net.VDD:
				layer_index = Layer.POWERED_DIFFUSION
			elif net.potential == Net.GND:
				layer_index = Layer.GROUNDED_DIFFUSION
			# UNKNOWN, pullup, and pulldown all fit into this
			else:
				layer_index = Layer.DIFFUSION
				
			coordinates = self.polygon_coordinates(polygon)
				
			#print 'early ' + repr(net.number)
			segdef = Segdef(net.number, pullup, layer_index, coordinates)
			segdefs.segdefs.append(segdef)

		for polygon in self.polysilicon.polygons:
			net = polygon.net
			
			pullup = net.get_pullup()
						
			layer_index = Layer.POLYSILICON
				
			coordinates = self.polygon_coordinates(polygon)
				
			segdef = Segdef(net.number, pullup, layer_index, coordinates)
			segdefs.segdefs.append(segdef)
			
			
		# Must be last
		for polygon in self.metals.gen_polygons():
			
			net = polygon.net
			pullup = net.get_pullup()
						
			layer_index = Layer.METAL
				
			coordinates = self.polygon_coordinates(polygon)
				
			segdef = Segdef(net.number, pullup, layer_index, coordinates)
			segdefs.segdefs.append(segdef)
			
		print segdefs
		segdefs.write()
	
	def get_transistor_name(self):
		self.last_transistor_name_index += 1
		return 't%u' % self.last_transistor_name_index
	
	def reset_transistor_names(self):
		self.last_transistor_name_index = 0
	
	'''
	Coordinate system convention transforms
	'''
	def x2jssim(self, x):
		return int(x)
	def y2jssim(self, y):
		#return int(y)
		return self.height - int(y)
		
	def build_transdefs(self):
		'''
		Find poly with two intersecting diffusion areas
		This forms a transistor
		Crude algorithm not taking account distance or other factors
		''' 
		
		transdefs = Transdefs()
		self.reset_transistor_names()
		print 'Building transdefs for %u transistors...' % len(self.transistors.transistors)
		for transistor in self.transistors.transistors:
			name = self.get_transistor_name()
			gate = transistor.g.number
			c1 = transistor.c1.number
			c2 = transistor.c2.number
			
			
			# [xmin, xmax, ymin, ymax]
			x1 = int(transistor.rect_p1.x)
			x2 = int(transistor.rect_p2.x)
			xmin = min(x1, x2)
			xmax = max(x1, x2)
				
			# Convert from UL to LL corrdinates
			y1 = self.y2jssim(transistor.rect_p1.y)
			y2 = self.y2jssim(transistor.rect_p2.y)
			ymin = min(y1, y2)
			ymax = max(y1, y2)
			
			bb = (xmin, xmax, ymin, ymax)
			
			# RFU, completly ignored
			geometry = [0, 0, 0, 0, 0]
			weak = transistor.weak
			
			transdef = Transdef(name, gate, c1, c2, bb, geometry, weak)
			transdefs.add(transdef)
			
		print transdefs
		transdefs.write()

	def show_nets(self):
		for i in range(self.min_net_number, self.last_net + 1):
			self.show_net(i)

	def show_net(self, net_number):
		r = PolygonRenderer(title='Net %u' % net_number)
		for layer in self.layers:
			r.add_layer(layer)
		
		# draw over the original polygon
		for layer in self.layers:
			for polygon in layer.polygons:
				if polygon.net.number == net_number:
					r.add_polygon(polygon, 'blue')
		r.render()

	def run(self):
		# Loop until we can't combine nets
		iteration = 0
		
		#intersection = False
		#intersections = 0
		#iteration += 1
		
		#print 'Iteration %u' % iteration
		
		self.assign_nets()
		self.find_and_merge_nets()
		self.find_transistors()
		self.find_pullups()
		# Now make them linearly ordered
		self.reassign_nets()
		# This wasn't needed because we can figure it out during build
		#self.mark_diffusion()
		
		#print 'Nets: %u, expecting 4' % self.last_net
		#self.show_nets()
		#sys.exit(1)
		
		self.build_segdefs()
		self.build_transdefs()



		

		#print 'Iteration found %u intersections' % intersections
				
		#print 'intersection done'
		
		'''
		# Polygons we've already checked
		closed_list = set()
		# Yet to check
		open_list = set()
		for layer in self.layers:
			for polygon in layer.polygons:
				open_list.add(polygon)
		
		metal = Layer.from_layers([self.metal_gnd, self.metal_vcc, self.metal])
		
		
		
		# Assign some temporary net names
		# They will be re-assigned at end
		# All polygons now have a net, lets see if we can merge
		self.assign_nets()
		
		# Now start the merge process
		
		# If a transistor layer was not given,
		# find transistors by looking for poly crossing
		
		# Now figure 
		'''
		
def help():
	print "uvjssim-generate: generate JSSim files from images"
	print "Usage: uvjssim-generate"
	print "Input files:"
	print "\t%s" % DEFAULT_IMAGE_FILE_METAL_VCC
	print "\t%s" % DEFAULT_IMAGE_FILE_METAL_GND
	print "\t%s" % DEFAULT_IMAGE_FILE_METAL
	print "\t%s" % DEFAULT_IMAGE_FILE_POLYSILICON
	print "\t%s" % DEFAULT_IMAGE_FILE_DIFFUSION
	print "\t%s" % DEFAULT_IMAGE_FILE_VIAS
	print "\t%s (currently unused)" % DEFAULT_IMAGE_FILE_BURIED_CONTACTS
	print "Output files:"
	print "\t%s" % DEFAULT_IMAGE_FILE_TRANSISTORS
	print "\t%s" % JS_FILE_TRANSDEFS
	print "\t%s" % JS_FILE_SEGDEFS

if __name__ == "__main__":
	if len(sys.argv) > 1:
		help()
		sys.exit(1)

	gen = UVJSSimGenerator()
	gen.run()

