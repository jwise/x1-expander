import pexpect
from pexpect import fdpexpect
import socket
import logging

logger = logging.getLogger(__name__)

class Monitor:
    @staticmethod
    def ABOVE(n):
        return ('>', n)
    
    @staticmethod
    def BELOW(n):
        return ('<', n)
    
    @staticmethod
    def EQUAL(n):
        return ('=', n)

    NONE = None
    
    TRIG_NONE = 0
    TRIG_OUTOFF = 1
    TRIG_ALARM = 2
    TRIG_BEEPER = 4

class Sequence:
    END_OFF = 'OFF'
    END_LAST = 'LAST'

    # cycles can be True, or 0-n
    # each group is a tuple (voltage, current, time)
    def __init__(self, groups, start = 0, cycles = True, end = END_OFF):
        self.groups = groups
        self.start = start
        self.cycles = cycles
        self.end = end

class Channel:
    def __init__(self, gpp, n):
        self.gpp = gpp
        self.n = n
    
    def meas(self):
        return self.gpp.meas()[self.n]
    
    def disable(self):
        self.gpp.sendline(f":OUTP{self.n}:STAT OFF")
        self.gpp.wait()
    
    def enable(self):
        self.gpp.sendline(f":OUTP{self.n}:STAT ON")
        self.gpp.wait()
    
    # TODO: OVP/OCP

    def source(self, voltage, current):
        self.gpp.sendline("TRACK0")
        if self.n == 1 or self.n == 2:
            self.gpp.sendline(f":LOAD{self.n}:CC OFF")
        self.gpp.sendline(f":SOUR{self.n}:CURR {current}")
        self.gpp.sendline(f":SOUR{self.n}:VOLT {voltage}")
        self.gpp.wait()
        if self.n == 1 or self.n == 2:
            self.gpp.sendline(f":MODE{self.n}?")
            rv = self.gpp.expect(r'(\S+)\s*\n')
            if rv.group(1) != b'IND':
                raise RuntimeError('supply failed to switch to source mode')
    
    def load(self, cv = None, cc = None, cr = None):
        if (not cv and not cc and not cr) or (cv and cc) or (cv and cr) or (cc and cr):
            raise ValueError('supply can track only one of CV / CC / CR mode at a time')
        if cv:
            mode = 'CV'
            self.gpp.sendline(f":SOUR{self.n}:VOLT {cv}")
            self.gpp.sendline(f":LOAD{self.n}:CV on")
        elif cc:
            mode = 'CC'
            self.gpp.sendline(f":SOUR{self.n}:CURR {cc}")
            self.gpp.sendline(f":LOAD{self.n}:CC on")
        elif cr:
            mode = 'CR'
            self.gpp.sendline(f":LOAD{self.n}:RES {cr}")
            self.gpp.sendline(f":LOAD{self.n}:CR on")
        self.gpp.wait()
        self.gpp.sendline(f":MODE{self.n}?")
        rv = self.gpp.expect(r'(\S+)\s*\n')
        if rv.group(1) != mode.encode():
            raise RuntimeError(f'supply failed to switch to {mode} mode')
    
    def is_load(self):
        self.gpp.sendline(f":MODE{self.n}?")
        rv = self.gpp.expect(r'(\S+)\s*\n')
        return rv.group(1) == b'CV' or rv.group(1) == b'CC' or rv.group(1) == b'CR'
    
    def monitor(self, current = Monitor.NONE, voltage = Monitor.NONE, power = Monitor.NONE, trigger = 0):
        self.gpp.sendline(f":MONI{self.n}:STAT OFF")

        # set, then clear all -- at least one must be set at all times,
        # apparently

        if current:
            self.gpp.sendline(f":MONI{self.n}:CURR:COND {current[0]}C,AND")
            self.gpp.sendline(f":MONI{self.n}:CURR:VAL {current[1]}")
        if voltage:
            self.gpp.sendline(f":MONI{self.n}:VOLT:COND {voltage[0]}V,AND")
            self.gpp.sendline(f":MONI{self.n}:VOLT:VAL {voltage[1]}")
        if power:
            self.gpp.sendline(f":MONI{self.n}:POWER:COND {power[0]}P")
            self.gpp.sendline(f":MONI{self.n}:POWER:VAL {power[1]}")

        if not current:
            self.gpp.sendline(f":MONI{self.n}:CURR:COND NONE,NONE")
        if not voltage:
            self.gpp.sendline(f":MONI{self.n}:VOLT:COND NONE,NONE")
        if not power:
            self.gpp.sendline(f":MONI{self.n}:POWER:COND NONE")

        # set, then clear all -- at least one must be set at all times,
        # apparently
        self.gpp.sendline(f":MONI{self.n}:STOP BEEPER,ON")
        self.gpp.sendline(f":MONI{self.n}:STOP OUTOFF,{'ON' if trigger & Monitor.TRIG_OUTOFF else 'OFF'}")
        self.gpp.sendline(f":MONI{self.n}:STOP ALARM,{'ON' if trigger & Monitor.TRIG_ALARM  else 'OFF'}")
        self.gpp.sendline(f":MONI{self.n}:STOP BEEPER,{'ON' if trigger & Monitor.TRIG_BEEPER else 'OFF'}")
        self.gpp.wait()
        if trigger and (current or voltage or power):
            self.gpp.sendline(f":MONI{self.n}:STAT ON")
        self.gpp.wait()
        
        # back to the home screen
        self.gpp.sendline(f':DISP:TYPE 1')
    
    def sequence(self, seq, active = True):
        self.gpp.sendline(f':SEQU{self.n}:STAT OFF')
        self.gpp.sendline(f':SEQU{self.n}:GROUP {len(seq.groups)}')
        for n,grp in enumerate(seq.groups):
            self.gpp.sendline(f':SEQU{self.n}:PARA {n},{grp[0]},{grp[1]},{grp[2]}')
        self.gpp.sendline(f':SEQU{self.n}:STAR {seq.start}')
        if seq.cycles == True:
            self.gpp.sendline(f':SEQU{self.n}:CYCLE I')
        else:
            self.gpp.sendline(f':SEQU{self.n}:CYCLE N,{seq.cycles}')
        self.gpp.sendline(f':SEQU{self.n}:ENDS {seq.end}')
        self.gpp.wait()
        if active:
            self.gpp.sendline(f':SEQU{self.n}:STAT ON')
            self.gpp.wait()

        # back to the home screen
        self.gpp.sendline(f':DISP:TYPE 1')
    
    def sequence_enable(self, active = True):
        self.gpp.sendline(f':SEQU{self.n}:STAT {"ON" if active else "OFF"}')

class Reading:
    def __init__(self, v, i, p, ch):
        self.voltage = v
        self.current = i
        self.power = p
        self.channel = ch
    
    def __repr__(self):
        return f"[Ch#{self.channel}: {self.voltage}V, {self.current}A, {self.power}W]"
    
    def _asdict(self):
        return { "voltage": self.voltage, "current": self.current, "power": self.power, "channel": self.channel }

class GPP4323:
    def __init__(self, host):
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.skt.connect((host, 1026))
        self.sess = fdpexpect.fdspawn(self.skt, timeout = 10)
        
        self.sess.sendline('*IDN?')
        rv = self.sess.expect('([^,]*),([^,]*),SN:([^,]*),([^,]*)\n')
        self.manufacturer = self.sess.match.group(1).decode()
        self.model = self.sess.match.group(2).decode()
        self.serial = self.sess.match.group(3).decode()
        self.version = self.sess.match.group(4).decode()
        self.sess.sendline('*CLS')
        self.sess.sendline(':SYST:CLE')
        self.sess.sendline(':STAT:QUE:ENAB (-440:+900)')
        
        logger.info(f"Connected to {self.manufacturer} {self.model}, serial number {self.serial}, FW version {self.version}")
        
        # read the error queue: :STAT:QUE?
    
    def __del__(self):
        logger.info(f"disconnecting from SN{self.serial}")
        self.skt.shutdown(socket.SHUT_RDWR)
        self.skt.close()
    
    def wait(self):
        self.sess.sendline("*OPC")
        tries = 5
        while tries > 0:
            self.sess.sendline("*ESR?")
            self.sess.expect(r'(\d+)\s*\n')
            val = int(self.sess.match.group(1))
            if val & 128:
                logger.warning(f"NOTE: SN{self.serial} reports power cycle")
            if val & 32:
                raise RuntimeError('command syntax error from supply')
            if val & 16:
                raise RuntimeError('execution error from supply')
            if val & 8:
                raise RuntimeError('device error from supply')
            if val & 4:
                logger.warning(f"NOTE: SN{self.serial} reports query error")
            if val & 1:
                break
            tries -= 1
        if tries == 0:
            raise RuntimeError('supply never became ready')

    def channel(self, n):
        return Channel(self, n)

    def expect(self, s):
        self.sess.expect(s)
        return self.sess.match
    
    def sendline(self, s):
        self.sess.sendline(s)
    
    def meas(self):
        self.sendline(":MEAS?")
        rv = self.expect(r'([0-9.,;]+)\s*\n')
        chs = [ch.split(b',') for ch in rv.group(1).split(b';')]
        chs = {chn+1: Reading(float(ch[0]), float(ch[1]), float(ch[2]), chn+1) for chn,ch in enumerate(chs)}
        return chs

