#!/usr/bin/env python
'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
This file is used to optimize the size of an image project
It works off of the following idea:
-In the end all images must lie on the same focal plane to work as intended
-Hugin likes a default per image FOV of 51 degrees since thats a typical camera FOV
-With a fixed image width, height, and FOV as above we can form a natural focal plane
-Adjust the project focal plane to match the image focal plane


Note the following:
-Ultimately the project width/height determines the output width/height
-FOV values are not very accurate: only 1 degree accuracy
-Individual image width values are more about scaling as opposed to the total project size than their output width?
    Hugin keeps the closest 

A lot of this seems overcomplicated for my simple scenario
Would I be better off 

Unless I make the algorithm more advanced by correctly calculating all images into a focal plane (by taking a reference)
it is a good idea to at least assert that all images are in the same focal plane
'''

from pr0ntools import execute
from pr0ntools.pimage import PImage
from pr0ntools.stitch.pto.util import *
from pr0ntools.benchmark import Benchmark
from pr0ntools import statistics

import sys
import random
import json

def debug(s = ''):
    pass

'''
Convert output to PToptimizer form



http://wiki.panotools.org/PTOptimizer
    # The script must contain:
    # one 'p'- line describing the output image (eg Panorama)
    # one 'i'-line for each input image
    # one or several 'v'- lines listing the variables to be optimized.
    # the 'm'-line is optional and allows you to specify modes for the optimization.
    # one 'c'-line for each pair of control points



p line
    Remove E0 R0
        Results in message
            Illegal token in 'p'-line [69] [E] [E0 R0 n"PSD_mask"]
            Illegal token in 'p'-line [48] [0] [0 R0 n"PSD_mask"]
            Illegal token in 'p'-line [82] [R] [R0 n"PSD_mask"]
            Illegal token in 'p'-line [48] [0] [0 n"PSD_mask"]
    FOV must be < 180
        v250 => v179
        Results in message
            Destination image must have HFOV < 180
i line
    Must have FOV
        v51
        Results in message
            Field of View must be positive
    Must have width, height
        w3264 h2448
        Results in message
            Image height must be positive
    Must contain the variables to be optimized
        make sure d and e are there
        reference has them equal to -0, 0 seems to work fine



Converting back
Grab o lines and get the d, e entries
    Copy the entries to the matching entries on the original i lines
Open questions
    How does FOV effect the stitch?
'''
def prepare_pto(pto, reoptimize = True):
    '''Simply and modify a pto project enough so that PToptimizer will take it'''
    print 'Stripping project'
    if 0:
        print pto.get_text()
        print
        print
        print
    
    def fix_pl(pl):
        pl.remove_variable('E')
        pl.remove_variable('R')
        v = pl.get_variable('v') 
        if v == None or v >= 180:
            print 'Manipulating project field of view'
            pl.set_variable('v', 179)
            
    def fix_il(il):
        v = il.get_variable('v') 
        if v == None or v >= 180:
            il.set_variable('v', 51)
        
        # panotools seems to set these to -1 on some ocassions
        if il.get_variable('w') == None or il.get_variable('h') == None or int(il.get_variable('w')) <= 0 or int(il.get_variable('h')) <= 0:
            img = PImage.from_file(il.get_name())
            il.set_variable('w', img.width())
            il.set_variable('h', img.height())

        for v in 'd e'.split():
            if il.get_variable(v) == None or reoptimize:
                il.set_variable(v, 0)
                #print 'setting var'
        
        nv = {}
        for k, v in il.variables.iteritems():
            if k in ['w', 'h', 'f', 'Va', 'Vb', 'Vc', 'Vd', 'Vx', 'Vy', 'd', 'e', 'g', 't', 'v', 'Vm', 'n']:
                nv[k] = v
        il.variables = nv
    
    fix_pl(pto.get_panorama_line())
    
    for il in pto.image_lines:
        fix_il(il)
        #print il
        #sys.exit(1)
    
    if 0:
        print
        print    
        print 'prepare_pto final:'
        print pto
        print
        print
        print 'Finished prepping for PToptimizer'    
    #sys.exit(1)
            
def merge_pto(ptoopt, pto):
    '''Take a resulting pto project and merge the coordinates back into the original'''
    '''
    o f0 r0 p0 y0 v51 d0.000000 e0.000000 u10 -buf 
    ...
    o f0 r0 p0 y0 v51 d-12.584355 e-1706.852324 u10 +buf -buf 
    ...
    o f0 r0 p0 y0 v51 d-2179.613104 e16.748410 u10 +buf -buf 
    ...
    o f0 r0 p0 y0 v51 d-2213.480518 e-1689.955438 u10 +buf 

    merge into
    

    # image lines
    #-hugin  cropFactor=1
    i f0 n"c0000_r0000.jpg" v51 w3264 h2448 d0 e0
    #-hugin  cropFactor=1
    i f0 n"c0000_r0001.jpg" v51 w3264 h2448  d0 e0
    #-hugin  cropFactor=1
    i f0 n"c0001_r0000.jpg" v51  w3264 h2448  d0 e0
    #-hugin  cropFactor=1
    i f0 n"c0001_r0001.jpg" v51 w3264 h2448 d0 e0
    
    note that o lines have some image ID strings before them but position is probably better until I have an issue
    '''
    
    # Make sure we are going to manipulate the data and not text
    pto.parse()
    
    base_n = len(pto.get_image_lines())
    opt_n = len(ptoopt.get_optimizer_lines())
    if base_n != opt_n:
        raise Exception('Must have optimized same number images as images.  Base pto has %d and opt has %d' % (base_n, opt_n))
    opts = list()
    print
    for i in range(len(pto.get_image_lines())):
        il = pto.get_image_lines()[i]
        ol = ptoopt.optimizer_lines[i]
        for v in 'd e'.split():
            val = ol.get_variable(v)
            debug('Found variable val to be %s' % str(val))
            il.set_variable(v, val)
            debug('New IL: ' + str(il))
        debug()
        
class PTOptimizer:
    def __init__(self, project):
        self.project = project
        self.debug = False
        # In practice I tend to get around 25 so anything this big signifies a real problem
        self.rms_error_threshold = 250.0
        # If set to true will clear out all old optimizer settings
        # If PToptimizer gets old values in it will use them as a base
        self.reoptimize = True
    
    def verify_images(self):
        first = True
        for i in self.project.get_image_lines():
            if first:
                self.w = i.width()
                self.h = i.height()
                self.v = i.fov()
                first = False
            else:
                if self.w != i.width() or self.h != i.height() or self.v != i.fov():
                    print i.text
                    print 'Old width %d, height %d, view %d' % (self.w, self.h, self.v)
                    print 'Image width %d, height %d, view %d' % (i.width(), i.height(), i.fov())
                    raise Exception('Image does not match')
        
    def run(self):
        '''
        The base Hugin project seems to work if you take out a few things:
        Eb1 Eev0 Er1 Ra0 Rb0 Rc0 Rd0 Re0 Va1 Vb0 Vc0 Vd0 Vx-0 Vy-0
        So say generate a project file with all of those replaced
        
        In particular we will generate new i lines
        To keep our original object intact we will instead do a diff and replace the optimized things on the old project
        
        
        Output is merged into the original file and starts after a line with a single *
        Even Hugin wpon't respect this optimization if loaded in as is
        Gives lines out like this
        
        o f0 r0 p0 y0 v51 a0.000000 b0.000000 c0.000000 g-0.000000 t-0.000000 d-0.000000 e-0.000000 u10 -buf 
        These are the lines we care about
        
        C i0 c0  x3996.61 y607.045 X3996.62 Y607.039  D1.4009 Dx-1.15133 Dy0.798094
        Where D is the magnitutde of the distance and x and y are the x and y differences to fitted solution
        
        There are several other lines that are just the repeats of previous lines
        '''
        bench = Benchmark()
        
        # The following will assume all of the images have the same size
        self.verify_images()
        
        # Copy project so we can trash it
        project = self.project.copy()
        prepare_pto(project, self.reoptimize)
        
        pre_run_text = project.get_text()
        if 0:
            print
            print
            print 'PT optimizer project:'
            print pre_run_text
            print
            print
                
        
        # "PToptimizer out.pto"
        args = ["PToptimizer"]
        args.append(project.get_a_file_name())
        #project.save()
        rc = execute.without_output(args)
        if rc != 0:
            fn = '/tmp/pr0nstitch.optimizer_failed.pto'
            print
            print
            print 'Failed rc: %d' % rc
            print 'Failed project save to %s' % (fn,)
            try:
                open(fn, 'w').write(pre_run_text)
            except:
                print 'WARNING: failed to write failure'
            print
            print
            raise Exception('failed position optimization')
        # API assumes that projects don't change under us
        project.reopen()
        
        '''
        Line looks like this
        # final rms error 24.0394 units
        '''
        rms_error = None
        for l in project.get_comment_lines():
            if l.find('final rms error') >= 00:
                rms_error = float(l.split()[4])
                break
        print 'Optimize: RMS error of %f' % rms_error
        # Filter out gross optimization problems
        if self.rms_error_threshold and rms_error > self.rms_error_threshold:
            raise Exception("Max RMS error threshold %f but got %f" % (self.rms_error_threshold, rms_error))
        
        if self.debug:
            print 'Parsed: %s' % str(project.parsed)

        if self.debug:
            print
            print
            print
            print 'Optimized project:'
            print project
            #sys.exit(1)
        print 'Optimized project parsed: %d' % project.parsed

        print 'Merging project...'
        merge_pto(project, self.project)
        if self.debug:
            print self.project
        
        bench.stop()
        print 'Optimized project in %s' % bench
        
'''
Calculate average x/y position
NOTE: x/y deltas are positive right/down
But global coordinates are positive left,up
Return positive left/up convention to match global coordinate system
'''
def pair_check(project, l_il, r_il):
    # lesser line
    l_ili = l_il.get_index()
    # Find matching control points
    cps_x = []
    cps_y = []
    for cpl in project.control_point_lines:
        # applicable?
        if cpl.getv('n') == l_ili and cpl.getv('N') == r_il:
            # compute distance
            # note: these are relative coordinates to each image
            # and strictly speaking can't be directly compared
            # however, because the images are the same size the width/height can be ignored
            cps_x.append(cpl.getv('x') - cpl.getv('X'))
            cps_y.append(cpl.getv('y') - cpl.getv('Y'))
        elif cpl.getv('n') == r_il and cpl.getv('N') == l_ili:
            cps_x.append(cpl.getv('X') - cpl.getv('x'))
            cps_y.append(cpl.getv('Y') - cpl.getv('y'))
    
    # Possible that no control points due to failed stitch
    # or due to edge case
    if len(cps_x) == 0:
        return None
    else:
        return (1.0 * sum(cps_x)/len(cps_x),
                1.0 * sum(cps_y)/len(cps_y))

def pre_opt_core(project, icm, closed_set, pairsx, pairsy, order, verbose=False):
    iters = 0
    while True:
        iters += 1
        print 'Iters %d' % iters
        fixes = 0
        # no status prints here, this loop is very quick
        for y in xrange(icm.height()):
            for x in xrange(icm.width()):
                if (x, y) in closed_set:
                    continue
                img = icm.get_image(x, y)
                # Skip missing images
                if img is None:
                    continue
                
                # see what we can gather from
                # list of [xcalc, ycalc]
                points = []
                
                # X
                # left
                # do we have a fixed point to the left?
                o = closed_set.get((x - order, y), None)
                if o:
                    d = pairsx.get((x - order + 1, y), None)
                    # and a delta to get to it?
                    if d:
                        dx, dy = d
                        points.append((o[0] - dx * order, o[1] - dy * order))
                # right
                o = closed_set.get((x + order, y), None)
                if o:
                    d = pairsx.get((x + order, y), None)
                    if d:
                        dx, dy = d
                        points.append((o[0] + dx * order, o[1] + dy * order))
                
                # Y
                o = closed_set.get((x, y - order), None)
                if o:
                    d = pairsy.get((x, y - order + 1), None)
                    if d:
                        dx, dy = d
                        points.append((o[0] - dx * order, o[1] - dy * order))
                o = closed_set.get((x, y + order), None)
                if o:
                    d = pairsy.get((x, y + order), None)
                    if d:
                        dx, dy = d
                        points.append((o[0] + dx * order, o[1] + dy * order))
                
                # Nothing useful?
                if len(points) == 0:
                    continue

                if verbose:
                    print '  %03dX, %03dY: setting' % (x, y)
                    for p in points:
                        print '    ', p
                
                # use all available anchor points from above
                il = project.img_fn2il[img]
                
                # take average of up to 4 
                points_x = [p[0] for p in points]
                xpos = 1.0 * sum(points_x) / len(points_x)
                il.set_x(xpos)
                
                points_y = [p[1] for p in points]
                ypos = 1.0 * sum(points_y) / len(points_y)
                il.set_y(ypos)
                
                closed_set[(x, y)] = (xpos, ypos)
                fixes += 1
        print 'Iter fixes: %d' % fixes
        if fixes == 0:
            print 'Break on stable output'
            print '%d iters' % iters
            break

def pre_opt_propagate(project, icm, closed_set, pairsx, pairsy, order, anch_cr):
    '''
    Take average delta and space tiles based on any adjacent placed tile
    '''
    def avg(vals, s):
        vals = filter(lambda x: x is not None, vals)
        vals = [s(val) for val in vals]
        return sum(vals) / len(vals)
    if len(pairsx) > 0:
        pairsx_avg = (avg(pairsx.values(), lambda x: x[0]), avg(pairsx.values(), lambda x: x[1]))
    else:
        pairsx_avg = None
    print 'pairsx: %s' % (pairsx_avg,)
    if len(pairsy) > 0:
        pairsy_avg = (avg(pairsy.values(), lambda x: x[0]), avg(pairsy.values(), lambda x: x[1]))
    else:
        pairsy_avg = None
    print 'pairsy: %s' % (pairsy_avg,)

    iters = 0
    while True:
        iters += 1
        print 'Iters %d' % iters
        fixes = 0
        # no status prints here, this loop is very quick
        for y in xrange(icm.height()):
            for x in xrange(icm.width()):
                if (x, y) in closed_set:
                    continue
                img = icm.get_image(x, y)
                # Skip missing images
                if img is None:
                    continue
                
                #print 'Trying to fix %s' % img
                # see what we can gather from
                # list of [xcalc, ycalc]
                points = []
                
                # X
                # left
                # do we have a fixed point to the left?
                o = closed_set.get((x - order, y), None)
                if o and pairsx_avg:
                    dx, dy = pairsx_avg
                    px, py = (o[0] - dx * order, o[1] - dy * order)
                    #print "  L calc (%0.1f, %0.1f)" % (px, py)
                    points.append((px, py))
                # right
                o = closed_set.get((x + order, y), None)
                if o and pairsx_avg:
                    dx, dy = pairsx_avg
                    px, py = (o[0] + dx * order, o[1] + dy * order)
                    #print "  R calc (%0.1f, %0.1f)" % (px, py)
                    points.append((px, py))
                
                # Y
                o = closed_set.get((x, y - order), None)
                if o and pairsy_avg:
                    dx, dy = pairsy_avg
                    px, py = (o[0] - dx * order, o[1] - dy * order)
                    #print "  U calc (%0.1f, %0.1f)" % (px, py)
                    points.append((px, py))
                o = closed_set.get((x, y + order), None)
                if o and pairsy_avg:
                    dx, dy = pairsy_avg
                    px, py = (o[0] + dx * order, o[1] + dy * order)
                    #print "  D calc (%0.1f, %0.1f)" % (px, py)
                    points.append((px, py))
                
                # Nothing useful?
                if len(points) == 0:
                    #print "  Couldn't match points :("
                    continue

                # use all available anchor points from above
                il = project.img_fn2il[img]
                
                # take average of up to 4 
                points_x = [p[0] for p in points]
                xpos = 1.0 * sum(points_x) / len(points_x)
                il.set_x(xpos)
                
                points_y = [p[1] for p in points]
                ypos = 1.0 * sum(points_y) / len(points_y)
                il.set_y(ypos)
                
                closed_set[(x, y)] = (xpos, ypos)
                fixes += 1
        print 'Iter fixes: %d' % fixes
        if fixes == 0:
            print 'Break on stable output'
            print '%d iters' % iters
            break

    print
    print
    print 'Final pass: guestimate'

    # one last attempt: just find an anchor and roll with it
    (anch_c, anch_r) = anch_cr
    # should be 0.0, 0.0
    anch_x, anch_y = closed_set[anch_cr]
    print 'Using anchor image c%d, r%d' % (anch_c, anch_r)

    for r in xrange(icm.height()):
        for c in xrange(icm.width()):
            if (c, r) in closed_set:
                continue
            img = icm.get_image(c, r)
            # Skip missing images
            if img is None:
                continue
            
            # ship it: "all working image programs have an even number of sign errors"
            xpos = anch_x - (c - anch_c) * pairsx_avg[0] - (r - anch_r) * pairsy_avg[0]
            ypos = anch_y - (c - anch_c) * pairsx_avg[1] - (r - anch_r) * pairsy_avg[1]
            print 'WARNING: rough estimate on %s: %0.1f, %0.1f' % (img, xpos, ypos)
            # use all available anchor points from above
            il = project.img_fn2il[img]
            il.set_x(xpos)
            il.set_y(ypos)
            closed_set[(c, r)] = (xpos, ypos)

def check_pair_outlier(icm, pairs, xorder, yorder, stdev=3):
    print 'Checking for outliers'
    print 'Computing stat'
    pointsx = []
    pointsy = []
    for y in xrange(0, icm.height(), yorder):
        for x in xrange(0, icm.width(), xorder):
            # Missing image
            try:
                d = pairs[(x, y)]
            except KeyError:
                continue
            # No control points
            if d is None:
                continue
            dx, dy = d
            pointsx.append(dx)
            pointsy.append(dy)

    x_sd = statistics.stdev(pointsx)
    x_u = statistics.mean(pointsx)
    print 'X mean: %0.3f' % x_u
    print 'X SD:   %0.3f' % x_sd

    y_sd = statistics.stdev(pointsy)
    y_u = statistics.mean(pointsy)
    print 'Y mean: %0.3f' % y_u
    print 'Y SD:   %0.3f' % y_sd

    if not stdev:
        print 'stdev filter: none'
    else:
        print 'stdev filter: %0.3f' % stdev
        '''
        x_thresh = abs(x_u) + abs(x_sd) * stdev
        y_thresh = abs(y_u) + abs(y_sd) * stdev
        print 'X thresh: %0.3f' % x_thresh
        print 'Y thresh: %0.3f' % y_thresh
        '''
        x_min = x_u - x_sd * stdev
        x_max = x_u + x_sd * stdev
        print 'X : %0.3f to %0.3f' % (x_min, x_max)
        y_min = y_u - y_sd * stdev
        y_max = y_u + y_sd * stdev
        print 'Y : %0.3f to %0.3f' % (y_min, y_max)
        
        removed = 0
        npairs = 0
        for y in xrange(0, icm.height(), yorder):
            for x in xrange(0, icm.width(), xorder):
                # Missing image
                try:
                    d = pairs[(x, y)]
                except KeyError:
                    continue
                # No control points
                if d is None:
                    continue
                npairs += 1
                dx, dy = d
                if (dx < x_min or dx > x_max) or (dy < y_min or dy > y_max):
                    print 'Ignoring x%d y%d' % (x, y)
                    pairs[(x, y)] = None
                    removed += 1
        print 'Removed %d / %d pairs' % (removed, npairs)

def anchor(project, icm):
    '''
    Chose an anchor image to stitch project
    The image is located in the given project and the (col, row) is returned
    Exception thrown if an anchor can't be chosen
    (happens if no control points)
    '''

    ret = []

    def try_anch(anch_c, anch_r):
        # Image must exist
        img = icm.get_image(anch_c, anch_r)
        if img is None:
            return False
        # Must be linked to at least one other image
        il = project.img_fn2il[img]
        cpls = img_cpls(project, il.get_index())
        if len(cpls) == 0:
            return False
        # Only anchor if control points
        print 'Chose anchor image: %s' % img
        ret.append((anch_c, anch_r))
        anch_il = project.img_fn2il[img]
        anch_il.set_x(0.0)
        anch_il.set_y(0.0)
        return True

    def try_anchs():
        # repair holes by successive passes
        # contains x,y points that have been finalized
        for anch_r in xrange(0, icm.height()):
            for anch_c in xrange(0, icm.width()):
                if try_anch(anch_c, anch_r):
                    return
        else:
            raise Exception('No images...')

    # Try center first, then work outward 
    # Center should propagate the lowest error
    def dxdys():
        for dx in (0, 1, -1):
            for dy in (0, 1, -1):
                yield dx, dy
    for (dx, dy) in dxdys():
        col = icm.width() / 2 + dx
        col = min(max(0, col), icm.width() - 1)
        row = icm.height() / 2 + dy
        row = min(max(0, row), icm.height() - 1)
        if try_anch(col, row):
            break
    else:
        try_anchs()

    return ret[0]

def pre_opt(project, icm, verbose=False, stdev=None):
    '''
    Generates row/col to use for initial image placement
    spiral pattern outward from center
    
    Assumptions:
    -All images must be tied together by at least one control point
    
    NOTE:
    If we produce a bad mapping ptooptimizer may throw away our hint
    '''
    # reference position
    #xc = icm.width() / 2
    #yc = icm.height() / 2
    project.build_image_fn_map()
    
    def printd(s):
        if verbose:
            print s

    rms_this = get_rms(project)
    if rms_this is not None:
        print 'Pre-opt: exiting project RMS error: %f' % rms_this
    
    # NOTE: algorithm will still run with missing control points to best of its ability
    # however, its expected that user will only run it on copmlete data sets
    if verbose:
        fail = False
        counts = {}
        for cpl in project.get_control_point_lines():
            n = cpl.getv('n')
            counts[n] = counts.get(n, 0) + 1
            N = cpl.getv('N')
            counts[N] = counts.get(N, 0) + 1
        print 'Control point counts:'
        for y in xrange(0, icm.height()):
            for x in xrange(0, icm.width()):
                img = icm.get_image(x, y)
                if img is None:
                    continue
                il = project.img_fn2il[img]
                ili = il.get_index()
                count = counts.get(ili, 0)
                print '  %03dX, %03dY: %d' % (x, y, count)
                if count == 0:
                    print '    ERROR: no control points'
                    fail = True
        if fail:
            raise Exception('One or more images do not have control points')

    def build_pairs():
        # dictionary of results so that we can play around with post-processing result
        # This step takes by far the longest in the optimization process
        pairsx = {}
        pairsy = {}
        # start with simple algorithm where we just sweep left/right
        for y in xrange(0, icm.height()):
            print 'Calc delta with Y %d / %d' % (y + 1, icm.height())
            for x in xrange(0, icm.width()):
                img = icm.get_image(x, y)
                # Skip missing images
                if img is None:
                    continue
                il = project.img_fn2il[img]
                ili = il.get_index()
                if x > 0:
                    img = icm.get_image(x - 1, y)
                    if img:
                        pairsx[(x, y)] = pair_check(project, project.img_fn2il[img], ili)
                    else:
                        pairsx[(x, y)] = None
                if y > 0:
                    img = icm.get_image(x, y - 1)
                    if img:
                        pairsy[(x, y)] = pair_check(project, project.img_fn2il[img], ili)
                    else:
                        pairsx[(x, y)] = None
        return pairsx, pairsy
    # (x, y) keyed dict gives the delta to the left or up
    # That is, (0, 0) is not included
    pairsx, pairsy = build_pairs()

    if verbose:
        print 'Delta map'
        for y in xrange(0, icm.height()):
            for x in xrange(0, icm.width()):
                print '  %03dX, %03dY' % (x, y)
                
                p = pairsx.get((x, y), None)
                if p is None:
                    print '    X: none'
                else:
                    print '    X: %0.3fx, %0.3fy' % (p[0], p[1])

                p = pairsy.get((x, y), None)
                if p is None:
                    print '    Y: none'
                else:
                    print '    Y: %0.3fx, %0.3fy' % (p[0], p[1])
    
    print
    check_pair_outlier_angle(icm, pairsx, pairsy)
    print
    check_pair_outlier(icm, pairsx, xorder=1, yorder=2, stdev=stdev)
    print
    check_pair_outlier(icm, pairsy, xorder=1, yorder=1, stdev=stdev)
    print

    anch_c, anch_r = anchor(project, icm)
    closed_set = {(anch_c, anch_r): (0.0, 0.0)}

    print
    print
    print 'First pass: adjacent images'
    pre_opt_core(project, icm, closed_set, pairsx, pairsy, order=1, verbose=verbose)
    
    print
    print
    print 'Second pass: adjacent adjacent images'
    pre_opt_core(project, icm, closed_set, pairsx, pairsy, order=2, verbose=verbose)
    
    print
    print
    print 'Third pass: propagate adjacent'
    pre_opt_propagate(project, icm, closed_set, pairsx, pairsy, order=1, anch_cr=(anch_c, anch_r))


    print
    print
    print 'Checking for critical images'
    for y in xrange(icm.height()):
        for x in xrange(icm.width()):
            if (x, y) in closed_set:
                continue
            img = icm.get_image(x, y)
            # Skip missing images
            if img is None:
                continue
            print '  WARNING: un-located image %s' % img

    print
    print
    print 'Checking for poorly optimized images'
    check_poor_opt(project, icm)

    print
    print
    if verbose:
        print 'Final position optimization:'
        for y in xrange(icm.height()):
            for x in xrange(icm.width()):
                p = closed_set.get((x, y))
                if p is None:
                    print '  % 3dX, % 3dY: none' % (x, y)
                else:
                    print '  % 3dX, % 3dY: %6.1fx, %6.1fy' % (x, y, p[0], p[1])

    rms_this = get_rms(project)
    print 'Pre-opt: final RMS error: %f' % rms_this

    # internal use only
    return closed_set

def get_rms(project):
    '''Calculate the root mean square error between control points'''
    rms = 0.0
    for cpl in project.control_point_lines:
        imgn = project.image_lines[cpl.get_variable('n')]
        imgN = project.image_lines[cpl.get_variable('N')]
        
        # global coordinates (d/e) are positive upper left
        # but image coordinates (x/X//y/Y) are positive down right
        # wtf?
        # invert the sign so that the math works out
        try:
            dx2 = ((imgn.getv('d') - cpl.getv('x')) - (imgN.getv('d') - cpl.getv('X')))**2
            dy2 = ((imgn.getv('e') - cpl.getv('y')) - (imgN.getv('e') - cpl.getv('Y')))**2
        # Abort RMS if not all variables defined
        except TypeError:
            return None
        
        if 0:
            print 'iter'
            print '  ', imgn.text
            print '  ', imgN.text
            print '  ', imgn.getv('d'), cpl.getv('x'), imgN.getv('d'), cpl.getv('X')
            print '  %f vs %f' % ((imgn.getv('d') + cpl.getv('x')), (imgN.getv('d') + cpl.getv('X')))
            print '  ', imgn.getv('e'), cpl.getv('y'), imgN.getv('e'), cpl.getv('Y')
            print '  %f vs %f' % ((imgn.getv('e') + cpl.getv('y')), (imgN.getv('e') + cpl.getv('Y')))
        
        this = math.sqrt(dx2 + dy2)
        if 0:
            print '  ', this
        rms += this
    return rms / len(project.control_point_lines)

def check_poor_opt(project, icm=None):
    # FIXME: calculate from actual image size + used overlap
    # Use an expected max angle
    imgx = 1632
    imgy = 1224

    ox = 0.7
    oy = 0.7
    if os.path.exists('out.json'):
        j = json.load(open('out.json', 'r'))
        ox = j['x']['overlap']
        oy = j['y']['overlap']
    ox *=  imgx
    oy *=  imgy
    # First order tolerance
    # ie x change in x direction
    tol_1 = ox + 175
    # Second order tolernace
    # ie x change in y direction
    tol_2 = 175

    def ildiff(imgl, imgr):
        '''
        return l - r as dx, dy
        '''
        ill = project.img_fn2il[imgl]
        ilr = project.img_fn2il[imgr]
        dx = ill.x() - ilr.x()
        dy = ill.y() - ilr.y()
        return dx, dy

    def check(refr, refc):
        ret = True
        img = icm.get_image(refc, refr)
        # Skip missing imagesx
        if img is None:
            return True

        # Global coordinates positive upper left
        # icm positive upper 
        if refc > 0:
            imgl = icm.get_image(refc - 1, refr)
            if imgl:
                dx, dy = ildiff(imgl, img)
                # Expected delta vs actual
                got = abs(dx - ox)
                if got > tol_1:
                    print '%s-%s: x-x tolerance 1 %d > expect %d' % (img, imgl, got, tol_1)
                    ret = False
                got = abs(dy)
                if got > tol_2:
                    print '%s-%s: y-y tolerance 2 %d > expect %d' % (img, imgl, got, tol_2)
                    ret = False
        if refr > 0:
            imgl = icm.get_image(refc, refr - 1)
            if imgl:
                dx, dy = ildiff(imgl, img)
                # Expected delta vs actual
                got = abs(dx)
                if got > tol_2:
                    print '%s-%s: x-x tolerance 2 %d > expect %d' % (img, imgl, got, tol_2)
                    ret = False
                got = abs(dy - oy)
                if got > tol_1:
                    print '%s-%s: y-y tolerance 1 %d > expect %d' % (img, imgl, got, tol_1)
                    ret = False
        return ret

    fails = 0
    for refr in xrange(icm.height()):
        for refc in xrange(icm.width()):
            if not check(refr, refc):
                fails += 1
    if fails:
        print 'WARNING: %d suspicious optimization result(s)' % fails
    else:
        print 'OK'

def check_pair_outlier_angle(icm, pairsx, pairsy):
    print 'Checking for outliers by angle'
    #return

    # FIXME: calculate from actual image size + used overlap
    # Use an expected max angle
    imgx = 1632
    imgy = 1224

    ox = 0.7
    oy = 0.7
    if os.path.exists('out.json'):
        j = json.load(open('out.json', 'r'))
        ox = j['x']['overlap']
        oy = j['y']['overlap']
    ox *=  imgx
    oy *=  imgy
    # First order tolerance
    # ie x change in x direction
    tolx_1 = ox + 165
    toly_1 = oy + 165
    # Second order tolernace
    # ie x change in y direction
    tol_2 = 165

    fails = 0
    npairs = [0, 0]

    '''
    worst_dxdc = 0.0
    worst_dxdr = 0.0
    worst_dydc = 0.0
    worst_dydr = 0.0
    '''
    def check(refc, refr):
        ret = True
        pairx = pairsx.get((refc, refr), None)
        if pairx is not None:
            npairs[0] += 1
            dx, dy = pairx
            img = icm.get_image(refc, refr)
            imgl = icm.get_image(refc - 1, refr)
            got = abs(dx - ox)
            if got > tolx_1:
                print '%s-%s: x-x tolerance 1 %d > expect %d' % (img, imgl, got, tolx_1)
                ret = False
                pairsx[(refc, refr)] = None
                pairsy[(refc, refr)] = None
            got = abs(dy)
            if got > tol_2:
                print '%s-%s: y-y tolerance 2 %d > expect %d' % (img, imgl, got, tol_2)
                ret = False
                pairsx[(refc, refr)] = None
                pairsy[(refc, refr)] = None
        pairy = pairsy.get((refc, refr), None)
        if pairy is not None:
            npairs[1] += 1
            dx, dy = pairy
            img = icm.get_image(refc, refr)
            imgl = icm.get_image(refc, refr - 1)
            got = abs(dx)
            if got > tol_2:
                print '%s-%s: x-x tolerance 2 %d > expect %d' % (img, imgl, got, tol_2)
                ret = False
                pairsx[(refc, refr)] = None
                pairsy[(refc, refr)] = None
            got = abs(dy - oy)
            if got > toly_1:
                print '%s-%s: y-y tolerance 1 %d > expect %d' % (img, imgl, got, toly_1)
                ret = False
                pairsx[(refc, refr)] = None
                pairsy[(refc, refr)] = None
        return ret

    for refr in xrange(icm.height()):
        for refc in xrange(icm.width()):
            if not check(refc, refr):
                fails += 1

    if fails:
        print 'WARNING: removed %d / (%dx %dy) suspicious optimization result(s)' % (fails, npairs[0], npairs[1])
    else:
        print 'OK'

# TODO: give some more thought and then delete entirely
def chaos_opt(project, icm):
    raise Exception("Isn't helpful, don't use")
    pos_xy = pre_opt(project, icm)
    
    verbose = 0
    #verbose = 1
    def printd(s):
        if verbose:
            print s
    
    
    il = project.img_fn2il[icm.get_image(0, 0)]
    il.set_x(0.0)
    il.set_y(0.0)
    
    iters = 0
    rms_last = None
    while True:
        iters += 1
        print 'Iters %d' % iters

        rms_this = get_rms(project)
        print 'RMS error: %f' % rms_this
        if rms_last is not None and (rms_last - rms_this) < 0.01:
            print 'Break on minor improvement'
            break
        
        open_set = set()
        for y in xrange(icm.height()):
            for x in xrange(icm.width()):
                open_set.add((x, y))
        while len(open_set) > 0:
            def process():
                il0 = project.img_fn2il[icm.get_image(pref[0], pref[1])]
                points = []
                x, y = pref
        
                # left
                o = pos_xy.get((x - 1, y), None)
                if o:
                    d = pair_check(project, project.img_fn2il[icm.get_image(pref[0] - 1, pref[1])], il0)
                    # and a delta to get to it?
                    if d:
                        dx, dy = d
                        points.append((o[0] + dx, o[1] + dy))
                # right
                o = pos_xy.get((x + 1, y), None)
                if o:
                    d = pair_check(project, project.img_fn2il[icm.get_image(pref[0] + 1, pref[1])], il0)
                    if d:
                        dx, dy = d
                        points.append((o[0] + dx, o[1] + dy))
                
                # Y
                o = pos_xy.get((x, y - 1), None)
                if o:
                    d = pair_check(project, project.img_fn2il[icm.get_image(pref[0], pref[1] - 1)], il0)
                    if d:
                        dx, dy = d
                        points.append((o[0] + dx, o[1] + dy))
                o = pos_xy.get((x, y + 1), None)
                if o:
                    d = pair_check(project, project.img_fn2il[icm.get_image(pref[0], pref[1] + 1)], il0)
                    if d:
                        dx, dy = d
                        points.append((o[0] + dx, o[1] + dy))
                
                # Nothing useful?
                if len(points) == 0:
                    return
        
                if verbose:
                    print '  %03dX, %03dY: setting' % (x, y)
                    for p in points:
                        print '    ', p
                
                # use all available anchor points from above
                il = project.img_fn2il[icm.get_image(x, y)]
                
                # take average of up to 4 
                points_x = [p[0] for p in points]
                xpos = 1.0 * sum(points_x) / len(points_x)
                il.set_x(xpos)
                
                points_y = [p[1] for p in points]
                ypos = 1.0 * sum(points_y) / len(points_y)
                il.set_y(ypos)
                
                # Adjust new position
                pos_xy[(x, y)] = (xpos, ypos)
            
            pref = random.sample(open_set, 1)[0]
            process()
            open_set.remove(pref)

'''
Assumes images are in a grid to simplify workflow management
Seed
    Predicts linear position based on average control point distance
    starting from center tile
Iterate
    Optimizes random xy regions
    Takes advantage of existing optimizer while reducing problem space to reduce o(n**2) issues
'''
class ChaosOptimizer:
    def __init__(self, project):
        self.project = project
        self.debug = False
        self.icm = None
        self.rms_error_threshold = 250.0
    
    def verify_images(self):
        first = True
        for i in self.project.get_image_lines():
            if first:
                self.w = i.width()
                self.h = i.height()
                self.v = i.fov()
                first = False
            else:
                if self.w != i.width() or self.h != i.height() or self.v != i.fov():
                    print i.text
                    print 'Old width %d, height %d, view %d' % (self.w, self.h, self.v)
                    print 'Image width %d, height %d, view %d' % (i.width(), i.height(), i.fov())
                    raise Exception('Image does not match')
    
    def run(self):
        bench = Benchmark()
        
        # The following will assume all of the images have the same size
        self.verify_images()
        
        fns = []
        # Copy project so we can trash it
        project = self.project.copy()
        for il in project.get_image_lines():
            fns.append(il.get_name())
        self.icm = ImageCoordinateMap.from_tagged_file_names(fns)

        chaos_opt(project, self.icm)
        prepare_pto(project, reoptimize=False)
        
        # "PToptimizer out.pto"
        args = ["PToptimizer"]
        args.append(project.get_a_file_name())
        print 'Optimizing %s' % project.get_a_file_name()
        #raise Exception()
        #self.project.save()
        rc = execute.without_output(args)
        if rc != 0:
            raise Exception('failed position optimization')
        # API assumes that projects don't change under us
        project.reopen()
        
        # final rms error 24.0394 units
        rms_error = None
        for l in project.get_comment_lines():
            if l.find('final rms error') >= 00:
                rms_error = float(l.split()[4])
                break
        print 'Optimize: RMS error of %f' % rms_error
        # Filter out gross optimization problems
        if self.rms_error_threshold and rms_error > self.rms_error_threshold:
            raise Exception("Max RMS error threshold %f but got %f" % (self.rms_error_threshold, rms_error))
        
        print 'Merging project...'
        merge_pto(project, self.project)
        if self.debug:
            print self.project
        
        bench.stop()
        print 'Optimized project in %s' % bench

class PreOptimizer:
    def __init__(self, project):
        self.project = project
        self.debug = False
        self.icm = None
        self.stdev = None
    
    def verify_images(self):
        first = True
        for i in self.project.get_image_lines():
            if first:
                self.w = i.width()
                self.h = i.height()
                self.v = i.fov()
                first = False
            else:
                if self.w != i.width() or self.h != i.height() or self.v != i.fov():
                    print i.text
                    print 'Old width %d, height %d, view %d' % (self.w, self.h, self.v)
                    print 'Image width %d, height %d, view %d' % (i.width(), i.height(), i.fov())
                    raise Exception('Image does not match')
    
    def run(self):
        bench = Benchmark()
        
        # The following will assume all of the images have the same size
        self.verify_images()
        
        fns = []
        # Copy project so we can trash it
        project = self.project.copy()
        for il in project.get_image_lines():
            fns.append(il.get_name())
        self.icm = ImageCoordinateMap.from_tagged_file_names(fns)

        print 'Verbose: %d' % self.debug
        print 'working direclty on %s' % self.project.get_a_file_name()
        pre_opt(self.project, self.icm, verbose=self.debug, stdev=self.stdev)
        
        bench.stop()
        print 'Optimized project in %s' % bench

class PreOptimizerPT:
    def __init__(self, project):
        self.project = project
        self.debug = False
        self.icm = None
        self.rms_error_threshold = 250.0
    
    def verify_images(self):
        first = True
        for i in self.project.get_image_lines():
            if first:
                self.w = i.width()
                self.h = i.height()
                self.v = i.fov()
                first = False
            else:
                if self.w != i.width() or self.h != i.height() or self.v != i.fov():
                    print i.text
                    print 'Old width %d, height %d, view %d' % (self.w, self.h, self.v)
                    print 'Image width %d, height %d, view %d' % (i.width(), i.height(), i.fov())
                    raise Exception('Image does not match')
    
    def run(self):
        bench = Benchmark()
        
        # The following will assume all of the images have the same size
        self.verify_images()
        
        fns = []
        # Copy project so we can trash it
        project = self.project.copy()
        for il in project.get_image_lines():
            fns.append(il.get_name())
        self.icm = ImageCoordinateMap.from_tagged_file_names(fns)

        pre_opt(project, self.icm)
        prepare_pto(project, reoptimize=False)
        
        # "PToptimizer out.pto"
        args = ["PToptimizer"]
        args.append(project.get_a_file_name())
        print 'Optimizing %s' % project.get_a_file_name()
        #raise Exception()
        #self.project.save()
        rc = execute.without_output(args)
        if rc != 0:
            raise Exception('failed position optimization')
        # API assumes that projects don't change under us
        project.reopen()
        
        # final rms error 24.0394 units
        rms_error = None
        for l in project.get_comment_lines():
            if l.find('final rms error') >= 00:
                rms_error = float(l.split()[4])
                break
        print 'Optimize: RMS error of %f' % rms_error
        # Filter out gross optimization problems
        if self.rms_error_threshold and rms_error > self.rms_error_threshold:
            raise Exception("Max RMS error threshold %f but got %f" % (self.rms_error_threshold, rms_error))
        
        print 'Merging project...'
        merge_pto(project, self.project)
        if self.debug:
            print self.project
        
        bench.stop()
        print 'Optimized project in %s' % bench


def usage():
    print 'optimizer <file in> [file out]'
    print 'If file out is not given it will be file in'

if __name__ == "__main__":
    from pr0ntools.stitch.pto.project import PTOProject

    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    file_name_in = sys.argv[1]
    if len(sys.argv) > 2:
        file_name_out = sys.argv[2]
    else:
        file_name_out = file_name_in
    
    print 'Loading raw project...'
    project = PTOProject.from_file_name(file_name_in)
    print 'Creating optimizer...'
    optimizer = PTOptimizer(project)
    #self.assertTrue(project.text != None)
    print 'Running optimizer...'
    print 'Parsed main pre-run: %s' % str(project.parsed)
    optimizer.run()
    print 'Parsed main: %d' % project.parsed
    print 'Saving...'
    project.save_as(file_name_out)
    print 'Parsed main done: %s' % str(project.parsed)

