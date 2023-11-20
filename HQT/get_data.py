# connet to mysql and get data
import pymysql
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
        self.tb_cli_insert_req_cal = self.tb_cli_insert_req

        # tb_cli_insert_resp 下单应答表
        self.select_tb_cli_insert_resp = ["tb_cli_insert_resp", "1"]
        self.select_tb_cli_insert_resp_len = self.get_demo_data_len(self.select_tb_cli_insert_resp[0])
        self.tb_cli_insert_resp = self.get_demo_data(self.select_tb_cli_insert_resp,self.select_tb_cli_insert_resp_len)
        self.tb_cli_insert_resp_cal = self.tb_cli_insert_resp

        # tb_cli_order_rtn 订单回报表
        self.select_tb_cli_order_rtn = ["tb_cli_order_rtn","1"]
        self.select_tb_cli_order_rtn_len = self.get_demo_data_len(self.select_tb_cli_order_rtn[0])
        self.tb_cli_order_rtn = self.get_demo_data(self.select_tb_cli_order_rtn,self.select_tb_cli_order_rtn_len)
        self.tb_cli_order_rtn_cal = self.tb_cli_order_rtn

        # tb_cli_insert_trade 成交回报表
        self.select_tb_cli_insert_trade = ["tb_cli_insert_trade","1"]
        self.select_tb_cli_insert_trade_len = self.get_demo_data_len(self.select_tb_cli_insert_trade[0])
        self.tb_cli_insert_trade = self.get_demo_data(self.select_tb_cli_insert_trade,self.select_tb_cli_insert_trade_len)
        self.tb_cli_insert_trade_cal = self.tb_cli_insert_trade

        # tb_cli_cancel_req 撤单请求表
        self.select_tb_cli_cancel_req = ["tb_cli_cancel_req","1"]
        self.select_tb_cli_cancel_req_len = self.get_demo_data_len(self.select_tb_cli_cancel_req[0])
        self.tb_cli_cancel_req = self.get_demo_data(self.select_tb_cli_cancel_req,self.select_tb_cli_cancel_req_len)
        self.tb_cli_cancel_req_cal = self.tb_cli_cancel_req

        # tb_cli_cancel_resp 撤单应答表
        self.select_tb_cli_cancel_resp = ["tb_cli_cancel_resp","1"]
        self.select_tb_cli_cancel_resp_len = self.get_demo_data_len(self.select_tb_cli_cancel_resp[0])
        self.tb_cli_cancel_resp = self.get_demo_data(self.select_tb_cli_cancel_resp,self.select_tb_cli_cancel_resp_len)
        self.tb_cli_cancel_resp_cal = self.tb_cli_cancel_resp

        # tb_cli_time_stamp 时间戳表，暂时不用
        self.select_tb_cli_time_stamp = ["tb_cli_time_stamp","1"]
        self.select_tb_cli_time_stamp_len = self.get_demo_data_len(self.select_tb_cli_time_stamp[0])
        self.tb_cli_time_stamp = self.get_demo_data(self.select_tb_cli_time_stamp,self.select_tb_cli_time_stamp_len)
        self.tb_cli_time_stamp_cal = self.tb_cli_time_stamp

        # tb_account_funds_info 账户资金表
        self.select_tb_account_funds_info = ["tb_account_funds_info","2"]
        self.select_tb_account_funds_info_len = self.get_demo_data_len(self.select_tb_account_funds_info[0])
        self.tb_account_funds_info = self.get_demo_data(self.select_tb_account_funds_info,self.select_tb_account_funds_info_len - 1)
        self.tb_account_funds_info_aft = self.get_demo_data(self.select_tb_account_funds_info,self.select_tb_account_funds_info_len)
        self.tb_account_funds_info_cal = self.tb_account_funds_info

        # tb_account_instrument_rates 账户合约费率表
        self.select_tb_account_instrument_rates = ["tb_account_instrument_rates","2"]
        self.select_tb_account_instrument_rates_len = self.get_demo_data_len(self.select_tb_account_instrument_rates[0])
        self.tb_account_instrument_rates = self.get_demo_data(self.select_tb_account_instrument_rates,self.select_tb_account_instrument_rates_len - 1)
        self.tb_account_instrument_rates_aft = self.get_demo_data(self.select_tb_account_instrument_rates,self.select_tb_account_instrument_rates_len)
        self.tb_account_instrument_rates_cal = self.tb_account_instrument_rates

        # tb_account_position 用户持仓表
        self.select_tb_account_position = ["tb_account_position","2"]
        self.select_tb_account_position_len = self.get_demo_data_len(self.select_tb_account_position[0])
        self.tb_account_position = self.get_demo_data(self.select_tb_account_position,self.select_tb_account_position_len - 1)
        self.tb_account_position_aft = self.get_demo_data(self.select_tb_account_position,self.select_tb_account_position_len)
        self.tb_account_position_cal = self.tb_account_position

        # tb_cancel_order_info 撤单记录表
        self.select_tb_cancel_order_info = ["tb_cancel_order_info","2"]
        self.select_tb_cancel_order_info_len = self.get_demo_data_len(self.select_tb_cancel_order_info[0])
        self.tb_cancel_order_info = self.get_demo_data(self.select_tb_cancel_order_info,self.select_tb_cancel_order_info_len - 1)
        self.tb_cancel_order_info_aft = self.get_demo_data(self.select_tb_cancel_order_info,self.select_tb_cancel_order_info_len)
        self.tb_cancel_order_info_cal = self.tb_cancel_order_info

        # tb_fee_ratio_info 费率表
        self.select_tb_fee_ratio_info = ["tb_fee_ratio_info","2"]
        self.select_tb_fee_ratio_info_len = self.get_demo_data_len(self.select_tb_fee_ratio_info[0])
        self.tb_fee_ratio_info = self.get_demo_data(self.select_tb_fee_ratio_info,self.select_tb_fee_ratio_info_len - 1)
        self.tb_fee_ratio_info_aft = self.get_demo_data(self.select_tb_fee_ratio_info,self.select_tb_fee_ratio_info_len)
        self.tb_fee_ratio_info_cal = self.tb_fee_ratio_info

        # tb_instrument_info 合约表
        self.select_tb_instrument_info = ["tb_instrument_info","2"]
        self.select_tb_instrument_info_len = self.get_demo_data_len(self.select_tb_instrument_info[0])
        self.tb_instrument_info = self.get_demo_data(self.select_tb_instrument_info,self.select_tb_instrument_info_len - 1)
        self.tb_instrument_info_aft = self.get_demo_data(self.select_tb_instrument_info,self.select_tb_instrument_info_len)
        self.tb_instrument_info_cal = self.tb_instrument_info

        # tb_order_info 委托表
        self.select_tb_order_info = ["tb_order_info","2"]
        self.select_tb_order_info_len = self.get_demo_data_len(self.select_tb_order_info[0])
        self.tb_order_info = self.get_demo_data(self.select_tb_order_info,self.select_tb_order_info_len - 1)
        self.tb_order_info_aft = self.get_demo_data(self.select_tb_order_info,self.select_tb_order_info_len)
        self.tb_order_info_cal = self.tb_order_info

        # tb_trade_info 成交记录表
        self.select_tb_trade_info = ["tb_trade_info","2"]
        self.select_tb_trade_info_len = self.get_demo_data_len(self.select_tb_trade_info[0])
        self.tb_trade_info = self.get_demo_data(self.select_tb_trade_info,self.select_tb_trade_info_len - 1)
        self.tb_trade_info_aft = self.get_demo_data(self.select_tb_trade_info,self.select_tb_trade_info_len)
        self.tb_trade_info_cal = self.tb_trade_info

        # tb_trading_code_info交易编码表
        self.select_tb_trading_code_info = ['tb_trading_code_info', '2']
        self.select_tb_trading_code_info_len = self.get_demo_data_len(self.select_tb_trading_code_info[0])
        self.tb_trading_code_info = self.get_demo_data(self.select_tb_trading_code_info,self.select_tb_trading_code_info_len - 1 )
        self.tb_trading_code_info_aft = self.get_demo_data(self.select_tb_trading_code_info,self.select_tb_trading_code_info_len)
        self.tb_trading_code_info_cal = self.tb_trading_code_info

    def get_demo_data(self, table_msg, lens):   # 获取表的数据
        sql_message = "select * from {} ORDER BY id DESC LIMIT {}".format(table_msg[0], table_msg[1])
        # print("sql_message:",sql_message)
        try:
            if  table_msg[1] == '1':
                df = pd.read_sql(sql_message , self.conn).to_dict(orient = 'records')[ 0 ]
            else:
                df = pd.read_sql(sql_message , self.conn).groupby('id').get_group(lens).to_dict(orient = 'records')[ 0 ]
        except Exception as e:
            # print('Exception ERROR:',e)
            df = pd.read_sql(sql_message , self.conn)
            if df.empty:
                df.loc[0] = ['None'] * len(df.columns)
                df = df.to_dict(orient = 'records')[ 0 ]
        # print("df:",df)
        return df

    def get_demo_data_len(self, table_name): # 获取表的长度
        sql_message = "select count(*) from {}".format(table_name)
        try:
            df = pd.read_sql(sql_message , self.conn).iloc[0, 0]
        except Exception as e:
            # print('Exception ERROR:',e)
            df = 2
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
        return {key: value for key , value in self.__dict__.items() if key not in [ 'conn' , 'cursor' , 'host' , 'port' , 'user' , 'password' , 'db' ,
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

        # self.own_data[ '' ][ '' ]
    # 状态比对
    def cal_tb_cli_order_rtn__order_status(self):
        """
        报单状态
        订单状态，通过对比两个方向的订单的量来判断是否正确：
        未成交、部分成交、全部成交、已撤单、部分撤单、全部撤单……
        :return:
        """
        pass

    # 字段计算
    def cal_tb_order_info__margin(self):
        """
        冻结保证金，跟订单走，先按报单量冻结:数量*价格*合约乘数*保证金率
        需要 判断方向
        :return:
        """
        # print("self.own_data[ 'tb_cli_insert_req' ][ 'limit_price' ]:" ,
        #       self.own_data[ 'tb_cli_insert_req' ][ 'limit_price' ])
        # print("self.own_data[ 'tb_instrument_info' ][ 'volume_multiple' ]:" ,
        #       self.own_data[ 'tb_instrument_info' ][ 'volume_multiple' ][0])
        # print("self.own_data[ 'tb_fee_ratio_info' ][ 'long_margin_ratio_by_money' ]:" ,
        #       self.own_data[ 'tb_fee_ratio_info' ][ 'long_margin_ratio_by_money' ][0])
        # print("self.own_data[ 'tb_fee_ratio_info' ][ 'short_margin_ratio_by_money' ]:" ,
        #       self.own_data[ 'tb_fee_ratio_info' ][ 'short_margin_ratio_by_money' ][0])
        # print("self.own_data[ 'tb_cli_insert_req' ][ 'volume_total_original' ]:" ,
        #         self.own_data[ 'tb_cli_insert_req' ][ 'volume_total_original' ])
        if self.own_data[ 'tb_cli_insert_req' ][ 'direction' ] == '0':
            self.own_data[ 'tb_order_info_cal' ][ 'margin' ] = self.own_data[ 'tb_cli_insert_req' ][ 'limit_price' ] * self.own_data[ 'tb_instrument_info' ][ 'volume_multiple' ][0] * self.own_data[ 'tb_fee_ratio_info' ][ 'long_margin_ratio_by_money' ][0] * self.own_data[ 'tb_cli_insert_req' ][ 'volume_total_original' ]
        elif self.own_data[ 'tb_cli_insert_req' ][ 'direction' ] == '1':
            self.own_data[ 'tb_order_info_cal' ][ 'margin' ] = self.own_data[ 'tb_cli_insert_req' ][ 'limit_price' ] * self.own_data[ 'tb_instrument_info' ][ 'volume_multiple' ][0] * self.own_data[ 'tb_fee_ratio_info' ][ 'short_margin_ratio_by_money' ][0] * self.own_data[ 'tb_cli_insert_req' ][ 'volume_total_original' ]
        # 其他方向则先赋空值
        else:
            self.own_data[ 'tb_order_info_cal' ][ 'margin' ] = None

    def cal_tb_order_info__fee(self):
        """
        冻结手续费，跟订单走，先按报单量冻结，成交后再解冻
        有费率，则，手数算一遍+费率算一遍
        没有费率，则，手数算一遍（如果费率直接配了0，是不是就无所谓了）
        费率算一遍：价格*手数*手续费率*合约乘数
        :return:
        """
        print("self.own_data[ 'tb_cli_insert_req' ][ 'limit_price' ]:" ,self.own_data[ 'tb_cli_insert_req' ][ 'limit_price' ])
        print("self.own_data[ 'tb_cli_insert_req' ][ 'volume_total_original' ]:" ,self.own_data[ 'tb_cli_insert_req' ][ 'volume_total_original' ])
        print("self.own_data[ 'tb_fee_ratio_info' ][ 'open_ratio_by_volume' ]:" ,self.own_data[ 'tb_fee_ratio_info' ][ 'open_ratio_by_volume' ][0])
        print("self.own_data[ 'tb_instrument_info' ][ 'volume_multiple' ]:" ,self.own_data[ 'tb_instrument_info' ][ 'volume_multiple' ][0])
        print("self.own_data[ 'tb_instrument_info' ][ 'fee_ratio_by_volume' ]:" ,self.own_data[ 'tb_instrument_info' ][ 'fee_ratio_by_volume' ][0])
        self.own_data[ 'tb_order_info_cal' ][ 'fee' ] = self.own_data[ 'tb_cli_insert_req' ][ 'volume_total_original' ] * self.own_data[ 'tb_instrument_info' ][ 'fee_ratio_by_volume' ] + self.own_data[ 'tb_cli_insert_req' ][ 'limit_price' ] * self.own_data[ 'tb_cli_insert_req' ][ 'volume_total_original' ] * self.own_data[ 'tb_fee_ratio_info' ][ 'open_ratio_by_volume' ]
        pass

    def cal_tb_account_position__margin(self):
        """
        解冻保证金，成交、撤单都会解冻保证金
        :return:
        """

        pass

    def cal_tb_account_position__posi_profit(self):
        """
        持仓盈亏
        :return:
        """

        pass

    def cal_tb_account_position__close_profit(self):
        """
        平仓盈亏
        :return:
        """
        pass

    def cal_tb_account_position__close_volume(self):
        """
        平仓数量
        :return:
        """
        pass

    def cal_tb_account_position__total_average_price(self):
        """
        总持仓均价
        :return:
        """
        pass

    def cal_tb_account_position__open_volume(self):
        """
        开仓成交数量
        :return:
        """
        pass

    def cal_tb_account_position__total_position(self):
        """
        持仓数量
        :return:
        """
        pass

    def cal_tb_account_position__position_frozen(self):
        """
        今持仓冻结数量
        :return:
        """
        pass

    def cal_tb_account_position__yd_position(self):
        """
        昨持仓冻结数量
        :return:
        """
        pass

    def caltb_account_position__position(self):
        """
        今持仓数量
        :return:
        """
        pass

    def cal_tb_cli_order_rtn__volume_total_original(self):
        """
        报单数量(以手为单位)
        :return:
        """
        pass

    def cal_tb_cli_order_rtn__volume_traded(self):
        """
        成交数量
        :return:
        """
        pass

    def cal_tb_cli_order_rtn__volume_total(self):
        """
        剩余数量
        :return:
        """
        pass

    def cal_tb_account_funds_info__available(self):
        """
        可用资金
        :return:
        """
        self.own_data[ 'tb_account_funds_info_cal' ][ 'available' ] = self.own_data[ 'tb_account_funds_info' ][ 'available' ] - self.own_data[ 'tb_order_info_cal' ][ 'margin' ] - self.own_data[ 'tb_order_info_cal' ][ 'fee' ]
        pass

    def cal_tb_account_funds_info__fee(self):
        """
        账户手续费，成交了才有手续费更新，手续费只会增加
        有一个成交订单则会计算一次手续费
        :return:
        """

        pass

    def cal_tb_account_funds_info__margin(self):
        """
        账户保证金，成交后才有保证金更新，会增加、减少，不会为负数
        有一个成交订单则会计算一次保证金
        :return:
        """

        pass

    def compare_cal_data(self):
        """
        用来对比apidemo和程序验算数据是否一致
        即 own_data 的后缀_aft数据和后缀_cal数据是否一致
        :return:
        """
        compare_flag = True
        print('tb_order_info_cal:margin:',self.own_data[ 'tb_order_info_cal' ][ 'margin' ],type(self.own_data[ 'tb_order_info_cal' ][ 'margin' ]))
        print('tb_order_info_aft:margin:',self.own_data[ 'tb_order_info_aft' ][ 'margin' ],type(self.own_data[ 'tb_order_info_aft' ][ 'margin' ]))

        print('tb_order_info_cal:fee:',self.own_data[ 'tb_order_info_cal' ][ 'fee' ],type(self.own_data[ 'tb_order_info_cal' ][ 'fee' ]))
        print('tb_order_info_aft:fee:',self.own_data[ 'tb_order_info_aft' ][ 'fee' ],type(self.own_data[ 'tb_order_info_aft' ][ 'fee' ]))

        print('tb_account_funds_info_cal:available:',self.own_data[ 'tb_account_funds_info_cal' ][ 'available' ],type(self.own_data[ 'tb_account_funds_info_cal' ][ 'available' ]))
        print('tb_account_funds_info_aft:available:',self.own_data[ 'tb_account_funds_info_aft' ][ 'available' ],type(self.own_data[ 'tb_account_funds_info_aft' ][ 'available' ]))

        # if self.own_data[ 'tb_order_info_cal' ][ 'margin' ] != self.own_data[ 'tb_order_info_aft' ][ 'margin' ]:
        #     compare_flag = False
        # if self.own_data[ 'tb_order_info_cal' ][ 'fee' ] != self.own_data[ 'tb_order_info_aft' ][ 'fee' ]:
        #     compare_flag = False
        # if self.own_data[ 'tb_account_funds_info_cal' ][ 'available' ] != self.own_data[ 'tb_account_funds_info_aft' ][ 'available' ]:
        #     compare_flag = False
        return compare_flag

    def compare_qry_data(self):
        """
        用来对比apidemo和柜台数据库数据是否一致
        :return:
        """
        pass


if __name__ == '__main__':
    # 公式是从开发哪里拿到的 验算只能看到取值问题和精度问题
    # 获取本方数据，后面用configparser读取配置文件
    own_data = get_apidemo_data(host = '171.17.104.16' ,
                       port = 3306 ,
                       user = 'root' ,
                       password = '123456' ,
                       db = 'hqt_fut_lbs_apidemo' ).return_all_dict()

    print(own_data)


    # # 获取对方数据，后面用configparser读取配置文件
    # opp_data = get_apidemo_data(host = '171.17.104.16' ,
    #                    port = 3306 ,
    #                    user = 'root' ,
    #                    password = '123456' ,
    #                    db = 'hqt_fut_lbs_apidemo_02' ).return_all_dict()
    #
    # # 比对数据正确性
    # cal = cal_apidemo_data(own_data, opp_data)
    # # print(cal.own_data)
    # # print(cal.opp_data)
    # #
    # own_log = open('own_log.txt', 'w')
    # opp_log = open('opp_log.txt', 'w')
    #
    # for key in cal.own_data.keys():
    #     opp_log.write(key + ":" + str(cal.own_data[key]) + '\n')
    # for key in cal.opp_data.keys():
    #     own_log.write(key + ":" + str(cal.opp_data[key]) + '\n')
    #
    # own_log.close()
    # opp_log.close()
    #
    # # 按需计算
    # print("cccccccccc",cal.own_data[ 'tb_order_info_cal' ][ 'margin' ])
    # cal.cal_tb_order_info__margin()
    # print("aaaaaaaaaa",cal.own_data[ 'tb_order_info_cal' ][ 'margin' ])
    #
    # print("cccccccccc",cal.own_data[ 'tb_order_info_cal' ][ 'fee' ])
    # cal.cal_tb_order_info__fee()
    # print("aaaaaaaaaa",cal.own_data[ 'tb_order_info_cal' ][ 'fee' ])
    #
    # print("cccccccccc",cal.own_data[ 'tb_account_funds_info_cal' ][ 'available' ])
    # cal.cal_tb_account_funds_info__available()
    # print("aaaaaaaaaa",cal.own_data[ 'tb_account_funds_info_cal' ][ 'available' ])
    #
    # # 规范一下输出格式
    # # 先输出订单状态：
    # # 本方订单：...
    # # 对手方订单：...
    # # 判断结果订单状态：正常、错误、未知
    # # 再输出数据验算：
    # # 起始数据 | 报单后数据 | 验算数据 | 验算结果
    #
    # # 比较函数
    # gg = cal.compare_cal_data()
    # print(gg)
    # print(type(gg))
    # if gg:
    #     print("验算通过")
    # else:
    #     print("验算不通过")
    #
    # print("本方订单：",cal.own_data[ 'tb_cli_insert_req' ])
    # print("对手方订单：",cal.opp_data[ 'tb_cli_insert_req' ])
    # if cal.own_data[ 'tb_cli_insert_req' ] == cal.opp_data[ 'tb_cli_insert_req' ]:
    #     print("订单状态：正常")
    # else:
    #     print("订单状态：错误")

    # cal_list = ['tb_order_info_cal', 'tb_order_info_aft', 'tb_account_funds_info_cal', 'tb_account_funds_info_aft']
    # for key in cal.own_data.keys():
    #     print()
