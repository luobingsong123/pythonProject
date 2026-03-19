"""
均线成交量策略

选股条件：
1. 市值低于200亿
2. 60日均线和20日均线单调性一致，斜率大于0°，小于30°
3. 60日内最大成交量和最小成交量之比小于等于3
"""

import math
import logging
from typing import List, Dict, Any, Optional
from strategy.base import BaseStrategy, StrategyResult
from database.queries import StockQueryService

logger = logging.getLogger(__name__)


class MAVolumeStrategy(BaseStrategy):
    """
    均线成交量策略
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化策略
        
        Args:
            params: 策略参数
                - max_market_cap: 最大市值（百万），默认200000（200亿）
                - min_slope_angle: 最小斜率角度，默认0°
                - max_slope_angle: 最大斜率角度，默认30°
                - ma_short_period: 短期均线周期，默认20
                - ma_long_period: 长期均线周期，默认60
                - volume_lookback: 成交量回看天数，默认60
                - max_volume_ratio: 最大成交量比，默认3
        """
        super().__init__("MA_VOLUME_FILTER", params)
        
        self.max_market_cap = self.params.get("max_market_cap", 200000)  # 200亿 = 200000百万
        self.min_slope_angle = self.params.get("min_slope_angle", 0)
        self.max_slope_angle = self.params.get("max_slope_angle", 30)
        self.ma_short_period = self.params.get("ma_short_period", 20)
        self.ma_long_period = self.params.get("ma_long_period", 60)
        self.volume_lookback = self.params.get("volume_lookback", 60)
        self.max_volume_ratio = self.params.get("max_volume_ratio", 3)
        
        self.query_service = StockQueryService()
    
    def select(
        self,
        date: str,
        daily_data: List[Dict[str, Any]],
        **kwargs
    ) -> List[StrategyResult]:
        """
        执行选股
        
        Args:
            date: 日期
            daily_data: 日线数据列表
            
        Returns:
            List[StrategyResult]: 选股结果
        """
        results = []
        
        for stock in daily_data:
            # 基础过滤
            if not self.filter(stock):
                continue
            
            market = stock.get("market", "")
            code = stock.get("code_int", 0)
            name = stock.get("name", "")
            
            # 获取详细数据进行策略判断
            if self._check_strategy_conditions(market, code, date, stock):
                # 计算得分（可以基于多个因子）
                score = self._calculate_score(stock)
                
                # 获取均线值用于输出
                ma_values = self.query_service.calculate_ma(
                    market, code, date, 
                    [self.ma_short_period, self.ma_long_period]
                )
                
                # 获取成交量统计
                volume_stats = self._get_volume_stats(market, code, date)
                
                result = StrategyResult(
                    symbol=f"{code:06d}",
                    exchange="SSE" if market == "sh" else "SZSE",
                    name=name,
                    score=score,
                    signals={
                        f"ma{self.ma_short_period}": ma_values.get(self.ma_short_period, 0),
                        f"ma{self.ma_long_period}": ma_values.get(self.ma_long_period, 0),
                        "market_cap": self._calculate_market_cap(stock),
                        "volume_max": volume_stats.get("max", 0),
                        "volume_min": volume_stats.get("min", 0),
                        "volume_ratio": volume_stats.get("ratio", 0),
                        "close": stock.get("close"),
                        "volume": stock.get("volume")
                    }
                )
                results.append(result)
        
        # 按得分排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def filter(self, stock_data: Dict[str, Any]) -> bool:
        """
        单只股票基础过滤
        
        Args:
            stock_data: 股票数据
            
        Returns:
            bool: 是否通过过滤
        """
        # 排除ST股
        if stock_data.get("isST") == 1:
            return False
        
        # 排除停牌股
        if stock_data.get("tradestatus") == 0:
            return False
        
        # 必须有收盘价和成交量数据
        if not stock_data.get("close") or not stock_data.get("volume"):
            return False
        
        return True
    
    def _check_strategy_conditions(
        self,
        market: str,
        code: int,
        date: str,
        stock_data: Dict[str, Any]
    ) -> bool:
        """
        检查策略条件
        
        Args:
            market: 市场代码
            code: 股票代码
            date: 日期
            stock_data: 股票数据
            
        Returns:
            bool: 是否满足所有条件
        """
        # 条件1: 市值低于200亿
        market_cap = self._calculate_market_cap(stock_data)
        if market_cap >= self.max_market_cap:
            return False
        
        # 条件2: 均线斜率检查
        if not self._check_ma_slope(market, code, date):
            return False
        
        # 条件3: 成交量比检查
        if not self._check_volume_ratio(market, code, date):
            return False
        
        return True
    
    def _calculate_market_cap(self, stock_data: Dict[str, Any]) -> float:
        """
        计算市值（百万）
        
        Args:
            stock_data: 股票数据
            
        Returns:
            float: 市值（百万）
        """
        close = float(stock_data.get("close", 0) or 0)
        volume = float(stock_data.get("volume", 0) or 0)
        turn = float(stock_data.get("turn", 0) or 0)
        
        if turn > 0:
            # 市值 = 收盘价 * 总股本
            # 总股本 ≈ 成交量 / 换手率
            market_cap = close * volume / turn / 1000000  # 转换为百万
            return market_cap
        
        return float('inf')  # 无法计算时返回无穷大
    
    def _check_ma_slope(self, market: str, code: int, date: str) -> bool:
        """
        检查均线斜率
        
        条件：
        - 60日均线和20日均线单调性一致（同涨或同跌）
        - 斜率大于0°，小于30°
        
        Args:
            market: 市场代码
            code: 股票代码
            date: 日期
            
        Returns:
            bool: 是否满足条件
        """
        # 获取历史数据计算均线序列
        # 需要至少ma_long_period + 10天的数据
        days_needed = self.ma_long_period + 10
        
        from datetime import datetime, timedelta
        end = datetime.strptime(date, "%Y%m%d")
        start = end - timedelta(days=days_needed * 2)  # 多取一些天数
        
        formatted_start = start.strftime("%Y-%m-%d")
        formatted_end = end.strftime("%Y-%m-%d")
        
        # 获取历史收盘价
        import pymysql
        from database.connection import get_db_connection
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT date, close
                    FROM stock_daily_data
                    WHERE market = %s AND code_int = %s 
                      AND date BETWEEN %s AND %s
                    ORDER BY date ASC
                """
                cursor.execute(sql, (market, code, formatted_start, formatted_end))
                rows = cursor.fetchall()
                
                if len(rows) < self.ma_long_period + 5:
                    return False
                
                closes = [float(row["close"]) for row in rows]
                
                # 计算均线序列
                ma_short_series = self._calculate_ma_series(closes, self.ma_short_period)
                ma_long_series = self._calculate_ma_series(closes, self.ma_long_period)
                
                if len(ma_short_series) < 5 or len(ma_long_series) < 5:
                    return False
                
                # 取最近5个均线值计算斜率
                short_recent = ma_short_series[-5:]
                long_recent = ma_long_series[-5:]
                
                # 计算斜率（使用线性回归）
                short_slope = self._calculate_slope(short_recent)
                long_slope = self._calculate_slope(long_recent)
                
                # 检查单调性一致性（同号）
                if short_slope * long_slope <= 0:
                    return False
                
                # 检查斜率角度（转换为角度）
                short_angle = math.degrees(math.atan(abs(short_slope)))
                long_angle = math.degrees(math.atan(abs(long_slope)))
                
                if not (self.min_slope_angle <= short_angle <= self.max_slope_angle):
                    return False
                
                if not (self.min_slope_angle <= long_angle <= self.max_slope_angle):
                    return False
                
                return True
                
        except Exception as e:
            logger.warning(f"检查均线斜率失败 {market}:{code}: {e}")
            return False
    
    def _calculate_ma_series(self, prices: List[float], period: int) -> List[float]:
        """
        计算均线序列
        
        Args:
            prices: 价格列表
            period: 均线周期
            
        Returns:
            List[float]: 均线序列
        """
        ma_series = []
        for i in range(period - 1, len(prices)):
            ma = sum(prices[i - period + 1:i + 1]) / period
            ma_series.append(ma)
        return ma_series
    
    def _calculate_slope(self, values: List[float]) -> float:
        """
        计算斜率（简单线性回归）
        
        Args:
            values: 数值列表
            
        Returns:
            float: 斜率
        """
        n = len(values)
        if n < 2:
            return 0
        
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0
        
        return numerator / denominator
    
    def _check_volume_ratio(self, market: str, code: int, date: str) -> bool:
        """
        检查成交量比
        
        条件：60日内最大成交量和最小成交量之比 <= 3
        
        Args:
            market: 市场代码
            code: 股票代码
            date: 日期
            
        Returns:
            bool: 是否满足条件
        """
        volume_stats = self._get_volume_stats(market, code, date)
        
        if volume_stats["min"] == 0:
            return False
        
        ratio = volume_stats["max"] / volume_stats["min"]
        return ratio <= self.max_volume_ratio
    
    def _get_volume_stats(
        self,
        market: str,
        code: int,
        date: str
    ) -> Dict[str, float]:
        """
        获取成交量统计
        
        Args:
            market: 市场代码
            code: 股票代码
            date: 日期
            
        Returns:
            Dict: 包含max, min, ratio的统计信息
        """
        from datetime import datetime, timedelta
        
        end = datetime.strptime(date, "%Y%m%d")
        start = end - timedelta(days=self.volume_lookback * 2)
        
        formatted_start = start.strftime("%Y-%m-%d")
        formatted_end = end.strftime("%Y-%m-%d")
        
        import pymysql
        from database.connection import get_db_connection
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT volume
                    FROM stock_daily_data
                    WHERE market = %s AND code_int = %s 
                      AND date BETWEEN %s AND %s
                    ORDER BY date DESC
                    LIMIT %s
                """
                cursor.execute(sql, (market, code, formatted_start, formatted_end, self.volume_lookback))
                rows = cursor.fetchall()
                
                if not rows:
                    return {"max": 0, "min": 1, "ratio": float('inf')}
                
                volumes = [float(row["volume"]) for row in rows if row["volume"] > 0]
                
                if not volumes:
                    return {"max": 0, "min": 1, "ratio": float('inf')}
                
                return {
                    "max": max(volumes),
                    "min": min(volumes),
                    "ratio": max(volumes) / min(volumes)
                }
                
        except Exception as e:
            logger.warning(f"获取成交量统计失败 {market}:{code}: {e}")
            return {"max": 0, "min": 1, "ratio": float('inf')}
    
    def _calculate_score(self, stock_data: Dict[str, Any]) -> float:
        """
        计算股票得分
        
        Args:
            stock_data: 股票数据
            
        Returns:
            float: 得分
        """
        # 可以基于多个因子计算得分
        # 这里简化处理，基于市值越小得分越高
        market_cap = self._calculate_market_cap(stock_data)
        
        # 市值得分（越小越好）
        cap_score = max(0, (self.max_market_cap - market_cap) / self.max_market_cap * 100)
        
        # 涨跌幅得分
        pct_chg = float(stock_data.get("pctChg", 0) or 0)
        change_score = max(0, pct_chg)
        
        # 综合得分
        score = cap_score * 0.6 + change_score * 0.4
        
        return score
