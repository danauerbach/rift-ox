#!/usr/bin/env python3

import os
from pathlib import Path
import queue
import signal
import sys
import threading 
import time

import paho.mqtt.client as mqtt
import toml

import winch
import winch.winmon
import winch.wincmd
import ctd

import config


############
# MQTT clients: 1 sub, 1 pub
#

# WINCH_CTL_MSG_START = 'start'
# WINCH_CTL_MSG_STOP = 'stop'
# WINCH_CTL_MSG_FORWARD = 'forward'
# WINCH_CTL_MSG_REVERSE = 'reverse'
# WINCH_CTL_MSG_NONE = 'none'
# WINCH_CTL_MSG_LIST = {
#     WINCH_CTL_MSG_START,
#     WINCH_CTL_MSG_STOP,
#     WINCH_CTL_MSG_FORWARD,
#     WINCH_CTL_MSG_REVERSE,
#     WINCH_CTL_MSG_NONE
# }

# class Direction(Enum):
#     DIRECTION_NONE = 'NONE'
#     DIRECTION_UP = 'UP'
#     DIRECTION_DOWN = 'DOWN'


def interrupt_handler(signum, frame):

    quit_evt.set()
    wincmd_thr.join()
    winmon_thr.join()

    # do whatever...
    # time.sleep(1)
    sys.exit(0)



if __name__ == "__main__":

    cfg = config.read()
    if cfg == None:
        print(f'winmon: ERROR unable to read rift-ox.toml config file. Quitting.')
        sys.exit(1)

    quit_evt = threading.Event()

    signal.signal(signal.SIGINT, interrupt_handler)

    # cmd_q = queue.Queue()

    # command_t = winch.mqtt.winmon_subber('win-commands', msgbus.TOPIC_COMMANDS, 'localhost', 1883, data_q)
    # command_t.on_message
    # command_t.loop_start()

    # pubber = winch.mqtt.winmon_pubber('win-pubber', 'localhost', 1883)
    # pubber.loop_start()

    # queue so wincmd can tell winmon what state the winch is in
    winch_status_q: queue.Queue = queue.Queue()

    wincmd_thr = threading.Thread(target=winch.wincmd.wincmd_loop, args=(cfg, winch_status_q, quit_evt), name="wincmd")
    wincmd_thr.start()

    winmon_thr = threading.Thread(target=winch.winmon.winmon_loop, args=(cfg, winch_status_q, quit_evt), name="winmon")
    winmon_thr.start()

    quit_evt.wait()

    wincmd_thr.join()
    winmon_thr.join()
