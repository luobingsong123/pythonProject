"""
股池数据读取模块
"""

import redis
from typing import Optional, List, Dict, Any
from core.base_service import BaseRedisService
from models.stock_selection import SelectionMessage, SelectionParser


class SelectionReader(BaseRedisService):
    """股池数据读取器"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        初始化读取器
        
        Args:
            redis_client: Redis客户端
        """
        super().__init__(redis_client)
    
    def read_selection(
        self,
        date: str,
        count: int = 100,
        last_id: str = "0-0"
    ) -> List[tuple]:
        """
        读取股池数据
        
        Args:
            date: 日期，格式YYYYMMDD
            count: 每次读取的最大消息数
            last_id: 起始消息ID，"0-0"表示从最早的消息开始
            
        Returns:
            List[tuple]: 消息列表，每个元素为(msg_id, message_dict)
        """
        stream_key = SelectionParser.build_stream_key(date)
        
        result = self._client.xread(
            {stream_key: last_id},
            count=count,
            block=None  # 阻塞模式，None表示不使用阻塞
        )
        
        if not result:
            return []
        
        messages = []
        for stream_name, stream_messages in result:
            for msg in stream_messages:
                messages.append(msg)
        
        return messages
    
    def read_latest(self, date: str, count: int = 100) -> List[tuple]:
        """
        读取最新的N条消息
        
        Args:
            date: 日期
            count: 读取的消息数
            
        Returns:
            List[tuple]: 消息列表
        """
        stream_key = SelectionParser.build_stream_key(date)
        
        # 使用XRANGE从最新往回读
        messages = self._client.xrevrange(
            stream_key,
            "+",  # 从最新开始
            "-",  # 到最早结束
            count=count
        )
        
        return messages
    
    def read_from_beginning(
        self,
        date: str,
        count: int = 100
    ) -> List[tuple]:
        """
        从头开始读取消息
        
        Args:
            date: 日期
            count: 读取的消息数
            
        Returns:
            List[tuple]: 消息列表
        """
        stream_key = SelectionParser.build_stream_key(date)
        
        messages = self._client.xrange(
            stream_key,
            "-",  # 从最早开始
            "+",  # 到最新结束
            count=count
        )
        
        return messages
    
    def parse_messages(
        self,
        messages: List[tuple]
    ) -> List[SelectionMessage]:
        """
        解析消息列表
        
        Args:
            messages: 原始消息列表
            
        Returns:
            List[SelectionMessage]: 解析后的选股消息列表
        """
        result = []
        for msg_id, msg_data in messages:
            try:
                selection = SelectionParser.parse_message((msg_id, msg_data))
                result.append(selection)
            except Exception as e:
                print(f"Failed to parse message {msg_id}: {e}")
        return result
    
    def get_stream_length(self, date: str) -> int:
        """
        获取Stream长度
        
        Args:
            date: 日期
            
        Returns:
            int: 消息数量
        """
        stream_key = SelectionParser.build_stream_key(date)
        return self._client.xlen(stream_key)
    
    def create_consumer_group(
        self,
        date: str,
        group_name: str,
        start_id: str = "0"
    ) -> bool:
        """
        创建消费者组
        
        Args:
            date: 日期
            group_name: 消费者组名称
            start_id: 起始ID
            
        Returns:
            bool: 是否创建成功
        """
        stream_key = SelectionParser.build_stream_key(date)
        
        try:
            self._client.xgroup_create(
                stream_key,
                group_name,
                start_id=start_id,
                mkstream=True
            )
            return True
        except redis.exceptions.ResponseError as e:
            # 消费者组已存在
            if "BUSYGROUP" in str(e):
                return False
            raise
    
    def read_with_consumer_group(
        self,
        date: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block: Optional[int] = None
    ) -> List[tuple]:
        """
        使用消费者组读取消息
        
        Args:
            date: 日期
            group_name: 消费者组名称
            consumer_name: 消费者名称
            count: 每次读取的消息数
            block: 阻塞超时（毫秒），None表示不阻塞
            
        Returns:
            List[tuple]: 消息列表
        """
        stream_key = SelectionParser.build_stream_key(date)
        
        # 确保消费者组存在
        self.create_consumer_group(date, group_name)
        
        result = self._client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={stream_key: ">"},
            count=count,
            block=block
        )
        
        if not result:
            return []
        
        messages = []
        for stream_name, stream_messages in result:
            for msg in stream_messages:
                messages.append(msg)
        
        return messages
    
    def ack_message(self, date: str, group_name: str, *message_ids: str) -> int:
        """
        确认消息
        
        Args:
            date: 日期
            group_name: 消费者组名称
            message_ids: 消息ID列表
            
        Returns:
            int: 确认的消息数量
        """
        stream_key = SelectionParser.build_stream_key(date)
        return self._client.xack(stream_key, group_name, *message_ids)
