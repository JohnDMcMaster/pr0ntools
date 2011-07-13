#! /usr/bin/env python
'''
This file is part of pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

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

VERSION = "1.0"

from pr0ntools.jssim.options import Options
import sys
from pr0ntools.jssim.generator import Generator
from pr0ntools.jssim.layer import UVPolygon, Net, Nets, PolygonRenderer, Point


'''
Are these x,y or y.x?
Where is the origin?
Assume visual6502 coordinate system
	Origin in lower left corner of screen
	(x, y)

 <polygon points="2601,2179 2603,2180 2603,2181 2604,2183" />
'''

from layer import Layer

		
def help():
	print "uvjssim-img2js version %s" % VERSION
	print "Generate JSSim files from images"
	print "Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>, 2 clause BSD license"
	print "Usage: uvjssim-generate [options]"
	print "--masks[=<bool>]: set options that favor input as masks as opposed to a physical chip"
	print "--trans-by-adj[=<bool>]: compute transistors by finding diffusion adjacent to poly"
	print "--trans-by-int[=<bool>]: compute transistors by finding diffusion intersecting poly"
	print "--help: this message"
	print "--trans-tech=<technology>: input transistor technology, one of (case insensitive):"
	print "\tbipolar"
	print "\tNMOS (default)"
	print "\tPMOS"
	print "\tCMOS"
	print "\tBiCMOS"
	print
	print "Input files:"
	print "\t%s" % Options.DEFAULT_IMAGE_FILE_METAL_VCC
	print "\t%s" % Options.DEFAULT_IMAGE_FILE_METAL_GND
	print "\t%s" % Options.DEFAULT_IMAGE_FILE_METAL
	print "\t%s" % Options.DEFAULT_IMAGE_FILE_POLYSILICON
	print "\t%s" % Options.DEFAULT_IMAGE_FILE_DIFFUSION
	print "\t%s" % Options.DEFAULT_IMAGE_FILE_VIAS
	print "\t%s (currently unused)" % Options.DEFAULT_IMAGE_FILE_BURIED_CONTACTS
	print "Output files:"
	print "\t%s" % Options.JS_FILE_NODENAMES
	print "\t%s" % Options.JS_FILE_TRANSDEFS
	print "\t%s" % Options.JS_FILE_SEGDEFS

if __name__ == "__main__":	
	for arg_index in range (1, len(sys.argv)):
		arg = sys.argv[arg_index]
		arg_key = None
		arg_value = None
		if arg.find("--") == 0:
			arg_value_bool = True
			if arg.find("=") > 0:
				arg_key = arg.split("=")[0][2:]
				arg_value = arg.split("=")[1]
				if arg_value == "false" or arg_value == "0" or arg_value == "no":
					arg_value_bool = False
			else:
				arg_key = arg[2:]
	
		if arg_key == "masks":
			Options.as_masks = arg_value_bool
		elif arg_key == "trans-by-adj":
			Options.transistors_by_adjacency = arg_value_bool
		elif arg_key == "trans-by-int":
			Options.transistors_by_intersect = arg_value_bool
		elif arg_key == "technology":
			Options.transistor_technology = transistor.Technology.from_string(arg_value)
			if Options.transistor_technology == Technology.INVALID:
				print 'Unrecognized technology %s' % arg_value
				help()
				sys.exit(1)
		elif arg_key == "help":
			help()
			sys.exit(0)
		else:
			print 'Unrecognized argument: %s' % arg
			help()
			sys.exit(1)
	
	Options.assign_defaults()

	gen = Generator()
	gen.run()

