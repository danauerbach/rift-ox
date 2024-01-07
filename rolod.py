#!/usr/bin/env python3

import signal
import sys
import time
import busio
from digitalio import DigitalInOut
import board
# Import the SSD1306 module.
import adafruit_ssd1306
# Import the RFM9x radio module.
import adafruit_rfm9x


def main():

    def interrupt_handler(signum, frame):

        sys.exit(0)

    signal.signal(signal.SIGINT, interrupt_handler)


    # Create the I2C interface.
    i2c = busio.I2C(board.SCL, board.SDA)

    # 128x32 OLED Display
    reset_pin = DigitalInOut(board.D4)
    display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)
    # Clear the display.
    display.fill(0)
    display.show()
    width = display.width
    height = display.height

    # Configure RFM9x LoRa Radio
    CS = DigitalInOut(board.CE1)
    RESET = DigitalInOut(board.D25)
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

    while True:

        # Clear the image
        display.fill(0)

        # Attempt to set up the RFM9x Module
        try:
            rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0)
            print('RFM9x: Detected')
        except RuntimeError as error:
            # Thrown on version mismatch
            print(f'RFM9x Error: {error}. Quitting.')
            sys.exit(1)

        # check for a packet
        packet = rfm9x.receive(timeout=0.5, with_ack=True)

        if packet is None:
        # Packet has not been received
            display.text('Nothing rcvd', 0, height-10, 1)
        else:
            packet_str = packet.decode()
            print(f'rcvd: {packet_str}')
            display.text(f'rcvd: {packet_str}', 0, height-20, 1)

            #TODO: SEND COMMAND TO MQTT CMD Topic

        display.show()

        time.sleep(0.1)
