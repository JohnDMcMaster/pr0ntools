'''
Each picture may have lens artifacts that make them not perfectly linear
This distorts the images to match the final plane
And command line usage is apparantly inaccurate.  
It doesn't document the .pto input option...weird

nona: stitch a panorama image

nona version 2010.0.0.5045

 It uses the transform function from PanoTools, the stitching itself
 is quite simple, no seam feathering is done.
 only the non-antialiasing interpolators of panotools are supported

 The following output formats (n option of panotools p script line)
 are supported:

  JPG, TIFF, PNG  : Single image formats without feathered blending:
  TIFF_m          : multiple tiff files
  TIFF_multilayer : Multilayer tiff files, readable by The Gimp 2.0

Usage: nona [options] -o output project_file (image files)
  Options: 
      -c         create coordinate images (only TIFF_m output)
      -v         quiet, do not output progress indicators
      -t num     number of threads to be used (default: nr of available cores)
      -g         perform image remapping on the GPU

  The following options can be used to override settings in the project file:
      -i num     remap only image with number num
                   (can be specified multiple times)
      -m str     set output file format (TIFF, TIFF_m, TIFF_multilayer, EXR, EXR_m)
      -r ldr/hdr set output mode.
                   ldr  keep original bit depth and response
                   hdr  merge to hdr
      -e exposure set exposure for ldr mode
      -p TYPE    pixel type of the output. Can be one of:
                  UINT8   8 bit unsigned integer
                  UINT16  16 bit unsigned integer
                  INT16   16 bit signed integer
                  UINT32  32 bit unsigned integer
                  INT32   32 bit signed integer
                  FLOAT   32 bit floating point
      -z         set compression type.
                  Possible options for tiff output:
                   NONE      no compression
                   PACKBITS  packbits compression
                   LZW       lzw compression
                   DEFLATE   deflate
                    compression


panotools wiki says that hugin should be able to output cropped but I don't see it doing so
	Checking nona...[OK]
	Checking enblend...[OK]
	Checking enfuse...[OK]
	Checking hugin_hdrmerge...[OK]
	Checking exiftool...[OK]
	nona  -z LZW -r ldr -m TIFF_m -o test -i 1 /tmp/huginpto_H3PO0O
	nona  -z LZW -r ldr -m TIFF_m -o test -i 2 /tmp/huginpto_H3PO0O
	nona  -z LZW -r ldr -m TIFF_m -o test -i 4 /tmp/huginpto_H3PO0O
	nona  -z LZW -r ldr -m TIFF_m -o test -i 6 /tmp/huginpto_H3PO0O
	nona  -z LZW -r ldr -m TIFF_m -o test -i 7 /tmp/huginpto_H3PO0O
	nona  -z LZW -r ldr -m TIFF_m -o test -i 9 /tmp/huginpto_H3PO0O
'''

from pr0ntools.temp_file import ManagedTempDir
from pr0ntools.execute import Execute
import os

class Remapper:
	TIFF_SINGLE = "TIFF_m"
	TIFF_MULTILAYER = "TIFF_multilayer"
	
	def __init__(self, pto_project):
		self.pto_project = pto_project
		# this is taken from the pto
		#self.output_file_base = output_file_base
		#self.output_managed_temp_dir = ManagedTempDir(self.pto_project.get_a_file_name() + "__")
		self.managed_temp_dir = ManagedTempDir.get()
		#self.image_type = Remapper.TIFF_MULTILAYER
		self.image_type = Remapper.TIFF_SINGLE
		self.output_files = None
		# panotools wiki says enblend 2.4+ supports this
		self.output_cropped = True
		self.compression_opt = "c:LZW"
		
	def run(self):
		project_name = self.pto_project.get_a_file_name()
		project_name = os.path.basename(project_name)
		project_name = project_name.split('.')[0]
		if len(project_name) == 0:
			project_name = 'out'
			raise Exception('Require project name')
		print 'Chose output prefix "%s"' % project_name
		self.remap(project_name)
		
	def remap(self, output_file_base):
		project = self.pto_project.copy()
		args = list()
		args.append("-m")
		args.append(self.image_type)
		pl = project.get_panorama_line()
		crop_opt = ""
		if self.image_type == Remapper.TIFF_SINGLE:
			if self.output_cropped:
				# FIXME: this needs to go into the n argument in the file, not a CLI option
				#  p f0 w1000 h500 v120 n"TIFF_m c:LZW r:CROP"
				#args.append("r:CROP")
				pl.set_variable("n", "TIFF_m %s ", self.compression_opt)
				# will be saved when we get the file name
				#pl.save()
				crop_opt = "r:CROP"
		pl.set_variable("n", "%s %s c:LZW" % (self.image_type, self.compression_opt, crop_opt))
		args.append("-z")
		args.append("LZW")
		#args.append("-g")
		args.append("-o")
		args.append(output_file_base)
		args.append(project.get_a_file_name())
		(rc, output) = Execute.with_output("nona", args)
		if not rc == 0:
			print
			print
			print
			print 'Failed to remap'
			print output
			raise Exception('failed to remap')
		self.pto_project.reopen()
		if self.image_type == Remapper.TIFF_MULTILAYER:
			self.output_files = [output_file_base + '.tif']
		elif self.image_type == Remapper.TIFF_SINGLE:
			self.output_files = list()
			for i in range(len(self.pto_project.get_image_lines())):
				self.output_files += '%s%04d.tif' % (output_file_base, i)
		else:
			raise Exception('bad image type')
	def get_output_files(self):
		return self.output_files
		
	
