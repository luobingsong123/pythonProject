# connet to mysql and get data
import pymysql
import pandas as pd
import random
import string
import pymysql.cursors


# 连接数据库
conn_demo = pymysql.connect(host = '192.168.1.138' ,
                       port = 3306 ,
                       user = 'root' ,
                       passwd = 'a*963.-+' ,
                       db = 'test_db' ,
                       charset = 'utf8')

conn_hqt = pymysql.connect(host = '192.168.1.138' ,
                       port = 3306 ,
                       user = 'root' ,
                       passwd = 'a*963.-+' ,
                       db = 'test_db' ,
                       charset = 'utf8')

# 获取一个光标
cursor = conn_demo.cursor()

# 生成随机数据并插入数据库表
def generate_random_data():
    # cancel_req 撤单请求
    OrigOrderLocalID = random.randint(1000000 , 100000000)  # int(11)   '原柜台订单号',
    OrigOrderRef = random.randint(1000000 , 100000000)  # int(11)   '原订单引用（本地报单号）',
    # ClientID = random.choice([ 'test_client' , 'test_cliena' ])  # char(11)   '交易编码',
    ClientID = 'test_client'  # char(11)   '交易编码',
    TraderID = 'ET46yN9MecnqI4iw'  # char(16)   '席位号',
    OrderRef = random.randint(1000000 , 100000000)  # int(11)   '撤单订单引用（客户端本地报单号）',
    ExchangeID = 'S'  # char(1)   '交易所编号',

    # cancel_rsp 撤单应答
    ClientID = 'test_client'  # char(11)   '交易编码',
    OrderLocalID = random.randint(1000000 , 100000000)  # int(11)   '撤单订单号',
    OrderRef = random.randint(1000000 , 100000000)  # int(11)   '撤单订单引用（客户端本地撤单号）',
    OrigOrderLocalID = random.randint(1000000 , 100000000)  # int(11)   '原柜台订单号',
    OrigOrderRef = random.randint(1000000 , 100000000)  # int(11)   '原订单引用（本地报单号）',
    ExchangeID = 'S'  # char(1)   '交易所编号',

    # insert_req 报单请求
    ClientID = 'test_client'  # char(11)   '交易编码',
    TraderID = 'ET46yN9MecnqI4iw'  # char(16)   '席位号',
    InstrumentID = ''.join(random.choices(string.ascii_letters + string.digits , k = 31))  # char(31)   '合约代码',
    OrderType = random.choice([ '0' , '1' ])  # char(1)   '报单类型：0->限价，1->市价',
    Direction = random.choice([ '1' , '2' ])  # char(1)   '买卖方向：1->买，2->卖',
    OffsetFlag = random.choice([ '1' , '2' , '3' , '4' ])  # char(1)   '开平标志：1->开仓，2->平仓，3->平今，4->平昨',
    HedgeFlag = random.choice([ '1' , '2' , '3' ])  # char(1)   '投保标志：1->投机，2->套利，3->套保',
    LimitPrice = random.randint(1000000 , 100000000)  # int(11)   '限价，单位：万分之一元',
    VolumeTotalOriginal = random.randint(1000000 , 100000000)  # int(11)   '报单数量(以手为单位)',
    OrderRef = random.randint(1000000 , 100000000)  # int(11)   '报单引用（客户端本地报单号）',
    ExchangeID = random.randint(1000000 , 100000000)  # char(1)   '交易所编号',

    # insert_rsp 报单应答
    ClientID = 'test_client'  # char(11)   '交易编码',
    OrderLocalID = random.randint(1000000 , 100000000)  # int(11)   '柜台报单号',
    OrderRef = random.randint(1000000 , 100000000)  # int(11)   '报单引用（本地报单号）',
    ExchangeID = 'S'  # char(1)   '交易所编号',

    # insert_rtn 报单回报
    ClientID = 'test_client'  # char(11)   '交易编码',
    OrderRef = random.randint(1000000 , 100000000)  # int(11)   '报单引用（客户端本地报单号）',
    OrderLocalID = random.randint(1000000 , 100000000)  # int(11)   '柜台报单号',
    OrderSysID = random.randint(1000000 , 100000000)  # bigint(22)   '交易所报单号',
    OrderStatus = '1'  # char(1)   '报单状态',
    VolumeTraded = random.randint(1000000 , 100000000)  # int(11)   '成交数量',
    VolumeTotal = random.randint(1000000 , 100000000)  # int(11)   '剩余数量',
    InstrumentID = ''.join(random.choices(string.ascii_letters + string.digits , k = 31))  # char(31)   '合约代码',
    OrderType = random.choice([ '0' , '1' ])  # char(1)   '报单类型：0->限价，1->市价',
    Direction = random.choice([ '1' , '2' ])  # char(1)   '买卖方向：1->买，2->卖',
    OffsetFlag = random.choice([ '1' , '2' , '3' , '4' ])  # char(1)   '开平标志：1->开仓，2->平仓，3->平今，4->平昨',
    HedgeFlag = random.choice([ '1' , '2' , '3' ])  # char(1)   '投保标志：1->投机，2->套利，3->套保',
    LimitPrice = random.randint(1000000 , 100000000)  # int(11)   '限价，单位：万分之一元',
    VolumeTotalOriginal = random.randint(1000000 , 100000000)  # int(11)   '报单数量(以手为单位)',
    ExchangeID = 'S'  # char(1)   '交易所编号',

    # insert_trade 报单成交回报
    ClientID = 'test_client'  # char(11)   '交易编码',
    OrderRef = random.randint(1000000 , 100000000)  # int(11)   '报单引用（客户端本地报单号）',
    OrderLocalID = random.randint(1000000 , 100000000)  # int(11)   '柜台报单号',
    OrderSysID = random.randint(1000000 , 100000000)  # bigint(22)   '交易所报单号',
    TradeID = random.randint(1000000 , 100000000)  # bigint(22)   '成交编号',
    InstrumentID = ''.join(random.choices(string.ascii_letters + string.digits , k = 31))  # char(31)   '合约代码',
    Direction = random.choice([ '1' , '2' ])  # char(1)   '买卖方向：1->买，2->卖',
    OffsetFlag = random.choice([ '1' , '2' , '3' , '4' ])  # char(1)   '开平标志：1->开仓，2->平仓，3->平今，4->平昨',
    HedgeFlag = random.choice([ '1' , '2' , '3' ])  # char(1)   '投保标志：1->投机，2->套利，3->套保',
    Price = random.randint(1000000 , 100000000)  # int(11)   '成交价格，单位：万分之一元',
    Volume = random.randint(1000000 , 100000000)  # int(11)   '成交数量',
    ExchangeID = 'S'  # char(1)   '交易所编号',

    # qry_asset 资金查询
    AccountID = 'test_client1'  # char(12)   '资金帐号,投资者账号',
    Available = random.randint(1000000 , 100000000)  # double(20,0)   '可用资金',
    YDBenefits = random.randint(1000000 , 100000000)  # double(20,0)   '上日权益',
    Benefits = random.randint(1000000 , 100000000)  # double(20,0)   '今权益',
    PositionProfit = random.randint(1000000 , 100000000)  # double(20,0)   '持仓盈亏',
    CloseProfit = random.randint(1000000 , 100000000)  # double(20,0)   '平仓盈亏',
    Fee = random.randint(1000000 , 100000000)  # double(20,0)   '手续费',
    Margin = random.randint(1000000 , 100000000)  # double(20,0)   '保证金',
    CurrencyId = 'RMB'  # char(4)   '币种',
    Deposit = random.randint(1000000 , 100000000)  # double(20,0)   '入金',
    Withdraw = random.randint(1000000 , 100000000)  # double(20,0)   '出金',
    UseLimit = random.randint(1000000 , 100000000)  # double(20,0)   '使用限度',
    RiskDegree = random.randint(1000000 , 100000000)  # double(20,0)   '风险度',

    # qry_feerate 费率查询
    AccountID = 'test_client1'  # char(12)   '资金帐号,投资者账号',
    InstrumentID = ''.join(random.choices(string.ascii_letters + string.digits ,
                                          k = 31))  # char(31)   '合约代码，若不为空，1.且UnderlyingInstrID为空，则为合约费率；2.且UnderlyingInstrID不为空，则合约费率同品种费率',
    UnderlyingInstrID = ''.join(random.choices(string.ascii_letters + string.digits ,
                                               k = 8))  # char(8)   '基础商品代码，若不为空，且InstrumentID为空则为品种费率',
    RatioGroupName = ''.join(random.choices(string.ascii_letters + string.digits , k = 32))  # char(32)   '费率组名',
    LongMarginRatioByMoney = random.randint(1000000 , 100000000)  # double(20,0)   '多头保证金率',
    LongMarginRatioByVolume = random.randint(1000000 , 100000000)  # double(20,0)   '多头保证金费',
    ShortMarginRatioByMoney = random.randint(1000000 , 100000000)  # double(20,0)   '空头保证金率',
    ShortMarginVolumeByVolume = random.randint(1000000 , 100000000)  # double(20,0)   '空头保证金费',
    OpenRatioByVolume = random.randint(1000000 , 100000000)  # double(20,0)   '开仓手续费',
    CloseRatioByVolume = random.randint(1000000 , 100000000)  # double(20,0)   '平仓手续费',
    CloseTDRatioByVolume = random.randint(1000000 , 100000000)  # double(20,0)   '平今手续费',
    OpenRatioByMoney = random.randint(1000000 , 100000000)  # double(20,0)   '开仓手续费率',
    CloseRatioByMoney = random.randint(1000000 , 100000000)  # double(20,0)   '平仓手续费率',
    CloseTDRatioByMoney = random.randint(1000000 , 100000000)  # double(20,0)   '平今手续费率',

    # # qry_instrument 合约查询
    # InstrumentID = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(31)   '合约代码',
    # Exchange = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(8)   '交易所代码',
    # UnderlyingInstrID = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(8)   '基础商品代码',
    # ProductClass = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(1)   '产品类型',
    # PositionType = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(1)   '持仓类型',
    # StrikePrice =  random.randint(1000000 , 100000000) # double(21,0)   '执行价',
    # OptionsType = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(1)   '期权类型',
    # VolumeMultiple = random.randint(1000000 , 100000000) # int(10)   '合约数量乘数',
    # UnderlyingMultiple =  random.randint(1000000 , 100000000) # double(21,0)   '合约基础商品乘数',
    # DeliveryYear = random.randint(1000000 , 100000000) # int(10)   '交割年份',
    # DeliveryMonth = random.randint(1000000 , 100000000) # int(10)   '交割月份',
    # AdvanceMonth = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(4)   '提前月份',
    # TradingAuth = 'RMB' # int(4)   '交易权限',
    # CreateDate = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(9)   '创建日',
    # OpenDate = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(9)   '上市日',
    # ExpireDate = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(9)   '到期日',
    # StartDelivDate = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(9)   '开始交割日',
    # EndDelivDate = ''.join(random.choices(string.ascii_letters + string.digits , k = 31)) # char(9)   '最后交割日',
    # BasisPrice =  random.randint(1000000 , 100000000) # double(21,0)   '挂牌基准价',
    # MaxMarketOrderVolume = random.randint(1000000 , 100000000) # int(10)   '市价单最大下单量',
    # MinMarketOrderVolume = random.randint(1000000 , 100000000) # int(10)   '市价单最小下单量',
    # MaxLimitOrderVolume = random.randint(1000000 , 100000000) # int(10)   '限价单最大下单量',
    # MinLimitOrderVolume = random.randint(1000000 , 100000000) # int(10)   '限价单最小下单量',
    # CurrencyId = 'RMB' # char(4)   '币种代码',
    # LastPrice =  random.randint(1000000 , 100000000) # double(21,0)   '最新价',
    # PreSettlementPrice =  random.randint(1000000 , 100000000) # double(21,0)   '昨结算价',
    # PreClosePrice =  random.randint(1000000 , 100000000) # double(21,0)   '昨收盘价',
    # PreOpenInterest =  random.randint(1000000 , 100000000) # double(21,0)   '昨持仓量',
    # OpenPrice =  random.randint(1000000 , 100000000) # double(21,0)   '今开盘价',
    # HighestPrice =  random.randint(1000000 , 100000000) # double(21,0)   '最高价',
    # LowestPrice =  random.randint(1000000 , 100000000) # double(21,0)   '最低价',
    # Volume = random.randint(1000000 , 100000000) # int(10)   '委托量',
    # Turnover =  random.randint(1000000 , 100000000) # double(21,0)   '成交金额',
    # OpenInterest =  random.randint(1000000 , 100000000) # double(21,0)   '持仓量',
    # ClosePrice =  random.randint(1000000 , 100000000) # double(21,0)   '今收盘价',
    # SettlementPrice =  random.randint(1000000 , 100000000) # double(21,0)   '今结算价',
    # UpperLimitPrice =  random.randint(1000000 , 100000000) # double(21,0)   '涨停板价',
    # LowerLimitPrice =  random.randint(1000000 , 100000000) # double(21,0)   '跌停板价',
    # PreDelta =  random.randint(1000000 , 100000000) # double(21,0)   '昨虚实度',
    # CurrDelta =  random.randint(1000000 , 100000000) # double(21,0)   '今虚实度',
    # BuySpeMarginRatioByMoney =  random.randint(1000000 , 100000000) # double(21,0)   '交易所投机买保证金率',
    # SellSpeMarginRatioByMoney =  random.randint(1000000 , 100000000) # double(21,0)   '交易所投机卖保证金率',
    # BuyHedgeMarginRatioByMoney =  random.randint(1000000 , 100000000) # double(21,0)   '交易所套保买保证金率',
    # SellHedgeMarginVolumeByMoney =  random.randint(1000000 , 100000000) # double(21,0)   '交易所套保买保证金率',
    # FeeRatioByVolume =  random.randint(1000000 , 100000000) # double(21,0)   '交易所手续费(按手数)',
    # FeeRatioByMoney =  random.randint(1000000 , 100000000) # double(21,0)   '交易所手续费率',
    # FeeDeliveryRatioByMoney =  random.randint(1000000 , 100000000) # double(21,0)   '交易所交割手续费率',

    # qry_order 订单查询
    AccountID = ''.join(random.choices(string.ascii_letters + string.digits , k = 32))  # char(12)   '资金帐号,投资者账号',
    OrderSysID = random.randint(1000000 , 100000000)  # bigint(21)   '交易所报单编号',
    OrderLocalID = random.randint(1000000 , 100000000)  # int(11)   '柜台报单编号',
    OrderRef = random.randint(1000000 , 100000000)  # int(11)   '本地报单号',
    InstrumentID = ''.join(random.choices(string.ascii_letters + string.digits , k = 31))  # char(31)   '合约代码',
    Direction = 'S'  # char(1)   '买卖方向',
    OffsetFlag = 'K'  # char(1)   '开平标志',
    HedgeFlag = 'T'  # char(1)   '投机套保标志',
    OrderStatus = 'B'  # char(1)   '报单状态',
    VolumeTotalOriginal = random.randint(1000000 , 100000000)  # int(11)   '报单数量',
    LimitPrice = random.randint(1000000 , 100000000)  # double(21,2)   '报单价格',
    OrderType = 'T'  # char(1)   '报单类型',
    VolumeTraded = random.randint(1000000 , 100000000)  # int(11)   '成交数量',
    VolumeCancel = random.randint(1000000 , 100000000)  # int(11)   '撤单数量',
    MinVolume = random.randint(1000000 , 100000000)  # int(11)   '最小成交量',
    TraderID = 'ET46yN9MecnqI4iw'  # char(16)   '席位号',
    Exchange = ''.join(random.choices(string.ascii_letters + string.digits , k = 8))  # char(8)   '交易所代码',
    TimeCondition = 'A'  # char(1)   '有效期类型',
    Margin = random.randint(1000000 , 100000000)  # double(21,0)   '冻结保证金',
    Fee = random.randint(1000000 , 100000000)  # double(21,0)   '冻结手续费',

    # qry_position 持仓查询
    AccountID = 'test_client1'  # char(12)   '资金账号',
    InstrumentID = ''.join(random.choices(string.ascii_letters + string.digits , k = 31))  # char(31)   '合约代码',
    Exchange = ''.join(random.choices(string.ascii_letters + string.digits , k = 8))  # char(8)   '交易所代码',
    Direction = ''.join(random.choices(string.ascii_letters + string.digits , k = 1))  # char(1)   '买卖方向',
    HedgeFlag = random.choice([ '1' , '2' , '3' ])  # char(1)   '投机套保标志',
    Margin = random.randint(1000000 , 100000000)  # double(20,0)   '解冻保证金',
    PosiProfit = random.randint(1000000 , 100000000)  # double(20,0)   '持仓盈亏',
    CloseProfit = random.randint(1000000 , 100000000)  # double(20,0)   '平仓盈亏',
    CloseVolume = random.randint(1000000 , 100000000)  # int(11)   '平仓数量',
    TotalAveragePrice = random.randint(1000000 , 100000000)  # double(20,2)   '总持仓均价',
    YDAveragePrice = random.randint(1000000 , 100000000)  # double(20,2)   '昨持仓均价',
    AveragePrice = random.randint(1000000 , 100000000)  # double(20,2)   '今持仓均价',
    OpenVolume = random.randint(1000000 , 100000000)  # int(11)   '开仓成交数量',
    TotalPosition = random.randint(1000000 , 100000000)  # int(11)   '持仓数量',
    PositionFrozen = random.randint(1000000 , 100000000)  # int(11)   '持仓冻结数量',
    YDPosition = random.randint(1000000 , 100000000)  # int(11)   '昨持仓数量',
    Position = random.randint(1000000 , 100000000)  # int(11)   '今持仓数量',

    # qry_trade 成交查询
    AccountID = 'test_client1'  # char(12)   '资金帐号,投资者账号',
    TradeID = random.randint(1000000 , 100000000)  # bigint(21)   '成交编号',
    Volume = random.randint(1000000 , 100000000)  # int(11)   '成交量',
    Price = random.randint(1000000 , 100000000)  # double(21,2)   '成交价',
    InstrumentID = ''.join(random.choices(string.ascii_letters + string.digits , k = 31))  # char(31)   '合约代码',
    Direction = 'S'  # char(1)   '买卖方向',
    OffsetFlag = 'K'  # char(1)   '开平标志',
    HedgeFlag = 'T'  # char(1)   '投机套保标志',
    OrderSysID = random.randint(1000000 , 100000000)  # bigint(21)   '交易所报单编号',
    OrderLocalID = random.randint(1000000 , 100000000)  # int(11)   '柜台报单编号',
    TraderID = 'ET46yN9MecnqI4iw'  # char(16)   '席位号',
    Exchange = ''.join(random.choices(string.ascii_letters + string.digits , k = 8))  # char(8)   '交易所代码',
    TradeType = 'A'  # char(1)   '成交类型',

    # qry_tradecode 交易编码查询
    AccountID = 'test_client1'  # char(12)   '资金账号',
    ExchangeID = 'S'  # char(1)   '交易所编号',
    Exchange = ''.join(random.choices(string.ascii_letters + string.digits , k = 8))  # char(8)   '交易所代码',
    ClientID = 'test_client'  # char(11)   '交易编码',

    # 生成撤单请求数据
    sql_cancel_req = f"INSERT INTO cancel_req (OrigOrderLocalID,OrigOrderRef,ClientID,TraderID,OrderRef,ExchangeID) VALUES ('{OrigOrderLocalID}','{OrigOrderRef}','{ClientID}','{TraderID}','{OrderRef}','{ExchangeID}')"
    # 生成撤单应答数据
    sql_cancel_rsp = f"INSERT INTO cancel_rsp (ClientID,OrderLocalID,OrderRef,OrigOrderLocalID,OrigOrderRef,ExchangeID) VALUES ('{ClientID}','{OrderLocalID}','{OrderRef}','{OrigOrderLocalID}','{OrigOrderRef}','{ExchangeID}')"
    # 生成报单请求数据
    sql_insert_req = f"INSERT INTO insert_req (ClientID,TraderID,InstrumentID,OrderType,Direction,OffsetFlag,HedgeFlag,LimitPrice,VolumeTotalOriginal,OrderRef,ExchangeID) VALUES ('{ClientID}','{TraderID}','{InstrumentID}','{OrderType}','{Direction}','{OffsetFlag}','{HedgeFlag}','{LimitPrice}','{VolumeTotalOriginal}','{OrderRef}','{ExchangeID}')"
    # 生成报单应答数据
    sql_insert_rsp = f"INSERT INTO insert_rsp (ClientID,OrderLocalID,OrderRef,ExchangeID) VALUES ('{ClientID}','{OrderLocalID}','{OrderRef}','{ExchangeID}')"
    # 生成报单回报数据
    sql_insert_rtn = f"INSERT INTO insert_rtn (ClientID,OrderRef,OrderLocalID,OrderSysID,OrderStatus,VolumeTraded,VolumeTotal,InstrumentID,OrderType,Direction,OffsetFlag,HedgeFlag,LimitPrice,VolumeTotalOriginal,ExchangeID) VALUES ('{ClientID}','{OrderRef}','{OrderLocalID}','{OrderSysID}','{OrderStatus}','{VolumeTraded}','{VolumeTotal}','{InstrumentID}','{OrderType}','{Direction}','{OffsetFlag}','{HedgeFlag}','{LimitPrice}','{VolumeTotalOriginal}','{ExchangeID}')"
    # 生成报单成交回报数据
    sql_insert_trade = f"INSERT INTO insert_trade (ClientID,OrderRef,OrderLocalID,OrderSysID,TradeID,InstrumentID,Direction,OffsetFlag,HedgeFlag,Price,Volume,ExchangeID) VALUES ('{ClientID}','{OrderRef}','{OrderLocalID}','{OrderSysID}','{TradeID}','{InstrumentID}','{Direction}','{OffsetFlag}','{HedgeFlag}','{Price}','{Volume}','{ExchangeID}')"
    # 生成资金查询数据
    sql_qry_asset = f"INSERT INTO qry_asset (AccountID,Available,YDBenefits,Benefits,PositionProfit,CloseProfit,Fee,Margin,CurrencyId,Deposit,Withdraw,UseLimit,RiskDegree) VALUES ('{AccountID}','{Available}','{YDBenefits}','{Benefits}','{PositionProfit}','{CloseProfit}','{Fee}','{Margin}','{CurrencyId}','{Deposit}','{Withdraw}','{UseLimit}','{RiskDegree}')"
    # 生成费率查询数据
    sql_qry_feerate = f"INSERT INTO qry_feerate (AccountID,InstrumentID,UnderlyingInstrID,RatioGroupName,LongMarginRatioByMoney,LongMarginRatioByVolume,ShortMarginRatioByMoney,ShortMarginVolumeByVolume,OpenRatioByVolume,CloseRatioByVolume,CloseTDRatioByVolume,OpenRatioByMoney,CloseRatioByMoney,CloseTDRatioByMoney) VALUES ('{AccountID}','{InstrumentID}','{UnderlyingInstrID}','{RatioGroupName}','{LongMarginRatioByMoney}','{LongMarginRatioByVolume}','{ShortMarginRatioByMoney}','{ShortMarginVolumeByVolume}','{OpenRatioByVolume}','{CloseRatioByVolume}','{CloseTDRatioByVolume}','{OpenRatioByMoney}','{CloseRatioByMoney}','{CloseTDRatioByMoney}')"
    # 生成订单查询数据
    sql_qry_order = f"INSERT INTO qry_order(AccountID,OrderSysID,OrderLocalID,OrderRef,InstrumentID,Direction,OffsetFlag,HedgeFlag,OrderStatus,VolumeTotalOriginal,LimitPrice,OrderType,VolumeTraded,VolumeCancel,MinVolume,TraderID,Exchange,TimeCondition,Margin,Fee) values('{AccountID}','{OrderSysID}','{OrderLocalID}','{OrderRef}','{InstrumentID}','{Direction}','{OffsetFlag}','{HedgeFlag}','{OrderStatus}','{VolumeTotalOriginal}','{LimitPrice}','{OrderType}','{VolumeTraded}','{VolumeCancel}','{MinVolume}','{TraderID}','{Exchange}','{TimeCondition}','{Margin}','{Fee}');"
    # 生成持仓查询数据
    sql_qry_position = f"INSERT INTO qry_position(AccountID,InstrumentID,Exchange,Direction,HedgeFlag,Margin,PosiProfit,CloseProfit,CloseVolume,TotalAveragePrice,YDAveragePrice,AveragePrice,OpenVolume,TotalPosition,PositionFrozen,YDPosition,Position) values('{AccountID}','{InstrumentID}','{Exchange}','{Direction}','{HedgeFlag}','{Margin}','{PosiProfit}','{CloseProfit}','{CloseVolume}','{TotalAveragePrice}','{YDAveragePrice}','{AveragePrice}','{OpenVolume}','{TotalPosition}','{PositionFrozen}','{YDPosition}','{Position}');"
    # 生成成交查询数据
    sql_qry_trade = f"INSERT INTO qry_trade(AccountID,TradeID,Volume,Price,InstrumentID,Direction,OffsetFlag,HedgeFlag,OrderSysID,OrderLocalID,TraderID,Exchange,TradeType) values('{AccountID}','{TradeID}','{Volume}','{Price}','{InstrumentID}','{Direction}','{OffsetFlag}','{HedgeFlag}','{OrderSysID}','{OrderLocalID}','{TraderID}','{Exchange}','{TradeType}');"
    # 生成交易编码查询数据
    sql_qry_tradecode = f"INSERT INTO qry_tradecode(AccountID,ExchangeID,Exchange,ClientID) values('{AccountID}','{ExchangeID}','{Exchange}','{ClientID}');"



    try:
        # 订单类生成一条数据
        print(sql_cancel_req)
        cursor.execute(sql_cancel_req)
        print(sql_cancel_rsp)
        cursor.execute(sql_cancel_rsp)
        print(sql_insert_req)
        cursor.execute(sql_insert_req)
        print(sql_insert_rsp)
        cursor.execute(sql_insert_rsp)
        print(sql_insert_rtn)
        cursor.execute(sql_insert_rtn)
        print(sql_insert_trade)
        cursor.execute(sql_insert_trade)
        # 查询类生成两条数据
        print(sql_qry_asset)
        cursor.execute(sql_qry_asset)
        print(sql_qry_asset)
        cursor.execute(sql_qry_asset)
        print(sql_qry_feerate)
        cursor.execute(sql_qry_feerate)
        print(sql_qry_feerate)
        cursor.execute(sql_qry_feerate)
        print(sql_qry_order)
        cursor.execute(sql_qry_order)
        print(sql_qry_order)
        cursor.execute(sql_qry_order)
        print(sql_qry_position)
        cursor.execute(sql_qry_position)
        print(sql_qry_position)
        cursor.execute(sql_qry_position)
        print(sql_qry_trade)
        cursor.execute(sql_qry_trade)
        print(sql_qry_trade)
        cursor.execute(sql_qry_trade)
        print(sql_qry_tradecode)
        cursor.execute(sql_qry_tradecode)
        print(sql_qry_tradecode)
        cursor.execute(sql_qry_tradecode)
    except Exception as e:
        print(f"Failed to insert data: {e}")
        # conn.rollback()


if __name__ == '__main__':
    # 生成数据
    # for i in range(1):
    #     print("loop i:" + str(i))
    #     for j in range(100):
    #         generate_random_data()
    #     conn_demo.commit()
    generate_random_data()
    conn_demo.commit()
    conn_demo.close()
    conn_hqt.close()

