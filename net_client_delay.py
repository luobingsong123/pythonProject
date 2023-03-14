import csv
import time
import re


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
    data = []
    with open(file, 'r') as config:
        reader = csv.reader(config)
        next(reader)
        while True:
            try:
                k = next(reader)
                val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                data.append(val + k[6].split('.')[1].split(' ')[0])
            except StopIteration:
                break
    return data


def timestamp(hms):
    head = "08 18 2021 "
    dt = head + hms
    timeArray = time.strptime(dt, "%m %d %Y %H:%M:%S")
    stamp = str(int(time.mktime(timeArray)))
    return stamp


def read_netc(file):
    data = []
    with open(file, 'r') as config:
        reader = csv.reader(config)
        next(reader)
        while True:
            try:
                k = next(reader)
                data.append(k[0])
            except StopIteration:
                break
    return data


if __name__ == '__main__':
    mw_50 = read_mw(r'D:\延时测试\客户端延时+\50_mw_delay.csv')
    client_50 = read_netc(r'D:\延时测试\客户端延时+\50_delay_data.csv')
    mw_102 = read_mw(r'D:\延时测试\客户端延时+\50_new_3_mw_delay.csv')
    client_102 = read_netc(r'D:\延时测试\客户端延时+\50_new_3_delay_data.csv')
    total_delay_50 = 0
    total_delay_102 = 0
    total_delay_50_102 = 0
    count = 0
    delay_50 = []
    delay_102 = []
    delay_50_102 = []
    log = open('50_client_delay.csv', 'w')
    log.write('client_50,mw_50,client_mw_50,new_2_client_50,new_2_mw_50,new_2_client_mw_50,new50_old50\n')
    for i in range((min(len(client_50), len(client_102)))):
        delay_50.append(int(client_50[i]) - int(mw_50[i]))
        delay_102.append(int(client_102[i]) - int(mw_102[i]))
        total_delay_50 += delay_50[i]
        total_delay_102 += delay_102[i]
        delay_50_102.append(delay_50[i] - delay_102[i])
        total_delay_50_102 += delay_50_102[i]
        log.write(client_50[i] + ',' + mw_50[i] + ',' + str(delay_50[i]) + ',' + client_102[i] + ',' + mw_102[i] + ',' + str(delay_102[i]) + ',' + str(delay_50_102[i]) + '\n')
        count += 1
    log.write('\nmax delay,'+str(max(delay_50_102)))
    log.write('\nmin delay,'+str(min(delay_50_102)))
    log.write('\nall calculator time,'+str(count))
    log.write('\navg delay,'+str(total_delay_50_102/count))
    log.write('\nmedian,'+str(find(delay_50_102)))
    log.close()
    print('max delay : ', max(delay_50_102))
    print('min delay : ', min(delay_50_102))
    print('all calculator time :', count)
    print('avg delay :', total_delay_50_102/count)
    print('median : ', find(delay_50_102))
