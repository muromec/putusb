import sys
import os
from PyQt4 import QtGui, QtCore

def test_connection():
    time.sleep(10)

class ConnectionWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        hbox = QtGui.QHBoxLayout()

        push1 = QtGui.QPushButton("Push Me 1")
        push2 = QtGui.QPushButton("Push Me 2")

        hbox.addWidget(push1)
        hbox.addWidget(push2)

        self.setLayout(hbox)

class FlashingWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

class QPWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self.setWindowTitle('PutUSB')

        self.conn_widget = ConnectionWidget()
        self.flsh_widget = FlashingWidget()

        self.setCentralWidget(self.conn_widget)


app = QtGui.QApplication(sys.argv)
win = QPWindow()
win.show()
sys.exit(app.exec_())

