'''
This file is part of uvscada
Licensed under 2 clause BSD license, see COPYING for details
'''

# no real interfaces really defined yet...
class Controller:
    def __init__(self, debug=False):
        self.debug = debug
        self.x = None
        self.y = None
        self.z = None
        self.axes = []
        self.axesd = {}

    def build_axes(self):
        self.axes = []
        if self.x:
            self.axes.append(self.x)
            self.axesd[self.x.name] = self.x
        if self.y:
            self.axes.append(self.y)
            self.axesd[self.y.name] = self.y
        if self.z:
            self.axes.append(self.z)
            self.axesd[self.z.name] = self.z

    def inches(self):
        for axis in self.axes:
            axis.inches()
        
    def mm(self):
        for axis in self.axes:
            axis.mm()

    def um(self):
        for axis in self.axes:
            axis.um()
        
    def home(self):
        for axis in self.axes:
            axis.home()
        
    def off(self):
        pass
    
    def on(self):
        pass

    def stop(self):
        '''Gracefully stop the system at next interrupt point'''
        for axis in self.axes:
            axis.stop()

    def estop(self):
        '''Halt the system ASAP, possibly losing precision/position'''
        for axis in self.axes:
            axis.estop()
