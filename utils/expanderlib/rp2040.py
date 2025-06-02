import usb
import sys
import struct
import time
from collections import namedtuple
import binascii

from elftools.elf.elffile import ELFFile

RP2040_MAGIC = 0x431FD10B

INA219_24V = 0x40
INA219_3V3 = 0x42
INA219_5V  = 0x43

Ina219Result = namedtuple("Ina219Result", ["vbus", "vshunt", "ishunt", "vbus_raw", "vshunt_raw"])

class Rp2040Boot:
    def __init__(self):
        def is_boot_rp2040(dev):
            return dev.idVendor == 0x2E8A and dev.idProduct == 0x0003 and dev.product == "RP2 Boot"
        self.rp2040 = usb.core.find(custom_match = is_boot_rp2040)
        if not self.rp2040:
            raise IOError("no RP2040 bootloader found")
        self.rp2040.set_configuration()
        self.intf = self.rp2040[0][(1, 0)] # XXX: this is not applicable if the MSC interface is not present
        self.intf.set_altsetting()
        self.ep_out = self.intf[0]
        self.ep_in  = self.intf[1]
        self.ep_out.clear_halt()
        self.ep_in.clear_halt()
    
    def send_cmd(self, cmdid, args = b"", data = b"", shouldreturn = True):
        cmd = struct.pack("<LLBBHL16s", RP2040_MAGIC, 31337, cmdid, len(args), 0, len(data), args)
        assert len(cmd) == 32
        self.ep_out.write(cmd)
        if len(data) > 0:
            self.ep_out.write(data)
        rv = None
        try:
            rv = self.ep_in.read(1024)
        except:
            if shouldreturn:
                raise
        if shouldreturn and rv:
            raise IOError("rp2040 returned from command that should have failed")
    
    def exclusive(self):
        self.send_cmd(0x01, b"\x02")
    
    def write(self, addr, data):
        args = struct.pack("<LL", addr, len(data))
        self.send_cmd(0x05, args, data)
    
    def reboot(self, pc, sp, delay):
        args = struct.pack("<LLL", pc, sp, delay)
        self.send_cmd(0x02, args, shouldreturn = False)
    
    def exec(self, addr):
        args = struct.pack("<L", addr)
        self.send_cmd(0x08, args, shouldreturn = False)
    
    def bootelf(self, file):
        SHF_ALLOC = 2
        
        self.exclusive()
        
        elf = ELFFile(open(file, 'rb'))
        for sh in elf.iter_sections():
            if sh['sh_flags'] & SHF_ALLOC:
                if sh['sh_type'] == 'SHT_PROGBITS':
                    ofs = sh['sh_addr']
                    print(f"writing {len(sh.data())} bytes to {ofs:x}")
                    self.write(ofs, sh.data())
                elif sh['sh_type'] == 'SHT_NOBITS':
                    ofs = sh['sh_addr']
                    sz = sh['sh_size']
                    print(f"writing {sz} zeroes to {ofs:x}")
                    self.write(ofs, b"\x00" * sz)
        print(f"booting from {elf.header['e_entry']:x}")
        self.reboot(elf.header['e_entry'], 0x20040000, 10)
    

PORTS = {
    'A': { 0:  5, 1:  4, 2:  4, 3:  2, 4: 29, 5: 35, 6:  1, 7:  0 },
    'B': { 0: 11, 1: 10, 2:  9, 3:  8, 4: 28, 5: 36, 6:  7, 7:  6 },
    'C': { 0: 17, 1: 16, 2: 15, 3: 14, 4: 27, 5: 34, 6: 13, 7: 12 },
    'D': { 0: 23, 1: 22, 2: 21, 3: 20, 4: 26, 5: 37, 6: 19, 7: 18 },
}

class Rp2040:
    def __init__(self):
        def is_expander_rp2040(dev):
            return dev.idVendor == 0x2E8A and dev.idProduct == 0x000A and dev.manufacturer == "X1Plus" and dev.product == "X1Plus Expander GPIO controller"
        self.rp2040 = usb.core.find(custom_match = is_expander_rp2040)
        if not self.rp2040:
            raise IOError("no Expander RP2040 found")
        self.rp2040.set_configuration()
        self.intf = self.rp2040[0][(0, 0)]
        self.ep_out = self.intf[0]
        self.ep_in  = self.intf[1]
    
    def write_leds(self, pin, buf):
        hdr = struct.pack('<BHB', 1, len(buf), pin)
        self.ep_out.write(hdr + buf)

    def gpio(self, pin, value = None, pull_up = False, pull_down = False):
        cfg = 0
        if pull_up:
            cfg |= 1
        if pull_down:
            cfg |= 2
        if value is not None:
            cfg |= 4
            if value:
                cfg |= 8
        self.ep_out.write(struct.pack('<BBB', 2, pin, cfg))

    def gpio_get(self, pin):
        self.ep_out.write(struct.pack('<BB', 3, pin))
        rv = self.ep_in.read(1)
        return rv[0]
    
    def i2c_write(self, scl, sda, addr, data):
        self.ep_out.write(struct.pack('<BBB', 4, scl, sda))
        self.ep_out.write(struct.pack('<BBB', 2, addr, len(data)) + data)
        self.ep_out.write(struct.pack('<B', 0))
        
        buf = b""
        while len(buf) < 1:
            buf += self.ep_in.read(0x100)
        if buf[0] != 0:
            raise IOError("I2C transaction failed")
    
    def i2c_read(self, scl, sda, addr, dlen):
        self.ep_out.write(struct.pack('<BBB', 4, scl, sda))
        self.ep_out.write(struct.pack('<BBB', 1, addr, dlen))
        self.ep_out.write(struct.pack('<B', 0))
        
        buf = b""
        while len(buf) < (dlen + 1):
            buf += self.ep_in.read(0x100)
        if buf[0] != 0:
            raise IOError("I2C transaction failed")
        
        return buf[1:]
    
    def stemma_read(self, *args, **kwargs):
        return self.i2c_read(PORTS['D'][0], PORTS['D'][1], *args, **kwargs)

    def stemma_write(self, *args, **kwargs):
        self.i2c_write(PORTS['D'][0], PORTS['D'][1], *args, **kwargs)

    def pca9536(self, led_pass = False, led_fail = False, load_5v = False, load_3v3 = False):
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
        
        self.stemma_write(addr, bytes([0x01, outputs]))
        self.stemma_write(addr, bytes([0x03, 0x00])) # set pins as outputs

    def ina219(self, addr):
        self.stemma_write(addr, bytes([0x00, 0x31, 0x9F])) # set PGA = 160 mV (PGA = /4)
        buf = self.stemma_read(addr, 2)
        cfg, = struct.unpack(">H", buf)
        assert cfg == 0x319F
        
        time.sleep(0.025)
        
        self.stemma_write(addr, bytes([0x01]))
        buf = self.stemma_read(addr, 2)
        vshunt, = struct.unpack(">h", buf)
        
        self.stemma_write(addr, bytes([0x02]))
        buf = self.stemma_read(addr, 2)
        vbus, = struct.unpack(">H", buf)
        
        vbus_f = float(vbus >> 3) * 0.004
        vshunt_f = float(vshunt) * 1e-5
        ishunt_f = vshunt_f * 0.5 / 0.04
        
        return Ina219Result(vbus = vbus_f, vshunt = vshunt_f, ishunt = ishunt_f, vbus_raw = vbus, vshunt_raw = vshunt)

"""
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
"""