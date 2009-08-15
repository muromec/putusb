#!/usr/bin/python

# boxlayout.py

import sys
from PyQt4 import QtGui, QtCore
import putusb


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

        vbox = QtGui.QVBoxLayout()

        # first line
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(find)
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


    def inf(self, text):
        self.log.append(text)

    def config(self):
        idx = self.machid.currentIndex()
        machid,x = self.machid.itemData(idx).toInt()

        cmdline = str(self.cmdline.text())

        self.inf("id: %d"%machid)

        return putusb.encode_params(cmdline, machid)


    def showInfo(self):

        self.inf("version: %s"%self.dev.version())
        self.inf("serial: %s"%self.dev.serial())

        if 'read' not in dir(self.dev):
          self.inf("memory read not supported")
          self.sendBlob()

        magic = self.dev.get(0x000c0000+131072-4,4)
        magic = putusb.decode_bytes(magic)



        if magic == 0xdeadb007:

          cfg = self.dev.get(0x000c0000,131072)
          self.inf("genblob configuration")

          line, machid, magic = putusb.decode_params(cfg)
          self.cmdline.setText(line)

          if machid in putusb.machids:
            self.inf("known phone")
            idx = putusb.machids.keys().index(machid)
            self.machid.setCurrentIndex(idx)

            print idx

          self.inf("cmdline: %s"%line)
          self.inf("machine: %d"%machid)
          self.inf("magic: %x"%magic)
        else:
          self.inf("genblob not configured")

    def setInfo(self):
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

    def findDev(self):
        self.log.clear()

        try:
          self.dev = putusb.MotoUsb()
          self.inf("device found: %s"%self.dev.name())
        except:
          self.inf("no device")

    def sendBlob(self):
        self.dev.set(0xa1000000, putusb.encode_bytes(0x0D3ADCA7))
        self.dev.run_file("blob")

        while self.dev.dev.idProduct != 0xbeef:
          self.findDev()

    def flash(self):

        self.showInfo()

        self.inf("flash")

        fdialog = QtGui.QFileDialog()
        fdialog.exec_()

        path = str(fdialog.selectedFiles()[0])

        self.inf("going to flash %s"%path)

        self.dev.flash_index(path)

app = QtGui.QApplication(sys.argv)
w = Main()
w.show()
sys.exit(app.exec_())

