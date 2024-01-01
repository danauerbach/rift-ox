#!/usr/bin/env python3

import json
from os.path import getmtime
from pathlib import Path
import queue
from threading import Thread, Event
import time

import paho.mqtt.client as mqtt


def pause_monitor(cfg: dict, quit_evt: Event):
    """waits the later of PAUSE_DURATION_SECS.
    Repeated PAUSE commands while pause already active
    adds another PAUSE_DUR to the pause end time"""

    def _on_connect(client, userdata, flags, rc):
        if rc==0:
            client.connected_flag=True #set flag
            print("winctl:pausemon: connected OK: {client}")
        else:
            print("winctl:pausemon: Bad connection for {client} Returned code: ", rc)
            client.loop_stop()

    def _on_disconnect(client, userdata, rc):
        client.connected_flag=False #set flag
        print("winctl:pausemon: client disconnected ok")

    def _on_ctl_publish(client, userdata, mid):
        print("winctl:pausemon: {client} mid= "  ,mid)

    def _on_pause_message(client : mqtt.Client, userdata, message):
        payload = message.payload.decode("utf-8")
        pause_q.put(payload)


    mqtt_host : str = cfg["mqtt"]["HOST"]
    mqtt_port : int = cfg["mqtt"]["PORT"]
    pause_dur: int = int(cfg["rift-ox-pi"]["PAUSE_DURATION_SECS"])
    pause_t = cfg["mqtt"]["WINCH_PAUSE_TOPIC"]
    pause_q: queue.Queue = queue.Queue()
    pause_active: bool = False

    CMD_START: dict = {
        "command": "start"
    }

    pausemon_sub : mqtt.Client = mqtt.Client('pausemon-data-sub')
    pausemon_sub.on_connect = _on_connect
    pausemon_sub.on_disconnect = _on_disconnect
    pausemon_sub.on_message = _on_pause_message
    pausemon_sub.connect(mqtt_host, mqtt_port)
    pausemon_sub.subscribe(pause_t, qos=2)
    pausemon_sub.loop_start()

    wincmd_pub : mqtt.Client = mqtt.Client('pausemon-ctl-pub')
    wincmd_pub.on_connect = _on_connect
    wincmd_pub.on_disconnect = _on_disconnect
    wincmd_pub.on_publish = _on_ctl_publish
    wincmd_pub.connect(mqtt_host, mqtt_port)
    wincmd_pub.loop_start()

    while not quit_evt.set():

        pause_msg: str = ""

        try:
            pause_msg = pause_q.get(block=True, timeout=1)
            pause_q.task_done()
        except queue.Empty as e:
            pass
        except Exception as e:
            print(f'winctl:pausemon: ERROR receiving data msg: {e}')
            continue

        # ignore pause if pause already active
        if (pause_msg == "pause"):
            if not pause_active:
                pause_active = True
                pause_start = time.time()
                pause_end = pause_start + pause_dur
                print(f'winctl:pausemon: PAUSE starting  t:{time.time()} dur={pause_dur} secs at={pause_start} ending={pause_end}')
            else:
                # extend pause_end by another pause_dur
                print(f'winctl:pausemon: PAUSE extending t:{time.time()} dur={pause_dur} secs at={pause_start} ending={pause_end}')
                pause_end += pause_dur

        if pause_active:
            # check modified date on pause flag file and add another pause_dur secs
            print(f'winctl:pausemon: PAUSE active    t:{time.time()} dur={pause_dur} secs at={pause_start} ending={pause_end}')

            if time.time() > pause_end:
                print(f'winctl:pausemon: PAUSE ending t:{time.time()} over after {pause_end - pause_start} secs')
                pause_active = False
                wincmd_pub.publish(cfg["mqtt"]["WINCH_CMD_TOPIC"],  json.dumps(CMD_START).encode(), qos=2)
                
