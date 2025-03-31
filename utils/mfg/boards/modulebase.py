import asyncio
import logging
import time
from contextlib import AsyncExitStack

import mfg

from mfg.hw.gpp4323 import GPP4323, Monitor
from mfg.hw.expanderlib import smsc9514, rp2040
from mfg.hw.expanderlib.rp2040 import INA219_24V, INA219_5V, INA219_3V3, PORTS

from mfg.hw import lan9514
from mfg.hw import sign_eeprom

logger = logging.getLogger(__name__)

async def _sync_ui():
    # synchronous tasks on this thread could prevent the UI from updating, so give the UI a chance
    await asyncio.sleep(0)

class ModuleFixture:
    # NAME = "X1Plus mainboard"
    # BOARD_ID = "X1P-002-C03"
    QUIESCENT_WAIT_TIMEOUT = 15
    SMSC9514_BOOT_TIMEOUT = 5
    RP2040_ENUMERATION_TIMEOUT = 2
    RP2040_BOOT_ATTEMPTS = 5
    
    @classmethod
    def add_args(cls, parser):
        parser.add_argument("--gpp-ip", action="store", nargs = 1, default = [ "10.1.10.132" ])
        parser.add_argument("--gpp-channel", action = "store", nargs = 1, default = [ "1" ])
    
    def __init__(self, args):
        self.gpp = GPP4323(args.gpp_ip[0])
        self.gpp_ch = self.gpp.channel(int(args.gpp_channel[0]))
        self.gpp.wait()
        self.gpp_ch.disable()
        self.gpp_ch.source(voltage = 0.0, current = 0.5)
        self.args = args

        logger.info("booting test fixture")
        time.sleep(0.5)
        self.gpp_ch.monitor(current = Monitor.ABOVE(1.0), trigger = Monitor.TRIG_OUTOFF | Monitor.TRIG_BEEPER)
        self.gpp_ch.source(voltage = 24.0, current = 0.5)
        self.gpp_ch.enable()
        
        for retry in range(self.SMSC9514_BOOT_TIMEOUT * 5, 0, -1):
            try:
                smsc = smsc9514.Smsc9514()
                break
            except:
                if retry == 1:
                    raise
                time.sleep(0.2)
        
        smsc.rp2040_reset()

        for retry in range(self.RP2040_ENUMERATION_TIMEOUT * 10, 0, -1):
            try:
                b = rp2040.Rp2040Boot()
                break
            except:
                if retry == 1:
                    raise
                time.sleep(0.1)
        b.bootelf(f"{mfg.__path__[0]}/../../fw/build/x1p_002_c_fw.elf")

        for retry in range(self.RP2040_ENUMERATION_TIMEOUT * 10, 0, -1):
            try:
                self.rp = rp2040.Rp2040()
                break
            except:
                if retry == 1:
                    raise
                time.sleep(0.1)

        self.rp.pca9536()
        
        logger.info("test fixture booted, letting power supplies settle for a moment")
        
        time.sleep(3)
        self.iq_24v = self.rp.ina219(INA219_24V)
        self.boot_time = time.time()
        
        logger.info(f"test fixture quiescent current {self.iq_24v.vbus}V, {self.iq_24v.ishunt}A")

    def port(self, port, *args, **kwargs):
        self.rp.gpio(PORTS['A'][port], *args, **kwargs)
    
    def reset_gpios(self):
        for n in range(8):
            self.port(n)
    
    def delta_current(self):
        i_24v = self.rp.ina219(INA219_24V)
        return i_24v.ishunt - self.iq_24v.ishunt
    
    def read_eeprom(self):
        self.rp.i2c_write(scl = PORTS['A'][7], sda = PORTS['A'][6], addr = 0x50, data = b'\x00')
        buf = b""
        buf += self.rp.i2c_read(scl = PORTS['A'][7], sda = PORTS['A'][6], addr = 0x50, dlen = 0x80)
        buf += self.rp.i2c_read(scl = PORTS['A'][7], sda = PORTS['A'][6], addr = 0x50, dlen = 0x80)
        return buf
    
    def write_eeprom(self, buf):
        pos = 0
        while len(buf) > 0:
            n = min(0x10, len(buf))
            
            self.rp.i2c_write(scl = PORTS['A'][7], sda = PORTS['A'][6], addr = 0x50, data = bytes([pos]) + buf[:n])

            pos += n
            buf = buf[n:]

    async def test(self, runner, serial = None, force = False):
        async with AsyncExitStack() as stack:
            self.rp.pca9536()
            
            # blink the pass/fail LED for a second at DUT end
            fail_status = True
            pass_status = False
            
            stack.callback(lambda: self.rp.pca9536(led_pass = pass_status, led_fail = fail_status))
            
            runner.measure("24V quiescent", self.iq_24v._asdict())
            runner.measure("fixture boot time", self.boot_time)
            
            await self.module_test(runner)

            # make sure EEPROM is blank
            runner.status("Reading EEPROM")
            await _sync_ui()
            self.reset_gpios()
            buf = self.read_eeprom()
            if buf != b'\xff' * 512:
                runner.measure("eeprom_contents", [ i for i in buf ])
                if force:
                    runner.log("EEPROM not empty, but continuing anyway as you asked")
                else:
                    raise FileExistsError("EEPROM not empty")
            else:
                runner.log("EEPROM is empty")

            if not serial:
                raise FileNotFoundError("No serial number specified")    

            EEPROM_SIZE = 256
            sno = int(serial.split("-")[-1])
            eeprom_base = f"{self.BOARD_ID:16s}{sno:08d}".encode()
            eeprom = sign_eeprom.sign(eeprom_base + b'\xFF' * (EEPROM_SIZE - len(eeprom_base)))
        
            runner.status("Writing EEPROM")
            await _sync_ui()
            self.write_eeprom(eeprom)

            runner.status("Reading back EEPROM")
            await _sync_ui()
            buf = self.read_eeprom()
            assert eeprom == buf

            runner.status("Test complete")

            fail_status = False
            pass_status = True
