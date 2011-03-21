import putusb
import struct
import os
from time import sleep

class Dev(object):
  def recv(self):
    pass

  def send(self,data):
    if len(data) < 100:
      print data.encode('hex')
    else:
      print len(data)

  def send_hex(self,data):
    self.send(data.decode('hex'))

class Boot(object):
  def __init__(self, name):
    self.file = open(name, 'rb')
    self.size = os.stat(name).st_size



dev = Dev()

dev = putusb.NvidiaUsb()

dev.recv() # gets uuid

f = open('bin/tegra_pre_boot.bin','rb')

while True:
  chunk = f.read(4096)
  if not chunk:
    break
  print 'send', len(chunk)

  dev.send(chunk)

dev.recv()

dev.send_cmd(1,0,0,1)

dev.recv()
while True:
  try:
    dev.recv() # here can fail
    break
  except:
    print 'err'
    sleep(0.2)

dev.recv()
dev.recv()

dev.send_cmd(4,0,)
dev.recv()
dev.send_cmd(4,1,)

fastboot = Boot('bin/fastboot.stock.bin')

dev.send_pack(1, 1,1,0x10,5,fastboot.size, 0, 0x108000, 0x108000,0xfffffe22)
while True:
  try:
    dev.recv()
    break
  except:
    print 'err'

  sleep(0.1)

dev.recv()
dev.send_cmd(4,2)


def send_loader(f, num):
  chunk = min(0x10000,f.size)
  data = struct.pack('iiii', 1, 2, num, chunk)
  f.size-=chunk

  count = sum([ord(_x) for _x in data]) - 1

  dev.send(data)

  def send_sum():
    dev.send(struct.pack('I',  0xffffffff ^ count))

  for x in range(16):
    data = f.file.read(4096)

    if not data:
      send_sum()
      return False

    count += sum([ord(_x) for _x in data])

    dev.send(data)

  send_sum()

  while True:
    try:
      dev.recv()
      break
    except:
      print 'err'

  return True

_num = 2
while send_loader(fastboot, _num):
  _num+=1

dev.recv()

while True:
  try:
    dev.recv()
    break
  except:
    print 'err'
    sleep(0.3)

dev.send_cmd(4,0)
dev.send_cmd(1, 0x11, 0, 0x18)

dev.recv()
dev.recv()

dev.send_cmd(4,1)
