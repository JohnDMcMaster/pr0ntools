'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import random
import os
import shutil
from pr0ntools.config import config

g_default_prefix_dir = None
g_default_prefix = None


PREFIX_BASE = config.temp_base()

def verbose(s):
    pass

class TempFile:
    @staticmethod
    def default_prefix():
        global g_default_prefix_dir
        global g_default_prefix
        
        if g_default_prefix is None:
            g_default_prefix_dir = ManagedTempDir.get(TempFile.get(PREFIX_BASE))
            g_default_prefix = os.path.join(g_default_prefix_dir.file_name, '')
            print 'TEMP DIR: %s' % g_default_prefix
        return g_default_prefix

    @staticmethod
    def rand_str(length):
        ret = ''
        for i in range(0, length):
            ret += "%X" % random.randint(0, 15)
        return ret

    @staticmethod
    def get(prefix = None, suffix = None):
        if not prefix:
            prefix = TempFile.default_prefix()
        if not suffix:
            suffix = ""
        # Good enough for now
        return prefix + TempFile.rand_str(16) + suffix

class ManagedTempFile:
    def __init__(self, file_name):
        if file_name:
            self.file_name = file_name
        else:
            self.file_name = TempFile.get()
    
    def __repr__(self):
        return self.file_name
    
    @staticmethod
    def get(prefix=None, suffix=None, prefix_mangle=None):
        if prefix_mangle:
            if prefix is not None:
                raise Exception("Can't specify prefix and prefix_mangle")
            # seed default prefix if not created
            TempFile.default_prefix()
            prefix = g_default_prefix + prefix_mangle
        return ManagedTempFile(TempFile.get(prefix, suffix))

    @staticmethod
    def from_existing(file_name):
        return ManagedTempFile(file_name)

    @staticmethod
    def from_same_extension(reference_file_name, prefix = None):
        return ManagedTempFile.get(prefix, '.' + reference_file_name.split(".")[-1])

    def __del__(self):
        try:
            if os.path.exists(self.file_name):
                if config.keep_temp_files():
                    verbose('KEEP: Deleted temp file %s' % self.file_name)
                else:
                    os.remove(self.file_name)
                    verbose('Deleted temp file %s' % self.file_name)
            else:
                verbose("Didn't delete inexistant temp file %s" % self.file_name)
        # Ignore if it was never created
        except:
            print 'WARNING: failed to delete temp file: %s' % self.file_name

class ManagedTempDir(ManagedTempFile):
    def __init__(self, temp_dir):
        ManagedTempFile.__init__(self, temp_dir)

    @staticmethod
    def get(temp_dir = None):
        ret = ManagedTempDir(temp_dir)
        os.mkdir(ret.file_name)
        return ret

    @staticmethod
    def get2(prefix=None, suffix=None, prefix_mangle=None):
        if prefix_mangle:
            if prefix is not None:
                raise Exception("Can't specify prefix and prefix_mangle")
            # seed default prefix if not created
            TempFile.default_prefix()
            prefix = g_default_prefix + prefix_mangle
        ret = ManagedTempDir(TempFile.get(prefix, suffix))
        os.mkdir(ret.file_name)
        return ret

    def get_file_name(self, prefix = '', suffix = None):
        # Make it in this dir
        return TempFile.get(os.path.join(self.file_name, prefix), suffix)

    def __del__(self):
        try:
            if os.path.exists(self.file_name):
                if config.keep_temp_files():            
                    print 'KEEP: Deleted temp dir %s' % self.file_name
                else:
                    shutil.rmtree(self.file_name)
                    print 'Deleted temp dir %s' % self.file_name
            else:
                print "Didn't delete inexistant temp dir %s" % self.file_name
        # Ignore if it was never created
        except:
            print 'WARNING: failed to delete temp dir: %s' % self.file_name
