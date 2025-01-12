import os
def find_library(lib):
    p = f"/usr/lib/{lib}.so"
    if os.path.exists(p):
        return p
import usb.backend.libusb1
usb.backend.libusb1.get_backend(find_library=find_library)

import usb
import sys
import struct
import time
import random
import colorsys
import math
import argparse
from collections import namedtuple

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

def _pca9536(led_pass = False, led_fail = False, load_5v = False, load_3v3 = False):
    addr = 0x41

    outputs = 0
    if led_pass:
        outputs |= 0x04
    if led_fail:
        outputs |= 0x08
    if load_5v:
        outputs |= 0x01
    if load_3v3:
        outputs |= 0x02

    ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
    ep_out.write(struct.pack('<BBBBB', 2, addr, 0x02, 0x01, outputs)) # set outputs to LED_PASS
    ep_out.write(struct.pack('<BBBBB', 2, addr, 0x02, 0x03, 0x00)) # set pins as outputs
    ep_out.write(struct.pack('<B', 0))
    buf = b""
    while len(buf) < 2:
        buf += ep_in.read(0x100)
    
    if buf != b'\x00\x00':
        raise RuntimeError("comm error with pca9536")

INA219_24V = 0x40
INA219_3V3 = 0x42
INA219_5V  = 0x43

Ina219Result = namedtuple("Ina219Result", ["vbus", "vshunt", "ishunt", "vbus_raw", "vshunt_raw"])

def _ina219(addr):
    ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
    ep_out.write(struct.pack('<BBBBBB', 2, addr, 0x03, 0x00, 0x31, 0x9F)) # set PGA = 160 mV (PGA = /4)
    ep_out.write(struct.pack('<B', 0))
    buf = b""
    while len(buf) < 1:
        buf += ep_in.read(0x100)
    if buf != b'\x00':
        raise RuntimeError("comm error setting INA219 config")

    ep_out.write(struct.pack('<BBB', 4, PORTS['D'][0], PORTS['D'][1]))
    ep_out.write(struct.pack('<BBB', 1, addr, 0x02))
    ep_out.write(struct.pack('<B', 0))
    buf = b""
    while len(buf) < 3:
        buf += ep_in.read(0x100)
    if buf[0] != 0:
        raise RuntimeError("comm error getting INA219 config")

    rv,cfg = struct.unpack(">BH", buf)
    assert cfg == 0x319F
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
    assert rv0 == 0
    assert rv1 == 0
    assert rv2 == 0
    assert rv3 == 0
    
    vbus_f = float(vbus >> 4 | (vbus & 1) << 12) * 0.004 # no idea why the latter is needed or why it's >> 4 instead of >> 3
    vshunt_f = float(vshunt) * 1e-5 / 2.0 # also why *2??
    ishunt_f = vshunt_f * 0.5 / 0.04
    
    return Ina219Result(vbus = vbus_f, vshunt = vshunt_f, ishunt = ishunt_f, vbus_raw = vbus, vshunt_raw = vshunt)

@mkcmd
def i2c_ina219(args):
    for addr in [0x40, 0x42, 0x43]:
        print(f"trying INA219 at {addr:02x}")
        result = _ina219(addr)
        print(f"{result.vbus:.3f} V @ {result.ishunt * 1000:.1f} mA")
        
@mkcmd
def i2c_pca9536(args):
    _pca9536(led_pass = True)
    print("PASS light is on")
    time.sleep(1)
    _pca9536()
    print("PASS light is off")

@mkcmd
def i2c_pca9536_load5(args):
    _pca9536(load_5v = True)

@mkcmd
def i2c_pca9536_load3v3(args):
    _pca9536(load_3v3 = True)

@mkcmd
def boardtest(args):
    _pca9536()
    try:
        print("checking quiescent current...")
        iq_24v = _ina219(INA219_24V)
        iq_5v = _ina219(INA219_5V)
        iq_3v3 = _ina219(INA219_3V3)
        
        assert 23.8 < iq_24v.vbus < 24.2
        assert 3.2 < iq_3v3.vbus < 3.4
        assert 4.9 < iq_5v.vbus < 5.1
        print(f"  quiescent voltages OK ({iq_24v.vbus:.2f}V, {iq_3v3.vbus:.2f}V, {iq_5v.vbus:.2f}V)")
        
        assert iq_24v.ishunt < 0.055
        assert iq_3v3.ishunt < 0.002
        assert iq_5v.ishunt < 0.002
        print(f"  quiescent current OK ({iq_24v.ishunt*1000:.2f}mA, {iq_3v3.ishunt*1000:.2f}mA, {iq_5v.ishunt*1000:.2f}mA)")
        
        # try 5V load
        print("checking 5V load efficiency...")
        _pca9536(load_5v = True)
        i5v_24v = _ina219(INA219_24V)
        i5v_5v = _ina219(INA219_5V)
        i5v_3v3 = _ina219(INA219_3V3)
        _pca9536()

        assert 23.8 < i5v_24v.vbus < 24.2
        assert 0.45 < i5v_5v.ishunt < 0.55, i5v_5v.ishunt
        assert 3.2 < i5v_3v3.vbus < 3.4
        
        dv = iq_5v.vbus - i5v_5v.vbus
        di_5v = i5v_5v.ishunt - iq_5v.ishunt
        esr = dv/di_5v
        print(f"  ESR = {esr:.3f} ohms at {i5v_5v.ishunt:.3f}A ({i5v_5v.vbus:.3f}V)")
        assert esr < 0.4
        
        dp_5v = iq_5v.vbus * di_5v
        dp_24v = i5v_24v.vbus * i5v_24v.ishunt - iq_24v.vbus * iq_24v.ishunt
        efficiency_5v = dp_5v / dp_24v
        print(f"  input dP {dp_24v:.3f}W, output dP {dp_5v:.3f}W, efficiency {efficiency_5v*100:.1f}%")
        assert efficiency_5v > .88
        # we assume the ESR is in the pins, not the reg

        print("checking 3v3 load efficiency...")
        _pca9536(load_3v3 = True)
        i3v3_24v = _ina219(INA219_24V)
        i3v3_5v = _ina219(INA219_5V)
        i3v3_3v3 = _ina219(INA219_3V3)
        _pca9536()

        assert 23.8 < i3v3_24v.vbus < 24.2
        assert 0.9 < i3v3_3v3.ishunt < 1.1
        assert 4.9 < i3v3_5v.vbus < 5.1
        
        dv = iq_3v3.vbus - i3v3_3v3.vbus
        di_3v3 = i3v3_3v3.ishunt - iq_3v3.ishunt
        esr = dv/di_3v3
        print(f"  ESR = {esr:.3f} ohms at {i3v3_3v3.ishunt:.3f}A ({i3v3_3v3.vbus:.3f}V)")
        assert esr < 0.4
        
        dp_3v3 = iq_3v3.vbus * di_3v3
        dp_24v = i3v3_24v.vbus * i3v3_24v.ishunt - iq_24v.vbus * iq_24v.ishunt
        efficiency_3v3 = dp_3v3 / dp_24v
        print(f"  input dP {dp_24v:.3f}W, output dP {dp_3v3:.3f}W, 24v -> 3v3 efficiency {efficiency_3v3*100:.1f}%, 5v -> 3v3 efficiency {efficiency_3v3/efficiency_5v*100:.1f}%")
        assert (efficiency_3v3/efficiency_5v) > .88

        print("regulator test PASS")
        _pca9536(led_pass = True)
        
    except AssertionError as e:
        _pca9536(led_fail = True)
        raise

args = parser.parse_args()
port = PORTS[args.port[0]]
args.func(args)
