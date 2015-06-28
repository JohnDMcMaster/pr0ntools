#!/usr/bin/env python

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
import ast
from scipy.cluster.vq import kmeans,vq
import numpy as np
import pylab as py

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

parser = argparse.ArgumentParser(description='CV test')
parser.add_argument('fn_in', nargs='?', default='sample.png', help='image file to process')
args = parser.parse_args()

fn_in = args.fn_in
#outdir = os.path.splitext(args.fn_in)[0]
outdir = '01_grid_autothresh'
if not os.path.exists(outdir):
    os.mkdir(outdir)
gridp = 14.44

if 0:
    im = Image.open(fn_in)

    print '%s: %dw x %dh' % (fn_in, im.size[0], im.size[1])
    print 'Grid pixel w/h: %s' % gridp
    im = im.crop((9, 9, im.size[0], im.size[1]))
    print 'crop: %dw x %dh' % (im.size[0], im.size[1])

    '''
    image mean
    [57.06916963894625, 112.62541678958048, 86.42082651720347, 255.0]
    '''
    print 'stat()'
    means = {'r': [], 'g': [],'b': [],'u': []}
    for y in drange(0, im.size[1], gridp):
        y = int(y)
        for x in drange(0, im.size[0], gridp):
            x = int(x)
            
            # TODO: look into using mask
            # I suspect this is faster
            imxy = im.crop((x, y, x + int(gridp), y + int(gridp)))
            mean = ImageStat.Stat(imxy).mean
            mmean = sum(mean[0:3])/3.0
            means['r'].append(mean[0])
            means['g'].append(mean[1])
            means['b'].append(mean[2])
            means['u'].append(mmean)
            #print 'x%0.4d y%0.4d:     % 8.3f % 8.3f % 8.3f % 8.3f % 8.3f' % (x, y, mean[0], mean[1], mean[2], mean[3], mmean)

    for c, d in means.iteritems():
        open(os.path.join(outdir, 'stat_%s.txt' % c), 'w').write(repr(d))
        matplotlib.pyplot.clf()
        #pylab.plot(h,fit,'-o')
        pylab.hist(d, bins=50)
        #pylab.save(os.path.join(outdir, 'stat_%s.png' % c))
        pylab.savefig(os.path.join(outdir, 'stat_%s.png' % c))


# Extract clusters
if 0:
    data2 = ast.literal_eval(open(os.path.join(outdir, 'stat_u.txt')).read())
    data2_np = np.array(data2)
    
    clusters = 2
    # computing K-Means with K = 2 (2 clusters)
    centroids,_ = kmeans(data2_np, clusters)
    centroids_sort = sorted(centroids)
    print centroids_sort
    # assign each sample to a cluster
    idx,_ = vq(data2_np, centroids)

'''
http://worldofpiggy.com/2015/02/18/expectation-maximization-in-action-and-some-python-code/
Manual least squares regression
'''
if 0:
    data2 = ast.literal_eval(open(os.path.join(outdir, 'stat_u.txt')).read())
    data2_np = np.array(data2)
    s = data2_np
    # From above
    clusters = [51.622280044093074, 150.84357233459423]


    def pdf_model(x, p):
        print
        print 'pdf_model()'
        print '  x=%s' % x
        print '  p=%s' % (p,)
        mu1, sig1, mu2, sig2, pi_1 = p
        print '  mu1:  %s' % mu1
        print '  sig1: %s' % sig1
        print '  mu2:  %s' % mu2
        print '  sig2: %s' % sig2
        print '  pi_1: %s' % pi_1
        raw1 = py.normpdf(x, mu1, sig1)
        print '  raw1: %s' % raw1
        raw2 = py.normpdf(x, mu2, sig2)
        print '  raw2: %s' % raw2
        ret = pi_1 * raw1 + (1 - pi_1) * raw2
        print '  ret: %s' % ret
        print
        return ret
    
    # Initial guess of parameters and initializations
    #p0 = np.array([clusters[0], 0.2, clusters[1], 0.2, 0.5])
    p0 = np.array([-0.2, 0.2, 0.8, 0.2, 0.5])
    mu1, sig1, mu2, sig2, pi_1 = p0
    mu = np.array([mu1, mu2]) # estimated means
    sig = np.array([sig1, sig2]) # estimated std dev
    pi_ = np.array([pi_1, 1-pi_1]) # mixture parameter
     
    gamma = np.zeros((2, s.size))
    N_ = np.zeros(2)
    p_new = p0
     
    # EM we start here
    delta = 0.000001
    improvement = float('inf')
     
    counter = 0
     
    while (improvement>delta):
        # Compute the responsibility func. and new parameters
        for k in [0,1]:
            pm = pdf_model(s, p_new)
            print len(pm), pm
            gamma[k,:] = pi_[k] * py.normpdf(s, mu[k], sig[k]) / pm   # responsibility
            
            N_[k] = 1.*gamma[k].sum() # effective number of objects to k category
            mu[k] = sum(gamma[k]*s)/N_[k] # new sample mean of k category
            sig[k] = np.sqrt( sum(gamma[k]*(s-mu[k])**2)/N_[k] ) # new sample var of k category
            pi_[k] = N_[k]/s.size # new mixture param of k category
            # updated parameters will be passed at next iter
            p_old = p_new
            p_new = [mu[0], sig[0], mu[1], sig[1], pi_[0]]
            # check convergence
            improvement = max(abs(p_old[0] - p_new[0]), abs(p_old[1] - p_new[1]) )
            counter += 1
     
    print "Means: %6.3f %6.3f" % (p_new[0], p_new[2])
    print "Std dev: %6.3f %6.3f" % (p_new[1], p_new[3])
    print "Mix (1): %6.3f " % p_new[4]
    print "Total iterations %d" % counter
    print pi_.sum(), N_.sum()










'''
Automatic least squares regression using leastsq
Took snippets from: http://stackoverflow.com/questions/10143905/python-two-curve-gaussian-fitting-with-non-linear-least-squares
Insufficient for me though: my peaks are non-uniform size
Therefore added height value to seocnd peak
Since what I ultimately need is just x values, normalize distributions
'''
if 1:
    from scipy.optimize import leastsq
    import matplotlib.pyplot as plt
    
    data2 = ast.literal_eval(open(os.path.join(outdir, 'stat_u.txt')).read())
    data2_np = np.array(data2)
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
    clusters = [51.622280044093074, 150.84357233459423]
    print 'Clusters'
    print '  1: %s' % clusters[0]
    print '  2: %s' % clusters[1]

    #  The return value is a tuple (n, bins, patches)
    (n, bins, patches) = pylab.hist(data2_np, bins=50)
    # Hmm so I think I'm supposed to normalize to height 1 before I feed in
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
    
    if 0:
        print 'Bins'
        for i, b in enumerate(bins):
            if i > 10:
                break
            print '  %s' % (b,)
        print 'Vals'
        for i, (x, y) in enumerate(zip(x, y_real)):
            if i > 10:
                break
            print '  x: %s, y: %s' % (x, y)
        sys.exit(1)
        

    
    def norm(x, mean, sd):
      norm = []
      for i in range(x.size):
        norm += [1.0/(sd*np.sqrt(2*np.pi))*np.exp(-(x[i] - mean)**2/(2*sd**2))]
      return np.array(norm)

    #m, dm, sd1, sd2 = [5, 10, 1, 1]
    m, dm, sd1, sd2, sc2 = [clusters[0], clusters[1] - clusters[0], 15, 15, 1.0]
    p = [m, dm, sd1, sd2, sc2] # Initial guesses for leastsq
    y_init = norm(x, m, sd1) + sc2 * norm(x, m + dm, sd2) # For final comparison plot

    resi = [0]
    def res(p, y, x):
        print
        print 'res'
        print '  y: %s' % y
        print '  x: %s' % x
        print '  p: %s' % p
        m, dm, sd1, sd2, sc2 = p
        m1 = m
        m2 = m1 + dm
        print '   m1 : %s' % m1
        print '   m2 : %s' % m2
        print '   sd1 : %s' % sd1
        print '   sd2 : %s' % sd2
        print '   sc2 : %s' % sc2
        y_fit = norm(x, m1, sd1) + sc2 * norm(x, m2, sd2)
        err = y - y_fit
        print '  err: %s' % err
        err2 = sum([e**2 for e in err])
        print '    errsum %s' % err2
        resi[0] += 1
        
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
    
    print 'Calc 1'
    print '  u: %s' % xres[0]
    print '  std: %s' % xres[2]
    print 'Calc 2'
    print '  u: %s' % (xres[0] + xres[1],)
    print '  std: %s' % xres[3]

    y_est = norm(x, xres[0], xres[2]) + norm(x, xres[0] + xres[1], xres[3])

    matplotlib.pyplot.clf()
    plt.plot(x, y_real,         label='Real Data')
    pylab.savefig(os.path.join(outdir, '01_real'))
    
    matplotlib.pyplot.clf()
    plt.plot(x, y_init, 'r.',   label='Starting Guess')
    pylab.savefig(os.path.join(outdir, '02_start'))
    
    matplotlib.pyplot.clf()
    plt.plot(x, y_est, 'g.',    label='Fitted')
    pylab.savefig(os.path.join(outdir, '03_fitted'))
    
    #plt.legend()
    #plt.show()
    
    



