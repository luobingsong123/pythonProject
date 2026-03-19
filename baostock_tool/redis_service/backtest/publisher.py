"""
Tick数据发布器
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from database.queries import StockQueryService
from market.publisher import SnapshotPublisher
from models.snapshot import SnapshotData, MarketQuote
from utils.serializer import TimestampUtil

logger = logging.getLogger(__name__)


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
            # 查不到数据时，推送一天全-1的数据
            logger.debug(f"未查到Tick数据，生成空数据推送: {market}:{code}")
            tick_data = self._generate_empty_tick_data(date)
        else:
            logger.debug(f"查到 {len(tick_data)} 条Tick数据: {market}:{code}")
        
        count = 0
        
        # 发布每条Tick数据
        for tick in tick_data:
            snapshot = self._convert_tick_to_snapshot(
                tick, date, exchange, symbol
            )
            
            if snapshot:
                self.publisher.publish(snapshot)
                count += 1
        
        logger.debug(f"推送Tick数据完成: {exchange}:{symbol}, 数量={count}")
        return count
    
    def _generate_empty_tick_data(self, date: str) -> List[Dict[str, Any]]:
        """
        生成一天的空Tick数据（全-1）
        
        Args:
            date: 日期 YYYYMMDD
            
        Returns:
            List[Dict]: 全-1的tick数据列表
        """
        result = []
        
        # 交易时段：9:30-11:30, 13:00-15:00
        # 每3秒一条
        year = int(date[:4])
        month = int(date[4:6])
        day = int(date[6:8])
        
        base_date = datetime(year, month, day)
        
        # 上午时段 9:30-11:30
        start_am = base_date.replace(hour=9, minute=30, second=0)
        end_am = base_date.replace(hour=11, minute=30, second=0)
        
        current = start_am
        while current <= end_am:
            result.append(self._create_empty_tick(current))
            current += timedelta(seconds=3)
        
        # 下午时段 13:00-15:00
        start_pm = base_date.replace(hour=13, minute=0, second=0)
        end_pm = base_date.replace(hour=15, minute=0, second=0)
        
        current = start_pm
        while current <= end_pm:
            result.append(self._create_empty_tick(current))
            current += timedelta(seconds=3)
        
        return result
    
    def _create_empty_tick(self, dt: datetime) -> Dict[str, Any]:
        """
        创建单条空tick数据
        
        Args:
            dt: 时间
            
        Returns:
            Dict: 空tick数据
        """
        return {
            "TradingTime": dt.strftime("%Y%m%d%H%M%S"),
            "PreClosePrice": -1,
            "OpenPrice": -1,
            "HighPrice": -1,
            "LowPrice": -1,
            "LastPrice": -1,
            "TotalVolume": -1,
            "TradeVolume": -1,
            "TotalAmount": -1,
            "TradeAmount": -1,
            "BuyPrice01": -1,
            "BuyPrice02": -1,
            "BuyPrice03": -1,
            "BuyPrice04": -1,
            "BuyPrice05": -1,
            "BuyVolume01": -1,
            "BuyVolume02": -1,
            "BuyVolume03": -1,
            "BuyVolume04": -1,
            "BuyVolume05": -1,
            "SellPrice01": -1,
            "SellPrice02": -1,
            "SellPrice03": -1,
            "SellPrice04": -1,
            "SellPrice05": -1,
            "SellVolume01": -1,
            "SellVolume02": -1,
            "SellVolume03": -1,
            "SellVolume04": -1,
            "SellVolume05": -1
        }
    
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
            logger.warning(f"Tick转换失败: {e}")
            return None
    
    def close(self):
        """关闭发布器"""
        if self.publisher:
            self.publisher.close()
