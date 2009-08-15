#!/usr/bin/python

# boxlayout.py

import sys
from PyQt4 import QtGui, QtCore
import putusb
from threading import Thread

from time import sleep

def bg(func):
  def func_bg(*args):

    t = Thread(target=func, args=args)
    t.setDaemon(True)
    t.start()

  return func_bg


class Main(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        click = QtCore.SIGNAL('clicked()')

        self.setWindowTitle('Ezx Flash')

        find = QtGui.QPushButton("Find device")
        rcfg = QtGui.QPushButton("Read config")
        wcfg = QtGui.QPushButton("Write config")
        fbtn = QtGui.QPushButton("Flash")
        clr = QtGui.QPushButton("Clear")
        txt = QtGui.QTextEdit()
        namelbl = QtGui.QLabel()
        statelbl = QtGui.QLabel()

        cmd = QtGui.QLineEdit()
        id_select = QtGui.QComboBox()

        idx = 0
        for machid in putusb.machids:
          name = putusb.machids[machid]
          machid = QtCore.QVariant(machid)

          id_select.insertItem(idx,name,machid)
          idx+=1

        self.connect( find, click, self.findDev )
        self.connect( rcfg, click, self.showInfo )
        self.connect( wcfg, click, self.setInfo )
        self.connect( fbtn, click, self.flash )
        self.connect( clr, click, txt.clear )
        self.connect(
            self, QtCore.SIGNAL('select'),
            self.selectFiles
        )


        vbox = QtGui.QVBoxLayout()

        # first line
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(find)
        hbox.addWidget(namelbl)
        hbox.addWidget(statelbl)
        hbox.addStretch(1)
        hbox.addWidget(rcfg)
        hbox.addWidget(wcfg)
        hbox.addWidget(fbtn)
        hbox.addWidget(clr)

        vbox.addLayout(hbox)

        # second line
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(cmd)
        hbox.addWidget(id_select)

        vbox.addLayout(hbox)

        txt.setReadOnly(True)
        vbox.addWidget(txt)

        # done
        self.setLayout(vbox)
        self.resize(300, 150)

        # save for further usage
        self.log = txt
        self.cmdline = cmd
        self.machid = id_select
        self.name = namelbl
        self.statelbl = statelbl

        self.flash = None


    def inf(self, text):
        self.log.append(text)
        print text

    def state(self, state):
        self.statelbl.setText(state)

    def config(self):
        idx = self.machid.currentIndex()
        machid,x = self.machid.itemData(idx).toInt()

        cmdline = str(self.cmdline.text())

        self.inf("id: %d"%machid)

        return putusb.encode_params(cmdline, machid)

    @bg
    def showInfo(self):

        self.inf("version: %s"%self.dev.version())
        self.inf("serial: %s"%self.dev.serial())

        if 'read' not in dir(self.dev):
          self.inf("memory read not supported")
          self.inf("loading blob to read memory")
          self.sendBlob()

        magic = self.dev.get(0x000c0000+131072-4,4)
        magic = putusb.decode_bytes(magic)

        if magic == 0xdeadb007:
          self.inf("magic found")

          self.state("reading config")
          cfg = self.dev.get(0x000c0000,131072)
          self.inf("genblob config:")

          line, machid, magic = putusb.decode_params(cfg)
          self.cmdline.setText(line)

          if machid in putusb.machids:
            self.inf("known phone")
            idx = putusb.machids.keys().index(machid)
            self.machid.setCurrentIndex(idx)

            print idx

          self.inf("cmdline: %s"%line)
          self.inf("machine: %s (%d)"%(putusb.machids[machid], machid))
          self.inf("magic: %x"%magic)
        else:
          self.inf("magic not found")
          self.inf("genblob not configured")

        self.state("")

    @bg
    def setInfo(self):
        self.state("writing config")
        cfg = self.config()

        if len(cfg) != 131072:
          print len(cfg)
          self.inf("invalid config")
          return

        if 'flash' not in dir(self.dev):
          self.inf("flashing not supported")
          self.sendBlob()

        self.dev.flash(0x000c0000, cfg)

        self.inf("config set")
        self.state("")

    @bg
    def findDev(self):
        self.state("looking for device")
        try:
          self.dev = putusb.MotoUsb()
          name = self.dev.name()
        except:
          name = "no device"

        self.name.setText(name)
        self.state("")

    def sendBlob(self):
        self.dev.version()
        self.dev.serial()

        self.state("loading blob")
        self.dev.set(0xa1000000, putusb.encode_bytes(0x0D3ADCA7))
        self.dev.run_file("blob")

        while self.dev.dev.idProduct != 0xbeef:
          self.findDev()
          sleep(0.3)

        self.state("")

    def selectFiles(self):
        print "select files"
        fdialog = QtGui.QFileDialog()
        fdialog.exec_()

        self.flash = str(fdialog.selectedFiles()[0])

        print "selected"


    @bg
    def flash(self):

        if 'flash' not in dir(self.dev):
          self.inf("memory read not supported")
          self.inf("loading blob to read memory")
          self.sendBlob()

        self.inf("flash")

        # viva bydlocode!
        # dont even want to know, how this should be
        # done with suckfull signal-signal-by-slot oops.
        # damn qt and damn python segfaults when 
        # trying to run fdialog from here
        self.emit(QtCore.SIGNAL('select'))

        while self.flash == None:
          sleep(0.1)

        if self.flash == False:
            self.flash = None
            return

        path = self.flash

        self.inf("going to flash %s"%path)

        self.state("flashing")
        try:
          self.dev.flash_index(path)
          self.inf("ok")
        except:
          self.inf("fail")

        self.state("")

app = QtGui.QApplication(sys.argv)
w = Main()
w.show()
sys.exit(app.exec_())

