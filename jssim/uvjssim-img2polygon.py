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
				
		# Validate sizes
		self.verify_layer_sizes(src_images.items())
	
		self.metal_gnd = Layer(src_images['metal_gnd'])
		self.metal_vcc = Layer(src_images['metal_vcc'])
		self.metal = Layer(src_images['metal'])
		self.polysilicon = Layer(src_images['metal_vcc'])
		self.diffusion = Layer(src_images['diffusion'])
		self.vias = Layer(src_images['vias'])
		#self.buried_contacts = Layer(DEFAULT_IMAGE_FILE_BURIED_CONTACTS)
		#self.transistors = Layer(DEFAULT_IMAGE_FILE_TRANSISTORS)

		self.layers = [self.metal_vcc, self.metal_gnd, self.metal, self.polysilicon, self.diffusion, self.vias]

	def verify_layer_sizes(self, images):
		width = None
		height = None
		reference_layer = None
		
		# Image can't read SVG
		# We could read the width/height attr still though
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
			
	def run(self):
		print 'Vaporware'
		
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
	print "\t%s" % DEFAULT_IMAGE_FILE_BURIED_CONTACTS
	print "Output files:"
	print "\t%s" % DEFAULT_IMAGE_FILE_TRANSISTORS
	print "\t%s" % JS_FILE_TRANSDEFS
	print "\t%s" % JS_FILE_SEGDEFS

if len(sys.argv) > 1:
	help()
	sys.exit(1)
	
gen = UVJSSimGenerator()
gen.run()

