import os
def find_library(lib):
    p = f"/usr/lib/{lib}.so"
    if os.path.exists(p):
        return p
import usb.backend.libusb1
usb.backend.libusb1.get_backend(find_library=find_library)

import usb
import struct
import time

smsc = usb.core.find(idVendor = 0x0424, idProduct = 0xEC00)
smsc.set_configuration()

USB_DIR_OUT = 0
USB_DIR_IN = 0x80
USB_TYPE_VENDOR = 0x2 << 5
USB_RECIP_DEVICE = 0

USB_VENDOR_REQUEST_WRITE_REGISTER = 0xA0
USB_VENDOR_REQUEST_READ_REGISTER = 0xA1

ID_REV = 0x0
LED_GPIO_CFG = 0x24
GPIO_CFG = 0x28

def smscread(addr):
    b = smsc.ctrl_transfer(USB_DIR_IN | USB_TYPE_VENDOR | USB_RECIP_DEVICE, USB_VENDOR_REQUEST_READ_REGISTER, 0, addr, 4)
    return struct.unpack("<L", b)[0]

def smscwrite(addr, data):
    len = smsc.ctrl_transfer(USB_DIR_OUT | USB_TYPE_VENDOR | USB_RECIP_DEVICE, USB_VENDOR_REQUEST_WRITE_REGISTER, 0, addr, struct.pack("<L", data))
    assert len == 4

print(f"ID_REV:       {smscread(ID_REV):08x}")
print(f"LED_GPIO_CFG: {smscread(LED_GPIO_CFG):08x}")
print(f"GPIO_CFG:     {smscread(GPIO_CFG):08x}")

smscwrite(GPIO_CFG, (smscread(GPIO_CFG) & ~((1 << 28))) | (1 << 20) | (1 << 12) | (1 << 4))
print(f"GPIO_CFG:     {smscread(GPIO_CFG):08x}")
time.sleep(0.1)
smscwrite(GPIO_CFG, (smscread(GPIO_CFG) & ~((1 << 28) | (1 << 4))) | (1 << 20) | (1 << 12))
print(f"GPIO_CFG:     {smscread(GPIO_CFG):08x}")
time.sleep(0.1)
smscwrite(GPIO_CFG, (smscread(GPIO_CFG) & ~((1 << 28))) | (1 << 20) | (1 << 12) | (1 << 4))
print(f"GPIO_CFG:     {smscread(GPIO_CFG):08x}")
time.sleep(0.1)
