#!/usr/bin/env python3

import os
from pathlib import Path
import queue
import signal
import sys
import threading 
# import time

# import paho.mqtt.client as mqtt
# import toml

import winch.pausemon
import winch.winmon
import winch.wincmd
import inverter.invmon

import config


def interrupt_handler(signum, frame):

    quit_evt.set()
    wincmd_thr.join()
    winmon_thr.join()
    pause_thr.join()

    # do whatever...
    # time.sleep(1)
    sys.exit(0)



if __name__ == "__main__":
    
    signal.signal(signal.SIGINT, interrupt_handler)

    cfg = config.read()
    if cfg == None:
        print(f'winmon: ERROR unable to read rift-ox.toml config file. Quitting.')
        sys.exit(1)

    quit_evt = threading.Event()

    # inv_cmd_q: queue.Queue = queue.Queue()
    # invertermon_thr = threading.Thread(target=inverter.invmon.inverter_monitor, args=(cfg, inv_cmd_q, quit_evt), name="invmon")
    # invertermon_thr.start()
    
    pause_thr = threading.Thread(target=winch.pausemon.pause_monitor, args=(cfg, quit_evt), name="pausemon")
    pause_thr.start()
    
    # queue so wincmd can tell winmon what state the winch is in
    winch_status_q: queue.Queue = queue.Queue()

    wincmd_thr = threading.Thread(target=winch.wincmd.wincmd_loop, args=(cfg, winch_status_q, quit_evt), name="wincmd")
    wincmd_thr.start()

    winmon_thr = threading.Thread(target=winch.winmon.winmon_loop, args=(cfg, winch_status_q, quit_evt), name="winmon")
    winmon_thr.start()

    # wait for a interrupt handler or another thread to set() the quit_evt
    quit_evt.wait()

    # gives threads a chance to exit cleanly    
    winmon_thr.join()
    wincmd_thr.join()
    pause_thr.join()
    # invertermon_thr.join()
