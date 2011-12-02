import usbio
from usbio.axis import DummyAxis


# no real interfaces really defined yet...
class Controller:
	def __init__(self):
		self.x = None
		self.y = None
		self.z = None

class DummyController(Controller):
	def __init__(self):
		Controller.__init__(self)
		self.x = DummyAxis()
		self.y = DummyAxis()
		self.axes = [self.x, self.y]

