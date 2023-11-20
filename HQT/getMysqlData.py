#!/usr/local/bin/python3
# -*- coding: utf-8 -*-
import pymysql
import copy
import pandas as pd
import pymysql.cursors


class get_apidemo_data(object):
    """
    先做单个账户的，后续再考虑多账户（多CSV文件同时）的处理
    订单量对比后续考虑其他的方式
    """
    def __init__(self, host, port, db, user, password):
        # 数据库信息
        self.host = host
        self.port = port
        self.db = db
        self.user = user
        self.password = password
        # 连接数据库
        self.conn = pymysql.connect(host = self.host , port = self.port , db = self.db , user = self.user ,
                                    password = self.password ,
                                    charset = 'utf8')
        self.cursor = self.conn.cursor()

        # tb_cli_insert_rep 下单请求表
        self.select_tb_cli_insert_rep = ["tb_cli_insert_req","1"]
        self.select_tb_cli_insert_rep_len = self.get_demo_data_len(self.select_tb_cli_insert_rep[0])
        self.tb_cli_insert_req = self.get_demo_data(self.select_tb_cli_insert_rep,self.select_tb_cli_insert_rep_len)
        self.tb_cli_insert_req_cal =  copy.deepcopy(self.tb_cli_insert_req)

        # tb_cli_insert_resp 下单应答表
        self.select_tb_cli_insert_resp = ["tb_cli_insert_resp", "1"]
        self.select_tb_cli_insert_resp_len = self.get_demo_data_len(self.select_tb_cli_insert_resp[0])
        self.tb_cli_insert_resp = self.get_demo_data(self.select_tb_cli_insert_resp,self.select_tb_cli_insert_resp_len)
        self.tb_cli_insert_resp_cal =  copy.deepcopy(self.tb_cli_insert_resp)

        # tb_cli_order_rtn 订单回报表
        self.select_tb_cli_order_rtn = ["tb_cli_order_rtn","1"]
        self.select_tb_cli_order_rtn_len = self.get_demo_data_len(self.select_tb_cli_order_rtn[0])
        self.tb_cli_order_rtn = self.get_demo_data(self.select_tb_cli_order_rtn,self.select_tb_cli_order_rtn_len)
        self.tb_cli_order_rtn_cal =  copy.deepcopy(self.tb_cli_order_rtn)

        # tb_cli_insert_trade 成交回报表
        self.select_tb_cli_insert_trade = ["tb_cli_insert_trade","1"]
        self.select_tb_cli_insert_trade_len = self.get_demo_data_len(self.select_tb_cli_insert_trade[0])
        self.tb_cli_insert_trade = self.get_demo_data(self.select_tb_cli_insert_trade,self.select_tb_cli_insert_trade_len)
        self.tb_cli_insert_trade_cal =  copy.deepcopy(self.tb_cli_insert_trade)

        # tb_cli_cancel_req 撤单请求表
        self.select_tb_cli_cancel_req = ["tb_cli_cancel_req","1"]
        self.select_tb_cli_cancel_req_len = self.get_demo_data_len(self.select_tb_cli_cancel_req[0])
        self.tb_cli_cancel_req = self.get_demo_data(self.select_tb_cli_cancel_req,self.select_tb_cli_cancel_req_len)
        self.tb_cli_cancel_req_cal =  copy.deepcopy(self.tb_cli_cancel_req)

        # tb_cli_cancel_resp 撤单应答表
        self.select_tb_cli_cancel_resp = ["tb_cli_cancel_resp","1"]
        self.select_tb_cli_cancel_resp_len = self.get_demo_data_len(self.select_tb_cli_cancel_resp[0])
        self.tb_cli_cancel_resp = self.get_demo_data(self.select_tb_cli_cancel_resp,self.select_tb_cli_cancel_resp_len)
        self.tb_cli_cancel_resp_cal =  copy.deepcopy(self.tb_cli_cancel_resp)

        # tb_cli_time_stamp 时间戳表，暂时不用
        self.select_tb_cli_time_stamp = ["tb_cli_time_stamp","1"]
        self.select_tb_cli_time_stamp_len = self.get_demo_data_len(self.select_tb_cli_time_stamp[0])
        self.tb_cli_time_stamp = self.get_demo_data(self.select_tb_cli_time_stamp,self.select_tb_cli_time_stamp_len)
        self.tb_cli_time_stamp_cal =  copy.deepcopy(self.tb_cli_time_stamp)

        # tb_account_funds_info 账户资金表
        self.select_tb_account_funds_info = ["tb_account_funds_info","2"]
        self.select_tb_account_funds_info_len = self.get_demo_data_len(self.select_tb_account_funds_info[0])
        self.tb_account_funds_info = self.get_demo_data(self.select_tb_account_funds_info,1)
        self.tb_account_funds_info_aft = self.get_demo_data(self.select_tb_account_funds_info,0)
        self.tb_account_funds_info_cal =  copy.deepcopy(self.tb_account_funds_info)

        # tb_account_instrument_rates 账户合约费率表
        self.select_tb_account_instrument_rates = ["tb_account_instrument_rates","2"]
        self.select_tb_account_instrument_rates_len = self.get_demo_data_len(self.select_tb_account_instrument_rates[0])
        self.tb_account_instrument_rates = self.get_demo_data(self.select_tb_account_instrument_rates,0)
        self.tb_account_instrument_rates_aft = self.get_demo_data(self.select_tb_account_instrument_rates,1)
        self.tb_account_instrument_rates_cal =  copy.deepcopy(self.tb_account_instrument_rates)

        # tb_account_position 用户持仓表
        self.select_tb_account_position = ["tb_account_position","2"]
        self.select_tb_account_position_len = self.get_demo_data_len(self.select_tb_account_position[0])
        # self.tb_account_position = self.get_demo_data(self.select_tb_account_position,0)
        # self.tb_account_position_aft = self.get_demo_data(self.select_tb_account_position,1)
        self.tb_account_position = self.get_data_for_account_position(self.select_tb_account_position[0],
                                                                    self.select_tb_account_position_len)
        self.tb_account_position_cal = copy.deepcopy(self.tb_account_position)


        # tb_cancel_order_info 撤单记录表
        self.select_tb_cancel_order_info = ["tb_cancel_order_info","2"]
        self.select_tb_cancel_order_info_len = self.get_demo_data_len(self.select_tb_cancel_order_info[0])
        self.tb_cancel_order_info = self.get_demo_data(self.select_tb_cancel_order_info,0)
        self.tb_cancel_order_info_aft = self.get_demo_data(self.select_tb_cancel_order_info,1)
        self.tb_cancel_order_info_cal =  copy.deepcopy(self.tb_cancel_order_info)

        # tb_fee_ratio_info 费率表
        self.select_tb_fee_ratio_info = ["tb_fee_ratio_info","2"]
        self.select_tb_fee_ratio_info_len = self.get_demo_data_len(self.select_tb_fee_ratio_info[0])
        # self.tb_fee_ratio_info = self.get_demo_data(self.select_tb_fee_ratio_info,0)
        # self.tb_fee_ratio_info_aft = self.get_demo_data(self.select_tb_fee_ratio_info,1)
        self.tb_fee_ratio_info = self.get_data_for_fee_ratio(self.select_tb_fee_ratio_info[0], self.select_tb_fee_ratio_info_len)
        self.tb_fee_ratio_info_cal =  copy.deepcopy(self.tb_fee_ratio_info)

        # tb_instrument_info 合约表
        #get_data_for_instrument_info
        self.select_tb_instrument_info = ["tb_instrument_info","2"]
        self.select_tb_instrument_info_len = self.get_demo_data_len(self.select_tb_instrument_info[0])
        # self.tb_instrument_info = self.get_demo_data(self.select_tb_instrument_info,0)
        # self.tb_instrument_info_aft = self.get_demo_data(self.select_tb_instrument_info,1)
        self.tb_instrument_info = self.get_data_for_instrument_info(self.select_tb_instrument_info[0],
                                                             self.select_tb_instrument_info_len)
        self.tb_instrument_info_cal =  copy.deepcopy(self.tb_instrument_info)

        # tb_order_info 委托表
        self.select_tb_order_info = ["tb_order_info","2"]
        self.select_tb_order_info_len = self.get_demo_data_len(self.select_tb_order_info[0])
        self.tb_order_info = self.get_demo_data(self.select_tb_order_info,0)
        self.tb_order_info_aft = self.get_demo_data(self.select_tb_order_info,1)
        self.tb_order_info_cal =  copy.deepcopy(self.tb_order_info)

        # tb_trade_info 成交记录表
        self.select_tb_trade_info = ["tb_trade_info","2"]
        self.select_tb_trade_info_len = self.get_demo_data_len(self.select_tb_trade_info[0])
        self.tb_trade_info = self.get_demo_data(self.select_tb_trade_info,0)
        self.tb_trade_info_aft = self.get_demo_data(self.select_tb_trade_info,1)
        self.tb_trade_info_cal =  copy.deepcopy(self.tb_trade_info)

        # tb_trading_code_info交易编码表
        self.select_tb_trading_code_info = ['tb_trading_code_info', '2']
        self.select_tb_trading_code_info_len = self.get_demo_data_len(self.select_tb_trading_code_info[0])
        self.tb_trading_code_info = self.get_demo_data(self.select_tb_trading_code_info,0 )
        self.tb_trading_code_info_aft = self.get_demo_data(self.select_tb_trading_code_info,1)
        self.tb_trading_code_info_cal =  copy.deepcopy(self.tb_trading_code_info)

    def get_demo_data(self, table_msg, index):   # 获取表的数据
        sql_message = "select * from {} ORDER BY id DESC LIMIT {}".format(table_msg[0], table_msg[1])
        # print("sql_message:",sql_message)
        # print("lens:",lens)
        try:
            if  table_msg[1] == '1':
                df = pd.read_sql(sql_message , self.conn).to_dict(orient = 'records')[ 0 ]
            else:
                if index == 0:
                    df = pd.read_sql(sql_message , self.conn).to_dict(orient = 'records')[ 0 ]
                else:
                    df = pd.read_sql(sql_message, self.conn).to_dict(orient='records')[ 1 ]
        except Exception as e:
            df = pd.read_sql(sql_message , self.conn)
            if df.empty:
                df.loc[0] = ['None'] * len(df.columns)
                df = df.to_dict(orient = 'records')[ 0 ]
        # print("df:",df)
        return df

    def get_data_for_fee_ratio(self, table_name, lens):
        ret = {}
        #ret[table_name] = {}
        sql_message = "select * from {}".format(table_name)
        #print(sql_message)
        try:
            for i in range(lens):
                df = pd.read_sql(sql_message, self.conn).to_dict(orient = "records")[i]
                parts = str(df['ratio_group_name']).split("|")
                innerKey = parts[1]
                ret[innerKey] = df
        except Exception as e:
            # print('Exception ERROR:',e)
            df = pd.read_sql(sql_message, self.conn)
            if df.empty:
                df.loc[0] = ['None'] * len(df.columns)
                ret = df.to_dict(orient='records')[0]
        #print(ret)
        return ret

    def get_data_for_instrument_info(self, table_name, lens):
        ret = {}
        #ret[table_name] = {}
        sql_message = "select * from {}".format(table_name)
        #print(sql_message)
        try:
            for i in range(lens):
                df = pd.read_sql(sql_message, self.conn).to_dict(orient = "records")[i]
                #parts = str(df['ratio_group_name']).split("|")
                innerKey = df['instrument_id']
                ret[innerKey] = df
        except Exception as e:
            # print('Exception ERROR:',e)
            df = pd.read_sql(sql_message, self.conn)
            if df.empty:
                df.loc[0] = ['None'] * len(df.columns)
                ret = df.to_dict(orient='records')[0]
        #print(ret)
        return ret

    def get_data_for_account_position(self, table_name, lens):
        ret = {}
        sql_message = "select * from {} ORDER BY id ASC".format(table_name)
        try:
            for i in range(lens): # 遍历表长度数据
                '''
                ret[innerKey][directionKey][item_][0] 为初始值
                ret[innerKey][directionKey][item_][1] 为报单后值
                在新开仓ret[innerKey][directionKey][item_]需要将ret[innerKey][directionKey][item_][0]赋值为0
                全部平仓后再次查询还能看到持仓，持仓为0
                '''
                df = pd.read_sql(sql_message, self.conn).to_dict(orient="records")[i]
                innerKey = df['instrument_id']
                directionKey = df['direction']
                if innerKey not in ret.keys():
                    ret[innerKey] = {}
                try:
                    for item_ in df.keys():
                        ret[ innerKey ][ directionKey ][ item_ ] = [ ret[ innerKey ][ directionKey ][ item_ ] ]
                        ret[innerKey][directionKey][item_].append(df[item_])
                except Exception as e:
                    ret[innerKey][directionKey] = {}
                    ret[innerKey][directionKey] = df
        except Exception as e:
            # print('Exception ERROR:',e)
            df = pd.read_sql(sql_message, self.conn)
            if df.empty:
                df.loc[0] = ['None'] * len(df.columns)
                ret = df.to_dict(orient='records')[0]
        # 遍历所有innerKey、directionKey、item_，将新开仓ret[innerKey][directionKey][item_][0]赋值为0
        for innerKey in ret.keys():
            for directionKey in ret[innerKey].keys():
                if isinstance(ret[innerKey][directionKey]['id'], list):
                    pass
                else:
                    for item_ in ret[innerKey][directionKey].keys():
                        if isinstance(ret[innerKey][directionKey][item_], str):
                            ret[innerKey][directionKey][item_] = [ret[innerKey][directionKey][item_], ret[innerKey][directionKey][item_]]
                        else:
                            ret[innerKey][directionKey][item_] = [0, ret[innerKey][directionKey][item_]]
        # print(ret)
        return ret

    def get_demo_data_len(self, table_name):# 获取表的长度
        sql_message = "select count(*) from {}".format(table_name)
        #print(sql_message)
        try:
            df = pd.read_sql(sql_message , self.conn).iloc[0, 0]
        except Exception as e:
            # print('Exception ERROR:',e)
            df = 2
        #print(df)
        return df

    def close(self):
        self.cursor.close()
        self.conn.close()

    def return_all_dict(self):
        """
        返回数据为双层字典形式，第一层键为数据表名，第二层键为字段名
        :return:
        """
        self.close()
        return {key: value for key , value in self.__dict__.items() if key not in ['conn' , 'cursor' , 'host' , 'port' , 'user' , 'password' , 'db' ,
                                                                                    'select_tb_cli_insert_rep' ,
                                                                                    'select_tb_cli_insert_rep_len' ,
                                                                                    'select_tb_cli_insert_resp' ,
                                                                                    'select_tb_cli_insert_resp_len' ,
                                                                                    'select_tb_cli_order_rtn' ,
                                                                                    'select_tb_cli_order_rtn_len' ,
                                                                                    'select_tb_cli_insert_trade' ,
                                                                                    'select_tb_cli_insert_trade_len' ,
                                                                                    'select_tb_cli_cancel_req' ,
                                                                                    'select_tb_cli_cancel_req_len' ,
                                                                                    'select_tb_cli_cancel_resp' ,
                                                                                    'select_tb_cli_cancel_resp_len' ,
                                                                                    'select_tb_account_funds_info' ,
                                                                                    'select_tb_account_funds_info_len' ,
                                                                                    'select_tb_cli_time_stamp' ,
                                                                                    'select_tb_cli_time_stamp_len' ,
                                                                                    'select_tb_cli_time_stamp' ,
                                                                                    'select_tb_cli_time_stamp_len' ,
                                                                                    'select_tb_account_position' ,
                                                                                    'select_tb_account_position_len' ,
                                                                                    'select_tb_instrument_info' ,
                                                                                    'select_tb_instrument_info_len' ,
                                                                                    'select_tb_order_info' ,
                                                                                    'select_tb_order_info_len' ,
                                                                                    'select_qry_trade' ,
                                                                                    'select_qry_trade_len' ,
                                                                                    'select_qry_tradecode' ,
                                                                                    'select_qry_tradecode_len' ,
                                                                                    'select_tb_cancel_order_info' ,
                                                                                    'select_tb_cancel_order_info_len' ,
                                                                                    'select_tb_fee_ratio_info',
                                                                                    'select_tb_fee_ratio_info_len',
                                                                                    'select_tb_trade_info',
                                                                                    'select_tb_trade_info_len',
                                                                                    'select_tb_trading_code_info',
                                                                                    'select_tb_trading_code_info_len',]}


class cal_apidemo_data(object):
    def __init__(self, own_dict, opp_dict):
        self.own_data = own_dict
        self.opp_data = opp_dict
        # 按需计算
        self.cal_tb_account_funds_info__margin()
        self.cal_tb_account_funds_info__fee()
        self.cal_tb_account_funds_info__available()
        self.cal_tb_cli_order_rtn__volume_total()
        self.cal_tb_cli_order_rtn__volume_traded()
        self.cal_tb_account_position__position()
        self.cal_tb_account_position__yd_position()
        self.cal_tb_account_position__position_frozen()
        self.cal_tb_account_position__total_position()
        self.cal_tb_account_position__open_volume()
        self.cal_tb_account_position__total_average_price()
        self.cal_tb_account_position__close_volume()
        self.cal_tb_account_position__close_profit()
        self.cal_tb_account_position__posi_profit()
        self.cal_tb_account_position__margin()
        self.cal_tb_order_info__fee()
        self.cal_tb_order_info__margin()

    # 字段计算
    def cal_tb_order_info__margin(self):
        """
        冻结保证金，跟订单走，先按报单量冻结:数量*价格*合约乘数*保证金率
        需要 判断方向
        买: 报单价*合约数量乘数*报单数量*多头保证金率
        卖: 报单价*合约数量乘数*报单数量*空头保证金率
        :return:
        """
        if self.own_data['tb_cli_insert_req']['direction'] == '0':
            self.own_data['tb_order_info_cal']['margin'] = self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['long_margin_ratio_by_money'] * self.own_data['tb_cli_insert_req']['volume_total_original']
        elif self.own_data['tb_cli_insert_req']['direction'] == '1':
            self.own_data['tb_order_info_cal']['margin'] = self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['short_margin_ratio_by_money'] * self.own_data['tb_cli_insert_req']['volume_total_original']
        # 其他方向则先赋空值
        # else:
        #     self.own_data['tb_order_info_cal']['margin'] = None

    def cal_tb_order_info__fee(self):
        """
        冻结手续费，跟订单走，先按报单量冻结，成交后再解冻
        有费率，则，手数算一遍+费率算一遍
        没有费率，则，手数算一遍（如果费率直接配了0，是不是就无所谓了）
        费率算一遍：价格*手数*手续费率*合约乘数
        :return:
        """
        self.own_data['tb_order_info_cal']['fee'] = self.own_data['tb_cli_insert_req']['volume_total_original'] * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['fee_ratio_by_volume'] + self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_cli_insert_req']['volume_total_original'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['open_ratio_by_volume']
        pass

    def cal_tb_account_position__margin(self):
        """
        持仓保证金，成交、撤单都会解冻保证金
        需要 判断方向
        买: 报单价*合约数量乘数*本次成交数量*多头保证金率
        卖: 报单价*合约数量乘数*本次成交数量*空头保证金率
        :return:
        """
        order_direction = self.own_data['tb_order_info']['direction']
        order_instrument_id = self.own_data['tb_order_info']['instrument_id']
        if order_direction != 'None' and order_instrument_id != 'None':
            if self.own_data['tb_account_position'] != {}:
                if self.own_data['tb_cli_insert_req']['direction'] == '0':
                    self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['margin'] = self.own_data['tb_account_position'][order_instrument_id][order_direction]['margin'][0] + self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['long_margin_ratio_by_money'] * self.own_data['tb_trade_info']['volume']
                elif self.own_data['tb_cli_insert_req']['direction'] == '1':
                    self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['margin'] = self.own_data['tb_account_position'][order_instrument_id][order_direction]['margin'][0] + self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['short_margin_ratio_by_money'] * self.own_data['tb_trade_info']['volume']
                # 其他方向则先赋空值
                else:
                    self.own_data['tb_account_position_cal']['margin'] = None
                pass

    def cal_tb_account_position__posi_profit(self):
        """
        持仓盈亏 = ( 昨结算价 - 总持仓均价 ) * 合约乘数 * 持仓数量
        TODO 今结算价???
        :return:
        """
        order_direction = self.own_data['tb_order_info']['direction']
        order_instrument_id = self.own_data['tb_order_info']['instrument_id']
        if order_direction != 'None' and order_instrument_id != 'None':
            if self.own_data['tb_account_position'] != {}:
                self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['posi_profit'] = ( self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['pre_settlement_price'] - self.own_data['tb_account_position'][order_instrument_id][order_direction]['total_average_price'][0] ) * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * self.own_data['tb_account_position'][order_instrument_id][order_direction]['total_position'][0]
                pass

    def cal_tb_account_position__close_profit(self):
        """
        平仓盈亏 = ( 平仓成交价 - 总持仓均价 ) * 合约乘数 * 平仓成交数量
        TODO 平仓成交价和平仓成交数量？？？
        :return:
        """
        order_direction = self.own_data['tb_order_info']['direction']
        order_instrument_id = self.own_data['tb_order_info']['instrument_id']
        if order_direction != 'None' and order_instrument_id != 'None':
            if self.own_data['tb_account_position'] != {}:
                self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['close_profit'] = ( self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 - self.own_data['tb_account_position'][order_instrument_id][order_direction]['total_average_price'][0] ) * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * self.own_data['tb_cli_insert_req']['volume_total_original']
                pass

    def cal_tb_account_position__close_volume(self):
        """
        平仓数量
        需要判断开仓标志
        买平: 卖方向持仓数量减少，平仓数量增加
        卖平: 买方向持仓数量减少，平仓数量增加
        :return:
        """
        order_direction = self.own_data['tb_order_info']['direction']
        order_instrument_id = self.own_data['tb_order_info']['instrument_id']
        if order_direction != 'None' and order_instrument_id != 'None':
            if self.own_data['tb_account_position'] != {}:
                if self.own_data['tb_order_info']['direction'] == '0':
                    if self.own_data['tb_order_info']['offset_flag'] == '1':
                        self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['close_volume'] = self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['close_volume'] + self.own_data['tb_order_info']['volume_traded']
                elif self.own_data['tb_order_info']['direction'] == '1':
                    if self.own_data['tb_order_info']['offset_flag'] == '1':
                        self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['close_volume'] = self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['close_volume'] + self.own_data['tb_order_info']['volume_traded']
                pass

    def cal_tb_account_position__total_average_price(self):
        """
        总持仓均价 = （总持仓均价(pre) * 持仓数量(pre) + 成交价(current) * 成交数量(current)） / (持仓数量(pre) + 成交数量(current))
        :return:
        """
        order_direction = self.own_data['tb_order_info']['direction']
        order_instrument_id = self.own_data['tb_order_info']['instrument_id']
        if order_direction != 'None' and order_instrument_id != 'None':
            if self.own_data['tb_account_position'] != {}:
                self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['total_average_price'] = ( self.own_data['tb_account_position'][order_instrument_id][order_direction]['total_average_price'][0] * self.own_data['tb_account_position'][order_instrument_id][order_direction]['total_position'][0] +
                                                                                        self.own_data['tb_trade_info']['price'] * self.own_data['tb_trade_info']['volume'] ) / ( self.own_data['tb_account_position'][order_instrument_id][order_direction]['total_position'][0] + self.own_data['tb_trade_info']['volume'] )
                pass

    def cal_tb_account_position__open_volume(self):
        """
        开仓成交数量
        需要判断开仓标志
        :return:
        """
        order_direction = self.own_data['tb_order_info']['direction']
        order_instrument_id = self.own_data['tb_order_info']['instrument_id']
        if order_direction != 'None' and order_instrument_id != 'None':
            if self.own_data['tb_account_position'] != {}:
                if self.own_data['tb_order_info']['offset_flag'] == '0':
                    self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['open_volume'] = self.own_data['tb_account_position'][order_instrument_id][order_direction]['open_volume'][0] + self.own_data['tb_order_info']['volume_traded']
                pass

    def cal_tb_account_position__total_position(self):
        """
        总持仓数量
        需要判断开仓标志
        开仓: 总持仓数量 = 总持仓数量 + 成交数量
        平仓: 总持仓数量 = 总持仓数量 - 成交数量
        :return:
        """
        order_direction = self.own_data['tb_order_info']['direction']
        order_instrument_id = self.own_data['tb_order_info']['instrument_id']
        if order_direction != 'None' and order_instrument_id != 'None':
            if self.own_data['tb_account_position'] != {}:
                    if self.own_data['tb_order_info']['offset_flag'] == '0':
                        self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['total_position'] = self.own_data['tb_account_position'][order_instrument_id][order_direction]['total_position'][0] + self.own_data['tb_order_info']['volume_traded']
                    elif self.own_data['tb_order_info']['offset_flag'] == '1':
                        self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['total_position'] = self.own_data['tb_account_position'][order_instrument_id][order_direction]['total_position'][0] - self.own_data['tb_order_info']['volume_traded']
                    pass


    def cal_tb_account_position__position_frozen(self):
        """
        今持仓冻结数量
        需要判断指令标志 平今、平仓
        平今: 今仓冻结数量 = 今仓冻结数量 + 报单数量
        平仓: 平仓剩余数量 = 报单数量 - 昨仓 + 昨仓冻结   昨仓不足时 今仓冻结数量 = 今仓冻结数量 + 平昨剩余数量
        :return:
        """
        order_direction = self.own_data['tb_order_info']['direction']
        order_instrument_id = self.own_data['tb_order_info']['instrument_id']
        if order_direction != 'None' and order_instrument_id != 'None':
            if self.own_data['tb_cli_insert_req']['offset_flag'] == '3':
                self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['position_frozen'] = self.own_data['tb_account_position'][order_instrument_id][order_direction]['position_frozen'][0] + self.own_data['tb_cli_insert_req']['volune_total_original']
            elif self.own_data['tb_cli_insert_req']['offset_flag'] == '1':
                avg_residue = self.own_data['tb_cli_insert_req']['volune_total_original'] - self.own_data['tb_account_position'][order_instrument_id][order_direction]['y_d_position'][0] + self.own_data['tb_account_position'][order_instrument_id][order_direction]['y_d_position_frozen'][0]
                self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['position_frozen'] = self.own_data['tb_account_position'][order_instrument_id][order_direction]['position_frozen'][0] + avg_residue if avg_residue > 0 else 0
            pass

    def cal_tb_account_position__yd_position(self):
        """
        昨持仓冻结数量
        需要判断指令标志 平昨、平仓
        平昨: 昨仓冻结数量 = 昨仓冻结数量 + 报单数量
        平仓: 平仓剩余数量 = 报单数量 - 昨仓 + 昨仓冻结   昨仓不足时 昨仓冻结数量 = 报单数量 - 平昨剩余数量 昨仓充足时 昨仓冻结数量 = 昨仓冻结数量 + 报单数量
        :return:
        """
        order_direction = self.own_data['tb_order_info']['direction']
        order_instrument_id = self.own_data['tb_order_info']['instrument_id']
        if order_direction != 'None' and order_instrument_id != 'None':
            if self.own_data['tb_cli_insert_req']['offset_flag'] == '4':
                self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['y_d_position_frozen'] = self.own_data['tb_account_position'][order_instrument_id][order_direction]['y_d_position_frozen'][0] + self.own_data['tb_cli_insert_req']['volune_total_original']
            elif self.own_data['tb_cli_insert_req']['offset_flag'] == '1':
                avg_residue = self.own_data['tb_cli_insert_req']['volune_total_original'] - self.own_data['tb_account_position'][order_instrument_id][order_direction]['y_d_position'][0] + self.own_data['tb_account_position'][order_instrument_id][order_direction]['y_d_position_frozen'][0]
                self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['position_frozen'] = self.own_data['tb_cli_insert_req']['volune_total_original'] - avg_residue if avg_residue > 0 else self.own_data['tb_account_position'][order_instrument_id][order_direction]['y_d_position_frozen'][0] + self.own_data['tb_cli_insert_req']['volune_total_original']
            pass

    def cal_tb_account_position__position(self):
        """
        今持仓数量
        今仓数量 = 今仓数量 + 成交数量
        :return:
        """
        if self.own_data['tb_order_info']['offset_flag'] != 'None':
            if self.own_data['tb_order_info']['offset_flag'] == '0':
                order_direction = self.own_data['tb_order_info']['direction']
                order_instrument_id = self.own_data['tb_order_info']['instrument_id']
                if self.own_data['tb_account_position'] != {}:
                        self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['position'] = self.own_data['tb_account_position'][order_instrument_id][order_direction]['position'][0] + self.own_data['tb_order_info']['volume_traded']
                        pass

    def cal_tb_cli_order_rtn__volume_traded(self):
        """
        成交数量
        成交数量 = 回报成交数量 - 订单原成交数量
        :return:
        """
        if self.own_data['tb_cli_order_rtn']['volume_traded'] != 'None' and self.own_data['tb_order_info'][
            'volume_traded'] != 'None':
            self.own_data['tb_cli_order_rtn_cal']['volume_traded'] = self.own_data['tb_cli_order_rtn']['volume_traded'] - self.own_data['tb_order_info']['volume_traded']
            pass

    def cal_tb_cli_order_rtn__volume_total(self):
        """
        剩余数量
        剩余数量 = 报单数量 -成交数量
        :return:
        """
        if self.own_data['tb_cli_order_rtn']['volume_total_original'] != 'None' and self.own_data['tb_cli_order_rtn']['volume_traded'] != 'None':
            self.own_data['tb_cli_order_rtn_cal']['volume_total'] = self.own_data['tb_cli_order_rtn']['volume_total_original'] - self.own_data['tb_cli_order_rtn']['volume_traded']
            pass

    def cal_tb_account_funds_info__available(self):
        """
        可用资金
        :return:
        """
        # 完全成交
        if "tb_trade_info" in self.own_data and self.own_data['tb_trade_info'].get('volume') != 'None':
            if int(self.own_data['tb_trade_info']['volume']) > 0:
                # 开仓
                if self.own_data['tb_trade_info']['offset_flag'] == '0':
                    # 成交保证金
                    deal_margin = 0
                    if self.own_data['tb_trade_info']['direction'] == '0':
                        deal_margin = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][
                            self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                      self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][
                                          self.own_data['tb_cli_insert_req']['instrument_id']][
                                          'long_margin_ratio_by_money']
                    elif self.own_data['tb_trade_info']['direction'] == '1':
                        deal_margin = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][
                            self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                      self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][
                                          self.own_data['tb_cli_insert_req']['instrument_id']][
                                          'short_margin_ratio_by_money']
                    # 成交手续费
                    deal_fee_open = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][
                        self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                    self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][
                                        self.own_data['tb_cli_insert_req']['instrument_id']]['open_ratio_by_money'] + \
                                    self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][
                                        self.own_data['tb_cli_insert_req']['instrument_id']]['open_ratio_by_volume']
                    self.own_data['tb_account_funds_info_cal']['available'] = self.own_data['tb_account_funds_info'][
                        'available'] - deal_margin - deal_fee_open
                # 平仓
                elif self.own_data['tb_trade_info']['offset_flag'] == '1':
                    # 成交释放金
                    deal_margin = 0
                    if self.own_data['tb_trade_info']['direction'] == '0':
                        deal_margin = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][
                            self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                      self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][
                                          self.own_data['tb_cli_insert_req']['instrument_id']][
                                          'long_margin_ratio_by_money']
                    elif self.own_data['tb_trade_info']['direction'] == '1':
                        deal_margin = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][
                            self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                      self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][
                                          self.own_data['tb_cli_insert_req']['instrument_id']][
                                          'short_margin_ratio_by_money']
                    # 成交手续费
                    deal_fee_close = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][
                        self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                     self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][
                                         self.own_data['tb_cli_insert_req']['instrument_id']]['close_ratio_by_money'] + \
                                     self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][
                                         self.own_data['tb_cli_insert_req']['instrument_id']]['close_ratio_by_volume']
                    self.own_data['tb_account_funds_info_cal']['available'] = self.own_data['tb_account_funds_info'][
                                                                                  'available'] + deal_margin - deal_fee_close
            # 未成交
            else:
                #self.own_data['tb_account_funds_info_cal']['available'] = self.own_data['tb_account_funds_info']['available'] - self.own_data['tb_order_info']['margin'] - self.own_data['tb_order_info']['fee']
                # 开仓
                if self.own_data['tb_cli_insert_req']['offset_flag'] == '0':
                    # 保证金
                    deal_margin = 0
                    if self.own_data['tb_cli_insert_req']['direction'] == '0':
                        deal_margin = self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_instrument_info'][
                            self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                      self.own_data['tb_cli_insert_req']['volume_total_original'] * self.own_data['tb_fee_ratio_info'][
                                          self.own_data['tb_cli_insert_req']['instrument_id']][
                                          'long_margin_ratio_by_money']
                    elif self.own_data['tb_cli_insert_req']['direction'] == '1':
                        deal_margin = self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_instrument_info'][
                            self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                      self.own_data['tb_cli_insert_req']['volume_total_original'] * self.own_data['tb_fee_ratio_info'][
                                          self.own_data['tb_cli_insert_req']['instrument_id']][
                                          'short_margin_ratio_by_money']
                    # 手续费
                    deal_fee_open = self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_instrument_info'][
                        self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                    self.own_data['tb_cli_insert_req']['volume_total_original'] * self.own_data['tb_fee_ratio_info'][
                                        self.own_data['tb_cli_insert_req']['instrument_id']]['open_ratio_by_money'] + \
                                    self.own_data['tb_cli_insert_req']['volume_total_original'] * self.own_data['tb_fee_ratio_info'][
                                        self.own_data['tb_cli_insert_req']['instrument_id']]['open_ratio_by_volume']

                    self.own_data['tb_account_funds_info_cal']['available'] = self.own_data['tb_account_funds_info'][
                                                                                  'available'] - deal_margin - deal_fee_open
                # 平仓
                elif self.own_data['tb_cli_insert_req']['offset_flag'] == '1':
                    # 成交释放金
                    deal_margin = 0
                    if self.own_data['tb_cli_insert_req']['direction'] == '0':
                        deal_margin = self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_instrument_info'][
                            self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                      self.own_data['tb_cli_insert_req']['volume_total_original'] * self.own_data['tb_fee_ratio_info'][
                                          self.own_data['tb_cli_insert_req']['instrument_id']][
                                          'long_margin_ratio_by_money']
                    elif self.own_data['tb_cli_insert_req']['direction'] == '1':
                        deal_margin = self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_instrument_info'][
                            self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                      self.own_data['tb_cli_insert_req']['volume_total_original'] * self.own_data['tb_fee_ratio_info'][
                                          self.own_data['tb_cli_insert_req']['instrument_id']][
                                          'short_margin_ratio_by_money']
                    # 成交手续费
                    deal_fee_close = self.own_data['tb_cli_insert_req']['limit_price'] * 0.0001 * self.own_data['tb_instrument_info'][
                        self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                                     self.own_data['tb_cli_insert_req']['volume_total_original'] * self.own_data['tb_fee_ratio_info'][
                                         self.own_data['tb_cli_insert_req']['instrument_id']]['close_ratio_by_money'] + \
                                     self.own_data['tb_cli_insert_req']['volume_total_original'] * self.own_data['tb_fee_ratio_info'][
                                         self.own_data['tb_cli_insert_req']['instrument_id']]['close_ratio_by_volume']
                    self.own_data['tb_account_funds_info_cal']['available'] = self.own_data['tb_account_funds_info'][
                                                                                  'available'] + deal_margin - deal_fee_close
            pass

    def cal_tb_account_funds_info__fee(self):
        """
        账户手续费，成交了才有手续费更新，手续费只会增加
        有一个成交订单则会计算一次手续费
        账户手续费 = 账户手续费 + 成交手续费
        判断开仓标志
        开仓: 成交手续费 = （按价格）成交价 * 合约数量乘数 * 成交数量 * 开仓手续费率 + （按手数）成交数量 * 开仓手续费（每手）
        平仓: 成交手续费 = （按价格）成交价 * 合约数量乘数 * 成交数量 * 平仓（平今）手续费率 + （按手数）成交数量 * 平仓（平今）手续费（每手）
        :return:
        """
        if self.own_data['tb_trade_info']['offset_flag'] == '0':
            deal_fee_open = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] *         \
                            self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['open_ratio_by_money'] + \
                            self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['open_ratio_by_volume']
            self.own_data['tb_account_funds_info_cal']['fee'] = self.own_data['tb_account_funds_info']['fee'] + deal_fee_open
        elif self.own_data['tb_trade_info']['offset_flag'] == '1':
            deal_fee_close = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] *            \
                             self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['close_ratio_by_money'] + \
                             self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['close_ratio_by_volume']
            self.own_data['tb_account_funds_info_cal']['fee'] = self.own_data['tb_account_funds_info']['fee'] + deal_fee_close
        pass

    def cal_tb_account_funds_info__margin(self):
        """
        账户保证金，成交后才有保证金更新，会增加、减少，不会为负数
        有一个成交订单则会计算一次保证金
        判断开仓标志
        开仓: 判断买卖方向
        买: 成交保证金 = 成交价 * 合约数量乘数 * 成交数量 * 多头保证金率
        卖: 成交保证金 = 成交价 * 合约数量乘数 * 成交数量 * 空头保证金率
        账户保证金 = 账户保证金 + 成交保证金
        平仓: 判断买卖方向
        买: 成交保证金 = 成交价 * 合约数量乘数 * 成交数量 * 多头保证金率
        卖: 成交保证金 = 成交价 * 合约数量乘数 * 成交数量 * 空头保证金率
        账户保证金 = 账户保证金 - 成交保证金
        :return:
        """
        if self.own_data['tb_trade_info']['offset_flag'] == '0':
            deal_margin = 0
            if self.own_data['tb_trade_info']['direction'] == '0':
                deal_margin = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                              self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['long_margin_ratio_by_money']
            elif self.own_data['tb_trade_info']['direction'] == '1':
                deal_margin = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                              self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['short_margin_ratio_by_money']
            self.own_data['tb_account_funds_info_cal']['margin'] = self.own_data['tb_account_funds_info']['margin'] + deal_margin
        elif self.own_data['tb_trade_info']['offset_flag'] == '1':
            deal_margin = 0
            if self.own_data['tb_trade_info']['direction'] == '0':
                deal_margin = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                              self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['long_margin_ratio_by_money']
            elif self.own_data['tb_trade_info']['direction'] == '1':
                deal_margin = self.own_data['tb_trade_info']['price'] * self.own_data['tb_instrument_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['volume_multiple'] * \
                              self.own_data['tb_trade_info']['volume'] * self.own_data['tb_fee_ratio_info'][self.own_data['tb_cli_insert_req']['instrument_id']]['short_margin_ratio_by_money']
            self.own_data['tb_account_funds_info_cal']['margin'] = self.own_data['tb_account_funds_info']['margin'] - deal_margin
        pass

    def compare_cal_data(self):
        """
        用来对比apidemo和程序验算数据是否一致
        即 own_data 的后缀_aft数据和后缀_cal数据是否一致
        :return:
        """
        order_direction = self.own_data['tb_order_info_cal']['direction']
        order_instrument_id = self.own_data['tb_order_info_cal']['instrument_id']
        if order_direction != 'None' and order_instrument_id != 'None':
            if self.own_data['tb_account_position'] != {}:
                position_list = self.own_data['tb_account_position_cal'][order_instrument_id][order_direction]['total_position']
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('字段类型' , '初始数据' , '计算数据' , '柜台数据'))
                # 持仓的查询函数更新，一堆验算要重写
                compare_flag = True

                # 可用资金
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('可用资金' ,
                                                                 self.own_data['tb_account_funds_info']['available'] ,
                                                                 self.own_data['tb_account_funds_info_cal']['available'] ,
                                                                 self.own_data['tb_account_funds_info_aft']['available']))
                if self.own_data['tb_account_funds_info_cal']['available'] != self.own_data['tb_account_funds_info_aft']['available']:
                    compare_flag = False
                    print("可用资金不一致")
                # 账户手续费
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('账户手续费' ,
                                                                 self.own_data['tb_account_funds_info']['fee'] ,
                                                                 self.own_data['tb_account_funds_info_cal']['fee'] ,
                                                                 self.own_data['tb_account_funds_info_aft']['fee']))
                if self.own_data['tb_account_funds_info_cal']['fee'] != self.own_data['tb_account_funds_info_aft']['fee']:
                    compare_flag = False
                    print("账户手续费不一致")
                # 账户保证金
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('账户保证金' ,
                                                                 self.own_data['tb_account_funds_info']['margin'] ,
                                                                 self.own_data['tb_account_funds_info_cal']['margin'] ,
                                                                 self.own_data['tb_account_funds_info_aft']['margin']))
                if self.own_data['tb_account_funds_info_cal']['margin'] != self.own_data['tb_account_funds_info_aft']['margin']:
                    compare_flag = False
                    print("账户保证金不一致")
                # 报单后持仓
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('报单后持仓' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['position'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ]['position'] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ]['position'][1]))
                if isinstance(position_list, list):
                    if self.own_data['tb_order_info_cal']['volume_traded'] != abs(position_list[0] - position_list[1]):
                        compare_flag = False
                        print("报单后持仓数量不一致")
                else:
                    if self.own_data['tb_account_position_cal'][order_instrument_id ][ order_direction ]['position'] != position_list:
                        compare_flag = False
                        print("报单后持仓数量不一致")
                # 解冻保证金
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('持仓保证金' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['margin'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ]['margin'] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ]['margin'][1]))
                if self.own_data['tb_account_position_cal'][ order_instrument_id ][ order_direction ]['margin'] != self.own_data['tb_account_position'][ order_instrument_id ][ order_direction ]['margin'][1]:
                    compare_flag = False
                    print("持仓保证金不一致")
                # 持仓盈亏
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('持仓盈亏' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['posi_profit'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ]['posi_profit'] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ]['posi_profit'][1]))
                if self.own_data['tb_account_position_cal'][ order_instrument_id ][ order_direction ]['posi_profit'] != self.own_data['tb_account_position'][ order_instrument_id ][ order_direction ]['posi_profit'][1]:
                    compare_flag = False
                    print("持仓盈亏不一致")
                # 平仓盈亏
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('平仓盈亏' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['close_profit'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'close_profit'] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'close_profit'][1]))
                if self.own_data['tb_account_position_cal'][ order_instrument_id ][ order_direction ]['close_profit'] != self.own_data['tb_account_position'][ order_instrument_id ][ order_direction ]['close_profit'][1]:
                    compare_flag = False
                    print("平仓盈亏不一致")
                # 平仓数量
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('平仓数量' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['close_volume'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'close_volume'][1] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'close_volume'][1]))
                if self.own_data['tb_account_position_cal'][ order_instrument_id ][ order_direction ]['close_volume'][1] != self.own_data['tb_account_position'][ order_instrument_id ][ order_direction ]['close_volume'][1]:
                    compare_flag = False
                    print("平仓数量不一致")
                # 总持仓均价
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('总持仓均价' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['total_average_price'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'total_average_price'] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'total_average_price'][1]))
                if self.own_data['tb_account_position_cal'][ order_instrument_id ][ order_direction ]['total_average_price'] != self.own_data['tb_account_position'][ order_instrument_id ][ order_direction ]['total_average_price'][1]:
                    compare_flag = False
                    print("总持仓均价不一致")
                # 开仓成交数量
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('开仓成交数量' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['open_volume'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ]['open_volume'] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ]['open_volume'][1]))
                if self.own_data['tb_account_position_cal'][ order_instrument_id ][ order_direction ]['open_volume'] != self.own_data['tb_account_position'][ order_instrument_id ][ order_direction ]['open_volume'][1]:
                    compare_flag = False
                    print("开仓成交数量不一致")
                # 总持仓数量
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('总持仓数量' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['total_position'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'total_position'] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'total_position'][1]))
                if self.own_data['tb_account_position_cal'][ order_instrument_id ][ order_direction ]['total_position'] != self.own_data['tb_account_position'][ order_instrument_id ][ order_direction ]['total_position'][1]:
                    compare_flag = False
                    print("总持仓数量不一致")
                # 今持仓冻结数量
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('今持仓冻结数量' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['position_frozen'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'position_frozen'][1] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'position_frozen'][1]))
                if self.own_data['tb_account_position_cal'][ order_instrument_id ][ order_direction ]['position_frozen'][1] != self.own_data['tb_account_position'][ order_instrument_id ][ order_direction ]['position_frozen'][1]:
                    compare_flag = False
                    print("今持仓冻结数量不一致")
                # 昨持仓冻结数量
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('昨持仓冻结数量' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['y_d_position_frozen'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'y_d_position_frozen'][1] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ][
                                                                     'y_d_position_frozen'][1]))
                if self.own_data['tb_account_position_cal'][ order_instrument_id ][ order_direction ]['y_d_position_frozen'][1] != self.own_data['tb_account_position'][ order_instrument_id ][ order_direction ]['y_d_position_frozen'][1]:
                    compare_flag = False
                    print("昨持仓冻结数量不一致")
                # 今持仓数量
                print('|{0:<16}|{1:<16}|{2:<16}|{3:<16}|'.format('今持仓数量' ,
                                                                 self.own_data['tb_account_position'][ order_instrument_id ][
                                                                     order_direction ]['position'][0] ,
                                                                 self.own_data['tb_account_position_cal'][
                                                                     order_instrument_id ][ order_direction ]['position'] ,
                                                                 self.own_data['tb_account_position'][
                                                                     order_instrument_id ][ order_direction ]['position'][1]))
                if self.own_data['tb_account_position_cal'][ order_instrument_id ][ order_direction ]['position'] != self.own_data['tb_account_position'][ order_instrument_id ][ order_direction ]['position'][1]:
                    compare_flag = False
                    print("今持仓数量不一致")
                return compare_flag

    def order_status(self):
        print("本方订单：" , self.own_data['tb_order_info'])
        print("对手方订单：" , self.opp_data['tb_order_info'])
        order_status_flag = True
        if self.own_data['tb_order_info']['instrument_id'] == self.opp_data['tb_order_info'][
            'instrument_id']:
            if self.own_data['tb_order_info']['direction'] != self.opp_data['tb_order_info']['direction']:
                if self.own_data['tb_order_info']['volume_total_original'] > self.opp_data['tb_order_info']['volume_total_original']:
                    if self.own_data['tb_order_info']['order_status'] != '3':  # 部分成交
                        order_status_flag = False
                else:
                    if self.own_data['tb_order_info']['order_status'] != '4':  # 全部成交
                        order_status_flag = False
            else:
                if self.own_data['tb_order_info']['order_status'] != '2':  # 已报未成交
                    order_status_flag = False
        else:
            if self.own_data['tb_order_info']['order_status'] != '2':  # 已报未成交

                order_status_flag = False
        return order_status_flag

    def compare_qry_data(self):
        """
        用来对比apidemo和柜台数据库数据是否一致
        :return:
        """
        pass


if __name__ == '__main__':
    # 公式是从开发哪里拿到的 验算只能看到取值问题和精度问题
    # 获取本方数据，后面用configparser读取配置文件
    own_data = get_apidemo_data(host='192.168.1.138',
                                port=3306,
                                user='root',
                                password='a*963.-+',
                                db='t1').return_all_dict()

    # 获取对方数据，后面用configparser读取配置文件
    opp_data = get_apidemo_data(host='192.168.1.138',
                                port=3306,
                                user='root',
                                password='a*963.-+',
                                db='t2').return_all_dict()

    own_data = get_apidemo_data(host='171.17.104.16',
                                port=3306,
                                user='root',
                                password='123456',
                                db='hqt_fut_lbs_apidemo').return_all_dict()
    #
    # # 获取对方数据，后面用configparser读取配置文件
    # opp_data = get_apidemo_data(host='171.17.104.16',
    #                             port=3306,
    #                             user='root',
    #                             password='123456',
    #                             db='hqt_fut_lbs_apidemo_02').return_all_dict()

    # own_data = get_apidemo_data(host = '171.17.106.117' ,
    #                    port = 3306 ,
    #                    user = 'root' ,
    #                    password = '123456' ,
    #                    db = 'hqt_fut_lbs_apidemo' ).return_all_dict()
    #
    # # 获取对方数据，后面用configparser读取配置文件
    # opp_data = get_apidemo_data(host = '171.17.106.117' ,
    #                    port = 3306 ,
    #                    user = 'root' ,
    #                    password = '123456' ,
    #                    db = 'hqt_fut_lbs_apidemo_02' ).return_all_dict()
    # 比对数据正确性
    cal = cal_apidemo_data(own_data, opp_data)
    # own_log = open('own_log.txt', 'w')
    # opp_log = open('opp_log.txt', 'w')
    # for key in cal.own_data.keys():
    #     opp_log.write(key + ":" + str(cal.own_data[key]) + '\n')
    # for key in cal.opp_data.keys():
    #     own_log.write(key + ":" + str(cal.opp_data[key]) + '\n')
    # own_log.close()
    # opp_log.close()
    # 规范一下输出格式
    # 先输出订单状态：
    # 本方订单：...
    # 对手方订单：...
    # 判断结果订单状态：正常、错误、未知
    # 再输出数据验算：
    # 起始数据 | 报单后数据 | 验算数据 | 验算结果
    # 比较函数
    compare_ = cal.compare_cal_data()
    if compare_:
        print("数据比对通过")
    else:
        print("数据比对不通过")

    # 订单状态比对
    order_status_ = cal.order_status()
    if order_status_:
        print("订单状态比对通过")
    else:
        print("订单状态比对不通过")
