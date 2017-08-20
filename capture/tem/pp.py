'''
Postprocess
'''

import json
from PIL import Image
import os
import numpy as np
import math

BIT_WH = 256

'''
{
u'bestk': 1,
u'res': [1.1362289094663497e-140, 3.902074920347574e-09],
u'pois': [574.7407407407408, 62.46765565962602],
u'meta': {
    u'txt_fn': u'sega_315-5571_xpol_train2/sega_315-5571_xpol_17_27.txt',
    u'glob_loc': [138, 223],
    u'tile_loc': [2, 7],
    u'lr': u'r',
    u'im_fn': u'sega_315-5571_xpol_train2/sega_315-5571_xpol_17_27.png',
    u'im_loc': [17, 27]
    }
}
'''

def heatmap(j, fn_out, rg):
    '''
    Scale from green being the best matches to red being the worst
    Black is no data
    white: (255, 255, 255)
    red: (255, 0, 0)
    green: (255, 255, 0)
    '''
    im = Image.new("RGB", (BIT_WH, BIT_WH), "black")
    
    # Start by building a map of all of the scores
    scores = np.zeros(BIT_WH * BIT_WH)
    for run in j['runs']:
        col, row = run['meta']['glob_loc']
        scores[row * BIT_WH + col] = run['res'][run['bestk']]
    print 'Worst score: %g' % np.min(scores)
    print 'Best score: %g' % np.max(scores)
    scoresl = np.log(scores)
    smin = np.min(scoresl)
    smax = np.max(scoresl)
    print 'Worst score: %g' % smin
    print 'Best score: %g' % smax
    # Normalize to 0 to 1
    scoresn = (scoresl - smin) / (smax - smin)
    print 'Worst score: %g' % np.min(scoresn)
    print 'Best score: %g' % np.max(scoresn)
    
    # red green
    if rg:
        for biti, score in enumerate(scoresn):
            g = int(255 * score)
            x = biti % BIT_WH
            y = biti / BIT_WH
            im.putpixel((x, y), (255 - g, g, 0))
    # white bad
    else:
        for biti, score in enumerate(scoresn):
            scorei = int(255 * (1 - score))
            x = biti % BIT_WH
            y = biti / BIT_WH
            im.putpixel((x, y), (scorei, scorei, scorei))
    im.save(fn_out)

# Display list of the worst score deltas
def find_worst(j, dir_out, worstn=6):
    results = []
    xyindex = {}
    for runi, run in enumerate(j['runs']):
        col, row = run['meta']['glob_loc']
        # run['res'][run['bestk']]
        score = abs(math.log(run['res'][1], 10) - math.log(run['res'][0], 10))
        results.append((score, run))
        xyindex[(col, row)] = runi
    results = sorted(results)

    def printr(i):
        score, run = results[i]
        #print run
        m = run['meta']
        print 'Score %f' % score
        print '  fn: %s' % m['im_fn']
        print '  tile_loc: %s' % (m['tile_loc'],)
        print '  Actual: %s' % run['ref']
        print '  Result: %s' % run['bestk']
        print '  POIs'
        for poi in run['pois']:
            print '    %g' % poi
        print '  us'
        lr = m['lr']
        for poi in run['pois']:
            for bit in xrange(2):
                k = '%d%s' % (bit, lr)
                print '    %s' % k
                for v in j['us'][k]:
                    print '      %g' % (v,)
        print '  Scores'
        for res in run['res']:
            print '    %g' % res

    print 'Worst %d results' % worstn
    for i in xrange(worstn):
        printr(i)

    # Find what percentile had errors
    # Work backwards until we find an error
    last_err = -1
    for i, result in enumerate(results):
        score, run = result
        m = run['meta']
        if run['ref'] is not None and run['ref'] != run['bestk']:
            last_err = i

        if 0:
            im_full = Image.open(m['im_fn'])
            crop = m['crop']
            im_tile = im_full.crop(crop)
            im_tile.save(os.path.join(dir_out, '%d.png' % i))

    # This number should be very small
    # Otherwise errors are getting undetected despite having bad score
    print
    print 'Last error at %d / %d: %0.1f%%' % (last_err, len(results), 100.0 * last_err / len(results))
    if last_err >= 0:
        printr(last_err)

        if 1:
            i = last_err
            score, run = results[i]
            m = run['meta']
            
            im_full = Image.open(m['im_fn'])

            # crop = (xmin, ymin, xmin + imwh, ymin + imwh)
            crop = m['crop']
            im_tile = im_full.crop(crop)
            #im_tile.show()
            im_tile.save(os.path.join(dir_out, 'worst.png'))


    print
    print 'Known bad'
    badb = 0
    badn = 0
    for x,y in [(35, 150), (36, 150), (13, 158), (38, 190), (30, 239)]:
        i = xyindex[(x, y)]
        printr(i)

        score, run = results[i]
        m = run['meta']
        # This whole region should be 0's
        if run['bestk'] == 1:
            badb += 1
        badn += 1
    print 'Failed %d / %d' % (badb, badn)

def bitmap(j, fn_out):
    im = Image.new("RGB", (BIT_WH, BIT_WH), "black")
    
    # Start by building a map of all of the scores
    scores = np.zeros(BIT_WH * BIT_WH)
    for run in j['runs']:
        col, row = run['meta']['glob_loc']
        if run['bestk']:
            im.putpixel((col, row), (255, 255, 255))
    im.save(fn_out)

def run(fn):
    print 'Loading'
    j = json.load(open(fn, 'r'))
    print 'Ready'
    dir_out = os.path.dirname(fn)

    #bitmap(j, os.path.join(dir_out, 'bitmap.png'))
    #heatmap(j, os.path.join(dir_out, 'confidence_rg.png'), True)
    #heatmap(j, os.path.join(dir_out, 'confidence_bw.png'), False)
    find_worst(j, dir_out)
 
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Grid auto-bitmap test')
    parser.add_argument('fn',  help='image file to process')
    args = parser.parse_args()

    run(args.fn)

