'''
Template matching test
Takes in some sample tagged tiles

Ubuntu 16.04.2
sudo apt-get install -y python-scipy

instead of ROI, weight by per pixel Pearson correlation?
Right now smaller region might pickup dust better though
Maybe instead should add some other quality dimensions for roughness or something
'''

from scipy.stats import multivariate_normal
import numpy as np

from PIL import Image
import glob
import re
import os
import json

'''
print
print 'Process %s' % png_fn


Grid is 1 pixel red
First valid tile is from 1,1 to 13,13

13 pixel images + 1 pixel gutter
rightmost at 99
1 + (13 + 1) * 7 = 99
cool
same for x and y

Proposal: since there are actually two types of ROM positions
(left facing or right facing)
think should actually create two different distributions
Alternatively could actually flip them around
But feel this is safer for now

So each cell will actually have several attributes:
-0 or 1
-left or right

Then for the final ROM left/right won't matter

For an 8x8
lr lr lr lr
lr lr lr lr
lr lr lr lr
lr lr lr lr
lr lr lr lr
lr lr lr lr
lr lr lr lr
lr lr lr lr


blah_xpol_31_31.png
So I guess
32x32 of 8x8 => 256 x 256 => 65536 bits => 8192 B => 8 KB
which matches
8192 ref_blah.bin
'''
BIT_WH = 256
#BYTE_WH = = 8192
def data_gen(dir_fn):
    for png_fn in glob.glob(dir_fn + "/*.png"):
        # 02_23.png
        # blah_xpol_08_23.png
        im_full = Image.open(png_fn)
        m = re.match('.*/([0-9]*)_([0-9]*).png', png_fn)
        if not m:
            m = re.match('.*_([0-9]*)_([0-9]*).png', png_fn)
        if not m:
            #print png_fn
            #raise Exception()
            # There are a few meta files
            continue
        # FIXME: are these rows or columns?
        im_row = int(m.group(2))
        im_col = int(m.group(1))

        meta = {
            'im_fn': png_fn,
            'im_loc': (im_col, im_row)
        }

        # Do we have training data?
        txt_fn = png_fn.replace('.png', '.txt')
        if os.path.exists(txt_fn):
            txt = open(txt_fn, 'r').read()
            txt = txt.strip().replace('\n', '')
            txtb = ''.join(['\x00' if c == '0' else '\x01' for c in txt])
            meta['txt_fn'] = txt_fn
        else:
            txtb = None
        
        # Convert into a bytearray of 0/1 bytes
        for tile_row in xrange(8):
            for tile_col in xrange(8):
                if txtb:
                    # byte 0 or 1
                    bit = ord(txtb[tile_row * 8 + tile_col])
                else:
                    bit = None
                # left or right as char
                # Note tiles are aligned, so only look at local coordinates
                meta['lr'] = 'l' if tile_row % 2 == 0 else 'r'
                meta['tile_loc'] = (tile_col, tile_row)
                meta['glob_loc'] = (8 * im_col + tile_col, 8 * im_row + tile_row)
                # Now slice out the image per above rules
                # Image width/height: 13 pix
                # Border: 1 pix
                imwh = 14
                xmin = 1 + 14 * tile_col
                ymin = 1 + 14 * tile_row
                # The crop rectangle, as a (left, upper, right, lower)-tuple.
                im_tile = im_full.crop((xmin, ymin, xmin + imwh, ymin + imwh))
                # Ex: (Image object, '\x00', {...})
                yield (im_tile, bit, dict(meta))

'''
4 variants: 0/1 or l/r
List of bits
Each bit has a 3x3 array of floats for each iamge section
But may be better to store as lists for each of the individual sectors for training
'''

'''
Split input iamge into sections
Returns in row major order
1:13
1:4, 5:9, 10:13
'''
if 0:
    POIS = 9
    def bitimg_pois(im, debug=False):
        ret = np.zeros(9)
        i = 0
        for xmin, xmax in ((1, 4), (5, 9), (10, 13)):
            for ymin, ymax in ((1, 4), (5, 9), (10, 13)):
                im_pix = im.crop((xmin, ymin, xmax, ymax))
                np_pix = np.array(im_pix)
                # Maybe should normalize this to average pixel?
                # Will make easier to compare distributions
                xw = xmax - xmin
                yh = ymax - ymin
                avg = np.sum(np_pix) / (xw * yh)
                if debug:
                    print xmin, xmax, ymin, ymax, '%0.3f' % avg
                ret[i] = avg
                i += 1
        #if debug:
        #    raise KeyboardInterrupt()
        return ret

if 1:
    POIS = 1
    def bitimg_pois(im, debug=False):
        ret = np.zeros(1)
        i = 0
        np_pix = np.array(im)
        # Maybe should normalize this to average pixel?
        # Will make easier to compare distributions
        xw = 9
        yh = 9
        avg = np.sum(np_pix) / (xw * yh)
        if debug:
            print xmin, xmax, ymin, ymax, '%0.3f' % avg
        ret[i] = avg
        i += 1
        #if debug:
        #    raise KeyboardInterrupt()
        return ret

'''
Reads data, splitting into sections and placing into output arrays
Output arrays have one entry per input image
'''
def bucket_data(gen):
    ret = {}
    for klr in genk():
        ret[klr] = [[] for _x in xrange(POIS)]
    for bitg in gen:
        im, bit, meta = bitg
        lr = meta['lr']
        klr = (bit, lr)
        pois = bitimg_pois(im)
        bucket = ret[klr]
        for i in xrange(POIS):
            bucket[i].append(pois[i])
    return ret

def genk():
    for k in xrange(2):
        for lr in 'lr':
            yield (k, lr)

class Template(object):
    def __init__(self):
        # Training data
        self.us = None
        self.covs = None

    def train(self, dir_fn, verbose=True):
        self.us = {}
        self.covs = {}

        gen = data_gen(dir_fn)
        buckets = bucket_data(gen)

        for klr in genk():
            bucket = buckets[klr]
            # 3x3 array, average the
            #print 'bucket', bucket[0:10]
            print 'bucket', len(bucket), len(bucket[0])
            us = np.mean(bucket, axis=1)
            self.us[klr] = us
            # https://docs.scipy.org/doc/numpy-1.12.0/reference/generated/numpy.cov.html
            self.covs[klr] = np.cov(bucket)

            if 0:
                print bucket[0][0:10]
                print bucket[1][0:10]
                print '  us'
                for i, u in enumerate(us):
                    print '  %d: %0.3f' % (i, u)
                raise KeyboardInterrupt()
    
            #print klr, self.us
            #print len(self.us[klr])
            #raise KeyboardInterrupt()
        #print self.covs
        if verbose:
            print 'Train debug'
            for klr in genk():
                k, lr = klr
                us = self.us[klr]
                cov = self.covs[klr]
                print 'k=%d, lr=%s' % (k, lr)
                print '  us'
                for i, u in enumerate(us):
                    print '  %d: %0.3f' % (i, u)

    def run(self, dir_fn, dir_out, verbose=False):
        # https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.stats.multivariate_normal.html
        gen = data_gen(dir_fn)
        '''
        Iterate through all the data we got, forming a ROM
        Bit order is global row major order
        The final order may not be correct
        '''
        bits = [bytearray('\x00' * BIT_WH) for _x in xrange(BIT_WH)]
        chk_good = 0
        chk_bad = 0

        metag = []
        best_match = 0.0
        worst_match = 1.0
        for bitgi, bitg in enumerate(data_gen(dir_fn)):
            verbosel = verbose and bitgi < 3
            im, bit_ref, meta = bitg
            if verbosel:
                print
                print 'Bit %d in %s' % (bitgi, meta['im_fn'])
            lr = meta['lr']
            # Returns a 9 element array
            pois = bitimg_pois(im)
            res = np.zeros(2)
            for k in xrange(2):
                klr = (k, lr)
                # Now score all the possible outcomes
                temp_us = self.us[klr]
                temp_covs = self.covs[klr]
                #print len(temp_us[0])
                res[k] = multivariate_normal.pdf(pois, mean=temp_us, cov=temp_covs)
            # Select result with the highest score
            # XXX: or should this be lowest...
            bestk = np.argmax(res)
            best_match = max(best_match, res[bestk])
            worst_match = min(worst_match, res[bestk])
            glob_col, glob_row = meta['glob_loc']
            bits[glob_row][glob_col] = bestk
            
            if bit_ref is not None:
                if bestk == bit_ref:
                    chk_good += 1
                else:
                    chk_bad += 1
            if verbosel:
                print 'res', res
                print 'pois', pois
                print 'Result: %d' % bestk
            
            metal = {
                'meta': meta,
                'bestk': bestk,
                'res': list(res),
                'pois': list(pois),
                'us': list(self.us),
                'covs': list([list(x) for x in self.covs]),
            }
            metag.append(metal)

        print 'Stats'
        nbits = sum([len(x) for x in bits])
        cnt_1s = sum([sum(x) for x in bits])
        cnt_0s = nbits - cnt_1s
        print '  Total bits: %d' % nbits
        print '  0s: %d' % cnt_0s
        print '  1s: %d' % cnt_1s
        print 'Check'
        print '  Good: %d' % chk_good
        print '  Bad: %d' % chk_bad
        print 'Score match'
        print '  Best:  %g' % best_match
        print '  Worst: %g' % worst_match

        metaf = {
            'runs': metag,
            'nbits': nbits,
            'cnt_0s': cnt_0s,
            'cnt_1s': cnt_1s,
            'chk_good': chk_good,
            'chk_bad': chk_bad,
            'score_best': best_match,
            'score_worst': best_match,
            # width, height
            'bits_wh': (BIT_WH, BIT_WH),
        }

        print 'Exporting...'
        # Are ready for output
        # Dump it somewhere
        if not os.path.exists(dir_out):
            os.mkdir(dir_out)
        dump_txt(bits, os.path.join(dir_out, 'out.txt'))
        #dump_bin(bits, os.path.join(dir_out, 'out.bin'))
        json.dump(metaf, open(os.path.join(dir_out, 'out.json'), 'w'))

def dump_txt(bits, fn):
    f = open(fn, 'w')
    for row in bits:
        for b in row:
            f.write('1' if b else '0')
        f.write('\n')
    f.close()

def dump_bin(bits, fn):
    f = open(fn, 'wb')
    for row in bits:
        for bi in xrange(0, len(bits), 8):
            b = 0
            for i in xrange(8):
                if bits[row][bi + i]:
                    # MSB first
                    b |= 1 << (7 - i)
            f.write(b)
    f.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Grid auto-bitmap test')
    parser.add_argument('--verboset', action='store_true', help='verbose train')
    parser.add_argument('--verboser', action='store_true', help='verbose run')
    parser.add_argument('dir_train', help='image file to process')
    parser.add_argument('dir_run', help='image file to process')
    parser.add_argument('dir_out', nargs='?', help='image file to process')
    args = parser.parse_args()

    dir_out = args.dir_out
    if not dir_out:
        dir_out = args.dir_run + "_out"

    t = Template()
    print 'Training...'
    t.train(args.dir_train, verbose=args.verboset)
    print 'Running...'
    t.run(args.dir_run, dir_out, verbose=args.verboser)

