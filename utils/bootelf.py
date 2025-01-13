import expanderlib.smsc9514
import expanderlib.rp2040
import time

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
b.bootelf('../../fw/build/x1p_002_c_fw.elf')

print("Waiting for RP2040 to reboot...")
for retry in range(10, 0, -1):
    try:
        rp = rp2040.Rp2040()
        break
    except Exception as e:
        if retry == 1:
            raise
        time.sleep(0.1)

rp.pca9536(led_pass = True)