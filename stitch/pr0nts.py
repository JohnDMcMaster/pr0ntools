#!/usr/bin/python
'''
pr0ntile: IC die image stitching and tile generation
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
pr0nts: pr0ntools tile stitcher
This takes in a .pto project and outputs 
'''

import sys 
import os.path
from pr0ntools.tile.tile import SingleTiler, TileTiler
from pr0ntools.stitch.tiler import Tiler
from pr0ntools.stitch.wander_stitch import WanderStitch
from pr0ntools.stitch.grid_stitch import GridStitch
from pr0ntools.stitch.fortify_stitch import FortifyStitch
from pr0ntools.execute import Execute
from pr0ntools.stitch.pto.project import PTOProject
import argparse

VERSION = '0.1'


def usage():
	print 'pr0nts: create tiles from unstitched images'
	print 'Usage:'
	print 'pr0nts <image file names>'
	print 'single file name will expect to be a .pto already optimized and cropped'
	print 'FIXME broken: multiple file names (TODO: or directory) will be stitched together and must overlap'


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='create tiles from unstitched images')
	parser.add_argument('pto', metavar='pto project', type=str, nargs=1, help='pto project')
	parser.add_argument('--super-tw', action="store", dest="super_tw", type=int, default=None, help='Supertile width')
	parser.add_argument('--super-th', action="store", dest="super_th", type=int, default=None, help='Supertile height')
	parser.add_argument('--force', action="store_true", dest="force", default=False, help='Force by replacing old files')
	parser.add_argument('--out-extension', action="store", dest="out_extension", type=str, default='.jpg', help='Select output image extension (and type), .jpg, .png, .tif, etc')

	args = parser.parse_args()
	fn = args.pto[0]
	
	print 'Assuming input %s is pto project to be stitched' % fn
	project = PTOProject.parse_from_file_name(fn)
	print 'Creating tiler'
	t = Tiler(project, 'out', super_tw=args.super_tw, super_th=args.super_th)
	t.force = args.force
	t.out_extension = args.out_extension
	print 'Running tiler'
	t.run()
	print 'Tiler done!'

