import asyncio
import logging

logger = logging.getLogger(__name__)

class Fixture:
    NAME = "X1Plus dummy fixture"
    BOARD_ID = "X1P-DMY-A00"
    
    def __init__(self):
        pass

    async def test(self, runner, serial = None, force = False):
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
