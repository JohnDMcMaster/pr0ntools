#!/usr/bin/python

import sys
from PyQt4 import QtGui, QtCore
import os
import json
import xmlrpclib
from xmlrpclib import Binary
from PIL import Image
#from PyQt4 import Qt
from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPixmap, QDesktopWidget
from PyQt4.QtCore import Qt
from PIL import Image, ImageDraw, ImageStat

import cfb
from cfb import CFB
from cfb import cfb_save, cfb_save_debug
from cfb import filt_unk_groups, cfb_verify, prop_ag, munge_unk_cont
from cfb import bitmap2fill, fill2bitmap

class GridWidget(QWidget):
    def __init__(self, tmp_dir):
        QWidget.__init__(self)
        self.tmp_dir = tmp_dir
        # images are a bit big
        self.sf = 0.5

        #self.cfb.crs = None
        #self.cfb.xy_mb = None
        #self.cfb.bitmap = None
        self.cfb = None
        self.jpg_fn = None
        self.pixmap = None
        self.img_label = QLabel()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.img_label)
        self.setLayout(self.layout)

    def server_next(self, cfb, jpg_fn):
        self.cfb = cfb
        self.jpg_fn = jpg_fn
        if self.jpg_fn:
            self.pixmap = QPixmap(self.jpg_fn)
            self.img_label.setPixmap(self.pixmap)

            # this ensures the label can also re-size downwards
            self.img_label.setMinimumSize(1, 1)
            # get resize events for the label
            self.img_label.installEventFilter(self)

        w = self.cfb.crs[0] * self.cfb.xy_mb[0][0] * self.sf
        h = self.cfb.crs[1] * self.cfb.xy_mb[1][0] * self.sf
        self.setMinimumSize(w, h)
        #self.resize((w, h)

    def eventFilter(self, source, event):
        if (source is self.img_label and event.type() == QtCore.QEvent.Resize):
            # re-scale the pixmap when the label resizes
            self.img_label.setPixmap(self.pixmap.scaled(
                self.img_label.size(), QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation))
        return QWidget.eventFilter(self, source, event)
    
    def gen_png(self):
        png_fn = os.path.join(self.tmp_dir, 'out.png')
        im = Image.new("RGB", self.cfb.crs, "white")
        draw = ImageDraw.Draw(im)
        for (c, r) in self.cfb.cr():
            draw.rectangle((c, r, c, r), fill=bitmap2fill[self.cfb.bitmap[(c, r)]])
        im.save(png_fn)
        return open(png_fn, 'r').read()

    
    #def mousePressEvent(self, event):
    #    print event.pos()

    def mouseReleaseEvent(self, event):
        #print event.pos()
        p = event.pos()
        c, r = self.cfb.xy2cr(p.x(), p.y(), self.sf)
        #print 'c=%d, r=%d' % (c, r)
        # cycle to next state
        old = self.cfb.bitmap[(c, r)]
        oldi = cfb.states.index(old)
        statep = cfb.states[(oldi + 1) % len(cfb.states)]
        self.cfb.bitmap[(c, r)] = statep
        
        #self.repaint()
        self.parent().update()

    def paintEvent(self, e):
        if self.jpg_fn:
            return
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawRectangles(qp)
        qp.end()
        
    def drawRectangles(self, qp):
        # No image loaded => nothing to render
        if not self.cfb.crs:
            return
        
        color = QtGui.QColor(0, 0, 0)
        color.setNamedColor('#d4d4d4')
        qp.setPen(color)

        '''
        qp.setBrush(QtGui.QColor(200, 0, 0))
        qp.drawRect(10, 15, 90, 60)

        qp.setBrush(QtGui.QColor(255, 80, 0, 160))
        qp.drawRect(130, 15, 90, 60)

        qp.setBrush(QtGui.QColor(25, 0, 90, 200))
        qp.drawRect(250, 15, 90, 60)
        '''
        
        for ((x0, y0), (x1, y1)), (c, r) in self.cfb.xy_cr(sf=self.sf):
            qp.setBrush(QtGui.QColor(bitmap2fill[self.cfb.bitmap[(c, r)]]))
            qp.drawRect(x0, y0, x1 - x0, y1 - y0)

class Test(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.server = xmlrpclib.ServerProxy('http://localhost:9000', allow_none=True)

        self.tmp_dir = '/tmp/pr0nsweeper'
        if not os.path.exists(self.tmp_dir):
            os.mkdir(self.tmp_dir)
        self.png_fn = os.path.join(self.tmp_dir, 'job.png')
        self.jpg_fn = os.path.join(self.tmp_dir, 'job.jpg')

        self.initUI()

        self.server_next()
    
    def keyPressEvent(self, event):
        def accept():
            if self.job:
                self.server.job_done(self.job['name'], Binary(self.grid1.gen_png()), '')
            self.server_next()

        def reject():
            if self.job:
                self.server.job_done(self.job['name'], None, 'rejected')
            self.server_next()

        def default():
            pass
            print event.key()
        
        # Convert unknowns to metal
        def m():
            for (c, r) in self.cfb.cr():
                ts = self.cfb.bitmap[(c, r)]
                if ts == 'u':
                    self.cfb.bitmap[(c, r)] = 'm'
            self.update()

        # Convert unknowns to empty
        def w():
            for (c, r) in self.cfb.cr():
                ts = self.cfb.bitmap[(c, r)]
                if ts == 'u':
                    self.cfb.bitmap[(c, r)] = 'v'
            self.update()
        
        def l():
            self.update()
        
        {
            Qt.Key_Enter: accept,
            Qt.Key_Return: accept,
            Qt.Key_Escape: reject,
            Qt.Key_M: m,
            Qt.Key_W: w,
            Qt.Key_L: l,
        }.get(event.key(), default)()
    
    def server_next(self):
        self.job = self.server.job_req()
        if self.job is None:
            print 'WARNING: no job'
            self.setWindowTitle('pr0nsweeper: Idle')
            self.png = Image.open('splash.png').convert(mode='RGB')
            self.cfb = CFB()
            self.cfb.crs = self.png.size
            self.cfb.xy_mb = [(30.0, 0.0), (30.0, 0.0)]
            self.grid1.server_next(None, None)
            self.grid2.server_next(None, None)
            self.img = None
        else:
            print 'RX %s' % self.job['name']
            self.setWindowTitle('pr0nsweeper: ' + self.job['name'])
            self.j = self.job['json']
            
            print 'Exporting images...'
            open(self.png_fn, 'w').write(self.job['png'].data)
            open(self.jpg_fn, 'w').write(self.job['img'].data)
    
            self.cfb = CFB()
            self.cfb.crs = [self.j['axes'][order]['n'] for order in xrange(2)]
            self.cfb.xy_mb = [[self.j['axes'][order]['m'], self.j['axes'][order]['b']] for order in xrange(2)]
    
            print 'Loading images...'
            self.png = Image.open(self.png_fn)
            self.img = Image.open(self.jpg_fn)
    
            print 'Images loaded'
        
        '''
        [c][r] to tile state
        m: metal
        v: void / nothing
        u: unknown
        '''
        self.cfb.bitmap = {}
        for (c, r) in self.cfb.cr():
            p = self.png.getpixel((c, r))
            self.cfb.bitmap[(c, r)] = fill2bitmap[p]

        self.grid1.server_next(self.cfb, None)
        self.grid2.server_next(self.cfb, self.jpg_fn)

        '''
        self.setGeometry(0, 0,
                    (self.img.size[0] * self.grid1.sf + 20) * 1,
                    (self.img.size[1] * self.grid1.sf + 20) * 2)
        '''

        '''
        if self.job is None:
            self.setGeometry(0, 0,
                        (self.cfb.crs[0] * self.cfb.xy_mb[0][0] * self.grid1.sf) * 1 + 20,
                        (self.cfb.crs[1] * self.cfb.xy_mb[1][0] * self.grid1.sf) * 1 + 20)
        else:
            self.setGeometry(0, 0,
                        (self.img.size[0] * self.grid1.sf + 20) * 1,
                        (self.img.size[1] * self.grid1.sf + 20) * 2)
        '''
        #dw = QDesktopWidget()
        #self.setGeometry(0, 0, dw.width(), dw.height())
        self.update()


    def initUI(self):
        self.setWindowTitle('pr0nsweeper: init')
        l = QHBoxLayout()
        self.grid1 = GridWidget(self.tmp_dir)
        l.addWidget(self.grid1)
        self.grid2 = GridWidget(self.tmp_dir)
        l.addWidget(self.grid2)
        self.setLayout(l)
        #self.setCentralWidget(self.grid)
        self.show()
    
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = Test()
    sys.exit(app.exec_())

