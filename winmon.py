#!/usr/bin/env python3

from enum import Enum
import json




import os.path
from pathlib import Path
import queue
import signal
import sys
import threading 
import time
import paho.mqtt.client as mqtt

import msgbus
############
# MQTT clients: 1 sub, 1 pub
#

home_dir = str(Path.home())

BOTTLE_INFO_FILE = os.path.join(home_dir, 'dev/rift-ox/ops/bottle_fire_depths')
HOLD_FLAG_FILE = os.path.join(home_dir, 'dev/rift-ox/ops/hold')
WINCH_CTL_MSG_GOSTART = 'gostart'
WINCH_CTL_MSG_STOP = 'stop'
WINCH_CTL_MSG_FORWARD = 'forward'
WINCH_CTL_MSG_REVERSE = 'reverse'
WINCH_CTL_MSG_NONE = 'none'
WINCH_CTL_MSG_LIST = {
    WINCH_CTL_MSG_GOSTART,
    WINCH_CTL_MSG_STOP,
    WINCH_CTL_MSG_FORWARD,
    WINCH_CTL_MSG_REVERSE,
    WINCH_CTL_MSG_NONE
}

class Direction(Enum):
    DIRECTION_NONE = 'NONE'
    DIRECTION_UP = 'UP'
    DIRECTION_DOWN = 'DOWN'



def on_log(client, userdata, level, buf):
   print(f'LOG: {buf}')

def on_message(client : mqtt.Client, userdata, message):
   
    #TODO need to check topic and route payload accordingly
    payload = message.payload.decode("utf-8")
    payjson = json.loads(payload)
    # if payjson["client_id"] in ['sim-pusher', 'ctdmon']:
    #     data_q.put(payjson)
    if message.topic in [msgbus.TOPIC_CTD_SENSOR_DATA,
                         msgbus.TOPIC_CTD_SENSORS_DATA_SIMUL]:
        data_q.put(payjson)

def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag=True #set flag
        print("connected OK: {client}")
    else:
        print("Bad connection for {client} Returned code: ", rc)
        client.loop_stop()

def on_disconnect(client, userdata, rc):
   client.connected_flag=False #set flag
   print("client disconnected ok")

# def on_publish(client, userdata, mid):
#    print("{client} mid= "  ,mid)

def on_subscribe(client, userdata, mid, granted_qos):
    print("Subscribed: "+str(mid)+" "+str(granted_qos))

def winmon_subber(client_id : str, topic : str or list[str], 
                  broker : str = 'localhost', port : int = 1883) -> mqtt.Client:

    client = mqtt.Client(client_id)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe
    # client.on_log = on_log
    client.on_message = on_message
    client.connect(broker, port)
    client.subscribe(topic, qos=2)

    return client

def winmon_pubber(client_id : str, broker : str = 'localhost', port : int = 1883) -> mqtt.Client:

    client = mqtt.Client(client_id)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    # client.on_publish = on_publish
    # client.on_log = on_log
    client.on_message = on_message
    client.connect(broker, port)

    return client


class BottleInfo():

    def __init__(self, botinfo_filename : str):

        self.botinfo_filename = botinfo_filename
        self.botinfo_timestamp = os.path.getmtime(self.botinfo_filename)
        self.target_downcast_depths = []
        self.target_upcast_depths = []

        # self.update_botinfo()

    def next_bottle_depth(self, direction : int, cur_depth : float) -> int or None:

        if direction == Direction.DIRECTION_DOWN:
            target_list = self.target_downcast_depths 
        elif direction == Direction.DIRECTION_UP:
            target_list = self.target_upcast_depths 
        else:
            target_list = None

        if not target_list:  # list is empty
            return None
        else:
            return target_list[0]  # return next depth

    def bottle_complete(self, direction, d):

        if direction == Direction.DIRECTION_DOWN:
            target_list = self.target_downcast_depths 
        elif direction == Direction.DIRECTION_UP:
            target_list = self.target_upcast_depths 
        else:
            print(f'UNEXPECTED {Direction.DIRECTION_NONE} during bottle closing at depth {d}')
            return 

        try:
            ndx = target_list.index(d)
            del target_list[ndx]
        except ValueError:
            print(f'Bottle depth {d} not found in depths list {self.target_downcast_depths} during {direction}-cast.')

    def update_botinfo(self, botinfo_dict : dict) -> bool:

        # botinfo = json.load(self.botinfo_filename)
        self.target_downcast_depths = sorted(botinfo_dict["downcast_depths"])
        self.target_upcast_depths = sorted(botinfo_dict["upcast_depths"], reverse=True)


def data_mon_loop(data_q : queue.Queue, bottle_q : queue.Queue, quit_evt : threading.Event):

    def stop_and_wait_at_bottom():
        #TODO SEND ALERT MSG
        #TODO TELL WINCH TO STOP
        #TODO touch HOLD_FLAG_FILE and record modified time
        #TODO loop every 5 minutes until HOLD_FLAG_FILE modified time is 15 minutes in the past
        #TODO READ BOTINFO file
        #TODO TELL WINCH to START UPCAST
        #TODO SEND ALERT MSG
        pass

    def stop_for_bottle_fire():
        #TODO SEND ALERT MSG
        #TODO TELL WINCH TO STOP
        #TODO WAIT 
        #TODO SEND ALERT MSG
        pass

    last_depth : float or None = None # depth is increaing positive on downcast
    direction  : Direction = Direction.DIRECTION_NONE   # -1==upcasting; 0==stationary; 1==downcasting
    stopped : bool = False
    prev_data_timestamp : float = 0

    STATIONARY_DIFF = 0.05 # meters. depth difference less than this is considered sattionary
    MIN_ALTITUDE = 5       # meters. DOn't get any closer to the seafloor than this
    MAX_DEPTH = 8          # meters. GO NO FARTHER
    CMD_GOSTART = 'gostart'
    CMD_GOHOME = 'gohome'
    CMD_STOP = 'stop'


    BOTTLE_FIRE_DEPTHS = {
        "downcast": [4],
        "upcast": [4,7]
    }

    # lets make a mqtt pubber to send winctl msgs. 
    # using mqtt instead of an internal queue will make it easier for external 
    # clients to send winch ctl instructions in an "emergency"
    winctl_pub = winmon_pubber('winmon-ctl-pub')
    winctl_pub.loop_start()


    botinfo = BottleInfo(BOTTLE_INFO_FILE)

    while not quit_evt.is_set():

        try:
            data_dict : dict = data_q.get(block=True, timeout=5)
            data_q.task_done()
        except queue.Empty as e:
            # print('no data message in queue')
            continue
        except Exception as e:
            print(f'ERROR receiving data msg: {e}')

        ### NEED TO THINK ABOUT THIS APPTOACH A LTITEL MORE
        try:
            botinfo = bottle_q.get(block=False)
            bottle_q.task_done()
            botinfo_str = botinfo.decode('utf-8')
            botinfo.update_botinfo(json.loads(botinfo_str))
            print(f'Bottle info updated: {botinfo}')
        except queue.Empty as em:
            pass
        except Exception as e:
            print(f'Unexpected error reading bitfino: {e}')


        if data_dict['record_type'] == 'ctddata':

            # print(f'winmon_loop:data_q msg: {round(time.time(), 2)} {json.dumps(data_dict)}')

            cur_depth = data_dict["depth_m"]
            cur_altitude = data_dict["altitude"]
            if last_depth == None:
                last_depth = data_dict["depth_m"]

            # set Direction and log change in motion state
            if (abs(last_depth - cur_depth) < STATIONARY_DIFF) and (direction != Direction.DIRECTION_NONE):
                print(f'Winch is stopped')
                direction = Direction.DIRECTION_NONE
            elif ((cur_depth - last_depth) > STATIONARY_DIFF) and (direction != Direction.DIRECTION_DOWN):
                print(f'Winch is now RUN FORWARD (downcast)')
                direction = Direction.DIRECTION_DOWN
            elif ((cur_depth - last_depth) < -STATIONARY_DIFF) and (direction != Direction.DIRECTION_UP):
                print(f'Winch is now RUN REVERSE (upcast)')
                direction = Direction.DIRECTION_UP


            if (direction == Direction.DIRECTION_DOWN):

                if (cur_altitude < MIN_ALTITUDE):
                    print(f'Winch is stopping within {MIN_ALTITUDE}m of the seafloor.')
                    stopped = True
                    cmd = {
                        "command": "stop"
                    }
                    winctl_pub.publish(msgbus.TOPIC_WINCH_MOTION_COMMAND, json.dumps(cmd).encode())
                    #TODO stopped = false
                    continue

                elif (cur_depth > MAX_DEPTH):
                    print(f'Winch is stopping at MAX depth {MAX_DEPTH}m.')
                    stopped = True
                    cmd = {
                        "command": "stop"
                    }
                    winctl_pub.publish(msgbus.TOPIC_WINCH_MOTION_COMMAND, json.dumps(cmd).encode())
                    stop_and_wait_at_bottom()
                    #TODO stopped = false
                    continue

            target_depth : int or None = botinfo.next_bottle_depth(direction, cur_depth)

            if target_depth:
                if direction == Direction.DIRECTION_DOWN:
                    if target_depth < cur_depth:
                        stopped = True
                        print(f'Winch pausing for bottle firing at depth ~{target_depth}m during downcast')
                        cmd = {
                            "command": "stop"
                        }
                        winctl_pub.pub(msgbus.TOPIC_WINCH_MOTION_COMMAND, json.dumps(cmd).encode())
                        time.sleep(90)
                        botinfo.bottle_complete(direction, target_depth)
                        cmd = {
                            "command": WINCH_CTL_MSG_FORWARD
                        }
                        winctl_pub.pub(msgbus.TOPIC_WINCH_MOTION_COMMAND, json.dumps(cmd).encode())
                        stopped = False

                elif direction == Direction.DIRECTION_UP:
                    if target_depth > cur_depth:
                        stopped = True
                        # stop_for_bottle_fire()
                        print(f'Winch pausing for bottle firing at depth ~{target_depth}m during upcast')
                        cmd = {
                            "command": "stop"
                        }
                        winctl_pub.pub(msgbus.TOPIC_WINCH_MOTION_COMMAND, json.dumps(cmd).encode())
                        time.sleep(30)
                        botinfo.bottle_complete(direction, target_depth)
                        cmd = {
                            "command": WINCH_CTL_MSG_REVERSE
                        }
                        winctl_pub.pub(msgbus.TOPIC_WINCH_MOTION_COMMAND, json.dumps(cmd).encode())
                        stopped = False

        elif data_dict['record_type'] == 'command':
            cmd = data_dict['cmd']
            if cmd.lower() == 'goup':
                # SORT OF ESCAPE HATCH if we get stuck at the bottom.
                #TODO START WINCH in REVERSE
                pass

    winctl_pub.loop_stop()


def bottle_mon_loop(botinfo_fn : str, bottle_q : queue.Queue, quit_evt : threading.Event):


    bottle_complete : list[bool] = [0, 0, 0, 0, 0, 0]

    last_file_mod_time = os.path.getmtime(BOTTLE_INFO_FILE)

    while not quit_evt.is_set():

        if last_file_mod_time != os.path.getmtime(BOTTLE_INFO_FILE):

            print(f'Reading bottle depth file: {botinfo_fn}')

            with open(botinfo_fn, 'rt') as bif:

                try:
                    # convert as json to str then to bytes to make sure file contents are valid json
                    botinfo_dict = json.load(bif)
                    botinfo_bytes = json.dumps(botinfo_dict)
                    bottle_q.put(botinfo_bytes.encode())
                except Exception as e:
                    print(f'Error reading bottle info file: {e}')

        time.sleep(2)


def winctl_loop(quit_evt : threading.Event):


    # internal queue to take message from MQTT client callback
    # and forward to main winctl loop
    def on_ctl_msg(client, userdata, message):

        # print(f'winmon:on_ctl_msg: {message.payload}')
        msg_str = message.payload.decode('utf-8')
        msg_json = json.loads(msg_str)
        ctl_q.put(msg_json)
        # print(msg_json)

    ctl_q = queue.Queue()
    winctl_sub = winmon_subber('winmon-ctl-sub', [(msgbus.TOPIC_WINCH_MOTION_COMMAND, 2),
                                                  (msgbus.TOPIC_COMMANDS, 2)])
    winctl_sub.on_message = on_ctl_msg
    winctl_sub.loop_start()

    simulator_pub = winmon_pubber('winmo-simul-pub')
    simulator_pub.loop_start


    winch_status = WINCH_CTL_MSG_NONE

    while not quit_evt.is_set():

        try:
            ctl_msg = ctl_q.get(block=True, timeout=0.5)
            ctl_q.task_done()
        except queue.Empty as em:
            pass
        except Exception as e:
            print(f'Error receviing WIN CTL Queue msg: {e}')
        else:
            cmd = ctl_msg['command']
            if cmd in WINCH_CTL_MSG_LIST:
                # got a valid win ctl command
                if cmd == WINCH_CTL_MSG_STOP:

                    print(f'############# WINCH COMMAND "{cmd}" BEGIN')
                    if winch_status not in [WINCH_CTL_MSG_STOP, WINCH_CTL_MSG_NONE]:
                        #TODO set DIO speed pin 'low' using ttyACM0 serial port
                        print(f'{round(time.time(), 2)} WIN CTL: STOP: SPEED->low')
                        time.sleep(2) # wait 2 secs for winch deceleration before changing direction lines
                        #TODO set DIO FORWARD (sink) pin 'low' using ttyACM0 serial port
                        #TODO set DIO REVERSE (sink) pin 'low' using ttyACM0 serial port
                        print(f'{round(time.time(), 2)} WIN CTL: STOP: FORWARD->high')
                        print(f'{round(time.time(), 2)} WIN CTL: STOP: REVERSE->high')
                    winch_status = WINCH_CTL_MSG_STOP
                    print(f'############# WINCH COMMAND "{cmd}" END')

                elif cmd == WINCH_CTL_MSG_FORWARD:

                    print(f'############# WINCH COMMAND "{cmd}" BEGIN:')
                    if winch_status not in [WINCH_CTL_MSG_STOP, WINCH_CTL_MSG_NONE]:   # if in motion stop and wait for decel
                        #TODO set DIO speed pin 'low' using ttyACM0 serial port
                        print(f'WIN CTL FORWARD: SPEED->low (stopping before estting new direction)')
                        time.sleep(2)
                    print(f'{round(time.time(), 2)} WIN CTL FORWARD: REVERSE->high')
                    print(f'{round(time.time(), 2)} WIN CTL FORWARD: FORWARD->low')
                    print(f'{round(time.time(), 2)} WIN CTL FORWARD: SPEED->high')
                    winch_status = WINCH_CTL_MSG_FORWARD

                elif cmd == WINCH_CTL_MSG_REVERSE:

                    print(f'############# WINCH COMMAND "{cmd}" BEGIN:')
                    if winch_status not in [WINCH_CTL_MSG_STOP, WINCH_CTL_MSG_NONE]:
                        print(f'{round(time.time(), 2)} WIN CTL REVERSE: SPEED->low')
                        time.sleep(2)
                    print(f'{round(time.time(), 2)} WIN CTL REVERSE: FORWARD->high')
                    print(f'{round(time.time(), 2)} WIN CTL REVERSE: REVERSE->low')
                    print(f'{round(time.time(), 2)} WIN CTL REVERSE: SPEED->high')
                    winch_status = WINCH_CTL_MSG_REVERSE

                elif cmd == WINCH_CTL_MSG_GOSTART:
                    
                    print(f'############# WINCH COMMAND "{cmd}" BEGIN:')
                    if winch_status not in [WINCH_CTL_MSG_STOP, WINCH_CTL_MSG_NONE]:
                        # really shouldn't be in motion for gostart, but hey...
                        print(f'WIN CTL GOSTART: SPEED->low')
                        time.sleep(2)

                    # we need to get the simulator going with motion
                    ctl_msg["command"] = WINCH_CTL_MSG_FORWARD
                    simulator_pub.publish(msgbus.TOPIC_WINCH_MOTION_COMMAND, json.dumps(ctl_msg).encode())
                    print(f'{round(time.time(), 2)} WIN CTL GOSTART: REVERSE->high')
                    print(f'{round(time.time(), 2)} WIN CTL GOSTART: FORWARD->low')
                    print(f'{round(time.time(), 2)} WIN CTL GOSTART: SPEED->high')
                    winch_status = WINCH_CTL_MSG_FORWARD

            else:
                print(f'INVALID WINCH CTL COMMAND: {cmd}')

    winctl_sub.loop_stop()


def interrupt_handler(signum, frame):

    quit_evt.set()
    time.sleep(1)

    # print(f'Handling signal {signum} ({signal.Signals(signum).name}).')
    data_t.loop_stop()
    pubber.loop_stop()

    # datamon_thr.join()
    # botinfo_thr.join()

    # do whatever...
    time.sleep(1)
    sys.exit(0)



if __name__ == "__main__":

    quit_evt = threading.Event()

    data_q = queue.Queue()
    bottle_q = queue.Queue()

    signal.signal(signal.SIGINT, interrupt_handler)

    data_t = winmon_subber('win-subber', 
                           [(msgbus.TOPIC_CTD_SENSOR_DATA, 2),
                            (msgbus.TOPIC_CTD_SENSORS_DATA_SIMUL, 2),
                            ],
                           'localhost', 1883)
    data_t.loop_start()

    command_t = winmon_subber('win-commands', msgbus.TOPIC_COMMANDS, 'localhost', 1883)
    command_t.on_message
    command_t.loop_start()

    pubber = winmon_pubber('win-pubber', 'localhost', 1883)
    pubber.loop_start()

    winctl_thr = threading.Thread(target=winctl_loop, args=(quit_evt,))
    winctl_thr.start()

    datamon_thr = threading.Thread(target=data_mon_loop, args=(data_q, bottle_q, quit_evt))
    datamon_thr.start()

    botinfo_thr = threading.Thread(target=bottle_mon_loop, args=(BOTTLE_INFO_FILE, bottle_q, quit_evt))
    botinfo_thr.start()

    quit_evt.wait()

