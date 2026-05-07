"""
股池数据读取模块
"""

import redis
from typing import Optional, List, Dict, Any
from baostock_tool.redis_service.core.base_service import BaseRedisService
from baostock_tool.redis_service.models.stock_selection import SelectionMessage, SelectionParser
from baostock_tool.redis_service.config.settings import settings


class SelectionReader(BaseRedisService):
    """股池数据读取器"""
    
    def __init__(
        self, 
        redis_client: Optional[redis.Redis] = None,
        data_structure: Optional[str] = None
    ):
        """
        初始化读取器
        
        Args:
            redis_client: Redis客户端
            data_structure: 数据结构类型 "stream" 或 "list"，默认使用配置中的值
        """
        super().__init__(redis_client)
        self._data_structure = (data_structure or settings.selection.data_structure).lower()
        self._key_prefix = settings.selection.key_prefix
        
        if self._data_structure not in ['stream', 'list']:
            self._data_structure = 'stream'
    
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
            last_id: 起始消息ID，"0-0"表示从最早的消息开始 (仅Stream模式有效)
            
        Returns:
            List[tuple]: 消息列表，每个元素为(msg_id, message_dict)
        """
        key = SelectionParser.build_key(date, self._key_prefix)
        
        if self._data_structure == 'stream':
            return self._read_from_stream(key, count, last_id)
        else:
            return self._read_from_list(key, count)
    
    def _read_from_stream(self, key: str, count: int, last_id: str) -> List[tuple]:
        """从 Stream 读取数据"""
        result = self._client.xread(
            {key: last_id},
            count=count,
            block=None
        )
        
        if not result:
            return []
        
        messages = []
        for stream_name, stream_messages in result:
            for msg in stream_messages:
                messages.append(msg)
        
        return messages
    
    def _read_from_list(self, key: str, count: int) -> List[tuple]:
        """从 List 读取数据（从头开始）"""
        # 使用 lrange 获取前 count 条
        items = self._client.lrange(key, 0, count - 1)
        
        messages = []
        for i, item in enumerate(items):
            # List 模式使用索引作为 ID
            msg_id = f"list:{i}"
            # item 已经是字符串 (decode_responses=True)
            messages.append((msg_id, {"data": item}))
        
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
        key = SelectionParser.build_key(date, self._key_prefix)
        
        if self._data_structure == 'stream':
            # 使用XRANGE从最新往回读
            messages = self._client.xrevrange(
                key,
                "+",  # 从最新开始
                "-",  # 到最早结束
                count=count
            )
            return messages
        else:
            # List 模式：使用 lrange 获取最新的 count 条
            list_len = self._client.llen(key)
            
            if list_len == 0:
                return []
            
            # 计算实际读取的起始索引
            start_index = max(0, list_len - count)
            items = self._client.lrange(key, start_index, -1)
            
            messages = []
            for i, item in enumerate(items):
                # 计算实际索引
                actual_index = start_index + i
                msg_id = f"list:{actual_index}"
                messages.append((msg_id, {"data": item}))
            
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
        key = SelectionParser.build_key(date, self._key_prefix)
        
        if self._data_structure == 'stream':
            messages = self._client.xrange(
                key,
                "-",  # 从最早开始
                "+",  # 到最新结束
                count=count
            )
            return messages
        else:
            return self._read_from_list(key, count)
    
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
        for msg in messages:
            try:
                # msg 可能是 (msg_id, msg_data) 或直接是字符串
                if isinstance(msg, tuple):
                    msg_id, msg_data = msg
                    selection = SelectionParser.parse_message(msg_data)
                elif isinstance(msg, str):
                    selection = SelectionParser.parse_message(msg)
                else:
                    selection = SelectionParser.parse_message(msg)
                result.append(selection)
            except Exception as e:
                print(f"Failed to parse message {msg}: {e}")
                import traceback
                traceback.print_exc()
        return result
    
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
    
    def create_consumer_group(
        self,
        date: str,
        group_name: str,
        start_id: str = "0"
    ) -> bool:
        """
        创建消费者组 (仅 Stream 模式有效)
        
        Args:
            date: 日期
            group_name: 消费者组名称
            start_id: 起始ID
            
        Returns:
            bool: 是否创建成功
        """
        if self._data_structure != 'stream':
            print("Warning: Consumer groups are not supported in List mode")
            return False
        
        key = SelectionParser.build_key(date, self._key_prefix)
        
        try:
            self._client.xgroup_create(
                key,
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
        使用消费者组读取消息 (仅 Stream 模式有效)
        
        Args:
            date: 日期
            group_name: 消费者组名称
            consumer_name: 消费者名称
            count: 每次读取的消息数
            block: 阻塞超时（毫秒），None表示不阻塞
            
        Returns:
            List[tuple]: 消息列表
        """
        if self._data_structure != 'stream':
            print("Warning: Consumer groups are not supported in List mode, use read_latest() instead")
            return self.read_latest(date, count)
        
        key = SelectionParser.build_key(date, self._key_prefix)
        
        # 确保消费者组存在
        self.create_consumer_group(date, group_name)
        
        result = self._client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={key: ">"},
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
        确认消息 (仅 Stream 模式有效)
        
        Args:
            date: 日期
            group_name: 消费者组名称
            message_ids: 消息ID列表
            
        Returns:
            int: 确认的消息数量
        """
        if self._data_structure != 'stream':
            # List 模式无需确认
            return len(message_ids)
        
        key = SelectionParser.build_key(date, self._key_prefix)
        return self._client.xack(key, group_name, *message_ids)
    
    # ============== 兼容旧接口的方法 ==============
    
    def get_stream_length(self, date: str) -> int:
        """
        获取数据长度 (兼容旧接口)
        
        Args:
            date: 日期
            
        Returns:
            int: 消息数量
        """
        return self.get_length(date)
    
    def stream_exists(self, date: str) -> bool:
        """
        检查是否存在数据 (兼容旧接口)
        
        Args:
            date: 日期
            
        Returns:
            bool: 是否存在
        """
        key = SelectionParser.build_key(date, self._key_prefix)
        return self._client.exists(key) > 0
