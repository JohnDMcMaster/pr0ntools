#!/usr/bin/env python

'''
TODO: version 1 was platform independent without video feed
Consider making video feed optional to make it continue to work on windows
or maybe look into Phonon some more for rendering
'''

'''
Question: why on Ubuntu 12.04 w/ custom kernel can I take pictures but not stream to screen?
'''


from config import config, RunConfig
from imager import Imager
from mc import MC
from mock_controller import MockController
from pr0ndexer_controller import PDC
from threads import ControllerThread, PlannerThread

VCImager = None
try:
    from vcimager import *
except ImportError:
    print 'Note: failed to import VCImager'

from pr0ntools.benchmark import Benchmark
from pr0ntools.pimage import PImage

from PyQt4 import Qt
from PyQt4.QtGui import *
from PyQt4.QtCore import *

import os.path
import re
import signal
import sys
import traceback
import threading
from PIL import Image
import StringIO

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

debug = False
def dbg(*args):
    if not debug:
        return
    if len(args) == 0:
        print
    elif len(args) == 1:
        print 'main: %s' % (args[0], )
    else:
        print 'main: ' + (args[0] % args[1:])

def get_cnc(log):
    engine = config['cnc']['engine']
    if engine == 'mock':
        return MockController(debug=debug, log=log)
    # USBIO MicroControle
    elif engine == 'MC':
        try:
            return MC(debug=debug, log=log)
        except IOError:
            print 'Failed to open MC device'
            raise
    # pr0ndexer (still on MicroControle hardware though)
    elif engine == 'PDC':
        try:
            return PDC(debug=False, log=log, config=config)
        except IOError:
            print 'Failed to open PD device'
            raise
    elif engine == 'auto':
        try:
            return PDC(debug=False, log=log, config=config)
        except IOError:
            pass
        
        try:
            mc = MC(debug=debug, log=log)
            if mc.version():
                return mc
            raise IOError('Couldnt find dev')
        except IOError:
            log('Failed to open MC device, falling back to mock')
            return MockController(debug=debug, log=log)
    else:
        raise Exception("Unknown CNC engine %s" % engine)




# Example sink code at
# https://coherence.beebits.net/svn/branches/xbox-branch-2/coherence/transcoder.py
class ResizeSink(gst.Element):
    # Above didn't have this but seems its not optional
    __gstdetails__ = ('ResizeSink','Sink', \
                      'Resize source to get around X11 memory limitations', 'John McMaster')

    _sinkpadtemplate = gst.PadTemplate ("sinkpadtemplate",
                                        gst.PAD_SINK,
                                        gst.PAD_ALWAYS,
                                        gst.caps_new_any())


    _srcpadtemplate =  gst.PadTemplate ("srcpadtemplate",
                                        gst.PAD_SRC,
                                        gst.PAD_ALWAYS,
                                        gst.caps_new_any())

    def __init__(self):
        gst.Element.__init__(self)
        self.sinkpad = gst.Pad(self._sinkpadtemplate, "sink")
        self.srcpad = gst.Pad(self._srcpadtemplate, "src")
        self.add_pad(self.sinkpad)
        self.add_pad(self.srcpad)

        self.sinkpad.set_chain_function(self.chainfunc)
        self.sinkpad.set_event_function(self.eventfunc)
    
    def chainfunc(self, pad, buffer):
        try:
            print 'Got resize buffer'
            # Simplest: just propagate the data
            # self.srcpad.push(buffer)
            
            # Import into PIL and downsize it
            # Raw jpeg to pr0n PIL wrapper object
            print 'resize chain', len(buffer.data), len(buffer.data) / 3264.0
            #open('temp.jpg', 'w').write(buffer.data)
            #io = StringIO.StringIO(buffer.data)
            io = StringIO.StringIO(str(buffer))
            try:
                image = PImage.from_image(Image.open(io))
            except:
                print 'failed to create image'
                return gst.FLOW_OK
            # Use a fast filter since this is realtime
            image = image.get_scaled(0.5, Image.NEAREST)

            output = StringIO.StringIO()
            image.save(output, 'jpeg')
            self.srcpad.push(gst.Buffer(output.getvalue()))
        except:
            traceback.print_exc()
            os._exit(1)
        
        return gst.FLOW_OK

    def eventfunc(self, pad, event):
        return True

gobject.type_register(ResizeSink)
gst.element_register (ResizeSink, 'myresize', gst.RANK_MARGINAL)

# nope...
# metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases
# ...and one stack overflow post later I know more about python classes than I ever wanted to
# basically magic + magic = fizzle
#class CaptureSink(gst.Element, QObject):
class CaptureSink(gst.Element):
    __gstdetails__ = ('CaptureSink','Sink', \
                      'Captures images for the CNC', 'John McMaster')

    _sinkpadtemplate = gst.PadTemplate ("sinkpadtemplate",
                                        gst.PAD_SINK,
                                        gst.PAD_ALWAYS,
                                        gst.caps_new_any())

    def __init__(self):
        gst.Element.__init__(self)
        self.sinkpad = gst.Pad(self._sinkpadtemplate, "sink")
        self.add_pad(self.sinkpad)

        self.sinkpad.set_chain_function(self.chainfunc)
        self.sinkpad.set_event_function(self.eventfunc)

        self.image_requested = threading.Event()
        self.next_image_id = 0
        self.images = {}
        
    def request_image(self, cb):
        '''Request that the next image be saved'''
        # Later we might make this multi-image
        if self.image_requested.is_set():
            raise Exception('Image already requested')
        self.cb = cb
        self.image_requested.set()
        
    def get_image(self, image_id):
        '''Fetch the image but keep it in the buffer'''
        return self.images[image_id]
        
    def del_image(self, image_id):
        '''Delete image in buffer'''
        del self.images[image_id]

    def pop_image(self, image_id):
        '''Fetch the image and delete it form the buffer'''
        ret = self.images[image_id]
        del self.images[image_id]
        # Arbitrarily convert to PIL here
        # TODO: should pass rawer/lossless image to PIL instead of jpg?
        return Image.open(StringIO.StringIO(ret))
    
    '''
    gstreamer plugin core methods
    '''
    
    def chainfunc(self, pad, buffer):
        #print 'Capture sink buffer in'
        try:
            '''
            Two major circumstances:
            -Imaging: want next image
            -Snapshot: want next image
            In either case the GUI should listen to all events and clear out the ones it doesn't want
            '''
            #print 'Got image'
            if self.image_requested.is_set():
                #print 'Processing image request'
                # Does this need to be locked?
                # Copy buffer so that even as object is reused we don't lose it
                # is there a difference between str(buffer) and buffer.data?
                self.images[self.next_image_id] = str(buffer)
                # Clear before emitting signal so that it can be re-requested in response
                self.image_requested.clear()
                #print 'Emitting capture event'
                self.cb(self.next_image_id)
                #print 'Capture event emitted'
                self.next_image_id += 1
        except:
            traceback.print_exc()
            os._exit(1)
        
        return gst.FLOW_OK

    def eventfunc(self, pad, event):
        return True
    
gobject.type_register(CaptureSink)
# Register the element into this process' registry.
gst.element_register (CaptureSink, 'capturesink', gst.RANK_MARGINAL)


class Axis(QWidget):
    # Absolute position given
    axisSet = pyqtSignal(int)
    
    def __init__(self, axis, parent = None):
        QWidget.__init__(self, parent)
        # controller axis object
        # Note that its wrapped in IPC layer
        self.axis = axis
        self.axis.movement_notify = lambda: self.emit_pos()
        
        self.initUI()
        self.jog_done = None
    
    def emit_pos(self):
        #print 'emitting distance %d' % self.axis.get_um()
        self.axisSet.emit(self.axis.get_um())
    
    def jog(self, n):
        self.axis.jog(n, self.emit_pos)
    
    def go_abs(self):
        #print 'abs'
        self.axis.set_pos(float(str(self.abs_pos_le.text())), self.emit_pos)
    
    def go_rel(self, cb=None):
        #print 'rel'
        self.jog(float(str(self.rel_pos_le.text())))
    
    def home(self):
        #print 'home'
        self.axis.home(self.emit_pos)
    
    def set_home(self):
        #print 'setting new home position'
        self.axis.set_home(self.emit_pos)
        
    def meas_reset(self):
        dbg('meas reset')
        self.meas_abs = self.axis.axis.get_um()
        self.meas_value.setText("0.0")
        
    def update_meas(self, pos):
        nv = pos - self.meas_abs
        dbg('new meas value %f' % nv)
        self.meas_value.setNum(nv)
        
    def updateAxis(self, pos):
        self.pos_value.setNum(pos)
        
    def initUI(self):
        self.gb = QGroupBox('Axis %s' % self.axis.name)
        self.gl = QGridLayout()
        self.gb.setLayout(self.gl)
        row = 0
        
        self.gl.addWidget(QLabel("Pos (um):"), row, 0)
        self.pos_value = QLabel("Unknown")
        self.gl.addWidget(self.pos_value, row, 1)
        self.axisSet.connect(self.updateAxis)
        row += 1
        
        # Return to 0 position
        self.home_pb = QPushButton("Home axis")
        self.home_pb.clicked.connect(self.home)
        self.gl.addWidget(self.home_pb, row, 0)
        # Set the 0 position
        self.set_home_pb = QPushButton("Set home")
        self.set_home_pb.clicked.connect(self.set_home)
        self.gl.addWidget(self.set_home_pb, row, 1)
        row += 1
        
        self.abs_pos_le = QLineEdit('0.0')
        self.gl.addWidget(self.abs_pos_le, row, 0)
        self.go_abs_pb = QPushButton("Go absolute (um)")
        self.go_abs_pb.clicked.connect(self.go_abs)
        self.gl.addWidget(self.go_abs_pb, row, 1)
        row += 1
        
        self.rel_pos_le = QLineEdit('0.0')
        self.gl.addWidget(self.rel_pos_le, row, 0)
        self.go_rel_pb = QPushButton("Go relative (um)")
        self.go_rel_pb.clicked.connect(self.go_rel)
        self.gl.addWidget(self.go_rel_pb, row, 1)
        row += 1

        self.meas_label = QLabel("Meas (um)")
        self.gl.addWidget(self.meas_label, row, 0)
        self.meas_value = QLabel("Unknown")
        self.gl.addWidget(self.meas_value, row, 1)
        # Only resets in the GUI, not related to internal axis position counter
        self.meas_reset_pb = QPushButton("Reset meas")
        self.meas_reset()
        self.meas_reset_pb.clicked.connect(self.meas_reset)
        self.axisSet.connect(self.update_meas)
        self.gl.addWidget(self.meas_reset_pb, row, 0)
        row += 1
        
        self.l = QHBoxLayout()
        self.l.addWidget(self.gb)
        self.setLayout(self.l)

class CNCGUI(QMainWindow):
    cncProgress = pyqtSignal(int, int, str, int)
    snapshotCaptured = pyqtSignal(int)
        
    def __init__(self):
        QMainWindow.__init__(self)
        self.showMaximized()

        # must be created early to accept early logging
        # not displayed until later though
        self.log_widget = QTextEdit()
        # Special case for logging that might occur out of thread
        self.connect(self, SIGNAL('log'), self.log)
        
        self.pt = None
        self.log_fd = None
        self.cnc_raw = get_cnc(log=self.emit_log)
        self.cnc_raw.on()
        self.cnc_ipc = ControllerThread(self.cnc_raw)
        self.initUI()
        
        for axis in self.axes.values():
            axis.emit_pos()
        
        # Must not be initialized until after layout is set
        self.gstWindowId = None
        engine_config = config['imager']['engine']
        if engine_config == 'auto':
            if os.path.exists("/dev/video0"):
                engine_config = 'gstreamer'
            else:
                engine_config = 'gstreamer-testsrc'
            self.log('Auto image engine: selected %s' % engine_config)
        if engine_config == 'gstreamer':
            self.source = gst.element_factory_make("v4l2src", "vsource")
            self.source.set_property("device", "/dev/video0")
            self.setupGst()
        elif engine_config == 'gstreamer-testsrc':
            self.source = gst.element_factory_make("videotestsrc", "video-source")
            self.setupGst()
        elif engine_config == 'mock':
            pass
        else:
            raise Exception('Unknown engine %s' % (engine_config,))
        
        self.cnc_ipc.start()
        
        # Offload callback to GUI thread so it can do GUI ops
        self.cncProgress.connect(self.processCncProgress)
        
        if self.cnc_raw is None:
            dbg("Disabling all motion controls on no CNC")
            self.setControlsEnabled(False)
        
        if self.gstWindowId:
            dbg("Starting gstreamer pipeline")
            self.player.set_state(gst.STATE_PLAYING)
        
        if config['cnc']['startup_run']:
            self.run()
        
    def log(self, s='', newline=True):
        if newline:
            s += '\n'
        
        c = self.log_widget.textCursor()
        c.clearSelection()
        c.movePosition(QTextCursor.End)
        c.insertText(s)
        self.log_widget.setTextCursor(c)
        
        if self.log_fd is not None:
            self.log_fd.write(s) 
        
    def emit_log(self, s='', newline=True):
        # event must be omitted from the correct thread
        # however, if it hasn't been created yet assume we should log from this thread
        self.emit(SIGNAL('log'), s)
        
    def x(self, n):
        self.axes['X'].jog(n)
    
    def y(self, n):
        self.axes['Y'].jog(n)
        
    def z(self, n):
        self.axes['Z'].jog(n)
        
    def reload_obj_cb(self):
        '''Re-populate the objective combo box'''
        self.obj_cb.clear()
        self.obj_config = None
        for objective in config['objective']:
            self.obj_cb.addItem(objective['name'])
    
    def update_obj_config(self):
        '''Make resolution display reflect current objective'''
        self.obj_config = config['objective'][self.obj_cb.currentIndex ()]
        self.log('Selected objective %s' % self.obj_config['name'])
        self.obj_mag.setText('Magnification: %0.2f' % self.obj_config["mag"])
        self.obj_x_view.setText('X view (um): %0.3f' % self.obj_config["x_view"])
        self.obj_y_view.setText('Y view (um): %0.3f' % self.obj_config["y_view"])
    
    def get_config_layout(self):
        cl = QGridLayout()
        
        row = 0
        l = QLabel("Objective")
        cl.addWidget(l, row, 0)
        self.obj_cb = QComboBox()
        cl.addWidget(self.obj_cb, row, 1)
        self.obj_cb.currentIndexChanged.connect(self.update_obj_config)
        row += 1
        self.obj_mag = QLabel("")
        cl.addWidget(self.obj_mag, row, 1)
        self.obj_x_view = QLabel("")
        row += 1
        cl.addWidget(self.obj_x_view, row, 1)
        self.obj_y_view = QLabel("")
        cl.addWidget(self.obj_y_view, row, 2)
        row += 1
        # seed it
        self.reload_obj_cb()
        self.update_obj_config()
        
        return cl
    
    def get_video_layout(self):
        # Overview
        def low_res_layout():
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Overview"))
            
            # Raw X-windows canvas
            self.video_container = QWidget()
            # Allows for convenient keyboard control by clicking on the video
            self.video_container.setFocusPolicy(Qt.ClickFocus)
            # TODO: do something more proper once integrating vodeo feed
            w, h = 800, 600
            w, h = 3264/8, 2448/8
            self.video_container.setMinimumSize(w, h)
            self.video_container.resize(w, h)
            policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.video_container.setSizePolicy(policy)
            
            layout.addWidget(self.video_container)
            
            return layout
        
        # Higher res in the center for focusing
        def high_res_layout():
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Focus"))
            
            # Raw X-windows canvas
            self.video_container2 = QWidget()
            # TODO: do something more proper once integrating vodeo feed
            w, h = 800, 600
            w, h = 3264/8, 2448/8
            self.video_container2.setMinimumSize(w, h)
            self.video_container2.resize(w, h)
            policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.video_container2.setSizePolicy(policy)
            
            layout.addWidget(self.video_container2)
            
            return layout
            
        layout = QHBoxLayout()
        layout.addLayout(low_res_layout())
        layout.addLayout(high_res_layout())
        return layout
    
    def setupGst(self):
        '''
        gst-launch v4l2src device=/dev/video0 ! tee ! queue ! videoscale ! capsfilter caps=video/x-raw-yuv ! xvimagesink 
            gst-launch v4l2src device=/dev/video0 ! videoscale ! xvimagesink
        gst-launch v4l2src device=/dev/video0 ! ffmpegcolorspace ! ximagesink
            works...hmm
        
        
        gst-launch v4l2src device=/dev/video0 ! ffmpegcolorspace ! videocrop top=100 left=1 right=4 bottom=0 ! ximagesink
        
        
        sysctl kernel.shmmax=67108864
            cranked up to 128M, no change
            er no that was in KB so that was 128GB...
        sysctl kernel.shmall=32768
            didn't try messing with this
            kernel.shmall = 2097152
            2GB, should be plenty


            
        sysctl kernel.shmmax=67108864
            default: 33554432
        sysctl kernel.shmall=32768
            default: 2097152
            
        Default IPC limits
        root@gespenst:/home/mcmaster# ipcs -l

            ------ Shared Memory Limits --------
            max number of segments = 4096
            max seg size (kbytes) = 32768
            max total shared memory (kbytes) = 8388608
            min seg size (bytes) = 1

            ------ Semaphore Limits --------
            max number of arrays = 128
            max semaphores per array = 250
            max semaphores system wide = 32000
            max ops per semop call = 32
            semaphore max value = 32767

            ------ Messages Limits --------
            max queues system wide = 1471
            max size of message (bytes) = 8192
            default max size of queue (by        
        
        Works fine at med res
        mcmaster@gespenst:~/document/external/pr0ntools/cnc_microscope/snapshot$ gst-launch v4l2src device=/dev/video0 ! videoscale ! xvimagesink 
            Setting pipeline to PAUSED ...
            Pipeline is live and does not need PREROLL ...
            Setting pipeline to PLAYING ...
            New clock: GstSystemClock

            (close window)

            ERROR: from element /GstPipeline:pipeline0/GstXvImageSink:xvimagesink0: Output window was closed
            Additional debug info:
            xvimagesink.c(1326): gst_xvimagesink_handle_xevents (): /GstPipeline:pipeline0/GstXvImageSink:xvimagesink0
            Execution ended after 2888164132 ns.
            Setting pipeline to PAUSED ...
            Setting pipeline to READY ...
            Setting pipeline to NULL ...
            Freeing pipeline ...
        Dies at high res
        mcmaster@gespenst:~/document/external/pr0ntools/cnc_microscope/snapshot$ gst-launch v4l2src device=/dev/video0 ! videoscale ! xvimagesink 
            Setting pipeline to PAUSED ...
            Pipeline is live and does not need PREROLL ...
            Setting pipeline to PLAYING ...
            New clock: GstSystemClock
            ERROR: from element /GstPipeline:pipeline0/GstXvImageSink:xvimagesink0: Failed to create output image buffer of 3264x2448 pixels
            Additional debug info:
            xvimagesink.c(2404): gst_xvimagesink_show_frame (): /GstPipeline:pipeline0/GstXvImageSink:xvimagesink0:
            XServer allocated buffer size did not match input buffer
            Execution ended after 1854135991 ns.
            Setting pipeline to PAUSED ...
            Setting pipeline to READY ...
            Setting pipeline to NULL ...
            Freeing pipeline ...
        On Fedora I had to do something like vmalloc=192M, related?
        
        
        gst-launch v4l2src device=/dev/video0 ! tee ! queue ! ffmpegcolorspace ! ximagesink
        '''
        
        dbg("Setting up gstreamer pipeline")
        self.gstWindowId = self.video_container.winId()
        self.gstWindowId2 = self.video_container2.winId()

        self.player = gst.Pipeline("player")
        #sinkxv = gst.element_factory_make("xvimagesink")
        sinkx = gst.element_factory_make("ximagesink", 'sinkx_overview')
        sinkx_focus = gst.element_factory_make("ximagesink", 'sinkx_focus')
        #fvidscale_cap = gst.element_factory_make("capsfilter")
        #fvidscale = gst.element_factory_make("videoscale")
        fcs = gst.element_factory_make('ffmpegcolorspace')
        caps = gst.caps_from_string('video/x-raw-yuv')
        #fvidscale_cap.set_property('caps', caps)

        self.tee = gst.element_factory_make("tee")

        self.capture_enc = gst.element_factory_make("jpegenc")
        self.capture_sink = gst.element_factory_make("capturesink")
        #self.resizer = gst.element_factory_make("myresize")
        self.resizer =  gst.element_factory_make("videoscale")
        self.snapshotCaptured.connect(self.captureSnapshot)
        self.capture_sink_queue = gst.element_factory_make("queue")

        '''
        Per #gstreamer question evidently v4l2src ! ffmpegcolorspace ! ximagesink
            gst-launch v4l2src ! ffmpegcolorspace ! ximagesink
        allocates memory different than v4l2src ! videoscale ! xvimagesink 
            gst-launch v4l2src ! videoscale ! xvimagesink 
        Problem is that the former doesn't resize the window but allows taking full res pictures
        The later resizes the window but doesn't allow taking full res pictures
        However, we don't want full res in the view window
        '''
        # Video render stream
        self.player.add(self.source, self.tee)
        gst.element_link_many(self.source, self.tee)

        self.size_tee = gst.element_factory_make("tee")
        self.size_queue_overview = gst.element_factory_make("queue")
        self.size_queue_focus = gst.element_factory_make("queue")
        # First lets make this identical to keep things simpler
        self.videocrop = gst.element_factory_make("videocrop")
        '''
        TODO: make this more automagic
        w, h = 3264/8, 2448/8 => 408, 306
        Want 3264/2, 2448,2 type resolution
        Image is coming in raw at this point which menas we need to end up with
        408*2, 306*2 => 816, 612
        since its centered crop the same amount off the top and bottom:
        (3264 - 816)/2, (2448 - 612)/2 => 1224, 918
        '''
        self.videocrop.set_property("top", 918)
        self.videocrop.set_property("bottom", 918)
        self.videocrop.set_property("left", 1224)
        self.videocrop.set_property("right", 1224)
        self.scale2 = gst.element_factory_make("videoscale")
        
        self.player.add(fcs, self.size_tee)
        gst.element_link_many(self.tee, fcs, self.size_tee)
        self.player.add(self.size_queue_overview, self.resizer, sinkx)
        gst.element_link_many(self.size_tee, self.size_queue_overview, self.resizer, sinkx)
        # gah
        # libv4l2: error converting / decoding frame data: v4l-convert: error destination buffer too small (16777216 < 23970816)
        '''
        Ubuntu 12.04 w/ 3.9.0-rc4 giving:
        Error: The stream is in the wrong format. gstbasesrc.c(2830): gst_base_src_start (): /GstPipeline:player/GstV4l2Src:vsource:
        Culprit seems to be videocrop
        gst-launch v4l2src device=/dev/video0 ! videocrop top=918 bottom=918 left=1224 right=1224 ! videoscale ! ximagesink
        gst-launch v4l2src device=/dev/video0 ! ffmpegcolorspace ! videocrop top=918 bottom=918 left=1224 right=1224 ! videoscale ! ximagesink
            
    mcmaster@pr0nscope:~/document/external/pr0ntools/cnc_microscope$ gst-launch v4l2src device=/dev/video0 ! videocrop top=918 bottom=918 left=1224 right=1224 ! videoscale ! ximagesink
        Setting pipeline to PAUSED ...
        ERROR: Pipeline doesn't want to pause.
        ERROR: from element /GstPipeline:pipeline0/GstV4l2Src:v4l2src0: Could not negotiate format
        Additional debug info:
        gstbasesrc.c(2830): gst_base_src_start (): /GstPipeline:pipeline0/GstV4l2Src:v4l2src0:
        Check your filtered caps, if any
        Setting pipeline to NULL ...
        Freeing pipeline ...
        gst-launch v4l2src device=/dev/video0 ! ffmpegcolorspace ! videocrop top=100 left=1 right=4 bottom=0 ! ximagesink
            works
    mcmaster@pr0nscope:~/document/external/pr0ntools/cnc_microscope$ gst-launch v4l2src device=/dev/video0 ! ffmpegcolorspace ! videocrop top=100 left=1 right=4 bottom=0 ! ximagesink
        Setting pipeline to PAUSED ...
        Pipeline is live and does not need PREROLL ...
        Setting pipeline to PLAYING ...
        New clock: GstSystemClock
        ERROR: from element /GstPipeline:pipeline0/GstXImageSink:ximagesink0: Output window was closed
        Additional debug info:
        ximagesink.c(1119): gst_ximagesink_handle_xevents (): /GstPipeline:pipeline0/GstXImageSink:ximagesink0
        Execution ended after 4460586853 ns.
        Setting pipeline to PAUSED ...
        Setting pipeline to READY ...
        Setting pipeline to NULL ...
        Freeing pipeline ...
    aha: the culprit is that I'm running the full driver which is defaulting to lower res
        '''
        if 0:
            self.player.add(self.size_queue_focus, self.videocrop)
            gst.element_link_many(self.size_tee, self.size_queue_focus, self.videocrop)
        if 1:
            self.player.add(self.size_queue_focus, self.videocrop, self.scale2, sinkx_focus)
            gst.element_link_many(self.size_tee, self.size_queue_focus, self.videocrop, self.scale2, sinkx_focus)

        # Frame grabber stream
        # compromise
        self.player.add(self.capture_sink_queue, self.capture_enc, self.capture_sink)
        gst.element_link_many(self.tee, self.capture_sink_queue, self.capture_enc, self.capture_sink)
        
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
            #print 'Other message: %s' % t
            # Deadlocks upon calling this...
            #print 'Cur state %s' % self.player.get_state()
            ''

    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            if message.src.get_name() == 'sinkx_overview':
                #print 'sinkx_overview win_id'
                win_id = self.gstWindowId
            elif message.src.get_name() == 'sinkx_focus':
                win_id = self.gstWindowId2
                #print 'sinkx_focus win_id'
            else:
                raise Exception('oh noes')
            
            assert win_id
            imagesink = message.src
            imagesink.set_xwindow_id(win_id)
    
    def home(self):
        dbg('home requested')
        #self.cnc_ipc.home()
        for axis in self.axes.values():
            axis.home()
            
    def go_rel(self):
        dbg('Go rel all requested')
        for axis in self.axes.values():
            axis.go_rel()
    
    def go_abs(self):
        dbg('Go abs all requested')
        for axis in self.axes.values():
            axis.go_abs()
    
    def processCncProgress(self, pictures_to_take, pictures_taken, image, first):
        dbg('Processing CNC progress')
        if first:
            dbg('First CB with %d items' % pictures_to_take)
            self.pb.setMinimum(0)
            self.pb.setMaximum(pictures_to_take)
            self.bench = Benchmark(pictures_to_take)
        else:
            dbg('took %s at %d / %d' % (image, pictures_taken, pictures_to_take))
            self.bench.set_cur_items(pictures_taken)
            self.log(str(self.bench))
            
        self.pb.setValue(pictures_taken)
        # Update position GUI
        for axis in self.axes.values():
            axis.emit_pos()
        
    def dry(self):
        return self.dry_cb.isChecked()
    
    def pause(self):
        if self.pause_pb.text() == 'Pause':
            self.pause_pb.setText('Run')
            self.cnc_ipc.setRunning(False)
            if self.pt:
                self.pt.setRunning(False)
            self.log('Pause requested')
        else:
            self.pause_pb.setText('Pause')
            self.cnc_ipc.setRunning(True)
            if self.pt:
                self.pt.setRunning(True)
            self.log('Resume requested')
    
    def run(self):
        if not self.snapshot_pb.isEnabled():
            print "Wait for snapshot to complete before CNC'ing"
            return
        emit_log = self.emit_log
        
        dry = self.dry()
        if dry:
            dbg('Dry run checked')
        rconfig = RunConfig()
        imager = None
        if not dry:
            self.log('Loading imager...')
            itype = config['imager']['engine']
            
            if itype == 'auto':
                if os.path.exists('/dev/video0'):
                    itype = 'gstreamer'
                else:
                    itype = 'gstreamer-testsrc'
            
            if itype == 'mock':
                imager = MockImager()
            elif itype == "VC":
                if VCImager is None:
                    raise Exception('Import failed')
                imager = VCImager()
            elif itype == 'gstreamer' or itype == 'gstreamer-testsrc':
                class GstImager(Imager):
                    def __init__(self, gui):
                        Imager.__init__(self)
                        self.gui = gui
                        self.image_ready = threading.Event()
                        self.image_id = None
                        
                    def take_picture(self, file_name_out = None):
                        emit_log('gstreamer imager: taking image to %s' % file_name_out)
                        def emitSnapshotCaptured(image_id):
                            emit_log('Image captured reported: %s' % image_id)
                            self.image_id = image_id
                            self.image_ready.set()

                        self.image_id = None
                        self.image_ready.clear()
                        self.gui.capture_sink.request_image(emitSnapshotCaptured)
                        emit_log('Waiting for next image...')
                        self.image_ready.wait()
                        emit_log('Got image %s' % self.image_id)
                        image = PImage.from_image(self.gui.capture_sink.pop_image(self.image_id))
                        factor = float(config['imager']['scalar'])
                        # Use a reasonably high quality filter
                        scaled = image.get_scaled(factor, Image.ANTIALIAS)
                        if not self.gui.dry():
                            scaled.save(file_name_out)

                imager = GstImager(self)
            else:
                raise Exception('Invalid imager type %s' % itype)
        if not config:
            raise Exception("missing uscope config")
        if not self.obj_config:
            raise Exception("missing obj config")
        
        rconfig.dry = dry
        
        def emitCncProgress(pictures_to_take, pictures_taken, image, first):
            #print 'Emitting CNC progress'
            if image is None:
                image = ''
            self.cncProgress.emit(pictures_to_take, pictures_taken, image, first)
        rconfig.progress_cb = emitCncProgress
        
        rconfig.obj_config = self.obj_config            
        # Will be offloaded to its own thread
        # Operations must be blocking
        # We enforce that nothing is running and disable all CNC GUI controls
        rconfig.controller = self.cnc_raw
        rconfig.imager = imager
        
        rconfig.job_name = str(self.job_name_le.text())
        if len(rconfig.job_name) == 0:
            rconfig.job_name = "out"
        if not dry and os.path.exists(rconfig.job_name):
            raise Exception("job name dir %s already exists" % rconfig.job_name)
        
        # If user had started some movement before hitting run wait until its done
        dbg("Waiting for previous movement (if any) to cease")
        self.cnc_ipc.wait_idle()
        
        def start_hook(out_dir):
            if not self.dry_cb.isChecked():
                self.log_fd = open(os.path.join(out_dir, 'log.txt'), 'w')
        self.pt = PlannerThread(self, rconfig, start_hook=start_hook)
        self.connect(self.pt, SIGNAL('log'), self.log)
        self.pt.plannerDone.connect(self.plannerDone)
        self.setControlsEnabled(False)
        
        '''
        #eeeee not working as well as I hoped
        # tracked it down to python video capture library operating on windows GUI frame buffer
        # now that switching over to Linux should be fine to be multithreaded
        # If need to use the old layer again should use signals to block GUI for minimum time
        if config['multithreaded']:
            dbg("Running multithreaded")
            self.pt.start()
        else:
            dbg("Running single threaded")
            def start_hook(out_dir):
                if not self.dry_cb.isChecked():
                    self.log_fd = open(os.path.join(out_dir, 'log.txt'), 'w')
            self.pt.run(start_hook=start_hook)
        '''
        dbg("Running multithreaded")
        self.pt.start()
    
    def setControlsEnabled(self, yes):
        self.go_pb.setEnabled(yes)
        self.go_abs_pb.setEnabled(yes)
        self.go_rel_pb.setEnabled(yes)
        self.snapshot_pb.setEnabled(yes)
    
    def plannerDone(self):
        self.log('RX planner done')
        # Cleanup camera objects
        self.log_fd = None
        self.pt = None
        self.setControlsEnabled(True)
        if config['cnc']['startup_run_exit']:
            print 'Planner debug break on completion'
            os._exit(1)
    
    def stop(self):
        '''Stop operations after the next operation'''
        for axis in self.cnc_ipc.axes:
            axis.stop()
        
    def estop(self):
        '''Stop operations immediately.  Position state may become corrupted'''
        for axis in self.cnc_ipc.axes:
            axis.estop()

    def clear_estop(self):
        '''Stop operations immediately.  Position state may become corrupted'''
        for axis in self.cnc_ipc.axes:
            axis.unestop()
            
    def get_axes_layout(self):
        layout = QHBoxLayout()
        gb = QGroupBox('Axes')
        
        def get_general_layout():
            layout = QVBoxLayout()

            def get_go():
                layout = QHBoxLayout()
                
                self.home_pb = QPushButton("Home all")
                self.home_pb.clicked.connect(self.home)
                layout.addWidget(self.home_pb)
        
                self.go_abs_pb = QPushButton("Go abs all")
                self.go_abs_pb.clicked.connect(self.go_abs)
                layout.addWidget(self.go_abs_pb)
            
                self.go_rel_pb = QPushButton("Go rel all")
                self.go_rel_pb.clicked.connect(self.go_rel)
                layout.addWidget(self.go_rel_pb)
                
                return layout
                
            def get_stop():
                layout = QHBoxLayout()
                
                self.stop_pb = QPushButton("Stop")
                self.stop_pb.clicked.connect(self.stop)
                layout.addWidget(self.stop_pb)
        
                self.estop_pb = QPushButton("Emergency stop")
                self.estop_pb.clicked.connect(self.estop)
                layout.addWidget(self.estop_pb)

                self.clear_estop_pb = QPushButton("Clear e-stop")
                self.clear_estop_pb.clicked.connect(self.clear_estop)
                layout.addWidget(self.clear_estop_pb)
                
                return layout
            
            layout.addLayout(get_go())
            layout.addLayout(get_stop())
            return layout
            
        layout.addLayout(get_general_layout())

        self.axes = dict()
        dbg('Axes: %u' % len(self.cnc_ipc.axes))
        for axis in self.cnc_ipc.axes:
            #if axis.name == 'Z':
            #    continue
            axisw = Axis(axis)
            dbg('Creating axis GUI %s' % axis.name)
            self.axes[axis.name] = axisw
            layout.addWidget(axisw)
        
        gb.setLayout(layout)
        return gb

    def get_snapshot_layout(self):
        gb = QGroupBox('Snapshot')
        layout = QGridLayout()

        snapshot_dir = config['imager']['snapshot_dir']
        if not os.path.isdir(snapshot_dir):
            self.log('Snapshot dir %s does not exist' % snapshot_dir)
            if os.path.exists(snapshot_dir):
                raise Exception("Snapshot directory is not accessible")
            os.mkdir(snapshot_dir)
            self.log('Snapshot dir %s created' % snapshot_dir)

        # nah...just have it in the config
        # d = QFileDialog.getExistingDirectory(self, 'Select snapshot directory', snapshot_dir)

        layout.addWidget(QLabel('File name'), 0, 0)
        self.snapshot_serial = -1
        self.snapshot_fn_le = QLineEdit('')
        layout.addWidget(self.snapshot_fn_le, 0, 1)

        layout.addWidget(QLabel('Auto-number?'), 1, 0)
        self.auto_number_cb = QCheckBox()
        self.auto_number_cb.setChecked(True)
        layout.addWidget(self.auto_number_cb, 1, 1)

        self.snapshot_pb = QPushButton("Snapshot")
        self.snapshot_pb.clicked.connect(self.take_snapshot)

        self.time_lapse_timer = None
        self.time_lapse_pb = QPushButton("Time lapse")
        self.time_lapse_pb.clicked.connect(self.time_lapse)
        layout.addWidget(self.time_lapse_pb, 2, 1)
        layout.addWidget(self.snapshot_pb, 2, 0)
        
        gb.setLayout(layout)
        self.snapshot_next_serial()
        return gb
    
    def snapshot_next_serial(self):
        if not self.auto_number_cb.isChecked():
                return
        prefix = self.snapshot_fn_le.text().split('.')[0]
        if prefix == '':
            self.snapshot_serial = 0
            prefix = 'snapshot_'
        else:
            dbg('Image prefix: %s' % prefix)
            m = re.search('([a-zA-z0-9_\-]*_)([0-9]+)', prefix)
            if m:
                dbg('Group 1: ' + m.group(1))
                dbg('Group 2: ' + m.group(2))
                prefix = m.group(1)
                self.snapshot_serial = int(m.group(2))

        while True:
            self.snapshot_serial += 1
            fn_base = '%s00%u' % (prefix, self.snapshot_serial)
            fn_full = os.path.join(config['imager']['snapshot_dir'], fn_base)
            if os.path.exists(fn_full):
                dbg('Snapshot %s already exists, skipping' % fn_full)
                continue
            # Omit base to make GUI easier to read
            self.snapshot_fn_le.setText(fn_base)
            break
    
    def take_snapshot(self):
        self.log('Requesting snapshot')
        # Disable until snapshot is completed
        self.snapshot_pb.setEnabled(False)
        def emitSnapshotCaptured(image_id):
            self.log('Image captured: %s' % image_id)
            self.snapshotCaptured.emit(image_id)
        self.capture_sink.request_image(emitSnapshotCaptured)
    
    def time_lapse(self):
        if self.time_lapse_pb.text() == 'Stop':
            self.time_lapse_timer.stop()
            self.time_lapse_pb.setText('Time lapse')
        else:
            self.time_lapse_pb.setText('Stop')
            self.time_lapse_timer = QTimer()
            def f():
                self.take_snapshot()
            self.time_lapse_timer.timeout.connect(f)
            # 5 seconds
            # Rather be more aggressive for now
            self.time_lapse_timer.start(5000)
            self.take_snapshot()
        
    def captureSnapshot(self, image_id):
        self.log('RX image for saving')
        def try_save():
            image = PImage.from_image(self.capture_sink.pop_image(image_id))
            txt = str(self.snapshot_fn_le.text())
            if '.' not in txt:
                txt = txt + '.jpg'
            elif '.jpg' not in txt:
                self.log('WARNING: refusing to take bad image file name %s' % txt)
                return
            fn_full = os.path.join(config['imager']['snapshot_dir'], txt)
            if os.path.exists(fn_full):
                self.log('WARNING: refusing to overwrite %s' % fn_full)
                return
            factor = float(config['imager']['scalar'])
            # Use a reasonably high quality filter
            image.get_scaled(factor, Image.ANTIALIAS).save(fn_full)
        try_save()
        
        # That image is done, get read for the next
        self.snapshot_next_serial()
        self.snapshot_pb.setEnabled(True)
    
    def get_scan_layout(self):
        gb = QGroupBox('Scan')
        layout = QGridLayout()

        # TODO: add overlap widgets
        
        layout.addWidget(QLabel('Job name'), 0, 0)
        self.job_name_le = QLineEdit('default')
        layout.addWidget(self.job_name_le, 0, 1)
        self.go_pb = QPushButton("Go")
        self.go_pb.clicked.connect(self.run)
        layout.addWidget(self.go_pb, 1, 0)
        self.pb = QProgressBar()
        layout.addWidget(self.pb, 1, 1)
        layout.addWidget(QLabel('Dry?'), 2, 0)
        self.dry_cb = QCheckBox()
        self.dry_cb.setChecked(config['cnc']['dry'])
        layout.addWidget(self.dry_cb, 2, 1)

        self.pause_pb = QPushButton("Pause")
        self.pause_pb.clicked.connect(self.pause)
        layout.addWidget(self.pause_pb, 3, 0)
        
        gb.setLayout(layout)
        return gb

    def get_bottom_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.get_axes_layout())
        def get_lr_layout():
            layout = QVBoxLayout()
            layout.addWidget(self.get_snapshot_layout())
            layout.addWidget(self.get_scan_layout())
            return layout
        layout.addLayout(get_lr_layout())
        return layout
        
    def initUI(self):
        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('pr0ncnc')    

        # top layout
        layout = QVBoxLayout()
        
        layout.addLayout(self.get_config_layout())
        layout.addLayout(self.get_video_layout())
        layout.addLayout(self.get_bottom_layout())
        self.log_widget.setReadOnly(True)
        layout.addWidget(self.log_widget)
        
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.show()
        
    def keyPressEvent(self, event):
        '''
        Upper left hand coordinate system
        '''
        # Only control explicitly, don't move by typing accident in other element
        if not self.video_container.hasFocus():
            return
        k = event.key()
        # Ignore duplicates, want only real presses
        if event.isAutoRepeat():
            return
            
        #inc = 5
        
        # Focus is sensitive...should step slower?
        # worry sonce focus gets re-integrated
        
        neg_map = { Qt.Key_Left:    'X',
                    Qt.Key_Up:      'Y',
                    Qt.Key_PageDown:'Z', 
                    }        
        axis = neg_map.get(k, None)
        if axis:
            dbg('Key %s+' % axis)
            axis = self.axes[axis]
            if axis.jog_done:
                return
            axis.jog_done = threading.Event()
            axis.axis.forever_neg(axis.jog_done, lambda: axis.emit_pos())
            return

        pos_map = { Qt.Key_Right:   'X',
                    Qt.Key_Down:    'Y',
                    Qt.Key_PageUp:  'Z', 
                    }        
        axis = pos_map.get(k, None)
        if axis:
            dbg('Key %s-' % axis)
            axis = self.axes[axis]
            if axis.jog_done:
                return
            axis.jog_done = threading.Event()
            axis.axis.forever_pos(axis.jog_done, lambda: axis.emit_pos())
            return
            
        if k == Qt.Key_Escape:
            self.stop()

    def keyReleaseEvent(self, event):
        if not self.video_container.hasFocus():
            return
        k = event.key()
        # Ignore duplicates, want only real presses
        if event.isAutoRepeat():
            return
        #inc = 5
        if k == Qt.Key_Left:
            dbg('left release')
            self.axes['X'].jog_done.set()
            self.axes['X'].jog_done = None
            self.axes['X'].emit_pos()
        elif k == Qt.Key_Right:
            dbg('right release')
            self.axes['X'].jog_done.set()
            self.axes['X'].jog_done = None
            self.axes['X'].emit_pos()
        elif k == Qt.Key_Up:
            self.axes['Y'].jog_done.set()
            self.axes['Y'].jog_done = None
            self.axes['Y'].emit_pos()
        elif k == Qt.Key_Down:
            self.axes['Y'].jog_done.set()
            self.axes['Y'].jog_done = None
            self.axes['Y'].emit_pos()
        elif k == Qt.Key_PageDown:
            self.axes['Z'].jog_done.set()
            self.axes['Z'].jog_done = None
            self.axes['Z'].emit_pos()
        elif k == Qt.Key_PageUp:
            self.axes['Z'].jog_done.set()
            self.axes['Z'].jog_done = None
            self.axes['Z'].emit_pos()
        
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
