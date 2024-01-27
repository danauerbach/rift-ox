from enum import Enum


class InverterState(Enum):
    POWER_OFF = '0'
    POWER_ON  = '1'

INVERTER_CMD_LIST = [
    InverterState.POWER_OFF,
    InverterState.POWER_ON
]