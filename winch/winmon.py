#!/usr/bin/env python3

from enum import Enum, auto
import json
import logging
import queue
import threading
import time

import paho.mqtt.client as mqtt

from winch import pausemon

from . import WinchDir, WinchStateName, WinchCmd

def winmon_loop(cfg: dict, winch_status_q: queue.Queue, quit_evt : threading.Event):
    """Listen to data_q queue for data records to check
    CTD depth and CTD altimeter as well as the winch PAYOUT sensors."""


    def stop_and_pause_at_bottom():
        #TODO SEND ALERT MSG
        #TODO TELL WINCH TO STOP
        #TODO touch HOLD_FLAG_FILE and record modified time
        #TODO loop every 5 minutes until HOLD_FLAG_FILE modified time is 15 minutes in the past
        #TODO READ BOTINFO file
        #TODO TELL WINCH to START UPCAST
        #TODO SEND ALERT MSG
        pass

    def _on_connect(client, userdata, flags, rc):
        if rc==0:
            client.connected_flag=True #set flag
            print("winctl:winmon: connected OK: {client}")
        else:
            print("winctl:winmon: Bad connection for {client} Returned code: ", rc)
            client.loop_stop()

    def _on_disconnect(client, userdata, rc):
        client.connected_flag=False #set flag
        print("winctl:winmon: client disconnected ok")

    def _on_data_message(client : mqtt.Client, userdata, message):
        payload = message.payload.decode("utf-8")
        payjson = json.loads(payload)
        if data_q: data_q.put(payjson)

    def _on_ctl_publish(client, userdata, mid):
        print("winctl:winmon: {client} mid= "  ,mid)

    def _on_data_subscribe(client, userdata, mid, granted_qos):
        print("winctl:winmon: Subscribed: "+str(mid)+" "+str(granted_qos))

    def update_depth(cur: float, last: float, depth: float) -> (float, float):
        if last == None:
            last = depth
        else:
            last = cur
        cur = depth
        return cur, last
    
    def get_winch_status(q: queue.Queue) -> (dict, bool):
        status: dict
        try:
            status = q.get()
        except queue.Empty as em:
            return {}, True
        else:
            q.task_done()
        return status, False
    
    data_q : queue.Queue = queue.Queue()

    
    # STATIONARY_MAX_DIFF : float = float(cfg["winch"]["STATIONARY_MAX_DIFF"]) # meters. depth difference less than this is considered sattionary
    MIN_ALTITUDE : float = float(cfg["winch"]["MIN_ALTITUDE"])                # meters. DOn't get any closer to the seafloor than this
    MAX_DEPTH : float = float(cfg["winch"]["MAX_DEPTH"])                      # meters. GO NO FARTHER
    STAGING_DEPTH : float = float(cfg["winch"]["STAGING_DEPTH"])              # meters. This is depth of initial pause at start of the downcast

    data_t : str = cfg["mqtt"]["CTD_DATA_TOPIC"]
    winch_command_topic : str = cfg["mqtt"]["WINCH_CMD_TOPIC"]

    mqtt_host : str = cfg["mqtt"]["HOST"]
    mqtt_port : int = cfg["mqtt"]["PORT"]

    # lets make a mqtt pubber to send winctl msgs. 
    # using mqtt instead of an internal queue will make it easier for external 
    # clients to send winch ctl instructions in an "emergency"
    wincmd_pub : mqtt.Client = mqtt.Client('winmon-ctl-pub')
    wincmd_pub.on_connect = _on_connect
    wincmd_pub.on_disconnect = _on_disconnect
    wincmd_pub.on_publish = _on_ctl_publish
    wincmd_pub.connect(mqtt_host, mqtt_port)
    wincmd_pub.loop_start()

    datamon_sub : mqtt.Client = mqtt.Client('winmon-data-sub')
    datamon_sub.on_connect = _on_connect
    datamon_sub.on_disconnect = _on_disconnect
    datamon_sub.on_subscribe = _on_data_subscribe
    datamon_sub.on_message = _on_data_message
    datamon_sub.connect(mqtt_host, mqtt_port)
    datamon_sub.subscribe(data_t, qos=2)
    datamon_sub.loop_start()

    pause_thr = threading.Thread(target=pausemon.pause_monitor, args=(cfg, quit_evt), name="pausemon")
    pause_thr.start()
    
    # assume we're at the surface, aka "Parked"
    cur_direction  : WinchDir = WinchDir.DIRECTION_NONE.value
    cur_depth_ctd: float = 0
    last_depth_ctd: float = None
    cur_depth: float = 0
    last_depth: float = None
    cur_altitude: float = MAX_DEPTH

    empty_count: int = 0

    while not quit_evt.is_set():

        if not winch_status_q.empty():
            status, err = get_winch_status(winch_status_q)
            if err:
                print('winctl:winmon ERROR retrieving winch status from queue')
            else:
                winch_status = status
                cur_direction = winch_status["dir"]
                cur_payouts = winch_status["payouts"]
                cur_state = winch_status["state"]

        try:
            data_dict : dict = data_q.get(block=True, timeout=1)
            data_q.task_done()
            empty_count = 0
        except queue.Empty as e:
            print('winctl:winmon: INFO no data message in data_q queue')
            empty_count += 1
            if empty_count > 60:
                print('winctl:winmon: still no CTD, PAYOUT or LATCH data')
                empty_count = 0
            continue
        except Exception as e:
            print(f'winctl:winmon: ERROR receiving data msg: {e}')
            continue

        # set Direction and log change in motion state
        if data_dict.get('record_type') == 'payoutdata':
            cur_depth, last_depth = update_depth(cur_depth, last_depth, data_dict["payout_m"])            

        elif data_dict.get('record_type') == 'ctddata':
            cur_depth_ctd, last_depth_ctd = update_depth(cur_depth_ctd, last_depth_ctd, data_dict["depth_m"])            
            cur_altitude = data_dict["altitude"]

        if cfg["rift-ox-pi"]["REALTIME_CTD"]:
            # Let's compare winch payout readings with depth from CTD
            delta: float = cur_depth - cur_depth_ctd
            if (cur_depth_ctd > 10) and ((delta / cur_depth_ctd) > 0.03):
                print(f'winctl:winmon: WARNING: winch PAYOUT reading differs from CTD DEPTH by {delta} meters at CTD depth of: {cur_depth_ctd}.')

        if (cur_direction == WinchDir.DIRECTION_DOWN.value):

            if (cur_depth > STAGING_DEPTH) and \
                (cur_state == WinchStateName.STAGING.value):
                    # just hit stagin depth on way down, call winch.state.pause() pause
                pub_winch_cmd(wincmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_DOWN_PAUSE)

            if (cur_altitude < MIN_ALTITUDE):
                print(f'winctl:winmon: Winch is stopping within {MIN_ALTITUDE}m of the seafloor.')
                pub_winch_cmd(wincmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_STOP_AT_MAX_DEPTH.value)
                stop_and_pause_at_bottom()
                continue

            elif (cur_depth > MAX_DEPTH):
                pub_winch_cmd(wincmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_STOP_AT_MAX_DEPTH.value)
                stop_and_pause_at_bottom()
                print(f'winctl:winmon: Winch is stopping at MAX depth {MAX_DEPTH} meters.')
                continue

        elif (cur_direction == WinchDir.DIRECTION_UP.value):
            
            if (cur_depth < STAGING_DEPTH) and \
                (cur_state in [WinchStateName.UPCASTING.value]):
                # just hit stagin depth on way up, let's pause here]
                pub_winch_cmd(wincmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_PAUSE.value)



    wincmd_pub.loop_stop()
    datamon_sub.loop_stop()
    pause_thr.join()

def pub_winch_cmd(pubber: mqtt.Client, topic: str, cmd: str, **kwargs) -> bool:
    cmd: dict = {
        "command": cmd
    }
    for key, val in kwargs.items():
        cmd[key] = val
    msg_info = pubber.publish(topic, json.dumps(cmd).encode(), qos=2)
    msg_info.wait_for_publish(1)
    if not msg_info.is_published():
        print(f'winctl:winmon: ERROR publishing msg {cmd} to topic {topic}')
    return msg_info.is_published()

