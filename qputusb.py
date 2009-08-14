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
        info = QtGui.QPushButton("Show config")
        clr = QtGui.QPushButton("Clear")
        txt = QtGui.QTextEdit()

        self.connect( find, click, self.findDev )
        self.connect( info, click, self.showInfo )
        self.connect( clr, click, txt.clear )

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(find)
        hbox.addStretch(1)
        hbox.addWidget(info)
        hbox.addWidget(clr)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox)

        txt.setReadOnly(True)
        vbox.addWidget(txt)

        self.log = txt

        self.setLayout(vbox)

        self.resize(300, 150)

    def inf(self, text):
        self.log.append(text)

    def showInfo(self):
        vn = self.dev.cmd("RQVN")
        sn = self.dev.cmd("RQSN")
        self.inf("version: %s"%vn)
        self.inf("serial: %s"%sn)

        magic = self.dev.get(0x000c0000+131072-4,4)
        magic = putusb.decode_bytes(magic)



        if magic == 0xdeadb007:

          cfg = self.dev.get(0x000c0000,131072)
          self.inf("genblob configuration")

          line, machid, magic = putusb.decode_params(cfg)

          self.inf("cmdline: %s"%line)
          self.inf("machine: %d"%machid)
          self.inf("magic: %x"%magic)
        else:
          self.inf("genblob not configured")

    def findDev(self):
        try:
          self.dev = putusb.MotoUsb()
          self.inf("device found: %s"%self.dev.name())
        except:
          self.inf("no device")

app = QtGui.QApplication(sys.argv)
w = Main()
w.show()
sys.exit(app.exec_())

