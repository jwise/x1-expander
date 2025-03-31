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
    NAME = "X1Plus Andon Board"
    BOARD_ID = "X1P-005-B02"
    
    async def module_test(self, runner):
        self.reset_gpios()

        di_base = self.delta_current()
        runner.check("module quiescent current @ 24V", self.delta_current(), (0.000, 0.005))
        runner.running()
        
        # check to ensure the buzzer seems to work
        runner.status("Testing buzzer")
        await _sync_ui()
        self.port(3, value = True)
        try:
            runner.check("module beep current @ 24V", self.delta_current() - di_base, (0.0035, 0.010))
        finally:
            self.port(3) # for god's sake
        
        # check to ensure LEDs draw some current
        runner.status("Testing LEDs")
        await _sync_ui()
        try:
            for i in range(25):
                self.rp.write_leds(PORTS['A'][1], b"\x00" * (i * 3) + b"\xFF\xFF\xFF" + b"\x00" * ((25 - i) * 3))
                runner.check(f"LED {i} current", self.delta_current() - di_base, (0.003, 0.006))
                await _sync_ui()
        finally:    
            self.rp.write_leds(PORTS['A'][1], b"\x00" * (25 * 3))
        
        # check to make sure that buttons are not shorted
        runner.status("Testing buttons")
        await _sync_ui()
        self.port(5, value = True)

        self.port(6, pull_up = True)
        self.port(7, pull_up = True)
        assert self.rp.gpio_get(PORTS['A'][6]) == 1, "io6 was not pulled up"
        assert self.rp.gpio_get(PORTS['A'][7]) == 1, "io7 was not pulled up"

