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
        try:
            await test(runner = self, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"TEST FAILED: {e.__class__.__name__}: {e}")
            return False
        
        return True
