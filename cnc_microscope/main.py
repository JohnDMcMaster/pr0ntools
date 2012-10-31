#!/usr/bin/env python

'''
TODO: version 1 was platform independent without video feed
Consider making video feed optional to make it continue to work on windows
or maybe look into Phonon some more for rendering
'''

from planner import *
from imager import *
from usbio.controller import *
from usbio.mc import MC
from pr0ntools.benchmark import Benchmark
from config import RunConfig
from config import config as config

from PyQt4 import Qt
from PyQt4.QtGui import *
from PyQt4.QtCore import *

import sys
import Queue
import threading
import traceback
import os.path
import os


def dbg(*args):
    if len(args) == 0:
        print
    elif len(args) == 1:
        print args[0]
    else:
        print args[0] % args[1:]

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


'''
Try to seperate imaging and movement
For now keep unified in planner thread
'''
class ImagingThread(QThread):
    def __init__(self):
        self.queue = Queue.Queue()
        self.running = threading.Event()
    
    def run(self):
        self.running.set()
        while self.running.is_set():
            time.sleep(1)
    
    def stop(self):
        self.running.clear()

# Sends events to the imaging and movement threads
class PlannerThread(QThread):
    plannerDone = pyqtSignal()

    def __init__(self,parent, rconfig):
        QThread.__init__(self, parent)
        self.rconfig = rconfig
        
    def run(self):
        print 'Initializing planner!'

        self.planner = Planner.get(self.rconfig)
        print 'Running planner'
        b = Benchmark()
        self.planner.run()
        b.stop()
        print 'Planner done!  Took : %s' % str(b)
        self.emit(SIGNAL("plannerDone()"))
    
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
        self.emit(SIGNAL("axisSet(double)"), self.axis.get_um())
    
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
        
        self.pos_value = QLabel("Pos (um):")
        self.gl.addWidget(self.pos_value, row, 0)
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
        #self.addWidget(gb)

'''
Offloads controller processing to another thread (or potentially even process)
Makes it easier to keep RT deadlines and such
However, it doesn't provide feedback completion so use with care
(other blocks until done)
TODO: should block?
'''
'''
There must be a way to automate this more
Don't extend axis or the getattr won't work correctly
maybe not the most elegant but works for current needs
'''
class ControllerThreadAxis:
    def __init__(self, controller, axis):
        # IPC controller, not core
        self.controller = controller
        # Core axis
        self.axis = axis
        self.name = axis.name
    
    def __str__(self):
        return '%s-%s (IPC)' % (self.controller, self.axis)
    
    def get_um(self):
        return self.axis.get_um()
    
    # how 'bout this
    def __getattr__(self, name):
        # Assumption is that non-system attributes are offloaded functions
        if name.find("__") == 0:
            # __len__, __nonzero__
            return eval('self.axis.%s' % name)
        def offload(*args):
            self.controller.offload(self.axis, name, args)
            # Always return None
            # no fetch methods currently supported
        return offload

class ControllerThread(QThread, Controller):
    def __init__(self, controller):
        QThread.__init__(self)
        Controller.__init__(self)
        self.queue = Queue.Queue()
        self.controller = controller
        self.running = threading.Event()
        self._idle = threading.Event()
        self._idle.set()
        
        #for axis in self.controller.axes:
        
        if self.controller.x:
            self.x = ControllerThreadAxis(self, self.controller.x)
        else:
            self.x = None

        if self.controller.y:
            self.y = ControllerThreadAxis(self, self.controller.y)
        else:
            self.y = None

        if self.controller.z:
            self.z = ControllerThreadAxis(self, self.controller.z)
        else:
            self.z = None
            
        self.build_axes()
        
        
    def idle(self):
        '''return true if the thread is idle'''
        return self._idle.is_set()
        
    def wait_idle(self):
        while True:
            time.sleep(0.15)
            if self.idle():
                break
        
    def offload(self, axis, name, args):
        self.queue.put(axis, name, args)

    def run(self):
        self.running.set()
        self._idle.clear()
        while self.running.is_set():
            try:
                (axis, name, args) = self.queue.get(True, 0.1)
                self._idle.clear()
            except Queue.Empty:
                self._idle.set()
                continue
            axis.__dict__[name](*args)
    
    def stop(self):
        self.running.clear()        

class CNCGUI(QMainWindow):
    cncProgress = pyqtSignal()
    
    def __init__(self):
        QMainWindow.__init__(self)

        self.cnc_raw = get_cnc()
        self.cnc_raw.on()
        self.cnc_ipc = ControllerThread(self.cnc_raw)
        self.initUI()
        
        # Offload callback to GUI thread so it can do GUI ops
        self.cncProgress.connect(self.processCncProgress)
        
        if self.cnc_raw is None:
            dbg("Disabling all motion controls on no CNC")
            self.setControlsEnabled(False)
        
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
        self.obj_mag.setText('Magnification: %f' % self.obj_config["mag"])
        self.obj_x_view.setText('X view (um): %f' % self.obj_config["x_view"])
        self.obj_y_view.setText('Y view (um): %f' % self.obj_config["y_view"])
    
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
        self.video_container.setFocusPolicy(Qt.ClickFocus)
        # TODO: do something more proper once integrating vodeo feed
        w, h = 640, 480
        self.video_container.setMinimumSize(w, h)
        self.video_container.resize(w, h)
        policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.video_container.setSizePolicy(policy)
        
        layout.addWidget(self.video_container)
        
        return layout
    
    def home(self):
        dbg('Home requested')
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
                imager = VCImager()
            elif itype == 'gstreamer':
                raise Exception('FIXME: implement gstreamer image feed')
            else:
                raise Exception('Invalid imager type %s' % itype)
        if not config:
            raise Exception("missing uscope config")
        if not self.obj_config:
            raise Exception("missing obj config")
        
        rconfig.dry = dry
        
        def emitCncProgress(pictures_to_take, pictures_taken, image, first):
            self.emit(SIGNAL('cncProgress'), pictures_to_take, pictures_taken, image, first)
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
    
    def plannerDone(self):
        # Cleanup camera objects
        self.pt = None
        self.setControlsEnabled(True)
        if config['cnc']['startup_run_exit']:
            print 'Planner debug break on completion'
            os._exit(1)

    def get_bottom_layout(self):
        bottom_layout = QHBoxLayout()
        
        axes_gb = QGroupBox('Axes')
        axes_layout = QHBoxLayout()
        
        self.home_pb = QPushButton("Home all")
        self.home_pb.connect(self.home_pb, SIGNAL("clicked()"), self.home)
        axes_layout.addWidget(self.home_pb)

        self.go_abs_pb = QPushButton("Go abs all")
        self.go_abs_pb.connect(self.go_abs_pb, SIGNAL("clicked()"), self.go_abs)
        axes_layout.addWidget(self.go_abs_pb)
    
        self.go_rel_pb = QPushButton("Go rel all")
        self.go_rel_pb.connect(self.go_rel_pb, SIGNAL("clicked()"), self.go_rel)
        axes_layout.addWidget(self.go_rel_pb)

        self.axes = dict()
        for axis in self.cnc_ipc.axes:
            axisw = Axis(axis)
            print 'Creating axis %s' % axis.name
            self.axes[axis.name] = axisw
            axes_layout.addWidget(axisw)
        axes_gb.setLayout(axes_layout)
        bottom_layout.addWidget(axes_gb)
        
        
        scan_gb = QGroupBox('Scan')
        scan_layout = QVBoxLayout()

        # TODO: add overlap widgets
        
        run_layout = QGridLayout()
        run_layout.addWidget(QLabel('Job name'), 0, 0)
        self.job_name_le = QLineEdit('default')
        run_layout.addWidget(self.job_name_le, 0, 1)
        self.go_pb = QPushButton("Go")
        self.go_pb.clicked.connect(self.run)
        run_layout.addWidget(self.go_pb, 1, 0)
        self.pb = QProgressBar()
        run_layout.addWidget(self.pb, 1, 1)
        run_layout.addWidget(QLabel('Dry?'), 2, 0)
        self.dry_cb = QCheckBox()
        self.dry_cb.setChecked(self.dry())
        run_layout.addWidget(self.dry_cb, 2, 1)
        scan_layout.addLayout(run_layout)
        
        scan_gb.setLayout(scan_layout)
        bottom_layout.addWidget(scan_gb)

        return bottom_layout
        
    def initUI(self):
        self.setGeometry(300, 300, 250, 150)        
        self.setWindowTitle('pr0ncnc')    
        self.show()
        
        # top layout
        layout = QVBoxLayout()
        
        layout.addLayout(self.get_config_layout())
        layout.addLayout(self.get_video_layout())
        layout.addLayout(self.get_bottom_layout())
        
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        
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
    app = QApplication(sys.argv)
    _gui = CNCGUI()
    sys.exit(app.exec_())
