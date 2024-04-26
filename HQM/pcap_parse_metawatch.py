#!/usr/bin/python3
# -*- coding: UTF-8 -*-
import struct
import socket
import binascii
import sys
import platform

def inet_to_str(inet):
    """将网络地址转换为字符串"""
    return socket.inet_ntop(socket.AF_INET, inet)

def parse_pcap(file_name):
    with open(file_name, 'rb') as f:
        # 读取pcap文件头
        pcap_header = f.read(24)
        while True:
            # 读取pcap数据包头
            pkt_header = f.read(16)
            if not pkt_header:
                break
            sec, usec, caplen, length = struct.unpack('IIII', pkt_header)
            # 读取数据包数据
            pkt_data = f.read(caplen)
            # 解析以太网头
            eth_header = pkt_data[:14]
            eth_type = struct.unpack('!H', eth_header[12:14])[0]
            if eth_type == 0x0800:  # IP协议
                # 解析IP头
                ip_header = pkt_data[14:34]
                src_ip = inet_to_str(ip_header[12:16])
                dst_ip = inet_to_str(ip_header[16:20])
                protocol = ip_header[9]
                metawatch_dev_msg = binascii.b2a_hex(pkt_data[-4:])
                metawatch_timestamp = binascii.b2a_hex(pkt_data[-12:-4])
                # 解析TCP/UDP头
                if protocol == 6 or protocol == 17:  # TCP或UDP协议
                    transport_header = pkt_data[34:54]
                    src_port = struct.unpack('!H', transport_header[0:2])[0]
                    dst_port = struct.unpack('!H', transport_header[2:4])[0]
                    yield (src_ip, src_port, dst_ip, dst_port, protocol, length, pkt_data[54:].hex(), metawatch_dev_msg, int(metawatch_timestamp, 16))
                else:  # 其他协议
                    yield (protocol, length, hex(eth_type))
            else:  # 其他协议
                protocol = None  # 或者你可以设置一个特殊的值
                yield (protocol, length, hex(eth_type))


def write_to_file(file_name, data):
    tick_timestamp = []
    trade_timestamp = []
    with open(file_name, 'w') as f:
        for item in data:
            if len(item) == 9:
                if item[2] != "10.10.1.107" and item[4] is not None:
                    f.write(f'{item[0]}:{item[1]} -> {item[2]}:{item[3]}, protocol: {item[4]}, length: {item[5]}, metawatch_devid:{item[7]}, timestamp:{item[8]} ,payload: {item[6]}\n')
                if item[0] == "10.10.1.138" and item[1] == 5566:
                    tick_timestamp.append(item[8])
                if item[0] == "10.10.1.93" and item[1] == 1:
                    trade_timestamp.append(item[8])
            else:
                f.write(f'eth_type: {item[2]}, protocol: {item[0]}, length: {item[1]}\n')
    return tick_timestamp, trade_timestamp


def cal_delay(tick_timestamp, trade_timestamp):
    delay = []
    i = 0
    while i < len(tick_timestamp):
        delays = trade_timestamp[i] - tick_timestamp[i]
        if delays > 5000000:
            tick_timestamp.pop(i)
            continue
        delay.append(delays)
        i += 1
    return delay


def delay_statistic(nums,log_file):
    sort_data = sorted(nums)
    data_len = len(sort_data)
    print ('{:24}:'.format('total calculate count :'),'{:>12}'.format(data_len))
    print ('*' * 50)
    # range data calculate
    # print ('except highest lowest range data calculate:')
    log_file.write('*' * 50 + '\n')
    log_file.write('except highest lowest range data calculate:' + '\n')
    pmax_delay = [100,95,90]
    for calculate_len in pmax_delay:
        delay_dict = {}  # type:
        negative_t = float(0)
        # range check,100 ~ 51%;
        if 100 >= calculate_len >= 51:
            first_ = int(data_len * (1 - calculate_len/float(100))/2)
            last_ = int(data_len * (1 - (1 - calculate_len / float(100))/2))
            cut_data = sort_data[first_: last_]
            cut_data_len = len(cut_data)
            if float(cut_data_len) / 2 != cut_data_len / 2:
                delay_dict['medin_delay'] = cut_data[(cut_data_len // 2 + 1)]
            else:
                delay_dict['medin_delay'] = float(cut_data[cut_data_len // 2] + cut_data[(cut_data_len // 2 - 1)]) / 2
            delay_dict['max_delay'] = cut_data[-1]
            delay_dict['min_delay'] = cut_data[0]
            delay_dict['avg_delay'] = sum(cut_data) / cut_data_len
            for i in cut_data:
                if i < 0:
                    negative_t += 1
                else:
                    break
            delay_dict['file_1_fast_proportion'] = str(round((negative_t / cut_data_len) * 100, 2)) + ' %'
            pmax = ('[ calculate range: {calculate_len:3} % ] [ file1 fast proportion: {file_1_fast_proportion:8} ] [ avg_delay: {avg_delay:10} ns ] [ medin_delay:{medin_delay:10} ns ] [ max_delay: {max_delay:10} ns ] [ min_delay: {min_delay:10} ns ]').format(calculate_len=calculate_len,file_1_fast_proportion=delay_dict['file_1_fast_proportion'],avg_delay=delay_dict['avg_delay'],medin_delay=delay_dict['medin_delay'],max_delay=delay_dict['max_delay'],min_delay=delay_dict['min_delay'])
            log_file.write(pmax + '\n')
            print (pmax)
        else:
            print ('range error!')
            sys.exit()

    # Delay distribution and dynamic average delay
    log_file.write('*' * 50 + '\n')
    log_file.write('Delay distribution and dynamic average delay:' + '\n')
    p = 0
    while p != 100:
        arg1 = float(p)
        arg2 = float(p + 1)
        arg5 = int(data_len * (arg1 / 100))
        arg6 = int(data_len * (arg2 / 100))
        arg3 = sort_data[arg5]
        try:
            arg4 = sort_data[arg6]
        except IndexError:
            arg6 = data_len
            arg4 = sort_data[arg6 - 1]
        if arg6 != 0:
            arg7 = sum(sort_data) / arg6
        else:
            arg7 = 0  # 或者你可以设置一个特定的值
        d = ('[{arg1:5}%,{arg2:5}%] = [{arg3:10} ns, {arg4:10} ns] = [ no.{arg5:10}, no.{arg6:10}]   [ dynamicAverage [0.00%,  {arg2:5}%] = {arg7:10} ns ]').format(arg1=arg1, arg2=arg2, arg3=arg3, arg4=arg4, arg5=arg5, arg6=arg6, arg7=arg7)
        log_file.write(d + '\n')
        # print '[{arg1:5}%,{arg2:5}%] = [{arg3:10} ns, {arg4:10} ns] = [ no.{arg5:10}, no.{arg6:10}]   [ dynamicAverage [0.00%,  {arg2:5}%] = {arg7:10} ns ]'.format(arg1=arg1, arg2=arg2, arg3=arg3, arg4=arg4, arg5=arg5, arg6=arg6, arg7=arg7)
        p += 1


if __name__ == '__main__':
    # 解析pcap文件并写入到文件
    if platform.system() == 'Windows':
        data = parse_pcap(r'C:\Users\DELL\Desktop\test (2).pcap')
        tick_timestamp, trade_timestamp = write_to_file('u50le_metawatch_timestamp.txt', data)  # 在write_to_file里获取时间戳
        delay = cal_delay(tick_timestamp, trade_timestamp)
        print("delay:", delay)
        delay_statistic(delay, open('delay_statistic.txt', 'w'))
    else:
        if len(sys.argv) < 2:
            print('Need 1 parameter: ./demo.py pcap_file')
            sys.exit()
        data = parse_pcap(sys.argv[1])
        tick_timestamp, trade_timestamp = write_to_file('u50le_metawatch_timestamp.txt', data)
        delay = cal_delay(tick_timestamp, trade_timestamp)
        print("delay:", delay)
        delay_statistic(delay, open('delay_statistic.txt', 'w'))
