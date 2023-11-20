#!/usr/bin/python
import socket
import struct
from time import *


HeartBeat = [0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
LoginRespond = [
0x01,0x12,0xD0,0x00,0x01,0x00,0x00,0x00,0x01,0x00,0x55,0x00,0x00,0x00,0x00,0x00,
0xD5,0xFD,0xC8,0xB7,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x03,0x00,0x73,0x00,0x32,0x30,0x31,0x32,0x30,0x31,0x31,0x32,0x00,0x32,0x31,
0x3A,0x30,0x30,0x3A,0x31,0x35,0x00,0x30,0x30,0x37,0x30,0x63,0x32,0x63,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x30,0x30,0x37,0x30,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x53,0x48,0x46,0x45,0x20,0x4D,0x61,0x72,0x6B,0x65,0x74,0x20,0x44,0x61,
0x74,0x61,0x20,0x50,0x6C,0x61,0x74,0x66,0x6F,0x72,0x6D,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x32,
0x30,0x31,0x32,0x30,0x31,0x31,0x31,0x00
]
LogoutRespond = [
0x01,0x14,0x78,0x00,0x04,0x00,0x00,0x00,0x01,0x00,0x55,0x00,0x00,0x00,0x00,0x00,
0xD5,0xFD,0xC8,0xB7,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x05,0x00,0x1B,0x00,0x30,0x30,0x37,0x30,0x63,0x32,0x63,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x30,0x30,0x37,0x30,0x00,0x00,0x00,0x00,0x00,0x00,0x00
]


def heartBeat(conn):

    data = struct.pack("%dB" % (len(HeartBeat)), *HeartBeat)
    conn.sendall(data)
    print('Had Sent the HeartBeat')
    return


def process(tcpCliSock, addr, receive_data):

    print('')
    print('^' *50 )
    print('Start to check the received message:')
    print("The listening is : %s:%d" % (addr[0], addr[1]))
    print('^' * 50)
    print('The received message')
    print(receive_data)
    print('^' * 50)
    print('The TypeID:')
    TypeID = receive_data[2:4]
    print(TypeID)
    print('^' * 50)
    if TypeID == '00':
        print('')
        print('GOOD!!! Receive the HeartBeat from Client')

    elif TypeID == '11':
        print('')
        print('Receive the LoginRequest from Client')
        print('Send the LoginRespond to Client')
        data = struct.pack("%dB" % (len(LoginRespond)), *LoginRespond)
        tcpCliSock.sendall(data)

    elif TypeID == '13':
        print('')
        print('Receive the LogoutRequest from Client')
        print('Send the LogoutRespond to Client')
        data = struct.pack("%dB" % (len(LogoutRespond)), *LogoutRespond)
        tcpCliSock.sendall(data)
        print('LogoutRespond Done, Close the connection between Server and Client')
        main_process.append('LogoutRespond')

    elif TypeID == '31':
        print('')
        print('Receive the SnapshotInquire from Client')
        print('Receive the SnapshotInquire from Client')
        print('Receive the SnapshotInquire from Client')
        SnapeID = receive_data[28:36]
        print(SnapeID)
        if SnapeID.upper() != 'FFFFFFFF':
            print('FAIL!!!!!!!!!!!!!')
            print('The current SnapshotInquire is not the latest SnapNum')
            main_process.append('SnapNumError')
            return False
        Topic_ID = receive_data[24:28]
        print('The TopicID is %s' % Topic_ID)
        if Topic_ID.upper() == 'E803':
            print('Receive the Topic-1000')
            print('Send the Topic-1000')
            tcpCliSock.sendall(topic_option['1000'])
            print('Topic-1000 done')
        elif Topic_ID.upper() == 'E903':
            print('Receive the Topic-1001')
            print('Send the Topic-1001')
            tcpCliSock.sendall(topic_option['1001'])
            print('Topic-1001 done')
        elif Topic_ID.upper() == '8813':
            print('Receive the Topic-5000')
            print('Send the Topic-5000')
            tcpCliSock.sendall(topic_option['5000'])
            print('Topic-5000 done')
        elif Topic_ID.upper() == '8913':
            print('Receive the Topic-5001')
            print('Send the Topic-5001')
            tcpCliSock.sendall(topic_option['5001'])
            print('Topic-5001 done')
        else:
            print('FAIL, The TopicID is wrong')
            main_process.append('TopicIDError')
    else:
        print('')
        print('FAIL')
        print('The Client send some strange message to Server!!!!!!! and still No HeartBeat')


def run():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # 允许端口复用
    server.bind(("20.20.1.76", 9999))   # 绑定 IP 端口，是否考虑OS直接获取本地IP
    server.listen(5)
    print('#' * 50)
    print('Sleep 5s for waiting the Client to connect')
    print('#' * 50)
    sleep(5)
    conn, addr = server.accept()

    first_time = mktime(localtime())
    while True:
        print('Waiting the Client Request...')
        try:
            receive_data1 = conn.recv(1300)     # 客户端返回数据
            receive_data = receive_data1.encode('hex')
            process(conn, addr, receive_data)
            print('Complete the Checking and Sending')
            first_time = mktime(localtime())
            conn.settimeout(0.5)
        except Exception as e: # The Timer and HeartBeat Eject
            second_time = mktime(localtime())
            print('!' * 50)
            print('No data received from Client')
            print('Start to record the time, will abort the Test when the time over 10s')
            print('Dump the Errors if has:')
            print(e)
            wait_time = int(second_time - first_time)
            print(wait_time)
            print('!' * 50)
            sleep(1)
            if 5 < wait_time < 10:
                print('Long Time No Information interaction, Send the HeartBeat')
                heartBeat(conn)
            if wait_time > 10:
                print('FAIL')
                print("Don't receive ANY data from Client in 10s")
                break
        if main_process:
            server.close()
            if main_process[0] == 'LogoutRespond':
                print('')
                print('Close the connection between Server and Client Since the LogoutRespond Done')
            elif main_process[0] == 'SnapshotInquire':
                print('')
                print('Close the connection between Server and Client Since receive the SnapshotInquire')
            elif main_process[0] == 'SnapNumError':
                print('')
                print('SnapNumError')
            elif main_process[0] == 'TopicIDError':
                print('')
                print('TopicIDError')
            else:
                print('')
                print('Receive some strange message, break the cycle')
            break
        print('finish 1 loop')
        print('*'*100)


def initial_system():   # 读文件

    file_content = {}
    path1 = '/home/HQM-SF/Debug/tcp_future_server/caspwang_server/topic-1000-snapshot.bin'
    path2 = '/home/HQM-SF/Debug/tcp_future_server/caspwang_server/topic-1001-snapshot.bin'
    path3 = '/home/HQM-SF/Debug/tcp_future_server/caspwang_server/topic-5000-snapshot.bin'
    path4 = '/home/HQM-SF/Debug/tcp_future_server/caspwang_server/topic-5001-snapshot.bin'
    print('Start to read the Bin File')

    print('Read the 1000 topic')
    file1000 = open(path1, 'rb')
    content1 = file1000.read()
    file1000.close()
    file_content['1000'] = content1
    print('Read 1000 done')

    print('Read the 1001 topic')
    file1001 = open(path2, 'rb')
    content2 = file1001.read()
    file1001.close()
    file_content['1001'] = content2
    print('Read 1001 done')

    print('Read the 5000 topic')
    file5000 = open(path3, 'rb')
    content3 = file5000.read()
    file5000.close()
    file_content['5000'] = content3
    print('Read 5000 done')

    print('Read the 5001 topic')
    file5001 = open(path4, 'rb')
    content4 = file5001.read()
    file5001.close()
    file_content['5001'] = content4
    print('Read 5001 done')

    return file_content


if __name__ == "__main__":
    main_process = []
    topic_option = initial_system()
    run()