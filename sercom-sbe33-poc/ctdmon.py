#!/usr/bin/env python3

#import readline
import argparse
import shlex
import serial
import time
import functools

EOL = '\r'

parser = argparse.ArgumentParser()

parser.add_argument("-p", "--serialport", help="serial port to connect to", 
                    default="/dev/ttyUSB0", type=str)

args = parser.parse_args()

COMMANDS_CTD = ['getcd', 'ds', 'tt']
COMMANDS_SBE33 = [str(num) for num in range(1,10)] + ['@']

def process_commands(ser : serial.Serial):
    print('Awaiting SeaBird commands...')

    while True:
        handle_messages(ser)
        the_input = input('==> ')
        if the_input:
            cmd, *args = shlex.split(the_input)
        else:
            cmd="none"

        if cmd in ['exit', 'quit']:
            break

        elif cmd=='help':
            print('Commands:')
            print('soh: Send SOH request')
            print('stop: Stop current streaming request')
            print('start: Start stream with default parameters')
            print('info: get station info')
            print('config: get station config')
            print('quit/exit: quit application')
       
        elif cmd=='ds':
            ctd_ds(cmd, ser, eop=b'/>')

        elif cmd.lower() in COMMANDS_CTD:
            print('CTD COMMNDS LIST')
            send_msg(ser, cmd)

        elif cmd in COMMANDS_SBE33:
            print('SBE33 COMMNDS LIST')
            send_msg(ser, cmd)

        # elif cmd=='@':
        #     toggle_sbe33_mode(ser)
            # send_msg(ser, cmd)

        elif cmd.lower == 'break':
            init_comms(ser)

        # # ...
        # else:
        #     send_msg(cmd)
    
    return

def send_msg(ser : serial.Serial, msg : str):
    msg = msg.rstrip() + EOL
    ba = bytearray()
    ba.extend(msg.encode())
    try:
        ser.write(ba)
        ser.flush()
    except serial.SerialTimeoutException as e:
        print(e)
    except serial.SerialException as e:
        print(e)
    else:
        pass

def send_soh_request(seq):
    pass

def send_start_dataacq(seq):
    pass 

def send_stop_dataacq(seq):
    pass

def send_station_info_request(seq):
    pass

def toggle_sbe33_mode(ser : serial.Serial):

    if ser.is_open:
        outline = '@' + EOL
        try:
            ser.write(outline.encode())
        except serial.SerialTimeoutException as toe:
            print(f'Time out writing "{outline.strip()}" ')
            return False
        else:
            pass

def init_comms(ser : serial.Serial):
    ser.write(b'\x0d\x0a\x0d\x0a') #\x0a\x0d\x0a\x0d\x0a')
    # ser.send_break(0.5)

def ctd_ds(cmd : str, ser : serial.Serial, eop=None, multiple_packets=False):

    send_msg(ser, cmd)

    # time.sleep(8)
    save_to = ser.timeout
    ser.timeout = 20
    resp = ser.read_until(expected=eop)
    ser.timeout = save_to

    print(resp.decode())
    print('ds response complete')

  


def handle_messages(ser : serial.Serial):

    HIDE_LINES = ["<Executed/>"]

    time.sleep(1)
    while ser.in_waiting:
        time.sleep(.5)
        line = ser.readline()
        if line:
            # for line in lines:
    #            line = bytearray(line).append(b'\0')
            print(f"<== {line.decode().rstrip()}")
    #        for line in lines[1:]:
    #            if functools.reduce(lambda ok, thisone: ok and not line.startswith(thisone), HIDE_LINES, True):
    #                print(f"==> {line}")
    
    return


print('Opening the Serial Port:')
ser = serial.Serial(args.serialport, 9600, timeout=10, parity=serial.PARITY_NONE, bytesize=8)
time.sleep(3)
#check for waiting messages

#start the interactive command processor
init_comms(ser)
process_commands(ser)  #start sequence number

ser.close()

# print('done')

# import asyncio
# import serial_asyncio

# class OutputProtocol(asyncio.Protocol):
#     def connection_made(self, transport):
#         self.transport = transport
#         print('port opened', transport)
#         transport.serial.rts = False  # You can manipulate Serial object via transport
#         transport.write(b'Hello, World!\n')  # Write serial data via transport

#     def data_received(self, data):
#         print('data received', repr(data))
#         if b'\n' in data:
#             self.transport.close()

#     def connection_lost(self, exc):
#         print('port closed')
#         self.transport.loop.stop()

#     def pause_writing(self):
#         print('pause writing')
#         print(self.transport.get_write_buffer_size())

#     def resume_writing(self):
#         print(self.transport.get_write_buffer_size())
#         print('resume writing')

# loop = asyncio.get_event_loop()
# coro = serial_asyncio.create_serial_connection(loop, OutputProtocol, '/dev/ttyUSB0', baudrate=9600)
# transport, protocol = loop.run_until_complete(coro)
# loop.run_forever()
# loop.close()