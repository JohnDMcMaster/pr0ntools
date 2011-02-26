'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

from pr0ntools.execute import Execute

'''
Part of perl-Panotools-Script

Usage:
    ptoclean [options] --output better.pto notgood.pto

     Options:
      -o | --output     Filename of pruned project (can be the the same as the input)
      -n | --amount     Distance factor for pruning (default=2)
      -f | --fast       Don't run the optimiser for each image pair (similar to APClean)
      -v | --verbose    Report some statistics
      -h | --help       Outputs help documentation
'''
class PTOClean:
	def __init__(self, pto_project):
		self.pto_project = pto_project
	
	def run(self):
		args = list()
		args.append("-o")
		args.append(self.pto_project.get_a_file_name())
		args.append(self.pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("ptoclean", args)
		if not rc == 0:
			raise Exception('failed to clean control points')
		self.pto_project.reopen()

