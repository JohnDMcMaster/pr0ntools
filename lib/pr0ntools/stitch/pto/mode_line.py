'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
http://search.cpan.org/dist/Panotools-Script/lib/Panotools/Script/Line/Mode.pm

  m i2

  g2.5         Set gamma value for internal computations (default 1.0)
                   See <http://www.fh-furtwangen.de/~dersch/gamma/gamma.html>
                This is especially useful in conjunction with the vignetting correction
                by division

  i2           Set interpolator, See <http://www.fh-furtwangen.de/~dersch/interpolator/interpolator.html>
                 one of:
                    0 - poly3 (default)
                    1 - spline16,
                    2 - spline36,
                    3 - sinc256,
                    4 - spline64,
                    5 - bilinear,
                    6 - nearest neighbor,
                    7 - sinc1024

   m2           Huber Sigma

   p0.001       Photometric Huber Sigma

   s1           Photometric Symmetric Error
'''

import line

'''
m g1 i0 f0 m2 p0.00784314
'''

class ModeLine(line.Line):
	def __init__(self, text, project):
		line.Line.__init__(self, text, project)
		
	def prefix(self):
		return 'm'
		
	def variable_print_order(self):
		return list(['g', 'i', 'f', 'm', 'p', 's'])
	
	def key_variables(self):
		return set()
	def int_variables(self):
		return set(['i', 'f', 'm', 's'])
	def float_variables(self):
		return set(['g', 'p'])
	def string_variables(self):
		return set()


	@staticmethod
	def from_line(line, pto_project):
		ret = ModeLine()
		ret.text = line
		return ret

