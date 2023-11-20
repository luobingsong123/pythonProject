#!/usr/local/bin/python3
# -*- coding: utf-8 -*-
import pymysql
import pandas as pd
import pymysql.cursors
import subprocess
import platform
import copy

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

    tb_trading_code_info_log = open(file_name + "_tb_trading_code_info_log.csv", "w")
    for k in dict_data.tb_trading_code_info.keys():
        tb_trading_code_info_log.write(
            str(k) + ',' + str(dict_data.tb_trading_code_info[k]) + '\n')
    tb_trading_code_info_log.close()

    tb_cancel_order_info_log = open(file_name + "_tb_cancel_order_info_log.csv", "w")
    for k in dict_data.tb_cancel_order_info.keys():
        for j in dict_data.tb_cancel_order_info[k].keys():
            tb_cancel_order_info_log.write(
                str(k) + ',' + str(j) + ',' + str(dict_data.tb_cancel_order_info[k][j]) + '\n')
    tb_cancel_order_info_log.close()


class get_order_data(object):
    def __init__(self, host, port, db, user, password):
        '''
            `tb_account_funds_info`
            `tb_account_position`
            `tb_order_info`
            `tb_instrument_info`
            `tb_account_instrument_rates`
            `tb_fee_ratio_info`
            `tb_cancel_order_info`
            `tb_trade_info`
            `tb_trading_code_info`
        '''
        self.conn = pymysql.connect(host=host, port=port, db=db, user=user, password=password, charset='utf8')
        self.tb_account_funds_info = self.get_tb_account_funds_info("tb_account_funds_info")
        self.tb_account_position = self.get_tb_account_position("tb_account_position")
        # self.tb_account_instrument_rates = self.get_tb_instrument_rates("tb_account_instrument_rates")
        self.tb_instrument_info = self.get_tb_instrument_info("tb_instrument_info")
        self.tb_order_info = self.get_tb_order_info("tb_order_info")
        self.tb_fee_ratio_info = self.get_tb_fee_ratio_info("tb_fee_ratio_info")
        self.tb_trade_info = self.get_tb_trade_info("tb_trade_info")
        # self.tb_trading_code_info = self.get_tb_trading_code_info("tb_trading_code_info")
        # self.tb_cancel_order_info = self.get_tb_cancel_order_info("tb_cancel_order_info")

        self.conn.close()

    def get_tb_account_funds_info(self, table_name):
        df = pd.read_sql("select * from {}".format(table_name), self.conn).to_dict(orient="records")
        result_dict = {}
        for row in df:
            investor_id = row["investor_id"]
            if investor_id not in result_dict:
                result_dict[investor_id] = row
            else:
                result_dict[investor_id].update(row)
        return result_dict

    def get_tb_account_position(self, table_name):  # 账户持仓
        df = pd.read_sql("select * from {}".format(table_name), self.conn).to_dict(orient="records")
        result_dict = {}
        for row in df:
            investor_id = row["investor_id"]
            instrument_id = row["instrument_id"]
            direction = row["direction"]
            try:
                result_dict[investor_id][instrument_id][direction] = row
            except KeyError:
                if investor_id not in result_dict:
                    result_dict[investor_id] = {}
                if instrument_id not in result_dict[investor_id]:
                    result_dict[investor_id][instrument_id] = {}
                result_dict[investor_id][instrument_id][direction] = row
            result_dict[investor_id][instrument_id][direction]['id'] = 0
            result_dict[investor_id][instrument_id][direction]['create_time'] = 0
            result_dict[investor_id][instrument_id][direction]['update_time'] = 0
            result_dict[investor_id][instrument_id][direction]['y_d_average_price'] = 0
            result_dict[investor_id][instrument_id][direction]['open_volume'] = 0
            result_dict[investor_id][instrument_id][direction]['close_volume'] = 0
        return result_dict

    def get_tb_order_info(self, table_name):  # 废单直接不处理
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
        # if len(order_sys_id_list) != len(set(order_sys_id_list)):
        #     print("order_sys_id重复！请确认！")
        # if len(order_local_i_d_list) != len(set(order_local_i_d_list)):
        #     print("order_local_i_d重复！请确认！")
            result_dict[investor_id][order_local_i_d]['id'] = 0
            result_dict[investor_id][order_local_i_d]['i_p'] = 0
            result_dict[investor_id][order_local_i_d]['m_a_c'] = 0
            result_dict[investor_id][order_local_i_d]['trader_id'] = 0
            result_dict[investor_id][order_local_i_d]['account_id'] = 0
            result_dict[investor_id][order_local_i_d]['client_id'] = 0
            result_dict[investor_id][order_local_i_d]['time_condition'] = 0
            result_dict[investor_id][order_local_i_d]['create_time'] = '0'
            result_dict[investor_id][order_local_i_d]['update_time'] = '0'
            if result_dict[investor_id][order_local_i_d]['limit_price'] > 999999:
                result_dict[investor_id][order_local_i_d]['limit_price'] /= 10000
        return result_dict

    def get_tb_instrument_info(self, table_name):
        df = pd.read_sql("select * from {}".format(table_name), self.conn).to_dict(orient="records")
        result_dict = {}
        for row in df:
            instrument_id = row["instrument_id"]
            if instrument_id not in result_dict:
                result_dict[instrument_id] = row
            else:
                result_dict[instrument_id].update(row)
            result_dict[instrument_id]['id'] = 0
            result_dict[instrument_id]['trading_status'] = 0
            result_dict[instrument_id]['settlement_price'] = 0
            result_dict[instrument_id]['lowest_price'] = 0
            result_dict[instrument_id]['highest_price'] = 0
            result_dict[instrument_id]['currency_id'] = 0
            result_dict[instrument_id]['start_deliv_date'] = 0
            result_dict[instrument_id]['end_deliv_date'] = 0
            result_dict[instrument_id]['open_date'] = 0
            result_dict[instrument_id]['create_date'] = 0
            result_dict[instrument_id]['expire_date'] = 0
            result_dict[instrument_id]['position_type'] = 0
            result_dict[instrument_id]['variety_id'] = 0
            result_dict[instrument_id]['options_type'] = 0
            result_dict[instrument_id]['open_price'] = 0
        return result_dict

    def get_tb_instrument_rates(self, table_name):
        df = pd.read_sql("select * from {}".format(table_name), self.conn).to_dict(orient="records")
        result_dict = {}
        # 遍历每一行记录
        for row in df:
            investor_id = row["investor_id"]
            instrument_id = row["instrument_id"]
            try:
                result_dict[investor_id][instrument_id] = row
            except KeyError:
                if investor_id not in result_dict:
                    result_dict[investor_id] = {}
                result_dict[investor_id][instrument_id] = row
        return result_dict

    def get_tb_fee_ratio_info(self, table_name):
        df = pd.read_sql("select * from {}".format(table_name), self.conn).to_dict(orient="records")
        result_dict = {}
        for row in df:
            investor_id = row["ratio_group_name"].split("|")[0]
            if row["ratio_group_name"].split("|")[1] == "":
                instrument_id = row["ratio_group_name"].split("|")[2]
            else:
                instrument_id = row["ratio_group_name"].split("|")[1]
            try:
                result_dict[investor_id][instrument_id] = row
            except KeyError:
                if investor_id not in result_dict:
                    result_dict[investor_id] = {}
                result_dict[investor_id][instrument_id] = row
            result_dict[investor_id][instrument_id]['ratio_group_name'] = 0
        return result_dict

    def get_tb_cancel_order_info(self, table_name):
        df = pd.read_sql("select * from {}".format(table_name), self.conn).to_dict(orient="records")
        result_dict = {}
        for row in df:
            investor_id = row["investor_id"]
            order_local_i_d = row["order_local_i_d"]
            if row["investor_id"] != "":
                try:
                    result_dict[investor_id][order_local_i_d] = row
                except KeyError:
                    if investor_id not in result_dict:
                        result_dict[investor_id] = {}
                    result_dict[investor_id][order_local_i_d] = row
        return result_dict

    def get_tb_trade_info(self, table_name):
        df = pd.read_sql("select * from {}".format(table_name), self.conn).to_dict(orient="records")
        result_dict = {}
        # 遍历每一行记录
        for row in df:
            investor_id = row["investor_id"]
            order_local_i_d = row["order_local_i_d"]
            trade_id = row["trade_id"]
            try:
                result_dict[investor_id][order_local_i_d][trade_id] = row
            except KeyError:
                if investor_id not in result_dict:
                    result_dict[investor_id] = {}
                if order_local_i_d not in result_dict[investor_id]:
                    result_dict[investor_id][order_local_i_d] = {}
                result_dict[investor_id][order_local_i_d][trade_id] = row
            result_dict[investor_id][order_local_i_d][trade_id]['id'] = 0
            result_dict[investor_id][order_local_i_d][trade_id]['account_id'] = 0
            result_dict[investor_id][order_local_i_d][trade_id]['trader_id'] = 0
            # result_dict[investor_id][order_local_i_d][trade_id]['create_time'] = result_dict[investor_id][order_local_i_d][trade_id]['create_time'][0:16]
            if result_dict[investor_id][order_local_i_d][trade_id]['price'] > 999999:
                result_dict[investor_id][order_local_i_d][trade_id]['price'] /= 10000
        return result_dict

    def get_tb_trading_code_info(self, table_name):
        df = pd.read_sql("select * from {}".format(table_name), self.conn).to_dict(orient="records")
        result_dict = {}
        for row in df:
            investor_id = row["investor_id"]
            if investor_id not in result_dict:
                result_dict[investor_id] = row
            else:
                result_dict[investor_id].update(row)
        return result_dict


if __name__ == '__main__':
    # 有废单 对比不了api报单和柜台订单情况
    # client_order_data = get_order_data(host='171.17.104.16', port=3306, user='root', password='123456', db='hqt_fut_lbs_apidemo_04')
    # counter_order_data = get_order_data(host='171.17.104.16', port=3306, user='root', password='123456', db='hqt_fut_lbs')

    client_order_data = get_order_data(host='171.17.104.16', port=3306, user='root', password='123456', db='hqt_fut_lbs_apidemo_01_18')
    counter_order_data = get_order_data(host='171.17.104.16', port=3306, user='root', password='123456', db='hqt_fut_18')

    client_order_data_bak = copy.deepcopy(client_order_data)
    counter_order_data_bak = copy.deepcopy(counter_order_data)

    # tb_account_funds_info
    log_client_tb_account_funds_info = open("query_client_tb_account_funds_info_log.csv", "w")
    log_counter_tb_account_funds_info = open("query_counter_tb_account_funds_info_log.csv", "w")
    tb_account_funds_info_pass_count = 0
    for k in client_order_data.tb_account_funds_info.keys():
        if client_order_data.tb_account_funds_info[k] == counter_order_data.tb_account_funds_info[k]:
            del client_order_data_bak.tb_account_funds_info[k]
            del counter_order_data_bak.tb_account_funds_info[k]
            tb_account_funds_info_pass_count += 1
    print('tb_account_funds_info_pass_count:',tb_account_funds_info_pass_count)
    for k in client_order_data_bak.tb_account_funds_info.keys():
        log_client_tb_account_funds_info.write(str(k) + ',' + str(client_order_data_bak.tb_account_funds_info[k]) + '\n')
    for k in counter_order_data_bak.tb_account_funds_info.keys():
        log_counter_tb_account_funds_info.write(str(k) + ',' + str(counter_order_data_bak.tb_account_funds_info[k]) + '\n')

    # tb_account_position
    log_client_tb_account_position = open("query_client_tb_account_position_log.csv", "w")
    log_counter_tb_account_position = open("query_counter_tb_account_position_log.csv", "w")
    tb_account_position_pass_count = 0
    for k in client_order_data.tb_account_position.keys():
        for j in client_order_data.tb_account_position[k].keys():
            if client_order_data.tb_account_position[k][j] == counter_order_data.tb_account_position[k][j]:
                del client_order_data_bak.tb_account_position[k][j]
                del counter_order_data_bak.tb_account_position[k][j]
                tb_account_position_pass_count += 1
    print('tb_account_position_pass_count:',tb_account_position_pass_count)
    for k in client_order_data_bak.tb_account_position.keys():
        for j in client_order_data_bak.tb_account_position[k].keys():
            log_client_tb_account_position.write(str(k) + ',' + str(j) + ',' + str(client_order_data_bak.tb_account_position[k][j]) + '\n')
    for k in counter_order_data_bak.tb_account_position.keys():
        for j in counter_order_data_bak.tb_account_position[k].keys():
            log_counter_tb_account_position.write(str(k) + ',' + str(j) + ',' + str(counter_order_data_bak.tb_account_position[k][j]) + '\n')

    # # tb_order_info
    # log_client_tb_order_info = open("query_client_tb_order_info_log.csv", "w")
    # log_counter_tb_order_info = open("query_counter_tb_order_info_log.csv", "w")
    # tb_order_info_pass_count = 0
    # for k in client_order_data.tb_order_info.keys():
    #     for j in client_order_data.tb_order_info[k].keys():
    #         if client_order_data.tb_order_info[k][j] == counter_order_data.tb_order_info[k][j]:
    #             del client_order_data_bak.tb_order_info[k][j]
    #             del counter_order_data_bak.tb_order_info[k][j]
    #             tb_order_info_pass_count += 1
    # print('tb_order_info_pass_count:',tb_order_info_pass_count)
    # for k in client_order_data_bak.tb_order_info.keys():
    #     for j in client_order_data_bak.tb_order_info[k].keys():
    #         log_client_tb_order_info.write(str(k) + ',' + str(j) + ',' + str(client_order_data_bak.tb_order_info[k][j]) + '\n')
    # for k in counter_order_data_bak.tb_order_info.keys():
    #     for j in counter_order_data_bak.tb_order_info[k].keys():
    #         log_counter_tb_order_info.write(str(k) + ',' + str(j) + ',' + str(counter_order_data_bak.tb_order_info[k][j]) + '\n')

    # tb_instrument_info
    log_client_tb_instrument_info = open("query_client_tb_instrument_info_log.csv", "w")
    log_counter_tb_instrument_info = open("query_counter_tb_instrument_info_log.csv", "w")
    tb_instrument_info_pass_count = 0
    for k in client_order_data.tb_instrument_info.keys():
        if client_order_data.tb_instrument_info[k] == counter_order_data.tb_instrument_info[k]:
            del client_order_data_bak.tb_instrument_info[k]
            del counter_order_data_bak.tb_instrument_info[k]
            tb_instrument_info_pass_count += 1
    print('tb_instrument_info_pass_count:',tb_instrument_info_pass_count)
    for k in client_order_data_bak.tb_instrument_info.keys():
        log_client_tb_instrument_info.write(str(k) + ',' + str(client_order_data_bak.tb_instrument_info[k]) + '\n')
    for k in counter_order_data_bak.tb_instrument_info.keys():
        log_counter_tb_instrument_info.write(str(k) + ',' + str(counter_order_data_bak.tb_instrument_info[k]) + '\n')

    # tb_account_instrument_rates
    # log_client_tb_account_instrument_rates = open("query_client_tb_account_instrument_rates_log.csv", "w")
    # log_counter_tb_account_instrument_rates = open("query_counter_tb_account_instrument_rates_log.csv", "w")
    # tb_account_instrument_rates_pass_count = 0
    # for k in client_order_data.tb_account_instrument_rates.keys():
    #     for j in client_order_data.tb_account_instrument_rates[k].keys():
    #         if client_order_data.tb_account_instrument_rates[k][j] == counter_order_data.tb_account_instrument_rates[k][j]:
    #             del client_order_data_bak.tb_account_instrument_rates[k][j]
    #             del counter_order_data_bak.tb_account_instrument_rates[k][j]
    #             tb_account_instrument_rates_pass_count += 1

    # tb_fee_ratio_info
    log_client_tb_fee_ratio_info = open("query_client_tb_fee_ratio_info_log.csv", "w")
    log_counter_tb_fee_ratio_info = open("query_counter_tb_fee_ratio_info_log.csv", "w")
    tb_fee_ratio_info_pass_count = 0
    for k in client_order_data.tb_fee_ratio_info.keys():
        for j in client_order_data.tb_fee_ratio_info[k].keys():
            if client_order_data.tb_fee_ratio_info[k][j] == counter_order_data.tb_fee_ratio_info[k][j]:
                del client_order_data_bak.tb_fee_ratio_info[k][j]
                del counter_order_data_bak.tb_fee_ratio_info[k][j]
                tb_fee_ratio_info_pass_count += 1
    print('tb_fee_ratio_info_pass_count:',tb_fee_ratio_info_pass_count)
    for k in client_order_data_bak.tb_fee_ratio_info.keys():
        for j in client_order_data_bak.tb_fee_ratio_info[k].keys():
            log_client_tb_fee_ratio_info.write(str(k) + ',' + str(j) + ',' + str(client_order_data_bak.tb_fee_ratio_info[k][j]) + '\n')
    for k in counter_order_data_bak.tb_fee_ratio_info.keys():
        for j in counter_order_data_bak.tb_fee_ratio_info[k].keys():
            log_counter_tb_fee_ratio_info.write(str(k) + ',' + str(j) + ',' + str(counter_order_data_bak.tb_fee_ratio_info[k][j]) + '\n')

    # tb_cancel_order_info

    # tb_trade_info
    log_client_tb_trade_info = open("query_client_tb_trade_info_log.csv", "w")
    log_counter_tb_trade_info = open("query_counter_tb_trade_info_log.csv", "w")
    tb_trade_info_pass_count = 0
    for k in client_order_data.tb_trade_info.keys():
        for j in client_order_data.tb_trade_info[k].keys():
            for i in client_order_data.tb_trade_info[k][j].keys():
                if client_order_data.tb_trade_info[k][j][i] == counter_order_data.tb_trade_info[k][j][i]:
                    del client_order_data_bak.tb_trade_info[k][j][i]
                    del counter_order_data_bak.tb_trade_info[k][j][i]
                    tb_trade_info_pass_count += 1
    print('tb_trade_info_pass_count:',tb_trade_info_pass_count)
    for k in client_order_data_bak.tb_trade_info.keys():
        for j in client_order_data_bak.tb_trade_info[k].keys():
            for i in client_order_data_bak.tb_trade_info[k][j].keys():
                log_client_tb_trade_info.write(str(k) + ',' + str(j) + ',' + str(i) + ',' + str(client_order_data_bak.tb_trade_info[k][j][i]) + '\n')
    for k in counter_order_data_bak.tb_trade_info.keys():
        for j in counter_order_data_bak.tb_trade_info[k].keys():
            for i in counter_order_data_bak.tb_trade_info[k][j].keys():
                log_counter_tb_trade_info.write(str(k) + ',' + str(j) + ',' + str(i) + ',' + str(counter_order_data_bak.tb_trade_info[k][j][i]) + '\n')

    # tb_trading_code_info

    # write_dict_data(counter_order_data, "query_counter")
    # write_dict_data(client_order_data, "query_client")

    if platform.system() == 'Windows':
        try:
            compare_files("query_client_tb_account_funds_info_log.csv", "query_counter_tb_account_funds_info_log.csv")
            compare_files("query_client_tb_account_position_log.csv", "query_counter_tb_account_position_log.csv")
            # compare_files("query_client_tb_order_info_log.csv", "query_counter_tb_order_info_log.csv")
            compare_files("query_client_tb_instrument_info_log.csv", "query_counter_tb_instrument_info_log.csv")
            # compare_files("query_client_tb_account_instrument_rates_log.csv", "query_counter_tb_account_instrument_rates_log.csv")
            compare_files("query_client_tb_fee_ratio_info_log.csv", "query_counter_tb_fee_ratio_info_log.csv")
            # compare_files("query_client_tb_cancel_order_info_log.csv", "query_counter_tb_cancel_order_info_log.csv")
            compare_files("query_client_tb_trade_info_log.csv", "query_counter_tb_trade_info_log.csv")
            # compare_files("query_client_tb_trading_code_info_log.csv", "query_counter_tb_trading_code_info_log.csv")
        except Exception as error:
            print(error)

