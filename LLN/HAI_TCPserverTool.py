#!/usr/bin/python
#coding=utf-8
import sys
import signal
import socket
import threading
from datetime import datetime
import os
import hashlib
import time
import logging


class Logger:
    def __init__(self, name='hai_logger', level=logging.DEBUG, log_dir='haisocketserverlog'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        date_str = datetime.now().strftime('%Y-%m-%d')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, 'hai_scoket_server_log_{}.log'.format(date_str))
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

class ClientThread(threading.Thread):
    def __init__(self, client_address, client_socket):
        self.total_data_length = 0
        self.last_data_length = 0
        self.last_time = time.time()
        self.connected = False
        threading.Thread.__init__(self)
        self.client_socket = client_socket
        self.client_address = client_address
        self.start_time = datetime.now()  # 记录连接开始的时间
        logger.info("New connection added: %s at %s", client_address, self.start_time.strftime('%Y_%m_%d %H:%M:%S'))

    def print_rate(self):
        while self.connected:
            time.sleep(5)
            current_time = time.time()
            current_data_length = self.total_data_length
            rate = (current_data_length - self.last_data_length) / (current_time - self.last_time) /1048576
            logger.info('%s Current rate: %.2f MB/sec', self.client_address, rate)
            self.last_data_length = current_data_length
            self.last_time = current_time

    def run(self):
        self.total_data_length = 0  # 初始化数据长度计数器
        self.recvmd5 = hashlib.md5()  # 初始化MD5计算器
        self.sendmd5 = hashlib.md5()  # 初始化MD5计算器
        self.connected = True
        threading.Thread(target=self.print_rate).start()
        filename = "{}_{}_{}.bin".format(self.client_address[0], self.client_address[1], datetime.now().strftime('%Y%m%d%H%M%S'))
        with open(filename, "wb") as file:
            while True:
                try:
                    data = self.client_socket.recv(1024)
                except socket.error as e:
                    logger.info("Connection reset by peer: %s", self.client_address)
                    logger.info('%s recv MD5: %s', self.client_address, self.recvmd5.hexdigest())  # 打印MD5值
                    logger.info('%s send MD5: %s', self.client_address, self.sendmd5.hexdigest())  # 打印MD5值
                    logger.info('%s Total data length: %s', self.client_address, self.total_data_length)
                    self.connected = False  # 连接已关闭
                    break
                self.total_data_length += len(data)  # 更新数据长度计数器
                self.recvmd5.update(data)  # 更新MD5值

                if not data:
                    self.end_time = datetime.now()  # 记录连接结束的时间
                    duration = self.end_time - self.start_time  # 计算连接时长
                    duration_formatted = str(duration).split(".")[0]  # 格式化为时:分:秒的格式
                    logger.info("Connection closed by %s", self.client_address)
                    logger.info('%s Connect time: %s', self.client_address, self.start_time.strftime('%Y_%m_%d %H:%M:%S'))
                    logger.info('%s Disconnect time: %s', self.client_address, self.end_time.strftime('%Y_%m_%d %H:%M:%S'))
                    logger.info('%s Total connect time: %s', self.client_address, duration_formatted)
                    logger.info('%s Total data length: %s', self.client_address, self.total_data_length)
                    logger.info('%s recv MD5: %s', self.client_address, self.recvmd5.hexdigest())  # 打印MD5值
                    logger.info('%s send MD5: %s', self.client_address, self.sendmd5.hexdigest())  # 打印MD5值
                    self.connected = False  # 连接已关闭
                    file.close()
                    break
                file.write(data)
                try:
                    self.client_socket.send(data)
                    self.sendmd5.update(data)
                except socket.error as e:
                    logger.info("Connection reset by peer: %s", self.client_address)
                    logger.info('%s MD5: %s', self.client_address, self.recvmd5.hexdigest())

        # if os.stat(filename).st_size == 0:
        #     os.remove(filename)  # 删除文件
        os.remove(filename)  # 删除文件
        self.client_socket.close()

    def send_test_data(self):
        self.client_socket.send(send_test_data)

def start_server(host, port, send_flag):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info("Server started on %s:%s", host, port)

    while True:
        server_socket.listen(10)
        client_socket, client_address = server_socket.accept()
        new_thread = ClientThread(client_address, client_socket)
        new_thread.daemon = True
        new_thread.start()
        if send_flag:
            try:
                send_thread = threading.Thread(target=new_thread.send_test_data)
                send_thread.daemon = True
                send_thread.start()
            except Exception as exc:
                logger.info(exc)

def quit(signal, frame):
    logger.info('Server is stopping...')
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('需要输入参数: '
        '1.换回模式：./ServerTool.py IP port\n'
        '2.连接成功立即向客户端发送数据模式：./ServerTool.py IP port send_flag')
        sys.exit()

    host = sys.argv[1]
    port = int(sys.argv[2])
    if len(sys.argv) == 4:
        send_flag = int(sys.argv[3])
        send_test_data = '1' + '0' * 100000000
    else:
        send_flag = 0
    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)
    try:
        start_server(host, port, send_flag)
    except Exception as exc:
        logger.info(exc)

