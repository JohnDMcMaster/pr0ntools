'''
pr0ndexer controller
Higher level wrapper around the primitive indexer interface to adapt to pr0nscope
Introduces things like units and concurrency
'''

import serial
import sys
import time
import threading
from usbio.controller import Controller
from usbio.axis import Axis
from pr0ndexer import Indexer

class PDC(Controller):
    def __init__(self, debug=False):
        Controller.__init__(self, debug=False)
        
        self.indexer = Indexer(debug=debug)
        print 'opened some USBIO okay'
        if self.indexer.serial is None:
            raise Exception("USBIO missing serial")
        
        self.x = PDCAxis('X', self.indexer)
        self.y = PDCAxis('Y', self.indexer)
        self.z = PDCAxis('Z', self.indexer)
        
        self.axes = [self.x, self.y, self.z]
        # enforce some initial state?
        
        self.um()
        print 'Controller ready'
    
    def __del__(self):
        self.off()

class PDCAxis(Axis):
    def __init__(self, name, indexer):
        Axis.__init__(self, name)
        self.indexer = indexer
        if self.indexer.serial is None:
            raise Exception("Indexer missing serial")
        
        # Ensure stopped
        self.indexer.step(self.name, 0)
        
        self._stop = threading.Event()
        self._estop = threading.Event()
        
    def forever_pos(self):
        '''Go forever in the positive direction until stopped'''
        while not self._stop.is_set():
            if self._estop.is_set():
                return
            # Step for half second at a time
            # last value overwrites though
            self.indexer.step(self.name, 5*self.indexer.steps_a_second(), wait=False)
            print 'Sleeping'
            time.sleep(0.1)
            print 'Woke up'
        self._stop.clear()
        self.indexer.step(self.name, 0)
        
    def forever_neg(self):
        '''Go forever in the negative direction until stopped'''
        while not self._stop.is_set():
            if self._estop.is_set():
                return
            # Step for half second at a time
            # last value overwrites though
            self.indexer.step(self.name, -5*self.indexer.steps_a_second(), wait=False)
            print 'Sleeping'
            time.sleep(0.1)
            print 'Woke up'
        self._stop.clear()
        self.indexer.step(self.name, 0)
    
    def stop(self):
        self._stop.set()

    def estop(self):
        self._estop.set()
    
    def unestop(self):
        self._estop.clear()
        
    def unstop(self):
        self._stop.clear()
        
    def step(self, steps):
        self.indexer.step(self.name, steps)
        self.net += steps

    # pretend we are at 0
    def set_home(self):
        self.net = 0
    
    def set_pos(self, units):
        '''
        Ex:
        old position is 2 we want 10
        we need to move 10 - 2 = 8
        '''
        self.jog(units - self.get_um())
        
    def home(self):
        self.step(-self.net)
