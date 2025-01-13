from expanderlib import smsc9514, rp2040
from expanderlib.rp2040 import INA219_24V, INA219_5V, INA219_3V3
import time
import argparse

import lan9514
import time
import struct
import sys
import sign_eeprom

parser = argparse.ArgumentParser()
parser.add_argument("--serial", action="store", nargs = 1)
parser.add_argument("--force", action="store_true", default = False)
args = parser.parse_args()

print("Resetting RP2040 from LAN9514...")
smsc = smsc9514.Smsc9514()
smsc.rp2040_reset()

print("Waiting for RP2040...")
for retry in range(10, 0, -1):
    try:
        b = rp2040.Rp2040Boot()
        break
    except Exception as e:
        if retry == 1:
            raise
        time.sleep(0.1)

print("Booting test firmware...")
b.bootelf('../fw/build/x1p_002_c_fw.elf')

print("Waiting for RP2040 to reboot...")
for retry in range(10, 0, -1):
    try:
        rp = rp2040.Rp2040()
        break
    except Exception as e:
        if retry == 1:
            raise
        time.sleep(0.1)

rp.pca9536()
try:
    print("checking quiescent current...")
    iq_24v = rp.ina219(INA219_24V)
    iq_5v = rp.ina219(INA219_5V)
    iq_3v3 = rp.ina219(INA219_3V3)
    
    print(iq_24v)
    print(iq_5v)
    print(iq_3v3)
    
    assert 23.8 < iq_24v.vbus < 24.2
    assert 3.2 < iq_3v3.vbus < 3.4
    assert 4.9 < iq_5v.vbus < 5.1
    print(f"  quiescent voltages OK ({iq_24v.vbus:.2f}V, {iq_3v3.vbus:.2f}V, {iq_5v.vbus:.2f}V)")
    
    print(f"  quiescent current OK ({iq_24v.ishunt*1000:.2f}mA, {iq_3v3.ishunt*1000:.2f}mA, {iq_5v.ishunt*1000:.2f}mA)")
    assert iq_24v.ishunt < 0.08
    assert iq_3v3.ishunt < 0.003
    assert iq_5v.ishunt < 0.003
    print(f"  quiescent current OK ({iq_24v.ishunt*1000:.2f}mA, {iq_3v3.ishunt*1000:.2f}mA, {iq_5v.ishunt*1000:.2f}mA)")
    
    # try 5V load
    print("checking 5V load efficiency...")
    rp.pca9536(load_5v = True)
    i5v_24v = rp.ina219(INA219_24V)
    i5v_5v = rp.ina219(INA219_5V)
    i5v_3v3 = rp.ina219(INA219_3V3)
    rp.pca9536()

    assert 23.8 < i5v_24v.vbus < 24.2
    assert 0.45 < i5v_5v.ishunt < 0.55, i5v_5v.ishunt
    assert 3.2 < i5v_3v3.vbus < 3.4
    
    dv = iq_5v.vbus - i5v_5v.vbus
    di_5v = i5v_5v.ishunt - iq_5v.ishunt
    esr = dv/di_5v
    print(f"  ESR = {esr:.3f} ohms at {i5v_5v.ishunt:.3f}A ({i5v_5v.vbus:.3f}V)")
    assert esr < 0.4
    
    dp_5v = iq_5v.vbus * di_5v
    dp_24v = i5v_24v.vbus * i5v_24v.ishunt - iq_24v.vbus * iq_24v.ishunt
    efficiency_5v = dp_5v / dp_24v
    print(f"  input dP {dp_24v:.3f}W, output dP {dp_5v:.3f}W, efficiency {efficiency_5v*100:.1f}%")
    assert efficiency_5v > .8
    # we assume the ESR is in the pins, not the reg

    print("checking 3v3 load efficiency...")
    rp.pca9536(load_3v3 = True)
    i3v3_24v = rp.ina219(INA219_24V)
    i3v3_5v = rp.ina219(INA219_5V)
    i3v3_3v3 = rp.ina219(INA219_3V3)
    rp.pca9536()

    assert 23.8 < i3v3_24v.vbus < 24.2
    assert 0.9 < i3v3_3v3.ishunt < 1.1
    assert 4.9 < i3v3_5v.vbus < 5.1
    
    dv = iq_3v3.vbus - i3v3_3v3.vbus
    di_3v3 = i3v3_3v3.ishunt - iq_3v3.ishunt
    esr = dv/di_3v3
    print(f"  ESR = {esr:.3f} ohms at {i3v3_3v3.ishunt:.3f}A ({i3v3_3v3.vbus:.3f}V)")
    assert esr < 0.4
    
    dp_3v3 = iq_3v3.vbus * di_3v3
    dp_24v = i3v3_24v.vbus * i3v3_24v.ishunt - iq_24v.vbus * iq_24v.ishunt
    efficiency_3v3 = dp_3v3 / dp_24v
    print(f"  input dP {dp_24v:.3f}W, output dP {dp_3v3:.3f}W, 24v -> 3v3 efficiency {efficiency_3v3*100:.1f}%, 5v -> 3v3 efficiency {efficiency_3v3/efficiency_5v*100:.1f}%")
    assert (efficiency_3v3/efficiency_5v) > .88

    print("regulator test PASS")
    
    # make sure EEPROM is blank
    print("testing EEPROM")
    buf = smsc.eeprom_readall()
    if buf != b'\xff' * 512:
        if args.force:
            print("  warning: EEPROM not empty")
        else:
            assert buf == (b'\xff' * 512), "EEPROM not empty"
    else:
        print("  EEPROM is empty")
    
    if args.serial:
        EEPROM_SIZE = 512

        board_rev = "C02"
        serial = args.serial[0]

        eeprom_base = lan9514.Lan9514(
            manufacturer_id = "X1Plus",
            product_name = f"Expander X1P-002-{board_rev}",
            serial_number = f"X1P-002-{board_rev}-{serial}",
            hs_device_descriptor = b'\x12\x01\x00\x02\x00\x00\x00\x40\x24\x04\x00\xec\x00\x01\x01\x02\x03\x01',
            fs_device_descriptor = b'\x12\x01\x00\x02\x00\x00\x00\x40\x24\x04\x00\xec\x00\x01\x01\x02\x03\x01',
            #hs_config_descriptor = b"\t\x02'\x00\x01\x01\x00\xe0\x01\t\x04\x00\x00\x03\xff\x00\xff\x00",
            #fs_config_descriptor = b"\t\x02'\x00\x01\x01\x00\xe0\x01\t\x04\x00\x00\x03\xff\x00\xff\x00",
        ).encode()

        eeprom = sign_eeprom.sign(eeprom_base + b'\xFF' * (EEPROM_SIZE - len(eeprom_base)))
        
        smsc.eeprom_writeall(eeprom)
        print("wrote EEPROM")
        
        buf = smsc.eeprom_readall()
        assert eeprom == buf

    rp.pca9536(led_pass = True)
    
    
except AssertionError as e:
    rp.pca9536(led_fail = True)
    raise
