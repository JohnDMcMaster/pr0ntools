#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
ZetCode PyQt4 tutorial 

This program shows a confirmation 
message box when we click on the close
button of the application window. 

author: Jan Bodnar
website: zetcode.com 
last edited: October 2011
"""

import sys
from PyQt4 import QtGui
from PyQt4.QtGui import *
from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4.QtCore import *
from planner import Planner, ControllerPlanner
from imager import DummyImager, VideoCaptureImager, PILImager

import usbio
from usbio.mc import MC

class Axis(QtGui.QWidget):
	def __init__(self, axis, parent = None):
		super(Axis, self).__init__()
		# controller axis object
		self.axis = axis
		self.initUI()
		
	def initUI(self):
		gb = QGroupBox()
		#al = QHBoxLayout()
		
		self.pos_gb = QGroupBox("pos (um)")
		gb.addWidget(self.pos_gb)
		self.pos_value = QLabel("Unknown")
		self.pos_gb.addWidget(self.pos_value)
		self.home_button = QPushButton("Home")
		self.pos_gb.addWidget(self.home_button)
		
		self.meas_gb = QGroupBox("Meas (um)")
		gb.addWidget(self.meas_gb)
		self.meas_value = QLabel("Unknown")
		self.meas_gb.addWidget(self.meas_value)
		self.meas_reset_button = QPushButton("Reset")
		self.meas_gb.addWidget(self.meas_reset_button)
		
		self.addWidget(gb)

class Example(QtGui.QMainWindow):
	
	def __init__(self):
		super(Example, self).__init__()

		self.mc = None
		
		if 0:
			self.run(True)
			print 'Planner debug break'
			sys.exit(1)
		
		try:
			self.mc = MC()
			self.mc.on()
		except:
			print 'Failed to open device'
			raise
		
		#self.controller = 
			
		if 0:
			self.run(True)
			print 'Planner debug break'
			sys.exit(1)
		
			
			
		self.initUI()
				
	def x(self, n):
		if self.mc is None:
			return
		self.mc.x.jog(n)
	
	def y(self, n):
		if self.mc is None:
			return
		self.mc.y.jog(n)
		
	def z(self, n):
		if self.mc is None:
			return
		self.mc.z.jog(n)
		
	def get_config_layout(self):
		cl = QVBoxLayout()
		
		l = QLabel("Objective")
		cl.addWidget(l)
		cb = QComboBox()
		cl.addWidget(cb)
		
		l = QLabel("Resolution")
		cl.addWidget(l)
		cb = QComboBox()
		cl.addWidget(cb)
		
		l = QLabel("Imaging device")
		cl.addWidget(l)
		cb = QComboBox()
		cl.addWidget(cb)

		l = QLabel("USBIO device")
		cl.addWidget(l)
		cb = QComboBox()
		cl.addWidget(cb)

		return cl
	
	def get_video_layout(self):
		video_layout = QHBoxLayout()
		
		view_layout = QVBoxLayout()
		l = QLabel("View")
		view_layout.addWidget(l)
		gv = QGraphicsView()

		scn = QGraphicsScene( gv )
		#scn.setSceneRect( gv.rect() )
		gv.setScene( scn )
		self.gv = gv
		self.scn = scn
		view_layout.addWidget(gv)
		video_layout.addLayout(view_layout)
		
		last_layout = QVBoxLayout()
		l = QLabel("Last")
		last_layout.addWidget(l)
		gv = QGraphicsView()
		last_layout.addWidget(gv)
		video_layout.addLayout(last_layout)
		
		return video_layout
	
	def home(self):
		print 'Home requested'
		if self.mc:
			self.mc.home()
			
	def progress_cb(self, pictures_to_take, pictures_taken, image, first):
		if first:
			self.pb.setMinimum(0)
			self.pb.setMaximum(pictures_to_take)
		else:
			print 'took %s at %d / %d' % (image, pictures_taken, pictures_to_take)
			if False:
				pix = QPixmap( image )
				# This will be a bit messy...maybe should make this a floating window
				#self.gv.setFixedSize( pix.width(), pix.height() )
				self.gv.setFixedSize( 400, 400 )
				self.scn.addPixmap( pix )
			
		self.pb.setValue(pictures_taken)
			
	def run(self, dry = False):
		controller = None
		imager = None
		if not dry:
			controller = self.mc
			#imager = VideoCaptureImager()
			imager = PILImager()
			self.planner = ControllerPlanner(self.progress_cb, controller, imager)
		else:
			self.planner = Planner()
		self.planner.run()
	
	def get_bottom_layout(self):
		bottom_layout = QHBoxLayout()
		
		axes_gb = QGroupBox('Axes')
		axes_layout = QHBoxLayout()
		self.home_button = QPushButton("Home all")
		self.home_button.connect(self.home_button, QtCore.SIGNAL("clicked()"), self.home)
		axes_layout.addWidget(self.home_button)
		if 0 and self.mc:
			for axis in self.mc.axes:
				axisw = Axis(axis)
				axes_layout.addWidget(axisw)
		axes_gb.setLayout(axes_layout)
		bottom_layout.addWidget(axes_gb)
		
		
		scan_gb = QGroupBox('Scan')
		scan_layout = QVBoxLayout()
		
		limits_gb = QGroupBox('Limits')
		limits_layout = QGridLayout()
		ul = QPushButton("Set UL")
		limits_layout.addWidget(ul, 0, 0)
		ur = QPushButton("Set UR")
		limits_layout.addWidget(ur, 0, 1)
		ll = QPushButton("Set LL")
		limits_layout.addWidget(ll, 1, 0)
		lr = QPushButton("Set LR")
		limits_layout.addWidget(lr, 1, 1)
		limits_gb.setLayout(limits_layout)
		scan_layout.addWidget(limits_gb)

		# TODO: add overlap widgets
		
		run_layout = QHBoxLayout()
		b = QPushButton("Go")
		b.connect(b, SIGNAL('clicked()'), self.run)
		run_layout.addWidget(b)
		self.pb = QProgressBar()
		run_layout.addWidget(self.pb)
		scan_layout.addLayout(run_layout)

		
		scan_gb.setLayout(scan_layout)
		bottom_layout.addWidget(scan_gb)

		return bottom_layout
		
	def initUI(self):
		self.setGeometry(300, 300, 250, 150)		
		self.setWindowTitle('pr0ncnc')	
		self.show()
		
		# top layout
		tl = QVBoxLayout(self)
		
		tl.addLayout(self.get_config_layout())
		tl.addLayout(self.get_video_layout())
		tl.addLayout(self.get_bottom_layout())
		
		w = QWidget()
		w.setLayout(tl)
		self.setCentralWidget(w)
		
	def initUIOld(self):
		self.setGeometry(300, 300, 250, 150)		
		self.setWindowTitle('Message box')	
		self.show()
		
		l = QHBoxLayout(self)
		
	def keyPressEvent(self, event):
		'''
		print event
		#print dir(event)
		print event.text()
		print 'type: %s' % str(event.type())
		print event.nativeScanCode()
		print event.nativeVirtualKey()
		print len(event.text())
		if event == QtCore.Qt.Key_Left:
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
		elif k == Qt.Key_PageUp:
			print 'up'
			self.z(inc)
		elif k == Qt.Key_PageDown:
			print 'down'
			self.z(-inc)
	
def main():
	app = QtGui.QApplication(sys.argv)
	ex = Example()
	sys.exit(app.exec_())


if __name__ == '__main__':
	#print QtCore.Qt.Key_Left
	main()

