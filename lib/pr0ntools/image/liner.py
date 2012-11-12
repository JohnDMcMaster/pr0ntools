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
import cv
import argparse        
import sys
import time
import math

def set_dbg(yes):
    global pdbg
    pdbg = yes

pdbg = 1
logf = None
#logf = open('liner.log', 'w')
def dbg(s, level = 1):
    global f
    if level <= pdbg:
        print s
    if logf:
        f.write('%s\n' % s)
    
def linearize(p0, p1):
    m = (p1[1] - p0[1]) / (p1[0] - p0[0])
    b = p0[1] - m * p0[0]
    return (m, b)

def linearized_pgen(p0, p1):
    '''Return a generator that generates points between two points'''
    
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

def vertex_len(p0, p1):
    '''Length of line connecting point p0 to point p1'''
    return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)

def contour_len(contour, closed=False):
    if len(contour) < 2:
        raise ValueError("Bad contour of len %d" % len(contour))
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

    # Needs to at least squiggle back and forth
    if contour_len(contour) < 2 * line_len:
        dbg('  Contour did not meet minimum size', level=2)
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
            dbg('Exception dump:')
            dbg('  vertexi_tail: %d' % vertexi_tail)
            dbg('  vertexi: %d' % vertexi)
            dbg('  len: %d' % len(contour))
            dbg('  indeices: %d' % n_contour_indices())
            raise
        
    dbg('  Best len from %u to %u' % (best_start, best_end), level=3)
    if pdbg > 3:
        for i in xrange(best_start, best_end + 1, 1):
            dbg('    (%dx, %dy)' % (contour[i][0], contour[i][1]))
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
        if pdbg > 3:
            dbg('      n_points: %d (ideal %g)' % (n_points, n_ideal))
        '''
        Skip 0 since previous covers it
        '''
        f = linearized_pgen(p0, p1)
        for n in xrange(1, n_points + 1):
            per = float(n) / n_points
            p = f(per)
            dbg('      split to (%dx, %dy) w/ %g percent' % (p[0], p[1], per * 100), level=3)
            ret.append(p)
    
    if pdbg > 3:
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

def pplane(name, plane):
    print 'Plane %s (%dw X %dh)' % (name, plane.width, plane.height)
    for x in xrange(plane.width):
        for y in xrange(plane.height):
            p = plane[x, y]
            if y % 2 == 1:
                print '(%03d) ' % (p),
        print
    print

def hs_histogram(src, mask=None):
    '''Takes a cvMat and computes a HS histogram (V is dropped)'''
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

    h_bins = 8
    s_bins = 8
    hist_size = [h_bins, s_bins]
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
class Liner():
    def __init__(self, fn, line, ref_polygon, show=False):
        # Interestingly enough doesn't work if its a list
        def polygize(poly):
            return [tuple(map(int, pair)) for pair in poly]
        self.fn = fn
        self.line = polygize(line)
        self.ref_polygon = polygize(ref_polygon)
        self.show = show
        self.ref_hist = None
        self.image = None
            
    def filter(self, contour):
        #return False
        # Reject noise
        if self.contour_area < self.min_area:
            return True
        if self.contour_area > self.max_area:
            return True
        return False
    
    def compute_ref(self):
        '''Compute a reference histogram that matched regions should approximate'''
        (width, height) = cv.GetSize(self.image)
        dest = cv.CreateMat(height, width, cv.CV_8UC3)
        mask8x1 = cv.CreateImage(cv.GetSize(self.image), 8, 1)
        mask8x3 = cv.CreateImage(cv.GetSize(self.image), 8, 3)
        for mask in (mask8x1, mask8x3):
            cv.Zero(mask)
            cv.FillConvexPoly(mask, self.ref_polygon, cv.ScalarAll(255))
        cv.Copy(self.image, dest, mask8x3)
    
        self.ref_hist = hs_histogram(dest, mask8x1)
    
    def compare_ref(self, polygon):
        '''Compare new polygon against the reference polygon histogram'''
        (width, height) = cv.GetSize(self.image)
        dest = cv.CreateMat(height, width, cv.CV_8UC3)
        mask8x1 = cv.CreateImage(cv.GetSize(self.image), 8, 1)
        mask8x3 = cv.CreateImage(cv.GetSize(self.image), 8, 3)
        for mask in (mask8x1, mask8x3):
            cv.Zero(mask)
            cv.FillConvexPoly(mask, polygon, cv.ScalarAll(255))
        cv.Copy(self.image, dest, mask8x3)
        return cv.CompareHist(self.ref_hist, hs_histogram(dest, mask8x1), cv.CV_COMP_CORREL) 
    
    def run(self):
        '''Given a filename w/ target image, a line tuple, and a reference rectangle ROI, return a polygon near the line'''
        start = time.time()
        # No code should modify this
        self.image = cv.LoadImage(self.fn)
        
        fn = self.fn

        self.compute_ref()
        
        best_contour = None
        best_thresh = None
        best_diff = float('inf')
        best_hist_diff = None
        # All contours generated
        total_contours = 0
        # Excluding those filtered out
        checked_contours = 0
        
        # TODO: should try a finer sweep after rough?
        #for g_thresh in xrange(0, 256, 8):
        for g_thresh in xrange(64, 168, 8):
            dbg('', level=2)
            dbg('thres %d, working on %s' % (g_thresh, fn), level=2)
            
            if not self.image:
                raise Exception('Failed to load %s' % fn)
            self.total_area = self.image.width * self.image.height
            # Select this by some metric with tagged features, say smallest - 10%
            self.min_area = 100.0
            self.max_area = self.total_area * 0.9
            dbg('Size: %dw X %dh = %g' % (self.image.width, self.image.height, self.total_area), level=3)
            
            size = cv.GetSize(self.image)
            dbg('Size: %s' % (size,), level=3)
            gray_img = cv.CreateImage( size, 8, 1 )
            storage = cv.CreateMemStorage(0)
            
            cv.CvtColor( self.image, gray_img, cv.CV_BGR2GRAY )
            cv.Threshold( gray_img, gray_img, g_thresh, 255, cv.CV_THRESH_BINARY )
            if 0 and g_thresh == 70:
                dbg('Saving intermediate B&W')
                cv.SaveImage('img_thresh.png', gray_img)
            
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
            
            min_rejected = 0
            max_rejected = 0
            total = 0
            contouri = -1
            for contour in icontours(contour_begin):
                total_contours += 1
                contouri += 1
                self.contour_area = cv.ContourArea(contour)
                if self.filter(contour):
                    continue
                checked_contours += 1
                #if contouri != 5:
                #    continue
                dbg('%d' % contouri, level=2)
                #print '  Points:'
                #print_contour(contour, '    ')
                if pdbg > 1:
                    dbg('  len %f' % contour_len(contour))
                    dbg('  area %f' % self.contour_area)
                this_diff = contour_line_diff(contour, self.line)
                if pdbg > 1:
                    dbg('  diff %f' % this_diff)
                if this_diff >= best_diff:
                    continue
                hist_diff = self.compare_ref(contour)
                # 0.95 was too lose
                if hist_diff < 0.99:
                    if pdbg > 1:
                        dbg("Rejected for poor histogram match")
                    continue
                dbg('New best contour', level=2)
                best_contour = contour
                best_thresh = g_thresh
                best_diff = this_diff
                best_hist_diff = hist_diff
                #draw_contour(contour)
        dbg("Best contour:")
        dbg('  Points: %d' % len(best_contour))
        dbg('  Threshold: %d' % best_thresh)
        dbg('  Best diff: %g' % best_diff)
        dbg('  Hist diff: %g' % best_hist_diff)
        if pdbg > 2:
            print_contour(best_contour, prefix = '  ')
    
        def show_liner():
            if 0:
                draw_img = cv.CreateImage( size, 8, 3 )
                cv.Copy(self.image, draw_img)
            if 0:
                draw_img = cv.CreateImage( size, 8, 1 )
                cv.Zero( draw_img )
                #cv.CvtColor( self.image, draw_img, cv.CV_BGR2GRAY )
            # B&W background but color highlighting
            if 1:
                gray_img = cv.CreateImage( size, 8, 1 )
                draw_img = cv.CreateImage( size, 8, 3 )
                #cv.Copy(self.image, draw_img)
                cv.CvtColor( self.image, gray_img, cv.CV_BGR2GRAY )
                cv.CvtColor( gray_img, draw_img, cv.CV_GRAY2BGR )
            
            '''Takes in list of (contour, color) tuples where contour is iterable for (x, y) tuples'''
            cv.PolyLine(draw_img, [best_contour], True, cv.CV_RGB(255, 0, 0) )
            cv.PolyLine(draw_img, [self.ref_polygon], True, cv.CV_RGB(0, 0, 255) )
            print self.line
            cv.PolyLine(draw_img, [self.line], True, cv.CV_RGB(0, 255, 0) )

            cv.ShowImage( "Contours", draw_img )
            cv.WaitKey()
            sys.exit(1)
        if self.show:
            show_liner()
        
        dbg('Total contours: %d' % total_contours)
        dbg('Checked contours: %d' % checked_contours)
        end = time.time()
        dbg('Liner delta: %0.3f sec' % (end - start,))
        return best_contour
            
    def draw_contour(contour, color=None):
        gray_img = cv.CreateImage( cv.GetSize(self.image), 8, 1 )
        #cv.CvtColor( self.image, gray_img, cv.CV_BGR2GRAY )
        cv.Zero( gray_img )
        # DrawContours(img, contour, external_color, hole_color, max_level [, thickness [, lineType [, offset]]]) -> None
         # in my small example external didn't get value but internal did
        if 0:
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
        else:
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
    
    def draw_color_contours(color_contours, color=None):
        '''Takes in list of (contour, color) tuples where contour is iterable for (x, y) tuples'''
        gray_img = cv.CreateImage( cv.GetSize(self.image), 8, 1 )
        #cv.CvtColor( self.image, gray_img, cv.CV_BGR2GRAY )
        cv.Zero( gray_img )
        for (contour, color) in color_contours:
            cv.PolyLine( gray_img , [contour] , True , color )
        cv.ShowImage( "Contours", gray_img )
        cv.WaitKey()

def liner(*args, **kwargs):
    '''Given a filename w/ target image, a line tuple, and a reference rectangle ROI, return a polygon near the line'''
    return Liner(*args, **kwargs).run()
    