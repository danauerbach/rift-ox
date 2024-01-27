import queue
import threading

import serial

from . import InverterState, INVERTER_CMD_LIST

# def set_inverter_state(inv_q: queue.Queue) -> None:
#     pass


def inverter_monitor(cfg: dict, inv_cmd_q: queue.Queue, quit_evt : threading.Event):

    # loop waiting for cmds to show up in the queue to send to the inv ctl serial port
    def send_command(open_serport : serial.Serial, cmd : bytes):

        try:
            open_serport.write(cmd)
            open_serport.flush()
            print(f'inverter Command sent : [{cmd}]')
        except serial.SerialTimeoutException as e:
            print(e)
        except serial.SerialException as e:
            print(e)
        else:
            pass

    inv_serport = cfg["rift-ox-pi"]["INVERTER_CMD_PORT"]

    while not quit_evt.is_set():

        data_dict = {}
        try:
            cmd = inv_cmd_q.get(block=True, timeout=0.25)
            inv_cmd_q.task_done()
        except queue.Empty as e:
            # print('winctl:winmon: NO CTDDATA message in data_q queue')
            continue
        except Exception as e:
            print(f'winctl:invmon: ERROR receiving data msg: {e}')
            continue

        if cmd in INVERTER_CMD_LIST:
            serport = serial.serial_for_url(inv_serport, )
            # send_command()

