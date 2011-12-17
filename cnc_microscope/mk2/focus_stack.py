import usbio
from usbio.mc import MC
from usbio.controller import DummyController
from imager import DummyImager, PILImager
import os
import os.path
import time

class Stacker:
	def __init__(self, out_dir, n, spacing_steps = 1, dry = False):
		#dry = True
		
		self.dry = dry
		self.out_dir = out_dir
		if n % 2 != 0:
			raise Exception('Center stacking requires even n')
		self.n = n
		self.n2 = n / 2
		# Specify in steps to be very exact instead of units
		self.spacing_steps = spacing_steps
		
		if self.dry:
			self.mc = DummyController()
			self.imager = DummyImager()
		else:
			self.mc = MC()
			self.mc.on()
			self.imager = PILImager()

	def run(self):
		if os.path.exists(self.out_dir):
			raise Exception("dir %s already exists" % self.out_dir)
		os.mkdir(self.out_dir)
	
		self.mc.z.step(-self.n2 * self.spacing_steps)
		'''
		n = 0: 1 picture
		n = 2: 3 pictures
		'''
		for i in range(self.n + 1):
			self.imager.take_picture('%s/%03d__z%04fum.tif' % (self.out_dir, i, self.mc.z.get_um()))
			# Avoid moving at end
			if i != self.n:
				self.mc.z.step(self.spacing_steps)
				time.sleep(3)
		print 'Homing...'
		self.mc.z.home()
			
s = Stacker("stack100_10", 100, 10)
s.run()

