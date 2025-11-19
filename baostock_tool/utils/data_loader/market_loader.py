# utils/data_loader/market_loader.py
import pandas as pd
from sqlalchemy import create_engine
from ..logger_utils.logger_tool import get_logger


# 本代码仅用于回测研究，实盘使用风险自担

class MarketDataLoader:
    def __init__(self, config_path="../config.ini"):
        self.engine = create_engine('mysql+pymysql://root:Root_123@192.168.1.78:3306/baostock_api_market_data')
        self.logger = get_logger(__name__)

    def get_all_stock_codes(self, min_list_date='2010-01-01', exclude_st=True):
        """获取全市场股票代码列表"""
        query = f"""
        SELECT market, code_int, name, list_date, industry
        FROM stock_basic_info 
        WHERE list_date <= '{min_list_date}'
          AND is_hs = 1  -- 只考虑沪深港通标的，提高质量
        """

        if exclude_st:
            query += " AND name NOT LIKE '%ST%' AND name NOT LIKE '%退%'"

        stock_list = pd.read_sql(query, self.engine)
        self.logger.info(f"获取到 {len(stock_list)} 只股票")
        return stock_list

    def get_trading_dates(self, start_date, end_date):
        """获取交易日历"""
        query = f"""
        SELECT calendar_date 
        FROM trade_calendar 
        WHERE calendar_date BETWEEN '{start_date}' AND '{end_date}'
          AND is_trading_day = 1
        ORDER BY calendar_date
        """
        dates = pd.read_sql(query, self.engine)
        return dates['calendar_date'].tolist()