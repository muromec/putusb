import putusb
import struct
import os

crap = '04040000a5e119fb4b1f96a46f0d37cae721f42300000000000000000000000000000000060000000404000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000080'
crap = crap.decode('hex')

crap = crap + '\x00'*(1028-len(crap))

class Dev(object):
  def recv(self):
    pass

  def send(self,data):
    if len(data) < 100:
      print data.encode('hex')
    pass

  def send_hex(self,data):
    pass

dev = Dev()

dev = putusb.NvidiaUsb()

dev.recv()
dev.send(crap)
dev.recv()

f = open('pre_boot.bin','rb')

while True:
  chunk = f.read(4096)
  if not chunk:
    break
  print 'send', len(chunk)

  dev.send(chunk)

dev.recv()

dev.send_hex('0100000001000000000000000000000001000000fdffffff')

dev.recv()
dev.recv()
dev.recv()
dev.recv()

dev.send_hex('010000000400000000000000fbffffff')
dev.recv()
dev.send_hex('010000000400000001000000faffffff')
dev.send_hex('010000000100000001000000100000000500000050480e0000000000008010000080100022feffff')
dev.recv()
dev.send_hex('010000000400000002000000f9ffffff')


def send_loader(f, num):
  chunk = min(0x10000,f.size)
  data = struct.pack('iiii', 1, 2, num, chunk)
  f.size-=chunk

  count = sum([ord(_x) for _x in data]) - 1

  def send_sum():
    dev.send(struct.pack('I',  0xffffffff ^ count))

  for x in range(16):
    data = f.file.read(4096)

    if not data:
      send_sum()
      return False

    count += sum([ord(_x) for _x in data])

  send_sum()

  dev.recv()

  return True

class Boot(object):
  def __init__(self, name):
    self.file = open(name, 'rb')
    self.size = os.stat(name).st_size

fastboot = Boot('fastboot.stock.bin')

_num = 2
while send_loader(fastboot, _num):
  _num+=1

