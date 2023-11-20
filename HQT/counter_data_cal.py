#!/usr/local/bin/python3
# -*- coding: utf-8 -*-
import pymysql
import copy
import pandas as pd
import pymysql.cursors
import subprocess
import platform

BC_EXE = r"D:\program file\Beyond Compare 4\BCompare.exe"


def round_(number, n):
    m = 10 ** n
    num = int(number * m + 0.5) / m
    return num
    
    
def compare_files(file1, file2):
    process = subprocess.Popen([BC_EXE, file1, file2])


def write_dict_data(dict_data, file_name):
    tb_account_position_log = open(file_name + "_tb_account_position_log.csv", "w")
    for k in dict_data.tb_account_position.keys():
        for j in sorted(dict_data.tb_account_position[k].keys()):
            for i in sorted(dict_data.tb_account_position[k][j].keys()):
                # 写文件，','分隔
                tb_account_position_log.write(str(k) + ',' + str(j) + ',' + str(i) + ',' + str(
                    dict_data.tb_account_position[k][j][i]) + '\n')
    tb_account_position_log.close()

    tb_account_funds_info_log = open(file_name + "_tb_account_funds_info_log.csv", "w")
    for k in dict_data.tb_account_funds_info.keys():
        tb_account_funds_info_log.write(str(k) + ',' + str(dict_data.tb_account_funds_info[k]) + '\n')
    tb_account_funds_info_log.close()

    # tb_account_instrument_rates_log = open(file_name + "_tb_account_instrument_rates_log.csv", "w")
    # for k in dict_data.tb_account_instrument_rates.keys():
    #     for j in dict_data.tb_account_instrument_rates[k].keys():
    #         tb_account_instrument_rates_log.write(
    #             str(k) + ',' + str(j) + ',' + str(dict_data.tb_account_instrument_rates[k][j]) + '\n')
    # tb_account_instrument_rates_log.close()
    #
    # tb_instrument_info_log = open(file_name + "_tb_instrument_info_log.csv", "w")
    # for k in dict_data.tb_instrument_info.keys():
    #     tb_instrument_info_log.write(str(k) + ',' + str(dict_data.tb_instrument_info[k]) + '\n')
    # tb_instrument_info_log.close()

    tb_order_info_log = open(file_name + "_tb_order_info_log.csv", "w")
    for k in dict_data.tb_order_info.keys():
        for j in dict_data.tb_order_info[k].keys():
            tb_order_info_log.write(str(k) + ',' + str(j) + ',' + str(dict_data.tb_order_info[k][j]) + '\n')
    tb_order_info_log.close()

    # tb_fee_ratio_info_log = open(file_name + "_tb_fee_ratio_info_log.csv", "w")
    # for k in dict_data.tb_fee_ratio_info.keys():
    #     for j in dict_data.tb_fee_ratio_info[k].keys():
    #         tb_fee_ratio_info_log.write(
    #             str(k) + ',' + str(j) + ',' + str(dict_data.tb_fee_ratio_info[k][j]) + '\n')
    # tb_fee_ratio_info_log.close()
    #
    tb_trade_info_log = open(file_name + "_tb_trade_info_log.csv", "w")
    for k in dict_data.tb_trade_info.keys():
        for j in dict_data.tb_trade_info[k].keys():
            tb_trade_info_log.write(
                str(k) + ',' + str(j) + ',' + str(dict_data.tb_trade_info[k][j]) + '\n')
    tb_trade_info_log.close()


class get_origin_data(object):
    def __init__(self, host, port, db, user, password):
        self.conn = pymysql.connect(host=host, port=port, db=db, user=user, password=password, charset='utf8')
        self.tb_account_funds_info = self.get_tb_account_funds_info("tb_account_funds_info")
        self.tb_account_position = self.get_tb_account_position("tb_account_position")
        self.tb_account_instrument_rates = self.get_tb_instrument_rates("tb_account_instrument_rates")
        self.tb_instrument_info = self.get_tb_instrument_info("tb_instrument_info")
        self.tb_order_info = self.get_tb_order_info("tb_order_info")
        self.tb_fee_ratio_info = self.get_tb_fee_ratio_info("tb_fee_ratio_info")
        self.tb_trade_info = self.get_tb_trade_info("tb_trade_info")
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
            result_dict[investor_id][instrument_id][direction]['account_id'] = 0
            result_dict[investor_id][instrument_id][direction]['contract_id'] = 0
            result_dict[investor_id][instrument_id][direction]['create_time'] = '0'
            result_dict[investor_id][instrument_id][direction]['update_time'] = '0'
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
            if order_local_i_d > 0:
                order_local_i_d_list.append(order_local_i_d)
            if order_sys_id > 0:
                order_sys_id_list.append(order_sys_id)

        if len(self.duplicates(order_sys_id_list)) != 0:
            print("order_sys_id重复！请确认！")
        if len(self.duplicates(order_local_i_d_list)) != 0:
            print("order_sys_id重复！请确认！")
        return result_dict

    def duplicates(self, list_):
        list_set = set(list_)

        try:
            min_num = min(list_)
            max_num = max(list_)
            print("最小的订单号：", min_num)
            print("最大的订单号：", max_num)
            complete_set = set(range(min_num, max_num + 1))
            missing_set = set(list(complete_set - list_set))
            if len(missing_set) != 0:
                print("缺失的订单数量：", len(missing_set))
                print("缺失的订单号：", sorted(missing_set))
        except Exception as e:
            print(e)

        for item in list_set:
            list_.remove(item)
        duplicates = list_
        if len(duplicates) != 0:
            print("重复的订单号：", duplicates)

        return duplicates

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


class cal_counter_data(object):
    def __init__(self, origin_data, cal_data, counter_data):
        self.origin_data = origin_data
        self.cal_data = cal_data
        self.counter_data = counter_data
        # cla_data orderinfo初值赋为 counter orderinfo；遍历订单过程更新对应订单的手续费、保证金、成交量
        # 后面最好对需要计算的键值都赋一个0，用于标注是否计算过
        '''
        TODO:对拷贝数据得到的字典中需要计算的值赋初值-1，用于标注是否计算过 @吴麒
        '''
        self.cal_tb_account_funds_info__available()
        self.cal_data.tb_order_info = copy.deepcopy(self.counter_data.tb_order_info)    # 需要计算的值赋初值-1
        self.order_info_traversal()

    def order_info_traversal(self):
        """
        遍历order_info，跟进订单状态对账户持仓、资金进行计算；
        考虑将开仓、平仓各自封装一个函数；
        """
        cal_count = 0
        # print("遍历order_info，跟进订单状态对账户持仓、资金进行计算")
        for investor_id in self.counter_data.tb_order_info.keys():
            for order_ref in self.counter_data.tb_order_info[investor_id].keys():
                # print(self.counter_data.tb_order_info[investor_id].keys())
                # continue
                '''
                需要分方向、开平仓处理:
                1、开仓：冻结保证金、手续费、可用资金
                2、平仓：可用持仓、
                '''
                limit_price = self.counter_data.tb_order_info[investor_id][order_ref]['limit_price']
                volume_total_original = self.counter_data.tb_order_info[investor_id][order_ref]['volume_total_original']
                volume_traded = self.counter_data.tb_order_info[investor_id][order_ref]['volume_traded']
                volume_frozen = volume_total_original - volume_traded
                direction = self.counter_data.tb_order_info[investor_id][order_ref]['direction']
                instrument_id = self.counter_data.tb_order_info[investor_id][order_ref]['instrument_id']
                order_local_i_d = self.counter_data.tb_order_info[investor_id][order_ref]['order_local_i_d']
                offset_flag = self.counter_data.tb_order_info[investor_id][order_ref]['offset_flag']
                # if order_local_i_d < 0:
                #     continue
                cal_count += 1
                if self.counter_data.tb_order_info[investor_id][order_ref]['offset_flag'] == '0':  # 开仓 对应方向持仓增加
                    if self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] in ['1', '2']:
                        # 柜台已报 交易所已报：手续费 保证金 增加 ； 可用资金减少；
                        margin_frozen = round_(self.cal_tb_order_info__margin(limit_price, volume_frozen, direction, instrument_id, investor_id), 3)
                        fee_frozen = round_(self.cal_tb_order_info__fee(limit_price, volume_frozen, instrument_id, investor_id,offset_flag), 3)
                        # cal_data订单冻结保证金、手续费更新
                        self.cal_data.tb_order_info[investor_id][order_ref]['margin'] = margin_frozen
                        self.cal_data.tb_order_info[investor_id][order_ref]['fee'] = fee_frozen
                        self.cal_data.tb_account_funds_info[investor_id]['available'] -= margin_frozen + fee_frozen
                    elif self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] in ['3', '4', '6']:
                        # 成交、部分成交、部分成交后撤单（6）  需要遍历成交记录明细：手续费 保证金 持仓 增加 ； 可用资金减少； 持仓盈亏变化
                        volume_traded_count = 0
                        try:  # 状态为'6' 的情况下可能没有成交记录
                            for order_local_i_d_ in self.counter_data.tb_trade_info[investor_id][order_local_i_d].keys():
                                volume_traded = self.counter_data.tb_trade_info[investor_id][order_local_i_d][order_local_i_d_]['volume']
                                volume_traded_count += volume_traded
                                self.update_open_tread_data(order_local_i_d, order_local_i_d_, investor_id, instrument_id, direction, volume_traded, offset_flag)
                        except KeyError as e:
                            # print("未成交直接撤单订单：", self.counter_data.tb_order_info[investor_id][order_local_i_d])
                            # print(e)
                            pass

                        if self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] == '6':
                            volume_cancel_count = volume_frozen
                        else:
                            volume_cancel_count = 0

                        if self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] == '3':
                            volume_frozen = volume_total_original - volume_traded_count
                            margin_frozen = round_(self.cal_tb_order_info__margin(limit_price, volume_frozen, direction, instrument_id, investor_id), 3)
                            fee_frozen = round_(self.cal_tb_order_info__fee(limit_price, volume_frozen, instrument_id, investor_id,offset_flag), 3)
                            self.cal_data.tb_order_info[investor_id][order_ref]['margin'] = margin_frozen
                            self.cal_data.tb_order_info[investor_id][order_ref]['fee'] = fee_frozen
                            self.cal_data.tb_account_funds_info[investor_id]['available'] -= margin_frozen + fee_frozen

                        # 更新订单相关信息
                        self.cal_data.tb_order_info[investor_id][order_ref]['volume_traded'] = volume_traded_count
                        self.cal_data.tb_order_info[investor_id][order_ref]['volume_cancel'] = volume_cancel_count

                    elif self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] in ['5', '7']:
                        # 柜台撤单 废单 不处理
                        pass
                    else:
                        print("订单状态错误")

                elif self.counter_data.tb_order_info[investor_id][order_ref]['offset_flag'] in ['3', '4']:  # 平今 平昨
                    # 平仓方向要跟订单方向相反
                    if direction == '0':
                        direction_ = '1'
                    elif direction == '1':
                        direction_ = '0'
                    # 区分一下平今、平昨
                    # 持仓更新另写
                    if self.counter_data.tb_order_info[investor_id][order_ref]['offset_flag'] in ['3']:
                        position_key_frozen = 'position_frozen'
                        position_key = 'position'
                        margin_key = 'margin'
                    elif self.counter_data.tb_order_info[investor_id][order_ref]['offset_flag'] in ['4']:
                        position_key_frozen = 'y_d_position_frozen'
                        position_key = 'y_d_position'
                        margin_key = 'y_d_margin'
                    else:
                        print('平今平昨平仓方向错误!')

                    if self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] in ['1', '2']:
                        # 柜台已报 交易所已报：冻结持仓/昨仓 增加 ； 可用持仓减少； 订单冻结手续费增加，可用资金减少；
                        # 先不管同时平今昨的情况
                        # free_frozen 只保留三位小数,四舍五入
                        fee_frozen = round_(self.cal_tb_order_info__fee(limit_price, volume_frozen, instrument_id, investor_id,offset_flag), 3)
                        self.cal_data.tb_order_info[investor_id][order_ref]['fee'] = fee_frozen
                        self.cal_data.tb_account_funds_info[investor_id]['available'] -= fee_frozen
                        self.cal_data.tb_account_position[investor_id][instrument_id][direction_][position_key_frozen] += volume_frozen

                    elif self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] in ['3', '4', '6']:
                        # 成交、部分成交、部分成交后撤单（6）  需要遍历成交记录明细：持仓/昨仓 减少 ； 可用资金增加； 持仓盈亏变化，手续费增加 冻结保证金不变
                        volume_traded_ = 0
                        self.cal_data.tb_account_position[investor_id][instrument_id][direction_][position_key_frozen] += volume_total_original
                        try:  # 状态为'6' 的情况下可能没有成交记录
                            for order_local_i_d_ in self.counter_data.tb_trade_info[investor_id][order_local_i_d].keys():
                                volume_traded = self.counter_data.tb_trade_info[investor_id][order_local_i_d][order_local_i_d_]['volume']
                                self.update_close_tread_data(order_local_i_d, order_local_i_d_, investor_id, instrument_id, direction_, volume_traded, offset_flag,margin_key,position_key,position_key_frozen)
                                volume_traded_ += volume_traded
                        except Exception as e:
                            # if self.counter_data.tb_order_info[investor_id][order_local_i_d]['order_local_i_d'] < 0:
                            #     print("其他柜台订单:", self.counter_data.tb_order_info[investor_id][order_local_i_d])
                            # else:
                            #     print("未成交直接撤单订单：", self.counter_data.tb_order_info[investor_id][order_local_i_d])
                            # print(e)
                            pass

                        self.cal_data.tb_order_info[investor_id][order_ref]['volume_traded'] = volume_traded_
                        self.cal_data.tb_order_info[investor_id][order_ref]['volume_cancel'] = volume_total_original - volume_traded_

                    elif self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] in ['5', '7']:
                        # 柜台撤单 废单 不处理
                        pass

                elif self.counter_data.tb_order_info[investor_id][order_ref]['offset_flag'] in ['1', '2']:  # 平仓 强平
                    '''
                    平仓量小于昨仓：只平昨仓
                    平仓量等于昨仓：只平昨仓
                    平仓量大于昨仓，小于全部持仓：全部昨仓+剩余数量今仓
                    平仓量等于全部持仓：全部昨仓+全部今仓
                    平仓量大于全部持仓：平仓失败
                    可以中间做个判断，当平仓量大于昨仓量时，加个成交量计数 做个成交量判断，超出昨仓量部分用平今：修改 offset_flag,margin_key,position_key,position_key_frozen
                    '''
                    # 平仓方向要跟订单方向相反
                    if direction == '0':
                        direction_ = '1'
                    elif direction == '1':
                        direction_ = '0'
                    try:
                        max_y_d_position = self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['y_d_position']
                    except KeyError:
                        max_y_d_position = 0
                    if volume_total_original <= max_y_d_position:
                        # 只平昨仓
                        volume_y_d = volume_total_original
                        volume_t_d = 0
                    else:
                        # 全部昨仓+剩余数量今仓
                        volume_y_d = max_y_d_position
                        volume_t_d = volume_total_original - max_y_d_position

                    if self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] in ['1', '2']:
                        # 柜台已报 交易所已报：冻结持仓/昨仓 增加 ； 可用持仓减少； 订单冻结手续费增加，可用资金减少；
                        # 先不管同时平今昨的情况
                        # free_frozen 只保留三位小数,四舍五入
                        # 平昨仓部分
                        fee_frozen = round_(self.cal_tb_order_info__fee(limit_price, volume_y_d, instrument_id, investor_id, '4'), 3)
                        # 平今仓部分
                        fee_frozen += round_(self.cal_tb_order_info__fee(limit_price, volume_t_d, instrument_id, investor_id, '3'), 3)
                        self.cal_data.tb_order_info[investor_id][order_ref]['fee'] = fee_frozen
                        self.cal_data.tb_account_funds_info[investor_id]['available'] -= fee_frozen
                        self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['y_d_position_frozen'] += volume_y_d
                        self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['position_frozen'] += volume_t_d

                    elif self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] in ['3', '4', '6']:
                        # 成交、部分成交、部分成交后撤单（6）  需要遍历成交记录明细：持仓/昨仓 减少 ； 可用资金增加； 持仓盈亏变化，手续费增加 冻结保证金不变
                        offset_flag = '4'
                        volume_traded_ = 0
                        if volume_traded > max_y_d_position:
                            volume_traded_yd = max_y_d_position
                            volume_traded_td = volume_traded - max_y_d_position
                            self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['y_d_position_frozen'] += volume_traded_yd
                            self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['position_frozen'] += volume_traded_td
                        else:
                            self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['y_d_position_frozen'] += volume_traded
                        try:  # 状态为'6' 的情况下可能没有成交记录
                            for order_local_i_d_ in self.counter_data.tb_trade_info[investor_id][order_local_i_d].keys():
                                volume_traded = self.counter_data.tb_trade_info[investor_id][order_local_i_d][order_local_i_d_]['volume']
                                volume_traded_ += volume_traded
                                if volume_traded > max_y_d_position:
                                    volume_traded_yd = max_y_d_position
                                    volume_traded_td = volume_traded - max_y_d_position
                                    self.update_close_tread_data(order_local_i_d, order_local_i_d_, investor_id, instrument_id, direction_, volume_traded_yd, offset_flag, 'y_d_margin','y_d_position','y_d_position_frozen')
                                    self.update_close_tread_data(order_local_i_d, order_local_i_d_, investor_id, instrument_id, direction_, volume_traded_td, '3', 'margin','position','position_frozen')
                                    volume_traded = volume_traded_yd
                                else:
                                    self.update_close_tread_data(order_local_i_d, order_local_i_d_, investor_id, instrument_id, direction_, volume_traded, offset_flag,'y_d_margin','y_d_position','y_d_position_frozen')
                                max_y_d_position -= volume_traded
                        except Exception as e:
                            # if self.counter_data.tb_order_info[investor_id][order_local_i_d]['order_local_i_d'] < 0:
                            #     print("其他柜台订单:", self.counter_data.tb_order_info[investor_id][order_local_i_d])
                            # else:
                            #     print("未成交直接撤单订单：", self.counter_data.tb_order_info[investor_id][order_local_i_d])
                            # print(e)
                            pass
                        self.cal_data.tb_order_info[investor_id][order_ref]['volume_traded'] = volume_traded_
                        self.cal_data.tb_order_info[investor_id][order_ref]['volume_cancel'] = volume_total_original - volume_traded_
                elif self.counter_data.tb_order_info[investor_id][order_ref]['order_status'] in ['5', '7']:
                    # 柜台撤单 废单 不处理
                    pass
                else:
                    print("订单状态错误")
        print('总有效订单数量：', cal_count)

    def cal_tb_account_funds_info__available(self):
        for investor_id in self.cal_data.tb_account_funds_info.keys():
            # 减去出金 加上入金
            self.cal_data.tb_account_funds_info[investor_id]['available'] += self.counter_data.tb_account_funds_info[investor_id]['deposit'] - self.counter_data.tb_account_funds_info[investor_id]['withdraw']

    def cal_tb_order_info__margin(self, limit_price, volume, direction, instrument_id, investor_id):
        """
        订单冻结保证金、账户保证金函数一样，入参的量价不一样
        冻结保证金，跟订单走，先按报单量冻结:数量*价格*合约乘数*保证金率
        需要 判断方向
        买: 报单价*合约数量乘数*报单数量*多头保证金率
        卖: 报单价*合约数量乘数*报单数量*空头保证金率
        :return:冻结保证金
        """
        if direction == '0':
            margin = limit_price * volume * self.counter_data.tb_instrument_info[instrument_id]['volume_multiple'] * \
                     self.counter_data.tb_fee_ratio_info[investor_id][instrument_id]['long_margin_ratio_by_money']
            # 打印所有参与计算参数的值出来：
        elif direction == '1':
            margin = limit_price * volume * self.counter_data.tb_instrument_info[instrument_id]['volume_multiple'] * \
                     self.counter_data.tb_fee_ratio_info[investor_id][instrument_id]['short_margin_ratio_by_money']
        else:
            margin = -1
        return margin

    def cal_tb_order_info__fee(self, limit_price, volume, instrument_id, investor_id, offset_flag):
        """
        订单冻结手续费、账户手续费函数一样，入参的量价不一样
        冻结手续费，跟订单走，先按报单量冻结，成交后再解冻
        有费率，则，手数算一遍+费率算一遍
        没有费率，则，手数算一遍（如果费率直接配了0，是不是就无所谓了）
        费率算一遍：手数*手续费率(按手数)*合约乘数*报单价 + 手数*手续费率
        :return:冻结手续费
        """
        if offset_flag == '0':  # 开仓
            fee = volume * self.counter_data.tb_fee_ratio_info[investor_id][instrument_id]['open_ratio_by_volume'] + \
                  limit_price * volume * self.counter_data.tb_fee_ratio_info[investor_id][instrument_id][
                      'open_ratio_by_money'] * self.counter_data.tb_instrument_info[instrument_id]['volume_multiple']
        elif offset_flag == '3':  # 平今
            fee = volume * self.counter_data.tb_fee_ratio_info[investor_id][instrument_id]['close_t_d_ratio_by_volume'] + \
                  limit_price * volume * self.counter_data.tb_fee_ratio_info[investor_id][instrument_id]['close_t_d_ratio_by_money'] * self.counter_data.tb_instrument_info[instrument_id]['volume_multiple']
        elif offset_flag in ['1','4']:    # 平昨
            fee = volume * self.counter_data.tb_fee_ratio_info[investor_id][instrument_id]['close_ratio_by_volume'] + \
                  limit_price * volume * self.counter_data.tb_fee_ratio_info[investor_id][instrument_id]['close_ratio_by_money'] * self.counter_data.tb_instrument_info[instrument_id]['volume_multiple']
        else:
            print("平仓费率计算平仓方向错误！")
            fee = -1
        return fee

    # @param volume 成交数量
    # @param price  成交价
    # @param instrument_id 合约代码
    # @param investor_id 账户号、投资者账号
    # @param direction 买卖方向
    # @param offset_flag 开仓标志
    # @return value 本次盈亏
    def cal_current_profit(self, volume,price,instrument_id,investor_id,direction,offset_flag,avg_price):
        # 开仓
        # 本次开仓盈亏 = 持仓盈亏 + （合约昨结算价 - 持仓均价） * 合约数量乘数 * 成交数量
        # 平仓
        # 本次平仓盈亏 = 平仓盈亏 + （成交价 - 持仓均价） * 合约数量乘数 * 成交数量
        current_profit = 0
        try:
            if offset_flag == '0':  # 开仓
                current_profit = (self.origin_data.tb_account_position[investor_id][instrument_id][direction]['posi_profit'] + (self.counter_data.tb_instrument_info[instrument_id]['pre_settlement_price'] - avg_price)
                        * self.origin_data.tb_instrument_info[instrument_id]['volume_multiple'] * volume)
                # print("open investor_id = ",investor_id,"posi_profit = ",self.origin_data.tb_account_position[investor_id][instrument_id][direction]['posi_profit'], "pre_settlement_price = ",self.counter_data.tb_instrument_info[instrument_id]['pre_settlement_price'],
                #      "avg_price = ", avg_price, "volume_multiple = ", self.origin_data.tb_instrument_info[instrument_id]['volume_multiple'], "volume = ",volume, "current_profit = ",current_profit)
                self.origin_data.tb_account_position[investor_id][instrument_id][direction]['posi_profit'] = current_profit
            elif offset_flag in ['1', '2', '3', '4']:  # 平仓
                current_profit = (self.origin_data.tb_account_position[investor_id][instrument_id][direction]['close_profit'] + (price - avg_price)
                        * self.origin_data.tb_instrument_info[instrument_id]['volume_multiple'] * volume)
                # print("close investor_id = ",investor_id,"instrument_id = ",instrument_id,"direction = ",direction,"close_profit = ",
                #      self.origin_data.tb_account_position[investor_id][instrument_id][direction]['close_profit'],
                #      "price = ",
                #      price,
                #      "avg_price = ", avg_price, "volume_multiple = ",
                #      self.origin_data.tb_instrument_info[instrument_id]['volume_multiple'], "volume = ", volume,
                #      "current_profit = ", current_profit)
                self.origin_data.tb_account_position[investor_id][instrument_id][direction]['close_profit'] = current_profit
        except KeyError as e:
            if offset_flag == '0':  # 开仓
                self.origin_data.tb_account_position[investor_id][instrument_id][direction]['posi_profit'] = 0
        return current_profit

    # @param volume 成交数量
    # @param price  成交价
    # @param instrument_id 合约代码
    # @param investor_id 账户号、投资者账号
    # @param direction 买卖方向
    # @return value 持仓均价
    def cal_avg_price(self, volume, price, instrument_id, investor_id, direction,offset_flag):
        # 持仓均价 = （原持仓均价 * 原总持仓数量 + 成交数量 * 成交价）/ (原总持仓数量 + 成交数量)
        # 开仓时需要计算、平仓时直接取
        avg_price = price
        try:
            if offset_flag == '0':  # 开仓
                avg_price = ((self.origin_data.tb_account_position[investor_id][instrument_id][direction]['total_average_price'] *
                          self.origin_data.tb_account_position[investor_id][instrument_id][direction]['total_position'] + volume * price) /
                         (self.origin_data.tb_account_position[investor_id][instrument_id][direction]['total_position'] + volume))
            elif offset_flag in ['1', '2', '3', '4']:  # 平仓
                avg_price = self.cal_data.tb_account_position[investor_id][instrument_id][direction]['total_average_price']
            self.origin_data.tb_account_position[investor_id][instrument_id][direction][
                'total_average_price'] = avg_price
            self.origin_data.tb_account_position[investor_id][instrument_id][direction]['total_position'] += volume
        except KeyError as e:
            if investor_id not in self.origin_data.tb_account_position:
                self.origin_data.tb_account_position[investor_id] = {}
            if instrument_id not in self.origin_data.tb_account_position[investor_id]:
                self.origin_data.tb_account_position[investor_id][instrument_id] = {}
            if direction not in self.origin_data.tb_account_position[investor_id][instrument_id]:
                self.origin_data.tb_account_position[investor_id][instrument_id][direction] = {}
            self.origin_data.tb_account_position[investor_id][instrument_id][direction]['total_average_price'] = avg_price
            # self.origin_data.tb_account_position[investor_id][instrument_id][direction]['total_position'] = volume
        return avg_price

    def update_open_tread_data(self, order_local_i_d, order_local_i_d_, investor_id, instrument_id, direction, volume_traded, offset_flag):
        if investor_id not in self.origin_data.tb_account_position:
            self.origin_data.tb_account_position[investor_id] = {}
        if instrument_id not in self.origin_data.tb_account_position[investor_id]:
            self.origin_data.tb_account_position[investor_id][instrument_id] = {}
        if direction not in self.origin_data.tb_account_position[investor_id][instrument_id]:
            self.origin_data.tb_account_position[investor_id][instrument_id][direction] = {
                'id': 0, 'account_id': 0, 'investor_id': '0', 'contract_id': 0,
                'instrument_id': '0', 'exchange': '0', 'direction': '0', 'hedge_flag': '0',
                'y_d_margin': 0, 'margin': 0, 'posi_profit': 0, 'close_profit': 0,
                'close_volume': 0, 'total_average_price': 0, 'y_d_average_price': 0,
                'average_price': 0, 'open_volume': 0, 'total_position': 0,
                'position_frozen': 0, 'y_d_position_frozen': 0, 'y_d_position': 0,
                'position': 0, 'create_time': '0', 'update_time': '0'}
        limit_price_traded = self.counter_data.tb_trade_info[investor_id][order_local_i_d][order_local_i_d_]['price']
        margin_traded = round_(self.cal_tb_order_info__margin(limit_price_traded, volume_traded, direction, instrument_id, investor_id), 3)
        fee_traded = round_(self.cal_tb_order_info__fee(limit_price_traded, volume_traded, instrument_id, investor_id, offset_flag), 3)
        # 持仓均价
        avg_price = round_(self.cal_avg_price(volume_traded, limit_price_traded, instrument_id, investor_id, direction,offset_flag),3)
        # 本次盈亏
        current_profit = round_(self.cal_current_profit(volume_traded, limit_price_traded, instrument_id, investor_id, direction,offset_flag, avg_price), 3)
        # 开仓成交：保证金+、手续费+、可用资金-
        self.cal_data.tb_account_funds_info[investor_id]['fee'] += fee_traded
        self.cal_data.tb_account_funds_info[investor_id]['margin'] += margin_traded
        self.cal_data.tb_account_funds_info[investor_id]['available'] -= margin_traded + fee_traded
        self.cal_data.tb_account_funds_info[investor_id]['benefits'] += current_profit - fee_traded
        # print("benefits = ", self.cal_data.tb_account_funds_info[investor_id]['benefits'], "current_profit = ", current_profit, "deal_free = ", deal_free)
        self.cal_data.tb_account_funds_info[investor_id]['position_profit'] += current_profit
        # if investor_id == '60076155':
        #     print(self.cal_data.tb_account_funds_info[investor_id]['available'],self.cal_data.tb_account_funds_info[investor_id]['fee'],self.cal_data.tb_account_funds_info[investor_id]['margin'])

        # 持仓更新
        try:  # 有旧持仓可以直接+
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['open_volume'] += volume_traded
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['total_position'] += volume_traded
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['position'] += volume_traded
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['margin'] += margin_traded
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['posi_profit'] = current_profit
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['total_average_price'] = avg_price
            self.origin_data.tb_account_position[investor_id][instrument_id][direction]['total_position'] += volume_traded
        except KeyError as e:  # 没有旧持仓，需要新建
            if investor_id not in self.cal_data.tb_account_position:
                self.cal_data.tb_account_position[investor_id] = {}
            if instrument_id not in self.cal_data.tb_account_position[investor_id]:
                self.cal_data.tb_account_position[investor_id][instrument_id] = {}
            if direction not in self.cal_data.tb_account_position[investor_id][instrument_id]:
                self.cal_data.tb_account_position[investor_id][instrument_id][direction] = {
                    'id': 0, 'account_id': 0, 'investor_id': investor_id, 'contract_id': 0,
                    'instrument_id': instrument_id, 'exchange': 'SHFE', 'direction': direction, 'hedge_flag': '1',
                    'y_d_margin': 0.0, 'margin': 0, 'posi_profit': 0, 'close_profit': 0.0,
                    'close_volume': 0, 'total_average_price': 0, 'y_d_average_price': 0.0,
                    'average_price': 0.0, 'open_volume': 0, 'total_position': 0,
                    'position_frozen': 0, 'y_d_position_frozen': 0, 'y_d_position': 0,
                    'position': 0, 'create_time': '0', 'update_time': '0'}
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['open_volume'] = volume_traded
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['position'] = volume_traded
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['total_position'] = volume_traded
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['margin'] = margin_traded
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['posi_profit'] = current_profit
            self.cal_data.tb_account_position[investor_id][instrument_id][direction]['total_average_price'] = avg_price
            self.origin_data.tb_account_position[investor_id][instrument_id][direction]['total_position'] = volume_traded

    def update_close_tread_data(self, order_local_i_d, order_local_i_d_, investor_id, instrument_id, direction_, volume_traded, offset_flag,margin_key,position_key,position_key_frozen):
        limit_price_traded = self.counter_data.tb_trade_info[investor_id][order_local_i_d][order_local_i_d_]['price']
        margin_traded = round_(self.cal_tb_order_info__margin(limit_price_traded, volume_traded, direction_, instrument_id, investor_id),3)
        fee_traded = round_(self.cal_tb_order_info__fee(limit_price_traded, volume_traded, instrument_id, investor_id, offset_flag), 3)

        # 平仓不更新持仓均价，直接使用 total_average_price 字段
        avg_price = self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['total_average_price']
        # 本次盈亏
        current_profit = round_(self.cal_current_profit(volume_traded, limit_price_traded, instrument_id, investor_id, direction_,offset_flag, avg_price), 3)
        # 平仓成交：保证金-、手续费+、可用资金+
        self.cal_data.tb_account_funds_info[investor_id]['fee'] += fee_traded
        self.cal_data.tb_account_funds_info[investor_id]['margin'] -= margin_traded
        self.cal_data.tb_account_funds_info[investor_id]['available'] += margin_traded - fee_traded
        self.cal_data.tb_account_position[investor_id][instrument_id][direction_][margin_key] -= margin_traded
        self.cal_data.tb_account_funds_info[investor_id]['benefits'] += (current_profit - fee_traded)
        self.cal_data.tb_account_funds_info[investor_id]['close_profit'] += current_profit
        # 持仓更新
        self.cal_data.tb_account_position[investor_id][instrument_id][direction_][position_key] -= volume_traded
        self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['close_volume'] += volume_traded
        self.cal_data.tb_account_position[investor_id][instrument_id][direction_][position_key_frozen] -= volume_traded
        self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['close_profit'] = current_profit
        self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['total_average_price'] = avg_price
        self.cal_data.tb_account_position[investor_id][instrument_id][direction_]['total_position'] -= volume_traded

        # 持仓均价计算使用
        self.origin_data.tb_account_position[investor_id][instrument_id][direction_]['total_position'] -= volume_traded


if __name__ == '__main__':
    '''
    测试数据：
    原始数据：138 total_base
    单笔开仓：138 t1
    单笔开仓后平仓：138 t2
    大量订单：138 t3
    '''
    # total_data = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='1010_total_data_01')
    # total_data_aft = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='1010_total_data_aft_01')

    # total_data = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='1012_oringin_data')
    # total_data_aft = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='1012_conter_data')

    # total_data = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='total_base')   # 原始数据
    # total_data_aft = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='t1')  # 单笔开仓
    # total_data_aft = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='t2')  # 单笔开仓后平仓
    # total_data_aft = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='t3')  # 大量订单

    # total_data = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='hqt_fut_lbs')
    # total_data_aft = get_origin_data(host='171.17.104.16', port=3306, user='root', password='123456', db='hqt_fut_lbs')

    total_data = get_origin_data(host='192.168.1.138', port=3306, user='root', password='a*963.-+', db='hqt_fut_18')
    total_data_aft = get_origin_data(host='171.17.104.16', port=3306, user='root', password='123456', db='hqt_fut_18')

    total_data_cal = copy.deepcopy(total_data)

    cal = cal_counter_data(total_data, total_data_cal, total_data_aft)
    # result = cal.compare_data()
    # if result:
    #     print("计算对比后资券数据一致")
    # else:
    #     print("计算对比后数据不一致")

    # 比较结果写入文件
    write_dict_data(cal.cal_data, "cal_data")
    write_dict_data(cal.counter_data, "counter_data")
    write_dict_data(cal.origin_data, "origin_data")

    # 调用Beyond Compare比较文件
    if platform.system() == 'Windows':
        try:
            compare_files("cal_data_tb_account_funds_info_log.csv", "counter_data_tb_account_funds_info_log.csv")
            compare_files("cal_data_tb_account_position_log.csv", "counter_data_tb_account_position_log.csv")
            # compare_files("cal_data_tb_account_instrument_rates_log.csv", "counter_data_tb_account_instrument_rates_log.csv")
            # compare_files("cal_data_tb_instrument_info_log.csv", "counter_data_tb_instrument_info_log.csv")
            compare_files("cal_data_tb_order_info_log.csv", "counter_data_tb_order_info_log.csv")
        except Exception as error:
            print(error)
