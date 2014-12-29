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
import sys

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
        
        # These aren't liked: TrX0 TrY0 TrZ0
        il.remove_variable('TrX')
        il.remove_variable('TrY')
        il.remove_variable('TrZ')

        # panotools seems to set these to -1 on some ocassions
        if il.get_variable('w') == None or il.get_variable('h') == None or int(il.get_variable('w')) <= 0 or int(il.get_variable('h')) <= 0:
            img = PImage.from_file(il.get_name())
            il.set_variable('w', img.width())
            il.set_variable('h', img.height())

        for v in 'd e'.split():
            if il.get_variable(v) == None or reoptimize:
                il.set_variable(v, 0)
                #print 'setting var'
    
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
        self.rms_error_threshold = 250.0
        self.reoptimize = True
        # in images
        self.stw = 4
        self.sth = 4
        self.icm = None
    
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
    
    def pre_opt(self, project):
        '''
        Generates row/col to use for initial image placement
        spiral pattern outward from center
        
        Assumptions:
        -All images must be tied together by at least one control point
        '''
        # reference position
        #xc = self.icm.width() / 2
        #yc = self.icm.height() / 2
        project.build_image_fn_map()
        
        # dictionary of results so that we can play around with post-processing result
        pairsx = {}
        pairsy = {}
        # start with simple algorithm where we just sweep left/right
        for y in xrange(0, self.icm.height()):
            for x in xrange(0, self.icm.width()):
                il = project.img_fn2il[self.icm.get_image(x, y)]
                ili = il.get_index()
                '''
                Calculate average x/y position
                '''
                def check(xl_il):
                    # lesser line
                    xl_ili = xl_il.get_index()
                    # Find matching control points
                    cps_x = []
                    cps_y = []
                    for cpl in project.get_control_point_lines():
                        # applicable?
                        if cpl.getv('n') == xl_ili and cpl.getv('N') == ili:
                            # compute distance
                            # note: these are relative coordinates to each image
                            # and strictly speaking can't be directly compared
                            # however, because the images are the same size the width/height can be ignored
                            cps_x.append(cpl.getv('X') - cpl.getv('x'))
                            cps_y.append(cpl.getv('Y') - cpl.getv('y'))
                        elif cpl.getv('n') == ili and cpl.getv('N') == xl_ili:
                            cps_x.append(cpl.getv('x') - cpl.getv('X'))
                            cps_y.append(cpl.getv('y') - cpl.getv('Y'))
                    
                    # Possible that no control points due to failed stitch
                    # or due to edge case
                    if len(cps_x) == 0:
                        return None
                    else:
                        return (    1.0 * sum(cps_x)/len(cps_x), 
                                    1.0 * sum(cps_y)/len(cps_y))
                if x > 0:
                    pairsx[(x, y)] = check(project.img_fn2il[self.icm.get_image(x - 1, y)])
                if y > 0:
                    pairsy[(x, y)] = check(project.img_fn2il[self.icm.get_image(x, y - 1)])
                
        # repair holes by successive passes
        # contains x,y points that have been finalized
        closed_set = {(0, 0): (0.0, 0.0)}
        iters = 0
        while True:
            iters += 1
            print 'Iters %d' % iters
            fixes = 0
            for y in xrange(self.icm.height()):
                for x in xrange(self.icm.width()):
                    if (x, y) in closed_set:
                        continue
                    # see what we can gather from
                    # list of [xcalc, ycalc]
                    points = []
                    
                    # X
                    # left
                    # do we have a fixed point to the left?
                    o = closed_set.get((x - 1, y), None)
                    if o:
                        d = pairsx[(x, y)]
                        # and a delta to get to it?
                        if d:
                            dx, dy = d
                            points.append((o[0] - dx, o[1] - dy))
                    # right
                    o = closed_set.get((x + 1, y), None)
                    if o:
                        d = pairsx[(x + 1, y)]
                        if d:
                            dx, dy = d
                            points.append((o[0] + dx, o[1] + dy))
                    
                    # Y
                    o = closed_set.get((x, y - 1), None)
                    if o:
                        d = pairsy[(x, y)]
                        if d:
                            dx, dy = d
                            points.append((o[0] - dx, o[1] - dy))
                    o = closed_set.get((x, y + 1), None)
                    if o:
                        d = pairsy[(x, y + 1)]
                        if d:
                            d = dx, dy
                            points.append((o[0] + dx, o[1] + dy))
                    
                    # Nothing useful?
                    if len(points) == 0:
                        continue
                    
                    # use all available anchor points from above
                    il = project.img_fn2il[self.icm.get_image(x, y)]
                    
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
        print 'Final position optimization:'
        for y in xrange(self.icm.height()):
            for x in xrange(self.icm.width()):
                p = closed_set.get((x, y))
                if p is None:
                    print '  %03dX, %03dY: none' % (x, y)
                else:
                    print '  %03dX, %03dY: %0.3fx, %0.3fy' % (x, y, p[0], p[1])

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

        self.pre_opt(project)
        
        prepare_pto(project, reoptimize=False)
        
        pre_run_text = project.get_text()
        
        # "PToptimizer out.pto"
        args = ["PToptimizer"]
        args.append(project.get_a_file_name())
        print 'Optimizing %s' % project.get_a_file_name()
        raise Exception()
        #self.project.save()
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
    project = PTOProject.parse_from_file_name(file_name_in)
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

