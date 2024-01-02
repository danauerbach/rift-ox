#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import datetime
import time
from typing import Protocol

from winch.dio_cmds import DIOCommander

from . import WinchStateName, WinchDir

# STATE_PARKED_STR = 'parked'
# STATE_STAGING_STR = 'staging'
# STATE_STAGED_STR = 'staged'
# STATE_DOWNCASTING_STR = 'downcasting'
# STATE_UPCASTING_STR = 'upcasting'
# STATE_ATLATCH_STR = 'atlatch'
# STATE_ATMAXDEPTH_STR = 'atmaxdepth'
# STATE_PARKING_STR = 'parking'
# STATE_PAUSED_STR = 'paused'
# STATE_STOPPED_STR = 'stopped'
# STATE_UNKNOWN_STR = 'unknown'

# parked
# parking
# atlatch (aka home)
# staging
# staged
# paused
# downcasting
# upcasting
# atmaxdepth
# unknown


class WinchState(Protocol):

    def stop(self):
        ...

    def start(self):
        ...

    def park(self):
        ...

    def down_pause(self):
        ...

    def up_pause(self):
        ...

    def down_cast(self):
        ...

    def up_cast(self):
        ...

    def ___str__(self):
        ...        


class WinchProto(Protocol):
    cmndr: DIOCommander

    def stop(self):
        ...

    def start(self):
        ...

    def down_pause(self):
        ...

    def up_pause(self):
        ...

    def down_cast(self):
        ...

    def up_cast(self):
        ...

    def set_state(self, state: WinchState):
        ...

    def get_state_str(self) -> str:
        ...

    def status(self) -> (dict, bool):
        ...
   
@dataclass
class ParkedState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when already {self}')

    def start(self):
        self.winch.cmndr.stage()
        self.winch.set_state(StagingState(self.winch))

    def park(self):
        # re-park, probably just for testing or if
        # a problem with the latch
        self.winch.set_state(ParkingState(self.winch))
        self.winch.cmndr.park()
        self.winch.set_state(ParkedState(self.winch))

    def down_pause(self):
        print(f'Can not down_pause when {self}')

    def up_pause(self):
        print(f'Can not up_pause when {self}')

    def down_cast(self):
        # same as start when in Parked state
        self.winch.cmndr.stage()
        self.winch.set_state(StagingState(self.winch))

    def up_cast(self):
        print(f'Can not up-cast when {self}')

    def __str__(self):
        return WinchStateName.PARKED     


class StagingState():
    winch: WinchProto

    def stop(self):
        # same as down_pause when Staging
        self.winch.cmndr.stop_winch()
        self.winch.set_state(DownPausedState(self.winch))

    def start(self):
        print(f'Can not start when {self}')

    def park(self):
        print(f'Can not park when {self}')

    def down_pause(self):
        self.winch.cmndr.stop_winch()
        self.winch.set_state(DownPausedState(self.winch))
        
    def up_pause(self):
        print(f'Can not up-pause when {self}')

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def up_cast(self):
        print(f'Can not upcast when {self}')

    def __str__(self):
        return WinchStateName.STAGING  


class DownStagedState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        # start called after pause duration elapses
        # same as down_cast
        self.winch.cmndr.downcast()
        self.winch.set_state(DowncastingState(self.winch))

    def park(self):
        # shouldn't need to parked after being Staged
        # but just in case
        self.winch.cmndr.park()
        self.winch.set_state(ParkedState(self.winch))

    def down_pause(self):
        print(f'Can not downpause when {self}')

    def up_pause(self):
        print(f'Can not uppause when {self}')

    def down_cast(self):
        # same behavior as 'start'
        # but from Staged, Downcasting should be 
        # same as down_cast
        self.winch.cmndr.downcast()
        self.winch.set_state(DowncastingState(self.winch))

    def up_cast(self):
        print(f'Can not upcast when {self}')

    def __str__(self):
        return WinchStateName.DOWN_STAGED


class UpStagedState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        # same as Park
        self.winch.set_state(ParkingState(self.winch))
        self.winch.cmndr.park()
        self.winch.set_state(ParkedState(self.winch))

    def park(self):
        # We're almost done, let's park
        self.winch.set_state(ParkingState(self.winch))
        self.winch.cmndr.park()
        self.winch.set_state(ParkedState(self.winch))

    def down_pause(self):
        print(f'Can not downpause when {self}')

    def up_pause(self):
        print(f'Can not uppause when {self}')

    def down_cast(self):
        print(f'Can not downpause when {self}')
        # same behavior as 'start'
        # but from Staged, Downcasting should be 
        # initiated with 'start' cmd
        self.winch.cmndr.downcast()
        self.winch.set_state(DowncastingState(self.winch))

    def up_cast(self):
        print(f'Can not upcast when {self}, only Park or Start')

    def __str__(self):
        return WinchStateName.UP_STAGED



class DowncastingState():
    winch: WinchProto

    def stop(self):
        self.winch.cmndr.stop_winch()
        ...

    def start(self):
        print(f'Can not start when {self}')
        ...

    def park(self):
        ...

    def down_pause(self):
        self.winch.cmndr.stop_winch()
        self.winch.set_state(DownPausedState(self.winch))        

    def up_pause(self):
        self.winch.cmndr.stop_winch()
        self.winch.set_state(UpPausedState(self.winch))        

    def down_cast(self):
        print(f'Can not downcast when {self}.')
        ...

    def up_cast(self):
        print(f'Can not upcast when {self}')
        ...

    def __str__(self):
        return WinchStateName.DOWNCASTING


class UpcastingState():
    winch: WinchProto

    def stop(self):
        self.winch.cmndr.stop_winch()

    def start(self):
        print(f'Can not start when {self}')
        ...

    def park(self):
        self.stop()
        self.winch.cmndr.park()
        self.winch.set_state(ParkedState(self.winch))

    def down_pause(self):
        print(f'Can not downpause when {self}')

    def up_pause(self):
        print(f'Can not uppause when {self}')

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def up_cast(self):
        print(f'Can not upcast when {self}')
        ...

    def __str__(self):
        return WinchStateName.UPCASTING



class MaxDepthState():
    winch: WinchProto

    def stop(self):
        self.winch.cmndr.stop_winch()

    def start(self):
        print(f'Can not start when {self}')

    def park(self):
        ...

    def down_pause(self):
        print(f'Can not downpause when {self}')
        ...

    def up_pause(self):
        print(f'Can not uppause when {self}')
        ...

    def down_cast(self):
        print(f'Can not downcast when {self}.')
        ...

    def up_cast(self):
        print(f'Can not upcast when {self}')

    def __str__(self):
        return WinchStateName.ATMAXDEPTH


class ParkingState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        print(f'Can not start when {self}')

    def park(self):
        ...

    def down_pause(self):
        print(f'Can not downpause when {self}')

    def up_pause(self):
        print(f'Can not uppause when {self}')

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def up_cast(self):
        print(f'Can not upcast when {self}')

    def __str__(self):
        return WinchStateName.PARKING

class DownPausedState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        print(f'Can not start when {self}')

    def park(self):
        ...

    def down_pause(self):
        print(f'Can not downpause when {self}')

    def up_pause(self):
        print(f'Can not uppause when {self}')

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def up_cast(self):
        print(f'Can not upcast when {self}')

    def __str__(self):
        return WinchStateName.DOWN_PAUSED

class UpPausedState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        # same as up_cast when in up-paused state
        self.winch.cmndr.upcast()
        self.winch.set_state(UpcastingState(self.winch))

    def park(self):
        print(f'Can not park when {self}, only when up-staged')

    def down_pause(self):
        print(f'Can not downpause when {self}')

    def up_pause(self):
        print(f'Can not uppause when {self}')

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def up_cast(self):
        self.winch.cmndr.upcast()
        self.winch.set_state(UpcastingState(self.winch))

    def __str__(self):
        return WinchStateName.UP_PAUSED



class Winch:

    def __init__(self, cmndr: DIOCommander):
        self.cmndr: DIOCommander = cmndr
        self.state: WinchState = ParkedState(self)
        #TODO SHould we check current depth? Or last written state and timestamp? Or check latch sensor?
        #TODO write out state to $RO_WINCH_STATE_FILE

        # vars only to facilitate simulated responses from winch
        self._sim_start_time = time.time()
        self._sim_winch_in_motion_dur = 0
        self._sim_winch_paused_dur = 0
        self._sim_start_motion = 0
        self._sim_start_pause = 0
        self._sim_park_start = 0

    def stop(self):
        self.state.stop()
        t = time.time()
        self._sim_winch_in_motion_dur += t - self._sim_start_motion
        self._sim_start_pause = t

    def start(self):
        self.state.start()
        t = time.time()
        self._sim_winch_paused_dur += t - self._sim_start_pause
        self._sim_start_motion = t

    def park(self):
        self.state.park()

    def down_pause(self):
        self.state.down_pause()
        t = time.time()
        self._sim_winch_in_motion_dur += t - self._sim_start_motion
        self._sim_start_pause = t

    def up_pause(self):
        self.state.up_pause()
        t = time.time()
        self._sim_winch_in_motion_dur += t - self._sim_start_motion
        self._sim_start_pause = t

    def down_cast(self):
        self.state.down_cast()
        t = time.time()
        self._sim_winch_paused_dur += t - self._sim_start_pause
        self._sim_start_motion = t

    def up_cast(self):
        self.state.up_cast()
        t = time.time()
        self._sim_winch_paused_dur += t - self._sim_start_pause
        self._sim_start_motion = t

    def set_state(self, state: WinchState):
        self.state = state

    def get_state_str(self) -> str:
        return str(self.state)

    def status(self) -> (dict, bool):
        status = {}

        # get payout sensors readings
        if self.cmndr.simulation:
            # based on 2 sec per rotation a 6 triggers
            # simulate 3 signals or 6 edges
            edgecnt = self._sim_winch_in_motion_dur * 6
            payouts = [edgecnt, edgecnt]
            err = False
        else:
            payouts, err = self.cmndr.get_payout_edge_count()
            if err:
                print(f'states:winch ERROR get payout edge count')
                return {}, err
        status["payouts"] = payouts

        # get latch sensor readings
        latch_cnt, err = self.cmndr.get_latch_edge_count()
        if err:
            print(f'states:winch ERROR get latch sensor edge count')
            return {}, err
        status["latch_cnt"] = latch_cnt

        # get winch direction, if any
        if self.cmndr.simulation:
            if isinstance(self.state, (UpcastingState,)):
                status["dir"] = WinchDir.DIRECTION_UP
            elif isinstance(self.state, (DowncastingState, StagingState)):
                status["dir"] = WinchDir.DIRECTION_DOWN
            else:
                status["dir"] = WinchDir.DIRECTION_NONE
            err = False
        else:
            status["dir"], err = self.cmndr.get_winch_direction()
            if err:
                print(f'states:winch ERROR get winch direction')
                return {}, err

        status["state"] = str(self.state)
        status["ts"] = datetime.utcnow().isoformat()

        return status, False

