#!/usr/bin/python
'''
Generate a complete Google Map from pre-stitched input image(s)
pre-stitched means non-overlapping
They can be either a single large input image or the bottom level tiles
'''

from pr0ntools.tile.map import Map, ImageMapSource, TileMapSource

import argparse        
import datetime
import multiprocessing
import os
import re

std_c_mc = '&copy;%d John McMaster, CC BY' % datetime.datetime.now().year
std_c_dig = '&copy;%d Digshadow, CC BY' % datetime.datetime.now().year

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate Google Maps code from image file(s)')
    parser.add_argument('images_in', help='image file or dir in')
    parser.add_argument('--level-min', type=int, default=0, help='Minimum zoom level')
    parser.add_argument('--level-max', type=int, default=None, help='Maximum zoom level')
    parser.add_argument('--out', '-o', default=None, help='Output directory')
    parser.add_argument('--js-only', action="store_true", dest="js_only", default=False, help='No tiles, only JavaScript')
    parser.add_argument('--skip-missing', action="store_true", dest="skip_missing", default=False, help='Skip missing tiles')
    parser.add_argument('--out-extension', default=None, help='Select output image extension (and type), .jpg, .png, .tif, etc')
    parser.add_argument('--name', dest="title_name", help='SiMap: <name> title')
    parser.add_argument('--title', dest="title", help='Set title.  Default: SiMap: <project name>')
    parser.add_argument('--copyright', '-c', help='Set copyright message (default: none)')
    parser.add_argument('--c-mc', '-M', action='store_true', help='Set copyright "%s"' % std_c_mc)
    parser.add_argument('--c-dig', '-D', action='store_true', help='Set copyright "%s"' % std_c_dig)
    parser.add_argument('--threads', type=int, default= multiprocessing.cpu_count())
    args = parser.parse_args()
    
    if args.c_mc:
        args.copyright = std_c_mc
    
    if args.c_dig:
        args.copyright = std_c_dig

    im_ext = args.out_extension
    out_dir = args.out

    if os.path.isdir(args.images_in):
        print 'Working on directory of max zoomed tiles'
        source = TileMapSource(args.images_in, threads=args.threads)
    else:
        print 'Working on singe input image %s' % args.images_in
        source = ImageMapSource(args.images_in, threads=args.threads)
        if not im_ext:
            im_ext = '.' + args.images_in.split('.')[-1]
        # Do auto-magic renaming for standr named die on sipr0n
        '''
        Always in form:
        <vendor>_<chip>_<dataset>.<ext>
        
        Typically something like
        <vendor>_<chip>_<layer>_<mag>.jpg
        ex: mos_6581r2_mz_mit20x.jpg
        
        But also variations
        ex: mos_6581r2_vec-a.png
        '''
        if not out_dir:
            m = re.match(r'single/([A-Za-z0-9]*)_([A-Za-z0-9\-]*)_(.*)\.(.*)', args.images_in)
            if m:
                out_dir = m.group(3)
                print 'Auto-naming output file for sipr0n: %s' % out_dir

    m = Map(source, args.copyright)
    if args.title_name:
        m.page_title = "SiMap: %s" % args.title_name
    if args.title:
        m.page_title = args.title
    m.min_level = args.level_min
    m.max_level = args.level_max
    m.js_only = args.js_only
    m.skip_missing = args.skip_missing
    
    if not out_dir:
        out_dir = "map"
    m.out_dir = out_dir
    
    if not im_ext:
        im_ext = '.jpg'
    m.set_im_ext(im_ext)
    m.generate()
