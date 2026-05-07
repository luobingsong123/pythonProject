"""
均线突破策略
"""

from typing import List, Dict, Any, Optional
from baostock_tool.redis_service.strategy.base import BaseStrategy, StrategyResult
from baostock_tool.redis_service.database.queries import StockQueryService


class MABreakthroughStrategy(BaseStrategy):
    """
    MA10突破策略
    当收盘价突破10日均线时入选
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化策略
        
        Args:
            params: 策略参数
                - ma_period: 均线周期，默认10
                - volume_ratio_min: 最小量比，默认1.0
                - turnover_min: 最小换手率，默认0.3
        """
        super().__init__("MA10_BREAKTHROUGH", params)
        self.ma_period = self.params.get("ma_period", 10)
        self.volume_ratio_min = self.params.get("volume_ratio_min", 1.0)
        self.turnover_min = self.params.get("turnover_min", 0.3)
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
            
            # 计算均线
            ma_values = self.query_service.calculate_ma(
                market, code, date, [self.ma_period]
            )
            
            ma = float(ma_values.get(self.ma_period, 0))
            close = float(stock.get("close", 0))
            preclose = float(stock.get("preclose", 0))
            
            # 突破条件：当日收盘价突破MA10
            if close > ma and preclose <= ma:
                score = (close - ma) / ma * 100  # 突破幅度作为得分
                
                result = StrategyResult(
                    symbol=f"{code:06d}",
                    exchange="SSE" if market == "sh" else "SZSE",
                    name=name,
                    score=score,
                    signals={
                        "ma10": ma,
                        "close": close,
                        "breakthrough": True,
                        "volume": stock.get("volume"),
                        "turnover": stock.get("turn")
                    }
                )
                results.append(result)
        
        # 按得分排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def filter(self, stock_data: Dict[str, Any]) -> bool:
        """
        单只股票过滤
        
        Args:
            stock_data: 股票数据
            
        Returns:
            bool: 是否通过过滤
        """
        # 排除ST股
        if stock_data.get("isST") == 1:
            return False
        
        # 换手率过滤
        turnover = float(stock_data.get("turn", 0) or 0)
        if turnover < self.turnover_min:
            return False
        
        # 成交额过滤（至少1000万）
        amount = float(stock_data.get("amount", 0) or 0)
        if amount < 10000000:
            return False
        
        return True
