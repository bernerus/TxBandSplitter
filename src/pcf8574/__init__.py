from pcf8574 import PCF85
from typing import *
import time
from smbus2 import SMBus

LOW = "LOW"
HIGH = "HIGH"
INPUT = "INPUT"
OUTPUT = "OUTPUT"

default_pin_names = {"p0": 0,
                     "p1": 1,
                     "p2": 2,
                     "p3": 3,
                     "p4": 4,
                     "p5": 5,
                     "p6": 6,
                     "p7": 7,
                     }


class PCF:

    def __init__(self, logger, address, pin_names: Dict[str, Union[int , Tuple[int, str]]] = None, bus_number=1):

        self.logger = logger
        self.address = address
        self.status = True
        self.pin_mode_flags = 0x00
        self.sm_bus_number = bus_number
        self.pin_names = pin_names

        if pin_names is None:
            self.pin_names = default_pin_names
        else:
            self.pin_names = {}
            for k, v in pin_names.items():
                if type(v) is tuple:
                    self.pin_names[k] = v[0]
                    if v[1] in [INPUT, OUTPUT]:
                        self.pin_mode(k, v[1])
                else:
                    self.pin_names[k] = v
        self.bus = SMBus(self.sm_bus_number)
        time.sleep(1)
        PCF85.setup(address, self.bus, self.status)

    def pin_mode(self, pin_name, mode):
        self.pin_mode_flags = PCF85.pin_mode(self.logger, self.pin_names[pin_name], mode, self.pin_mode_flags)

    def bit_read(self, pin_name):
        return PCF85.bit_read(self.logger, self.pin_names[pin_name], self.bus, self.address)

    def byte_read(self, pin_mask):
        return PCF85.byte_read(self.logger, pin_mask, self.bus, self.address)

    def byte_write(self, pin_mask, value):
        return PCF85.byte_write(self.logger, pin_mask, self.bus, self.address, value & 0xff)

    def bit_write(self, pin_name, value):
        PCF85.bit_write(self.logger, self.pin_names[pin_name], value, self.address, self.pin_mode_flags, self.bus)