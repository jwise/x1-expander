#!/usr/bin/env python3

import asyncio
import logging
import time
import json

from boardtest_dummy import test_x1p_002

from nicegui import app, run, ui

logger = logging.getLogger(__name__)

logging.getLogger().setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter("[%(asctime)s] %(name)s: %(levelname)s: %(message)s"))
logging.getLogger().addHandler(ch)

class _BoardLogHandler(logging.Handler):
    def __init__(self, boardlog):
        self.boardlog = boardlog
        logging.Handler.__init__(self)
        self.setLevel(logging.DEBUG)
        self.setFormatter(logging.Formatter("%(name)s: %(levelname)s: %(message)s"))
    
    def emit(self, record):
        self.boardlog.log(self.format(record))

class BoardLog:
    def __init__(self, testfunc, serial):
        self.logger = logging.getLogger(testfunc.__module__).getChild(testfunc.__name__)
        self.serial = serial
        self.testfunc = testfunc
        self.events = []
    
    def _event(self, ty, payload = None):
        self.events.append({ "type": ty, "payload": payload, "ts": time.time() })
    
    def running(self):
        self._event("running")
        ui_set_indicator('running')
    
    def status(self, msg):
        self._event("status", msg)
        ui_test_status.text = msg
        self.logger.info(msg)
    
    def log(self, msg):
        self._event("log", msg)
        self.logger.debug(msg)
    
    def measure(self, name, measurement):
        self._event("measurement", { "name": name, "value": measurement })
        self.logger.debug(f"measurement {name}: {json.dumps(measurement)}")
    
    def check(self, name, value, range):
        self._event("check", { "name": name, "value": value, "lbound": range[0], "ubound": range[1] })
        self.logger.debug(f"range check {name}: {range[0]} < {value} < {range[1]}")
        assert range[0] < value < range[1], f"value {name} ({value}) out of range ({range[0]},{range[1]})"
    
    async def run(self, **kwargs):
        ui_current_serial.text = self.serial

        blh = _BoardLogHandler(self)
        blh.addFilter(lambda record: record.name != self.logger.name)
        
        logging.getLogger().addHandler(blh)
        try:
            ui_set_indicator('waiting')
            self._event("start", { "serial": self.serial })
            await self.testfunc(runner = self, serial = self.serial, **kwargs)
        except Exception as e:
            self._event("fail", str(e))
            ui_test_status.text = str(e)
            self.logger.error(f"TEST FAILED: {str(e)}")
            ui_set_indicator('fail')
            print(self.events)
            return
        finally:
            logging.getLogger().removeHandler(blh)
        
        print(self.events)
        self.logger.info("TEST PASSED")
        ui_set_indicator('pass')


class _UiLogHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.setLevel(logging.DEBUG)
        self.setFormatter(logging.Formatter("[%(asctime)s] %(name)s: %(levelname)s: %(message)s"))
    
    def emit(self, record):
        try:
            log_element.push(self.format(record))
        except:
            self.handleError(record)

logging.getLogger().addHandler(_UiLogHandler())

async def run_test(self):
    ui_test_button.enabled = False
    ui_force.enabled = False
    force = ui_force.value
    await BoardLog(testfunc = test_x1p_002, serial = ui_nextsn.value).run(force = force)
    ui_force.value = False
    ui_test_button.enabled = True
    ui_force.enabled = True
    ui_nextsn.value = "X1P-002-C03-0002"

def check_serial(sn_proposed):
    if not sn_proposed.startswith("X1P-002-C03-"):
        return "Invalid prefix"
    
    if sn_proposed == "X1P-002-C03-0002":
        return "Already serialized"

    if sn_proposed > "X1P-002-C03-0010":
        return "Label not yet printed"
    
    return None

def previous_sn():
    if ui_current_serial.text != "...":
        ui_nextsn.value = ui_current_serial.text

### Actual UI stuff follows

ui.page_title("X1P-002 board test")
ui.dark_mode().enable() # duh

indicators = {
    'pass': ui.label("PASS").classes("bg-green-600 rounded-lg w-full text-center p-20 text-8xl"),
    'fail': ui.label("FAIL").classes("bg-red-600 rounded-lg w-full text-center p-20 text-8xl"),
    'waiting': ui.label("Waiting").classes("bg-gray-200 rounded-lg w-full text-center p-20 text-8xl text-black"),
    'running': ui.label("Running").classes("bg-green-200 rounded-lg w-full text-center p-20 text-8xl text-black"),
}

ui_current_serial = ui.label("...").classes("rounded-lg w-full text-center text-3xl")

ui_test_status = ui.label("...").classes("rounded-lg w-full text-center text-3xl")

ui.separator()

with ui.row(align_items = "center").classes('w-full'):
    ui.space()
    ui_test_button = ui.button("Run test", on_click = run_test, color="positive")
    ui.separator().props("vertical")
    ui_force = ui.checkbox("Force reprogram board")
    ui.separator().props("vertical")
    ui_nextsn = ui.input(label = "Next serial number", validation = check_serial)
    ui.button("Previous", on_click = previous_sn, color="negative")
    ui.space()

ui.separator()

with ui.row(align_items = "center").classes('w-full'):
    ui.space()
    ui.label("First unprinted label:").classes("text-bold")
    ui.label("X1P-002-C03-0020")
    ui.separator().props("vertical")
    ui.number(label = "Labels to print", value = 20, min = 1)
    ui.separator().props("vertical")
    ui_print_button = ui.button("Print labels")
    ui.space()

ui.separator()

ui_nextsn.value = "X1P-002-C03-0001"

log_element = ui.log().classes('w-full')


def ui_set_indicator(indicator):
    for v in indicators.values():
        v.visible = False
    indicators[indicator].visible = True

ui_set_indicator('waiting')

#app.on_startup(test_main)

ui.run()
