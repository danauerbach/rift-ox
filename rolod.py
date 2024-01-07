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

import paho.mqtt.client as mqtt

import config
from lora import RIFTOX_CMDS
from winch import pub_winch_cmd


def _on_connect(client, userdata, flags, rc):
    if rc==0:
        print("winctl:winmon: connected OK: {client}")
    else:
        print("winctl:winmon: Bad connection for {client} Returned code: ", rc)
        client.loop_stop()

def _on_disconnect(client, userdata, rc):
    print("winctl:winmon: client disconnected ok")


def main():

    def interrupt_handler(signum, frame):

        sys.exit(0)

    signal.signal(signal.SIGINT, interrupt_handler)

    cfg = config.read()
    if cfg == None:
        print(f'winmon: ERROR unable to read rift-ox.toml config file. Quitting.')
        sys.exit(1)

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

    # set up mqtt pubber

    cmd_t = cfg['mqtt']['WINCH_CMD_TOPIC']
    mqtt_host = cfg['mqtt']['REMOTE_HOST']
    mqtt_port = cfg['mqtt']['PORT']
    cmd_pubber = mqtt.Client('rolod-cmd-pub')
    cmd_pubber.on_connect = _on_connect
    cmd_pubber.on_disconnect = _on_disconnect
    try:
        res = cmd_pubber.connect(mqtt_host, mqtt_port)
    except OSError as e:
        print(f'OSError connecting to mqqt host {mqtt_host}: {e}')
        print(f'pubber connected?: {cmd_pubber.is_connected()}')


    cmd_pubber.loop_start()

    while True:

        # Clear the image
        display.fill(0)

        # Attempt to set up the RFM9x Module
        try:
            rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0)
            # print('RFM9x: Detected')
        except RuntimeError as error:
            # Thrown on version mismatch
            print(f'RFM9x Error: {error}. Quitting.')
            sys.exit(1)

        # check for a packet
        packet = rfm9x.receive(timeout=1.0, with_ack=True)

        if packet is None:
        # Packet has not been received
            display.text('Nothing rcvd', 0, height-20, 1)
        else:
            packet_str = packet.decode()
            print(f'rcvd: {packet_str}')
            display.text(f'rcvd: {packet_str}', 0, height-20, 1)

            # publish cmd to mqtt winch cmd topic
            if packet_str in RIFTOX_CMDS:
                if not cmd_pubber.is_connected():
                    print("Can't send command, cmd_pubber not connected")
                    display.text(f"cmd_pubber not conn'd", 0, height-10, 1)
                else:
                    if pub_winch_cmd(cmd_pubber, cmd_t, packet_str):
                        print(f"CMD PUB'D: {packet_str}")
                        display.text(f"CMD PUB'D: {packet_str}", 0, height-10, 1)
                    else:
                        print(f"ERR PUBBING CMD: {packet_str}")
                        display.text(f"ERR PUBBING CMD: {packet_str}", 0, height-10, 1)
            else:
                print(f"INV CMD: {packet_str}")
                display.text(f"INV CMD: {packet_str}", 0, height-10, 1)

        display.show()


if __name__ == "__main__":
    
    main()
    
