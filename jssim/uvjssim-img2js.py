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



TODO:
-Generate transistor polygons
-Compute pullups
-Remove pullups from transistors
-Give a .txt input file that specifies a point to node name
	(assumes each node has at least one unique spot which seems reasonable, there should be at least one via)
'''

from pr0ntools.pimage import PImage
import sys
from layer import UVPolygon, Net, Nets, PolygonRenderer


DEFAULT_IMAGE_EXTENSION = ".svg"
DEFAULT_IMAGE_FILE_METAL_VCC = "metal_vcc" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_METAL_GND = "metal_gnd" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_METAL = "metal" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_POLYSILICON = "polysilicon" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_DIFFUSION = "diffusion" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_VIAS = "vias" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_BURIED_CONTACTS = "buried_contacts" + DEFAULT_IMAGE_EXTENSION
DEFAULT_IMAGE_FILE_TRANSISTORS = "transistors" + DEFAULT_IMAGE_EXTENSION

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

class Segdef:
	'''
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
		print 'net: ' + repr(self.net)
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
			ret += transdef + ',\n'
			
		ret += ']\n'
		return ret
	
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
		# gate
		self.g = g
		# connection1
		self.c1 = c1
		# connection2
		self.c2 = c2
	
class Transistors:
	def __init__(self):
		# no particular order
		self.transistors = set()

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
		
		# visual6502 net numbers seem to start at 1, not 0
		self.min_net_number = 1
				
		self.transdefs = list()
		
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

		#self.buried_contacts = Layer(DEFAULT_IMAGE_FILE_BURIED_CONTACTS)
		#self.transistors = Layer(DEFAULT_IMAGE_FILE_TRANSISTORS)

		self.layers = [self.polysilicon, self.diffusion, self.vias, self.metal_vcc, self.metal_gnd, self.metal]
		
		# net to set of polygons
		# Used for merging nets
		# number to net object
		self.nets = Nets()
		#self.polygon_nets = dict()

	def reset_net_number(self):
		self.last_net = self.min_net_number - 1

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
	
	def find_transistors(self):
		'''
		Find / connect transistors
		Note that these aren't actually connected so they aren't merged
		Instead we create the transdefs
		Assume for now (with a check) that each poly proximity diffusion (some are used as wiring) has two connections
		These will form the sides of the transistor and maybe can take the extremes of that area to form the transistor
		polygon
		
		Low priority since harder and not really used in simulation
		''' 
		
		print 'Poly polygons: %u' % len(self.polysilicon.polygons)
		print 'Diff polygons: %u' % len(self.diffusion.polygons)
		layeri = self.polysilicon.intersection(self.diffusion)
		#layeri.show()
		
	def merge_nets(self, layeri):
		'''
		At the beginning of this function we have computed intersections (layeri)
		but not yet started a marge
		
		For each intersection merge the two nets
		Arbitrarily favor the lower net,
		we will probably have to renumber anyway, but it could help debugging and could make generally more predictable
		'''
		# Merge each intersection
		for polygon in layeri.polygons:
			poly1 = polygon.poly1
			poly2 = polygon.poly2
			
			# But only if they weren't already merged
			if not poly1.net == poly2.net:
				# Add them to the 
				new_net = poly1.net
				old_net = poly2.net
				
				# Net knows nothing of polygon so we must copy ourself
				for polygon in self.nets[old_net.number].members:
					polygon.net = new_net
				self.nets.merge(new_net.number, old_net.number)
						
	def condense_layers(self):
		'''Merge nets on same layer, needed if multiple polygons when could have done single'''
		for layer in self.layers:
			layeri = layer.intersection(layer)
			self.merge_nets(layeri)
		
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
		self.condense_layers()
		
		# Note that you cannot have diffusion and poly, via is for one or the other		
		self.merge_metal_vias()
		# Connected poly to metal
		self.merge_poly_vias_layers()
		# Connect diffusion to metal
		self.merge_diffusion_vias_layers()
		
	def find_pullups(self):
		'''Find pullup transistors, mark net as pullup, and remove from transistor list'''
		# FIXME
		pass
				
	def build_segdefs(self):
		segdefs = Segdefs()
		# Everything that needs rendering
		# Not preserving grounded/powered/regular order, fix later if needed
		for polygon in self.diffusion.polygons:
			net = polygon.net
			
			pullup = net.get_pullup()
						
			if net.potential == Net.VDD:
				layer_index = Layer.POWERED_DIFFUSION
			elif net.potential == Net.GND:
				layer_index = Layer.GROUNDED_DIFFUSION
			# UNKNOWN, pullup, and pulldown all fit into this
			else:
				layer_index = Layer.DIFFUSION
				
			coordinates = polygon.coordinates()
				
			print 'early ' + repr(net.number)
			segdef = Segdef(net.number, pullup, layer_index, coordinates)
			segdefs.segdefs.append(segdef)

		for polygon in self.polysilicon.polygons:
			net = polygon.net
			
			pullup = net.get_pullup()
						
			layer_index = Layer.POLYSILICON
				
			coordinates = polygon.coordinates()
				
			segdef = Segdef(net.number, pullup, layer_index, coordinates)
			segdefs.segdefs.append(segdef)
			
			
		# Must be last
		for polygon in self.metals.polygons:
			net = polygon.net
			pullup = net.get_pullup()
						
			layer_index = Layer.METAL
				
			coordinates = polygon.coordinates()
				
			segdef = Segdef(net.number, pullup, layer_index, coordinates)
			segdefs.segdefs.append(segdef)
			
		print segdefs
		segdefs.write()
	
	def build_transdefs(self):
		'''
		Find poly with two intersecting diffusion areas
		This forms a transistor
		Crude algorithm not taking account distance or other factors
		''' 
		
		transdefs = Transdefs()
		
		
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
		print 'Vaporware'
		
		# Loop until we can't combine nets
		iteration = 0
		
		#intersection = False
		#intersections = 0
		#iteration += 1
		
		#print 'Iteration %u' % iteration
		
		self.assign_nets()
		self.find_and_merge_nets()
		self.find_pullups()
		# Now make them linearly ordered
		self.reassign_nets()
		# This wasn't needed because we can figure it out during build
		#self.mark_diffusion()
		self.find_transistors()
		
		print 'Nets: %u, expecting 4' % self.last_net
		#self.show_nets()
		sys.exit(1)
		
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

