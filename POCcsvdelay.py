#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys

fpga_in = 0
fpga_out = 0
total_soft_time = []
total_fpga_time = []
total_fpga_in_data = []
total_fpga_out_data = []
total_delay_time = []


def heap_adjust(parent, heap):  # 更新结点后进行调整
    child = 2 * parent + 1
    while len(heap) > child:
        if child + 1 < len(heap):
            if heap[child + 1] < heap[child]:
                child += 1
        if heap[parent] <= heap[child]:
            break
        heap[parent], heap[child] = heap[child], heap[parent]
        parent, child = child, child * 2 + 1


def find(nums):
    heapnum = len(nums) // 2
    heap = nums[:heapnum + 1]
    for i in range(len(heap) // 2 - 1, -1, -1):  # 前n/2个元素建堆
        heap_adjust(i, heap)
    for j in range(heapnum + 1, len(nums)):
        if nums[j] > heap[0]:
            heap[0] = nums[j]
            heap_adjust(0, heap)
    # 奇数时是最中间的数，偶数时是最中间两数的均值
    return heap[0] if len(nums) % 2 == 1 else float(heap[0] + min(heap[1], heap[2])) / 2


def read_file(fpga_in_file, fpga_out_file):
    print(fpga_in_file, ' Start to calculate.')
    with open(fpga_in_file, 'r') as fpga_in_data:
        while True:
            fpga_line = fpga_in_data.readline()
            if not fpga_line:
                break
            total_fpga_in_data.append(fpga_line.split(',')[1])
        fpga_in_data.close()
    with open(fpga_out_file, 'r') as fpga_out_data:
        while True:
            soft_line = fpga_out_data.readline()
            if not soft_line:
                break
            total_fpga_out_data.append(soft_line.split('|')[1])
        fpga_out_data.close()


def calculator(fpga_in_file, fpga_out_file): # fpgain = s5 ,fpgaout = poc
    read_file(fpga_in_file, fpga_out_file)
    i = 0
    j = 0
    count = 0
    all_delay = []
    total_delay = 0
    delay_log = open(fpga_out_file + '.csv', 'w')
    # delay_log.write('N_api_delay_data' + ',' + 'api_delay_data' + ',' + 'dif\n')
    all_data = open(fpga_out_file + 'delay.csv', 'a')
    print(len(total_fpga_in_data))
    print(len(total_fpga_out_data))
    print('start compare')
    # while i < 1000:
    while i < len(total_fpga_in_data):
        try:
            delay = int(total_fpga_out_data[i]) - int(total_fpga_in_data[i])
            if delay:
                all_delay.append(delay)
                total_delay += delay
                delay_log.write(str(total_fpga_in_data[i]) + ',' + str(total_fpga_out_data[i]) + ',' + str(delay) + '\n')
                count += 1
            i += 1
        except IndexError:
            break
    print('all calculate line:', count)
    print('max delay : ', max(all_delay))
    print('min delay : ', min(all_delay))
    print('avg delay :', int(total_delay / count))
    print('median : ', find(all_delay))
    all_data.write('all calculate line,' + 'max delay,' + 'min delay,' + 'avg delay,' + 'median\n')
    all_data.write(str(count) + ',' + str(max(all_delay)) + ',' + str(min(all_delay)) + ',' + str(int(total_delay / count)) + ',' + str(find(all_delay)))
    all_data.close()


if __name__ == '__main__':
    server_file = r'D:\延时测试\上海对比\Timestamp_recv_index.txt'
    clientdemo_file = r'D:\延时测试\上海对比\SSE_INDEX_BIN_0826'
    calculator(server_file, clientdemo_file)  # server = s5
