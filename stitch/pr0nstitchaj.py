#!/usr/bin/python
'''
pr0nstitchaj: AJ's autopano WINE wrapper for Hugin
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools.stitch.pto.project import PTOProject
import sys 
import os.path
import argparse
from pr0ntools.stitch.all_stitch import AllStitch

def arg_fatal(s):
    print s
    help()
    sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="create Hugin .pto using Andrew Jenny's autopano")
    #parser.add_argument('pto', metavar='pto project', type=str, nargs=1, help='pto project')
    parser.add_argument('--verbose', '-v', action="store_true", default=False, help='spew lots of info')
    parser.add_argument('--overwrite', action="store_true", default=False, help='overwrite existing output file')
    parser.add_argument('--dry', action="store_true", default=False, help='dont actually stitch')
    parser.add_argument('files', nargs='+', help='a .pto and some image files')
    args = parser.parse_args()

    pto_fn = "out.pto"
    image_fns = []
    for fn in args.files:
        print fn
        if fn.find(".pto") >= 0:
            pto_fn = fn
        else:
            image_fns.append(fn)
    
    if len(image_fns) < 2:
        raise Exception('Need at least two images to stitch')
    
    engine = AllStitch.from_file_names(image_fns)
    engine.set_output_project_file_name(pto_fn)
    engine.set_dry(args.dry)
    
    if not args.overwrite:
        if pto_fn and os.path.exists(pto_fn):
            print 'ERROR: cannot overwrite existing project file: %s' % pto_fn
            sys.exit(1)
    
    engine.run()
    print 'Done!'

