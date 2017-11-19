#!/usr/bin/python
'''
pr0pto
.pto utilities
Copyright 2012 John McMaster
'''
import argparse
import sys
from pr0ntools.stitch.pto.project import PTOProject
from pr0ntools.stitch.optimizer import pto2icm
#from pr0ntools.stitch.pto.util import *
from pr0ntools.util import IOTimestamp, IOLog
from pr0ntools.benchmark import Benchmark

import os
import math
import matplotlib.pyplot as plt

def pto2cps(pto):
    '''
    Enumerate all control point differences
    Map to a dictionary of (n, N) lists containing (dx, dy) tuples
    Also create an index of all the entries?
    '''
    ret = {}
    for cpl in pto.control_point_lines:
        n = cpl.getv('n')
        N = cpl.getv('N')
        imgn = pto.image_lines[n]
        imgN = pto.image_lines[N]
        dx = (imgn.getv('d') - cpl.getv('x')) - (imgN.getv('d') - cpl.getv('X'))
        dy = (imgn.getv('e') - cpl.getv('y')) - (imgN.getv('e') - cpl.getv('Y'))

        # Make canonical
        # Usually n < N
        if N > n:
            n, N = N, n
            dx = -dx
            dy = -dy
        points = ret.get((n, N), [])
        points.append((dx, dy))
        ret[(n, N)] = points
    return ret

def rm_image_cps(self, indexes):
    '''
    Given a list of n, N tuples, delete all control points matching indexes
    '''
    removed = 0
    newls = []
    for cpl in self.control_point_lines:
        n = cpl.get_variable('n')
        N = cpl.get_variable('N')
        if not ((n, N) in indexes or (N, n) in indexes):
            newls.append(cpl)
        else:
            removed += 1
    self.control_point_lines = newls
    return removed

def check_cp(pto):
    print 'Building CP map'
    cps = pto2cps(pto)
    errors = []
    for cpk, diffs in sorted(cps.iteritems()):
        n, N = cpk
        img1 = pto.i2img(n).get_name()
        img2 = pto.i2img(N).get_name()
        
        # Compute error
        rms = 0.0
        for diff in diffs:
            dx, dy = diff
            rms += math.sqrt(dx**2 + dy**2)
        rms /= len(diffs)

        print '%s - %s: % 6.1f:' % (img1, img2, rms)
        for diff in diffs:
            dx, dy = diff
            print '  % 6.1f % 6.1f' % (dx, dy)
        errors.append((rms, (img1, img2)))

    errors = sorted(errors)
    print 'Worst:'
    rms, (img1, img2) = errors[-1]
    print '  %s - %s: % 6.1f' % (img1, img2, rms)

    if 0:
        rmss = []
        for rms, (_img1, _img2) in errors:
            rmss.append(rms)

        plt.hist(rmss, normed=True, bins=32)
        plt.show()

    if 1:
        # From histogram plot
        # 1 translation error is about 25
        # These are way outside valid range
        thresh = 50.0
        print
        bad = 0
        print 'Thresh = % 6.1f' % thresh
        toremove = set()
        for rms, (img1, img2) in errors:
            if rms > thresh:
                bad += 1
                print '  %s - %s: % 6.1f' % (img1, img2, rms)
                i1 = pto.get_image_by_fn(img1).get_index()
                i2 = pto.get_image_by_fn(img2).get_index()
                toremove.add((i1, i2))
            bad += 1
        if 1:
            print 'Removing CPs between %d image pairs' % len(toremove)
            removed = rm_image_cps(pto, toremove)
            print 'Removed %d CPs' % removed

def parser_add_bool_arg(yes_arg, default=False, **kwargs):
    dashed = yes_arg.replace('--', '')
    dest = dashed.replace('-', '_')
    parser.add_argument(yes_arg, dest=dest, action='store_true', default=default, **kwargs)
    parser.add_argument('--no-' + dashed, dest=dest, action='store_false', **kwargs)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Manipulate .pto files')
    parser.add_argument('--verbose', action="store_true", help='Verbose output')
    parser.add_argument('pto', metavar='.pto in', nargs=1,
                   help='project to work on')
    parser.add_argument('out', metavar='.pto out', nargs='?',
                   help='output file, default to override input')
    args = parser.parse_args()
    pto_in = args.pto[0]
    pto_out = args.out
    if pto_out is None:
        pto_out = pto_in

    exist = os.path.exists('pr0npto.log')
    # can easily be multiple invocations, save all data
    _outlog = IOLog(obj=sys, name='stdout', out_fn='pr0npto.log', mode='a')
    _errlog = IOLog(obj=sys, name='stderr', out_fd=_outlog.out_fd)

    if True or args.stampout:
        _outdate = IOTimestamp(sys, 'stdout')
        _errdate = IOTimestamp(sys, 'stderr')

    if exist:
        _outlog.out_fd.write('\n')
        _outlog.out_fd.write('\n')
        _outlog.out_fd.write('\n')
        _outlog.out_fd.write('*' * 80 + '\n')
        _outlog.out_fd.write('*' * 80 + '\n')
        _outlog.out_fd.write('*' * 80 + '\n')
    print 'pr0npto starting'
    print 'In: %s' % pto_in
    print 'Out: %s' % pto_out
    bench = Benchmark()

    pto = PTOProject.from_file_name(pto_in)
    # Make sure we don't accidently override the original
    pto.remove_file_name()
    
    print 'Checking for bad CPs'
    check_cp(pto)

    if 1:
        print 'Saving to %s' % pto_out
        pto.save_as(pto_out)
    
    bench.stop()
    print 'Completed in %s' % bench


