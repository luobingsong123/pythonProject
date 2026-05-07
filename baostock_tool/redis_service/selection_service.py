"""
选股服务主入口

读取配置文件 -> 查询数据 -> 执行选股 -> 存入数据库 -> 推送到Redis
如果Redis连接失败，则只存入数据库
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from baostock_tool.redis_service.config.settings import settings
from baostock_tool.redis_service.config.config_loader import update_global_settings
from baostock_tool.redis_service.database.connection import DatabasePool, init_db_pool, close_db_pool
from baostock_tool.redis_service.database.queries import StockQueryService
from baostock_tool.redis_service.database.selection_repository import SelectionRepository
from baostock_tool.redis_service.selection.writer import SelectionWriter
from baostock_tool.redis_service.strategy.selector import StockSelector
from baostock_tool.redis_service.models.stock_selection import SelectionMessage
from baostock_tool.redis_service.utils.serializer import TimestampUtil
from typing import Optional, List, Dict, Any
from baostock_tool.redis_service.core.connection import get_redis_client
from baostock_tool.redis_service.utils.log_manager import setup_logging, get_logger
import datetime

def check_redis_connection() -> bool:
    """
    检查Redis连接是否正常

    Returns:
        bool: 连接是否正常
    """
    try:
        client = get_redis_client()
        result = client.ping()
        client.close()
        return result
    except Exception as e:
        print(f"Redis连接失败: {e}")
        return False


def run_selection_service(
    start_date: str,
    end_date: str,
    strategy_id: Optional[str] = None,
    use_strategy: bool = True,
    default_selection_count: int = 10,
    strategy_params: Optional[Dict[str, Any]] = None,
    real_flag: bool = False
):
    """
    运行选股服务

    Args:
        start_date: 选股开始日期
        end_date: 选股结束日期
        strategy_id: 策略ID
        use_strategy: 是否使用选股策略
        default_selection_count: 默认选股数量
        strategy_params: 策略参数
    """
    logger = get_logger("selection_service")

    # 检查Redis连接
    redis_available = check_redis_connection()
    if redis_available:
        logger.info("Redis连接正常，将推送数据到Redis并设置过期时间")
    else:
        logger.warning("Redis连接失败，选股结果将仅存入数据库")

    # 初始化数据库连接池
    db_config = {
        "host": settings.database.host,
        "port": settings.database.port,
        "user": settings.database.user,
        "password": settings.database.password,
        "database": settings.database.database,
        "charset": settings.database.charset
    }

    db_pool = init_db_pool(db_config)
    logger.info("数据库连接池初始化成功")

    # 初始化服务
    query_service = StockQueryService(db_pool)
    repository = SelectionRepository(db_pool)

    # 初始化选股器
    selector = StockSelector(query_service=query_service, repository=repository)

    # 初始化Redis写入器（如果Redis可用）
    selection_writer = None
    if redis_available:
        selection_writer = SelectionWriter()

    try:
        # 获取交易日列表
        if real_flag:
            # 如果实盘标志，则使用当前日期作为唯一交易日
            trade_dates = [datetime.datetime.now().strftime("%Y%m%d")]
        else:
            trade_dates = query_service.get_trading_dates(start_date, end_date)
            logger.info(f"获取到 {len(trade_dates)} 个交易日")

        # 遍历每个交易日执行选股
        for date in trade_dates:
            logger.info(f"\n{'='*60}")
            logger.info(f"处理交易日: {date}")
            logger.info(f"{'='*60}")

            # 执行选股
            logger.info(f"执行选股: 策略={strategy_id if use_strategy else '无'}, 数量={default_selection_count}")

            stocks = selector.select(
                date=date,
                strategy_id=strategy_id if use_strategy else None,
                count=default_selection_count,
                save_to_db=True,  # 自动保存到数据库
                strategy_params=strategy_params
            )

            if not stocks:
                logger.warning(f"日期 {date} 未选出任何股票")
                continue

            logger.info(f"选出 {len(stocks)} 只股票:")
            for i, stock in enumerate(stocks, 1):
                logger.info(f"  {i}. {stock.exchange}:{stock.symbol} {stock.name}")

            # 推送到Redis（如果Redis可用）
            if redis_available and selection_writer:
                batch_id = f"SELECT_{date}_001"

                # 创建选股消息
                selection_message = SelectionMessage(
                    type="stock_selection",
                    version="1.0",
                    timestamp=TimestampUtil.current_timestamp(),
                    batch_id=batch_id,
                    strategy_id=strategy_id if use_strategy else "DEFAULT",
                    total_count=len(stocks),
                    stocks=stocks
                )

                # 推送到Redis
                msg_id = selection_writer.write_selection(
                    date=date,
                    batch_id=batch_id,
                    strategy_id=strategy_id if use_strategy else "DEFAULT",
                    stocks=stocks,
                    total_count=len(stocks)
                )

                logger.info(f"选股数据已推送到Redis: Key=selection:{settings.selection.data_structure}:{date}, MsgID={msg_id}")
                logger.info(f"过期时间: {settings.selection.expire_seconds}秒 ({settings.selection.expire_seconds // 3600}小时)")

        logger.info("\n" + "="*60)
        logger.info("选股服务执行完成")
        logger.info("="*60)

        if redis_available:
            logger.info(f"选股结果已存入数据库并推送到Redis（过期时间{settings.selection.expire_seconds}秒）")
        else:
            logger.info("选股结果已存入数据库（Redis不可用，未推送）")

    except Exception as e:
        logger.error(f"选股服务执行失败: {e}", exc_info=True)
        raise
    finally:
        # 清理资源
        if selection_writer:
            selection_writer.close()
        close_db_pool()
        logger.info("资源清理完成")


def main(real_flag: bool = False):
    """主函数"""

    # 配置文件路径
    config_path = 'config/config.ini'

    # 从配置文件加载配置
    try:
        update_global_settings(config_path)
        # 初始化日志系统
        setup_logging()
        logger = get_logger("main")
        logger.info(f"配置文件加载成功: {config_path}")
    except Exception as e:
        print(f"配置文件加载失败: {e}")
        return

    # 从配置文件获取参数
    start_date = settings.backtest.start_date
    end_date = settings.backtest.end_date
    use_strategy = settings.backtest.use_strategy
    strategy_id = settings.backtest.strategy_id
    default_selection_count = settings.backtest.default_selection_count
    strategy_params = settings.backtest.strategy_params

    # 打印配置信息
    logger.info("="*60)
    logger.info("选股服务配置信息")
    logger.info("="*60)
    logger.info(f"配置文件: {config_path}")
    logger.info(f"选股日期: {start_date} ~ {end_date}")
    logger.info(f"使用策略: {'是' if use_strategy else '否'}")
    if use_strategy:
        logger.info(f"策略ID: {strategy_id}")
        logger.info(f"策略参数: {strategy_params}")
    logger.info(f"选股数量: {default_selection_count}")
    logger.info(f"Redis: {settings.redis.host}:{settings.redis.port} DB={settings.redis.db}")
    logger.info(f"数据结构: {settings.selection.data_structure.upper()}")
    logger.info(f"Key前缀: {settings.selection.key_prefix}")
    logger.info(f"Key过期时间: {settings.selection.expire_seconds}秒 ({settings.selection.expire_seconds // 3600}小时)")
    logger.info(f"数据库: {settings.database.host}:{settings.database.port}/{settings.database.database}")
    logger.info("="*60)

    # 运行选股服务
    run_selection_service(
        start_date=start_date,
        end_date=end_date,
        strategy_id=strategy_id if use_strategy else None,
        use_strategy=use_strategy,
        default_selection_count=default_selection_count,
        strategy_params=strategy_params,
        real_flag=real_flag
    )


if __name__ == "__main__":
    main(real_flag=True)
