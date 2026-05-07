"""
股池数据写入模块
"""

import logging
import redis
from typing import Optional, List
from baostock_tool.redis_service.core.base_service import BaseRedisService
from baostock_tool.redis_service.models.stock_selection import SelectionMessage, SelectionParser, StockInfo
from baostock_tool.redis_service.config.settings import settings

logger = logging.getLogger(__name__)


class SelectionWriter(BaseRedisService):
    """股池数据写入器"""
    
    def __init__(
        self, 
        redis_client: Optional[redis.Redis] = None,
        maxlen: Optional[int] = None,
        data_structure: Optional[str] = None,
        expire_seconds: Optional[int] = None
    ):
        """
        初始化写入器
        
        Args:
            redis_client: Redis客户端
            maxlen: 最大长度，默认使用配置中的值
            data_structure: 数据结构类型 "stream" 或 "list"，默认使用配置中的值
            expire_seconds: Key过期时间（秒），默认使用配置中的值
        """
        super().__init__(redis_client)
        self._maxlen = maxlen or settings.selection.maxlen
        self._data_structure = (data_structure or settings.selection.data_structure).lower()
        self._key_prefix = settings.selection.key_prefix
        self._expire_seconds = expire_seconds or settings.selection.expire_seconds
        
        if self._data_structure not in ['stream', 'list']:
            logger.warning(f"不支持的数据结构类型: {self._data_structure}，使用默认值 'stream'")
            self._data_structure = 'stream'
    
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
        写入选股数据
        
        Args:
            date: 日期，格式YYYYMMDD
            batch_id: 选股批次ID
            strategy_id: 选股策略ID
            stocks: 股票列表
            total_count: 选股总数，如果为None则使用len(stocks)
            version: 版本号
            timestamp: 毫秒时间戳，如果为None则使用当前时间
            
        Returns:
            str: 写入消息的ID (Stream模式返回消息ID，List模式返回 "list:{index}")
        """
        from baostock_tool.redis_service.utils.serializer import TimestampUtil
        import json
        
        message = SelectionMessage(
            type="stock_selection",
            version=version,
            timestamp=timestamp or TimestampUtil.current_timestamp(),
            batch_id=batch_id,
            strategy_id=strategy_id,
            total_count=total_count or len(stocks),
            stocks=stocks
        )
        
        key = SelectionParser.build_key(date, self._key_prefix)
        
        if self._data_structure == 'stream':
            return self._write_to_stream(key, message)
        else:
            return self._write_to_list(key, message)
    
    def _write_to_stream(self, key: str, message: SelectionMessage) -> str:
        """
        写入到 Stream
        
        Args:
            key: Stream Key
            message: 选股消息
            
        Returns:
            str: 消息ID
        """
        fields = SelectionParser.to_stream_fields(message)
        
        logger.debug(f"推送选股数据到 Redis Stream: Key={key}, 批次={message.batch_id}")

        # 注意：这将清空该Key下所有的Stream消息
        if self._client.exists(key):
            self._client.delete(key)
            logger.debug(f"检测到旧Key存在，已删除: {key}")

        # 使用xadd创建新的Stream。由于Key刚被删除，这里相当于从零开始创建
        msg_id = self._client.xadd(
            key,
            fields,
            maxlen=self._maxlen,
            approximate=True
        )
        
        # 设置过期时间
        if self._expire_seconds > 0:
            self._client.expire(key, self._expire_seconds)
            logger.debug(f"设置Key过期时间: {key}, {self._expire_seconds}秒")
        
        return msg_id
    
    def _write_to_list(self, key: str, message: SelectionMessage) -> str:
        """
        写入到 List
        
        Args:
            key: List Key
            message: 选股消息
            
        Returns:
            str: 写入结果标识
        """
        import time
        
        value = SelectionParser.to_list_value(message)
        
        logger.debug(f"推送选股数据到 Redis List: Key={key}, 批次={message.batch_id}")
        
        # 使用 pipeline 保证原子性
        pipe = self._client.pipeline()

        pipe.delete(key)  # 删除所有的 key
        pipe.rpush(key, value)
        pipe.ltrim(key, -self._maxlen, -1)  # 保留最新的 maxlen 条
        
        # 设置过期时间
        if self._expire_seconds > 0:
            pipe.expire(key, self._expire_seconds)
            logger.debug(f"设置Key过期时间: {key}, {self._expire_seconds}秒")
        
        results = pipe.execute()
        
        # 返回写入后的列表长度作为标识
        list_len = results[0]
        return f"list:{list_len}"
    
    def write_raw(self, key: str, data: str) -> str:
        """
        直接写入数据
        
        Args:
            key: Key
            data: JSON数据字符串
            
        Returns:
            str: 写入消息的ID
        """
        if self._data_structure == 'stream':
            return self._client.xadd(
                key,
                {"data": data},
                maxlen=self._maxlen,
                approximate=True
            )
        else:
            # 覆盖逻辑：在Pipeline中先删除
            pipe = self._client.pipeline()
            pipe.delete(key)  # 先删除
            pipe.rpush(key, data)
            pipe.ltrim(key, -self._maxlen, -1)
            results = pipe.execute()
            return f"list:{results[0]}"
    
    def trim(self, key: str, count: int) -> int:
        """
        裁剪保留最近N条
        
        Args:
            key: Key
            count: 保留的消息数量
            
        Returns:
            int: 裁剪的消息数量
        """
        if self._data_structure == 'stream':
            return self._client.xtrim(key, count, approximate=True)
        else:
            # List 模式：使用 ltrim
            current_len = self._client.llen(key)
            if current_len > count:
                self._client.ltrim(key, -count, -1)
                return current_len - count
            return 0
    
    def delete(self, date: str) -> bool:
        """
        删除数据
        
        Args:
            date: 日期
            
        Returns:
            bool: 是否删除成功
        """
        key = SelectionParser.build_key(date, self._key_prefix)
        try:
            self._client.delete(key)
            return True
        except Exception:
            return False
    
    def get_length(self, date: str) -> int:
        """
        获取数据长度
        
        Args:
            date: 日期
            
        Returns:
            int: 消息数量
        """
        key = SelectionParser.build_key(date, self._key_prefix)
        if self._data_structure == 'stream':
            return self._client.xlen(key)
        else:
            return self._client.llen(key)
    
    def exists(self, date: str) -> bool:
        """
        检查是否存在
        
        Args:
            date: 日期
            
        Returns:
            bool: 是否存在
        """
        key = SelectionParser.build_key(date, self._key_prefix)
        return self._client.exists(key) > 0
    
    # ============== 兼容旧接口的方法 ==============
    
    def get_stream_length(self, date: str) -> int:
        """获取数据长度 (兼容旧接口)"""
        return self.get_length(date)
    
    def stream_exists(self, date: str) -> bool:
        """检查是否存在数据 (兼容旧接口)"""
        return self.exists(date)
    
    def trim_stream(self, date: str, count: int) -> int:
        """裁剪保留最近N条 (兼容旧接口)"""
        key = SelectionParser.build_key(date, self._key_prefix)
        return self.trim(key, count)
    
    def delete_stream(self, date: str) -> bool:
        """删除数据 (兼容旧接口)"""
        return self.delete(date)
