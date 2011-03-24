import sys
import os
from PyQt4 import QtGui, QtCore

class Main(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.setWindowTitle('Test window')

        hbox = QtGui.QHBoxLayout()

        push1 = QtGui.QPushButton("Push Me 1")
        push2 = QtGui.QPushButton("Push Me 2")

        hbox.addWidget(push1)
        hbox.addWidget(push2)

        self.setLayout(hbox)

app = QtGui.QApplication(sys.argv)
win = Main()
win.show()
sys.exit(app.exec_())

