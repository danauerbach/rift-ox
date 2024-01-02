#!/usr/bin/env python3

from datetime import datetime
from enum import Enum
import json
import logging
from pathlib import Path
import queue
import threading
import time

import paho.mqtt.client as mqtt

from winch.dio_cmds import DIOCommander
# from winch import states
from winch.states import Winch

from . import WINCH_CMD_LIST, WinchCmd


def wincmd_loop(cfg: dict, winch_status_q: queue.Queue, quit_evt : threading.Event):

    # internal queue to take message from MQTT client callback
    # and forward to main winctl loop
    def on_CMD(client, userdata, message):

        msg_str = message.payload.decode('utf-8')
        msg_json = json.loads(msg_str)
        cmd_q.put(msg_json)

    def on_ctl_connect(client, userdata, flags, rc):
        if rc==0:
            client.connected_flag=True #set flag
            print("connected OK: {client}")
        else:
            print("Bad connection for {client} Returned code: ", rc)
            client.loop_stop()

    def on_ctl_disconnect(client, userdata, rc):
        client.connected_flag=False #set flag
        print("client disconnected ok")

    def on_ctl_subscribe(client, userdata, mid, granted_qos):
        print("Subscribed: "+str(mid)+" "+str(granted_qos))

    def get_payout_fn(name: Path) -> str:
        ops_dir = Path(cfg['rift-ox-pi']['OPS_DIR'])
        Path.mkdir(ops_dir, parents = True, exists_ok = True)
        return ops_dir.joinpath(name)
    
    def save_payout(status: dict, fn: Path):
        ts = status["ts"]
        payouts = status["payouts"]
        with open(get_payout_fn(fn), mode='a') as pofl:
            pofl.write(f'{ts:<26}, {payouts[0]}, {payouts[1]}')
        return

    def share_new_winch_status(winch: Winch, fname: Path) -> (dict, bool):
        status, err = winch.status()
        if err:
            return {}, True
        else:
            save_payout(status, fname)
            winch_status_q.put(status)
            return status, False


    cmd_q = queue.Queue()

    wincmd_sub = mqtt.Client('wincmd-sub')
    wincmd_sub.on_connect = on_ctl_connect
    wincmd_sub.on_disconnect = on_ctl_disconnect
    wincmd_sub.on_subscribe = on_ctl_subscribe
    wincmd_sub.on_message = on_CMD
    wincmd_sub.connect(cfg["mqtt"]["HOST"], cfg["mqtt"]["PORT"])
    err, _ = wincmd_sub.subscribe(cfg["mqtt"]["WINCH_CMD_TOPIC"], qos=2)
    if err != None:
        print(f'winmon:wincmd ERROR subscribing to {cfg["mqtt"]["WINCH_CMD_TOPIC"]}')
        print(f'winmon:wincmd shutting down')
        quit_evt.set()
        time.sleep(.25)
    else:
        wincmd_sub.loop_start()

        # simulator_pub = winmqtt.winmon_pubber('winmon-simul-pub')
        # simulator_pub.loop_start

    dio_cmndr: DIOCommander = DIOCommander(cfg, simulation=cfg["rift-ox-pi"]["SIMULATION"])
    winch: Winch = Winch(dio_cmndr)

    # get initial winch status
    init_status, err = share_new_winch_status(winch, Path("payouts"))
    if err:
        print(f'winctl:winmon: ERROR getting initial winch status')

    while not quit_evt.is_set():

        status, err = share_new_winch_status(winch, Path("payouts"))
        if err:
            print(f'winctl:winmon: ERROR getting initial winch status')

        cmd_msg = ""
        try:
            cmd_msg = cmd_q.get(block=True, timeout=1.0)
            cmd_q.task_done()
        except queue.Empty as em:
            print('winctl:wincmd: INFO no data message in cmd_q queue')
            continue
        except Exception as e:
            print(f'winctl:wincmd: Error receiving msg from cmd_q Queue: {e}')
            continue

        cmd = cmd_msg['command'].lower()
        if cmd not in WINCH_CMD_LIST:
            print(f'winctl:wincmd: INVALID COMMAND: {cmd}')
            continue

        if cmd == WinchCmd.WINCH_CMD_START:
            winch.start()

        elif cmd == WinchCmd.WINCH_CMD_STOP_AT_MAX_DEPTH:
            winch.up_pause()

        elif cmd == WinchCmd.WINCH_CMD_UP_PAUSE:
            winch.up_pause()

        elif cmd == WinchCmd.WINCH_CMD_DOWN_PAUSE:
            winch.down_pause()

        elif cmd == WinchCmd.WINCH_CMD_PARK:
            winch.park()

        elif cmd == WinchCmd.WINCH_CMD_DOWNCAST:
            winch.downcast()

        elif cmd == WinchCmd.WINCH_CMD_UPCAST:
            winch.upcast()

        elif cmd == WinchCmd.WINCH_CMD_RETURN:
            winch.upcast()

        elif cmd == WinchCmd.WINCH_CMD_SETSTATE:
            winch.set_state

        #     print(f'############# WINCH COMMAND "{cmd}" BEGIN')
        #     if winch_status not in [WINCH_CMD_STOP, WINCH_CMD_NONE]:
        #         #TODO set DIO speed pin 'low' using ttyACM0 serial port
        #         print(f'{round(time.time(), 2)} WIN CTL: STOP: SPEED->low')
        #         time.sleep(2) # wait 2 secs for winch deceleration before changing direction lines
        #         #TODO set DIO FORWARD (sink) pin 'low' using ttyACM0 serial port
        #         #TODO set DIO REVERSE (sink) pin 'low' using ttyACM0 serial port
        #         print(f'{round(time.time(), 2)} WIN CTL: STOP: FORWARD->high')
        #         print(f'{round(time.time(), 2)} WIN CTL: STOP: REVERSE->high')
        #     winch_status = WINCH_CMD_STOP
        #     print(f'############# WINCH COMMAND "{cmd}" END')

        # elif cmd == WinchCmd.WINCH_CMD_DOWNCAST:

        #     print(f'############# WINCH COMMAND "{cmd}" BEGIN:')
        #     if winch_status not in [WINCH_CMD_STOP, WINCH_CMD_NONE]:   # if in motion stop and wait for decel
        #         #TODO set DIO speed pin 'low' using ttyACM0 serial port
        #         print(f'WIN CTL FORWARD: SPEED->low (stopping before estting new direction)')
        #         time.sleep(2)
        #     print(f'{round(time.time(), 2)} WIN CTL FORWARD: REVERSE->high')
        #     print(f'{round(time.time(), 2)} WIN CTL FORWARD: FORWARD->low')
        #     print(f'{round(time.time(), 2)} WIN CTL FORWARD: SPEED->high')
        #     winch_status = WINCH_CMD_DOWNCAST

        # elif cmd == WinchCmd.WINCH_CMD_UPCAST:

        #     print(f'############# WINCH COMMAND "{cmd}" BEGIN:')
        #     if winch_status not in [WINCH_CMD_STOP, WINCH_CMD_NONE]:
        #         print(f'{round(time.time(), 2)} WIN CTL REVERSE: SPEED->low')
        #         time.sleep(2)
        #     print(f'{round(time.time(), 2)} WIN CTL REVERSE: FORWARD->high')
        #     print(f'{round(time.time(), 2)} WIN CTL REVERSE: REVERSE->low')
        #     print(f'{round(time.time(), 2)} WIN CTL REVERSE: SPEED->high')
        #     winch_status = WINCH_CMD_UPCAST

        # elif cmd == WinchCmd.WINCH_CMD_START:
            
        #     print(f'############# WINCH COMMAND "{cmd}" BEGIN:')
        #     if winch_status not in [WINCH_CMD_STOP, WINCH_CMD_NONE]:
        #         # really shouldn't be in motion for gostart, but hey...
        #         print(f'WIN CTL GOSTART: SPEED->low')
        #         time.sleep(2)

        #     # we need to get the simulator going with motion
        #     cmd_msg["command"] = WINCH_CMD_DOWNCAST
        #     # simulator_pub.publish(TOPIC_WINCH_MOTION_COMMAND, json.dumps(CMD).encode())
        #     print(f'{round(time.time(), 2)} WIN CTL GOSTART: REVERSE->high')
        #     print(f'{round(time.time(), 2)} WIN CTL GOSTART: FORWARD->low')
        #     print(f'{round(time.time(), 2)} WIN CTL GOSTART: SPEED->high')
        #     winch_status = WINCH_CMD_DOWNCAST

    status, err = share_new_winch_status(winch, Path("payouts"))
    if err:
        print(f'winctl:winmon: ERROR getting initial winch status')


    err = save_payout(status, Path('last_payouts'))
    if err:
        print(f"winctl:wincmd: ERROR GET LAST Payout Edge Counts")

    wincmd_sub.loop_stop()
