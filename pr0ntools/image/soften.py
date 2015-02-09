'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools.temp_file import ManagedTempFile
import os
import time
import subprocess
import sys

def soften_gauss(src_fn, dst_fn=None):
    '''
    http://www.imagemagick.org/Usage/convolve/#soft_blur
    
    convert face.png -morphology Convolve Gaussian:0x3  face_strong_blur.png
    convert face.png face_strong_blur.png \
      -compose Blend -define compose:args=60,40% -composite \
      face_soft_blur.png
     
    If dest_file_name is not given, done in place
    '''

    sys.stdout.flush()
    if not os.path.exists(src_fn):
        raise Exception('Soften input file name missing')
        
    if dst_fn is None:
        dst_fn = src_fn

    args = ["convert"]
    args.append(src_fn)
    args.append("-morphology")
    args.append("Convolve")
    args.append("Gaussian:0x3")
    args.append(dst_fn)

    print 'going to execute: %s' % (args,)
    # Specifying nothing completely throws away the output
    subp = subprocess.Popen(args, stdout=None, stderr=None, shell=False)
    subp.communicate()
    print 'Execute done, rc: %s' % (subp.returncode,)
    if not subp.returncode == 0:
        raise Exception('soften failed')

    # having some problems that looks like file isn't getting written to disk
    # monitoring for such errors
    # remove if I can root cause the source of these glitches
    for i in xrange(30):
        if os.path.exists(dst_fn):
            break
        if i == 0:
            print 'WARNING: soften missing strong blur dest file name %s, waiting a bit...' % (dst_fn,)
        time.sleep(0.1)
    else:
        raise Exception('Missing soften strong blur output file name %s' % dst_fn)
    
def soften_composite(src_fn, dst_fn=None):
    tmp_file = ManagedTempFile.from_same_extension(src_fn)
    soften_gauss(src_fn, tmp_file.file_name)

    if dst_fn is None:
        dst_fn = src_fn

    args = ["convert"]
    args.append(src_fn)
    args.append(tmp_file.file_name)
    args.append("-compose")
    args.append("Blend")
    args.append("-define")
    args.append("compose:args=60,40%")
    args.append("-composite")
    # If we got a dest file, use it
    args.append(dst_fn)
    print 'going to execute: %s' % (args,)
    subp = subprocess.Popen(args, stdout=None, stderr=None, shell=False)
    subp.communicate()
    print 'Execute done, rc: %s' % (subp.returncode,)
    if not subp.returncode == 0:
        raise Exception('failed to form strong blur')

    # having some problems that looks like file isn't getting written to disk
    # monitoring for such errors
    # remove if I can root cause the source of these glitches
    for i in xrange(30):
        if os.path.exists(dst_fn):
            break
        if i == 0:
            print 'WARNING: soften missing strong blur dest file name %s, waiting a bit...' % (dst_fn,)
        time.sleep(0.1)
    else:
        raise Exception('Missing soften strong blur output file name %s' % dst_fn)
