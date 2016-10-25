#!/usr/bin/python
'''
pr0ntile: IC die image stitching and tile generation
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import sys 
import os.path
from pr0ntools import pimage
from pr0ntools.pimage import PImage
from pr0ntools.pimage import TempPImage
from pr0ntools.stitch.wander_stitch import WanderStitch
from pr0ntools.stitch.grid_stitch import GridStitch
from pr0ntools.stitch.fortify_stitch import FortifyStitch
from pr0ntools.execute import Execute
from PIL import Image
from pr0ntools.stitch.image_coordinate_map import ImageCoordinateMap
import shutil
import math
import Queue
import multiprocessing
import traceback
import time

def get_fn(basedir, row, col, ext='.jpg'):
    return '%s/y%03d_x%03d%s' % (basedir, row, col, ext)

def get_fn_level(basedir, level, row, col, ext='.jpg'):
    return '%s/%d/y%03d_x%03d%s' % (basedir, level, row, col, ext)

def calc_max_level_from_image(image, zoom_factor=None):
    return calc_max_level(image.height(), image.width(), zoom_factor)

def calc_max_level(height, width, zoom_factor=None):
    if zoom_factor is None:
        zoom_factor = 2
    '''
    Calculate such that max level is a nice screen size
    Lets be generous for small viewers...especially considering limitations of mobile devices
    '''
    fit_width = 640
    fit_height = 480
    
    width_levels = math.ceil(math.log(width, zoom_factor) - math.log(fit_width, zoom_factor))
    height_levels = math.ceil(math.log(height, zoom_factor) - math.log(fit_height, zoom_factor))
    max_level = int(max(width_levels, height_levels, 0))
    # Take the number of zoom levels required to fit the entire thing on screen
    print 'Calc max zoom level for %d X %d screen: %d (wmax: %d lev / %d pix, hmax: %d lev / %d pix)' % (fit_width, fit_height, max_level, width_levels, width, height_levels, height)
    return max_level

'''
Take a single large image and break it into tiles
'''
class ImageTiler(object):
    def __init__(self, image, x0 = None, x1 = None, y0 = None, y1 = None, tw = 250, th = 250):
        self.verbose = False
        self.image = image
        self.progress_inc = 0.10
        
        if x0 is None:
            x0 = 0
        self.x0 = x0
        if x1 is None:
            x1 = image.width()
        self.x1 = x1
        if y0 is None:
            y0 = 0
        self.y0 = y0
        if y1 is None:
            y1 = image.height()
        self.y1 = y1
        
        self.tw = tw
        self.th = th
        self.out_dir = None

        self.set_out_extension('.jpg')
        
    def set_out_extension(self, s):
        self.out_extension = s
        
    # FIXME / TODO: this isn't the google reccomended naming scheme, look into that more    
    # part of it was that I wanted them to sort nicely in file list view
    def get_name(self, row, col):
        out_dir = ''
        if self.out_dir:
            out_dir = '%s/' % self.out_dir
        return '%sy%03d_x%03d%s' % (out_dir, row, col, self.out_extension)
        
    def make_tile(self, x, y, row, col):
        xmin = x
        ymin = y
        xmax = min(xmin + self.tw, self.x1)
        ymax = min(ymin + self.th, self.y1)
        nfn = self.get_name(row, col)

        if self.verbose:
            print '%s: (x %d:%d, y %d:%d)' % (nfn, xmin, xmax, ymin, ymax)
        ip = self.image.subimage(xmin, xmax, ymin, ymax)
        '''
        Images must be padded
        If they aren't they will be stretched in google maps
        '''
        if ip.width() != self.tw or ip.height() != self.th:
            if self.verbose:
                print 'WARNING: %s: expanding partial tile (%d X %d) to full tile size' % (nfn, ip.width(), ip.height())
            ip.set_canvas_size(self.tw, self.th)
        ip.image.save(nfn)
        
    def run(self):
        '''
        Namer is a function that accepts the following arguments and returns a string:
        namer(row, col)
    
        python can bind objects to functions so a user parameter isn't necessary?
        '''
    
        '''
        if namer is None:
            namer = google_namer
        '''

        col = 0
        next_progress = self.progress_inc
        processed = 0
        n_images = len(range(self.x0, self.x1, self.tw)) * len(range(self.y0, self.y1, self.th))
        for x in xrange(self.x0, self.x1, self.tw):
            row = 0
            for y in xrange(self.y0, self.y1, self.th):
                self.make_tile(x, y, row, col)
                row += 1
                processed += 1
                if self.progress_inc:
                    cur_progress = 1.0 * processed / n_images
                    if cur_progress >= next_progress:
                        print 'Progress: %02.2f%% %d / %d' % (cur_progress * 100, processed, n_images)
                        next_progress += self.progress_inc
            col += 1

'''
Only support tiled workers since unclear if full image can/should be parallelized
'''
class TWorker(object):
    def __init__(self,
            ti, qo, ext,
            # tile width/height
            tw, th):
        self.process = multiprocessing.Process(target=self.run)
        self.ti = ti
        
        self.qi = multiprocessing.Queue()
        self.qo = qo
        self.running = multiprocessing.Event()
        
        self.ext = ext
        self.tw = tw
        self.th = th
        self.zoom = 2.0
    
    def submit(self, event, args):
        self.qi.put((event, args))

    def complete(self, event, args):
        self.qo.put((self.ti, event, args))

    def task_subtile(self, val):
        dst_dir, dst_row, dst_cols, src_dir = val
        src_rowb = 2 * dst_row
        
        # Workers are given 1 output row (2 input rows) at a time
        for dst_col in xrange(dst_cols):
            src_colb = 2 * dst_col

            # Collapse 2x2
            # XXX: how much faster would it be to actually know?
            # Would we save anything given that occasionally I process broken sets?
            # Just guess based on fn existing since its most foolproof anyway
            # adjust to be more accurate if we have a reason to care
            src_img_fns = [
                [None, None],
                [None, None],
                ]
            for src_col in xrange(src_colb, src_colb + 2):
                for src_row in xrange(src_rowb, src_rowb + 2):
                    fn = get_fn(src_dir, src_row, src_col, ext=self.ext)
                    src_img_fns[src_row - src_rowb][src_col - src_colb] = fn if os.path.exists(fn) else None
            
            img_full = pimage.from_fns(src_img_fns,
                    tw=self.tw, th=self.th)
            img_scaled = pimage.rescale(img_full, 0.5, filt=Image.ANTIALIAS)
            dst_fn = get_fn(dst_dir, dst_row, dst_col, ext=self.ext)
            img_scaled.save(dst_fn)
    
    def start(self):
        self.process.start()
        # Prevents later join failure
        self.running.wait(1)

    def run(self):
        self.running.set()
        #print 'Worker starting'
        while self.running.is_set():
            try:
                task, args = self.qi.get(True, 0.1)
            except Queue.Empty:
                continue
            
            def task_subtile(args):
                self.task_subtile(args)
                self.complete('done', args)
            
            taskers = {
                'subtile': task_subtile,
                }
            
            try:
                taskers[task](args)
            except Exception as e:
                raise
                #if not self.ignore_errors:
                #    raise
                # We shouldn't be trying commands during dry but just in case should raise?
                print 'WARNING: got exception trying supertile %s' % str(task)
                traceback.print_exc()
                estr = traceback.format_exc()
                self.complete('exception', (task, e, estr))

'''
Creates smaller tiles from source tiles
'''
class TileTiler(object):
    def __init__(self, rows, cols, src_dir, max_level, min_level=0, dst_basedir=None, threads=1):
        self.verbose = False
        self.cp_lmax = True
        self.src_dir = src_dir
        self.max_level = max_level
        self.min_level = min_level
        self.dst_basedir = dst_basedir
        self.set_out_extension('.jpg')
        self.zoom_factor = 2
        self.tw = 250
        self.th = 250
        # JPEG quality level, 1-100 or something
        self.quality = 90
        # Fraction of 1 to print each progress level at
        # None to disable
        self.progress_inc = 0.10
        self.threads = threads

        self.workers = None
        
        self.rcs = {}
        for level in xrange(self.max_level, self.min_level - 1, -1):
            if rows == 0 or cols == 0:
                raise Exception()
            self.rcs[level] = (rows, cols)
            def div_rnd(x):
                # 4 => 2
                # 3 => 2
                # 2 => 1
                if x % 2 == 0:
                    return x / 2
                else:
                    return x / 2 + 1
            rows = div_rnd(rows)
            cols = div_rnd(cols)

    def wstart(self):
        self.workers = []
        self.wopen = set()
        # Our input queue / worker output queue
        self.qi = multiprocessing.Queue()
        for wi in xrange(self.threads):
            print 'Bringing up W%02d' % wi
            w = TWorker(wi, self.qi, ext='.jpg',
                tw=self.tw, th=self.th)
            self.workers.append(w)
            w.start()
            self.wopen.add(wi)

    def wkill(self):
        if self.workers is None:
            return
        
        print 'Shutting down workers'
        for worker in self.workers:
            worker.running.clear()
        print 'Waiting for workers to exit...'
        allw = True
        for wi, worker in enumerate(self.workers):
            if worker is None:
                continue
            worker.process.join(1)
            if worker.process.is_alive():
                print '  W%d: failed to join' % wi
                allw = False
            else:
                print '  W%d: stopped' % wi
                self.workers[wi] = None
                self.wopen.remove(wi)
        if allw:
            self.workers = None

    def set_out_extension(self, s):
        self.out_extension = s

    def subtile(self, level, dst_dir, src_dir):
        '''Subtile from previous level'''
        
        # Prepare a new image coordinate map so we can form the next tile set
        src_rows, src_cols = self.rcs[level + 1]
        dst_rows, dst_cols = self.rcs[level]
        dst_images = src_rows * dst_rows
        
        print 'Shrink by %0.1f: cols %s => %s, rows %s => %s' % (self.zoom_factor,
                src_cols, dst_cols,
                src_rows, dst_rows)
        
        next_progress = self.progress_inc
        done = 0
        # AttributeError: 'xrange' object has no attribute 'next'
        def dst_row_genf():
            for x in xrange(dst_rows):
                yield x
        dst_row_gen = dst_row_genf()
        
        while True:
            idle = True
            
            # No more jobs to give and all workers are idle?
            if dst_row_gen is None and len(self.wopen) == len(self.workers):
                break
            
            # Scrub completed tasks
            while True:
                try:
                    wi, event, val = self.qi.get(False)
                except Queue.Empty:
                    break
                if event != 'done':
                    print event, val
                    raise Exception()
                idle = False
                self.wopen.add(wi)
                
                done += 1
                progress = 1.0 * done / dst_images
                if self.progress_inc and progress >= next_progress:
                    print 'Progress: %02.2f%% %d / %d' % (progress * 100, done, dst_images)
                    next_progress += self.progress_inc
            
            # More tasks to give?
            if dst_row_gen and len(self.wopen):
                # Assign next task
                try:
                    dst_row = dst_row_gen.next()
                # Out of tasks?
                except StopIteration:
                    dst_row_gen = None
                    continue
                
                idle = False
                worker = self.workers[self.wopen.pop()]
                worker.submit('subtile',
                    (dst_dir, dst_row, dst_cols,
                    src_dir))
                continue
            
            if idle:
                # Couldn't find something to do
                time.sleep(0.05)
            
        # Next shrink will be on the previous tile set, not the original
        if self.verbose:
            print 'Shrinking the world for future rounds'

    def run(self):
        try:
            self.wstart()
            
            if not os.path.exists(self.dst_basedir):
                os.mkdir(self.dst_basedir)
            
            for level in xrange(self.max_level, self.min_level - 1, -1):
                print
                print '************'
                print 'Zoom level %d' % level
                dst_dir = '%s/%d' % (self.dst_basedir, level)
                
                # For the first level we may just copy things over
                if level == self.max_level:
                    src_dir = self.src_dir
                    if self.cp_lmax:
                        print 'Direct copying on first zoom %s => %s' % (src_dir, dst_dir)
                        shutil.copytree(src_dir, dst_dir)
                    else:
                        # explicitly load and save images to clean dir, same jpg format
                        # a bit more paranoid but questionable utility still
                        raise Exception()
                # Additional levels we take the image coordinate map and shrink
                else:
                    src_dir = '%s/%d' % (self.dst_basedir, level + 1)
                    if not os.path.exists(dst_dir):
                        os.mkdir(dst_dir)
                    self.subtile(level, dst_dir, src_dir)
        finally:
            self.wkill()

    def __del__(self):
        self.wkill()

# replaces from_single
class SingleTiler:
    def __init__(self, fn, max_level = None, min_level = None, out_dir_base=None):
        self.fn = fn
        self.max_level = max_level
        self.min_level = min_level
        self.dst_basedir = out_dir_base
        self.set_out_extension('.jpg')
        self.progress_inc = 0.10

    def set_out_extension(self, s):
        self.out_extension = s

    def run(self):
        fn = self.fn
        max_level = self.max_level
        min_level = self.min_level

        if min_level is None:
            min_level = 0
        i = PImage.from_file(fn)
        if max_level is None:
            max_level = calc_max_level_from_image(i)
    
        '''
        Test file is the carved out metal sample of the 6522
        It is 5672 x 4373 pixels
        I might do a smaller one first
        '''
        if not os.path.exists(self.dst_basedir):
            os.mkdir(self.dst_basedir)
        
        for level in xrange(max_level, min_level - 1, -1):
            print
            print '************'
            print 'Zoom level %d' % level
            out_dir = '%s/%d' % (self.dst_basedir, level)
            if not os.path.exists(out_dir):
                os.mkdir(out_dir)
        
            tiler = ImageTiler(i)
            tiler.progress_inc = self.progress_inc
            tiler.out_dir = out_dir
            tiler.run()
        
            if level != min_level:
                # Each zoom level is half smaller than previous
                i = i.get_scaled(0.5, filt=Image.ANTIALIAS)
                if 0:
                    i.save('test.jpg')
                    sys.exit(1)

