'''
pr0ntools
Copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from temp_file import ManagedTempFile
import datetime
import os
import select
import subprocess
import sys
import time

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
        cmd = program
        for arg in args:
            cmd += ' "' + arg + '"'
            
        if working_dir:
            cmd = 'cd %s && ' % working_dir + cmd

        print 'cmd in: %s' % cmd
        # Streams output to screen but may be causing synchronization issues
        #print 'Executing'
        os.sys.stdout.flush()
        ret = os.system(cmd)
        os.sys.stdout.flush()
        #print 'Execute done'
        return ret
        
    @staticmethod
    def show_output_simple(cmd, print_output=False, working_dir=None):
        '''Return rc'''
        if working_dir:
            cmd = 'cd %s && ' % working_dir + cmd

        print 'cmd in: %s' % cmd
        # Streams output to screen but may be causing synchronization issues
        #print 'Executing'
        os.sys.stdout.flush()
        ret = os.system(cmd)
        os.sys.stdout.flush()
        #print 'Execute done'
        return ret

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

class Prefixer:
    def __init__(self, f, prefix):
        self.f = f
        self.inline = False
        self.prefix = prefix

    def write(self, s):
        pos = 0
        while True:
            posn = s.find('\n', pos)
            if posn >= 0:
                if not self.inline:
                    self.f.write(self.prefix())
                self.f.write(s[pos:posn + 1])
                pos = posn + 2
                self.inline = False
            else:
                out = s[pos:]
                if len(out) and not self.inline:
                    self.f.write(self.prefix())
                    self.inline = True
                self.f.write(out)
                break
        self.f.flush()
        
def timestamp(args, stdout=sys.stdout, stderr=sys.stderr):
    return prefix(args, stdout, stderr, lambda: datetime.datetime.utcnow().isoformat() + ': ')

def prefix(args, stdout=sys.stdout, stderr=sys.stderr, prefix=lambda: ''):
    '''Execute, prepending timestamps to newlines'''
    subp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    try:
        p_stdout = Prefixer(stdout, prefix)
        p_stderr = Prefixer(stderr, prefix)
        while subp.poll() is None:
            r_rdy, _w_rdy, _x_rdy = select.select([subp.stdout, subp.stderr], [], [], 0.1)
            if subp.stdout in r_rdy:
                p_stdout.write(os.read(subp.stdout.fileno(), 1024))
            if subp.stderr in r_rdy:
                p_stderr.write(os.read(subp.stderr.fileno(), 1024))
        # Flush lingering output
        # could move these above but afraid of race conditions losing output
        while True:
            s = os.read(subp.stdout.fileno(), 1024)
            if len(s) == 0:
                break
            p_stdout.write(s)
        while True:
            s = os.read(subp.stderr.fileno(), 1024)
            if len(s) == 0:
                break
            p_stderr.write(s)
    
        return subp.returncode
    finally:
        if subp.poll() is None:
            try:
                subp.kill()
            # be careful of race conditions.  child may execute after poll
            except OSError:
                pass

def exc_ret_istr(cmd, args, print_out=True):
    '''Execute command, returning status and output.  Optionally print as it runs'''
    
    p = subprocess.Popen([cmd] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, close_fds=True)
    output = bytearray()

    def check():
        rlist, _wlist, _xlist = select.select([p.stdout, p.stderr], [], [], 0.05)
        for f in rlist:
            d = f.read()
            output.extend(d)
            if print_out:
                sys.stdout.write(d)
                sys.stdout.flush()

    while p.returncode is None:
        # Hmm how to treat stdout  vs stderror?
        check()
        #time.sleep(0.05)
        p.poll()

    check()
    return p.returncode, str(output)
