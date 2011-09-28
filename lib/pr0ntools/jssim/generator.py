'''
This file is part of pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
What about negative coordinates?
CIF and other formats seem to support these
'''

from pr0ntools.benchmark import Benchmark
from pr0ntools.pimage import PImage
from pr0ntools.jssim.files.nodenames import *
from pr0ntools.jssim.files.segdefs import *
from pr0ntools.jssim.files.transdefs import *
from pr0ntools.jssim.layer import Layer
from pr0ntools.jssim.options import Options
from pr0ntools.jssim.transistor import *
from pr0ntools.jssim.cif.parser import Parser as CIFParser
from pr0ntools.jssim.cif.parser import Layer as CIFLayer
import sys
from pr0ntools.jssim.layer import UVPolygon, Net, Nets, PolygonRenderer, Point

from pr0ntools.jssim.util import set_debug_width, set_debug_height

if False:
	clip_x_min = 250
	clip_x_max = 360
	clip_y_min = 150
	clip_y_max = 250
	clip_poly = UVPolygon.from_rect_ex(clip_x_min, clip_y_min, clip_x_max - clip_x_min + 1, clip_y_max - clip_y_min + 1)
	clip_poly.color = 'white'
else:
	clip_poly = False

class Generator:
	def __init__(self):
		self.vias = None
		self.metal_gnd = None
		self.metal_vcc = None
		self.metal = None
		self.polysilicon = None
		self.diffusion = None
		self.labels = None
	
	@staticmethod
	def from_qt_images(src_images = None):
		g = Generator()
		g.from_qt_images_init(src_images)
		return g
	
	def from_qt_images_init(self, src_images = None):
		if src_images == None:
			src_images = dict()
			src_images['metal_gnd'] = Options.DEFAULT_IMAGE_FILE_METAL_GND
			src_images['metal_vcc'] = Options.DEFAULT_IMAGE_FILE_METAL_VCC
			src_images['metal'] = Options.DEFAULT_IMAGE_FILE_METAL
			src_images['polysilicon'] = Options.DEFAULT_IMAGE_FILE_POLYSILICON
			src_images['diffusion'] = Options.DEFAULT_IMAGE_FILE_DIFFUSION
			src_images['vias'] = Options.DEFAULT_IMAGE_FILE_VIAS
			src_images['labels'] = Options.DEFAULT_IMAGE_FILE_LABELS
		
		# Validate sizes
		self.verify_layer_sizes(src_images.values())
	
		self.vias = Layer.from_svg(src_images['vias'])
		self.metal_gnd = Layer.from_svg(src_images['metal_gnd'])
		self.metal_vcc = Layer.from_svg(src_images['metal_vcc'])
		self.metal = Layer.from_svg(src_images['metal'])
		print self.metal.width
		self.polysilicon = Layer.from_svg(src_images['polysilicon'])
		self.diffusion = Layer.from_svg(src_images['diffusion'])		
		self.labels = Layer.from_svg(src_images['labels'])

		self.init()
	
	@staticmethod
	def from_cif(file_name = "in.cif"):
		g = Generator()
		g.from_cif_init(file_name)
		return g
		
	def default_layer_names(self):
		if not self.vias.name:
			self.vias.name = 'vias'
		if not self.metal.name:
			self.metal.name = 'metal'
		if not self.polysilicon.name:
			self.polysilicon.name = 'polysilicon'
		if not self.diffusion.name:
			self.diffusion.name = 'diffusion'
		if not self.labels.name:
			self.labels.name = 'labels'
	
	def from_cif_init(self, file_name = "in.cif"):
		self.vias = Layer()
		self.metal = Layer()
		self.polysilicon = Layer()
		self.diffusion = Layer()
		self.labels = Layer()
		self.metal_gnd = None
		self.metal_vcc = None
		self.default_layer_names()
		
		parsed = CIFParser.parse(file_name)
		
		print 'CIF width: %d' % parsed.width
		print 'CIF height: %d' % parsed.height
		
		self.rebuild_layer_lists(False)
		# Make sizes the furthest point found
		for layer in self.layers + [self.labels]:
			#print 'Setting %s to %s' % (layer.name, parsed.width)
			layer.width = parsed.width
			layer.height = parsed.height
		
		def add_cif_polygons(uv_layer, cif_layer):
			print '%s: adding %d boxes' % (uv_layer.name, len(cif_layer.boxes)) 
			for box in cif_layer.boxes:
				'''
				CIF uses lower left coordinate system
				Convert to internal representation, upper left
				
				UL
					Vertical
						B 22 94 787 2735
					Horizontal
						B 116 22 740 2793
				'''
				#print '.',
				if False:
					print 'start'
					print box.xpos
					print box.ypos
					print box.width
					print box.height
				# FIXME: change this into one operation since this now takes non-negligible amount of time
				#uvp = UVPolygon.from_rect(box.xpos, box.ypos, box.width, box.height)
				uvp = UVPolygon.from_rect_ex(box.xpos, box.ypos, box.width, box.height, flip_height = uv_layer.height)
				if False:
					print uvp
					uvp.show()
				#uvp.flip_horizontal(uv_layer.height)
				#print uvp
				#uvp.show()
				uv_layer.add_uvpolygon(uvp)
				#sys.exit(1)
			# uv_layer.show()
			#sys.exit(1)
			
		print 'Width: %d, height: %d' % (parsed.width, parsed.height)
		print 'Parsed labels: %d' % len(parsed.labels)
		for label in parsed.labels:
			# Make it a smallish object
			# Really 1 pix should be fine...but I'm more afraid of corner cases breaking things
			# Get it working first and then debug corner cases if needed
			# Maybe length should be related to text length
			uvpoly = UVPolygon.from_rect_ex(label.x, label.y, 20, 20, flip_height = parsed.height)
			uvpoly.text = label.text
			print uvpoly 
			#uvpoly.show()
			self.labels.add_uvpolygon(uvpoly)
		#self.labels.show()
		#sys.exit(1)
				
		for layer_id in parsed.layers:
			layer = parsed.layers[layer_id]
			bench = Benchmark()
			# NMOS metal
			if layer_id == CIFLayer.NM:
				add_cif_polygons(self.metal, layer)
			# NMOS poly
			elif layer_id == CIFLayer.NP:
				add_cif_polygons(self.polysilicon, layer)
			# NMOS diffusion
			elif layer_id == CIFLayer.ND:
				add_cif_polygons(self.diffusion, layer)
			# NMOS contact
			elif layer_id == CIFLayer.NC:
				add_cif_polygons(self.vias, layer)
			else:
				raise Exception('Unsupported layer type %s' % repr(layer_id))
			print bench
			
		#self.compute_wh()
		self.init()
	
	def compute_wh(self):
		'''Some formats such as CIF don't embed width/height.  Instead we have to standardize on some computed value'''
		width = 0
		height = 0
		
		# Find the highest width/height
		for layer in self.layers:
			layer.compute_wh()
			width = max(width, layer.width)
			height = max(height, layer.height)
		
		# Should be maxed out, normalize
		for layer in self.layers:
			layer.width = width
			layer.height = height

	
	def rebuild_layer_lists(self, complete = True):
		self.layers = list()
		self.layers.append(self.polysilicon)
		self.layers.append(self.diffusion)
		self.layers.append(self.vias)
		
		self.layers.append(self.metal)
		if self.metal_vcc:
			self.layers.append(self.metal_vcc)
		if self.metal_gnd:
			self.layers.append(self.metal_gnd)

	def color_layers(self):
		if not self.metal.color:
			self.metal.set_color('blue')
		if self.metal_gnd and not self.metal_gnd.color:
			self.metal_gnd.set_color('blue')
		if self.metal_vcc and not self.metal_vcc.color:
			self.metal_vcc.set_color('blue')
		
		if not self.polysilicon.color:
			self.polysilicon.set_color('red')
		if not self.diffusion.color:
			self.diffusion.set_color('green')
		if not self.vias.color:
			self.vias.set_color('black')
	
	def clip(self):
		global clip_poly
		if not clip_poly:
			return
			
		for layer in self.layers:
		#for layer in [self.diffusion]:
			layer.keep_intersecting(clip_poly)
			#layer.add_uvpolygon_begin(clip_poly)
			#layer.show()
			#clip_poly.show()
	
	def init(self):
		set_debug_width(self.metal.width)
		set_debug_height(self.metal.height)
		#print g_width, g_height
		#sys.exit(1)
	
		self.default_layer_names()
	
		# Clip as early as possible to avoid extra operations
		self.clip()
		
		self.color_layers()
	
		self.metal.index = Layer.METAL
		
		if self.metal_gnd:
			self.metal_gnd.potential = Net.GND
			self.metal_gnd.index = Layer.METAL
		if self.metal_vcc:
			self.metal_vcc.potential = Net.VCC
			self.metal_vcc.index = Layer.METAL
		
		self.polysilicon.index = Layer.POLYSILICON
		
		# visual6502 net numbers seem to start at 1, not 0
		self.min_net_number = 1
				
		self.transdefs = Transdefs()
		
		self.reset_net_number()
		# Skip some checks before nets are setup, but make the reference availible
		self.nets = None
		#self.polygon_nets = dict()
		self.remove_polygon = self.remove_polygon_no_nets
		
		self.vdd = None
		self.vss = None
		
		# Deals with small non-intersecting delta issues, but does distort the result
		print 'Enlarging layers...'
		bench = Benchmark()
		for layer in self.layers:
			layer.enlarge(None, 1.0)
		print 'Layers enlarged in %s' % repr(bench)
		
		# Must be done before projrection or can result in complex geometries
		# Well you can still get them, but its much easier if you don't do this first
		bench = Benchmark()
		self.condense_polygons()
		print 'Polygons condensed in %s' % repr(bench)

		# net to set of polygons
		# Used for merging nets
		# number to net object
		self.nets = Nets()
		self.remove_polygon = self.remove_polygon_regular
		
		if Options.transistors_by_intersect:
			self.project_diffusion()
		#print 'Polygons: %d' % len(self.diffusion.polygons)
		#self.diffusion.show_polygons()
		#sys.exit(1)
		#self.diffusion.index = Layer.UNKNOWN_DIFFUSION


		#self.buried_contacts = Layer(Options.DEFAULT_IMAGE_FILE_BURIED_CONTACTS)
		#self.transistors = Layer(Options.DEFAULT_IMAGE_FILE_TRANSISTORS)
		self.transistors = Transistors()
		
		self.rebuild_layer_lists()
		
		self.verify_layer_sizes_after_load()
		
		for layer in self.layers:
			layer.show()
		
	def reset_net_number(self):
		self.last_net = self.min_net_number - 1

	def verify_layer_sizes_after_load(self):
		self.width = self.metal.width
		self.height = self.metal.height
		#self.metal.show()
		
		for layer in self.layers:
			if layer.width != self.width:
				print 'Expected width %d, layer (%s): %d' % (self.width, layer.name, layer.width)
				raise Exception('layer width mismatch')
			if layer.height != self.height:
				print 'Expected height %d, layer (%s): %d' % (self.width, layer.name, layer.height)
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
		for polygon in self.get_metal():
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
				#print 'post potential: %u' % polygon.net.potential
					
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
		#if transistor.weak:uv_polygon_list(
		#	raise Exception('weak')
	
		print 'Adding transistor'
		self.transistors.add(transistor)
	
	def project_diffusion(self):
		print 'Projecting diffusion...'
		bench = Benchmark()
		start_polygons = len(self.diffusion.polygons)
		# Save in case we want to reference it
		self.diffusion_original = self.diffusion
		if False:
			self.diffusion.show()
			self.polysilicon.show()
		
		#self.diffusioni = self.diffusion_original.subtract(self.polysilicon)
		#self.diffusion = self.diffusioni.to_layer()		
		
		self.diffusion = self.diffusion_original.subtract(self.polysilicon)
		
		# Find intersection with poly to form transistors
		# Require 2, some chips use diffusion for conduction to bypass metal
		# 4003 overlaps diffusion and poly because they split a contact across them
		
		# Subtract out the poly from diffusion
		# We can then use the same proximity algorithm as before
		# However, we will save intersections to get a better idea of correct transistor mapping
		end_polygons = len(self.diffusion.polygons)
		print 'Projected diffusion %d => %d polygons in %s' % (start_polygons, end_polygons, repr(bench))
		
		if False:
			self.diffusion.show()
			#self.polysilicon.show()
			#self.diffusion_original.show()
			sys.exit(1)
		
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
				for diff_polygon in diffusion_polygons:
					print diff_polygon
					#diff_polygon.show()
				raise Exception("Unexpected number of diffusion polygons intersecting polysilicon polygon")
			# Merge should have already ran
			
			cs = list(diffusion_polygons)
			self.add_transistor(polysilicon_polygon.net, cs[0].net, cs[1].net, polysilicon_polygon)
			
			
			
	
	def all_layers(self):
		'''All polygon layers including virtual layers but not metadata layers'''
		return self.layers + self.get_metals()

	def remove_polygon_no_nets(self, polygon):
		'''Intended to be used for early condensing before nets are established'''
		for layer in self.all_layers():
			if polygon in layer.polygons:
				layer.remove_polygon(polygon)
			
	def remove_polygon_regular(self, polygon):
		net = self.nets[polygon.net.number]
		net.remove_member(polygon)
		# Invalidate references?
		# del polygon
		#print
		for layer in self.all_layers():
			#print 'Checking ' + layer.name
			if polygon in layer.polygons:
				#print '***Removing polygon from ' + layer.name
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
		if layeri.layer1 is not layeri.layer2:
			raise Exception('Can only merge against own layer')
		total_loops = len(layeri.polygons)
		begin_polygons = len(layeri.layer1.polygons)
		print 'Merging %s/%s %d intersections from %d polygons...' % (layeri.layer1.name, layeri.layer2.name, total_loops, begin_polygons)
		loops = 0
		for polygon in layeri.polygons:
			if loops % (total_loops / 10) == 0:
				print 'loops: %d / %d (%0.2f %%)' % (loops, total_loops, 100.0 * loops / total_loops)
			loops += 1
			
			poly1 = polygon.poly1
			poly2 = polygon.poly2
			
			# Avoid merging against self (should be optimized out of intersection)
			if poly1 == poly2:
				raise Exception('equal early')
				
			# May have been merged, figure out what polygon it currently belongs to
			while poly1 in successors:
				poly1 = successors[poly1]
			while poly2 in successors:
				poly2 = successors[poly2]
			# We may have already replaced?
			if poly1 == poly2:
				continue
				print
				print successors
				print
				print poly1
				raise Exception('equal late')
			
			# Only worry if the actual polygons overlap, not the xpolygons
			# Note that we can safely do this check on the original polygon and not the new polygon (if applicable)
			'''
			FIXME: refine this
			this was because we would have a gap which wouldn't quite work?
			Could try envolope, although if we are doing xpolygon it doesn't make sense to just later throw it out
			'''
			if not poly1.polygon.intersects(poly2.polygon):
				print 'Rejecting xpolygon only match'
				continue
			
			#union = poly1.polygon.union(poly2.polygon)
			union = poly1.union(poly2)
			# Hmm not sure why this happens
			if union.polygon.geom_type == 'MultiPolygon':
				print
				print
				print
				print 'unexpected multipolygon'
				print 'poly1: ' + repr(poly1)
				print 'poly2: ' + repr(poly2)
				print 'union: ' + repr(union.polygon)
				'''
				FIXME: not sure why this happens
				Maybe zero area segments?
				poly1: <polygon points="1084,621, 1087,621, 1087,614, 1061,614, 1061,614, 1060,614, 1060,623, 1061,623, 1061,622, 1084,622" />
				poly2: <polygon points="1061,623, 1083,623, 1083,623, 1061,623" />
				'''
				continue
				poly1.show()
				poly2.show()
				Layer.from_sl_multi(union.polygon).show()
				print 'unexpected multipolygon'
				sys.exit(1)
			# nets should be identical since we should have done net merge before
			#union.show('Union of %u and %u' % (poly1.net.number, poly2.net.number))
			#print 'union: ' + repr(union)
			successors[poly2] = poly1

			# Replace poly1's polygon and get rid of poly2
			#poly1.show("pre poly1")
			poly1.set_polygon(union.polygon)			
			#poly1.show("tranformed poly1")
			#sys.exit(1)
			
			self.remove_polygon(poly2)
	
		end_polygons = len(layeri.layer1.polygons)
		print 'Merged from %d => %d polygons' % (begin_polygons, end_polygons)
		if False:
			print 'Polygon intersections: %u' % len(layeri.polygons)
			print
			print 'metals:'
			print self.get_metal()
			#self.get_metal().show()
			print
			
			print 'metals polygons: %u' % len(self.get_metal().polygons)
			if len(self.get_metal().polygons) != 4:
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
		print 'Condensing polygons...'

		#for polygon in self.metal.polygons:
		#	self.show_net(polygon.net.number)

		#for layer in self.layers:
		#self.metal.show()
		# FIXME: to simplify debugging
		# Should relaly be all visible or conductive layers
		layer_number = 0
		for layer in self.layers:
		#for layer in [self.get_metal()]:
		#for layer in self.visible_layers():
			layer_number += 1
			before_count = len(layer.polygons)
			print "Condensing %s's %d polygons (%d / %d)..." % (layer.name, before_count, layer_number, len(self.layers))
			layeri = layer.intersection(layer, True)
			#print layeri
			if False:
				layeri.show()
				sys.exit(1)
			# Electically connect them
			self.merge_nets(layeri)
			# and geometrically merge them
			self.merge_polygons(layeri)
			after_count = len(layer.polygons)
			print 'Condensed %d => %d' % (before_count, after_count)
			if False:
				for polygon in layer.polygons:
					polygon.show()
				layer.show()
				sys.exit(1)
		
		if False:
			for layer in self.layers:
				layer.show()
			sys.exit(1)
		
		if False:
			print
			print 
			print
			for net in self.nets.nets:
				print net
				print self.nets[net].members
		#self.show_nets()
		#sys.exit(1)
		
		#self.metal.show_polygons()
		#sys.exit(1)
		
		#for polygon in self.metal.polygons:
		#	self.show_net(polygon.net.number)
		#self.show_nets()
		#sys.exit(1)
		
	def merge_poly_vias_layers(self):		
		print 'Metal polygons: %u' % len(self.get_metal().polygons)
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
		print 'Metal polygons: %u' % len(self.get_metal().polygons)
		print 'Diff polygons: %u' % len(self.diffusion.polygons)
		print 'Vias polygons: %u' % len(self.vias.polygons)

		#self.diffusion.show()
		#self.vias.show()

		# Start with two 
		diffusion_layeri = self.diffusion.intersection(self.vias, True)
		#diffusion_layeri.show()
		self.merge_nets(diffusion_layeri)
		
		
		#sys.exit(1)
		
	def get_metals(self):
		metal_layers = list()
	
		metal_layers.append(self.metal)
		if self.metal_gnd:
			metal_layers.append(self.metal_gnd)
		if self.metal_vcc:
			metal_layers.append(self.metal_vcc)
		return metal_layers
		
	def get_metal(self):
		# Rebuild every time for now instead of managing invalidations
		# Relativly quick compared to (I think) number of times needed
		self.metals = None
		if self.metals is None:
			metal_layers = self.get_metals()
			# Note this is a nontrivial operation, we add all polygons to it
			# Maybe we can make virtual layer somehow?
			self.metals = Layer.from_layers(metal_layers, name='metals')

		return self.metals
		
	def merge_metal_vias(self):
		for metal_layer in self.get_metals():
			metals_layeri = metal_layer.intersection(self.vias, True)
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
				#polygon.show()
				#self.show_nets()
				
				r = PolygonRenderer(title='Nets')
				self.append_nets_to_render(r)
				r.add_polygon(polygon, color='orange')
				r.render()
				
				raise Exception(msg)
		

	def find_and_merge_nets(self):
		# Combine polygons at a net level on the same layer
		# Only needed if you have bad input polygons
		# Really would be better to pre-process input to combine them
		#bench = Benchmark()
		#self.condense_polygons()
		#print 'Polygons condensed in %s' % repr(bench)
		#self.show_nets()
		#sys.exit(1)
		self.verify_net_index()
		
		# Note that you cannot have diffusion and poly, via is for one or the other		
		bench = Benchmark()
		self.merge_metal_vias()
		print 'Metal and vias merged in %s' % repr(bench)
		#self.show_nets()
		#self.verify_net_index()
		#sys.exit(1)
		
		self.via_check(2)
		
		# Connected poly to metal
		
		bench = Benchmark()
		self.merge_poly_vias_layers()
		print 'Poly and vias merged in %s' % repr(bench)
		#self.show_nets()
		self.verify_net_index()
		
		# Connect diffusion to metal
		bench = Benchmark()
		self.merge_diffusion_vias_layers()
		print 'Diffusion and vias merged in %s' % repr(bench)
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
		for polygon in self.get_metal().gen_polygons():
			
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
	
	def get_metal_layers(self):
		l = list()
		l.append(self.metal)
		if self.metal_vcc:
			l.append(metal_vcc)
		if self.metal_gnd:
			l.append(metal_gnd)
		return l
	
	def conductive_layers(self):
		return list([self.polysilicon, self.diffusion]) + self.get_metal_layers()

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
				# ??? what was this for?  Debugging?
				"""
				if net_name == 'vcc':
					#UVPolygon.show_polygons([label_polygon, polygon])
					'''
					intersection = label_polygon.intersection(polygon)
					if intersection:
						intersection.show()
					else:
					'''
					pass
				"""
				
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
				net.add_name_parsed(net_name)
			if not matched:
				print 'Unmatched label: %s' % label_polygon
				if not Options.ignore_unmatched_labels:
					self.show_polygon_in_all(label_polygon)
					raise Exception('Could not assign net name ' + net_name)
		
	def add_rendered_layers(self, r):
		# draw over the original polygon
		for layer in self.layers:
			color = None
			r.add_layer(layer, color = color)
		
	def show_polygon_in_all(self, uvpolygon):
		r = PolygonRenderer(title='Highlighting polygon')
		for layer in self.layers:
			r.add_layer(layer)
		self.add_rendered_layers(r)
		r.add_polygon(uvpolygon, color='orange')
		r.render()
	
	def show_nets(self):
		if True:
			for i in self.nets.nets:
				self.show_net(i)
		else:
			r = PolygonRenderer(title='Nets')
			self.append_nets_to_render(self, r)
			r.render()

	def append_nets_to_render(self, r):
		i = 0
		for net in self.nets:
			cur_color = Options.color_wheel[colori % len(Options.color_wheel)]
			i += 1
			for member in net.members:
				r.add_polygon(member, color = cur_color)

	def show_net(self, net_number):
		r = PolygonRenderer(title='Net %u' % net_number, width=self.metal.width, height=self.metal.height)
		for layer in self.layers:
			r.add_layer(layer)
		
		# draw over the original polygon
		for layer in self.layers:
			for polygon in layer.polygons:
				if polygon.net.number == net_number:
					r.add_polygon(polygon, 'orange')
		r.render()

	def run(self):
		# Loop until we can't combine nets
		iteration = 0
		
		#intersection = False
		#intersections = 0
		#iteration += 1
		
		#print 'Iteration %u' % iteration
		
		print '********************'
		print 'Phase 1 / 5: seeding nets'
		self.assign_nets()
		
		# This is a relativly quick operation so move it earlier to reduce chance of late errors
		if Options.assign_node_names_early:
			self.assign_node_names()
		
		print '********************'
		print 'Phase 2 / 5: merging nets'
		self.find_and_merge_nets()

		print '********************'
		print 'Phase 3 / 5: finding transistors (and pullups'
		self.find_transistors()
		self.find_pullups()
		
		#sys.exit(1)
		
		print '********************'
		print 'Phase 4 / 5: assigning nets'
		
		# Now make them linearly ordered
		self.reassign_nets()
		if not Options.assign_node_names_early:
			self.assign_node_names()
		# This wasn't needed because we can figure it out during build
		#self.mark_diffusion()
		
		#print 'Nets: %u, expecting 4' % self.last_net
		#self.show_nets()
		#sys.exit(1)
		
		print '********************'
		print 'Phase 5 / 5: generating final output'
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

