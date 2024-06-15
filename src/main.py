#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, signal
import sys
import time
import datetime


import pprint

from pcf8574 import *

from p21_defs import *

import argparse


import logging

logger=logging.getLogger(__name__)
logger.setLevel("INFO")
hdlr = logging.StreamHandler()
hdlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)8s %(filename)20s:%(lineno)-5s %(message)s'))
logger.addHandler(hdlr)

import txop

def kill_siblings():

    # Ask user for the name of process
    name = "SM6FBQ/etc/startserver.sh"
    try:

        # iterating through each instance of the process
        for line in os.popen("ps -ef | grep " + name + " | grep -v grep"):
            fields = line.split()

            # extracting Process ID from the output
            pid = fields[1]
            ppid = fields[2]
            if int(pid) == os.getpid(): # Avoid suicide
                continue
            # if fields[-1].endswith("debugging"):
                # continue

            # terminating process
            while True:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    # os.kill(int(ppid), signal.SIGSTOP)
                    print("Sent kill signal to process %d" % int(pid))
                    time.sleep(1)
                except Exception as e:
                    print ("Process %s is now dead: %s" % (int(pid), e))
                    break

    except:
        print("Error Encountered while running script")



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""Eavesdrop on SoapySDRServer log to control transmit filter selection and control transmit preamplifier
        By default, the log is listened on UDP localhost on port 1235"""
    )
    parser.add_argument("--udp", help="Get control input from UDP instead of stdin", action="store_true")
    parser.add_argument("--tune", help="Tune everything manually", action="store_true")
    parser.add_argument("--debugging", help="Debug run, overthrow and kill normally running processes", action="store_true")
    parser.add_argument("--band_margins", help="Margins for band selection in Hz", action="store", default=5000000, type=int)
    # Note: band_attenuation list is for 50,432,144 and 1296 MHz in that order!!!
    parser.add_argument("--band_attenuation", help="Delimited list of Attenuations for 50,144,432 and 1296 Mhz", action="store", default='1,9,3,0', type=str)

    args = parser.parse_args()

    print(args.band_attenuation)

    if args.debugging:
        kill_siblings()

    txop = txop.TxOp(logger, args)

    try:
        if args.udp:
            txop.control_from_udp()
        elif args.tune:
            txop.tune_loop()
        else:
            txop.control_from_stdin()
    finally:
        txop.offair()
        pass
