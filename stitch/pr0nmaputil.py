#!/usr/bin/env python

from pr0ntools.tile.map_util import *
import argparse

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Generate Google Maps code from image file(s)')
	parser.add_argument('files_in', metavar='N', type=str, nargs='+', help='files in')
	parser.add_argument('--rotate', action="store", dest="rotate_degrees", type=int, default=None, help='Degrees to rotate CW')
	parser.add_argument('--force', action="store_true", dest="force", default=False, help='Force conversion')
	parser.add_argument('--rc', action="store_true", dest="rc", default=False, help='Row/col form like cnc_microscope gives')
	args = parser.parse_args()

	for f in args.files_in:
		if not args.rotate_degrees is None:
			rotate_tiles(f, None, args.rotate_degrees, args.force, args.rc)

