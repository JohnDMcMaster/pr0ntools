'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details

This is a stitching strategy where a regular input grid is assumed
I get this using my CNC microscope because the pictures *are* taken as fairly precise intervals
This allows considerable optimization since we know where all the picture are
'''

from image_coordinate_map import ImageCoordinateMap
import os
import sys
from pr0ntools.stitch.pto.util import dbg
import threading
import Queue
import traceback
from common_stitch import *
#from pr0ntools.util import msg
import time

# FIXME: placeholder
def msg(s=''):
    #print '%s: %s' % (now(), s)
    print s

class Worker(threading.Thread):
    def __init__(self, i):
        threading.Thread.__init__(self)
        self.i = i
        self.qi = Queue.Queue()
        self.qo = Queue.Queue()
        self.running = threading.Event()
        self.generate_control_points_by_pair = None

    def run(self):
        self.running.set()
        while self.running.is_set():
            try:
                task = self.qi.get(True, 0.1)
            except Queue.Empty:
                continue
            
            try:
                (pair, pair_images) = task

                msg()
                msg()
                msg()
                msg()
                msg()
                msg('*' * 80)
                msg('w%d: task rx' % self.i)
            
                final_pair_project = self.generate_control_points_by_pair(pair, pair_images)
                
                if not final_pair_project:
                    msg('WARNING: bad project @ %s, %s' % (repr(pair), repr(pair_images)))
                else:
                    if False:
                        msg()
                        msg('Final pair project')
                        msg(final_pair_project.get_a_file_name())
                        msg()
                        msg()
                        msg(final_pair_project)
                        msg()
                        msg()
                        msg()
                        #sys.exit(1)
                    if len(final_pair_project.get_text().strip()) == 0:
                        raise Exception('Generated empty pair project')
                
                self.qo.put(('done', (task, final_pair_project)))
                msg('w%d: task done' % self.i)
                
            except Exception as e:
                traceback.print_exc()
                self.qo.put(('exception', (task, e)))

class GridStitch(CommonStitch):
    def __init__(self):
        CommonStitch.__init__(self)
        self.coordinate_map = None
        self.set_regular(True)
        self.canon2orig = dict()
        self.skip_missing = False
        self.threads = 1
        self.workers = []
        
    @staticmethod
    def from_file_names(image_file_names, flip_col = False, flip_row = False, flip_pre_transpose = False, flip_post_transpose = False, depth = 1,
            alt_rows = False, alt_cols = False, rows = None, cols = None):
        engine = GridStitch()
        engine.image_file_names = image_file_names
        dbg('Orig file names: %s' % str(image_file_names))
        
        '''
        Certain program take file names relative to the project file, others to working dir
        Since I like making temp files in /tmp so as not to clutter up working dir, this doesn't work well
        Only way to get stable operation is to make all file paths canonical
        '''
        file_names_canonical = list()
        for file_name in image_file_names:
            new_fn = os.path.realpath(file_name)
            engine.canon2orig[new_fn] = file_name
            file_names_canonical.append(new_fn)
        
        engine.coordinate_map = ImageCoordinateMap.from_file_names(file_names_canonical,
                flip_col, flip_row, flip_pre_transpose, flip_post_transpose, depth,
                alt_rows, alt_cols, rows, cols)
        return engine
    
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
        self.failures = FailedImages(open_list)
        
        
    def generate_control_points(self):
        '''
        Generate control points
        Generate to all neighbors to start with
        '''
        #temp_projects = list()

        msg()
        n_pairs = len(list(self.coordinate_map.gen_pairs(1, 1)))
        msg('***Pairs: %d***' % n_pairs)
        msg()
        pair_submit = 0
        pair_complete = 0
        
            
        msg('Initializing %d workers' % self.threads)
        for ti in xrange(self.threads):
            w = Worker(ti)
            w.generate_control_points_by_pair = self.generate_control_points_by_pair
            self.workers.append(w)
            w.start()

        coord_pairs = self.coordinate_map.gen_pairs(1, 1)
        
        all_allocated = False

        # Seed project with all images in order
        # note we used the filename that will get used below
        # not the final output file name
        for can_fn in sorted(self.canon2orig.keys()):
            self.project.add_image(can_fn)
        self.project.save()

        while not (all_allocated and pair_complete == pair_submit):
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
                
                if what == 'done':
                    (_task, final_pair_project) = out[1]
                    msg('W%d: done' % wi)
                    # May have failed
                    if final_pair_project:
                        final_pair_projects.append(final_pair_project)
                        if pair_complete % 10 == 0:
                            print 'Saving intermediate result to %s' % self.project.file_name
                            self.project.save()
                            print 'Saved'

                elif what == 'exception':
                    #(_task, e) = out[1]
                    msg('ERROR: W%d failed w/ exception' % wi)
                    raise Exception('Shutdown on worker failure')
                else:
                    msg('%s' % (out,))
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
                            msg('All tasks allocated')
                            all_allocated = True
                            break
        
                        pair_submit += 1
            
                        msg('*' * 80)
                        msg('W%d: submit %s (%d / %d)' % (wi, repr(pair), pair_submit, n_pairs))
            
                        # Image file names as list
                        pair_images = self.coordinate_map.get_images_from_pair(pair)
                        msg('pair images: ' + repr(pair_images))
                        if pair_images[0] is None or pair_images[1] is None:
                            if not self.skip_missing:
                                raise Exception('Missing images.  Use --skip-missing to continue')
                            msg('WARNING: skipping missing image')
                            continue
                            
                        worker.qi.put((pair, pair_images))
                        break
                    
            time.sleep(0.1)
            
        msg('pairs done')
        
        for worker in self.workers:
            worker.running.clear()
        
        msg('Reverting canonical file names to original input...')
        # Fixup the canonical hack
        for can_fn in self.canon2orig:
            # FIXME: if we have issues with images missing from the project due to bad stitch
            # we should add them (here?) instead of throwing an error
            orig = self.canon2orig[can_fn]
            il = self.project.get_image_by_fn(can_fn)
            if il:
                il.set_name(orig)
            else:
                msg('WARNING: adding image without feature match %s' % orig)
                self.project.add_image(orig)

        self.project.save()
        
        '''
        if 0:
            msg('Sub projects (full image):')
            for project in temp_projects:
                # prefix so I can grep it for debugging
                msg('\tSUB: ' + project.file_name)
        '''
        '''
        if 0:
            msg()
            msg()
            msg('Master project file: %s' % self.project.file_name)
            msg()
            msg()
            msg(self.project.text)
            msg()
            msg()
        '''
            
    def do_generate_control_points_by_pair(self, pair, image_fn_pair):
        ret = CommonStitch.do_generate_control_points_by_pair(self, pair, image_fn_pair)
        if ret is None and pair.adjacent():
            msg('WARNING: last ditch effort, increasing field of view')
            
        return ret

