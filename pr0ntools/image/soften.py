'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.execute import Execute
from pr0ntools import execute
import os
import time
import sys

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
    
        sys.stdout.flush()
        if not os.path.exists(source_file_name):
            raise Exception('Soften input file name missing')
            
        strong_blur_mtemp_file = ManagedTempFile.from_same_extension(source_file_name)

        args = ["convert"]
        args.append(source_file_name)
        args.append("-morphology")
        args.append("Convolve")
        args.append("Gaussian:0x3")
        args.append(strong_blur_mtemp_file.file_name)
        rc = execute.without_output(args)
        if not rc == 0:
            raise Exception('failed to form strong blur')

        for i in xrange(30):
            if os.path.exists(strong_blur_mtemp_file.file_name):
                break
            if i == 0:
                print 'WARNING: soften missing strong blur dest file name %s, waiting a bit...' % (strong_blur_mtemp_file.file_name,)
            time.sleep(0.1)
        else:
            raise Exception('Missing soften strong blur output file name %s' % strong_blur_mtemp_file.file_name)
        
        args = ["convert"]
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
        rc = execute.without_output(args)
        if not rc == 0:
            raise Exception('failed to form strong blur')

        # We're done! (nothing to return)
        
        # XXX: expierment to see if wait helps...probalby just need check
        for i in xrange(30):
            if os.path.exists(dest_file_name):
                break
            if i == 0:
                print 'WARNING: soften missing dest file name %s, waiting a bit...' % (dest_file_name,)
            time.sleep(0.1)
        else:
            raise Exception('Missing output file name %s' % dest_file_name)

