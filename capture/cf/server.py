#!/usr/bin/python
'''
For now this has very narrow focus of taking in a directory, serving it, and then terminating
Eventually this should become a service that can register projects in different directories

Do not assume that the two computers have any connection between them other than the socket
-Do not share file paths
-Do not open additional sockets

Initially client is expected to be a PyQt GUI
Eventually the client should be a web application (maybe Django)
'''
import argparse
from multiprocessing import Process, Queue
from Queue import Empty
import time
import os
import shutil
import glob
import traceback
import multiprocessing
import json

from pr0ntools.util import add_bool_arg

from SimpleXMLRPCServer import SimpleXMLRPCServer
from xmlrpclib import Binary
import datetime

class Server(object):
    def __init__(self, indir, verbose=False):
        self.running = True
        self.server = None
        self.indir = indir
        self.verbose = verbose

        # Unallocated
        self.todo = set()
        # Client has requested but not completed
        self.outstanding = {}
        self.completed = set()
    
    def add_dir(self, indir):
        # out.png means it should have completed successfully
        # alternatively open every json file and see if it looks okay
        print 'Scanning for new jobs: %s' % indir
        for fn in glob.glob(indir + '/*/out.png'):
            base = os.path.dirname(fn)
            print '  Adding: %s' % base
            self.todo.add(base)
        print 'Scan complete'
        
    def run(self):
        print 'Building job list'
        self.add_dir(self.indir)
        
        print 'Starting server'
        server = SimpleXMLRPCServer(('localhost', 9000), logRequests=self.verbose, allow_none=True)
        server.register_introspection_functions()
        server.register_multicall_functions()
        #server.register_instance(self.rpc)
        server.register_function(self.job_req,      "job_req")
        server.register_function(self.job_done,     "job_done")
        server.serve_forever()
    
    '''
    RPC
    '''
    def job_req(self):
        try:
            '''
            In order to process the client needs:
            -Output image (out.png)
            -Image for grid (cropped or original if not rotating)
            -Offsets into the original image (out.json)
            '''
            try:
                base = self.todo.pop()
            except KeyError:
                # No jobs to hand out
                print 'WARNING: client requested job but no jobs'
                return None
            print 'Allocating %s' % base
            
            j = json.load(open(os.path.join(base, 'out.json')))
            
            if j['pass'] != True:
                raise Exception("Bad job %s" % base)
            
            ret = {
                    'name': base,
                    'png': Binary(open(os.path.join(base, j['png'])).read()),
                    'img': Binary(open(os.path.join(base, j['img'])).read()),
                    'json': j,
                    }
            self.outstanding[base] = {
                    'ret': ret,
                    # so can timeout clients that don't complete jobs
                    'tstart': time.time(),
                    }
            return ret
        except:
            traceback.print_exc()
            raise
    
    '''
    new_png may be None indicating the job was rejected
    In this case msg must be set
    Otherwise msg is optional
    '''
    def job_done(self, base, new_png, msg):
        try:
            print 'Completed: %s: %s' % (base, new_png is not None)
            submit = self.outstanding[base]
            print 'Time: %0.1f' % (time.time() - submit['tstart'],)
            if new_png is not None:
                open(os.path.join(base, 'sweep.png'), 'w').write(new_png.data)
            open(os.path.join(base, 'sweep.txt'), 'w').write(msg)
            self.completed.add(base)
            del self.outstanding[base]
            
            if args.reserve and len(self.todo) == 0:
                print 'reserve: reloading'
                self.outstanding = {}
                self.completed = set()
                self.add_dir(self.indir)
        except:
            traceback.print_exc()
            raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grid auto-bitmap test')
    # ord('pr') = 28786
    parser.add_argument('--port', type=int, default=28786, help='TCP port number')
    add_bool_arg(parser, '--debug', default=False)
    add_bool_arg(parser, '--reserve', default=False)
    parser.add_argument('dir', help='Directory to nom')
    args = parser.parse_args()

    s = Server(args.dir, args.debug)
    s.run()
