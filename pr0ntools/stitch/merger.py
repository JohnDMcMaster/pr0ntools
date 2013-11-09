'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools import execute
from pr0ntools.temp_file import ManagedTempFile
import os.path
import os

def print_debug(s = ''):
    pass

class Merger:
    def __init__(self, files):
        self.files = files
        self.pto = None
        
    def run(self, to_pto = False):
        from pr0ntools.stitch.pto.project import PTOProject
        
        others = self.files
        pto = self.pto

        '''Take in a list of pto files and merge them into pto'''
        if to_pto:
            pto_temp_file = self.pto.get_a_file_name()
        else:
            pto_temp_file = ManagedTempFile.get(None, ".pto")

        args = ["pto_merge"]
        args.append("--output=%s" % pto_temp_file)

        # Possible this is still empty
        if pto.file_name and os.path.exists(pto.file_name):
            args.append(pto.file_name)
        for other in others:
             args.append(other.get_a_file_name())
    
        print_debug(args)

        rc = execute.without_output(args)
        # go go go
        if not rc == 0:
            print
            print
            print
            #print 'Output:'
            #print output
            print 'rc: %d' % rc
            if rc == 35072:
                # ex: empty projects seem to cause this
                print 'Out of memory, expect malformed project file'
            raise Exception('failed pto_merge')

        if not os.path.exists(str(pto_temp_file)):
            raise Exception('Output file missing: %s' % (pto_temp_file,))

        if to_pto:
            self.pto.reopen()
            return self.pto
        else:
            return PTOProject.from_temp_file(pto_temp_file)


