import putusb
import struct
import os
from time import sleep

dev = putusb.NvidiaUsb()

dev.recv() # gets uuid

dev.send_pre('bin/tegra_pre_boot.bin')

dev.send_cmd(1,0,0,1)

dev.recv()
dev.recv()
dev.recv()
dev.recv()

dev.send_cmd(4,0,)
dev.recv()
dev.send_cmd(4,1,)

dev.send_loader("bin/fastboot.stock.bin")

dev.recv()

dev.send_cmd(4,0)
dev.send_cmd(1, 0x11, 0, 0x18)

dev.recv()
dev.recv()

dev.send_cmd(4,1)
