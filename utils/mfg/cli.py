#!/usr/bin/env python3

import time
import logging
import argparse
import asyncio
import json

from .boards import dummy

logger = logging.getLogger(__name__)

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
    
    asyncio.run(ConsoleRunner().run(dummy.Fixture().test, serial = args.serial, force = args.force))
