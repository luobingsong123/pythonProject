"""
配置文件加载器

从 config.ini 文件加载配置并转换为 Settings 对象
"""

import configparser
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

from .settings import (
    Settings,
    RedisConfig,
    DatabaseConfig,
    MarketConfig,
    SelectionConfig,
    BacktestConfig,
    LoggingConfig
)


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径，默认为 config/config.ini
        """
        if config_path is None:
            # 默认配置文件路径
            self.config_path = Path(__file__).parent / "config.ini"
        else:
            self.config_path = Path(config_path)
        
        self.config = configparser.ConfigParser()
        
    def load(self) -> Settings:
        """
        加载配置文件
        
        Returns:
            Settings: 配置对象
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        # 读取配置文件
        self.config.read(self.config_path, encoding='utf-8')
        
        # 构建配置对象
        return Settings(
            redis=self._load_redis_config(),
            database=self._load_database_config(),
            market=self._load_market_config(),
            selection=self._load_selection_config(),
            backtest=self._load_backtest_config(),
            logging=self._load_logging_config()
        )
    
    def _load_redis_config(self) -> RedisConfig:
        """加载 Redis 配置"""
        section = 'redis'

        # 处理密码（可能为空）
        password = self.config.get(section, 'password', fallback='')
        password = password if password else None

        # 处理布尔值
        decode_responses = self.config.getboolean(section, 'decode_responses', fallback=True)

        # 处理模式
        mode = self.config.get(section, 'mode', fallback='auto').lower()
        if mode not in ['single', 'cluster', 'auto']:
            mode = 'auto'

        return RedisConfig(
            host=self.config.get(section, 'host', fallback='localhost'),
            port=self.config.getint(section, 'port', fallback=6379),
            db=self.config.getint(section, 'db', fallback=0),
            password=password,
            encoding=self.config.get(section, 'encoding', fallback='utf-8'),
            decode_responses=decode_responses,
            socket_timeout=self.config.getint(section, 'socket_timeout', fallback=5),
            socket_connect_timeout=self.config.getint(section, 'socket_connect_timeout', fallback=5),
            max_connections=self.config.getint(section, 'max_connections', fallback=50),
            mode=mode
        )
    
    def _load_database_config(self) -> DatabaseConfig:
        """加载数据库配置"""
        section = 'database'
        
        return DatabaseConfig(
            host=self.config.get(section, 'host', fallback='localhost'),
            port=self.config.getint(section, 'port', fallback=3306),
            user=self.config.get(section, 'user', fallback='root'),
            password=self.config.get(section, 'password', fallback=''),
            database=self.config.get(section, 'database', fallback=''),
            charset=self.config.get(section, 'charset', fallback='utf8mb4'),
            pool_size=self.config.getint(section, 'pool_size', fallback=5)
        )
    
    def _load_market_config(self) -> MarketConfig:
        """加载行情配置"""
        section = 'market'
        
        return MarketConfig(
            snapshot_channel_prefix=self.config.get(section, 'snapshot_channel_prefix', fallback='market:snapshot'),
            subscribe_pattern=self.config.get(section, 'subscribe_pattern', fallback='market:snapshot:*')
        )
    
    def _load_selection_config(self) -> SelectionConfig:
        """加载股池配置"""
        section = 'selection'
        
        # 处理数据存储结构
        data_structure = self.config.get(section, 'data_structure', fallback='stream').lower()
        if data_structure not in ['stream', 'list']:
            data_structure = 'stream'
        
        return SelectionConfig(
            data_structure=data_structure,
            key_prefix=self.config.get(section, 'key_prefix', fallback='selection:stream'),
            maxlen=self.config.getint(section, 'maxlen', fallback=10000),
            consumer_group=self.config.get(section, 'consumer_group', fallback='selection_consumer'),
            consumer_name=self.config.get(section, 'consumer_name', fallback='consumer_01'),
            expire_seconds=self.config.getint(section, 'expire_seconds', fallback=86400)
        )
    
    def _load_backtest_config(self) -> BacktestConfig:
        """加载回测配置"""
        section = 'backtest'
        
        # 解析策略参数（JSON 格式）
        strategy_params_str = self.config.get(section, 'strategy_params', fallback='{}')
        try:
            strategy_params = json.loads(strategy_params_str)
        except json.JSONDecodeError:
            strategy_params = {}
        
        # 解析交易日列表
        trade_dates_str = self.config.get(section, 'trade_dates', fallback='')
        trade_dates = [d.strip() for d in trade_dates_str.split(',') if d.strip()] if trade_dates_str else []
        
        # 处理布尔值
        use_strategy = self.config.getboolean(section, 'use_strategy', fallback=True)
        use_pipeline = self.config.getboolean(section, 'use_pipeline', fallback=True)
        
        return BacktestConfig(
            start_date=self.config.get(section, 'start_date', fallback='20241001'),
            end_date=self.config.get(section, 'end_date', fallback='20241008'),
            strategy_id=self.config.get(section, 'strategy_id', fallback='MA10_BREAKTHROUGH'),
            use_strategy=use_strategy,
            default_selection_count=self.config.getint(section, 'default_selection_count', fallback=10),
            strategy_params=strategy_params,
            trade_dates=trade_dates,
            preload_days=self.config.getint(section, 'preload_days', fallback=30),
            use_pipeline=use_pipeline
        )

    def _load_logging_config(self) -> LoggingConfig:
        """加载日志配置"""
        section = 'logging'

        # 验证日志级别
        level = self.config.get(section, 'level', fallback='INFO').upper()
        if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            level = 'INFO'

        return LoggingConfig(
            level=level,
            log_file=self.config.get(section, 'log_file', fallback='logs/redis_service.log'),
            max_bytes=self.config.getint(section, 'max_bytes', fallback=10) * 1024 * 1024,  # MB转字节
            backup_count=self.config.getint(section, 'backup_count', fallback=5),
            console_output=self.config.getboolean(section, 'console_output', fallback=True)
        )

    def get_custom_config(self, section: str) -> Dict[str, Any]:
        """
        获取自定义配置段
        
        Args:
            section: 配置段名称
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        if not self.config.has_section(section):
            return {}
        
        return dict(self.config[section])
    
    def reload(self) -> Settings:
        """
        重新加载配置
        
        Returns:
            Settings: 配置对象
        """
        self.config.clear()
        return self.load()


# 全局配置加载器实例
config_loader = ConfigLoader()


def load_config(config_path: Optional[str] = None) -> Settings:
    """
    加载配置的便捷函数
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        Settings: 配置对象
    """
    loader = ConfigLoader(config_path)
    return loader.load()


def update_global_settings(config_path: Optional[str] = None) -> None:
    """
    更新全局 settings 对象
    
    Args:
        config_path: 配置文件路径
    """
    from .settings import settings
    config = load_config(config_path)
    
    # 更新全局 settings
    for field_name in config.model_dump():
        setattr(settings, field_name, getattr(config, field_name))
