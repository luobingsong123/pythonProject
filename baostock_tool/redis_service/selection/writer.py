"""
股池数据写入模块
"""

import redis
from typing import Optional, List
from core.base_service import BaseRedisService
from models.stock_selection import SelectionMessage, SelectionParser, StockInfo
from config.settings import settings


class SelectionWriter(BaseRedisService):
    """股池数据写入器"""
    
    def __init__(
        self, 
        redis_client: Optional[redis.Redis] = None,
        maxlen: Optional[int] = None
    ):
        """
        初始化写入器
        
        Args:
            redis_client: Redis客户端
            maxlen: Stream最大长度，默认使用配置中的值
        """
        super().__init__(redis_client)
        self._maxlen = maxlen or settings.selection.stream_maxlen
    
    def write_selection(
        self,
        date: str,
        batch_id: str,
        strategy_id: str,
        stocks: List[StockInfo],
        total_count: Optional[int] = None,
        version: str = "1.0",
        timestamp: Optional[int] = None
    ) -> str:
        """
        写入选股数据到Stream
        
        Args:
            date: 日期，格式YYYYMMDD
            batch_id: 选股批次ID
            strategy_id: 选股策略ID
            stocks: 股票列表
            total_count: 选股总数，如果为None则使用len(stocks)
            version: 版本号
            timestamp: 毫秒时间戳，如果为None则使用当前时间
            
        Returns:
            str: 写入消息的ID
        """
        from utils.serializer import TimestampUtil
        
        message = SelectionMessage(
            type="stock_selection",
            version=version,
            timestamp=timestamp or TimestampUtil.current_timestamp(),
            batch_id=batch_id,
            strategy_id=strategy_id,
            total_count=total_count or len(stocks),
            stocks=stocks
        )
        
        stream_key = SelectionParser.build_stream_key(date)
        fields = SelectionParser.to_stream_fields(message)
        
        return self._client.xadd(
            stream_key,
            fields,
            maxlen=self._maxlen,
            approximate=True  # 使用近似修剪，更高效
        )
    
    def write_raw(self, stream_key: str, data: str) -> str:
        """
        直接写入数据到Stream
        
        Args:
            stream_key: Stream Key
            data: JSON数据字符串
            
        Returns:
            str: 写入消息的ID
        """
        return self._client.xadd(
            stream_key,
            {"data": data},
            maxlen=self._maxlen,
            approximate=True
        )
    
    def trim_stream(self, date: str, count: int) -> int:
        """
        裁剪Stream保留最近N条
        
        Args:
            date: 日期
            count: 保留的消息数量
            
        Returns:
            int: 裁剪的消息数量
        """
        stream_key = SelectionParser.build_stream_key(date)
        return self._client.xtrim(stream_key, count, approximate=True)
    
    def delete_stream(self, date: str) -> bool:
        """
        删除Stream
        
        Args:
            date: 日期
            
        Returns:
            bool: 是否删除成功
        """
        stream_key = SelectionParser.build_stream_key(date)
        try:
            self._client.delete(stream_key)
            return True
        except Exception:
            return False
    
    def get_stream_info(self, date: str) -> dict:
        """
        获取Stream信息
        
        Args:
            date: 日期
            
        Returns:
            dict: Stream信息
        """
        stream_key = SelectionParser.build_stream_key(date)
        info = self._client.xinfo_stream(stream_key)
        return info
    
    def stream_exists(self, date: str) -> bool:
        """
        检查Stream是否存在
        
        Args:
            date: 日期
            
        Returns:
            bool: 是否存在
        """
        stream_key = SelectionParser.build_stream_key(date)
        return self._client.exists(stream_key) > 0
