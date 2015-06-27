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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CV test')
    parser.add_argument('fn_in', help='image file to process')
    args = parser.parse_args()

    outdir = os.path.splitext(args.fn_in)[0]
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
        edges = cv2.Canny(gray,50,150,apertureSize = 3)

        x0s = []
        y0s = []

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
            
            #x0s.append(x0)
            #y0s.append(y0)
            # now assume that since lines are nearly vertical x0s is just the straight value (ie assume sin(x) = x)
            if 1 or rho > -100 and rho < 100:
                if 1 or linei < 3:
                    # because we are on border, some are slightly below 0 and underflow to slightly below pi
                    # rather than having negative angles rho goes negative
                    x0s.append(abs(rho))
                
                    print rho, theta
                    print '  ', x0, y0
                    print '  ', x1, y1, x2, y2
                    #cv2.line(img,(x1,y1),(x2,y2),(random.randint(0, 255),random.randint(0, 255),random.randint(0, 255)),2)
                    cv2.line(img,(x1,y1),(x2,y2),(0, 0, 255),2)
                linei += 1

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

    if 0:
        angle2 = 1
        im = Image.open(args.fn_in)
        im = im.rotate(angle2)
        F1 = fftpack.fft2(im)
        print F1




    if 1:
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
        



