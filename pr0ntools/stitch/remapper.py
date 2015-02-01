'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
Each picture may have lens artifacts that make them not perfectly linear
This distorts the images to match the final plane
And command line usage is apparantly inaccurate.  
It doesn't document the .pto input option...weird

nona: stitch a panorama image

nona version 2010.0.0.5045

 It uses the transform function from PanoTools, the stitching itself
 is quite simple, no seam feathering is done.execute
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

#from pr0ntools.execute import Execute, CommandFailed
from pr0ntools import execute
import datetime
import os
import sys

class RemapperFailed(execute.CommandFailed):
    pass

def get_nona_files(output_prefix, max_images):
    ret = set()
    '''Get all the files that nona could have generated based on what exists'''
    # The images shouldn't change, use the old loaded project
    for i in xrange(max_images):
        fn = '%s%04d.tif' % (output_prefix, i)
        if os.path.exists(fn):    
            ret.add(fn)
    return ret

class Nona:
    TIFF_SINGLE = "TIFF_m"
    TIFF_MULTILAYER = "TIFF_multilayer"
    
    def __init__(self, pto_project, output_prefix="nonaout"):
        if output_prefix is None or len(output_prefix) == 0 or output_prefix == '.' or output_prefix == '..':
            raise RemapperFailed('Bad output file base "%s"' % str(output_prefix))
        
        self.pto_project = pto_project
        # if true assume pto project is already setup up correctly
        # just use it
        self.pto_fn = None
        
        # this is taken from the pto
        #self.output_file_base = output_file_base
        #self.output_managed_temp_dir = ManagedTempDir(self.pto_project.get_a_file_name() + "__")
        #self.image_type = Remapper.TIFF_MULTILAYER
        self.image_type = Nona.TIFF_SINGLE
        self.output_files = None
        # panotools wiki says enblend 2.4+ supports this
        self.output_cropped = True
        self.compression_opt = "c:LZW"
        self.output_prefix = output_prefix
        self.args = None

        def p(s=''):
            print '%s: %s' % (datetime.datetime.utcnow().isoformat(), s)
        self.p = p
        self.pprefix = lambda: datetime.datetime.utcnow().isoformat() + ': '
        self.stdout = sys.stdout
        self.stderr = sys.stderr
    
    '''
    def run(self):
        project_name = self.pto_project.get_a_file_name()
        #print
        #print 'Remapping project %s' %  project_name
        project_name = os.path.basename(project_name)
        project_name = project_name.split('.')[0]
        if len(project_name) == 0:
            project_name = 'out'
            raise RemapperFailed('Require project name')
        print 'Chose output prefix "%s"' % project_name
        self.remap(project_name)
    '''
        
    def remap(self):
        old_files = get_nona_files(self.output_prefix, len(self.pto_project.get_image_lines()))
        # For my purposes right now I think this will always be 0
        if len(old_files) != 0:
            print old_files
            raise RemapperFailed('Found some old files')

        if self.pto_fn:
            project = self.pto_project
            project_fn = self.pto_fn
        else:
            project = self.pto_project.copy()
            pl = project.get_panorama_line()
            crop_opt = ""
            if self.image_type == Nona.TIFF_SINGLE:
                if self.output_cropped:
                    #  p f0 w1000 h500 v120 n"TIFF_m c:LZW r:CROP"
                    crop_opt = "r:CROP"
            pl.set_variable("n", "%s %s %s" % (self.image_type, crop_opt, self.compression_opt))
            project_fn = project.get_a_file_name()
        
        args = ["nona",
                "-m", self.image_type,
                "-verbose",
                "-z",
                "LZW",
                #"-g",
                "-o", self.output_prefix,
                ]
        for arg in self.args:
            args.append(arg)
        
        args.append(project_fn)
        # example:
        # cmd in: nona "-m" "TIFF_m" "-verbose" "-z" "LZW" "-o" "/tmp/pr0ntools_7E296EA2D31827B4/0DF5034FE1CEE831/" "out.pto"
        # p w2673 h2056 f0 v76 n"TIFF_m r:CROP c:LZW" E0.0 R0 S"276,2673,312,2056"
        # m line unchanged
        rc = execute.prefix(args, stdout=self.stdout, stderr=self.stderr, prefix=self.pprefix)
        if not rc == 0:
            self.p()
            self.p()
            self.p()
            self.p('Failed to remap')
            self.p('If you see "Write error at scanline..." you are out of scratch space')
            self.p('Clear up temp storage (ie in /tmp) or move it using .pr0nrc')
            #print output
            raise RemapperFailed('failed to remap')
        #project.reopen()
        if self.image_type == Nona.TIFF_MULTILAYER:
            self.output_files = [self.output_prefix + '.tif']
        elif self.image_type == Nona.TIFF_SINGLE:
            self.output_files = list()
            # This algorithm breaks down once you start doing cropping
            # it may be a set but lists have advantages trying to trace whats happening
            self.output_files = sorted(list(get_nona_files(self.output_prefix, len(self.pto_project.get_image_lines()))))
            self.p('Think nona just generated %d files' % (len(self.output_files),))
        else:
            raise RemapperFailed('bad image type')
    def get_output_files(self):
        return self.output_files
        

