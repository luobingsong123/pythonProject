"""
Redis Service 主入口

启动回测服务，将选股结果推送到 Redis
消费者请使用 run_consumer.py 独立启动
"""

import sys
import os
import argparse

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from config.config_loader import update_global_settings
from backtest.engine import BacktestEngine


def start_backtest_service(date: str, use_strategy: bool = True):
    """
    启动回测服务
    
    Args:
        date: 回测日期
        use_strategy: 是否使用选股策略
    """
    print("\n" + "="*60)
    print("启动回测服务")
    print("="*60)
    
    # 创建回测配置
    from config.settings import BacktestConfig
    config = BacktestConfig(
        start_date=date,
        end_date=date,
        strategy_id=settings.backtest.strategy_id,
        use_strategy=use_strategy,
        default_selection_count=settings.backtest.default_selection_count
    )
    
    # 创建并初始化回测引擎
    engine = BacktestEngine(config)
    
    # 数据库配置
    db_config = {
        "host": settings.database.host,
        "port": settings.database.port,
        "user": settings.database.user,
        "password": settings.database.password,
        "database": settings.database.database,
        "charset": settings.database.charset
    }
    
    engine.initialize(db_config)
    print("✓ 回测引擎初始化成功")
    
    # 运行回测
    engine.run()
    print("✓ 回测服务运行完成")
    
    # 保持连接不关闭，等待消费者随时消费
    print("\n回测完成，选股数据已推送到 Redis")
    print("使用 run_consumer.py 启动消费者消费数据")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Redis Service 回测服务入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 启动回测服务
  python main.py --date 20241008
  
  # 不使用选股策略
  python main.py --date 20241008 --no-strategy
  
  # 消费者在另一个终端独立启动
  python run_consumer.py --date 20241008
        """
    )
    
    parser.add_argument(
        '--date',
        type=str,
        default='20241008',
        help='日期，格式YYYYMMDD'
    )
    
    parser.add_argument(
        '--no-strategy',
        action='store_true',
        help='不使用选股策略，使用默认选股数量'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.ini',
        help='配置文件路径（默认: config/config.ini）'
    )
    
    args = parser.parse_args()
    
    # 从配置文件加载配置
    try:
        print("正在加载配置文件...")
        update_global_settings(args.config)
        print(f"✓ 配置文件加载成功: {args.config}")
    except Exception as e:
        print(f"⚠ 配置文件加载失败，使用默认配置: {e}")

    # 确定是否使用策略（命令行参数优先于配置文件）
    use_strategy = not args.no_strategy
    if use_strategy and not settings.backtest.use_strategy:
        # 如果命令行没有指定，使用配置文件的值
        use_strategy = settings.backtest.use_strategy

    # 打印配置信息
    print("\n" + "="*60)
    print("Redis Service 配置信息")
    print("="*60)
    print(f"配置文件: {args.config}")
    print(f"日期: {args.date}")
    print(f"使用策略: {'是' if use_strategy else '否'}")
    if use_strategy:
        print(f"策略ID: {settings.backtest.strategy_id}")
    print("\nRedis配置:")
    print(f"  Host: {settings.redis.host}")
    print(f"  Port: {settings.redis.port}")
    print(f"  DB: {settings.redis.db}")
    print("\n数据库配置:")
    print(f"  Host: {settings.database.host}")
    print(f"  Port: {settings.database.port}")
    print(f"  Database: {settings.database.database}")
    print("="*60)
    
    # 启动回测服务
    start_backtest_service(args.date, use_strategy=use_strategy)


if __name__ == "__main__":
    main()
