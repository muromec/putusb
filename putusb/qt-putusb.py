import sys
import os
import time
import threading
import Queue

from PyQt4 import QtGui, QtCore

from putusb import putusb

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

        super(PartitionRow, self).__init__()
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

        self.fname = None


    def select_file(self,):
        print 'select file'
        fdialog = QtGui.QFileDialog()

        if fdialog.exec_():
          self.fname = unicode(fdialog.selectedFiles()[0])
        else:
          self.fname = None

        print 'selected %s' % self.fname
        # TODO: check file size here and reject if bigger

    def add_to_grid(self, grid, row_id):
        grid.addWidget(self.id_lbl,   row_id, 0)
        grid.addWidget(self.name_lbl, row_id, 1)
        grid.addWidget(self.file_btn, row_id, 3)
        grid.addWidget(self.prgr_bar, row_id, 4)
        grid.addWidget(self.size_lbl, row_id, 5)

# ======================= FlashingWidget =======================================

class FlashingWidget(QtGui.QWidget):

    flash = QtCore.SIGNAL("flash(int, QString)")

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)

        self._partitions_num = 1

        self.partitions = []

        self.commit_btn = QtGui.QPushButton('Commit')
        # TODO: make it disable or hidden for the first time

        click = QtCore.SIGNAL('clicked()')

        self.connect(self.commit_btn, click , self.commit)

        self.layout.addWidget(self.commit_btn, 20, 4)

    def add_partition_widgets(self, partition):
        print "add partition ", partition
        part = PartitionRow(partition)
        part.add_to_grid(self.layout, self._partitions_num)
        self.partitions.append(part)
        # FIXME: maby append _partition?

        self._partitions_num += 1

    def commit(self):
        print 'commit all'

        for part in self.partitions:
          if part.fname is None:
            continue

          self.emit(self.flash, part._partition.num, part.fname)

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


        def flash_part(self, num, fname):
            print num, fname

    def wait(self, event):
        time.sleep(3)
        self.dev = self.MockUsb()
        event.set()

#DevState = MockDevState

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

        self.connect(self.flsh_widget, FlashingWidget.flash,
            self.flash_part)

        print "asking for partition data"

        for part in self.state.dev.parts():
          self.emit(got_partition_signal, part)

    def flash_part(self, num, fname):
        # TODO: progress bar here
        self.state.dev.flash_part(num, fname)

# ======================= main() ===============================================

app = PUApplication(sys.argv)
app.start()
sys.exit(app.exec_())

