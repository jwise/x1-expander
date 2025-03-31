import asyncio
import logging
import time

from mfg.hw.expanderlib.rp2040 import PORTS
from .modulebase import ModuleFixture

logger = logging.getLogger(__name__)

async def _sync_ui():
    # synchronous tasks on this thread could prevent the UI from updating, so give the UI a chance
    await asyncio.sleep(0)

class Fixture(ModuleFixture):
    NAME = "X1Plus Shutter Release"
    BOARD_ID = "X1P-006-B02"
    
    async def module_test(self, runner):
        self.reset_gpios()

        di_base = self.delta_current()
        runner.check("module quiescent current @ 24V", self.delta_current(), (-0.001, 0.002))
        runner.running()
        
        runner.status("Testing Cam1 SSR")
        await _sync_ui()
        self.port(3, value = True)
        try:
            runner.check("SSR Cam1 current @ 24V", self.delta_current() - di_base, (0.001, 0.003))
        finally:
            self.port(3)

        runner.status("Testing Cam2 SSR")
        await _sync_ui()
        self.port(5, value = True)
        try:
            runner.check("SSR Cam2 current @ 24V", self.delta_current() - di_base, (0.001, 0.003))
        finally:
            self.port(5)

