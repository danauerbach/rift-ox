#!/usr/bin/env python3

import serial
import time
from typing import Tuple, Union

from . import  WinchDir


class DIOCommander():

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.dio_tty_port = cfg["rift-ox-pi"]["DIO_PORT"]
        self.simulation = cfg["rift-ox-pi"]["SIMULATION"]

        print(f"SIMULATION: {self.simulation}")

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
        self.KILL33_PIN = {
            "group": cfg["rift-ox-pi"]["DIO_KILL33_GROUP"],
            "pin": cfg["rift-ox-pi"]["DIO_KILL33_PIN"]
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
        for command in cmds:
            self.issue_command(cmd=command)
            # time.sleep(0.01)

    def pin_low(self, pin: str):
        cmd: str = ''
        if pin == 'stop':
            cmd = f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} low\r'
        elif pin == 'up':
            cmd = f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} low\r'
        elif pin == 'down':
            cmd = f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} low\r'
        elif pin == 'latch':
            cmd = f'dio set DO_G{self.LATCH_RELEASE_PIN["group"]} {self.LATCH_RELEASE_PIN["pin"]} low\r'

        self.issue_command(cmd)

    def pin_hi(self, pin: str):
        cmd: str = ''
        if pin == 'stop':
            cmd = f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} high\r'
        elif pin == 'up':
            cmd = f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} high\r'
        elif pin == 'down':
            cmd = f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} high\r'
        elif pin == 'latch':
            cmd = f'dio set DO_G{self.LATCH_RELEASE_PIN["group"]} {self.LATCH_RELEASE_PIN["pin"]} high\r'

        self.issue_command(cmd=cmd)

        cmd: str = ''
    def stop_winch(self):
        cmds = [
            f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} high\r',
            f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} low\r',
            f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} low\r',
        ]
        for cmd in cmds:
            self.issue_command(cmd=cmd)
            # time.sleep(0.03)

    def latch_release(self):
        cmd = f'dio set DO_G{self.LATCH_RELEASE_PIN["group"]} {self.LATCH_RELEASE_PIN["pin"]} low\r'
        self.issue_command(cmd=cmd)

    def latch_hold(self):
        cmd = f'dio set DO_G{self.LATCH_RELEASE_PIN["group"]} {self.LATCH_RELEASE_PIN["pin"]} high\r'
        self.issue_command(cmd=cmd)

    def stage(self):
        # fdist let's make sure latch pin is being held...
        cmds = [
            f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} low\r',
            f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} high\r',
            f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} low\r',
        ]
        for cmd in cmds:
            self.issue_command(cmd=cmd)
            # time.sleep(0.03)

    def down_cast(self, stop_after_ms: int =0):
        cmds = [
            f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} low\r',
            f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} high\r',
            f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} low\r',
        ]
        for cmd in cmds:
            self.issue_command(cmd=cmd)
            # time.sleep(0.03)
        if stop_after_ms > 0:
            time.sleep(stop_after_ms / 1000)
            self.stop_winch()

    def up_cast(self, stop_after_ms: int =0):
        cmds = [
            f'dio set DO_G{self.UPCAST_PIN["group"]} {self.UPCAST_PIN["pin"]} high\r',
            f'dio set DO_G{self.DOWNCAST_PIN["group"]} {self.DOWNCAST_PIN["pin"]} low\r',
            f'dio set DO_G{self.MOTOR_STOP_PIN["group"]} {self.MOTOR_STOP_PIN["pin"]} low\r',
        ]
        for cmd in cmds:
            self.issue_command(cmd=cmd)
            # time.sleep(0.03)
        if stop_after_ms > 0:
            time.sleep(stop_after_ms / 1000)
            self.stop_winch()

    def kill33(self):
        cmd: str = f'dio set DO_G{self.KILL33_PIN["group"]} {self.KILL33_PIN["pin"]} high\r'
        self.issue_command(cmd=cmd)

    def get_latch_sensor_state(self) -> Tuple[int, bool]:

        cmd = f'dio get DI_G{self.LATCH_SENSOR_PIN["group"]}\r'
        result, err = self.issue_command(cmd=cmd)
        if self.simulation:  # SIMULATION: fake latch LOW signal
            result = 0
            err = False
        else:
            if err:
                return 0, err

        return int(result), err
    
    def get_latch_edge_count(self) -> Tuple[str, bool]:
        edge_cnt_str: str
        cmd = f'dio edge DI_G{self.LATCH_SENSOR_PIN["group"]} {self.LATCH_SENSOR_PIN["pin"]}\r'
        edge_cnt_str, err = self.issue_command(cmd=cmd)
        if err:
            return "0", True
        return edge_cnt_str, False

    def get_payout_edge_count(self) -> Tuple[list[int], bool]:
        payout_1: str = ''
        payout_2: str = ''
        p1: int = 0
        p2: int = 0
        res: bool = False
        cmd = f'dio edge DI_G{self.PAYOUT1_PIN["group"]} {self.PAYOUT1_PIN["pin"]}\r'
        payout_1, err = self.issue_command(cmd=cmd)
        if not err and payout_1.isdigit():
            p1 = int(payout_1)
        else:
            res = True

        cmd = f'dio edge DI_G{self.PAYOUT2_PIN["group"]} {self.PAYOUT2_PIN["pin"]}\r'
        payout_2, err = self.issue_command(cmd=cmd)
        if not err and payout_2.isdigit():
            p2 = int(payout_2)
        else:
            res = True

        return [p1, p2], res

    def get_winch_direction(self) -> Tuple[str, bool]:
        err: bool = False
        res: bool = False
        up_active: bool = False
        down_active: bool = False
        stop_active: bool = False
        up_pin_query = f'dio get DO_G{self.UPCAST_PIN["group"]} output {self.UPCAST_PIN["pin"]}\r'
        down_pin_query = f'dio get DO_G{self.DOWNCAST_PIN["group"]} output {self.DOWNCAST_PIN["pin"]}\r'
        stop_pin_query = f'dio get DO_G{self.MOTOR_STOP_PIN["group"]} output {self.MOTOR_STOP_PIN["pin"]}\r'

        up_pin_state, err = self.issue_command(up_pin_query)
        if not err and up_pin_state.isdigit():
            up_active = not bool(int(up_pin_state))  # "1" is active but in python 0 == True
        else:
            res = True

        down_pin_state, err = self.issue_command(down_pin_query)
        if not err and down_pin_state.isdigit():
            down_active = not bool(int(down_pin_state))
        else:
            res = True

        stop_pin_state, err = self.issue_command(stop_pin_query)
        if not err and stop_pin_state.isdigit():
            stop_active = not bool(int(stop_pin_state))
        else:
            res = True

        if res:
            return WinchDir.DIRECTION_NONE.value, res

        # stop_active = stop_pin_state == "1"
        # down_active = down_pin_state == "1"
        # up_active = up_pin_state == "1"
        if stop_active:
            return WinchDir.DIRECTION_NONE.value, res

        # stop not active...
        if up_active and not down_active: return WinchDir.DIRECTION_UP.value, res
        if not up_active and down_active: return WinchDir.DIRECTION_DOWN.value, res
        
        # either both direction lines HIGH or both LOW, either way winch not moving.
        return WinchDir.DIRECTION_NONE.value, res

    def issue_command(self, cmd : str) -> Tuple[str, bool]:

        # cmd_bytes: bytes = self._dio_command_ddbytes(cmd)
        cmd_bytes: bytes = cmd.encode()
        if cmd_bytes == None:
            print(f'ERROR converting command info {cmd.strip()} to bytes')
            return "", True

        return self._send_bytes(cmd_bytes)


    def _send_bytes(self, cmd_bytes: bytes) -> Tuple[str, bool]:
           
        result: str = ""
        err: bool = False

        if not self.simulation:

            with serial.Serial(self.dio_tty_port) as mcu:

                # print(f'_send_bytes issuing: "{cmd_bytes.decode().strip()}"')
                mcu.write(b"\r\n")
                time.sleep(0.05)
                # print(f'{mcu.read(mcu.inWaiting())}')  #get anything waiting in buffer and discard
                mcu.read(mcu.in_waiting) #get anything waiting in buffer and discard

                written = mcu.write(cmd_bytes)
                mcu.flush()

                time.sleep(0.01)
                res = mcu.read(mcu.in_waiting)
                res_array = res.split(b'\r\n')
                #TODO LOG INFO
                # print(f"RESPONSE: {res_array}")
                if res_array:
                    # print(f'DIO RESPONSE: {res_array}')
                    # print(f"DIO RESPONSE: {res_array[1].decode()}")
                    result = res_array[1].decode()
                    #TODO LOG INFO
                else:
                    result = ""
                    err = True
                    #TODO log error
                    # print(f'DIO INVALID RESPONSE')

            return result, err

        else:
            # print(f'_send_bytes: logging: "{cmd_bytes.decode().strip()}"')
            return "", False
