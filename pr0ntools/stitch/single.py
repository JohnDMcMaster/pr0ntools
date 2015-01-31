from PIL import Image
import re

def singlify(fns_in, fn_out):
    def coord(fn):
        '''Return (x, y) for filename'''
        # st_021365x_005217y.jpg
        m = re.match('.*st_([0-9]*)x_([0-9]*)y.jpg', fn)
        return (int(m.group(1), 10), int(m.group(2), 10))
    
    print 'Calculating dimensions...'
    xmin = None
    for fn in fns_in:
        (x, y) = coord(fn)
        if xmin is None:
            xmin = x
            ymin = y
            xmax = x
            ymax = y
        else:
            xmin = min(xmin, x)
            ymin = min(ymin, y)
            xmax = max(xmax, x)
            ymax = max(ymax, y)
    
    print 'X: %d:%d' % (xmin, xmax)
    print 'Y: %d:%d' % (ymin, ymax)
    with Image.open(fns_in[0]) as im0:
        print 'Base size: %dw x %dh' % (im0.size[0], im0.size[1])
        w = im0.size[0] + xmax - xmin
        h = im0.size[1] + ymax - ymin
        print 'Net size: %dw x %dh' % (w, h)
        dst = Image.new(im0.mode, (w, h))
    
    for fni, fn in enumerate(fns_in):
        print 'Merging %d/%d %s...' % (fni + 1, len(fns_in), fn)
        (x, y) = coord(fn)
        im = Image.open(fn)
        dst.paste(im, (x - xmin, y - ymin))
    print 'Saving...'
    dst.save(fn_out, quality=90)
    print 'Done!'
