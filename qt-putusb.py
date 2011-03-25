import sys
import os
import time
import threading

from PyQt4 import QtGui, QtCore

def bg(func):
  def func_bg(*args):

    t = threading.Thread(target=func, args=args)
    t.setDaemon(True)
    t.start()

  return func_bg

@bg
def connect(event):
    time.sleep(4)
    print "connected"
    event.set()

class ConnectionWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        vbox = QtGui.QVBoxLayout()

        self.status = QtGui.QLabel("Not connected")
        # self.icon = QtGui.QImage(128, 128, QtGui.QImage.Format_RGB32)
        self.icon = QtGui.QDial()
        self.advice = QtGui.QLabel("Connect device...")

        vbox.addWidget(self.status)
        vbox.addWidget(self.icon)
        vbox.addWidget(self.advice)

        self.setLayout(vbox)

    def show_connected(self):
        print "showing connected"
        self.status.setText("Connected")
        # update icon
        self.advice.setText("Device found")

class FlashingWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        hbox = QtGui.QHBoxLayout()

        push1 = QtGui.QPushButton("Push 1")
        push2 = QtGui.QPushButton("Push 2")

        hbox.addWidget(push1)
        hbox.addWidget(push2)

        self.setLayout(hbox)

class PUWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self.setWindowTitle('PutUSB')

class PUApplication(QtGui.QApplication):

    def __init__(self, args):
        QtGui.QApplication.__init__(self, args)

        self.win = PUWindow()

        self.conn_widget = ConnectionWidget()
        self.flsh_widget = FlashingWidget()

        self.win.setCentralWidget(self.conn_widget)

        self.win.show()

    @bg
    def run_(self):

        wevent = threading.Event()
        connect(wevent)
        wevent.wait()

        self.conn_widget.show_connected()
        time.sleep(2)
        self.win.setCentralWidget(self.flsh_widget)

app = PUApplication(sys.argv)
app.run_()
sys.exit(app.exec_())

