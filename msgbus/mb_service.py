#!/usr/bin/env python3

import argparse
import logging
import os
import paho.mqtt.client as paho
import random
import sys
# from threading import Thread
import time

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient


parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]))
parser.add_argument('-t', '--topic-root', dest='topicroot', help='Topic root to subscribe to', 
                    default='testtopic')
parser.add_argument("-e", "--endpoint", action="store",
                    default='aqe93b4u3dqbs-ats.iot.us-west-2.amazonaws.com',
                    dest="endpoint", help="Your AWS IoT custom endpoint")
parser.add_argument("-r", "--ca_file", action="store",
                    default='/home/rift-ox/awsiot/root-CA.crt',
                    dest="rootCAPath", help="Root CA file path")
parser.add_argument("-c", "--cert", action="store",
                    default='/home/rift-ox/awsiot/ro-rp-1.cert.pem',
                    dest="certificatePath", help="Certificate file path")
parser.add_argument("-k", "--key", action="store",
                    default='/home/rift-ox/awsiot/ro-rp-1.private.key',
                    dest="privateKeyPath", help="Private key file path")
# parser.add_argument("-p", "--port", action="store", dest="port", type=int, default=8883, help="Port number override")
args = parser.parse_args()

lgr : logging.Logger = logging.getLogger(__name__)
stdhdlr = logging.StreamHandler(sys.stdout)
lgr.setLevel(logging.DEBUG)
lgr.addHandler(stdhdlr)
#

broker = 'localhost'
port = 1883

def connect_mqtt(client_id):
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            lgr.debug(f"{client._client_id.decode()}: Connected to MQTT Broker!")
        else:
            lgr.error(f"{client._client_id.decode()}: Failed to connect, return code: {rc}\n")

    def on_disconnect(client, userdata, rc):
        lgr.debug(f"{client._client_id.decode()}: Disconnected with result code: {rc}")

    # Set Connecting Client ID
    client = paho.Client(client_id)
    if client == 0:
        lgr.error("Error creating Paho Client()")
        return None
    
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    return client

def on_publish(client, userdata, rc):
    lgr.debug(f"{client._client_id.decode()}: published a msg")
    # print(f"{client._client_id.decode()}: published a msg")
    pass

def on_message(client, userdata, msg):
    # print(dir(client))
    # lgr.debug(f"Received msg {msg.payload.decode()} on topic {msg.topic} from {client._client_id.decode()}")
    lgr.debug(f"{msg.payload.decode()} on topic {msg.topic}")
    # print(f"{client._client_id.decode()}: received msg {msg.payload.decode()} from topic {msg.topic}")

    # send to AWS
    print(type(msg.payload.decode()))
    pubinfo = myAWSIoTMQTTClient.publish('jsg/ro/test', msg.payload.encode('utf-8'), QoS=2)
    pubinfo.wait_for_publish()
    if not pubinfo.is_published():
        lgr.error("error publiishing")

    pass

topic = f'{args.topicroot}/#'
lgr.debug(f'Subscribing to topic: {args.topicroot}/#')

client_id = os.path.basename(f'{sys.argv[0]}-0')
subclient = connect_mqtt(client_id)
subclient.on_message = on_message
subclient.connect(broker, port)
subclient.subscribe(f'{args.topicroot}/#', qos=2)
subclient.loop_start()

endpoint = args.endpoint
awsTopic = 'jsg/ro/test'
awsPort = 8883
rootCAPath = args.rootCAPath
certificatePath = args.certificatePath
privateKeyPath = args.privateKeyPath

myAWSIoTMQTTClient = AWSIoTMQTTClient('ro-rp-1')
myAWSIoTMQTTClient.configureEndpoint(endpoint, awsPort)
myAWSIoTMQTTClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

# Connect and subscribe to AWS IoT
myAWSIoTMQTTClient.connect()

# pubclient = connect_mqtt("pubber")
# pubclient.on_publish = on_publish
# pubclient.connect(broker, port)
# pubclient.loop_start()
# pubinfo = pubclient.publish(args.topicroot, payload=f"my first mqtt msg".encode("utf-8"), qos=0)
# time.sleep(1)


# time.sleep(2)

msgnum = 1

try:
    while True:
        # pubinfo = pubclient.publish(f"{args.topicroot}/test", payload=f"my mqtt msg {msgnum}".encode("utf-8"), qos=0)
        # pubinfo.wait_for_publish()
        # if not pubinfo.is_published():
        #     lgr.error("error publiishing")
        # msgnum += 1
        # pubinfo = myAWSIoTMQTTClient.publish(f"{awsTopic}", payload=f"my mqtt msg {msgnum}".encode("utf-8"), qos=0)
        # pubinfo.wait_for_publish()
        # if not pubinfo.is_published():
        #     lgr.error("error publiishing")
        msgnum += 1
        time.sleep(2)

except KeyboardInterrupt as e:
    pass

finally:
    myAWSIoTMQTTClient.disconnect()
    subclient.disconnect()
    time.sleep(1)



