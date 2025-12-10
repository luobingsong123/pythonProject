import logging
import os
from datetime import datetime
import sys


def setup_logger(
        logger_name: str = __name__,  # Logger 的名字（默认用当前模块名）
        log_level: int = logging.INFO,  # 全局日志级别（默认 INFO）
        log_dir: str = "./logs",  # 日志存储目录（默认当前目录下的 logs 文件夹）
        log_filename: str = None  # 日志文件名（默认用日期命名，比如 2024-05-20_baostockAPI_running.log）
) -> logging.Logger:
    """
    配置并返回一个带文件+控制台输出的 Logger

    参数说明：
        logger_name: Logger 的标识（建议用模块名，比如 __name__，方便追踪日志来源）
        log_level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        log_dir: 日志文件存储的目录（会自动创建不存在的目录）
        log_filename: 自定义日志文件名（不传则用日期生成默认名）
    返回：
        配置好的 logging.Logger 对象
    """
    # 1. 自动创建日志目录（如果不存在）
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)  # exist_ok=True 避免目录存在时报错

    # 2. 初始化 Logger（根据名字获取/创建）
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)  # 设置 Logger 的最低接收级别

    # 3. 避免重复添加 Handler（关键！否则多次调用会重复打印日志）
    if getattr(logger, "has_handlers", lambda: False)():
        logger.handlers.clear()

    # 4. 生成最终的日志文件名（默认用日期）
    if not log_filename:
        log_date = datetime.now().strftime("%Y-%m-%d")
        log_filename = f"{log_date}{logger_name}.log"

    # 5. 创建「文件 Handler」：写入日志到文件
    file_handler = logging.FileHandler(
        filename=os.path.join(log_dir, log_filename),  # 拼接完整文件路径
        mode="a",  # 追加模式（默认，不会覆盖旧日志）
        encoding="utf-8"  # 防止中文乱码
    )
    file_handler.setLevel(log_level)  # 文件日志的级别（可单独调整，比如设为 DEBUG 更详细）

    # 6. 创建「控制台 Handler」：输出日志到终端
    console_handler = logging.StreamHandler(sys.stdout)  # 输出到标准输出（终端）
    console_handler.setLevel(log_level)  # 控制台日志级别（可单独调整，比如设为 WARNING 只显示警告以上）

    # 7. 定义统一日志格式（两个 Handler 共用）
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - Line: %(lineno)d - %(levelname)s - %(message)s"
        # 格式说明：
        # %(asctime)s: 时间（比如 2024-05-20 14:30:00,123）
        # %(name)s: Logger 名字（比如 main 或 __name__）
        # %(levelname)s: 日志级别（INFO/ERROR 等）
        # %(message)s: 日志内容
    )
    file_handler.setFormatter(formatter)  # 给文件 Handler 设置格式
    console_handler.setFormatter(formatter)  # 给控制台 Handler 设置格式

    # 8. 将 Handler 绑定到 Logger（关键！否则 Handler 不生效）
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger  # 返回配置好的 Logger，供其他模块使用

def get_logger(
        logger_name: str = __name__,
        log_level: int = logging.INFO,
        log_dir: str = "./logs",
        log_filename: str = None
        ) -> logging.Logger:
    """
    获取配置好的 Logger（封装 setup_logger 方便调用）

    参数说明：
        logger_name: Logger 的标识（建议用模块名，比如 __name__）
        log_level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        log_dir: 日志文件存储的目录
        log_filename: 自定义日志文件名
    返回：
        配置好的 logging.Logger 对象
    """
    return setup_logger(
        logger_name=logger_name,
        log_level=log_level,
        log_dir=log_dir,
        log_filename=log_filename
    )