#!/usr/bin/env python3

from pprint import pprint
import serial
import signal
import sys
import threading
import time
from typing import Tuple, Union

# DIO_ACTION_GET_VAL           = 0x00    # Read the state and count of an input, or just the state of an output
# DIO_ACTION_SET_VAL           = 0x01    # Set the logical state of a digital output
# DIO_ACTION_SETCOUNT_VAL      = 0x02    # Set the edge count of a digital input to the passed value
# DIO_ACTION_SETMODE_VAL       = 0x03    # Switch between sink-source and open-collector drive mode on supported hardware
# DIO_ACTION_NUMDEVICES_VAL    = 0x04    # Reports the number of DIO banks available on the device
# DIO_ACTION_NUMOUTPUTS_VAL    = 0x05    # Reports the number of outputs available to the indicated device
# DIO_ACTION_NUMINPUTS_VAL     = 0x06    # Reports the number of inputs available to the indicated device
# DIO_ACTION_GETEDGECOUNT_VAL  = 0x07    # Reports the number of rising and failing edges detected by an input pin

DIO_ACTION_GET_NAME          = "dio-get"        # Read the state and count of an input, or just the state of an output
DIO_ACTION_SET_NAME          = "dio-set"        # Set the logical state of a digital output
DIO_ACTION_SETMODE_NAME      = "dio-mode"    # Switch between sink-source and open-collector drive mode on supported hardware
DIO_ACTION_NUMDEVICES_NAME   = "dio-numdev"     # Reports the number of DIO banks available on the device
DIO_ACTION_NUMOUTPUTS_NAME   = "dio-numoutputs"     # Reports the number of outputs available to the indicated device
DIO_ACTION_NUMINPUTS_NAME    = "dio-numinputs"     # Reports the number of inputs available to the indicated device
DIO_ACTION_GETEDGECOUNT_NAME = 'dio-getedges'    # Reports the number of rising and failing edges detected by an input pin
DIO_VALID_COMMANDS           = [DIO_ACTION_GET_NAME, 
                                DIO_ACTION_SET_NAME, 
                                DIO_ACTION_SETMODE_NAME, 
                                DIO_ACTION_NUMDEVICES_NAME, 
                                DIO_ACTION_NUMOUTPUTS_NAME, 
                                DIO_ACTION_NUMINPUTS_NAME,
                                DIO_ACTION_GETEDGECOUNT_NAME,
                                "RAW:"]
DIO_VALID_PARAMS              = ['dir', 'group', 'pin', 'value']
DIO_DIRECTION_IN              = "in"
DIO_DIRECTION_OUT             = "out"
DIO_VALID_DIRECTIONS          = [DIO_DIRECTION_IN,
                                 DIO_DIRECTION_OUT]
DIO_LONG_DIRECTION_DICT       = {
    DIO_DIRECTION_IN: 'input',
    DIO_DIRECTION_OUT: 'output'
}
DIO_SHORT_DIRECTION_DICT       = {
    DIO_DIRECTION_IN: 'I',
    DIO_DIRECTION_OUT: 'O'
}
DIO_VALID_GROUPS              = [0,1,2,3] #list(range(0,4))
DIO_VALID_PINS                = list(range(0,8))
DIO_MODE_DRAIN                = 'open-drain'
DIO_MODE_SOURCE               = 'source'
DIO_VALID_MODES               = [DIO_MODE_DRAIN,
                                 DIO_MODE_SOURCE]

# CMD_RESPONOSE_SUCCESS         = 0x0000     # The last command was processed successfully    
# CMD_RESPONOSE_INV_DEV         = 0x0001     # The device indicated by the command exceeded the number of devices available to the system
# CMD_RESPONOSE_UNB_DEV         = 0x0002     # The device targetted exists, but the MCU was unable to attach to and communicate with it
# CMD_RESPONOSE_DIO_INV_PIN     = 0x0003     # The target pin exceeded the number of inputs or outputs actually present
# CMD_RESPONOSE_DIO_READ_FAIL   = 0x0004     # Reading the state of the targetted pin failed for an unknown reason
# CMD_RESPONOSE_DIO_WRITE_FAIL  = 0x0005     # Writing the state of the targetted pin failed for an unknown reason
# CMD_RESPONOSE_DIO_MODE_UNSUP  = 0x0006     # Setting the DIO mode to push-pull or sink-source is not supported
# CMD_RESPONOSE_INVALID_CMD     = 0x0007     # The subcommand requested was outside of the valid range for the message kind
# CMD_RESPONOSE_BAD_MSG_KIND    = 0x0008     # The message kind was not one of Valid Command Kinds
# CMD_RESPONOSE_VER_READ_FAIL   = 0x0009     # Reading the application version failed for an unknown reason



def interrupt_handler(signum, frame):

    quit_evt.set()

    # do whatever...
    # op_gpio_serial.close()
    time.sleep(1)
    sys.exit(0)


if __name__ == "__main__":

    signal.signal(signal.SIGINT, interrupt_handler)

    quit_evt = threading.Event()

    dio_port = '/dev/ttyACM0'

    while not quit_evt.is_set():

        cmd = input('Enter DIO Command: ')
        if cmd.lower().startswith('quit'):
            quit_evt.set()
            continue
        elif not cmd:
            print('no command entered, try again')
            continue
        cmd_bytes = f'{cmd}\r'.encode()

        try:
            with serial.Serial(dio_port) as mcu:
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
                    print(f"RESPONSE: {res_array[1].decode()}")
                    text = res_array[1]
                else:
                    text=None
                    print(f'INVALID RESPONSE')

        except Exception as e:
            print("Error")
            print(e)

        print()
        time.sleep(0.3)

