import pandas as pd
import backtrader as bt
import pandas_ta as ta
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
import config
from utils.logger_utils import setup_logger
import matplotlib.pyplot as plt
import os
os.makedirs("csv", exist_ok=True)
db_config_ = config.get_db_config()
log_config = config.get_log_config()
logger = setup_logger(logger_name=__name__,
                   log_level=log_config["log_level"],
                   log_dir=log_config["log_dir"], )

db_url = URL.create(
    drivername="mysql+pymysql",
    username=db_config_["user"],
    password=db_config_["password"],
    host=db_config_["host"],
    port=db_config_["port"],
    database=db_config_["database"]
)

engine = create_engine(db_url)


# 本代码仅用于回测研究，实盘使用风险自担

def get_stock_data_from_db(stock_code="601288", market="sh", start_date="2019-01-01"):
    """
    从数据库提取单只股票历史数据（修复版本）
    """
    # 使用SQLAlchemy连接（推荐方式）
    query = f"""
    SELECT date, open, high, low, close, volume, amount, pctChg
    FROM stock_daily_data 
    WHERE market = '{market}' 
      AND code_int = {stock_code}
      AND frequency = 'd'
      AND date >= '{start_date}'
    ORDER BY date
    """
    df = pd.read_sql(query, engine)
    # 数据清洗与格式化
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df = df.ffill()  # 前向填充缺失值
    return df


def get_stock_basic_from_db():
    """
    从数据库获取个股列表
    """
    # 使用SQLAlchemy连接（推荐方式）
    query = f"""
    SELECT market, code_int, name
    FROM stock_basic_info 
    WHERE (market = 'sh' AND code_int > 600000 AND code_int < 610000)
       OR (market = 'sz' AND code_int > 0 AND code_int < 310000)
    ORDER BY code_int
    """
    df = pd.read_sql(query, engine)
    # 方法1：简单修复，直接使用code_int作为索引
    df.set_index('code_int', inplace=True)

    return df


def get_trade_calendar_from_db():
    """
    从数据库获取交易日历
    """
    # 使用SQLAlchemy连接（推荐方式）
    query = f"""
    SELECT calendar_date
    FROM trade_calendar 
    WHERE is_trading_day = 1
    ORDER BY calendar_date
    """
    df = pd.read_sql(query, engine)
    # 数据清洗与格式化
    df['calendar_date'] = pd.to_datetime(df['calendar_date']).dt.date
    df.set_index('calendar_date', inplace=True)
    df = df.ffill()  # 前向填充缺失值
    return df

calendar_date = get_trade_calendar_from_db()
# print(calendar_date.head())
print(calendar_date.index[0])
# stock_codes = get_stock_basic_from_db()
# print(stock_codes.head())


# for index, row in stock_codes.iterrows():
#     stock_code = index
#     market = row['market']
#     name = row['name'].replace('*', '')
#     start_date = "2025-10-01"
#     datas = get_stock_data_from_db(stock_code, market, start_date)
#     # 确保股票代码是6位字符串格式
#     if isinstance(stock_code, (int, float)):
#         # 如果是数值类型，补0到6位
#         stock_code_formatted = f"{int(stock_code):06d}"
#     else:
#         # 其他类型转换为字符串
#         stock_code_formatted = str(stock_code).zfill(6)
#     if datas.empty:
#         print(f"股票 {stock_code_formatted} 无数据，跳过")
#         continue
#     print(f"股票代码: {stock_code_formatted}, 名称: {name}")
#     print(datas.head())
#     # 保存文件
#     filename = f"csv/{stock_code_formatted}_{market}_{name}_daily_data.csv"
#     datas.to_csv(filename)
#     print(f"已保存: {filename}")
