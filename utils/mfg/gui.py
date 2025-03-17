#!/usr/bin/env python3

import asyncio
import logging
import time
import json

from . import boards, mfgdb, zprint

from nicegui import app, run, ui

logger = logging.getLogger(__name__)


class _NiceGuiRunnerHandler(logging.Handler):
    def __init__(self, boardlog):
        self.boardlog = boardlog
        logging.Handler.__init__(self)
        self.setLevel(logging.DEBUG)
        self.setFormatter(logging.Formatter("%(name)s: %(levelname)s: %(message)s"))
    
    def emit(self, record):
        self.boardlog.log(self.format(record))

class NiceGuiRunner:
    def __init__(self, ui, fixture, serial, db):
        self.ui = ui
        self.logger = logging.getLogger(fixture.__module__)
        self.serial = serial
        self.fixture = fixture
        self.db = db
    
    def _event(self, ty, payload = None):
        self.db.event(self.serial, { "type": ty, "payload": payload, "ts": time.time() })
    
    def running(self):
        self._event("running")
        self.ui.set_indicator('running')
    
    def status(self, msg):
        self._event("status", msg)
        self.ui.test_status.text = msg
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
        self.ui.current_serial.text = self.serial

        blh = _NiceGuiRunnerHandler(self)
        blh.addFilter(lambda record: record.name != self.logger.name)
        
        logging.getLogger().addHandler(blh)
        try:
            self.ui.set_indicator('waiting')
            self._event("start", { "serial": self.serial })
            await self.fixture.test(runner = self, serial = self.serial, **kwargs)
        except Exception as e:
            self._event("fail", str(e))
            self.ui.test_status.text = str(e)
            self.logger.error(f"TEST FAILED: {str(e)}")
            self.ui.set_indicator('fail')
            return
        finally:
            logging.getLogger().removeHandler(blh)
        
        self._event("pass")
        self.ui.test_status.text = "Test passed"
        self.logger.info("TEST PASSED")
        self.ui.set_indicator('pass')



### Actual UI stuff follows

class _NiceGuiLogHandler(logging.Handler):
    def __init__(self, element):
        logging.Handler.__init__(self)
        self.setLevel(logging.DEBUG)
        self.setFormatter(logging.Formatter("[%(asctime)s] %(name)s: %(levelname)s: %(message)s"))
        self.element = element
    
    def emit(self, record):
        try:
            self.element.push(self.format(record))
        except:
            self.handleError(record)

class TestUi():
    def __init__(self, fixture, db):
        self.fixture = fixture
        self.db = db
        self.prevsn = None

    def set_indicator(self, indicator):
        for v in self.indicators.values():
            v.visible = False
        self.indicators[indicator].visible = True

    def longsn(self, proposed = None):
        if proposed is None:
            proposed = self.nextsn.value
        return f"{self.fixture.BOARD_ID}-{proposed}"

    def check_nextsn(self, sn_proposed):
        if len(sn_proposed) != 4:
            return "Invalid format"
        try:
            int(sn_proposed)
        except:
            return "Invalid format"
        
        sn = self.longsn(sn_proposed)
        
        if self.db.has_event(sn, "pass"):
            return "Already serialized"
        
        if not self.db.has_event(sn, "print_label"):
            return "Label not yet printed"
        
        return None

    async def run_test(self):
        self.test_button.enabled = False
        self.force.enabled = False
        force = self.force.value
        await NiceGuiRunner(ui = self, fixture = self.fixture, db = self.db, serial = self.longsn()).run(force = force)
        self.force.value = False
        self.test_button.enabled = True
        self.force.enabled = True
        self.prevsn = self.nextsn.value
        self.nextsn.value = "%04d" % (int(self.nextsn.value) + 1, )

    def previous_sn(self):
        if self.prevsn is not None:
            self.nextsn.value = self.prevsn
    
    async def print_labels(self):
        start_sn = int(self.next_label.text.rsplit("-",1)[1])
        
        labels = [ f"{self.fixture.BOARD_ID}-{start_sn + i:04d}" for i in range(int(self.label_count.value))]
        
        await zprint.print_serial_labels(labels)
        
        for sn in labels:
            self.db.event(sn, { "type": "print_label" })
        
        self.nextsn.value = "%04d" % (start_sn, )
        self.next_label.text = self.db.first_without_event(self.fixture.BOARD_ID, "print_label")
        self.nextsn.validate()

    def render(self):
        ui.page_title(f"{self.fixture.BOARD_ID} board test")
        ui.dark_mode().enable() # duh

        self.indicators = {
            'pass': ui.label("PASS").classes("bg-green-600 rounded-lg w-full text-center p-20 text-8xl"),
            'fail': ui.label("FAIL").classes("bg-red-600 rounded-lg w-full text-center p-20 text-8xl"),
            'waiting': ui.label("Waiting").classes("bg-gray-200 rounded-lg w-full text-center p-20 text-8xl text-black"),
            'running': ui.label("Running").classes("bg-green-200 rounded-lg w-full text-center p-20 text-8xl text-black"),
        }

        self.current_serial = ui.label("...").classes("rounded-lg w-full text-center text-3xl")

        self.test_status = ui.label("...").classes("rounded-lg w-full text-center text-3xl")

        ui.separator()

        with ui.row(align_items = "center").classes('w-full'):
            ui.space()
            self.test_button = ui.button("Run test", on_click = self.run_test, color="positive")
            ui.separator().props("vertical")
            self.force = ui.checkbox("Force reprogram board").props("color=negative")
            ui.separator().props("vertical")
            self.nextsn = ui.input(label = "Next serial number", validation = self.check_nextsn).props(f"mask=\"####\" prefix=\"{self.fixture.BOARD_ID}-\" fill-mask=\"_\"").classes("w-48")
            ui.button("Previous", on_click = self.previous_sn, color="negative")
            ui.space()

        ui.separator()

        with ui.row(align_items = "center").classes('w-full'):
            ui.space()
            ui.label("First unprinted label:").classes("text-bold")
            self.next_label = ui.label(self.db.first_without_event(self.fixture.BOARD_ID, "print_label"))
            ui.separator().props("vertical")
            self.label_count = ui.number(label = "Labels to print", value = 20, min = 1)
            ui.separator().props("vertical")
            self.print_button = ui.button("Print labels", on_click = self.print_labels)
            ui.space()

        ui.separator()

        self.nextsn.value = self.db.first_without_event(self.fixture.BOARD_ID, "pass").split("-")[3]

        self.log_element = ui.log(max_lines = 20).classes('w-full')
        logging.getLogger().addHandler(_NiceGuiLogHandler(self.log_element))

        self.set_indicator('waiting')

if __name__ in {"__main__", "__mp_main__"}:
    logging.getLogger().setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(name)s: %(levelname)s: %(message)s"))
    logging.getLogger().addHandler(ch)

    class Args():
        eeprom_empty = False
            
    testui = TestUi(fixture = boards.dummy(Args), db = mfgdb.DummyDb())
    testui.render()
    ui.run()

