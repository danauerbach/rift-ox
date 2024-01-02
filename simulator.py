#!/usr/bin/env python3

import argparse
import json
import logging
import queue
import signal
import sys
import threading
import time

import paho.mqtt.client as mqtt

import msgbus


SIMULATION_DOWNCAST = 'downcast'

parser = argparse.ArgumentParser()

parser.add_argument("--simulation", help="simulate RIFT-OX actions using MQTT messages",  
                    choices=['downcast'], type=str)

args = parser.parse_args()


def connector(client : str, broker : str = 'localhost', port : int = 1883, keep_alive=True) -> bool:
    """Attempts connection set delay to >1 to keep trying
    but at longer intervals. If runforever flag is true then
    it will keep trying to connect or reconnect indefinetly otherwise
    gives up after 3 failed attempts"""

    connflag : bool = False
    delay : int = 5
    badcount : int =0 # counter for bad connection attempts

    while not connflag and (badcount < 3):
        print("connecting to broker "+str(broker))
        #print("connecting to broker "+str(broker)+":"+str(port))
        print("Attempts ",str(badcount))
        time.sleep(delay)
        try:
            client.connect(broker,port,keep_alive)
            connflag=True
            print(f"connection to {broker}:{port} successful ")

        except:
            client.badconnection_flag=True
            print("connection failed "+str(badcount) + 'failed attempts.')
            badcount +=1
            connflag = False

    return connflag            
        


def client_loop(client, broker, port, keepalive):
    t = threading.Thread(target = client_loop, args=(client,broker,port,60), name='simul:client')
    t.start()

def simulate_downcast(ctd_simul : mqtt.Client, monitor_client : mqtt.Client, cmd_q : queue.Queue, start_evt : threading.Event) -> bool:
    """send CTD data and altimeter messages that 
    will simulate a downcast. Simulation leaves carousel 
    at simulated sea floor.
    
    Both CTD and Alimeter msgs will be generated at 
    DEPTH_DATA_RECS_PER_SEC times per second. The depth 
    will be increased at the rate of PAYOUT_RATE meters per second.
    
    If winch publishes 'WINCH_STOP' command has been received, 
    break out of downcast loop"""

    SEA_FLOOR_DEPTH = 30         # meters. Once at this depth, This will trigger altimeter proximity
    DEPTH_DATA_RECS_PER_SEC = 4  # CTD and Altimeter data sent per second 
    PAYOUT_RATE = .3             # m/s. Probably shouldn't try it with values > 1.0

    print('simulator: waiting for GOSTART command')
    direction = 'stop'
    start_evt.wait()


    cur_depth : int = 0  # current depth in meters
    while (cur_depth < SEA_FLOOR_DEPTH) and cur_depth >= 0:

        try:
            cmd_msg = cmd_q.get(block=False)
        except queue.Empty:
            pass
        else:
            cmd = cmd_msg['command']
            print(f'simulator:downcast {round(time.time(), 2)} received command: {cmd}')
            if cmd == 'reverse':
                direction = 'reverse'
            elif cmd == 'forward':
                direction = 'forward'
            else:
                direction = 'stop'

        if direction == 'forward':
            cur_depth += PAYOUT_RATE
        elif direction == 'reverse':
            cur_depth -= PAYOUT_RATE

        time.sleep(1/DEPTH_DATA_RECS_PER_SEC)
        payload = {
            'client_id': 'sim-pusher',
            'timestamp': round(time.time(), 2),
            'record_type': 'ctddata',
            'depth_m': round(cur_depth, 2),
            'altitude': round(SEA_FLOOR_DEPTH - cur_depth, 2)
        }
        ctd_simul.publish(msgbus.TOPIC_CTD_SENSORS_DATA_SIMUL, json.dumps(payload), qos=2)
        print(f'DOWNCAST SIMULATOR: Depth: {round(cur_depth, 2)}, Altitude: {round(SEA_FLOOR_DEPTH - cur_depth, 2)}')

            


def create_pubber_client(client_name : str, broker : str = 'localhost', port : int = 1883) -> mqtt.Client:

    client_id = client_name
    client = mqtt.Client(client_id)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    return client

# def on_message(client, userdata, message):
#     print("Message received: ",str(message.payload.decode("utf-8")))
#     if (message.topic == msgbus.TOPIC_COMMANDS):
#         msg_str = message.payload.decode("utf-8")
#         msg_json = json.loads(msg_str)
#         if msg_json["command"] == 'gostart':
#             print(f'starting simulation with "gostart"')
#             start_evt.set()

def on_connect(client : mqtt.Client, userdata, flags, rc):

    if rc==0:
        client.connected_flag=True #set flag
        print(f"connected OK: {client}")          
    else:
        print("Bad connection Returned code=",rc)
        client.loop_stop()  

def on_disconnect(client, userdata, rc):
   client.connected_flag=False #set flag
   print("client disconnected ok")

def on_publish(client, userdata, mid):
   print("In on_pub callback mid= "  ,mid)

def on_subscribe(client, userdata, mid, granted_qos):
    print("Subscribed: "+str(mid)+" "+str(granted_qos))

def simulation_monitor(client_id : str):

    client = mqtt.Client(client_id)
    # client.on_subscribe = on_subscribe
    # client.on_connect = on_connect
    # client.on_message = on_message

    return client


def interrupt_handler(signum, frame):

    # print(f'Handling signal {signum} ({signal.Signals(signum).name}).')
    monitor_client.loop_stop()
    simulator_client.loop_stop()

    # do whatever...
    time.sleep(1)
    sys.exit(0)


def on_cmd_msg(client, userdata, message):

    # print(f"CMD Message on topic {message.topic}: ",str(message.payload.decode("utf-8")))
    if (message.topic in [msgbus.TOPIC_COMMANDS,
                          msgbus.TOPIC_WINCH_MOTION_COMMAND]):
        msg_str = message.payload.decode("utf-8")
        print(f'simulation:on_ctl_msg: {round(time.time(), 2)} received msg: {msg_str}')
        msg_json = json.loads(msg_str)
        if msg_json['command'] in ['gostart', 'stop', 'forward', 'reverse']:
            cmd = {
                "command": msg_json['command']
            }
            if msg_json["command"] == 'gostart':
                start_evt.set()
            else:
                cmd_q.put(cmd)
            # elif msg_json['command'] == 'stop':
            # elif msg_json['command'] == 'forward':
            # elif msg_json['command'] == 'reverse':


if __name__ == "__main__":

    signal.signal(signal.SIGINT, interrupt_handler)

    if args.simulation == SIMULATION_DOWNCAST:

        print("Simulating DOWNCAST...")

        print('Constructing internal message Queue...')

        start_evt = threading.Event()

        monitor_client = simulation_monitor('sim-mon')
        monitor_client.on_message = on_cmd_msg
        monitor_client.connect('localhost', 1883)
        monitor_client.subscribe([(msgbus.TOPIC_WINCH_MOTION_COMMAND, 2),
                                  (msgbus.TOPIC_COMMANDS, 2)], qos=2)
        monitor_client.loop_start()
        cmd_q = queue.Queue()


        # create simlutor publish client
        simulator_client = create_pubber_client('sim-pusher', 'localhost', 1883)
        simulator_client.connect('localhost', 1883)
        simulator_client.loop_start()

        res = simulate_downcast(simulator_client, monitor_client, cmd_q, start_evt)

        monitor_client.loop_stop()
        simulator_client.loop_stop()



    