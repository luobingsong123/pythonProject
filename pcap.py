# !/usr/bin/env python
# coding=utf-8
# 读取pcap文件，解析相应的信息，为了在记事本中显示的方便，把二进制的信息

import struct
import time, datetime


def time_trans(GMTtime):
    timeArray = time.localtime(GMTtime)
    otherStyleTime = time.strftime("%Y--%m--%d %H:%M:%S", timeArray)
    return otherStyleTime  # 2013--10--10 23:40:00


class pcap_packet_header:
    def __init__(self):
        self.GMTtime = b'\x00\x00'
        self.MicroTime = b'\x00\x00'
        self.caplen = b'\x00\x00'
        self.lens = b'\x00\x00'


if __name__ == '__main__':

    fpcap = open(r'D:\广发证券FPGA行情POC方案\SZMDGW20210825_tcpdump.pcap', 'rb')
    ftxt = open('result.txt', 'w')
    fout = open('zs0401_1.bin', 'wb')
    string_data = fpcap.read()

    # pcap文件包头解析
    # 第一个头解析
    pcap_header = {}
    pcap_header['magic_number'] = string_data[0:4]
    pcap_header['version_major'] = string_data[4:6]
    pcap_header['version_minor'] = string_data[6:8]
    pcap_header['thiszone'] = string_data[8:12]
    pcap_header['sigfigs'] = string_data[12:16]
    pcap_header['snaplen'] = string_data[16:20]
    pcap_header['linktype'] = string_data[20:24]
    print(pcap_header)
    # 把pacp文件头信息写入result.txt
    ftxt.write("Pcap文件的包头内容如下： \n")
    for key in ['magic_number', 'version_major', 'version_minor', 'thiszone',
                'sigfigs', 'snaplen', 'linktype']:
        ftxt.write(key + " : " + repr(pcap_header[key]) + '\n')

    # pcap文件的数据包解析
    step = 0
    packet_num = 0
    packet_data = []

    pcap_packet_header_list = []
    i = 24
    while (i < len(string_data)):
    # while i < 10000:
        # 数据包头各个字段bytes
        GMTtime = string_data[i:i + 4]
        MicroTime = string_data[i + 4:i + 8]
        caplen = string_data[i + 8:i + 12]
        lens = string_data[i + 12:i + 16]
        # 数据包各个字段的正常表示
        packet_GMTtime = struct.unpack('I', GMTtime)[0]
        # print('GMTtime',packet_GMTtime)
        # print('GMTtime len',len(str(packet_GMTtime)))
        packet_GMTtime = time_trans(packet_GMTtime)
        # print('GMTtime',packet_GMTtime)
        # print('GMTtime len',len(str(packet_GMTtime)))
        packet_MicroTime = struct.unpack('I', MicroTime)[0]
        # print('microtime',packet_MicroTime)
        # print('microtime len',len(str(packet_MicroTime)))
        packet_caplen = struct.unpack('I', caplen)[0]
        # print('caplen',packet_caplen)
        # print('caplen len',len(str(packet_caplen)))
        packet_len = struct.unpack('I', lens)[0]
        # print('len',packet_len)
        # print('len len',len(str(packet_len)))
        # 数据包头对象
        head = pcap_packet_header()
        head.GMTtime = packet_GMTtime
        head.MicroTime = packet_MicroTime
        head.caplen = packet_caplen
        head.lens = packet_len
        # print(head.MicroTime)
        # print(packet_MicroTime)
        pcap_packet_header_list.append(head)
        # print(packet_len)
        # 写入此包数据
        # packet_data.append(string_data[i + 16:i + 16 + packet_len])
        # i = i + packet_len + 16
        fout.write(string_data[i + 70:i + packet_len + 16])
        i = i + packet_len + 16
        packet_num += 1
        # a=input()
        # 把pacp文件里的数据包信息写入result.txt
    for i in range(packet_num):
        # 先写每一包的包头
        ftxt.write("这是第" + str(i) + "包数据的包头和数据：" + '\n')
        ftxt.write('GMTtime' + ' : ' + repr(pcap_packet_header_list[i].GMTtime) + '\n')
        ftxt.write('MicroTime' + ' : ' + repr(pcap_packet_header_list[i].MicroTime) + '\n')
        ftxt.write('caplen' + ' : ' + repr(pcap_packet_header_list[i].caplen) + '\n')
        ftxt.write('lens' + ' : ' + repr(pcap_packet_header_list[i].lens) + '\n')
        # 再写数据部分
        # ftxt.write('此包的数据内容' + repr(packet_data[i]) + '\n')
        # fout.write(packet_data[i])
    ftxt.write('一共有' + str(packet_num) + "包数据" + '\n')
    fout.close()
    # ftxt.close()
    fpcap.close()
    print('all data packet :', packet_num)
    '''
    def display_hex(frame): 
      hex_str='' 
      for j in frame:
        temp=ord(j) 
        temp=hex(temp) 
        if len(temp)==3: 
          temp = temp.replace('0x','0x0') 
        hex_str=hex_str+temp 
      hex_str=hex_str.replace('0x',' ') 
      return hex_str

      '''
