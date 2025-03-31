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
    NAME = "X1Plus Addressable-LED Level Shifter"
    BOARD_ID = "X1P-004-B01"
    
    async def module_test(self, runner):
        self.reset_gpios()

        di_base = self.delta_current()
        runner.check("module quiescent current @ 24V", self.delta_current(), (-0.003, 0.003))
        runner.running()
        
        # sadly, not much we can do here!  if it's not a short, it's probably fine.

