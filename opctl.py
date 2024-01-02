#!/usr/bin/env python3

from pprint import pprint
import serial
import signal
import sys
import threading
import time

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

def dio_get_pin_status(port, dir, group, pin):
    if dir == "I":
        dircmd = "input"
    else:
        dircmd = "output"

    print(f'ISSUING COMMAND: dio get D{dir}_G{group} {dircmd} {pin}'.encode())
    port.write(f'dio get D{dir}_G{group} {dircmd} {pin}\r'.encode())
    time.sleep(0.05)
    res = port.read(port.inWaiting())
    # print(f' GOT RESPONSE: {res}')
    if len(res) > 0:
        return res.split(b'\r\n')[1]
    else:
        return b''

def dio_get_all_pin_status(port, dir="I"):
    result = ""
    for group in range(0, 4):
        for pin in range(0, 4):
            result = result + dio_get_pin_status(port, dir, group, pin).decode()
    if "Failed" in result:
        result = "Not found"
    return result


def dio_command_bytes (cmd_name : str, **kwargs) -> (bytes or None):

    def group_valid(group : int):
        return group in DIO_VALID_GROUPS

    def pin_valid(group : int):
        return group in DIO_VALID_PINS

    ldir : str = ''
    llong_dir : str = ''
    lgroup : int = -1
    lpin : int = -1
    lvalue : str = ''
    cmd_bytes = bytearray(0)

    if 'dir' in kwargs:
        if kwargs["dir"] in DIO_VALID_DIRECTIONS:
            long_dir = DIO_LONG_DIRECTION_DICT[kwargs["dir"]]
            dir = kwargs["dir"][0].upper()
        else:
            #TODO LOG error
            return None

    if 'group' in kwargs:
        group = int(kwargs["group"])
        if not group_valid(group):
            #TODO log error
            print(f"invalid GROUP: {type(group)}. SHould be in {DIO_VALID_GROUPS}")
            return None

    if 'pin' in kwargs:
        pin = int(kwargs["pin"])
        if not pin_valid(pin):
            #TODO log error
            print(f"invalid PIN: {pin}. SHould be in {DIO_VALID_PINS}")
            return None

    if 'value' in kwargs:
        value = kwargs["value"]

    # cmd_bytes = bytearray(0)  # save enough room for the command header. 
    #                           # will have to expand for DIO command info
    # cmd_bytes = f'{cmd_name} dir={dir} group={group} pin={pin}\r'.encode()

    print(f'cmd_name: {cmd_name}')
    if cmd_name == DIO_ACTION_GET_NAME:

        cmd_bytes = f'dio get D{dir}_G{group} {long_dir} {pin}\r'. encode()

    elif cmd_name == DIO_ACTION_SET_NAME:

        if dir != DIO_DIRECTION_OUT[0].upper():
            #TODO log error
            print("can't SET INPUT pin")
            return None

        if not value:
            #TODO log error
            print("SET requires value= parameter")
            return None
        if value not in ['high', 'low', 'true', 'false']:
            #TODO log error
            print("Invalid set value: {value}")
            return None
        else:
            cmd_bytes = f'dio set D{dir}_G{group} {pin} {value}\r'. encode()

    elif cmd_name == DIO_ACTION_SETMODE_NAME:

        if dir != DIO_DIRECTION_OUT[0].upper():
            #TODO log error
            print("can't SET MODE on input group")
            return None
        
        # if value not in DIO_VALID_MODES:
        #     #TODO log error
        #     print("Invalid MODE {value}")
        #     return None
        # else:
        cmd_bytes = f'dio mode D{dir}_G{group} {value}\r'. encode()

    elif cmd_name == DIO_ACTION_NUMDEVICES_NAME:

        cmd_bytes = f'device list\r'. encode()

    elif cmd_name == DIO_ACTION_NUMOUTPUTS_NAME:

        cmd_bytes = f'dio num DO_G{group} outputs\r'. encode()

    elif cmd_name == DIO_ACTION_NUMINPUTS_NAME:

        cmd_bytes = f'dio num DI_G{group} inputs\r'. encode()

    elif cmd_name == DIO_ACTION_GETEDGECOUNT_NAME:

        cmd_bytes = f'dio edges D{dir}_G{group} {pin}\r'.encode()

    elif cmd_name == None:
        print(f"No valid command string: cmd:{cmd_name}; params:{kwargs};")
        cmd_bytes = None
    else:
        print(f"Unsupported command: cmd:{cmd_name}; params:{kwargs};")
        cmd_bytes = None

    return cmd_bytes

def dio_parse_params(cmdstr : str) -> (str, dict):

    params : dict = {}
    if cmdstr:
        cmdparts = cmdstr.split()
        if cmdparts[0] in DIO_VALID_COMMANDS:
            cmd = cmdparts[0]
        else:
            cmd = ''

        for part in cmdparts[1:]:
            # print(f'checking param: {part}')
            if part.startswith('dir='):
                params['dir'] = part.split('=')[1]
            elif part.startswith('group='):
                params['group'] = int(part.split('=')[1])
            elif part.startswith('pin='):
                params['pin'] = int(part.split('=')[1])
            elif part.startswith('value='):
                params['value'] = part.split('=')[1]
            else:
                print(f'invalid param: {part}')
                #TODO Logg error
                return None, {}

        #TODO Log info
        print(params)

    return cmd, params



if __name__ == "__main__":

    signal.signal(signal.SIGINT, interrupt_handler)

    quit_evt = threading.Event()

    # op_gpio_serial : serial.Serial = serial.Serial('/dev/ttyACM0') #, 9600, timeout=2.0, write_timeout=2, parity=serial.PARITY_EVEN, bytesize=8)

    """setup dio parameters"""
    dio_port = '/dev/ttyACM0'

    while not quit_evt.is_set():

        cmd = input('Enter DIO Command: ')
        if cmd.lower().startswith('quit'):
            quit_evt.set()
            continue
        elif not cmd:
            print('no command entered, try again')
            continue
        # else:
        #     cmd_words = cmd.split()
        #     if cmd_words[0] not in DIO_VALID_COMMANDS:
        #         print(f'Invalid command verb: {cmd_words[0]}')
        #         continue

        # if cmd_words[0] == 'RAW:':
        cmd_bytes = f'{" ".join(cmd)}\r'.encode()
        # else:
        #     cmd_verb, params = dio_parse_params(cmd)
        #     print(f'CMD: {cmd_verb}')
        #     pprint(params)
        #     if cmd_verb:
        #         cmd_bytes = dio_command_bytes(cmd_verb, **params)
        #         # print(f'CMD_BYTES: {cmd_bytes}')
        #     else:
        #         print(f'error constructing command from: {cmd}')

        try:
            with serial.Serial(dio_port) as mcu:
                time.sleep(0.05)
                mcu.write(b"\r\n")
                time.sleep(0.05)
                # print(f'{mcu.read(mcu.inWaiting())}')  #get anything waiting in buffer and discard
                mcu.read(mcu.inWaiting()) #get anything waiting in buffer and discard

                # cmd_bytes = dio_command_bytes(DIO_ACTION_NUMINPUTS_NAME, dir=DIO_DIRECTION_IN, group=0, pin=1)
                # print(f'COMMAND BYTES: {cmd_bytes}')
                written = mcu.write(cmd_bytes)
                mcu.flush()
                #TODO LOG INFO

                time.sleep(0.01)
                res = mcu.read(mcu.inWaiting())
                res_array = res.split(b'\r\n')
                #TODO LOG INFO
                # print(f"RESPONSE: {res_array}")
                if res_array:
                    # print(f'RESPONSE: {res_array}')
                    print(f"RESPONSE: {res_array[1].decode()}")
                    text = res_array[1]
                    #TODO LOG INFO
                else:
                    text=None
                    #TODO log error
                    print(f'INVALID RESPONSE')

        except Exception as e:
            print("Error")
            print(e)

        print()
        time.sleep(0.3)
        # quit_evt.set()



        # cmd : str = input('Enter byte-code cmd> ')
        # # cmd = cmd.upper()
        # # cmd_words : list[str] = cmd.split()
        # cmd_words = cmd

        # print(f"you entered {cmd_words}")
        # print()


        # time.sleep(0.005)
        # op_gpio_serial.write(b"\r\n")
        # time.sleep(0.005)

        # pin_status = dio_get_all_pin_status(op_gpio_serial, "O")
        # print(pin_status)

        # break

        # time.sleep(0.005)
        # op_gpio_serial.write(b"\r\n")
        # time.sleep(0.005)
        # op_gpio_serial.read(op_gpio_serial.inWaiting()) #get anything waiting in buffer and discard

        # for pin in range(0,8):
        #     op_gpio_serial.write(f'dio get DO_G0 output {pin}\n'.encode())
        #     time.sleep(0.05)
        #     res = op_gpio_serial.read(op_gpio_serial.inWaiting())
        #     res_array = res.split(b'\r\n')
        #     print(f"{res_array}")
    
        # break



        # if cmd_words[0] == 'QUIT':
        #     quit_evt.set()

        # elif cmd_words[0] == DIO_ACTION_GET_NAME:
        #     pin_val : int = int(cmd_words[1]).to_bytes(length=1, byteorder=sys.byteorder)
        #     print(pin_val)
        #     cmd_bytes = dio_command_bytes(DIO_ACTION_GET_NAME, pin_val)

        # elif cmd_words[0] == DIO_ACTION_SET_NAME:
        #     pin_val : int = int(cmd_words[1]).to_bytes(length=1, byteorder=sys.byteorder)
        #     print(pin_val)
        #     cmd_bytes = dio_command_bytes(DIO_ACTION_GET_NAME, pin_val)

        # elif cmd_words[0] == DIO_ACTION_NUMDEVICES_NAME:

        #     cmd_bytes = dio_command_bytes(cmd_words[0], None)
        #     op_gpio_serial.write(cmd_bytes)
        #     print(f'sending command: {cmd_bytes}')

        #     while not quit_evt.is_set():

        #         try: 
        #             resp = op_gpio_serial.readline()
        #             print(resp)
        #             print(resp.decode())
        #         except:
        #             print('serial read timeout/error, quitting')
        #             quit_evt.set()
        # # elif: cmd[0] == DIO_ACTION_SETCOUNT_NAME:
        # #     pin_val = int(cmd[1])

        # # elif: cmd[0] == DIO_ACTION_SETMODE_NAME:
        # #     pin_val = int(cmd[1])

        # # elif cmd[0] == DIO_ACTION_NUMDEVICES_NAME:

        # # elif cmd[0] == DIO_ACTION_NUMOUTPUTS_NAME:

        # # elif cmd[0] == DIO_ACTION_NUMINPUTS_NAME:


        
