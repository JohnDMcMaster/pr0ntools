#!/usr/bin/env python
'''
Attempt to optimize faster by optimize sub-tiles and then combining into a larger project
'''

from pr0ntools import execute
from pr0ntools.pimage import PImage
from pr0ntools.stitch.pto.util import *
from pr0ntools.benchmark import Benchmark
from pr0ntools.stitch.pto.variable_line import VariableLine
import sys

def debug(s = ''):
    pass
            
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
    
    def run(self):
        bench = Benchmark()
        
        # The following will assume all of the images have the same size
        self.verify_images()
        
        # Copy project so we can trash it
        project = self.project.to_ptoptimizer()
        self.prepare_pto(project)

        print 'Building image coordinate map'
        i_fns = []
        for il in self.project.image_lines:
            i_fns.append(il.get_name())
        icm = ImageCoordinateMap.from_file_names(i_fns)
        print 'Built image coordinate map'
        
        if icm.width() <= self.tw:
            raise Exception('Decrease tile width')
        if icm.height() <= self.th:
            raise Exception('Decrease tile height')


        print 'Optimizing base region'
        x0 = icm.width() / 2
        x1 = x0 + self.tw - 1
        y0 = icm.height() / 2
        y1 = y0 + self.th - 1
        print 'Selected base region x(%d:%d), y(%d:%d)' % (x0, x1, y0, y1)
        
        # Remove all previously selected optimizations
        project.variable_lines = []
        # Mark the selected images for optimization
        for col in xrange(x0, x1 + 1, 1):
            for row in xrange(y0, y1 + 1, 1):
                fn = icm.get_image(col, row)
                img_i = self.project.img_fn2i(fn)
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
        print 'Optimized project parsed: %d' % project.parsed

        print 'Merging project...'
        merge_pto(project, self.project)
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
