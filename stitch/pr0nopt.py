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

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Manipulate .pto files')
	parser.add_argument('pto', metavar='.pto in', type=str, nargs=1,
                   help='project to work on')
	parser.add_argument('out', metavar='.pto out', type=str, nargs='?',
                   help='output file, default to override input')
	parser.add_argument('--allow-missing', action="store_true", dest="allow_missing", default=False, help='Allow missing images')
	parser.add_argument('--pto-ref', action='store', type=str, dest="pto_ref", default=None,
                   help='project to use for creating linear system (default: in)')
	args = parser.parse_args()
	pto_in = args.pto[0]
	pto_out = args.out
	if pto_out is None:
		pto_out = pto_in

	print 'In: %s' % pto_in
	print 'Out: %s' % pto_out

	pto = PTOProject.from_file_name(pto_in)
	if args.pto_ref:
		pto_ref = PTOProject.from_file_name(args.pto_ref)
		pto_ref.remove_file_name()
	else:
		pto_ref = None
	# Make sure we don't accidently override the original
	pto.remove_file_name()
	
	linear_reoptimize(pto, pto_ref, args.allow_missing)

	if 0:
		print 'Image lines %d' % len(pto.get_image_lines())
		for line in pto.get_image_lines():
			print line

	print 'Saving to %s' % pto_out
	pto.save_as(pto_out)


