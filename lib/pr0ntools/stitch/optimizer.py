'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
Others
celeste_standalone 
ptscluster
cpclean

 
autooptimiser: optimize image positions
autooptimiser version 2010.0.0.5045

Usage:  autooptimiser [options] input.pto
   To read a project from stdio, specify - as input file.

  Options:
     -o file.pto  output file. If obmitted, stdout is used.

    Optimisation options (if not specified, no optimisation takes place)
     -a       auto align mode, includes various optimisation stages, depending
               on the amount and distribution of the control points
     -p       pairwise optimisation of yaw, pitch and roll, starting from
              first image
     -n       Optimize parameters specified in script file (like PTOptimizer)

    Postprocessing options:
     -l       level horizon (works best for horizontal panos)
     -s       automatically select a suitable output projection and size
    Other options:
     -q       quiet operation (no progress is reported)
     -v HFOV  specify horizontal field of view of input images.
               Used if the .pto file contains invalid HFOV values
               (autopano-SIFT writes .pto files with invalid HFOV)

   When using -a -l and -s options together, a similar operation to the "Align"
    button in hugin is performed.
'''
class PositionOptimizer:
	pto_project = None
	
	def __init__(self, pto_project):
		self.pto_project = pto_project
	
	def optimize(self):
		# "autooptimiser -n -o project.pto project.pto"
		args = list()
		args.append("-n")
		args.append("-o")
		args.append(pto_project.get_a_file_name())
		args.append(pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("autooptimiser", args)
		if not rc == 0:
			raise Exception('failed position optimization')
		self.project.reopen()

