#!/usr/bin/python
'''
Generate a complete Google Map from pre-stitched input image(s)
pre-stitched means non-overlapping
They can be either a single large input image or the bottom level tiles
'''

import os
import sys
import argparse		
from pr0ntools.tile.map import Map, ImageMapSource, TileMapSource

std_copyright = '&copy;2013 John McMaster blah blah blah, CC BY-NC-SA'

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Generate Google Maps code from image file(s)')
	parser.add_argument('images_in', help='image file or dir in')
	parser.add_argument('--level-min', type=int, default=0, help='Minimum zoom level')
	parser.add_argument('--level-max', type=int, default=None, help='Maximum zoom level')
	parser.add_argument('--out', '-o', dest="out_dir", default="map", help='Output directory')
	parser.add_argument('--js-only', action="store_true", dest="js_only", default=False, help='No tiles, only JavaScript')
	#parser.add_argument('--merge', action="store_true", dest="merge", default=False, help='Merge into existing data')
	#parser.add_argument('--force', action="store_true", dest="force", default=False, help="Delete existing data if present")
	parser.add_argument('--skip-missing', action="store_true", dest="skip_missing", default=False, help='Skip missing tiles')
	parser.add_argument('--out-extension', default='.jpg', help='Select output image extension (and type), .jpg, .png, .tif, etc')
	parser.add_argument('--name', dest="title_name", help='SiMap: <name> title')
	parser.add_argument('--title', dest="title", help='Set title.  Default: SiMap: <project name>')
	parser.add_argument('--copyright', '-c', help='Set copyright message (default: none)')
	parser.add_argument('--std-copyright', '-C', action='store_true', help='Set copyright to "%s"' % std_copyright)
	args = parser.parse_args()
	
	if args.std_copyright:
		args.copyright = std_copyright
	
	if os.path.isdir(args.images_in):
		print 'Working on directory of max zoomed tiles'
		source = TileMapSource(args.images_in)
	else:
		if args.images_in.find('.pto') >= 0:
			raise ValueError('Cannot stitch .pto directly at this time, use pr0ntile first')
		print 'Working on singe input image %s' % args.images_in
		source = ImageMapSource(args.images_in)

	m = Map(source, args.copyright)
	if args.title_name:
		m.page_title = "SiMap: %s" % args.title_name
	if args.title:
		m.page_title = args.title
	m.min_level = args.level_min
	m.max_level = args.level_max
	m.out_dir = args.out_dir
	m.js_only = args.js_only
	m.skip_missing = args.skip_missing
	m.set_out_extension(args.out_extension)
	m.generate()

