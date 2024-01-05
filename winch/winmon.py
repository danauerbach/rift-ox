#!/usr/bin/env python3

from enum import Enum, auto
import json
import logging
import queue
import threading
import time
from typing import Tuple

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
            print("winctl:winmon: connected OK: {client}")
        else:
            print("winctl:winmon: Bad connection for {client} Returned code: ", rc)
            client.loop_stop()

    def _on_disconnect(client, userdata, rc):
        print("winctl:winmon: client disconnected ok")

    def _on_data_message(client : mqtt.Client, userdata, message):
        payload = message.payload.decode("utf-8")
        payjson = json.loads(payload)
        if data_q: data_q.put(payjson)

    def _on_data_subscribe(client, userdata, mid, granted_qos):
        print("winctl:winmon: Subscribed: "+str(mid)+" "+str(granted_qos))

    def get_winch_status(q: queue.Queue) -> Tuple[dict, bool]:
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

    # assume we're at the surface, aka "Parked"
    cur_direction  : str = WinchDir.DIRECTION_NONE.value
    cur_depth_ctd: float = 0
    cur_depth: float = 0
    cur_state: str = ""
    cur_altitude: float = MAX_DEPTH
    MAX_DEPTH_REACHED = False
    MAX_DEPTH_PAYOUT_EDGES = -1

    empty_count: int = 0

    while not quit_evt.is_set():

        status, err = get_winch_status(winch_status_q)
        if len(status.keys()) > 0:
            winch_status = status
            cur_direction = winch_status["dir"]
            cur_depth = float(winch_status["depth_m"])
            cur_state = winch_status["state"]
                
        data_dict = {}
        try:
            data_dict : dict = data_q.get(block=True, timeout=0.1)
            data_q.task_done()
            empty_count = 0
        except queue.Empty as e:
            # print('winctl:winmon: NO CTDDATA message in data_q queue')
            if cfg["rift-ox-pi"]["REALTIME_CTD"]:
                empty_count += 1
                if empty_count > 60:
                    print('winctl:winmon: still NO CTD, PAYOUT or LATCH data')
                    empty_count = 0
        except Exception as e:
            print(f'winctl:winmon: ERROR receiving data msg: {e}')
            continue

        # set Direction and log change in motion state
        if data_dict:
            if data_dict.get('type') == 'ctd':
                # NOTE: PRIMARY DEPTH INFO COMES FROM PAYOUT SENSORS
                #       THIS IS FOR COMPARISON ONLY
                cur_depth_ctd = data_dict["depth_m"]
                cur_altitude = data_dict["alt_m"]

                if cfg["rift-ox-pi"]["REALTIME_CTD"]:
                    # Let's compare winch payout readings with depth from CTD
                    delta: float = cur_depth - cur_depth_ctd
                    if (cur_depth_ctd > 10) and ((delta / cur_depth_ctd) > 0.005):
                        # report difference if more than 0.5%
                        print(f'winctl:winmon: WARNING: winch PAYOUT reading differs from CTD DEPTH by {delta} meters at CTD depth of: {cur_depth_ctd}.')

        # print(f'winctl:winmon: cur_depth: {cur_depth}')
        if (cur_direction == WinchDir.DIRECTION_DOWN.value):

            # print(f'cur_direction: {cur_direction}')
            # print(f'cur_state: {cur_state}')
            # print(f'STAGING_DEPTH: {STAGING_DEPTH}')
            # print(f'{cur_depth > STAGING_DEPTH}; {cur_state == WinchStateName.STAGING.value}')
            if (cur_depth > STAGING_DEPTH) and \
                (cur_state == WinchStateName.STAGING.value):
                    # just hit stagin depth on way down, call winch.state.pause() pause
                pub_winch_cmd(wincmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_PAUSE.value)

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
                pub_winch_cmd(wincmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_UPSTAGE.value)

        time.sleep(0.1)

    wincmd_pub.loop_stop()
    datamon_sub.loop_stop()

def pub_winch_cmd(pubber: mqtt.Client, topic: str, command: str, **kwargs) -> bool:
    cmd: dict = {
        "command": command
    }
    for key, val in kwargs.items():
        cmd[key] = val
    msg_info = pubber.publish(topic, json.dumps(cmd).encode(), qos=2)
    msg_info.wait_for_publish(1)
    if not msg_info.is_published():
        print(f'winctl:winmon: ERROR publishing msg {cmd} to topic {topic}')
    return msg_info.is_published()

