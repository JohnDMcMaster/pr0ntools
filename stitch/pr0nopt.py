#!/usr/bin/python
'''
pr0opt
.pto optimization
Copyright 2012 John McMaster
'''
import argparse		
from pr0ntools.stitch.optimizer import PTOptimizer
from pr0ntools.stitch.pto.project import PTOProject
from pr0ntools.stitch.pto.util import *
from pr0ntools.stitch.linear_optimizer import *

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Manipulate .pto files')
	parser.add_argument('pto_ref', metavar='.pto reference', type=str, nargs=1,
                   help='reference project to work on')
	parser.add_argument('images', metavar='images', type=str, nargs='+',
                   help='image files to put int output')
	parser.add_argument('--out', action='store', type=str, dest="pto_out", default="out.pto",
                   help='output file name (default: out.pto)')
	parser.add_argument('--allow-missing', action="store_true", dest="allow_missing", default=True, help='Allow missing images')
	parser.add_argument('--border', action="store_true", dest="border", default=False, help='Manually optimize border')
	args = parser.parse_args()
	pto_ref_fn = args.pto_ref[0]
	pto_out_fn = args.pto_out

	print 'Reference in: %s' % pto_ref_fn
	print 'Out: %s' % pto_out_fn

	# Have to start somewhere...
	pto_out = PTOProject.from_default()
	# Add the images in
	for image in args.images:
		pto_out.add_image(image)
	
	pto_ref = PTOProject.from_file_name(pto_ref_fn)
	pto_ref.remove_file_name()
	
	linear_reoptimize(pto_out, pto_ref, allow_missing=args.allow_missing, order=2, border=args.border)

	print 'Centering...'
	center(pto_out)
	
	print 'Converting to Hugin form...'
	resave_hugin(pto_out)
	
	print 'Saving to %s' % pto_out_fn
	pto_out.save_as(pto_out_fn)

