import csv

input_timestamp = []
output_timestamp = []
delay_time = []
all_delay_time = 0
count = 0
file_in = r'D:\延时测试\U50_50.csv'
file_out = r'D:\延时测试\U50_102.csv'

with open(file_in, 'r') as config:
    reader = csv.reader(config)
    next(reader)
    while True:
        try:
            k = next(reader)
            input_timestamp.append(k[1])
        except StopIteration:
            break

with open(file_out, 'r') as config:
    reader = csv.reader(config)
    next(reader)
    while True:
        try:
            k = next(reader)
            output_timestamp.append(k[1])
        except StopIteration:
            break

i = 0
dif_ns = 0
dif_s = 0
delin = 0
delout = 0
while i < len(output_timestamp):
    # print(float(output_timestamp[i]), float(input_timestamp[i]))
    x_out = output_timestamp[i].split('.', 1)
    x_in = input_timestamp[i].split('.', 1)
    dif_s = int(x_out[0]) - int(x_in[0])
    if dif_s == 0:
        dif_ns = int(x_out[1]) - int(x_in[1])
        if dif_ns > 100000:
            del input_timestamp[i]
            i -= 1
            count -= 1
            delin += 1
        elif dif_ns < 0:
            del output_timestamp[i]
            i -= 1
            count -= 1
            delout += 1
        else:
            all_delay_time += dif_ns
            delay_time.append(dif_ns)
    elif dif_s > 0:
        del input_timestamp[i]
        i -= 1
        count -= 1
        delin += 1
    else:
        del output_timestamp[i]
        i -= 1
        count -= 1
        delout += 1
    i += 1
    count += 1

with open('delay.txt', 'w') as config:
    for i in range(len(delay_time)):
        config.write(str(delay_time[i])+'\n')
    config.write('\nmax delay time : '+str(max(delay_time)))
    config.write('\nmin delay time : '+str(min(delay_time)))
    config.write('\ndelin times : '+str(delin))
    config.write('\ndelout times : '+str(delout))
    config.write('\nall nums : '+str(count))
    config.write('\navg delay time : '+str(all_delay_time/count))
    config.close()

print('max delay time : ', max(delay_time))
print('min delay time : ', min(delay_time))
print('delin times:', delin)
print('delout times:', delout)
print('all nums :', count)
print('avg delay time :', all_delay_time/count)
