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
'''
The final program
Takes a collection of images and produces final output image

Usage: enblend [options] [--output=IMAGE] INPUT...
Blend INPUT images into a single IMAGE.

INPUT... are image filenames or response filenames.  Response
filenames start with an "@" character.

Common options:
  -V, --version          output version information and exit
  -a                     pre-assemble non-overlapping images
  -h, --help             print this help message and exit
  -l, --levels=LEVELS    number of blending LEVELS to use (1 to 29);
                         negative number of LEVELS decreases maximum
  -o, --output=FILE      write output to FILE; default: "a.tif"
  -v, --verbose[=LEVEL]  verbosely report progress; repeat to
                         increase verbosity or directly set to LEVEL
  -w, --wrap[=MODE]      wrap around image boundary, where MODE is
                         NONE, HORIZONTAL, VERTICAL, or BOTH; default: none;
                         without argument the option selects horizontal wrapping
  -x                     checkpoint partial results
  --compression=COMPRESSION
                         set compression of output image to COMPRESSION,
                         where COMPRESSION is:
                         NONE, PACKBITS, LZW, DEFLATE for TIFF files and
                         0 to 100 for JPEG files

Extended options:
  -b BLOCKSIZE           image cache BLOCKSIZE in kilobytes; default: 2048KB
  -c                     use CIECAM02 to blend colors
  -d, --depth=DEPTH      set the number of bits per channel of the output
                         image, where DEPTH is 8, 16, 32, r32, or r64
  -g                     associated-alpha hack for Gimp (before version 2)
                         and Cinepaint
  --gpu                  use graphics card to accelerate seam-line optimization
  -f WIDTHxHEIGHT[+xXOFFSET+yYOFFSET]
                         manually set the size and position of the output
                         image; useful for cropped and shifted input
                         TIFF images, such as those produced by Nona
  -m CACHESIZE           set image CACHESIZE in megabytes; default: 1024MB


Mask generation options:
  --coarse-mask[=FACTOR] shrink overlap regions by FACTOR to speedup mask
                         generation; this is the default; if omitted FACTOR
                         defaults to 8
  --fine-mask            generate mask at full image resolution; use e.g.
                         if overlap regions are very narrow
  --smooth-difference=RADIUS
                         smooth the difference image prior to seam-line
                         optimization with a Gaussian blur of RADIUS;
                         default: 0 pixels
  --optimize             turn on mask optimization; this is the default
  --no-optimize          turn off mask optimization
  --optimizer-weights=DISTANCEWEIGHT[:MISMATCHWEIGHT]
                         set the optimizer's weigths for distance and mismatch;
                         default: 8:1
  --mask-vectorize=LENGTH
                         set LENGTH of single seam segment; append "%" for
                         relative value; defaults: 4 for coarse masks and
                         20 for fine masks
  --anneal=TAU[:DELTAEMAX[:DELTAEMIN[:KMAX]]]
                         set annealing parameters of optimizer strategy 1;
                         defaults: 0.75:7000:5:32
  --dijkstra=RADIUS      set search RADIUS of optimizer strategy 2; default:
                         25 pixels
  --save-masks[=TEMPLATE]
                         save generated masks in TEMPLATE; default: "mask-%n.tif";
                         conversion chars: %i: mask index, %n: mask number,
                         %p: full path, %d: dirname, %b: basename,
                         %f: filename, %e: extension; lowercase characters
                         refer to input images uppercase to the output image
  --load-masks[=TEMPLATE]
                         use existing masks in TEMPLATE instead of generating
                         them; same template characters as "--save-masks";
                         default: "mask-%n.tif"
  --visualize[=TEMPLATE] save results of optimizer in TEMPLATE; same template
                         characters as "--save-masks"; default: "vis-%n.tif"
'''
class Remapper:
	pto_project = None
	output_file_name = None
	managed_temp_dir = None
	
	def __init__(self, pto_project, output_file_name):
		self.pto_project = pto_project
		self.output_file_name = output_file_name
		#self.output_managed_temp_dir = ManagedTempDir(self.pto_project.get_a_file_name() + "__")
		self.managed_temp_dir = ManagedTempDir.get()
		
	def run(self):
		self.remap()
		# We now have my_prefix_0000.tif, my_prefix_0001.tif, etc
		self.merge()
		
	def remap(self):
		args = list()
		args.append("-m")
		args.append("TIFF")
		args.append("-z")
		args.append("LZW")
		#args.append("-g")
		args.append("-o")
		args.append(output_prefix)
		args.append(pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("nona", args)
		if not rc == 0:
			raise Exception('failed to remap')
		self.project.reopen()


	def merge(self):
		'''
		[mcmaster@gespenst 2X2-ordered]$ enblend -o my_prefix.tif my_prefix_000*
		enblend: info: loading next image: my_prefix_0000.tif 1/1
		enblend: info: loading next image: my_prefix_0001.tif 1/1

		enblend: excessive overlap detected; remove one of the images
		enblend: info: remove invalid output image "my_prefix.tif"
		'''
		args = list()
		args.append("-m")
		args.append("TIFF_m")
		args.append("-z")
		args.append("LZW")
		#args.append("-g")
		args.append("-o")
		args.append(pto_project.get_a_file_name())
		args.append(pto_project.get_a_file_name())
		(rc, output) = Execute.with_output("enblend", args)
		if not rc == 0:
			raise Exception('failed to blend')
		self.project.reopen()

