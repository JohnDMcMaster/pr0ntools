'''
pr0ntools
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
[mcmaster@gespenst tile]$ enblend --help
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

Report bugs at <http://sourceforge.net/projects/enblend/>.
'''

from pr0ntools import execute
from pr0ntools.execute import Execute, CommandFailed
from pr0ntools.config import config
import fcntl
import time
import sys
import datetime

class BlenderFailed(CommandFailed):
    pass

class Blender:
    def __init__(self, input_files, output_file, lock=False):
        self.input_files = input_files
        self.output_file = output_file
        self.compression = None
        self.gpu = False
        self.additional_args = []
        self._lock = lock
        self._lock_fp = None
        self.out_prefix = lambda: datetime.datetime.utcnow().isoformat() + ': '
        def p(s=''):
            print '%s%s' % (self.out_prefix(), s)
        self.p = p
        
    def lock(self):
        if not self._lock:
            self.p('note: Skipping enblend lock')
            return
        pid_file = '/tmp/pr0ntools-enblend.pid'
        self._lock_fp = open(pid_file, 'w')
        i = 0
        self.p('note: Acquiring enblend lock')
        while True:
            try:
                fcntl.lockf(self._lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except IOError:
                # Can take a while, print every 10 min or so and once at failure
                if i % (10 * 60 * 10) == 0:
                    self.p('Failed to acquire enblend lock, retrying (print every 10 min)')
                time.sleep(0.1)
            i += 1
        self.p('Acquired enblend lock')
        
    def unlock(self):
        if self._lock_fp is None:
            self.p('Skipping enblend unlock')
            return
        self.p('Releasing enblend lock')
        self._lock_fp.close()
        self._lock_fp = None
        
    def old_merge(self):
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
        args.append(self.pto_project.get_a_file_name())
        args.append(self.pto_project.get_a_file_name())
        self.lock()
        try:
            (rc, _output) = Execute.with_output("enblend", args)
            if not rc == 0:
                raise BlenderFailed('failed to blend')
            self.project.reopen()
            self.p('enblend finished OK')
        finally:
            self.unlock()
        self.p('Blender complete')

        
    def run(self):
        args = ["enblend", "-o", self.output_file]
        if self.compression:
            args.append('--compression=%s' % str(self.compression))
        if self.gpu:
            args.append('--gpu')
        for arg in self.additional_args:
            args.append(arg)
        for f in self.input_files:
            args.append(f)
        
        for opt in config.enblend_opts().split():
            args.append(opt)
        
        self.lock()
                
        rc = execute.prefix(args, stdout=sys.stdout, stderr=sys.stderr, prefix=self.out_prefix)
        if not rc == 0:
            self.p('')
            self.p('')
            self.p('')
            self.p('Failed to blend')
            self.p('rc: %d' % rc)
            self.p(args)
            raise BlenderFailed('failed to remap')
