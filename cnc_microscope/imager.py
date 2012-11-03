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

	# Note: g-code imager ignores file name since it saved to auto-named SD card
	def take_picture(self, file_name_out = None):
		'''Take a picture, preferably saving to given file name'''
		raise Exception('Required')

class MockImager(Imager):
	def __init__(self):
		Imager.__init__(self)
		
	def take_picture(self, file_name_out = None):
		print 'Mock imager: image to %s' % file_name_out
