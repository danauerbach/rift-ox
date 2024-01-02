#!/usr/bin/env python3

import serial
import time

from . import  WinchDir, \
    DIO_VALID_COMMANDS, \
    DIO_VALID_GROUPS, \
    DIO_VALID_PINS, \
    DIO_VALID_DIRECTIONS, \
    DIO_VALID_MODES, \
    DIO_ACTION_DEVICE_LIST_NAME, \
    DIO_ACTION_GET_NAME, \
    DIO_ACTION_SET_NAME, \
    DIO_ACTION_MODE_NAME, \
    DIO_ACTION_NUM_NAME, \
    DIO_ACTION_PWM_NAME, \
    DIO_ACTION_EDGE_NAME, \
    DIO_LONG_DIRECTION_DICT, \
    DIO_SHORT_DIRECTION_DICT, \
    DIO_DIRECTION_IN , \
    DIO_DIRECTION_OUT, \
    DIO_MODE_DRAIN, \
    DIO_MODE_SOURCE




class DIOCommander():

    def __init__(self, cfg: dict, simulation: bool = True):
        self.cfg = cfg
        self.dio_tty_port = cfg["rift-ox-pi"]["DIO_PORT"]
        self.simulation = simulation

        self.MOTOR_STOP_PIN = {
            "group": cfg["rift-ox-pi"]["DIO_MOTOR_STOP_GROUP"],
            "pin": cfg["rift-ox-pi"]["DIO_MOTOR_STOP_PIN"],
        }
        self.DOWNCAST_PIN = {
            "group": cfg["rift-ox-pi"]["DIO_DOWNCAST_GROUP"],
            "pin": cfg["rift-ox-pi"]["DIO_DOWNCAST_PIN"],
        }
        self.UPCAST_PIN = {
            "group": cfg["rift-ox-pi"]["DIO_UPCAST_GROUP"],
            "pin": cfg["rift-ox-pi"]["DIO_UPCAST_PIN"],
        }
        self.LATCH_RELEASE_PIN = {
            "group": cfg["rift-ox-pi"]["DIO_LATCH_RELEASE_GROUP"],
            "pin": cfg["rift-ox-pi"]["DIO_LATCH_RELEASE_PIN"]
        }
        self.PAYOUT1_PIN = {
            "group": cfg["rift-ox-pi"]["DIO_PAYOUT1_SENSOR_GROUP"],
            "pin": cfg["rift-ox-pi"]["DIO_PAYOUT1_SENSOR_PIN"],
        }
        self.PAYOUT2_PIN = {
            "group": cfg["rift-ox-pi"]["DIO_PAYOUT2_SENSOR_GROUP"],
            "pin": cfg["rift-ox-pi"]["DIO_PAYOUT2_SENSOR_PIN"],
        }
        self.LATCH_SENSOR_PIN = {
            "group": cfg["rift-ox-pi"]["DIO_LATCH_SENSOR_GROUP"],
            "pin": cfg["rift-ox-pi"]["DIO_LATCH_SENSOR_PIN"],
        }

        self.init_dio_pins()

    def init_dio_pins(self):
        cmds = [
            f'dio mode DO_G0 source\r',
            f'dio mode DO_G1 source\r',
            f'dio mode DO_G2 source\r',
            f'dio mode DO_G3 source\r',
            f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} low\r',
            f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} low\r',
            f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} low\r',
            f'dio set DO_G{self.LATCH_RELEASE_PIN["group"]} {self.LATCH_RELEASE_PIN["pin"]} low\r'
        ]
        for cmd in cmds:
            self.issue_command(method="init_dio_pins", cmd=cmd)
            time.sleep(0.03)

    def pin_low(self, pin: str):
        if pin == 'stop':
            cmd = f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} low\r'
        elif pin == 'up':
            cmd = f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} low\r'
        elif pin == 'down':
            cmd = f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} low\r'
        elif pin == 'latch':
            cmd = f'dio set DO_G{self.LATCH_RELEASE_PIN["group"]} {self.LATCH_RELEASE_PIN["pin"]} low\r'

        self.issue_command(method=f"{pin}_low", cmd=cmd)
        time.sleep(0.03)

    def pin_hi(self, pin: str):
        if pin == 'stop':
            cmd = f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} high\r'
        elif pin == 'up':
            cmd = f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} high\r'
        elif pin == 'down':
            cmd = f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} high\r'
        elif pin == 'latch':
            cmd = f'dio set DO_G{self.LATCH_RELEASE_PIN["group"]} {self.LATCH_RELEASE_PIN["pin"]} high\r'

        self.issue_command(method=f"{pin}_hi", cmd=cmd)
        time.sleep(0.03)

    def stop_winch(self):
        cmds = [
            f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} high\r',
            f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} low\r',
            f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} low\r',
        ]
        for cmd in cmds:
            self.issue_command(method="stop_winch", cmd=cmd)
            time.sleep(0.03)

    def latch_release(self):
        cmds = [
            f'dio set DO_G{self.LATCH_RELEASE_PIN["group"]} {self.LATCH_RELEASE_PIN["pin"]} low\r',
        ]
        for cmd in cmds:
            self.issue_command(method="latch_release", cmd=cmd)
            time.sleep(0.03)

    def latch_hold(self):
        cmds = [
            f'dio set DO_G{self.LATCH_RELEASE_PIN["group"]} {self.LATCH_RELEASE_PIN["pin"]} high\r',
        ]
        for cmd in cmds:
            self.issue_command(method="latch_hold", cmd=cmd)
            time.sleep(0.03)

    def stage(self):
        cmds = [
            f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} low\r',
            f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} high\r',
            f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} low\r',
        ]
        for cmd in cmds:
            self.issue_command(method="stage", cmd=cmd)
            time.sleep(0.03)

    def down_cast(self, stop_after_ms=0):
        cmds = [
            f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} low\r',
            f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} high\r',
            f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} low\r',
        ]
        for cmd in cmds:
            self.issue_command(method="down_cast", cmd=cmd)
            time.sleep(0.03)
        if stop_after_ms > 0:
            time.sleep(stop_after_ms / 1.000)
            self.stop_winch()

    def up_cast(self, stop_after_ms=0):
        cmds = [
            f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} high\r',
            f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} low\r',
            f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} low\r',
        ]
        for cmd in cmds:
            self.issue_command(method="up_cast", cmd=cmd)
            time.sleep(0.03)
        if stop_after_ms > 0:
            time.sleep(stop_after_ms / 1.000)
            self.stop_winch()

    def park(self):
        """Parking is moving winch backwards until LATCH signal
        is detected and then paying out until the latch is not detected.
        This should leave the winch in the (physically) LATCHED position"""

        # check currnet latch state
        latch_high, err = self.get_latch_sensor_state()
        if err:
            print('dio_cmds:park UNABLE to get LATCH SENSOR state when PARKING')
            return
        
        if not latch_high:
            # we don't know if we are above or below the latch,
            # so unwind just a little to be confident we are below the latch
            self.down_cast(stop_after_ms=self.cfg["winch"]["PARKING_DOWNCAST_1_MS"])
            latch_high, err = self.get_latch_sensor_state()

        # start upcast
        if not latch_high:
            # capture latch_sensor edge count before raising back up
            start_latch_edge_count, err = self.get_latch_edge_count()
            new_latch_edge_count = start_latch_edge_count
        
            latch_found = False
            self.up_cast() #### NOT SURE THIS IS A GOOD IDEA
            while not latch_found:
                # check fr new LATCH edge count
                if self.simulation:  # SIMULATION: fake latch addl edges after 2 secs
                    time.sleep(1.5)
                    new_latch_edge_count = start_latch_edge_count + 2
                    err = False
                else:
                    new_latch_edge_count, err = self.get_latch_edge_count()
                if err:
                    self.stop_winch() #### NOT SURE THIS IS A GOOD IDEA
                    print('dio_cmds:park UNABLE to get LATCH SENSOR state when PARKING')
                    return
                latch_found = new_latch_edge_count > start_latch_edge_count
                if latch_found:
                    self.stop_winch()
                    start_latch_edge_count = new_latch_edge_count
                    break
                time.sleep(0.33)    

        # presumably we are on the LATCH now. SO, per SHerman/CLARS, 
        # need to move up a little, then down just past the latch
        self.up_cast(stop_after_ms=self.cfg["winch"]["PARKING_UPCAST_MS"])
        time.sleep(.5)
        self.down_cast(stop_after_ms=self.cfg["winch"]["PARKING_DOWNCAST_2_MS"])
                
        # it should now be parked with physical catch latch activated
        #TODO TEST TEST TEST

    def get_latch_sensor_state(self) -> (bool, bool):

        cmd = f'dio get DI_G{self.LATCH_SENSOR_PIN["group"]}\r'
        result, err = self.issue_command(method="get_latch_sensor_state", cmd=cmd)
        if self.simulation:  # SIMULATION: fake latch LOW signal
            result = "0"
            err = False
        else:
            if err:
                return result, err

        return int(result), err

    def get_latch_edge_count(self) -> (int, bool):
        cmd = f'dio edge DI_G{self.LATCH_SENSOR_PIN["group"]} {self.LATCH_SENSOR_PIN["pin"]}\r'
        edge_count, err = self.issue_command("get_latch_edge_count", cmd)
        if err:
            return None, True
        edge_count = int(edge_count)
        return edge_count, False

    def get_payout_edge_count(self) -> (list[int], bool):
        cmds = [
            f'dio edge DI_G{self.PAYOUT1_PIN["group"]} {self.PAYOUT1_PIN["pin"]}\r',
            f'dio edge DI_G{self.PAYOUT2_PIN["group"]} {self.PAYOUT2_PIN["pin"]}\r',
        ]
        payout_counts = []
        for cmd in cmds:
            result, err = self.issue_command(method="get_payout_edge_count", cmd=cmd)
            if err:
                return None, True
            payout_counts = payout_counts.append(int(result))

        if len(payout_counts) == 0:
            return payout_counts, True
        
        return payout_counts, False

    def get_winch_direction(self) -> (WinchDir, bool):
        err: bool = False
        up_pin_query = f'dio get DO_G{self.UPCAST_PIN["group"]} output {self.UPCAST_PIN["pin"]}\r'.encode()
        down_pin_query = f'dio get DO_G{self.DOWNCAST_PIN["group"]} output {self.DOWNCAST_PIN["pin"]}\r'.encode()
        stop_pin_query = f'dio get DO_G{self.MOTOR_STOP_PIN["group"]} output {self.MOTOR_STOP_PIN["pin"]}\r'.encode()

        up_pin_state, err = self._send_bytes(up_pin_query)
        if err:
            return None, True
        up_active: bool = not bool(int(up_pin_state))  # "1" is active but in python 0 == True

        down_pin_state, err = self._send_bytes(down_pin_query)
        if err:
            return None, True
        down_active:bool = not bool(int(down_pin_state))

        stop_pin_state, err = self._send_bytes(stop_pin_query)
        if err:
            return None, True
        stop_active = not bool(int(stop_pin_state))

        if stop_active:
            return WinchDir.DIRECTION_NONE

        # stop not active...
        if up_active and not down_active: return WinchDir.DIRECTION_UP, err
        if not up_active and down_active: return WinchDir.DIRECTION_DOWN, err
        
        # either both direction lines HIGH or both LOW, either way winch not moving.
        return WinchDir.DIRECTION_NONE, err

    def issue_command(self, method: str, cmd : str) -> (str, bool):

        # cmd_bytes: bytes = self._dio_command_ddbytes(cmd)
        cmd_bytes: bytes = cmd.encode()
        if cmd_bytes == None:
            print(f'ERROR converting command info {cmd.strip()} to bytes')
            return "", True

        # print(f'COMMAND to {self.dio_tty_port}: {cmd_bytes.decode()}')
        if not self.simulation:
            return self._send_bytes(cmd_bytes)
        else:
            self._log_cmd(method, cmd_bytes)
            return "", True


    def _dio_command_bytes (self, cmd : str) -> (bytes or None):

        print(f'dio_cmds:dio_command_bytes: cmd: {cmd.strip()}')
        cmd_bytes = bytearray(0)

        # def group_valid(group : int):
        #     return group in DIO_VALID_GROUPS

        # def pin_valid(group : int):
        #     return group in DIO_VALID_PINS

        # if 'dir' in kwargs:
        #     if kwargs["dir"] in DIO_VALID_DIRECTIONS:
        #         long_dir = DIO_LONG_DIRECTION_DICT[kwargs["dir"]]
        #         dir = kwargs["dir"][0].upper()
        #     else:
        #         #TODO LOG error
        #         return None

        # if 'group' in kwargs:
        #     group = int(kwargs["group"])
        #     if not group_valid(group):
        #         #TODO log error
        #         print(f"invalid GROUP: {type(group)}. Should be in {DIO_VALID_GROUPS}")
        #         return None

        # if 'pin' in kwargs:
        #     pin = int(kwargs["pin"])
        #     if not pin_valid(pin):
        #         #TODO log error
        #         print(f"invalid PIN: {pin}. SHould be in {DIO_VALID_PINS}")
        #         return None

        # if 'value' in kwargs:
        #     value = kwargs["value"]


        # if cmd == DIO_ACTION_GET_NAME:

        #     cmd_bytes = f'dio get D{dir}_G{group} {long_dir} {pin}\r'. encode()

        # elif cmd == DIO_ACTION_SET_NAME:

        #     if dir != DIO_DIRECTION_OUT[0].upper():
        #         #TODO log error
        #         print("can't SET INPUT pin")
        #         return None

        #     if not value:
        #         #TODO log error
        #         print("SET requires value= parameter")
        #         return None
            
        #     if value not in ['high', 'low', 'true', 'false']:
        #         #TODO log error
        #         print("Invalid set value: {value}")
        #         return None

        #     cmd_bytes = f'dio set D{dir}_G{group} {pin} {value}\r'.encode()

        # elif cmd == DIO_ACTION_MODE_NAME:

        #     if dir != DIO_DIRECTION_OUT[0].upper():
        #         #TODO log error
        #         print("can't SET MODE on input group")
        #         return None
            
        #     if value not in DIO_VALID_MODES:
        #         #TODO log error
        #         print("Invalid MODE {value}")
        #         return None

        #     cmd_bytes = f'dio mode D{dir}_G{group} {value}\r'.encode()

        # elif cmd == DIO_ACTION_NUM_NAME:

        #     if dir == DIO_DIRECTION_IN[0].upper():
        #         cmd_bytes = f'dio num DI_G{group} inputs\r'.encode()
        #     elif dir == DIO_DIRECTION_OUT[0].upper():
        #         cmd_bytes = f'dio num DO_G{group} outputs\r'.encode()

        # elif cmd == DIO_ACTION_DEVICE_LIST_NAME:

        #     cmd_bytes = f'device list\r'. encode()

        # elif cmd == DIO_ACTION_EDGE_NAME:

        #     if dir != DIO_DIRECTION_IN[0].upper():
        #         #TODO log error
        #         print("can only get edges on input group pin")
        #         return None
            
        #     cmd_bytes = f'dio edges D{dir}_G{group} {pin}\r'.encode()

        # elif cmd == None:
        #     print(f"No valid command string: cmd:{cmd.strip()}; params:{kwargs};")
        #     cmd_bytes = None

        # else:
        #     print(f"Unsupported command: cmd:{cmd.strip()}; params:{kwargs};")
        #     cmd_bytes = None

        # return cmd_bytes
    
    def _send_bytes(self, cmd_bytes: bytes) -> (str, bool):
           
        result: str = ""
        err: bool = False

        with serial.Serial(self.dio_tty_port) as mcu:

            mcu.write(b"\r\n")
            time.sleep(0.05)
            # print(f'{mcu.read(mcu.inWaiting())}')  #get anything waiting in buffer and discard
            mcu.read(mcu.inWaiting()) #get anything waiting in buffer and discard

            # cmd_bytes = dio_command_bytes(DIO_ACTION_NUMINPUTS_NAME, dir=DIO_DIRECTION_IN, group=0, pin=1)
            written = mcu.write(cmd_bytes)
            mcu.flush()
            print(f'Command sent: {cmd_bytes.decode().strip()}')
            #TODO LOG INFO

            time.sleep(0.01)
            res = mcu.read(mcu.inWaiting())
            res_array = res.split(b'\r\n')
            #TODO LOG INFO
            # print(f"RESPONSE: {res_array}")
            if res_array:
                # print(f'DIO RESPONSE: {res_array}')
                # print(f"DIO RESPONSE: {res_array[1].decode()}")
                result = res_array[1]
                #TODO LOG INFO
            else:
                result = None
                err = True
                #TODO log error
                # print(f'DIO INVALID RESPONSE')

        return result, err

    def _log_cmd(self, method, cmd_bytes: bytes):
        print(f'{method} issuing: "{cmd_bytes.decode().strip()}"')
