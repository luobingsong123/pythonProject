"""
股票数据查询服务
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from database.connection import DatabasePool, get_db_connection


class StockQueryService:
    """股票数据查询服务"""
    
    def __init__(self, db_pool: Optional[DatabasePool] = None):
        """
        初始化查询服务
        
        Args:
            db_pool: 数据库连接池
        """
        self._db_pool = db_pool
    
    def _get_connection(self):
        """获取数据库连接"""
        if self._db_pool:
            return self._db_pool.connection()
        # 使用全局连接池
        from contextlib import contextmanager
        @contextmanager
        def wrapper():
            conn = get_db_connection()
            try:
                yield conn
            finally:
                # 全局连接池会自动管理
                pass
        return wrapper()
    
    def get_daily_data(
        self,
        date: str,
        market: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取日线数据
        
        Args:
            date: 日期，格式YYYYMMDD
            market: 市场代码(sh/sz)，None表示所有市场
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 日线数据列表
        """
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                if market:
                    sql = """
                        SELECT 
                            market, code_int, `name`,
                            open, high, low, close, preclose,
                            volume, amount, turn, pctChg,
                            peTTM, pbMRQ, isST
                        FROM stock_daily_data d
                        JOIN stock_basic_info b ON d.market = b.market AND d.code_int = b.code_int
                        WHERE date = %s AND d.market = %s
                        ORDER BY amount DESC
                        LIMIT %s
                    """
                    cursor.execute(sql, (formatted_date, market, limit))
                else:
                    sql = """
                        SELECT 
                            d.market, d.code_int, b.`name`,
                            d.open, d.high, d.low, d.close, d.preclose,
                            d.volume, d.amount, d.turn, d.pctChg,
                            d.peTTM, d.pbMRQ, d.isST
                        FROM stock_daily_data d
                        JOIN stock_basic_info b ON d.market = b.market AND d.code_int = b.code_int
                        WHERE d.date = %s
                        ORDER BY d.amount DESC
                        LIMIT %s
                    """
                    cursor.execute(sql, (formatted_date, limit))
                
                return cursor.fetchall()
    
    def get_top_stocks(
        self,
        date: str,
        count: int = 10,
        market: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取当日成交额前N的股票
        
        Args:
            date: 日期
            count: 返回数量
            market: 市场代码
            
        Returns:
            List[Dict]: 股票列表
        """
        return self.get_daily_data(date, market, count)
    
    def get_minute_data(
        self,
        date: str,
        market: str,
        code: int,
        frequency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取分钟线数据
        
        Args:
            date: 日期
            market: 市场代码
            code: 股票代码
            frequency: 频率(5/15/30/60)
            
        Returns:
            List[Dict]: 分钟线数据
        """
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        date, time, market, code_int,
                        open, high, low, close,
                        volume, amount
                    FROM stock_minute_data
                    WHERE date = %s AND market = %s 
                      AND code_int = %s AND frequency = %s
                    ORDER BY time
                """
                cursor.execute(sql, (formatted_date, market, code, frequency))
                return cursor.fetchall()
    
    def get_minute_data_5d(
        self,
        end_date: str,
        market: str,
        code: int,
        frequency: int = 5
    ) -> List[List[Dict[str, Any]]]:
        """
        获取最近5天的分钟线数据
        
        Args:
            end_date: 结束日期
            market: 市场代码
            code: 股票代码
            frequency: 频率
            
        Returns:
            List[List[Dict]]: 5天的分钟线数据，每天一个列表
        """
        # 计算5个交易日的日期
        dates = self._get_trade_dates(end_date, 5)
        
        result = []
        for date in dates:
            day_data = self.get_minute_data(date, market, code, frequency)
            result.append(day_data)
        
        return result
    
    def get_tick_data(
        self,
        date: str,
        market: str,
        code: int
    ) -> List[Dict[str, Any]]:
        """
        获取Tick数据(3秒级)
        
        Args:
            date: 日期
            market: 市场代码
            code: 股票代码
            
        Returns:
            List[Dict]: Tick数据列表
        """
        # 表名格式: level2_3s_YYYYMMDD
        table_name = f"level2_3s_{date}"
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                sql = f"""
                    SELECT 
                        Symbol, TradingDate, TradingTime,
                        PreClosePrice, OpenPrice, HighPrice, LowPrice, LastPrice,
                        TotalVolume, TradeVolume, TotalAmount, TradeAmount,
                        PERatio1, PERatio2,
                        TotalSellOrderVolume, WtAvgSellPrice, SellLevelNo,
                        SellPrice05, SellPrice04, SellPrice03, SellPrice02, SellPrice01,
                        SellVolume05, SellVolume04, SellVolume03, SellVolume02, SellVolume01,
                        TotalBuyOrderVolume, WtAvgBuyPrice, BuyLevelNo,
                        BuyPrice01, BuyPrice02, BuyPrice03, BuyPrice04, BuyPrice05,
                        BuyVolume01, BuyVolume02, BuyVolume03, BuyVolume04, BuyVolume05,
                        UNIX, Market
                    FROM {table_name}
                    WHERE Symbol = %s AND Market = %s
                    ORDER BY TradingTime
                """
                
                # 转换市场代码
                market_code = "SH" if market == "sh" else "SZ"
                symbol = f"{market_code}{code:06d}"
                
                try:
                    cursor.execute(sql, (symbol, market_code))
                    return cursor.fetchall()
                except Exception as e:
                    # 表可能不存在
                    print(f"Error querying tick data: {e}")
                    return []
    
    def get_stock_basic_info(
        self,
        market: str,
        code: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息
        
        Args:
            market: 市场代码
            code: 股票代码
            
        Returns:
            Dict: 股票基本信息
        """
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                    SELECT market, code_int, name, industry, area, list_date
                    FROM stock_basic_info
                    WHERE market = %s AND code_int = %s
                """
                cursor.execute(sql, (market, code))
                return cursor.fetchone()
    
    def _get_trade_dates(self, end_date: str, days: int) -> List[str]:
        """
        获取最近N个交易日日期
        
        Args:
            end_date: 结束日期
            days: 天数
            
        Returns:
            List[str]: 日期列表(YYYYMMDD格式)
        """
        # 简化实现：假设每天都是交易日
        # 实际应该从数据库查询交易日历
        end = datetime.strptime(end_date, "%Y%m%d")
        dates = []
        
        for i in range(days):
            date = end - timedelta(days=i)
            dates.append(date.strftime("%Y%m%d"))
        
        return dates[::-1]  # 正序排列
    
    def calculate_ma(
        self,
        market: str,
        code: int,
        end_date: str,
        periods: List[int] = [5, 10, 20]
    ) -> Dict[int, float]:
        """
        计算均线
        
        Args:
            market: 市场代码
            code: 股票代码
            end_date: 结束日期
            periods: 均线周期列表
            
        Returns:
            Dict[int, float]: 均线值
        """
        max_period = max(periods)
        # 需要获取的数据天数
        days_needed = max_period + 5  # 多取几天确保有足够数据
        
        dates = self._get_trade_dates(end_date, days_needed)
        start_date = dates[0]
        
        formatted_start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        formatted_end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                    SELECT close
                    FROM stock_daily_data
                    WHERE market = %s AND code_int = %s 
                      AND date BETWEEN %s AND %s
                    ORDER BY date DESC
                    LIMIT %s
                """
                cursor.execute(sql, (market, code, formatted_start, formatted_end, days_needed))
                rows = cursor.fetchall()
                
                # 将 Decimal 转换为 float
                closes = [float(row["close"]) for row in rows]
                
                result = {}
                for period in periods:
                    if len(closes) >= period:
                        result[period] = sum(closes[:period]) / period
                    else:
                        result[period] = closes[0] if closes else 0.0
                
                return result
    
    def get_ma5_high(
        self,
        market: str,
        code: int,
        end_date: str
    ) -> float:
        """
        获取近5日最高价
        
        Args:
            market: 市场代码
            code: 股票代码
            end_date: 结束日期
            
        Returns:
            float: 近5日最高价
        """
        dates = self._get_trade_dates(end_date, 5)
        start_date = dates[0]
        
        formatted_start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        formatted_end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                    SELECT MAX(high) as max_high
                    FROM stock_daily_data
                    WHERE market = %s AND code_int = %s 
                      AND date BETWEEN %s AND %s
                """
                cursor.execute(sql, (market, code, formatted_start, formatted_end))
                row = cursor.fetchone()
                return float(row["max_high"]) if row and row["max_high"] else 0.0
