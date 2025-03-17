from jinja2 import Environment, PackageLoader
import sys
import asyncio
import socket
import logging

logger = logging.getLogger(__name__)

ZEBRA_IP = None

async def print_serial_labels(serials):
    env = Environment(loader=PackageLoader("mfg", ".."))
    zpl = env.get_template(f"serial.zpl_tpl").render(serials = serials)
    
    logger.debug(f"generated {len(zpl)} bytes of ZPL for serials {serials}")
    
    if not ZEBRA_IP:
        logger.warning("no printer connected -- doing nothing")
    else:
        logger.info(f"printing to Zebra at {ZEBRA_IP}")
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ZEBRA_IP, 9100), timeout = 5)
        writer.write(zpl.encode("UTF-8"))
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        logger.info("done printing")
