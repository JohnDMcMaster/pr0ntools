'''
This file is part of pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

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


