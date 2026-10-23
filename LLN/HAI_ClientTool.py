#!/usr/bin/python
#coding=utf-8
import socket
import time
from threading import Thread
import signal
import sys
from datetime import datetime
import random
import hashlib
import os
import logging
import subprocess
import itertools
import string


class Logger:
    def __init__(self, name='hai_logger', level=logging.DEBUG, log_dir='haisocketclientlog'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        date_str = datetime.now().strftime('%Y-%m-%d')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, 'hai_socket_client_log_{}.log'.format(date_str))
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        formatter = logging.Formatter('[%(levelname)5s][%(asctime)s][%(pathname)s:  %(lineno)d][%(process)d] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    def get_logger(self):
        return self.logger
    
logger = Logger().get_logger()


class HaiClient():
    def __init__(self, IP, port, local_IP='',local_port=0,file_name = 'HAI_ClientTool_Default_File.bin'):
        self.local_IP = local_IP
        self.local_port = local_port
        self.IP = IP
        self.port = port
        self.file_name = file_name
        self.socket_name = 'unknown'
        self.stop_thread = False

    def connect(self):
        self.send_md5 = hashlib.md5()  # 初始化MD5计算器
        self.send_len = 0
        self.recv_md5 = hashlib.md5()  # 初始化MD5计算器
        self.recv_len = 0
        while True:
            try:
                self.s = socket.socket()
                # 阻塞模式
                self.s.setblocking(True)
                # 非阻塞模式
                # self.s.setblocking(False)
                self.s.bind((self.local_IP, self.local_port,))
                self.s.connect((self.IP, self.port,))
                self.socket_name = self.s.getsockname()
            except Exception as message:
                logger.info('connect error: %s' % message)
                time.sleep(5)
                continue
            else:
                logger.info('connect success. local addr: %s', self.socket_name)
                logger.info('connect success. remote addr: %s', self.s.getpeername())
                self.s.settimeout(None)
                break

    def connect_close(self):
        try:
            self.s.close()
            logger.info('close socket')
        except Exception as message:
            logger.info('close error: %s' % message)
        try:
            self.send_file.close()
            logger.info('close file')
        except Exception as message:
            logger.info('close error: %s' % message)
        try:
            self.save_file.close()
            logger.info('close file')
        except Exception as message:
            logger.info('close error: %s' % message)

    def data_send(self,rand=[1460],time_interval=0):
        # 搞个判断，如果文件名为F_10000，则生成一份10000个F的数据
        self.send_file = open(self.file_name, 'rb')
        start_time = time.time()  # 记录开始时间
        try:
            while True:
                file_len = random.choice(rand)
                data = self.send_file.read(file_len)
                time.sleep(float(time_interval))
                if not data:
                    # self.s.sendall(b'')
                    self.send_file.close()
                    break
                self.s.sendall(data)
                self.send_md5.update(data)  # 更新MD5值
                self.send_len += len(data)
                # print('send_len:', self.send_len)
            end_time = time.time()  # 记录结束时间
            send_rate = self.send_len / (end_time - start_time) /1048000  # 计算发送速率
            logger.info('send done')
            logger.info('%s send MD5: %s', self.socket_name, self.send_md5.hexdigest())  # 打印本地IP端口和MD5值
            logger.info('%s Total send data length: %s %.2f MB/sec', self.socket_name, self.send_len, send_rate)
        except Exception as e:
            logger.info('Error sending data: %s' % e)
            end_time = time.time()  # 记录结束时间
            send_rate = self.send_len / (end_time - start_time) /1048000  # 计算发送速率
            logger.info('send done')
            logger.info('%s send MD5: %s', self.socket_name, self.send_md5.hexdigest())  # 打印本地IP端口和MD5值
            logger.info('%s Total send data length: %s %.2f MB/sec', self.socket_name, self.send_len, send_rate)

    def thread_send(self,rand, time_interval=0):
        t_send = Thread(target=self.data_send,args=(rand,time_interval))
        t_send.setDaemon(True)
        t_send.start()
        return

    def recv_msg(self,print_flag=False):
        self.save_file_name = "recv_{}_{}".format(self.file_name, datetime.now().strftime('%Y%m%d%H%M%S'))
        self.save_file = open(self.save_file_name, 'wb')
        if print_flag:
            pass
        else:
            self.s.settimeout(10)
        start_time = time.time()  # 记录开始时间
        while not self.stop_thread:
            try:
                data = self.s.recv(4096)
                self.recv_md5.update(data)  # 更新MD5值
                if print_flag:
                    logger.info('recv_data: %s' % data)
                if not data:
                    end_time = time.time()  # 记录结束时间
                    recv_rate = self.recv_len / (end_time - start_time) /1048000 # 计算接收速率
                    logger.info('No data received, closing file and connection.')
                    logger.info('%s recv MD5: %s', self.socket_name, self.recv_md5.hexdigest())
                    logger.info('%s Total recv data length: %s %.2f MB/sec', self.socket_name, self.recv_len, recv_rate)
                    self.compare_result()
                    sys.exit()
                self.recv_len += len(data)
                # print('recv_len:', self.recv_len)
                self.save_file.write(data)
            except socket.timeout:
                logger.info('No data received for 10 seconds, closing file and connection.')
                end_time = time.time()  # 记录结束时间
                recv_rate = self.recv_len / (end_time - start_time - 10) /1048000 # 计算接收速率
                logger.info('%s recv MD5: %s', self.socket_name, self.recv_md5.hexdigest())  # 打印本地IP端口和MD5值
                logger.info('%s Total recv data length: %s %.2f MB/sec', self.socket_name, self.recv_len, recv_rate)
                self.compare_result()
                self.save_file.close()
            #    self.s.close()
                break
            except Exception as e:
                logger.info(e)
                break
                sys.exit()

    def thread_recv(self, print_flag=False):
        t_recv = Thread(target=self.recv_msg, args=(print_flag,))
        t_recv.setDaemon(True)
        t_recv.start()
        return

    def compare_result(self):
        md5_result_flag = False
        data_len_result_flag = False
        try:
            if self.send_md5.hexdigest() == self.recv_md5.hexdigest():
                logger.info('%s MD5 check pass', self.socket_name)
                md5_result_flag = True
                os.remove(self.save_file_name)  # 删除文件
            else:
                logger.info('%s MD5 check fail', self.socket_name)
    #            sys.exit()
            if self.send_len == self.recv_len:
                logger.info('%s Data length check pass', self.socket_name)
                data_len_result_flag = True
            else:
                logger.info('%s Data length check fail', self.socket_name)
     #           sys.exit()
        except Exception as e:
            logger.info('Exception: %s', e)
        return md5_result_flag, data_len_result_flag

    # def func_connect_ex(self):
    #     logger.info('connect_ex')
    #     self.s = socket.fromfd(3, socket.AF_INET, socket.SOCK_STREAM)
    #     self.s = socket.create_connection((self.IP, self.port), timeout=5)
    #     self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     self.s.connect_ex((self.IP, self.port))
    #     logger.info('connect success. local addr: %s', self.socket_name)
    #     logger.info('connect success. remote addr: %s', self.s.getpeername())
    #
    #     logger.info('start sendall')
    #     self.s.sendall(b'hello')
    #     logger.info('sendall done')
    #     data = self.s.recv(1024)
    #     print('Received', repr(data))
    #     self.s.send(b'hello')
    #     buffer = bytearray(1024)
    #     nbytes = self.s.recv_into(buffer)
    #     # 打印接收到的字节数和数据
    #     print('Received', nbytes, 'bytes:', buffer[:nbytes])
    #     self.s.close()

    # def func_connect_(self):
    #     self.s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
    #     logger.info('connect success. local addr: %s', self.socket_name)
    #     logger.info('connect success. remote addr: %s', self.s.getpeername())
    #     self.s.send(b'hello')
    #     buffer = bytearray(1024)
    #     nbytes = self.s.recv_into(buffer)
    #     # 打印接收到的字节数和数据
    #     print('Received', nbytes, 'bytes:', buffer[:nbytes])
    #     self.s.close()

# def start_client():
#     pass

def csv_test(csv_file):
    print(csv_file)
    # 按这个格式读取csv文件
    # mode, IP, port, file_name, func_id, rand, time_interval, retry_flag
    test_case = []
    with open(csv_file, 'r') as f:
        for line in f:
            test_case.append(line.split(','))
    for case in test_case:
        print(case)
        if case[4] == '1':
            hai_client = HaiClient(case[1], int(case[2]), case[3])
            hai_client.connect()
            hai_client.thread_recv(True)
            hai_client.thread_send(rand=[int(case[5])], time_interval=float(case[6]))
            hai_client.recv_msg()
            hai_client.s.close()
        elif case[4] == '2':
            hai_client = HaiClient(case[1], int(case[2]), case[3])
            hai_client.connect()
            hai_client.s.close()
            time.sleep(float(case[6]))
        elif case[4] == '3':
            hai_client = HaiClient(case[1], int(case[2]), case[3])
            hai_client.connect()
            hai_client.data_send(rand=[int(case[5])], time_interval=float(case[6]))
            hai_client.s.close()
        elif case[4] == '4':
            hai_client = HaiClient(case[1], int(case[2]), case[3])
            hai_client.connect()
            hai_client.thread_send(rand=[int(case[5]),])
            while True:
                time.sleep(float(case[6]))
                hai_client.s.recv(65536)
                continue
            hai_client.s.close()
        else:
            break
    pass


def quit(signum, frame):
    logger.info("\nCLIENT DISCONNECT.")
    sys.exit()


notice = '''
不输入参数为手动连接，其他模式及其参数：
1.指定包长、间隔、发送文件，发包间隔为0则为最大速率,发包长度为N则遍历[1,64,128,256,1024,1459,1460,1461,1500, 2000]:  
./HAI_ClientTool.py  1  sever_IP  sever_port local_IP local_port(可以和local_IP同时为空) 发送文件名  发包长度[Bytes](N)  发包间隔[s]  循环次数  
2.重复连接:  
./HAI_ClientTool.py  2  sever_IP  sever_port local_IP  local_port(可以和local_IP同时为空) N         N                 重连间隔[s] 循环次数 
3.只发不收-指定包长、间隔、发送文件，发包间隔为0则为最大速率,用于测试TCP Window Full场景:
./HAI_ClientTool.py  3  sever_IP  sever_port local_IP  local_port(可以和local_IP同时为空) 发送文件名  发包长度[Bytes](N)  发包间隔[s]  循环次数 
4.全速发送指定包长、间隔、发送文件后，等待【接收间隔[s]】时长后再接收65536Bytes数据包，用于测试TCP Window Full重复恢复场景:
./HAI_ClientTool.py  4  sever_IP  sever_port local_IP  local_port(可以和local_IP同时为空) 发送文件名  发包长度[Bytes](N)  接收间隔[s]  循环次数 
5.发送csv格式用例 
./HAI_ClientTool.py TEST_FILE.csv
 '''


if __name__ == '__main__':
    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)
    if len(sys.argv) == 1:
        logger.info(notice)
        logger.info('不输入参数则为手工模式.')
        local_IP = str(raw_input('local IP：'))
        local_port = int(raw_input('local port：'))
        IP = str(raw_input('server IP：'))
        port = int(raw_input('server port：'))
        hai_client = HaiClient(IP, port, local_IP, local_port)
        hai_client.connect()
        hai_client.thread_recv(True)
        while True:
            try:
                hai_client.s.sendall(raw_input('send data:'))
            except Exception as e:
                logger.info(e)
                continue
            time.sleep(0.1)
    elif len(sys.argv) == 2:
        # 做成读CSV的形式，每行一个用例，执行后记录结果
        csv_test(sys.argv[1])
        test_result = [False, False]
        if test_result[0] and test_result[1]:
            # 生成报告
            print('tt')
        else:
            print('ff')
        sys.exit()
    elif len(sys.argv) != 8 and len(sys.argv) != 10:
        logger.info('参数错误')
        logger.info(notice)
        sys.exit()
    func_id = sys.argv[1]
    IP = sys.argv[2]
    port = int(sys.argv[3])
    if sys.argv[4] == 'N':
        file_name = 'HAI_ClientTool_Default_File.bin' + datetime.now().strftime('%Y%m%d%H%M%S')
    else:
        file_name = sys.argv[4]
        if file_name.startswith('F_'):
            #先判断文件在不在，不在就生成
            if not os.path.exists(file_name):
                len_f = int(file_name.split('_')[1])
                logger.info('Generate file with F * %s', len_f)
                with open(file_name, 'w') as f:
                    count = 0
                    for _ in itertools.islice(itertools.repeat(None), len_f):
                        f.write('F')
                        count += 1
                        if count % 1024 == 0:
                            f.write('\n')
            else:
                logger.info('File already exists.')
        elif file_name.startswith('R_'):
            #先判断文件在不在，不在就生成
            if not os.path.exists(file_name):
                len_f = int(file_name.split('_')[1])
                logger.info('Generate file with Random str * %s', len_f)
                with open(file_name, 'w') as f:
                    # 生成一个由 0-9 和 a-Z 组成的随机字符串
                    chars = string.ascii_letters + string.digits
                    count = 0
                    for _ in itertools.islice(itertools.repeat(None), len_f):
                        f.write(random.choice(chars))
                        count += 1
                        if count % 1024 == 0:
                            f.write('\n')
                f.close()
            else:
                logger.info('File already exists.')
    # logger.info(sys.argv[5])
    if sys.argv[5] == 'N':
        rand = [1, 40, 48, 159, 687, 996, 1007, 1460, 1459, 1461, 1500, 2000]
    elif sys.argv[5] == 'R':
        rand = list(range(1, 2001))
    else:
        rand = [int(sys.argv[5])]
    time_interval = float(sys.argv[6])
    retry_flag = int(sys.argv[7])
    try:
        while retry_flag > 0:
            logger.info('第%s次测试开始' % (int(sys.argv[7]) - retry_flag + 1))
            hai_client = HaiClient(IP, port, file_name=file_name)
            if func_id == '1':
                # logger.info('清寄存器：cd /home/lbs/HAI-MF-SS_v1.0.0_S1_B04/soft && ./fpgatool --writeReg  0x20500 1')
                # os.chdir('/home/lbs/HAI-MF-SS_v1.0.0_S1_B04/soft')
                # subprocess.call(["./fpgatool", "--writeReg", "0x20500", "1"])
                # os.chdir('/home/lbs')
                logger.info('启动socket连接')
                hai_client.connect()
                logger.info('启动数据发送线程')
                hai_client.thread_send(rand=rand, time_interval=time_interval,)
                logger.info('启动数据接收线程')
                hai_client.recv_msg()
                logger.info('关闭socket连接')
                hai_client.s.close()
                logger.info('循环次数-1')
                retry_flag -= 1
                logger.info('等待0.5s')
                time.sleep(0.5)
            elif func_id == '2':
                hai_client.connect()
                #hai_client.s.sendall(b'')
                hai_client.thread_recv()
                time.sleep(0.01)
                logger.info('close socket. local addr:{}'.format(hai_client.s.getsockname()))
                hai_client.stop_thread = True
                hai_client.s.close()
                time.sleep(time_interval)
                retry_flag -= 1
            elif func_id == '3':
                hai_client.connect()
                hai_client.data_send(rand=rand, time_interval=time_interval,)
                # hai_client.recv_msg()
                hai_client.s.close()
                retry_flag -= 1
                time.sleep(0.5)
            elif func_id == '4':
                hai_client.connect()
                hai_client.thread_send(rand=rand,)
                while True:
                    time.sleep(time_interval)
                    hai_client.s.recv(65536)
                    continue
                # hai_client.recv_msg()
                hai_client.s.close()
                retry_flag -= 1
                time.sleep(0.5)
            else:
                logger.info('参数错误')
                logger.info(notice)
                sys.exit()
    except Exception as exc:
        logger.info(exc)


