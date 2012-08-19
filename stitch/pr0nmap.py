#!/usr/bin/python
'''
Generate a complete Google Map from pre-stitched input image(s)
pre-stitched means non-overlapping
They can be either a single large input image or the bottom level tiles
'''

import os
import argparse		
from pr0ntools.tile.map import Map, ImageMapSource, TileMapSource
		
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Generate Google Maps code from image file(s)')
	parser.add_argument('images_in', metavar='N', type=str, nargs='+', help='images in')
	parser.add_argument('--level-min', action="store", dest="level_min", type=int, default=0, help='Minimum zoom level')
	parser.add_argument('--level-max', action="store", dest="level_max", type=int, default=None, help='Maximum zoom level')
	parser.add_argument('--out', action="store", dest="out_dir", type=str, default="map", help='Output directory')
	parser.add_argument('--js-only', action="store_true", dest="js_only", default=False, help='No tiles, only JavaScript')
	#parser.add_argument('--merge', action="store_true", dest="merge", default=False, help='Merge into existing data')
	#parser.add_argument('--force', action="store_true", dest="force", default=False, help="Delete existing data if present")
	parser.add_argument('--skip-missing', action="store_true", dest="skip_missing", default=False, help='Skip missing tiles')
	parser.add_argument('--out-extension', action="store", dest="out_extension", type=str, default='.jpg', help='Select output image extension (and type), .jpg, .png, .tif, etc')
	parser.add_argument('--name', action="store", dest="title_name", type=str, default=None, help='SiMap: <name> title')
	parser.add_argument('--title', action="store", dest="title", type=str, default=None, help='Set title.  Default: SiMap: <project name>')
	args = parser.parse_args()
	
	if len(args.images_in) == 0:
		print 'Require at least one image in'
		sys.exit(1)
	elif len(args.images_in) == 1:
		image_in = args.images_in[0]
		if os.path.isdir(image_in):
			print 'Working on directory of max zoomed tiles'
			source = TileMapSource(image_in)
		else:
			if image_in.find('.pto') >= 0:
				raise ValueError('Cannot stitch .pto directly at this time, use pr0ntile first')
			print 'Working on singe input image %s' % image_in
			source = ImageMapSource(image_in)
	else:
		#images_in = args.images_in
		raise Exception('NO! no biscuit!')

	m = Map(source)
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

