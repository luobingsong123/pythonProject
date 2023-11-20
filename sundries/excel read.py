# -*- coding: utf-8 -*-
import pandas as pd


def case_read(file):
    df = pd.read_excel(file)  #读取xlsx中第一个sheet
    test_data_dict = {}
    case_list = []
    step_list = []
    for i in df.index.values:#获取行号的索引，并对其进行遍历：
        #根据i来获取每一行指定的数据 并利用to_dict转成字典
        # case名称做键，step做值，剩下的东西做step里的子键值
        case=df.loc[i,['case', ]].to_list()
        step=df.loc[i,['step', ]].to_list()
        content=df.loc[i,['comments', 'server', 'user', 'password', 'shell_str', 'wait_str', 'timeout', 'fail_str', ]].to_dict()
        case_list.append(case)
        step_list.append(step)
        try:
            test_data_dict[case[0]][step[0]] = content
        except KeyError:
            test_data_dict[case[0]] = {step[0]: content}
    return test_data_dict, case_list, step_list


k = case_read('D:\FPGA自动测试表格-TCPUDP.xlsx')
print(k)
# print(type(k['test1']['step1']['timeout']))
# print()
print(type(k[0]['test1']['step1']['timeout']))
print(k[0]['test1']['step1']['timeout'])
print(type(k[1]))
print(type(k[2]))

#     test_data.append(row_data)
#     # print(test_data)
# print("最终获取到的数据是：{0}".format(test_data))
#
#
# data = []
# all_data = {}
# step = {}
# comments = {}
# server = {}
# user = {}
# password = {}
# shell_str = {}
# wait_str = {}
# timeout = {}
# fail_str = {}
# for i in df.index.values:  # 获取行号索引，遍历
#     row_data = df.loc[i].values
#     # row_data = df.loc[i, ['case', 'step', 'comments', 'server', 'user', 'password', 'shell_str', 'wait_str', 'timeout', 'fail_str', ]].to_dict()
#     # data.append(row_data)
#     # print(row_data[1])
#     try:
#         all_data[row_data[1]][row_data[2]].update({'comments': row_data[3]}, {'server': row_data[4]}, {'user': row_data[5]}, {'password': row_data[6]}, {'shell_str': row_data[7]}, {'wait_str': row_data[8]}, {'timeout': row_data[9]}, {'fail_str': row_data[10]})
#         comments[comments] = row_data[3]
#         # server[server] = [row_data[4]]
#         # user[user] = [row_data[5]]
#         # password[password] = [row_data[6]]
#         # shell_str[shell_str] = [row_data[7]]
#         # wait_str[wait_str] = [row_data[8]]
#         # timeout[timeout] = [row_data[9]]
#         # fail_str[fail_str] = [row_data[10]]
#         # step[row_data[2]].update'comments': row_data[3]
#         # all_data[row_data[1]].update(step)
#     except KeyError:
#         all_data[row_data[1]] = {row_data[2]: {}}
#         all_data[row_data[1]][row_data[2]] = {{'comments': row_data[3]}, {'server': row_data[4]}, {'user': row_data[5]}, {'password': row_data[6]}, {'shell_str': row_data[7]}, {'wait_str': row_data[8]}, {'timeout': row_data[9]}, {'fail_str': row_data[10]}}
#
#
#     # for j in row_data:
# print(all_data)



# print('数据：{0}'.format(data))
#     test_data.append(row_data)
#     # print(test_data)
# print("最终获取到的数据是：{0}".format(test_data))
#
#
# data = []
# all_data = {}
# step = {}
# comments = {}
# server = {}
# user = {}
# password = {}
# shell_str = {}
# wait_str = {}
# timeout = {}
# fail_str = {}
# for i in df.index.values:  # 获取行号索引，遍历
#     row_data = df.loc[i].values
#     # row_data = df.loc[i, ['case', 'step', 'comments', 'server', 'user', 'password', 'shell_str', 'wait_str', 'timeout', 'fail_str', ]].to_dict()
#     # data.append(row_data)
#     # print(row_data[1])
#     try:
#         all_data[row_data[1]][row_data[2]].update({'comments': row_data[3]}, {'server': row_data[4]}, {'user': row_data[5]}, {'password': row_data[6]}, {'shell_str': row_data[7]}, {'wait_str': row_data[8]}, {'timeout': row_data[9]}, {'fail_str': row_data[10]})
#         comments[comments] = row_data[3]
#         # server[server] = [row_data[4]]
#         # user[user] = [row_data[5]]
#         # password[password] = [row_data[6]]
#         # shell_str[shell_str] = [row_data[7]]
#         # wait_str[wait_str] = [row_data[8]]
#         # timeout[timeout] = [row_data[9]]
#         # fail_str[fail_str] = [row_data[10]]
#         # step[row_data[2]].update'comments': row_data[3]
#         # all_data[row_data[1]].update(step)
#     except KeyError:
#         all_data[row_data[1]] = {row_data[2]: {}}
#         all_data[row_data[1]][row_data[2]] = {{'comments': row_data[3]}, {'server': row_data[4]}, {'user': row_data[5]}, {'password': row_data[6]}, {'shell_str': row_data[7]}, {'wait_str': row_data[8]}, {'timeout': row_data[9]}, {'fail_str': row_data[10]}}
#
#
#     # for j in row_data:
# print(all_data)



# print('数据：{0}'.format(data))
