#!/usr/bin/env python3

import time
import logging
import argparse
import asyncio
import json

logger = logging.getLogger(__name__)

async def test_x1p_002(runner, serial = None, force = False):
    runner.status("Waiting for LAN9514...")
    for _ in range(3):
        runner.log("still waiting: e")
        await asyncio.sleep(0.5)
    
    runner.running()
    
    runner.status("Resetting RP2040 from LAN9514...")
    await asyncio.sleep(0.5)
    
    runner.status("Checking quiescent current...")
    # ._asdict()
    runner.measure("iq_24v", {'vbus': 0, 'vshunt': 1, 'ishunt': 2, 'vbus_raw': 3, 'vshunt_raw': 4})
    
    runner.check("5v_esr", 0.135, range = (0, 1.0))
    
    logger.debug("debug message from deep within...")
    
    runner.check("i3v3_24v.vbus", 24, range = (23.8, 24.2))
    runner.log("regulator test PASS")
    runner.status("Reading EEPROM")
    await asyncio.sleep(0.5)
    if serial:
        if not force:
            assert False, "Board EEPROM is not empty"
        runner.status("Writing EEPROM")
        await asyncio.sleep(0.5)
        runner.status("Reading EEPROM")
        await asyncio.sleep(0.5)
    runner.status("Pass")

class ConsoleRunner:
    def __init__(self):
        self.logger = logger.getChild("ConsoleRunner")
    
    def running(self):
        self.logger.info("board detected; test running")
    
    def status(self, msg):
        self.logger.info(msg)
    
    def log(self, msg):
        self.logger.debug(msg)
    
    def measure(self, name, measurement):
        self.logger.debug(f"measurement {name}: {json.dumps(measurement)}")
    
    def check(self, name, value, range):
        self.logger.debug(f"range check {name}: {range[0]} < {value} < {range[1]}")
        assert range[0] < value < range[1]
    
    async def run(self, test, *args, **kwargs):
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter("TEST CONSOLE: [%(asctime)s] %(name)s: %(levelname)s: %(message)s"))
        logging.getLogger().addHandler(ch)
        
        try:
            await test(runner = self, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"TEST FAILED: {e}")
            return False
        finally:
            logging.getLogger().removeHandler(ch)
        
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", action="store", nargs = 1)
    parser.add_argument("--force", action="store_true", default = False)
    args = parser.parse_args()

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    
    serial = None
    if args.serial:
        serial = args.serial[0]
    
    asyncio.run(ConsoleRunner().run(test_x1p_002, serial = args.serial, force_serialize = args.force))
