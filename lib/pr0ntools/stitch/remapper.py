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
                   DEFLATE   deflate compression
'''

from pr0ntools.temp_file import ManagedTempDir
from pr0ntools.execute import Execute

class Remapper:
	TIFF_SINGLE = "TIFF"
	TIFF_MULTILAYER = "TIFF_m"
	
	def __init__(self, pto_project):
		self.pto_project = pto_project
		# this is taken from the pto
		#self.output_file_base = output_file_base
		#self.output_managed_temp_dir = ManagedTempDir(self.pto_project.get_a_file_name() + "__")
		self.managed_temp_dir = ManagedTempDir.get()
		self.image_type = Remapper.TIFF_SINGLE
		self.output_files = None
		
	def run(self):
		raise Exception('FIXME')
		
	def remap(self, output_file_base):
		args = list()
		args.append("-m")
		args.append(self.image_type)
		args.append("-z")
		args.append("LZW")
		#args.append("-g")
		args.append("-o")
		args.append(output_file_base)
		args.append(self.pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("nona", args)
		if not rc == 0:
			print
			print
			print
			print 'Failed to remap'
			print output
			raise Exception('failed to remap')
		self.pto_project.reopen()
		if self.image_type == TIFF_MULTILAYER:
			self.output_files = [self.output_file_base + '.tif']
		elif self.image_type == TIFF_SINGLE:
			self.output_files = list()
			for i in range(len(self.get_image_lines())):
				self.output_files += '%s%04d.tif' % (self.output_file_base, i)
		else:
			raise Exception('bad image type')
	def get_output_files(self):
		return self.output_files
		
	
