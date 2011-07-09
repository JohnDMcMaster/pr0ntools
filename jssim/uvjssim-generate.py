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

from pr0ntools import PImage

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


class Layer:
	

	def __init__(self, image_file_name):
		#self.pimage = PImage(image_file_name)
		self.from_svg(image_file_name)
		
	

class UVJSSimGenerator:
	def __init__(self):	
		self.metal_vcc = Layer(DEFAULT_IMAGE_FILE_METAL_VCC)
		self.metal_gnd = Layer(DEFAULT_IMAGE_FILE_METAL_GND)
		self.metal = Layer(DEFAULT_IMAGE_FILE_METAL)
		self.polysilicon = Layer(DEFAULT_IMAGE_FILE_POLYSILICON)
		self.diffusion = Layer(DEFAULT_IMAGE_FILE_DIFFUSION)
		self.vias = Layer(DEFAULT_IMAGE_FILE_VIAS)
		#self.buried_contacts = Layer(DEFAULT_IMAGE_FILE_BURIED_CONTACTS)
		#self.transistors = Layer(DEFAULT_IMAGE_FILE_TRANSISTORS)

		self.layers = [self.metal_vcc, self.metal_gnd, self.metal, self.polysilicon, self.diffusion, self.vias]

		self.verify_layer_sizes()

	def verify_layer_sizes(self):
		width = None
		height = None
		reference_layer = None
		
		for layer in layers:
			this_width = layer.pimage.width()
			this_height = layer.pimage.width()
			if width == None:
				width = this_width
				height = this_height
				reference_layer = layer
				continue
			if this_width != width or this_height != height:
				print '%s size (width=%u, height=%u) does not match %s size (width=%u, height=%u)' % ...
						(reference_layer.pimage.file_name(), width, height, ...
						layer.pimage.file_name(), this_width, this_height)
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

