#!/usr/bin/env python3

import json
import logging
from pathlib import Path
import queue
import threading
import time

import paho.mqtt.client as mqtt

from .dio_cmds import DIOCommander
from winch.states import Winch

from . import WINCH_CMD_LIST, WinchCmd


def wincmd_loop(cfg: dict, winch_status_q: queue.Queue, quit_evt : threading.Event):

    # internal queue to take message from MQTT client callback
    # and forward to main winctl loop
    def on_CMD(client, userdata, message):

        msg_str = message.payload.decode('utf-8')
        print(f'wincmd_loop: cmd rcvd: {msg_str}')
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
        Path.mkdir(ops_dir, parents = True, exist_ok = True)
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

    dio_cmndr: DIOCommander = DIOCommander(cfg, simulation=cfg["rift-ox-pi"]["SIMULATION"])
    winch: Winch = Winch(dio_cmndr)

    # get initial winch status
    init_status, err = share_new_winch_status(winch, Path("payouts"))
    if err:
        print(f'winctl:winmon: ERROR getting initial winch status')

    while not quit_evt.is_set():

        print(f'wincmd_loop: top')

        status, err = share_new_winch_status(winch, Path("payouts"))
        if err:
            print(f'winctl:winmon: ERROR getting winch status')

        cmd_msg = ""
        try:
            cmd_msg = cmd_q.get(block=True, timeout=1.0)
            cmd_q.task_done()
        except queue.Empty as em:
            print('winctl:wincmd: NO WINCH COMMAND message in cmd_q queue')
            continue
        except Exception as e:
            print(f'winctl:wincmd: Error receiving msg from cmd_q Queue: {e}')
            continue

        cmd = cmd_msg['command'].lower()
        if cmd not in WINCH_CMD_LIST:
            print(f'winctl:wincmd: INVALID COMMAND ===>>> {cmd}')
            continue

        
        if cmd == WinchCmd.WINCH_CMD_START.value:
            winch.start()

        elif cmd == WinchCmd.WINCH_CMD_STOP.value:
            # currently an alias for PAUSE
            winch.stop()

        elif cmd == WinchCmd.WINCH_CMD_DOWNCAST.value:
            winch.down_cast()

        elif cmd == WinchCmd.WINCH_CMD_STOP_AT_MAX_DEPTH.value:
            winch.stop_at_bottom()

        elif cmd == WinchCmd.WINCH_CMD_UPCAST.value:
            winch.up_cast()

        elif cmd == WinchCmd.WINCH_CMD_UPSTAGE.value:
            winch.up_stage()

        elif cmd == WinchCmd.WINCH_CMD_PARK.value:
            """Parking is moving winch backwards until LATCH signal
            is detected and then paying out for < 1sec so that bullet will latch.
            This should leave the winch in the (physically) LATCHED position
            
            NOTE we are using dio_cmndr.<command> directly to control winch while bypassing the 
            because WInch state machine because Parking requires multiple winch 
            commands all while Parking and the Winch state machine can handle this."""

            print(f'PARKING: STARTING')

            # check current latch edge count
            start_latch_edge_cnt, err = winch.get_latch_edge_count()
            if err:
                print('dio_cmds:park UNABLE to get LATCH SENSOR state when PARKING')
                return

            new_latch_edge_count = start_latch_edge_cnt
            print(f'PARKING: LATCH EDGE CNT: {start_latch_edge_cnt}')
        
            print(f'PARKING: UP CASTING')
            dio_cmndr.up_cast() #### NOT SURE THIS IS A GOOD IDEA
            latch_found = (new_latch_edge_count > start_latch_edge_cnt)
            print(f'PARKING: LATCH FOUND - INITIAL: {latch_found}')
            while not latch_found:
                # check fr new LATCH edge count
                new_latch_edge_count, err = winch.get_latch_edge_count()
                if err:
                    winch.stop_winch() #### NOT SURE THIS IS A GOOD IDEA
                    print('dio_cmds:park UNABLE to get LATCH SENSOR state when PARKING')
                    return
                latch_found = new_latch_edge_count > start_latch_edge_cnt
                print(f'PARKING: LATCH FOUND - LOOP: {latch_found}')

                # need a pretty fast loop here while up_casting
                time.sleep(0.01)    

            print(f'PARKING: LATCH FOUND: {latch_found}')
            print(f'PARKING: STOPPING WINCH')
            # latch has been found
            dio_cmndr.stop_winch()
            # presumably we are on the LATCH now. drop a fraction of a sec (an inch or two)
            print(f'PARKING: RELEASING LATCH')
            dio_cmndr.latch_release()
            time.sleep(1) # REMOVE AFTER TESTING
            print(f'PARKING: DOWNCASTING FOR {cfg["winch"]["PARKING_DOWNCAST_MS"]}ms')
            dio_cmndr.down_cast(stop_after_ms=int(cfg["winch"]["PARKING_DOWNCAST_MS"]))
            dio_cmndr.stop_winch()

        elif cmd == WinchCmd.WINCH_CMD_SETSTATE.value:
            winch.set_state()

    
    status, err = share_new_winch_status(winch, Path("payouts"))
    if err:
        print(f'winctl:winmon: ERROR getting final winch status')


    # err = save_payout(status, Path('last_payouts'))
    # if err:
    #     print(f"winctl:wincmd: ERROR GET LAST Payout Edge Counts")

    wincmd_sub.loop_stop()
