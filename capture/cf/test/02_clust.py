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

'''
(336 - 52) / 10 = 28.4
self.gridp = 14.44
were images rescaled at some point?


86.53488372
1.5
57.18421053
28.18461538
    vs 28.88 used for earlier tests
    probably okay
'''

data2 = [83.0, 57.0, 26.0, 26.0, 1.0, 1.0, 27.0, 1.0, 26.0, 0.0, 27.0, 2.0, 24.0, 3.0, 24.0, 2.0, 85.0, 59.0, 27.0,
        25.0, 58.0, 32.0, 27.0, 24.0, 25.0, 26.0, 27.0, 2.0, 84.0, 1.0, 27.0, 86.0, 59.0, 32.0, 31.0, 83.0, 90.0, 1.0,
        33.0, 82.0, 1.0, 25.0, 84.0, 57.0, 2.0, 2.0, 81.0, 55.0, 4.0, 23.0, 82.0, 80.0, 1.0, 2.0, 2.0, 33.0, 26.0, 1.0,
        1.0, 2.0, 23.0, 25.0, 25.0, 58.0, 31.0, 1.0, 32.0, 32.0, 58.0, 90.0, 31.0, 33.0, 89.0, 56.0, 89.0, 25.0, 58.0,
        27.0, 58.0, 25.0, 83.0, 26.0, 57.0, 31.0, 28.0, 1.0, 58.0, 56.0, 24.0, 89.0, 87.0, 88.0, 55.0, 88.0, 56.0, 33.0,
        34.0, 89.0, 87.0, 32.0, 58.0, 25.0, 1.0, 60.0, 33.0, 26.0, 24.0, 56.0, 57.0, 32.0, 83.0, 57.0, 88.0, 84.0, 57.0,
        81.0, 57.0, 90.0, 32.0, 31.0, 32.0, 91.0, 89.0, 30.0, 2.0, 27.0, 58.0, 25.0, 83.0, 0.0, 58.0, 25.0, 33.0, 88.0,
        87.0, 56.0, 89.0, 57.0, 1.0, 3.0, 93.0, 2.0, 25.0, 24.0, 1.0, 91.0, 2.0, 30.0, 1.0, 32.0, 26.0, 57.0, 58.0, 57.0,
        83.0, 90.0, 0.0, 58.0, 25.0, 93.0, 91.0, 1.0, 89.0, 88.0, 33.0, 1.0, 34.0, 2.0, 54.0, 55.0, 57.0, 33.0, 91.0,
        58.0, 60.0, 58.0, 33.0, 3.0, 80.0, 22.0, 55.0, 80.0]
data2 = sorted(data2)
data2_np = np.array(data2)

if 0:
    outdir = 'c0011_r0000/rotate_hi'
    matplotlib.pyplot.clf()
    pylab.hist(x0sd_roi, bins=100)
    pylab.savefig(os.path.join(outdir, 'clust.png'))

if 0:
    # data generation
    data = vstack((rand(150,2) + array([.5,.5]),rand(150,2)))

    # computing K-Means with K = 2 (2 clusters)
    centroids,_ = kmeans(data,2)
    # assign each sample to a cluster
    idx,_ = vq(data,centroids)

    # some plotting using numpy's logical indexing
    plot(data[idx==0,0],data[idx==0,1],'ob',
         data[idx==1,0],data[idx==1,1],'or')
    plot(centroids[:,0],centroids[:,1],'sg',markersize=8)
    show()


if 1:
    '''
    The pitch of the clusters should be constant
    Find the mean pitch and penalize when clusters stray from it
    '''
    clustersm = {}
    clustersm_c = {}
    '''
    Need 2 clusters to take centroid difference
    But with only two there is only one centroid derrivitive => average is the diff
    Therefore need at least 3 for a meaningful result
    '''
    for clusters in xrange(3, 20):
    #for clusters in (6,):
        print
        print clusters
        # computing K-Means with K = 2 (2 clusters)
        centroids,_ = kmeans(data2_np, clusters)
        centroids_sort = sorted(centroids)
        print centroids_sort
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
    
    '''
    [1.5,       28.184615384615384,               57.184210526315788,         86.534883720930239]
    [1.5, 25.368421052631579, 32.148148148148145, 57.184210526315788,         86.534883720930239]
    [1.5, 25.368421052631579, 32.148148148148145, 57.184210526315788, 82.411764705882348, 89.230769230769226]
    '''



