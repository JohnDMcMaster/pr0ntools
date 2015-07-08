#!/usr/bin/python

import sys
from PyQt4 import QtGui, QtCore

class Test(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.points = []
        self.initUI()
        self.fn = '../cf/sample/out.png'
        # orig: 1527x736
        
        self.crs = [106, 50]
        m = 14.436969377188399
        b = 10.0
        self.xy_mb = [[m, b], [m, b]]
        
        self.state = {}
        for (c, r) in self.cr():
            self.state[(c, r)] = False

    def cr(self):
        for c in xrange(self.crs[0] + 1):
            for r in xrange(self.crs[1] + 1):
                yield (c, r)

    def xy(self):
        '''Generate (x0, y0) upper left and (x1, y1) lower right (inclusive) tile coordinates'''
        for c in xrange(self.crs[0] + 1):
            (xm, xb) = self.xy_mb[0]
            x = int(xm * c + xb)
            for r in xrange(self.crs[1] + 1):
                (ym, yb) = self.xy_mb[1]
                y = int(ym * r + yb)
                yield (x, y), (x + xm, y + ym)

    def xy_cr(self):
        for c in xrange(self.crs[0] + 1):
            (xm, xb) = self.xy_mb[0]
            x = int(xm * c + xb)
            for r in xrange(self.crs[1] + 1):
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
        
    def mousePressEvent(self, event):
        print event.pos()

    def mouseReleaseEvent(self, event):
        print event.pos()
        p = event.pos()
        #self.points.append(event.pos())
        c, r = self.xy2cr(p.x(), p.y())
        print 'c=%d, r=%d' % (c, r)
        self.state[(c, r)] = not self.state[(c, r)]
        
        #self.repaint()
        self.update()

    def initUI(self):
        self.setGeometry(10, 10, 1527, 736)
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
            if self.state[(c, r)]:
                qp.setBrush(QtGui.QColor(255, 0, 0, 255))
            else:
                qp.setBrush(QtGui.QColor(0, 255, 0, 255))
            qp.drawRect(x0, y0, x1 - x0, y1 - y0)
    
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = Test()
    sys.exit(app.exec_())

