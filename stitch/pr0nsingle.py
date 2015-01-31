#!/usr/bin/env python
import argparse
from pr0ntools.stitch.single import singlify

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate Google Maps code from image file(s)')
    parser.add_argument('fn_out', help='')
    parser.add_argument('fns_in', nargs='+', help='')
    args = parser.parse_args()

    # Warning: will throw HugeJPEG if too big
    singlify(args.fns_in, args.fn_out)
