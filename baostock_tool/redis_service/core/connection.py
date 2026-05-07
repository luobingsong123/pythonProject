"""
Redis连接池管理模块
"""

import redis
from typing import Optional
from baostock_tool.redis_service.config.settings import RedisConfig, settings


class RedisPool:
    """Redis连接池管理器"""

    _pool: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    _is_cluster = False

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
                max_connections=self.config.max_connections,
                health_check_interval=30  # 健康检查间隔
            )
        return self._pool

    def get_client(self) -> redis.Redis:
        """
        获取Redis客户端

        Returns:
            redis.Redis: Redis客户端实例
        """
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> redis.Redis:
        """
        创建Redis客户端（根据配置选择单机/集群模式）

        Returns:
            redis.Redis: Redis客户端实例
        """
        print(f"正在连接 Redis: {self.config.host}:{self.config.port}")

        # 根据配置的 mode 选择连接方式
        mode = getattr(self.config, 'mode', 'auto').lower()

        if mode == 'cluster':
            # 强制使用集群模式
            print("使用配置: 集群模式")
            return self._create_cluster_client()
        elif mode == 'single':
            # 强制使用单机模式
            print("使用配置: 单机模式")
            return self._create_standalone_client()
        else:
            # 自动检测模式
            print("使用配置: 自动检测模式")
            return self._auto_detect_and_create_client()

    def _create_standalone_client(self) -> redis.Redis:
        """
        创建单机Redis客户端

        Returns:
            redis.Redis: Redis客户端实例
        """
        try:
            client = redis.Redis(
                connection_pool=self.get_connection_pool(),
                decode_responses=self.config.decode_responses
            )
            client.ping()
            self._is_cluster = False
            print(f"✓ Redis 连接成功 (单机模式): {self.config.host}:{self.config.port}")
            return client
        except Exception as e:
            print(f"✗ Redis 单机模式连接失败: {e}")
            raise

    def _auto_detect_and_create_client(self) -> redis.Redis:
        """
        自动检测并创建Redis客户端

        Returns:
            redis.Redis: Redis客户端实例
        """
        # 先尝试单机模式
        print("尝试单机模式连接...")
        try:
            client = redis.Redis(
                connection_pool=self.get_connection_pool(),
                decode_responses=self.config.decode_responses
            )

            # 测试基本连接
            client.ping()
            print("✓ 单机模式连接成功")

            # 尝试执行 Stream 命令来验证是否真的支持
            # 因为集群模式下某些命令可能会失败
            try:
                # 使用一个临时的 key 测试
                test_key = "__redis_connection_test__"
                client.set(test_key, "1", ex=10)  # 10秒过期
                client.get(test_key)
                client.delete(test_key)
                
                # 如果能执行这些命令，说明是单机模式
                self._is_cluster = False
                print(f"✓ Redis 连接成功 (单机模式): {self.config.host}:{self.config.port}")
                return client
                
            except redis.exceptions.ConnectionError as e:
                error_msg = str(e)
                # 检查是否是集群错误
                if 'CLUSTERDOWN' in error_msg or 'MOVED' in error_msg or 'ASK' in error_msg:
                    print(f"⚠ 检测到集群错误: {error_msg[:100]}")
                    print("切换到集群模式...")
                    # 关闭单机客户端
                    try:
                        client.close()
                    except:
                        pass
                    # 清空连接池
                    self._pool = None
                    return self._create_cluster_client()
                else:
                    raise

        except redis.exceptions.ConnectionError as e:
            error_msg = str(e)
            # 检查是否是集群错误
            if 'CLUSTERDOWN' in error_msg or 'MOVED' in error_msg or 'ASK' in error_msg:
                print(f"⚠ 检测到集群错误: {error_msg[:100]}")
                print("切换到集群模式...")
                return self._create_cluster_client()
            else:
                print(f"✗ Redis 连接失败: {e}")
                raise
        except Exception as e:
            print(f"✗ Redis 连接失败: {e}")
            raise

    def _create_cluster_client(self) -> redis.Redis:
        """
        创建 Redis 集群客户端

        Returns:
            redis.Redis: Redis客户端实例
        """
        # 尝试导入集群客户端（支持新旧版本）
        RedisCluster = None
        try:
            # 新版本 redis-py (>=4.0.0) 内置集群支持
            from redis.cluster import RedisCluster as NewRedisCluster
            RedisCluster = NewRedisCluster
            print("使用 redis-py 内置集群支持 (版本 >= 4.0)")
        except ImportError:
            try:
                # 旧版本使用 redis-py-cluster 包
                from rediscluster import RedisCluster as OldRedisCluster
                RedisCluster = OldRedisCluster
                print("使用 redis-py-cluster 包")
            except ImportError:
                print("✗ 未找到 Redis 集群支持")
                print("  解决方案:")
                print("  1. 升级 redis 包: pip install --upgrade redis")
                print("  2. 或安装 redis-py-cluster: pip install redis-py-cluster")
                raise Exception(
                    "Redis cluster support not found. "
                    "Please install: pip install --upgrade redis"
                )

        try:
            # 构建集群客户端参数
            cluster_kwargs = {
                'host': self.config.host,
                'port': self.config.port,
                'decode_responses': self.config.decode_responses,
                'socket_timeout': self.config.socket_timeout,
                'socket_connect_timeout': self.config.socket_connect_timeout,
            }

            # 添加密码（如果有）
            if self.config.password:
                cluster_kwargs['password'] = self.config.password

            # 新版本 redis-py 的参数
            if hasattr(RedisCluster, '__module__') and 'redis.cluster' in RedisCluster.__module__:
                cluster_kwargs['skip_full_coverage_check'] = True
                cluster_kwargs['max_connections'] = self.config.max_connections

            # 创建集群客户端
            client = RedisCluster(**cluster_kwargs)

            # 测试连接
            client.ping()
            self._is_cluster = True
            print(f"✓ Redis 连接成功 (集群模式): {self.config.host}:{self.config.port}")
            return client

        except Exception as e:
            print(f"✗ Redis 集群模式连接失败: {e}")
            raise
    
    def close(self):
        """关闭连接池"""
        if self._client:
            try:
                if self._is_cluster:
                    # 集群模式关闭
                    self._client.close()
                else:
                    # 单机模式关闭
                    self._client.close()
            except Exception as e:
                print(f"关闭 Redis 客户端时出错: {e}")
            self._client = None

        if self._pool and not self._is_cluster:
            # 集群模式不需要手动关闭连接池
            try:
                self._pool.disconnect()
            except Exception as e:
                print(f"关闭 Redis 连接池时出错: {e}")
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
