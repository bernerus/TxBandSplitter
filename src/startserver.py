#!/usr/bin/python3

import subprocess
import argparse
import os
import signal
import sys
import time

pids_stopped = []

def kill_siblings():

    # Ask user for the name of process
    names = ["/usr/local/bin/SoapySDRServer",
             "/home/bernerus/proj/SDRTxControl/startserver.py",
             "/bin/sh -c /usr/local/bin/SoapySDRServer",
    ]

    try:
        for name in names:
            # iterating through each instance of the process
            for line in os.popen("ps -ef | grep " + name + " | grep -v grep"):
                fields = line.split()

                # extracting Process ID from the output
                pid = int(fields[1])
                ppid = fields[2]
                if int(pid) == os.getpid():  # Avoid suicide
                    continue
                # if fields[-1].endswith("debugging"):
                # continue

                # terminating process
                while True:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        # os.kill(int(ppid), signal.SIGSTOP)
                        print("Sent kill signal to process %d" % pid)
                        time.sleep(1)
                    except Exception as e:
                        print("Process %s is now dead: %s" % (pid, e))
                        pids_stopped.append(pid)
                        break

    except:
        print("Error Encountered while running script")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""Start the SoapySDRserver, log its stdout to log/SoapyServer.log and also start SDRTxControl listening to the same output."""
    )
    parser.add_argument("--udp", help="Get SDRTxControl input from UDP instead of stdin", action="store_true")
    parser.add_argument("--debugging", help="Debug run, overthrow and kill normally running processes", action="store_true")
    parser.add_argument("--band_margins", help="Margins for band selection in Hz", action="store", default=5000000, type=int)
    # Note: band_attenuation list is for 50,432,144 and 1296 MHz in that order!!!
    parser.add_argument("--band_attenuation", help="Attenuation list for 50,144,432 and 1296 Mhz", action="store", default='1,9,3,0', type=str)

    args = parser.parse_args()

    txcontrol_args = ""
    if args.debugging:
        txcontrol_args += " --debugging"
    if args.band_margins:
        txcontrol_args += " --band_margins=%d" % args.band_margins
    if args.band_attenuation:
        txcontrol_args += " --band_attenuation=%s" % args.band_attenuation

    os.chdir("/home/bernerus/SM6FBQ")
    if args.debugging:
        try:
            kill_siblings()
            subprocess.check_call("/usr/local/bin/SoapySDRServer --bind=0.0.0.0:1234  2>&1 | tee log/SoapyServer.log | ~/proj/SDRTxControl/main.py %s >> log/SDRTxControl.log  " % txcontrol_args
                , shell=True, bufsize=0)

        except KeyboardInterrupt:

            for line in os.popen("ps -ef | grep 'sleep 600' | grep -v grep "):
                fields = line.split()
                # extracting Process ID from the output
                pid = int(fields[1])
                subprocess.Popen("sh -c 'kill -15 %d >/tmp/killout 2>&1' & " % pid, shell=True, close_fds=True)
                print("Killing sleep process %d" % pid)
                #time.sleep(600)
                #print("Killied sleep process %d" % pid)

        finally:
                pass
    else:
            subprocess.run("/usr/local/bin/SoapySDRServer --bind=0.0.0.0:1234  2>&1 | tee log/SoapyServer.log | ~/proj/SDRTxControl/main.py %s >> log/SDRTxControl.log 2>&1" % txcontrol_args
                       , shell=True, bufsize=0)
