import csv
import time
import re

U50_74 = []
U50_102 = []


def timestamp(hms):
    head = "03 21 2021 "
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
                if int(k[7]) == 42:     # 过Cisco交换机前
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    U50_74.append(val + k[6].split('.')[1].split(' ')[0])
                elif int(k[7]) == 43:   # 过Cisco交换机后
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    U50_102.append(val + k[6].split('.')[1].split(' ')[0])
                else:
                    pass
            except StopIteration:
                break


def data_calculator(file):
    read_mw(file)
    count = 0
    all_delay = []
    total_delay = 0
    delay_log = open(file + '.csv', 'w')
    print('start compare')
    i = 0
    j = 0
    # for i in range(min(len(U50_74),len(U50_102))):
    #     delay = int(U50_74[i]) - int(U50_102[i])
    #     all_delay.append(delay)
    #     delay_log.write(str(U50_74[i]) + ',' + str(U50_102[i]) + ',' + str(delay) + '\n')
    #     total_delay += delay
    #     count += 1
    while i < min(len(U50_74),len(U50_102)):
        try:
            delay = int(U50_74[i]) - int(U50_102[j])
            if delay > 500:
                j += 1
            elif delay < -500:
                i += 1
            else:
                all_delay.append(delay)
                delay_log.write(str(U50_74[i]) + ',' + str(U50_102[j]) + ',' + str(delay) + '\n')
                total_delay += delay
                i += 1
                j += 1
                count += 1
        except IndexError:
            print('read data done')
            break
    print('avg delay :', int(total_delay / count))
    print('median : ', find(all_delay))
    print('max delay : ', max(all_delay))
    print('min delay : ', min(all_delay))
    print('all calculate packet:', count)
    delay_log.write('avg delay :' + str(total_delay / count) + '\n')
    delay_log.write('max delay : ' + str(max(all_delay)) + '\n')
    delay_log.write('min delay : ' + str(min(all_delay)) + '\n')
    delay_log.write('median : ' + str(find(all_delay)) + '\n')
    delay_log.write('all calculate packet:' + str(count) + '\n')


if __name__ == '__main__':
    file = r'D:\CiscoA-B_ping_01.csv'
    # file = r'D:\CiscoA-B_ping_01.csv'
    # file = r'D:\CiscoA-B_ping_01.csv'
    data_calculator(file)
