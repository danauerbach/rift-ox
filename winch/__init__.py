#!/usr/bin/env python3

from collections import namedtuple
from enum import Enum
import os
from pathlib import Path

home_dir = str(Path.home())

class WinchDir(Enum):
    DIRECTION_NONE = 'NONE'
    DIRECTION_UP = 'UP'
    DIRECTION_DOWN = 'DOWN'

class WinchStateName(Enum):
    PARKED =        "parked"
    PARKING  =      "parking"
    STAGING  =      "staging"
    UP_STAGED  =    "upstaged"
    DOWN_STAGED  =  "downstaged"
    UP_PAUSED  =    "uppaused"
    DOWN_PAUSED  =  "downpaused"
    DOWNCASTING  =  "downcasting"
    UPCASTING  =    "upcasting"
    MAXDEPTH  =     "maxdepth"
    # ATLATCH  =    "atlatch"


# WINCH CONTROL COMMAND CONSTANTS
class WinchCmd(Enum):
    WINCH_CMD_START =             'start'                   # go to staging depth (see config file). Only valid when ParkedState
    WINCH_CMD_DOWNCAST =          'down-cast'             # start downcast (from StagedState)
    WINCH_CMD_PAUSE =             'pause'             # stop winch and wait for PAUSE_DURATION_SECS timeout
    WINCH_CMD_STOP =              'stop'              # essentially an alias for 'pause'
    WINCH_CMD_STOP_AT_MAX_DEPTH = 'stop-at-max-depth' # stop winch motion and wait for next command
    WINCH_CMD_UPCAST =            'up-cast'                 # Start upcast (from any state except HomeState)
    WINCH_CMD_UPSTAGE =           'up-stage'                 # Start upcast (from any state except HomeState)
    WINCH_CMD_PARK =              'park'                     # go up past latch and down a little bit and release latch and drop down a little
    WINCH_CMD_SETSTATE =          'set-state'

WINCH_CMD_LIST = {
    WinchCmd.WINCH_CMD_START, \
    WinchCmd.WINCH_CMD_DOWNCAST, \
    WinchCmd.WINCH_CMD_PAUSE, \
    WinchCmd.WINCH_CMD_STOP_AT_MAX_DEPTH, \
    WinchCmd.WINCH_CMD_UPCAST, \
    WinchCmd.WINCH_CMD_UPSTAGE, \
    WinchCmd.WINCH_CMD_PARK, \
    WinchCmd.WINCH_CMD_SETSTATE
}

# Orange Pi DIO
DIO_ACTION_DEVICE_LIST_NAME  = "device list"     # Reports the number of outputs available to the indicated device
DIO_ACTION_GET_NAME          = "get"        # Read the state and count of an input, or just the state of an output
DIO_ACTION_SET_NAME          = "set"        # Set the logical state of a digital output
DIO_ACTION_MODE_NAME         = "mode"    # Switch between sink-source and open-collector drive mode on supported hardware
DIO_ACTION_NUM_NAME          = "num"     # Reports the number of DIO banks available on the device, either output or input
DIO_ACTION_PWM_NAME          = "pwm"     # Reports the number of outputs available to the indicated device
DIO_ACTION_EDGE_NAME         = 'edge'    # Reports the number of rising and failing edges detected by an input pin
DIO_VALID_COMMANDS           = [DIO_ACTION_DEVICE_LIST_NAME,
                                DIO_ACTION_GET_NAME, 
                                DIO_ACTION_SET_NAME, 
                                DIO_ACTION_MODE_NAME, 
                                DIO_ACTION_NUM_NAME, 
                                DIO_ACTION_PWM_NAME, 
                                DIO_ACTION_EDGE_NAME]
# DIO_VALID_PARAMS              = ['dir', 'group', 'pin', 'value']
DIO_DIRECTION_IN              = "in"
DIO_DIRECTION_OUT             = "out"
DIO_VALID_DIRECTIONS          = [DIO_DIRECTION_IN,
                                 DIO_DIRECTION_OUT]
DIO_LONG_DIRECTION_DICT       = {
    DIO_DIRECTION_IN: 'input',
    DIO_DIRECTION_OUT: 'output'
}
DIO_SHORT_DIRECTION_DICT       = {
    DIO_DIRECTION_IN: 'I',
    DIO_DIRECTION_OUT: 'O'
}
DIO_VALID_GROUPS              = list(range(0,4))
DIO_VALID_PINS                = list(range(0,4))
DIO_MODE_DRAIN                = 'open-drain'
DIO_MODE_SOURCE               = 'source'
DIO_VALID_MODES               = [DIO_MODE_DRAIN,
                                 DIO_MODE_SOURCE]
