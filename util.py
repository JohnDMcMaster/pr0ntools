'''
This file is part of pr0ntools
Misc utilities
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under GPL V3+
'''

def rjust_str(s, nchars):
	'''right justify string, space padded to nchars spaces'''
	return ('%% %ds' % nchars) % s

