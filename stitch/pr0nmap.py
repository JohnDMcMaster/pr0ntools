#!/usr/bin/python
'''
Generate a complete Google Map from input image(s)
'''

import argparse		
from pr0ntools.tile.map import Map
		
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Generate Google Maps code from image file(s)')
	parser.add_argument('images_in', metavar='N', type=str, nargs='+', help='images in')
	parser.add_argument('--level-min', action="store", dest="level_min", type=int, default=0, help='Minimum zoom level')
	parser.add_argument('--level-max', action="store", dest="level_max", type=int, default=None, help='Maximum zoom level')
	parser.add_argument('--out', action="store", dest="out_dir", type=str, default="map", help='Output directory')
	args = parser.parse_args()
	
	if len(args.images_in) == 1:
		image_in = args.images_in[0]
		print 'Working on singe input image %s' % image_in
		m = Map(image_in)
		m.min_level = args.level_min
		m.max_level = args.level_max
		m.out_dir = args.out_dir
		m.generate()
	else:
		print 'bad number of images in %s' % len(args.images_in)
		sys.exit(1)

