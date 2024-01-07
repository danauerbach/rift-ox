#!/usr/bin/env python3

import signal
import sys
# import time
from typing import Tuple

import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import the SSD1306 module.
import adafruit_ssd1306
# Import the RFM9x radio module.
import adafruit_rfm9x

# from winch import WinchCmd
from lora import IO_MODE, RIFTOX_CMDS, LORA_MODE_CMDS

CMD_QUIT = "QUIT"

def setup_buttons():

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

    return btnA, btnB, btnC

def main():

    def interrupt_handler(signum, frame):

        sys.exit(0)

    signal.signal(signal.SIGINT, interrupt_handler)

    btnA, btnB, btnC = setup_buttons()

    # Create the I2C interface.
    i2c = busio.I2C(board.SCL, board.SDA)

    # 128x32 OLED Display
    reset_pin = DigitalInOut(board.D4)
    display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)
    
    # Clear the display and get OLED dims
    display.fill(0)
    display.show()
    width = display.width
    height = display.height

    # Configure RFM9x LoRa Radio
    CS = DigitalInOut(board.CE1)
    RESET = DigitalInOut(board.D25)
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

    rfm9x: adafruit_rfm9x.RFM9x
    current_mode: IO_MODE = IO_MODE.SEND
    cmd: str = ''
    cmd_conf: str =''

    while True:
        
        display.fill(0)
        display.text(f'Mode: {current_mode.value}', 0, 0, 1)

        # Attempt to set up the RFM9x Module
        try:
            rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0)
            # display.text('RFM9x: Detected', 0, 0, 1)
            # print('RFM9x: Detected')
        except RuntimeError as error:
            # Thrown on version mismatch
            # display.text('RFM9x: ERROR', 0, 0, 1)
            print(f'RFM9x Error: {error}. Quitting.')
            sys.exit(1)

        if current_mode == IO_MODE.SEND:

            cmd = input(f'Enter   Command: ')
            cmd = cmd.upper()
            if cmd == CMD_QUIT:
                break

            if cmd not in RIFTOX_CMDS + LORA_MODE_CMDS:
                print(f'INVALID COMMAND: {cmd}')
                cmd_list: str = ' '.join(RIFTOX_CMDS+LORA_MODE_CMDS)
                print(f'Must be one of: "{cmd_list}"')
                continue

            cmd_conf = input(f'Confirm Command: ')
            cmd_conf = cmd_conf.upper()

            if cmd_conf == cmd:

                if cmd in RIFTOX_CMDS:
                    
                    if rfm9x.send_with_ack(f'{cmd}'.encode()):
                        print(f"sent & ack'd: {cmd}")

                        display.text(f"sent & ack'd: {cmd}", 0, 12, 1)
                    else:
                        display.text(f"ERROR SENDING: {cmd}", 0, 12, 1)

                elif cmd == IO_MODE.SEND.value:

                    current_mode = IO_MODE.SEND

                elif cmd == IO_MODE.RECEIVE.value:

                    current_mode = IO_MODE.RECEIVE


            else:
                print(f'COMMAND CONFIRMATION FAILED ==> "{cmd_conf}" != "{cmd}"')                
                print('Please try again...\n')
                    
        elif current_mode == IO_MODE.RECEIVE:

            # check for a packet
            packet = rfm9x.receive(timeout=1.0, with_ack=True)

            if packet is None:
            # Packet has not been received
                display.text('Nothing rcvd', 0, height-10, 1)
            else:
                packet_str = packet.decode()
                print(f'rcvd: {packet_str}')
                display.text(f'rcvd: {packet_str}', 0, height-20, 1)

        # Check buttons
        if not btnA.value:
            # Button A Pressed
            current_mode = IO_MODE.SEND
        if not btnB.value:
            # Button B Pressed
            pass
        if not btnC.value:
            # Button C Pressed
            current_mode = IO_MODE.RECEIVE

        display.show()


if __name__ == "__main__":
    
    main()
    
