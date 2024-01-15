#!/usr/bin/env python3

from enum import Enum, auto
import json
import logging
from pathlib import Path
import queue
import threading
import time
from typing import Tuple, Union

import paho.mqtt.client as mqtt
import toml

from winch import pausemon

from . import WinchDir, WinchStateName, WinchCmd, pub_cmd
from .pause_depths import PauseDepths



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
            status = q.get(block=True, timeout=0.1)
        except queue.Empty as em:
            return {}, True
        else:
            q.task_done()
        return status, False
    
    data_q : queue.Queue = queue.Queue()

    MIN_ALTITUDE : float = float(cfg["winch"]["MIN_ALTITUDE"])    # meters. DOn't get any closer to the seafloor than this
    MAX_DEPTH : float = float(cfg["winch"]["MAX_DEPTH"])          # meters. GO NO FARTHER
    STAGING_DEPTH : float = float(cfg["winch"]["STAGING_DEPTH"])  # meters. This is depth of initial pause at start of the downcast


    cdt_cmd_t : str = cfg["mqtt"]["CTD_CMD_TOPIC"]
    cdt_data_t : str = cfg["mqtt"]["CTD_DATA_TOPIC"]
    winch_command_topic : str = cfg["mqtt"]["WINCH_CMD_TOPIC"]
    
    pause_depths_fn = Path(cfg['bottles']['PAUSE_DEPTHS_FN'])
    if str(Path.home()).startswith('/Users/'):   # hack because dev dir path on Dan's computer is not th same as ~/dev on productionb Pi's
        pause_depths: PauseDepths = PauseDepths(Path.home().joinpath('dev/rift-ox/dev/config', pause_depths_fn))             # pause at these depths in meters
    else:
        pause_depths: PauseDepths = PauseDepths(Path.home().joinpath('config', pause_depths_fn))             # pause at these depths in meters

    mqtt_host : str = cfg["mqtt"]["HOST"]
    mqtt_port : int = cfg["mqtt"]["PORT"]

    # lets make a mqtt pubber to send winctl msgs. 
    # using mqtt instead of an internal queue will make it easier for external 
    # clients to send winch ctl instructions in an "emergency"
    cmd_pub : mqtt.Client = mqtt.Client('winmon-ctl-pub')
    cmd_pub.on_connect = _on_connect
    cmd_pub.on_disconnect = _on_disconnect
    cmd_pub.connect(mqtt_host, mqtt_port)
    cmd_pub.loop_start()

    datamon_sub : mqtt.Client = mqtt.Client('winmon-data-sub')
    datamon_sub.on_connect = _on_connect
    datamon_sub.on_disconnect = _on_disconnect
    datamon_sub.on_subscribe = _on_data_subscribe
    datamon_sub.on_message = _on_data_message
    datamon_sub.connect(mqtt_host, mqtt_port)
    datamon_sub.subscribe(cdt_data_t, qos=2)
    datamon_sub.loop_start()

    # assume we're at the surface, aka "Parked"
    winch_status: dict = {}
    cur_direction  : str = WinchDir.DIRECTION_NONE.value
    cur_depth_ctd: float = 0
    cur_depth: float = 0
    cur_state: str = ""
    last_state: str = ''
    cur_altitude: float = 100  # meters, limit of alt range
    max_depth_reached: float = 0.0  # will change on the way down

    empty_count: int = 0

    while not quit_evt.is_set():

        status, err = get_winch_status(winch_status_q)
        if len(status.keys()) > 0:
            winch_status = status
            cur_direction = winch_status["dir"]
            cur_depth = float(winch_status["depth_m"])
            last_state = cur_state
            cur_state = winch_status["state"]

            # heading up from bottom, lets reread pause_depths...
            if (last_state == WinchStateName.MAXDEPTH.value) and \
                (cur_state == WinchStateName.UPCASTING.value):
                pause_depths.refresh()
                #TODO KILL33

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
                    print('winctl:winmon: still NO CTD data')
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

        print(f'winctl:winmon: winch status: {winch_status}')
        if (cur_direction == WinchDir.DIRECTION_DOWN.value):

            max_depth_reached = cur_depth if cur_depth > max_depth_reached else max_depth_reached

            if (cur_depth > STAGING_DEPTH) and \
                (cur_state == WinchStateName.STAGING.value):
                    # just hit stagin depth on way down, call winch.state.pause() pause
                pub_cmd(cmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_PAUSE.value)
                pub_cmd(cmd_pub, cdt_cmd_t, "init")

            if (cur_altitude < MIN_ALTITUDE):
                print(f'winctl:winmon: Winch is stopping within {MIN_ALTITUDE}m of the seafloor.')
                pub_cmd(cmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_STOP_AT_MAX_DEPTH.value)
                stop_and_pause_at_bottom()
                continue

            elif (cur_depth > MAX_DEPTH):
                pub_cmd(cmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_STOP_AT_MAX_DEPTH.value)
                stop_and_pause_at_bottom()
                print(f'winctl:winmon: Winch is stopping at MAX depth {MAX_DEPTH} meters.')
                continue

        elif (cur_direction == WinchDir.DIRECTION_UP.value):
            
            if (cur_state in [WinchStateName.UPCASTING.value]):

                if (cur_depth < STAGING_DEPTH):
                    # just hit stagin depth on way up, let's pause here]
                    pub_cmd(cmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_UPSTAGE.value)
                    pub_cmd(cmd_pub, cdt_cmd_t, "stop")

                else:
                    next_pause = pause_depths.get_next_depth(max_depth=max_depth_reached)
                    if next_pause:
                        if cur_depth < next_pause:
                            pause_depths.use_next_depth()
                            pub_cmd(cmd_pub, winch_command_topic, WinchCmd.WINCH_CMD_PAUSE.value)


        time.sleep(0.1)

    # wincmd_pub.loop_stop()
    # datamon_sub.loop_stop()
