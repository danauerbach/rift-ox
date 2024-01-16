#!/usr/bin/env python3

#import readline
import argparse
from datetime import datetime
import json
from os.path import abspath, expanduser
from pathlib import Path
import queue
import re
import shlex
import serial
import signal
import pytz

# {'temp_c': 2.7479, 
# 'cond': 3.0075, 
# 'pres': 0.637, 
# 'volt0': 4.9928, 
# 'alt_m': 99.86, 
# 'volt2': 1.5949, 
# 'depth_m': 0.63, 
# 'lat': 74.80584, 
# 'lon': 103.65894, 
# 'ts': 1705377669.34,
# 'type': 'ctd'
# }

### reads from source raw ctdmon serialport.log file
### and cnverts all valid data lines (start with 40 hex byte string)
### to CSV

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("-f", "--logfile", help="serial port log file to parse", 
                        default="~/dev/logs/serialport.log", type=str)

    args = parser.parse_args()

    serialport_fn = abspath(expanduser(args.logfile))
    hex_regex = r'[0-9[A-F]{40} '
    json_str: str

    with open(serialport_fn, 'rt') as ifl, open('serialport.csv', 'wt') as ofl:

        ofl.write('temp_c,cond,pres,volt0,alt_m,volt2,depth_m,lat,lon,ts,type\n')

        line = ifl.readline()
        while line != '':  # The EOF char is an empty string
            # print(line)
            if re.search(hex_regex, line):
                json_str = line.split(maxsplit=1)[1].strip()
                jobj = json.loads(json_str)
                hts: str = datetime.fromtimestamp(jobj['ts'], tz=pytz.UTC).isoformat(timespec='milliseconds')
                ofl.write(f"{jobj['temp_c']}, {jobj['cond']}, {jobj['pres']}, {jobj['volt0']}, {jobj['alt_m']}, {jobj['volt2']}, {jobj['depth_m']}, {jobj['lat']}, {jobj['lon']}, {jobj['ts']}, {hts}, '{jobj['type']}'\n")
                
            line = ifl.readline()
            

       
