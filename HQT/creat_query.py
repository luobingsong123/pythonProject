#!/usr/local/bin/python3
# -*- coding: utf-8 -*-
import pymysql
import pandas as pd
import pymysql.cursors
import os

'''
1.查询数据库的所有账户信息、合约名+涨跌停价格
2.生产全用户+合约的FAK订单数据
'''


class get_origin_data(object):
    def __init__(self, host, port, db, user, password):
        self.conn = pymysql.connect(host=host, port=port, db=db, user=user, password=password, charset='utf8')
        self.tb_account_funds_info = self.get_tb_account_funds_info("tb_account_funds_info")
        self.tb_account_position = self.get_tb_account_position("tb_account_position")
        self.tb_account_instrument_rates = self.get_tb_instrument_rates("tb_account_instrument_rates")
        self.tb_instrument_info = self.get_tb_instrument_info("tb_instrument_info")
        # self.tb_order_info = self.get_tb_order_info("tb_order_info")
        # self.tb_fee_ratio_info = self.get_tb_fee_ratio_info("tb_fee_ratio_info")
        # self.tb_trade_info = self.get_tb_trade_info("tb_trade_info")
        self.tb_trading_code_info = self.get_tb_trading_code_info("tb_trading_code_info")
        self.order_ref_id = self.get_all_order_ref_id()
        print(self.order_ref_id)
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
        if len(order_sys_id_list) != len(set(order_sys_id_list)):
            print("order_sys_id重复！请确认！")
        if len(order_local_i_d_list) != len(set(order_local_i_d_list)):
            print("order_local_i_d重复！请确认！")
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

    def get_all_order_ref_id(self):
        order_ref = {}
        for investor_id in self.tb_account_funds_info.keys():
            data = pd.read_sql(
                "SELECT * FROM `tb_order_info` WHERE investor_id = {} ORDER BY order_ref DESC LIMIT 1".format(
                    investor_id), self.conn).to_dict(orient="records")
            if data:
                order_ref[investor_id] = data[0]["order_ref"] + 1
            else:
                order_ref[investor_id] = 0
        return order_ref


if __name__ == '__main__':
    # total_data = get_origin_data(host='171.17.104.16', port=3306, user='root', password='123456', db='hqt_fut_lbs')
    total_data = get_origin_data(host='171.17.106.117', port=3306, user='root', password='123456', db='hqt_fut_lbs')
    instrument_id_list = total_data.tb_instrument_info.keys()
    account_id_list = total_data.tb_account_funds_info.keys()

    client_id = {}
    for account_id in account_id_list:
        client_id[account_id] = total_data.tb_trading_code_info[account_id]["client_id"]

