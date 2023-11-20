import random
import time

t = 0
print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
while True:
    box1 = []
    box2 = []
    bifen = []
    sf = []
    i = 0
    j = 0
    k = 0
    while i < 4:
        box1.append(random.randrange(0,4))
        box2.append(random.randrange(0,4))
        i += 1
        t += 1
    if box1 == box2:
        while j < 2:
            bifen.append(random.randrange(0, 7))
            j += 1
        tmp = [box1[0]+box1[1],box1[2]+box1[3]]
        tmp_sf = []
        for d in [0,2]:
            if box1[d] > box1[d+1]:
                tmp_sf.append(0)
            elif box1[d] == box1[d+1]:
                tmp_sf.append(1)
            else:
                tmp_sf.append(2)
        # print('进球 ：',box1)
        # print('比分 ：',bifen)
        # print('猜分 ：',tmp)
        if tmp == bifen:
            while k < 2:
                sf.append(random.randrange(0, 3))
                k += 1
            # print('333333333333333333333')
            # print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            # print('333333333333333333333')
            # print(box1)
            # print(tmp)
            # print(tmp_sf)
            # print(sf)
            # print(t)
            if tmp_sf == sf:
                print('！！！！！！！！！！！！！！！！！！！！！！！！！')
                print('进球：',bifen)
                print('比分：',box1)
                print('！！！！！！！！！！！！！！！！！！！！！！！！！')
                print(t)
                break
    # time.sleep(1)
print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))