# connet to mysql and get data
import pymysql
import pandas as pd
import random
import string
import pymysql.cursors


class tariff_calculation(object):
    """
    先做单个账户的，后续再考虑多账户（多CSV文件同时）的处理
    订单量对比后续考虑其他的方式
    """
    def __init__(self, host, port, db, user, password):
        self.host = host
        self.port = port
        self.db = db
        self.user = user
        self.password = password
        print(self.host)
        print(self.port)
        print(self.db)
        print(self.user)
        print(self.password)


        # 账户初始资金数据
        self.account_asset_before_account_id = None  # 资金帐号,投资者账号
        self.account_asset_before_available = None  # 可用资金
        self.account_asset_before_yd_benefits = None  # 上日权益
        self.account_asset_before_benefits = None  # 今权益
        self.account_asset_before_position_profit = None  # 持仓盈亏
        self.account_asset_before_close_profit = None  # 平仓盈亏
        self.account_asset_before_fee = None  # 手续费
        self.account_asset_before_margin = None  # 保证金
        self.account_asset_before_currency_id = None  # 币种
        self.account_asset_before_deposit = None  # 入金
        self.account_asset_before_withdraw = None  # 出金
        self.account_asset_before_use_limit = None  # 使用限度
        self.account_asset_before_risk_degree = None  # 风险度

        # 账户费率
        self.feerate_account_id = None  # 资金帐号,投资者账号
        self.feerate_ratio_group_name = None  # 费率组名
        self.feerate_long_margin_ratio_by_money = None  # 多头保证金率
        self.feerate_long_margin_ratio_by_volume = None  # 多头保证金费
        self.feerate_short_margin_ratio_by_money = None  # 空头保证金率
        self.feerate_short_margin_volume_by_volume = None  # 空头保证金费
        self.feerate_open_ratio_by_volume = None  # 开仓手续费
        self.feerate_close_ratio_by_volume = None  # 平仓手续费
        self.feerate_close_td_ratio_by_volume = None  # 平今手续费
        self.feerate_open_ratio_by_money = None  # 开仓手续费率
        self.feerate_close_ratio_by_money = None  # 平仓手续费率
        self.feerate_close_td_ratio_by_money = None  # 平今手续费率

        # 账户持仓
        self.position_demo = {} # 持仓字典 先做成 资金账户->合约 两层的字典

        # 账户委托
        self.account_insert_req = {}  # 报单请求
        self.account_insert_rsp = {}  # 报单应答
        self.account_insert_rtn = {}  # 报单回报
        self.account_insert_trade = {}  # 报单成交
        self.account_cancel_req = {}  # 撤单请求
        self.account_cancel_rsp = {}  # 撤单应答

        # 账户最终资金数据
        self.account_asset_after_account_id = None  # 资金帐号,投资者账号
        self.account_asset_after_available = None  # 可用资金
        self.account_asset_after_yd_benefits = None  # 上日权益
        self.account_asset_after_benefits = None  # 今权益
        self.account_asset_after_position_profit = None  # 持仓盈亏
        self.account_asset_after_close_profit = None  # 平仓盈亏
        self.account_asset_after_fee = None  # 手续费
        self.account_asset_after_margin = None  # 保证金
        self.account_asset_after_currency_id = None  # 币种
        self.account_asset_after_deposit = None  # 入金
        self.account_asset_after_withdraw = None  # 出金
        self.account_asset_after_use_limit = None  # 使用限度
        self.account_asset_after_risk_degree = None  # 风险度

    def close(self):
        self.cursor.close()
        self.conn.close()

    def connect_mysql(self):
        self.conn = pymysql.connect(host=self.host, port=self.port, db=self.db, user=self.user, password=self.password,
                                    charset='utf8')
        self.cursor = self.conn.cursor()

    def get_demo_data(self, sql_message):
        df = pd.read_sql(sql_message , self.conn)
        return df

    def get_one(self, sql):
        result = None
        try:
            self.connect_mysql()
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
            self.close()
        except Exception as e:
            print(e)
        return result

    def get_all(self, sql):
        list = ()
        try:
            self.connect_mysql()
            self.cursor.execute(sql)
            list = self.cursor.fetchall()
            self.close()
        except Exception as e:
            print(e)
        return list

    def calculation(self):
        """
        计算账户资金:
        1.获取账户资金
        2.获取账户持仓
        3.获取账户费率
        4.处理报单数据
            1.报单数据先全部查出来：报单请求、报单应答、报单回报、报单成交、撤单请求、撤单应答
            2.处理报单数据：完全成交、部分成交、未成交
            3.处理撤单数据：撤单成功、撤单失败
            4.累计过程值：手续费、保证金、持仓盈亏、平仓盈亏，更新到账户初始资金数据
        5.计算账户持仓
        6.计算账户资金
        7.对比1和5、2和6
        """

        pass

    # def get_hqt_data(self, sql_message):
    #     pass

# 连接数据库
# conn_demo = pymysql.connect(host = '192.168.1.138' ,
#                        port = 3306 ,
#                        user = 'root' ,
#                        passwd = 'a*963.-+' ,
#                        db = 'test_db' ,
#                        charset = 'utf8')
#
# conn_hqt = pymysql.connect(host = '192.168.1.138' ,
#                        port = 3306 ,
#                        user = 'root' ,
#                        passwd = 'a*963.-+' ,
#                        db = 'test_db' ,
#                        charset = 'utf8')
#
# # 获取一个光标
# cursor = conn_demo.cursor()
#
# # 生成随机数据并插入数据库表
# def generate_random_data():
#     client_id = random.choice(['test_client','test_cliena'])
#     trader_id = 'ET46yN9MecnqI4iw'
#     instrument_id = ''.join(random.choices(string.ascii_letters + string.digits , k = 31))
#     order_type = random.choice([ '0' , '1'])
#     direction = random.choice([ '1' , '2'])
#     offset_flag = random.choice([ '1' , '2', '3', '4'])
#     hedge_flag = random.choice([ '1' , '2', '3'])
#     limit_price = random.randint(1000000 , 100000000)
#     volume_total_original = random.randint(1000000 , 100000000)
#     order_ref = random.randint(1000000 , 100000000)
#     exchange_id = 'S'
#     sql = f"INSERT INTO insert_req (client_id, trader_id, instrument_id, order_type, direction, offset_flag, hedge_flag, limit_price, volume_total_original, order_ref, exchange_id) VALUES ('{client_id}', '{trader_id}', '{instrument_id}', '{order_type}', '{direction}', '{offset_flag}', '{hedge_flag}', '{limit_price}', '{volume_total_original}', '{order_ref}', '{exchange_id}')"
#     try:
#         cursor.execute(sql)
#         # print(f"Inserted data for {name}, CountryCode={country_code}, District={district}, Population={population}")
#     except Exception as e:
#         print(f"Failed to insert data: {e}")
#         # conn.rollback()



if __name__ == '__main__':
    # 生成数据
    # for i in range(1):
    #     print("loop i:" + str(i))
    #     for j in range(100):
    #         generate_random_data()
    #     conn_demo.commit()

    # 实例化类
    get_data = tariff_calculation(host = '192.168.1.138' ,
                       port = 3306 ,
                       user = 'root' ,
                       password = 'a*963.-+' ,
                       db = 'test_db' )
    get_data.connect_mysql()

    # 查资金表 account_asset
    account_asset_total_data = get_data.get_demo_data("select * from account_asset")
    # 查持仓表 position
    position_total_data = get_data.get_demo_data("select * from position")
    # 查费率表 feerate
    feerate_total_data = get_data.get_demo_data("select * from feerate")
    # 查报单表 insert_req
    # insert_req_total_data = get_data_demo("select * from insert_req")
    insert_req_total_data = get_data.get_demo_data("SELECT * FROM insert_req WHERE client_id LIKE '%test_client%'")
    # 查成交表 insert_trade
    insert_trade_total_data = get_data.get_demo_data("select * from insert_trade")

    print(insert_req_total_data)
    print(insert_req_total_data.iloc[-2])

    # print(account_asset_total_data)
    # print(position_total_data)
    # print(feerate_total_data)
    # print(insert_req_total_data)
    # print(insert_trade_total_data)

    # print(table_total_data)
    # print(table_total_data.shape)
    # print(table_total_data.columns)
    # print(table_total_data.dtypes)
    # print(table_total_data.describe())
    # print(table_total_data.info())
    # print(table_total_data.isnull().sum())
    # print(len(table_total_data['instrument_id'].unique()))
    # print(len(table_total_data['order_ref']))
    # table_total_data_dict = table_total_data.to_dict()
    # print(insert_req_total_data['client_id'].unique())

    # conn_demo.close()
    # conn_hqt.close()
    # test = ''.join(random.choices(string.ascii_letters + string.digits , k = 16))
    # print(test)
