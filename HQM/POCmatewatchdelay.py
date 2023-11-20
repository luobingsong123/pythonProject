import csv
import time
import re

fpag_in = []
fpag_out = []


def timestamp(hms):
    head = "08 24 2021 "
    dt = head + hms
    timeArray = time.strptime(dt, "%m %d %Y %H:%M:%S")
    stamp = str(int(time.mktime(timeArray)))
    return stamp


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


def read_mw(file):
    with open(file, 'r') as config:
        reader = csv.reader(config)
        next(reader)
        while True:
            try:
                k = next(reader)
                # print(k)
                if int(k[7]) == 34:     # AP55的数据
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    fpag_in.append(val + k[6].split('.')[1].split(' ')[0])
                elif int(k[7]) == 33:   # AP56的数据
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    fpag_out.append(val + k[6].split('.')[1].split(' ')[0])
                else:
                    pass
            except StopIteration:
                break


def data_calculator(file):
    read_mw(file)
    i = 0
    j = 0
    count = 0
    all_delay = []
    total_delay = 0
    delay_log = open(file + '.csv', 'w')
    all_data = open(file + 'delay.csv', 'a')
    print(len(fpag_in))
    print(len(fpag_out))
    print('start compare')
    all_jg = 0
    count_jg = 0
    all_sb = 0
    count_sb = 0
    while i < len(fpag_in):
        try:
            delay = int(fpag_out[j]) - int(fpag_in[i])
            if delay > 8354:
                i += 1
            elif delay <= 80:
                j += 1
            else:
                all_delay.append(delay)
                total_delay += delay
                if len(all_delay) > 1:
                    jg = all_delay[-1] - all_delay[-2]
                    if jg > 0:
                        delay_log.write(str(fpag_in[i]) + ',' + str(fpag_out[j]) + ',' + str(delay) + ',' + str(jg) + '\n')
                        count += 1
                        all_jg += jg
                        count_jg += 1
                    else:
                        delay_log.write(str(fpag_in[i]) + ',' + str(fpag_out[j]) + ',' + str(delay) + ',' + str(all_delay[-1]) + '\n')
                        all_sb += all_delay[-1]
                        count_sb += 1
                else:
                    delay_log.write(str(fpag_in[i]) + ',' + str(fpag_out[j]) + ',' + str(delay) + ',' + str(all_delay[-1]) + '\n')
                    all_sb += all_delay[-1]
                    count_sb += 1
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
    file = r'D:\广发证券FPGA行情POC方案\pcap\sz_MDDP_turnover.csv'
    data_calculator(file)
