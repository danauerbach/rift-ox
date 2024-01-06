#!/usr/bin/env python3

import argparse
import signal
import sys
import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import the SSD1306 module.
import adafruit_ssd1306
# Import the RFM9x radio module.
import adafruit_rfm9x

from winch import WinchCmd
CMD_QUIT = "QUIT"


def interrupt_handler(signum, frame):

    sys.exit(0)


def main():

    signal.signal(signal.SIGINT, interrupt_handler)

    parser = argparse.ArgumentParser()

    parser.add_argument("command", help="Send command to RIFT-OX over LoRa radio (case insensitive)", 
                        choices=["goscience", "quit", "kill33", "pause"])
    
    args = parser.parse_args()

    cmd: str = args.command.upper()
    

    # Button A
    btnA = DigitalInOut(board.D5)
    btnA.direction = Direction.INPUT
    btnA.pull = Pull.UP

    # Button B
    btnB = DigitalInOut(board.D6)
    btnB.direction = Direction.INPUT
    btnB.pull = Pull.UP

    # Button C
    btnC = DigitalInOut(board.D12)
    btnC.direction = Direction.INPUT
    btnC.pull = Pull.UP

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

    # Clear the image
    display.fill(0)

    # Attempt to set up the RFM9x Module
    rfm9x: adafruit_rfm9x.RFM9x
    try_cnt = 0
    while True:
        # Clear the image
        display.fill(0)

        # Attempt to set up the RFM9x Module
        try:
            rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0)
            display.text('RFM9x: Detected', 0, 0, 1)
        except RuntimeError as error:
            # Thrown on version mismatch
            display.text('RFM9x: ERROR', 0, 0, 1)
            print('RFM9x Error: ', error)
            if try_cnt <= 5:
                print('trying again in 5 secs...')
                time.sleep(5)
                pass
            else:
                print('Too many RFM9x initialization errors. Quitting.')
                sys.exit(1)
        
        cmd:str = ''
        while cmd != CMD_QUIT:
            cmd_conf = input(f'Confirm Coammnd: ')
            cmd_conf = cmd_conf.upper()

            if cmd_conf == cmd:
                if cmd == CMD_QUIT:
                    break
                display.fill(0)
                display.text(f'cmd: {cmd}', 0, 0, 1)

                rfm9x.send(f'CMD: {cmd}'.encode())
                print(f'Command sent: {cmd}')

            else:
                print(f'COMMAND CONFIRMATION FAILED ==> "{cmd_conf}" != "{cmd}"')                
                print('Please try again...')
        break

    sys.exit(0)


    # Check buttons
    if not btnA.value:
        # Button A Pressed
        display.text('Ada', width-85, height-7, 1)
        display.show()
        rfm9x.send(bytes("Button A Pressed", "utf-8"))
        time.sleep(0.1)
    if not btnB.value:
        # Button B Pressed
        display.text('Fruit', width-75, height-7, 1)
        display.show()
        time.sleep(0.1)
    if not btnC.value:
        # Button C Pressed
        display.text('Radio', width-65, height-7, 1)
        display.show()
        time.sleep(0.1)

    display.show()
    # time.sleep(0.1)

if __name__ == "__main__":
    
    main()
    
