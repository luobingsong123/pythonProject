"""
日志管理模块

统一管理整个服务的日志配置
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from baostock_tool.redis_service.config.settings import settings


def setup_logging(
        logger_name: str = "redis_service",
        log_level: Optional[int] = None,
        log_file: Optional[str] = None,
        max_bytes: Optional[int] = None,
        backup_count: Optional[int] = None,
        console_output: Optional[bool] = None
) -> logging.Logger:
    """
    配置并返回统一的日志器

    Args:
        logger_name: 日志器名称
        log_level: 日志级别，默认使用配置文件中的值
        log_file: 日志文件路径，默认使用配置文件中的值
        max_bytes: 日志文件最大大小（字节），默认使用配置文件中的值
        backup_count: 保留日志文件数量，默认使用配置文件中的值
        console_output: 是否输出到控制台，默认使用配置文件中的值

    Returns:
        logging.Logger: 配置好的日志器
    """
    # 从配置获取参数
    log_config = settings.logging
    level = log_level or log_config.get_log_level()
    file_path = log_file or log_config.log_file
    max_size = max_bytes or log_config.max_bytes
    backup = backup_count or log_config.backup_count
    console = console_output if console_output is not None else log_config.console_output

    # 创建日志目录
    log_dir = Path(file_path).parent
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)

    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s | %(filename)s:%(lineno)d | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 文件处理器（支持轮转）
    file_handler = RotatingFileHandler(
        filename=file_path,
        maxBytes=max_size,
        backupCount=backup,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return logging.getLogger(logger_name)


def get_logger(name: str = __name__) -> logging.Logger:
    """
    获取日志器

    Args:
        name: 日志器名称

    Returns:
        logging.Logger: 日志器
    """
    return logging.getLogger(name)