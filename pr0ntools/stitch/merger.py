'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0ntools import execute
from pr0ntools.temp_file import ManagedTempFile
import os.path
from pr0ntools.stitch.pto.util import dbg

class Merger:
    def __init__(self, ptos):
        self.ptos = ptos
        
    def run(self):
        from pr0ntools.stitch.pto.project import PTOProject
        
        '''Take in a list of pto files and merge them into pto'''
        pto_temp_file = ManagedTempFile.get(None, ".pto")

        args = ["pto_merge"]
        args.append("--output=%s" % pto_temp_file)

        for pto in self.ptos:
            args.append(pto.get_a_file_name())
    
        print 'MERGING: %s' % (args,)

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

        return PTOProject.from_temp_file(pto_temp_file)
