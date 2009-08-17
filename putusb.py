import usb
import os
from time import sleep

moto = 0x22b8

names = {
    'gen-blob':(0x000a0800,131072),
    'kernel':(0x000e0000,2097152),
    'root':(0x002e0000,64094208),
}

machids = {
    0:"none",
    1743:"Motorola A1200",
    1744:"Motorola E2",
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
    mask = ((1<<8)-1) << n*8

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
      self.flash = self.flash_genblob
      self.flash_file = self.flash_file_genblob
      self.erase = self.erase_genblob
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

    resp = None
    while not resp:
      try:
        resp = self.recv()
      except usb.USBError as e:
        print e

        if 'No such device' in e.args[0]:
          print 'device dissappeared'
          return

        sleep(0.8)

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

    if len(data) < 4096:
      crap = '%'*(4096 - len(data))
      data += crap

    size = len(data)

    packet = chr(size>>8) + chr(size&0xf)
    packet += data
    packet += chr(lolsum(packet))

    resp = self.cmd('BIN',packet)

    if resp != '\x02ACK\x1eBIN\x03':
      print 'bin resp error', resp
      raise

    return True

  def set(self, addr, data):
    left = len(data)

    while left:
      chunk = min(left,4*1024)
      print hex(addr)
      self.addr(addr)
      self.bin(data[:chunk])

      addr += chunk
      data = data[chunk:]
      left -= chunk

  def fix_data_genblob(self, addr, data):
    if addr % 0x20000:
      prefix_len = addr % 0x20000
      prefix = self.get(addr-prefix_len,prefix_len)

      data = prefix + data
      addr = addr-prefix_len

    if len(data) % 0x20000:
      data += '%'*(0x20000 - (len(data) % 0x20000))

    return addr,data

  def flash_genblob(self, addr, data):

    addr,data = self.fix_data_genblob(addr,data)

    left = len(data)

    while left:
      chunk = min(left,0x80000)
      print 'flash %d to %x'%(chunk,addr)

      self.set(0xa0400000,data[:chunk])
      self.flash_cmd(0xa0400000,addr,chunk)

      addr += chunk
      data = data[chunk:]
      left -= chunk

  def flash_file_genblob(self, addr, path):
    file = open(path)

    while True:
      data = file.read(0x80000)

      if not len(data):
        print "all"
        break

      addr,data = self.fix_data_genblob(addr,data)

      chunk = len(data)

      print "flash %d to %x"%(chunk,addr)

      self.set(0xa0400000,data)
      self.flash_cmd(0xa0400000,addr,chunk)

      addr += chunk

      yield addr

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
      if not line or line[0] == '#':
        continue

      line = line[:-1]

      if '=' in line:
        name,addresses = line.split("=",1)
        addr,size = addresses.split(' ',1)
        addr = int(addr,16)
        size = int(size)

        names[name] = (addr,size)
        print names

        continue

      dest,path = line.split(' ',1)
      path = dir+path
      try:
        stat = os.stat(path)
      except:
        continue

      start,end = self.name2addr(dest,stat.st_size)

      print "going to flash %s as %s to 0x%x"%(path,dest,start)

      for current in self.flash_file(start,path):
        yield start,current,end,dest

      # erase
      #for current in self.erase(start+stat.st_size,end):
      #  yield start,current,end,dest


  def name2addr(self,name,size):
    if name not in names:
      raise IOError

    addr,size_max = names[name]

    if size <= size_max:
      return addr,size_max
    else:
      raise IOError

  def serial(self):
    sn = self.cmd("RQSN")

    if sn[:6] != '\x02RSSN\x1e':
      return "unknown"

    return sn[6:-1]

  def version(self):
    vn = self.cmd("RQVN")

    if vn[:6] != '\x02RSVN\x1e':
      raise IOError

    return vn[6:-1]

  def off(self):
    self.cmd("POWER_DOWN")

  def run_file(self,path):
    file = open(path)
    data = file.read()
    file.close()

    self.set(0xa0de0000, data)
    self.jump(0xa0de0000)

  def erase_genblob(self,addr,end):
    self.set(0xa0400000,'\xff'*0x80000)

    while addr < end:
      self.flash_cmd(0xa0400000,addr,0x80000)
      print "erased %x"%addr

      addr += 0x80000

      yield addr



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
