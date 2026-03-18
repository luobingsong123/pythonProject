"""
Redis Service 主入口

统一管理 Redis Pub/Sub 服务的启动和数据消费流程
"""

import sys
import os
import argparse
import signal
from typing import Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from config.config_loader import load_config, update_global_settings
from backtest.engine import BacktestEngine
from examples.consumer_demo import StockConsumer

# 加载配置
config = load_config('config/config.ini')

# 更新全局配置
update_global_settings('config/config.ini')

class RedisServiceManager:
    """Redis 服务管理器"""
    
    def __init__(self):
        self.consumer: Optional[StockConsumer] = None
        self.backtest_engine: Optional[BacktestEngine] = None
        self.running = False
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n\n收到信号 {signum}，正在停止服务...")
        self.stop()
        sys.exit(0)
    
    def start_backtest_service(self, config_args: dict):
        """
        启动回测服务
        
        Args:
            config_args: 回测配置参数
        """
        print("\n" + "="*60)
        print("启动回测服务")
        print("="*60)
        
        # 创建回测配置
        from config.settings import BacktestConfig
        config = BacktestConfig(**config_args)
        
        # 创建并初始化回测引擎
        self.backtest_engine = BacktestEngine(config)
        
        # 数据库配置
        db_config = {
            "host": settings.database.host,
            "port": settings.database.port,
            "user": settings.database.user,
            "password": settings.database.password,
            "database": settings.database.database,
            "charset": settings.database.charset
        }
        
        try:
            self.backtest_engine.initialize(db_config)
            print("✓ 回测引擎初始化成功")
            
            # 运行回测
            self.backtest_engine.run()
            print("✓ 回测服务运行完成")
            
        except Exception as e:
            print(f"✗ 回测服务启动失败: {e}")
            raise
        finally:
            if self.backtest_engine:
                self.backtest_engine.close()
    
    def start_consumer_service(self, date: str, max_snapshots: int = 100):
        """
        启动消费服务
        
        Args:
            date: 消费日期
            max_snapshots: 最大消费快照数
        """
        print("\n" + "="*60)
        print("启动消费服务")
        print("="*60)
        
        self.consumer = StockConsumer()
        self.setup_signal_handlers()
        
        try:
            self.consumer.run(date)
            print("✓ 消费服务运行完成")
        except Exception as e:
            print(f"✗ 消费服务运行失败: {e}")
            raise
        finally:
            if self.consumer:
                self.consumer.close()
    
    def start_full_pipeline(self, date: str, use_strategy: bool = True):
        """
        启动完整流程：回测 -> 消费
        
        Args:
            date: 日期
            use_strategy: 是否使用选股策略
        """
        print("\n" + "#"*60)
        print("# 完整流程启动")
        print("#"*60)
        
        # 步骤1: 运行回测服务
        config_args = {
            "start_date": date,
            "end_date": date,
            "strategy_id": settings.backtest.strategy_id,
            "use_strategy": use_strategy,
            "default_selection_count": settings.backtest.default_selection_count
        }
        
        try:
            self.start_backtest_service(config_args)
            
            # 步骤2: 启动消费服务
            self.start_consumer_service(date)
            
            print("\n" + "#"*60)
            print("# 完整流程执行成功")
            print("#"*60)
            
        except Exception as e:
            print(f"\n✗ 完整流程执行失败: {e}")
            raise
    
    def stop(self):
        """停止所有服务"""
        print("\n正在停止服务...")
        
        if self.consumer:
            self.consumer.close()
            self.consumer = None
        
        if self.backtest_engine:
            self.backtest_engine.close()
            self.backtest_engine = None
        
        print("服务已停止")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Redis Service 统一入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 启动完整流程（回测+消费）
  python main.py --mode full --date 20241008
  
  # 仅启动回测服务
  python main.py --mode backtest --date 20241008
  
  # 仅启动消费服务
  python main.py --mode consumer --date 20241008
  
  # 消费服务指定最大快照数
  python main.py --mode consumer --date 20241008 --max-snapshots 500
  
  # 不使用选股策略
  python main.py --mode full --date 20241008 --no-strategy
        """
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'backtest', 'consumer'],
        default='full',
        help='运行模式: full(完整流程), backtest(仅回测), consumer(仅消费)'
    )
    
    parser.add_argument(
        '--date',
        type=str,
        default='20241008',
        help='日期，格式YYYYMMDD'
    )
    
    parser.add_argument(
        '--max-snapshots',
        type=int,
        default=100,
        help='消费服务最大行情快照数 (仅consumer模式)'
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
        print("  请检查配置文件路径和格式是否正确")
    
    # 打印配置信息
    print("\n" + "="*60)
    print("Redis Service 配置信息")
    print("="*60)
    print(f"配置文件: {args.config}")
    print(f"运行模式: {args.mode}")
    print(f"日期: {args.date}")
    print(f"使用策略: {'否' if args.no_strategy else '是'}")
    if args.mode == 'consumer':
        print(f"最大快照数: {args.max_snapshots}")
    print("\nRedis配置:")
    print(f"  Host: {settings.redis.host}")
    print(f"  Port: {settings.redis.port}")
    print(f"  DB: {settings.redis.db}")
    print("\n数据库配置:")
    print(f"  Host: {settings.database.host}")
    print(f"  Port: {settings.database.port}")
    print(f"  Database: {settings.database.database}")
    print("="*60)
    
    # 创建服务管理器
    manager = RedisServiceManager()
    
    try:
        if args.mode == 'full':
            manager.start_full_pipeline(args.date, use_strategy=not args.no_strategy)
        elif args.mode == 'backtest':
            config_args = {
                "start_date": args.date,
                "end_date": args.date,
                "strategy_id": settings.backtest.strategy_id,
                "use_strategy": not args.no_strategy,
                "default_selection_count": settings.backtest.default_selection_count
            }
            manager.start_backtest_service(config_args)
        elif args.mode == 'consumer':
            manager.start_consumer_service(args.date, args.max_snapshots)
        
        print("\n✓ Redis Service 运行完成\n")
        
    except KeyboardInterrupt:
        print("\n\n✓ 用户中断服务")
    except Exception as e:
        print(f"\n✗ 服务运行失败: {e}")
        sys.exit(1)
    finally:
        manager.stop()


if __name__ == "__main__":
    main()
