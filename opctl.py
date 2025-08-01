#!/usr/bin/env python3

import cmd
import serial
import signal
import sys
import time

import config
from winch.dio_cmds import DIOCommander
from winch.winch import Winch


class DIOShell(cmd.Cmd):

    DIO_CMDS = ['set', 'get', 'mode', 'edge']
    RIFT_OX_CMNDS = ['upcast', 'downcast', 'stop', 'unlock', 'lock', 'park', 'unpark', 'quit']

    HELP_TEXT = """\n
dio set  D{ I | O }_G<group-num>  <pin_num>  { active | inactive }   (Set pin to active/high or inactive/low)
dio get  D{ I | O }_G<group-num>  output  <pin_num>                  (Get state of a pin)
dio mode DO_G<group-num>  { source | open-drain }                    (Set output group to source or open-drain (sink) current)
dio mode DO_G<group-num>                                             (Get output mode for a digital output group)
dio edge DI_G<group-num>  <pin-num>                                  (Get the number of edges detected by a digital input)

where:
   <group-num>: 0-3
   <pin-num>:   0-7

upcast [ secs ]     : Send upcast winch command. IF 'secs' specified stop winch after 'secs' seconds
downcast [ secs ]   : Send downcast winch command. IF 'secs' specified stop winch after 'secs' seconds
stop                : Send stop winch command
lock                : Release the latch solenoid to prevent the cable bullet from downcasting
unlock              : Hold the latch solenoid to allow the cable bullet to downcast

Notes: 1) commands are case sensitive
       2) pin 0 is adjacent the VCC pin\n"""

    def __init__(self, cfg):
        self.dio_port = cfg['rift-ox-pi']['DIO_PORT']
        self.prompt = 'Enter DIO Command: '
        self.cmndr = DIOCommander(cfg)
        self.winch = Winch(self.cmndr)
        super().__init__()

    def do_dio(self, arg):
        cmd_s: str = f'dio {arg}\r'
        # self.send_dio_cmd(cmd_s)
        resp, err = self.cmndr.issue_command(cmd_s)
        print(f'DIO RESPONSE: {resp} (err: {err})')

    def do_park(self, arg):
        self.winch.park()

    def do_unpark(self, arg):
        self.winch.unpark()

    def do_upcast(self, arg):
        try:
            dur: float = float(arg)
        except:
            print(f'*** Invalid command: upcast {arg}')
            self.help_dio()
        else:
            self.cmndr.up_cast(stop_after_ms=int(dur*1000))

    def do_downcast(self, arg):
        try:
            dur: float = float(arg)
        except:
            print(f'*** Invalid command: downcast {arg}')
            self.help_dio()
        else:
            self.cmndr.down_cast(stop_after_ms=int(dur*1000))

    def do_stop(self, arg):
        self.cmndr.stop_winch()

    def do_unlock(self, arg):
        self.cmndr.latch_hold()

    def do_lock(self, arg):
        self.cmndr.latch_release()

    def do_quit(self, arg):
        pass

    def help_dio(self):
        print(self.HELP_TEXT)

    def help_upcast(self):
        print("upcast [ secs ]  : Send upcast winch command. IF 'secs' specified stop winch after 'secs' seconds")

    def help_downcast(self):
        print("downcast [ secs ]  : Send downcast winch command. IF 'secs' specified stop winch after 'secs' seconds")

    def help_stop(self):
        print("stop                    (Send stop winch command)")

    def help_unlock(self):
        print("Hold the latch solenoid to allow the cable bullet to downcast")

    def help_lock(self):
        print("Release the latch solenoid to prevent the cable bullet from downcasting")

    def help_park(self):
        print("Upcast until latch sensor triggered, then stop and downcast for a little bit")

    def winch_init(self):
        self.cmndr.init_dio_pins()

    def precmd(self, line):
        words = line.split()
        if words[0].lower() in 'help':
            return line
        elif words[0].lower() == 'dio':
            if len(words) > 2:
                if words[1] not in self.DIO_CMDS:
                    print(f'*** Invalid command: {line}')
                    self.help_dio()
                    return ''
            else:
                print(f'*** Invalid command: {line}')
                self.help_dio()
                return ''
        elif words[0].lower() not in self.RIFT_OX_CMNDS:
            print(f'*** Invalid command: {line}')
            self.help_dio()
            return ''

        return line
    
    # trigger exist of main cmdLoop
    def postcmd(self, stop, line):
        return line.upper() in ['QUIT', 'EXIT']

    # do NOT use last cmd when empty line is input
    def emptyline(self):
        return ''

    def send_dio_cmd(self, cmd):

        cmd_bytes: bytes = cmd.encode()
        try:
            with serial.Serial(self.dio_port) as mcu:
                time.sleep(0.05)
                mcu.write(b"\r\n")
                time.sleep(0.05)
                # print(f'{mcu.read(mcu.inWaiting())}')  #get anything waiting in buffer and discard
                mcu.read(mcu.in_waiting) #get anything waiting in buffer and discard

                written = mcu.write(cmd_bytes)
                mcu.flush()

                time.sleep(0.01)
                res = mcu.read(mcu.in_waiting)
                res_array = res.split(b'\r\n')

                if res_array:
                    # print(f"RESPONSE: {res_array[1].decode()}")
                    text = res_array[1]
                else:
                    text=None
                    print(f'RESPONSE INVALID')

        except Exception as e:
            print(e)



if __name__ == "__main__":

    def interrupt_handler(signum, frame):

        sys.exit(0)


    signal.signal(signal.SIGINT, interrupt_handler)

    cfg = config.read()
    if cfg == None:
        print(f'winmon: ERROR unable to read rift-ox.toml config file. Quitting.')
        sys.exit(1)

    # print(f'{DIOShell.HELP_TEXT}')
    print(f"\nEnter 'help dio' for dio command syntax help.\n")

    sys.exit(DIOShell(cfg).cmdloop())

