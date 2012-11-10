#!/usr/bin/env python
'''
Goal:
Traditional edge detectors seem to be based on finding unknown edges in a picture
Instead, find the edge given a location

***Phase 1: use Canny edge detector given a line
generates a profile based on that line

Phase 2: use custom variable slope edge detector

may generate inner and outer polygon
    can tell which is which by area fairly easily
What to do?  Some options:
-Take inner
-Take outter
-Take middle
When I'm drawing I've been shooting for middle
Inner is probably preferable for now



Parameters
Canny edge detector threshold
    should sweep values?
    Ideally would do a potentially more expensive baseline and then slowly deviate from it as needed
Line match threshold
    problem: what is minimum feature size?
    Two proposals:
        people determine feature size by having a level of detail in mind (ie match aginst reference)
        determine the largest features and only pick them up
    rank features based on highest contrast / least variance
        minimum threshold to keep to keep efficient
    randomly start at points and determine if feature can be located
        or could grid the image

problem: canny throws away color matching (I'm currently converting to grayscale => BW)
    not necessarily an issue, deal with it as time goes on
problem: how to tell if a polygon contains a line?
    for each edge on the polygon do a match?
    probably need to match multiple segments...linear regression?
    
    
    
    
'''
import cv
import argparse        
import sys
import math

def dbg(s):
    if 0:
        print s

# for v/h contour
def pvhcontour(contour, indent = ''):
    print '%sContour length: %d' % (indent, len(contour))
    #print contour.v_next
    #print contour.h_next
    '''
    # V is not used for LIST
    if contour.v_next:
        print '%sV'% indent
        pcontour(contour.v_next, indent + '  ')
    '''
    if contour.h_next():
        print '%sV'% indent
        pcontour(contour.h_next(), indent + '  ')

    return

def linearize(p0, p1):
    m = (p1[1] - p0[1]) / (p1[0] - p0[0])
    b = p0[1] - m * p0[0]
    return (m, b)

def linearized_pgen(p0, p1):
    l = vertex_len(p0, p1)
    # Give nth point (x, y) where 0 gives p0 and n_points - 1 gives p1
    f = None
    # So we get to have some fun then
    # Do a regression so that we know where to generate midpoints
    # Note that slope can be zero...don't do simple x vs y
    # Assume points aren't equal
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    #print 'dx: %g, dy: %g' % (dx, dy)
    if abs(dx) > abs(dy):
        # Larger dy/dx
        # ex: y = 7
        m = dy / dx
        b = p0[1] - m * p0[0]
        def f(n):
            # for two point:
            # 0 => start
            # 1 => end
            x = p0[0] + dx * n
            return (x, m * x + b)
    else:
        # Larger dx/dy (ex: x = 7), solve for x = my + b
        # dx/dy
        m = dx / dy
        b = p0[0] - m * p0[1]
        def f(n):
            y = p0[1] + dy * n
            return (m * y + b, y)
    return f

'''
Find a net error distance between a polygon and a line
Very crude algorithm, can probably be improved
Assumes:
    -that polygon reasonably approximates line somewhere
    -Ideal polygon edge is longer than line
    -
Algorithm: (simple brute force)
-Set best regression to infinity
-Break up polygon into segments of at most delta size
-Choose an arbitrary point on polygon and collect segments until >= line length
    could choose another threshold like 0.95 line length
-For each segment minimally >= line length calculate regression distance to the line
    (adding segments can only make worse, keep going until we can drop one)
    -Sum regression distances
    -if above is lower than last known record it
-Return the best distance (points themselves are discarded at this time)

Algorithm: no, might provide heuristic but not actual solution
-Start with a circle with length out to furthest distance from center of line to polygon
-While a line segment exists still of enough size:
    -Compute 
    -Decrease circle diameter

Algorithm:
-Find the closest polygon point to the center of the line
-

TODO: is there some way to leverage linear regression to simplify this?
would give us an idea of slope, then would just need to justify range
'''
def contour_line_diff(contour_in, line):
    '''polygon: cvContour, line: '''
    #print
    #print
    best_diff = float('inf')
    # Inclusive
    # Not output, for debugging only
    best_start = None
    best_end = None
    # Size in pixels of the largest acceptable segment
    # TODO: relate to min feature size
    max_segment = 10
    #contour = list2contour(segment_contour(contour_in, max_segment))
    contour = segment_contour(contour_in, max_segment)
    #draw_contour(contour)
    print '  Polygon segmented from %u => %u points' % (len(contour_in), len(contour))
    
    # Now approximate the regression
    # Start by building a line at least given length
    # If its not long enough automatically reject it
    line_len = vertex_len(line[0], line[1])
    # Line point generator
    # Returns a function that given a fraction of 1
    # return a point along the line
    line_pgen = linearized_pgen(line[0], line[1])

    # Needs to at least squiggle back and forth
    if contour_len(contour) < 2 * line_len:
        print '  Contour did not meet minimum size'
        return float('inf')
    
    working_len = 0.0
    working = []
    # Next point to close a vertex
    vertexi = 1
    # Last point currently using
    # the next to get dropped
    vertexi_tail = 0
    while working_len < line_len:
        # XXX: could this go out of bounds?
        working_len += vertex_len(contour[vertexi - 1], contour[vertexi])
        vertexi += 1
    while True:
        try:
            # print 'Iter, tail %d, head %d, cur len %g, best diff %g' % (vertexi_tail, vertexi, working_len, best_diff)
            def n_contour_indices():
                # ranges are inclusive
                if vertexi > vertexi_tail:
                    return vertexi - vertexi_tail + 1
                else:
                    # Remaining + wrap around
                    return len(contour) - vertexi_tail + vertexi + 1
            
            #if vertexi_tail > vertexi:
            #    raise Exception('oops')
            
            def diff_line(contour_indices):
                n = 0
                this_diff = 0.0
                ith = 0
                for i in contour_indices:
                    # Find subsegment in the reference line we are diffing against
                    # working_len
                    ref_point = line_pgen(float(ith) / (n_contour_indices() - 1))
                    this_point = contour[i]
                    # XXX: should do any sort of scaling here? (ex sqrt)
                    this_diff += vertex_len(ref_point, this_point)
                    ith += 1
                return this_diff
            
            '''
            Distance between midpoints weighted by segment length
            Two ways: forward or backward
            Need to compute both and see which is better
                TODO: theres probably some way to optimize this
            '''
            def lgen():
                # Wrapped around?  Discrete intervals
                if vertexi < vertexi_tail:
                    gened = 0
                    #print 'Left wrap around'
                    for i in xrange(vertexi_tail, len(contour), 1):
                        yield i
                        gened += 1
                    for i in xrange(0, vertexi + 1, 1):
                        yield i
                        gened += 1
                    if gened != n_contour_indices():
                        raise Exception('Wrong number of points %d' % gened)
                else:
                    for i in xrange(vertexi_tail, vertexi, 1):
                        yield i
            l = diff_line(lgen())
            def rgen():
                # Wrapped around?  Discrete intervals
                if vertexi < vertexi_tail:
                    #print 'Right wrap around'
                    for i in xrange(vertexi, -1, -1):
                        yield i
                    for i in xrange(n_contour_indices() - 1, vertexi - 1, -1):
                        yield i
                else:
                    for i in xrange(vertexi - 1, vertexi_tail - 1, -1):
                        yield i
            r = diff_line(rgen())
            if l < r:
                this_diff = l
            else:
                this_diff = r
            #print '  diffs, L: %g, R: %g, better: %g' % (l, r, this_diff)
            if this_diff == 0.0:
                raise Exception('FIXME') 
            # A new record?
            # Make sure to check the initial attempt
            if this_diff < best_diff:
                best_diff = this_diff
                best_start = vertexi_tail
                best_end = vertexi
            
            # Once closing point is checked we are done
            if vertexi_tail >= len(contour) - 1:
                break
            
            '''
            Otherwise we need to try to optimize
            Can only get better if we can knock a point off of the beginning
            '''
            working_len -= vertex_len(contour[vertexi_tail], contour[vertexi_tail + 1])
            vertexi_tail += 1
            while working_len < line_len:
                p0 = contour[vertexi - 1]
                # Must check closing vertex
                # Note that vertexi wraps around until tail catches up
                p1 = contour[vertexi]
                working_len += vertex_len(p0, p1)
                vertexi = (vertexi + 1) % len(contour)
        except:
            print 'Exception dump:'
            print '  vertexi_tail: %d' % vertexi_tail
            print '  vertexi: %d' % vertexi
            print '  len: %d' % len(contour)
            print '  indeices: %d' % n_contour_indices()
            raise
        
    print '  Best len from %u to %u' % (best_start, best_end)
    for i in xrange(best_start, best_end + 1, 1):
        print '    (%dx, %dy)' % (contour[i][0], contour[i][1])
    return best_diff

def list2contour(list):
    # FIXME: look into this
    ret = cv.CreateMat( len(list), 2, cv.CV_32FC1 )
    for i in xrange(len(list)):
        ret[i][0] = list[i][0]
        ret[i][1] = list[i][1]
    return ret
    
def segment_contour(contour, max_segment):
    '''Accepts an unclosed contour and returns an unclosed contour with small segments'''
    # TODO: should really be a generator
    if len(contour) < 2:
        raise ValueError("Bad contour")
    # Always anchor at the first point
    ret = [contour[0]]
    for pointi in xrange(len(contour) - 1):
        #print
        # Even if broken up end point still exists
        p0 = contour[pointi]
        #print 'p0: %s' % (p0,)
        p1 = contour[pointi + 1]
        #print 'p1: %s' % (p1,)
        l = vertex_len(p0, p1)
        n_ideal = float(l) / max_segment
        # Nothing special to do?
        if n_ideal <= 1:
            dbg('    Optimizing short vertex (%dx, %dy) size %g' % (p1[0], p1[1], l))
            ret.append(p1)
            continue
        dbg('    Splitting')
        dbg('      p0: (%dx, %dy)' % p0)
        dbg('      p1: (%dx, %dy)' % p1)
        n_points = int(math.ceil(n_ideal))
        dbg('      n_points: %d (ideal %g)' % (n_points, n_ideal))
        '''
        Skip 0 since previous covers it
        '''
        f = linearized_pgen(p0, p1)
        for n in xrange(1, n_points + 1):
            per = float(n) / n_points
            p = f(per)
            dbg('      split to (%dx, %dy) w/ %g percent' % (p[0], p[1], per * 100))
            ret.append(p)
    
    print '  Orig:'
    last = None
    for (x, y) in contour:
        delta = ''
        if last is not None:
            delta = ', delta %g' % vertex_len(last, (x, y))
        dbg( '    (%dx, %dy)%s' % (x, y, delta))
        last = (x, y)

    dbg('  Ret:')
    last = None
    delta_n = 0.0
    for (x, y) in ret:
        delta = ''
        if last is not None:
            delta_n = vertex_len(last, (x, y))
            delta = ', delta %g' % delta_n
        dbg('    (%dx, %dy)%s' % (x, y, delta))
        if delta_n > max_segment:
            raise Exception('Segment too big')
        last = (x, y)
    
    return ret
        
def vertex_len(p0, p1):
    '''Length of line connecting point p0 to point p1'''
    return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)

def contour_len(contour, closed=False):
    if len(contour) < 2:
        raise ValueError("Bad contour")
    '''Return floating point integer of contour length'''
    # I'm sure there's a function for this 
    # but its a good excercise and I'm not sure what the func is
    ret = 0.0
    for pointi in xrange(len(contour) - 1):
        p0 = contour[pointi]
        p1 = contour[pointi + 1]
        #print point
        # Coordinates at UL, same as kolourpaint
        #print p0[0], p1[1]
        # pythagrean theorm
        ret += vertex_len(p0, p1)
    if not closed:
        ret += vertex_len(contour[0], contour[-1])
    #draw_contour(contour)
    return ret
    
def print_contour(contour, prefix = ''):
    for pointi in xrange(len(contour) - 1):
        p = contour[pointi]
        '''
        (x, y) w/ origin in upper left hand corner of images
        '''
        print '%s(%dx, %dy)' % (prefix, p[0], p[1])

def icontours(contours):
    while contours:
        yield contours
        contours = contours.h_next()

g_image = None


def filter(contour):
    return False
    # Reject noise
    if area < min_area:
        return True
    if area > max_area:
        return True
    return False

def process(fn):
    global g_image
    
    # Fixed for now, then move to best match
    g_thresh = 100
    
    print 'Working on %s' % fn
    
    g_image = cv.LoadImage(fn)
    if not g_image:
        raise Exception('Failed to load %s' % fn)
    total_area = g_image.width * g_image.height
    print 'Size: %dw X %dh = %g' % (g_image.width, g_image.height, total_area)
    # Select this by some metric with tagged features, say smallest - 10%
    min_area = 100.0
    max_area = total_area * 0.9
    
    gray_img = cv.CreateImage( cv.GetSize(g_image), 8, 1 )
    storage = cv.CreateMemStorage(0)
    
    cv.CvtColor( g_image, gray_img, cv.CV_BGR2GRAY )
    cv.Threshold( gray_img, gray_img, g_thresh, 255, cv.CV_THRESH_BINARY )
    print 'Saving intermediate B&W'
    cv.SaveImage('diffusion_0_thresh.png', gray_img)
    
    '''
    int cvFindContours(
                              img,
       IplImage*
       CvMemStorage*          storage,
       CvSeq**                firstContour,
       int                    headerSize = sizeof(CvContour),
       CvContourRetrievalMode mode        = CV_RETR_LIST,
       CvChainApproxMethod    method       = CV_CHAIN_APPROX_SIMPLE
    );
    '''
    contour_begin = cv.FindContours( gray_img, storage )
    
    contour = contour_begin
    min_rejected = 0
    max_rejected = 0
    total = 0
    contouri = -1
    for contour in icontours(contour_begin):
        contouri += 1
        if filter(contour):
            continue
        #if contouri != 5:
        #    continue
        print '%d' % contouri
        #print '  Points:'
        #print_contour(contour, '    ')
        print '  len %f' % contour_len(contour)
        print '  area %f' % cv.ContourArea(contour)
        # Roughly on the center of the left side
        line = [(63, 115), (65, 319)]
        print '  diff %f' % contour_line_diff(contour, line)
        #draw_contour(contour)
        
def draw_contour(contour):
    gray_img = cv.CreateImage( cv.GetSize(g_image), 8, 1 )
    #cv.CvtColor( g_image, gray_img, cv.CV_BGR2GRAY )
    cv.Zero( gray_img )
    # DrawContours(img, contour, external_color, hole_color, max_level [, thickness [, lineType [, offset]]]) -> None
     # in my small example external didn't get value but internal did
    cv.DrawContours(
            #img
            gray_img,
            # contour
            contour,
            # external_color
            cv.ScalarAll(255),
            # hole_color
            cv.ScalarAll(255),
            # max_level
            0,
            # Thickness
            1
            )
    cv.ShowImage( "Contours", gray_img )
    cv.WaitKey()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="More ice I tell you.  More ice")
    #parser.add_argument('files', metavar='files', type=str, nargs='+',
    #               help='Input training folders and files to classify')
    parser.add_argument('--debug', action="store_true", dest="debug", default=False, help='Debug')
    parser.add_argument('--show', action="store_true", dest="show", default=False, help='Show contours')
    parser.add_argument('--filter', action="store_true", dest="filter", default=False, help='Show only contours we like')
    args = parser.parse_args()
    show = args.show
    filt = args.filter

    if show:
        cv.NamedWindow( "Contours", 1 );
    args.files = ['img_bw.jpg']
    for fn in args.files:
        process(fn)





