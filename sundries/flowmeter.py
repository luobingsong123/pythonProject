import csv
import re


def read_mw(file):
    timet = {}
    with open(file, 'r') as config:
        reader = csv.reader(config)
        next(reader)
        while True:
            try:
                k = next(reader)
                val = re.findall('\d{2}\:\d{2}\:\d{2}\.\d{3}', k[6])[0]
                try:
                    timet[val].append(int(k[5]) - 16)
                except KeyError:
                    timet[val] = [int(k[5]) - 16]
            except StopIteration:
                break
    return timet


if __name__ == '__main__':
    d = read_mw(r'D:\海通选优\option_loss_01.csv')
    log = open('flowmeter.csv','w')
    log.write('time,total_byte,total_packet\n')
    for i in d:
        total_byte = 0
        for j in d[i]:
            total_byte += j
        log.write(i + ',' + str(total_byte) + ',' + str(len(d[i])) + '\n')
    log.close()
