'''
pr0ntools
Benchmarking utility
Copyright 2010 John McMaster
'''

import time

class Benchmark:
    start_time = None
    end_time = None
    
    def __init__(self, max_items = None):
        # For the lazy
        self.start_time = time.time()
        self.end_time = None
        self.max_items = max_items
        self.cur_items = 0

    def start(self):
        self.start_time = time.time()
        self.end_time = None
        self.cur_items = 0

    def stop(self):
        self.end_time = time.time()
    
    def advance(self, n = 1):
        self.cur_items += n

    @staticmethod
    def time_str(delta):
        fraction = delta % 1
        delta -= fraction
        delta = int(delta)
        seconds = delta % 60
        delta /= 60
        minutes = delta % 60
        delta /= 60
        hours = delta
        return '%02d:%02d:%02d.%04d' % (hours, minutes, seconds, fraction * 10000)
    
    def __repr__(self):
        if self.end_time:
            return self.time_str(self.end_time - self.start_time)
        elif self.max_items:
            cur_time = time.time()
            delta_t = cur_time - self.start_time
            if True or delta_t < 0.000001:
                rate = self.cur_items / (delta_t)
                remaining = (self.max_items - self.cur_items) * rate
                eta_str = self.time_str(remaining)
            else:
                eta_str = "indeterminate"
            return '%d / %d, ETA: %s' % (self.cur_items, self.max_items, eta_str)
        else:
            return self.time_str(time.time() - self.start_time)

