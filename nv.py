import putusb

dev = putusb.NvidiaUsb()
dev.boot("bin/tegra_pre_boot.bin", "bin/fastboot.stock.bin")
