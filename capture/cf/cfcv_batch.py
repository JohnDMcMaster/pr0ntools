#!/usr/bin/python
import argparse
from multiprocessing import Process, Queue
from Queue import Empty
import time
import os
import shutil
import glob
import traceback
import multiprocessing

from pr0ntools.util import add_bool_arg
from cfcv import GridCap, GridCapFailed
import cfcv

class Worker(Process):
    def __init__(self):
        Process.__init__(self)
        self.qi = Queue()
        self.qo = Queue()
        self.running = True
    
    def send_qo(self, e, *args):
        self.qo.put((e, args))
        
    def send_qi(self, e, *args):
        self.qi.put((e, args))
    
    def process(self, fn, outdir):
        if os.path.exists(outdir):
            print 'WARNING: removing stable outdir %s' % outdir
            shutil.rmtree(outdir)
        gc = GridCap(fn, outdir)
        # FIXME: test
        '''
        "m": 28.798439172285491,
        "m": 28.858570666253318,
        "m": 28.863853412915169,
        "m": 28.870065695379324,
        "m": 28.897894257052542,
        "m": 28.898561602670757,
        "m": 28.902170052993778,
        "m": 28.904432700498411,
        "m": 28.912128923940617,
        "m": 28.921572162297931,
        "m": 28.92840006812828,
        "m": 28.938493227866346,
        "m": 28.95081479394069,
        "m": 28.974397399436118,
        '''
        gc.m_est = 28.9
        '''
        Mean angle: 0.015334 rad (0.878571 deg)
        Mean angle: 0.014321 rad (0.820513 deg)
        Mean angle: 0.015828 rad (0.906849 deg)
        Mean angle: 0.015526 rad (0.889583 deg)
        avg: 0.873879ll
        '''
        gc.straighten_angle = 0.87387911
        print 'Running GridCap'
        try:
            gc.run()
            print 'GridCap done ok'
            self.send_qo('process', fn, outdir, True)
        except GridCapFailed as e:
            print e
            print 'GridCap failed'
            traceback.print_exc()
            self.send_qo('process', fn, outdir, False)

    def run(self):
        print 'Working running'
        try:
            while self.running:
                try:
                    (e, args) = self.qi.get(timeout=0.1)
                except Empty:
                    time.sleep(0.1)
                    continue
                print 'Worker got %s' % (e,)
                
                def stop():
                    print 'Shutting down'
                    self.running = False
                
                def default(*args):
                    msg = 'Unknown message %s(%s)' % (e, args)
                    print msg
                    self.send_qo('exception', msg)
                
                {
                    'process': self.process,
                    'stop': stop,
                }.get(e, default)(*args)
        except Exception as e:
            msg = 'Got exception %s' % (e,)
            print msg
            self.send_qo('exception', msg)
            self.running = False
            raise

class Server(object):
    def __init__(self):
        self.running = True
        self.workers = []
        self.w_busy = set()
        self.w_free = set()
        for i in xrange(args.workers):
            print 'Creating worker %d' % i
            w = Worker()
            self.workers.append(w)
            self.w_free.add(w)
        print self.w_free
    
    def process_rx(self, worker, fn, outdir, ok):
        print '%s: done' % fn
        
        '''
        if ok:
            dst = os.path.join(args.dir_out, os.path.basename(fn))
        else:
            dst = os.path.join(args.dir_fail, os.path.basename(fn))
        print '%s => %s' % (fn, dst)
        shutil.move(fn, dst)
        '''
        self.w_free.add(worker)
    
    def to_process(self):
        for f in glob.glob(args.dir_in + '/*.jpg'):
            yield f
    
    def service_worker(self, worker):
        try:
            (e, args) = worker.qo.get(timeout=0.1)
        except Empty:
            return False
            print 'Server got %s' % (e,)
        
        def exception(_worker, msg):
            print 'Shutting down on worker exception: %s' % msg
            self.running = False
        
        def default(*args):
            msg = 'Unknown message %s(%s)' % (e, args)
            print msg
            self.send_qo('exception', msg)
        
        {
            'process': self.process_rx,
            'exception': exception,
        }.get(e, default)(*([worker] + list(args)))
        return True
    
    def run(self):
        print 'Starting workers'
        for worker in self.workers:
            worker.start()
        
        print 'Creating out dir'
        os.mkdir(args.dir_out)
        #os.mkdir(args.dir_fail)
        try:
            to_process = self.to_process()
            worked = True
            while self.running:
                if not worked:
                    time.sleep(0.1)
                worked = False
                
                # Process completed jobs
                for worker in self.workers:
                    worked |= self.service_worker(worker)
            
                # Hand out jobs to free workers
                while len(self.w_free) and to_process:
                    try:
                        fn = to_process.next()
                    except StopIteration:
                        print 'Allocated all files'
                        to_process = None
                        break
                    print
                    print
                    print
                    print '*' * 80
                    worked = True
                    worker = self.w_free.pop()
                    dst_dir = os.path.join(args.dir_out, os.path.basename(fn).replace('.jpg', ''))
                    print 'Process %s => %s' % (fn, dst_dir)
                    worker.send_qi('process', fn, dst_dir)
    
                # All work completed?
                if to_process is None and len(self.w_free) == len(self.workers):
                    print 'All jobs complete'
                    self.running = False
        finally:
            print
            print 'Shutting down workers on exit'
            for worker in self.workers:
                print 'Stopping %s' % worker
                worker.send_qi('stop')
            print

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grid auto-bitmap test')
    # ord('pr') = 28786
    parser.add_argument('--port', type=int, default=28786, help='TCP port number')
    parser.add_argument('--workers', type=int, default= multiprocessing.cpu_count(), help='Number worker processes')
    add_bool_arg(parser, '--debug', default=False)
    parser.add_argument('dir_in', help='Directory to grab jobs from')
    parser.add_argument('dir_out', help='Directory to put completed jobs')
    args = parser.parse_args()

    cfcv.debug = args.debug
    
    s = Server()
    s.run()
