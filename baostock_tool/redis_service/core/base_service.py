"""
Redis基础服务类
"""

import redis
from abc import ABC, abstractmethod
from typing import Optional
from baostock_tool.redis_service.core.connection import RedisPool, get_redis_client
from baostock_tool.redis_service.config.settings import Settings


class BaseRedisService(ABC):
    """Redis服务基类"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        初始化基础服务
        
        Args:
            redis_client: Redis客户端，如果为None则使用全局默认客户端
        """
        self._client = redis_client or get_redis_client()
    
    @property
    def client(self) -> redis.Redis:
        """获取Redis客户端"""
        return self._client
    
    def ping(self) -> bool:
        """
        检查Redis连接
        
        Returns:
            bool: 连接是否正常
        """
        try:
            return self._client.ping()
        except Exception:
            return False
    
    def close(self):
        """关闭客户端连接"""
        if self._client:
            self._client.close()
