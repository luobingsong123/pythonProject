"""
数据库连接池管理模块
"""

import pymysql
from pymysql.cursors import DictCursor
from typing import Optional, Dict, Any
from contextlib import contextmanager


class DatabasePool:
    """数据库连接池管理器"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str = "",
        charset: str = "utf8mb4",
        pool_size: int = 5
    ):
        """
        初始化数据库连接池
        
        Args:
            host: 数据库主机
            port: 数据库端口
            user: 用户名
            password: 密码
            database: 数据库名
            charset: 字符集
            pool_size: 连接池大小
        """
        self.config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": charset,
            "cursorclass": DictCursor,
            "autocommit": True
        }
        self._pool = []
        self._max_size = pool_size
        self._in_use = 0
    
    def get_connection(self) -> pymysql.Connection:
        """
        获取数据库连接

        Returns:
            pymysql.Connection: 数据库连接
        """
        # 先从连接池获取
        if self._pool:
            return self._pool.pop()

        # 如果未达到最大连接数，创建新连接
        if self._in_use < self._max_size:
            self._in_use += 1
            return pymysql.connect(**self.config)

        # 连接池已耗尽
        raise Exception("Connection pool exhausted")

    def release_connection(self, conn: pymysql.Connection):
        """
        释放连接回连接池

        Args:
            conn: 数据库连接
        """
        if conn:
            # 尝试回收到连接池
            if len(self._pool) < self._max_size:
                # 检查连接是否仍然有效
                try:
                    conn.ping(reconnect=False)
                    self._pool.append(conn)
                    return
                except:
                    conn.close()
                    self._in_use -= 1
            else:
                # 连接池已满，关闭连接
                try:
                    conn.close()
                except:
                    pass
                self._in_use -= 1
    
    @contextmanager
    def connection(self):
        """上下文管理器获取连接"""
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        finally:
            if conn:
                self.release_connection(conn)
    
    def close_all(self):
        """关闭所有连接"""
        for conn in self._pool:
            conn.close()
        self._pool.clear()
        self._in_use = 0
    
    def ping(self) -> bool:
        """
        检查数据库连接
        
        Returns:
            bool: 连接是否正常
        """
        try:
            with self.connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
        except Exception:
            return False


# 全局默认连接池
_default_db_pool = None


def init_db_pool(config: Dict[str, Any]) -> DatabasePool:
    """
    初始化全局数据库连接池
    
    Args:
        config: 数据库配置
        
    Returns:
        DatabasePool: 数据库连接池
    """
    global _default_db_pool
    _default_db_pool = DatabasePool(**config)
    return _default_db_pool


def get_db_connection() -> pymysql.Connection:
    """
    获取全局默认数据库连接

    Returns:
        pymysql.Connection: 数据库连接
    """
    global _default_db_pool
    if _default_db_pool is None:
        raise Exception("Database pool not initialized. Call init_db_pool() first.")
    return _default_db_pool.get_connection()


def release_db_connection(conn: pymysql.Connection):
    """
    释放全局默认数据库连接

    Args:
        conn: 数据库连接
    """
    global _default_db_pool
    if _default_db_pool:
        _default_db_pool.release_connection(conn)


def close_db_pool():
    """关闭全局数据库连接池"""
    global _default_db_pool
    if _default_db_pool:
        _default_db_pool.close_all()
        _default_db_pool = None
