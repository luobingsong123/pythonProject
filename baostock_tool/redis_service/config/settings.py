"""
Redis配置管理模块
"""

from pydantic import BaseModel, Field
from typing import Optional, List
import logging


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    log_file: str = "logs/redis_service.log"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True

    def get_log_level(self) -> int:
        """获取日志级别"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(self.level.upper(), logging.INFO)


class RedisConfig(BaseModel):
    """Redis连接配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    encoding: str = "utf-8"
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    max_connections: int = 50
    # Redis 模式: "single" (单机), "cluster" (集群), "auto" (自动检测)
    mode: str = "auto"


class DatabaseConfig(BaseModel):
    """数据库连接配置"""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = ""
    charset: str = "utf8mb4"
    pool_size: int = 5


class ClickHouseConfig(BaseModel):
    """ClickHouse连接配置"""
    host: str = "localhost"
    port: int = 9000
    user: str = "default"
    password: str = ""
    database: str = "quant_trader"


class MarketConfig(BaseModel):
    """行情相关配置"""
    # Pub/Sub通道前缀
    snapshot_channel_prefix: str = "market:snapshot"
    # 订阅模式
    subscribe_pattern: str = "market:snapshot:*"


class SelectionConfig(BaseModel):
    """股池相关配置"""
    # 数据存储结构: "stream" (Redis 5.0+) 或 "list" (Redis 3.0+)
    data_structure: str = "stream"
    # Key前缀 (Stream 或 List 共用)
    key_prefix: str = "selection:stream"
    # 最大长度 (Stream 或 List 最大保存消息数)
    maxlen: int = 10000
    # 消费者组名称 (仅 Stream 模式有效)
    consumer_group: str = "selection_consumer"
    # 消费者名称 (仅 Stream 模式有效)
    consumer_name: str = "consumer_01"
    # Redis Key 过期时间（秒），默认24小时
    expire_seconds: int = 86400


class BacktestConfig(BaseModel):
    """回测配置"""
    # 回测开始日期
    start_date: str = "20260101"
    # 回测结束日期
    end_date: str = "20260317"
    # 选股策略ID
    strategy_id: str = "MA10_BREAKTHROUGH"
    # 默认选股数量（无策略时使用）
    default_selection_count: int = 10
    # 是否使用选股策略
    use_strategy: bool = True
    # 策略参数
    strategy_params: dict = Field(default_factory=dict)
    # 交易日列表
    trade_dates: List[str] = Field(default_factory=list)
    # 数据预加载天数（日K线开始日期提前 preload_days * 1.68 个交易日）
    preload_days: int = 30
    # 是否使用 Redis Pipeline 批量推送
    use_pipeline: bool = True


class Settings(BaseModel):
    """全局配置"""
    redis: RedisConfig = RedisConfig()
    database: DatabaseConfig = DatabaseConfig()
    clickhouse: ClickHouseConfig = ClickHouseConfig()
    market: MarketConfig = MarketConfig()
    selection: SelectionConfig = SelectionConfig()
    backtest: BacktestConfig = BacktestConfig()
    logging: LoggingConfig = LoggingConfig()


# 全局配置实例
settings = Settings()
