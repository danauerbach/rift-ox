#!/usr/bin/env python
#-----------------------------------------------------------------------------
# qwiic_env_bme280_ex4.py
#
# Simple Example for the Qwiic BME280 Device
#------------------------------------------------------------------------
#
# Written by  SparkFun Electronics, May 2019
# 
# This python library supports the SparkFun Electroncis qwiic 
# qwiic sensor/board ecosystem on a Raspberry Pi (and compatable) single
# board computers. 
#

#
# Do you like this library? Help support SparkFun. Buy a board!
#
#==================================================================================
# Copyright (c) 2019 SparkFun Electronics
#
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to deal 
# in the Software without restriction, including without limitation the rights 
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all 
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
# SOFTWARE.
#==================================================================================
# Example 4 - port of the Arduino example 4
#

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

import logging
import time
import json
import argparse
#import busio
import qwiic_bme280
import sys
import socket
from datetime import datetime, timezone, timedelta
import pytz

AllowedActions = ['both', 'publish', 'subscribe']

# Read in command-line parameters
def parseArgs():

    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host", help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--ca_file", action="store", required=True, dest="rootCAPath", help="Root CA file path")
    parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
    parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
    parser.add_argument("-p", "--port", action="store", dest="port", type=int, default=8883, help="Port number override")
    parser.add_argument("-id", "--client_id", action="store", dest="clientId", default="ro-rp-1",
                        help="Targeted client id")
    parser.add_argument("-t", "--topic", action="store", dest="topic", default="sdk/test/Python", help="Targeted topic")
    parser.add_argument("-m", "--mode", action="store", dest="mode", default="publish",
                        help="Operation modes: %s"%str(AllowedActions))
    parser.add_argument("-M", "--message", action="store", dest="message", default="Hello World!",
                        help="Message to publish")

    args = parser.parse_args()

    return args

def runExample():

    args = parseArgs()
    print(args)
    host = args.host
    rootCAPath = args.rootCAPath
    certificatePath = args.certificatePath
    privateKeyPath = args.privateKeyPath
    port = args.port
    clientId = args.clientId
    topic = args.topic

    if args.mode not in AllowedActions:
        parser.error("Unknown --mode option %s. Must be one of %s" % (args.mode, str(AllowedActions)))
        exit(2)

    if (not args.certificatePath or not args.privateKeyPath):
        parser.error("Missing credentials for authentication.")
        exit(2)

    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

    # AWSIoTMQTTClient connection configuration
    myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
    myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

    # Connect and subscribe to AWS IoT
    myAWSIoTMQTTClient.connect()
    if args.mode == 'both' or args.mode == 'subscribe':
        myAWSIoTMQTTClient.subscribe(topic, 1, customCallback)

    print("Pausing to give AWS IoT a breath...")
    time.sleep(5)

    mySensor = qwiic_bme280.QwiicBme280()

    if mySensor.connected == False:
        print("The Qwiic BME280 device isn't connected to the system. Please check your connection", \
            file=sys.stderr)
        return

    mySensor.begin()

    # setup the sensor
    mySensor.filter = 1         # 0 to 4 is valid. Filter coefficient. See 3.4.4
    mySensor.standby_time = 0   # 0 to 7 valid. Time between readings. See table 27.

    mySensor.over_sample = 5            # 0 to 16 are valid. 0 disables temp sensing. See table 24.
    mySensor.pressure_oversample = 5    # 0 to 16 are valid. 0 disables pressure sensing. See table 23.
    mySensor.humidity_oversample = 1    # 0 to 16 are valid. 0 disables humidity sensing. See table 19.
    mySensor.mode = mySensor.MODE_NORMAL # MODE_SLEEP, MODE_FORCED, MODE_NORMAL is valid. See 3.3

    while True:
        # print("Humidity:\t%.3f" % mySensor.humidity)

        # print("Pressure:\t%.3f" % mySensor.pressure)    

        # print("Altitude:\t%.3f" % mySensor.altitude_feet)

        # print("Temperature:\t%.2f\n" % mySensor.temperature_fahrenheit)

        payload = {}
        payload["Humidity"]    = mySensor.humidity
        payload["Pressure"]    = mySensor.pressure
        payload["Temperature"] = mySensor.temperature_fahrenheit
        payload["thingId"]     = "ro-rpi-1"
        payload["hostname"]    = socket.gethostname()
        tz = pytz.timezone("UTC")
        timestamp = round(datetime.now(tz).timestamp() * 1000)
        payload["timestamp"]   = timestamp
        
        messageJson = json.dumps(payload).strip()
        myAWSIoTMQTTClient.publish(topic, messageJson, 1)
        if args.mode == 'publish':
            print('Published topic %s: %s' % (topic, messageJson))


        time.sleep(1)


if __name__ == '__main__':
    try:
        runExample()
    except (KeyboardInterrupt, SystemExit) as exErr:
        sys.exit(0)

