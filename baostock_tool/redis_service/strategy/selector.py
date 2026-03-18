"""
选股器 - 整合策略和数据库查询
"""

from typing import List, Optional, Dict, Any
from database.queries import StockQueryService
from database.selection_repository import SelectionRepository
from strategy.base import BaseStrategy, StrategyResult
from strategy.ma_breakthrough import MABreakthroughStrategy
from strategy.ma_volume_strategy import MAVolumeStrategy
from models.stock_selection import (
    StockInfo, BasicInfo, MinuteVolume, TechnicalIndicators, FundamentalData
)


class StockSelector:
    """股票选择器"""
    
    def __init__(
        self,
        query_service: Optional[StockQueryService] = None,
        strategy: Optional[BaseStrategy] = None,
        repository: Optional[SelectionRepository] = None
    ):
        """
        初始化选择器
        
        Args:
            query_service: 查询服务
            strategy: 选股策略
            repository: 选股结果仓库
        """
        self.query_service = query_service or StockQueryService()
        self.strategy = strategy
        self.repository = repository or SelectionRepository()
    
    def create_strategy(self, strategy_id: str, params: Optional[Dict[str, Any]] = None) -> BaseStrategy:
        """
        创建策略实例
        
        Args:
            strategy_id: 策略ID
            params: 策略参数
            
        Returns:
            BaseStrategy: 策略实例
        """
        if strategy_id == "MA10_BREAKTHROUGH":
            return MABreakthroughStrategy(params)
        elif strategy_id == "MA_VOLUME_FILTER":
            return MAVolumeStrategy(params)
        else:
            raise ValueError(f"Unknown strategy: {strategy_id}")
    
    def select(
        self,
        date: str,
        strategy_id: Optional[str] = None,
        count: int = 10,
        market: Optional[str] = None,
        save_to_db: bool = False,
        strategy_params: Optional[Dict[str, Any]] = None
    ) -> List[StockInfo]:
        """
        执行选股
        
        Args:
            date: 日期
            strategy_id: 策略ID
            count: 选股数量
            market: 市场代码
            save_to_db: 是否保存到数据库
            strategy_params: 策略参数
            
        Returns:
            List[StockInfo]: 选股结果
        """
        # 获取日线数据
        print(f"\n[DEBUG] 查询日K线数据: date={date}, market={market}, limit=500")
        daily_data = self.query_service.get_daily_data(date, market, limit=500)
        
        if not daily_data:
            print(f"[DEBUG] 未查到日K线数据")
            return []
        
        # 调试打印：日K线数据样本
        print(f"[DEBUG] 查到 {len(daily_data)} 条日K线数据")
        print(f"[DEBUG] 前3条数据样本:")
        for i, stock in enumerate(daily_data[:3], 1):
            print(f"    [{i}] {stock.get('market')}:{stock.get('code_int')} {stock.get('name')}")
            print(f"        收盘价: {stock.get('close')}, 成交额: {stock.get('amount')}, 换手率: {stock.get('turn')}")
        
        # 如果有策略ID但没有策略实例，创建策略
        if strategy_id and not self.strategy:
            self.strategy = self.create_strategy(strategy_id, strategy_params)
        
        # 如果有策略，使用策略选股
        if self.strategy:
            strategy_results = self.strategy.select(date, daily_data)
            selected = strategy_results[:count]
        else:
            # 无策略时，按成交额取前N
            selected = self._select_top_by_amount(daily_data, count)
        
        # 转换为StockInfo
        stocks = self._convert_to_stock_info(selected, date)
        
        # 保存到数据库
        if save_to_db and stocks:
            self._save_selection_to_db(date, strategy_id or "DEFAULT", stocks, strategy_params)
        
        return stocks
    
    def _save_selection_to_db(
        self,
        date: str,
        strategy_id: str,
        stocks: List[StockInfo],
        strategy_params: Optional[Dict[str, Any]]
    ):
        """
        保存选股结果到数据库
        
        Args:
            date: 日期
            strategy_id: 策略ID
            stocks: 股票列表
            strategy_params: 策略参数
        """
        from models.stock_selection import SelectionMessage
        from utils.serializer import TimestampUtil
        
        batch_id = f"SELECT_{date}_001"
        
        selection = SelectionMessage(
            type="stock_selection",
            version="1.0",
            timestamp=TimestampUtil.current_timestamp(),
            batch_id=batch_id,
            strategy_id=strategy_id,
            total_count=len(stocks),
            stocks=stocks
        )
        
        success = self.repository.save_selection_result(selection, strategy_params)
        if success:
            print(f"✓ 选股结果已保存到数据库: {batch_id}")
        else:
            print(f"✗ 保存选股结果失败: {batch_id}")
    
    def _select_top_by_amount(
        self,
        daily_data: List[Dict[str, Any]],
        count: int
    ) -> List[StrategyResult]:
        """
        按成交额选择前N
        
        Args:
            daily_data: 日线数据
            count: 数量
            
        Returns:
            List[StrategyResult]: 选择结果
        """
        results = []
        
        for stock in daily_data[:count]:
            market = stock.get("market", "")
            code = stock.get("code_int", 0)
            name = stock.get("name", "")
            amount = float(stock.get("amount", 0) or 0)
            
            result = StrategyResult(
                symbol=f"{code:06d}",
                exchange="SSE" if market == "sh" else "SZSE",
                name=name,
                score=amount / 100000000,  # 以亿元为单位
                signals={
                    "amount": amount,
                    "volume": stock.get("volume"),
                    "close": stock.get("close")
                }
            )
            results.append(result)
        
        return results
    
    def _convert_to_stock_info(
        self,
        results: List[StrategyResult],
        date: str
    ) -> List[StockInfo]:
        """
        将策略结果转换为StockInfo
        
        Args:
            results: 策略结果
            date: 日期
            
        Returns:
            List[StockInfo]: 股票信息列表
        """
        stocks = []
        
        for result in results:
            # 获取详细信息
            market_map = {"SSE": "sh", "SZSE": "sz"}
            market = market_map.get(result.exchange, "sh")
            code = int(result.symbol)
            
            # 获取均线
            ma_values = self.query_service.calculate_ma(
                market, code, date, [5, 10, 20]
            )
            
            # 获取近5日最高价
            ma5_high = float(self.query_service.get_ma5_high(market, code, date))
            
            # 获取5天分钟数据
            minute_data_5d = self.query_service.get_minute_data_5d(
                date, market, code, frequency=5
            )
            
            # 获取基本面数据
            daily_data = self.query_service.get_daily_data(date, market, limit=1)
            pe = pb = market_cap = 0
            if daily_data:
                pe = float(daily_data[0].get("peTTM", 0) or 0)
                pb = float(daily_data[0].get("pbMRQ", 0) or 0)
                # 市值估算：收盘价 * 成交量 / 换手率
                close = float(daily_data[0].get("close", 0) or 0)
                volume = float(daily_data[0].get("volume", 0) or 0)
                turn = float(daily_data[0].get("turn", 0) or 0)
                if turn > 0:
                    market_cap = close * volume / turn / 1000000  # 百万
            
            # 构建StockInfo
            stock = StockInfo(
                symbol=result.symbol,
                exchange=result.exchange,
                name=result.name,
                basic_info=BasicInfo(
                    prev_close=float(result.signals.get("close", 0)),
                    ma10=float(ma_values.get(10, 0)),
                    ma5_high=ma5_high,
                    volume_ratio=1.2,  # 简化计算
                    turnover_rate=float(result.signals.get("turnover", 0.5))
                ),
                minute_volume_5d_01=self._convert_minute_data(
                    minute_data_5d[0] if len(minute_data_5d) > 0 else []
                ),
                minute_volume_5d_02=self._convert_minute_data(
                    minute_data_5d[1] if len(minute_data_5d) > 1 else []
                ),
                minute_volume_5d_03=self._convert_minute_data(
                    minute_data_5d[2] if len(minute_data_5d) > 2 else []
                ),
                minute_volume_5d_04=self._convert_minute_data(
                    minute_data_5d[3] if len(minute_data_5d) > 3 else []
                ),
                minute_volume_5d_05=self._convert_minute_data(
                    minute_data_5d[4] if len(minute_data_5d) > 4 else []
                ),
                technical_indicators=TechnicalIndicators(
                    ma5=float(ma_values.get(5, 0)),
                    ma10=float(ma_values.get(10, 0)),
                    ma20=float(ma_values.get(20, 0)),
                    vol_ma5=float(result.signals.get("volume", 0)) * 0.8,
                    vol_ma10=float(result.signals.get("volume", 0)) * 0.9
                ),
                fundamental_data=FundamentalData(
                    pe=pe,
                    pb=pb,
                    market_cap=market_cap
                )
            )
            
            stocks.append(stock)
        
        return stocks
    
    def _convert_minute_data(
        self,
        data: List[Dict[str, Any]]
    ) -> List[MinuteVolume]:
        """
        转换分钟数据格式
        
        Args:
            data: 原始分钟数据
            
        Returns:
            List[MinuteVolume]: 转换后的数据
        """
        result = []
        for item in data:
            time_str = item.get("time", "")
            # 从YYYYMMDDHHMMSSsss格式提取HH:MM
            if len(time_str) >= 12:
                time_formatted = f"{time_str[8:10]}:{time_str[10:12]}"
            else:
                time_formatted = "09:30"
            
            result.append(MinuteVolume(
                time=time_formatted,
                volume=int(item.get("volume", 0))
            ))
        
        return result
