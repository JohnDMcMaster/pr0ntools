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
	args = parser.parse_args()
	pto_in = args.pto[0]
	pto_out = args.out
	if pto_out is None:
		pto_out = pto_in

	print 'In: %s' % pto_in
	print 'Out: %s' % pto_out

	pto = PTOProject.from_file_name(pto_in)
	# Make sure we don't accidently override the original
	pto.remove_file_name()
	
	linear_reoptimize(pto, args.allow_missing)

	print 'Saving to %s' % pto_out
	pto.save_as(pto_out)


