from time import *
import paramiko
from multiprocessing import Process
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
        while True:
            sleep(0.5)
            ret = self.chan.recv(655350)
            ret = ret.decode('utf-8')
            result += ret
            return result
    '''
    发送文件
    @:param upload_files上传文件路径 例如：/tmp/RE_test_tool.py
    @:param upload_path 上传到目标路径 例如：/tmp/test_new.py
    '''
    def upload_file(self, upload_files, upload_path):
        try:
            tran = paramiko.Transport(sock=(self.ip, self.port))
            tran.connect(username=self.username, password=self.password)
            sftp = paramiko.SFTPClient.from_transport(tran)
            result = sftp.put(upload_files, upload_path)
            return True if result else False
        except Exception as ex:
            print(ex)
            tran.close()
        finally:
            tran.close()


# 连接正常的情况
if __name__ == '__main__':
    host = []
    server_72 = Linux('192.168.1.72', 'root', '123456')  # 传入Ip，用户名，密码
    server_76 = Linux('192.168.1.76', 'root', '123456')  # 传入Ip，用户名，密码
    server_72.send('cd /home/lbs/server/tc_set')
    server_76.send('cd /home/lbs/host_platform_v5.0.5')
    server_76.send('export LD_LIBRARY_PATH=./api')
    while True:
        try:
            res_76 = server_76.send('./HostPlatform modrdreg 5 0x61')
            print(res_76)
            # print(server_77.send('./HostPlatform modrdreg 4 0x66'))
            # print(server_77.send('./HostPlatform modrdreg 4 0x6d'))
            server_72.send('tc qdisc del dev p3p1 root')
            server_72.send('tc qdisc del dev p3p2 root')
            if '2]' in res_76:     # 2路，MDDP
                server_72.send('sh opt_cap_fluctuant_20.sh')      # TCP取消限速， sh kill.sh
                # print('TCP取消限速')
                print('10网卡限速')
            elif '1]' in res_76:    # 0路，TCP
                server_72.send('sh opt_cap_fluctuant_10.sh')  # TCP限速100KB/S， sh opt_tcp_fluctuant.sh
                print('10网卡限速')
            elif '3]' in res_76:    # 1路，CAP
                server_72.send('sh opt_cap_fluctuant_10.sh')  # TCP限速100KB/S， sh opt_tcp_fluctuant.sh
                print('20网卡限速')
            else:
                pass
            sleep(3)
        except Exception:
            sleep(5)
            print('host reset!')
            continue
