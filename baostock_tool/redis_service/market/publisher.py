"""
行情快照发布器模块
"""

import redis
from typing import Optional
from core.base_service import BaseRedisService
from models.snapshot import SnapshotData, SnapshotParser
from config.settings import settings
from models.snapshot import MarketQuote
from utils.serializer import TimestampUtil

class SnapshotPublisher(BaseRedisService):
    """行情快照发布器"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        初始化发布器
        
        Args:
            redis_client: Redis客户端
        """
        super().__init__(redis_client)
        self._parser = SnapshotParser()
    
    def publish(self, snapshot: SnapshotData) -> int:
        """
        发布行情快照
        
        Args:
            snapshot: 行情快照数据对象
            
        Returns:
            int: 接收消息的订阅者数量
        """
        channel = snapshot.get_channel()
        message = SnapshotParser.to_json(snapshot)
        return self._client.publish(channel, message)
    
    def publish_raw(self, channel: str, message: str) -> int:
        """
        直接发布消息到指定通道
        
        Args:
            channel: 通道名
            message: JSON消息字符串
            
        Returns:
            int: 接收消息的订阅者数量
        """
        return self._client.publish(channel, message)
    
    def build_and_publish(
        self,
        exchange: str,
        symbol: str,
        last_price: float,
        volume: int,
        amount: float,
        bid_price: list,
        bid_volume: list,
        ask_price: list,
        ask_volume: list,
        date: str,
        timestamp: str,
        timestamp_ms: Optional[int] = None
    ) -> int:
        """
        构建并发布行情快照
        
        Args:
            exchange: 交易所代码
            symbol: 股票代码
            last_price: 最新价
            volume: 成交量
            amount: 成交额
            bid_price: 买价列表
            bid_volume: 买量列表
            ask_price: 卖价列表
            ask_volume: 卖量列表
            date: 日期
            timestamp: 时间
            timestamp_ms: 毫秒时间戳，如果为None则使用当前时间
            
        Returns:
            int: 接收消息的订阅者数量
        """
        
        snapshot = SnapshotData(
            type="snapshot",
            timestamp=timestamp_ms or TimestampUtil.current_timestamp(),
            exchange=exchange,
            symbol=symbol,
            data=MarketQuote(
                last_price=last_price,
                volume=volume,
                amount=amount,
                bid_price=bid_price,
                bid_volume=bid_volume,
                ask_price=ask_price,
                ask_volume=ask_volume,
                date=date,
                timestamp=timestamp
            )
        )
        return self.publish(snapshot)
    
    def publish_to_pattern(self, pattern: str, message: str) -> int:
        """
        发布消息到匹配模式的所有通道
        
        注意：Pub/Sub模式不支持发布到模式通道，
        此方法仅用于批量发布到多个具体通道
        
        Args:
            pattern: 通道模式（目前会被忽略）
            message: JSON消息
            
        Returns:
            int: 总接收者数量
        """
        # Pub/Sub不直接支持模式发布，这里需要遍历发布
        # 实际使用中建议使用具体通道名
        raise NotImplementedError(
            "Pub/Sub does not support publishing to patterns. "
            "Please use publish() with specific channel."
        )
