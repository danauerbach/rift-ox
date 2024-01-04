#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import datetime
from threading import Timer
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

    def down_cast(self):
        ...

    def pause(self):
        ...

    def stop_at_bottom(self):
        ...

    def up_cast(self):
        ...

    def up_stage(self):
        ...

    def park(self):
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

    def stop_at_bottom(self):
        ...

    def set_state(self, state: WinchState):
        ...

    def get_latch_edge_count(self):
        ...
    
    def latch_release(self):
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

    def down_cast(self):
        # same as start when in Parked state
        self.start()

    def pause(self):
        print(f'Can not pause when {self}')

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def up_cast(self):
        print(f'Can not up-cast when {self}')

    def up_stage(self):
        print(f'Can not up_stage when {self}')

    def park(self):
        # re-park, probably just for testing or if
        # a problem with the latch
        self.winch.set_state(ParkingState(self.winch))
        self.winch.cmndr.park()
        self.winch.set_state(ParkedState(self.winch))

    def __str__(self):
        return WinchStateName.PARKED.value


@dataclass
class StagingState():
    winch: WinchProto

    def stop(self):
        # same as pause when Staging
        self.pause()

    def start(self):
        print(f'Can not start when {self}')

    def down_cast(self):
        print(f'Can not down-cast when {self}')

    def pause(self):
        print(f'Can not pause when {self}')

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def up_cast(self):
        print(f'Can not up-cast when {self}')

    def up_stage(self):
        print(f'Can not up-stage when {self}')

    def park(self):
        print(f'Can not park when {self}')

    def __str__(self):
        return WinchStateName.STAGING.value


class DownStagedState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        # start called after pause duration elapses
        # same as down_cast
        self.down_cast()

    def down_cast(self):
        # same behavior as 'start'
        # but from Staged, Downcasting should be 
        # same as down_cast
        self.winch.cmndr.down_cast()
        self.winch.set_state(DowncastingState(self.winch))

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def pause(self):
        print(f'Can not pause when {self}')

    def up_cast(self):
        print(f'Can not upcast when {self}')

    def up_stage(self):
        print(f'Can not up-stage when {self}')

    def park(self):
        # shouldn't need to parked after being Staged
        # but just in case
        self.winch.set_state(ParkingState(self.winch))
        self.winch.cmndr.park()
        self.winch.set_state(ParkedState(self.winch))

    def __str__(self):
        return WinchStateName.DOWN_STAGED.value


class UpStagedState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        # same as Park when UpStaged
        self.park()

    def down_cast(self):
        print(f'Can not downcast when {self}')

    def pause(self):
        print(f'Can not pause when {self}')

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def up_cast(self):
        print(f'Can not upcast when {self}, only Park or Start')

    def up_stage(self):
        print(f'Can not up-stage when {self}')

    def park(self):
        # We're almost done, let's park
        self.winch.set_state(ParkingState(self.winch))
        self.winch.cmndr.park()
        self.winch.set_state(ParkedState(self.winch))

    def __str__(self):
        return WinchStateName.UP_STAGED.value



class DowncastingState():
    winch: WinchProto

    def stop(self):
        # same as down_pause
        self.pause()

    def start(self):
        print(f'Can not start when {self}')

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def pause(self):
        self.winch.cmndr.stop_winch()
        self.winch.set_state(DownPausedState(self.winch))        

    def stop_at_bottom(self):
        self.winch.cmndr.stop_winch()
        self.winch.set_state(MaxDepthState(self.winch))

    def up_cast(self):
        print(f'Can not up-cast when {self}')

    def up_stage(self):
        print(f'Can not up-stage when {self}')

    def park(self):
        print(f'Can not park when {self}')

    def __str__(self):
        return WinchStateName.DOWNCASTING.value


class UpcastingState():
    winch: WinchProto

    def stop(self):
        # same as pause
        self.pause()

    def start(self):
        print(f'Can not start when {self}')

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def pause(self):
        self.winch.cmndr.stop_winch()
        self.winch.set_state(UpPausedState(self.winch))        

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def up_cast(self):
        print(f'Can not upcast when {self}')

    def up_stage(self):
        self.winch.cmndr.stop_winch()
        self.winch.set_state(UpStagedState(self.winch))        

    def park(self):
        print(f'Can not park when {self}')

    def __str__(self):
        return WinchStateName.UPCASTING.value



class MaxDepthState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}.')

    def start(self):
        self.up_cast()

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def pause(self):
        print(f'Can not downpause when {self}')

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def up_cast(self):
        self.winch.cmndr.up_cast()
        self.winch.set_state(UpcastingState(self.winch))

    def up_stage(self):
        print(f'Can not up-stage when {self}')

    def park(self):
        print(f'Can not park when {self}')

    def __str__(self):
        return WinchStateName.MAXDEPTH.value


class ParkingState():
    # the park() command which intiates ParkingState
    # ends by setting state to ParkedState
    # so no cmds active while parking
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        print(f'Can not start when {self}')

    def down_cast(self):
        print(f'Can not down-cast when {self}.')

    def pause(self):
        print(f'Can not pause when {self}')

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def up_cast(self):
        print(f'Can not upcast when {self}')

    def up_stage(self):
        print(f'Can not up-stage when {self}')

    def park(self):
        print(f'Can not park when {self}')

    def __str__(self):
        return WinchStateName.PARKING.value

class DownPausedState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        # same as down cast
        self.down_cast()
        print(f'Can not start when {self}')

    def down_cast(self):
        self.winch.cmndr.down_cast()
        self.winch.set_state(DowncastingState(self.winch))

    def pause(self):
        print(f'Can not pause when {self}')

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def up_cast(self):
        print(f'Can not upcast when {self}')

    def up_stage(self):
        print(f'Can not up-stage when {self}')

    def park(self):
        print(f'Can not park when {self}')

    def __str__(self):
        return WinchStateName.DOWN_PAUSED.value

class UpPausedState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        # same as up_cast when in up-paused state
        self.winch.cmndr.upcast()
        self.winch.set_state(UpcastingState(self.winch))

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def pause(self):
        print(f'Can not pause when {self}')

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def up_cast(self):
        self.winch.cmndr.upcast()
        self.winch.set_state(UpcastingState(self.winch))

    def up_stage(self):
        print(f'Can not up-stage when {self}')

    def park(self):
        print(f'Can not park when {self}, only when up-staged')

    def __str__(self):
        return WinchStateName.UP_PAUSED.value



class Winch:

    def __init__(self, cmndr: DIOCommander):
        self.cmndr: DIOCommander = cmndr
        self.state: WinchState = ParkedState(self)

        # vars only to facilitate simulated responses from winch
        self._sim_start_time = time.time()
        self._sim_winch_in_motion_dur = 0
        self._sim_winch_paused_dur = 0
        self._sim_start_motion = 0
        self._sim_start_pause = 0
        self._sim_park_start = 0
        self._sim_latch_edge_count = 0

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

    def down_cast(self):
        self.state.down_cast()
        t = time.time()
        self._sim_winch_paused_dur += t - self._sim_start_pause
        self._sim_start_motion = t

    def pause(self):
        self.state.up_pause()
        t = time.time()
        self._sim_winch_in_motion_dur += t - self._sim_start_motion
        self._sim_start_pause = t

    def stop_at_bottom(self):
        self.state.stop_at_bottom()
        t = time.time()
        self._sim_winch_in_motion_dur += t - self._sim_start_motion
        self._sim_start_pause = t

    def up_cast(self):
        self.state.up_cast()
        t = time.time()
        self._sim_winch_paused_dur += t - self._sim_start_pause
        self._sim_start_motion = t

    def up_stage(self):
        self.state.up_pause()
        t = time.time()
        self._sim_winch_in_motion_dur += t - self._sim_start_motion
        self._sim_start_pause = t

    def park(self):
        if self.cmndr.simulation:
            self._sim_latch_edge_count += 3
        self.state.park()

    def set_state(self, state: WinchState):
        self.state = state

    def get_latch_edge_count(self) -> (int, bool):
        latch_edge_count, _ = self.cmndr.get_latch_edge_count()
        if self.cmndr.simulation:
            latch_edge_count = self._sim_latch_edge_count
        return latch_edge_count, False
    
    # def _sim_inc_latch_edge_count(self, cnt: int):
    #     self._sim_latch_edge_count += cnt

    # def _sim_inc_latch_edge_count(self, cnt: int, delay_secs: int = 0) -> None:
    #     timer = 
    
    def latch_release(self):
        self.cmndr.latch_release()

    def status(self) -> (dict, bool):
        cur_status = {}

        # get payout sensors readings
        payouts, err = self.cmndr.get_payout_edge_count()
        if err:
            print(f'states:winch ERROR get payout edge count')
            return {}, err

        if self.cmndr.simulation:
            # based on 2 sec per rotation a 6 triggers
            # simulate 3 signals or 6 edges
            edgecnt = self._sim_winch_in_motion_dur * 12
            payouts = [edgecnt, edgecnt]
            err = False

        cur_status["payouts"] = payouts

        # get latch sensor readings
        latch_cnt, err = self.cmndr.get_latch_edge_count()
        if err:
            print(f'states:winch ERROR get latch sensor edge count')
            return {}, err

        if self.cmndr.simulation:
            latch_cnt = self._sim_latch_edge_count

        cur_status["latch_cnt"] = latch_cnt

        # get winch direction, if any
        if self.cmndr.simulation:
            if isinstance(self.state, (UpcastingState,)):
                cur_status["dir"] = WinchDir.DIRECTION_UP.value
            elif isinstance(self.state, (DowncastingState, StagingState)):
                cur_status["dir"] = WinchDir.DIRECTION_DOWN.value
            else:
                cur_status["dir"] = WinchDir.DIRECTION_NONE.value
            err = False
        else:
            cur_status["dir"], err = self.cmndr.get_winch_direction()
            if err:
                print(f'states:winch ERROR get winch direction')
                return {}, err

        cur_status["state"] = str(self.state)
        cur_status["ts"] = datetime.utcnow().isoformat()

        return cur_status, False

