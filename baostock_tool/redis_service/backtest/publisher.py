"""
Tick数据发布器
"""

from typing import Optional, List, Dict, Any
from database.queries import StockQueryService
from market.publisher import SnapshotPublisher
from models.snapshot import SnapshotData, MarketQuote
from utils.serializer import TimestampUtil


class TickDataPublisher:
    """Tick数据发布器"""
    
    def __init__(
        self,
        query_service: Optional[StockQueryService] = None,
        snapshot_publisher: Optional[SnapshotPublisher] = None
    ):
        """
        初始化发布器
        
        Args:
            query_service: 查询服务
            snapshot_publisher: 行情发布器
        """
        self.query_service = query_service or StockQueryService()
        self.publisher = snapshot_publisher or SnapshotPublisher()
    
    def publish_tick_data(
        self,
        date: str,
        market: str,
        code: int,
        exchange: str,
        symbol: str
    ) -> int:
        """
        发布Tick数据
        
        Args:
            date: 日期
            market: 市场代码(sh/sz)
            code: 股票代码
            exchange: 交易所代码(SSE/SZSE)
            symbol: 股票代码(6位)
            
        Returns:
            int: 发布的消息数量
        """
        # 获取Tick数据
        tick_data = self.query_service.get_tick_data(date, market, code)
        
        if not tick_data:
            print(f"    No tick data found for {exchange}:{symbol} on {date}")
            return 0
        
        count = 0
        
        # 发布每条Tick数据
        for tick in tick_data:
            snapshot = self._convert_tick_to_snapshot(
                tick, date, exchange, symbol
            )
            
            if snapshot:
                self.publisher.publish(snapshot)
                count += 1
        
        return count
    
    def _convert_tick_to_snapshot(
        self,
        tick: Dict[str, Any],
        date: str,
        exchange: str,
        symbol: str
    ) -> Optional[SnapshotData]:
        """
        将Tick数据转换为行情快照
        
        Args:
            tick: Tick数据
            date: 日期
            exchange: 交易所代码
            symbol: 股票代码
            
        Returns:
            SnapshotData: 行情快照
        """
        try:
            # 解析时间
            trading_time = tick.get("TradingTime")
            if isinstance(trading_time, str):
                dt = TimestampUtil.parse_timestamp(trading_time)
                time_str = dt.strftime("%H:%M:%S")
                timestamp_ms = int(dt.timestamp() * 1000)
            else:
                time_str = "09:30:00"
                timestamp_ms = TimestampUtil.current_timestamp()
            
            # 构建买卖盘
            bid_prices = [
                float(tick.get("BuyPrice01", 0) or 0),
                float(tick.get("BuyPrice02", 0) or 0),
                float(tick.get("BuyPrice03", 0) or 0),
                float(tick.get("BuyPrice04", 0) or 0),
                float(tick.get("BuyPrice05", 0) or 0)
            ]
            
            bid_volumes = [
                int(tick.get("BuyVolume01", 0) or 0),
                int(tick.get("BuyVolume02", 0) or 0),
                int(tick.get("BuyVolume03", 0) or 0),
                int(tick.get("BuyVolume04", 0) or 0),
                int(tick.get("BuyVolume05", 0) or 0)
            ]
            
            ask_prices = [
                float(tick.get("SellPrice01", 0) or 0),
                float(tick.get("SellPrice02", 0) or 0),
                float(tick.get("SellPrice03", 0) or 0),
                float(tick.get("SellPrice04", 0) or 0),
                float(tick.get("SellPrice05", 0) or 0)
            ]
            
            ask_volumes = [
                int(tick.get("SellVolume01", 0) or 0),
                int(tick.get("SellVolume02", 0) or 0),
                int(tick.get("SellVolume03", 0) or 0),
                int(tick.get("SellVolume04", 0) or 0),
                int(tick.get("SellVolume05", 0) or 0)
            ]
            
            # 构建行情快照
            snapshot = SnapshotData(
                type="snapshot",
                timestamp=timestamp_ms,
                exchange=exchange,
                symbol=symbol,
                data=MarketQuote(
                    last_price=float(tick.get("LastPrice", 0) or 0),
                    volume=int(tick.get("TotalVolume", 0) or 0),
                    amount=float(tick.get("TotalAmount", 0) or 0),
                    bid_price=bid_prices,
                    bid_volume=bid_volumes,
                    ask_price=ask_prices,
                    ask_volume=ask_volumes,
                    date=date,
                    timestamp=time_str
                )
            )
            
            return snapshot
            
        except Exception as e:
            print(f"Error converting tick to snapshot: {e}")
            return None
    
    def close(self):
        """关闭发布器"""
        if self.publisher:
            self.publisher.close()
