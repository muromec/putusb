import putusb

dev = putusb.NvidiaUsb()
dev.boot("bin/tegra_pre_boot.bin", "bin/fastboot.stock.bin")

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
