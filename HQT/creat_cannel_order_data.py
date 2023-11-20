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


if __name__ == '__main__':
    # total_data = get_origin_data(host='171.17.104.16', port=3306, user='root', password='123456', db='hqt_fut_lbs')
    total_data = get_origin_data(host='171.17.106.117', port=3306, user='root', password='123456', db='hqt_fut_lbs')
    instrument_id_list = total_data.tb_instrument_info.keys()
    account_id_list = total_data.tb_account_funds_info.keys()
    client_id = {}
    for account_id in account_id_list:
        client_id[account_id] = total_data.tb_trading_code_info[account_id]["client_id"]
    last_price_dict = {}
    for instrument_id in instrument_id_list:
        last_price = total_data.tb_instrument_info[instrument_id]["last_price"]
        upper_limit_price = total_data.tb_instrument_info[instrument_id]["upper_limit_price"]
        lower_limit_price = total_data.tb_instrument_info[instrument_id]["lower_limit_price"]
        price_tick = total_data.tb_instrument_info[instrument_id]["price_tick"]
        last_price_dict[instrument_id] = [last_price, upper_limit_price, lower_limit_price,
                                          upper_limit_price + price_tick, upper_limit_price - price_tick,
                                          lower_limit_price + price_tick, lower_limit_price - price_tick,-price_tick,-upper_limit_price,-lower_limit_price]
    min_limit_order_volume_dict = {}
    for instrument_id in instrument_id_list:
        max_limit_order_volume = total_data.tb_instrument_info[instrument_id]["max_limit_order_volume"]
        min_limit_order_volume = total_data.tb_instrument_info[instrument_id]["min_limit_order_volume"]
        min_limit_order_volume_dict[instrument_id] = [min_limit_order_volume*2, max_limit_order_volume, min_limit_order_volume,max_limit_order_volume-min_limit_order_volume,
                                                      max_limit_order_volume+min_limit_order_volume,0, -min_limit_order_volume, -max_limit_order_volume]

    # 新建文件夹
    if not os.path.exists("data"):
        os.mkdir("data")
    if not os.path.exists("data/fak_open_10000"):
        os.mkdir("data/fak_open_10000")
    if not os.path.exists("data/all_user_instrument_traversal"):
        os.mkdir("data/all_user_instrument_traversal")
    if not os.path.exists("data/all_traversal"):
        os.mkdir("data/all_traversal")
    if not os.path.exists("data/fak_close_10000"):
        os.mkdir("data/fak_close_10000")
    if not os.path.exists("data/fak_close_true"):
        os.mkdir("data/fak_close_true")

    # print("fak开仓全合约10000笔订单csv测试用例开始生成数据:")
    # for account_id in account_id_list:
    #     print("开始生成账户{}的数据".format(account_id))
    #     csv_data = open("data/fak_open_10000/{}_fak_open_total_instrument_data_10000.csv".format(account_id), "w")
    #     csv_data.write("0,{},\n".format(account_id))
    #     csv_data.write("10,{},1,\n".format(account_id))
    #     csv_lens = 2
    #     while csv_lens < 10000:
    #         for instrument_id in instrument_id_list:
    #             csv_data.write(
    #                 "7,{},{},PRE,{},4,0,0,{},{},\n".format(account_id, client_id[account_id], instrument_id,
    #                                                        int(last_price_dict[instrument_id][0] * 10000),
    #                                                        min_limit_order_volume_dict[instrument_id][0]))
    #             csv_lens += 1
    #     print("账户{}的数据生成完毕".format(account_id))
    #     csv_data.close()
    # print("fak开仓全合约10000笔订单csv测试用例数据生成完毕！")
    #
    # close_offsetflag = [1, 3, 4]
    # print("fak平仓/平今/平昨全合约10000笔订单csv测试用例开始生成数据:")
    # for account_id in account_id_list:
    #     print("开始生成账户{}的数据".format(account_id))
    #     csv_data = open("data/fak_close_10000/{}_fak_close_total_instrument_data_10000.csv".format(account_id), "w")
    #     csv_data.write("0,{},\n".format(account_id))
    #     csv_data.write("10,{},1,\n".format(account_id))
    #     csv_lens = 2
    #     while csv_lens < 10000:
    #         for instrument_id in instrument_id_list:
    #             for offsetflag in close_offsetflag:
    #                 csv_data.write(
    #                     "7,{},{},PRE,{},4,0,{},{},{},\n".format(account_id, client_id[account_id], instrument_id, offsetflag,
    #                                                            int(last_price_dict[instrument_id][0] * 10000),
    #                                                            min_limit_order_volume_dict[instrument_id][0]))
    #             csv_lens += 1
    #     print("账户{}的数据生成完毕".format(account_id))
    #     csv_data.close()
    # print("fak开仓全合约10000笔订单csv测试用例数据生成完毕！")

    print("有持仓数据合约fak平仓/平今/平昨订单csv测试用例开始生成数据:")

    for investor_id in total_data.tb_account_position.keys():
        print("开始生成账户{}的数据".format(investor_id))
        csv_data = open("data/fak_close_true/{}_fak_close_true_data.csv".format(investor_id), "w")
        csv_data.write("0,{},\n".format(investor_id))
        csv_data.write("10,{},1,\n".format(investor_id))
        for instrument_id in total_data.tb_account_position[investor_id].keys():
            for direction in total_data.tb_account_position[investor_id][instrument_id].keys():
                offsetflag_ = []
                if direction == '0':
                    direction_ = 1
                elif direction == '1':
                    direction_ = 0
                if total_data.tb_account_position[investor_id][instrument_id][direction]["position"] != 0:
                    offsetflag_.append(3)
                if total_data.tb_account_position[investor_id][instrument_id][direction]["y_d_position"] != 0:
                    offsetflag_.append(4)
                for offsetflag in offsetflag_:
                    # if offsetflag == 3:
                    #     volume = total_data.tb_account_position[investor_id][instrument_id][direction]["position"]
                    # elif offsetflag == 4:
                    #     volume = total_data.tb_account_position[investor_id][instrument_id][direction]["y_d_position"]
                    # if volume > min_limit_order_volume_dict[instrument_id][1]:
                    volume = min_limit_order_volume_dict[instrument_id][2]
                    csv_data.write("7,{},{},PRE,{},4,{},{},{},{},\n".format(investor_id, client_id[investor_id], instrument_id, direction_, offsetflag,
                                                               int(last_price_dict[instrument_id][0] * 10000),volume))
        print("账户{}的数据生成完毕".format(investor_id))
        csv_data.write("10,{},2,\n".format(investor_id))
        csv_data.close()
    print("有持仓数据合约fak平仓/平今/平昨订单csv测试用例数据生成完毕！")


    # ordertype = [2, 4, 5]
    # direction = [1, 2]
    # offsetflag = [0, 1, 3, 4]
    # # 量、价边界值数据，考虑最小变动价位、最小变动量、超量超价
    # # 边界值和正常值分开
    # # 边界值做个区分
    # print("全遍历csv测试用例开始生成数据:")
    # for account_id in account_id_list:
    #     print("开始生成账户{}的数据".format(account_id))
    #     csv_data = open("data/all_traversal/{}_all_traversal.csv".format(account_id), "w")
    #     csv_data.write("0,{},\n".format(account_id))
    #     csv_data.write("10,{},1,\n".format(account_id))
    #
    #     for offsetflag_ in offsetflag:
    #         for ordertype_ in ordertype:
    #             for direction_ in direction:
    #                 for price_ in last_price_dict[instrument_id]:
    #                     for volume_ in min_limit_order_volume_dict[instrument_id]:
    #                         for instrument_id in instrument_id_list:
    #                             csv_data.write(
    #                                 "7,{},{},PRE,{},{},{},{},{},{},\n".format(account_id, client_id[account_id], instrument_id,
    #                                                                           int(price_ * 10000), ordertype_,
    #                                                                           direction_, offsetflag_, volume_))
    #     print("账户{}的数据生成完毕".format(account_id))
    #     # 发完撤单
    #     csv_data.write("10,{},1,\n".format(account_id))
    #     csv_data.write("12,{},\n".format(account_id))
    #     csv_data.write("10,{},10,\n".format(account_id))
    #     csv_data.close()
    # print("全遍历csv测试用例开始生成数据！")
    #
    # print("全用户全合约全方向遍历csv测试用例开始生成数据:")
    # for account_id in account_id_list:
    #     print("开始生成账户{}的数据".format(account_id))
    #     csv_data = open("data/all_user_instrument_traversal/{}_all_user_instrument_traversal.csv".format(account_id), "w")
    #     csv_data.write("0,{},\n".format(account_id))
    #     csv_data.write("10,{},1,\n".format(account_id))
    #     for instrument_id in instrument_id_list:
    #         for ordertype_ in ordertype:
    #             for direction_ in direction:
    #                 for offsetflag_ in offsetflag:
    #                         csv_data.write("7,{},{},PRE,{},{},{},{},{},{},\n".format(account_id, client_id[account_id], instrument_id,
    #                                                                                          int(last_price_dict[instrument_id][0] * 10000),
    #                                                                                          ordertype_, direction_, offsetflag_,
    #                                                                                          min_limit_order_volume_dict[instrument_id][0]))
    #     print("账户{}的数据生成完毕".format(account_id))
    #     # 发完撤单
    #     csv_data.write("10,{},1,\n".format(account_id))
    #     csv_data.write("12,{},\n".format(account_id))
    #     csv_data.write("10,{},10,\n".format(account_id))
    #     csv_data.close()
    # print("全用户全合约全方向遍历csv测试用例开始生成数据！")
