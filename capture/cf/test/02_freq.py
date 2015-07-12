import cv2
import numpy as np
from matplotlib import pyplot as plt
import argparse
import matplotlib as ml
import matplotlib.pyplot as plt
import numpy as np
import Image
import os
import csv
from pylab import plot,show
from numpy import vstack,array
from numpy.random import rand
from scipy.cluster.vq import kmeans,vq
import pylab
import matplotlib
import scipy.fftpack
import scipy

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CV test')
    parser.add_argument('fn_in', nargs='?', default='sample.png', help='image file to process')
    args = parser.parse_args()

    outdir = '02_freq'
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    if 0:
        img = cv2.imread(args.fn_in,0)
        f = np.fft.fft2(img)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20*np.log(np.abs(fshift))

        plt.subplot(121),plt.imshow(img, cmap = 'gray')
        plt.title('Input Image'), plt.xticks([]), plt.yticks([])
        plt.subplot(122),plt.imshow(magnitude_spectrum, cmap = 'gray')
        plt.title('Magnitude Spectrum'), plt.xticks([]), plt.yticks([])
        #plt.show()
        plt.savefig(os.path.join(outdir, '01-01_plt.png'))
    
    # http://stackoverflow.com/questions/21362843/interpret-numpy-fft-fft2-output
    # blue: low freq
    # red: high freq
    if 0:
        image = np.asarray(Image.open(args.fn_in).convert('L'))
        freq_raw = np.fft.fft2(image)
        freq = np.abs(freq_raw)

        print 'freq'
        print '  ', len(freq.ravel())
        print '  ',  min(freq.ravel())
        print '  ',  max(freq.ravel())
        
        lfreq = np.log(freq)
        
        print 'lfreq'
        print '  ',  len(lfreq.ravel())
        print '  ',  min(lfreq.ravel())
        print '  ',  max(lfreq.ravel())
        
        #freq = np.fft.fftfreq(freq.ravel().size, d=timestep)
        frows = np.fft.fftfreq(freq_raw.shape[0],d=2)
        fcols = np.fft.fftfreq(freq_raw.shape[1],d=2)
        
        print 'rows'
        print len(frows)
        print frows
        if 0:
            fig, ax = plt.subplots(nrows=2, ncols=2, figsize=(14, 6))
            ax[0,0].hist(frows, bins=200)
            ax[0,0].set_title('frows')
            ax[0,1].hist(fcols, bins=200)
            ax[0,1].set_title('fcols')
            ax[1,0].imshow(np.log(freq), interpolation="none")
            ax[1,0].set_title('log(freq)')
            ax[1,1].imshow(image, interpolation="none")
            #plt.show()
            plt.savefig(os.path.join(outdir, '02-01_plt.png'))
        
        if 0:
            fig, ax = plt.subplots(nrows=2, ncols=2, figsize=(14, 6))
            ax[0,0].hist(freq.ravel(), bins=200)
            ax[0,0].set_title('hist(freq)')
            ax[0,1].hist(np.log(freq).ravel(), bins=200)
            ax[0,1].set_title('hist(log(freq))')
            ax[1,0].imshow(np.log(freq), interpolation="none")
            ax[1,0].set_title('log(freq)')
            ax[1,1].imshow(image, interpolation="none")
            #plt.show()
            plt.savefig(os.path.join(outdir, '02-02_plt.png'))
    
    f = open('sample/s02-15_sum.csv', 'r')
    f.readline()
    cr = csv.reader(f, delimiter=',')
    vs = [int(l[1]) for l in cr]
    if 0:
        N = 10000
        
        #f = np.fft.fft(vs)
        f = yf = scipy.fftpack.fft(vs)

        matplotlib.pyplot.clf()
        #plt.plot(f)
        plt.plot(2.0/N * np.abs(yf[0:N/2]))
        pylab.savefig(os.path.join(outdir, '03-01_plt.png'))


    if 1:
        # Number of samplepoints
        N = len(vs)
        # sample spacing
        T = 1.0
        x = np.linspace(0.0, N*T, N)
        y = vs

        yf = scipy.fftpack.fft(y)
        xf = np.linspace(0.0, 1.0/(2.0*T), N/2)
        
        xfp = xf[1:]
        yfp = 2.0/N * np.abs(yf[1:N/2])
        
        # remove dc component
        matplotlib.pyplot.clf()
        plt.subplot(311)
        plt.plot(xfp, yfp)
        
        plt.subplot(312)
        plt.plot(xfp[0:100], yfp[0:100])

        ax = plt.subplot(313)
        ax.set_xscale('log')
        #plt.plot([1.0 / x for x in xfp[10:100]], yfp[10:100])
        plt.plot([1.0 / x for x in xfp], yfp)

        ax = plt.subplot(313)
        lxs = []
        lys = []
        import heapq
        largest_y = heapq.nlargest(10, yfp)
        n = 0
        for large_y in heapq.nlargest(10, yfp):
            i = list(yfp).index(large_y)
            x = xfp[i]
            pix = 1.0 / x
            print '%d: x: %0.3f, y: %0.3f' % (n, x, large_y)
            print '  pix: %0.6f (%0.6fx)' % (pix, pix / 14.392157,)
            lxs.append(pix)
            lys.append(large_y)
            matplotlib.pyplot.text(pix, large_y, '%d' % n)
            n += 1
        plt.plot(lxs, lys, 'ro', color='red')
        plt.show()


    if 0:
        t = np.arange(len(vs))
        sp = np.fft.fft(vs)
        freq = np.fft.fftfreq(t.shape[-1])
        plt.plot(freq, sp.real, freq, sp.imag)
        pylab.savefig(os.path.join(outdir, '04-01_plt.png'))

    if 0:
        t = np.arange(256)
        sp = np.fft.fft(np.sin(t))
        freq = np.fft.fftfreq(t.shape[-1])
        plt.plot(freq, sp.real, freq, sp.imag)
        
        plt.show()
        
    if 0:
        # Number of samplepoints
        N = 1600
        # sample spacing
        T = 1.0
        x = np.linspace(0.0, N*T, N)
        y = np.sin(0.005 * 2.0*np.pi*x) + 0.5*np.sin(0.05 * 2.0*np.pi*x)
        #fig, ax = plt.subplots()
        #ax.plot(x, y)
        #plt.show()
        
        
        xf = np.linspace(0.0, 1.0/(2.0*T), N/2)
        yf = scipy.fftpack.fft(y)
        yfp = 2.0/N * np.abs(yf[0:N/2])
        print xf[0:4]
        print yf[0:4]
        print yfp[0:4]
        
        matplotlib.pyplot.clf()
        plt.subplot(411)
        plt.plot(x, y)
        plt.subplot(412)
        plt.plot(xf, yf[0:N/2])
        plt.subplot(413)
        plt.plot(xf, yfp)
        
        #xf = [1.0/xf for x in xf]
        xf = xf[0:100]
        yfp = yfp[0:100]
        plt.subplot(414)
        plt.plot(xf, yfp)
        plt.show()

    if 0:
        # Number of samplepoints
        N = 1000
        # sample spacing
        T = 1.0 / 320.0
        x = np.linspace(0.0, N*T, N)
        # 10 units per pixel, 4 units per pixel
        y = np.sin(20 * 2.0*np.pi*x) + 0.5*np.sin(80 * 2.0*np.pi*x)
        #fig, ax = plt.subplots()
        #ax.plot(x, y)
        #plt.show()
        
        yf = scipy.fftpack.fft(y)
        xf = np.linspace(0.0, 1.0/(2.0*T), N/2)
        
        fig, ax = plt.subplots()
        ax.plot(xf, 2.0/N * np.abs(yf[0:N/2]))
        plt.show()

    if 0:
        # Number of samplepoints
        N = 1000
        # sample spacing
        T = 1.0
        x = np.linspace(0.0, N*T, N)
        # 10 units per pixel, 4 units per pixel
        y = 100.0 + np.sin(0.1 * 2.0*np.pi*x) + 0.5*np.sin(0.01 * 2.0*np.pi*x)
        #fig, ax = plt.subplots()
        #ax.plot(x, y)
        #plt.show()
        
        yf = scipy.fftpack.fft(y)
        xf = np.linspace(0.0, 1.0/(2.0*T), N/2)
        
        # remove dc component
        fig, ax = plt.subplots()
        ax.plot(xf[1:], 2.0/N * np.abs(yf[1:N/2]))
        plt.show()
    
    if 0:
        # Number of samplepoints
        N = len(vs)
        # sample spacing
        T = 1.0
        x = np.linspace(0.0, N - 1, N)
        yf = scipy.fftpack.fft(vs)
        xf = np.linspace(0.0, 1.0/(2.0*T), N/2)
        
        fig, ax = plt.subplots()
        ax.plot(xf, 2.0/N * np.abs(yf[0:N/2]))
        plt.show()
