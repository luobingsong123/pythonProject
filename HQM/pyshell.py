from time import *
import paramiko
from multiprocessing import Process
from multiprocessing import Queue
from threading import Thread
# coding=utf-8


# 定义一个类，表示一台远端linux主机
class Linux(object):
    # 通过IP, 用户名，密码，超时时间初始化一个远程Linux主机
    def __init__(self, ip, username, password, timeout=30):
        self.ip = ip
        self.username = username
        self.password = password
        self.timeout = timeout
        # transport和chanel
        self.t = ''
        self.chan = ''
        # 链接失败的重试次数
        self.try_times = 3
        self.connect()

    # 调用该方法连接远程主机
    def connect(self):
        while True:
            # 连接过程中可能会抛出异常，比如网络不通、链接超时
            try:
                self.t = paramiko.Transport(sock=(self.ip, 22))
                self.t.connect(username=self.username, password=self.password)
                self.chan = self.t.open_session()
                self.chan.settimeout(self.timeout)
                self.chan.get_pty()
                self.chan.invoke_shell()
                # 如果没有抛出异常说明连接成功，直接返回
                print('连接%s成功' % self.ip)
                # 接收到的网络数据解码为str
                # print(self.chan.recv(655350).decode('utf-8'))
                print(self.chan.recv(655350))
                return
            # 这里不对可能的异常如socket.error, socket.timeout细化，直接一网打尽
            except Exception as e1:
                if self.try_times != 0:
                    print('连接%s失败，进行重试' % self.ip)
                    self.try_times -= 1
                else:
                    print('重试3次失败，结束程序')
                    exit(1)

    # 断开连接
    def close(self):
        self.chan.close()
        self.t.close()

    # 发送要执行的命令
    def send(self, cmd):
        cmd += '\r'
        result = ''
        # 发送要执行的命令
        self.chan.send(cmd)
        # 回显很长的命令可能执行较久，通过循环分批次取回回显,执行成功返回true,失败返回false
        # 这里加一个循环读取回显的线程
        while True:
            sleep(0.5)
            ret = self.chan.recv(655350)
            ret = ret.decode('utf-8')
            result += ret
            test.push(result)
            return result


class ResultPush(object):
    def __init__(self,queue):
        self.q = queue

    def push(self, msg):
        self.q.put(msg)


def customer(queue1):
    print("start customer")
    while 1:
        data = queue1.get()  # 收消息
        print(data)


# 连接正常的情况
if __name__ == '__main__':
    server_78 = Linux('192.168.1.78', 'root', '123456')  # 传入Ip，用户名，密码
    q = Queue()  # 创建一个队列
    cus = Thread(target=customer, args=(q,))
    cus.start()
    # 消息队列初始化
    test = ResultPush(q)
    while True:
        res = server_78.send(input(''))
