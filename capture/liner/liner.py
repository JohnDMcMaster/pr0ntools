#!/usr/bin/env python

from pr0ntools.image.liner import *

set_dbg(True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="More ice I tell you.  More ice")
    #parser.add_argument('files', metavar='files', type=str, nargs='+',
    #               help='Input training folders and files to classify')
    parser.add_argument('--debug', action="store_true", dest="debug", default=False, help='Debug')
    parser.add_argument('--show', action="store_true", dest="show", default=False, help='Show contours')
    parser.add_argument('--filter', action="store_true", dest="filter", default=False, help='Show only contours we like')
    args = parser.parse_args()
    show = args.show
    filt = args.filter

    if show:
        cv.NamedWindow( "Contours", 1 );
    args.files = ['img_bw.jpg']
    args.files = ['img.jpg']
    for fn in args.files:
        # Roughly on the center of the left side
        #line = [(63, 115), (65, 319)]
        # Now try finding a circle
        line = [(103, 304), (130, 308)]
        liner(fn, line)

