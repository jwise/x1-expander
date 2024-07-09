import struct

class Lan9514:
    def __init__(self, from_bytes=None, **kwargs):
        if from_bytes:
            self._init_from_bytes(from_bytes)
        else:
            self._init_from_kwargs(**kwargs)
    
    def _init_from_kwargs(self,
        mac_address = b'\xff\xff\xff\xff\xff\xff',
        fs_polling_interval = 0x01,
        hs_polling_interval = 0x04,
        configuration_flags = 0x05,
        language_id = 0x0409,
        manufacturer_id = None,
        product_name = None,
        serial_number = None,
        configuration_string = None,
        interface_string = None,
        hs_device_descriptor = None,
        hs_config_descriptor = None,
        fs_device_descriptor = None,
        fs_config_descriptor = None,
        vid = 0x0424,
        pid = 0x9514,
        did = 0x0100,
        cfg1 = 0x9B,
        cfg2 = 0x18,
        cfg3 = 0x00,
        nrd = 0x02,
        pds = 0x00,
        pdb = 0x00,
        maxps = 0x01,
        maxpb = 0x00,
        hcmcs = 0x01,
        hcmcb = 0x00,
        pwrt = 0x32,
        boostup = 0x00,
        boost5 = 0x00,
        boost42 = 0x00,
        prtsp = 0x00,
        prtr12 = 0x21,
        prtr34 = 0x43,
        prtr5 = 0x05,
        stcd = 0x01):
        for k,v in locals().items():
            if k == 'self':
                continue
            setattr(self, k, v)
    
    def _init_from_bytes(self, data):
        def eat_bytes(len, ofs):
            if not len or not ofs:
                return None
            ofs = ofs * 2 # word offset!
            return data[ofs:ofs+len]
        def eat_string_descriptor(len, ofs):
            bs = eat_bytes(len, ofs)
            if not bs:
                return None
            assert bs[0] == len
            assert bs[1] == 0x03 # string descriptor
            return bs[2:].decode("utf_16_le")
        self.mac_address = data[1:7]
        self.fs_polling_interval = data[7]
        self.hs_polling_interval = data[8]
        self.configuration_flags = data[9]
        self.language_id = struct.unpack("<H", data[0xA:0xC])[0]
        self.manufacturer_id = eat_string_descriptor(data[0xC], data[0xD])
        self.product_name = eat_string_descriptor(data[0xE], data[0xF])
        self.serial_number = eat_string_descriptor(data[0x10], data[0x11])
        self.configuration_string = eat_string_descriptor(data[0x12], data[0x13])
        self.interface_string = eat_string_descriptor(data[0x14], data[0x15])
        self.hs_device_descriptor = eat_bytes(data[0x16], data[0x17])
        self.hs_config_descriptor = eat_bytes(data[0x18], data[0x19])
        self.fs_device_descriptor = eat_bytes(data[0x1A], data[0x1B])
        self.fs_config_descriptor = eat_bytes(data[0x1C], data[0x1D])
        self.vid = struct.unpack("<H", data[0x20:0x22])[0]
        self.pid = struct.unpack("<H", data[0x22:0x24])[0]
        self.did = struct.unpack("<H", data[0x24:0x26])[0]
        self.cfg1 = data[0x26]
        self.cfg2 = data[0x27]
        self.cfg3 = data[0x28]
        self.nrd = data[0x29]
        self.pds = data[0x2a]
        self.pdb = data[0x2b]
        self.maxps = data[0x2c]
        self.maxpb = data[0x2d]
        self.hcmcs = data[0x2e]
        self.hcmcb = data[0x2f]
        self.pwrt = data[0x30]
        self.boostup = data[0x31]
        self.boost5 = data[0x32]
        self.boost42 = data[0x33]
        self.prtsp = data[0x35]
        self.prtr12 = data[0x36]
        self.prtr34 = data[0x37]
        self.prtr5 = data[0x38]
        self.stcd = data[0x39]
        self.remaining_bytes = data[0x3A:]
    
    def encode(self):
        eeprom = b''
        extra = b''
        
        def put8(v):
            nonlocal eeprom
            eeprom += bytes([v])
        def put16le(v):
            nonlocal eeprom
            eeprom += struct.pack("<H", v)
        def putbytes(v):
            nonlocal extra
            if v == None:
                put8(0)
                put8(0)
                return
            ofs = (len(extra) + 0x3A) // 2
            l = len(v)
            extra += v
            if len(v) % 2:
                extra += b'\x00'
            put8(l)
            put8(ofs)
        def putstring(s):
            if s == None:
                put8(0)
                put8(0)
                return
            raw = s.encode("utf_16_le")
            putbytes(bytes([len(raw) + 2, 0x03]) + raw)
        
        put8(0xA5)
        eeprom += self.mac_address
        put8(self.fs_polling_interval)
        put8(self.hs_polling_interval)
        put8(self.configuration_flags)
        put16le(self.language_id)
        putstring(self.manufacturer_id)
        putstring(self.product_name)
        putstring(self.serial_number)
        putstring(self.configuration_string)
        putstring(self.interface_string)
        putbytes(self.hs_device_descriptor)
        putbytes(self.hs_config_descriptor)
        putbytes(self.fs_device_descriptor)
        putbytes(self.fs_config_descriptor)
        put8(0) # reserved
        put8(0)
        put16le(self.vid)
        put16le(self.pid)
        put16le(self.did)
        put8(self.cfg1)
        put8(self.cfg2)
        put8(self.cfg3)
        put8(self.nrd)
        put8(self.pds)
        put8(self.pdb)
        put8(self.maxps)
        put8(self.maxpb)
        put8(self.hcmcs)
        put8(self.hcmcb)
        put8(self.pwrt)
        put8(self.boostup)
        put8(self.boost5)
        put8(self.boost42)
        put8(0) # reserved
        put8(self.prtsp)
        put8(self.prtr12)
        put8(self.prtr34)
        put8(self.prtr5)
        put8(self.stcd)
        assert(len(eeprom) == 0x3A)
        eeprom += extra
        
        return eeprom
