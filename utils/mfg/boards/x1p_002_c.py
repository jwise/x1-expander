import asyncio
import logging
from contextlib import AsyncExitStack

import mfg

from mfg.hw.gpp4323 import GPP4323, Monitor
from mfg.hw.expanderlib import smsc9514, rp2040
from mfg.hw.expanderlib.rp2040 import INA219_24V, INA219_5V, INA219_3V3

from mfg.hw import lan9514
from mfg.hw import sign_eeprom

logger = logging.getLogger(__name__)

async def _sync_ui():
    # synchronous tasks on this thread could prevent the UI from updating, so give the UI a chance
    await asyncio.sleep(0)

class Fixture:
    NAME = "X1Plus mainboard"
    BOARD_ID = "X1P-002-C03"
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

    async def boot_rp2040(self, runner, smsc):
        runner.log("Resetting RP2040 from LAN9514")
        smsc.rp2040_reset()

        runner.log("Waiting for RP2040")
        for retry in range(self.RP2040_ENUMERATION_TIMEOUT * 10, 0, -1):
            try:
                b = rp2040.Rp2040Boot()
                break
            except:
                if retry == 1:
                    raise
                await asyncio.sleep(0.1)

        runner.log("Booting test firmware")
        await _sync_ui()
        b.bootelf(f"{mfg.__path__[0]}/../../fw/build/x1p_002_c_fw.elf")

        runner.log("Waiting for RP2040 to reboot")
        for retry in range(self.RP2040_ENUMERATION_TIMEOUT * 10, 0, -1):
            try:
                rp = rp2040.Rp2040()
                break
            except:
                if retry == 1:
                    raise
                await asyncio.sleep(0.1)

        return rp

    async def test(self, runner, serial = None, force = False):
        async with AsyncExitStack() as stack:
            runner.status("Waiting for board quiescent current")
            self.gpp_ch.monitor(current = Monitor.ABOVE(1.0), trigger = Monitor.TRIG_OUTOFF | Monitor.TRIG_BEEPER)
            self.gpp_ch.source(voltage = 3.5, current = 0.5)
            self.gpp_ch.enable()
            
            stack.callback(self.gpp_ch.disable)
        
            for retry in range(self.QUIESCENT_WAIT_TIMEOUT * 5, 0, -1):
                meas = self.gpp_ch.meas()
                if meas.current > 0.01:
                    # we have a DUT, ready to go
                    break
                if retry == 1:
                    raise TimeoutError("DUT never appeared")
                await asyncio.sleep(0.2)
            await asyncio.sleep(0.3) # let it settle
            meas = self.gpp_ch.meas()
            runner.check("Iddq at 3.5V", meas.current, (0.005, 0.150))
            self.gpp_ch.disable()

            runner.running()
        
            await asyncio.sleep(0.5)
            
            self.gpp_ch.source(voltage = 24, current = 0.5)
            self.gpp_ch.enable()
            runner.status("Waiting for LAN9514")
            await _sync_ui()
            for retry in range(self.SMSC9514_BOOT_TIMEOUT * 5, 0, -1):
                try:
                    smsc = smsc9514.Smsc9514()
                    break
                except:
                    if retry == 1:
                        raise
                    await asyncio.sleep(0.2)
            
            runner.status("Booting RP2040")
            await _sync_ui()
            for retry in range(self.RP2040_BOOT_ATTEMPTS, 0, -1):
                try:
                    rp = await self.boot_rp2040(runner, smsc)
                    break
                except:
                    if retry == 1:
                        raise

            # do this before initializing the pca9536, to avoid a small race here            
            meas = self.gpp_ch.meas()
            
            rp.pca9536()
            
            # blink the pass/fail LED for a second at DUT end
            fail_status = True
            pass_status = False
            
            stack.push_async_callback(asyncio.sleep, 1)
            stack.callback(lambda: rp.pca9536(led_pass = pass_status, led_fail = fail_status))

            runner.check("Idd at 24V, enumerated", meas.current, (0.025, 0.060))

            
            runner.status("Checking quiescent current")
            await _sync_ui()
            iq_24v = rp.ina219(INA219_24V)
            iq_5v = rp.ina219(INA219_5V)
            iq_3v3 = rp.ina219(INA219_3V3)
    
            runner.measure("24v_q", iq_24v._asdict())
            runner.measure("5v_q", iq_5v._asdict())
            runner.measure("3v3_q", iq_3v3._asdict())
            
            runner.check("vddq_24v", iq_24v.vbus, (23.8, 24.2))
            runner.check("vddq_5v",  iq_5v.vbus,  (4.9, 5.1))
            runner.check("vddq_3v3", iq_3v3.vbus, (3.2, 3.4))

            runner.check("iddq_24v", iq_24v.ishunt, (0, 0.08))
            runner.check("iq_5v",  iq_5v.ishunt,  (0, 0.003))
            runner.check("iq_3v3", iq_3v3.ishunt, (0, 0.003))

            
            runner.status("Checking 5V load efficiency...")
            await _sync_ui()
            rp.pca9536(load_5v = True)
            i5v_24v = rp.ina219(INA219_24V)
            i5v_5v = rp.ina219(INA219_5V)
            i5v_3v3 = rp.ina219(INA219_3V3)
            rp.pca9536()

            runner.measure("i5v_24v", i5v_24v._asdict())
            runner.measure("i5v_5v", i5v_5v._asdict())
            runner.measure("i5v_3v3", i5v_3v3._asdict())

            runner.check("vdd_5vload_24v", i5v_24v.vbus, (23.8, 24.2))
            runner.check("iload_5v", i5v_5v.ishunt, (0.45, 0.55))
            runner.check("vdd_5vload_3v3", i5v_3v3.vbus, (3.0, 3.4))
            
            dv = iq_5v.vbus - i5v_5v.vbus
            di_5v = i5v_5v.ishunt - iq_5v.ishunt
            esr = dv/di_5v
            runner.check("esr_5v", esr, (0.0, 1.2))
    
            dp_5v = iq_5v.vbus * di_5v
            dp_24v = i5v_24v.vbus * i5v_24v.ishunt - iq_24v.vbus * iq_24v.ishunt
            efficiency_5v = dp_5v / dp_24v
            runner.measure("input_dp_5v", dp_24v)
            runner.measure("output_dp_5v", dp_5v)
            runner.check("efficiency_5v", efficiency_5v, (0.8, 1.0))
            # we assume the ESR is in the pins, not the reg, so we use the 24v vbus for 5V, not the 5V-load vbus for 5V


            runner.status("Checking 3.3V load efficiency...")
            await _sync_ui()
            rp.pca9536(load_3v3 = True)
            i3v3_24v = rp.ina219(INA219_24V)
            i3v3_5v = rp.ina219(INA219_5V)
            i3v3_3v3 = rp.ina219(INA219_3V3)
            rp.pca9536()

            runner.measure("i3v3_24v", i3v3_24v._asdict())
            runner.measure("i3v3_5v", i3v3_5v._asdict())
            runner.measure("i3v3_3v3", i3v3_3v3._asdict())
            
            runner.check("vdd_3v3load_24v", i3v3_24v.vbus, (23.8, 24.2))
            runner.check("iload_3v3", i3v3_3v3.ishunt, (0.9, 1.1))
            runner.check("vdd_3v3load_5v", i3v3_5v.vbus, (4.6, 5.1))

            dv = iq_3v3.vbus - i3v3_3v3.vbus
            di_3v3 = i3v3_3v3.ishunt - iq_3v3.ishunt
            esr = dv/di_3v3
            runner.check("esr_3v3", esr, (0.0, 1.2))
    
            dp_3v3 = iq_3v3.vbus * di_3v3
            dp_24v = i3v3_24v.vbus * i3v3_24v.ishunt - iq_24v.vbus * iq_24v.ishunt
            efficiency_3v3 = dp_3v3 / dp_24v
            runner.measure("input_dp_3v3", dp_24v)
            runner.measure("output_dp_3v3", dp_3v3)
            runner.measure("efficiency_3v3_raw", efficiency_3v3)
            runner.check("efficiency_3v3_from_5v", efficiency_3v3 / efficiency_5v, (0.88, 1.0))

            # make sure EEPROM is blank
            runner.status("Reading EEPROM")
            await _sync_ui()
            buf = smsc.eeprom_readall()
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

            EEPROM_SIZE = 512

            eeprom_base = lan9514.Lan9514(
                manufacturer_id = "X1Plus",
                product_name = f"Expander {self.BOARD_ID}",
                serial_number = f"{serial}",
                hs_device_descriptor = b'\x12\x01\x00\x02\x00\x00\x00\x40\x24\x04\x00\xec\x00\x01\x01\x02\x03\x01',
                fs_device_descriptor = b'\x12\x01\x00\x02\x00\x00\x00\x40\x24\x04\x00\xec\x00\x01\x01\x02\x03\x01',
                #hs_config_descriptor = b"\t\x02'\x00\x01\x01\x00\xe0\x01\t\x04\x00\x00\x03\xff\x00\xff\x00",
                #fs_config_descriptor = b"\t\x02'\x00\x01\x01\x00\xe0\x01\t\x04\x00\x00\x03\xff\x00\xff\x00",
            ).encode()

            eeprom = sign_eeprom.sign(eeprom_base + b'\xFF' * (EEPROM_SIZE - len(eeprom_base)))
        
            runner.status("Writing EEPROM")
            await _sync_ui()
            smsc.eeprom_writeall(eeprom)

            runner.status("Reading back EEPROM")
            await _sync_ui()
            buf = smsc.eeprom_readall()
            assert eeprom == buf

            runner.status("Test complete")

            fail_status = False
            pass_status = True
