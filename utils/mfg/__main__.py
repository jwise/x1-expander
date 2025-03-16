import argparse
import asyncio
import logging

from . import cli, boards

logging.getLogger().setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter("[%(asctime)s] %(name)s: %(levelname)s: %(message)s"))
logging.getLogger().addHandler(ch)

parser = argparse.ArgumentParser()
parser.add_argument("--cli", action="store_true", default = False)

cligroup = parser.add_argument_group("CLI-specific options")
cligroup.add_argument("--serial", action="store", nargs = 1)
cligroup.add_argument("--force", action="store_true", default = False)

fixture_options = parser.add_subparsers(metavar = "fixture", required=True)
for fixture in boards.fixtures:
    fparser = fixture_options.add_parser(fixture.BOARD_ID.lower(), help = fixture.NAME)
    fparser.set_defaults(fixture = fixture)
    group = fparser.add_argument_group("fixture-specific options")
    fixture.add_args(group)

args = parser.parse_args()

fixture = args.fixture(args)

if args.cli:
    asyncio.run(cli.ConsoleRunner().run(fixture.test, serial = args.serial[0] if args.serial else None, force = args.force))
else:
    from . import gui
    from nicegui import ui

    testui = gui.TestUi(fixture = fixture, db = gui._DummyDb())
    testui.render()
    ui.run(reload = False)
