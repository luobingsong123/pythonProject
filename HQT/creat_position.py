#!/usr/local/bin/python3
# -*- coding: utf-8 -*-
import pymysql
import pandas as pd
import pymysql.cursors
import os
import datetime


'''
1.查询数据库的所有账户信息、合约名+涨跌停价格
2.生产全用户+合约的FAK订单数据
'''


class get_origin_data(object):
    def __init__(self, host, port, db, user, password):
        self.conn = pymysql.connect(host=host, port=port, db=db, user=user, password=password, charset='utf8')
        # self.tb_account_funds_info = self.get_tb_account_funds_info("tb_account_funds_info")
        self.tb_trading_code_info = self.get_tb_account_info("tb_trading_code_info")
        self.tb_account_position = self.get_tb_account_position("tb_account_position")
        # print(self.tb_account_position.keys())
        # self.tb_account_instrument_rates = self.get_tb_instrument_rates("tb_account_instrument_rates")
        self.tb_instrument_info = self.get_tb_instrument_info("tb_instrument_info")
        # # self.tb_order_info = self.get_tb_order_info("tb_order_info")
        # # self.tb_fee_ratio_info = self.get_tb_fee_ratio_info("tb_fee_ratio_info")
        # # self.tb_trade_info = self.get_tb_trade_info("tb_trade_info")
        # self.tb_trading_code_info = self.get_tb_trading_code_info("tb_trading_code_info")

    def insert_sql_data(self):
        # 创建SQL参数初始值
        investor_id_list = self.tb_trading_code_info.keys()
        # print(investor_id_list)
        # contract_id = 0     #  instrument_id对应的id号
        instrument_id_list = self.tb_instrument_info.keys()
        EXCHANGE = 'SHFE'
        direction_list = ['0', '1']
        hedge_flag = 1
        # y_d_margin = 0  # 直接等于合约最新价*量
        # margin = 0  # 直接等于合约最新价*量
        posi_profit = 0
        close_profit = 0
        close_volume = 0
        total_average_price = 0
        # y_d_average_price = 0   # 直接等于最新价
        average_price = 0
        open_volume = 0
        # total_position = 0  # 直接等于昨持仓量
        position_frozen = 0
        y_d_position_frozen = 0
        y_d_position = 5000
        position = 0
        create_time = datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")
        update_time = datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")
        # pass_count = 0
        for investor_id in investor_id_list:
            for instrument_id in instrument_id_list:
                for direction in direction_list:
                    try:
                        if self.tb_account_position[investor_id][instrument_id][direction]:
                            # pass_count += 1
                            # print("已存在数据，跳过！", pass_count)
                            continue
                    except KeyError:
                        pass
                    account_id = self.tb_trading_code_info[investor_id]["account_id"]
                    contract_id = self.tb_instrument_info[instrument_id]["id"]
                    y_d_margin = self.tb_instrument_info[instrument_id]["last_price"] * y_d_position
                    margin = y_d_margin
                    total_position = y_d_position
                    y_d_average_price = self.tb_instrument_info[instrument_id]["last_price"]
                    sql = f"INSERT INTO tb_account_position(account_id, investor_id, contract_id, instrument_id, EXCHANGE, direction, hedge_flag, y_d_margin, margin, posi_profit, close_profit, close_volume, total_average_price, y_d_average_price, average_price, open_volume, total_position, position_frozen, y_d_position_frozen, y_d_position, `position`, create_time, update_time)VALUES('{account_id}', '{investor_id}', '{contract_id}', '{instrument_id}', '{EXCHANGE}', '{direction}', '{hedge_flag}', '{y_d_margin}', '{margin}', '{posi_profit}', '{close_profit}', '{close_volume}', '{total_average_price}', '{y_d_average_price}', '{average_price}', '{open_volume}', '{total_position}', '{position_frozen}', '{y_d_position_frozen}', '{y_d_position}', '{position}', '{create_time}', '{update_time}')"
                    try:
                        self.conn.cursor().execute(sql)
                        # print(f"Inserted data for {name}, CountryCode={country_code}, District={district}, Population={population}")
                    except Exception as e:
                        print(f"Failed to insert data: {e}")
                        # conn.rollback()

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

    def get_tb_account_info(self, table_name):
        df = pd.read_sql("select * from {}".format(table_name), self.conn).to_dict(orient="records")
        result_dict = {}
        for row in df:
            investor_id = row["investor_id"]
            result_dict[investor_id] = row
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


if __name__ == '__main__':
    # total_data = get_origin_data(host='171.17.104.16', port=3306, user='root', password='123456', db='hqt_fut_lbs')
    total_data = get_origin_data(host='171.17.106.117', port=3306, user='root', password='123456', db='hqt_fut_lbs')
    # total_data = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='hqt_fut_lbs')
    total_data.insert_sql_data()
    total_data.conn.close()