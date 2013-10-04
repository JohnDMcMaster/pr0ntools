'''
This file is part of pr0ntools
Misc utilities
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under GPL V3+
'''
import math

def rjust_str(s, nchars):
	'''right justify string, space padded to nchars spaces'''
	return ('%% %ds' % nchars) % s

def mean_stddev(data):
    '''mean and standard deviation'''
    mean = sum(data) / float(len(data))
    varience = sum([(x - mean)**2 for x in data])
    stddev = math.sqrt(varience / float(len(data) - 1))
    return (mean, stddev) 

