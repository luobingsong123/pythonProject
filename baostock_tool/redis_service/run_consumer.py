"""
独立消费者启动脚本

可随时独立启动，消费选股池和行情数据
将数据写入文件而非打印

使用示例:
  python run_consumer.py --date 20241008
  python run_consumer.py --date 20241008 --output data.csv
"""

import sys
import os
import argparse
import signal
import time
import csv
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from config.config_loader import load_config, update_global_settings
from selection.reader import SelectionReader
from market.subscriber import SnapshotSubscriber
from models.snapshot import SnapshotData


class FileConsumer:
    """文件消费者 - 将数据写入文件"""
    
    def __init__(self, output_file: str = None):
        """初始化消费者"""
        self.selection_reader = SelectionReader()
        self.snapshot_subscriber = SnapshotSubscriber()
        self.selected_stocks: List[Dict[str, Any]] = []
        
        # 统计数据
        self.stats = {
            "selection_count": 0,
            "snapshot_count": 0,
            "stock_stats": {},
            "start_time": None,
            "end_time": None
        }
        
        # 输出文件
        self.output_file = output_file
        self.csv_file = None
        self.csv_writer = None
    
    def _init_csv(self):
        """初始化CSV文件"""
        if self.output_file:
            self.csv_file = open(self.output_file, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            # 写入表头
            self.csv_writer.writerow([
                'timestamp', 'exchange', 'symbol', 'last_price', 
                'volume', 'amount', 'bid_price', 'bid_volume', 
                'ask_price', 'ask_volume', 'date', 'time'
            ])
    
    def _write_snapshot(self, snapshot: SnapshotData):
        """将快照数据写入CSV文件"""
        if self.csv_writer:
            data = snapshot.data
            self.csv_writer.writerow([
                snapshot.timestamp,
                snapshot.exchange,
                snapshot.symbol,
                data.last_price,
                data.volume,
                data.amount,
                '|'.join(str(p) for p in data.bid_price),
                '|'.join(str(v) for v in data.bid_volume),
                '|'.join(str(p) for p in data.ask_price),
                '|'.join(str(v) for v in data.ask_volume),
                data.date,
                data.timestamp
            ])
    
    def consume_selection(self, date: str, wait_timeout: int = 30) -> bool:
        """
        消费选股池数据
        
        Args:
            date: 日期
            wait_timeout: 等待超时时间（秒）
            
        Returns:
            bool: 是否成功消费到数据
        """
        start_time = time.time()
        
        while time.time() - start_time < wait_timeout:
            messages = self.selection_reader.read_latest(date, count=1)
            
            if messages:
                selections = self.selection_reader.parse_messages(messages)
                
                if selections:
                    selection = selections[0]
                    
                    self.selected_stocks = [
                        {
                            "symbol": stock.symbol,
                            "exchange": stock.exchange,
                            "name": stock.name
                        }
                        for stock in selection.stocks
                    ]
                    
                    self.stats["selection_count"] = len(self.selected_stocks)
                    return True
            
            time.sleep(1)
        
        return False
    
    def consume_market_data(
        self,
        date: str,
        max_snapshots: int = 999999999,
        timeout: int = 60
    ) -> int:
        """
        消费行情数据
        
        Args:
            date: 日期
            max_snapshots: 最大消费快照数
            timeout: 超时时间（秒）
            
        Returns:
            int: 消费的快照数量
        """
        if not self.selected_stocks:
            return 0
        
        # 构建订阅模式
        channels = [
            f"market:snapshot:{stock['exchange']}:{stock['symbol']}"
            for stock in self.selected_stocks
        ]
        
        count = 0
        start_time = time.time()
        
        try:
            pattern = "market:snapshot:*"
            
            for snapshot in self.snapshot_subscriber.subscribe(pattern):
                # 检查是否是指定股票的行情
                if any(
                    s['exchange'] == snapshot.exchange and 
                    s['symbol'] == snapshot.symbol 
                    for s in self.selected_stocks
                ):
                    count += 1
                    
                    # 写入文件
                    self._write_snapshot(snapshot)
                    
                    # 更新统计
                    stock_key = f"{snapshot.exchange}:{snapshot.symbol}"
                    self.stats["stock_stats"][stock_key] = \
                        self.stats["stock_stats"].get(stock_key, 0) + 1
                    
                    if count >= max_snapshots:
                        break
                    
                    if time.time() - start_time > timeout:
                        break
                    
        except KeyboardInterrupt:
            pass
        except Exception:
            pass
        
        self.stats["snapshot_count"] = count
        return count
    
    def run(self, date: str, max_snapshots: int = 999999999, timeout: int = 60):
        """
        运行消费者
        
        Args:
            date: 日期
            max_snapshots: 最大消费快照数
            timeout: 超时时间
        """
        self.stats["start_time"] = time.time()
        
        # 初始化CSV
        self._init_csv()
        
        # 步骤1: 消费选股池
        if not self.consume_selection(date):
            return
        
        # 步骤2: 消费行情数据
        self.consume_market_data(date, max_snapshots, timeout)
        
        self.stats["end_time"] = time.time()
    
    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        duration = 0
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = self.stats["end_time"] - self.stats["start_time"]
        
        return {
            "selection_count": self.stats["selection_count"],
            "snapshot_count": self.stats["snapshot_count"],
            "duration_seconds": round(duration, 2),
            "stock_stats": self.stats["stock_stats"],
            "output_file": self.output_file
        }
    
    def close(self):
        """关闭消费者"""
        if self.csv_file:
            self.csv_file.close()
        self.selection_reader.close()
        self.snapshot_subscriber.close()


class ConsumerRunner:
    """消费者运行器"""
    
    def __init__(self):
        self.consumer = None
        self.logger = None
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.stop()
        sys.exit(0)
    
    def run(self, date: str, max_snapshots: int = 100, output_file: str = None):
        """
        运行消费者
        
        Args:
            date: 消费日期
            max_snapshots: 最大消费快照数
            output_file: 输出文件路径
        """
        from utils.log_manager import get_logger
        self.logger = get_logger("consumer_runner")
        
        self.logger.info("="*60)
        self.logger.info("独立消费者启动")
        self.logger.info("="*60)
        self.logger.info(f"日期: {date}, 最大快照数: {max_snapshots}")
        self.logger.info(f"输出文件: {output_file}")
        self.logger.info(f"Redis: {settings.redis.host}:{settings.redis.port} DB={settings.redis.db}")
        self.logger.info("="*60)
        
        self.consumer = FileConsumer(output_file)
        self.setup_signal_handlers()
        
        try:
            self.consumer.run(date, max_snapshots)
        except Exception as e:
            self.logger.error(f"消费者运行失败: {e}")
            raise
        finally:
            self.stop()
    
    def stop(self):
        """停止消费者"""
        if self.consumer:
            # 获取统计摘要
            summary = self.consumer.get_summary()
            
            # 打印统计信息
            print("\n" + "="*60)
            print("消费统计")
            print("="*60)
            print(f"选股数量: {summary['selection_count']}")
            print(f"行情快照: {summary['snapshot_count']}")
            print(f"耗时: {summary['duration_seconds']} 秒")
            if summary['output_file']:
                print(f"输出文件: {summary['output_file']}")
            
            if summary['stock_stats']:
                print(f"\n各股票行情统计:")
                for stock_key, count in sorted(summary['stock_stats'].items()):
                    print(f"  {stock_key}: {count} 条")
            
            print("="*60)
            
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
  python run_consumer.py --date 20241008 --output data.csv
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
        '--output',
        type=str,
        default=None,
        help='输出文件路径（CSV格式）'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.ini',
        help='配置文件路径（默认: config/config.ini）'
    )
    
    args = parser.parse_args()
    
    # 从配置文件加载配置
    from utils.log_manager import setup_logging, get_logger
    
    try:
        update_global_settings(args.config)
        setup_logging()
        logger = get_logger("main")
        logger.info(f"配置文件加载成功: {args.config}")
    except Exception as e:
        print(f"配置文件加载失败: {e}")
    
    # 创建并运行消费者
    runner = ConsumerRunner()
    
    try:
        runner.run(args.date, args.max_snapshots, args.output)
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"消费者运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
