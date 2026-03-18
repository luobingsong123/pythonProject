"""
独立消费者启动脚本

可随时独立启动，消费选股池和行情数据

使用示例:
  python run_consumer.py --date 20241008
  python run_consumer.py --date 20241008 --max-snapshots 500
"""

import sys
import os
import argparse
import signal

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from config.config_loader import load_config, update_global_settings
from examples.consumer_demo import StockConsumer


class ConsumerRunner:
    """消费者运行器"""
    
    def __init__(self):
        self.consumer = None
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n\n收到信号 {signum}，正在停止消费者...")
        self.stop()
        sys.exit(0)
    
    def run(self, date: str, max_snapshots: int = 100):
        """
        运行消费者
        
        Args:
            date: 消费日期
            max_snapshots: 最大消费快照数
        """
        print("\n" + "="*60)
        print("独立消费者启动")
        print("="*60)
        print(f"日期: {date}")
        print(f"最大快照数: {max_snapshots}")
        print("\nRedis配置:")
        print(f"  Host: {settings.redis.host}")
        print(f"  Port: {settings.redis.port}")
        print(f"  DB: {settings.redis.db}")
        print("="*60)
        
        self.consumer = StockConsumer()
        self.setup_signal_handlers()
        
        try:
            self.consumer.run(date)
            print("\n✓ 消费者运行完成")
        except Exception as e:
            print(f"\n✗ 消费者运行失败: {e}")
            raise
        finally:
            self.stop()
    
    def stop(self):
        """停止消费者"""
        if self.consumer:
            self.consumer.close()
            self.consumer = None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='独立消费者启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python run_consumer.py --date 20241008
  python run_consumer.py --date 20241008 --max-snapshots 500
        """
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
        help='最大消费行情快照数'
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
    
    # 创建并运行消费者
    runner = ConsumerRunner()
    
    try:
        runner.run(args.date, args.max_snapshots)
    except KeyboardInterrupt:
        print("\n\n✓ 用户中断")
    except Exception as e:
        print(f"\n✗ 消费者运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
