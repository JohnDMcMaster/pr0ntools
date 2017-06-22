'''
Postprocess
'''

import json
from PIL import Image
import os
import numpy as np

BIT_WH = 256

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

    bitmap(j, os.path.join(dir_out, 'bitmap.png'))
    heatmap(j, os.path.join(dir_out, 'confidence_rg.png'), True)
    heatmap(j, os.path.join(dir_out, 'confidence_bw.png'), False)
 
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Grid auto-bitmap test')
    parser.add_argument('fn',  help='image file to process')
    args = parser.parse_args()

    run(args.fn)

