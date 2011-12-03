#from VideoCapture import Device

import VideoCapture as VC  
from PIL import Image  
from PIL import ImageOps  
import time  


class Imager:
	def __init__(self):
		pass

	def take_picture(self, file_name_out = None):
		pass

class DummyImager(Imager):
	def __init__(self):
		pass
		
	def take_picture(self, file_name_out = None):
		pass

class VideoCaptureImager:
	def __init__(self):
		self.cam = Device()
	
	def take_picture(self, file_name_out = None):
		print 'Taking picture to %s' % file_name_out
		self.cam.saveSnapshot(file_name_out)

class PILImager:
	def __init__(self):
		self.cam = VC.Device() # initialize the webcam  
		img = self.cam.getImage() # in my testing the first getImage stays black.  
		time.sleep(1) # give sometime for the device to come up  

	def take_picture(self, file_name_out = None):  
		img = self.cam.getImage() # capture the current image  
		img.save(file_name_out)

	def __del__(self):
		# Why did example have this?  Shouldn't this happen automatically?
		del self.cam # no longer need the cam. uninitialize  
