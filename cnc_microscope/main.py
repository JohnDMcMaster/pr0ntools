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

def get_cnc():
    engine = config['cnc']['engine']
    if engine == 'mock':
        return MockController()
    elif engine == 'MC':
        try:
            return MC()
        except IOError:
            print 'Failed to open MC device'
            raise
    else:
        raise Exception("Unknown CNC engine %s" % engine)

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
        try:
            '''
            Two major circumstances:
            -Imaging: want next image
            -Snapshot: want next image
            In either case the GUI should listen to all events and clear out the ones it doesn't want
            '''
            #print 'Got image'
            if self.image_requested.is_set():
                print 'Processing image request'
                # Does this need to be locked?
                # Copy buffer so that even as object is reused we don't lse it
                self.images[self.next_image_id] = str(buffer)
                # Clear before emitting signal so that it can be re-requested in response
                self.image_requested.clear()
                print 'Emitting capture event'
                self.cb(self.next_image_id)
                print 'Capture event emitted'
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
    axisSet = pyqtSignal()
    
    def __init__(self, axis, parent = None):
        QWidget.__init__(self, parent)
        # controller axis object
        # Note that its wrapped in IPC layer
        self.axis = axis
        self.initUI()
    
    def jog(self, n):
        self.axis.jog(n)
        self.emit_pos()
    
    def go_abs(self):
        #print 'abs'
        self.axis.set_pos(float(str(self.abs_pos_le.text())))
        self.emit_pos()
    
    def go_rel(self):
        #print 'rel'
        self.jog(float(str(self.rel_pos_le.text())))
    
    def emit_pos(self):
        #print 'emitting pos'
        self.axisSet.emit(self.axis.get_um())
    
    def home(self):
        #print 'home'
        self.axis.home()
        # We moved to 0 position
        self.emit_pos()
    
    def set_home(self):
        #print 'setting new home position'
        self.axis.set_home()
        # We made the current position 0
        self.emit_pos()
        
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

        self.cnc_raw = get_cnc()
        self.cnc_raw.on()
        self.cnc_ipc = ControllerThread(self.cnc_raw)
        self.initUI()
        
        # Must not be initialized until after layout is set
        self.gstWindowId = None
        if config['imager']['engine'] == 'gstreamer':
            self.source = gst.element_factory_make("v4l2src", "vsource")
            self.source.set_property("device", "/dev/video0")
            self.setupGst()
        elif config['imager']['engine'] == 'gstreamer-testsrc':
            self.source = gst.element_factory_make("videotestsrc", "video-source")
            self.setupGst()    
        
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
        print 'Selected objective %s' % self.obj_config['name']
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
        layout = QVBoxLayout()
        layout.addWidget(QLabel("View"))
        
        # Raw X-windows canvas
        self.video_container = QWidget()
        # Allows for convenient keyboard control by clicking on the video
        #self.video_container.setFocusPolicy(Qt.ClickFocus)
        # TODO: do something more proper once integrating vodeo feed
        w, h = 800, 600
        self.video_container.setMinimumSize(w, h)
        self.video_container.resize(w, h)
        policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.video_container.setSizePolicy(policy)
        
        layout.addWidget(self.video_container)
        
        return layout
    
    def setupGst(self):
        dbg("Setting up gstreamer pipeline")
        self.gstWindowId = self.video_container.winId()

        self.player = gst.Pipeline("player")
        sink = gst.element_factory_make("xvimagesink", "sink")
        fvidscale_cap = gst.element_factory_make("capsfilter", "fvidscale_cap")
        fvidscale = gst.element_factory_make("videoscale", "fvidscale")
        caps = gst.caps_from_string('video/x-raw-yuv')
        fvidscale_cap.set_property('caps', caps)
        self.stream_queue = gst.element_factory_make("queue")

        self.tee = gst.element_factory_make("tee")

        self.capture_enc = gst.element_factory_make("jpegenc")
        self.capture_sink = gst.element_factory_make("capturesink")
        self.snapshotCaptured.connect(self.captureSnapshot)
        self.capture_sink_queue = gst.element_factory_make("queue")

        '''
        TODO: should these be split into two different piplines?
        Might be more reliable to not run video stream during CNC
        Also note that image aren't scaled in hardware
        Do scaling in PIL where we have more control
        '''
        self.player.add(self.source, self.tee, self.stream_queue, fvidscale, fvidscale_cap, sink)
        self.player.add(self.capture_sink_queue, self.capture_enc, self.capture_sink)
        # Video render stream
        gst.element_link_many(self.source, self.tee, self.stream_queue, fvidscale, fvidscale_cap, sink)
        # Frame grabber stream
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
    
    def home(self):
        dbg('home requested')
        self.cnc_ipc.home()
            
    def go_rel(self):
        dbg('Go rel all requested')
        for k in self.axes:
            axis = self.axes[k]
            axis.go_rel()
    
    def go_abs(self):
        dbg('Go abs all requested')
        for k in self.axes:
            axis = self.axes[k]
            axis.go_abs()
    
    def processCncProgress(self, pictures_to_take, pictures_taken, image, first):
        print 'Processing CNC progress'
        if first:
            print 'First CB with %d items' % pictures_to_take
            self.pb.setMinimum(0)
            self.pb.setMaximum(pictures_to_take)
            self.bench = Benchmark(pictures_to_take)
        else:
            print 'took %s at %d / %d' % (image, pictures_taken, pictures_to_take)
            self.bench.set_cur_items(pictures_taken)
            print self.bench
            
        self.pb.setValue(pictures_taken)
            
    def dry(self):
        return self.dry_cb.isChecked()
    
    def run(self):
        if not self.snapshot_pb.isEnabled():
            print "Wait for snapshot to complete before CNC'ing"
            return
        
        dry = self.dry()
        if dry:
            dbg('Dry run checked')
        rconfig = RunConfig()
        imager = None
        if not dry:
            print 'Loading imager...'
            itype = config['imager']['engine']
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
                        print 'gstreamer imager: taking image to %s' % file_name_out
                        def emitSnapshotCaptured(image_id):
                            print 'Image captured reported: %s' % image_id
                            self.image_id = image_id
                            self.image_ready.set()

                        self.image_id = None
                        self.image_ready.clear()
                        self.gui.capture_sink.request_image(emitSnapshotCaptured)
                        print 'Waiting for next image...'
                        self.image_ready.wait()
                        print 'Got image %s' % self.image_id
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
            print 'Emitting CNC progress'
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
        
        self.pt = PlannerThread(self, rconfig)
        self.pt.plannerDone.connect(self.plannerDone)
        self.setControlsEnabled(False)
        #eeeee not working as well as I hoped
        # tracked it down to python video capture library operating on windows GUI frame buffer
        # now that switching over to Linux should be fine to be multithreaded
        # If need to use the old layer again should use signals to block GUI for minimum time
        if config['multithreaded']:
            dbg("Running multithreaded")
            self.pt.start()
        else:
            dbg("Running single threaded")
            self.pt.run()
    
    def setControlsEnabled(self, yes):
        self.go_pb.setEnabled(yes)
        self.go_abs_pb.setEnabled(yes)
        self.go_rel_pb.setEnabled(yes)
        self.snapshot_pb.setEnabled(yes)
    
    def plannerDone(self):
        print 'RX planner done'
        # Cleanup camera objects
        self.pt = None
        self.setControlsEnabled(True)
        if config['cnc']['startup_run_exit']:
            print 'Planner debug break on completion'
            os._exit(1)
    
    def stop(self):
        '''Stop operations after the next operation'''
        print 'FIXME: stop'
        
    def estop(self):
        '''Stop operations immediately.  Position state may become corrupted'''
        print 'FIXME: estop'

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
                
                return layout
            
            layout.addLayout(get_go())
            layout.addLayout(get_stop())
            return layout
            
        layout.addLayout(get_general_layout())

        self.axes = dict()
        print 'Axes: %u' % len(self.cnc_ipc.axes)
        for axis in self.cnc_ipc.axes:
            axisw = Axis(axis)
            print 'Creating axis GUI %s' % axis.name
            self.axes[axis.name] = axisw
            layout.addWidget(axisw)
        
        gb.setLayout(layout)
        return gb

    def get_snapshot_layout(self):
        gb = QGroupBox('Snapshot')
        layout = QGridLayout()

        snapshot_dir = config['imager']['snapshot_dir']
        if not os.path.isdir(snapshot_dir):
            print 'Snapshot dir %s does not exist' % snapshot_dir
            if os.path.exists(snapshot_dir):
                raise Exception("Snapshot directory is not accessible")
            os.mkdir(snapshot_dir)
            print 'Snapshot dir %s created' % snapshot_dir        

        # nah...just have it in the config
        # d = QFileDialog.getExistingDirectory(self, 'Select snapshot directory', snapshot_dir)

        layout.addWidget(QLabel('File name'), 0, 0)
        self.snapshot_serial = -1
        self.snapshot_fn_le = QLineEdit('')
        self.snapshot_next_serial()
        layout.addWidget(self.snapshot_fn_le, 0, 1)
        self.snapshot_pb = QPushButton("Snapshot")
        self.snapshot_pb.clicked.connect(self.take_snapshot)
        layout.addWidget(self.snapshot_pb, 1, 0, 2, 1)
        
        gb.setLayout(layout)
        return gb
    
    def snapshot_next_serial(self):
        while True:
            self.snapshot_serial += 1
            fn_base = 'snapshot00%u.jpg' % self.snapshot_serial
            fn_full = os.path.join(config['imager']['snapshot_dir'], fn_base)
            if os.path.exists(fn_full):
                print 'Snapshot %s already exists, skipping' % fn_full
                continue
            # Omit base to make GUI easier to read
            self.snapshot_fn_le.setText(fn_base)
            break
    
    def take_snapshot(self):
        print 'Requesting snapshot'
        # Disable until snapshot is completed
        self.snapshot_pb.setEnabled(False)
        def emitSnapshotCaptured(image_id):
            print 'Image captured: %s' % image_id
            self.snapshotCaptured.emit(image_id)
        self.capture_sink.request_image(emitSnapshotCaptured)
    
    def captureSnapshot(self, image_id):
        print 'RX image for saving'
        image = PImage.from_image(self.capture_sink.pop_image(image_id))
        fn_full = os.path.join(config['imager']['snapshot_dir'], str(self.snapshot_fn_le.text()))
        factor = float(config['imager']['scalar'])
        # Use a reasonably high quality filter
        image.get_scaled(factor, Image.ANTIALIAS).save(fn_full)
        
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
        
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.show()
        
    def keyPressEvent(self, event):
        '''
        print event
        #print dir(event)
        print event.text()
        print 'type: %s' % str(event.type())
        print event.nativeScanCode()
        print event.nativeVirtualKey()
        print len(event.text())
        if event == Qt.Key_Left:
            print 'left'
        event.ignore()
        '''
        '''
        Stuck direction
        2
        3
        1
        4
    
        now it goes
        3
        2
        4
        1
        '''
    
        
        '''
        Upper left hand coordinate system
        '''
        # Only control explicitly, don't move by typing accident in other element
        if not self.video_container.hasFocus():
            return
        k = event.key()
        inc = 5
        if k == Qt.Key_Left:
            print 'left'
            self.x(-inc)
        elif k == Qt.Key_Right:
            print 'right'
            self.x(inc)
        elif k == Qt.Key_Up:
            print 'up'
            self.y(-inc)
        elif k == Qt.Key_Down:
            print 'down'
            self.y(inc)
        # Focus is sensitive
        elif k == Qt.Key_PageUp:
            print 'up'
            self.z(1)
        elif k == Qt.Key_PageDown:
            print 'down'
            self.z(-1)

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
