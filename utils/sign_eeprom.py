import sys
import struct
import ecdsa
import time

# DO NOT USE THIS ON AN UNTRUSTED MACHINE.  IT TAKES NO EFFORT TO AVOID SIDE
# CHANNEL ATTACKS AND DOES NOTHING TO CLEAN ITS KEYS OUT OF MEMORY AFTER
# USE.

# ecdsa.util.sigencode_string format; to transform into an OpenSSL DER digest:
#   ecdsa.util.sigencode_der(*ecdsa.util.sigdecode_string(sig, ecdsa.NIST256p.order), ecdsa.NIST256p.order)
ECDSA_SIG_LENGTH = 64

def sign(eeprom, key="private.pem"):
    origlen = len(eeprom)
    
    if eeprom[-1] != 0xFF:
        raise ValueError("eeprom already appears to have a signature block?")

    eeprom = bytearray(eeprom)

    ser_time_data = struct.pack("<LB", int(time.time()), 2)
    sig_block_size = len(ser_time_data)+ECDSA_SIG_LENGTH
    eeprom[len(eeprom)-sig_block_size:] = b'\xFF' * ECDSA_SIG_LENGTH + ser_time_data
    
    with open(key) as f:
        sk = ecdsa.SigningKey.from_pem(f.read())
    sig = sk.sign_deterministic(eeprom)
    eeprom[len(eeprom)-sig_block_size:] = sig + ser_time_data
    
    assert len(eeprom) == origlen

    return bytes(eeprom)

def validate(eeprom, key="public.pem", verbose=False):
    if eeprom[-1] == 0xFF:
        if verbose:
            print("EEPROM appears to be blank or unsigned")
        return False
    if eeprom[-1] == 1:
        if verbose:
            (ser_time, type) = struct.unpack("<LB", eeprom[len(eeprom)-5:])
            print(f"EEPROM has serialization version 1 (time only, unsigned), serialized at {ser_time}")
        return False
    if eeprom[-1] == 2:
        sig = eeprom[len(eeprom)-5-ECDSA_SIG_LENGTH:len(eeprom)-5]
        ser_time_data = eeprom[len(eeprom)-5:]
        
        # knock out the signature and replace with 0xFF
        eeprom = bytearray(eeprom)
        sig_block_size = len(ser_time_data)+ECDSA_SIG_LENGTH
        eeprom[len(eeprom)-sig_block_size:] = b'\xFF' * ECDSA_SIG_LENGTH + ser_time_data
        
        with open(key) as f:
            vk = ecdsa.VerifyingKey.from_pem(f.read())
        
        try:
            if not vk.verify(sig, eeprom):
                if verbose:
                    print("EEPROM signature type 2 did not verify")
                return False
        except Exception as e:
            if verbose:
                print(f"EEPROM signature type 2 verification raised exception: {e}")
            return False
        
        (ser_time, type) = struct.unpack("<LB", eeprom[len(eeprom)-5:])
        if verbose:
            print(f"EEPROM has valid serialization version 2 (signed), serialized at {ser_time}")
        
        return True
    if verbose:
        print(f"EEPROM has unsupported signature block version {eeprom[-1]}")
    return False

if __name__ == "__main__":
    with open(sys.argv[1], 'rb') as f:
        bs = f.read()
    if validate(bs, verbose=True):
        print("EEPROM signature verification successful")
    else:
        print("EEPROM does not have a valid signature")
