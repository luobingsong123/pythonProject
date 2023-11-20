#!/usr/local/bin/python3
# -*- coding: utf-8 -*-
import pymysql
import copy
import pandas as pd
import pymysql.cursors
import subprocess

'''
柜台订单表有状态的就对比，状态为7的就不管了
会出现客户端有柜台没有的情况

'''

BC_EXE = r"D:\program file\Beyond Compare 4\BCompare.exe"

def compare_files(file1, file2):
    process = subprocess.Popen([BC_EXE, file1, file2])




def write_dict_data(dict_data, file_name):
    tb_account_position_log = open(file_name + "_tb_account_position_log.csv", "w")
    for k in dict_data.tb_account_position.keys():
        for j in dict_data.tb_account_position[k].keys():
            for i in dict_data.tb_account_position[k][j].keys():
                # 写文件，','分隔
                tb_account_position_log.write(str(k) + ',' + str(j) + ',' + str(i) + ',' + str(
                    dict_data.tb_account_position[k][j][i]) + '\n')
    tb_account_position_log.close()

    tb_account_funds_info_log = open(file_name + "_tb_account_funds_info_log.csv", "w")
    for k in dict_data.tb_account_funds_info.keys():
        tb_account_funds_info_log.write(str(k) + ',' + str(dict_data.tb_account_funds_info[k]) + '\n')
    tb_account_funds_info_log.close()

    tb_account_instrument_rates_log = open(file_name + "_tb_account_instrument_rates_log.csv", "w")
    for k in dict_data.tb_account_instrument_rates.keys():
        for j in dict_data.tb_account_instrument_rates[k].keys():
            tb_account_instrument_rates_log.write(
                str(k) + ',' + str(j) + ',' + str(dict_data.tb_account_instrument_rates[k][j]) + '\n')
    tb_account_instrument_rates_log.close()

    tb_instrument_info_log = open(file_name + "_tb_instrument_info_log.csv", "w")
    for k in dict_data.tb_instrument_info.keys():
        tb_instrument_info_log.write(str(k) + ',' + str(dict_data.tb_instrument_info[k]) + '\n')
    tb_instrument_info_log.close()

    tb_order_info_log = open(file_name + "_tb_order_info_log.csv", "w")
    for k in dict_data.tb_order_info.keys():
        for j in dict_data.tb_order_info[k].keys():
            tb_order_info_log.write(str(k) + ',' + str(j) + ',' + str(dict_data.tb_order_info[k][j]) + '\n')
    tb_order_info_log.close()

    tb_fee_ratio_info_log = open(file_name + "_tb_fee_ratio_info_log.csv", "w")
    for k in dict_data.tb_fee_ratio_info.keys():
        for j in dict_data.tb_fee_ratio_info[k].keys():
            tb_fee_ratio_info_log.write(
                str(k) + ',' + str(j) + ',' + str(dict_data.tb_fee_ratio_info[k][j]) + '\n')
    tb_fee_ratio_info_log.close()

    tb_trade_info_log = open(file_name + "_tb_trade_info_log.csv", "w")
    for k in dict_data.tb_trade_info.keys():
        for j in dict_data.tb_trade_info[k].keys():
            tb_trade_info_log.write(
                str(k) + ',' + str(j) + ',' + str(dict_data.tb_trade_info[k][j]) + '\n')
    tb_trade_info_log.close()


class get_order_data(object):
    def __init__(self, host, port, db, user, password):
        self.conn = pymysql.connect(host=host, port=port, db=db, user=user, password=password, charset='utf8')
        self.counter_tb_order_info = self.get_counter_tb_order_info("tb_order_info")
        self.client_tb_order_info = self.get_client_tb_order_info("tb_order_info")

        self.conn.close()

    def get_counter_tb_order_info(self, table_name):  # 废单直接不处理
        '''
        订单号检查，遍历order_info，检查：
        order_sys_id大于0的部分，唯一不重复，放一个列表
        order_local_i_d，唯一不重复，放一个列表
        :return:
        '''
        order_sys_id_list = []
        order_local_i_d_list = []

        df = pd.read_sql("select * from {}".format(table_name), self.conn).to_dict(orient="records")
        result_dict = {}
        for row in df:
            investor_id = row["investor_id"]
            order_local_i_d = row["order_local_i_d"]
            order_sys_id = row["order_sys_id"]

            if row["investor_id"] != "":
                try:
                    result_dict[investor_id][order_local_i_d] = row
                except KeyError:
                    if investor_id not in result_dict:
                        result_dict[investor_id] = {}
                    result_dict[investor_id][order_local_i_d] = row

        # 检查order_sys_id、order_local_i_d是否重复
            if order_local_i_d != 0:
                order_local_i_d_list.append(order_local_i_d)
            if order_sys_id != 0:
                order_sys_id_list.append(order_sys_id)
        if len(order_sys_id_list) != len(set(order_sys_id_list)):
            print("order_sys_id重复！请确认！")
        if len(order_local_i_d_list) != len(set(order_local_i_d_list)):
            print("order_local_i_d重复！请确认！")
        return result_dict

    def get_client_tb_order_info(self, table_name):  # 废单直接不处理
        pass


if __name__ == '__main__':
    # 有废单 对比不了
    counter_order_data = get_order_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='hqt_fut_lbs')
    client_order_data = get_order_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='hqt_fut_lbs')

