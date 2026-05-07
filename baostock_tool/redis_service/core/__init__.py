"""
核心模块 - Redis连接和服务基类
"""

from baostock_tool.redis_service.core.connection import RedisPool, get_redis_client, close_redis_client
from baostock_tool.redis_service.core.base_service import BaseRedisService

__all__ = [
    "RedisPool",
    "get_redis_client",
    "close_redis_client",
    "BaseRedisService"
]
