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


def delaycal(datas):
    lists = []
    with open(datas, 'r') as data:
        while True:
            dataline = data.readline()
            if not dataline:
                break
            lists.append(dataline.split('|')[1])
    return lists


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
            total_fpga_in_data.append(int(fpga_line))
        fpga_in_data.close()
    with open(fpga_out_file, 'r') as fpga_out_data:
        while True:
            soft_line = fpga_out_data.readline()
            if not soft_line:
                break
            total_fpga_out_data.append(soft_line.split('|')[1])
        fpga_out_data.close()


def calculator(fpga_in_file, fpga_out_file,rang):
    read_file(fpga_in_file, fpga_out_file)
    i = 0
    j = 0
    count = 0
    total_fpga_out_data_jg = []
    all_delay = []
    total_delay = 0
    delay_log = open(fpga_out_file + '.csv', 'w')
    # delay_log.write('N_api_delay_data' + ',' + 'api_delay_data' + ',' + 'dif\n')
    all_data = open(fpga_out_file + 'delay.csv', 'a')
    print(len(total_fpga_in_data))
    print(len(total_fpga_out_data))
    print('start compare')
    # while i < 1000:
    all_jg = 0
    count_jg = 0
    all_sb = 0
    count_sb = 0
    while i < len(total_fpga_in_data):
        try:
            delay = int(total_fpga_out_data[j]) - int(total_fpga_in_data[i])
            if delay > rang:
                i += 1
            elif delay <= 800:
                j += 1
            else:
                all_delay.append(delay)
                total_fpga_out_data_jg.append(int(total_fpga_out_data[j]))
                total_delay += delay
                if len(all_delay) > 1:
                    jg = total_fpga_out_data_jg[-1] - total_fpga_out_data_jg[-2]
                    if jg < 5000:
                        delay_log.write(str(total_fpga_out_data[j]) + ',' + str(int(total_fpga_in_data[i])) + ',' + str(delay) + ',' + str(jg) + '\n')
                        count += 1
                        all_jg += jg
                        count_jg += 1
                    else:
                        delay_log.write(
                            str(total_fpga_out_data[j]) + ',' + str(int(total_fpga_in_data[i])) + ',' + str(delay) + ',' + str(all_delay[-1]) + '\n')
                        all_sb += delay
                        count_sb += 1
                else:
                    delay_log.write(
                        str(total_fpga_out_data[j]) + ',' + str(int(total_fpga_in_data[i])) + ',' + str(delay) + ',' + str(all_delay[-1]) + '\n')
                    all_sb += delay
                    count_sb += 1
                # delay_log.write(str(total_fpga_in_data[i]) + ',' + str(total_fpga_out_data[i]) + ',' + str(delay) + '\n')
                    count += 1
                j += 1
        except IndexError:
            break
    print('fast packet delay:', int(all_sb / count_sb))
    print('interval:', int(all_jg / count_jg))
    print('avg delay :', int(total_delay / count))
    print('max delay : ', max(all_delay))
    print('min delay : ', min(all_delay))
    print('median : ', find(all_delay))
    print('all calculate line:', count)
    all_data.write('fast packet delay:,' + 'interval:,' + 'avg delay,' + 'max delay,' + 'min delay,' + 'median,' + 'total line\n')
    all_data.write(str(int(all_sb / count_sb)) + ',' + str(int(all_jg / count_jg)) + ',' + str(int(total_delay / count)) + ',' + str(max(all_delay)) + ',' + str(min(all_delay)) + ',' + str(find(all_delay)) + ',' + str(count))
    all_data.close()


if __name__ == '__main__':
    # 800~80000
    # server_file = r'D:\延时测试\上海旁路\端到端\sh_Timestamp_source_option.txt'
    # clientdemo_file = r'D:\延时测试\上海旁路\端到端\SSE_OPTION_BIN_0828'
    # rang = 80000
    # 800~20000
    # server_file = r'D:\延时测试\上海旁路\端到端\Timestamp_source_entrust.txt'
    # clientdemo_file = r'D:\延时测试\上海旁路\端到端\SSE_ENTRUST_BIN_0828'
    # rang = 20000
    # 800~60000
    # server_file = r'D:\延时测试\上海旁路\端到端\Timestamp_source_index.txt'
    # clientdemo_file = r'D:\延时测试\上海旁路\端到端\SSE_INDEX_BIN_0828'
    # rang = 60000
    # 800~40000
    server_file = r'D:\延时测试\上海旁路\端到端\Timestamp_source_level2.txt'
    clientdemo_file = r'D:\延时测试\上海旁路\端到端\SSE_LEVEL2_BIN_0828'
    rang = 40000
    calculator(server_file, clientdemo_file,rang)
