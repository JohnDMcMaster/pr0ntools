import cv2
import numpy as np
import argparse
import pylab
import matplotlib
import os
from collections import Counter
from PIL import Image, ImageDraw, ImageStat
from scipy import fftpack

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
    if 1:
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
        angle2 = 1
        im = Image.open(args.fn_in)
        im = im.rotate(angle2)
        F1 = fftpack.fft2(im)
        print F1


