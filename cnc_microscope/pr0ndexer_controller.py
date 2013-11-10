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
        if self.indexer.serial is None:
            raise Exception("USBIO missing serial")
        
        self.x = PDCAxis('X', self.indexer)
        self.y = PDCAxis('Y', self.indexer)
        self.z = PDCAxis('Z', self.indexer)
        
        self.axes = [self.x, self.y, self.z]
        # enforce some initial state?
        
        self.um()
    
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
        
    def forever_pos(self, done, progress_notify=None):
        '''Go forever in the positive direction until stopped'''
        # Because we are free-wheeling we need to know how many were completed to maintain position
        steps_orig = self.indexer.net_tostep(self.name)
        
        while not done.is_set():
            if self._estop.is_set():
                self.indexer.step(self.name, 0)
                return
            # Step for half second at a time
            # last value overwrites though
            self.indexer.step(self.name, 1*self.indexer.steps_a_second(), wait=False)
            time.sleep(0.05)
        self._stop.clear()
        # make a clean stop
        self.indexer.step(self.name, 30, wait=False)
        # Fib a little by reporting where we will end up, should be good enough
        # as we will end there shortly
        # if we change plan before then its in charge of updating position
        # XXX: wraparound issue?  should not be issue in practice since stage would crash first
        self.net += self.indexer.net_tostep(self.name) - steps_orig
        if progress_notify:
            progress_notify()
        
    def forever_neg(self, done, progress_notify):
        '''Go forever in the negative direction until stopped'''
        # Because we are free-wheeling we need to know how many were completed to maintain position
        steps_orig = self.indexer.net_tostep(self.name)
        
        while not done.is_set():
            if self._estop.is_set():
                self.indexer.step(self.name, 0)
                return
            # Step for half second at a time
            # last value overwrites though
            self.indexer.step(self.name, -1*self.indexer.steps_a_second(), wait=False)
            time.sleep(0.05)
        self._stop.clear()
        # make a clean stop
        self.indexer.step(self.name, -30, wait=False)
        # Fib a little by reporting where we will end up, should be good enough
        # as we will end there shortly
        # if we change plan before then its in charge of updating position
        # XXX: wraparound issue?  should not be issue in practice since stage would crash first
        self.net += self.indexer.net_tostep(self.name) - steps_orig
        if progress_notify:
            progress_notify()
    
    def stop(self):
        self.indexer.step(self.name, 0)

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
