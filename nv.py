import putusb

dev = putusb.NvidiaUsb()
#dev.boot("bin/tegra_pre_boot.bin", "bin/fastboot.stock.bin")
print putusb.Usb.recv(dev)

f = open('dump_0.bin')
dev.send(f.read())
f.close()

print dev.recv()

dev.send_pre('bin/dump_1.bin')

print dev.recv()

dev.cmd(1,1,4,4,0x0ff0)

print dev.recv()

state = putusb.LoadState('bin/dump_2.bin')
while state.size:
      map(dev.send, state.feed())
      dev.recv_ack()

print dev.recv()

dev.send_ack()

# send odm data
dev.cmd(1,3,4,6,0x300d8011)
dev.recv_ack()

print dev.recv()

dev.send_ack()

dev.send_loader('bin/dump_3.bin')



print 'LOADED'

part = 5
"""

size, off = dev.part_info(part=part)

f = open("crap2", 'wb')
f.truncate()
map(f.write, dev.read_part(part,size))
f.close()
"""

f = open("crap1", 'wb')
f.truncate()
map(f.write, dev.read_part(part) )
f.close()
