import usb
import os
from time import sleep

moto = 0x22b8

names = {
    'kernel':(0x000e0000,2097152),
    'root':(0x002e0000,64094208),
}

def lolsum(data):
  sum = 0

  for b in data:
    sum += ord(b)

    if sum >= 256:
      sum -= 256

  return sum

def add_sum(data):
  return data + "%.2X"%lolsum(data)

def addr_data(addr):
  addr = "%.8X"%addr
  addr += "%.2X"%lolsum(addr)
  return addr

def decode_bytes(long):
  ret = 0
  off = 0

  while long:
    ret |= (ord(long[0]) << off)

    off+=8
    long = long[1:]

  return ret

def encode_bytes(bytes,len=4):
  ret = ''
  for n in xrange(len):
    mask = ((1<<8)-1) << n*4

    ret += chr((bytes&mask)>>n*8)

  return ret

def encode_params(cmdline, machid):
  all = 0x20000

  data = cmdline
  data += '\x00'*(all-8-len(cmdline))
  data += encode_bytes(machid)
  data += '\x07\xb0\xad\xde' # blob magic

  return data

def decode_params(data):
  cmdline = data[:data.find('\x00')]
  machid = decode_bytes(data[-8:-4])
  magic = decode_bytes(data[-4:])


  return cmdline,machid,magic

class MotoUsb:
  def __init__(self):
    for bus in usb.busses():
        for dev in bus.devices:
          if dev.idVendor == moto:
            self.dev = dev
            break

    self.handle = self.dev.open()

    if self.dev.idProduct in (0xbeef,0x6003,0x6021):
      self.ep_out = 2
      self.ep_in = 1
    else:
      self.ep_out = 1
      self.ep_in = 2

    if self.dev.idProduct == 0xbeef:
      self.read = self.read_genblob
    elif self.dev.idProduct == 0x4903:
      self.read = self.read_lte2

    self.dump_s = False
    self.dump_r = False


  def send(self, data):
    #print (data,self.ep_out)
    self.handle.bulkWrite(self.ep_out, data)

  def recv(self):
    bytes = self.handle.bulkRead(self.ep_in, 8192)
    return reduce(lambda a,s: a+chr(s), bytes, '')


  def sr(self, cmd):
    self.send(cmd)
    sleep(0.1)

    resp = None
    while not resp:
      try:
        resp = self.recv()
      except usb.USBError as e:

        if 'No such device' in e.args[0]:
          print 'device dissappeared'
          return

        sleep(0.1)

    return resp

  def cmd(self, cmd, data = None):
    packet = '\x02'
    packet += cmd

    if data:
      packet += '\x1e'
      packet += data

    packet += '\x03'

    if self.dump_s:
      print (packet,)

    ret =  self.sr(packet)

    if self.dump_r:
      print (ret,)

    return ret

  def addr(self, addr):
    data = self.cmd('ADDR',addr_data(addr))

    if data[:5] != '\x02ACK\x1e':
      print 'addr answer error'
      raise

    if int(data[10:18],16) != addr:
      print 'addr value error'
      raise

    return True



  def jump(self, addr):
    return self.cmd('JUMP',addr_data(addr))

  def read_genblob(self, off, size):
    resp = self.cmd('RBIN', add_sum("%.8X%.4X"%(off,size)))

    head = resp[:6]

    if head != '\x02RBIN\x1e':
      print 'response error'
      raise

    data = resp[6:-2]
    check = ord(resp[-2])

    if len(data) != size:
      print 'len mismatch'
      raise

    
    return data

  def read_lte2(self, off, size):
    resp = self.cmd('READ', add_sum("%.8X,%.4X"%(off,size)))

    data = resp[8:8+size]

    return data

  def get(self, off, size):
    left = size
    data = ''

    while True:
      chunk = min(left,1024*4)

      data += self.read(off,chunk)

      print "down: %d%% left"%( float(left) / size * 100 )

      left -= chunk
      off += chunk

      if left <= 0:
        break

    return data

  def bin(self, data):
    if self.dev.idProduct == 0x6023 and len(data) < 4096:
      print 'gen2 sucks'
      crap = '%'*(4096 - len(data))
      data += crap

    if len(data) % 8:
      print 'unaligned data'
      crap = '&'*(8 - len(data) % 8)
      data += crap

    size = len(data)

    packet = chr(size>>8) + chr(size&0xf)
    packet += data
    packet += chr(lolsum(packet))

    resp = self.cmd('BIN',packet)

    if resp != '\x02ACK\x1eBIN\x03':
      print 'bin resp error'
      raise

    return True

  def set(self, addr, data):
    left = len(data)

    while left:
      chunk = min(left,4*1024)
      self.addr(addr)
      self.bin(data[:chunk])

      addr += chunk
      data = data[chunk:]
      left -= chunk

  def flash(self, addr, data):
    if len(data) % 0x20000:
      crap = '%'*(0x20000 - (len(data) % 0x20000))
      data += crap

    left = len(data)

    while left:
      chunk = min(left,0x80000)
      print 'flash %d to %x'%(chunk,addr)

      self.set(0xa0400000,data[:chunk])
      self.flash_cmd(0xa0400000,addr,chunk)

      addr += chunk
      data = data[chunk:]
      left -= chunk

  def flash_file(self, addr, path):
    file = open(path)

    while True:
      data = file.read(0x80000)

      if not len(data):
        print "all"
        break

      if len(data) % 0x20000:
        crap = '%'*(0x20000 - (len(data) % 0x20000))
        data += crap

      chunk = len(data)

      print "flash %d to %x"%(chunk,addr)

      self.set(0xa0400000,data)
      self.flash_cmd(0xa0400000,addr,chunk)

      addr += chunk

    file.close()




  def flash_cmd(self, source, dest, size):
    packet = "%.8X%.8X%.8X"%(source, dest, size)
    packet += "%.2X"%(lolsum(packet))

    resp = self.cmd("FLASH", packet)

  def name(self):
    pid = self.dev.idProduct
    if pid == 0xbeef:
      name = "Gen Blob"

    elif pid == 0x6023:
      name = "Gen2"
    else:
      name = "Unknown"

    name += " (0x%x)"
    return name%self.dev.idProduct


  def flash_index(self,index):

    dir = index[:index.rindex("/")+1]

    file = open(index)
    contents = file.readlines()
    file.close()

    for line in  contents:
      if line[0] == '#':
        continue

      line = line[:-2]

      dest,path = line.split(' ',1)
      path = dir+path
      try:
        stat = os.stat(path)
      except:
        continue

      addr = self.name2addr(dest,stat.st_size)

      print "going to flash %s as %s to 0x%x"%(path,dest,addr)

      self.flash_file(addr,path)

  def name2addr(self,name,size):
    if name not in names:
      raise IOError

    addr,size_max = names[name]

    if size <= size_max:
      return addr
    else:
      raise IOError


if __name__ == '__main__':
  dev = MotoUsb()

  import sys

  if len(sys.argv) == 2:
    cmd = sys.argv[1]
    data = None

  elif len(sys.argv) == 3:
    cmd = sys.argv[1]
    data = sys.argv[2]

  else:
    cmd = 'RQVN'
    data = None

  print dev.cmd(cmd, data)
