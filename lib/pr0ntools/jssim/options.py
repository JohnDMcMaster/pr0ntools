'''
This file is part of pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools.jssim.transistor import *

class Options:

	'''
	If True treat input files as masks instead of the end result
	Self aligned gates may be drawn as large diffusion areas in the masks but result in adjacent areas on die
	'''
	as_masks = False
	# Look for transistors by looking for diffusion near poly
	transistors_by_adjacency = None
	# Look for transistors by intersecting poly and diffusion
	transistors_by_intersect = None

	technology = Technology.NMOS
	
	# Assigning early is good for normal use since we want to perform simple error checking
	# before running full computations
	# However, debugging may only want to use partial mask in which case labels might not line up
	assign_node_names_early = True
	
	color_wheel = ('red', 'blue', 'green', 'yellow')
	
	# hack to complement above
	ignore_unmatched_labels = True
	
	# Use quadtree to signifigantly reduce CPU usage at the cost of increased memory
	using_quadtree = True

	# Reserved for future use
	# JSSim can only use point list type polygons, ie not ones with holes
	# Code breaks polygons apart for rendering to compensate
	'''
	from shapely.geometry.Polygon:
	is_simple
		True if the geometry is simple, meaning that any self-intersections 
		are only at boundary points, else False	
	'''
	simple_polygons = True

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

	DATA_VER = "1.0"
	JS_FILE_TRANSDEFS = "transdefs.js"
	TRANSDEFS_VER = DATA_VER
	JS_FILE_SEGDEFS = "segdefs.js"
	SEGDEFS_VER = DATA_VER
	JS_FILE_NODENAMES = "nodenames.js"
	NODENAMES_VER = DATA_VER

	@staticmethod
	def assign_defaults():
		if Options.transistors_by_adjacency is None:
			Options.transistors_by_adjacency = not Options.as_masks
		if Options.transistors_by_intersect is None:
			Options.transistors_by_intersect = Options.as_masks


