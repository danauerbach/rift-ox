# Listens to mqtt topics on locahost
from argparse import ArgumentParser, Namespace
import paho.mqtt.client as paho
import signal
import sys, os
import time

parser = ArgumentParser()
parser.add_argument('topic', help="Topic to subscribe to", type=str)

args = parser.parse_args()

print(f"topic: {args.topic}")


def make_subber(id : str, topic : str) -> paho.Client :
    
    def on_connect(id, userdata, flags, rc):
        if rc == 0:
            print(f"{id._client_id.decode()}: Connected to MQTT Broker!")
        else:
            print(f"{id._client_id.decode()}: Failed to connect, return code: {rc}\n")

    def on_disconnect(id, userdata, rc):
        print(f"{id._client_id.decode()}: Disconnected with result code: {rc}")


    subber = paho.Client(f" subber '{id}' for {topic}")
    subber.on_connect = on_connect
    subber.on_disconnect = on_disconnect

    return subber


def on_message(client, userdata, msg):
    print(f"{msg.topic}: {str(msg.payload)}")

#sub1 : paho.Client = make_subber('subber-1', 'top1')
sub1 = make_subber('subber-1', args.topic)
sub1.on_message = on_message
sub1.connect('localhost', 1883)
sub1.subscribe(args.topic)
sub1.loop_start()

# Our signal handler
def signal_handler(signum, frame) -> None : 
    print("Signal ID:", signum, " Frame: ", frame)  
    sub1.disconnect()
    time.sleep(1)
    sys.exit(-1)
 
# Handling SIGINT 
signal.signal(signal.SIGINT, signal_handler)


while True:
    time.sleep(.1)
