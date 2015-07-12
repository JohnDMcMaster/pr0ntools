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
import json
import shutil

from pr0ntools.util import add_bool_arg

debug = False

class GridCapFailed(Exception):
    pass

def rms_err(d1, d2):
    if len(d1) != len(d2):
        raise ValueError("Must be equal length")
    errs = []
    for i1, i2 in zip(d1, d2):
        errs.append((i1 - i2) ** 2)
    return math.sqrt(sum(errs) / len(errs))

def drange(start, stop=None, step=1.0):
    if stop is None:
        (start, stop) = (0, start)
    r = start
    while r < stop:
        yield r
        r += step

'''
def has_around(bitmap, c, r, t, d='v', order=1):
    return (bitmap.get((c - 1,  r),     d) != t and
            bitmap.get((c + 1,  r),     d) != t and
            bitmap.get((c,      r - 1), d) != t and
            bitmap.get((c,      r + 1), d) != t)
'''
def has_around(bitmap, c, r, t, d='v', order=1):
    '''Return true if d exists for order tiles in at least one direction around c, r'''
    # the four directions
    for cr in [
            lambda i: (c - i,  r),
            lambda i: (c + i,  r),
            lambda i: (c,      r - 1),
            lambda i: (c,      r + 1),
            ]:
        def check():
            # order tiles this direction match?
            for i in xrange(order + 1):
                if bitmap.get(cr(i), d) != t:
                    return False
            return True
        # this direction has a match?
        if check():
            return True
    # No direction matched
    return False
                

class GridCap:
    def __init__(self, fn, outdir):
        self.fn = fn
        self.outdir = outdir
        if not os.path.exists(self.outdir):
            os.mkdir(self.outdir)
        
        # rotated and cropped
        self.preproc_fn = None
        self.preproc_im = None
        self.edges = None
        # Must be within 3 signas of mean to be confident
        self.thresh_sig = 3.0
        self.step = None
        
        self.copy_fn = None
        self.png_fn = None
        
        self.straighten_angle = None
        self.calc_straighten_angle = None
        
        # green seems to give the best results on my setup
        self.channel = 'g'
        
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
        self.xy_mb = [None, None]
        self.m_est = None
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
        
        self.bitmap = None
        
        # Misc parameters to debug dump
        self.paramsj = {}
        
    def run(self):
        print 'run()'
        self.step = 0
        self.sstep = 0
        pass_ = False

        print
        
        try:
            print
            print
            print

            copy_fn = os.path.join(self.outdir, 'raw.' + os.path.splitext(self.fn)[1])
            shutil.copy(self.fn, copy_fn)
            self.copy_fn = copy_fn
    
            print '*' * 80
            # Straighten, cropping image slightly
            self.step += 1
            if self.straighten_angle == 0.0:
                print 'Skipping straighten'
                fn = os.path.join(self.fn, 'in.' + os.path.splitext(self.fn)[1])
                shutil.copy(self.fn, fn)
                self.preproc_fn = fn
                self.preproc_im = Image.open(self.fn)
            else:
                print 'straighten()'
                self.straighten()
    
            print
            print
            print
    
            print '*' * 80
            # Find grid
            self.step += 1
            self.gridify()
    
            print
            print
            print
    
            print '*' * 80
            # Figure out thresholds based on grid
            self.step += 1
            self.autothresh()
    
            print
            print
            print
    
            print '*' * 80
            # Use computed thresholds on grid to guess materials
            self.step += 1
            print 'capture()'
            self.capture()
        
            print
            print
            print
    
            print '*' * 80
            self.save()
            pass_ = True
        finally:
            print
            print
            print
            print '*' * 80
            print 'Shutting down'
            print 'Saving JSON on done'
            self.save_json(pass_)

    def straighten(self):
        self.sstep = 0
        if self.straighten_angle is not None:
            print 'Straighten: using given angle %0.3f deg' % self.straighten_angle
            angled = self.straighten_angle
            angle = angled * np.pi / 180.
        else:
            img = cv2.imread(self.fn)
            if debug:
                self.sstep += 1
                cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_orig.png' % (self.step, self.sstep)), img)
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if debug:
                self.sstep += 1
                cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_cvtColor.png' % (self.step, self.sstep)), gray)
            
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            if debug:
                self.sstep += 1
                cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_canny.png' % (self.step, self.sstep)), edges)
    
            lines = cv2.HoughLines(edges, 1, np.pi/1800., 400)
            # In radians
            thetas_keep = []
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
                
                thetad = theta * 180. / np.pi
                # take out outliers
                # I usually snap to < 1.5 (tyipcally < 0.2) so this should be plenty of margin
                if thetad < 3.0:
                    #print 'Theta: %g, rho: %g' % (theta, rho)
                    thetas_keep.append(theta)
                    cv2.line(img, (x1,y1),(x2,y2),(0, 0, 255),2)
                else:
                    cv2.line(img, (x1,y1),(x2,y2),(0, 255, 0),2)
    
            if debug:
                self.sstep += 1
                cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_lines.png' % (self.step, self.sstep)), img)
    
            if debug:
                matplotlib.pyplot.clf()
                pylab.hist(thetas_keep, bins=100)
                self.sstep += 1
                pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_theta_dist.png' % (self.step, self.sstep)))
            
            angle = sum(thetas_keep) / len(thetas_keep)
            angled = angle * 180. / np.pi
            print 'Mean angle: %f rad (%f deg)' % (angle, angled)
            self.calc_straighten_angle = angled
        

        im = Image.open(self.fn)
        # In degrees
        # Positive values cause CCW rotation, same convention as above theta
        # but we want to correct it so go opposite direction
        print 'Straighten: rotate %0.3f deg' % self.straighten_angle
        im = im.rotate(angled, resample=Image.BICUBIC)
        if debug:
            self.sstep += 1
            im.save(os.path.join(self.outdir, 's%02d-%02d_rotate.png' % (self.step, self.sstep)))
        
        imw, imh = im.size
        print 'Image size: %dw x %dh' % (imw, imh)
        sy = int(abs(imw * math.sin(angle)))
        sx = int(abs(imh * math.sin(angle)))
        print 'x crop: %d' % sx
        print 'y crop: %d' % sy
        im_crop = im.crop((sx, sy, imw - sx, imh - sy))
        
        # Used by server: always save
        self.sstep += 1
        self.preproc_fn = os.path.join(self.outdir, 's%02d-%02d_crop.jpg' % (self.step, self.sstep))
        self.preproc_im = im_crop
        im_crop.save(self.preproc_fn)


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
        
        if self.m_est is None:
            m_est = self.lin_kmeans(np.array(x0sd_roi))
        else:
            print 'Skipping lin_kmeans(): using provided m estimate %0.3f' % self.m_est
            m_est = self.m_est
        b_est = 0.0
        
        grid_xlin, self.crs[order] = self.leastsq_axis_iter(order, x0s, m_est, b_est)
        self.xy_mb[order] = grid_xlin
        self.dbg_grid()

            

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
        if not debug:
            return
        im = self.preproc_im.copy()
        draw = ImageDraw.Draw(im)
        # +1: draw right bounding box
        if self.xy_mb[0] is not None:
            (m, b) = self.xy_mb[0]
            if b is not None:
                for c in xrange(self.crs[0] + 1):
                    x = int(m * c + b)
                    draw.line((x, 0, x, im.size[1]), fill=128)
        
        if self.xy_mb[1] is not None:
            (m, b) = self.xy_mb[1]
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
    
    def leastsq_axis_iter(self, order, x0s, m_est, b_est, png=0, m_est_tol=0.05):
        verbose = False
        
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
        m_cur = m_est
        b_cur = b_est
        # 4 is somewhat arbitrary.  Can we get away with only 1 or 2?
        for i in xrange(4, len(x0s)):
            if verbose:
                print
            x0s_this = x0s[0:i+1]
            mb, rowcols = self.leastsq_axis(order, x0s_this, m_cur, b_cur, png=0)
            if abs((mb[0] - m_est) / m_est) > m_est_tol:
                print 'WARNING: throwing away new mb: exceeds estimate tolerance %0.3f' % m_est_tol
            else:
                m_cur, b_cur = mb
            if verbose:
                print 'Iter % 6d x = %16.12f c + %16.12f' % (itern[0], m_cur, b_cur)
            if png:
                self.leastsq_axis_png(os.path.join(log_dir, 'iter_%04d_%0.6fm_%0.6fb.png' % (itern[0], m_cur, b_cur)), x0s_this, m_cur, b_cur)
            itern[0] += 1
        print
        print 'Iter done'
        print 'Result x = %16.12f c + %16.12f' % (m_cur, b_cur)
        while b_cur > m_cur:
            b_cur -= m_cur
        while b_cur < 0:
            b_cur += m_cur
        print 'Normalized x = %16.12f c + %16.12f' % (m_cur, b_cur)
        return (m_cur, b_cur), rowcols
    
    def leastsq_axis(self, order, x0s, m_est, b_est, png=0, m_est_tol=0.05):
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
        verbose = False
        silent = True
        def res(p):
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
                '''
                
                # Keep it from getting unreasonably large
                '''
                if b > maxx:
                    xd1c += b - maxx
                if b < 0:
                    xd1c += -b
                if m > maxx / 2:
                    xd1c += m - maxx
                '''
                # penalize if drifts from estimate which should be accurate within a few percent
                mpe = abs(m - m_est) / m_est
                if mpe > m_est_tol:
                    xd1c += (mpe - m_est_tol) * abs(m - m_est)
                
                err.append(xd1c)
                
            if png:
                self.leastsq_axis_png(os.path.join(log_dir, 'iter_%04d_%0.6fm_%0.6fb.png' % (itern[0], m, b)), x0s, m, b)
            
            itern[0] += 1
            if not silent:
                print '  Error: %0.6f (%0.6f rms)' % (sum(err), math.sqrt(sum([x**2 for x in err]) / len(err)))
            return err
    
        (mb, cov) = leastsq(res, [m_est, b_est])
        
        if not silent:
            print 'Covariance: %0.1f' % cov
            print 'Calc x = %0.1f c + %0.1f' % (mb[0], mb[1])
        
        rowcols = int((self.preproc_im.size[order] - mb[1])/mb[0])
        if not silent:
            print 'Calc cols: %d' % rowcols
        return mb, rowcols

    def max_axis_contrast(self, order, y0s):
        '''
        Using pre-calculated complimentary order, assume same m
        Slide b across m until the maximum contrast is found
        '''
        if order != 1:
            raise Exception("FIXME")
        print 'max_axis_contrast()'
        m = self.xy_mb[0][0]
        print 'm: %0.6f' % m
        
        img = cv2.imread(self.preproc_fn)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # <type 'numpy.ndarray'>
        edges = cv2.Canny(gray, 125, 250, apertureSize=3)
        
        # FIXME: this only works for order 1
        # had problems with reduce
        sums = []
        for row in edges:
            sums.append(np.sum(row))
        
        if debug:
            matplotlib.pyplot.clf()
            plt.plot(sums)
            self.sstep += 1
            pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_sum.png' % (self.step, self.sstep)))
            with open(os.path.join(self.outdir, 's%02d-%02d_sum.csv' % (self.step, self.sstep)), 'w') as f:
                f.write('n,v\n')
                for n, v in enumerate(sums):
                    f.write('%d,%d\n' % (n, v))
        
        smin = min(sums)
        smax = max(sums)
        
        print 'Min: %0.1f' % smin
        print 'Max: %0.1f' % smax
        print 'Normalizing...'
        for i in xrange(len(sums)):
            sums[i] = (sums[i] - smin) / (smax - smin)

        # avoid boundary conditions where truncating a data point on some makes the error go down
        rows = int(self.preproc_im.size[1] / m) - 1
        
        # Brute force to avoid non-linear issues
        print 'Sweeping b values...'
        berrs = []
        for b in xrange(int(m)):
            print 'b = %d' % b
            def res():
                errs = []
                for row in xrange(rows):
                    # inclusive
                    y0 = int(m * row + b)
                    # not inclusive
                    y1 = int(m * (row + 1) + b)
                    avg = sum(sums[y0:y1]) / (y1 - y0)
                    if avg < 0.5:
                        err = avg
                    else:
                        err = 1.0 - avg
                    errs.append(err**2)
                return math.sqrt(sum(errs) / len(errs))
            berrs.append(res())
        emin = min(berrs)
        print 'Min error: %0.6f' % emin
        print 'Max error: %0.6f' % max(berrs)
        b = berrs.index(emin)
        print 'Baseline y = %16.12f r + %d' % (m, b)

        while b > m:
            b -= m
        while b < 0:
            b += m
        print 'Normalized y = %16.12f c + %d' % (m, b)

        # TODO: consider doing least squares to fine tune remaining error

        self.xy_mb[order] = (m, b)
        rowcols = int((self.preproc_im.size[order] - b)/m)
        print 'Rows: %d' % rowcols
        self.crs[order] = rowcols
        
        self.dbg_grid()

    def lines(self, edges, dbg_img):
        if not debug:
            dbg_img = None
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
                if not dbg_img is None:
                    cv2.line(dbg_img, (x1,y1),(x2,y2),(0, 0, 255),2)
            elif theta > np.pi/2 - d and theta < np.pi/2 + d or theta > 3 * np.pi / 2 - d and theta < 3 * np.pi / 2 + d:
                y0s.append(abs(rho))
            else:
                if not dbg_img is None:
                    cv2.line(dbg_img, (x1,y1),(x2,y2),(0, 255, 0),2)
                continue
        
        if not dbg_img is None:
            self.sstep += 1
            cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_lines.png' % (self.step, self.sstep)), dbg_img)
        return x0s, y0s

    def gridify(self):
        '''Final output to self.xy_mb, self.crs[1], self.crs[0]'''
        
        print 'gridify(): solving for design grid'
        
        # Find lines and compute x/y distances between them
        img = cv2.imread(self.preproc_fn)
        if debug:
            self.sstep += 1
            cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_orig.png' % (self.step, self.sstep)), img)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if debug:
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
        if debug:
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

        self.xy_mb = [None, None]

        print 'x0s: %d' % len(x0s)
        if len(x0s) != 0:
            x0sd_all, x0sd_roi = gen_diffs(x0s)
            
            if debug:
                matplotlib.pyplot.clf()
                pylab.hist(x0sd_all, bins=100)
                self.sstep += 1
                pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_pairx_all.png' % (self.step, self.sstep)))
    
            if debug:
                matplotlib.pyplot.clf()
                pylab.hist(x0sd_roi, bins=100)
                self.sstep += 1
                pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_pairx_small.png' % (self.step, self.sstep)))

        print 'y0s: %d' % len(x0s)
        if len(y0s) != 0:
            y0sd_all, y0sd_roi = gen_diffs(y0s)
            
            if debug:
                matplotlib.pyplot.clf()
                pylab.hist(y0sd_all, bins=100)
                self.sstep += 1
                pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_pairy_all.png' % (self.step, self.sstep)))
    
            if debug:
                matplotlib.pyplot.clf()
                pylab.hist(y0sd_roi, bins=100)
                self.sstep += 1
                pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_pairy_small.png' % (self.step, self.sstep)))

        if len(x0s) != 0 and len(y0s):
            raise Exception("FIXME")
            print 'Grid detection: using global x/y lines'
            
            # attempt to auto-cluster
            # try to find the largest clusters along the same level of detail
            
            #return (x0s, x0sd_all, x0sd_roi, y0s, y0sd_all, y0sd_roi)

            # Cluster differences to find distance between them
            # XXX: should combine x and y set?
            m = self.lin_kmeans(np.array(x0sd_roi))
            # Take now known grid pitch and find offsets
            # by doing regression against original positions

            self.xy_mb[0], self.crs[0] = self.gridify_axis(0, m, x0s)
            self.xy_mb[1], self.crs[1] = self.gridify_axis(1, m, y0s)
            
            self.dbg_grid()
            
        elif len(x0s) != 0:
            print 'WARNING: no y lines.  Switching to column detection mode'
            self.regress_axis(0, x0s, x0sd_roi)
            # Using above, slide y b variable around to maximize contrast
            self.max_axis_contrast(1, y0s)
        elif len(y0s) != 0:
            raise Exception("FIXME")
            self.regress_axis(1, y0s, y0sd_roi)
            self.max_axis_contrast(0, x0s)
        else:
            raise Exception("Failed to detect grid.  Adjust thresholds?")

    def cr(self, adj=0):
        for c in xrange(self.crs[0] + adj):
            for r in xrange(self.crs[1] + adj):
                yield (c, r)

    def xy(self, adj=0):
        '''Generate (x0, y0) upper left and (x1, y1) lower right (inclusive) tile coordinates'''
        for c in xrange(self.crs[0] + adj):
            (xm, xb) = self.xy_mb[0]
            x = int(xm * c + xb)
            for r in xrange(self.crs[1] + adj):
                (ym, yb) = self.xy_mb[1]
                y = int(ym * r + yb)
                yield (x, y), (x + xm, y + ym)

    def xy_cr(self, b, adj=0):
        for c in xrange(self.crs[0] + adj):
            (xm, xb) = self.xy_mb[0]
            if not b:
                xb = 0.0
            x = int(xm * c + xb)
            for r in xrange(self.crs[1] + adj):
                (ym, yb) = self.xy_mb[1]
                if not b:
                    yb = 0.0
                y = int(ym * r + yb)
                yield ((x, y), (int(x + xm), int(y + ym))), (c, r)

    def autothresh(self):
        print 'autothresh(): characterizing grid'
        
        print 'Collecting threshold statistics...'
        means = {'r': [], 'g': [],'b': [],'u': []}
        self.means_rc = {}
        
        for ((x0, y0), (x1, y1)), (c, r) in self.xy_cr(True):
            # TODO: look into using mask
            # I suspect this is faster though
            #print x0, y0, x1, y1
            imxy = self.preproc_im.crop((x0, y0, x1, y1))
            mean = ImageStat.Stat(imxy).mean
            mmean = sum(mean[0:3])/3.0
            
            channels = {
                'r': mean[0],
                'g': mean[1],
                'b': mean[2],
                'u': mmean,
                }
            for k, v in channels.iteritems():
                means[k].append(v)
            self.means_rc[(c, r)] = channels[self.channel]
            #print 'x%0.4d y%0.4d:     % 8.3f % 8.3f % 8.3f % 8.3f % 8.3f' % (x, y, mean[0], mean[1], mean[2], mean[3], mmean)

        if debug:
            for c, d in means.iteritems():
                open(os.path.join(self.outdir, 'stat_%s.txt' % c), 'w').write(repr(d))
                matplotlib.pyplot.clf()
                #pylab.plot(h,fit,'-o')
                pylab.hist(d, bins=50)
                self.sstep += 1
                pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_stat_%c.png' % (self.step, self.sstep, c)))
    
        data2 = means[self.channel]
        # Extract clusters
        data2_np = np.array(data2)
        
        # Metal and not metal
        # some small noise from vias, dirt, etc
        clusters = 2
        centroids, _ = kmeans(data2_np, clusters)
        centroids_sort = sorted(centroids)
        print centroids_sort
        clusters = centroids_sort
        # TODO: mark on graph




        #s = data2_np
        '''
        Calc 1
          u: 49.9241213118
          std: 11.8942536516
        Calc 2
          u: 151.27967783
          std: 11.0204734112
        '''
        # From above
        #clusters = [51.622280044093074, 150.84357233459423]
        print 'Clusters'
        print '  1: %s' % clusters[0]
        print '  2: %s' % clusters[1]

        #  The return value is a tuple (n, bins, patches)
        (n, bins, _patches) = pylab.hist(data2_np, bins=50)
        # Supposed to normalize to height 1 before I feed in?
        n = [0.03 * d / max(n) for d in n]
        #print 'n', n
        #print 'bins', len(bins), bins
        # patches <a list of 50 Patch objects>
        #print 'patches', patches
        #sys.exit(1)
        x = np.array([(b + a) / 2. for a, b in zip(bins, bins[1:])])
        y_real = n
        if len(x) != len(y_real):
            raise GridCapFailed("state mismatch")
        
        def norm(x, mean, sd):
            norm = []
            for i in range(x.size):
                norm += [1.0/(sd*np.sqrt(2*np.pi))*np.exp(-(x[i] - mean)**2/(2*sd**2))]
            return np.array(norm)

        p = [clusters[0], clusters[1] - clusters[0], 15, 15, 1.0]
        m, dm, sd1, sd2, sc2 = p
        y_init = norm(x, m, sd1) + sc2 * norm(x, m + dm, sd2)

        resi = [0]
        def res(p, y, x):
            verbose = 0
            if verbose:
                print
                print 'res'
                print '  y: %s' % y
                print '  x: %s' % x
                print '  p: %s' % p
            m, dm, sd1, sd2, sc2 = p
            m1 = m
            m2 = m1 + dm
            if verbose:
                print '   m1 : %s' % m1
                print '   m2 : %s' % m2
                print '   sd1 : %s' % sd1
                print '   sd2 : %s' % sd2
                print '   sc2 : %s' % sc2
            y_fit = norm(x, m1, sd1) + sc2 * norm(x, m2, sd2)
            err = y - y_fit
            if verbose:
                print '  err: %s' % err
            err2 = sum([e**2 for e in err])
            if verbose:
                print '    errsum %s' % err2
            resi[0] += 1
            
            if debug and verbose:
                matplotlib.pyplot.clf()
                plt.subplot(311)
                plt.plot(x, y_real)
                plt.subplot(312)
                plt.plot(x, y_fit)
                plt.subplot(313)
                plt.plot(x, err, label='Error: %s' % err2)
                pylab.savefig(os.path.join('steps', '%03d' % resi[0]))
            
            return err

        # The actual optimizer
        # http://docs.scipy.org/doc/scipy-0.15.1/reference/generated/scipy.optimize.leastsq.html
        #(xres, cov_x, infodict, mesg, ier) = leastsq(res, p, args = (y_real, x))
        (xres, cov_x) = leastsq(res, p, args = (y_real, x))
        #print help(leastsq)
        print 'xres', xres
        print 'cov_x', cov_x
        
        #if not ier in (1, 2, 3, 4):
        #    raise Exception("Failed w/ msg: %s" % (mesg,))
        
        g1_u = xres[0]
        g1_std = xres[2]
        g2_u = xres[0] + xres[1]
        g2_std = xres[3]
        print 'Calc 1'
        print '  u: %s' % g1_u
        print '  std: %s' % g1_std
        print 'Calc 2'
        print '  u: %s' % (g2_u,)
        print '  std: %s' % g2_std

        y_est = norm(x, g1_u, g1_std) + norm(x, g2_u, g2_std)

        if debug:
            matplotlib.pyplot.clf()
            plt.plot(x, y_real,         label='Real Data')
            self.sstep += 1
            pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_real.png' % (self.step, self.sstep)))
        
        if debug:
            matplotlib.pyplot.clf()
            plt.plot(x, y_init, 'r.',   label='Starting Guess')
            self.sstep += 1
            pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_start.png' % (self.step, self.sstep)))
        
        if debug:
            matplotlib.pyplot.clf()
            plt.plot(x, y_est, 'g.',    label='Fitted')
            self.sstep += 1
            pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_fitted.png' % (self.step, self.sstep)))
       
        
        self.threshl = g1_u + 3 * g1_std
        self.threshh = g2_u - 3 * g2_std
        print 'Thresholds'
        print '  Void:  %s' % self.threshl
        print '  Metal: %s' % self.threshh
        print '  Flagz: %s' % (self.threshh - self.threshl,)
        if self.threshl >= self.threshh:
            raise GridCapFailed("Thresholds overlap.  Grid not fitted correctly?")

    def bitmap_netstat(self, bitmap, c, r):
        '''
        return dictionary with m and u keys
        each key holds a set with the cols and rows contiguous with start point c, r (including c, r)
        
        This could potentially blow through the stack for large polygons
        If problems optimize
        
        TODO: abort when find certain metal threshold?
        '''
        
        ret = {'m': set(), 'u': set()}
        checked = set()
        
        def check(c, r):
            #print 'check(%d, %d)' % (c, r)
            if (c, r) in checked:
                return
            this = bitmap.get((c, r), None)
            # Out of bounds?
            if this is None:
                return
            checked.add((c, r))
            # Void?  We are off the polygon: stop looking
            if this == 'v':
                return
            
            # got something
            ret[this].add((c, r))
            
            check(c - 1, r)
            check(c + 1, r)
            check(c, r - 1)
            check(c, r + 1)
        
        check(c, r)
        return ret

    def capture(self):
        # make initial guesses based on thresholds

        print 'capture_seed()'

        def gen_bitmap(threshl, threshh):
            bitmap = {}
            unk_open = set()
            for (c, r) in self.cr():
                thresh = self.means_rc[(c, r)]
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

        print 'Initial counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))
        if debug:
            self.sstep += 1
            self.bitmap_save(bitmap, os.path.join(self.outdir, 's%02d-%02d_bitmap_init.png' % (self.step, self.sstep)))

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
        
        '''
        Remove any segments that are composed of only unknown and 0-1 positive matches
        '''
        def filt_unk_groups(bitmap, unk_open):
            to_remove = set()
            checked = set()
            for c, r in set(unk_open):
                if (c, r) in checked:
                    continue
                
                bins = self.bitmap_netstat(bitmap, c, r)
                checked = checked.union(bins['u'])
                if len(bins['m']) <= 1:
                    print '  Unknown %dc, %dr rm: %d unknowns, %d metal' % (c, r, len(bins['u']), len(bins['m']))
                    to_remove = to_remove.union(bins['u'])
                    to_remove = to_remove.union(bins['m'])
            
            for cr in to_remove:
                bitmap[cr] = 'v'
                unk_open.discard(cr)
                
        #filt_unk_lone(bitmap, unk_open)
        filt_unk_groups(bitmap, unk_open)
        print 'Post-lone counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))
        if debug:
            self.sstep += 1
            self.bitmap_save(bitmap, os.path.join(self.outdir, 's%02d-%02d_lone.png' % (self.step, self.sstep)))

        print

        '''
        If a single unknown is on a contiguous strip of metal its likely a via has distorted it
        Note: this will ocassionally cause garbage to incorrectly merge nets
        '''
        def munge_unk_cont(bitmap, unk_open):
            # Don't propagate
            # Make a list and apply it after the sweep
            to_promote = set()
            for c, r in set(unk_open):
                # Abort if any adjacent unknowns
                if has_around(bitmap, c, r, 'u', order=1):
                    continue
                # Is there surrounding metal forming a line? (or solid)
                if not has_around(bitmap, c, r, 'm', order=2):
                    continue
                print '  Unknown %dc, %dr => m: join m' % (c, r)
                to_promote.add((c, r))
            for (c, r) in to_promote:
                bitmap[(c, r)] = 'm'
                unk_open.discard((c, r))
                    
        print 'Merging contiguous statements'
        munge_unk_cont(bitmap, unk_open)
        print 'Post contiguous counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))
        if debug:
            self.sstep += 1
            self.bitmap_save(bitmap, os.path.join(self.outdir, 's%02d-%02d_contiguous.png' % (self.step, self.sstep)))
        
        print
        
        '''
        Try to propagate using more aggressive threshold after initial truth is created that we are pretty confident in
        Any warnings in aggressive adjacent to metal in baseline are taken as truth
        '''
        print 'prop_ag()'
        def prop_ag(bitmap, bitmap_ag):
            to_promote = set()
            for c, r in self.cr():
                # Skip if nothing is there
                if bitmap_ag[(c, r)] == 'v':
                    continue
                # Do we already think something is there?
                if bitmap[(c, r)] == 'm':
                    continue
                # Is there something to extend?
                if not has_around(bitmap, c, r, 'm', order=2):
                    continue
                print '  %dc, %dr => m: join m' % (c, r)
                to_promote.add((c, r))
            for (c, r) in to_promote:
                bitmap[(c, r)] = 'm'
                unk_open.discard((c, r))
            
        # FIXME: look into ways to make this more dynamic
        # above 10 generated false positives
        # below 9 lost one of the fixes
        # keep at 9 for now as it stil has some margin
        bitmap_ag, _unk_open = gen_bitmap(self.threshl - 9, self.threshh)
        if debug:
            self.sstep += 1
            self.bitmap_save(bitmap_ag, os.path.join(self.outdir, 's%02d-%02d_aggressive.png' % (self.step, self.sstep)))
        prop_ag(bitmap, bitmap_ag)
        print 'Aggressive counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))
        if debug:
            self.sstep += 1
            self.bitmap_save(bitmap, os.path.join(self.outdir, 's%02d-%02d_post_aggressive.png' % (self.step, self.sstep)))
        
        print
        print 'Final counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))

        self.bitmap = bitmap

    def save(self):
        self.png_fn = os.path.join(self.outdir, 'out.png')
        im = Image.new("RGB", self.crs, "white")
        draw = ImageDraw.Draw(im)
        bitmap2fill = {
                'v':'white',
                'm':'blue',
                'u':'orange',
                }
        for (c, r) in self.cr():
            draw.rectangle((c, r, c, r), fill=bitmap2fill[self.bitmap[(c, r)]])
        im.save(self.png_fn)
        
    def save_json(self, pass_):
        # Critical parameters needed to fixup errors
        axes = []
        
        png_fn = None
        if self.png_fn:
            png_fn = os.path.basename(self.png_fn)
        
        img_orig = None
        if self.copy_fn:
            img_orig = os.path.basename(self.copy_fn)
        
        img = None
        if self.preproc_fn:
            img = os.path.basename(self.preproc_fn)
        
        j = {
            'pass': pass_,
            'img_src': self.fn,
            # Original image
            # this may be used for aligning tiles
            'img_orig': img_orig,
            # The image that coordinate parameters fit to
            'img': img,
            'png': png_fn,
            'axes': axes,
            'calc_straighten_angle': self.calc_straighten_angle,
            'straighten_angle': self.straighten_angle,
            'params': self.paramsj,
        }
        for order in xrange(2):
            if self.xy_mb[order] is None:
                m = None
                b = None
            else:
                m, b = self.xy_mb[order]
            
            if self.crs is None:
                crs = None
            else:
                crs = self.crs[order]
            
            ja = {
                # number of rows/cols
                'n': crs,
                # pixels per row/col
                'm': m,
                # row/col offset
                'b': b,
            }
            axes.append(ja)
        js = json.dumps(j, sort_keys=True, indent=4, separators=(',', ': '))
        open(os.path.join(self.outdir, 'out.json'), 'w').write(js)

    def bitmap_save(self, bitmap, fn):
        #im = self.preproc_im.copy()
        im = Image.new("RGB", (int(self.crs[0] * self.xy_mb[0][0]), int(self.crs[1] * self.xy_mb[1][0])), "white")
        draw = ImageDraw.Draw(im)
        bitmap2fill = {
                'v':'black',
                'm':'blue',
                'u':'orange',
                }
        for ((x0, y0), (x1, y1)), (c, r) in self.xy_cr(False):
            draw.rectangle((x0, y0, x1, y1), fill=bitmap2fill[bitmap[(c, r)]])
        im.save(fn)
        
        self.bitmap_verify(bitmap)

    def bitmap_verify(self, bitmap):
        for (c, r) in bitmap:
            if c >= self.crs[0] or r >= self.crs[1]:
                raise Exception("Got c=%d, r=%d w/ global cs=%d, rs=%d" % (c, r, self.crs[0], self.crs[1]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grid auto-bitmap test')
    parser.add_argument('--angle', help='Correct specified rotation instead of auto-rotating (degrees)')
    add_bool_arg(parser, '--debug', default=True)
    parser.add_argument('--channel', default='g', help='Which color channel to use for histograms (rgbu).  u: gray')
    parser.add_argument('--m-est')
    parser.add_argument('fn_in', help='image file to process')
    args = parser.parse_args()

    debug = args.debug

    gc = GridCap(args.fn_in, os.path.splitext(args.fn_in)[0])
    gc.channel = args.channel
    if args.angle is not None:
        gc.straighten_angle = float(args.angle)
    if args.m_est is not None:
        gc.m_est = float(args.m_est)
        if gc.m_est <= 0.0:
            raise Exception('Bad m estimate')
    gc.run()
