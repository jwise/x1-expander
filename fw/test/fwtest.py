import usb
import sys
import struct
import time
import random
import colorsys
import math
import argparse

def is_expander_rp2040(dev):
    return dev.idVendor == 0x2E8A and dev.idProduct == 0x000A and dev.manufacturer == "X1Plus" and dev.product == "X1Plus Expander GPIO controller"
rp2040 = usb.core.find(custom_match = is_expander_rp2040)
rp2040.set_configuration()

intf = rp2040[0][(0,0)]
ep_out = intf[0]
ep_in  = intf[1]

PORTS = {
    'A': { 0:  5, 1:  4, 2:  4, 3:  2, 4: 29, 5: 35, 6:  1, 7:  0 },
    'B': { 0: 11, 1: 10, 2:  9, 3:  8, 4: 28, 5: 36, 6:  7, 7:  6 },
    'C': { 0: 17, 1: 16, 2: 15, 3: 14, 4: 27, 5: 34, 6: 13, 7: 12 },
    'D': { 0: 23, 1: 22, 2: 21, 3: 20, 4: 26, 5: 37, 6: 19, 7: 18 },
}

port = PORTS['D']

def write_leds(pin, buf):
    hdr = struct.pack('<BHB', 1, len(buf), pin)
    ep_out.write(hdr + buf)

def gpio(pin, value = None, pull_up = False, pull_down = False):
    cfg = 0
    if pull_up:
        cfg |= 1
    if pull_down:
        cfg |= 2
    if value is not None:
        cfg |= 4
        if value:
            cfg |= 8
    ep_out.write(struct.pack('<BBB', 2, pin, cfg))

def gpio_get(pin):
    ep_out.write(struct.pack('<BB', 3, pin))
    rv = ep_in.read(1)
    return rv[0]

parser = argparse.ArgumentParser()
parser.add_argument('--port', action="store", nargs = 1, default=["D"])

subparsers = parser.add_subparsers(title = 'commands', required = True)

def mkcmd(func):
    subparsers.add_parser(func.__name__).set_defaults(func=func)

@mkcmd
def beep(args):
    gpio(port[3], True)
    gpio_get(port[3])
    time.sleep(0.2)
    gpio(port[3], False)
    gpio_get(port[3])

@mkcmd
def shutter_cama(args):
    gpio(port[3], True)
    gpio_get(port[3])
    time.sleep(0.2)
    gpio(port[3], False)
    gpio_get(port[3])

@mkcmd
def shutter_camb(args):
    gpio(port[5], True)
    gpio_get(port[5])
    time.sleep(0.2)
    gpio(port[5], False)
    gpio_get(port[5])


@mkcmd
def buttons(args):
    gpio(port[5], True)
    gpio(port[6], pull_up = True)
    gpio(port[7], pull_up = True)
    while True:
        print(gpio_get(port[6]), gpio_get(port[7]))
        time.sleep(0.2)

@mkcmd
def rainbow(args):
    ph = 0
    while True:
        ph = ph + 0.01
        arr = []
        for i in range(25):
            x = i % 5
            y = i // 5
            arr += colorsys.hsv_to_rgb((ph + math.sqrt(x ** 2 + y ** 2) * 0.05) % 1, 1.0, 1.0)
        buf = bytes([int(a * 0.1 * 255) for a in arr])
        write_leds(port[1], buf)
        if ph > 1:
            ph -= 1
        time.sleep(0.03)

@mkcmd
def i2c_eeprom(args):
    gpio(port[5], False)
    ep_out.write(struct.pack('<BBB', 4, port[7], port[6]))
    for addr in range(0x80):
        ep_out.write(struct.pack('<BBB', 1, addr, 0))
    ep_out.write(struct.pack('<B', 0))
    
    buf = b""
    while len(buf) < 0x80:
        buf += ep_in.read(0x80)
    for addr in range(0x80):
        if buf[addr] == 0:
            print(f"I2C device at {addr:02x}")

    ep_out.write(struct.pack('<BBB', 4, port[7], port[6]))
    ep_out.write(struct.pack('<BBBB', 2, 0x50, 0x01, 0x00))
    ep_out.write(struct.pack('<B', 0))
    buf = b""
    while len(buf) < 1:
        buf += ep_in.read(0x100)
    print(f"set addr buf {buf}")
    # eeprom is slow, so this must be done in two transactions

    ep_out.write(struct.pack('<BBB', 4, port[7], port[6]))
    ep_out.write(struct.pack('<BBB', 1, 0x50, 0x80))
    ep_out.write(struct.pack('<B', 0))
    buf = b""
    while len(buf) < 0x81:
        buf += ep_in.read(0x100)
    print(f"eeprom buf {buf} {len(buf)}")
    
@mkcmd
def i2c_stemma(args):
    ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
    for addr in range(0x80):
        ep_out.write(struct.pack('<BBB', 1, addr, 0))
    ep_out.write(struct.pack('<B', 0))
    
    buf = b""
    while len(buf) < 0x80:
        buf += ep_in.read(0x80)
    for addr in range(0x80):
        if buf[addr] == 0:
            print(f"I2C device at {addr:02x}")

@mkcmd
def i2c_ina219(args):
    for addr in [0x40, 0x42, 0x43]:
        print(f"trying INA219 at {addr:02x}")
        ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
        ep_out.write(struct.pack('<BBBBBB', 2, addr, 0x03, 0x00, 0x31, 0x9F)) # set PGA = 160 mV (PGA = /4)
        ep_out.write(struct.pack('<B', 0))
        buf = b""
        while len(buf) < 1:
            buf += ep_in.read(0x100)
        # print(buf)

        ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
        ep_out.write(struct.pack('<BBB', 1, addr, 0x02))
        ep_out.write(struct.pack('<B', 0))
        buf = b""
        while len(buf) < 2:
            buf += ep_in.read(0x100)
        # print(buf)
        rv,cfg = struct.unpack(">BH", buf)
        print(f"config {cfg:04x}")
        time.sleep(0.2)
        
        ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
        ep_out.write(struct.pack('<BBBB', 2, addr, 0x01, 0x01))
        ep_out.write(struct.pack('<BBB', 1, addr, 0x03))
        ep_out.write(struct.pack('<B', 0))
        ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
        ep_out.write(struct.pack('<BBBB', 2, addr, 0x01, 0x02))
        ep_out.write(struct.pack('<BBB', 1, addr, 0x03))
        ep_out.write(struct.pack('<B', 0))
        buf = b""
        while len(buf) < 10:
            buf += ep_in.read(0x100)
        # print(buf)
        rv0, rv1, vshunt, vs1, rv2, rv3, vbus, vb1 = struct.unpack('<BBHBBBHB', buf)
        vbus_f = float(vbus >> 4 | (vbus & 1) << 12) * 0.004 # no idea why the latter is needed or why it's >> 4 instead of >> 3
        vshunt_f = float(vshunt) * 1e-5 / 2.0 # also why *2??
        ishunt_f = vshunt_f * 0.5 / 0.04
        print(f"vshunt {vshunt:04x} = {vshunt_f * 1000:.1f} mV = {ishunt_f * 1000:.1f} mA, vbus {vbus:04x} = {vbus_f:.3f} V ")
        
        
        
@mkcmd
def i2c_pca9536(args):
    addr = 0x41

    ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
    ep_out.write(struct.pack('<BBBBB', 2, addr, 0x02, 0x01, 0x04)) # set outputs to LED_PASS
    ep_out.write(struct.pack('<BBBBB', 2, addr, 0x02, 0x03, 0x00)) # set pins as outputs
    ep_out.write(struct.pack('<B', 0))
    buf = b""
    while len(buf) < 2:
        buf += ep_in.read(0x100)
    print(buf)
    
    time.sleep(1)

    ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
    ep_out.write(struct.pack('<BBBBB', 2, addr, 0x02, 0x01, 0x00)) # set outputs to off
    ep_out.write(struct.pack('<BBBBB', 2, addr, 0x02, 0x03, 0x00)) # set pins as outputs
    ep_out.write(struct.pack('<B', 0))
    buf = b""
    while len(buf) < 2:
        buf += ep_in.read(0x100)
    print(buf)

@mkcmd
def i2c_pca9536_load5(args):
    addr = 0x41

    ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
    ep_out.write(struct.pack('<BBBBB', 2, addr, 0x02, 0x01, 0x01)) # set outputs to load_5v
    ep_out.write(struct.pack('<BBBBB', 2, addr, 0x02, 0x03, 0x00)) # set pins as outputs
    ep_out.write(struct.pack('<B', 0))
    buf = b""
    while len(buf) < 2:
        buf += ep_in.read(0x100)
    print(buf)

@mkcmd
def i2c_pca9536_load3v3(args):
    addr = 0x41

    ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
    ep_out.write(struct.pack('<BBBBB', 2, addr, 0x02, 0x01, 0x02)) # set outputs to load_3v3
    ep_out.write(struct.pack('<BBBBB', 2, addr, 0x02, 0x03, 0x00)) # set pins as outputs
    ep_out.write(struct.pack('<B', 0))
    buf = b""
    while len(buf) < 2:
        buf += ep_in.read(0x100)
    print(buf)

    
    

args = parser.parse_args()
port = PORTS[args.port[0]]
args.func(args)
