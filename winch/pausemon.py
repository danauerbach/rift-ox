#!/usr/bin/env python3

import json
from os.path import getmtime
from pathlib import Path
import queue
from threading import Thread, Event
import time

import paho.mqtt.client as mqtt

from winch import WinchCmd


def pause_monitor(cfg: dict, quit_evt: Event):
    """waits the later of PAUSE_DURATION_SECS.
    Repeated PAUSE commands while pause already active
    adds another PAUSE_DUR to the pause end time"""

    def _on_connect(client, userdata, flags, rc):
        if rc==0:
            print("winctl:pausemon: connected OK: {client}")
        else:
            print("winctl:pausemon: Bad connection for {client} Returned code: ", rc)
            client.loop_stop()

    def _on_disconnect(client, userdata, rc):
        print("winctl:pausemon: client disconnected ok")

    def _on_cmd_publish(client, userdata, mid):
        print("winctl:pausemon: {client} mid= "  ,mid)

    def _on_pause_message(client : mqtt.Client, userdata, message):
        payload = message.payload.decode("utf-8")
        pause_q.put(payload)


    CMD_START: dict = {
        "command": WinchCmd.WINCH_CMD_START.value
    }

    pause_q: queue.Queue = queue.Queue()

    mqtt_host : str = cfg["mqtt"]["HOST"]
    mqtt_port : int = cfg["mqtt"]["PORT"]
    pause_t = cfg["mqtt"]["WINCH_PAUSE_TOPIC"]
    pausemon_sub : mqtt.Client = mqtt.Client('pausemon-data-sub')
    pausemon_sub.on_connect = _on_connect
    pausemon_sub.on_disconnect = _on_disconnect
    pausemon_sub.on_message = _on_pause_message
    pausemon_sub.connect(mqtt_host, mqtt_port)
    pausemon_sub.subscribe(pause_t, qos=2)
    pausemon_sub.loop_start()

    wincmd_pub : mqtt.Client = mqtt.Client('pausemon-cmd-pub')
    wincmd_pub.on_connect = _on_connect
    wincmd_pub.on_disconnect = _on_disconnect
    wincmd_pub.on_publish = _on_cmd_publish
    wincmd_pub.connect(mqtt_host, mqtt_port)
    wincmd_pub.loop_start()

    default_pause_dur: float = float(cfg["winch"]["PAUSE_DURATION_SECS"])
    bottle_pause_dur = float(cfg["winch"]["BOTTLE_PAUSE_DURATION_SECS"])
    pause_dur: float = 0.0
    pause_active: bool = False
    pause_msg: str = ""
    pause_start: float = 0
    pause_end: float = 0

    while not quit_evt.is_set():

        try:
            pause_msg = ''
            pause_msg = pause_q.get(block=True, timeout= 0.15)
            pause_q.task_done()
        except queue.Empty as e:
            pass
        except Exception as e:
            print(f'winctl:pausemon: ERROR receiving data msg: {e}')
            continue

        # ignore pause if pause already active
        t = time.time()
        pause_msg = pause_msg.lower()
        if (pause_msg in ["pause", "bottle-pause"]):
            
            if pause_msg == "pause":
                pause_dur = default_pause_dur
            elif pause_msg == "bottle-pause":
                pause_dur = bottle_pause_dur

            if not pause_active:
                pause_active = True
                pause_start = t
                pause_end = pause_start + pause_dur
                print(f'winctl:pausemon: PAUSE starting  t:{time.time()} dur={pause_dur} secs at={pause_start} ending={pause_end}')
            else:
                # extend pause_end by another pause_dur
                print(f'winctl:pausemon: PAUSE extending t:{time.time()} dur={pause_dur} secs at={pause_start} ending={pause_end}')
                pause_end += pause_dur

        if pause_active:
            # check modified date on pause flag file and add another pause_dur secs
            # print(f'winctl:pausemon: PAUSE active    t:{time.time()} dur={pause_dur} secs at={pause_start} ending={pause_end}')

            if t > pause_end:
                print(f'winctl:pausemon: PAUSE ending t:{time.time()} over after {pause_end - pause_start} secs')
                pause_active = False
                wincmd_pub.publish(cfg["mqtt"]["WINCH_CMD_TOPIC"],  json.dumps(CMD_START).encode(), qos=2)
                
