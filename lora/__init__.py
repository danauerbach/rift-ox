#!/usr/bin/env python3

from enum import Enum


class IO_MODE(Enum):
    SEND = 'SEND'
    RECEIVE = 'RECEIVE'

RIFTOX_CMDS = ['GOSCIENCE', 'PAUSE', 'KILL33', 'QUIT']
LORA_MODE_CMDS = [IO_MODE.SEND.value, IO_MODE.RECEIVE.value]

