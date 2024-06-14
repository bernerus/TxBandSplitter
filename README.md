# TxBandSplitter
SDR Transmit band splitter and amplifier for VHF/UHF bands. A KiCad + Python project.

The aim of this project is to create an intermediate transmit driver stage that 
takes the RF level of an SDR transmitter from around 1 dBm to around +30 dBm.
Doing this would probably be illegal except for licensed radio amateurs, but
such equipment should nevertheless work only on the amateur bands.
This device takes 1 dBm RF from e.g. a HackRF transceiver, splits the output on
either the 50, 144, 432 och 1295 MHz bands and takes the output level to about +30 dBm or 1 W.
The amplification is done in two steps with the filtering and a programmable attenuator in between,
The final RF is the again split on 4 outputs usein PIN diodes.

The band selection, amplifier power and level of attenuation is controlled over an I2C connection
suitable for connectiong to a RaspBerry PI computer.

Sample software for controlling the device from an RPI is written in Python.
