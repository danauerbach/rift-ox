#!/usr/bin/env python3

#import readline
import argparse
from enum import Enum
import os
import pickle

import json

from pprint import pprint
import queue
import re
import shlex
import serial
import signal
import sys
import threading
import time

import paho.mqtt.client as mqtt



def cloud_client(clientid: str) -> mqtt.Client:

    client = mqtt.Client(clientid)
    client.on_publish = 

    return client