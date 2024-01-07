#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import datetime
from math import pi
from threading import Timer
import time
from typing import Protocol, Tuple, Union

import paho.mqtt.client as mqtt

from .dio_cmds import DIOCommander
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

    def __str__(self) -> str:
        ...        


class WinchProto(Protocol):
    cmndr: DIOCommander
    pause_t: str
    pausemon_pub: mqtt.Client

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

    def park(self):
        ...

    def set_state(self, state: WinchState):
        ...

    def get_latch_edge_count(self) -> Tuple[int, bool]:
        ...
    
    def latch_release(self):
        ...

    def status(self) -> tuple[dict, bool]:
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
        # Handled directly in wincmd loop
        pass
        # self.winch.set_state(ParkingState(self.winch))
        # self.winch.cmndr.park()
        # self.winch.set_state(ParkedState(self.winch))

    def __str__(self):
        return WinchStateName.PARKED.value


@dataclass
class StagingState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        print(f'Can not start when {self}')

    def down_cast(self):
        print(f'Can not down-cast when {self}')

    def pause(self):
        self.winch.pausemon_pub.publish(self.winch.pause_t, \
                                        "pause".encode(), qos=2)
        self.winch.cmndr.stop_winch()
        self.winch.set_state(DownStagedState(self.winch)) 
        #TODO Need to send CMD to start ctdmon data acq (initlogging, etc)

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
        print(f'Can not up-cast when {self}')

    def up_stage(self):
        print(f'Can not up-stage when {self}')

    def park(self):
        print(f'Can not park when {self}')

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
        #TODO send cmd to stop data acq in ctdmon
        if not self.winch.cmndr.cfg['winch']['NO_PARKING']:
            self.winch.set_state(ParkingState(self.winch))
            self.winch.park()
            self.winch.set_state(ParkedState(self.winch))
        else:
            print(f'Sorry, parking is disabled for today. STOPPING HERE')
            self.winch.cmndr.stop_winch()
            self.winch.set_state(ParkedState(self.winch))

    def __str__(self):
        return WinchStateName.UP_STAGED.value



@dataclass
class DowncastingState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        print(f'Can not start when {self}')

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def pause(self):
        self.winch.pausemon_pub.publish(self.winch.pause_t, \
                                        "pause".encode(), qos=2)
        self.winch.cmndr.stop_winch()
        self.winch.set_state(DownPausedState(self.winch))        

    def stop_at_bottom(self):
        self.winch.pausemon_pub.publish(self.winch.pause_t, \
                                        "pause".encode(), qos=2)
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


@dataclass
class UpcastingState():
    winch: WinchProto

    def stop(self):
        print(f'Can not stop when {self}')

    def start(self):
        print(f'Can not start when {self}')

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def pause(self):
        self.winch.pausemon_pub.publish(self.winch.pause_t, \
                                        "pause".encode(), qos=2)
        self.winch.cmndr.stop_winch()
        self.winch.set_state(UpPausedState(self.winch))        

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def up_cast(self):
        print(f'Can not upcast when {self}')

    def up_stage(self):
        self.winch.pausemon_pub.publish(self.winch.pause_t, \
                                        "pause".encode(), qos=2)
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
        self.winch.cmndr.up_cast()
        self.winch.set_state(UpcastingState(self.winch))

    def down_cast(self):
        print(f'Can not downcast when {self}.')

    def pause(self):
        print(f'Can not pause when {self}')

    def stop_at_bottom(self):
        print(f'Can not stop-at-bottom when {self}')

    def up_cast(self):
        self.winch.cmndr.up_cast()
        self.winch.set_state(UpcastingState(self.winch))

    def up_stage(self):
        print(f'Can not up-stage when {self}')

    def park(self):
        print(f'Can not park when {self}, only when up-staged')

    def __str__(self):
        return WinchStateName.UP_PAUSED.value



class Winch:

    def __init__(self, cmndr: DIOCommander):

        def on_connect(client, userdata, flags, rc):
            if rc==0:
                client.connected_flag=True #set flag
                print("winctl:states:pausemon connected OK: {client}")
            else:
                print("winctl:states:pausemon Bad connection for {client} Returned code: ", rc)
                client.loop_stop()

        def on_disconnect(client, userdata, rc):
            client.connected_flag=False #set flag
            print("winctl:states:pausemon client disconnected ok")

        def _on_pause_publish(client, userdata, mid):
            print("winctl:states:pausemon: {client} mid= "  ,mid)

    
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

        mqtt_host : str = self.cmndr.cfg["mqtt"]["HOST"]
        mqtt_port : int = self.cmndr.cfg["mqtt"]["PORT"]

        # set up pause cmd mqtt publisher
        self.pause_t = self.cmndr.cfg["mqtt"]["WINCH_PAUSE_TOPIC"]

        self.pausemon_pub : mqtt.Client = mqtt.Client('pausemon-ctl-pub')
        self.pausemon_pub.on_connect = on_connect
        self.pausemon_pub.on_disconnect = on_disconnect
        self.pausemon_pub.on_publish = _on_pause_publish
        self.pausemon_pub.connect(mqtt_host, mqtt_port)
        self.pausemon_pub.loop_start()

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
        self.state.up_stage()

    # def park(self):
    #     #TODO WORK ON LATCH_EDGE SIMULATION: use timer() ??
    #     #     PUT IN dio_cmnds.park() ??
    #     if self.cmndr.simulation:
    #         self._sim_latch_edge_count += 3
    #     self.state.park()

    def park(self):
        """Parking is moving winch backwards until LATCH signal
        is detected and then paying out for < 1sec so that bullet will latch.
        This should leave the winch in the (physically) LATCHED position
        
        NOTE we are using dio_cmndr.<command> directly to control winch while bypassing the 
        because WInch state machine because Parking requires multiple winch 
        commands all while Parking and the Winch state machine can handle this."""

        def _sim_inc_latch_cnt(edgeinc: int) -> None:
            self._sim_latch_edge_count += edgeinc
            print(f'PARKING Timer changed latch edge count to {self._sim_latch_edge_count}')

        print(f'PARKING: STARTING')

        if self.cmndr.simulation:
            t = Timer(interval=3, function=_sim_inc_latch_cnt, args=(10,))
            t.start()
            # self._sim_latch_edge_count += 3

        # check current latch edge count
        start_latch_edge_cnt, err = self.get_latch_edge_count()
        if err:
            print('PARKING UNABLE to get LATCH SENSOR state when PARKING')
            return

        new_latch_edge_count = start_latch_edge_cnt
        print(f'PARKING: LATCH EDGE CNT: {start_latch_edge_cnt}')
    
        print(f'PARKING: UP CASTING')
        self.cmndr.up_cast() #### NOT SURE THIS IS A GOOD IDEA
        latch_found = (new_latch_edge_count > start_latch_edge_cnt)
        print(f'PARKING: LATCH FOUND - INITIAL: {latch_found}')
        while not latch_found:
            # check fr new LATCH edge count
            new_latch_edge_count, err = self.get_latch_edge_count()
            print(f'PARKING: NEW LATCH EDGE CNT: {new_latch_edge_count}')
            if err:
                self.cmndr.stop_winch() #### NOT SURE THIS IS A GOOD IDEA
                print('PARKING UNABLE to get LATCH SENSOR state when PARKING')
                return
            latch_found = new_latch_edge_count > start_latch_edge_cnt
            print(f'PARKING: LATCH FOUND - LOOP: {latch_found}')

            # need a pretty fast loop here while up_casting
            time.sleep(0.05)    

        print(f'PARKING: LATCH FOUND: {latch_found}')
        print(f'PARKING: STOPPING WINCH')
        # latch has been found
        self.cmndr.stop_winch()
        # presumably we are on the LATCH now. drop a fraction of a sec (an inch or two)
        print(f'PARKING: RELEASING LATCH')
        self.cmndr.latch_release()
        time.sleep(1) # REMOVE AFTER TESTING
        print(f'PARKING: DOWNCASTING FOR {self.cmndr.cfg["winch"]["PARKING_DOWNCAST_MS"]}ms')
        self.cmndr.down_cast(stop_after_ms=int(self.cmndr.cfg["winch"]["PARKING_DOWNCAST_MS"]))
        self.cmndr.stop_winch()

    def set_state(self, state: WinchState):
        if self.cmndr.simulation:
            self.update_payout_edge_counts()
        self.state = state

    def get_latch_edge_count(self) -> Tuple[int, bool]:
        latch_edge_count_str, _ = self.cmndr.get_latch_edge_count()
        if self.cmndr.simulation:
            latch_edge_count_str = self._sim_latch_edge_count
        return int(latch_edge_count_str), False
    
    def latch_release(self):
        self.cmndr.latch_release()

    def update_payout_edge_counts(self):
        if self.cmndr.simulation:
            # calling get_payout)_edge_count just so we can send cmd being 'sent'
            _, _ = self.cmndr.get_payout_edge_count()
            t = time.time()
            if isinstance(self.state, (StagingState, DowncastingState)):
                self.down_edges += (t - self._sim_payout_ts) * 12.0
            elif isinstance(self.state, UpcastingState):
                self.up_edges += (t - self._sim_payout_ts) * 12.0
            self._sim_payout_ts = t

        else:
            # get real payout sensors readings
            payouts, err = self.cmndr.get_payout_edge_count()
            if err:
                print(f'states:winch ERROR get payout edge count')
                return
            if isinstance(self.state, (StagingState, DowncastingState)):
                self.down_edges += (payouts[0] - self.last_payout_cnt)
            elif isinstance(self.state, UpcastingState):
                self.up_edges += (payouts[0] - self.last_payout_cnt)
            self.last_payout_cnt = payouts[0]

    def depth_from_payout_edges_m(self) -> float:

        # assumes 5.25in radius sheave/wheel
        cable_radius_inches = self.cmndr.cfg["winch"]["SEA_CABLE_DIAMETER_INCH"] / 2.0
        dist_down: float = (self.down_edges / 12) * 2 * pi * (5.25 + cable_radius_inches) / 39.37008
        dist_up: float = (self.up_edges / 12) * 2 * pi * (5.25 + cable_radius_inches) / 39.37008
        return dist_down - dist_up

    def status(self) -> Tuple[dict, bool]:

        cur_status = {}

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

        if cur_status['dir'] != WinchDir.DIRECTION_NONE.value:
            self.update_payout_edge_counts()

        cur_status["depth_m"] = round(self.depth_from_payout_edges_m(), 2)
        cur_status["state"] = str(self.state)
        cur_status["ts"] = datetime.utcnow().isoformat()

        return cur_status, False
