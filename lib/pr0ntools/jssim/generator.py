'''
This file is part of pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools.pimage import PImage
from pr0ntools.jssim.files.nodenames import *
from pr0ntools.jssim.files.segdefs import *
from pr0ntools.jssim.files.transdefs import *
from pr0ntools.jssim.layer import Layer
from pr0ntools.jssim.options import Options
from pr0ntools.jssim.transistor import *
import sys
from pr0ntools.jssim.layer import UVPolygon, Net, Nets, PolygonRenderer, Point

class Generator:
	def __init__(self, src_images = None):
		if src_images == None:
			src_images = dict()
			src_images['metal_gnd'] = Options.DEFAULT_IMAGE_FILE_METAL_GND
			src_images['metal_vcc'] = Options.DEFAULT_IMAGE_FILE_METAL_VCC
			src_images['metal'] = Options.DEFAULT_IMAGE_FILE_METAL
			src_images['polysilicon'] = Options.DEFAULT_IMAGE_FILE_POLYSILICON
			src_images['diffusion'] = Options.DEFAULT_IMAGE_FILE_DIFFUSION
			src_images['vias'] = Options.DEFAULT_IMAGE_FILE_VIAS
			src_images['labels'] = Options.DEFAULT_IMAGE_FILE_LABELS
		
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
		if Options.transistors_by_intersect:
			self.project_diffusion()
		#print 'Polygons: %d' % len(self.diffusion.polygons)
		#self.diffusion.show_polygons()
		#sys.exit(1)
		#self.diffusion.index = Layer.UNKNOWN_DIFFUSION

		self.labels = Layer.from_svg(src_images['labels'])

		#self.buried_contacts = Layer(Options.DEFAULT_IMAGE_FILE_BURIED_CONTACTS)
		#self.transistors = Layer(Options.DEFAULT_IMAGE_FILE_TRANSISTORS)
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
		for transistor in self.transistors.transistors:
			if not transistor.weak:
				continue
			# c1/g should be active and C2 on VCC
			if not transistor.c2.potential == Net.VDD:
				raise Exception('inconsistent state')
			if not transistor.c1 == transistor.g:
				raise Exception('inconsistent state')
			
			transistor.c1.pull_up()
	
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
		#print Options.transistors_by_adjacency
		#print Options.transistors_by_intersect
		#sys.exit(1)
		if Options.transistors_by_adjacency:
			self.find_transistors_by_adjacency()
		if Options.transistors_by_intersect:
			self.find_transistors_by_intersect()	
	
	def add_transistor(self, g_net, c1_net, c2_net, bb_polygon):
		'''Rejects transistor if already added'''
		
		print "***Adding transistor"
		
		transistor = Transistor()
		transistor.g = g_net
		transistor.c1 = c1_net
		transistor.c2 = c2_net
		# Try to optimize connections to make pullup / pulldown easier to detect (JSSim will also want this)
		if transistor.c1.potential == Net.VDD or transistor.c1.potential == Net.GND:
			temp = transistor.c1
			transistor.c1 = transistor.c2
			transistor.c2 = temp
	
		# rough approximation hack assuming square...fix later
		# we need to truncate to the region inside the bound box
		# slightly better: take points from opposite ends of the intersection to make a rectangle, intersection with poly
		transistor.set_bb(bb_polygon.get_points()[0], bb_polygon.get_points()[2])
	
		'''
		Pullup if c1 is high and c2 is connected to g
		(weak and pullup are treated identically)
		'''
		self.print_important_nets()
		# TODO: we assume only PMOS or NMOS
		# may need to adust this if using CMOS?
		print 'NMOS?: ' + repr(Options.technology.has_nmos())
		if Options.technology.has_nmos():
			print 'Potentials: c1: %d, g: %d, c2: %d' % (transistor.c1.potential, transistor.g.potential, transistor.c2.potential)
			print 'Nets: c1: %d, g: %d, c2: %d' % (transistor.c1.number, transistor.g.number, transistor.c2.number)
			# NMOS pullup has one node connected to high potential and other two tied together
			transistor.weak = transistor.c2.potential == Net.VDD and (transistor.c1 == transistor.g)
		if Options.technology.has_pmos():
			# PMOS pulldown has one node connected to low potential and other two tied together
			transistor.weak = transistor.c2.potential == Net.GND and (transistor.c1 == transistor.g)
		
		print 'trans: ' + repr(transistor)
		print 'direct weak: ' + repr(transistor.weak)
		#if transistor.weak:
		#	raise Exception('weak')
	
		print 'Adding transistor'
		self.transistors.add(transistor)
	
	def project_diffusion(self):
		# Save in case we want to reference it
		self.diffusion_original = self.diffusion
		#self.diffusion.show()
		#self.polysilicon.show()
		self.diffusioni = self.diffusion_original.subtract(self.polysilicon)
		self.diffusion = self.diffusioni.to_layer()		
		#self.diffusion.show()
		#sys.exit(1)
		
		# Find intersection with poly to form transistors
		# Require 2, some chips use diffusion for conduction to bypass metal
		# 4003 overlaps diffusion and poly because they split a contact across them
		
		# Subtract out the poly from diffusion
		# We can then use the same proximity algorithm as before
		# However, we will save intersections to get a better idea of correct transistor mapping
		
	def find_transistors_by_intersect(self):
		'''
		Some areas may contain overlapping diffusion and poly with a contact
		This does not form a transistor, simply a way of connecting
		So, a match must have 
		
		Assume that we have a diffusion intersection
		(offloaded the work from this function to earlier on)
		'''
		self.find_transistors_by_adjacency()
		
		# TODO
		# Now fixup with the improved transistor coordinates
		
	def find_transistors_by_adjacency(self):
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
		layeri = self.polysilicon.intersection(self.diffusion, True)
		#layeri.show()
		#sys.exit(1)

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
				print 'Diff polygons: %d' % len(diffusion_polygons)
				raise Exception("Unexpected number of diffusion polygons intersecting polysilicon polygon")
			# Merge should have already ran
			
			cs = list(diffusion_polygons)
			self.add_transistor(polysilicon_polygon.net, cs[0].net, cs[1].net, polysilicon_polygon)
			
			
			
	
	def all_layers(self):
		'''All polygon layers including virtual layers but not metadata layers'''
		return self.layers + [self.metals]

	def remove_polygon(self, polygon):
		net = self.nets[polygon.net.number]
		net.remove_member(polygon)
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
		if len(net.members) == 0:
			# ZOMBIE!!!  No more references
			# Kill it
			nets.remove(net)

	def merge_polygons(self, layeri):
		'''
		And now we must make a single polygon
			IF we can make a single non-enclosed polygon
			JSSim can only handle non-enclosed polygons
			I'm not sure if its easier to enhance JSSim or carefully combine here
			More than likely its better to avoid combining on compatibility grounds
		
		poly1 will be the new polygon
		we must keep track of successors or we lose merge info
		union will only work on true intersection, we must work with the xplogyons?
		actually we only care about overlap so no we don't
		'''
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
		
		#layeri.show()

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
	
	def verify_net_index(self):
		'''
		Check that the net numbers in polygon objects lines up with the net numbers in the nets object
		'''
		# Make a copy of net sets
		net_polys = dict()
		for net in self.nets.nets:
			net_polys[net] = set(self.nets[net].members)
		
		# Now take them out of nets
		for layer in self.layers:
			for polygon in layer.polygons:
				net_n = polygon.net.number
				if net_n in net_polys:
					# Net exists
					if not polygon in net_polys[net_n]:
						raise Exception('Polygon thinks it belongs to net %d but nets index does not' % net)
				else:
					print 'Dead'
					sys.exit(1)
					raise Exception("Polygon has inexistent net %d" % net_n)
	
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
			layeri = layer.intersection(layer, True)
			print layeri
			if False:
				layeri.show()
				sys.exit(1)
			# Electically connect them
			self.merge_nets(layeri)
			# and visually merge them
			self.merge_polygons(layeri)
		
		print
		print 
		print
		for net in self.nets.nets:
			print net
			print self.nets[net].members
		#self.show_nets()
		#sys.exit(1)
		
		
		#for polygon in self.metal.polygons:
		#	self.show_net(polygon.net.number)
		#sys.exit(1)
		
	def merge_poly_vias_layers(self):		
		print 'Metal polygons: %u' % len(self.metals.polygons)
		print 'Poly polygons: %u' % len(self.polysilicon.polygons)
		print 'Vias polygons: %u' % len(self.vias.polygons)

		# Start with two 
		polysilicon_layeri = self.polysilicon.intersection(self.vias, True)
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

		#self.diffusion.show()
		#self.vias.show()

		# Start with two 
		diffusion_layeri = self.diffusion.intersection(self.vias, True)
		#diffusion_layeri.show()
		self.merge_nets(diffusion_layeri)
		
		
		#sys.exit(1)
		
	def merge_metal_vias(self):
		metals_layeri = self.metals.intersection(self.vias, True)
		#metals_layeri.show()
		self.merge_nets(metals_layeri)

	def via_check(self, min_connections):
		'''
		All vias should have connected to metal and either poly or diffusion
		Including the via, need 3 polygons minimum
		'''
		checked = set()
		for polygon in self.vias.polygons:
			net = polygon.net
			if net in checked:
				continue
			checked.add(net)
			print 'Via poly count for net %d: %d' % (net.number, len(net.members))
			if len(net.members) < min_connections:
				msg = 'Non-sensical via, require %d connections, got %d' % (min_connections, len(net.members))
				print 'ERROR: ' + msg
				polygon.show()
				self.show_nets()
				raise Exception(msg)
		

	def find_and_merge_nets(self):
		# Combine polygons at a net level on the same layer
		# Only needed if you have bad input polygons
		# Really would be better to pre-process input to combine them
		self.condense_polygons()
		print 'Polygons condensed'
		#self.show_nets()
		self.verify_net_index()
		
		# Note that you cannot have diffusion and poly, via is for one or the other		
		self.merge_metal_vias()
		print 'Metal and vias merged'
		#self.show_nets()
		#self.verify_net_index()
		#sys.exit(1)
		
		self.via_check(2)
		
		# Connected poly to metal
		
		self.merge_poly_vias_layers()
		print 'Poly and vias merged'
		#self.show_nets()
		self.verify_net_index()
		
		# Connect diffusion to metal
		print 'Diffusion and vias merged'
		self.merge_diffusion_vias_layers()
		#self.show_nets()
		self.verify_net_index()
		
		self.via_check(3)
		
		#self.show_nets()
		
		print 'Finished merge'
		#sys.exit(1)
		
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
		
	def build_nodenames(self):
		nodenames = NodeNames()
		for net_number in self.nets.nets:
			net = self.nets[net_number]
			for name in net.names:
				nodename = NodeName(name, net_number)
				nodenames.add(nodename)
		nodenames.run_DRC()

		print nodenames
		nodenames.write()

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

	def gen_conductive_polygons(self):
		for layer in self.conductive_layers():
			for polygon in layer.polygons:
				yield polygon
	
	def conductive_layers(self):
		return list([self.polysilicon, self.diffusion, self.metal_vcc, self.metal_gnd, self.metal])

	def assign_node_names(self):
		'''Assign labels to nets by looking at label text box intersection with conductive areas'''
		# Try to match up each label
		# keep look after a match to look for collisions
		print 'labels: ' + repr(self.labels.__class__)
		print self.labels.polygons
		#Layer.show_layers(self.conductive_layers() + [self.labels])
		for label_polygon in self.labels.polygons:
			net_name = label_polygon.text
			matched = False
			#if net_name == 'vcc':
			#	label_polygon.show()
			for polygon in self.gen_conductive_polygons():
				if net_name == 'vcc':
					#UVPolygon.show_polygons([label_polygon, polygon])
					'''
					intersection = label_polygon.intersection(polygon)
					if intersection:
						intersection.show()
					else:
					'''
					pass
				if not label_polygon.intersects(polygon):
					continue
				# A match!
				matched = True
				net = polygon.net
				'''
				if net.name and not net.name == net_name:
					print 'old name: %s' % net.name
					print 'new name: %s' % net_name
					raise Exception('Net already named something different')
				'''
				net.add_name(net_name)
			if not matched:
				raise Exception('Could not assign net name ' + net_name)
		
	def show_nets(self):
		for i in self.nets.nets:
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
		
		#sys.exit(1)
		
		# Now make them linearly ordered
		self.reassign_nets()
		self.assign_node_names()
		# This wasn't needed because we can figure it out during build
		#self.mark_diffusion()
		
		#print 'Nets: %u, expecting 4' % self.last_net
		#self.show_nets()
		#sys.exit(1)
		
		self.build_segdefs()
		self.build_transdefs()
		self.build_nodenames()



		

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

