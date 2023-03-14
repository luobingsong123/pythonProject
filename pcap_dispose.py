import struct
import binascii
from scapy.all import *


if __name__ == '__main__':
    pcap = rdpcap(r'C:\Users\DELL\Desktop\pocp2p_acudp.pcap')
    i = 0
    while i < len(pcap):
        pcap_s = pcap[i]
        pcap_s.show()
        i +=1


    # fpcap = open(r'C:\Users\DELL\Desktop\pocp2p_acudp.pcap', 'rb')
    # string_data = fpcap.read()
    # head = string_data[0:40]
    # i = 40
    # data = {}
    # data['MsgType'] = binascii.b2a_hex(string_data[i:i+1])
    # # data['MsgLength'] = int(binascii.b2a_hex(string_data[i+1:i+2]))
    # data['MsgLength'] = struct.unpack('B', string_data[i+1:i+2])[0]
    # data['MsgID'] = struct.unpack('I', string_data[i+2:i+6])[0]
    # print(data['MsgLength'])
    # print(data['MsgID'])
    # data['body'] = binascii.b2a_hex(string_data[i:i + int(data['MsgLength'])])
    # print(data['body'])

    # print(binascii.b2a_hex(string_data[0:40]))  # 40
    # print(binascii.b2a_hex(string_data[40:42]))     # 1+1
    # print(binascii.b2a_hex(string_data[42:255]))    # len - 2
    # print(binascii.b2a_hex(string_data[255:271]))   # 16
    # print(binascii.b2a_hex(string_data[271:287]))   # 16
    # print(binascii.b2a_hex(string_data[287:777]))
    # pcap文件包头解析
    # 第一个头解析
    # pcap_header = {}
    # pcap_header['magic_number'] = string_data[0:4]
    # pcap_header['version_major'] = string_data[4:6]
    # pcap_header['version_minor'] = string_data[6:8]
    # pcap_header['thiszone'] = string_data[8:12]
    # pcap_header['sigfigs'] = string_data[12:16]
    # pcap_header['snaplen'] = string_data[16:20]
    # pcap_header['linktype'] = string_data[20:24]
    # print(pcap_header)
    # msg = {}
    # msg['tyep'] = string_data[0:256]
    # print(msg)
    # i = 0
    # 首保头40
    # 统一尾16
    # while i < 1024:
    #     # print(struct.unpack('I', string_data[i:i + 4])[0])
    #     print(binascii.b2a_hex(string_data[i:i + 8]))
    #     i += 8
