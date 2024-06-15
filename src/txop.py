
import re
import sys
import time

import OpenSSL.SSL

from pcf8574 import *

from p21_defs import *

import socket
import logging
UDP_IP = "127.0.0.1"
UDP_PORT = 1235
import socketio

import queue
msg_q = queue.Queue()
import threading
from threading import Lock
thread_lock = Lock()


def background_thread(sio):
    """Send server generated events to clients."""
    logging.info("Starting background thread")
    count = 0
    while True:
        count += 1
        if not msg_q.empty():
            what, item = msg_q.get_nowait()
            # print("Sending %s %d %s" % (what, count, item))
            sio.emit(what, item, namespace="/wsjtx")
        sio.sleep(1)

def emit(what, data):
    msg_q.put((what, data))

def start_socketio():
    global sio_thread
    sio = socketio.Client(logger=True, engineio_logger=False)
    sio.connect('http://192.168.1.126:8877', namespaces=["/wsjtx"])
    # with thread_lock:
    if sio_thread is None:
        sio_thread = threading.Thread(target=background_thread, args=(sio,), daemon=True)
        sio_thread.start()

    return sio

class TxOp:
    """ Handles T/R, band switching and transmit level for 4 VHF/UHF bands"""
    def try_init_p21(self):
        if not self.p21:
            try:
                self.p21 = PCF(self.logger, P21_I2C_ADDRESS, {P21_VC1: (0, OUTPUT),
                                                              P21_VC2: (1, OUTPUT),
                                                              P21_ATTEN_1: (2, OUTPUT),
                                                              P21_ATTEN_2: (3, OUTPUT),
                                                              P21_ATTEN_4: (4, OUTPUT),
                                                              P21_ATTEN_8: (5, OUTPUT),
                                                              P21_UNUSED_6: (6, INPUT),
                                                              P21_TXEN_L: (7, OUTPUT),
                                                              }, P21_BUS_NUMBER)
                self.p21.bit_write(P21_VC1, LOW)
                self.p21.bit_write(P21_VC1, HIGH)
                self.p21.bit_write(P21_VC1, LOW)
                self.p21.bit_write(P21_TXEN_L, HIGH)
                self.logger.info("Found I2C port %x" % P21_I2C_ADDRESS)
                test=self.p21_byte_read(0xFF)
                self.logger.debug("data on I2C port %x = %x" % (P21_I2C_ADDRESS, test))

                fail=False
                for x in range(0,256):
                    self.p21.byte_write(0xff, x)
                    ret = self.p21_byte_read(0xff)
                    if ret != x:
                        self.logger.error("P21 data %x read back as %x" % (x, ret))
                        fail=True
                    else:
                        pass
                        # self.logger.info("P21 data %x read back as %x" % (x, ret))
                if fail:
                    sys.exit(1)
                else:
                    self.logger.info("PCF8574 read back test succeeded")


            except OSError as e:
                self.logger.error("I2C port %x not found: %s" % (P21_I2C_ADDRESS, e))
                self.p21 = None
                self.disable_tx_controls()
        return self.p21


    def __init__(self,  logger, args):

        self.tx_controls = True
        self.logger = logger
        self.atten = None
        self.band_attenuation = []
        self.band_margins = [0,0,0,0]

        self.p21 = None
        self.p21 = self.try_init_p21()
        if not self.p21:
            self.logger.error("I2C port 21 not functional")
            sys.exit(1)
        self.last_status = 0xff
        if "band_attenuation" in args:
            try:
                self.band_attenuation = [int(x) for x in args.band_attenuation.split(',')]
            except AttributeError:
                self.band_attenuation = [int(x) for x in args["band_attenuation"].split(',')]

        if not self.band_attenuation:
            self.band_attenuation = [1,3,9,0] # DB Attenuation for linearity, Order: 50, 432, 144, 1296 MHz bands,

        if "band_margins" in args:
            try:
                self.band_margins = args.band_margins
            except AttributeError:
                self.band_margins = args["band_margins"]

        if not self.band_margins:
            self.band_margins = 0

        pass

    def disable_tx_controls(self):
        self.tx_controls=False

    def enable_tx_controls(self):
        self.tx_controls = True

    def p21_byte_read(self, xx):
        try:
            return self.p21.byte_read(xx)
        except IOError:
            self.p21 = None
            self.p21 = self.try_init_p21()
            return self.p21.byte_read(xx)

    def p21_bit_read(self, xx):
        try:
            return self.p21.bit_read(xx)
        except IOError:
            self.p21 = None
            self.p21 = self.try_init_p21()
            return self.p21.bit_read(xx)


    def get_status(self):
        self.try_init_p21()
        if not self.p21:
            return
        current_p21_sense = self.p21_byte_read(0xff)
        return current_p21_sense

    def bit_reverse(self, i, n):
        ret= int(format(i, '0%db' % n)[::-1], 2) >>4
        self.logger.info("Reversed %s is %s" % (format(i, '08b'), format(ret, '08b')))
        return ret

    def my_status(self):
        self.try_init_p21()
        if self.p21:
            transmitting = not self.p21_bit_read(P21_TXEN_L)
            band_6m = self.p21_byte_read(P21_VC_MASK) == P21_VC_50
            band_2m = self.p21_byte_read(P21_VC_MASK) == P21_VC_144
            band_70cm = self.p21_byte_read(P21_VC_MASK) == P21_VC_432
            band_23cm = self.p21_byte_read(P21_VC_MASK) == P21_VC_1296
            s = ""
            s += "Transmit power is on<br/>" if transmitting else "Transmit power is off.<br/>"
            s += "Band selected is "
            s += "6m " if band_6m else ""
            s += "2m " if band_2m else ""
            s += "70cm " if band_70cm else ""
            s += "23cm " if band_23cm else ""
            atten = 15^self.p21_byte_read(P21_ATTEN_MASK) << P21_ATTEN_SHIFT
            s += "Transmit attenuation = %d dB" % atten
        else:
            s = "Transmit control info is not available<br/>"
        return s

    def control_from_udp(self):
        sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
        sock.bind((UDP_IP, UDP_PORT))

        try:
            while (True):
                data, addr = sock.recvfrom(100)  # buffer size is 1024 bytes
                print("received message: %s" % data)
                if not data:
                    break

                for line in data.splitlines():
                    line = line.decode()
                    self.decode_and_control(line)
                    continue
        finally:
            self.offair()

    def control_from_stdin(self):
        try:
            for line in sys.stdin:
                    self.decode_and_control(line)
        finally:
            self.offair()

    def decode_and_control(self, line):
        print(line, flush=True)
        m = re.search(r"hackrf frequency to (\d+)", line)
        self.band_select = None
        start_tx = False
        if m:
            start_tx = True
            fq = int(m.group(1))
            if fq > 28000000 - self.band_margins and fq < 30000000 + self.band_margins:  # 6m
                self.band_select = P21_VC_50
            if fq > 50000000 - self.band_margins and fq < 52000000 + self.band_margins:  # 6m
                self.band_select = P21_VC_50
            elif fq > 144000000 - self.band_margins and fq < 146000000 + self.band_margins:  # 2m
                self.band_select = P21_VC_144
            elif fq > 432000000 - self.band_margins and fq < 438000000 + self.band_margins:  # 70cm
                self.band_select = P21_VC_432
            elif fq > 1240000000 - self.band_margins and fq < 1300000000 + self.band_margins:  # 23cm
                self.band_select = P21_VC_1296
            else:
                tart_tx = False

            self.logger.info("Band_select = %s" % self.band_select)

            self.onair = False

            if self.band_select is not None:
                self.p21.byte_write(0xFF, self.build_to_set(self.band_select))
            if start_tx:
                time.sleep(0.1)
                self.onair=True
                self.p21.byte_write(0xFF, self.build_to_set(self.band_select))
            return
        if re.search(r"Hackrf TX stopped", line):
            self.onair = 0
            self.logger.info("Power off TX")
        if self.band_select is not None:
            to_set = self.build_to_set(self.band_select)

            self.p21.byte_write(0xFF, to_set)
        else:
            self.offair()

    def build_to_set(self, band_select, atten = None):
        to_set = band_select
        self.logger.info("Band select To_set = %s" % format(to_set, '08b'))
        if atten is None:
            self.atten = self.band_attenuation[band_select]
        else:
            self.atten = atten

        atten_value = (0xFF ^ self.atten)

        self.logger.info("Atten_value 1=%d,  To_set = %s" % (atten_value, format(to_set, '08b')))
        atten_value = self.bit_reverse(atten_value, 4)  # Bits are reversed in hardware

        self.logger.info("Atten_value_2=%d,  To_set = %s" % (atten_value, format(to_set, '08b')))
        atten_value = (atten_value << P21_ATTEN_SHIFT) & P21_ATTEN_MASK

        self.logger.info("Atten_value_3=%d,  To_set = %s" % (atten_value, format(to_set, '08b')))
        to_set |= atten_value


        if not self.onair:
            to_set |= P21_TXEN_L
        else:
            to_set &= ~P21_TXEN_L
        self.logger.info("Setting band_select to=%d, atten=%d, to_set=%s" % (self.band_select, self.atten, format(to_set, '08b')))

        return to_set

    def offair(self):
        self.p21.byte_write(0xFF, 0xFF)  # Turn off transmitter, reset to 6m and no attenuation.


    def tune_loop(self):
        from sshkeyboard import listen_keyboard

        self.atten = 0
        self.band_select = P21_VC_50
        self.onair = 0
        self.logger.info("Use Right arrow to transmit, left to stop transmit")
        self.logger.info("Use up/down arrows to manipulate gain")
        self.logger.info("Selected 50 MHz band")
        self.logger.info("Starting with maximum gain")

        def on_release(key):
            pass


        def on_press(c):
            try:
                if c == '6':
                    self.band_select = P21_VC_50
                    self.logger.info("Selected 50 MHz band")
                elif c == '2':
                    self.band_select = P21_VC_144
                    self.logger.info("Selected 144 MHz band")
                elif c == '7':
                    self.band_select = P21_VC_432
                    self.logger.info("Selected 432 MHz band")
                elif c == '3':
                    self.band_select = P21_VC_1296
                    self.logger.info("Selected 1296 MHz band")
                elif c == "up":  # Up arrow
                    self.atten -= 1
                    if self.atten < 0:
                        self.atten = 0
                    self.logger.info("Gain lowered by %d dB" % self.atten)
                elif c == "down":  # Down arrow
                    self.atten += 1
                    if self.atten > 15:
                        self.atten = 15
                    self.logger.info("Gain lowered by %d dB" % self.atten)

                elif c == "left":  # Left arrow
                    self.onair = 0
                    self.logger.info("Off Air")

                elif c == "right":  # Right arrow
                    self.onair = 1
                    self.logger.info("On Air")

                else:
                    self.logger.warning("Undefined key %s" % c)
                    return

                to_set = self.build_to_set(self.band_select, atten=self.atten)
                self.p21.byte_write(0xFF, to_set)

            except AttributeError as e:
                self.logger.warning('special key {0} pressed'.format(c))
                self.logger.warning('Attribute error %s' % e)
        try:
            listen_keyboard(
                on_press=on_press,
                on_release=on_release,
            )

        finally:
            self.offair()
