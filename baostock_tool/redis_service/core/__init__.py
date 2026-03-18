"""
核心模块 - Redis连接和服务基类
"""

from core.connection import RedisPool, get_redis_client, close_redis_client
from core.base_service import BaseRedisService

__all__ = [
    "RedisPool",
    "get_redis_client",
    "close_redis_client",
    "BaseRedisService"
]
