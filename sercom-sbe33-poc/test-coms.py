#!/usr/bin/env python3

#import readline
import argparse
import shlex
import serial
import functools

parser = argparse.ArgumentParser()

parser.add_argument("-p", "--serialport", help="serial port to connect to", 
                    default="/dev/ttyUSB0", type=str)

args = parser.parse_args()

def process_commands(ser, seq_num):
    print('Awaiting commands...')
    print('To get help, enter `help`.')

    while True:
        handle_messages(ser)
        the_input = input('> ')
        if the_input:
            cmd, *args = shlex.split(the_input)
        else:
            cmd="none"

        if cmd=='exit':
            break

        elif cmd=='quit':
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
            send_msg(cmd)
            seq_num+=1

        elif cmd=='getcd':
            send_msg(cmd)
            seq_num+=1

        # elif cmd=='stop':
        elif cmd=='1':
            send_msg(cmd)
            seq_num+=1

        elif cmd=='2':
            send_msg(cmd)
            seq_num+=1

        elif cmd=='9':
            send_msg(cmd)
            seq_num+=1

        elif cmd=='@':
            send_msg(cmd)
            seq_num+=1

        # ...
        else:
            send_msg(cmd)
            seq_num+=1
    
    return

def send_msg(msg):
    ba = bytearray()
    if msg != '@':
        msg += "\r\n"
    ba.extend(msg.encode())
    res = ser.write(ba)
    # print(f"ser.write({ba}: {res}")

def send_soh_request(seq):
    message = bytearray()
    message += struct.pack('!H',1) #ApplicationLayerVersion
    message += struct.pack('!H',3) #PacketType
    message += struct.pack('!H',0) #PacketPayloadLength

    #Transport Layer
    SegmentHeader = bytearray()
    SegmentHeader += struct.pack('!H',1) #TransportLayerVersion
    SegmentHeader += struct.pack('!H',seq) #PacketSequenceNumber  every request needs to be different than the one before
    SegmentHeader += struct.pack('!H',0) #SegmentIndex
    SegmentHeader += struct.pack('!H',1)  #SegmentTotalCount
    SegmentHeader += struct.pack('!H',len(message))  #SegmentPayloadLength

    SegmentHeaderCRC = bytearray()
    SegmentHeaderCRC += struct.pack('!H',crcPegasus(SegmentHeader)) #(Bytes 0-9 inclusive)

    SegmentPayloadCRC = bytearray()
    SegmentPayloadCRC += struct.pack('!H',crcPegasus(message))
    #end Transportlayer
    #end Datalink Layer

    FrameSynchronizationWord = b'PT02'

    #create an SOH request Message
    soh_req = bytearray()
    soh_req += FrameSynchronizationWord
    soh_req += SegmentHeader
    soh_req += SegmentHeaderCRC
    soh_req += message
    soh_req += SegmentPayloadCRC

    print("Sending:")
    print(soh_req.hex())

    ser.write(soh_req)    
    return

def send_start_request(seq):
    message = bytearray()
    message += struct.pack('!H',1) #ApplicationLayerVersion
    message += struct.pack('!H',1) #PacketType
    message += struct.pack('!H',6) #PacketPayloadLength
    message += struct.pack('!H', 0x07) #Channels
    message += struct.pack('!b', 10) #SamplingRate factor
    message += struct.pack('!b', 1) #SamplingRate multiplier
    message += struct.pack('!B', 24) #SampleResolution
    message += struct.pack('!B', 1)  #DataframesPerPacket

    #Transport Layer
    SegmentHeader = bytearray()
    SegmentHeader += struct.pack('!H',1) #TransportLayerVersion
    SegmentHeader += struct.pack('!H',seq) #PacketSequenceNumber  every request needs to be different than the one before
    SegmentHeader += struct.pack('!H',0) #SegmentIndex
    SegmentHeader += struct.pack('!H',1)  #SegmentTotalCount
    SegmentHeader += struct.pack('!H',len(message))  #SegmentPayloadLength
    #print("Header CRC")
    #print(hex(crcPegasus(SegmentHeader)))

    SegmentHeaderCRC = bytearray()
    SegmentHeaderCRC += struct.pack('!H',crcPegasus(SegmentHeader)) #(Bytes 0-9 inclusive)

    SegmentPayloadCRC = bytearray()
    SegmentPayloadCRC += struct.pack('!H',crcPegasus(message))

    #end Transportlayer
    #end Datalink Layer

    FrameSynchronizationWord = b'PT02'

    #create an SOH request Message
    stream_req = bytearray()
    stream_req += FrameSynchronizationWord
    stream_req += SegmentHeader
    stream_req += SegmentHeaderCRC
    stream_req += message
    stream_req += SegmentPayloadCRC

    print("Sending:")
    print(stream_req.hex())

    ser.write(stream_req)
    return 

def send_stop_request(seq):
    message = bytearray()
    message += struct.pack('!H',1) #ApplicationLayerVersion
    message += struct.pack('!H',2) #PacketType
    message += struct.pack('!H',0) #PacketPayloadLength

    #Transport Layer
    SegmentHeader = bytearray()
    SegmentHeader += struct.pack('!H',1) #TransportLayerVersion
    SegmentHeader += struct.pack('!H',seq) #PacketSequenceNumber  every request needs to be different than the one before
    SegmentHeader += struct.pack('!H',0) #SegmentIndex
    SegmentHeader += struct.pack('!H',1)  #SegmentTotalCount
    SegmentHeader += struct.pack('!H',len(message))  #SegmentPayloadLength
    #print("Header CRC")
    #print(hex(crcPegasus(SegmentHeader)))

    SegmentHeaderCRC = bytearray()
    SegmentHeaderCRC += struct.pack('!H',crcPegasus(SegmentHeader)) #(Bytes 0-9 inclusive)

    SegmentPayloadCRC = bytearray()
    SegmentPayloadCRC += struct.pack('!H',crcPegasus(message))

    #end Transportlayer
    #end Datalink Layer

    FrameSynchronizationWord = b'PT02'

    #create an SOH request Message
    stream_req = bytearray()
    stream_req += FrameSynchronizationWord
    stream_req += SegmentHeader
    stream_req += SegmentHeaderCRC
    stream_req += message
    stream_req += SegmentPayloadCRC

    print("Sending:")
    print(stream_req.hex())

    ser.write(stream_req)    
    return

def send_station_info_request(seq):
    message = bytearray()
    message += struct.pack('!H',1) #ApplicationLayerVersion
    message += struct.pack('!H',4) #PacketType
    message += struct.pack('!H',0) #PacketPayloadLength

    #Transport Layer
    SegmentHeader = bytearray()
    SegmentHeader += struct.pack('!H',1) #TransportLayerVersion
    SegmentHeader += struct.pack('!H',seq) #PacketSequenceNumber  every request needs to be different than the one before
    SegmentHeader += struct.pack('!H',0) #SegmentIndex
    SegmentHeader += struct.pack('!H',1)  #SegmentTotalCount
    SegmentHeader += struct.pack('!H',len(message))  #SegmentPayloadLength

    SegmentHeaderCRC = bytearray()
    SegmentHeaderCRC += struct.pack('!H',crcPegasus(SegmentHeader)) #(Bytes 0-9 inclusive)

    SegmentPayloadCRC = bytearray()
    SegmentPayloadCRC += struct.pack('!H',crcPegasus(message))
    #end Transportlayer
    #end Datalink Layer

    FrameSynchronizationWord = b'PT02'

    #create an SOH request Message
    req = bytearray()
    req += FrameSynchronizationWord
    req += SegmentHeader
    req += SegmentHeaderCRC
    req += message
    req += SegmentPayloadCRC

    print("Sending:")
    print(req.hex())

    ser.write(req)    
    return

def send_station_config_request(seq):
    message = bytearray()
    message += struct.pack('!H',1) #ApplicationLayerVersion
    message += struct.pack('!H',8) #PacketType
    message += struct.pack('!H',0) #PacketPayloadLength

    #Transport Layer
    SegmentHeader = bytearray()
    SegmentHeader += struct.pack('!H',1) #TransportLayerVersion
    SegmentHeader += struct.pack('!H',seq) #PacketSequenceNumber  every request needs to be different than the one before
    SegmentHeader += struct.pack('!H',0) #SegmentIndex
    SegmentHeader += struct.pack('!H',1)  #SegmentTotalCount
    SegmentHeader += struct.pack('!H',len(message))  #SegmentPayloadLength

    SegmentHeaderCRC = bytearray()
    SegmentHeaderCRC += struct.pack('!H',crcPegasus(SegmentHeader)) #(Bytes 0-9 inclusive)

    SegmentPayloadCRC = bytearray()
    SegmentPayloadCRC += struct.pack('!H',crcPegasus(message))
    #end Transportlayer
    #end Datalink Layer

    FrameSynchronizationWord = b'PT02'

    #create an SOH request Message
    req = bytearray()
    req += FrameSynchronizationWord
    req += SegmentHeader
    req += SegmentHeaderCRC
    req += message
    req += SegmentPayloadCRC

    print("Sending:")
    print(req.hex())

    ser.write(req)    
    return


def handle_messages(ser):

    HIDE_LINES = ["<Executed/>"]

    #retrieve any messages
    # print(ser.readlines())
#    lines = [line.decode().strip() for line in ser.readlines()]
    lines = ser.readlines()
    if lines:
        for line in lines:
#            line = bytearray(line).append(b'\0')
            print(f"==> {line.decode()}")
#        for line in lines[1:]:
#            if functools.reduce(lambda ok, thisone: ok and not line.startswith(thisone), HIDE_LINES, True):
#                print(f"==> {line}")

    return


print('Opening the Serial Port:')
ser = serial.Serial(args.serialport, 9600, timeout=2, parity=serial.PARITY_NONE, bytesize=8)
print(ser)

#check for waiting messages

#start the interactive command processor
process_commands(ser, 10)  #start sequence number

ser.close()

print('done')

