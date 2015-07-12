from pylab import plot,show
from numpy import vstack,array
from numpy.random import rand
from scipy.cluster.vq import kmeans,vq
import cv2
import numpy as np
import argparse
import pylab
import matplotlib
import os
from collections import Counter
from PIL import Image, ImageDraw, ImageStat
from scipy import fftpack
import random
from scipy.optimize import leastsq
import matplotlib.pyplot as plt
import math
import glob

def drange(start, stop=None, step=1.0):
    if stop is None:
        (start, stop) = (0, start)
    r = start
    while r < stop:
        yield r
        r += step

class GridCap:
    def __init__(self, fn):
        self.fn = fn
        self.outdir = os.path.splitext(args.fn_in)[0]
        if not os.path.exists(self.outdir):
            os.mkdir(self.outdir)
        
        # rotated and cropped
        self.preproc_fn = None
        self.preproc_im = None
        self.edges = None
        # Must be within 3 signas of mean to be confident
        self.thresh_sig = 3.0
        self.step = None
        
        # Number of pixels to look at for clusters
        # needs to be enough that at least 3 grid lines are in scope
        # TODO: look into ways to automaticaly detect this
        # what if I ran it over the entire image?
        # would be a large number of clusters
        # Maybe just chose a fraction of the image size?
        self.clust_thresh = 100
        
        '''
        Row/col pixel offset for grid lines
        x = col * xm + xb
        y = row * ym + yb
        (xm, xb) = self.grid_xlin[0]
        (ym, yb) = self.grid_ylin[1]
        '''
        self.grid_lins = None
        # 0: cols, 1: rows
        self.crs = [None, None]
        
        '''
        [c][r] to tile state
        m: metal
        v: void / nothing
        u: unknown
        '''
        self.ts = None

        # low thresh: equal or lower => empty
        # high tresh: equal or higher => metal
        # in between: flag for review
        self.threshl = None
        self.threshh = None
        
        self.means_rc = None
        
    def run(self):
        print 'run()'
        self.step = 0
        self.sstep = 0

        print
        
        # Straighten, cropping image slightly
        self.step += 1
        
        self.preproc_fn = self.fn
        self.preproc_im = Image.open(self.fn)

        print

        # Find grid
        self.step += 1
        print 'gridify()'
        self.gridify()

        print

    def regress_axis(self, order, x0s, x0sd_roi):
        '''
        
        x0s: x position where vertical lines occurred
        x0sds_roi: difference between x positions (lower values)

        order
            0: use x positions to slice columns
            1: use y positions to slice rows
        '''
        
        '''
        Cluster differences to find the distance between clusters
        This is approximately the distance between grid lines
        '''
        
        if 0:
            m_est = self.lin_kmeans(np.array(x0sd_roi))
            b_est = 0.0
        else:
            '''
            Optimal cluster size: 8
            Cluster pitch: 13.9718618393
            
            The actual is 14.44 meaning we are 3.4% off
            
            seed:x = 14.44 c + 9.0
            Calc x = 14.4 c + 9.9
            Error: 4.029336

            seed:x = 13.9718618393 c + 9.0
            Calc x = 14.0 c + 8.4
            Error: 18.827268

            seed:x = 10 c + 9.0
            Calc x = 10.0 c + 12.0
            Error: 17.731580
            
            seed:x = 10 c + 0
            Calc x = 10.0 c + 2.0
            Error: 17.731580
            
            It seems that it really can recognize a good solution but the high-nonlinearity means it has hard time finding it
            '''
            
            #m_est = 10;     b_est = 0
            #m_est = 14.44;  b_est = 9.0
            m_est = 13.9718618393;     b_est = 0
        
        #grid_xlin, self.crs[0] = self.leastsq_axis(order, x0s, m_est, b_est)
        grid_xlin, self.crs[0] = self.leastsq_axis_iter(order, x0s, m_est, b_est)
        self.grid_lins = (grid_xlin, None)
        self.dbg_grid()
        print 'Debug break'
        import sys; sys.exit(1)

        m = self.lin_kmeans(np.array(x0sd_roi))
        grid_xlin, self.crs[0] = self.gridify_axis(order, m, x0s)
        self.grid_lins = (grid_xlin, None)
        self.dbg_grid()
        
        print 'Cols: %d' % self.crs[order]
        for i in xrange(3):
            print '  %d: %s' % (i, grid_xlin[0] * i + grid_xlin[1])
        print '  ...'
        
        for col in self.crs[0]:
            (xm, xb) = self.grid_lins[0]
            x0 = int(xm * col + xb)
            x1 = int(xm * (col + 1) + xb)
            
            # TODO: look into using mask
            # I suspect this is faster though
            edges = self.edges.crop((x0, 0, x1, self.edges[1]))
            x0s_crop, y0s_crop = self.lines(edges, None)
            

    def lin_kmeans(self, data2_np):
        '''
        The pitch of the clusters should be constant
        Find the mean pitch and penalize when clusters stray from it
        '''
        clustersm = {}
        clustersm_c = {}
        clustersm_d = {}
        clustersm_centroids = {}
        '''
        Need 2 clusters to take centroid difference
        But with only two there is only one centroid derrivitive => average is the diff
        Therefore need at least 3 for a meaningful result
        '''
        for clusters in xrange(3, 20):
            verbose = 0
            if verbose:
                print
                print clusters
            # computing K-Means with K = 2 (2 clusters)
            centroids,_ = kmeans(data2_np, clusters)
            centroids_sort = sorted(centroids)
            clustersm_centroids[clusters] = centroids_sort
            #print centroids_sort
            # assign each sample to a cluster
            idx,_ = vq(data2_np, centroids)
            errs = []
            if verbose:
                print 'Errors'
            for v, i in zip(data2_np, idx):
                #print '  %s, %s' % (v, centroids[i])
                errs.append((v - centroids[i]) ** 2)
            err = sum(errs) / len(errs)
            if verbose:
                print 'RMS error: %s' % (err,)
            clustersm[clusters] = err
            
            centroidsd = [b - a for a, b in zip(centroids_sort, centroids_sort[1:])]
            avg = 1.0 * sum(centroidsd) / len(centroidsd)
            clustersm_d[clusters] = avg
            if verbose:
                print 'Centroidsd (%s)' % avg
            errs = []
            for c in centroidsd:
                e = (c - avg) ** 2
                if verbose:
                    print '  %s => %s' % (c, e)
                errs.append(e)
            err = sum(errs) / len(errs)
            clustersm_c[clusters] = err
            if verbose:
                print 'Derritive error: %s' % err
            
            
        print clustersm
        print clustersm_c
        
        print
        print
        print
        clust_opt = min(clustersm_c, key=clustersm_c.get)
        print 'Optimal cluster size: %s' % clust_opt
        cluster_d = clustersm_d[clust_opt]
        print 'Cluster pitch: %s' % cluster_d
        '''
        if 0:
            centroids = clustersm_centroids[clust_opt]
            m, b, rval, pval, std_err = stats.linregress(range(len(centroids)), centroids)
            print 'X grid regression'
            print '  m: %s' % m
            print '  b: %s' % b
            print '  rval: %s' % rval
            print '  pval: %s' % pval
            print '  std_err: %s' % std_err
        '''
        return cluster_d

        
    def dbg_grid(self):
        '''Draw a grid onto the image to see that it lines up'''
        im = self.preproc_im.copy()
        draw = ImageDraw.Draw(im)
        # +1: draw right bounding box
        if self.grid_lins[0] is not None:
            (m, b) = self.grid_lins[0]
            if b is not None:
                for c in xrange(self.crs[0] + 1):
                    x = int(m * c + b)
                    draw.line((x, 0, x, im.size[1]), fill=128)
        
        if self.grid_lins[1] is not None:
            (m, b) = self.grid_lins[1]
            if b is not None:
                for r in xrange(self.crs[1] + 1):
                    y = int(m * r + b)
                    draw.line((0, y, im.size[0], y), fill=128)
        del draw
        self.sstep += 1
        im.save(os.path.join(self.outdir, 's%02d-%02d_grid.png' % (self.step, self.sstep)))
        del im
    
    def gridify_axis(self, order, m, xy0s):
        '''grid_xylin => m x + b coefficients '''
        '''
        Now that we know the line pitch need to fit it back to the original x and y data
        Pitch is known, just play with offsets
        Try to snap points to offset and calculate the error
        
        Calcualte regression on pixels to get row/col pixel offset for grid lines
        xline = col * m + b
        '''
        #points = sorted(x0s)
        
        def res(p, points):
            (b,) = p
            err = []
            for x in points:
                xd = (x - b) / m
                err.append(xd % 1)
            return err
        
        print 'order %d: regressing %d lines' % (order, len(xy0s))
        (xyres, _cov_xy) = leastsq(res, [m/2], args=(xy0s,))
        print 'Optimal X offset: %s' % xyres[0]
        grid_xylin = (m, xyres[0])
        rowcols = int((self.preproc_im.size[order] - grid_xylin[1])/grid_xylin[0])

        return grid_xylin, rowcols

    def leastsq_axis_png(self, fn, detected, m, b):
        '''
        Want actual detected lines draw in red
        Then draw the linear series onto the image
        '''

        im = self.preproc_im.copy()
        draw = ImageDraw.Draw(im)
        
        for x in detected:
            draw.line((x, 0, x, im.size[1]), fill='red')
        
        # +1: draw right bounding box
        # just clpi it
        cols = 200
        for c in xrange(cols + 1):
            x = int(m * c + b)
            draw.line((x, 0, x, im.size[1]), fill='blue')
        
        del draw
        im.save(fn)
        del im
    
    def leastsq_axis_iter(self, order, x0s, m_est, b_est, png=1):
        print
        print
        
        x0s = sorted(x0s)
        
        if png:
            log_dir = os.path.join(self.outdir, 'leastsq')
            if os.path.exists(log_dir):
                print 'Cleaning up old visuals'
                for fn in glob.glob('%s/*' % log_dir):
                    os.unlink(fn)
            else:
                os.mkdir(log_dir)
        
        itern = [0]
        for i in xrange(4, len(x0s)):
            print
            x0s_this = x0s[0:i+1]
            mb, rowcols = self.leastsq_axis(order, x0s_this, m_est, b_est, png=False)
            m_est, b_est = mb
            print 'Iter % 6d x = %16.12f c + %16.12f' % (itern[0], m_est, b_est)
            if png:
                self.leastsq_axis_png(os.path.join(log_dir, 'iter_%04d_%0.6fm_%0.6fb.png' % (itern[0], m_est, b_est)), x0s_this, m_est, b_est)
            itern[0] += 1
        print
        print 'Iter done'
        return mb, rowcols
    
    def leastsq_axis(self, order, x0s, m_est, b_est, png=False):
        if png:
            log_dir = os.path.join(self.outdir, 'leastsq')
            if os.path.exists(log_dir):
                print 'Cleaning up old visuals'
                for fn in glob.glob('%s/*' % log_dir):
                    os.unlink(fn)
            else:
                os.mkdir(log_dir)
        
        '''
        Return 
        (m, b), cols
        
        Problem: if it choses a really large m then errors are minimized as x / m approaches 0
        '''
        maxx = max(x0s)
        itern = [0]
        def res(p):
            verbose = False
            silent = True
            m, b = p
            if not silent:
                print 'Iter % 6d x = %16.12f c + %16.12f' % (itern[0], m, b)
            err = []
            if verbose:
                print '  Points'
            for x in x0s:
                # Find the closest column number
                xd = (x - b) / m
                # Errors are around 1 so center
                # ie 0.9, 0.1 are equivalent errors => 0.1, 0.1
                xd1 = xd % 1
                if xd1 < 0.5:
                    xd1c = xd1
                else:
                    xd1c = 1.0 - xd1
                if verbose:
                    print '    x:      %d' % x
                    print '      xd:   %16.12f' % xd
                    print '      xd1:  %16.12f' % xd1
                    print '      xd1c: %16.12f' % xd1c

                
                '''
                # test if it can chose a good low m
                if m > 30:
                    xd1c += m - 30
                
                # hack to keep it from going too large
                if b > maxx:
                    xd1c += b - maxx
                if b < 0:
                    xd1c += -b
                if m > maxx:
                    xd1c += m - maxx
                '''
                # penalize heavily if drifts from estimate which should be accurate within a few percent
                #m_err = 
                err.append(xd1c)
                
            if png:
                self.leastsq_axis_png(os.path.join(log_dir, 'iter_%04d_%0.6fm_%0.6fb.png' % (itern[0], m, b)), x0s, m, b)
            
            itern[0] += 1
            if not silent:
                print '  Error: %0.6f (%0.6f rms)' % (sum(err), math.sqrt(sum([x**2 for x in err]) / len(err)))
            return err
    
        (mb, cov) = leastsq(res, [m_est, b_est])
        
        print 'Covariance: %0.1f' % cov
        print 'Calc x = %0.1f c + %0.1f' % (mb[0], mb[1])
        rowcols = int((self.preproc_im.size[order] - mb[1])/mb[0])
        print 'Calc cols: %d' % rowcols
        return mb, rowcols

    def lines(self, edges, dbg_img):
        lines = cv2.HoughLines(edges, 1, np.pi/1800., 400)
        x0s = []
        y0s = []
        for rho,theta in lines[0]:
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho

            scal = 2000
            x1 = int(x0 + scal * -b)
            y1 = int(y0 + scal *  a)
            x2 = int(x0 - scal * -b)
            y2 = int(y0 - scal *  a)
            
            # only keep vertical lines for now
            # these will have thetas close to 0 or pi
            d = 0.1
            if theta > 0 - d and theta < 0 + d or theta > np.pi - d and theta < np.pi + d:
                x0s.append(abs(rho))
                if dbg_img is not None:
                    cv2.line(dbg_img, (x1,y1),(x2,y2),(0, 0, 255),2)
            elif theta > np.pi/2 - d and theta < np.pi/2 + d or theta > 3 * np.pi / 2 - d and theta < 3 * np.pi / 2 + d:
                y0s.append(abs(rho))
            else:
                if dbg_img is not None:
                    cv2.line(dbg_img, (x1,y1),(x2,y2),(0, 255, 0),2)
                continue
        
        if dbg_img is not None:
            self.sstep += 1
            cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_lines.png' % (self.step, self.sstep)), dbg_img)
        return x0s, y0s

    def gridify(self):
        '''Final output to self.grid_lins, self.crs[1], self.crs[0]'''
        
        # Find lines and compute x/y distances between them
        img = cv2.imread(self.preproc_fn)
        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_orig.png' % (self.step, self.sstep)), img)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_cvtColor.png' % (self.step, self.sstep)), gray)
        
        '''
        http://stackoverflow.com/questions/6070530/how-to-choose-thresold-values-for-edge-detection-in-opencv
        
        Firstly Canny Uses two Thresholds for hysteris and Nonmaxima Suppression, one low threshold and one high threshold. 
        Its generally preferred that high threshold is chosen to be double of low threshold .

        Lower Threshold -- Edges having Magnitude less than that will be suppressed
        
        Higher Threshhold -- Edges having Magnitude greater than will be retained
        
        and Edges between Low and High will be retained only if if lies/connects to a high thresholded edge point.
        '''
        self.edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_canny.png' % (self.step, self.sstep)), self.edges)

        x0s, y0s = self.lines(self.edges, img)

        # Sweep over all line pairs, generating set of all line distances
        def gen_diffs(xys):
            diffs_all = []
            diffs_roi = []
        
            for i in xrange(len(xys)):
                for j in xrange(i):
                    d = abs(xys[i] - xys[j])
                    diffs_all.append(d)
                    if d < self.clust_thresh:
                        diffs_roi.append(d)
            return diffs_all, diffs_roi

        self.grid_lins = [None, None]

        print 'x0s: %d' % len(x0s)
        if len(x0s) != 0:
            x0sd_all, x0sd_roi = gen_diffs(x0s)
            
            matplotlib.pyplot.clf()
            pylab.hist(x0sd_all, bins=100)
            self.sstep += 1
            pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_pairx_all.png' % (self.step, self.sstep)))
    
            matplotlib.pyplot.clf()
            pylab.hist(x0sd_roi, bins=100)
            self.sstep += 1
            pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_pairx_small.png' % (self.step, self.sstep)))

        print 'y0s: %d' % len(x0s)
        if len(y0s) != 0:
            y0sd_all, y0sd_roi = gen_diffs(y0s)
            
            matplotlib.pyplot.clf()
            pylab.hist(y0sd_all, bins=100)
            self.sstep += 1
            pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_pairy_all.png' % (self.step, self.sstep)))
    
            matplotlib.pyplot.clf()
            pylab.hist(y0sd_roi, bins=100)
            self.sstep += 1
            pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_pairy_small.png' % (self.step, self.sstep)))

        if len(x0s) != 0 and len(y0s):
            print 'Grid detection: using global x/y lines'
            
            # attempt to auto-cluster
            # try to find the largest clusters along the same level of detail
            
            #return (x0s, x0sd_all, x0sd_roi, y0s, y0sd_all, y0sd_roi)

            # Cluster differences to find distance between them
            # XXX: should combine x and y set?
            m = self.lin_kmeans(np.array(x0sd_roi))
            # Take now known grid pitch and find offsets
            # by doing regression against original positions

            self.grid_lins[0], self.crs[0] = self.gridify_axis(0, m, x0s)
            self.grid_lins[1], self.crs[1] = self.gridify_axis(1, m, y0s)
            
            self.dbg_grid()
            
        elif len(x0s) != 0:
            print 'WARNING: no y lines.  Switching to column detection mode'
            self.regress_axis(0, x0s, x0sd_roi)
        elif len(y0s) != 0:
            raise Exception("FIXME")
            self.regress_axis(1, y0s, y0sd_roi)
        else:
            raise Exception("Failed to detect grid.  Adjust thresholds?")








    def cr(self):
        for c in xrange(self.crs[0] + 1):
            for r in xrange(self.crs[1] + 1):
                yield (c, r)

    def xy(self):
        '''Generate (x0, y0) upper left and (x1, y1) lower right (inclusive) tile coordinates'''
        for c in xrange(self.crs[0] + 1):
            (xm, xb) = self.grid_lins[0]
            x = int(xm * c + xb)
            for r in xrange(self.crs[1] + 1):
                (ym, yb) = self.grid_lins[1]
                y = int(ym * r + yb)
                yield (x, y), (x + xm, y + ym)

    def xy_cr(self):
        for c in xrange(self.crs[0] + 1):
            (xm, xb) = self.grid_lins[0]
            x = int(xm * c + xb)
            for r in xrange(self.crs[1] + 1):
                (ym, yb) = self.grid_lins[1]
                y = int(ym * r + yb)
                yield ((x, y), (x + xm, y + ym)), (c, r)




    def bitmap_save(self, bitmap, fn):
        viz = self.preproc_im.copy()
        draw = ImageDraw.Draw(viz)
        bitmap2fill = {
                'v':'black',
                'm':'blue',
                'u':'orange',
                }
        for ((x0, y0), (x1, y1)), (c, r) in self.xy_cr():
            draw.rectangle((x0, y0, x1, y1), fill=bitmap2fill[bitmap[(c, r)]])
        viz.save(fn)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grid auto-bitmap test')
    parser.add_argument('--angle', help='Correct specified rotation instead of auto-rotating')
    parser.add_argument('--no-straighten', action='store_true')
    parser.add_argument('fn_in', help='image file to process')
    args = parser.parse_args()

    gc = GridCap(args.fn_in)
    gc.run()
