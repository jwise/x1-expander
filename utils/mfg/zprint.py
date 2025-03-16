from jinja2 import Environment, PackageLoader
import sys
import socket
import logging

logger = logging.getLogger(__name__)

ZEBRA_IP = None

def print_serial_labels(serials):
    env = Environment(loader=PackageLoader("mfg", ".."))
    zpl = env.get_template(f"serial.zpl_tpl").render(serials = serials)
    
    logger.debug(f"generated {len(zpl)} bytes of ZPL for serials {serials}")
    
    if not ZEBRA_IP:
        logger.warning("no printer connected -- doing nothing")
    else:
        logger.info(f"printing to Zebra at {ZEBRA_IP}")
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        skt.connect((ZEBRA_IP, 9100))
        skt.send(zpl.encode("UTF-8"))
        skt.close()
        logger.info("done printing")
