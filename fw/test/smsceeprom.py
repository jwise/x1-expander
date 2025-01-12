import os
def find_library(lib):
    p = f"/usr/lib/{lib}.so"
    if os.path.exists(p):
        return p
import usb.backend.libusb1
usb.backend.libusb1.get_backend(find_library=find_library)

import sys
import usb
import struct
import time

smsc = usb.core.find(idVendor = 0x0424, idProduct = 0xEC00)
#smsc.set_configuration()

USB_DIR_OUT = 0
USB_DIR_IN = 0x80
USB_TYPE_VENDOR = 0x2 << 5
USB_RECIP_DEVICE = 0

USB_VENDOR_REQUEST_WRITE_REGISTER = 0xA0
USB_VENDOR_REQUEST_READ_REGISTER = 0xA1

ID_REV = 0x0
LED_GPIO_CFG = 0x24
GPIO_CFG = 0x28

E2P_CMD = 0x30
E2P_CMD_BUSY = 0x80000000
E2P_CMD_READ = 0x00000000
E2P_CMD_EWDS = 0x10000000
E2P_CMD_EWEN = 0x20000000
E2P_CMD_WRITE = 0x30000000
E2P_CMD_WRAL = 0x40000000
E2P_CMD_ERASE = 0x50000000
E2P_CMD_ERAL = 0x60000000
E2P_CMD_RELOAD = 0x70000000
E2P_CMD_TIMEOUT = 0x400
E2P_CMD_LOADED = 0x200
# E2P_CMD_ADDR is LSBs

E2P_DATA = 0x34

def smscread(addr):
    b = smsc.ctrl_transfer(USB_DIR_IN | USB_TYPE_VENDOR | USB_RECIP_DEVICE, USB_VENDOR_REQUEST_READ_REGISTER, 0, addr, 4)
    return struct.unpack("<L", b)[0]

def smscwrite(addr, data):
    len = smsc.ctrl_transfer(USB_DIR_OUT | USB_TYPE_VENDOR | USB_RECIP_DEVICE, USB_VENDOR_REQUEST_WRITE_REGISTER, 0, addr, struct.pack("<L", data))
    assert len == 4

print(f"ID_REV:       {smscread(ID_REV):08x}")

def smsceepromwait(allow_timeout = True):
    for i in range(1000):
        rv = smscread(E2P_CMD)
        if (rv & E2P_CMD_TIMEOUT) and not allow_timeout:
            raise TimeoutError("EEPROM timeout detected by LAN9514")
        if (rv & E2P_CMD_BUSY) == 0:
            return
        time.sleep(0.001)
    raise TimeoutError("EEPROM wait timed out implicitly")

def smsceepromread(addr):
    smsceepromwait()
    smscwrite(E2P_CMD, E2P_CMD_BUSY | E2P_CMD_READ | addr)
    smsceepromwait(allow_timeout = False)
    return smscread(E2P_DATA) & 0xFF

def smsceepromwrite(addr, data):
    smsceepromwait()
    smscwrite(E2P_CMD, E2P_CMD_BUSY | E2P_CMD_EWEN)
    smsceepromwait(allow_timeout = False)
    smscwrite(E2P_DATA, data)
    smscwrite(E2P_CMD, E2P_CMD_BUSY | E2P_CMD_WRITE | addr)
    smsceepromwait(allow_timeout = False)

print("reading EEPROM...")
buf = b""
for ad in range(512):
    buf += bytes([smsceepromread(ad)])

print(buf)

print("writing EEPROM...")
with open(sys.argv[1], "rb") as f:
    buf = f.read()
for ad,da in enumerate(buf):
    smsceepromwrite(ad, da)

print("done")