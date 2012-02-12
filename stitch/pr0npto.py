#!/usr/bin/python
'''
pr0pto
.pto utilities
Copyright 2012 John McMaster
'''
import argparse		

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Manipulate .pto files')
	parser.add_argument('--center', action="store_true", dest="center", default=False, help='Center the project')
	parser.add_argument('--anchor', action="store_true", dest="anchor", default=False, help='Re-anchor in the center')
	parser.add_argument('--optimize', action="store_true", dest="optimize", default=False, help='Optimize the project')
	parser.add_argument('--lens-model', action="store", type=str, dest="lens_model", default=None, help='Apply lens model file')
	parser.add_argument('--reset-photometrics', action="store_true", dest="reset_photometrics", default=False, help='Reset photometrics')
	parser.add_argument('pto', metavar='.pto in', type=str, nargs=1,
                   help='project to work on')
	parser.add_argument('out', metavar='.pto out', type=str, nargs='?',
                   help='output file, default to override input')
	args = parser.parse_args()
	pto = args.pto[0]
	pto_out = args.out
	if pto_out is None:
		pto_out = pto

	print 'In: %s' % pto
	print 'Out: %s' % pto_out

	if args.center:
		print 'Centering pto'
	
	if args.anchor:
		print 'Re-finding anchor'
	
	if args.lens_model:
		print 'Applying lens model'

	if args.reset_photometrics:
		# Overall exposure
		# *very* important
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
	
	if args.optimize:
		print 'Optimizing'

	#project.save_as(pto_out)

