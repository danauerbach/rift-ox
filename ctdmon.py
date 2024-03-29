#!/usr/bin/env python3

import argparse
import json
from os.path import abspath, expanduser
import queue
import shlex
import signal
import sys
import threading
import time

import paho.mqtt.client as mqtt
from awscrt import mqtt as awsmqtt
from awsiot import mqtt_connection_builder

import config
from sbe19v2plus.sbe33_serialport import SBE33SerialDataPort

SBE33_MENU_TOGGLE_CMD = '@'
COMMANDS_CTD = ['getcd', 'getsd', 'gethd', 'ds', 'tt', 'startnow', 'stop', 'wake',
                'pumpon', 'pumpoff', 'initlogging', 'outputexecutedtag',
                'datetime=', 'qs', 'autorun=', 'ignoreswitch=',
                'setvolttype', 'setvoltsn', 'volt', 'outputsal=', 'profilemode']
COMMANDS_SBE33 = [str(num) for num in range(1,10)]


def process_commands(ctd : SBE33SerialDataPort):

    while not ctd.quit_evt.is_set():

        the_input = input('ro> ')
        if the_input:
            cmd, *args = shlex.split(the_input)
            cmd = the_input.lower()
            # cmd = cmd.lower()
            print(f'command: {cmd}')
        else:
            cmd=""
            ctd.enqueue_command(cmd, eol='\r')

        if cmd in ['quit']:
            # ctd.enqueue_command('stop', eol='\r')
            # time.sleep(3)
            ctd.quit_evt.set()

        elif cmd =='help':
            print('Commands:')
            print('stop: Stop CTD and data acq')
            print('initlogging: erase CTD internal storage and prep for data acq')
            print('startnow: Start CTD and data acquisition')
            print('quit: quit application (DOES NOT stop CTD data acq)')
    
        # elif cmd == 'ds':
        #     ctd.enqueue_command(cmd, eol='\r')

        elif cmd == 'wake':
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.startswith("outputexecutedtag="):
            ctd.enqueue_command(cmd, '\r')

        elif cmd.startswith("echo="):
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.startswith("outputformat="):
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.startswith("navg="):
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.startswith("ignoreswitch="):
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.startswith("autorun="):
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.startswith("outputsal="):
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.startswith("setvolttype"):
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.startswith("setvoltsn"):
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.startswith("volt"):
            ctd.enqueue_command(cmd, eol='\r')
            time.sleep(3)
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.lower() == 'profilemode':
            cmd = "mp"
            ctd.enqueue_command(cmd, eol='\r')
            time.sleep(3)
            ctd.enqueue_command(cmd, eol='\r')
            ctd.enqueue_command("getcd", eol='\r')

        elif cmd.lower() == 'startnow':
            ctd.enqueue_command(cmd, eol='\r')
            ctd.serial_port_cmd_q.join()
            ctd.ctd_status[ctd.CTD_STATE] = ctd.CTD_STATE_ACQUIRING_DATA

        elif cmd.lower() == 'stop':
            ctd.ctd_status[ctd.CTD_STATE] = ctd.CTD_STATE_COMMAND_PROMPT
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.lower() == 'ctlc':
            ctd.ctd_status[ctd.CTD_STATE] = ctd.CTD_STATE_COMMAND_PROMPT
            ctd.enqueue_command("\x03", eol='\r')

        elif cmd.lower() in COMMANDS_CTD:
            ctd.enqueue_command(cmd, eol='\r')

        elif cmd.lower() in COMMANDS_SBE33:
            ctd.enqueue_command(cmd, eol='\n')

        elif cmd==SBE33_MENU_TOGGLE_CMD:
            ctd.toggle_sbe33_menu()

        else:
            print(f'Error: unsupported command: {cmd+"."}')

        time.sleep(2)

    print('user input thread shutting down...')
    
    return


def data_relay_loop(cfg: dict, data_q : queue.Queue, quit_evt : threading.Event):

    client : mqtt.Client = mqtt.Client('ctdmon')
    client.connect('localhost', 1883)
    client.loop_start()

    # Callback when connection is accidentally lost.
    def on_connection_interrupted(connection, error, **kwargs):
        print("Connection interrupted. error: {}".format(error))

    # Callback when an interrupted connection is re-established.
    def on_connection_resumed(connection, return_code, session_present, **kwargs):
        print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

    skip_aws: bool = cfg['rift-ox-pi']['SKIP_AWS']
    client_id = cfg['mqtt']['AWS_RIFT_OX_CLIENT_ID']
    endpoint = cfg['mqtt']['AWS_ENDPOINT']
    aws_topic = cfg['mqtt']['AWS_DATA_TOPIC']
    port = cfg['mqtt']['AWS_PORT']
    rootca_fn = abspath(expanduser(cfg['mqtt']['AWS_ROOT_CA_FILE']))
    cert_fn = abspath(expanduser(cfg['mqtt']['AWS_CERT_FILE']))
    privkey_fn = abspath(expanduser(cfg['mqtt']['AWS_PRIV_KEY_FILE']))
    if not skip_aws:
       # Create a MQTT connection using AWS SDK
        awsclient = mqtt_connection_builder.mtls_from_path(
            endpoint=endpoint,
            port=port,
            cert_filepath=cert_fn,
            pri_key_filepath=privkey_fn,
            ca_filepath=rootca_fn,
            on_connection_interrupted=on_connection_interrupted,
            on_connection_resumed=on_connection_resumed,
            client_id=client_id,
            clean_session=False,
            keep_alive_secs=30)

        connect_future = awsclient.connect()
        # Future.result() waits until a result is available
        connect_future.result()
        print("awsclient connected!")

    while not quit_evt.is_set():

        try:
            msg = data_q.get(block=True, timeout=1)
            data_q.task_done()

            # add client_id & winch state (NYI)
            msg['c_id'] = client_id
            msg['wsta'] = "NYI"
            # Convert the dictionary to bytes
            json_str = json.dumps(msg)
            bytes_data = json_str.encode("utf-8")
            # Print the bytes data
            client.publish(cfg["mqtt"]["CTD_DATA_TOPIC"], bytes_data, qos=2)
            if not skip_aws:
                awsclient.publish(
                    topic=aws_topic,
                    payload=json_str,
                    qos=awsmqtt.QoS.AT_LEAST_ONCE)

        except queue.Empty as e:
            continue
        else:
            pass
            #TODO put pucloish to AWS here...

    if not skip_aws:
        disconnect_future = awsclient.disconnect()
        disconnect_future.result()

    client.loop_stop()
    client.disconnect()


def interrupt_handler(signum, frame):

    # print(f'Handling signal {signum} ({signal.Signals(signum).name}).')

    quit_evt.set()

    # do whatever...
    time.sleep(1)
    sys.exit(0)

def main(quit_evt : threading.Event):

    signal.signal(signal.SIGINT, interrupt_handler)

    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--serialport", help="serial port to connect to", 
                        default="/dev/ttyUSB1", type=str)
    parser.add_argument("-b", "--baud", help="baud rate", 
                        default="9600", type=str)
    parser.add_argument('--max-alt-voltage', help="VA500 full range voltage in Volts", 
                        default=5, type=int)

    args = parser.parse_args()

    serialport = args.serialport
    baud = int(args.baud)
    altimeter_max_volts = args.max_alt_voltage

    # ctd_config = sbe19v2plus.config.Config(
    #     mode = sbe19v2plus.config.SBE19Mode.PROFILE_MODE, 
    #     output_format = sbe19v2plus.config.SBE19OutputFmt.OUTPUT_FORMAT_1,
    #     data_chan_volt0=True, data_chan_volt2=True
    # )
    cfg = config.read()
    if cfg == None:
        print(f'ctdmon: ERROR unable to read rift-ox.toml config file. Quitting.')
        sys.exit(1)

    data_q : queue.Queue = queue.Queue()
    data_relay_thr = threading.Thread(target=data_relay_loop, args=(cfg, data_q, quit_evt), name="ctdmon:datarelay")
    data_relay_thr.start()

    ext_cmd_q: queue.Queue = queue.Queue()   # this queue accepts 'cmds' which are passed directly, as is, to the SBE33 serialport
    ctd_io = SBE33SerialDataPort("serialport.log", quit_evt, data_q, ext_cmd_q, serialport, baud, altimeter_max_volts)
    ctd_io.start()

    def _on_connect(client, userdata, flags, rc):
        if rc==0:
            print("ctdmon: connected OK: {client}")
        else:
            print("winctl:winmon: Bad connection for {client} Returned code: ", rc)
            client.loop_stop()

    def _on_disconnect(client, userdata, rc):
        print("winctl:winmon: client disconnected ok")

    def _on_message(client : mqtt.Client, userdata, message):
        # read commands and put in local queue for sending to SBE33 data serial port
        payload = message.payload.decode("utf-8")
        print(f'Ext CTD Command rcvd: {payload}')
        ext_cmd_q.put(payload)

    # set up MQTT subscriber to listen for external commands that need to be sent to the SBE33 data port
    mqtt_host = cfg['mqtt']['HOST']
    mqtt_port = cfg['mqtt']['PORT']
    cmd_t = cfg['mqtt']['CTD_CMD_TOPIC']
    external_cmd_client = mqtt.Client('ctdmon-ext-cmd')
    external_cmd_client.on_connect = _on_connect
    external_cmd_client.on_disconnect = _on_disconnect
    external_cmd_client.on_message = _on_message
    external_cmd_client.connect(mqtt_host, mqtt_port)
    external_cmd_client.subscribe(cmd_t, qos=2)
    external_cmd_client.loop_start()



    # set_config(ctd_io)

    #start the interactive command processor
    while process_commands(ctd_io):
        pass
    
    ctd_io.quit()



quitting = False

if __name__ == '__main__':

    quit_evt = threading.Event()

    main(quit_evt)
