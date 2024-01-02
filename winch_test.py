#!/usr/bin/env python3

import argparse
import sys
import signal
import config

from winch.dio_cmds import DIOCommander

def interrupt_handler(signum, frame):

    # quit_evt.set()

    # time.sleep(1)
    sys.exit(0)

def main():

    signal.signal(signal.SIGINT, interrupt_handler)

    parser = argparse.ArgumentParser()

    parser.add_argument("--to-winch", help="Send commands to RIFT-OX Winch",  
                        type=bool, default=False)
    args = parser.parse_args()

    sim = args.simulation

    cfg = config.read()
    if cfg == None:
        print(f'ctdmon: ERROR unable to read rift-ox.toml config file. Quitting.')
        sys.exit(1)

    cmndr = DIOCommander(cfg, sim)
    VALID_CMDS = ["down", "up", "stop", "pedgecnt", "ledgecnt", "lrelease", "lhold", "quit"]

    done: bool = False
    while not done:

        cmd = input(f'Enter Winch Command {VALID_CMDS}: ')

        if cmd not in VALID_CMDS:
            print(f'{cmd} is not a valid command.')
            print(f'Valid commands: {VALID_CMDS}\n')

        if cmd == "down":
            cmndr.down_cast()
        elif cmd =="up":
            cmndr.up_cast()
        elif cmd =="stop":
            cmndr.stop_winch()
        elif cmd =="pedgecnt":
            payouts = cmndr.get_payout_edge_count()
            print(f'    PAYOUT SENSOR EDGE COUNTS: {payouts}\n')
        elif cmd =="ledgecnt":
            latchcnt = cmndr.get_latch_edge_count()
            print(f'    LATCH SENSOR EDGE COUNT: {latchcnt}\n')
        elif cmd =="lrelease":
            cmndr.latch_release()
        elif cmd =="lhold":
            cmndr.latch_hold()
        elif cmd == "quit":
            done = True



if __name__ == '__main__':
    main()

