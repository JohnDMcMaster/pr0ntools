'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

import os
from temp_file import ManagedTempFile
import subprocess
import select
import sys

class CommandFailed(Exception):
    pass

'''
FIXME XXX TODO
This module is a mess
I think that processes are lingering around due to me teeing output 
and waiting on either not all of the processes or the wrong one
'''

'''
Good idea but doesn't work...
http://stackoverflow.com/questions/2996887/how-to-replicate-tee-behavior-in-python-when-using-subprocess
suggests just reading from stdout
'''
class IOTee:
    def __init__(self):
        self.stdout = ''
        self.stderr = ''

    def write(self, data):
        self.stdout += data
        sys.stdout.write(data)

    def write_error(self, data):
        self.stderr += data
        sys.stderr.write(data)

def with_output(args, print_output=False):
    '''
    Return (rc, stdout+stderr))
    Echos stdout/stderr to screen as it 
    '''
    print 'going to execute: %s' % (args,)
    if print_output:
        # Specifying pipe will cause communicate to read to it
        print 'tst'
        tee = IOTee()
        subp = subprocess.Popen(args, stdout=tee, stderr=tee, shell=False)
    else:
        # Specifying nothing completely throws away the output
        subp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    (stdout, stderr) = subp.communicate()
    
    return (subp.returncode, stdout, stderr)

def without_output(args, print_output=True):
    '''
    Return rc
    Echos stdout/stderr to screen
    '''
    print 'going to execute: %s' % (args,)
    if print_output:
        subp = subprocess.Popen(args, shell=False)
    else:
        # Specifying nothing completely throws away the output
        subp = subprocess.Popen(args, stdout=None, stderr=None, shell=False)
    
    subp.communicate()
    return subp.returncode

class Execute:
    @staticmethod
    def simple(cmd, working_dir = None):
        '''Returns rc of process, no output'''
        
        print 'cmd in: %s' % cmd
        
        
        # Probably reliable but does not stream output to screen
        if 0:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
            _output, _unused_err = process.communicate()
            return process.poll()
        
        
        # Streams output to screen but may be causing synchronization issues
        if 1:
            #print 'Executing'
            os.sys.stdout.flush()
            ret = os.system(cmd)
            os.sys.stdout.flush()
            #print 'Execute done'
            return ret
        
        if 0:
            cmd = "/bin/bash " + cmd 
            output = ''
            to_exec = cmd.split(' ')
            print 'going to execute: %s' % to_exec
            subp = subprocess.Popen(to_exec)
            while subp.returncode is None:
                # Hmm how to treat stdout  vs stderror?
                com = subp.communicate()[0]
                if com:
                    print com
                com = subp.communicate()[1]
                if com:
                    print com
                time.sleep(0.05)
                subp.poll()
    
            return subp.returncode
        

    @staticmethod
    def show_output(program, args, working_dir = None):
        '''Return (rc, output)'''
        to_exec = program
        for arg in args:
            to_exec += ' "' + arg + '"'
        return Execute.show_output_simple(to_exec, working_dir)
        
    @staticmethod
    def show_output_simple(cmd, print_output=False, working_dir = None):    
        '''Return rc'''
        working_dir_str = ''
        if working_dir:
            working_dir_str = 'cd %s && ' % working_dir
            output = None
        rc = Execute.simple(working_dir_str + cmd)
        return rc

    @staticmethod
    def with_output(program, args, working_dir = None, print_output = False):
        '''Return (rc, output)'''
        to_exec = program
        for arg in args:
            to_exec += ' "' + arg + '"'
        return Execute.with_output_simple(to_exec, working_dir, print_output)
        
    @staticmethod
    def with_output_simple(cmd, working_dir = None, print_output = False):    
        '''Return (rc, output)'''
        # Somehow the pipe seems to really slow down the shutdown...not sure why
        # Don't use it for .pto grid stitching
        
        working_dir_str = ''
        tmp_file = ManagedTempFile.get(None, '_exec.txt')
        if working_dir:
            working_dir_str = 'cd %s && ' % working_dir
        if print_output:
            # ugly...but simple
            # ((false; true; true) 2>&1; echo "***RC_HACK: $?") |tee temp.txt
            rc = Execute.simple('(' + working_dir_str + cmd + ') 2>&1 |tee %s; exit $PIPESTATUS' % tmp_file.file_name)
        else:
            rc = Execute.simple(working_dir_str + cmd + ' &> %s' % tmp_file.file_name)
        
        output = open(tmp_file.file_name).read()
        # print 'OUTPUT: %d, %s' % (rc, output)
        return (rc, output)
    
        
        '''
        print 'cmd in: %s' % cmd
        #rc = os.system(cmd)
        #output = ''
        #cmd = "/bin/bash " + cmd 
        output = ''
        #subp = subprocess.Popen(cmd.split(' '))
        #subp = subprocess.Popen(cmd, stdin=stdin)
        # Hmm okay why don't I get the output to stdout/stderr
        subp = subprocess.Popen(cmd, shell=True)
        while subp.returncode is None:
            # Hmm how to treat stdout  vs stderror?
            com = subp.communicate()[0]
            if com:
                output += com
            com = subp.communicate()[1]
            if com:
                output += com         
            time.sleep(0.05)
            subp.poll()
    
        return (subp.returncode, output)
        '''

