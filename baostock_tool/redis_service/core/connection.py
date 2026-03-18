"""
Redis连接池管理模块
"""

import redis
from typing import Optional
from config.settings import RedisConfig, settings


class RedisPool:
    """Redis连接池管理器"""
    
    _pool: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    
    def __init__(self, config: Optional[RedisConfig] = None):
        """
        初始化连接池
        
        Args:
            config: Redis配置，如果不提供则使用默认配置
        """
        self.config = config or settings.redis
    
    def get_connection_pool(self) -> redis.ConnectionPool:
        """
        获取Redis连接池
        
        Returns:
            redis.ConnectionPool: 连接池实例
        """
        if self._pool is None:
            self._pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                encoding=self.config.encoding,
                decode_responses=self.config.decode_responses,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                max_connections=self.config.max_connections
            )
        return self._pool
    
    def get_client(self) -> redis.Redis:
        """
        获取Redis客户端
        
        Returns:
            redis.Redis: Redis客户端实例
        """
        if self._client is None:
            self._client = redis.Redis(connection_pool=self.get_connection_pool())
        return self._client
    
    def close(self):
        """关闭连接池"""
        if self._client:
            self._client.close()
            self._client = None
        if self._pool:
            self._pool.disconnect()
            self._pool = None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self.get_client()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 全局默认连接池
_default_pool = None


def get_redis_client() -> redis.Redis:
    """
    获取全局默认Redis客户端
    
    Returns:
        redis.Redis: Redis客户端实例
    """
    global _default_pool
    if _default_pool is None:
        _default_pool = RedisPool()
    return _default_pool.get_client()


def close_redis_client():
    """关闭全局默认Redis客户端"""
    global _default_pool
    if _default_pool:
        _default_pool.close()
        _default_pool = None
