"""
行情快照订阅器模块
"""

import redis
import threading
from typing import Optional, Callable, Generator, Any
from baostock_tool.redis_service.core.base_service import BaseRedisService
from baostock_tool.redis_service.models.snapshot import SnapshotData, SnapshotParser


class SnapshotSubscriber(BaseRedisService):
    """行情快照订阅器"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        初始化订阅器
        
        Args:
            redis_client: Redis客户端
        """
        super().__init__(redis_client)
        self._parser = SnapshotParser()
        self._pubsub: Optional[redis.client.PubSub] = None
        self._listening = False
        self._thread: Optional[threading.Thread] = None
    
    def subscribe(self, pattern: str) -> Generator[SnapshotData, None, None]:
        """
        订阅行情快照
        
        Args:
            pattern: 通道模式，如 "market:snapshot:SSE:*" 或 "market:snapshot:*"
            
        Yields:
            SnapshotData: 行情快照数据对象
        """
        # 不忽略订阅消息，需要等待订阅确认
        self._pubsub = self._client.pubsub()
        self._pubsub.psubscribe(pattern)
        self._listening = True
        
        # 等待订阅确认消息
        try:
            confirm_msg = self._pubsub.get_message(timeout=5)
            if confirm_msg and confirm_msg["type"] == "psubscribe":
                print(f"Pattern subscription confirmed: {confirm_msg}")
        except Exception as e:
            print(f"Error waiting for subscription confirm: {e}")
        
        try:
            while self._listening:
                try:
                    message = self._pubsub.get_message(timeout=1)
                    if message is None:
                        continue
                    # 跳过订阅相关消息
                    if message["type"] in ("psubscribe", "subscribe", "punsubscribe", "unsubscribe"):
                        continue
                    if message["type"] == "pmessage":
                        data = message["data"]
                        
                        try:
                            snapshot = SnapshotParser.parse_message(data)
                            yield snapshot
                        except Exception as e:
                            # 解析失败时跳过
                            print(f"Failed to parse message: {e}")
                            continue
                except redis.ConnectionError:
                    if not self._listening:
                        break
                    continue
        finally:
            self.unsubscribe()
    
    def subscribe_raw(self, pattern: str) -> Generator[dict, None, None]:
        """
        订阅并返回原始消息
        
        Args:
            pattern: 通道模式
            
        Yields:
            dict: 包含channel和data的原始消息
        """
        self._pubsub = self._client.pubsub(ignore_subscribe_messages=True)
        self._pubsub.psubscribe(pattern)
        self._listening = True
        
        try:
            while self._listening:
                try:
                    message = self._pubsub.get_message(timeout=1)
                    if message is None:
                        continue
                    if message["type"] == "pmessage":
                        yield {
                            "channel": message["channel"],
                            "pattern": message["pattern"],
                            "data": message["data"]
                        }
                except redis.ConnectionError:
                    if not self._listening:
                        break
                    continue
        finally:
            self.unsubscribe()
    
    def subscribe_callback(self, pattern: str, callback: Callable[[SnapshotData], None]):
        """
        使用回调函数订阅
        
        Args:
            pattern: 通道模式
            callback: 处理消息的回调函数
        """
        self._pubsub = self._client.pubsub(ignore_subscribe_messages=True)
        self._pubsub.psubscribe(pattern)
        self._listening = True
        
        def listener():
            while self._listening:
                try:
                    message = self._pubsub.get_message(timeout=1)
                    if message is None:
                        continue
                    if message["type"] == "pmessage":
                        try:
                            snapshot = SnapshotParser.parse_message(message["data"])
                            callback(snapshot)
                        except Exception as e:
                            print(f"Error in callback: {e}")
                except redis.ConnectionError:
                    if not self._listening:
                        break
                    continue
        
        self._thread = threading.Thread(target=listener, daemon=True)
        self._thread.start()
    
    def unsubscribe(self):
        """取消订阅"""
        self._listening = False
        if self._pubsub:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.punsubscribe()
            except Exception:
                pass
            self._pubsub = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
            self._thread = None
    
    def subscribe_to_exchange(self, exchange: str) -> Generator[SnapshotData, None, None]:
        """
        订阅指定交易所的所有行情
        
        Args:
            exchange: 交易所代码，如 "SSE"
            
        Yields:
            SnapshotData: 行情快照数据对象
        """
        pattern = f"market:snapshot:{exchange}:*"
        return self.subscribe(pattern)
    
    def subscribe_to_symbol(self, exchange: str, symbol: str) -> Generator[SnapshotData, None, None]:
        """
        订阅指定股票的行情
        
        Args:
            exchange: 交易所代码
            symbol: 股票代码
            
        Yields:
            SnapshotData: 行情快照数据对象
        """
        channel = f"market:snapshot:{exchange}:{symbol}"
        
        self._pubsub = self._client.pubsub(ignore_subscribe_messages=True)
        self._pubsub.subscribe(channel)
        self._listening = True
        
        try:
            while self._listening:
                try:
                    message = self._pubsub.get_message(timeout=1)
                    if message is None:
                        continue
                    if message["type"] == "message":
                        try:
                            snapshot = SnapshotParser.parse_message(message["data"])
                            yield snapshot
                        except Exception as e:
                            print(f"Failed to parse message: {e}")
                            continue
                except redis.ConnectionError:
                    if not self._listening:
                        break
                    continue
        finally:
            self.unsubscribe()
    
    def close(self):
        """关闭订阅器"""
        self.unsubscribe()
        super().close()
