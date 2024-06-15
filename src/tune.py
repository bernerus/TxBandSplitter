#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, signal
import sys
import time
import datetime


import pprint

from pcf8574 import *

from p21_defs import *


import logging

logger=logging.getLogger(__name__)
logger.setLevel("INFO")
hdlr = logging.StreamHandler()
hdlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)8s %(filename)20s:%(lineno)-5s %(message)s'))
logger.addHandler(hdlr)


import txop


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press ⇧⌘B to toggle the breakpoint.

def main():
    pass

args = {
    "band_attenuation": '0,0,0,0'
}

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    try:
        # socket_io.run(app, host='0.0.0.0', port=8877, log_output=False, debug=False)
        txop = txop.TxOp(logger, args)
        txop.tune_loop()
    finally:
        # app.azel.az_stop()
        pass
