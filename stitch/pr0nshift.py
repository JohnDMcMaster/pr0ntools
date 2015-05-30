#!/usr/bin/python
import argparse
import glob
import sys
import os
import re
import shutil

from pr0ntools.stitch.image_coordinate_map import ImageCoordinateMap

'''
r29-
r30-
'''

def parser_add_bool_arg(yes_arg, default=False, **kwargs):
    dashed = yes_arg.replace('--', '')
    dest = dashed.replace('-', '_')
    parser.add_argument(yes_arg, dest=dest, action='store_true', default=default, **kwargs)
    parser.add_argument('--no-' + dashed, dest=dest, action='store_false', **kwargs)

def row_right(row, pos):
    '''Shift elements right starting at pos'''
    # need to grow map? (most of the time yes)
    if (icm.cols - 1, row) in icm.layout:
        icm.cols += 1
    for col in xrange(icm.cols, pos - 1, -1):
        try:
            del icm.layout[(col + 1, row)]
        except KeyError:
            pass
        try:
            icm.layout[(col + 1, row)] = icm.layout[(col, row)]
            # Delete the old key
            del icm.layout[(col, row)]
        # Nothing to shift in
        except KeyError:
            pass

def row_left(row, pos):
    '''Shift elements left starting at pos'''
    for col in xrange(0, icm.cols):
        try:
            del icm.layout[(col, row)]
        except KeyError:
            pass
        try:
            icm.layout[(col, row)] = icm.layout[(col + 1, row)]
            # Delete the old key
            del icm.layout[(col + 1, row)]
        # Nothing to shift in
        except KeyError:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Manipulate .pto files')
    parser.add_argument('--dry', action='store_true', help='Dont actually do anything')
    parser.add_argument('dir', help='Image directory to work on')
    parser.add_argument('actions', nargs='+', help='Actions to perform')
    args = parser.parse_args()

    print 'Constructing ICM'
    working_set = set(glob.glob(os.path.join(args.dir, '*.jpg')))
    icm = ImageCoordinateMap.from_tagged_file_names(working_set)
    print 'ICM ready'
    
    for action in args.actions:
        print 'Action: %s' % action
        
        m = re.match('r([0-9]+)-', action)
        if m:
            row = int(m.group(1))
            print 'Remove row %d' % row
            # if additional rows exist shift them
            for cur_row in xrange(row + 1, icm.rows):
                for cur_col in xrange(icm.cols):
                    fn = icm.get_image(cur_col, cur_row)
                    icm.set_image(cur_col, cur_row - 1, fn)
                    icm.set_image(cur_col, cur_row, None)
            continue
        
        # Give the image that was duplicated.  It will be removed
        m = re.match('c([0-9]+)_r([0-9]+).jpg-', action)
        if m:
            rm_col = int(m.group(1))
            rm_row = int(m.group(2))
            # The image given is removed (specify the second image taken)
            print 'Remove double image @ %dc, %dr' % (rm_col, rm_row)
            
            # remove the bad image
            del icm.layout[(rm_col, rm_row)]
            
            # Determine shift needed
            # Even row: moving right
            if rm_row % 2 == 0:
                # If the first image is duplicate its column 1 thats the duplicate
                if rm_col == 0:
                    raise Exception("Row must be > 0")
                # to avoid getting negative columns, shift previous rows right                
                # shift previous rows right
                for row in xrange(0, rm_row):
                    row_right(row, 0)
                # Shift remaining images this row
                row_left(rm_row, rm_col + 1)
                # Remaining rows stay the same
            # Odd row: moving left
            else:
                # Shift remaining images this row
                row_right(rm_row, rm_col - 1)
                # Shift remaining images
                for row in xrange(rm_row + 1, icm.rows):
                    row_right(row, 0)
                
            continue

        # Give the image that was skipped
        m = re.match('c([0-9]+)_r([0-9]+).jpg+', action)
        if m:
            skip_col = int(m.group(1))
            skip_row = int(m.group(2))
            print 'Add skipped image @ %dc, %dr' % (skip_col, skip_row)

            # No image to remove: a gap is going to form
            
            # Determine shift needed
            # Even row: moving right
            if skip_row % 2 == 0:
                # Shift remaining images this row
                row_right(skip_row, skip_col)
                # Shift remaining images
                for row in xrange(skip_row + 1, icm.rows):
                    row_right(row, 0)
            # Odd row: moving left
            else:
                # to avoid getting negative columns, shift previous rows right                
                # shift previous rows right
                for row in xrange(0, skip_row):
                    row_right(row, 0)
                # Shift remaining images this row
                row_right(skip_row, skip_col + 1)
                
            continue
        
        raise Exception('Unrecognized action %s' % action)

    tmp_dir = os.path.join(args.dir, 'pr0nshift.tmp')
    if os.path.exists(tmp_dir):
        if os.listdir(path) != []:
            raise Exception("Aborting run: stale pr0nshift dir")
        if not args.dry:
            os.rmdir(tmp_dir)
    if not args.dry:
        os.mkdir(tmp_dir)
        
    print 'Phase 1: stage'
    dry_actions = {}
    for (col, row) in sorted(list(icm.gen_set())):
        src_fn = icm.get_image(col, row)
        dst_fn = os.path.join(tmp_dir, 'c%04d_r%04d.jpg' % (col, row))
        working_set.remove(src_fn)
        if args.dry:
            dry_actions[src_fn] = ('=> %s' % dst_fn)
        else:
            shutil.move(src_fn, dst_fn)
    for del_fn in working_set:
        if args.dry:
            dry_actions[src_fn] = ('rm')
        else:
            os.unlink(del_fn)
    for fn in sorted(dry_actions):
        print 'DRY: %s %s' % (fn, dry_actions[fn])

    
    print 'Phase 2: merge'
    for (col, row) in icm.gen_set():
        basename = 'c%04d_r%04d.jpg' % (col, row)
        src_fn = os.path.join(tmp_dir, basename)
        dst_fn = os.path.join(args.dir, basename)
        if args.dry:
            #print 'DRY: %s => %s' % (src_fn, dst_fn)
            pass
        else:
            if os.path.exists(dst_fn):
                raise Exception("Dst filename %s exists" % dst_fn)
            shutil.move(src_fn, dst_fn)
        
    print 'Cleaning up'
    if not args.dry:
        # should be empty
        os.rmdir(tmp_dir)
    
    print 'Done'

