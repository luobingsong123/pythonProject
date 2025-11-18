import pandas as pd
import backtrader as bt
import matplotlib.pyplot as plt


# 本代码仅用于回测研究，实盘使用风险自担

# 1. SQL数据查询（示例查询单只股票）
def get_stock_data_from_db(stock_code="000001", market="sz", start_date="2020-01-01"):
    """
    从数据库提取单只股票历史数据
    """
    # 实际使用时替换为您的数据库连接
    import pymysql

    # 数据库连接（请根据实际情况修改参数）
    conn = pymysql.connect(host='localhost', user='username',
                           password='password', database='stock_db')

    query = f"""
    SELECT date, open, high, low, close, volume, amount, pctChg
    FROM stock_daily_data 
    WHERE market = '{market}' 
      AND code_int = {stock_code}
      AND frequency = 'd'
      AND date >= '{start_date}'
    ORDER BY date
    """

    df = pd.read_sql(query, conn)
    conn.close()

    # 数据清洗与格式化
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df.fillna(method='ffill', inplace=True)  # 前向填充缺失值

    return df


# 测试数据提取
stock_data = get_stock_data_from_db("000001", "sz")  # 以平安银行为例
print(f"数据量：{len(stock_data)}条")
print(stock_data.head())