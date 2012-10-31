#from VideoCapture import Device

try:
	import VideoCapture as VC  
except:
	VC = None
from PIL import Image  
from PIL import ImageOps  
import time  
import psutil

'''
R:127
G:103
B:129
'''

# driver does not play well with other and effectively results in a system restart
# provide some basic protection
def camera_in_use():
	'''
	C:\Program Files\AmScope\AmScope\x86\scope.exe
	'''
	for p in psutil.get_process_list():
		try:
			if p.exe.find('scope.exe') >= 0:
				print 'Found process %s' % p.exe
				return True
		except:
			pass
	return False

class Imager:
	def __init__(self):
		pass

	def take_picture(self, file_name_out = None):
		pass

class MockImager(Imager):
	def __init__(self):
		pass
		
	def take_picture(self, file_name_out = None):
		print 'Mock imager: image to %s' % file_name_out

class VCImager:
	def __init__(self):
		if camera_in_use():
			print 'WARNING: camera in use, not loading imager'
			raise Exception('Camera in use')				
		if not VC:
			raise Exception('Failed to import VC')
	
		self.cam = VC.Device() # initialize the webcam  
		img = self.cam.getImage() # in my testing the first getImage stays black.  
		time.sleep(1) # give sometime for the device to come up  

	def take_picture(self, file_name_out = None):  
		img = self.cam.getImage() # capture the current image  
		# on windows this causes the app to block on a MS Paint window..not desirable
		#img.show()
		img.save(file_name_out)

	def __del__(self):
		# Why did example have this?  Shouldn't this happen automatically?
		del self.cam # no longer need the cam. uninitialize  

