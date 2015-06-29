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
import matplotlib.pyplot as plt
import sys
from scipy.optimize import leastsq

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CV test')
    parser.add_argument('fn_in', help='image file to process')
    args = parser.parse_args()

    outdir = '02_angle'
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    if 0:
        img = cv2.imread(args.fn_in)
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray,50,150,apertureSize = 3)

        lines = cv2.HoughLines(edges,1,np.pi/1800,400)
        for rho,theta in lines[0]:
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a*rho
            y0 = b*rho
            x1 = int(x0 + 1000*(-b))
            y1 = int(y0 + 1000*(a))
            x2 = int(x0 - 1000*(-b))
            y2 = int(y0 - 1000*(a))

            cv2.line(img,(x1,y1),(x2,y2),(0,0,255),2)

        cv2.imwrite(os.path.join(outdir, 'houghlines3_hi.jpg'),img)

    if 0:
        img = cv2.imread(args.fn_in)
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray,50,150,apertureSize = 3)
        minLineLength = 100
        maxLineGap = 10
        # TypeError: <unknown> is not a numpy array
        lines = cv2.HoughLinesP(edges,1,np.pi/180,100,minLineLength,maxLineGap)
        for x1,y1,x2,y2 in lines[0]:
            cv2.line(img,(x1,y1),(x2,y2),(0,255,0),2)

        cv2.imwrite('houghlines5.jpg',img)

    # graph theta distribution
    '''
    1 degree was too course
    0.1 degree seems okay
    
    200 points produced bad result but 400 seems to be pretty good
    '''
    if 0:
        img = cv2.imread(args.fn_in)
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray,50,150,apertureSize = 3)

        lines = cv2.HoughLines(edges,1,np.pi/1800.,400)
        d = []
        for rho,theta in lines[0]:
            theta = theta * 180. / np.pi
            # take out outliers
            # I usually snap to < 1.5 so this should be plenty of margin
            if theta < 3.0:
                #print 'Theta: %g, rho: %g' % (theta, rho)
                d.append(theta)

        matplotlib.pyplot.clf()
        pylab.hist(d, bins=100)
        pylab.savefig(os.path.join(outdir, 'theta_dist_hi.png'))
        
        # from a quick test in gimp
        ideal = 0.94
        # 400 point average
        pre_meas = 0.889583
        
        if 0:
            angle = Counter(d).most_common(1)[0]
            #angle_deg = angle * 180/np.pi
            print 'Most common angle: %f (%d times)' % (angle[0], angle[1])
            angle = angle[0]
        # Off a little but better than original
        if 1:
            angle = sum(d) / len(d)
            print 'Mean angle: %f' % (angle,)

        
        im = Image.open(args.fn_in)
        #im.save(os.path.join(outdir, 'orig.png'))
        im = im.rotate(angle, resample=Image.BICUBIC)
        im.save(os.path.join(outdir, 'rotate_hi.png'))



    if 0:
        img = cv2.imread(args.fn_in)
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        for thresh1 in [1, 10, 100, 250]:
            for thresh2 in [1, 10, 100, 250]:
                print
                print thresh1, thresh2
                # threshold1 - first threshold for the hysteresis procedure.
                # threshold2 - second threshold for the hysteresis procedure.
                edges = cv2.Canny(gray, thresh1, thresh2, apertureSize=3)
        
                x0s = []
                y0s = []
        
                lines = cv2.HoughLines(edges,1,np.pi/1800,400)
                linei = 0
                if lines is None:
                    print 'WARNING: failed'
                    continue
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
                cv2.imwrite(os.path.join(outdir, 'thresh_%03d_%03d.png' % (thresh1, thresh2)),img)
                print 'x0s: %d' % len(x0s)
                if len(x0s) == 0:
                    print "  WARNING: no lines"
                print 'y0s: %d' % len(y0s)
                if len(y0s) == 0:
                    print "  WARNING: no lines"

        import sys
        sys.exit(1)

        x0sd_roi = []
        x0sd_all = []
        for i in xrange(len(x0s)):
            for j in xrange(i):
                d = abs(x0s[i] - x0s[j])
                x0sd_all.append(d)
                if d < 100:
                    x0sd_roi.append(d)
        print 'x0s: %d' % len(x0s)

        matplotlib.pyplot.clf()
        pylab.hist(x0sd_all, bins=100)
        pylab.savefig(os.path.join(outdir, 'rotate_lines_histx_all.png'))

        matplotlib.pyplot.clf()
        pylab.hist(x0sd_roi, bins=100)
        pylab.savefig(os.path.join(outdir, 'rotate_lines_histx_roi.png'))
        
        if 0:
            matplotlib.pyplot.clf()
            pylab.hist(y0sd, bins=100)
            pylab.savefig(os.path.join(outdir, 'rotate_lines_histy.png'))



    if 1:
        print 'writing to %s' % outdir
        img = cv2.imread(args.fn_in)
        print type(img)
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        cv2.imwrite(os.path.join(outdir, 'reduce_01_gray.png'), gray)
        print type(gray)
        edges = cv2.Canny(gray, 125, 250, apertureSize=3)
        cv2.imwrite(os.path.join(outdir, 'reduce_02_edges.png'), edges)
        print type(edges)
        
        print len(edges)
        sums = []
        for row in edges:
            sums.append(np.sum(row))
        matplotlib.pyplot.clf()
        plt.plot(sums)
        pylab.savefig(os.path.join(outdir, 'reduce'))
        
        # Find the highest value and annotate image
        maxes = []
        for i in xrange(5):
            mval = max(sums)
            ymax = sums.index(mval)
            cv2.line(img, (0, ymax), (1527, ymax), (0, 0, 255), 2)
            sums[ymax] = 0.0
        cv2.imwrite(os.path.join(outdir, 'reduce_03_mark.png'), img)


        # {'h': 0, 'o': 0, 'v': 78}
        #lines = cv2.HoughLines(edges, 1, np.pi/1800, 400)
        # {'h': 0, 'o': 0, 'v': 443}
        #lines = cv2.HoughLines(edges, 1, np.pi/1800, 200)
        # {'h': 0, 'o': 0, 'v': 723}
        #lines = cv2.HoughLines(edges, 1, np.pi/1800, 150)
        # {'h': 0, 'o': 0, 'v': 957}
        #lines = cv2.HoughLines(edges, 1, np.pi/1800, 125)
        lines = cv2.HoughLines(edges, 1, np.pi/1800, 115)
        # {'h': 115, 'o': 34, 'v': 1494}
        #lines = cv2.HoughLines(edges, 1, np.pi/1800, 100)
        linei = 0
        lc = {'h':0, 'v':0, 'o': 0}
        for rho,theta in lines[0]:
            # only keep vertical lines for now
            # these will have thetas close to 0 or pi
            d = 0.1

            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho

            scal = 2000
            x1 = int(x0 + scal * -b)
            y1 = int(y0 + scal *  a)
            x2 = int(x0 - scal * -b)
            y2 = int(y0 - scal *  a)

            if theta > 0 - d and theta < 0 + d or theta > np.pi - d and theta < np.pi + d:
                lc['v'] += 1
                #cv2.line(img,(x1,y1),(x2,y2),(0, 255, 0),2)
            elif theta > np.pi/2 - d and theta < np.pi/2 + d or theta > 3 * np.pi / 2 - d and theta < 3 * np.pi / 2 + d:
                print 'hor line'
                cv2.line(img,(x1,y1),(x2,y2),(255, 0, 0),2)
                lc['h'] += 1
            else:
                print 'other line'
                cv2.line(img, (x1,y1),(x2,y2),(255, 255, 0),2)
                lc['o'] += 1

        print lc
        cv2.imwrite(os.path.join(outdir, 'reduce_04_hough.png'), img)
        
        sys.exit(1)
        
    
        #test = cv2.cvtColor(edges)
        test = cv2.cv.GetMat(edges)
        rowr = cv2.reduce(edges, 0, cv2.cv.CV_REDUCE_SUM)
        colr = cv2.reduce(edges, 0, cv2.cv.CV_REDUCE_SUM)
    
        matplotlib.pyplot.clf()
        plt.subplot(211)
        plt.plot(rowr)
        plt.subplot(212)
        plt.plot(colr)
        pylab.savefig(os.path.join(outdir, 'reduce'))
        





        def dbg_grid(im):
            '''Draw a grid onto the image to see that it lines up'''
            im = im.copy()
            draw = ImageDraw.Draw(im)
            # +1: draw right bounding box
            for c in xrange(cols + 1):
                (m, b) = self.grid_lins[0]
                x = int(m * c + b)
                draw.line((x, 0, x, im.size[1]), fill=128)
            for r in xrange(rows + 1):
                (m, b) = self.grid_lins[1]
                y = int(m * r + b)
                draw.line((0, y, im.size[0], y), fill=128)
            del draw
            im.save(os.path.join(outdir, 'reduce_05_grid.png'))
            del im
        
        def gridify_offsets(self, m, x0s, y0s):
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
            
            imw, imh = self.preproc_im.size
            
            print 'X: regressing %d lines' % len(x0s)
            (xres, _cov_x) = leastsq(res, [m/2], args=(x0s,))
            print 'Optimal X offset: %s' % xres[0]
            grid_xlin = (m, xres[0])
            self.cols = int((imw - grid_xlin[1])/grid_xlin[0])
            
            print 'Y: regressing %d lines' % len(y0s)
            (yres, _cov_y) = leastsq(res, [m/2], args=(y0s,))
            print 'Optimal Y offset: %s' % yres[0]
            grid_ylin = (m, yres[0])
            self.rows = int((imh - grid_ylin[1])/grid_ylin[0])
            
            self.grid_lins = (grid_xlin, grid_ylin)
            
            self.dbg_grid()





















    if 0:
        angle2 = 1
        im = Image.open(args.fn_in)
        im = im.rotate(angle2)
        F1 = fftpack.fft2(im)
        print F1







    if 0:
        img = cv2.imread(args.fn_in)
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray,50,150,apertureSize = 3)

        x0s = []

        lines = cv2.HoughLines(edges,1,np.pi/1800,400)
        linei = 0
        for rho,theta in lines[0]:
            # only keep vertical lines for now
            # these will have thetas close to 0 or pi
            d = 0.1
            if not (theta > 0 - d and theta < 0 + d or theta > 3.14 - d and theta < 3.14 + d):
                continue

            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho

            scal = 2000
            x1 = int(x0 + scal * -b)
            y1 = int(y0 + scal *  a)
            x2 = int(x0 - scal * -b)
            y2 = int(y0 - scal *  a)

            # filter out lines at edge (lots of issues due to rotation)
            #if x0 < 40 or y0 < 40:
            #    continue
            
            x0s.append(abs(rho))
            if 0:
                print rho, theta
                print '  ', x0, y0
                print '  ', x1, y1, x2, y2
            cv2.line(img,(x1,y1),(x2,y2),(0, 0, 255),2)

        cv2.imwrite(os.path.join(outdir, 'rotate_lines.jpg'),img)

        x0sd_roi = []
        x0sd_all = []
        for i in xrange(len(x0s)):
            for j in xrange(i):
                d = abs(x0s[i] - x0s[j])
                x0sd_all.append(d)
                if d < 100:
                    x0sd_roi.append(d)
        print 'x0s: %d' % len(x0s)

        
        # attempt to auto-cluster
        # try to find the largest clusters along the same level of detail
        print x0sd_roi
        

        matplotlib.pyplot.clf()
        pylab.hist(x0sd_roi, bins=100)
        pylab.savefig(os.path.join(outdir, 'rotate_lines_histx_roi.png'))
        



