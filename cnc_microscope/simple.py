#!/usr/bin/env python

'''
TODO: version 1 was platform independent without video feed
Consider making video feed optional to make it continue to work on windows
or maybe look into Phonon some more for rendering
'''

from pr0ntools.benchmark import Benchmark
from config import *
from threads import *

from PyQt4 import Qt
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from pr0ntools.pimage import PImage

import StringIO

import sys
import traceback
import os.path
import os
import signal

import Image

gobject = None
pygst = None
gst = None
try:
    import gobject, pygst
    pygst.require('0.10')
    import gst
except ImportError:
    if config['imager']['engine'] == 'gstreamer' or config['imager']['engine'] == 'gstreamer-testrc':
        print 'Failed to import a gstreamer package when gstreamer is required'
        raise

def dbg(*args):
    if len(args) == 0:
        print
    elif len(args) == 1:
        print 'main: %s' % (args[0], )
    else:
        print 'main: ' + (args[0] % args[1:])

g_test = True
        
class CNCGUI(QMainWindow):
    cncProgress = pyqtSignal(int, int, str, int)
    snapshotCaptured = pyqtSignal(int)
        
    def __init__(self):
        QMainWindow.__init__(self)
        
        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('pr0ncnc')    
        
        # top layout
        layout = QGridLayout()
        col = 0

        self.l1 = QLabel('Widget 1')
        self.l1.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        layout.addWidget(self.l1, 0, col)
        col += 1
        
        if 0:
            self.l2 = QLabel('Widget 2')
            self.l2.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
            layout.addWidget(self.l2, 0, col)
            col += 1

        self.video_container = QWidget()
        self.video_container.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        w, h = 800, 600
        if 1:
            pal = QPalette(self.video_container.palette())
            self.video_container.setAutoFillBackground(True)
            pal.setColor(QPalette.Window, QColor('black'))
            self.video_container.setPalette(pal)            
            #self.video_container.setBackgroundRole(Qt.black)
        self.video_container.setMinimumSize(w, h)
        self.video_container.resize(w, h)
        layout.addWidget(self.video_container, 0, col)
        col += 1
        
        def fire(*args):
            print 'Resize'
            w, h = 400, 300
            self.video_container.setMinimumSize(w, h)
            self.video_container.resize(w, h)
            self.resize(0, 0)
        self.t = QTimer(self)
        self.t.timeout.connect(fire)
        self.t.setSingleShot(True)
        self.t.start(500)
    
        self.widget = QWidget()
        self.widget.setLayout(layout)
        #self.widget.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
        self.setCentralWidget(self.widget)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
        self.updateGeometry()
        self.show()
        
def excepthook(excType, excValue, tracebackobj):
    print '%s: %s' % (excType, excValue)
    traceback.print_tb(tracebackobj)
    os._exit(1)

if __name__ == '__main__':
    '''
    We are controlling a robot
    '''
    sys.excepthook = excepthook
    # Exit on ^C instead of ignoring
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    gobject.threads_init()
    
    app = QApplication(sys.argv)
    _gui = CNCGUI()
    # XXX: what about the gstreamer message bus?
    # Is it simply not running?
    # must be what pygst is doing
    sys.exit(app.exec_())
