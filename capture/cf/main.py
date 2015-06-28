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
        # rotated and cropped
        self.preproc_fn = None
        self.preproc_im = None
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
        self.rows = None
        self.cols = None
        
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
        self.step = 0
        self.sstep = 0
        
        # Straighten, cropping image slightly
        self.step += 1
        self.straighten()

        # Find grid
        self.step += 1
        self.gridify()

        # Figure out thresholds based on grid
        self.step += 1
        self.autothresh()

        # Use computed thresholds on grid to guess materials
        self.step += 1
        self.capture()

    def straighten(self):
        self.sstep = 0

        img = cv2.imread(self.fn)
        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_orig.png' % (self.step, self.sstep)), img)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_cvtColor.png' % (self.step, self.sstep)), gray)
        
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_canny.png' % (self.step, self.sstep)), edges)

        lines = cv2.HoughLines(edges, 1, np.pi/1800., 400)
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
            
            theta = theta * 180. / np.pi
            # take out outliers
            # I usually snap to < 1.5 (tyipcally < 0.2) so this should be plenty of margin
            if theta < 3.0:
                #print 'Theta: %g, rho: %g' % (theta, rho)
                thetas_keep.append(theta)
                cv2.line(img, (x1,y1),(x2,y2),(0, 0, 255),2)
            else:
                cv2.line(img, (x1,y1),(x2,y2),(0, 255, 0),2)

        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_lines.png' % (self.step, self.sstep)), img)

        matplotlib.pyplot.clf()
        pylab.hist(thetas_keep, bins=100)
        self.sstep += 1
        pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_dist.png' % (self.step, self.sstep)))
        
        angle = sum(d) / len(d)
        print 'Mean angle: %f' % (angle,)

        im = Image.open(self.fn)
        im = im.rotate(angle, resample=Image.BICUBIC)
        self.sstep += 1
        im.save(os.path.join(self.outdir, 's%02d-%02d_rotate.png' % (self.step, self.sstep)))
        
        imw, imh = im.size
        sy = abs(imw * math.sin(angle))
        sx = abs(imh * math.cos(angle))
        im_crop = im.crop((sx, sy, imw - sx, imh - sy)

        self.sstep += 1
        self.preproc_fn = self.outdir, 's%02d-%02d_shrink.png' % (self.step, self.sstep))
        self.preproc_im = im_crop
        im_crop.save(os.path.join(self.outdir, 's%02d-%02d_crop.png' % (self.step, self.sstep)))

    def gridify(self):
        img = cv2.imread(self.preproc_fn)
        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_orig.png' % (self.step, self.sstep)), img)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_cvtColor.png' % (self.step, self.sstep)), gray)
        
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_canny.png' % (self.step, self.sstep)), edges)

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
                cv2.line(img, (x1,y1),(x2,y2),(0, 0, 255),2)
            elif theta > np.pi/2 - d and theta < np.pi/2 + d or theta > 3 * np.pi / 2 - d and theta < 3 * np.pi / 2 + d:
                y0s.append(abs(rho))
            else:
                cv2.line(img, (x1,y1),(x2,y2),(0, 255, 0),2)
                continue

        self.sstep += 1
        cv2.imwrite(os.path.join(self.outdir, 's%02d-%02d_lines.png' % (self.step, self.sstep)), img)

        x0sd_all = []
        x0sd_roi = []
        # Sweep over all line pairs, generating set of all line distances
        for i in xrange(len(x0s)):
            for j in xrange(i):
                d = abs(x0s[i] - x0s[j])
                x0sd_all.append(d)
                if d < self.clust_thresh:
                    x0sd_roi.append(d)
        print 'x0s: %d' % len(x0s)

        
        # attempt to auto-cluster
        # try to find the largest clusters along the same level of detail
        
        matplotlib.pyplot.clf()
        pylab.hist(x0sd_all, bins=100)
        self.sstep += 1
        pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_tresh_all.png' % (self.step, self.sstep)), img)

        matplotlib.pyplot.clf()
        pylab.hist(x0sd_roi, bins=100)
        self.sstep += 1
        pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_tresh_roi.png' % (self.step, self.sstep)), img)


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
            print 'Errors'
            for v, i in zip(data2_np, idx):
                #print '  %s, %s' % (v, centroids[i])
                errs.append((v - centroids[i]) ** 2)
            err = sum(errs) / len(errs)
            print 'RMS error: %s' % (err,)
            clustersm[clusters] = err
            
            centroidsd = [b - a for a, b in zip(centroids_sort, centroids_sort[1:])]
            avg = 1.0 * sum(centroidsd) / len(centroidsd)
            clustersm_d[clusters] = avg
            print 'Centroidsd (%s)' % avg
            errs = []
            for c in centroidsd:
                e = (c - avg) ** 2
                print '  %s => %s' % (c, e)
                errs.append(e)
            err = sum(errs) / len(errs)
            clustersm_c[clusters] = err
            print 'Derritive error: %s' % err
            
            
        print clustersm
        print clustersm_c
        
        print
        print
        print
        clust_opt = min(clustersm_c, key=clustersm_c.get)
        print 'Optimal cluster size: %s' % clust_opt
        cluster_d = clustersm_d[cluster_opt]
        print 'Cluster pitch: %s' % cluster_d
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
        Now that we know the line pitch need to fit it back to the original x and y data
        Pitch is known, just play with offsets
        Try to snap points to offset and calculate the error
        
        Calcualte regression on pixels to get row/col pixel offset for grid lines
        xline = col * m + b
        '''
        points = sorted(x0s)
        
        m = cluster_d
        def res(p, points):
            (b,) = p
            err = []
            for x in points:
                xd = (x - b) / m
                err.append(xd % 1)
            return err
        
        imw, imh = self.preproc_im.size
        
        (xres, cov_x) = leastsq(res, [m/2], args=(x0s,))
        print 'Optimal X offset: %s' % xres[0]
        grid_xlin = (cluster_d, xres[0])
        self.cols = int((imw - grid_xlin[1])/grid_xlin[0])
        
        (yres, cov_y) = leastsq(res, [m/2], args=(y0s,))
        print 'Optimal Y offset: %s' % yres[0]
        grid_ylin = (cluster_d, yres[0])
        self.rows = int((imh - grid_ylin[1])/grid_ylin[0])
        
        self.grid_lins = (grid_xlin, grid_ylin)
        
        self.dbg_grid()
        
    def dbg_grid(self):
        '''Draw a grid onto the image to see that it lines up'''
        im = self.preproc_im.copy()
        draw = ImageDraw.Draw(im)
        # +1: draw right bounding box
        for c in xrange(self.cols + 1):
            (m, b) = self.grid_lins[0]
            x = int(m * c + b)
            draw.line((x, 0, x, im.size[1]), fill=128)
        for c in xrange(self.rows + 1):
            (m, b) = self.grid_lins[1]
            y = int(m * r + b)
            draw.line((0, y, im.size[0], y), fill=128)
        del draw
        self.sstep += 1
        im.save(os.path.join(self.outdir, 's%02d-%02d_grid.png' % (self.step, self.sstep))
        del im









    def cr(self):
        for c in xrange(self.cols + 1):
            for r in xrange(self.rows + 1):
                yield (c, r)

    def xy(self):
        '''Generate (x0, y0) upper left and (x1, y1) lower right (inclusive) tile coordinates'''
        for c in xrange(self.cols + 1):
            (xm, xb) = self.grid_lins[0]
            x = int(xm * c + xb)
            for r in xrange(self.rows + 1):
                (ym, yb) = self.grid_lins[1]
                y = int(ym * r + yb)
                yield (x, y), (x + xm, y + ym)

    def xy_cr(self):
        for c in xrange(self.cols + 1):
            (xm, xb) = self.grid_lins[0]
            x = int(xm * c + xb)
            for r in xrange(self.rows + 1):
                (ym, yb) = self.grid_lins[1]
                y = int(ym * r + yb)
                yield ((x, y), (x + xm, y + ym)), (c, r)

    def autothresh(self):
        print 'stat()'
        means = {'r': [], 'g': [],'b': [],'u': []}
        self.means_rc = {}
        
        for ((x0, x1), (x1, y1)), (c, r) in self.xy_cr():
            # TODO: look into using mask
            # I suspect this is faster though
            imxy = im.crop((x0, y0, x1, y1))
            mean = ImageStat.Stat(imxy).mean
            mmean = sum(mean[0:3])/3.0
            means['r'].append(mean[0])
            means['g'].append(mean[1])
            means['b'].append(mean[2])
            means['u'].append(mmean)
            self.means_rc[(c, r)] = mmean
            #print 'x%0.4d y%0.4d:     % 8.3f % 8.3f % 8.3f % 8.3f % 8.3f' % (x, y, mean[0], mean[1], mean[2], mean[3], mmean)

        for c, d in means.iteritems():
            open(os.path.join(outdir, 'stat_%s.txt' % c), 'w').write(repr(d))
            matplotlib.pyplot.clf()
            #pylab.plot(h,fit,'-o')
            pylab.hist(d, bins=50)
            self.sstep += 1
            pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_stat_%c.png' % (self.step, self.sstep, c)))
    
        data2 = means['u']
        data2_np = np.array(data2)




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




        s = data2_np
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
        (n, bins, patches) = pylab.hist(data2_np, bins=50)
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
            raise Exception("state mismatch")
        
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
            
            if verbose:
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

        matplotlib.pyplot.clf()
        plt.plot(x, y_real,         label='Real Data')
        self.sstep += 1
        pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_real.png' % (self.step, self.sstep))
        
        matplotlib.pyplot.clf()
        plt.plot(x, y_init, 'r.',   label='Starting Guess')
        self.sstep += 1
        pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_start.png' % (self.step, self.sstep))
        
        matplotlib.pyplot.clf()
        plt.plot(x, y_est, 'g.',    label='Fitted')
        self.sstep += 1
        pylab.savefig(os.path.join(self.outdir, 's%02d-%02d_fitted.png' % (self.step, self.sstep))
       
        
        self.threshl = g1_ + 3 * gl_std
        self.threshh = g2_ - 3 * g2_std
        print 'Thresholds'
        print '  Void:  %s' % self.threshl
        print '  Metal: %s' % self.threshh
        print '  Flagz: %s' % (self.threshh - self.threshl,)
        if self.threshl >= self.threshh:
            raise Exception("State mismatch")





    def capture(self):
        # make initial guesses based on thresholds

        print 'capture_seed()'

        bitmap = {}
        for (c, r) in self.cr():
            thresh = self.means_rc[(c, r)]
            # The void
            if thresh <= self.threshl:
                bitmap[(c, r)] = 'v'
            # Pretty metal
            elif thresh >= self.threshh:
                bitmap[(c, r)] = 'm'
            # WTFBBQ
            else:
                bitmap[(c, r)] = 'u'




        print 'Initial counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))
        self.sstep += 1
        bitmap_save(bitmap, os.path.join(self.outdir, 's%02d-%02d_bitmap_init.png' % (self.step, self.sstep)))

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
        print 'Post-lone counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))
        self.sstep += 1
        bitmap_save(bitmap, os.path.join(self.outdir, 's%02d-%02d_lone.png' % (self.step, self.sstep)))

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
        print 'Post contiguous counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))
        self.sstep += 1
        bitmap_save(bitmap, os.path.join(self.outdir, 's%02d-%02d_contiguous.png' % (self.step, self.sstep)))
        
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
        self.sstep += 1
        bitmap_save(bitmap_ag, os.path.join(self.outdir, 'viz_drc_04-1_ag.png'))
        prop_ag(bitmap, bitmap_ag)
        print 'Aggressive counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))
        self.sstep += 1
        bitmap_save(bitmap, os.path.join(self.outdir, 's%02d-%02d_aggressive.png' % (self.step, self.sstep)))
        
        print
        print 'Final counts'
        for c in 'mvu':
            print '  %s: %d' % (c, len(filter(lambda k: k == c, bitmap.values())))



    def bitmap_save(self, bitmap, fn):
        viz = self.preproc_im.copy()
        draw = ImageDraw.Draw(viz)
        bitmap2fill = {
                'v':'black',
                'm':'blue',
                'u':'orange',
                }
        for ((x0, x1), (x1, y1)), (c, r) in self.xy_cr():
            draw.rectangle((x0, y0, x1, y1), fill=bitmap2fill[bitmap[(c, r)])
        viz.save(fn)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grid auto-bitmap test')
    parser.add_argument('fn_in', help='image file to process')
    args = parser.parse_args()

    outdir = os.path.splitext(args.fn_in)[0]
    if not os.path.exists(outdir):
        os.mkdir(outdir)

