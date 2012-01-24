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

class PTOptimizer:
	def __init__(self, pto_project):
		self.pto_project = pto_project
	
	def optimize(self):
		'''
		The base Hugin project seems to work if you take out a few things:
		Eb1 Eev0 Er1 Ra0 Rb0 Rc0 Rd0 Re0 Va1 Vb0 Vc0 Vd0 Vx-0 Vy-0
		So say generate a project file with all of those replaced
		
		In particular we will generate new i lines
		To keep our original object intact we will instead do a diff and replace the optimized things on the old project
		'''
		# Copy project so we can trash it
		project = self.pto_project.to_ptoptimizer()
		
		# "PToptimizer out.pto"
		args = list()
		args.append(pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("PToptimizer", args)
		if not rc == 0:
			raise Exception('failed position optimization')
		project.reopen()

		print
		print
		print
		print 'Optimized project:'
		print project
		sys.exit(1)

