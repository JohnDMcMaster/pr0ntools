import Queue
import threading
from PyQt4.QtCore import *
import time
from controller import Controller
from planner import Planner
from pr0ntools.benchmark import Benchmark
import os

def dbg(*args):
    if len(args) == 0:
        print
    elif len(args) == 1:
        print 'threading: %s' % (args[0], )
    else:
        print 'threading: ' + (args[0] % args[1:])

'''
Try to seperate imaging and movement
For now keep unified in planner thread
'''
class ImagingThread(QThread):
    def __init__(self):
        self.queue = Queue.Queue()
        self.running = threading.Event()
    
    def run(self):
        self.running.set()
        while self.running.is_set():
            time.sleep(1)
    
    def stop(self):
        self.running.clear()

'''
Offloads controller processing to another thread (or potentially even process)
Makes it easier to keep RT deadlines and such
However, it doesn't provide feedback completion so use with care
(other blocks until done)
TODO: should block?
'''
'''
There must be a way to automate this more
Don't extend axis or the getattr won't work correctly
maybe not the most elegant but works for current needs
'''
class ControllerThreadAxis(object):
    def __init__(self, controller, axis):
        # IPC controller, not core
        self.controller = controller
        # Core axis
        self.axis = axis
        self.name = axis.name
    
    def __str__(self):
        return '%s-%s (IPC)' % (self.controller, self.axis)
    
    def get_um(self):
        return self.axis.get_um()
        
    def estop(self):
        '''Stop immediately.  Thread safe'''
        self.axis.estop()

    # how 'bout this
    def __getattr__(self, name):
        # Assumption is that non-system attributes are offloaded functions
        if name.find("__") == 0:
            # __len__, __nonzero__
            return eval('self.axis.%s' % name)
        def offload(*args):
            self.controller.offload(self.axis, name, args)
            # Always return None
            # no fetch methods currently supported
        return offload

class ControllerThread(QThread, Controller):
    def __init__(self, controller):
        QThread.__init__(self)
        Controller.__init__(self)
        self.queue = Queue.Queue()
        self.controller = controller
        self.running = threading.Event()
        self._idle = threading.Event()
        self._idle.set()
        self.normal_running = threading.Event()
        self.normal_running.set()
        
        #for axis in self.controller.axes:
        
        if self.controller.x:
            self.x = ControllerThreadAxis(self, self.controller.x)
        else:
            self.x = None

        if self.controller.y:
            self.y = ControllerThreadAxis(self, self.controller.y)
        else:
            self.y = None

        if self.controller.z:
            self.z = ControllerThreadAxis(self, self.controller.z)
        else:
            self.z = None
            
        self.build_axes()
        
    def setRunning(self, running):
        if running:
            self.normal_running.set()
        else:
            self.normal_running.clear()
        
    def idle(self):
        '''return true if the thread is idle'''
        return self._idle.is_set()
        
    def wait_idle(self):
        while True:
            time.sleep(0.15)
            if self.idle():
                break
        
    def offload(self, axis, name, args):
        self.queue.put((axis, name, args))

    def run(self):
        self.running.set()
        self._idle.clear()
        while self.running.is_set():
            if not self.normal_running.isSet():
                self.normal_running.wait(0.1)
                continue
            try:
                (axis, name, args) = self.queue.get(True, 0.1)
                self._idle.clear()
            except Queue.Empty:
                self._idle.set()
                continue
            #print 'Queue has something, ~size: %d' % (self.queue.qsize(),)
            #print type(axis)
            #print dir(axis)
            #print axis.__dict__
            #weird...only has variables and not functions...I thought there was no distinction in python?
            #axis.__dict__[name](*args)
            if name == 'jog':
                (units, cb_inc) = args
                axis.jog(units)
                cb_inc()
            elif name == 'set_pos':
                (units, cb_inc) = args
                axis.set_pos(units)
                cb_inc()
            elif name == 'set_home':
                (cb_inc,) = args
                axis.set_home()
                cb_inc()
            elif name == 'home':
                (cb_inc,) = args
                axis.home()
                cb_inc()
            else:
                try:
                    getattr(axis, name)(*args)
                except TypeError:
                    print type(axis)
                    print axis.__class__
                    raise
    
    def stop(self):
        self.running.clear()        

# Sends events to the imaging and movement threads
class PlannerThread(QThread):
    plannerDone = pyqtSignal()

    def __init__(self,parent, rconfig, start_hook):
        QThread.__init__(self, parent)
        self.rconfig = rconfig
        self.planner = None
        #self.log_buff = bytearray()
        self.start_hook = start_hook
        
    def log(self, msg):
        #print 'emitting log %s' % msg
        #self.log_buff += str(msg) + '\n'
        self.emit(SIGNAL('log'), msg)
    
    def setRunning(self, running):
        planner = self.planner
        if planner:
            planner.setRunning(running)
        
    def run(self):
        try:
            self.log('Initializing planner!')
    
            self.planner = Planner.get(self.rconfig, self.log)
            self.log('Running planner')
            b = Benchmark()
            self.planner.run(start_hook=self.start_hook)
            b.stop()
            self.log('Planner done!  Took : %s' % str(b))
            
            '''
            log_fn = os.path.join(self.planner.out_dir(), 'log.txt')
            if self.rconfig.dry:
                self.log('DRY: write %d byte log to %s' % (len(self.log_buff), log_fn))
            else:
                open(log_fn, 'w').write(self.log_buff)
            '''
            self.plannerDone.emit()
        except Exception as e:
            self.log('WARNING: planner thread crashed: %s' % str(e))
            raise

