#!/usr/bin/env python
'''
Attempt to optimize faster by optimize sub-tiles and then combining into a larger project
'''

from pr0ntools import execute
from pr0ntools.pimage import PImage
from pr0ntools.stitch.pto.util import *
from pr0ntools.benchmark import Benchmark
from pr0ntools.stitch.pto.image_line import ImageLine
from pr0ntools.stitch.pto.variable_line import VariableLine
from pr0ntools.stitch.pto.control_point_line import ControlPointLine
from pr0ntools.stitch.pto.project import PTOProject
import sys
import math
from pr0ntools.stitch.image_coordinate_map import ImageCoordinateMap
import os
import sys
from pr0ntools.pimage import PImage
try:
    import scipy
    from scipy import polyval, polyfit
except ImportError:
    scipy = None

def debug(s = ''):
    pass


'''
Second order linear system of the form:
r = c0 x0 + c1 x1 + c2

TODO: consider learning NumPy...
This is simple enough that its not justified yet
'''

def regress_row(m, pto, cols, rows, selector, allow_missing = False):
    '''
    pto: pto to optimize
    m: image coordinate map for pto
    rows: which rows to use
    selector: gets either x or y coordinate
    '''
    # Discard the constants, we will pick a reference point later
    slopes = []
    for row in rows:
        '''
        For each column find a y position error
        y = col * c0 + c1
        '''
        fit_cols = []
        deps = []
        for col in cols:
            fn = m.get_image(col, row)
            if fn is None:
                if allow_missing:
                    continue
                raise Exception('c%d r%d not in map' % (col, row))
            il = pto.get_image_by_fn(fn)
            if il is None:
                raise Exception('Could not find %s in map' % fn)
            fit_cols.append(col)
            selected = selector(il)
            if selected is None:
                raise Exception('Reference image line is missing x/y position: %s' % il)
            deps.append(selected)
        if len(fit_cols) == 0:
            if not allow_missing:
                raise Exception('No matches')
            continue
        
        if 0:
            print 'Fitting polygonomial'
            print fit_cols
            print deps
        
        # Find x/y given a col
        (c0, _c1) = polyfit(fit_cols, deps, 1)
        slopes.append(c0)
    if len(slopes) == 0:
        if not allow_missing:
            raise Exception('No matches')
        # No dependence
        return 0.0
    # XXX: should remove outliers
    return sum(slopes) / len(slopes)

def regress_col(m, pto, cols, rows, selector, allow_missing = False):
    # Discard the constants, we will pick a reference point later
    slopes = []
    for col in cols:
        '''
        For each row find an y position
        y = row * c0 + c1
        '''
        fit_rows = []
        deps = []
        for row in rows:
            fn = m.get_image(col, row)
            if fn is None:
                if allow_missing:
                    continue
                raise Exception('c%d r%d not in map' % (col, row))
            il = pto.get_image_by_fn(fn)
            if il is None:
                raise Exception('Could not find %s in map' % fn)
            fit_rows.append(row)
            deps.append(selector(il))
        
        if len(fit_rows) == 0:
            if not allow_missing:
                raise Exception('No matches')
            continue
        (c0, _c1) = polyfit(fit_rows, deps, 1)
        slopes.append(c0)
    if len(slopes) == 0:
        if not allow_missing:
            raise Exception('No matches')
        # No dependence
        return 0.0
    # XXX: should remove outliers
    return sum(slopes) / len(slopes)

def calc_constants(order, m_real, pto_ref,
        c0s, c1s, c3s, c4s,
        m_ref = None, allow_missing=False, col_border=0, row_border=0):
    if m_ref is None:
        m_ref = m_real
    
    ref_fns = pto_ref.get_file_names()
    
    c2s = []
    c5s = []
    # Only calculate relative to central area
    for cur_order in range(order):
        this_c2s = []
        this_c5s = []
        candidates = 0
        for col in range(0 + col_border, m_real.width() - col_border):
            for row in range(0 + row_border, m_real.height() - row_border):
                candidates += 1
                fn = m_real.get_image(col, row)
                if not fn in ref_fns:
                    continue
                if fn is None:
                    if not allow_missing:
                        raise Exception('Missing item')
                    continue
                il = pto_ref.get_image_by_fn(fn)
                if il is None:
                    raise Exception('%s should have been in ref' % fn)
                try:
                    # x = c0 * c + c1 * r + c2
                    row_order = row % order
                    if row_order == cur_order:
                        cur_x = cur_x = il.x() - c0s[row_order] * col - c1s[row_order] * row
                        this_c2s.append(cur_x)
            
                    # y = c3 * c + c4 * r + c5
                    col_order = col % order
                    if col_order == cur_order:
                        cur_y = il.y() - c3s[col_order] * col - c4s[col_order] * row
                        this_c5s.append(cur_y)
                
                    #print '%s: x%g y%g' % (fn, cur_x, cur_y)
                
                except:
                    print
                    print il
                    print c0s, c1s, c3s, c4s
                    print col, row
                    print 
            
                    raise
        
        print 'Order %u: %u even solutions' % (cur_order, len(this_c2s))
        print 'Order %u: %u even solutions' % (cur_order, len(this_c5s))
        if 1:
            c2s.append(sum(this_c2s) / len(this_c2s))
            c5s.append(sum(this_c5s) / len(this_c5s))
        else:
            c2s.append(this_c2s[0])
            c5s.append(this_c5s[0])
    return (c2s, c5s)
    
def rms_errorl(l):
    return (sum([(i - sum(l) / len(l))**2 for i in l]) / len(l))**0.5
    
def rms_error_diff(l1, l2):
    if len(l1) != len(l2):
        raise ValueError("Lists must be identical")
    return (sum([(l2[i] - l1[i])**2 for i in range(len(l1))]) / len(l1))**0.5

def linearize(pto, pto_ref = None, allow_missing = False, order = 2):
    if order is 0:
        raise Exception('Can not have order 0')
    if type(order) != type(0):
        raise Exception('Order is bad type')
    
    '''
    Our model should be like this:
    -Each axis will have some degree of backlash.  This backlash will create a difference between adjacent rows / cols
    -Axes may not be perfectly adjacent
        The naive approach would give:
            x = c * dx + xc
            y = r * dy + yc
        But really we need this:
            x = c * dx + r * dx/dy + xc
            y = c * dy/dx + r * dy + yc
        Each equation can be solved separately
        Need 3 points to solve each and should be in the expected direction of that line
        
        
    Perform a linear regression on each row/col?
    Might lead to very large y = mx + b equations for the column math
    '''
    
    if pto_ref is None:
        pto_ref = pto

    '''
    Phase 1: calculate linear system
    '''
    # Start by building an image coordinate map so we know what x and y are
    pto_ref.parse()
    ref_fns = pto_ref.get_file_names()
    real_fns = pto.get_file_names()
    print 'Files (all: %d, ref: %d):' % (len(real_fns), len(ref_fns))
    if 0:
        for fn in real_fns:
            if fn in ref_fns:
                ref_str = '*'
            else:
                ref_str = ' '
            print '  %s%s' % (ref_str, fn)
    m_ref = ImageCoordinateMap.from_tagged_file_names(ref_fns)
    # Ref likely does not cover the entire map
    ((ref_x0, ref_x1), (ref_y0, ref_y1)) = m_ref.active_box()
    print 'Reference map uses x(%d:%d), y(%d:%d)' % (ref_x0, ref_x1, ref_y0, ref_y1)

    #m_real = ImageCoordinateMap.from_tagged_file_names(real_fns)
    #print 'Real map uses x(%d:%d), y(%d:%d)' % (ref_x0, ref_x1, ref_y0, ref_y1)
    #m.debug_print()
    
    '''
    Ultimately trying to form this equation
    x = c0 * c + c1 * r + c2
    y = c3 * c + c4 * r + c5
    
    Except that constants will also have even and odd varities
    c2 and c5 will be taken from reasonable points of reference, likely (0, 0) or something like that
    '''
    
    c0s = []
    c1s = []
    c3s = []
    c4s = []
    for cur_order in xrange(order):
        # Ex: ref_x0 = 3
        # cur_order 0: start 4
        # cur_order 1: start 3
        if ref_x0 % order == cur_order:
            reg_x0 = ref_x0
        else:
            reg_x0 = ref_x0 + 1
        if ref_y0 % order == cur_order:
            reg_y0 = ref_y0
        else:
            reg_y0 = ref_y0 + 1
        reg_x1 = ref_x1
        reg_y1 = ref_y1
        print 'Order %d: using x(%d:%d), y(%d:%d)' % (cur_order, reg_x0, reg_x1, reg_y0, reg_y1)

        # Given a column find x (primary x)
        # dependence of x on col in specified rows
        c0s.append(regress_row(m_ref, pto_ref,
                    cols=xrange(m_ref.width()), rows=xrange(reg_y0, reg_y1 + 1, order),
                    selector=lambda x: x.x(), allow_missing=allow_missing))
        # dependence of x on row in specified cols
        c1s.append(regress_col(m_ref, pto_ref,
                    cols=xrange(reg_x0, reg_x1 + 1, order), rows=xrange(m_ref.height()), selector=lambda x: x.x(),
                    allow_missing=allow_missing))
        # Given a row find y (primary y)
        # dependence of y on col in specified rows
        c3s.append(regress_row(m_ref, pto_ref,
                    cols=xrange(m_ref.width()), rows=xrange(reg_y0, reg_y1 + 1, order), selector=lambda x: x.y(),
                    allow_missing=allow_missing))
        # cdependence of y on row in specified cols
        c4s.append(regress_col(m_ref, pto_ref,
                    cols=xrange(reg_x0, reg_x1 + 1, order), rows=xrange(m_ref.height()), selector=lambda x: x.y(),
                    allow_missing=allow_missing))

    # Now chose a point in the center
    # it doesn't have to be a good fitting point in the old system, it just has to be centered
    # Fix at the origin
    
    '''
    Actually the even and the odd should have the same slope
    The only difference should be their offset
    '''
    
    if 0:
        print 'Solution found'
        print '  x = %g c + %g r + TBD' % (c0s[0], c1s[0])
        print '  y = %g c + %g r + TBD' % (c3s[0], c4s[0])

    # Verify the solution matrix by checking it against the reference project
    print
    print 'Verifying reference solution matrix....'
    # Entire reference is assumed to be good always, no border
    (c2s_ref, c5s_ref) = calc_constants(order, m_ref, pto_ref, c0s, c1s, c3s, c4s, m_ref, allow_missing)
    #c1s = [c1 + 12 for c1 in c1s]
    # Print the solution matrx for debugging
    for cur_order in range(order):
        # XXX: if we really cared we could center these up
        # its easier to just run the centering algorithm after though if one cares
        print 'Reference order %d solution:' % cur_order
        print '  x = %g c + %g r + %g' % (c0s[cur_order], c1s[cur_order], c2s_ref[cur_order])
        print '  y = %g c + %g r + %g' % (c3s[cur_order], c4s[cur_order], c5s_ref[cur_order])
    
    return ((c0s, c1s, c2s_ref), (c3s, c4s, c5s_ref))

def linear_reoptimize(pto, pto_ref = None, allow_missing = False, order = 2, border = False):
    '''
    Change XY positions to match the trend in a linear XY positioned project (ex from XY stage).  pto must have all images in pto_ref
    
    pto: project to optimize
    pto_ref: pto to use to calculate constants.  Useful to do a small test optimize and apply to full pto
    allow_missing: don't throw error if missing files
    order: number of unique row patterns.  Default 2 (1 left, 1 right, 1 left, 1 right, etc)
    border: whether to fully optimize the border
    ref_fns: which files from ref projec to use
    '''
    if scipy is None:
        raise Exception('Re-optimizing requires scipi')
    
    ((c0s, c1s, c2s_ref), (c3s, c4s, c5s_ref)) = linearize(pto, pto_ref, allow_missing, order)

    
    
    
    calc_ref_xs = []
    calc_ref_ys = []
    ref_xs = []
    ref_ys = []
    print 'Errors:'
    x_last = None
    y_last = None
    for col in range(m_ref.width()):
        for row in range(m_ref.height()):
            fn = m_ref.get_image(col, row)
            if fn is None:
                continue
            il = pto_ref.get_image_by_fn(fn)
            col_eo = col % order
            row_eo = row % order
            x_calc = c0s[row_eo] * col + c1s[row_eo] * row + c2s_ref[row_eo]
            y_calc = c3s[col_eo] * col + c4s[col_eo] * row + c5s_ref[col_eo]
            calc_ref_xs.append(x_calc)
            calc_ref_ys.append(y_calc)
            x_orig = il.x()
            y_orig = il.y()
            ref_xs.append(x_orig)
            ref_ys.append(y_orig)
            print '  c%d r%d: x%g y%g (x%g, y%g)' % (col, row, x_calc - x_orig, y_calc - y_orig, x_orig, y_orig)
            if col > 0:
                fn_old = m_ref.get_image(col - 1, row)
                if fn_old:
                    il_old = pto_ref.get_image_by_fn(fn_old)
                    print '    dx: %g' % (il.x() - il_old.x())
                    if col > 1:
                        '''
                        x1' = x1 - x0
                        x2' = x2 - x1
                        x2'' = x2' - x1' = (x2 - x1) - (x1 - x0) = x2 - 2 x1 + x0
                        '''
                        fn_old2 = m_ref.get_image(col - 2, row)
                        if fn_old2:
                            il_old2 = pto_ref.get_image_by_fn(fn_old2)
                            print '    dx2: %g' % (il.x() - 2 * il_old.x() + il_old2.x())
            if row != 0:
                fn_old = m_ref.get_image(col, row - 1)
                if fn_old:
                    il_old = pto_ref.get_image_by_fn(fn_old)
                    print '    dy: %g' % (il.y() - il_old.y())
                    if row > 1:
                        fn_old2 = m_ref.get_image(col, row - 2)
                        if fn_old2:
                            il_old2 = pto_ref.get_image_by_fn(fn_old2)
                            print '    dy2: %g' % (il.y() - 2 * il_old.y() + il_old2.y())
    x_ref_rms_error = rms_error_diff(calc_ref_xs, ref_xs)
    y_ref_rms_error = rms_error_diff(calc_ref_ys, ref_ys)
    print 'Reference RMS error x%g y%g' % (x_ref_rms_error, y_ref_rms_error)
    print
    #exit(1)
    
    '''
    The reference project might not start at 0,0
    Therefore scan through to find some good starting positions so that we can calc each point
    in the final project
    '''
    print 'Anchoring solution...'
    '''
    Calculate the constant at each reference image
    Compute reference positions from these values
    '''
    
    '''
    FIXME: we have to calculate these initially and then re-calc for border if required
    if top_bottom_backlash and border:
        row_border = 1
    else:
        row_border = 0
    if left_right_backlash and border:
        col_border = 1
    else:
        col_border = 0
    '''
    row_border = 0
    col_border = 0
    
    (c2s, c5s) = calc_constants(order, m_real, pto_ref, c0s, c1s, c3s, c4s, m_ref, allow_missing, col_border, row_border)
    #c2s = [c2 + 30 for c2 in c2s]
        
    # Print the solution matrx for debugging
    for cur_order in range(order):
        # XXX: if we really cared we could center these up
        # its easier to just run the centering algorithm after though if one cares
        print 'Order %d solution:' % cur_order
        print '  x = %g c + %g r + %g' % (c0s[cur_order], c1s[cur_order], c2s[cur_order])
        print '  y = %g c + %g r + %g' % (c3s[cur_order], c4s[cur_order], c5s[cur_order])
    
    c2_rms = rms_errorl(c2s)
    c5_rms = rms_errorl(c5s)
    print 'RMS offset error x%g y%g' % (c2_rms, c5_rms)
    left_right_backlash = False
    top_bottom_backlash = False
    if c2_rms > c5_rms:
        print 'x offset varies most, expect left-right scanning'
        left_right_backlash = True
    else:
        print 'y offset varies most, expect top-bottom scanning'
        top_bottom_backlash = True
    #exit(1)
    '''
    We have the solution matrix now so lets roll
    '''
    optimized = set()
    for col in range(col_border, m_real.width() - col_border):
        for row in range(row_border, m_real.height() - row_border):
            fn = m_real.get_image(col, row)
            il = pto.get_image_by_fn(fn)

            if fn is None:
                if not allow_missing:
                    raise Exception('Missing item')
                continue
            
            col_eo = col % order
            row_eo = row % order
            
            # FIRE!
            # take the dot product
            x = c0s[row_eo] * col + c1s[row_eo] * row + c2s[row_eo]
            y = c3s[col_eo] * col + c4s[col_eo] * row + c5s[col_eo]
            # And push it out
            #print '%s: c%d r%d => x%g y%d' % (fn, col, row, x, y)
            il.set_x(x)
            il.set_y(y)
            #print il
            optimized.add(fn)
    '''
    Finally manually optimize those that were in the border area
    '''
    if border:
        # Gather all file names
        # There are essentially four cases to do this faster but be lazy since it will still be O(images)
        to_manually_optimize = set()
        for col in range(0, m_real.width()):
            for row in range(m_real.height()):
                fn = m_real.get_image(col, row)
                il = pto.get_image_by_fn(fn)

                if fn is None:
                    if not allow_missing:
                        raise Exception('Missing item')
                    continue
                if fn in optimized:
                    continue
                to_manually_optimize.add(fn)
        # Prepare the pto to operate on the ones we want
        optimize_xy_only_for_images(pto, to_manually_optimize)
        # and run
        optimizer = PTOptimizer(pto)
        # Don't clear out the xy data we just calculated
        optimizer.reoptimize = False
        optimizer.run()











def merge_pto(src_pto, dst_pto, cplsi):
    '''
    Take a resulting pto project and merge the coordinates back into the original
    cplsi: control point indices to smash in dst_pto
    '''
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
    dst_pto.parse()
    
    base_n = len(dst_pto.get_image_lines())
    opt_n = len(src_pto.get_optimizer_lines())
    # old optimized version assuming same indices
    # XXX: remove in favor of (slower?) safer version?
    if base_n == opt_n:
        for i in range(len(dst_pto.get_image_lines())):
            il = dst_pto.get_image_lines()[i]
            ol = src_pto.optimizer_lines[i]
            for v in 'de':
                val = ol.get_variable(v)
                debug('Found variable val to be %s' % str(val))
                il.set_variable(v, val)
                debug('New IL: ' + str(il))
            debug()
    else:
        cplsi_iter = cplsi.__iter__()
        for cpl in src_pto.get_control_point_lines():
            # c n1 N0 x121.0 y258.0 X133.0 Y1056.0 t0
            n = cpl.get_variable('n')
            N = cpl.get_variable('N')
            
            # recycle old line object
            # it may even be the matching one but that shouldn't matter
            cpl2 = dst_pto.control_point_lines[cplsi_iter.next()]
            # Indexes will be different, adjust accordingly
            cpl2.set_variable('n', dst_pto.i2i(src_pto, n))
            cpl2.set_variable('N', dst_pto.i2i(src_pto, N))
        
        # verify consumed all images
        try:
            cplsi_iter.next()
            raise Exception("Didn't use all images")
        except StopIteration:
            pass
        
class TileOpt:
    def __init__(self, project):
        self.project = project
        self.debug = False
        # In practice I tend to get around 25 so anything this big signifies a real problem
        self.rms_error_threshold = 250.0
        
        # Tile width
        self.tw = 5
        # Tile height
        self.th = 5
    
    def partial_optimize(self, xo0, xo1, yo0, yo1,
                xf0=0, xf1=0, yf0=0, yf1=0):
        '''
        Return a PTOptimizer optimized sub-self.opt_project
        o: optimized row/col
        f: fixed row/col
            relative to counterpart
            allows to join in with pre-optimized rows/cols
        '''
        print 'Optimizing base region'
        print 'Selected base region x(%d:%d), y(%d:%d)' % (xo0, xo1, yo0, yo1)

        if xf0 > 0:
            raise Exception('')
        if xf1 < 0:
            raise Exception('')
        if yf0 > 0:
            raise Exception('')
        if yf1 < 0:
            raise Exception('')
            
        xf0 += xo0
        xf1 += xo1
        yf0 += yo0
        yf1 += yo1
        
        '''
        # Remove all previously selected optimizations
        project.variable_lines = []
        # Mark the selected images for optimization
        for col in xrange(xo0, xo1 + 1, 1):
            for row in xrange(yo0, yo1 + 1, 1):
                fn = self.icm.get_image(col, row)
                img_i = self.project.img_fn2i(fn)
                vl = VariableLine('v d%d e%d' % (img_i, img_i), project)
                project.variable_lines.append(vl)
        '''
        project = PTOProject.from_blank()
        
        # Copy special lines
        # in particular need to keep canvas scale
        project.set_pano_line_by_text(str(self.opt_project.panorama_line))
        project.set_mode_line_by_text(str(self.opt_project.mode_line))
        
        # Copy in image lines
        # Create a set of all images of interest to make relevant lines easy to find
        rel_i = set()
        for col in xrange(xf0, xf1 + 1, 1):
            for row in xrange(yf0, yf1 + 1, 1):
                fn = self.icm.get_image(col, row)
                il = self.project.img_fn2l(fn)
                rel_i.add(il.get_index())
                # Image itself
                project.image_lines.append(ImageLine(str(il), project))
        
        # save indices to quickly eliminate/replace them
        cpl_is = []
        # Now that all images are added we can add features between them
        for cpli, cpl in enumerate(self.opt_project.get_control_point_lines()):
            # c n1 N0 x121.0 y258.0 X133.0 Y1056.0 t0
            n = cpl.get_variable('n')
            N = cpl.get_variable('N')
            if n in rel_i and N in rel_i:
                cpl2 = ControlPointLine(str(cpl), project)
                # Indexes will be different, adjust accordingly
                cpl2.set_variable('n', project.i2i(self.opt_project, n))
                cpl2.set_variable('N', project.i2i(self.opt_project, N))
                project.control_point_lines.append(cpl2)
                cpl_is.append(cpli)
        
        
        anchor = None
        # All variable?
        if xo0 == xf0 and xo1 == xf1 and yo0 == yf0 and yo1 == yf1:
            # Then must anchor solution to a fixed tile
            anchor = ((xo0 + xo1) / 2, (xf0 + xf1) / 2)
        
        # Finally, set images to optimize (XY only)
        for col in xrange(xo0, xo1 + 1, 1):
            for row in xrange(yo0, yo1 + 1, 1):
                # Don't optimize if its the fixed image
                if (col, row) == anchor:
                    continue
                fn = self.icm.get_image(col, row)
                img_i = project.img_fn2i(fn)
                vl = VariableLine('v d%d e%d' % (img_i, img_i), project)
                project.variable_lines.append(vl)
        
        # In case it crashes do a debug dump
        pre_run_text = project.get_text()
        if 0:
            print project.variable_lines
            print
            print
            print 'PT optimizer project:'
            print pre_run_text
            print
            print
            raise Exception('Debug break')
                
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
        print 'Optimized project parsed: %d' % self.opt_project.parsed
        return (project, cpl_is)
    
    def run(self):
        bench = Benchmark()
        
        # The following will assume all of the images have the same size
        self.verify_images()
        
        # Copy project so we can trash it
        self.opt_project = self.project.to_ptoptimizer()
        self.prepare_pto(self.opt_project)

        print 'Building image coordinate map'
        i_fns = []
        for il in self.opt_project.image_lines:
            i_fns.append(il.get_name())
        self.icm = ImageCoordinateMap.from_file_names(i_fns)
        print 'Built image coordinate map'
        
        if self.icm.width() <= self.tw:
            raise Exception('Decrease tile width')
        if self.icm.height() <= self.th:
            raise Exception('Decrease tile height')

        order = 2
        
        
        '''
        Phase 1: baseline
        Fully optimize a region in the center of our pano
        '''
        print 'Phase 1: baseline'
        x0 = (self.icm.width() - self.tw) / 2
        if x0 % order != 0:
            x0 += 1
        x1 = x0 + self.tw - 1
        y0 = (self.icm.height() - self.th) / 2
        if y0 % order != 0:
            y0 += 1
        y1 = y0 + self.th - 1
        (center_pto, center_cplis) = self.partial_optimize(x0, x1, y0, y1)
        merge_pto(center_pto, self.opt_project, center_cplis)


        '''
        Phase 2: predict
        Now use base center project to predict optimization positions for rest of project
        Assume that scanning left/right and that backlash will cause rows to alternate ("order 2")
        Note this will also fill in position estimates for unmatched images
        x = c0 * c + c1 * r + c2
        y = c3 * c + c4 * r + c5
        XXX: is there reason to have order 2 y coordinates?
        '''
        print 'Phase 2: predict'
        ((c0s, c1s, c2s), (c3s, c4s, c5s)) = linearize(self.opt_project, center_pto, allow_missing=False, order=order)
        # Exclude filenames directly optimized
        center_is = set()
        for il in center_pto.get_image_lines():
            center_is.add(self.opt_project.i2i(center_pto, il.get_index()))
        for row in xrange(self.icm.width()):
            for col in xrange(self.icm.height()):
                fn = self.icm.get_image(col, row)
                il = self.project.img_fn2l(fn)
                # Skip directly optimized lines
                if il.get_index() in center_is:
                    continue
                # Otherwise predict position
                x = c0s[col%order] * col + c1s[col%order] * row + c2s[col%order]
                il.set_variable('d', x)
                y = c3s[row%order] * col + c4s[row%order] * row + c5s[row%order]
                il.set_variable('e', y)
        
        
        '''
        Phase 3: optimize
        Moving out from center, optimize sub-sections based off of prediction
        Move in a cross pattern
            Left
            Right
            Up
            Down
            Expand scope
        '''
        '''
        x0 = self.icm.width() / 2
        if x0 % order != 0:
            x0 += 1
        x1 = x0 + self.tw - 1
        y0 = self.icm.height() / 2
        if y0 % order != 0:
            y0 += 1
        y1 = y0 + self.th - 1
        (center_pto, center_cplis) = self.partial_optimize(x0, x1, y0, y1)
        merge_pto(center_pto, self.opt_project, center_cplis)
        '''


        if self.debug:
            print self.project
        
        bench.stop()
        print 'Optimized project in %s' % bench
        
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
        
    def prepare_pto(self, pto):
        '''Simply and modify a pto project enough so that PToptimizer will take it'''
        print 'Stripping project'
        
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
            
            # These aren't liked: TrX0 TrY0 TrZ0
            il.remove_variable('TrX')
            il.remove_variable('TrY')
            il.remove_variable('TrZ')
    
            # panotools seems to set these to -1 on some ocassions
            if il.get_variable('w') == None or il.get_variable('h') == None or int(il.get_variable('w')) <= 0 or int(il.get_variable('h')) <= 0:
                img = PImage.from_file(il.get_name())
                il.set_variable('w', img.width())
                il.set_variable('h', img.height())
                
            # Force reoptimize by zeroing optimization result
            il.set_variable('d', 0)
            il.set_variable('e', 0)
        
        fix_pl(pto.get_panorama_line())
        
        for il in pto.image_lines:
            fix_il(il)
