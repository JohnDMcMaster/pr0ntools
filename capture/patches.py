#!/usr/bin/python
'''
Test program to classify patches
Each patch type must be a folder
Single input images are classified

Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import sys 
import os.path
import argparse		

import pr0ntools.layer.parser

import Image
from opencv.cv import *
import Image

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Nuke 'em")
	parser.add_argument('files', metavar='files', type=str, nargs='+',
                   help='Input training folders and files to classify')
	args = parser.parse_args()
	dirs = list()
	files = list()
	
	for f in args.files:
		if not os.path.exists(f):
			raise ValueError('No file %s' % f)
		if os.path.isdir(f):
			dirs.append(f)
		else:
			files.append(f)

	print '%d training dirs' % len(dirs)
	print '%d things to classify' % len(files)
	

	for d in dirs:
		if d[-1] == '/':
			d = d[0:-1]
		name = os.path.basename(d)
		print
		print 'Working on %s in %s' % (name, d)
		for f in os.listdir(d):
			fcan = os.path.join(d, f)
			print fcan
			
			'''
			IplImage* hsv = cvCreateImage( cvGetSize(src), 8, 3 );
			cvCvtColor( src, hsv, CV_BGR2HSV );
			IplImage* h_plane = cvCreateImage( cvGetSize(src), 8, 1 );
			IplImage* s_plane = cvCreateImage( cvGetSize(src), 8, 1 );
			IplImage* v_plane = cvCreateImage( cvGetSize(src), 8, 1 );
			IplImage* planes[] = { h_plane, s_plane };
			cvCvtPixToPlane( hsv, h_plane, s_plane, v_plane, 0 );
			
			
			C
				CvHistogram* cvCreateHist(
					int     dims,
					int*    sizes,
					int     type,
					float** ranges = NULL,
					int     uniform = 1
				);
				 void cvCalcHist(
					IplImage**       image,
					CvHistogram* hist,
					int          accumulate = 0,
					const CvArr* mask       = NULL
					);
			Python
				some sort of alias
				
				cvCalcArrHist(*args)
					cvCalcArrHist(CvArr arr, CvHistogram hist, int accumulate = 0, CvArr mask = None)
			
			
				cvCreateHist(*args)
					cvCreateHist(int dims, int type, float ranges = None, int uniform = 1) -> CvHistogram
			'''
			im = Image.open(fcan)
			gray = cvCreateImage (cvSize (im.size[0], im.size[1]), 8, 1)
			bins = [32]
			hist = cvCreateHist(len(bins), bins, CV_HIST_ARRAY)
			#cvCalcHist(image, hist)
			cvCalcHist(gray, hist)
			
			sys.exit(1)




