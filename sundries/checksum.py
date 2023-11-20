packet = ['45', '00', '00', '3C', '8C', 'AF', '40', '00', '40', '06',
          '00', '00',  # 校验位
          'C0', 'A8', 'C9', '83',  # 源IP
          'C0', 'A8', 'C9', '81',  # 目的IP
          ]


def DataCheck(Info):
    Data = Info.split(" ")
    sum = 0
    for i in Data:
        sum = int('0x' + i, 16) + sum
    check = 0xffff - ((0x0000ffff & sum) + (sum >> 16))
    return check


if __name__ == '__main__':
    IPH = ''
    for i in range(0, 20):
        if i % 2 == 0 or i == 19:
            IPH = IPH + packet[i]
        else:
            IPH = IPH + packet[i] + ' '
    IPHcheck = DataCheck(IPH)
    IPHcheck = str(hex(IPHcheck))[2:]
    IPHcheck = IPHcheck.zfill(4)
    packet[10] = IPHcheck[0:2].upper()
    packet[11] = IPHcheck[2:4].upper()
    print(packet)



