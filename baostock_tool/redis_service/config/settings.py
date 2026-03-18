"""
Redis配置管理模块
"""

from pydantic import BaseModel, Field
from typing import Optional, List


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


class MarketConfig(BaseModel):
    """行情相关配置"""
    # Pub/Sub通道前缀
    snapshot_channel_prefix: str = "market:snapshot"
    # 订阅模式
    subscribe_pattern: str = "market:snapshot:*"


class SelectionConfig(BaseModel):
    """股池相关配置"""
    # Stream Key前缀
    stream_key_prefix: str = "selection:stream"
    # Stream最大长度
    stream_maxlen: int = 10000
    # 消费者组名称
    consumer_group: str = "selection_consumer"


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


class Settings(BaseModel):
    """全局配置"""
    redis: RedisConfig = RedisConfig()
    database: DatabaseConfig = DatabaseConfig()
    market: MarketConfig = MarketConfig()
    selection: SelectionConfig = SelectionConfig()
    backtest: BacktestConfig = BacktestConfig()


# 全局配置实例
settings = Settings()
