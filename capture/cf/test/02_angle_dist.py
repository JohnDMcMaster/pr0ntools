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
    parser.add_argument('fns_in', nargs='+', help='image file to process')
    args = parser.parse_args()

    outdir = os.path.splitext(args.fn_in)[0]
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    # graph theta distribution
    '''
    1 degree was too course
    0.1 degree seems okay
    
    200 points produced bad result but 400 seems to be pretty good
    '''
    pop = []
    for fn in args.fns_in:
        img = cv2.imread(fn)
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
            pop.append(angle)

    matplotlib.pyplot.clf()
    pylab.hist(pop, bins=100)
    pylab.savefig('theta_dist_pop.png')

