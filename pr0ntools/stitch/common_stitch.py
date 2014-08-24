'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details

Common code for various stitching strategies
'''

from pr0ntools.image.soften import Softener
from pr0ntools.stitch.control_point import ControlPointGenerator, ajpto2pto_text
from pr0ntools.stitch.pto.project import PTOProject
from pr0ntools.stitch.pto.util import *
from pr0ntools.stitch.remapper import Remapper
from pr0ntools.temp_file import ManagedTempFile
import sys
import json
import traceback

'''
Add failures between images that are very important
The "very important" failures are the one immediatly adjacent in row/col order

{
    "c0021_r0028.jpg": [
        "c0020_r0027.jpg"
    ]
}
'''
'''
class FailedImage:
    def __init__(self, file_name, pos):
        self.fn = file_name
        self.failures = set()

    def add(self, file_name):
        self.failures.add(file_name)
'''
class FailedImages:
    def __init__(self, all_images):
        # JSON object
        self.json = dict()
        self.pairs = 0
        # Set containing all image names
        self.open_list = set(all_images)
        
    def add_failure(self, image_fn_pair):
        self.pairs += 1
        for i in range(2):
            if i == 0:
                primary = image_fn_pair[0]
                against = image_fn_pair[1]
            else:
                primary = image_fn_pair[1]
                against = image_fn_pair[0]
        
            if not primary in self.json:
                failure = list()
            else:
                failure = self.json[primary]
            failure.append(against)
            self.json[primary] = failure
    
    def add_success(self, image_fn_pair):
        for fn in image_fn_pair:
            if fn in self.open_list:
                self.open_list.remove(fn)
    
    def __str__(self):
        return json.dumps(self.json, sort_keys=True, indent=4)

    def pair_count(self):
        return self.pairs
        
    def critical_count(self):
        '''Number of unanchored images'''
        return len(self.open_list)

class CommonStitch:
    def __init__(self):
        self.output_image_file_name = None
        self.project = None
        self.remapper = None
        self.photometric_optimizer = None
        self.cleaner = None
        # Used before init, later ignore for project.file_name
        self.output_project_file_name = None
        self.image_file_names = None
        self.control_point_gen = None

        # Images have predictable separation?
        self.regular = False
        # Only used if regular image
        self.subimage_control_points = True
        
        # TODO: parse these from scan.json
        # and fix scan.json to invert these to match these values
        self.x_overlap = 1.0 / 3.0
        self.y_overlap = 1.0 / 3.0
        
        self.dry = False
        
        # Each filename as the key
        #self.failures = FailedImages()
        self.failures = None

    def set_dry(self, d):
        self.dry = d

    def set_regular(self, regular):
        self.regular = regular

    def set_output_project_file_name(self, file_name):
        self.output_project_file_name = file_name

    def set_output_image_file_name(self, file_name):
        self.output_image_file_name = file_name

    def init_failures(self):
        pass

    def failure_json_w(self):
        print 'Writing failure JSON'
        cc = self.failures.critical_count()
        print '%d pairs failed to make %d images critical' % (self.failures.pair_count(), cc)
        if cc:
            print '******WARNING WARNING WARING******'
            print '%d images are not connected' % cc
            print '******WARNING WARNING WARING******'
        failure_json = {
                'critical_images': cc,
                'failures': self.failures.json,}
                
        open('stitch_failures.json', 'w').write(json.dumps(failure_json, sort_keys=True, indent=4, separators=(',', ': ')))

    def run(self):
        if self.dry:
            print 'Dry run abort'
            return
    
        if not self.output_project_file_name and not self.output_image_file_name:
            raise Exception("need either project or image file")
        #if not self.output_project_file_name:
            #self.project_temp_file = ManagedTempFile.get()
            #self.output_project_file_name = self.project_temp_file.file_name
        print 'Beginning stitch'
        print 'output project file name: %s' % self.output_project_file_name
        print 'output image file name: %s' % self.output_image_file_name
        
        #sys.exit(1)
        self.init_failures()

        # Generate control points and merge them into a master project
        self.control_point_gen = ControlPointGenerator()
        # How many rows and cols to go to each side
        # If you hand took the pictures, this might suit you
        self.project = PTOProject.from_blank()
        if self.output_project_file_name:
            self.project.set_file_name(self.output_project_file_name)
            if os.path.exists(self.output_project_file_name):
                # Otherwise, we merge into it
                print 'WARNING: removing old project file: %s' % self.output_project_file_name
                os.remove(self.output_project_file_name)
        else:
            self.project.get_a_file_name(None, "_master.pto")
        
        self.project.image_file_names = self.image_file_names

        try:
            '''
            Generate control points
            '''
            self.generate_control_points()
    
            print 'Post stitch fixup...'
            optimize_xy_only(self.project)
            fixup_i_lines(self.project)
            fixup_p_lines(self.project)
            if 0:
                center_anchor(self.project)
            
            
            print
            print '***PTO project baseline final (%s / %s) data length %d***' % (self.project.file_name, self.output_project_file_name, len(self.project.get_text()))
            print
            
            self.failure_json_w()
            print
            
            # Make dead sure its saved up to date
            self.project.save()
            # having issues with this..
            if self.output_project_file_name and not self.project.file_name == self.output_project_file_name:
                raise Exception('project file name changed %s %s', self.project.file_name, self.output_project_file_name)
            
            # TODO: missing calc opt size/width/height/fov and crop
            
            # Did we request an actual stitch?
            if self.output_image_file_name:
                print 'Stitching...'
                self.remapper = Remapper(self.project)
                self.remapper.remap(self.output_image_file_name)
            else:
                print 'NOT stitching (common stitch)'
        except Exception as e:
            sys.stdout.flush()
            sys.stderr.flush()
            print
            print 'WARNING: stitch FAILED'
            traceback.print_exc()
            try:
                fn = self.project.file_name + ".failed"
                print 'Attempting to save intermediate result to %s' % fn
                self.project.save_as(fn)
            except:
                print 'WARNING: failed intermediate save'
            raise e

    def control_points_by_subimage(self, pair, image_fn_pair, subimage_factor = None):
        '''Stitch two images together by cropping to restrict overlap'''
        
        # subimage_factor: (y, x) overlap percent tuple or none for default
        # pair: pair of row/col or coordinate positions (used to determine relative positions)
        # (0, 0) at upper left
        # image_fn_pair: pair of image file names
        
        print 'Preparing subimage stitch on %s:%s' % (image_fn_pair[0], image_fn_pair[1])
        '''
        Just work on the overlap section, maybe even less
        '''
        
        images = [PImage.from_file(image_file_name) for image_file_name in image_fn_pair]
        
        '''
        image_0 used as reference
        4 basic situations: left, right, up right
        8 extended: 4 basic + corners
        Pairs should be sorted, which simplifies the logic
        '''
        sub_image_0_x_delta = 0
        sub_image_0_y_delta = 0
        sub_image_1_x_end = images[1].width()
        sub_image_1_y_end = images[1].height()

        if subimage_factor:
            y_overlap = subimage_factor[0]
            x_overlap = subimage_factor[1]
        else:
            x_overlap = self.x_overlap
            y_overlap = self.y_overlap

        # image 0 left of image 1?
        if pair.first.col < pair.second.col:
            # Keep image 0 right, image 1 left
            sub_image_0_x_delta = int(images[0].width() * (1.0 - x_overlap))
            sub_image_1_x_end = int(images[1].width() * x_overlap)
        
        # image 0 above image 1?
        if pair.first.row < pair.second.row:
            # Keep image 0 top, image 1 bottom
            sub_image_0_y_delta = int(images[0].height() * (1.0 - y_overlap))
            sub_image_1_y_end = int(images[1].height() * y_overlap)
        
        '''
        print 'image 0 x delta: %d, y delta: %d' % (sub_image_0_x_delta, sub_image_0_y_delta)
        Note y starts at top in PIL
        '''
        sub_image_0 = images[0].subimage(sub_image_0_x_delta, None, sub_image_0_y_delta, None)
        sub_image_1 = images[1].subimage(None, sub_image_1_x_end, None, sub_image_1_y_end)
        sub_image_0_file = ManagedTempFile.get(None, '.jpg')
        sub_image_1_file = ManagedTempFile.get(None, '.jpg')
        print 'sub image 0: width=%d, height=%d, name=%s' % (sub_image_0.width(), sub_image_0.height(), sub_image_0_file.file_name)
        print 'sub image 1: width=%d, height=%d, name=%s' % (sub_image_1.width(), sub_image_1.height(), sub_image_0_file.file_name)
        #sys.exit(1)
        sub_image_0.image.save(sub_image_0_file.file_name)
        sub_image_1.image.save(sub_image_1_file.file_name)
        
        sub_image_fn_pair = (sub_image_0_file.file_name, sub_image_1_file.file_name)
        # subimage file name symbolic link to subimage file name
        # this should be taken care of inside of control point actually
        #sub_link_to_sub = dict()
        # subimage to the image it came from
        sub_to_real = dict()
        sub_to_real[sub_image_0_file.file_name] = image_fn_pair[0]
        sub_to_real[sub_image_1_file.file_name] = image_fn_pair[1]

        # Returns a pto project object
        fast_pair_project = self.control_point_gen.generate_core(sub_image_fn_pair)
        if fast_pair_project is None:
            print 'WARNING: failed to gen control points @ %s' % repr(pair)
            return None
        oto_text = str(fast_pair_project)
        if 0:
            print oto_text
        # are we actually doing anything useful here?
        # The original intention was to make dead sure we had the right file order
        # but I'm pretty sure its consistent and we don't need to parse the comments
        final_pair_project = ajpto2pto_text(oto_text, sub_image_0_file, sub_image_1_file, sub_image_0_x_delta, sub_image_0_y_delta, sub_to_real)
        
        # Filenames become absolute
        #sys.exit(1)
        return final_pair_project

    def try_control_points_with_position(self, pair, image_fn_pair, subimage_factor = None):
        '''Try to stitch two images together without any (high level) image processing other than cropping'''
        # If images are arranged in a regular grid and we are allowed to crop do it
        if self.regular and self.subimage_control_points:
            return self.control_points_by_subimage(pair, image_fn_pair, subimage_factor)
        # Otherwise run stitches on the full image
        else:
            print 'Full image stitch (not partial w/ regular %d and subimage control %d)' % (self.regular, self.subimage_control_points)
            return self.control_point_gen.generate_core(image_fn_pair)

    # Control point generator wrapper entry
    def generate_control_points_by_pair(self, pair, image_fn_pair):
        ret = self.do_generate_control_points_by_pair(pair, image_fn_pair)
        # If it failed and they were adjacent it is a "critical pair"
        if self.failures and pair.adjacent():
            if ret:
                self.failures.add_success(image_fn_pair)
            else:
                self.failures.add_failure(image_fn_pair)
        return ret
    
    def do_generate_control_points_by_pair(self, pair, image_fn_pair):
        '''high level function uses by sub-stitches.  Given a pair of images make a best effort to return a .pto object'''
        '''
        pair: ImageCoordinatePair() object
        image_fn_pair: tuple of strings
        
        Algorithm:
        First try to stitch normally (either whole image or partial depending on the mode)
        If that doesn't succeed and softening is enabled try up to three times to soften to produce a match
        If that still doesn't produce a decent solution return None and let higher levels deal with
        '''
        soften_iterations = 3
    
        print
        print
        #print 'Generating project for image pair (%s / %s, %s / %s)' % (image_fn_pair[0], str(pair[0]), image_fn_pair[1], str(pair[1]))
        print 'Generating project for image pair (%s, %s)' % (image_fn_pair[0], image_fn_pair[1])
    
        if True:
            # Try raw initially
            print 'Attempting sharp match...'
            ret_project = self.try_control_points_with_position(pair, image_fn_pair)
            if ret_project:
                return ret_project
        
        print 'WARNING: bad project, attempting soften...'

        soften_image_file_0_managed = ManagedTempFile.from_same_extension(image_fn_pair[0])
        soften_image_file_1_managed = ManagedTempFile.from_same_extension(image_fn_pair[1])
        print 'Soften fn0: %s' % soften_image_file_0_managed.file_name
        print 'Soften fn1: %s' % soften_image_file_1_managed.file_name

        softener = Softener()

        for i in xrange(soften_iterations):
            # And then start screwing with it
            # Wonder if we can combine features from multiple soften passes?
            # Or at least take the maximum
            # Do features get much less accurate as the soften gets up there?
        
            print 'Attempting soften %d / %d' % (i + 1, soften_iterations)

            if i == 0:
                softener.run(image_fn_pair[0], soften_image_file_0_managed.file_name)
                softener.run(image_fn_pair[1], soften_image_file_1_managed.file_name)
            else:
                softener.run(soften_image_file_0_managed.file_name)
                softener.run(soften_image_file_1_managed.file_name)            
            
            pair_soften_image_file_names = (soften_image_file_0_managed.file_name, soften_image_file_1_managed.file_name)
            ret_project = self.try_control_points_with_position(pair, pair_soften_image_file_names)
            # Did we win?
            if ret_project:
                # Fixup the project to reflect the correct file names
                text = str(ret_project)
                print
                print 'Before sub'
                print
                print str(ret_project)
                print
                print
                print
                print '%s => %s' % (soften_image_file_0_managed.file_name, image_fn_pair[0])
                text = text.replace(soften_image_file_0_managed.file_name, image_fn_pair[0])
                print '%s => %s' % (soften_image_file_1_managed.file_name, image_fn_pair[1])
                text = text.replace(soften_image_file_1_managed.file_name, image_fn_pair[1])

                ret_project.set_text(text)
                print
                print 'After sub'
                print
                print str(ret_project)
                print
                print
                print
                #sys.exit(1)
                return ret_project

        print 'WARNING: gave up on generating control points!' 
        return None
        #raise Exception('ERROR: still could not make a coherent project!')

