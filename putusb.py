import usb
import os
import sys
from time import sleep
import struct
from collections import namedtuple

names = {
    'gen-blob':(0x000a0800,131072),
    'kernel':(0x000e0000,2097152),
    'root':(0x002e0000,64094208),
}

machids = {
    0:"none",
    1743:"Motorola E6",
    1742:"Motorola A1200",
    1744:"Motorola E2",
}

def lolsum(data,limit=256):
  sum = 0

  for b in data:
    sum += ord(b)

    if sum >= limit:
      sum -= limit

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

def decode_bytes_be(long):
  ret = 0
  off = len(long)*8

  while long:
    off -= 8
    ret |= (ord(long[0]) << off)

    long = long[1:]

  return ret

def encode_bytes(bytes,len=4):
  ret = ''
  for n in xrange(len):
    mask = ((1<<8)-1) << n*8

    ret += chr((bytes&mask)>>n*8)

  return ret

def encode_bytes_be(bytes,len=4):
  ret = ''
  for n in xrange(len):
    n = len-n-1
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

class Usb(object):

  dev = None
  RTIMEOUT = 100
  WTIMEOUT = 100

  def find(self, vendor):
    for bus in usb.busses():
        for dev in bus.devices:
          if dev.idVendor == vendor:
            self.dev = dev
            break

        if self.dev:
          break
    else:
      raise IOError("no device found")

  def __init__(self, vendor=None):
    self.find(vendor or self.VENDOR)

    self.setup_ep()

    self.handle = self.dev.open()

    self.dump_s = False
    self.dump_r = False

  def send(self, data):
    #print (data,self.ep_out)
    self.handle.bulkWrite(self.ep_out, data, self.WTIMEOUT)

  def recv(self):
    bytes = self.handle.bulkRead(self.ep_in, 8192, self.RTIMEOUT)
    return reduce(lambda a,s: a+chr(s), bytes, '')


  def sr(self, cmd):
    self.send(cmd)

    resp = None
    while not resp:
      try:
        resp = self.recv()
      except usb.USBError:
        _t,e,_x = sys.exc_info()
        print e

        if 'No such device' in e.args[0]:
          print 'device dissappeared'
          return

        sleep(0.8)

    return resp



class MotoUsb(Usb):
  BIN_CHUNK = 4096
  GET_CNUNK = 4096

  VENDOR = 0x22b8

  def __init__(self,):
    super(MotoUsb, self).__init__(self)

    config = self.dev.configurations[0]
    self.handle.setConfiguration(1)

    iface = config.interfaces[0][0]
    self.handle.claimInterface(iface)

    if self.dev.idProduct == 0xbeef:
      self.read = self.read_genblob
      self.flash = self.flash_genblob
      self.flash_file = self.flash_file_genblob
      self.erase = self.erase_genblob
    elif self.dev.idProduct == 0x4903:
      self.read = self.read_lte2

  def setup_ep(self):
    if self.dev.idProduct in (0xbeef,0x6003,0x6021):
      self.ep_out = 2
      self.ep_in = 0x81
    else:
      self.ep_out = 1
      self.ep_in = 0x82

  def cmd(self, cmd, data = None):
    packet = '\x02'
    packet += cmd

    if data:
      packet += '\x1e'
      packet += data

    packet += '\x03'

    if self.dump_s:
      print 'send:\nHEX:\t%s\nSTR:\t%s'%(
          packet.encode('hex'),
          packet
      )

    ret =  self.sr(packet)

    if self.dump_r:
     print '--------\nrecvd:\nHEX:\t%s\nSTR:\t%s\n=======\n'%(
          ret.encode('hex'),
          ret
      )

    return ret

  def addr(self, addr, noerr=False):
    data = self.cmd('ADDR',addr_data(addr))

    if noerr:
      return

    if data[:5] != '\x02ACK\x1e':
      raise IOError('addr answer error')

    if int(data[10:18],16) != addr:
      raise IOError('addr value error')


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
    resp = self.cmd('READ', "%.8X,%.4X"%(off,size))

    data = resp[8:8+size]

    return data

  def read_ramldr1(self, off, size):
    if size != 256:
      raise IOError("incorrect size %x" % size)

    return self.cmd("DUMP", "%.8X" % off)

  def get(self, off, size):
    left = size
    data = ''

    while True:
      chunk = min(left,self.GET_CNUNK)

      data += self.read(off,chunk)

      print "down: %d%% left"%( float(left) / size * 100 )

      left -= chunk
      off += chunk

      if left <= 0:
        break

    return data

  def bin(self, data, noerr=False):

    if len(data) < self.BIN_CHUNK:
      crap = '%'*(self.BIN_CHUNK - len(data))
      data += crap

    size = len(data)

    packet = chr(size>>8) + chr(size&0xff)
    packet += data
    packet += chr(lolsum(packet))

    resp = self.cmd('BIN',packet)

    if not noerr and resp != '\x02ACK\x1eBIN\x03':
      print 'bin resp error', resp
      raise

    return True

  def set(self, addr, data, noerr=False):
    left = len(data)

    while left:
      chunk = min(left,self.BIN_CHUNK)
      print hex(addr)
      self.addr(addr, noerr)
      self.bin(data[:chunk], noerr)

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
    file = open(path,'rb')

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
      return addr,addr+size
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
    size = os.stat(path).st_size
    file = open(path,'rb')

    data = ''

    while len(data) < size:
      data += file.read()
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

  def read_ramldr2(self,addr,size):
    packet = 'R'
    packet += encode_bytes_be(addr,4)
    packet += encode_bytes_be(size,4)

    print (packet,)
    self.send(packet)

    data = ''
    while len(data) < size:
      chunk = self.recv()
      if not chunk:
        raise IOError("agggr")

      data += chunk

    return data

  def addr_ramldr2(self,addr):
    packet = 'F'
    packet += encode_bytes_be(addr,4)
    print(packet,)

    ret = self.sr(packet)
    print (ret,)

    return decode_bytes_be(ret)

  def flash_ramldr2(self,addr,data):

    ret = ''
    while len(data):
      chunk = self.addr_ramldr2(addr)
      print "flash %x to addr %x"%(chunk,addr)
      self.flash_send_ramldr2(data[:chunk])

      data = data[chunk:]
      addr += chunk

      while True:
        sleep(0.6)
        try:
          ret += self.recv()
          break
        except:
          pass

      sleep(2)


    return ret


  def flash_send_ramldr2(self,data):

    all = len(data)
    sent = 0
    while len(data):
      ret = self.sr(data[:1024])

      data = data[1024:]
      sent += 1024

      if ret != '_OK':
        print (ret,)
        print "sent %x of %x"%(sent,all)

class LoadState(object):

  CHUNK = 0x10000
  FLUSH = 16

  def __init__(self, filename,n=2):
    self.f = open(filename, 'rb')
    self.size = os.stat(filename).st_size
    self.chunknum = n


  def __delete__(self):
    self.f.close()


  def counted(self):
    return struct.pack('I',  0xffffffff ^ self.checksum)

  def count(self, data):

    self.checksum += sum([ord(_x) for _x in data])

    return data

  def feed(self):
    chunk = min(self.CHUNK, self.size)
    self.size -= chunk
    self.checksum = -1

    data = struct.pack("IIII", 1, 2, self.chunknum, chunk)
    self.chunknum += 1
    yield self.count(data)

    for x in range(self.FLUSH):
      data = self.f.read(4096)

      if not data:
        break

      self.count(data)
      yield data

    yield self.counted()


class NvidiaUsb(Usb):
  VENDOR = 0x0955
  RTIMEOUT = 500
  WTIMEOUT = 300

  _Part = namedtuple("Part", "num name typ start_sectors size_sectors sector")

  class Part(_Part):
    @property
    def start(self):
      return self.start_sectors * self.sector

    @property
    def size(self):
      return self.size_sectors * self.sector

  def __init__(self):
    self.recv_ack_num = 0
    self.send_ack_num = 0

    super(NvidiaUsb, self).__init__()

  def setup_ep(self):
    self.ep_out = 1
    self.ep_in = 0x81

  def boot(self, pre, loader):

    print 'uuid', self.recv().encode('hex')
    print 'sending pre-loader'
    self.send_pre(pre)

    #self.unk_1_0_0_1()

    # hmmmm... before commenting 1 0 0 1 first
    # ack was 0
    self.recv_ack_num = 1

    _WTIMEOUT = self.WTIMEOUT
    self.WTIMEOUT = 1000

    print 'sending loader'
    self.send_loader(loader)
    self.WTIMEOUT = _WTIMEOUT

    #self.unk_1_11_0_18()

    return True

  def recv(self):
    for x in xrange(20):
      try:
        ret = super(NvidiaUsb, self).recv()
        break
      except usb.USBError, e:
        print e
        sleep(0.2)
    else:
      raise e

    return ret

  def recv_unpack(self, fmt="I"):
    data = self.recv()

    size = struct.calcsize(fmt)
    nums = len(data)/size

    numbers = struct.unpack(fmt*nums,data)

    return numbers

  def recv_ack(self):
    numbers = self.recv_unpack()

    if numbers[0] != 1:
      print 'invalid cmd'

    if numbers[1] != 4:
      print 'not ack', numbers

    if numbers[2] != self.recv_ack_num:
      print 'invalid ack sequence got %r, want %d' % (numbers,
          self.recv_ack_num)
    else:
      self.recv_ack_num += 1

    # TODO: checksum

  def send_ack(self):
    self.send_cmd(4,self.send_ack_num)
    self.send_ack_num+=1

  def send_pack(self, *args, **kw):

    data = struct.pack('I'*len(args), *args)

    if kw.get('cs'):
      cs = 0xFFFFFFFF

      cs -= sum([ord(x) for x in data]) - 1

      data += struct.pack("I", cs)

    return self.send(data)

  def send_cmd(self, *args):
    args = (1,) + args

    return self.send_pack(cs=True, *args)

  def cmd(self, *args):
    self.send_cmd(*args)
    self.recv_ack()

  def send_pre(self, filename):
    f = open(filename, 'rb')

    while True:
      data = f.read(4096)

      if not data:
        break

      self.send(data)

    self.recv_unpack()

  def send_loader(self, filename):
    state = LoadState(filename)

    self.cmd(1,1,0x10,5, state.size,0, 0x108000,0x108000)
    print self.recv_unpack()
    self.send_ack()

    while state.size:
      map(self.send, state.feed())
      self.recv_ack()


    self.send_ack_num=0

    print self.recv_unpack()
    self.send_ack()

  # issued after sending loader
  def unk_1_11_0_18(self):
    self.cmd(1, 0x11, 0, 0x18)

    print self.recv_unpack()

    self.send_ack()


  # issued before sending loader
  def unk_1_0_0_1(self):
    self.cmd(1,0,0,1)

    print self.recv_unpack()
    print self.recv_unpack()
    print self.recv_unpack()

    self.send_ack()

    print self.recv_unpack()
    self.send_ack()


  def part_info(self, part):
    self.cmd(1,0,4,0xf,part) # 3 is for third part?

    acks = self.recv_unpack() # 1, 2, send ack, recv ack(?)

    print acks
    print 's', self.send_ack_num
    print 'r', self.send_ack_num

    self.send_ack_num = acks[2]
    #self.recv_ack_num = acks[3]+1

    print 'partition info'
    size, off = self.recv_unpack("L") # size and offset, two long ints

    print 'checksum'
    print self.recv_unpack() # one int (checksum?)

    self.send_ack()

    print self.recv_unpack()
    self.send_ack()

    return size,off


  def read_part(self, part, size=None):
    if size == None:
      size = self.part[part].size

    # actual read code
    self.send_cmd(1,1,0x14,0x11,part,0,0,size,0)

    print self.recv_unpack() # its ack?
    print self.recv_unpack() # wtf?

    while size:
      chunk_size = min(LoadState.CHUNK, size)
      while chunk_size:
        ret = self.recv()
        chunk_size -= len(ret)
        size -= len(ret)

        yield ret

      cs = self.recv()
      assert len(cs) == 4
      print cs.encode('hex')
      self.send_ack()
      print self.recv_unpack() # wtf?

    self.send_ack()

  def flash_part(self, part, filename):

    state = LoadState(filename, 1)

    self.recv_ack_num = 0
    self.cmd(1,0,0xc,0xe,part,state.size,0)

    # use with: magic here?
    _WTIMEOUT = self.WTIMEOUT
    self.WTIMEOUT = 1000

    while state.size:
      map(self.send, state.feed())
      self.recv_ack()

    self.WTIMEOUT = _WTIMEOUT

    print self.recv_unpack() # wtf?

    self.send_ack()

  def raw_parts(self):

    self.cmd(1,0,0,0x13)
    acks = self.recv_unpack() # wtf?
    self.send_ack_num = acks[2]
    print self.recv_unpack() # wtf?

    print self.recv_unpack() # wtf?

    self.send_ack()
    print self.recv_unpack() # wtf?
    ret = self.recv() # wtf?
    print self.recv_unpack() # wtf?

    self.send_ack()

    print self.recv_unpack() # wtf?
    self.send_ack()


    return ret

  def parts(self, force=False):
    if force and hasattr(self, "_raw_parts"):
      del self._raw_parts


    if not hasattr(self, "_raw_parts"):
      self._raw_parts = self.raw_parts()

    raw = self._raw_parts

    CHUNK = 32
    off = 0
    fmt = "I4sIIIIxx"

    ret = []

    while (len(raw) - off) >= CHUNK:
      ret.append(self.Part._make(
          struct.unpack_from(fmt, raw, offset=off)
        )
      )
      off += CHUNK

    return ret

  @property
  def part(self):
    return dict(
        [ (p.num, p) for p in self.parts()]
    )


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
