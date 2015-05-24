'''
pr0ntools
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''
'''
This class takes in a .pto project and does not modify it or any of the perspective parameters it specifies
It produces a series of output images, each a subset within the defined crop area
Pixels on the edges that don't fit nicely are black filled

Crop ranges are not fully inclusive
    ex: 0:255 results in a 255 width output, not 256

Arbitrarily assume that the right and bottom are the ones that aren't



This requires the following to work (or at least well):
-Source images must have some unique portion
    If they don't there is no natural "safe" region that can be blended separately
This works by forming larger tiles and then splitting them into smaller tiles


New strategy
Construct a spatial map using all of the images
Define an input intermediate tile width, height
    If undefined default to 3 * image width/height
    Note however, the larger the better (of course full image is ideal)
Define a safe buffer zone heuristic
    Nothing in this area shared with other tiles will be kept
    It will be re-generated as we crawl along and the center taken out
    
    In my images 1/3 of the image should be unique
    The assumption I'm trying to make is that nona will not try to blend more than one image away
    The default should be 1 image distance
    
Keep a closed set (and open set?) of all of the tiles we have generated
Each time we construct a new stitching frame only re-generate tiles that we actually need
This should simplify a lot of the bookkeeping, especially as things get hairy
At the end check that all times have been generated and throw an error if we are missing any
Greedy algorithm to generate a tile if its legal (and safe)
'''

from pr0ntools.stitch.remapper import Nona
from pr0ntools.stitch.blender import Enblend
from image_coordinate_map import ImageCoordinateMap
from pr0ntools.execute import Execute
from pr0ntools.config import config
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.temp_file import ManagedTempDir
#from pr0ntiles.tile import Tiler as TilerCore
from pr0ntools.pimage import PImage
from pr0ntools.benchmark import Benchmark
from pr0ntools.geometry import ceil_mult
from pr0ntools.execute import CommandFailed
from pr0ntools.stitch.pto.util import dbg

import datetime
import math
import os
import Queue
import shutil
import subprocess
import sys
import threading
import time
import traceback

class InvalidClip(Exception):
    pass

'''
# thread safe stdout/stderr file
class ThreadedIO:
    def __init__(self):
        self.buff = bytearray()
    
    def write(self, s):
'''

class PartialStitcher:
    def __init__(self, pto, bounds, out, worki, work_run, p, pprefix, lock):
        self.pto = pto
        self.bounds = bounds
        self.out = out
        self.nona_args = []
        self.enblend_args = []
        self.enblend_lock = False
        self.worki = worki
        self.work_run = work_run
        self.p = p
        self.pprefix = pprefix
        self.lock = lock
        
    def run(self):
        '''
        Phase 1: remap the relevant source image areas onto a canvas
        
        Note that nona will load ALL of the images (one at a time)
        but will only generate output for those that matter
        Each one takes a noticible amount of time but its relatively small compared to the time spent actually mapping images
        '''
        self.p()
        self.p('Supertile phase 1: remapping (nona)')
        if self.out.find('.') < 0:
            raise Exception('Require image extension')
        # Hugin likes to use the base filename as the intermediates, lets do the sames
        out_name_base = self.out[0:self.out.find('.')].split('/')[-1]
        self.p("out name: %s, base: %s" % (self.out, out_name_base))
        #ssadf
        if out_name_base is None or len(out_name_base) == 0 or out_name_base == '.' or out_name_base == '..':
            raise Exception('Bad output file base "%s"' % str(out_name_base))

        # Scope of these files is only here
        # We only produce the single output file, not the intermediates
        managed_temp_dir = ManagedTempDir.get()
        # without the slash they go into the parent directory with that prefix
        out_name_prefix = managed_temp_dir.file_name + "/"
        
        '''
        For large projects this was too slow
        Instead, we simply copy the project and manually fix up the relevant portion
        '''
        self.p('Copying pto')
        pto = self.pto.copy()
        #pto = self.mini_pto.copy()
        
        self.p('Cropping...')
        #sys.exit(1)
        pl = pto.get_panorama_line()
        # It is fine to go out of bounds, it will be black filled
        #pl.set_bounds(x, min(x + self.tw(), pto.right()), y, min(y + self.th(), pto.bottom()))
        pl.set_crop(self.bounds)
        self.p('Preparing remapper...')
        def hook():
            self.p('Prep done, releasing lock')
            self.lock.release()
        remapper = Nona(pto, out_name_prefix, start_hook=hook)
        remapper.p = self.p
        remapper.pprefix = self.pprefix
        remapper.args = self.nona_args
        self.p('Starting remapper...')
        remapper.remap()
        
        '''
        Phase 2: blend the remapped images into an output image
        '''
        self.p()
        self.p('Supertile phase 2: blending (enblend)')
        blender = Enblend(remapper.get_output_files(), self.out, lock=self.enblend_lock)
        blender.p = self.p
        blender.pprefix = self.pprefix
        blender.args = self.enblend_args
        blender.run()
        # We are done with these files, they should be nuked
        if not config.keep_temp_files():
            for f in remapper.get_output_files():
                os.remove(f)
        
        self.p('Supertile ready!')


class Worker(threading.Thread):
    def __init__(self, i, tiler):
        threading.Thread.__init__(self)
        self.i = i
        self.qi = Queue.Queue()
        self.qo = Queue.Queue()
        self.running = threading.Event()
        self.tiler = tiler
        self.exit = False
    
    def p(self, s=''):
        if not self.running:
            raise Exception('not running')
        print '%s w%d: %s' % (datetime.datetime.utcnow().isoformat(), self.i, s)
    
    def pprefix(self):
        # hack: ocassionally get io
        # use that to interrupt if need be
        if not self.running:
            raise Exception('not running')
        # TODO: put this into queue so we don't drop
        return '%s w%d: ' % (datetime.datetime.utcnow().isoformat(), self.i)
        
    def run(self):
        self.running.set()
        self.exit = False
        while self.running.is_set():
            try:
                task = self.qi.get(True, 0.1)
            except Queue.Empty:
                continue
            
            try:
                (st_bounds,) = task

                self.p('')
                self.p('')
                self.p('')
                self.p('')
                self.p('*' * 80)
                self.p('task rx')

                try:
                    img = self.try_supertile(st_bounds)
                    self.qo.put(('done', (st_bounds, img)))
                except CommandFailed as e:
                    if not self.tiler.ignore_errors:
                        raise
                    # We shouldn't be trying commands during dry but just in case should raise?
                    self.p('WARNING: got exception trying supertile %d' % (self.tiler.n_supertiles))
                    traceback.print_exc()
                    estr = traceback.format_exc()
                    self.qo.put(('exception', (task, e, estr)))
                self.p('task done')
                
            except Exception as e:
                traceback.print_exc()
                estr = traceback.format_exc()
                self.qo.put(('exception', (task, e, estr)))
        self.p('exiting')
        self.exit = True

    def try_supertile(self, st_bounds):
        '''x0/1 and y0/1 are global absolute coordinates'''
        # First generate all of the valid tiles across this area to see if we can get any useful work done?
        # every supertile should have at least one solution or the bounds aren't good
        x0, x1, y0, y1 = st_bounds

        self.p('Waiting for worker lock...')
        self.tiler.gil_sucks.acquire()
        self.p('Glot lock')
        
        bench = Benchmark()
        try:
            if self.tiler.st_dir:
                # nah...tiff takes up too much space
                dst = os.path.join(self.tiler.st_dir, 'st_%06dx_%06dy.jpg' % (x0, y0))
                if os.path.exists(dst):
                    self.tiler.gil_sucks.release()
                    # normally this is a .tif so slight loss in quality
                    img = PImage.from_file(dst)
                    self.p('supertile short circuit on already existing: %s' % (dst,))
                    return img
                
            temp_file = ManagedTempFile.get(None, '.tif')

            #out_name_base = "%s/r%03d_c%03d" % (self.tiler.out_dir, row, col)
            #print 'Working on %s' % out_name_base
            stitcher = PartialStitcher(self.tiler.pto, st_bounds, temp_file.file_name, self.i, self.running, p=self.p, pprefix=self.pprefix, lock=self.tiler.gil_sucks)
            stitcher.enblend_lock = self.tiler.enblend_lock
            stitcher.nona_args = self.tiler.nona_args
            stitcher.enblend_args = self.tiler.enblend_args

            if self.tiler.dry:
                self.p('dry: skipping partial stitch')
                self.tiler.gil_sucks.release()
                stitcher = None
            else:
                stitcher.run()
        
            self.p('')
            self.p('phase 3: loading supertile image')
            if self.tiler.dry:
                self.p('dry: skipping loading PTO')
                img = None
            else:
                if self.tiler.st_dir:
                    self.tiler.st_fns.append(dst)
                    #shutil.copyfile(temp_file.file_name, dst)
                    args = ['convert',
                            '-quality', '90', 
                            temp_file.file_name, dst]                    
                    print 'going to execute: %s' % (args,)
                    subp = subprocess.Popen(args, stdout=None, stderr=None, shell=False)
                    subp.communicate()
                    if subp.returncode != 0:
                        raise Exception('Failed to copy stitched file')

                    # having some problems that looks like file isn't getting written to disk
                    # monitoring for such errors
                    # remove if I can root cause the source of these glitches
                    for i in xrange(30):
                        if os.path.exists(dst):
                            break
                        if i == 0:
                            print 'WARNING: soften missing strong blur dest file name %s, waiting a bit...' % (dst,)
                        time.sleep(0.1)
                    else:
                        raise Exception('Missing soften strong blur output file name %s' % dst)

                img = PImage.from_file(temp_file.file_name)
                self.p('supertile width: %d, height: %d' % (img.width(), img.height()))
            return img
        except:
            self.p('supertile failed at %s' % (bench,))
            raise

# For managing the closed list        

class Tiler:
    
    def __init__(self, pto, out_dir, tile_width=250, tile_height=250, st_scalar_heuristic=4, dry=False, stw=None, sth=None, stp=None, clip_width=None, clip_height=None):
        '''
        stw: super tile width
        sth: super tile height
        stp: super tile pixels (auto stw, sth)
        '''
        self.img_width = None
        self.img_height = None
        self.dry = dry
        self.st_scalar_heuristic = st_scalar_heuristic
        self.ignore_errors = False
        self.ignore_crop = False
        self.verbose = False
        self.verbosity = 2
        self.stw = stw
        self.sth = sth
        self.clip_width = clip_width
        self.clip_height = clip_height
        self.st_dir = None
        self.nona_args = []
        self.enblend_args = []
        self.threads = 1
        self.workers = None
        self.st_fns = []
        '''
        When running lots of threads, we get stuck trying to get something mapping
        I think this is due to GIL contention
        To work around this, workers do pre-map stuff single threaded (as if they were in the server thread)
        '''
        self.gil_sucks =  threading.Lock()
        self.gil_sucks.acquire()
        self.gil_sucks.release()
        
        # TODO: this is a heuristic just for this, uniform input images aren't actually required
        for i in pto.get_image_lines():
            w = i.width()
            h = i.height()
            if self.img_width is None:
                self.img_width = w
            if self.img_height is None:
                self.img_height = h
            if self.img_width != w or self.img_height != h:
                raise Exception('Require uniform input images for size heuristic')
        
        self.pto = pto
        # make absolutely sure that threads will only be doing read only operations
        # pre-parse the project
        self.pto.parse()
        print 'Making absolute'
        pto.make_absolute()
        
        
        
        self.out_dir = out_dir
        self.tw = tile_width
        self.th = tile_height
        
        #out_extension = '.png'
        self.out_extension = '.jpg'
                
        # Delete files in the way?
        self.force = False
        # Keep old files and skip already generated?
        self.merge = False
        
        spl = self.pto.get_panorama_line()
        self.x0 = spl.left()
        self.x1 = spl.right()
        self.y0 = spl.top()
        self.y1 = spl.bottom()
        #print spl
        
        self.calc_size_heuristic(self.img_width, self.img_height)
        
        # Auto calc tile parameters based on # super tile pixels?
        if stp:
            if self.stw or self.sth:
                raise ValueError("Can't manually specify width/height and do auto")
            '''
            Given an area and a length and width, find the optimal tile sizes
            such that there are the least amount of tiles but they cover all area
            with each tile being as small as possible
            
            Generally get better results if things remain square
            Long rectangular sections that can fit a single tile easily should
                Idea: don't let tile sizes get past aspect ratio of 2:1
            
            Take the smaller dimension
            '''
            # Maximum h / w or w / h
            aspect_max = 2.0
            w = self.width()
            h = self.height()
            a = w * h
            '''
            w = h / a
            p = w * h = (h / a) * h
            p * a = h**2, h = (p * a)**0.5
            '''
            min_stwh = int((stp / aspect_max)**0.5)
            max_stwh = int((stp * aspect_max)**0.5)
            print 'Maximum supertile width/height: %d w/ square @ %d' % (max_stwh, int(stp**0.5))
            # Theoretical number of tiles if we had no overlap
            theoretical_tiles = a * 1.0 / stp
            print 'Net area %d (%dw X %dh) requires at least ceil(%g) tiles' % \
                    (a, w, h, theoretical_tiles)
            aspect = 1.0 * w / h
            # Why not just run a bunch of sims and take the best...
            if 0:
                '''
                Take a rough shape of the canvas and then form rectangles to match
                '''
                if aspect >= 2.0:
                    print 'width much larger than height'
                elif aspect <= 0.5:
                    print 'Height much larger than width'
                else:
                    print 'Squarish canvas, forming squares'
            if 1:
                # Keep each tile size constant
                print 'Sweeping tile size optimizer'
                best_w = None
                best_h = None
                self.best_n = None
                # Get the lowest perimeter among n
                # Errors occur around edges
                best_p = None
                # Arbitrary step at 1000
                # Even for large sets we want to optimize
                # for small sets we don't care
                for check_w in xrange(min_stwh, max_stwh, 100):
                    check_h = stp / check_w
                    print 'Checking supertile size %dw X %dh (area %d)' % (check_w, check_h, check_w * check_h)
                    try:
                        tiler = Tiler(pto = self.pto, out_dir = self.out_dir,
                                tile_width = self.tw, tile_height = self.th,
                                st_scalar_heuristic=self.st_scalar_heuristic, dry=True,
                                stw=check_w, sth=check_h, stp=None, clip_width=self.clip_width, clip_height=self.clip_height)
                    except InvalidClip as e:
                        print 'Discarding: invalid clip: %s' % (e,)
                        print
                        continue
                    
                    # The area will float around a little due to truncation
                    # Its better to round down than up to avoid running out of memory
                    n_expected = tiler.expected_sts()
                    # XXX: is this a bug or something that I should just skip?
                    if n_expected == 0:
                        print 'Invalid STs 0'
                        print
                        continue
                        
                    p = (check_w + check_h) * 2
                    print 'Would generate %d supertiles each with perimeter %d' % (n_expected, p)
                    # TODO: there might be some optimizations within this for trimming...
                    # Add a check for minimum total mapped area
                    if self.best_n is None or self.best_n > n_expected and best_p > p:
                        print 'Better'
                        self.best_n = n_expected
                        best_w = check_w
                        best_h = check_h
                        best_p = p
                        if n_expected == 1:
                            print 'Only 1 ST: early break'
                            break
                    print
            print 'Best n %d w/ %dw X %dh' % (self.best_n, best_w, best_h)
            if 0:
                print
                print 'Debug break'
                sys.exit(1)
            self.stw = best_w
            self.sth = best_h
            self.trim_stwh()
        
        # These are less related
        # They actually should be set as high as you think you can get away with
        # Although setting a smaller number may have higher performance depending on input size
        if self.stw is None:
            self.stw = self.img_width * self.st_scalar_heuristic
        if self.sth is None:
            self.sth = self.img_height * self.st_scalar_heuristic
        
        self.recalc_step()        
        # We build this in run
        self.map = None
        print 'Clip width: %d' % self.clip_width
        print 'Clip height: %d' % self.clip_width
        print 'ST width: %d' % self.stw
        print 'ST height: %d' % self.sth
        if self.stw <= 2 * self.clip_width and not self.stw < w:
            print 'Failed'
            print '  STW: %d' % self.stw
            print '  Clip W: %d' % self.clip_width
            print '  W: %d (%d - %d)' % (w, self.right(), self.left())
            raise InvalidClip('Clip width %d exceeds supertile width %d after adj: reduce clip or increase ST size' % (self.clip_width, self.stw))
        if self.sth <= 2 * self.clip_height and not self.stw < h:
            raise InvalidClip('Clip height %d exceeds supertile height %d after adj: reduce clip or increase ST size' % (self.clip_height, self.sth))
        
    def msg(self, s, l):
        '''Print message s at verbosity level l'''
        if l <= self.verbosity:
            print s
        
    def expected_sts(self):
        '''Number of expected supertiles'''
        return len(list(self.gen_supertiles()))
        
    def trim_stwh(self):
        '''
        Supertiles may be larger than the margins
        If so it just slows down stitching with a lot of stuff getting thrown away
        
        Each time a supertile is added we lose one overlap unit
        ideally canvas w = n * stw - (n - 1) * overlap
        Before running this function stw may be oversized
        '''
        self.recalc_step()
        orig_st_area = self.stw * self.sth
        orig_net_area = self.expected_sts() * orig_st_area
        orig_stw = self.stw
        orig_sth = self.sth

        # eliminate corner cases by only trimming when it can do any good
        print 'Trimming %d supertiles' % self.best_n
        if self.best_n <= 1:
            print 'Only one ST: not trimming'
            return
        
        if 0:
            # First one is normal but each additional takes a clip
            w_sts = int(1 + math.ceil(1.0 * (self.width() - self.stw) / (self.stw - self.super_t_xstep)))
            h_sts = int(1 + math.ceil(1.0 * (self.height() - self.sth) / (self.sth - self.super_t_ystep)))
            print '%dw X %dh supertiles originally' % (w_sts, h_sts)
            #total_clip_width = self.clip_width * 
        else:
            h_sts = 0
            h_extra = 0
            for y in xrange(self.top(), self.bottom(), self.super_t_ystep):
                h_sts += 1
                y1 = y + self.sth
                if y1 >= self.bottom():
                    h_extra = y1 - self.bottom()
                    break
                
            w_sts = 0
            w_extra = 0
            for x in xrange(self.left(), self.right(), self.super_t_xstep):
                w_sts += 1
                x1 = x + self.stw
                if x1 >= self.right():
                    w_extra = x1 - self.right()
                    break
            print '%d width tiles waste %d pixels' % (w_sts, w_extra)
            self.stw = self.stw - w_extra / w_sts
            print '%d height tiles waste %d pixels' % (h_sts, h_extra)
            self.sth = self.sth - h_extra / h_sts
            # Since we messed with the tile width the step needs recalc
            self.recalc_step()
        
        new_st_area = self.stw * self.sth
        new_net_area = self.expected_sts() * new_st_area
        print 'Final supertile trim results:'
        print '  Width %d => %d (%g%% of original)' % (orig_stw, self.stw, 100.0 * self.stw / orig_stw)
        print '  Height %d => %d (%g%% of original)' % (orig_sth, self.sth, 100.0 * self.sth / orig_sth)
        print '  ST area %d => %d (%g%% of original)' % (orig_st_area, new_st_area, 100.0 * new_st_area / orig_st_area )
        print '  Net area %d => %d (%g%% of original)' % (orig_net_area, new_net_area, 100.0 * new_net_area / orig_net_area)
    
    def make_full(self):
        '''Stitch a single supertile'''
        self.stw = self.width()
        self.sth = self.height()
    
    def recalc_step(self):
        '''
        We won't stitch any tiles in the buffer zone
        We don't stitch on the right to the current supertile and won't stitch to the left on the next supertile
        So, we must take off 2 clip widths to get a safe area
        We probably only have to take off one tw, I haven't thought about it carefully enough
        
        If you don't do this you will not stitch anything in the center that isn't perfectly aligned
        Will get worse the more tiles you create
        '''
        try:
            self.super_t_xstep = self.stw - 2 * self.clip_width - 2 * self.tw
            self.super_t_ystep = self.sth - 2 * self.clip_height - 2 * self.th
        except:
            print self.stw, self.clip_width, self.tw
            raise
    
    def calc_size_heuristic(self, image_width, image_height):
        '''
        The idea is that we should have enough buffer to have crossed a safe area
        If you take pictures such that each picture has at least some unique area (presumably in the center)
        it means that if we leave at least one image width/height of buffer we should have an area where enblend is not extending to
        Ultimately this means you lose 2 * image width/height on each stitch
        so you should have at least 3 * image width/height for decent results
        
        However if we do assume its on the center the center of the image should be unique and thus not a stitch boundry
        '''
        if self.clip_width is None:
            self.clip_width = int(image_width * 1.5)
        if self.clip_height is None:
            self.clip_height = int(image_height * 1.5)
        
    def gen_supertile_tiles(self, st_bounds):
        x0, x1, y0, y1 = st_bounds
        '''Yield UL coordinates in (y, x) pairs'''
        xt0 = ceil_mult(x0, self.tw, align=self.x0)
        xt1 = ceil_mult(x1, self.tw, align=self.x0)
        if xt0 >= xt1:
            print x0, x1
            print xt0, xt1
            raise Exception('Bad input x dimensions')
        yt0 = ceil_mult(y0, self.th, align=self.y0)
        yt1 = ceil_mult(y1, self.th, align=self.y0)
        if yt0 >= yt1:
            print y0, y1
            print yt0, yt1
            raise Exception('Bad input y dimensions')
            
        if self.tw <= 0 or self.th <= 0:
            raise Exception('Bad step values')


        skip_xl_check = False
        skip_xh_check = False
        # If this is an edge supertile skip the buffer check
        if x0 == self.left():
            #print 'X check skip (%d): left border' % x0
            skip_xl_check = True
        if x1 == self.right():
            #print 'X check skip (%d): right border' % x1
            skip_xh_check = True
            
        skip_yl_check = False
        skip_yh_check = False
        if y0 == self.top():
            print 'Y check skip (%d): top border' % y0
            skip_yl_check = True
        if y1 == self.bottom():
            print 'Y check skip (%d): bottom border' % y1
            skip_yh_check = True
            
        for y in xrange(yt0, yt1, self.th):
            # Are we trying to construct a tile in the buffer zone?
            if (not skip_yl_check) and y < y0 + self.clip_height:
                if self.verbose:
                    print 'Rejecting tile @ y%d, x*: yl clip' % (y)
                continue
            if (not skip_yh_check) and y + self.th >= y1 - self.clip_height:
                if self.verbose:
                    print 'Rejecting tile @ y%d, x*: yh clip' % (y)
                continue
            for x in xrange(xt0, xt1, self.tw):                 
                # Are we trying to construct a tile in the buffer zone?
                if (not skip_xl_check) and x < x0 + self.clip_width:
                    if self.verbose:
                        print 'Rejecting tiles @ y%d, x%d: xl clip' % (y, x)
                    continue
                if (not skip_xh_check) and x + self.tw >= x1 - self.clip_width:
                    if self.verbose:
                        print 'Rejecting tiles @ y%d, x%d: xh clip' % (y, x)
                    continue
                yield (y, x)
                
    def process_image(self, img, st_bounds):
        '''
        A tile is valid if its in a safe location
        There are two ways for the location to be safe:
        -No neighboring tiles as found on canvas edges
        -Sufficiently inside the blend area that artifacts should be minimal
        '''
        bench = Benchmark()
        [x0, x1, y0, y1] = st_bounds
        gen_tiles = 0
        print
        # TODO: get the old info back if I miss it after yield refactor
        print 'Phase 4: chopping up supertile'
        self.msg('step(x: %d, y: %d)' % (self.tw, self.th), 3)
        #self.msg('x in xrange(%d, %d, %d)' % (xt0, xt1, self.tw), 3)
        #self.msg('y in xrange(%d, %d, %d)' % (yt0, yt1, self.th), 3)
    
        for (y, x) in self.gen_supertile_tiles(st_bounds):    
            # If we made it this far the tile can be constructed with acceptable enblend artifacts
            row = self.y2row(y)
            col = self.x2col(x)
        
            # Did we already do this tile?
            if self.is_done(row, col):
                # No use repeating it although it would be good to diff some of these
                if self.verbose:
                    print 'Rejecting tile x%d, y%d / r%d, c%d: already done' % (x, y, row, col)
                continue
        
            # note that x and y are in whole pano coords
            # we need to adjust to our frame
            # row and col on the other hand are used for global naming
            self.make_tile(img, x - x0, y - y0, row, col)
            gen_tiles += 1
        bench.stop()
        print 'Generated %d new tiles for a total of %d / %d in %s' % (gen_tiles, len(self.closed_list), self.net_expected_tiles, str(bench))
        if gen_tiles == 0:
            raise Exception("Didn't generate any tiles")
        # temp_file should be automatically deleted upon exit
        # WARNING: not all are tmp files, some may be recycled supertiles
    
    def get_name(self, row, col):
        out_dir = ''
        if self.out_dir:
            out_dir = '%s/' % self.out_dir
        return '%sy%03d_x%03d%s' % (out_dir, row, col, self.out_extension)
    
    def make_tile(self, i, x, y, row, col):
        '''Make a tile given an image, the upper left x and y coordinates in that image, and the global row/col indices'''    
        if self.dry:
            if self.verbose:
                print 'Dry: not making tile w/ x%d y%d r%d c%d' % (x, y, row, col)
        else:
            xmin = x
            ymin = y
            xmax = min(xmin + self.tw, i.width())
            ymax = min(ymin + self.th, i.height())
            nfn = self.get_name(row, col)

            if self.verbose:
                print 'Subtile %s: (x %d:%d, y %d:%d)' % (nfn, xmin, xmax, ymin, ymax)
            ip = i.subimage(xmin, xmax, ymin, ymax)
            '''
            Images must be padded
            If they aren't they will be stretched in google maps
            '''
            if ip.width() != self.tw or ip.height() != self.th:
                dbg('WARNING: %s: expanding partial tile (%d X %d) to full tile size' % (nfn, ip.width(), ip.height()))
                ip.set_canvas_size(self.tw, self.th)
            # http://www.pythonware.com/library/pil/handbook/format-jpeg.htm
            # JPEG is a good quality vs disk space compromise but beware:
            # The image quality, on a scale from 1 (worst) to 95 (best).
            # The default is 75. 
            # Values above 95 should be avoided;
            # 100 completely disables the JPEG quantization stage.
            ip.image.save(nfn, quality=95)    
        self.mark_done(row, col)
                
    def x2col(self, x):
        col = int((x - self.x0) / self.tw)
        if col < 0:
            print x, self.x0, self.tw
            raise Exception("Can't have negative col")
        return col
    
    def y2row(self, y):
        ret = int((y - self.y0) / self.th)
        if ret < 0:
            print y, self.y0, self.th
            raise Exception("can't have negative row")
        return ret
    
    def is_done(self, row, col):
        return (row, col) in self.closed_list
    
    def mark_done(self, row, col, current = True):
        self.closed_list.add((row, col))
        if current:
            self.this_tiles_done += 1
    
    def tiles_done(self):
        '''Return total number of tiles completed'''
        return len(self.closed_list)
    
    def gen_open_list(self):
        for y in xrange(self.rows()):
            for x in xrange(self.cols()):
                if not self.is_done(y, x):
                    yield (y, x)
    
    def dump_open_list(self):
        print 'Open list:'
        for (row, col) in self.gen_open_list():
            print '  r%d c%d' % (row, col)
            
    def rows(self):
        return int(math.ceil(self.height() / self.th))
    
    def cols(self):
        return int(math.ceil(self.width() / self.tw))
            
    def height(self):
        return abs(self.top() - self.bottom())
    
    def width(self):
        return abs(self.right() - self.left())
    
    def left(self):
        return self.x0
        
    def right(self):
        return self.x1
    
    def top(self):
        return self.y0
    
    def bottom(self):
        return self.y1
    
    def optimize_step(self):
        '''
        TODO: even out the steps, we can probably get slightly better results
        
        The ideal step is to advance to the next area where it will be legal to create a new 
        Slightly decrease the step to avoid boundary conditions
        Although we clip on both side we only have to get rid of one side each time
        '''
        #txstep = self.stw - self.clip_width - 1
        #tystep = self.sth - self.clip_height - 1
        pass
    
    def gen_supertiles(self):
        # 0:256 generates a 256 width pano
        # therefore, we don't want the upper bound included
        
        print 'M: Generating supertiles from y(%d:%d) x(%d:%d)' % (self.top(), self.bottom(), self.left(), self.right())
        #row = 0
        y_done = False
        for y in xrange(self.top(), self.bottom(), self.super_t_ystep):
            y0 = y
            y1 = y + self.sth
            if y1 >= self.bottom():
                y_done = True
                y0 = max(self.top(), self.bottom() - self.sth)
                y1 = self.bottom()
                print 'M: Y %d:%d would have overstretched, shifting to maximum height position %d:%d' % (y, y + self.sth, y0, y1)
                
            #col = 0
            x_done = False
            for x in xrange(self.left(), self.right(), self.super_t_xstep):
                x0 = x
                x1 = x + self.stw
                # If we have reached the right side align to it rather than truncating
                # This makes blending better to give a wider buffer zone
                if x1 >= self.right():
                    x_done = True
                    x0 = max(self.left(), self.right() - self.stw)
                    x1 = self.right()
                    print 'M: X %d:%d would have overstretched, shifting to maximum width position %d:%d' % (x, x + self.stw, x0, x1)
                
                yield [x0, x1, y0, y1]
                
                #col += 1
                if x_done:
                    break
            #row +=1     
            if y_done:
                break
        print 'M: All supertiles generated'
        
    def n_supertile_tiles(self, st_bounds):
        return len(list(self.gen_supertile_tiles(st_bounds)))
        
    def should_try_supertile(self, st_bounds):
        # If not merging always stitch
        if not self.merge:
            return True
        
        print 'M: checking supertile for existing tiles with %d candidates' % (self.n_supertile_tiles(st_bounds))
        
        for (y, x) in self.gen_supertile_tiles(st_bounds):
            # If we made it this far the tile can be constructed with acceptable enblend artifacts
            row = self.y2row(y)
            col = self.x2col(x)
            
            #print 'Checking (r%d, c%d)' % (row, col)
            # Did we already do this tile?
            if not self.is_done(row, col):
                return True
        return False
    
    def seed_merge(self):
        '''Add all already generated tiles to the closed list'''
        icm = ImageCoordinateMap.from_dir_tagged_file_names(self.out_dir)
        already_done = 0
        for (col, row) in icm.gen_set():
            self.mark_done(row, col, False)
            already_done += 1
        print 'Map seeded with %d already done tiles' % already_done
    
    def run(self):
        print 'Input images width %d, height %d' % (self.img_width, self.img_height)
        print 'Output to %s' % self.out_dir
        print 'Super tile width %d, height %d from scalar %d' % (self.stw, self.sth, self.st_scalar_heuristic)
        print 'Super tile x step %d, y step %d' % (self.super_t_xstep, self.super_t_ystep)
        print 'Supertile clip width %d, height %d' % (self.clip_width, self.clip_height)
        
        if self.merge and self.force:
            raise Exception('Can not merge and force')
        
        if not self.dry:
            self.dry = True
            print
            print
            print
            print '***BEGIN DRY RUN***'
            self.run()
            print '***END DRY RUN***'
            print
            print
            print
            self.dry = False
            
        if not self.ignore_crop and self.pto.get_panorama_line().getv('S') is None:
            raise Exception('Not cropped.  Set ignore crop to force continue')

        '''
        if we have a width of 256 and 1 pixel we need total size of 256
        If we have a width of 256 and 256 pixels we need total size of 256
        if we have a width of 256 and 257 pixel we need total size of 512
        '''
        print 'Tile width: %d, height: %d' % (self.tw, self.th)
        print 'Net size: %d width (%d:%d) X %d height (%d:%d) = %d MP' % (self.width(), self.left(), self.right(), self.height(), self.top(), self.bottom(), self.width() * self.height() / 1000000)
        print 'Output image extension: %s' % self.out_extension
        
        self.this_tiles_done = 0
        
        bench = Benchmark()
        
        # Scrub old dir if we don't want it
        if os.path.exists(self.out_dir) and not self.merge:
            if self.force:
                if not self.dry:
                    shutil.rmtree(self.out_dir)
            else:
                raise Exception("Must set force to override output")
        if not self.dry and not os.path.exists(self.out_dir):
            os.mkdir(self.out_dir)
        if self.st_dir and not self.dry and not os.path.exists(self.st_dir):
            os.mkdir(self.st_dir)
        # in form (row, col)
        self.closed_list = set()
        
        self.n_expected_sts = len(list(self.gen_supertiles()))
        print 'M: Generating %d supertiles' % self.n_expected_sts
        
        x_tiles_ideal = 1.0 * self.width() / self.tw
        x_tiles = math.ceil(x_tiles_ideal)
        y_tiles_ideal = 1.0 * self.height() / self.th
        y_tiles = math.ceil(y_tiles_ideal)
        self.net_expected_tiles = x_tiles * y_tiles
        ideal_tiles = x_tiles_ideal * y_tiles_ideal
        print 'M: Ideal tiles: %0.3f x, %0.3f y tiles => %0.3f net' % (
                x_tiles_ideal, y_tiles_ideal, ideal_tiles)
        print 'M: Expecting to generate x%d, y%d => %d basic tiles' % (
                x_tiles, y_tiles, self.net_expected_tiles)
        if self.merge:
            self.seed_merge()

        print 'M: Initializing %d workers' % self.threads
        self.workers = []
        for ti in xrange(self.threads):
            w = Worker(ti, self)
            self.workers.append(w)
            w.start()

        print
        print
        print
        print 'S' * 80
        print 'M: Serial end'
        print 'P' * 80

        try:
            #temp_file = 'partial.tif'
            self.n_supertiles = 0
            st_gen = self.gen_supertiles()
    
            all_allocated = False
            last_progress = time.time()
            pair_submit = 0
            pair_complete = 0
            idle = False
            while not (all_allocated and pair_complete == pair_submit):
                progress = False
                # Check for completed jobs
                for wi, worker in enumerate(self.workers):
                    try:
                        out = worker.qo.get(False)
                    except Queue.Empty:
                        continue
                    pair_complete += 1
                    what = out[0]
                    progress = True
    
                    if what == 'done':
                        (st_bounds, img) = out[1]
                        print 'MW%d: done w/ submit %d, complete %d' % (wi, pair_submit, pair_complete)
                        self.process_image(img, st_bounds)
                    elif what == 'exception':
                        if not self.ignore_errors:
                            for worker in self.workers:
                                worker.running.clear()
                            # let stdout clear up
                            # (only moderately effective)
                            time.sleep(1)
                        
                        #(_task, e) = out[1]
                        print '!' * 80
                        print 'M: ERROR: MW%d failed w/ exception' % wi
                        (_task, _e, estr) = out[1]
                        print 'M: Stack trace:'
                        for l in estr.split('\n'):
                            print l
                        print '!' * 80
                        if self.ignore_errors:
                            raise Exception('M: shutdown on worker failure')
                        print 'M WARNING: continuing despite worker failure'
                    else:
                        print 'M: %s' % (out,)
                        raise Exception('M: internal error: bad task type %s' % what)
    
                # Any workers need more work?
                for wi, worker in enumerate(self.workers):
                    if all_allocated:
                        break
                    if worker.qi.empty():
                        while True:
                            try:
                                st_bounds = st_gen.next()
                            except StopIteration:
                                print 'M: all tasks allocated'
                                all_allocated = True
                                break
            
                            progress = True

                            [x0, x1, y0, y1] = st_bounds
                            self.n_supertiles += 1
                            print 'M: checking supertile x(%d:%d) y(%d:%d)' % (x0, x1, y0, y1)
                            if not self.should_try_supertile(st_bounds):
                                print 'M WARNING: skipping supertile %d as it would not generate any new tiles' % self.n_supertiles
                                continue
                
                            print '*' * 80
                            #print 'W%d: submit %s (%d / %d)' % (wi, repr(pair), pair_submit, n_pairs)
                            print "Creating supertile %d / %d with x%d:%d, y%d:%d" % (self.n_supertiles, self.n_expected_sts, x0, x1, y0, y1)
                            print 'W%d: submit' % (wi,)
                
                            worker.qi.put((st_bounds,))
                            pair_submit += 1
                            break
    
                if progress:
                    last_progress = time.time()
                    idle = False
                else:
                    if not idle:
                        print 'M Server thread idle'
                    idle = True
                    # can take some time, but should be using smaller tiles now
                    if time.time() - last_progress > 4 * 60 * 60:
                        print 'M WARNING: server thread stalled'
                        last_progress = time.time()
                        time.sleep(0.1)

    
            bench.stop()
            print 'M Processed %d supertiles to generate %d new (%d total) tiles in %s' % (self.n_expected_sts, self.this_tiles_done, self.tiles_done(), str(bench))
            tiles_s = self.this_tiles_done / bench.delta_s()
            print 'M %f tiles / sec, %f pix / sec' % (tiles_s, tiles_s * self.tw * self.th)
            
            if self.tiles_done() != self.net_expected_tiles:
                print 'M ERROR: expected to do %d basic tiles but did %d' % (self.net_expected_tiles, self.tiles_done())
                self.dump_open_list()
                raise Exception('State mismatch')
        finally:
            print 'Shutting down workers'
            for worker in self.workers:
                worker.running.clear()
            print 'Waiting for workers to exit...'
            for i, worker in enumerate(self.workers):
                worker.join(1)
                if worker.isAlive():
                    print '  W%d: failed to join' % i
                else:
                    print '  W%d: stopped' % i
            self.workers = None
