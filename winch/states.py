#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import datetime
from math import pi
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

    def pause(self):
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
        self.winch.cmndr.stop_winch()
        self.winch.set_state(DownStagedState(self.winch))        

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


@dataclass
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


@dataclass
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



@dataclass
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



@dataclass
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


@dataclass
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

@dataclass
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

@dataclass
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

        # set up payout vars
        self.down_edges: float = 0.0
        self.up_edges: float = 0.0
        self.last_payout_cnt: int
        self._sim_payout_ts: float = time.time()  # only used when simulation == True

        if not self.cmndr.simulation:
            payouts, err = self.cmndr.get_payout_edge_count()
            if err:
                print(f'winch:winch: ERROR getting payout edge cnts')
                return 
            else:
                self.last_payout_cnt = payouts[0]  # doesn't matter which sensor we use

        # vars only to facilitate simulated responses from winch
        self._sim_latch_edge_count = 0

    def stop(self):
        self.state.stop()

    def start(self):
        self.state.start()

    def down_cast(self):
        self.state.down_cast()

    def pause(self):
        self.state.pause()

    def stop_at_bottom(self):
        self.state.stop_at_bottom()

    def up_cast(self):
        self.state.up_cast()

    def up_stage(self):
        self.state.pause()

    def park(self):
        #TODO WORK ON LATCH_EDGE SIMULATION: use timer() ??
        #     PUT IN dio_cmnds.park() ??
        if self.cmndr.simulation:
            self._sim_latch_edge_count += 3
        self.state.park()

    def set_state(self, state: WinchState):
        if self.cmndr.simulation:
            self.update_payout_edge_counts()
        self.state = state

    def get_latch_edge_count(self) -> (int, bool):
        latch_edge_count, _ = self.cmndr.get_latch_edge_count()
        if self.cmndr.simulation:
            latch_edge_count = self._sim_latch_edge_count
        return latch_edge_count, False
    
    def latch_release(self):
        self.cmndr.latch_release()

    def update_payout_edge_counts(self):
        if self.cmndr.simulation:
            t = time.time()
            if isinstance(self.state, (StagingState, DowncastingState)):
                self.down_edges += (t - self._sim_payout_ts) * 12.0
            elif self.state in [UpcastingState]:
                self.up_edges += (t - self._sim_payout_ts) * 12.0
            self._sim_payout_ts = t

        else:
            # get real payout sensors readings
            payouts, err = self.cmndr.get_payout_edge_count()
            if err:
                print(f'states:winch ERROR get payout edge count')
                return
            if self.state in [StagingState, DowncastingState]:
                self.down_edges += (payouts[0] - self.last_payout_cnt)
            elif self.state in [UpcastingState]:
                self.up_edges += (payouts[0] - self.last_payout_cnt)
            self.last_payout_cnt = payouts[0]

    def depth_from_payout_edges_m(self) -> float:
        # assumes 5.25in radius wheel
        #TODO THIS MUST BE REFINED TO INCLUDE CABLE RADIUS
        dist_down: float = (self.down_edges / 12) * 2 * pi * 5.25 / 39.37008
        dist_up: float = (self.up_edges / 12) * 2 * pi * 5.25 / 39.37008
        return dist_down - dist_up

    def status(self) -> (dict, bool):

        cur_status = {}

        self.update_payout_edge_counts()

        cur_status["depth_m"] = round(self.depth_from_payout_edges_m(), 2)

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
