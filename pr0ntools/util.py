'''
This file is part of pr0ntools
Misc utilities
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''
import math
import sys
import datetime

def rjust_str(s, nchars):
    '''right justify string, space padded to nchars spaces'''
    return ('%% %ds' % nchars) % s

def mean_stddev(data):
    '''mean and standard deviation'''
    mean = sum(data) / float(len(data))
    varience = sum([(x - mean)**2 for x in data])
    stddev = math.sqrt(varience / float(len(data) - 1))
    return (mean, stddev) 

def now():
    return datetime.datetime.utcnow().isoformat()

def msg(s=''):
    print '%s: %s' % (now(), s)

# Print timestamps in front of all output messages
class IOTimestamp(object):
    def __init__(self, obj=sys, name='stdout'):
        self.obj = obj
        self.name = name
        
        self.fd = obj.__dict__[name]
        obj.__dict__[name] = self
        self.nl = True

    def __del__(self):
        if self.obj:
            self.obj.__dict__[self.name] = self.fd

    def flush(self):
        self.fd.flush()
       
    def write(self, data):
        parts = data.split('\n')
        for i, part in enumerate(parts):
            if i != 0:
                self.fd.write('\n')
            # If last bit of text is just an empty line don't append date until text is actually written
            if i == len(parts) - 1 and len(part) == 0:
                break
            if self.nl:
                self.fd.write('%s: ' % now())
            self.fd.write(part)
            # Newline results in n + 1 list elements
            # The last element has no newline
            self.nl = i != (len(parts) - 1)

# Log file descriptor to file
class IOLog(object):
    def __init__(self, obj=sys, name='stdout', out_fn=None, out_fd=None, mode='w'):
        if out_fd:
            self.out_fd = out_fd
        else:
            self.out_fd = open(out_fn, mode)
        
        self.obj = obj
        self.name = name
        
        self.fd = obj.__dict__[name]
        obj.__dict__[name] = self
        self.nl = True

    def __del__(self):
        if self.obj:
            self.obj.__dict__[self.name] = self.fd

    def flush(self):
        self.fd.flush()
       
    def write(self, data):
        self.fd.write(data)
        self.out_fd.write(data)
