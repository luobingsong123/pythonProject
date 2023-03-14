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
        filename = input("Enter the file path/file name：")
        datetime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        file = os.path.basename(filename).split('.')[0] + datetime
        log = Logging(file + '.log')
        all_data = case_read(filename)
        all_test_data = all_data[0]     # dict
        all_case_index = all_data[1]    # list
        all_step_dict = all_data[2]    # dict
        log.logging(filename)
        case_result = {}
        # for循环根据case-step进行类初始化，每次把所有step的ssh都先连接上，再给函数进行操作；
        # 执行测试部分
        for case in all_case_index:
            # case内操作
            class_list = []
            log.logging('START TESTING CASE: %s' % case)
            log.logging('THE CASE START TIME: %s' % datetime)
            for step in all_step_dict[case]:
                # step的ssh初始化
                step_init = PyShell(**all_test_data[case][step])  # 传递列表进去
                # 初始化后按case放进list
                class_list.append(step_init)
            res = start(*all_step_dict[case],*class_list)
            case_result[case] = res
            sleep(10)
            log.logging('CASE ENDING: %s' % case)
            log.logging('THE CASE END TIME: %s' % time.strftime("%Y.%m.%d %H:%M", time.localtime()))
        # 输出测试结果
        write_test_result(**case_result)
