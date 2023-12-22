from enum import Enum 
# from collections import namedtuple
# from pprint import PrettyPrinter
# from typing import Union
import xml.etree.ElementTree as ET


SBE19v2plusVars = {}
SBE19v2plusVars["ofmt_1"] = {}
SBE19v2plusVars["ofmt_1"]["temp"] = {}
SBE19v2plusVars["ofmt_1"]["temp"]["len"] = 6
SBE19v2plusVars["ofmt_1"]["cond"] = {}
SBE19v2plusVars["ofmt_1"]["cond"]["len"] = 6
SBE19v2plusVars["ofmt_1"]["press"] = {}
SBE19v2plusVars["ofmt_1"]["press"]["len"] = 6
SBE19v2plusVars["ofmt_1"]["volt0"] = {}
SBE19v2plusVars["ofmt_1"]["volt0"]["len"] = 4
SBE19v2plusVars["ofmt_1"]["volt1"] = {}
SBE19v2plusVars["ofmt_1"]["volt1"]["len"] = 4
SBE19v2plusVars["ofmt_1"]["volt2"] = {}
SBE19v2plusVars["ofmt_1"]["volt2"]["len"] = 4
SBE19v2plusVars["ofmt_1"]["volt3"] = {}
SBE19v2plusVars["ofmt_1"]["volt3"]["len"] = 4
SBE19v2plusVars["ofmt_1"]["volt4"] = {}
SBE19v2plusVars["ofmt_1"]["volt4"]["len"] = 4
SBE19v2plusVars["ofmt_1"]["volt5"] = {}
SBE19v2plusVars["ofmt_1"]["volt5"]["len"] = 4
SBE19v2plusVars["ofmt_1"]["sbe38"] = {}
SBE19v2plusVars["ofmt_1"]["sbe38"]["len"] = 5
SBE19v2plusVars["ofmt_1"]["wetlabs"] = {}
SBE19v2plusVars["ofmt_1"]["wetlabs"]["len"] = 12
SBE19v2plusVars["ofmt_1"]["GTD1_press"] = {}
SBE19v2plusVars["ofmt_1"]["GTD1_press"]["len"] = 8
SBE19v2plusVars["ofmt_1"]["GTD1_tempc"] = {}
SBE19v2plusVars["ofmt_1"]["GTD1_tempc"]["len"] = 6
SBE19v2plusVars["ofmt_1"]["GTD2_press"] = {}
SBE19v2plusVars["ofmt_1"]["GTD2_press"]["len"] = 8
SBE19v2plusVars["ofmt_1"]["GTD2_tempc"] = {}
SBE19v2plusVars["ofmt_1"]["GTD2_tempc"]["len"] = 6
SBE19v2plusVars["ofmt_1"]["optode"] = {}
SBE19v2plusVars["ofmt_1"]["optode"]["len"] = 6
SBE19v2plusVars["ofmt_1"]["sbe63_ox_ph"] = {}
SBE19v2plusVars["ofmt_1"]["sbe63_ox_ph"]["len"] = 6
SBE19v2plusVars["ofmt_1"]["sbe63_ox_tempV"] = {}
SBE19v2plusVars["ofmt_1"]["sbe63_ox_tempV"]["len"] = 6
# for moored mode only
SBE19v2plusVars["ofmt_1"]["time"] = {}
SBE19v2plusVars["ofmt_1"]["time"]["len"] = 8
    


class SBE19OutputFmt(Enum):
    # OUTPUT_FORMAT_0 = 0
    OUTPUT_FORMAT_1 = 1
    # OUTPUT_FORMAT_2 = 2
    OUTPUT_FORMAT_3 = 3
    # OUTPUT_FORMAT_4 = 4
    # OUTPUT_FORMAT_5 = 5

class SBE19Mode(Enum):
    MOORED_MODE = 1
    PROFILE_MODE = 2

class Config:

    OUTPUT_FORMATS = {
        'converted HEX': SBE19OutputFmt.OUTPUT_FORMAT_1,
        'converted decimal': SBE19OutputFmt.OUTPUT_FORMAT_3
    }

    def __init__(self, mode : SBE19Mode = SBE19Mode.PROFILE_MODE, 
                 output_format: SBE19OutputFmt = SBE19OutputFmt.OUTPUT_FORMAT_1,
                 data_chan_volt0: bool = False, data_chan_volt1: bool = False,
                 data_chan_volt2: bool = False, data_chan_volt3: bool = False,
                 data_chan_volt4: bool = False, data_chan_volt5: bool = False,
                 data_chan_sbe38: bool = False, data_chan_wetlabs: bool = False,
                 data_chan_GTD: bool = False, data_chan_DualGTD: bool = False,
                 data_chan_optode: bool = False, data_chan_sbe63: bool = False,
                 profile_scans_to_average : bool = False,
                 profile_min_cond_freq: int = 3000, profile_pump_delay: int = 60, 
                 profile_auto_run: bool = False, profile_ignore_switch: bool = True,
                 moored_sample_interval = 15, moored_ncycles = 3000,
                 moored_pump_mode = 1, moored_delay_before = 0, moored_delay_after = 0,
                 moored_transmit_realtime = False,
                 battery_type: str = "", battery_cutoff: float = 7.5,
                 echo: bool = False, output_executed_tag: bool = False,
                 output_sal: bool = False, output_sv: bool = False,
                 output_ucsd: bool = False
                 ):
        
        self.mode = mode

        self.profile_scans_to_average = profile_scans_to_average
        self.profile_min_cond_freq = profile_min_cond_freq
        self.profile_pump_delay = profile_pump_delay
        self.profile_auto_run = profile_auto_run
        self.profile_ignore_switch = profile_ignore_switch

        self.moored_sample_interval = moored_sample_interval
        self.moored_ncycles = moored_ncycles
        self.moored_pump_mode = moored_pump_mode
        self.moored_delay_before = moored_delay_before
        self.moored_delay_after = moored_delay_after
        self.moored_transmit_realtime = moored_transmit_realtime

        self.battery_type = battery_type
        self.battery_cutoff = battery_cutoff

        self.volt0 = data_chan_volt0
        self.volt1 = data_chan_volt1
        self.volt2 = data_chan_volt2
        self.volt3 = data_chan_volt3
        self.volt4 = data_chan_volt4
        self.volt5 = data_chan_volt5
        self.sbe38 = data_chan_sbe38
        self.wetlabs = data_chan_wetlabs
        self.GTD = data_chan_GTD
        self.DualGTD = data_chan_DualGTD
        self.optode = data_chan_optode
        self.sbe63 = data_chan_sbe63

        self.echo = echo
        self.output_executed_tag = output_executed_tag
        self.output_format = output_format
        self.output_sal = output_sal
        self.output_sv = output_sv
        self.output_ucsd = output_ucsd
        #

    def __str__(self):

        def bool2YesNo(val: bool) -> str:
            return 'Yes' if val else 'No'

        res = ""
        res += f"{'Mode:':>30} {self.mode:<20}\n"
        res += f"{'Output Format:':>30} {self.output_format:<20}\n"
        if self.mode == SBE19Mode.MOORED_MODE:
            res += f"{'Sample Interval:':>30} {self.moored_sample_interval:<20}\n"
            res += f"{'NCycles:':>30} {self.moored_ncycles:<20}\n"
            res += f"{'Pump Mode:':>30} {self.moored_pump_mode:<20}\n"
            res += f"{'DElay Before Sampling:':>30} {self.moored_delay_before:<20}\n"
            res += f"{'Delay After Sampling:':>30} {self.moored_delay_after:<20}\n"
            res += f"{'Transmit Real-Time:':>30} {self.moored_transmit_realtime:<20}\n"
        elif self.mode == SBE19Mode.PROFILE_MODE:
            res += f"{'profile_scans_to_average:':>30} {self.profile_scans_to_average:<20}\n"
            res += f"{'profile_min_cond_freq:':>30} {self.profile_min_cond_freq:<20}\n"
            res += f"{'profile_pump_delay:':>30} {self.profile_pump_delay:<20}\n"
            res += f"{'profile_auto_run:':>30} {self.profile_auto_run:<20}\n"
            res += f"{'profile_ignore_switch:':>30} {self.profile_ignore_switch:<20}\n"

        res += f"{'echo:':>30} {bool2YesNo(self.echo)}\n"
        res += f"{'output_executed_tag:':>30} {bool2YesNo(self.output_executed_tag)}\n"
        res += f"{'output_sal:':>30} {bool2YesNo(self.output_sal)}\n"
        res += f"{'output_sv:':>30} {bool2YesNo(self.output_sv)}\n"
        res += f"{'output_ucsd:':>30} {bool2YesNo(self.output_ucsd)}\n"

        res += f"{'volt0:':>30} {bool2YesNo(self.volt0)}\n"
        res += f"{'volt1:':>30} {bool2YesNo(self.volt1)}\n"
        res += f"{'volt2:':>30} {bool2YesNo(self.volt2)}\n"
        res += f"{'volt3:':>30} {bool2YesNo(self.volt3)}\n"
        res += f"{'volt4:':>30} {bool2YesNo(self.volt4)}\n"
        res += f"{'volt5:':>30} {bool2YesNo(self.volt5)}\n"
        res += f"{'sbe38:':>30} {bool2YesNo(self.sbe38)}\n"
        res += f"{'wetlabs:':>30} {bool2YesNo(self.wetlabs)}\n"
        res += f"{'GTD:':>30} {bool2YesNo(self.GTD)}\n"
        res += f"{'DualGTD:':>30} {bool2YesNo(self.DualGTD)}\n"
        res += f"{'optode:':>30} {bool2YesNo(self.optode)}\n"
        res += f"{'sbe63:':>30} {bool2YesNo(self.sbe63)}\n"

        res += f"{'battery_type:':>30} {self.battery_type:<20}\n"
        res += f"{'battery_cutoff:':>30} {self.battery_cutoff:<20}\n"

        return res

    def update_getcd_info(self, xml_str : str) -> bool:

        #TODO Logging
        # print(xml_str.strip())

        config_el = ET.fromstring(xml_str)
        if config_el is None:
            print('no configurqation') #TODO LOG Error
            return False

        # Look for Profile Mode tag...
        # for child in root:
        profile_el = config_el.find('ProfileMode')
        if profile_el is not None:
            # print("In Profile mode") 
            #TODO Logging
            self.mode = SBE19Mode.PROFILE_MODE
            child = profile_el.find('ScansToAverage')
            if child is not None:
                self.profile_scans_to_average = int(child.text.strip())
            else:
                print('no ScansToAverage') #TODO LOG Error
                #TODO LOG Error
                return False 
            child = profile_el.find('MinimumCondFreq')
            if child is not None:
                self.profile_min_cond_freq = int(child.text.strip())
            else:
                print('no mincondfreq') #TODO LOG Error
                #TODO LOG Error
                return False 
            child = profile_el.find('PumpDelay')
            if child is not None:
                self.profile_pump_delay = int(child.text.strip())
            else:
                print('no pumpdelay') #TODO LOG Error
                #TODO LOG Error
                return False 
            child = profile_el.find('AutoRun')
            if child is not None:
                self.profile_auto_run = child.text.strip().lower() in ['y','yes']
            else:
                print('no autorun') #TODO LOG Error
                #TODO LOG Error
                return False 
            child = profile_el.find('IgnoreSwitch')
            if child is not None:
                self.profile_ignore_switch = child.text.strip().lower() in ['y','yes']
            else:
                print('no ignoreswitch') #TODO LOG Error
                #TODO LOG Error
                return False 

        moored_el = config_el.find('MooredMode')
        if moored_el is not None:
            print("In Moored mode") #TODO Logging
            self.mode = SBE19Mode.MOORED_MODE
            child = moored_el.find('SampleInterval')
            if child is not None:
                self.moored_sample_interval = int(child.text.strip())
            else:
                #TODO LOG Error
                return False 
            child = moored_el.find('MeasurementsPerSample')
            if child is not None:
                self.moored_ncycles = int(child.text.strip())
            else:
                #TODO LOG Error
                return False 
            child = moored_el.find('Pump')
            if child is not None:
                self.moored_pump_mode = int(child.text.strip())
            else:
                #TODO LOG Error
                return False 
            child = moored_el.find('SampleInterval')
            if child is not None:
                self.moored_delay_before = float(child.text.strip())
            else:
                #TODO LOG Error
                return False 
            child = moored_el.find('SampleInterval')
            if child is not None:
                self.moored_delay_after = float(child.text.strip())
            else:
                #TODO LOG Error
                return False 
            child = moored_el.find('SampleInterval')
            if child is not None:
                self.moored_transmit_realtime = child.text.strip().lower() in ['y','yes']
            else:
                #TODO LOG Error
                return False 

        battery_el = config_el.find('Battery')
        if battery_el is not None:
            child = battery_el.find('Type')
            if child is not None:
                self.battery_type = child.text.strip()
            else:
                #TODO LOG Error
                return False 
            child = battery_el.find('CutOff')
            if child is not None:
                self.battery_cutoff = child.text.strip()
            else:
                #TODO LOG Error
                return False 
        else:
            #TODO LOG Error
            print('no battery')
            return False 

        data_el = config_el.find('DataChannels')
        if data_el is not None:
            child = data_el.find('ExtVolt0')
            if child is not None:
                self.volt0 = child.text.strip().lower() in ['y','yes']
            else:
                print('ExtVolt0')
                #TODO LOG Error
                return False 
            child = data_el.find('ExtVolt1')
            if child is not None:
                self.volt1 = child.text.strip().lower() in ['y','yes']
            else:
                print('ExtVolt1')
                #TODO LOG Error
                return False 
            child = data_el.find('ExtVolt2')
            if child is not None:
                self.volt2 = child.text.strip().lower() in ['y','yes']
            else:
                print('ExtVolt2')
                #TODO LOG Error
                return False 
            child = data_el.find('ExtVolt3')
            if child is not None:
                self.volt3 = child.text.strip().lower() in ['y','yes']
            else:
                print('ExtVolt3')
                #TODO LOG Error
                return False 
            child = data_el.find('ExtVolt4')
            if child is not None:
                self.volt4 = child.text.strip().lower() in ['y','yes']
            else:
                print('ExtVolt4')
                #TODO LOG Error
                return False 
            child = data_el.find('ExtVolt5')
            if child is not None:
                self.volt5 = child.text.strip().lower() in ['y','yes']
            else:
                print('ExtVolt5')
                #TODO LOG Error
                return False 

            child = data_el.find('SBE38')
            if child is not None:
                self.sbe38 = child.text.strip().lower() in ['y','yes']
            else:
                print('sbe38')
                #TODO LOG Error
                return False 
            child = data_el.find('WETLABS')
            if child is not None:
                self.wetlabs = child.text.strip().lower() in ['y','yes']
            else:
                print('WETLABS')
                #TODO LOG Error
                return False 
            child = data_el.find('OPTODE')
            if child is not None:
                self.GTD = child.text.strip().lower() in ['y','yes']
            else:
                print('optode')
                #TODO LOG Error
                return False 
            child = data_el.find('SBE63')
            if child is not None:
                self.DualGTD = child.text.strip().lower() in ['y','yes']
            else:
                print('optode')
                #TODO LOG Error
                return False 
            child = data_el.find('SBE38')
            if child is not None:
                self.optode = child.text.strip().lower() in ['y','yes']
            else:
                #TODO LOG Error
                return False 
            child = data_el.find('SBE38')
            if child is not None:
                self.sbe63 = child.text.strip().lower() in ['y','yes']
            else:
                #TODO LOG Error
                return False 
        else:
            #TODO LOG Error
            print('error parsing DataChannels')
            return False 

        
        child = config_el.find('EchoCharacters')
        if child is not None:
            self.echo = child.text.strip().lower() in ['y','yes']
        else:
            pass #TODO LOG Error
        child = config_el.find('OutputExecutedTag')
        if child is not None:
            self.output_executed_tag = child.text.strip().lower() in ['y','yes']
        else:
            pass #TODO LOG Error

        child = config_el.find('OutputFormat')
        if child is not None:
            self.output_format = self.OUTPUT_FORMATS[child.text.strip()]
        else:
            pass #TODO LOG Error

        child = config_el.find('OutputSalinity')
        if child is not None:
            self.output_sal = child.text.strip().lower() in ['y','yes']
        child = config_el.find('OutputSoundVelocity')
        if child is not None:
            self.output_sv = child.text.strip().lower() in ['y','yes']
        child = config_el.find('OutputSigma_T')
        if child is not None:
            self.output_ucsd = child.text.strip().lower() in ['y','yes']

        # print(f"All done parding") 
        #TODO Logging
        return True

