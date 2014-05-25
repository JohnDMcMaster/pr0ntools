#!/usr/bin/env python

'''
TODO: version 1 was platform independent without video feed
Consider making video feed optional to make it continue to work on windows
or maybe look into Phonon some more for rendering
'''

from imager import *
from usbio.mc import MC
from pr0ntools.benchmark import Benchmark
from config import *
from threads import *
VCImager = None
try:
    from vcimager import *
except ImportError:
    print 'Note: failed to import VCImager'

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

        self.initUI()
        
        # Must not be initialized until after layout is set
        self.gstWindowId = None
        if g_test:
            self.source = gst.element_factory_make("videotestsrc", "video-source")
            self.setupGst()    
        else:
            self.source = gst.element_factory_make("v4l2src", "vsource")
            self.source.set_property("device", "/dev/video0")
            self.setupGst()
        
        dbg("Starting gstreamer pipeline")
        self.player.set_state(gst.STATE_PLAYING)
        
    def get_size_layout(self):
        layout = QGridLayout()
        col = 0

        l = QLabel('Resolution')
        l.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        layout.addWidget(l, 0, col)
        self.resolution = QComboBox()
        self.resolution.addItem('800x600')
        self.resolution.addItem('1600x1200')
        self.resolution.addItem('3264x2448')
        self.resolution.setCurrentIndex(self.resolution.findText('3264x2448'))
        self.resolution.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        layout.addWidget(self.resolution, 1, col)
        col += 1
        
        if 1:
            l = QLabel('View scalar')
            l.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
            layout.addWidget(l, 0, col)
            self.scalar = QComboBox()
            self.scalar.addItem('25%')
            self.scalar.addItem('33%')
            self.scalar.addItem('50%')
            self.scalar.addItem('100%')
            self.scalar.setCurrentIndex(self.scalar.findText('50%'))
            self.scalar.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
            layout.addWidget(self.scalar, 1, col)
            col += 1
        
        self.resolution.currentIndexChanged.connect(self.resolution_changed)
        self.scalar.currentIndexChanged.connect(self.scalar_changed)
        
        '''
        Problem: when shrinking video widget net window size is the same
        Causes it to get spread out all over and makes things awkward
        '''
        #policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        #layout.setSizePolicy(policy)
        
        return layout
    
    def resolution_changed(self, *args):
        self.resize_video()
    
    def scalar_changed(self, *args):
        self.resize_video()
    
    def get_display_resolution(self):
        '''Return display resolution (w, h) tuple'''
        #return (800, 600)
        actual_res = [int(x) for x in self.resolution.currentText().split('x')]
        scalar = int(self.scalar.currentText().replace('%', '')) / 100.0
        return (int(actual_res[0] * scalar), int(actual_res[1] * scalar))
    
    def resize_video(self):
        # Allows for convenient keyboard control by clicking on the video
        #self.video_container.setFocusPolicy(Qt.ClickFocus)
        # TODO: do something more proper once integrating vodeo feed
        w, h = self.get_display_resolution()
        self.video_container.setMinimumSize(w, h)
        self.video_container.resize(w, h)
        
    def get_video_layout(self):
        layout = QVBoxLayout()
        l = QLabel("View")
        l.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        layout.addWidget(l)
        
        # Raw X-windows canvas
        self.video_container = QWidget()
        

        #self.resize_video()
        w, h = 800, 600
        self.video_container.setMinimumSize(w, h)
        self.video_container.resize(w, h)
        
        def fire(*args):
            w, h = 400, 300
            self.video_container.setMinimumSize(w, h)
            self.video_container.resize(w, h)
        self.t = QTimer(self)
        self.t.timeout.connect(fire)
        self.t.start(500)
        
        policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.video_container.setSizePolicy(policy)
        
        layout.addWidget(self.video_container)
        
        return layout
    
    def setupGst(self):
        dbg("Setting up gstreamer pipeline")
        self.gstWindowId = self.video_container.winId()

        self.player = gst.Pipeline("player")
        sinkx = gst.element_factory_make("ximagesink")
        fcs = gst.element_factory_make('ffmpegcolorspace')
        caps = gst.caps_from_string('video/x-raw-yuv')
        self.stream_queue = gst.element_factory_make("queue")

        self.player.add(self.source, self.stream_queue, fcs, sinkx)
        # Video render stream
        gst.element_link_many(self.source, self.stream_queue, fcs, sinkx)
        
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)
    
    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            print "End of stream"
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.player.set_state(gst.STATE_NULL)
        else:
            print 'Other message: %s' % t
            # Deadlocks upon calling this...
            #print 'Cur state %s' % self.player.get_state()

    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            win_id = self.gstWindowId
            assert win_id
            imagesink = message.src
            imagesink.set_xwindow_id(win_id)
    
    def initUI(self):
        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('pr0ncnc')    
        
        # top layout
        layout = QVBoxLayout()
        
        layout.addLayout(self.get_size_layout())
        layout.addLayout(self.get_video_layout())
        
        self.widget = QWidget()
        self.widget.setLayout(layout)
        #w.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.setCentralWidget(self.widget)
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
