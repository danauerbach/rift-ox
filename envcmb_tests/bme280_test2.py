#!/usr/bin/env python3
#-----------------------------------------------------------------------------

import argparse
import json
import logging
import os
import time
import sys

import qwiic_bme280
import paho.mqtt.client as paho

TOPIC_DEFAULT = "/rift-ox/sensors/bme280/0"
BME280_I2C_ADDRESS = 0x77

parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]))
parser.add_argument('-t', '--topic', help="mqtt topic to publish to", default=TOPIC_DEFAULT)
parser.add_argument('-b', '--broker', help="mqtt broker host", default="localhost")
parser.add_argument('-p', '--port', help="mqtt broker port", type=int, default="1883")
args = parser.parse_args()

BROKER = args.broker
PORT = args.port
TOPIC = args.topic

lgr : logging.Logger = logging.getLogger('asd')
stdhdlr = logging.StreamHandler(sys.stdout)
lgr.setLevel(logging.DEBUG)
lgr.addHandler(stdhdlr)


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
    pass

def on_subscribe(client, userdata, mid, granted_qos):
    lgr.DEBUG(f'Client {client._client_id.decode()} subscribed to ')


def runExample():

	mySensor = qwiic_bme280.QwiicBme280(BME280_I2C_ADDRESS)

	if mySensor.connected == False:
		lgr.error("The Qwiic BME280 device isn't connected to the system. Please check your connection")
		return

	mySensor.begin()

	# setup the sensor
	mySensor.filter = 1  		# 0 to 4 is valid. Filter coefficient. See 3.4.4
	mySensor.standby_time = 0 	# 0 to 7 valid. Time between readings. See table 27.
	
	mySensor.over_sample = 5			# 0 to 16 are valid. 0 disables temp sensing. See table 24.
	mySensor.pressure_oversample = 5	# 0 to 16 are valid. 0 disables pressure sensing. See table 23.
	mySensor.humidity_oversample = 1	# 0 to 16 are valid. 0 disables humidity sensing. See table 19.
	mySensor.mode = mySensor.MODE_NORMAL # MODE_SLEEP, MODE_FORCED, MODE_NORMAL is valid. See 3.3

	mqtt_client_id = os.path.basename(sys.argv[0])
	pubclient = connect_mqtt(mqtt_client_id)
	pubclient.on_publish = on_publish
	pubclient.connect(BROKER, PORT)
	pubclient.loop_start()
      
	lgr.debug(f'Publishing to {TOPIC}...')

	while True:
		# print("Humidity:\t%.3f" % mySensor.humidity)
		# print("Pressure:\t%.3f" % mySensor.pressure)	
		# print("Altitude:\t%.3f" % mySensor.altitude_feet)
		# print("Temperature:\t%.2f\n" % mySensor.temperature_fahrenheit)

		msg = {
            "ts": round(time.time(), 3),
			"bme280_humi": round(mySensor.humidity, 2),
			"bme280_pres": round(mySensor.pressure, 2),
			"bme280_alt_m": round(mySensor.altitude_meters, 2),
			"bme280_temp_c": round(mySensor.temperature_celsius, 2)
		}
		pubinfo = pubclient.publish(TOPIC, payload=json.dumps(msg).encode("utf-8"), qos=2, )

		time.sleep(1)


if __name__ == '__main__':
	try:
		runExample()
	except (KeyboardInterrupt, SystemExit) as exErr:
		sys.exit(0)

