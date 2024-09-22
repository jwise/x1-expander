import lan9514
import time
import struct
import sys
import sign_eeprom

EEPROM_SIZE = 256

board_rev = sys.argv[1] # "X1P-005-B01"
serial = int(sys.argv[2])

eeprom_base = f"{board_rev:16s}{serial:08d}".encode()
eeprom = sign_eeprom.sign(eeprom_base + b'\xFF' * (EEPROM_SIZE - len(eeprom_base)))

fname = f"eeprom-{board_rev}-{serial:08d}.bin"
with open(fname, "wb") as f:
    f.write(eeprom)

print(f"wrote plugin EEPROM data to {fname}")
