'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under the terms of the LGPL V3 or later, see COPYING for details
'''

from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.execute import Execute

class Softener:
	original_weight = None
	blurred_weight = None
	gaussian_size = None

	def __init__(self, original_weight = 0.6, blurred_weight = 0.4, gaussian_size = 3):
		self.original_weight = original_weight
		self.blurred_weight = blurred_weight
		self.gaussian_size = gaussian_size
		
	def run(self, source_file_name, dest_file_name = None):
		'''
		http://www.imagemagick.org/Usage/convolve/#soft_blur
		
		convert face.png -morphology Convolve Gaussian:0x3  face_strong_blur.png
		convert face.png face_strong_blur.png \
		  -compose Blend -define compose:args=60,40% -composite \
		  face_soft_blur.png
		 
		If dest_file_name is not given, done in place
		'''
	
		strong_blur_mtemp_file = ManagedTempFile.from_same_extension(source_file_name)

		args = list()
		args.append(source_file_name)
		args.append("-morphology")
		args.append("Convolve")
		args.append("Gaussian:0x3")
		args.append(strong_blur_mtemp_file.file_name)
		(rc, output) = Execute.with_output("convert", args)
		if not rc == 0:
			raise Exception('failed to form strong blur')

		args = list()
		args.append(source_file_name)
		args.append(strong_blur_mtemp_file.file_name)
		args.append("-compose")
		args.append("Blend")
		args.append("-define")
		args.append("compose:args=60,40%")
		args.append("-composite")
		# If we got a dest file, use it
		if dest_file_name:
			args.append(dest_file_name)
		# Otherwise, overwrite
		else:
			args.append(source_file_name)		
		(rc, output) = Execute.with_output("convert", args)
		if not rc == 0:
			raise Exception('failed to form strong blur')

		# We're done! (nothing to return)

