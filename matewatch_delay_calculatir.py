import csv
import time
import re

N_API_LENGTH = {'index': 86, 'level2': 231, 'entrust': 65, 'option': 143}
API_LENGTH = {'index': 122, 'level2': 387, 'entrust': 100, 'option': 271}
data_NAPI_INDEX = []
data_NAPI_LEVEL2 = []
data_NAPI_ENTRUST = []
data_NAPI_OPTION = []
data_API_INDEX = []
data_API_LEVEL2 = []
data_API_ENTRUST = []
data_API_OPTION = []


def timestamp(hms):
    head = "08 18 2021 "
    dt = head + hms
    timeArray = time.strptime(dt, "%m %d %Y %H:%M:%S")
    stamp = str(int(time.mktime(timeArray)))
    return stamp


def read_mw(file):
    with open(file, 'r') as config:
        reader = csv.reader(config)
        next(reader)
        while True:
            try:
                k = next(reader)
                if int(k[5]) == N_API_LENGTH['index']:
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    data_NAPI_INDEX.append(val + k[6].split('.')[1].split(' ')[0])
                elif int(k[5]) == N_API_LENGTH['level2']:
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    data_NAPI_LEVEL2.append(val + k[6].split('.')[1].split(' ')[0])
                elif int(k[5]) == N_API_LENGTH['entrust']:
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    data_NAPI_ENTRUST.append(val + k[6].split('.')[1].split(' ')[0])
                elif int(k[5]) == N_API_LENGTH['option']:
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    data_NAPI_OPTION.append(val + k[6].split('.')[1].split(' ')[0])
                elif int(k[5]) == API_LENGTH['index']:
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    data_API_INDEX.append(val + k[6].split('.')[1].split(' ')[0])
                elif int(k[5]) == API_LENGTH['level2']:
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    data_API_LEVEL2.append(val + k[6].split('.')[1].split(' ')[0])
                elif int(k[5]) == API_LENGTH['entrust']:
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    data_API_ENTRUST.append(val + k[6].split('.')[1].split(' ')[0])
                elif int(k[5]) == API_LENGTH['option']:
                    val = timestamp(re.findall('\d{2}\:\d{2}\:\d{2}', k[6])[0])
                    data_API_OPTION.append(val + k[6].split('.')[1].split(' ')[0])
            except StopIteration:
                break


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


def data_calculator(file):
    read_mw(file)
    print(len(data_NAPI_INDEX))
    print(len(data_NAPI_LEVEL2))
    print(len(data_NAPI_ENTRUST))
    print(len(data_NAPI_OPTION))
    N_API_DATA = {'index': data_NAPI_INDEX, 'level2': data_NAPI_LEVEL2, 'entrust': data_NAPI_ENTRUST,
                  'option': data_NAPI_OPTION}
    API_DATA = {'index': data_API_INDEX, 'level2': data_API_LEVEL2, 'entrust': data_API_ENTRUST,
                'option': data_API_OPTION}
    for i in ['index', 'level2', 'entrust', 'option']:
        try:
            print(i)
            delay_time = []
            all_delay_time = 0
            count = 0
            delay_log = open(i + '.csv', 'w')
            all_data = open('delay.csv', 'a')
            delay_log.write('N_api_delay_data' + ',' + 'api_delay_data' + ',' + 'dif\n')
            j = 0
            c1 = 0
            c2 = 0
            # for j in range(min(len(N_API_DATA[i]),len(API_DATA[i]))):
            # while j < 300000:
            while j < (min(len(N_API_DATA[i]), len(API_DATA[i]))):
                try:
                    delay = int(N_API_DATA[i][j + c1]) - int(API_DATA[i][j + c2])
                    if delay < -2000:
                        c1 += 1
                    elif delay > 100:
                        c2 += 1
                    else:
                        delay_time.append(delay)
                        all_delay_time += delay
                        count += 1
                        delay_log.write(str(N_API_DATA[i][j]) + ',' + str(API_DATA[i][j]) + ',' + str(delay) + '\n')
                        j += 1
                except IndexError:
                    break
            delay_log.write('\nall calculate line,' + str(count))
            delay_log.write('\nmax delay,' + str(max(delay_time)))
            delay_log.write('\nmin delay,' + str(min(delay_time)))
            delay_log.write('\navg delay,' + str(int(all_delay_time / count)))
            delay_log.write('\nmedian,' + str(find(delay_time)))
            delay_log.close()
            print('all calculate line:', count)
            print('max delay : ', max(delay_time))
            print('min delay : ', min(delay_time))
            print('avg delay :', int(all_delay_time / count))
            print('median : ', find(delay_time))
            all_data.write('DATE TYPE' + ',' + 'TOTAL LINE' + ',' + 'AVG DELAY' + ',' + 'MAX DELAY' + ',' + 'MIN DELAY' + ',' + 'MEDIAN' + '\n')
            all_data.write(i + ',' + str(count) + ',' + str(int(all_delay_time / count)) + ',' + str(max(delay_time)) + ',' + str(min(delay_time)) + ',' + str(find(delay_time)) + '\n')
            all_data.close()
        except ValueError:
            print(i, "on date!")
            continue


if __name__ == '__main__':
    file = r'D:\延时测试\穿透延时对比\多包x30.csv'
    data_calculator(file)
