#!/usr/bin/python
'''
pr0nstitch: IC die image feature generation for stitching
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details

Command refernece:
http://wiki.panotools.org/Panorama_scripting_in_a_nutshell
Some parts of this code inspired by Christian Sattler's tool
(https://github.com/JohnDMcMaster/csstitch)
pr0nstitch is described in detail at
http://uvicrec.blogspot.com/2011/02/scaling-up-image-stitching.html
'''

import argparse
import os.path
import signal
import sys
import traceback
from pr0ntools.stitch.wander_stitch import WanderStitch
from pr0ntools.stitch.all_stitch import AllStitch
from pr0ntools.stitch.grid_stitch import GridStitch
from pr0ntools.stitch.fortify_stitch import FortifyStitch
from pr0ntools.util import IOTimestamp, IOLog

project_file = 'panorama0.pto'
temp_project_file = '/tmp/pr0nstitch.pto'
allow_overwrite = True

AUTOPANO_SIFT_C = 1
autopano_sift_c = "autopano-sift-c"
AUTOPANO_AJ = 2
# I use this under WINE, the Linux version doesn't work as well
autopano_aj = "autopanoaj"
grid_only = False

CONTROL_POINT_ENGINE = AUTOPANO_AJ

def help():
    print '\timage file: added to input images'
    print '\tdirectory: added to input image directories'
    print '\t.pto file: assumed to be project file'
    print '--result=<file_name> or --out=<file_name>'
    print '\t--result-image=<image file name>'
    print '\t--result-project=<project file name>'
    print '--input-project=<project file name>'
    print '--cp-engine=<engine>'
    print '\tautopano-sift-c: autopano-SIFT-c'
    print '\t\t--autopano-sift-c=<path>, default = autopano-sift-c'
    print '\tautopano-aj: Alexandre Jenny\'s autopano'
    print '\t\t--autopano-aj=<path>, default = autopanoaj'
    print '--pto-merger=<engine>'
    print '\tdefault: use pto_merge if availible'
    print '\tpto_merge: Hugin supported merge (Hugin 2010.2.0+)'
    print '\t\t--pto_merge=<path>, default = pto_merge'
    print '\tinternal: quick and dirty internal version'
    print '--algorithm=<algorithm>'
    print '\tgrid: assume input is a regular grid tagged with row/col (default)'
    print '\twander: assume input is contiguous. Use for back and forth pattern'
    # Did hacks, not supported externally
    #print '\tfortify: use input-project and try to fill in additional control points'
    # Consider supporting
    #print '\tauto: poke around at images and then do stitch after figuring out layout (computationally expensive!)'
    print 'Grid formation options (col 0, row 0 should be upper left):'
    print '--grid-only[=<bool>]: only construct/print the grid map and exit'
    print '--flip-col[=<bool>]: flip columns'
    print '--flip-row[=<bool>]: flip rows'
    print '--flip-pre-transpose[=<bool>]: switch col/row before all other flips'
    print '--flip-post-transpose[=<bool>]: switch col/row after all other flips'
    print '--no-overwrite[=<bool>]: do not allow overwrite of existing files'
    print '--regular[=<bool>]: images are separated by regular intervals like CNC would produce, default true'
    print '--skip-missing: allow holes'

def arg_fatal(s):
    print s
    help()
    sys.exit(1)

def t_or_f(arg):
    arg_value = str(arg).lower()
    return not (arg_value == "false" or arg_value == "0" or arg_value == "no")

def excepthook(excType, excValue, tracebackobj):
    print '%s: %s' % (excType, excValue)
    traceback.print_tb(tracebackobj)
    os._exit(1)

def parser_add_bool_arg(yes_arg, default=False, **kwargs):
    dashed = yes_arg.replace('--', '')
    dest = dashed.replace('-', '_')
    parser.add_argument(yes_arg, dest=dest, action='store_true', default=default, **kwargs)
    parser.add_argument('--no-' + dashed, dest=dest, action='store_false', **kwargs)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Stitch images quickly into .pto through hints')
    parser.add_argument('--out', default='out.pto', help='Output file name')
    parser_add_bool_arg('--grid-only', default=False, help='')
    parser.add_argument('--algorithm', default='grid', help='')
    parser.add_argument('--threads', default='1')
    parser.add_argument('--n-rows', help='')
    parser.add_argument('--n-cols', help='')
    parser_add_bool_arg('--alt-rows', default=False, help='')
    parser_add_bool_arg('--alt-cols', default=False, help='')
    parser_add_bool_arg('--flip-row', default=False, help='')
    parser_add_bool_arg('--flip-col', default=False, help='')
    parser_add_bool_arg('--flip-pre-transpose', default=False, help='')
    parser_add_bool_arg('--flip-post-transpose', default=False, help='')
    parser_add_bool_arg('--overwrite', default=False, help='')
    parser_add_bool_arg('--regular', default=True, help='')
    parser.add_argument('--x-overlap', help='')
    parser.add_argument('--y-overlap', help='')
    parser_add_bool_arg('--dry', default=False, help='')
    parser_add_bool_arg('--skip-missing', default=False, help='')
    parser.add_argument('fns', nargs='+', help='File names')
    parser_add_bool_arg('--stampout', default=True, help='timestamp output')
    args = parser.parse_args()
    
    if args.stampout:
        _outdate = IOTimestamp(sys, 'stdout')
        _errdate = IOTimestamp(sys, 'stderr')
    _outlog = IOLog(obj=sys, name='stdout', out_fn='pr0nstitch.log')
    _errlog = IOLog(obj=sys, name='stderr', out_fd=_outlog.out_fd)

    depth = 1
    # CNC like precision?
    # Default to true for me
    regular = True
                
    input_image_file_names = list()
    input_project_file_name = None
    output_project_file_name = None
    output_image_file_name = None
    for arg in args.fns:
        if arg.find('.pto') > 0:
            output_project_file_name = arg
        elif os.path.isfile(arg) or os.path.isdir(arg):
            input_image_file_names.append(arg)
        else:
            arg_fatal('unrecognized arg: %s' % arg)
    if len(input_image_file_names) == 0:
        raise Exception('Requires image file names')

    print 'post arg'
    print 'output image: %s' % output_image_file_name
    print 'output project: %s' % output_project_file_name
    
    args.threads = int(args.threads)
    if args.threads < 1:
        raise Exception('Bad threads')
    
    if args.algorithm == "grid":
        '''
        Probably most intuitive is to have (0, 0) at lower left 
        like its presented in many linear algebra works and XY graph
        ...but image stuff tends to to upper left, so thats what things use
        '''
        if args.n_rows or args.n_cols:
            engine = GridStitch.from_file_names(input_image_file_names, args.flip_col, args.flip_row, args.flip_pre_transpose, args.flip_post_transpose, depth,
                    args.alt_rows, args.alt_cols, args.n_rows, args.n_cols)
            engine.threads = args.threads
        else:
            engine = GridStitch.from_tagged_file_names(input_image_file_names)
        engine.skip_missing = args.skip_missing
        if grid_only:
            print 'Grid only, exiting'
            sys.exit(0)
    elif args.algorithm == "wander":
        engine = WanderStitch.from_file_names(input_image_file_names)
    elif args.algorithm == "all":
        engine = AllStitch.from_file_names(input_image_file_names)
    elif args.algorithm == "fortify":
        if len(input_image_file_names) > 0:
            raise Exception('Cannot use old project and image files')
        if input_project_file_name is None:
            raise Exception('Requires input project')
        engine = FortifyStitch.from_existing_project_file_name(input_project_file_name)
    else:
        raise Exception('need an algorithm / engine')

    engine.set_output_project_file_name(output_project_file_name)
    engine.set_output_image_file_name(output_image_file_name)
    engine.set_regular(regular)
    engine.set_dry(args.dry)
    
    if args.x_overlap:
        engine.x_overlap = args.x_overlap
    if args.y_overlap:
        engine.y_overlap = args.y_overlap
    
    if not allow_overwrite:
        if output_project_file_name and os.path.exists(output_project_file_name):
            print 'ERROR: cannot overwrite existing project file: %s' % output_project_file_name
            sys.exit(1)
        if output_image_file_name and os.path.exists(output_image_file_name):
            print 'ERROR: cannot overwrite existing image file: %s' % output_image_file_name
            sys.exit(1)    

    sys.excepthook = excepthook
    # Exit on ^C instead of ignoring
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    engine.run()
    print 'Done!'

