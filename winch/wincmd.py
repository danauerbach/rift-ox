#!/usr/bin/env python3

import json
import logging
from pathlib import Path
import queue
import threading
import time
from typing import Tuple, Union

import paho.mqtt.client as mqtt

from .dio_cmds import DIOCommander
from .winch import Winch

from . import WINCH_CMD_LIST, WinchCmd


def wincmd_loop(cfg: dict, winch_status_q: queue.Queue, quit_evt : threading.Event):

    # internal queue to take message from MQTT client callback
    # and forward to main winctl loop
    def on_cmd_msg(client, userdata, message):

        msg_str = message.payload.decode('utf-8')
        print(f'winctl:wincmd_loop: : CMD RCVD: {msg_str}')
        msg_json = json.loads(msg_str)
        cmd_q.put(msg_json)

    def on_connect(client, userdata, flags, rc):
        if rc==0:
            print("winctl:wincmd: connected OK: {client}")
        else:
            print("winctl:wincmd: Bad connection for {client} Returned code: ", rc)
            client.loop_stop()

    def on_disconnect(client, userdata, rc):
        print("client disconnected ok")

    def on_cmd_subscribe(client, userdata, mid, granted_qos):
        print("Subscribed: "+str(mid)+" "+str(granted_qos))

    def _on_pause_publish(client, userdata, mid):
        print("winctl:wincmd:pause_pub: {client} mid= "  ,mid)

    def get_payout_fn(name: Path) -> Path:
        ops_dir = Path(cfg['rift-ox-pi']['OPS_DIR'])

        payout_fpath: Path
        if str(Path.home()).startswith('/Users/'):   # hack because dev dir path on Dan's computer is not th same as ~/dev on productionb Pi's
            payout_fpath = Path.home().joinpath('dev/rift-ox', ops_dir, name)             # pause at these depths in meters
        else:
            payout_fpath = Path.home().joinpath(ops_dir, name)             # pause at these depths in meters

        Path.mkdir(payout_fpath, parents = True, exist_ok = True)
        return payout_fpath
    
    def save_payout(status: dict, fn: Path):
        ts = status["ts"]
        payout_depth = status["depth_m"]
        with open(get_payout_fn(fn), mode='a') as pofl:
            pofl.write(f'{ts:<26}, {payout_depth}\r')
        return

    def share_new_winch_status(winch: Winch, fname: Path) -> Tuple[dict, bool]:
        status, err = winch.status()
        if err:
            return {}, True
        else:
            winch_status_q.put(status)
            save_payout(status, fname)
            return status, False

    mqtt_host : str = cfg["mqtt"]["HOST"]
    mqtt_port : int = cfg["mqtt"]["PORT"]
    payout_log_file: str = cfg['rift-ox-pi']['PAYOUT_FN']
    cmd_q = queue.Queue()

    wincmd_sub = mqtt.Client('wincmd-sub')
    wincmd_sub.on_connect = on_connect
    wincmd_sub.on_disconnect = on_disconnect
    wincmd_sub.on_subscribe = on_cmd_subscribe
    wincmd_sub.on_message = on_cmd_msg
    wincmd_sub.connect(mqtt_host, mqtt_port)
    res, _ = wincmd_sub.subscribe(cfg["mqtt"]["WINCH_CMD_TOPIC"], qos=2)
    if res != mqtt.MQTT_ERR_SUCCESS:
        print(f'winmon:wincmd ERROR subscribing to {cfg["mqtt"]["WINCH_CMD_TOPIC"]}')
        print(f'winmon:wincmd shutting down')
        quit_evt.set()
        time.sleep(.25)
    else:
        wincmd_sub.loop_start()

        # simulator_pub = winmqtt.winmon_pubber('winmon-simul-pub')
        # simulator_pub.loop_start

    dio_cmndr: DIOCommander = DIOCommander(cfg)
    winch: Winch = Winch(dio_cmndr)

    last_winch_state = ''

    # get initial winch status
    _, err = share_new_winch_status(winch, Path(payout_log_file))
    if err:
        print(f'winctl:winmon: ERROR getting initial winch status')

    while not quit_evt.is_set():

        status, err = share_new_winch_status(winch, Path(payout_log_file))
        if err:
            print(f'winctl:winmon: ERROR getting winch status')
        else:
            if status['state'] != last_winch_state:
                last_winch_state = status['state']
                state_json = json.dumps(status)
                print(f'winctl:winmon: WINCH STATE: {state_json}')

        cmd_msg = ""
        try:
            cmd_msg = cmd_q.get(block=True, timeout=0.25)
            cmd_q.task_done()
        except queue.Empty as em:
            # print('winctl:wincmd: NO WINCH COMMAND message in cmd_q queue')
            continue
        except Exception as e:
            print(f'winctl:wincmd: Error receiving msg from cmd_q Queue: {e}')
            continue

        cmd = cmd_msg['command'].upper()
        if cmd not in WINCH_CMD_LIST:
            print(f'winctl:wincmd: INVALID COMMAND ===>>> {cmd}')
            continue

        
        if cmd == WinchCmd.WINCH_CMD_START.value:
            winch.start()

        # elif cmd == WinchCmd.WINCH_CMD_STOP.value:
        #     winch.stop()

        elif cmd == WinchCmd.WINCH_CMD_PAUSE.value:
            winch.pause()

        elif cmd == WinchCmd.WINCH_CMD_DOWNCAST.value:
            winch.down_cast()

        elif cmd == WinchCmd.WINCH_CMD_STOP_AT_MAX_DEPTH.value:
            winch.stop_at_bottom()

        elif cmd == WinchCmd.WINCH_CMD_UPCAST.value:
            winch.up_cast()

        elif cmd == WinchCmd.WINCH_CMD_UPSTAGE.value:
            winch.up_stage()

    
    status, err = share_new_winch_status(winch, Path(payout_log_file))
    if err:
        print(f'winctl:winmon: ERROR getting final winch status')


    # err = save_payout(status, Path('last_payouts'))
    # if err:
    #     print(f"winctl:wincmd: ERROR GET LAST Payout Edge Counts")

    wincmd_sub.loop_stop()
