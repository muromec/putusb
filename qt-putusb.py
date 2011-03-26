import sys
import os
import time
import threading
import Queue

from PyQt4 import QtGui, QtCore

def bg(func):
  def func_bg(*args):

    t = threading.Thread(target=func, args=args)
    t.setDaemon(True)
    t.start()

  return func_bg

# ======================= connect ==============================================

@bg
def connect(event):
    time.sleep(3)
    print "connected"
    event.set()

# ======================= collect_device_info ==================================

@bg
def collect_device_info(q):
    q.put({ 'id': 2, 'path': '/dev/di2', 'size': 520, 'label': 'Unknown',
            'ro': True, 'fixed': True })
    time.sleep(1)
    q.put({ 'id': 3, 'path': '/layout', 'size': 218, 'label': 'Layout',
            'ro': True, 'fixed': True })
    time.sleep(1)
    q.put({ 'id': 4, 'path': '/dev/di4', 'size': 516, 'label': 'Unknown',
            'ro': True, 'fixed': True })
    time.sleep(2)
    q.put({ 'id': 5, 'path': '/kernel1', 'size': 127, 'label': 'Kernel 1',
            'ro': False, 'fixed': False })
    time.sleep(1)
    q.put({ 'id': 6, 'path': '/kernel2', 'size': 127, 'label': 'Kernel 2',
            'ro': False, 'fixed': False })
    time.sleep(1)
    q.put({ 'id': 7, 'path': '/dev/di7', 'size': 127, 'label': 'Unknown',
            'ro': True, 'fixed': True })
    time.sleep(1)
    q.put({ 'id': 8, 'path': '/root', 'size': 127, 'label': 'Root',
            'ro': False, 'fixed': True })
    time.sleep(3)
    q.put({ 'id': 9, 'path': '/home', 'size': 127, 'label': 'Home',
            'ro': False, 'fixed': True })
    time.sleep(1)
    q.put(None)

# ======================= ConnectionWidget =====================================

class ConnectionWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        vbox = QtGui.QVBoxLayout()

        self.status = QtGui.QLabel("Not connected")
        # self.icon = QtGui.QImage(128, 128, QtGui.QImage.Format_RGB32)
        self.icon = QtGui.QDial(self)
        self.advice = QtGui.QLabel("Connect device...")

        self.status.setAlignment(QtCore.Qt.AlignCenter)
        self.advice.setAlignment(QtCore.Qt.AlignCenter)

        vbox.addWidget(self.status)
        vbox.addWidget(self.icon)
        vbox.addWidget(self.advice)

        self.setLayout(vbox)

    def show_connected(self):
        self.status.setText("Connected")
        # update icon
        self.advice.setText("Preparing...")

# ======================= FlashingWidget =======================================

class FlashingWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)

    def add_partition_widgets(self, partition):
        print "add partition ", partition
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel(str(partition['id'])))
        self.layout.addLayout(hbox)

# ======================= PUWindow =============================================

class PUWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self.setWindowTitle('PutUSB')

# ======================= PUApplication ========================================

class PUApplication(QtGui.QApplication, threading.Thread):

    def __init__(self, args):
        QtGui.QApplication.__init__(self, args)
        threading.Thread.__init__(self)

        self.win = PUWindow()

        self.conn_widget = ConnectionWidget()
        self.flsh_widget = FlashingWidget()

        self.win.setCentralWidget(self.conn_widget)

        self.win.show()

    def run(self):

        connect_evt = threading.Event()
        connect(connect_evt)
        connect_evt.wait()

        self.conn_widget.show_connected()
        time.sleep(1)
        # self.conn_widget.dispose()

        self.win.setCentralWidget(self.flsh_widget)

        #got_partition_signal = QtCore.pyqtSignal(tuple)
        #got_partition_signal.connect(self.flsh_widget.add_partition_widgets)
        got_partition_signal = QtCore.SIGNAL('gotPData(PyQt_PyObject)')
        self.connect(self, got_partition_signal, self.flsh_widget.add_partition_widgets)

        print "asking for partition data"

        q = Queue.Queue()
        collect_device_info(q)
        while True:
            item = q.get()
            if item is None:
	            break
            #self.flsh_widget.add_partition_widgets(item)
            self.emit(got_partition_signal, item)

# ======================= main() ===============================================

app = PUApplication(sys.argv)
app.start()
sys.exit(app.exec_())

