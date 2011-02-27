'''
cpclean: remove wrong control points by statistic method
cpclean version 2010.0.0.5045

Usage:  cpclean [options] input.pto

CPClean uses statistical methods to remove wrong control points

Step 1 optimises all images pairs, calculates for each pair mean 
       and standard deviation and removes all control points 
       with error bigger than mean+n*sigma
Step 2 optimises the whole panorama, calculates mean and standard deviation
       for all control points and removes all control points with error
       bigger than mean+n*sigma

  Options:
     -o file.pto  Output Hugin PTO file. Default: '<filename>_clean.pto'.
     -n num   distance factor for checking (default: 2)
     -p       do only pairwise optimisation (skip step 2)
     -w       do optimise whole panorama (skip step 1)
     -h       shows help
'''

'''
Usage:
ptovariable [options] project.pto

 Options:
	   --positions          Optimise positions
	   --roll               Optimise roll for all images except anchor if --positions not set
	   --pitch              Optimise pitch for all images except anchor if --positions not set
	   --yaw                Optimise yaw for all images except anchor if --positions not set
	   -r <num> <num> <..>  Optimise roll for specified images
	   -p <num> <num> <..>  Optimise pitch for specified images
	   -y <num> <num> <..>  Optimise yaw for specified images
	   --view               Optimise angle of view
	   --barrel             Optimise barrel distortion
	   --centre             Optimise optical centre
	   --vignetting         Optimise vignetting
	   --vignetting-centre  Optimise vignetting centre
	   --response           Optimise camera response EMoR parameters
	   --exposure           Optimise exposure (EV)
	   --white-balance      Optimise colour balance
  -o | --output OUTFILE     Specify output file default is to overwrite input       
  -h | --help               Outputs help documentation
'''
class PhotometricOptimizer:
	pto_project = None
	
	def __init__(self, pto_project):
		self.pto_project = pto_project
	
	def run(self):
		# Make sure its syncd
		self.pto_project.save()
	
		'''
		Setup variables for optimization
		'''	
		args = list()
		# Defect where brightness varies as we move towards the outside of the lens
		args.append("--vignetting")
		# ?
		args.append("--response")
		# ?
		args.append("--exposure")
		# ?
		args.append("--white-balance")
		# Overwrite input
		args.append(self.pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("ptovariable", args)
		if not rc == 0:
			raise Exception('failed photometric optimization setup')
		# Reload now that we overwrote
		self.pto_project.reopen()

		'''
		Do actual optimization
		'''	
		args = list()
		args.append("-o")
		args.append(self.pto_project.get_a_file_name())
		args.append(self.pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("vig_optimize", args)
		if not rc == 0:
			raise Exception('failed photometric optimization')
		# Reload now that we overwrote
		self.pto_project.reopen()		

