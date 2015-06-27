#!/usr/bin/env python

'''
Improves on 01 by operating on a raw image

Primary goals:
-Determine grid layout
-Don't consider items not in grid

Secondary:
-Automaticly detect rotation
    Okay manually passing this for now
'''

#from cv2 import cv
from PIL import Image, ImageDraw, ImageStat
import sys
import time
import os
import shutil
import random
import argparse        
import numpy
import pylab
import matplotlib

dbgl = 1

def dbg(s, level = 1):
    if level > dbgl:
        return
    print s

def drange(start, stop=None, step=1.0):
    if stop is None:
        (start, stop) = (0, start)
    r = start
    while r < stop:
        yield r
        r += step

class CVTest():
    def __init__(self, fn, outdir):
        self.fn = fn
        self.outdir = outdir
        # Approx number of pixels per grid unit
        #self.gridp = 29
        self.gridp = 14.44
        
        # Tag as empty
        '''
        90: at least one missed via at end and one in the middle (not even tagged as warning)
        80: some minor improvements but a lot more warnings
        70: the one big error was fixed but lots of little errors introduced
        
        Resolution: leave as 90 for now
        Let DRC and/or more advanced rules catch
        '''
        self.threshl = 90
        # Tag as metal
        self.threshh = 110
        # Anything in between is flagged for review
        # might consider a DRC check to try to guess these
    
    def run(self):
        start = time.time()
        
        '''
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        os.mkdir(self.outdir)
        '''
        if not os.path.exists(self.outdir):
            os.mkdir(self.outdir)
        
        im = Image.open(self.fn)
        print '%s: %dw x %dh' % (self.fn, im.size[0], im.size[1])
        print 'Grid pixel w/h: %s' % self.gridp
        im = im.crop((9, 9, im.size[0], im.size[1]))
        print im
        print 'crop: %dw x %dh' % (im.size[0], im.size[1])

        self.grid_lines(im)
        #self.stat(im)
        #self.viz(im)
        self.viz_drc(im)
        #self.final(im)

        end = time.time()
        dbg('Runtime: %0.3f sec' % (end - start,))
    
    def grid_lines(self, im):
        '''Draw a grid onto the image to see that it lines up'''
        print 'grid_lines()'
        im = im.copy()
        draw = ImageDraw.Draw(im)
        for x in drange(0, im.size[0], self.gridp):
            x = int(x)
            draw.line((x, 0, x, im.size[1]), fill=128)
        for y in drange(0, im.size[1], self.gridp):
            y = int(y)
            draw.line((0, y, im.size[0], y), fill=128)
        del draw
        im.save(os.path.join(self.outdir, 'grid.png'))
        del im

    def stat(self, im):
        '''
        image mean
        [57.06916963894625, 112.62541678958048, 86.42082651720347, 255.0]
        '''
        print 'stat()'
        means = {'r': [], 'g': [],'b': [],'u': []}
        for y in drange(0, im.size[1], self.gridp):
            y = int(y)
            for x in drange(0, im.size[0], self.gridp):
                x = int(x)
                
                # TODO: look into using mask
                # I suspect this is faster
                imxy = im.crop((x, y, x + int(self.gridp), y + int(self.gridp)))
                mean = ImageStat.Stat(imxy).mean
                mmean = sum(mean[0:3])/3.0
                means['r'].append(mean[0])
                means['g'].append(mean[1])
                means['b'].append(mean[2])
                means['u'].append(mmean)
                #print 'x%0.4d y%0.4d:     % 8.3f % 8.3f % 8.3f % 8.3f % 8.3f' % (x, y, mean[0], mean[1], mean[2], mean[3], mmean)

        for c, d in means.iteritems():
            matplotlib.pyplot.clf()
            #pylab.plot(h,fit,'-o')
            pylab.hist(d, bins=50)
            #pylab.save(os.path.join(self.outdir, 'stat_%s.png' % c))
            pylab.savefig(os.path.join(self.outdir, 'stat_%s.png' % c))

    def viz(self, im):
        print 'viz()'
        means = {'r': [], 'g': [],'b': [],'u': []}

        threshm = {}
        c2x = {}
        r2y = {}
        
        r = 0
        for y in drange(0, im.size[1], self.gridp):
            y = int(y)
            r2y[r] = y
            c = 0
            for x in drange(0, im.size[0], self.gridp):
                x = int(x)
                c2x[c] = x
                
                # TODO: look into using mask
                # I suspect this is faster
                imxy = im.crop((x, y, x + int(self.gridp), y + int(self.gridp)))
                mean = ImageStat.Stat(imxy).mean
                mmean = sum(mean[0:3])/3.0
                means['r'].append(mean[0])
                means['g'].append(mean[1])
                means['b'].append(mean[2])
                means['u'].append(mmean)
                #print 'x%0.4d y%0.4d:     % 8.3f % 8.3f % 8.3f % 8.3f % 8.3f' % (x, y, mean[0], mean[1], mean[2], mean[3], mmean)
                threshm[(c, r)] = mmean
                c += 1
            r += 1
        
        cols = c
        rows = r
        print 'Design grid: %dc x %dr' % (cols, rows)
        
        viz = im.copy()
        draw = ImageDraw.Draw(viz)

        print 'Annotating'
        # looks ugly due to non-integer pitch + randomized order
        #for (c, r), thresh in threshm.iteritems():
        for c in xrange(cols):
            for r in xrange(rows):
                thresh = threshm[(c, r)]
                x = c2x[c]
                y = r2y[r]
                # The void
                if thresh <= self.threshl:
                    fill = "black"
                # Pretty metal
                elif thresh >= self.threshh:
                    fill = "blue"
                # WTFBBQ
                else:
                    fill = "orange"
                
                #print 'drawing'
                draw.rectangle((x, y, x + int(self.gridp), y + int(self.gridp)), fill=fill)
        
        print 'Saving'
        viz.save(os.path.join(self.outdir, 'viz.png'))
        
    def viz_drc(self, im):
        '''Like above except try to do DRC to filter out false positives'''
        print 'viz()'
        means = {'r': [], 'g': [],'b': [],'u': []}

        threshm = {}
        c2x = {}
        r2y = {}
        
        r = 0
        for y in drange(0, im.size[1], self.gridp):
            y = int(y)
            r2y[r] = y
            c = 0
            for x in drange(0, im.size[0], self.gridp):
                x = int(x)
                c2x[c] = x
                
                # TODO: look into using mask
                # I suspect this is faster
                imxy = im.crop((x, y, x + int(self.gridp), y + int(self.gridp)))
                mean = ImageStat.Stat(imxy).mean
                mmean = sum(mean[0:3])/3.0
                means['r'].append(mean[0])
                means['g'].append(mean[1])
                means['b'].append(mean[2])
                means['u'].append(mmean)
                #print 'x%0.4d y%0.4d:     % 8.3f % 8.3f % 8.3f % 8.3f % 8.3f' % (x, y, mean[0], mean[1], mean[2], mean[3], mmean)
                threshm[(c, r)] = mmean
                c += 1
            r += 1
        
        cols = c
        rows = r
        print 'Design grid: %dc x %dr' % (cols, rows)
        def rowcol():
            for c in xrange(cols):
                for r in xrange(rows):
                    yield (c, r)

        viz = im.copy()
        draw = ImageDraw.Draw(viz)

        def bitmap_save(bitmap, fn):
            bitmap2fill = {
                    'v':'black',
                    'm':'blue',
                    'u':'orange',
                    }
            for c, r in rowcol():
                fill = bitmap2fill[bitmap[(c, r)]]
                x = c2x[c]
                y = r2y[r]
                draw.rectangle((x, y, x + int(self.gridp), y + int(self.gridp)), fill=fill)
            
            viz.save(fn)
        
        print
        
        def gen_bitmap(threshl, threshh):
            '''
            m: metal
            v: void / nothing
            u: unknown
            '''
            bitmap = {}

            print 'Generating bitmap'
            # looks ugly due to non-integer pitch + randomized order
            #for (c, r), thresh in threshm.iteritems():
            unk_open = set()
            for c, r in rowcol():
                thresh = threshm[(c, r)]
                x = c2x[c]
                y = r2y[r]
                # The void
                if thresh <= threshl:
                    bitmap[(c, r)] = 'v'
                # Pretty metal
                elif thresh >= threshh:
                    bitmap[(c, r)] = 'm'
                # WTFBBQ
                else:
                    bitmap[(c, r)] = 'u'
                    unk_open.add((c, r))
            return (bitmap, unk_open)
        (bitmap, unk_open) = gen_bitmap(self.threshl, self.threshh)

        print 'Unknown (initial): %d' % len(unk_open)
        bitmap_save(bitmap, os.path.join(self.outdir, 'viz_drc_01_init.png'))

        print
        
        '''
        If an unknown is surrounded by void eliminate it
        Its very likely noise
        '''
        print 'Looking for lone unknowns'
        def filt_unk_lone(bitmap, unk_open):
            for c, r in set(unk_open):
                # look for adjacent
                if     (bitmap.get((c - 1, r), 'v') == 'v' and bitmap.get((c + 1, r), 'v') == 'v' and
                        bitmap.get((c, r - 1), 'v') == 'v' and bitmap.get((c, r + 1), 'v') == 'v'):
                    print '  Unknown %dc, %dr rm: lone' % (c, r)
                    bitmap[(c, r)] = 'v'
                    unk_open.discard((c, r))
        filt_unk_lone(bitmap, unk_open)
        print 'Unknown (post-lone): %d' % len(unk_open)
        bitmap_save(bitmap, os.path.join(self.outdir, 'viz_drc_02_lone.png'))

        def has_around(bitmap, c, r, t, d='v'):
            return (bitmap.get((c - 1, r), d) == t or bitmap.get((c + 1, r), d) == t or
                        bitmap.get((c, r - 1), d) == t or bitmap.get((c, r + 1), d) == t)

        print

        '''
        If a single unknown is on a contiguous strip of metal its likely a via has distorted it
        Note: this will ocassionally cause garbage to incorrectly merge nets
        '''
        def munge_unk_cont(bitmap, unk_open):
            for c, r in set(unk_open):
                # Abort if any adjacent unknowns
                if has_around(bitmap, c, r, 'u'):
                    continue
                # Is there surrounding metal?
                if not has_around(bitmap, c, r, 'm'):
                    continue
                print '  Unknown %dc, %dr => m: join m' % (c, r)
                bitmap[(c, r)] = 'm'
                unk_open.discard((c, r))
                    
        print 'Looking for lone unknowns'
        munge_unk_cont(bitmap, unk_open)
        print 'Unknown (post-cont): %d' % len(unk_open)
        bitmap_save(bitmap, os.path.join(self.outdir, 'viz_drc_03_cont.png'))
        
        print
        
        '''
        Try to propagate using more aggressive threshold after initial truth is created that we are pretty confident in
        Any warnings in aggressive adjacent to metal in baseline are taken as truth
        '''
        print 'prop_ag()'
        def prop_ag(bitmap, bitmap_ag):
            for c, r in rowcol():
                # Skip if nothing is there
                if bitmap_ag[(c, r)] == 'v':
                    continue
                # Do we already think something is there?
                if bitmap[(c, r)] == 'm':
                    continue
                # Is there something to extend?
                if not has_around(bitmap, c, r, 'm'):
                    continue
                print '  %dc, %dr => m: join m' % (c, r)
                bitmap[(c, r)] = 'm'
            
        # above 10 generated false positives
        # below 9 lost one of the fixes
        # keep at 9 for now as it stil has some margin
        bitmap_ag, _unk_open = gen_bitmap(self.threshl - 9, self.threshh)
        bitmap_save(bitmap_ag, os.path.join(self.outdir, 'viz_drc_04-1_ag.png'))
        prop_ag(bitmap, bitmap_ag)
        print 'Unknown (post-ag): %d' % len(unk_open)
        bitmap_save(bitmap, os.path.join(self.outdir, 'viz_drc_04-2_ag.png'))
        
        print
        print 'Final counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))

    def final(self, im):
        print 'final()'
        im = im.copy()
        im.save(os.path.join(self.outdir, 'final.png'))
        del im

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CV test')
    parser.add_argument('fn_in', help='image file to process')
    args = parser.parse_args()

    cvt = CVTest(args.fn_in, os.path.splitext(args.fn_in)[0])
    cvt.run()

