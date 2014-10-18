from controller import Controller
from axis import Axis

class MockController(Controller):
    def __init__(self, debug=False):
        Controller.__init__(self, debug=debug)
        self.x = DummyAxis('X')
        self.y = DummyAxis('Y')
        self.axes = [self.x, self.y]

class DummyAxis(Axis):
    def __init__(self, name = 'dummy'):
        Axis.__init__(self, name)
        self.steps_per_unit = 1
        self.net = 0
    
    def jog(self, units):
        print 'Dummy axis %s: jogging %s' % (self.name, units)
        
    def step(self, steps):
        print 'Dummy axis %s: stepping %s' % (self.name, steps)

    def set_pos(self, units):
        print 'Dummy axis %s: set_pos %s' % (self.name, units)
    
    def stop(self):
        print 'Dummy axis %s: stop' % (self.name,)

    def estop(self):
        print 'Dummy axis %s: emergency stop' % (self.name,)
    
    def unestop(self):
        print 'Dummy axis %s: clearing emergency stop' % (self.name,)
    
    def set_home(self):
        print 'Dummy axis %s: set home' % (self.name,)

    def home(self):
        print 'Dummy axis %s: home' % (self.name,)

    def forever_neg(self):
        print 'Dummy axis %s: forever_neg' % (self.name,)
          
    def forever_pos(self):
        print 'Dummy axis %s: forever_pos' % (self.name,)
        

