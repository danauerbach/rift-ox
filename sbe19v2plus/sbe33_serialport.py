#!/usr/bin/env python3

#import readline
import argparse
from datetime import datetime
import json
import os
import queue
import re
import shlex
import serial
import signal
import sys
import threading
import time
from typing import Union, List

import paho.mqtt.client as mqtt
import gsw

import config
import sbe19v2plus.config

class SBE33SerialDataPort():

    CTD_ACTIVE_DEVICE = 'active_device'
    CTD_ACTIVE_DEVICE_UNK = 'active_device_unk'
    CTD_ACTIVE_DEVICE_NONE = 'active_device_none'
    CTD_ACTIVE_DEVICE_SBE33 = 'active_device_sbe33'
    CTD_ACTIVE_DEVICE_SBE19PlusV2 = 'active_device_sbe19PlusV2'
    CTD_STATE = 'ctd_state'
    CTD_STATE_UNKNOWN = 'unknown'
    CTD_STATE_AWAKE = 'awake'
    CTD_STATE_ASLEEP = 'asleep'
    CTD_STATE_READING_GETCD_CONFIG = 'reading getcd'
    CTD_STATE_COMMAND_PROMPT = 'ctd prompt'
    CTD_STATE_TIMEOUT = 'timeout'
    CTD_STATE_SBE33_MENU = 'sbe33 menu'
    CTD_STATE_ACQUIRING_DATA = 'acquiring data'
    CTD_ACTIVE_INDICATORS = ['S>',
                            "<ERROR type=\'INVALID COMMAND\' msg=\'RCVD:wake\'/>",
                            "SBE 19plus",
                            "exiting the set up menu"
    ]
    SBE33_MENU_ACTIVE_INDICATORS = ["selection ="] #, "SBE 33/36 Deck Unit set up menu:"]
    GETCD_CONFIG_XML_START = "<ConfigurationData DeviceType = 'SBE19plus'"
    GETCD_CONFIG_XML_END = '</ConfigurationData>'
    SBE33_MODE_START = 'the current mode = '
    CTD_TIMED_OUT_INDICATORS = ['time out', 'S>time out']
    CTD_CMD_INITLOGGING = 'initlogging'
    CTD_CMD_STARTNOW = 'startnow'
    CTD_CMD_STOP = 'stop'
    CTD_CMD_LIST = [
        CTD_CMD_INITLOGGING,
        CTD_CMD_STARTNOW,
        CTD_CMD_STOP,
    ]

    
    def __init__(self, logfile : str, quit_evt : threading.Event, 
                 data_q, ext_cmd_q : queue.Queue, serialport: str, baud: int, 
                 alt_volt_range: int):

        # this config will reflect the state of the CTD via the getcd/getsd command responses
        self.ctd_config = sbe19v2plus.config.Config()

        self.ctd_status = {
            self.CTD_ACTIVE_DEVICE : self.CTD_ACTIVE_DEVICE_UNK,
            self.CTD_STATE : self.CTD_STATE_UNKNOWN,
        }

        self.sbe33_mode = 0  # init val, needs ot be set to '2'

        self.GetCD_str = ''

        self.quit_evt = quit_evt
        self.serial_port_cmd_q = queue.Queue(maxsize=1)
        self.data_q = data_q
        self.ext_cmd_q = ext_cmd_q
        self.ser_port = serial.serial_for_url(serialport, baud, timeout=0.5, 
                                              write_timeout=1, parity=serial.PARITY_EVEN, bytesize=7)
        self.altimeter_max_volts = alt_volt_range
        
        self.read_thr = threading.Thread(target=self.read_loop, name="ctdmon:read_loop")
        self.write_thr = threading.Thread(target=self.write_loop, name="ctdmon:write_loop")
        self.ext_cmd_thr = threading.Thread(target=self.external_command_monitor, name="ctdmon:ext_cmd_loop")
        self.threads_started = False
        self.lock = threading.Lock()
        self.sbe19_active_event = threading.Event()
        self.sbe33_active_event = threading.Event()
        self.getcd_read_event = threading.Event()
        self.confirmation_request_event = threading.Event()

        self.logfile = os.path.normpath(logfile)
        print(f'Initializing CTD Reader with path {self.logfile}')  


    def toggle_sbe33_menu(self):

        if self.ctd_status[self.CTD_ACTIVE_DEVICE] != self.CTD_ACTIVE_DEVICE_SBE33:
            self.enqueue_command('@', eol='\r')
            print('activating sbe33 menu...')
            self.sbe33_active_event.wait()
            self.sbe33_active_event.clear()

        elif self.ctd_status[self.CTD_ACTIVE_DEVICE] == self.CTD_ACTIVE_DEVICE_SBE33:
            print('de-activating sbe33 menu...')
            self.enqueue_command('@', eol='\n')
            self.sbe19_active_event.wait()
            self.sbe19_active_event.clear()
        self.serial_port_cmd_q.join()


    def ctd_configure(self):

        self.enqueue_command('mp', '\r')
        time.sleep(2)
        self.enqueue_command('mp', '\r')
        self.enqueue_command('outputformat=1', '\r')
        self.enqueue_command('autorun=no', '\r')
        self.enqueue_command('ignoreswitch=yes', '\r')
        self.enqueue_command('echo=no', '\r')
        self.enqueue_command('outputexecutedtag=no', '\r')
        t = datetime.utcnow()
        self.enqueue_command(f'DateTime={t.strftime("%m%d%Y%H%M%S")}', '\r')

        # these commands need to be confirmed with a second issuance
        time.sleep(2)
        self.enqueue_command('volt0=yes', '\r')
        time.sleep(2)
        self.enqueue_command('volt0=yes', '\r')
        self.enqueue_command('volt1=no', '\r')
        time.sleep(2)
        self.enqueue_command('volt1=no', '\r')
        self.enqueue_command('volt2=yes', '\r')
        time.sleep(2)
        self.enqueue_command('volt2=yes', '\r')
        self.enqueue_command('volt3=no', '\r')
        time.sleep(2)
        self.enqueue_command('volt3=no', '\r')
        self.enqueue_command('volt4=no', '\r')
        time.sleep(2)
        self.enqueue_command('volt4=no', '\r')
        self.enqueue_command('volt5=no', '\r')
        time.sleep(2)
        self.enqueue_command('volt5=no', '\r')

        # now read config from device
        self.enqueue_command('getcd', '\r')
        self.getcd_read_event.wait()
        # wait until config commands all been issued
        time.sleep(1)
        self.enqueue_command('startnow', 'r')
        self.serial_port_cmd_q.join()

    
    def init_state(self):

        # let's tkae a few secs to see if we can discern the current STATE and DEVICE
        time.sleep(2)
        # if self.ctd_status[self.CTD_STATE] == self.CTD_STATE_UNKNOWN:
        #     time.sleep(5)
                            # figure out the current STATE and ACTIVE DEVICE

        if (self.ctd_status[self.CTD_STATE] != self.CTD_STATE_ACQUIRING_DATA):
        # if not acquiring data, do config things...

            # let's send a return and see if we can figure out current state
            if self.ctd_status[self.CTD_STATE] == self.CTD_STATE_UNKNOWN:
                # will assume it is in CTD state and issue 'wake'
                # if not, wake will just trigger re-output of SBE 33 menu
                # either way this should trigger initialization of STATE and ACTIVE DEVICE
                self.enqueue_command('', '\r\n')

                while not self.sbe19_active_event.is_set() and not self.sbe33_active_event.is_set():
                    time.sleep(1)

            # if not acquiring data and active device is the CTD then toggle to SBE33 menu mode
            if self.ctd_status[self.CTD_ACTIVE_DEVICE] == self.CTD_ACTIVE_DEVICE_SBE19PlusV2:
                self.toggle_sbe33_menu()
                while self.ctd_status[self.CTD_ACTIVE_DEVICE] != self.CTD_ACTIVE_DEVICE_SBE33:
                    print('init_state: waiting for sbe33...')
                    time.sleep(0.5)
                self.sbe33_active_event.clear()
                self.enqueue_command('2', eol='\n')
                self.enqueue_command('7', eol='\n')
                self.sbe33_active_event.wait()
            elif self.ctd_status[self.CTD_ACTIVE_DEVICE] == self.CTD_ACTIVE_DEVICE_SBE33:
                self.enqueue_command('2', eol='\n')
                time.sleep(2)
            else:
                print(f'init_state: what the heck device is active? {self.ctd_status[self.CTD_ACTIVE_DEVICE]}')
            
            if self.sbe33_mode != 2:
                while self.sbe33_mode != 2:
                    time.sleep(0.25)

            # now go ack top CTD to set config
            self.toggle_sbe33_menu() # go back to CTD
            while self.ctd_status[self.CTD_ACTIVE_DEVICE] != self.CTD_ACTIVE_DEVICE_SBE19PlusV2:
                print('init_state: waiting for sbe19...')
                time.sleep(0.5)

            self.ctd_configure()
        
        else:
            # CTD is already running and acquiring data
            # for some reason ctdmon was restarted after starting the CTD
            # now read config from device
            self.enqueue_command('stop', '\r')
            time.sleep(0.5)
            self.enqueue_command('getcd', '\r')
            self.getcd_read_event.wait()
            self.enqueue_command('startnow', '\r')



    def start(self):
        self.read_thr.start()
        time.sleep(0.5)
        self.write_thr.start()
        time.sleep(0.5)
        self.ext_cmd_thr.start()
        time.sleep(0.5)
        self.threads_started = True
        
        self.init_state()


    def process_getcd_response(self) -> bool:

        self.GetCD_str = self.GetCD_str.strip()
        if self.ctd_config:
            del self.ctd_config

        self.ctd_config = sbe19v2plus.config.Config()
        res = self.ctd_config.update_getcd_info(self.GetCD_str) 
        if not res:
            print('ERROR PARSING GETC XML')
        print(self.ctd_config) #TODO Log
        #TODO debug or Log
        return res


    def update_state(self, line : str):

        #TODO Log
        # print(f'Check state change for line: {line}')

        if self.ctd_status[self.CTD_STATE] == self.CTD_STATE_READING_GETCD_CONFIG:
            self.ctd_status[self.CTD_ACTIVE_DEVICE] = self.CTD_ACTIVE_DEVICE_SBE19PlusV2
            self.sbe33_active_event.clear()
            self.sbe19_active_event.set()
            self.GetCD_str += f"{line}\n"
            if line.startswith(self.GETCD_CONFIG_XML_END):
                self.ctd_status[self.CTD_STATE] = self.CTD_STATE_COMMAND_PROMPT
                # print('Parsing (GetCD) CTD configuration...')
                #TODO Parse config info with elemTree
                self.process_getcd_response()
                self.getcd_read_event.set()

        elif line in self.CTD_ACTIVE_INDICATORS:
            # print(f'line: CTD IS ACTIVE')
            self.ctd_status[self.CTD_STATE] = self.CTD_STATE_COMMAND_PROMPT
            self.ctd_status[self.CTD_ACTIVE_DEVICE] = self.CTD_ACTIVE_DEVICE_SBE19PlusV2
            self.sbe33_active_event.clear()
            self.sbe19_active_event.set()

        elif line in self.SBE33_MENU_ACTIVE_INDICATORS:
            self.ctd_status[self.CTD_STATE] = self.CTD_STATE_SBE33_MENU
            self.ctd_status[self.CTD_ACTIVE_DEVICE] = self.CTD_ACTIVE_DEVICE_SBE33
            self.sbe33_active_event.set()
            self.sbe19_active_event.clear()
            # print('SBE 33 is ACTIVE')

        elif line in self.CTD_TIMED_OUT_INDICATORS:
            self.ctd_status[self.CTD_STATE] = self.CTD_STATE_TIMEOUT
            self.ctd_status[self.CTD_ACTIVE_DEVICE] = self.CTD_ACTIVE_DEVICE_NONE
            self.sbe33_active_event.clear()
            self.sbe19_active_event.clear()
            # print('SBE 19 TIMED OUT.. trying to wake up...')
            self.enqueue_command('wake', '\r')

        elif line.startswith(self.GETCD_CONFIG_XML_START):
            self.ctd_status[self.CTD_STATE] = self.CTD_STATE_READING_GETCD_CONFIG
            self.ctd_status[self.CTD_ACTIVE_DEVICE] = self.CTD_ACTIVE_DEVICE_SBE19PlusV2
            self.GetCD_str = line + '\n'
            self.sbe33_active_event.clear()
            self.sbe19_active_event.set()
            # print('Reading (GetCD) CTD configuration...')
            # print(line)

        elif line.startswith(self.SBE33_MODE_START):
            mode_pos = len(self.SBE33_MODE_START)
            self.sbe33_mode = int(line[mode_pos])
            # print(f'SBE33 MODE: {self.sbe33_mode}')

        else:
            
            if re.search("^A-Z0-9]+$", line):
                self.ctd_status[self.CTD_STATE] = self.CTD_STATE_ACQUIRING_DATA
                self.ctd_status[self.CTD_ACTIVE_DEVICE] = self.CTD_ACTIVE_DEVICE_SBE19PlusV2
                self.sbe33_active_event.clear()
                self.sbe19_active_event.set()


    def enqueue_command(self, cmds: Union[str, list[str]], eol : str = ''):

        # print(f'enqueuing: {cmds}')

        if isinstance(cmds, str) or (cmds == ''):
            cmdlist: list[str] = [str(cmds)]
        else:
            cmdlist = cmds

        cmd : str
        if isinstance(cmdlist, list):
            for cmd in cmdlist:
                cmd += eol
                ba = bytearray()
                ba.extend(cmd.encode())
                self.serial_port_cmd_q.put(ba)
                # print(f'Command enqueued: [{ba}]')


    def read_loop(self):

        with open(self.logfile, "at") as of:
            line = ''
            while not self.quit_evt.is_set():
                # print(f'CTD_STATUS: {self.ctd_status[self.CTD_STATE]}')
                time.sleep(0.05)
                # try:
                self.lock.acquire()
                line = self.ser_port.readline()
                self.lock.release()
                if line:
                    timestamp = round(datetime.utcnow().timestamp(), 2)
                    line_utf8 = line.decode(encoding='utf-8').strip()

                    self.update_state(line_utf8.strip())
                    if re.search("^[A-Z0-9]{18}[A-Z0-9]+$", line_utf8) is not None:
                        self.ctd_status[self.CTD_STATE] = self.CTD_STATE_ACQUIRING_DATA
                    # else:
                    #     print(f'not data rec: {line_utf8} {len(line_utf8)})')

                    if self.ctd_status[self.CTD_STATE] == self.CTD_STATE_ACQUIRING_DATA:
                        sample_dict = self.parse_data(line_utf8)
                        sample_dict["ts"] = timestamp
                        sample_dict["type"] = 'ctd'
                        of.write(f"{line_utf8} {sample_dict}\n")
                        self.data_q.put(sample_dict)

                    else:
                        of.write(f"{line_utf8}\n")

                    of.flush()
                else:
                    pass

        print('serial port read thread shutting down...')
        return
    
    def write_loop(self):

        while not self.quit_evt.is_set():
            try:
                cmd = self.serial_port_cmd_q.get(block=True, timeout=1)
                self.send_command(cmd)
                self.serial_port_cmd_q.task_done()
            except queue.Empty as e:
                pass
            else:
                pass
            finally:
                cmd = ''

        print('serial port write thread shutting down...')

    def external_command_monitor(self):

        while not self.quit_evt.is_set():
            try:
                cmd = self.ext_cmd_q.get(block=True, timeout=0.5)
                self.ext_cmd_q.task_done()
            except queue.Empty as e:
                continue

            cmd = cmd.lower()
            if cmd in self.CTD_CMD_LIST:
                print(f'SBE33SerialPort: sending ext cmd: {cmd}')
                self.enqueue_command(cmd, '\r')


    
    def send_command(self, cmd : bytes):

        try:
            self.lock.acquire()
            self.ser_port.write(cmd)
            self.ser_port.flush()
            self.lock.release()
            print(f'Command sent                   : [{cmd}]')
            self.last_command = cmd
        except serial.SerialTimeoutException as e:
            print(e)
        except serial.SerialException as e:
            print(e)
        else:
            pass


    def quit(self):
        self.read_thr.join()
        self.write_thr.join()
        self.ext_cmd_thr.join()
        print('closing serial port...')
        self.ser_port.close()

    def expected_sample_line_length(self, has_gps : bool) -> int:

        llen = 0

        if self.ctd_config.output_format == sbe19v2plus.config.SBE19OutputFmt.OUTPUT_FORMAT_1:
        # note: this is a HEX mode and will have 14 chars (7 bytes) of lat/lon info, if available

            llen += 6  # temp
            llen += 6  # conductivity
            llen += 6  # pressure

            if self.ctd_config.volt0: 
                # print('expected_sample_line_;ength: Volt0: True')
                # print(f'expected_sample_line_;ength: Volt0-len: {sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["volt0"]["len"]}')
                llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["volt0"]["len"]
            if self.ctd_config.volt1: llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["volt1"]["len"]
            if self.ctd_config.volt2: llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["volt2"]["len"]
            if self.ctd_config.volt3: llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["volt3"]["len"]
            if self.ctd_config.volt4: llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["volt4"]["len"]
            if self.ctd_config.volt5: llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["volt5"]["len"]
            if self.ctd_config.sbe38: llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["sbe38"]["len"]
            if self.ctd_config.wetlabs: llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["wetlabns"]["len"]
            if self.ctd_config.GTD or self.ctd_config.DualGTD: 
                llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["GTD1_press"]["len"] + \
                        sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["GTD1_tempc"]["len"]
            if self.ctd_config.DualGTD:
                llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["GTD2_press"]["len"] + \
                        sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["GTD2_tempc"]["len"]
            if self.ctd_config.optode:  llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["optode"]["len"]
            if self.ctd_config.sbe63:
                llen += sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["sbe_ox_ph"]["len"] + \
                        sbe19v2plus.config.SBE19v2plusVars["ofmt_1"]["sbe63_ox_tempV"]["len"]
            if self.ctd_config.mode == sbe19v2plus.config.SBE19Mode.MOORED_MODE:
                # for exatr time stamp filed
                llen += 8

            # llen += 6 # for surface PAR depth: RIFT_OX NOT USING
            if has_gps:
                llen += 14 # for gps

            # print(f'expecting line length: {llen}/ {has_gps}')
        return llen

    def data_len_correct(self, line : str, has_gps : bool):

        return len(line) == self.expected_sample_line_length(has_gps)
        

    def parse_data(self, line : str) -> dict:
        """Parse raw data line based on current output format.
        Output a dict with parsed values in proper type: int or float
        """

        line_str = line.strip()

        # print(f'line len: {len(line_str)}')

        has_gps : bool = len(line_str) == 40  # OUTPUTFORMAT == 1 ONLY - it's 26 without gps
        if self.data_len_correct(line, has_gps):

            if self.ctd_config.output_format == self.ctd_config.output_format.OUTPUT_FORMAT_1:
                # str_val_dict = self.extract_strings(line_str)
                # print(f'parsing {line} for format 1')
                return self._convert_output_format_1(line_str, has_gps)
            else:  # unsupport format
                #TODO log and send error msg/mqtt
                # perhaps return the same dict but with raw input...?

                print(f'parsing {line} UNSUPPORTED FORMAT')
                return {}
            
        else:  # BAD DATA RECORD
            #TODO log and send error msg/mqtt
            # perhaps return the same dict but with raw input...?
            print(f'parsing {line} UNEXPECTED LEN: {len(line)}')
            return {}


    
    def altimeter_meters(self, volts, minV=0, maxV=10):
        # VA500 100m range
        # votlages may be set to 0-5 or 0-10 range in configuration.
        volts_m = (100)/(maxV - minV) * volts
        return volts_m

    def _convert_output_format_1(self, line : str, has_gps : bool) -> dict:

        cfg = self.ctd_config
        res = {}

        # 2BC30D 103CA5 018861 A67E ACBD 19138B5974E941
        pos = 0
        tempstr = line[pos:pos+6]; pos += 6
        res["t_c"] = round((int(tempstr, 16) / 100000) - 10, 4)
        condstr = line[pos:pos+6]; pos += 6
        res["cond"] = round((int(condstr, 16) / 1000000) - 1, 4)
        presstr = line[pos:pos+6]; pos += 6
        res["pres"] = round((int(presstr, 16) / 1000) - 100, 4)


        if cfg.volt0:
            strval = line[pos:pos+4]; pos += 4
            res["v0"] = round(int(strval, 16) / 13107, 4)
            res["alt_m"] = round(self.altimeter_meters(res["volt0"], 
                                                            minV=0, 
                                                            maxV=self.altimeter_max_volts), 2)
        if cfg.volt1:
            strval = line[pos:pos+4]; pos += 4
            res["v1"] = round(int(strval, 16) / 13107, 4)
        if cfg.volt2:
            strval = line[pos:pos+4]; pos += 4
            res["v2"] = round(int(strval, 16) / 13107, 4)
        if cfg.volt3:
            strval = line[pos:pos+4]; pos += 4
            res["v3"] = round(int(strval, 16) / 13107, 4)
        if cfg.volt4:
            strval = line[pos:pos+4]; pos += 4
            res["v4"] = round(int(strval, 16) / 13107, 4)
        if cfg.volt5:
            strval = line[pos:pos+4]; pos += 4
            res["v5"] = round(int(strval, 16) / 13107, 4)

        if cfg.sbe38:
            strval = line[pos:pos+5]; pos += 5
            res["sbe38"] = round((int(strval, 16) / 100000) - 10, 4)

        if cfg.wetlabs:
            strval = line[pos:pos+12]; pos += 12
            res["wetlabs"] = round(int(strval, 16), 4)

        if cfg.GTD or cfg.DualGTD:
            strval = line[pos:pos+8]; pos += 8
            res["GTD1_press"] = round(int(strval, 16) / 100000, 4)
            strval = line[pos:pos+6]; pos += 6
            res["GTD1_tempc"] = round((int(strval, 16) / 100000) -10, 4)

        if cfg.DualGTD:
            strval = line[pos:pos+8]; pos += 8
            res["GTD2_press"] = round(int(strval, 16) / 100000, 4)
            strval = line[pos:pos+6]; pos += 6
            res["GTD2_tempc"] = round((int(strval, 16) / 100000) -10, 4)

        if cfg.optode:
            strval = line[pos:pos+6]; pos += 6
            res["optode"] = round((int(strval, 16) / 10000) - 10, 4)

        if cfg.sbe63:  
            strval = line[pos:pos+6]; pos += 6
            res["ox_ph"] = round((int(strval, 16) / 100000) - 10, 4)
            strval = line[pos:pos+6]; pos += 6
            res["ox_temp_vstr"] = round((int(strval, 16) / 1000000) - 1, 4)

        if cfg.mode == sbe19v2plus.config.SBE19Mode.MOORED_MODE:
            strval = line[pos:pos+8]; pos += 8
            res["time2000"] = round(int(strval, 16), 4)

        if has_gps:
            # assuming NMEA from GPS data is here
            # print(f'GPS info: {line[pos:pos+14]}')
            lat1 = line[pos:pos+2]; pos += 2
            lat2 = line[pos:pos+2]; pos += 2
            lat3 = line[pos:pos+2]; pos += 2
            lat = ( int(lat1, 16) * 2**16 + int(lat2, 16) * 2**8 + int(lat3, 16) ) / 50000
            lon1 = line[pos:pos+2]; pos += 2
            lon2 = line[pos:pos+2]; pos += 2
            lon3 = line[pos:pos+2]; pos += 2
            lon = ( int(lon1, 16) * 2**16 + int(lon2, 16) * 2**8 + int(lon3, 16) ) / 50000
            hemispheres_byte = int(line[pos:pos+1], 16); pos += 1
            if ((hemispheres_byte >> 6) & 1) == 1:
                lon = -lon
            if ((hemispheres_byte >> 6) & 1) == 1:
                lat = -lat
        else:
            # assuming at SIO, approx
            lat = 32
            lon = -117

        res["dep_m"] = round(-gsw.z_from_p(res["pres"], lat), 2)  # make positive depth down from surface
        res["lat"] = lat
        res["lon"] = lon

        return res
