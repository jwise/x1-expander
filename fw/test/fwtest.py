import usb
import sys
import struct
import time
import random
import colorsys

def is_expander_rp2040(dev):
    return dev.idVendor == 0x2E8A and dev.idProduct == 0x000A and dev.manufacturer == "X1Plus" and dev.product == "X1Plus Expander GPIO controller"
rp2040 = usb.core.find(custom_match = is_expander_rp2040)
rp2040.set_configuration()

intf = rp2040[0][(0,0)]
ep_out = intf[0]
ep_in  = intf[1]

PORTA1 = 4
PORTB1 = 10
PORTC1 = 16
PORTD1 = 22

ph = 0
while True:
    ph = ph + 0.01
    arr = []
    for i in range(8):
        arr += colorsys.hsv_to_rgb((ph + i * 0.05) % 1, 1.0, 1.0)
    buf = bytes([int(a * 0.1 * 255) for a in arr])
    buf = struct.pack('<HB', len(buf), PORTD1) + buf
    ep_out.write(buf)
    if ph > 1:
        ph -= 1
    time.sleep(0.03);

ep_out.write(b'\x03\x00\x04')
ep_out.write(bytes([random.randint(0, 32), random.randint(0, 32), random.randint(0, 32)]))
