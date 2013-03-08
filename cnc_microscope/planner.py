#!/usr/bin/python
'''
pr0ncnc: IC die image scan
Copyright 2010 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import sys
import time
import math
import numpy
import numpy.linalg
import os
from config import config
import copy
import shutil

VERSION = '0.1'

ACTION_GCODE = 1
ACTION_RENAME = 2
ACTION_JSON = 3

dry_run = False
# Coordinate seems to be accurate enough and more intuitive to work with
include_rowcol = False
include_coordinate = True
    


def drange(start, stop, step, inclusive = False):
    r = start
    if inclusive:
        while r <= stop:
            yield r
            r += step
    else:
        while r < stop:
            yield r
            r += step

def drange_at_least(start, stop, step):
    '''Garauntee max is in the output'''
    r = start
    while True:
        yield r
        if r > stop:
            break
        r += step

# tolerance drange
# in output if within a delta
def drange_tol(start, stop, step, delta = None):
    '''Garauntee max is in the output'''
    if delta is None:
        delta = step * 0.05
    r = start
    while True:
        yield r
        if r > stop:
            break
        r += step

'''
I'll move this to a JSON, XML or something format if I keep working on this

Canon SD630

15X eyepieces
    Unitron WFH15X
Objectives
    5X
    10X
    20X
    40X
    
Intel wafer
upper right: 0, 0, 0
lower left: 0.2639,0.3275,-0.0068

'''

'''
class CameraResolution:
    width = 1280
    height = 1024
    pictures = 500

class Camera:
    vendor = "canon"
    model = "SD630"
    resolutions = list()
    memory = None
    
    def __init__():
        #resolutions.append(
        set_memory("4GB")

    def set_memory(s):
        memory = 4000000000
'''

class FocusLevel:
    # Assume XY isn't effected by Z
    eyepiece_mag = None
    objective_mag = None
    # Not including digital
    camera_mag = None
    # Rough estimates for now
    # The pictures it take are actually slightly larger than the view area I think
    # Inches, or w/e your measurement system is set to
    x_view = None
    y_view = None
    
    def __init__(self):
        pass

class PlannerAxis:
    def __init__(self, name,
                # Desired image overlap
                # Actual may be greater if there is more area
                # than minimum number of pictures would support
                req_overlap_percent, 
                # How much the imager can see (in um)
                view,
                # Actual sensor dimension may be oversampled, scale down as needed
                imager_width, imager_scalar,
                # start and end absolute positions (in um)
                # Inclusive such that 0:0 means image at position 0 only
                start, end):
        # How many the pixels the imager sees after scaling
        # XXX: is this global scalar playing correctly with the objective scalar?
        self.view_pixels = imager_width * imager_scalar
        
        self.name = name
        '''
        The naming is somewhat bad on this as it has an anti-intuitive meaning
        
        Proportion of each image that is unique from previous
        Overlap of 1.0 means that images are all unique sections
        Overlap of 0.0 means never move and keep taking the same spot
        '''
        self.req_overlap_percent = req_overlap_percent
        
        self.start = start
        # Requested end, not necessarily true end
        self.req_end = end
        self.end = end
        if self.delta() < view:
            print 'Axis %s: delta %0.3f < view %0.3f, expanding end' % (self.name, self.delta(), view)
            self.end = start + view
        self.view = view

    def delta(self):
        '''Total distance that will actually be imaged'''
        return self.end - self.start + 1
                
    def req_delta(self):
        '''Total distance that needs to be imaged (ie requested)'''
        return self.req_end - self.start + 1
                
    def delta_pixels(self):
        return self.images_ideal() * self.view_pixels
        
    def images_ideal(self):
        '''
        Always 1 non-overlapped image + the overlapped images
        (can actually go negative though)
        Remaining distance from the first image divided by
        how many pixels of each image are unique to the previously taken image when linear
        '''
        if self.req_delta() <= self.view:
            return 1.0 * self.req_delta() / self.view
        ret = 1.0 + (self.req_delta() - self.view) / (self.req_overlap_percent * self.view)
        if ret < 0:
            raise Exception('bad number of idea images %s' % ret)
        return ret
    
    def images(self):
        '''How many images should actually take after considering margins and rounding'''
        ret = int(math.ceil(self.images_ideal()))
        if ret < 1:
            print self.images_ideal()
            raise Exception('Bad number of images %d' % ret)
        return ret
    
    def step(self):
        '''How much to move each time we take the next image'''
        '''
        Note that one picture has wider coverage than the others
        Thus its treated specially and subtracted from the remainder
        
        It is okay for the second part to be negative since we could
        try to image less than our sensor size
        However, the entire quantity should not be negative
        '''
        # Note that we don't need to adjust the initial view since its fixed, only the steps
        # self.images_to_take = 1.0 + (self.delta() - self.view) / self.step_size_calc
        images_to_take = self.images()
        if images_to_take == 1:
            return self.delta()
        else:
            return (self.delta() - self.view) / (images_to_take - 1.0)
        
    def step_percent(self):
        '''Actual percentage we move to take the next picture'''
        # Contrast with requested value self.req_overlap_percent
        return self.step() / self.view
        
    #def overlap(self):
    #    '''Actual percentage of each image that is unique when linearly stepping'''
            
class Planner:
    def __init__(self, rconfig_in):
        # FIXME: this is better than before but CTypes pickle error from deepcopy
        #self.rconfig = copy.deepcopy(rconfig)
        self.rconfig = copy.copy(rconfig_in)
        rconfig = self.rconfig
        obj_config = rconfig.obj_config
        self.progress_cb = rconfig.progress_cb
    
        if rconfig.scan_config is None:
            rconfig.scan_config = config.get_scan_config()
        scan_config = rconfig.scan_config

        scan_config['computed'] = dict()
        scan_config['computed']['x'] = dict()
        scan_config['computed']['y'] = dict()
        
        ideal_overlap = 2.0 / 3.0
        if 'overlap' in scan_config:
            ideal_overlap = float(scan_config['overlap'])
        # Maximum allowable overlap proportion error when trying to fit number of snapshots
        #overlap_max_error = 0.05
        
        focus = FocusLevel()
        self.focus = focus
        try:
            focus.eyepiece_mag = float(config['eyepiece'][0])
        except:
            focus.eyepiece_mag = 1.0
        focus.objective_mag = float(obj_config['mag'])
        focus.camera_mag = float(config['imager']['mag'])
        # FIXME: this needs a baseline and scale it
        focus.x_view = float(obj_config['x_view'])
        focus.y_view = float(obj_config['y_view'])
    
        self.even_xy_backlash = True
        
        '''
        Planar test run
        plane calibration corner ended at 0.0000, 0.2674, -0.0129
        '''
    
        self.x = PlannerAxis('X', ideal_overlap, focus.x_view, 
                    float(config['imager']['width']), float(config['imager']['scalar']),
                    float(scan_config['start']['x']), float(scan_config['end']['x']))
        self.y = PlannerAxis('Y', ideal_overlap, focus.y_view,
                    float(config['imager']['height']), float(config['imager']['scalar']),
                    float(scan_config['start']['y']), float(scan_config['end']['y']))
        
        self.parse_points()
        if not self.z:
            print 'WARNING: crudely removing Z since its not present or broken'
        self.parse_focus_stack()
        
        print 'X %f to %f, Y %f to %f' % (self.x.start, self.x.end, self.y.start, self.y.end)
        print 'Ideal overlap: %f, actual X %g, Y %g' % (ideal_overlap, self.x.step_percent(), self.y.step_percent())
        scan_config['computed']['x']['overlap']  = self.x.step_percent()
        scan_config['computed']['y']['overlap']  = self.x.step_percent()
        print 'full x delta: %f, y delta: %f' % (self.x.delta(), self.y.delta())
        print 'view x: %f, y: %f' % (focus.x_view, focus.y_view)
            
        if self.z:
            self.z_backlash = float(config['stage']['z_backlash'])
        else:
            self.z_backlash = None
    
        #self.x_overlap = self.x.step() / focus.x_view
        #self.y_overlap = self.y.step() / focus.y_view
        #print 'step x: %g, y: %g' % (self.x.step(), self.y.step())
        '''
        expect = 100, actual = 100 => 100 % efficient
        expect = 100, actual = 200 => 50 % efficient        
        '''
        #print 'X overlap actual %g vs ideal %g, %g efficient' % (
        #        self.x_overlap, ideal_x_overlap, ideal_x_overlap / self.x_overlap * 100.0 )
        #print 'Y overlap actual %g vs ideal %g, %g efficient' % (
        #        self.y_overlap, ideal_y_overlap, ideal_y_overlap / self.y_overlap * 100.0 )

        # A true useful metric of efficieny loss is how many extra pictures we had to take
        # Maybe overhead is a better way of reporting it
        ideal_n_pictures = self.x.images_ideal() * self.y.images_ideal()
        expected_n_pictures = self.x.images() * self.y.images()
        print 'Ideally taking %g pictures (%g X %g) but actually taking %d (%d X %d), %g efficient' % (
                ideal_n_pictures, self.x.images_ideal(), self.y.images_ideal(), 
                expected_n_pictures, self.x.images(), self.y.images(),
                ideal_n_pictures / expected_n_pictures * 100.0)
        
        if self.z and self.others:
            self.calc_normal()
        else:
            print 'Not calculating normal (z %s, others %s)' % (self.z, self.others)
        
        self.getPointsExInit()
    
        # Try actually generating the points and see if it matches how many we thought we were going to get
        self.pictures_to_take = self.getNumPoints()
        if self.pictures_to_take != expected_n_pictures:
            print 'Going to take %d pictures but thought was going to take %d pictures (x %d X y %d)' % (self.pictures_to_take, expected_n_pictures, self.x.images(), self.y.images())
            print 'Points:'
            for p in self.getPoints():
                print '    ' + str(p)
            raise Exception('Fail')
        self.pictures_taken = 0
        self.actual_pictures_taken = 0
        self.notify_progress(None, True)

    def __del__(self):
        pass
        
    def parse_points(self):
        self.z = True

        scan_config = self.rconfig.scan_config
        if scan_config is None:
            raise Exception('Missing scan parameters')
        
        try:
            self.z_start = float(scan_config['start']['z'])
        except:
            print 'Failed to find z start, disabling Z'
            self.z_start = None
            self.z = False
        self.start = [self.x.start, self.y.start, self.z_start]
        
        try:
            self.z_end = float(scan_config['end']['z'])
        except:
            print 'Failed to find z end, disabling Z'
            self.z_end = None
            self.z = False
        self.end = [self.x.end, self.y.end, self.z_end]
    
        if 'others' in scan_config:
            self.others = []
            i = 0
            for p in scan_config['others']:
                l = [float(p['x']), float(p['y']), None]
                print l
                self.others.append(l)
                try:
                    self.others[i][2] = float(p['z'])
                except:
                    self.others[i][2] = None
                    print 'Failed to find z other (%s), disabling Z' % (p)
                    self.z = False
                #self.other = [self.x_other, self.y_other, self.z_other]    
                i += 1
        else:
            print 'Could not find other points'
            #raise Exception('die')
            self.others = None
    
    def parse_focus_stack(self):
        config = self.rconfig.scan_config
        if 'stack' in config:
            stack = config['stack']
            self.num_stack = int(stack['num'])
            self.stack_step_size = int(stack['step_size'])
        else:
            self.num_stack = None
            self.stack_step_size = None
        
    def calc_normal(self):
        '''
        To find the Z on this model, find projection to center line
        Projection of A (position) onto B (center line) length = |A| cos(theta) = A dot B / |B| 
        Should I have the z component in here?  In any case it should be small compared to others 
        and I'll likely eventually need it
        '''

        '''            
        planar projection

        Given two vectors in plane, create orthagonol basis vectors
        Project vertex onto plane to get vertex coordinates within the plane
        http://stackoverflow.com/questions/3383105/projection-of-polygon-onto-plane-using-gsl-in-c-c

        Constraints
        Linear XY coordinate system given
        Need to project point from XY to UV plane to get Z distance
        UV plane passes through XY origin


        Eh a simple way
        Get plane in a x + b y + c z + d = 0 form
        If we know x and y, should be simple
        d = 0 for simplicity (set plane intersect at origin)

        Three points
            (0, 0, 0) implicit
            (ax, ay, az) at other end of rectangle
            (bx, by, bz) somewhere else on plane, probably another corner
        Find normal vector, simple to convert to equation
            nonzero normal vector n = (a, b, c)
            through the point x0 =(x0, y0, z0)
            n * (x - x0) = 0, 
            yields ax + by + cz + d = 0 
        "Converting between the different notations in 3D"
            http://www.euclideanspace.com/maths/geometry/elements/plane/index.htm
            Convert Three points to normal notation
            N = (p1 - p0) x (p2 - p0)
            d = -N * p02
            where:
                * N = normal to plane (not necessarily unit length)
                * d = perpendicular distance of plane from origin.
                * p0,p1 and p2 = vertex points
                * x = cross product
        '''
        
        def cross(p0, p1, p2):
            # [a - b for a, b in zip(a, b)]
            # cross0 = p1 - p0
            cross0 = [float(t1) - float(t0) for t1, t0 in zip(p1, p0)]
            # cross1 = p2 - p0
            cross1 = [float(t2) - float(t0) for t2, t0 in zip(p2, p0)]
            c = numpy.cross(cross0, cross1)
            n = numpy.linalg.norm(c)
            # Keep pointed up to make things more regular
            if c[2] < 0:
                n *= -1.0
            for i in range(3):
                c[i] /= n
            return c
            
        print 'Calculating normal'
            
        if len(self.others) == 1:
            print 'Single plane case'
            p0 = self.start
            p1 = self.end
            p2 = self.others[0]
            self.normal = cross(p0, p1, p2)
        else:
            print 'Multiple plane case'
            # This is massively inefficient but number of points should be low
            self.normal = [0.0, 0.0, 0.0]
            #ps = [self.start, self.end] + self.others
            n = 0
            '''
            for p0 in ps:
                for p1 in ps:
                    if p1 == p0:
                        continue
                    for p2 in ps:
                        if p2 == p1 or p2 == p0:
                            continue
            '''
            for p0 in [self.start]:
                for p1 in [self.end]:
                    for p2 in self.others:
                        normal = cross(p0, p1, p2)
                        print
                        print 'Computed normal %s' % str(normal)
                        print p0
                        print p1
                        print p2
                        print
                        for i in range(0, 3):
                            self.normal[i] += normal[i]
                        n += 1
                            
            for i in range(0, 3):
                self.normal[i] /= n
        # a x + b y + c z + d = 0 
        # z = -(a x + by) / c
        # dz/dy = -b / c
        self.dz_dy = -self.normal[1] / self.normal[2]
        
        print 'Normal: %s' % str(self.normal)
        
        # Validate the plane mode l is reasonable
        compare = self.others
        #compare = [[4197.88, 236.898, -21.0], [0.0, 4200.0, 28.0]]
        #compare = [[4197.8, 400.0, -26.5], [0.0, 4200.0, 10.0]]
        for p in [self.start, self.end] + compare:
            z = self.calc_z(p[0], p[1])
            z_expect = p[2]
            d = abs(z - z_expect)
            thresh = 5.0
            thresh_absolute = 500
            print 'Point %s: calc %g, error %g' % (str(p), z, d)
            if d > thresh:
                print 'Bad planar solution, difference %g vs threshold %g' % (d, thresh)
                print p
                print 'Computed z: %g, expected z: %g' % (z, z_expect)
                print self.others
                print 'Normal: %s' % str(self.normal)
                if d > thresh_absolute:
                    raise Exception('Bad planar solution')
            
    def notify_progress(self, image_file_name, first = False):
        if self.progress_cb:
            self.progress_cb(self.pictures_to_take, self.pictures_taken, image_file_name, first)

    def comment(self, s = ''):
        if len(s) == 0:
            print
        else:
            print '# %s' % s

    def calc_z(self, cur_x, cur_y):
        if not self.z:
            return None
            
        if False:
            return self.calc_z_simple(cur_x, cur_y)
        else:
            return self.calc_z_planar(cur_x, cur_y)
    
    def calc_z_simple(self, cur_x, cur_y):
        if self.z_start is None or self.z_end is None:
            full_z_delta = None
        else:
            full_z_delta = self.z_end - self.z_start
        #print full_z_delta
    
        center_length = math.sqrt(self.x.end * self.x.end + self.y.end * self.y.end)
        projection_length = (cur_x * self.x.end + cur_y * self.y.end) / center_length
        cur_z = full_z_delta * projection_length / center_length
        # Proportion of entire sweep
        #print 'cur_z: %f, projection_length %f, center_length %f' % (cur_z, projection_length, center_length)
        return cur_z
    
    def calc_z_planar(self, cur_x, cur_y):
        # Plane is through origin, so x0 is (0, 0, 0) and dissapears, same goes for distance d
        # Now we just need to solve the equation for z
        # a x + b y + c z + d = 0 
        # z = -(a x + b y) / c
        cur_z = -(self.normal[0] * cur_x + self.normal[1] * cur_y) / self.normal[2]
        return cur_z
        
    def end_program(self):
        pass
    
    def pause(self, seconds):
        pass

    def write_metadata(self):
        if self.rconfig.dry:
            return
        # Copy config for reference
        self.rconfig.write_to_dir(self.out_dir())
        # TODO: write out coordinate map
        
    def genBasename(self, point, original_file_name):
        suffix = original_file_name.split('.')[1]
        row = point[3]
        col = point[4]
        rowcol = ''
        if include_rowcol:
            rowcol = 'c%04d_r%04d' % (col, row)
        coordinate = ''
        # 5 digits seems quite reasonable
        if include_coordinate:
            coordinate = "x%05d_y%05d" % (point[0] * 1000, point[1] * 1000)
        spacer = ''
        if len(rowcol) and len(coordinate):
            spacer = '__'
        return "%s%s%s%s" % (rowcol, spacer, coordinate, suffix)

    def out_dir(self):
        return os.path.join(config['cnc']['out_dir'], self.rconfig.job_name)
        
    def get_this_file_name(self, stack_mangle = None):
        # row and column, 0 indexed
        #return 'c%04X_r%04X.jpg' % (self.cur_col, self.cur_row)
        if stack_mangle:
            stack_mangle = '_' + stack_mangle
        else:
            stack_mangle = ''
        #extension = '.tif'
        extension = '.jpg'
        r =  'c%04d_r%04d%s%s' % (self.cur_col, self.cur_row, stack_mangle, extension)
        if self.out_dir():
            r = '%s/%s' % (self.out_dir(), r)
        return r
        
    def prepare_image_output(self):
        od = self.out_dir()
        if od:
            if self.rconfig.dry:
                print 'DRY: mkdir(%s)' % od
            else:
                base = config['cnc']['out_dir']
                if not os.path.exists(base):
                    print 'Creating base directory %s' % base
                    os.mkdir(base)
                if os.path.exists(od):
                    if not config['cnc']['overwrite']:
                        raise Exception("Output dir %s already exists" % od)
                    print 'WARNING: overwriting old output'
                    shutil.rmtree(od)
                print 'Creating output directory %s' % od
                os.mkdir(od)
            
    def take_picture(self, image_file_name):
        self.focus_camera()
        self.do_take_picture(image_file_name)
        self.actual_pictures_taken += 1
        self.reset_camera()
    
    def take_pictures(self):
        if self.num_stack:
            n = self.num_stack
            if n % 2 != 1:
                raise Exception('Center stacking requires odd n')
            # how much to step on each side
            n2 = (self.num_stack - 1) / 2
            self.absolute_move(None, None, -n2 * self.stack_step_size)
            
            self.pictures_taken += 1
            
            '''
            Say 3 image stack
            Move down 1 step to start and will have to do 2 more
            '''
            for i in range(n):
                image_file_name = self.get_this_file_name('%02d' % i)
                self.take_picture(image_file_name)
                # Avoid moving at end
                if i != n:
                    self.relative_move(None, None, self.stack_step_size)
                    # we now sleep before the actual picture is taken
                    #time.sleep(3)
                self.notify_progress(image_file_name)
        else:
            image_file_name = self.get_this_file_name()
            self.take_picture(image_file_name)        
            self.pictures_taken += 1
            self.notify_progress(image_file_name)
    
    def do_take_picture(self, file_name = None):
        print 'Dummy: taking picture to %s' % file_name
        pass
        
    def reset_camera(self):
        pass
        
    def focus_camera(self):
        pass
            
    '''
    def gen_x_points(self):
        # We want to step nicely but this simple step doesn't take into account our x field of view
        x_end = self.x.end - self.focus.x_view
        for cur_x in drange_at_least(self.x.start, x_end, self.x.step()):
            yield cur_x
    
    def gen_y_points(self):
        y_end = self.y.end - self.focus.y_view
        for cur_y in drange_at_least(self.y.start, y_end, self.y.step()):
            yield cur_y
    '''
    
    def gen_x_points(self):
        for i in range(self.x.images()):
            yield self.x.start + i * self.x.step()
    
    def gen_y_points(self):
        for i in range(self.y.images()):
            yield self.y.start + i * self.y.step()
    
    def getNumPoints(self):
        pictures_to_take = 0
        #pictures_to_take = len(list(drange_at_least(self.x.start, self.x.end, self.x.step()))) * len(list(drange_at_least(self.y.start, self.y.end, self.y.step())))
        #for cur_x in self.gen_x_points():
        #    for cur_y in self.gen_y_points():
        #        pictures_to_take += 1
        for _p in self.getPoints():
            pictures_to_take += 1
        return pictures_to_take
    
    """
    def getPoints(self):
        '''ret (x, y, z)'''
        for cur_x in self.gen_x_points():
            for cur_y in self.gen_y_points():
                cur_z = self.calc_z(cur_x, cur_y)
                yield (cur_x, cur_y, cur_z)
    """
    
    def getPoints(self):
        for (cur_x, cur_y, cur_z, _row, _col) in self.getPointsEx():
            yield (cur_x, cur_y, cur_z)
    
    """
    def getPointsEx(self):
        '''ret (x, y, z, row, col)'''
        last_x = None
        row = 0
        col = -1
        for point in getPoints():
            if not last_x == point[0]:
                col += 1
                row = 0
            yield (point[0], point[1], point[2], row, col)
            last_x = point[0]
            row += 1
    """

    def getPointsExInit(self):
        if 0:
            self.getPointsExCore = self.getPointsExLoop
        else:
            #self.getPointsEx = self.getPointsExSerpentineXY
            self.getPointsExCore = self.getPointsExSerpentineYX
    
    def validate_point(self, p):
        (cur_x, cur_y, cur_z, cur_row, cur_col) = p
        #print 'xh: %g vs cur %g, yh: %g vs cur %g' % (xh, cur_x, yh, cur_y)
        #do = False
        #do = cur_x > 3048 and cur_y > 3143
        x_tol = 1.0
        y_tol = 1.0
        xmax = cur_x + self.focus.x_view
        ymax = cur_y + self.focus.y_view
        
        fail = False
        
        if cur_col < 0 or cur_col >= self.x.images():
            print 'Col out of range 0 <= %d <= %d' % (cur_col, self.x.images())
            fail = True
        if cur_x < self.x.start - x_tol or xmax > self.x.end + x_tol:
            print 'X out of range'
            fail = True
            
        if cur_row < 0 or cur_row >= self.y.images():
            print 'Row out of range 0 <= %d <= %d' % (cur_row, self.y.images())
            fail = True
        if cur_y < self.y.start - y_tol or ymax > self.y.end + y_tol:
            print 'Y out of range'
            fail = True        
        
        if fail:
            print 'Bad point:'
            print '  X: %g' % cur_x
            print '  Y: %g' % cur_y
            print '  Z: %s' % str(cur_z)
            print '  Row: %g' % cur_row
            print '  Col: %g' % cur_col
            raise Exception('Bad point (%g + %g = %g, %g + %g = %g) for range (%g, %g) to (%g, %g)' % (
                    cur_x, self.focus.x_view, xmax,
                    cur_y, self.focus.y_view, ymax,
                    self.x.start, self.y.start,
                    self.x.end, self.y.end))
    
    def getPointsEx(self):
        for p in self.getPointsExCore():
            self.validate_point(p)
            yield p
    
    
    # Simpler and less backlash issues
    # However, takes longer as  we have to go back to the other side
    def getPointsExLoop(self):
        col = 0
        for cur_x in self.gen_x_points():
            row = 0
            for cur_y in self.gen_y_points():
                cur_z = self.calc_z(cur_x, cur_y)
                yield (cur_x, cur_y, cur_z, row, col)
                row += 1
            col += 1
    
    # Has higher throughput but more prone to backlash issue
    def getPointsExSerpentineXY(self):
        y_list_active = [x for x in self.gen_y_points()]
        y_list_next = list(y_list_active)
        y_list_next.reverse()
        col = 0
        forward = True
        for cur_x in self.gen_x_points():
            if forward:
                row = 0
            else:
                row = len(y_list_active) - 1
            for cur_y in y_list_active:
                cur_z = self.calc_z(cur_x, cur_y)
                yield (cur_x, cur_y, cur_z, row, col)
                if forward:
                    row += 1
                else:
                    row -= 1
            # swap direction
            temp = y_list_active
            y_list_active = y_list_next
            y_list_next = temp
            col += 1
            forward = not forward
            
    def getPointsExSerpentineYX(self):
        x_list_active = [x for x in self.gen_x_points()]
        x_list_next = list(x_list_active)
        x_list_next.reverse()
        row = 0
        forward = True
        for cur_y in self.gen_y_points():
            if forward:
                col = 0
            else:
                col = len(x_list_active) - 1
            for cur_x in x_list_active:
                cur_z = self.calc_z(cur_x, cur_y)
                yield (cur_x, cur_y, cur_z, row, col)
                if forward:
                    col += 1
                else:
                    col -= 1
            # swap direction
            temp = x_list_active
            x_list_active = x_list_next
            x_list_next = temp
            row += 1
            forward = not forward
    
    # Its actually less than this but it seems it takes some stepping
    # to get it out of the system
    def x_backlash(self):
        return 50
    def y_backlash(self):
        return 50
        
    def run(self):
        print
        print
        print
        self.comment('Generated by pr0ncnc %s on %s' % (VERSION, time.strftime("%d/%m/%Y %H:%M:%S")))
        focus = self.focus
        net_mag = focus.objective_mag * focus.eyepiece_mag * focus.camera_mag
        self.comment('objective: %f, eyepiece: %f, camera: %f, net: %f' % (focus.objective_mag, focus.eyepiece_mag, focus.camera_mag, net_mag))
        self.comment('x size: %f um / %d pix, y size: %f um / %d pix' % (self.x.delta(), self.x.delta_pixels(), self.y.delta(), self.y.delta_pixels()))
        self.comment('x fov: %f, y fov: %f' % (focus.x_view, focus.y_view))
        self.comment('x_step: %f, y_step: %f' % (self.x.step(), self.y.step()))
        
        z_backlash = self.z_backlash
        if z_backlash:
            if self.dz_dy > 0:
                # Then decrease and increase
                self.comment('increasing dz/dy backlash normalization')
                #relative_move(0.0, 0.0, -z_backlash)
                #relative_move(0.0, 0.0, z_backlash)
            else:
                # Then increase then decrease
                self.comment('decreasing dz/dy backlash normalization')
                #relative_move(0.0, 0.0, z_backlash)
                #relative_move(0.0, 0.0, -z_backlash)
        self.comment('pictures: %d' % self.pictures_to_take)
        self.comment()

        '''
        prev_x = 0.0
        prev_y = 0.0
        prev_z = 0.0
        '''

        self.prepare_image_output()
        
        if self.even_xy_backlash:
            # Make sure first backlash compensation works as expected
            # And prep y for even step
            self.absolute_move(self.x.start, self.y.start - self.y_backlash())
        
        # Because of the backlash on Z, its better to scan in same direction
        # Additionally, it doesn't matter too much for focus which direction we go, but XY is thrown off
        # So, need to make sure we are scanning same direction each time
        # err for now just easier I guess
        forward = None
        self.cur_col = -1
        # columns
        last_y = None
        for (cur_x, cur_y, cur_z, self.cur_row, self.cur_col) in self.getPointsEx():
        #for cur_x in self.gen_x_points():
            self.cur_x = cur_x
            #self.cur_col += 1
            #self.cur_row = -1
            # rows
            #for cur_y in self.gen_y_points():
            
            #forward = cur_x > last_x
            if last_y is None:
                forward = True
            elif cur_y != last_y:
                forward = not forward

            if self.even_xy_backlash and last_y != cur_y:
                # Make backlash even
                if forward:
                    # Going forward means we need to back up
                    self.relative_move(-self.x_backlash(), None)
                else:
                    # And otherwise overshoot the other way
                    self.relative_move(self.x_backlash(), None)
            
            if True:
                self.cur_y = cur_y
                '''
                Until I can properly spring load the z axis, I have it rubber banded
                Also, for now assume simple planar model where we assume the third point is such that it makes the plane "level"
                    That is, even X and Y distortion
                '''
        
                #self.cur_row += 1
                first_y = self.cur_row == 0
                z_backlash_delta = 0.0
                if first_y and z_backlash:
                    # Reposition z to ensure we aren't getting errors from axis backlash
                    # Taking into account y slant to make sure we will be going in the same direction
                    # z increasing as we scan along y?
                    if self.dz_dy > 0:
                        # Then decrease and increase
                        #self.comment('increasing dz/dy backlash normalization')
                        z_backlash_delta = -z_backlash
                    else:
                        # Then increase then decrease
                        #self.comment('decreasing dz/dy backlash normalization')
                        z_backlash_delta = z_backlash

                print
                cur_z = self.calc_z(cur_x, cur_y)
                # print cur_z
                # print 'full_z_delta: %f, z_start %f, z_end %f' % (full_z_delta, z_start, z_end)
                self.comment('forward %d, (%f, %f, %s)' % (forward, cur_x, cur_y, str(cur_z)))

                #if cur_z < z_start or cur_z > z_end:
                #    print 'cur_z: %f, z_start %f, z_end %f' % (cur_z, z_start, z_end)
                #    raise Exception('z out of range')
                '''
                x_delta = cur_x - prev_x
                y_delta = cur_y - prev_y
                if self.z:
                    z_delta = cur_z - prev_z
        
                z_param = None
                if self.z:
                    z_param = z_delta + z_backlash_delta
                '''
                #self.relative_move(x_delta, y_delta, z_param)
                self.absolute_move(cur_x, cur_y, cur_z)
                if z_backlash_delta:
                    self.relative_move(0.0, 0.0, -z_backlash_delta)
                self.take_pictures()
                '''
                prev_x = cur_x
                prev_y = cur_y
                prev_z = cur_z
                '''
                first_y = False

            '''
            if forward:
                for cur_y in range(y_start, y_end, y_step):
                    inner_loop()
            else:
                for cur_y in range(y_start, y_end, y_step):
                    inner_loop()
            '''
            #raise Exception('break')
            last_y = cur_y

        self.cur_x = cur_x
        self.cur_y = cur_y
        self.home()
        self.end_program()

        print
        print
        print
        #self.comment('Statistics:')
        #self.comment('Pictures: %d' % pictures_taken)
        if not self.pictures_taken == self.pictures_to_take:
            raise Exception('pictures taken mismatch (taken: %d, to take: %d)' % (self.pictures_to_take, self.pictures_taken))
            
        self.write_metadata()
        
    def home(self):
        self.relative_move(-self.cur_x, -self.cur_y)

    def relative_move(self, x, y, z = None):
        if x is None:
            x = 0.0
        if y is None:
            y = 0.0
        if z is None:
            z = 0.0
        print 'DRY: relative move to (%f, %f, %f)' % (x, y, z)

    def absolute_move(self, x, y, z = None):
        print 'DRY: absolute move to (%s, %s, %s)' % (str(x), str(y), str(z))
    
    @staticmethod
    def get(rconfig):
        if not rconfig.dry:
            return ControllerPlanner(rconfig)
        else:
            print "***DRY RUN***"
            #return DryPlanner(rconfig)
            return Planner(rconfig)
    
class DryPlanner(Planner):
    def __init__(self, **args):
        Planner.__init__(self, **args)
    
class GCodePlanner(Planner):
    '''
    M7 (coolant on): tied to focus / half press pin
    M8 (coolant flood): tied to snap picture
        M7 must be depressed first
    M9 (coolant off): release focus / picture
    '''
    
    def __init__(self, **args):
        Planner.__init__(self, **args)

    def do_take_picture(self, file_name):
        self.line('M8')
        self.pause(3)

    def reset_camera(self):
        # original needed focus button released
        self.line('M9')
    
    def absolute_move(self, x, y, z = None):
        self.do_move('G90', x, y, z)

    def relative_move(self, x, y, z = None):
        if not x and not y and not z:
            self.line('(omitted G91 for 0 move)')
            return
        self.do_move('G91', x, y, z)

    def do_move(self, code, x, y, z):
        x_part = ''
        if x:
            x_part = ' X%lf' % (x)
        y_part = ''
        if y:
            y_part = ' Y%lf' % (y)
        z_part = ''
        if z:
            z_part = ' Z%lf' % (z)

        self.line('%s G1%s%s%s F3' % (code, x_part, y_part, z_part))

    def comment(self, s = ''):
        if len(s) == 0:
            self.line()
        else:
            self.line('(%s)' % s)

    def focus_camera(self):
        self.line('M7')
        self.pause(2)

    # What was this?
    '''
    def fix_focus(self):
        # And just don't 
        #focus_camera()
        pass
    '''

    def line(self, s = ''):
        print s

    def end_program(self):
        self.line()
        self.line('(Done!)')
        #self.line('M2')

    def home(self):
        self.absolute_move(0, 0, 0)
        
'''
Live control using an active Controller object
'''
class ControllerPlanner(Planner):
    def __init__(self, rconfig):
        Planner.__init__(self, rconfig)
        self.controller = rconfig.controller
        self.imager = rconfig.imager

    def do_take_picture(self, file_name):
        #self.line('M8')
        #self.pause(3)
        # TODO: add this in once I move over to the windows machine
        # Give it some time to settle
        if self.imager:
            '''
            At full res this takes a while to settle
            all settings, including resolution, seem to be getting inherited from AmScope program which works fine for me
            '''
            #print 'test'
            #time.sleep(4.5)
            # allows for better cooling, motor is getting hot
            #time.sleep(15)
            time.sleep(6)
            self.imager.take_picture(file_name)
        else:
            time.sleep(0.5)

    def reset_camera(self):
        # original needed focus button released
        #self.line('M9')
        # suspect I don't need anything here
        pass
    
    def absolute_move(self, x, y, z = None):
        if not x is None:
            self.controller.x.set_pos(x)
        if not y is None:
            self.controller.y.set_pos(y)
        if not z is None:
            self.controller.z.set_pos(z)
    
    def relative_move(self, x, y, z = None):
        if not x and not y and not z:
            print 'Omitting 0 move'
            return
        if x:
            self.controller.x.jog(x)
        if y:
            self.controller.y.jog(y)
        if z:
            self.controller.z.jog(z)

    def focus_camera(self):
        # no z axis control right now
        pass
        
    def end_program(self):
        print 'Done!'

    def home(self):
        self.controller.home()
        
