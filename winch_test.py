#!/usr/bin/env python3

import argparse
import sys
import signal
import time
import config

from winch.dio_cmds import DIOCommander

def interrupt_handler(signum, frame):

    # quit_evt.set()

    # time.sleep(1)
    sys.exit(0)

def main() -> None:

    signal.signal(signal.SIGINT, interrupt_handler)

    parser = argparse.ArgumentParser()

    parser.add_argument("--to-winch", help="Send commands to RIFT-OX Winch", action="store_true")
    parser.add_argument("--exercise-pin", type=str, 
                        help="cycle specified pin low/high three times",
                        choices=["stop", "up", "down", "latch", "none"], default="none")
    
    parser.add_argument("--stop-hi", help="set STOP pin HIGH at start of exercising pin", action="store_true")
    parser.add_argument("--up-hi", help="set UP pin HIGH at start of exercising pin", action="store_true")
    parser.add_argument("--down-hi", help="set DOWN pin HIGH at start of exercising pin", action="store_true")
    parser.add_argument("--latch-hi", help="set LATCH pin HIGH at start of exercising pin", action="store_true")

    args = parser.parse_args()

    sim = not args.to_winch
    expin = args.exercise_pin
    stophi = args.stop_hi
    uphi = args.up_hi
    downhi = args.down_hi
    latchhi = args.latch_hi


    cfg = config.read()
    if cfg == None:
        print(f'ctdmon: ERROR unable to read rift-ox.toml config file. Quitting.')
        sys.exit(1)

    cmndr = DIOCommander(cfg, sim)

    if expin != "none":

        if stophi:
            cmndr.pin_hi("stop")
        else:
            cmndr.pin_low("stop")
        if uphi:
            cmndr.pin_hi("up")
        else:
            cmndr.pin_low("up")
        if downhi:
            cmndr.pin_hi("down")
        else:
            cmndr.pin_low("down")
        if latchhi:
            cmndr.pin_hi("latch")
        else:
            cmndr.pin_low("latch")

        ndx = 0
        while ndx < 3:
            cmndr.pin_low(expin)
            time.sleep(3)
            cmndr.pin_hi(expin)
            time.sleep(3)
            ndx += 1

        return

    else:
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

