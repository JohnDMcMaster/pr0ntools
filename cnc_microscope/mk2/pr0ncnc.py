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
from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4.QtCore import *

import usbio
from usbio.mc import MC


class Example(QtGui.QMainWindow):
	
	def __init__(self):
		super(Example, self).__init__()
		
		self.initUI()
		self.mc = None
		try:
			self.mc = MC()
			self.mc.on()
			if False:
				self.mc.y.jog(100)
				sys.exit(1)
		except:
			print 'Failed to open device'
			#raise
				
	def x(self, n):
		if self.mc is None:
			return
		self.mc.x.jog(n)
	
	def y(self, n):
		if self.mc is None:
			return
		self.mc.y.jog(n)
		
	def initUI(self):
		self.setGeometry(300, 300, 250, 150)		
		self.setWindowTitle('Message box')	
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
	
		
		k = event.key()
		inc = 100
		if k == Qt.Key_Left:
			print 'left'
			self.x(-inc)
		elif k == Qt.Key_Right:
			print 'right'
			self.x(inc)
		elif k == Qt.Key_Up:
			print 'up'
			self.y(inc)
		elif k == Qt.Key_Down:
			print 'down'
			self.y(-inc)
	
def main():
	app = QtGui.QApplication(sys.argv)
	ex = Example()
	sys.exit(app.exec_())


if __name__ == '__main__':
	#print QtCore.Qt.Key_Left
	main()

