#!/usr/bin/env python3

### MQTT TOPICS
# GLOBAL
TOPIC_COMMANDS = 'rift-ox/commander/command' # potnetially subscribed to by all clients

# WINCH
TOPIC_WINCH_PAYOUT = 'rift-ox/winmon/winch/payout'
TOPIC_WINCH_TENSION = 'rift-ox/winmon/winch/tension'
TOPIC_WINCH_LATCH = 'rift-ox/winmon/winch/latch'
TOPIC_WINCH_MOTION = 'rift-ox/winmon/winch/motion'
TOPIC_WINCH_MOTION_CHANGE = 'rift-ox/winmon/winch/motion-change'
TOPIC_WINCH_MOTION_COMMAND = 'rift-ox/winmon/winch/motion-cmd'
TOPIC_WINCH_ALL = 'rift-ox/winmon/#'

# CTD
TOPIC_CTD_SENSOR_DATA = 'rift-ox/ctdmon/ctddata'
# TOPIC_ALTIMETER = 'rift-ox/ctdmon/altimeter/data'
TOPIC_CTD_SENSORS_DATA_SIMUL = 'rift-ox/simulator/ctddata'
# TOPIC_ALTIMETER_SIMUL = 'rift-ox/simulator/altimeter/data'

# 