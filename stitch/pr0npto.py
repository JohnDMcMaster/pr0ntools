#!/usr/bin/python
'''
pr0pto
.pto utilities
Copyright 2012 John McMaster
'''
import argparse
from pr0ntools.stitch.optimizer import PTOptimizer, ChaosOptimizer
from pr0ntools.stitch.linopt import LinOpt
from pr0ntools.stitch.tile_opt import TileOpt
from pr0ntools.stitch.pto.project import PTOProject
from pr0ntools.stitch.pto.util import *

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Manipulate .pto files')
	parser.add_argument('--center', action="store_true", dest="center", default=None, help='Center the project')
	parser.add_argument('--anchor', action="store_true", dest="anchor", help='Re-anchor in the center')
	parser.add_argument('--set-optimize-xy', action="store_true", dest="set_optimize_xy", default=False, help='Set project to optimize xy')
	parser.add_argument('--optimize', action="store_true", dest="optimize", help='Optimize the project and also center by default')
	parser.add_argument('--chaos-opt', action="store_true", help='Experimental optimization algorithm')
	parser.add_argument('--tile-opt', action="store_true", help='Optimize project by optimizing sub areas')
	parser.add_argument('--lin-opt', action="store_true", help='Optimize project using linear predictive optimize algorithm')
	parser.add_argument('--reoptimize', action="store_true", dest="reoptimize", default=True, help='When optimizing do not remove all existing optimizations')
	parser.add_argument('--no-reoptimize', action="store_false", dest="reoptimize", default=True, help='When optimizing do not remove all existing optimizations')
	parser.add_argument('--lens-model', action="store", default=None, help='Apply lens model file')
	parser.add_argument('--reset-photometrics', action="store_true", dest="reset_photometrics", default=False, help='Reset photometrics')
	parser.add_argument('--basename', action="store_true", dest="basename", default=False, help='Strip image file names down to basename')
	parser.add_argument('--hugin', action="store_true", help='Resave using panotools (Hugin form)')
	parser.add_argument('--pto-ref', action='store', default=None,
                   help='project to use for creating linear system (default: in)')
	parser.add_argument('--allow-missing', action="store_true", help='Allow missing images')
	parser.add_argument('pto', metavar='.pto in', nargs=1,
                   help='project to work on')
	parser.add_argument('out', metavar='.pto out', nargs='?',
                   help='output file, default to override input')
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
	
	if args.center is True:
		center(pto)
	
	if args.anchor:
		print 'Re-finding anchor'
		center_anchor(pto)
	
	if args.basename:
		print 'Converting to basename'
		make_basename(pto)
		
	if args.hugin:
		print 'Resaving with hugin'
		resave_hugin(pto)
	
	if args.lens_model:
		print 'Applying lens model (FIXME)'

	if args.pto_ref:
		pto_ref = PTOProject.from_file_name(args.pto_ref)
		pto_ref.remove_file_name()
		linear_reoptimize(pto, pto_ref, args.allow_missing)

	if args.reset_photometrics:
		# Overall exposure
		# *very* important
		#??? shouldn't this be pto.?
		project.panorama_line.set_variable('E', 1)
		# What about m's p and s?

		for image_line in project.image_lines:
			# Don't adjust exposure
			image_line.set_variable('Eev', 1)
			# blue and red white balance correction at normal levels
			image_line.set_variable('Eb', 1)
			image_line.set_variable('Er', 1)
			# Disable EMoR corrections
			image_line.set_variable('Ra', 0)
			image_line.set_variable('Rb', 0)
			image_line.set_variable('Rc', 0)
			image_line.set_variable('Rd', 0)
			image_line.set_variable('Re', 0)
	
	if args.set_optimize_xy:
		optimize_xy_only(pto)
	
	# Needs to be late to get the earlier additions if we used them
	if args.optimize:
		print 'Optimizing'
		opt = PTOptimizer(pto)
		opt.reoptimize = args.reoptimize
		opt.run()
		# Default
		if not args.center is False:
			print 'Centering...'
			center(pto)

	if args.chaos_opt:
		print 'Optimizing'
		opt = ChaosOptimizer(pto)
		opt.reoptimize = args.reoptimize
		opt.run()
		# Default
		if not args.center is False:
			print 'Centering...'
			center(pto)

	# Needs to be late to get the earlier additions if we used them
	if args.lin_opt:
		print 'Optimizing'
		opt = LinOpt(pto)
		opt.reoptimize = args.reoptimize
		opt.run()
		# Default
		if not args.center is False:
			print 'Centering...'
			center(pto)

	# Needs to be late to get the earlier additions if we used them
	if args.tile_opt:
		print 'Optimizing'
		opt = TileOpt(pto)
		opt.reoptimize = args.reoptimize
		opt.run()
		# Default
		if not args.center is False:
			print 'Centering...'
			center(pto)

	print 'Saving to %s' % pto_out
	pto.save_as(pto_out)


