"""
股票数据查询服务
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from database.connection import DatabasePool, get_db_connection
from config.settings import settings


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
        from .connection import get_db_connection, release_db_connection

        @contextmanager
        def wrapper():
            conn = get_db_connection()
            try:
                yield conn
            finally:
                release_db_connection(conn)
        return wrapper()
    
    def get_daily_data(
        self,
        date: str,
        market: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取日线数据（仅股票，排除指数）
        
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
                # 股票代码范围（排除指数）
                # 沪市股票: 600000-689999
                # 深市股票: 000001-002999, 300001-301999
                if market:
                    sql = """
                        SELECT 
                            d.market, d.code_int, b.`name`,
                            d.open, d.high, d.low, d.close, d.preclose,
                            d.volume, d.amount, d.turn, d.pctChg,
                            d.peTTM, d.pbMRQ, d.isST
                        FROM stock_daily_data d
                        JOIN stock_basic_info b ON d.market = b.market AND d.code_int = b.code_int
                        WHERE d.date = %s AND d.market = %s
                          AND (
                            (d.market = 'sh' AND d.code_int BETWEEN 600000 AND 689999)
                            OR (d.market = 'sz' AND (
                                d.code_int BETWEEN 1 AND 2999
                                OR d.code_int BETWEEN 300001 AND 301999
                            ))
                          )
                        ORDER BY d.amount DESC
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
                          AND (
                            (d.market = 'sh' AND d.code_int BETWEEN 600000 AND 689999)
                            OR (d.market = 'sz' AND (
                                d.code_int BETWEEN 1 AND 2999
                                OR d.code_int BETWEEN 300001 AND 301999
                            ))
                          )
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
            List[Dict]: 分钟线数据，查不到时返回全-1数据
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
                result = cursor.fetchall()
                
                # 查不到数据时返回全-1数据
                if not result:
                    return self._generate_empty_minute_data(date, frequency)
                
                return result
    
    def _generate_empty_minute_data(self, date: str, frequency: int = 5) -> List[Dict[str, Any]]:
        """
        生成空的分钟线数据（全-1）
        
        Args:
            date: 日期
            frequency: 频率
            
        Returns:
            List[Dict]: 全-1的分钟线数据
        """
        result = []
        # 5分钟线时间点：9:30-11:30, 13:00-15:00
        # 上午：9:30, 9:35, ..., 11:30 (24个点)
        # 下午：13:00, 13:05, ..., 15:00 (24个点)
        
        intervals = frequency  # 分钟间隔
        
        # 上午时段 9:30-11:30
        for hour in range(9, 12):
            start_min = 30 if hour == 9 else 0
            end_min = 60 if hour < 11 else 30
            for minute in range(start_min, end_min, intervals):
                time_str = f"{date}{hour:02d}{minute:02d}00"
                result.append({
                    "date": date,
                    "time": time_str,
                    "open": -1,
                    "high": -1,
                    "low": -1,
                    "close": -1,
                    "volume": -1,
                    "amount": -1
                })
        
        # 下午时段 13:00-15:00
        for hour in range(13, 15):
            for minute in range(0, 60, intervals):
                time_str = f"{date}{hour:02d}{minute:02d}00"
                result.append({
                    "date": date,
                    "time": time_str,
                    "open": -1,
                    "high": -1,
                    "low": -1,
                    "close": -1,
                    "volume": -1,
                    "amount": -1
                })
        
        # 15:00
        result.append({
            "date": date,
            "time": f"{date}150000",
            "open": -1,
            "high": -1,
            "low": -1,
            "close": -1,
            "volume": -1,
            "amount": -1
        })
        
        return result
    
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

                # 验证表是否存在
                check_table_sql = f"SHOW TABLES LIKE '{table_name}'"
                cursor.execute(check_table_sql)
                table_exists = cursor.fetchone()
                if not table_exists:
                    print(f"    [DEBUG] 表不存在: {table_name}")
                    return []

                # 检查表中的 Market 值（调试用）
                check_market_sql = f"SELECT DISTINCT Market FROM {table_name} LIMIT 10"
                cursor.execute(check_market_sql)
                market_rows = cursor.fetchall()
                market_values = [row['Market'] if 'Market' in row else row for row in market_rows]
                print(f"    [DEBUG] 表中Market值: {market_values}")

                # 转换市场代码（保持与数据库一致）
                # 根据你的手动查询，数据库使用的是 SZSE 而不是 SZ
                market_code = "SSE" if market == "sh" else "SZSE"
                symbol = f"{code:06d}"  # 只有6位代码，不加前缀

                try:
                    print(f"    [DEBUG] 查询Tick SQL: {sql}")
                    print(f"    [DEBUG] 查询参数: Symbol={symbol}, Market={market_code}")
                    cursor.execute(sql, (symbol, market_code))
                    result = cursor.fetchall()
                    print(f"    [DEBUG] 查询结果数量: {len(result)}")
                    return result
                except Exception as e:
                    # 表可能不存在
                    print(f"    [DEBUG] 查询Tick数据异常: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
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
    
    def _get_trade_dates(self, end_date: str, days: int, preload: bool = False) -> List[str]:
        """
        获取最近N个交易日日期
        
        Args:
            end_date: 结束日期
            days: 天数
            preload: 是否启用预加载（开始日期提前 preload_days * 1.68 个交易日）
            
        Returns:
            List[str]: 日期列表(YYYYMMDD格式)
        """
        # 简化实现：假设每天都是交易日
        # 实际应该从数据库查询交易日历
        end = datetime.strptime(end_date, "%Y%m%d")
        
        if preload and days > 0:
            # 预加载：开始日期提前 preload_days * 1.68 个交易日
            preload_offset = math.ceil(settings.backtest.preload_days * 1.68)
            days = days + preload_offset
        
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
        
        # 启用预加载
        dates = self._get_trade_dates(end_date, days_needed, preload=True)
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
        # 启用预加载
        dates = self._get_trade_dates(end_date, 5, preload=True)
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
