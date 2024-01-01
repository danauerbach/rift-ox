#!/usr/bin/env python3

import queue
import time
import sys
from threading import Thread, Event
import signal
import config

from winch import pausemon

def interrupt_handler(signum, frame):

    quit_evt.set()

    time.sleep(1)
    sys.exit(0)

def main(quit_evt: Event):


    signal.signal(signal.SIGINT, interrupt_handler)

    cfg = config.read()
    if cfg == None:
        print(f'ctdmon: ERROR unable to read rift-ox.toml config file. Quitting.')
        sys.exit(1)

    pthr = Thread(target=pausemon.pause_monitor, args=(cfg, quit_evt))
    pthr.start()
    
    pthr.join()
        
if __name__ == '__main__':
    print("HELLO FROM PAUSEMON")
    quit_evt = Event()
    main(quit_evt)

