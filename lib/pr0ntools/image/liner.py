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
-Take outer
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
# XXX: why does PyDev analysis fail on first but succeed on second?
#import cv
from cv2 import cv
import sys
import time
import math
import os
import shutil
import random

dbgl = 3
pdbg = 0
logf = None
logf = open('liner.log', 'w')
'''
gray: derrived from grayscale image            
purple: area rejected
red: length rejected
teal: worse than existing diff
yellow: histogram rejected
green: new best
'''
draw_thresh_contours = 1
thresh_dir = "liner-thresholds"

def set_dbg(yes):
    global pdbg
    pdbg = yes

def dbg(s, level = 1):
    if level > dbgl:
        return
    s = 'pr0nliner-lib: %s' % str(s)
    if pdbg:
        print s
    if logf:
        logf.write('%s\n' % str(s))
    
def linearize(p0, p1):
    m = (p1[1] - p0[1]) / (p1[0] - p0[0])
    b = p0[1] - m * p0[0]
    return (m, b)

def linearized_pgen(p0, p1):
    '''Return a generator that generates points between two points'''
    
    #l = vertex_len(p0, p1)
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

def vertex_len(p0, p1):
    '''Length of line connecting point p0 to point p1'''
    return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)

def contour_len(contour, closed=False):
    if len(contour) < 2:
        raise ValueError("Bad contour of len %d" % len(contour))
    '''Return floating point integer of contour length'''
    # I'm sure there's a function for this 
    # but its a good excercise and I'm not sure what the func is
    '''
    the function?
    double cvArcLength(
        const void* curve,
        CvSlice     slice     = CV_WHOLE_SEQ,
        int         is_closed = -1
    );
    #define cvContourPerimeter( contour )      \
       cvArcLength( contour, CV_WHOLE_SEQ, 1 )
    
    cv.ArchLength exists but cv.ContourPerimeter does not
    '''
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
    
def print_contour(contour, prefix = '', level=3):
    if level > dbgl:
        return
    dbg('%sContour:' % prefix)
    for pointi in xrange(len(contour) - 1):
        p = contour[pointi]
        '''
        (x, y) w/ origin in upper left hand corner of images
        '''
        dbg('%s(%dx, %dy)' % (prefix, p[0], p[1]))

def icontours(contours):
    while contours:
        yield contours
        contours = contours.h_next()

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
    dbg('  Polygon segmented from %u => %u points' % (len(contour_in), len(contour)), level=2)
    
    # Now approximate the regression
    # Start by building a line at least given length
    # If its not long enough automatically reject it
    line_len = vertex_len(line[0], line[1])
    # Line point generator
    # Returns a function that given a fraction of 1
    # return a point along the line
    line_pgen = linearized_pgen(line[0], line[1])

    working_len = 0.0
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
            dbg('Exception dump:')
            dbg('  vertexi_tail: %d' % vertexi_tail)
            dbg('  vertexi: %d' % vertexi)
            dbg('  len: %d' % len(contour))
            dbg('  indeices: %d' % n_contour_indices())
            raise
        
    dbg('  Best len from %u to %u' % (best_start, best_end), level=3)
    if dbgl > 3:
        for i in xrange(best_start, best_end + 1, 1):
            dbg('    (%dx, %dy)' % (contour[i][0], contour[i][1]))
    return best_diff

def list2contour(l):
    # FIXME: look into this
    ret = cv.CreateMat( len(l), 2, cv.CV_32FC1 )
    for i in xrange(len(l)):
        ret[i][0] = l[i][0]
        ret[i][1] = l[i][1]
    return ret
    
def segment_contour(contour, max_segment):
    '''Accepts an unclosed contour and returns an unclosed contour with small segments'''
    # TODO: should really be a generator
    if len(contour) < 2:
        raise ValueError("Bad contour of len %d" % len(contour))
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
            dbg('    Optimizing short vertex (%dx, %dy) size %g' % (p1[0], p1[1], l), level=4)
            ret.append(p1)
            continue
        dbg('    Splitting', level=3)
        dbg('      p0: (%dx, %dy)' % p0, level=3)
        dbg('      p1: (%dx, %dy)' % p1, level=3)
        n_points = int(math.ceil(n_ideal))
        dbg('      n_points: %d (ideal %g)' % (n_points, n_ideal), level=3)
        '''
        Skip 0 since previous covers it
        '''
        f = linearized_pgen(p0, p1)
        for n in xrange(1, n_points + 1):
            per = float(n) / n_points
            p = f(per)
            dbg('      split to (%dx, %dy) w/ %g percent' % (p[0], p[1], per * 100), level=3)
            ret.append(p)
    
    if dbgl > 3:
        dbg('  Orig:')
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

def pplane(name, plane, prefix=''):
    print '%sPlane %s (%dw X %dh)' % (prefix, name, plane.width, plane.height)
    for x in xrange(plane.width):
        print prefix,
        for y in xrange(plane.height):
            p = plane[x, y]
            if y % 2 == 1:
                print '(%03d) ' % (p),
        print
    print

def hs_histogram(src, mask=None):
    '''Takes a cvMat and computes a hue-saturation histogram (value is dropped)'''
    # Convert to HSV
    # Allocate the 3 HSV 8 bit channels
    hsv = cv.CreateImage(cv.GetSize(src), 8, 3)
    # Convert from the default BGR representation to HSV
    cv.CvtColor(src, hsv, cv.CV_BGR2HSV)

    # Extract the H and S planes
    h_plane = cv.CreateMat(src.rows, src.cols, cv.CV_8UC1)
    s_plane = cv.CreateMat(src.rows, src.cols, cv.CV_8UC1)
    v_plane = cv.CreateMat(src.rows, src.cols, cv.CV_8UC1)
    # Copy out omitting the values we don't want
    cv.Split(hsv, h_plane, s_plane, v_plane, None)
    planes = [h_plane, s_plane]

    if 0:
        pplane('H plane', h_plane, prefix='    ')
        pplane('S plane', s_plane, prefix='    ')

    h_bins = 8
    s_bins = 8
    #hist_size = [h_bins, s_bins]
    # hue varies from 0 (~0 deg red) to 180 (~360 deg red again
    # ??? My values give a hue of 0-255
    h_ranges = [0, 255]
    # saturation varies from 0 (black-gray-white) to
    # 255 (pure spectrum color)
    s_ranges = [0, 255]
    ranges = [h_ranges, s_ranges]
    # Allocate bins
    # note that we haven't put any data in yet
    #1: uniform
    hist = cv.CreateHist([h_bins, s_bins], cv.CV_HIST_ARRAY, ranges, 1)
    # Convert the array planes back into images since thats what CalcHist needs?
    # Doc seems to indcate that cvMat will work as well
    # Doesn't this cross the hue and saturate values together?  That doesn't seem to make sense, like comparing red to blue
    # Guess its a 2D histogram so it deals with where they overlap
    cv.CalcHist([cv.GetImage(i) for i in planes], hist, 0, mask)
    cv.NormalizeHist(hist, 1.0)
    
    return hist

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
class LinerBase():
    def __init__(self, fn, line, ref_polygon, show=False):
        # Interestingly enough doesn't work if its a list
        def polygize(poly):
            return [tuple(map(int, pair)) for pair in poly]
        self.fn = fn
        self.line = polygize(line)
        self.ref_polygon = polygize(ref_polygon)
        self.show = show
        self.ref_hist = None
        self.cur_thresh = None
            
    def filter(self):
        #return False
        # Reject noise
        if self.contour_area < self.min_area:
            return True
        if self.contour_area > self.max_area:
            return True
        return False
    
    def get_ref(self):
        '''Return reference (image, polygon)'''
        raise Exception('Required')
    
    def compute_ref(self):
        '''Compute a reference histogram that matched regions should approximate'''
        (image, polygon) = self.get_ref()
        
        (width, height) = cv.GetSize(image)
        # (rows, cols,...)
        dest = cv.CreateMat(height, width, cv.CV_8UC3)
        mask8x1 = cv.CreateImage(cv.GetSize(image), 8, 1)
        cv.Zero(mask8x1)
        cv.FillConvexPoly(mask8x1, polygon, cv.ScalarAll(255))
        cv.Copy(image, dest)
    
        self.ref_hist = hs_histogram(dest, mask8x1)
    
    def compare_ref(self, polygon):
        '''Compare new polygon against the reference polygon histogram'''
        
        (image, mask) = self.get_working()
        return cv.CompareHist(self.ref_hist, hs_histogram(image, mask), cv.CV_COMP_CORREL) 
    
    def get_working(self):
        '''Return a CvMat containing the currently being processed polygon plus a mask indicating the ROI'''
        raise Exception("Required")
        
        
    def try_contour(self):
        self.total_contours += 1
        self.contouri += 1
        self.contour_area = cv.ContourArea(self.cur_contour)
        dbg('Thresh contour %d' % self.contouri, level=2)
        if self.filter():
            dbg('  Rejected: filtered contour b/c area not %f <= %f <= %f'% (self.min_area, self.contour_area, self.max_area))
            if draw_thresh_contours:
                # Purple
                cv.PolyLine(self.contours_map, [self.cur_contour], True, cv.CV_RGB(128, 0, 128) )
            return
            
        self.checked_contours += 1
        #if contouri != 5:
        #    continue
        #print '  Points:'
        #print_contour(contour, '    ')
        contour_len_ = contour_len(self.cur_contour)
        dbg('  len %f' % contour_len_, level=2)
        dbg('  area %f' % self.contour_area, level=2)
        if contour_len_ < self.min_len:
            dbg('  Rejected: did not meet minimum length w/ %f < %f' % (contour_len_, self.min_len), level=2)
            if draw_thresh_contours:
                # red
                cv.PolyLine(self.contours_map, [self.cur_contour], True, cv.CV_RGB(255, 0, 0) )
            return
        
        this_diff = contour_line_diff(self.cur_contour, self.line)
        dbg('  diff %f' % this_diff, level=2)
        if this_diff >= self.best_diff:
            dbg("  Rejected: worse diff %f >= %f" % (this_diff, self.best_diff), level=2)
            if draw_thresh_contours:
                # Teal 
                cv.PolyLine(self.contours_map, [self.cur_contour], True, cv.CV_RGB(0, 128, 128) )
            return
        hist_diff = self.compare_ref(self.cur_contour)
        dbg("  Hist diff: %f" % hist_diff, level=2)
        # 0.95 was too lose
        if hist_diff < 0.90:
            dbg("  Rejected: poor histogram match", level=2)
            if draw_thresh_contours:
                # Yellow
                #cv.PolyLine(self.contours_map, [self.cur_contour], True, cv.CV_RGB(255, 255, 0) )
                cv.PolyLine(self.contours_map, [self.cur_contour], True, cv.CV_RGB(random.randint(0, 256), random.randint(0, 256), random.randint(0, 256)) )
            return
        dbg('  Accepted: new best contour', level=2)
        self.best_contour = self.cur_contour
        self.best_thresh = self.cur_thresh
        self.best_diff = this_diff
        self.best_hist_diff = hist_diff
        #draw_contour(self.cur_contour)
        if draw_thresh_contours:
            # green
            cv.PolyLine(self.contours_map, [self.cur_contour], True, cv.CV_RGB(0, 255, 0) )
            
    def try_thresh(self):
        dbg('', level=2)
        dbg('thres %d, best so far %s' % (self.cur_thresh, self.best_diff), level=1)
        
        line_len = vertex_len(self.line[0], self.line[1])
        # Needs to at least squiggle back and forth
        self.min_len = 2 * line_len
        
        self.total_area = self.image.width * self.image.height
        # Select this by some metric with tagged features, say smallest - 10%
        self.min_area = 100.0
        self.max_area = self.total_area * 0.9
        dbg('Size: %dw X %dh = %g' % (self.image.width, self.image.height, self.total_area), level=3)
        
        size = cv.GetSize(self.image)
        dbg('Size: %s' % (size,), level=3)
        self.gray_img = cv.CreateImage( size, 8, 1 )
        storage = cv.CreateMemStorage(0)
        
        cv.CvtColor( self.image, self.gray_img, cv.CV_BGR2GRAY )
        cv.Threshold( self.gray_img, self.gray_img, self.cur_thresh, 255, cv.CV_THRESH_BINARY )
        if 0 and self.cur_thresh == 70:
            dbg('Saving intermediate B&W')
            cv.SaveImage('img_thresh.png', self.gray_img)
        
        '''
        int cvFindContours(
           IplImage*              img,
           CvMemStorage*          storage,
           CvSeq**                firstContour,
           int                    headerSize = sizeof(CvContour),
           CvContourRetrievalMode mode        = CV_RETR_LIST,
           CvChainApproxMethod    method       = CV_CHAIN_APPROX_SIMPLE
        );
        '''
        self.contour_begin = cv.FindContours(self.gray_img, storage)
        
        if draw_thresh_contours:
            '''
            B&W background but color highlighting
            actually the image is missing...but looks fine so w/e
            '''
            self.contours_map = cv.CreateImage( cv.GetSize(self.image), 8, 3 )
            # Sort of works although not very well...does not look like the gray image
            #cv.Zero(self.contours_map)
            cv.CvtColor( self.gray_img, self.contours_map, cv.CV_GRAY2BGR )
        
        self.contouri = -1
        for self.cur_contour in icontours(self.contour_begin):
            self.try_contour()
        
        if draw_thresh_contours:
            # TODO: save image instead
            if 0:
                cv.ShowImage( "Contours", self.contours_map )
                cv.WaitKey()
            else:
                cv.SaveImage(os.path.join(thresh_dir, '%03d.png' % self.cur_thresh), self.contours_map)
            
    def run(self):
        '''Given a filename w/ target image, a line tuple, and a reference rectangle ROI, return a polygon near the line'''
        start = time.time()
        
        if draw_thresh_contours:
            if os.path.exists(thresh_dir):
                shutil.rmtree(thresh_dir)
            os.mkdir(thresh_dir)
        
        self.compute_ref()
        
        self.best_contour = None
        self.best_thresh = None
        self.best_diff = float('inf')
        self.best_hist_diff = None
        # All contours generated
        self.total_contours = 0
        # Excluding those filtered out
        self.checked_contours = 0
        
        # TODO: should try a finer sweep after rough?
        #for g_thresh in xrange(0, 256, 8):
        # somewhat arbitrary "reasonable" range
        # TODO: tune based off of training data
        for self.cur_thresh in xrange(64, 168, 8):
            self.try_thresh()
        if self.best_contour is None:
            raise Exception('Failed to match a contour')
        #for self.cur_thresh in xrange(152, 153, 8):
        dbg("Best contour:")
        dbg('  Points: %d' % len(self.best_contour))
        dbg('  Threshold: %d' % self.best_thresh)
        dbg('  Best diff: %g' % self.best_diff)
        dbg('  Hist diff: %g' % self.best_hist_diff)
        print_contour(self.best_contour, prefix = '  ', level=3)
    
        dbg('Total contours: %d' % self.total_contours)
        dbg('Checked contours: %d' % self.checked_contours)
        end = time.time()
        dbg('Liner delta: %0.3f sec' % (end - start,))
        return self.best_contour
            
'''
Liner the operates on a single source image
No tiling
'''
class SimpleLiner(LinerBase):
    def __init__(self, *args, **kwargs):
        LinerBase.__init__(self, *args, **kwargs)
        self.image = None
    
    def get_ref(self):
        '''
        Could return a subimage bounded by polygon which is
        probably more efficient
        but if they care about performacne they should use the tile version?
        '''
        return (self.image, self.ref_polygon)
    
    def get_working(self):
        (width, height) = cv.GetSize(self.image)
        dest = cv.CreateMat(height, width, cv.CV_8UC3)
        mask8x1 = cv.CreateImage(cv.GetSize(self.image), 8, 1)
        cv.Zero(mask8x1)
        cv.FillConvexPoly(mask8x1, self.cur_contour, cv.ScalarAll(255))
        # Could 8x3 mask copy but histogram mask will take care of it
        cv.Copy(self.image, dest)
        return (dest, mask8x1)

    def draw_contour(self, contour, color=None):
        gray_img = cv.CreateImage( cv.GetSize(self.image), 8, 1 )
        #cv.CvtColor( self.image, gray_img, cv.CV_BGR2GRAY )
        cv.Zero( gray_img )
        # DrawContours(img, contour, external_color, hole_color, max_level [, thickness [, lineType [, offset]]]) -> None
        # in my small example external didn't get value but internal did
        #  void cvPolyLine(CvArr* img,
        #        CvPoint** pts, int* npts,
        #        int contours, int is_closed, CvScalar color,
        #        int thickness=1, int lineType=8, int shift=0)
        if color is None:
            # White for default black background
            #color = cv.CV_RGB(255, 255, 255)
            color = cv.ScalarAll(255)
        cv.PolyLine( gray_img , [contour] , True , color )
        cv.ShowImage( "Contours", gray_img )
        cv.WaitKey()
    
    def draw_color_contours(self, color_contours, color=None):
        '''Takes in list of (contour, color) tuples where contour is iterable for (x, y) tuples'''
        gray_img = cv.CreateImage( cv.GetSize(self.image), 8, 1 )
        #cv.CvtColor( self.image, gray_img, cv.CV_BGR2GRAY )
        cv.Zero( gray_img )
        for (contour, color) in color_contours:
            cv.PolyLine( gray_img , [contour] , True , color )
        cv.ShowImage( "Contours", gray_img )
        cv.WaitKey()

    def show_liner(self):
        size = cv.GetSize(self.image)
        # B&W background but color highlighting
        gray_img = cv.CreateImage( size, 8, 1 )
        draw_img = cv.CreateImage( size, 8, 3 )
        #cv.Copy(self.image, draw_img)
        cv.CvtColor( self.image, gray_img, cv.CV_BGR2GRAY )
        cv.CvtColor( gray_img, draw_img, cv.CV_GRAY2BGR )
        
        '''Takes in list of (contour, color) tuples where contour is iterable for (x, y) tuples'''
        cv.PolyLine(draw_img, [self.best_contour], True, cv.CV_RGB(255, 0, 0) )
        cv.PolyLine(draw_img, [self.ref_polygon], True, cv.CV_RGB(0, 0, 255) )
        print self.line
        cv.PolyLine(draw_img, [self.line], True, cv.CV_RGB(0, 255, 0) )

        cv.ShowImage( "Contours", draw_img )
        cv.WaitKey()
        sys.exit(1)
    
    def run(self):
        # No code should modify this
        self.image = cv.LoadImage(self.fn)
        if not self.image:
            raise Exception('Failed to load %s' % self.fn)
        ret = LinerBase.run(self)
        
        if self.show:
            self.show_liner()
        
        return ret

'''
Liner the operates in a directory of tiles instead of a single image
'''
class TileLiner(LinerBase):
    def __init__(self, *args, **kwargs):
        LinerBase.__init__(self, *args, **kwargs)
        
    def get_ref(self):
        pass
    
    def get_working(self):
        pass

def liner(*args, **kwargs):
    '''Given a filename w/ target image, a line tuple, and a reference rectangle ROI, return a polygon near the line'''
    return SimpleLiner(*args, **kwargs).run()
