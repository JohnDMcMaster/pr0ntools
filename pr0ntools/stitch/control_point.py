'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''
from pr0ntools.temp_file import ManagedTempFile
from pr0ntools.temp_file import ManagedTempDir
from pr0ntools.execute import Execute, without_output
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
        (rc, output) = (without_output(command, args), '')
        if not rc == 0:
            print
            print
            print
            print 'output:\n%s' % output

            raise Exception('Bad rc: %d' % rc)
        
        # We return PTO object, not string
        return PTOProject.from_temp_file(project_file)


class AutopanoAJ:    
    def __init__(self):
        # For compatibility, I'd like to remove this entirely with default False
        self.invalidate_on_ransac = True
        self.print_output = False
    '''
    autopano.exe /f /tmp/file1.jpg /tmp/file2.jpg /project:hugin 
    Example stitch command
    Will result in .pto in being in /tmp though
    
    Eh its pretty unreliable (wine issue?) if we don't put pix in current dir
    Easiest way to accomplish this without copying is to create temp dir and symlink
    we are editing the files anyway, so not a big deal
    '''
    def generate_core(self, image_file_names):
        command = "autopanoaj"
        args = list()
        final_project_file = ManagedTempFile.get(None, ".pto")
        temp_dir = ManagedTempDir.get()
        
        # default is .oto
        args.append("/project:hugin")
        # Use image args instead of dir
        
        # Images
        for image_file_name in image_file_names:
            # args.append(image_file_name.replace("/tmp/", "Z:\\tmp\\"))
            image_file_name = os.path.realpath(image_file_name)

            link_file_name = os.path.join(temp_dir.file_name, os.path.basename(image_file_name))
            dbg('Linking %s -> %s' % (link_file_name, image_file_name))
            os.symlink(image_file_name, link_file_name)

        # go go go
        (rc, output) = Execute.with_output(command, args, temp_dir.file_name, self.print_output)
        print 'Finished control point pair execution'
        if not rc == 0:
            print
            print
            print
            print 'output:\n%s' % output

            if output.find('This application has requested the Runtime to terminate it in an unusual way'):
                print 'WARNING: skipping crash'
                return None
            
            raise Exception('Bad rc: %d' % rc)
        
        '''
        Doesn't like the match:
        PICTURE PAIRS VALIDATION 
          Pair (  0,  1)
            Ransac (In : 21, Out : 4, Residu : 4.43799)
            REMOVED
          Timing : 583.7 us
        '''
        if output.find('REMOVED') >= 0:
            # This is normal for > 2 image projects
            # Usually for 2 images this indicates that it removed all control points
            # FIXME: it would be better to check the output control point list than check here
            print 'WARNING: RANSAC invalidated control points'
            if self.invalidate_on_ransac:
                return None
        
        output_file_name = os.path.join(temp_dir.file_name, "panorama0.pto")
        
        '''
        This happens occassionally, not sure why
        Seems for some reason there is a delay getting the file written out
        '''
        tstart = time.time()
        i = 0
        while time.time() - tstart < 10.0:
            if os.path.exists(output_file_name):
                if i > 0:
                    print 'Yay!  Found output file after %0.2f sec' % (time.time() - tstart,)
                break
            if i == 0:
                print 'WARNING: missing output pto file: %s' % output_file_name
            time.sleep(0.05)
            i += 1
        else:
            print 'WARNING: gave up looking for pto file: %s' % output_file_name
            return None
        
        # We return PTO object, not string
        # Ditch the gen file because its unreliable
        shutil.move(output_file_name, final_project_file.file_name)
        f = open(final_project_file.file_name, 'r')
        project_text = f.read()
        # Under WINE, do fixup
        # #-imgfile 2816 704 "Z:\tmp\pr0ntools_471477ADA1679A2E\pr0ntools_3CD1C0B1BB218E40.jpg"
        project_text = project_text.replace('Z:\\', '/').replace('\\', '/')
        for image_file_name in image_file_names:
            link_file_name = os.path.join(temp_dir.file_name, os.path.basename(image_file_name))
            dbg('Replacing %s -> %s' % (link_file_name, image_file_name))
            project_text = project_text.replace(link_file_name, image_file_name)

        if False:
            
            print
            print 'Raw control point project (after symbolic link and WINE file name substitution)'
            print
            print
            print project_text
            print
            print
            print
        f.close()
        f = open(final_project_file.file_name, 'w')
        f.write(project_text)
        project = PTOProject.from_temp_file(final_project_file)
        return project
        
        

# This might be removed soon as I'm not sure it does much
# or at least the problem it solved could now be solved simpler now that I have a PTO object
def ajpto2pto_text(pto_str, sub_image_0_file, sub_image_1_file, sub_image_0_x_delta, sub_image_0_y_delta, sub_to_real, load_images = True):
    '''Take in an old style autopanoaj project and return a .pto object'''
    return ajpto2pto_text_generic(pto_str, (sub_image_0_file, sub_image_1_file), sub_image_0_x_delta, sub_image_0_y_delta, sub_to_real, load_images)

def ajpto2pto_text_simple(pto_str, load_images = True):
    return ajpto2pto_text_generic(pto_str, None, None, None, None, load_images)

def ajpto2pto_text_generic(pto_str, sub_image_files, x_delta, y_delta, sub_to_real, load_images = True):
    '''
    Convert .oto text (like from autopanoaj) to a .pto
    
    XXX: there's a friggen .pto option
    why aren't I using that...
    
    Should seperate parsing the project and shifting the data
    This function has multiple issues
    '''
    # image index to subimage file name link (not symbolic link)
    index_to_sub_file_name = dict()
    imgfile_index = 0
    part_pair_index = 0
    
    ret = PTOProject.from_simple()
    
    # Actually I think really is a .pto, just in a less common format
    for line in pto_str.split('\n'):
        if len(line.strip()) == 0:
            continue
        # This type of line is gen by autopano-sift-c
        elif line[0] == 'c':
            # c n0 N1 x1142.261719 y245.074757 X699.189408 Y426.042661 t0
            # Adjust the image towards the upper left hand corner
            if x_delta or y_delta:
                # Parse
                parts = line.split()
                if len(parts) < 7:
                    raise Exception('bad line: %s' % line)
                if not parts[1] == 'n0':
                    print line
                    print parts[1]
                    raise Exception('n0 mismatch')
                if not parts[2] == 'N1':
                    print line
                    print parts[2]
                    raise Exception('N1 mismatch')
                
                x = float(parts[3][1:])                                
                y = float(parts[4][1:])
                X = float(parts[5][1:])
                Y = float(parts[6][1:])
    
                #sub_image_1_x_end = image_1.width()
                #sub_image_1_y_end = image_1.height()
    
                # FIXME: still the two file optimized version
                # Assumes that it only has to compare one since it knows the other
                if index_to_sub_file_name[0] == sub_image_files[0].file_name:
                    # normal adjustment
                    x += x_delta
                    y += y_delta
                elif index_to_sub_file_name[1] == sub_image_files[0].file_name:
                    # they got flipped
                    X += x_delta
                    Y += y_delta
                else:
                    print index_to_sub_file_name
                    print 'index_to_sub_file_name[0]: %s' % repr(index_to_sub_file_name[0])
                    print 'index_to_sub_file_name[1]: %s' % repr(index_to_sub_file_name[1])
                    print 'sub_image_0_file: %s' % repr(sub_image_files[0])
                    print 'sub_image_1_file: %s' % repr(sub_image_files[1])
                    raise Exception("confused")
    
                # Write
                new_line = "c n0 N1 x%f y%f X%f Y%f t0" % (x, y, X, Y)
                #out += new_line + '\n'
                ret.add_control_point_line_by_text(new_line)
            else:
                ret.add_control_point_line_by_text(line)
        elif line[0] == 'p':
            #ret.panorama_line = PanoramaLine(line, ret)
            ret.set_pano_line_by_text(line)
        # This type of line is generated by pto_merge
        elif line[0] == 'o':
            '''
            #-imgfile 1632 408 "/tmp/pr0ntools_6691335AD228382E.jpg"
            o f0 y+0.000000 r+0.000000 p+0.000000 u20 d0.000000 e0.000000 v70.000000 a0.000000 b0.000000 c0.000000
            to
            i w2816 h704 f0 a0 b-0.01 c0 d0 e0 p0 r0 v180 y0  u10 n"/tmp/pr0ntools_6691335AD228382E.jpg"
            '''
            new_line = ''
            new_line += 'i'
            # default FOV
            new_line += ' v51'
            
            orig_fn = index_to_sub_file_name[part_pair_index]
            if sub_to_real:
                new_fn = sub_to_real[orig_fn]
            else:
                new_fn = orig_fn
            dbg('Replacing %s => %s' % (orig_fn, new_fn))
            new_line += ' n"%s"' % new_fn
            
            part_pair_index += 1
            dbg('new line: %s' % new_line)
            ret.add_image_line_by_text(new_line)
        # These lines are generated by autopanoaj
        # The comment line is literally part of the file format, some sort of bizarre encoding
        # #-imgfile 2816 704 "/tmp/pr0ntools_2D24DE9F6CC513E0/pr0ntools_6575AA69EA66B3C3.jpg"
        # o f0 y+0.000000 r+0.000000 p+0.000000 u20 d0.000000 e0.000000 v70.000000 a0.000000 b0.000000 c0.000000
        elif line.find('#-imgfile') == 0:
            # Replace pseudo file names with real ones
            new_line = line
            index_to_sub_file_name[imgfile_index] = line.split('"')[1]
            imgfile_index += 1
        elif line.find('#') == 0:
            pass
        else:
            #new_line = line
            dbg('WARNING: discarding unknown line %s' % line)
        #out += new_line + '\n'
    #else:
        #out += line + '\n'

    #ret = PTOProject.from_text(out)
    
    if load_images:
        dbg('Fixing up image lines')
        fixup_image_dim(ret)
    
    return ret


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
        (rc, output) = Execute.with_output(command, args)
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
 
        (rc, output) = Execute.with_output('cpfind', args, print_output=self.print_output)
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
        
        (rc, output) = Execute.with_output('cpclean', args, print_output=self.print_output)
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
        return project

def get_cp_engine(engine=None):
    return {
            'autopano-sift-c': AutopanoSiftC,
            'autopanoaj': AutopanoAJ,
            'panocp': PanoCP,
            None: PanoCP
    }[engine]()
