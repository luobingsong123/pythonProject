# utils/data_loader/stock_loader.py
import pandas as pd
import backtrader as bt
from ..logger_utils.logger_tool import get_logger


class StockDataLoader:
    def __init__(self):
        self.engine = create_engine('mysql+pymysql://root:Root_123@192.168.1.78:3306/baostock_api_market_data')
        self.logger = get_logger(__name__)

    def load_single_stock_data(self, market, code_int, start_date, end_date):
        """加载单只股票数据"""
        query = f"""
        SELECT date, open, high, low, close, volume, amount, pctChg
        FROM stock_daily_data 
        WHERE market = '{market}' 
          AND code_int = {code_int}
          AND frequency = 'd'
          AND date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY date
        """

        try:
            df = pd.read_sql(query, self.engine)
            if len(df) == 0:
                return None

            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df.ffill()

            # 转换为backtrader数据格式
            data = bt.feeds.PandasData(
                dataname=df,
                datetime=None,
                open='open', high='high', low='low', close='close',
                volume='volume', openinterest=-1
            )

            return data

        except Exception as e:
            self.logger.error(f"加载股票{market}{code_int}数据失败: {e}")
            return None