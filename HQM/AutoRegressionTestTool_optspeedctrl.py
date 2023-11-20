# coding=utf-8
import time
from time import sleep
import pandas as pd
import paramiko
import os


class Logging(object):
    def __init__(self, file_name):
        self.filename = open(file_name, 'w')

    def logging(self, msg):
        self.filename.write(msg + '\n')
        print(msg)


# 读用例文件
def case_read(file_name):
    df = pd.read_excel(file_name)  # 读取xlsx中第一个sheet
    test_data_dict = {}
    case_index = []  # case索引
    case_step_dict = {}    # step索引
    for i in df.index.values:   # 获取行号的索引，并对其进行遍历：
        # 根据i来获取每一行指定的数据 并利用to_dict转成字典
        read_case = df.loc[i,['case', ]].to_list()
        read_step = df.loc[i,['step', ]].to_list()
        content = df.loc[i,['comments', 'server', 'user', 'password', 'shell_str', 'wait_str', 'wait_time', 'timeout', 'fail_str']].to_dict()
        # case名称做键，step做值，剩下的东西做step里的子键值
        try:
            test_data_dict[read_case[0]][read_step[0]] = content
        except KeyError:
            test_data_dict[read_case[0]] = {read_step[0]: content}
        # 按表格顺序获取case,去掉重复case,作为case索引 case_index
        if read_case[0] not in case_index:
            case_index.append(read_case[0])
        # step字典,case_step_dict
        try:
            case_step_dict[read_case[0]].append(read_step[0])
        except KeyError:
            case_step_dict[read_case[0]] = [read_step[0]]
    return test_data_dict, case_index, case_step_dict


# 输出测试结果为表格
def write_test_result(**kwargs):
    test_case = []
    test_step = []
    test_result = []
    test_comments = []
    for k in kwargs.keys():
        for j in kwargs[k].keys():
            log.logging(
                f'TEST CASE {k} : STEP {j} RESULT {kwargs[k][j][0]}, TEST COMMENTS : {kwargs[k][j][1]}')
            test_case.append(k)
            test_step.append(j)
            if kwargs[k][j][0]:
                test_result.append('pass')
            else:
                test_result.append('fail')
            test_comments.append(kwargs[k][j][1])
    df = pd.DataFrame({'test_case': test_case, 'test_step': test_step,'test_result':test_result,'test_comments': test_comments})
    df.to_excel(file + '.xlsx')


# 执行用例,每个step对应的连接都作为参数传入；
def start(*args):
    step_result = {}
    # 执行测试
    for i in range(len(all_step_dict[case])):
        step_result[all_step_dict[case][i]] = class_list[i].start_test()
        sleep(3)
    # STEP执行完成后断开ssh连接
    for i in range(len(all_step_dict[case])):
        class_list[i].close()
    return step_result


# PyShell
class PyShell(object):
    def __init__(self, **kwargs):
        # self.case = kwargs['case']
        # self.step = kwargs['step']
        self.comments = kwargs['comments']
        self.server = kwargs['server']
        self.user = kwargs['user']
        self.password = str(kwargs['password'])
        self.shell_str = kwargs['shell_str'].split('|')
        self.wait_str = kwargs['wait_str'].split('|')
        self.wait_time = kwargs['wait_time']
        self.timeout = kwargs['timeout']
        self.fail_str = kwargs['fail_str'].split('|')
        # transport和channel
        self.transport = ''
        self.channel = ''
        # 链接失败的重试次数
        self.try_times = 3
        self.connect()

    # 调用该方法连接远程主机
    def connect(self):
        while True:
            # 连接过程中可能会抛出异常，比如网络不通、链接超时
            try:
                self.transport = paramiko.Transport(sock=(self.server, 22))
                self.transport.connect(username=self.user, password=self.password)
                self.channel = self.transport.open_session()
                self.channel.settimeout(self.timeout)
                self.channel.get_pty()
                self.channel.invoke_shell()  # 伪终端方法，命令执行后连接不会重置
                # 如果没有抛出异常说明连接成功，直接返回
                print('连接%s成功' % self.server)
                # 接收到的网络数据解码为str
                print(self.channel.recv(65535))
                return
            # 直接返回失败不定位
            except Exception:
                if self.try_times != 0:
                    print('连接%s失败，进行重试' % self.server)
                    self.try_times -= 1
                else:
                    print('重试3次失败，结束程序')
                    exit(1)

    # 发送要执行的命令
    def send(self, cmd):
        cmd += '\r'
        result = ''
        # 发送要执行的命令
        self.channel.send(cmd)
        # 回显很长的命令可能执行较久，通过循环分批次取回回显,执行成功返回true,失败返回false
        while True:
            sleep(0.5)
            ret = self.channel.recv(-1)
            ret = ret.decode('utf-8')
            result += ret
            return result

    # 启动命令下发&回显匹配
    def start_test(self):
        times = 0
        if len(self.shell_str) > 1:
            for i in self.shell_str[0:-1]:
                self.send(i)
        result = self.send(self.shell_str[-1])
        while times < self.timeout:
            for i in self.wait_str:
                if i in result:
                    log.logging(result)
                    return True, self.comments + ' pass'
            for i in self.fail_str:
                if i in result:
                    log.logging(result)
                    return False, self.comments + ' fail'
            log.logging(result)
            wait_time = 0
            while wait_time < self.wait_time:
                times += 1
                wait_time += 1
                sleep(1)
            d = '\n'
            result = self.send(d)
        return False, self.comments + ' timeout'

    # 断开连接
    def close(self):
        self.channel.close()
        self.transport.close()


if __name__ == '__main__':
    while True:
        # 用例内容获取
        # filename = input("Enter the file path/file name (Press 'Ctrl + C' exit) ：")
        test_flag = True
        datetime = time.strftime("%Y%m%d%H%M%S", time.localtime())
        file = 'opt_speed_ctrl-' + datetime
        log = Logging(file + '.log')
        step_78_clientdemo= {'comments': 'step_78_rdreg', 'server': '192.168.1.78', 'user': 'root', 'password': 123456, 'shell_str': '/home/lbs/host_platform_v5.0.3/sh_rdreg.sh', 'wait_str': 'mod register', 'wait_time': 1, 'timeout': 5, 'fail_str': 'error'}
        step_78_host= {'comments': 'step_78_rdreg', 'server': '192.168.1.78', 'user': 'root', 'password': 123456, 'shell_str': '/home/lbs/host_platform_v5.0.3/sh_rdreg.sh', 'wait_str': 'mod register', 'wait_time': 1, 'timeout': 5, 'fail_str': 'error'}
        step_78_rdreg = {'comments': 'step_78_rdreg', 'server': '192.168.1.78', 'user': 'root', 'password': 123456, 'shell_str': '/home/lbs/host_platform_v5.0.3/sh_rdreg.sh', 'wait_str': 'mod register', 'wait_time': 1, 'timeout': 5, 'fail_str': 'error'}
        step_72_tcstart = {'comments': 'step_72_tcstart', 'server': '192.168.1.72', 'user': 'root', 'password': 123456, 'shell_str': '/home/lbs/server/speed.sh', 'wait_str': ']#', 'wait_time': 1, 'timeout': 5, 'fail_str': 'RTNETLINK answers:'}
        step_72_tcstop = {'comments': 'step_72_tcstop', 'server': '192.168.1.72', 'user': 'root', 'password': 123456, 'shell_str': 'tc qdisc del dev p3p2 root', 'wait_str': ']#', 'wait_time': 1, 'timeout': 5, 'fail_str': 'RTNETLINK answers:'}
        step_72_server = {'comments': 'step_72_tcstop', 'server': '192.168.1.72', 'user': 'root', 'password': 123456, 'shell_str': 'tc qdisc del dev p3p2 root', 'wait_str': ']#', 'wait_time': 1, 'timeout': 5, 'fail_str': 'RTNETLINK answers:'}
        step_76_client = {'comments': 'step_76_tcstop', 'server': '192.168.1.76', 'user': 'root', 'password': 123456, 'shell_str': 'tc qdisc del dev p3p2 root', 'wait_str': ']#', 'wait_time': 1, 'timeout': 5, 'fail_str': 'RTNETLINK answers:'}

        # 初始化
        pyshell_78_host = PyShell(**step_78_host)
        pyshell_78_clientdemo = PyShell(**step_78_clientdemo)
        pyshell_78_rdreg = PyShell(**step_78_rdreg)
        pyshell_72_tcstart = PyShell(**step_72_tcstart)
        pyshell_72_tcstop = PyShell(**step_72_tcstop)
        pyshell_72_server = PyShell(**step_72_server)
        pyshell_76_client = PyShell(**step_76_client)

        # 环境初始化
        pyshell_78_clientdemo.send('cd /home/lbs/ClientDemo_v4.0.18 && sh fpgastop.sh')
        sleep(1)
        pyshell_78_host.send('cd /home/lbs/host_platform_v5.0.3 && sh kill.sh')
        sleep(1)
        pyshell_72_server.send('/home/lbs/server/kill.sh')
        sleep(1)
        pyshell_76_client.send('/home/lbs/opt_client/kill.py')
        sleep(1)

        # 启动
        pyshell_78_clientdemo.send('cd /home/lbs/ClientDemo_v4.0.18 && sh fpgastart.sh')
        sleep(1)
        pyshell_78_host.send('cd /home/lbs/host_platform_v5.0.3 && sh run.sh')
        sleep(1)
        log.logging(pyshell_72_server.send('cd /home/lbs/server  && sh overtime_shopt.sh'))
        sleep(1)
        log.logging(pyshell_76_client.send('/home/lbs/opt_client/opt_TCPclient1.py'))
        sleep(1)

        # 监控
        pyshell_78_rdreg.send('cd /home/lbs/host_platform_v5.0.3')
        i = 0
        while test_flag:
            revalue = pyshell_78_rdreg.send('./sh_rdreg_speed.sh')
            log.logging(revalue)
            if '0]' in revalue:
                log.logging(pyshell_72_tcstop.send('tc qdisc del dev p3p2 root'))
            elif '1]' in revalue:
                log.logging(pyshell_72_tcstart.send('/home/lbs/server/speed.sh'))
            else:
                log.logging(pyshell_72_tcstop.send('tc qdisc del dev p3p2 root'))
            sleep(2)
            if i % 100 == 0:
                try:
                    log.logging(pyshell_78_rdreg.send('./Debug_MS5_shopt_rdreg.sh'))
                except EOFError:
                    pass
                # if '[0]' in pyshell_78_rdreg.send('./sh_end.sh'):
                #     test_flag = False
            sleep(1)
            i += 1

        # 关闭
        try:
            pyshell_78_clientdemo.send('cd /home/lbs/ClientDemo_v4.0.18 && mv data data_' + datetime)
            pyshell_78_clientdemo.send('cd /home/lbs/ClientDemo_v4.0.18 && sh fpgastop.sh')
            sleep(1)
            pyshell_78_host.send('cd /home/lbs/host_platform_v5.0.3 && sh kill.sh')
            sleep(1)
            pyshell_72_server.send('/home/lbs/server/kill.sh')
            sleep(1)
            pyshell_76_client.send('/home/lbs/opt_client/kill.py')
            sleep(1)
        except EOFError:
            pass