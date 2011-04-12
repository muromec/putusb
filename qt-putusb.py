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

class PartitionRow(QtCore.QObject):

    click = QtCore.SIGNAL('clicked()')
    def __init__(self, partition):
        self._partition = partition

        self.id_lbl = QtGui.QLabel(str(partition.num))
        self.name_lbl = QtGui.QLabel(partition.name)

        if partition.typ:
            self.file_btn = QtGui.QPushButton('File...')

            self.connect(self.file_btn, self.click, self.select_file)
        else:
            self.file_btn = QtGui.QLabel('Read-Only')

        self.prgr_bar = QtGui.QProgressBar()

        # be human-readable
        fmt = "[%d %s]"
        size = partition.size
        if size > 1024*1024:
          size /= 1024*1024
          quant = "MB"
        else:
          size /= 1024
          quant = "KB"

        self.size_lbl = QtGui.QLabel(fmt % (size,quant))

    def select_file(self,):
        print 'select file'
        fdialog = QtGui.QFileDialog()

        if fdialog.exec_():
          self.fname = unicode(fdialog.selectedFiles()[0])
        else:
          self.fname = None

        print 'selected %s' % self.fname

    def add_to_grid(self, grid, row_id):
        grid.addWidget(self.id_lbl,   row_id, 0)
        grid.addWidget(self.name_lbl, row_id, 1)
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

class MockDevState(object):
    class MockUsb(object):
        def parts(self):
            return [
                putusb.NvidiaUsb.Part(
                  2,
                  "RT",
                  2,
                  200,
                  200,
                  0x800
                )
            ]

    def wait(self, event):
        time.sleep(3)
        self.dev = self.MockUsb()
        event.set()

DevState = MockDevState

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

