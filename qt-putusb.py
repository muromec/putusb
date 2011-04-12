import sys
import os
import time
import threading
import Queue

from PyQt4 import QtGui, QtCore

import putusb

def bg(func):
  def func_bg(*args):

    t = threading.Thread(target=func, args=args)
    t.setDaemon(True)
    t.start()

  return func_bg

# ======================= connect ==============================================

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

# ======================= PartitionRow =========================================

class PartitionRow:

    def __init__(self, partition):
        self._partition = partition

        self.id_lbl = QtGui.QLabel(str(partition.num))
        self.name_lbl = QtGui.QLabel(partition.name)
        self.path_lbl = QtGui.QLabel(partition.name)
        self.file_btn = QtGui.QLabel('Read-Only') if partition.typ == 0 \
                        else QtGui.QPushButton('File...')
        self.prgr_bar = QtGui.QProgressBar()
        self.size_lbl = QtGui.QLabel('[' + str(partition.size/1024/1024) + 'MB]' if partition.typ == 0 \
                                else '{' + str(partition.size/1024/1024) + 'MB}')

    def add_to_grid(self, grid, row_id):
        grid.addWidget(self.id_lbl,   row_id, 0)
        grid.addWidget(self.name_lbl, row_id, 1)
        grid.addWidget(self.path_lbl, row_id, 2)
        grid.addWidget(self.file_btn, row_id, 3)
        grid.addWidget(self.prgr_bar, row_id, 4)
        grid.addWidget(self.size_lbl, row_id, 5)

# ======================= FlashingWidget =======================================

class FlashingWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)

        self._partitions_num = 0

    def add_partition_widgets(self, partition):
        print "add partition ", partition
        PartitionRow(partition).add_to_grid(self.layout, self._partitions_num)
        self._partitions_num += 1

# ======================= PUWindow =============================================

class PUWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self.setWindowTitle('PutUSB')

# ======================= PUApplication ========================================

class DevState(object):
    def wait(self, event):
        while True:
            try:
                self.dev = putusb.NvidiaUsb()
                break
            except IOError:
                self.dev = None
                time.sleep(1)

        # deal with it
        self.dev.boot("bin/tegra_pre_boot.bin", "bin/fastboot.stock.bin")

        event.set()

class PUApplication(QtGui.QApplication, threading.Thread):

    def __init__(self, args):
        QtGui.QApplication.__init__(self, args)
        threading.Thread.__init__(self)

        self.win = PUWindow()

        self.conn_widget = ConnectionWidget()
        self.flsh_widget = FlashingWidget()

        self.win.setCentralWidget(self.conn_widget)

        self.win.show()
        self.state = DevState()

    def run(self):

        connect_evt = threading.Event()
        bg(self.state.wait)(connect_evt)
        connect_evt.wait()

        self.conn_widget.show_connected()
        time.sleep(1) # wtf?
        # self.conn_widget.dispose()

        self.win.setCentralWidget(self.flsh_widget)

        #got_partition_signal = QtCore.pyqtSignal(tuple)
        #got_partition_signal.connect(self.flsh_widget.add_partition_widgets)
        got_partition_signal = QtCore.SIGNAL('gotPData(PyQt_PyObject)')
        self.connect(self, got_partition_signal, self.flsh_widget.add_partition_widgets)

        print "asking for partition data"

        for part in self.state.dev.parts():
          self.emit(got_partition_signal, part)

# ======================= main() ===============================================

app = PUApplication(sys.argv)
app.start()
sys.exit(app.exec_())

