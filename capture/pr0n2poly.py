#!/usr/bin/python
'''
pr0n2poly: IC image to polygons
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import sys 
import os.path
import argparse		

import pr0ntools.layer.parser

from opencv.cv import *
from PIL import Image

class SVGTestVector:
	def __init__(self, image_fn, layers):
		self.layers = layers
		self.image_fn = image_fn
		print 'Constructing test vector with source image %s and %d layers' % (self.image_fn, len(self.layers))
		for layer in self.layers:
			self.layers[layer].show()
		
		cv_gray = self.cv_gray()
        cvCanny(gray,edge2,20,100)


	def cv_gray(self):
		im = Image.open(image_fn)
		gray = cvCreateImage (cvSize (im.size[0], im.size[1]), 8, 1)

        for h in range(im.size[1]):
              for w in range(im.size[0]):
                    p=im.getpixel((w,h))
                    if(type(p)==type(1)):
                          gray[h][w] = im.getpixel((w,h))
                    else:
                          gray[h][w] = im.getpixel((w,h))[0]
      return gray
	
	@staticmethod
	def from_file(fn):
		parser = pr0ntools.layer.parser.MultilayerSVGParser(fn)
		parser.run()
		if len(parser.images) != 1:
			raise Exception('Test vector must have exactly one image')
		return SVGTestVector(list(parser.images)[0], parser.layers)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Manipulate .pto files')
	parser.add_argument('image_in', metavar='image_in', type=str, nargs=1,
                   help='Image to process')
	parser.add_argument('svg_out', metavar='svg_out', type=str, nargs=1,
                   help='Output file')
	parser.add_argument('training_in', metavar='training_in', type=str, nargs='+',
                   help='Tagged SVGs')
	#parser.add_argument('--allow-missing', action="store_true", dest="allow_missing", default=True, help='Allow missing images')
	args = parser.parse_args()
	image_in_fn = args.image_in[0]
	svg_out_fn = args.svg_out[0]
	training_svgs = args.training_in

	if svg_out_fn.find('svg') < 0:
		raise Exception("Output must be SVG")
	for f in training_svgs:
		if f.find('.svg') < 0:
			raise Exception('Training must be SVGs')

	print 'In: %s' % image_in_fn
	print 'Out: %s' % svg_out_fn
	print '%d training files' % len(training_svgs)
	
	for svg in training_svgs:
		vec = SVGTestVector.from_file(svg)


