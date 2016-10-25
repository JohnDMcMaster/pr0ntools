'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details

This is a stitching strategy where a regular input grid is assumed
I get this using my CNC microscope because the pictures *are* taken as fairly precise intervals
This allows considerable optimization since we know where all the picture are
'''

import image_coordinate_map
from image_coordinate_map import ImageCoordinateMap
import os
import sys
from pr0ntools.stitch.pto.util import dbg
import Queue
import traceback
import common_stitch
import time
import shutil
import multiprocessing

from pr0ntools.util import IOTimestamp

class Worker(object):
    def __init__(self, i, log_fn):
        self.process = multiprocessing.Process(target=self.run)
        
        self.i = i
        self.qi = multiprocessing.Queue()
        self.qo = multiprocessing.Queue()
        self.pq = multiprocessing.Queue()
        self.running = multiprocessing.Event()
        self.generate_control_points_by_pair = None
        self.idle = True
        self.log_fn = log_fn
        
    def start(self):
        self.process.start()
        # Prevents later join failure
        self.running.wait(1)

    def run(self):
        _outlog = open(self.log_fn, 'w')
        sys.stdout = _outlog
        sys.stderr = _outlog

        _outdate = IOTimestamp(sys, 'stdout')
        _errdate = IOTimestamp(sys, 'stderr')

        self.running.set()
        while self.running.is_set():
            try:
                task = self.qi.get(True, 0.1)
            except Queue.Empty:
                self.idle = True
                continue
            self.idle = False
            
            try:
                (pair, pair_fns) = task

                print
                print
                print
                print
                print
                print '*' * 80
                print 'w%d: task rx' % self.i
            
                pto = self.generate_control_points_by_pair(pair, pair_fns)
                
                if not pto:
                    print 'WARNING: bad project @ %s, %s' % (repr(pair), pair_fns)
                else:
                    if len(pto.get_text().strip()) == 0:
                        raise Exception('Generated empty pair project')
                
                self.qo.put(('done', (task, pto)))
                print 'w%d: task done' % self.i
                
            except Exception as e:
                traceback.print_exc()
                estr = traceback.format_exc()
                self.qo.put(('exception', (task, e, estr)))

class GridStitch(common_stitch.CommonStitch):
    def __init__(self):
        common_stitch.CommonStitch.__init__(self)
        self.coordinate_map = None
        self.set_regular(True)
        self.canon2orig = dict()
        self.skip_missing = False
        self.threads = 1
        self.workers = []
        self.workers_p = []
        
    @staticmethod
    def from_tagged_file_names(image_file_names):
        engine = GridStitch()
        engine.image_file_names = image_file_names
        dbg('Orig file names: %s' % str(image_file_names))
        
        file_names_canonical = list()
        for file_name in image_file_names:
            new_fn = os.path.realpath(file_name)
            engine.canon2orig[new_fn] = file_name
            file_names_canonical.append(new_fn)
        
        engine.coordinate_map = ImageCoordinateMap.from_tagged_file_names(file_names_canonical)
        
        return engine

    def init_failures(self):
        open_list = set()
        for (file_name, _row, _col) in self.coordinate_map.images():
            open_list.add(file_name)
        self.failures = common_stitch.FailedImages(open_list)
        
        
    def generate_control_points(self):
        '''
        Generate control points
        Generate to all neighbors to start with
        '''
        #temp_projects = list()

        print
        n_pairs = len(list(self.coordinate_map.gen_pairs(1, 1)))
        print '***Pairs: %d***' % n_pairs
        print
        pair_submit = 0
        pair_complete = 0
        
        if self.skip_missing:
            print 'Not verifying image map'
        else:
            print 'Verifying image map'
            try:
                self.coordinate_map.is_complete()
            except image_coordinate_map.MissingImage as e:
                print '!' * 80
                print 'Missing images.  Use --skip-missing to continue'
                print '!' * 80
                raise e
        
        print 'Initializing %d workers' % self.threads
        for ti in xrange(self.threads):
            w = Worker(ti, os.path.join(self.log_dir, 'w%02d.log' % ti))
            w.generate_control_points_by_pair = self.generate_control_points_by_pair
            self.workers.append(w)
            w.start()

        try:
            coord_pairs = self.coordinate_map.gen_pairs(1, 1)
            
            all_allocated = False
    
            # Seed project with all images in order
            # note we used the filename that will get used below
            # not the final output file name
            for can_fn in sorted(self.canon2orig.keys()):
                self.project.add_image(can_fn)
            self.project.save()
    
            last_progress = time.time()
            while not (all_allocated and pair_complete == pair_submit):
                progress = False
                # Most efficient to merge things in batches as they complete
                final_pair_projects = []
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
                        (task, pto) = out[1]
                        prog = 'complete %d/%d' % (pair_complete, n_pairs)
                        print 'W%d: done w/ submit %d, %s' % (wi, pair_submit, prog)
                        
                        (_pair, pair_fns) = task
                        if pto:
                            self.failures.add_success(pair_fns)
                        else:
                            self.failures.add_failure(pair_fns)

                        fn = os.path.join(self.log_dir, 'stat.txt')
                        open(fn + '.tmp', 'w').write(prog + '\n')
                        shutil.move(fn + '.tmp', fn)
                        # May have failed
                        if pto:
                            final_pair_projects.append(pto)
                            if pair_complete % 10 == 0:
                                print 'Saving intermediate result to %s' % self.project.file_name
                                self.project.save()
                                print 'Saved'
    
                    elif what == 'exception':
                        for worker in self.workers:
                            worker.running.clear()
                        # let stdout clear up
                        time.sleep(1)
                        
                        #(_task, e) = out[1]
                        print '!' * 80
                        print 'ERROR: W%d failed w/ exception' % wi
                        (_task, _e, estr) = out[1]
                        print 'Stack trace:'
                        for l in estr.split('\n'):
                            print l
                        print '!' * 80
                        raise Exception('Shutdown on worker failure')
                    else:
                        print '%s' % (out,)
                        raise Exception('Internal error: bad task type %s' % what)
                # Merge projects
                if len(final_pair_projects):
                    print 'Merging %d projects' % len(final_pair_projects)
                    self.project.merge_into(final_pair_projects)
                
                # Any workers need more work?
                for wi, worker in enumerate(self.workers):
                    if all_allocated:
                        break
                    if worker.qi.empty():
                        while True:
                            try:
                                pair = coord_pairs.next()
                            except  StopIteration:
                                print 'All tasks allocated'
                                all_allocated = True
                                break
            
                            progress = True
                
                            print '*' * 80
                            print 'W%d: submit %s (%d / %d)' % (wi, repr(pair), pair_submit, n_pairs)
                
                            # Image file names as list
                            pair_images = self.coordinate_map.get_images_from_pair(pair)
                            print 'pair images: ' + repr(pair_images)
                            if pair_images[0] is None or pair_images[1] is None:
                                print 'WARNING: skipping missing image'
                                continue
                                
                            worker.qi.put((pair, pair_images))
                            pair_submit += 1
                            break
                        
                if progress:
                    last_progress = time.time()
                else:
                    if time.time() - last_progress > 30:
                        print 'WARNING: server thread stalled'
                        last_progress = time.time()
                
                time.sleep(0.1)
                
            print 'pairs done'
            
        finally:
            print 'Shutting down workers'
            for worker in self.workers:
                worker.running.clear()
        
        print 'Reverting canonical file names to original input...'
        # Fixup the canonical hack
        for can_fn in self.canon2orig:
            # FIXME: if we have issues with images missing from the project due to bad stitch
            # we should add them (here?) instead of throwing an error
            orig = self.canon2orig[can_fn]
            il = self.project.get_image_by_fn(can_fn)
            if il:
                il.set_name(orig)
            else:
                print 'WARNING: adding image without feature match %s' % orig
                self.project.add_image(orig)

        self.project.save()
        
        '''
        if 0:
            print 'Sub projects (full image):'
            for project in temp_projects:
                # prefix so I can grep it for debugging
                print '\tSUB: ' + project.file_name
        '''
        '''
        if 0:
            print
            print
            print 'Master project file: %s' % self.project.file_name
            print
            print
            print self.project.text
            print
            print
        '''
            
    def do_generate_control_points_by_pair(self, pair, image_fn_pair):
        ret = common_stitch.CommonStitch.do_generate_control_points_by_pair(self, pair, image_fn_pair)
        if ret is None and pair.adjacent():
            print 'WARNING: last ditch effort, increasing field of view'
            
        return ret

