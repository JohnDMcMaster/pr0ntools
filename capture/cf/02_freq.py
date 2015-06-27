import cv2
import numpy as np
from matplotlib import pyplot as plt
import argparse
import matplotlib as ml
import matplotlib.pyplot as plt
import numpy as np
import Image

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CV test')
    parser.add_argument('fn_in', help='image file to process')
    args = parser.parse_args()

    if 0:
        img = cv2.imread(args.fn_in,0)
        f = np.fft.fft2(img)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20*np.log(np.abs(fshift))

        plt.subplot(121),plt.imshow(img, cmap = 'gray')
        plt.title('Input Image'), plt.xticks([]), plt.yticks([])
        plt.subplot(122),plt.imshow(magnitude_spectrum, cmap = 'gray')
        plt.title('Magnitude Spectrum'), plt.xticks([]), plt.yticks([])
        plt.show()
    # http://stackoverflow.com/questions/21362843/interpret-numpy-fft-fft2-output
    # blue: low freq
    # red: high freq
    if 1:
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
        if 1:
            fig, ax = plt.subplots(nrows=2, ncols=2, figsize=(14, 6))
            ax[0,0].hist(frows, bins=200)
            ax[0,0].set_title('frows')
            ax[0,1].hist(fcols, bins=200)
            ax[0,1].set_title('fcols')
            ax[1,0].imshow(np.log(freq), interpolation="none")
            ax[1,0].set_title('log(freq)')
            ax[1,1].imshow(image, interpolation="none")
            plt.show()
        import sys
        sys.exit(1)
        
        
        fig, ax = plt.subplots(nrows=2, ncols=2, figsize=(14, 6))
        ax[0,0].hist(freq.ravel(), bins=200)
        ax[0,0].set_title('hist(freq)')
        ax[0,1].hist(np.log(freq).ravel(), bins=200)
        ax[0,1].set_title('hist(log(freq))')
        ax[1,0].imshow(np.log(freq), interpolation="none")
        ax[1,0].set_title('log(freq)')
        ax[1,1].imshow(image, interpolation="none")
        plt.show()

