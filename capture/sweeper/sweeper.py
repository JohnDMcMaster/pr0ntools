#!/usr/bin/python

import sys
from PyQt4 import QtGui, QtCore
import os
import json

from PIL import Image

states = 'vmu'
bitmap2fill = {
        'v':'white',
        'm':'blue',
        'u':'orange',
        }
fill2bitmap = {
        (255, 255, 255):'v',    # white
        (0, 0, 255):    'm',    # blue
        (255, 165, 0):  'u',    # orange
        }

class Test(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.points = []
        j_dir = '../cf/sample/'
        self.fn_j = os.path.join(j_dir, 'out.json')
        self.j = json.load(open(self.fn_j, 'r'))
        
        print 'Loading images...'
        self.fn_bmp = os.path.join(j_dir, self.j['png'])
        self.bmp = Image.open(self.fn_bmp)
        self.fn_img = os.path.join(j_dir, self.j['img'])
        self.img = Image.open(self.fn_img)
        print 'Images loaded'
        
        self.crs = [self.j['axes'][order]['n'] for order in xrange(2)]
        self.xy_mb = [[self.j['axes'][order]['m'], self.j['axes'][order]['b']] for order in xrange(2)]
        
        '''
        [c][r] to tile state
        m: metal
        v: void / nothing
        u: unknown
        '''
        self.ts = {}
        for (c, r) in self.cr():
            p = self.bmp.getpixel((c, r))
            self.ts[(c, r)] = fill2bitmap[p]

        self.initUI()

    def cr(self):
        for c in xrange(self.crs[0]):
            for r in xrange(self.crs[1]):
                yield (c, r)

    def xy(self):
        '''Generate (x0, y0) upper left and (x1, y1) lower right (inclusive) tile coordinates'''
        for c in xrange(self.crs[0]):
            (xm, xb) = self.xy_mb[0]
            x = int(xm * c + xb)
            for r in xrange(self.crs[1]):
                (ym, yb) = self.xy_mb[1]
                y = int(ym * r + yb)
                yield (x, y), (x + xm, y + ym)

    def xy_cr(self):
        for c in xrange(self.crs[0]):
            (xm, xb) = self.xy_mb[0]
            x = int(xm * c + xb)
            for r in xrange(self.crs[1]):
                (ym, yb) = self.xy_mb[1]
                y = int(ym * r + yb)
                yield ((x, y), (int(x + xm), int(y + ym))), (c, r)
    
    def xy2cr(self, x, y):
        m, b = self.xy_mb[0]
        c = int((x - b) / m)

        m, b = self.xy_mb[1]
        r = int((y - b) / m)
        
        if c > self.crs[0]:
            raise ValueError("max col %d, got %d => %d" % (self.crs[0], x, c))
        if r > self.crs[1]:
            raise ValueError("max row %d, got %d => %d" % (self.crs[1], y, r))
        
        return (c, r)
        
    #def mousePressEvent(self, event):
    #    print event.pos()

    def mouseReleaseEvent(self, event):
        #print event.pos()
        p = event.pos()
        #self.points.append(event.pos())
        c, r = self.xy2cr(p.x(), p.y())
        #print 'c=%d, r=%d' % (c, r)
        # cycle to next state
        old = self.ts[(c, r)]
        oldi = states.index(old)
        statep = states[(oldi + 1) % len(states)]
        self.ts[(c, r)] = statep
        
        #self.repaint()
        self.update()

    def initUI(self):
        self.setGeometry(0, 0, self.img.size[0] + 20, self.img.size[1])
        self.setWindowTitle('Colours')
        self.show()

    def paintEvent(self, e):

        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawRectangles(qp)
        qp.end()
        
    def drawRectangles(self, qp):
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
        
        for ((x0, y0), (x1, y1)), (c, r) in self.xy_cr():
            qp.setBrush(QtGui.QColor(bitmap2fill[self.ts[(c, r)]]))
            qp.drawRect(x0, y0, x1 - x0, y1 - y0)
    
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = Test()
    sys.exit(app.exec_())

