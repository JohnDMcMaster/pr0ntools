'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.temp_file import ManagedTempDir
from pr0ntools.execute import exc_ret_istr
from pr0ntools.stitch.pto.project import PTOProject
from pr0ntools.stitch.pto.util import *
from pr0ntools.stitch.pto.control_point_line import ControlPointLine
from pr0ntools.stitch.pto.image_line import ImageLine
import shutil
import os.path
import time

def dbg(s):
    pass

# clear; rm -f /tmp/*.pto /tmp/*.jpg; pr0nstitch --result=out.jpg *.jpg

"""
class ControlPointGenerator:
    @staticmethod
    def from_string():
        pass

    @staticmethod
    def from_id():
        pass
        
    def generate_core(image_file_names):
        '''
        Input should be a list of either 
        Returns a PTOProject
        '''
        pass

    def generate_by_name(image_file_names):
        '''Takes in a list of image file names'''
        return generate_core(imageFileNames)

    def generate_by_PIL(images):
        '''Takes in a list of TempFilePIL images'''
        return generateControlPointsCore(imageFiles)

class AutopanoAj(ControlPointGenerator):
    os.system("autopanoaj /allinone /project:hugin '/ransac_dist:1.0'")
    os.system("cat %s |sed 's@%s@%s@g' >/tmp/%s" % (project_file, original_dir, image_dir, temp_project_file))
"""

#class ControlPointGenerator:    
class AutopanoSiftC:
    '''
    Example stitch command
    "autopano-sift-c" "--maxmatches" "0" "--maxdim" "10000" "out.pto" "first.png" "second.png"
    '''
    def generate_core(self, image_file_names):
        project_file = ManagedTempFile.get(None, ".pto")

        command = "autopano-sift-c"
        args = list()
        
        # Try to post process them to make them more accurate
        #args.append("--refine")
        
        # Perform RANSAC to try to get bad control points out
        #args.append("--ransac")
        #args.append("on")

        # Unlimited matches
        args.append("--maxmatches")
        args.append("0")
        
        # ?
        #args.append("--maxdim")
        #args.append("10000")

        # Project file
        args.append(project_file.file_name)
        
        # Images
        for image_file_name in image_file_names:
            args.append(image_file_name)

        # go go go
        #(rc, output) = Execute.with_output(command, args)
        (rc, output) = (exc_ret_istr(command, args), '')
        if not rc == 0:
            print
            print
            print
            print 'output:\n%s' % output

            raise Exception('Bad rc: %d' % rc)
        
        # We return PTO object, not string
        return PTOProject.from_temp_file(project_file)

def pto_unsub(src_prj, sub_image_files, deltas, sub_to_real):
    '''
    Transforms a sub-project back into original control point coordinate space using original file names
    Returns a new project file
    src_prj: base project that needs to be transformed
    sub_image_files: tuple specifying original project 0/1 positions
        needed to correctly apply deltas
    deltas: delta to apply to pair_project coordinates to bring back to target (original) project space
        0: x
        1: y
        images are relative to each other
        only has delta within relative image frame, not entire project canvas
    sub_to_real: map of project file names to target (original) project file names
        the output project must use these instead of the original names
    '''
    ret = PTOProject.from_simple()
    
    same_order = True
    # Copy/fix images
    print 'Order check'
    for i, src_il in enumerate(src_prj.get_image_lines()):
        # copy it
        dst_il = ImageLine(str(src_il), ret)
        # fix the name so that it can be merged
        dst_il.set_name(sub_to_real[src_il.get_name()])
        # add it
        ret.add_image_line(dst_il)
        same_order = same_order and sub_image_files[i].file_name == src_il.get_name()
        print '  %d: %s vs %s' % (i, sub_image_files[i].file_name, src_il.get_name())
    
    # Copy/shift control points
    # Should have been filtered out earlier
    if len(src_prj.get_control_point_lines()) == 0:
        raise Exception('No source control point lines')
    for src_cpl in src_prj.get_control_point_lines():
        # copy it
        dst_cpl = ControlPointLine(str(src_cpl), ret)
        # shift to original coordinate space
        if same_order:
            # normal adjustment
            dst_cpl.set_variable('x', src_cpl.get_variable('x') + deltas[0])
            dst_cpl.set_variable('y', src_cpl.get_variable('y') + deltas[1])
        else:
            # they got flipped
            dst_cpl.set_variable('X', src_cpl.get_variable('X') + deltas[0])
            dst_cpl.set_variable('Y', src_cpl.get_variable('Y') + deltas[1])
        # add it
        ret.add_control_point_line(dst_cpl)

    return ret

class ControlPointGeneratorXX:
    '''
    autopano.exe /f /tmp/file1.jpg /tmp/file2.jpg /project:hugin 
    Example stitch command
    Will result in .pto in being in /tmp though
    '''
    def generate_core(self, image_file_names):
        command = "autopanoaj"
        args = list()
        project_file = ManagedTempFile.get(None, ".pto")
        
        # default is .oto
        args.append("/project:hugin")
        # Use image args instead of dir
        args.append("/f");
        args.append('/path:Z:\\tmp')
        
        # Images
        for image_file_name in image_file_names:
            args.append(image_file_name.replace("/tmp/", "Z:\\tmp\\"))

        # go go go
        #(rc, output) = Execute.with_output(command, args)
        rc, output = exc_ret_istr(command, args, print_out=True)
        
        if not rc == 0:
            raise Exception('Bad rc: %d' % rc)
        
        # We return PTO object, not string
        # Ditch the gen file because its unreliable
        shutil.move("/tmp/panorama0.pto", project_file.file_name)
        f = open(project_file.file_name, 'r')
        project_text = f.read()
        # Under WINE, do fixup
        project_text = project_text.replace('Z:\\tmp\\', '/tmp/')
        if 0:
            print
            print
            print
            print project_text
            print
            print
            print
        f.close()
        f = open(project_file.file_name, 'w')
        f.write(project_text)
        return PTOProject.from_temp_file(project_file)

# panotool's cpfind/cpclean
class PanoCP:    
    def __init__(self):
        self.print_output = True
    
    def generate_core(self, img_fns):
        # cpfind (and likely cpclean) trashes absolute file names
        # we need to restore them so that tools recognize the file names
        real_fn_base2full = {}
        
        args = list()
        project = PTOProject.from_default2()
        fn_obj = ManagedTempFile.get(None, ".pto")
        project.set_file_name(fn_obj.file_name)
        
        # Start with cpfind
        args.append("--multirow")
        args.append("--fullscale")
        # output file
        args.append("-o")
        args.append(project.file_name)
        # input file
        args.append(project.file_name)
        
        # Images
        for img_fn in img_fns:
            # xxx: why do we take the realpath?
            real_fn = os.path.realpath(img_fn)
            real_fn_base2full[os.path.basename(real_fn)] = img_fn
            project.add_image(real_fn, def_opt=True)

        project.save()
        print
        print
        print
        print project.get_text()
        print
        print
        print
 
        #(rc, output) = Execute.with_output('cpfind', args, print_output=self.print_output)
        (rc, output) = exc_ret_istr('cpfind', args, print_out=self.print_output)
        
        print 'PanoCP: cpfind done'
        if not rc == 0:
            print
            print
            print
            print 'output:'
            print output
            print
            raise Exception('Bad rc: %d' % rc)
        
        
        # Now run cpclean
        args = list()
        # output file
        args.append("-o")
        args.append(project.file_name)
        # input file
        args.append(project.file_name)
        
        (rc, output) = exc_ret_istr('cpclean', args, print_out=self.print_output)
        print 'PanoCP: cpclean done'
        if not rc == 0:
            print
            print
            print
            print 'output:'
            print output
            print
            raise Exception('Bad rc: %d' % rc)


        project.reopen()
        print 'Fixing image lines...'
        for il in project.image_lines:
            src = il.get_name()
            dst = real_fn_base2full[src]
            print '  %s => %s' % (src, dst)
            il.set_name(dst)
        
        project.set_file_name(None)
        fn_obj = None

        # Will happen if failed to match
        # be optimistic: cpclean work will be wasted but avoids parsing project twice
        if len(project.get_control_point_lines()) == 0:
            print 'WARNING: failed'
            return None
        return project

def get_cp_engine(engine=None):
    return {
            'autopano-sift-c': AutopanoSiftC,
            'panocp': PanoCP,
            None: PanoCP
    }[engine]()
