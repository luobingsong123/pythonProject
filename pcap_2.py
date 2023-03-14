#!/usr/bin/python
import binascii as B
import sys
import re
import os
from time import sleep


Pcap_Head_Dir = {
    'magic': 4,
    'major': 2,
    'minor': 2,
    'thiszone':4,
    'sigfigs':4,
    'snaplen':4,
    'linktype':4,
    'timestamp_s':4,
    'timestamp_ns':4,
    'caplen': 4,
    'len':4
}
Pcap_Head_list =['magic', 'major', 'minor', 'thiszone', 'sigfigs', 'snaplen', 'linktype', 'timestamp_s', 'timestamp_ns', 'caplen','len']
Packet_Header = ['timestamp_s', 'timestamp_ns', 'caplen','len']
timestamp_list = []


def read_file(pcap_file):
    pcap_file.read(40)
    content = pcap_file.read(38)
    content_hex = B.b2a_hex(content)
    need_content_hex = re.sub(r"(?<=\w)(?=(?:\w\w)+$)", " ", content_hex)
    content_hex_list = need_content_hex.split()
    Source_IP_list = [str(int(content_hex_list[26], 16)), str(int(content_hex_list[27],16)), str(int(content_hex_list[28],16)), str(int(content_hex_list[29],16))]
    S_Port =content_hex_list[34] + content_hex_list[35]
    P_Port = content_hex_list[36] + content_hex_list[37]
    Source_ip = '.'.join(Source_IP_list)
    Source_port = str(int(S_Port, 16))
    Port_port = str(int(P_Port,16))
    pcap_file.close()
    return Source_ip, Source_port, Port_port


if __name__ == '__main__':
    if len(sys.argv) !=2:
        print('The usage: ./demo.py file.pcap')
        sys.exit()
    file_name = sys.argv[1]
    file = open(file_name, 'rb')
    file.seek(0)
    source_ip, source_port, purpose_port =read_file(file)
    print('The Source_IP is %s' % source_ip)
    print('The Source_Port is %s' % source_port)
    cmd1 = 'tcpprep -c %s' % source_ip
    cmd2 = '/24 -i %s' % file_name
    cmd3 = '\t-o out.cache'
    complete_cmd = cmd1 + cmd2 + cmd3
    print(complete_cmd)
    os.system(complete_cmd)
    sleep(2)
    print('Had Generate the out.cache')
    print('Start to rewrite the cache')
    new_source_ip = raw_input('Please type the New_Source_IP:')
    new_purpose_ip = raw_input('Please type the New_Purpose_IP(MultiCast IP):\n(Pay attention: \n224.0.0.0~239.255.255.255)\n224~239\nmust be 0\nless than 10\nless than10\n:')
    cmd4 = 'tcprewrite --endpoints=%s:%s' % (new_source_ip, new_purpose_ip)
    cmd5 = '\t--cachefile=out.cache --infile=%s' % file_name
    smac = raw_input('Please type the ether from ifconfig in %s:'% new_source_ip)
    b = new_purpose_ip.split('.')
    last_8 = int(b[-1])
    second_8 = int(b[-2])
    first_8 = int(b[-3])
    last_hex = hex(int(last_8)).split('0x')[1]
    second_hex = hex(int(second_8)).split('0x')[1]
    first_hex = hex(int(first_8)).split('0x')[1]
    c = [first_hex, second_hex, last_hex]
    e = []
    for i in c:
        if len(i) < 2:
            i = '0' + i
        e.append(i)
    d = ':'.join(e)
    dmac = '01:00:5e:' + d
    cmd6 = '\t--enet-dmac=%s --enet-smac=%s --outfile=output1.pcap' % (dmac, smac)
    completed_cmd2 = cmd4 + cmd5 + cmd6
    os.system('cd /home/HQM-MultiCast/MDGW_server/pcap;%s' % completed_cmd2)
    print(completed_cmd2)
    print('ALL done')
    print('SourceIP is: %s' %new_source_ip)
    print('PurposeIP is:%s' % new_purpose_ip)
    print('The purpose_port is %s' % purpose_port)