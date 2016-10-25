'''
This file is part of pr0ntools
Misc utilities
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''
import datetime
import math
import os
import shutil
import sys

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

def logwt(d, fn, shift_d=True, shift_f=False, stampout=True):
    '''Log with timestamping'''
    
    if shift_d:
        try_shift_dir(d)
        os.mkdir(d)
    
    fn_can = os.path.join(d, fn)
    outlog = IOLog(obj=sys, name='stdout', out_fn=fn_can, shift=shift_f)
    errlog = IOLog(obj=sys, name='stderr', out_fd=outlog.out_fd)
    
    # Add stamps after so that they appear in output logs
    outdate = None
    errdate = None
    if stampout:
        outdate = IOTimestamp(sys, 'stdout')
        errdate = IOTimestamp(sys, 'stderr')
    
    return (outlog, errlog, outdate, errdate)

def try_shift_dir(d):
    if not os.path.exists(d):
        return
    i = 0
    while True:
        dst = d + '.' + str(i)
        if os.path.exists(dst):
            i += 1
            continue
        shutil.move(d, dst)
        break


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
                self.fd.write('%s: ' % datetime.datetime.utcnow().isoformat())
            self.fd.write(part)
            # Newline results in n + 1 list elements
            # The last element has no newline
            self.nl = i != (len(parts) - 1)

# Log file descriptor to file
class IOLog(object):
    def __init__(self, obj=sys, name='stdout', out_fn=None, out_fd=None, mode='a', shift=False):
        if out_fd:
            self.out_fd = out_fd
        else:
            # instead of jamming logs together, shift last to log.txt.1, etc
            if shift and os.path.exists(out_fn):
                i = 0
                while True:
                    dst = out_fn + '.' + str(i)
                    if os.path.exists(dst):
                        i += 1
                        continue
                    shutil.move(out_fn, dst)
                    break
            
            hdr = mode == 'a' and os.path.exists(out_fn)
            self.out_fd = open(out_fn, mode)
            if hdr:
                self.out_fd.write('*' * 80 + '\n')
                self.out_fd.write('*' * 80 + '\n')
                self.out_fd.write('*' * 80 + '\n')
                self.out_fd.write('Log rolled over\n')
        
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

def add_bool_arg(parser, yes_arg, default=False, **kwargs):
    dashed = yes_arg.replace('--', '')
    dest = dashed.replace('-', '_')
    parser.add_argument(yes_arg, dest=dest, action='store_true', default=default, **kwargs)
    parser.add_argument('--no-' + dashed, dest=dest, action='store_false', **kwargs)

