"""
消费者Demo - 消费选股池和行情数据

业务流程：
1. 先消费选股池数据并打印
2. 再逐个消费行情数据并打印
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from typing import List, Dict, Any

from selection.reader import SelectionReader
from market.subscriber import SnapshotSubscriber
from models.snapshot import SnapshotData
from models.stock_selection import SelectionMessage


class StockConsumer:
    """股票数据消费者"""
    
    def __init__(self):
        """初始化消费者"""
        self.selection_reader = SelectionReader()
        self.snapshot_subscriber = SnapshotSubscriber()
        self.selected_stocks: List[Dict[str, Any]] = []
        self.consumed_snapshots: List[SnapshotData] = []
    
    def consume_selection(self, date: str, wait_timeout: int = 30) -> bool:
        """
        消费选股池数据
        
        Args:
            date: 日期
            wait_timeout: 等待超时时间（秒）
            
        Returns:
            bool: 是否成功消费到数据
        """
        print(f"\n{'='*60}")
        print(f"[Step 1] 消费选股池数据 - {date}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        while time.time() - start_time < wait_timeout:
            # 尝试读取股池数据
            messages = self.selection_reader.read_latest(date, count=1)
            
            if messages:
                # 解析消息
                selections = self.selection_reader.parse_messages(messages)
                
                if selections:
                    selection = selections[0]
                    self._print_selection(selection)
                    
                    # 保存选股结果
                    self.selected_stocks = [
                        {
                            "symbol": stock.symbol,
                            "exchange": stock.exchange,
                            "name": stock.name
                        }
                        for stock in selection.stocks
                    ]
                    
                    print(f"\n✓ 成功消费选股池数据，共 {len(self.selected_stocks)} 只股票")
                    return True
            
            print("  等待选股池数据...")
            time.sleep(1)
        
        print(f"\n✗ 消费选股池数据超时（{wait_timeout}秒）")
        return False
    
    def _print_selection(self, selection: SelectionMessage):
        """
        打印选股池数据
        
        Args:
            selection: 选股消息
        """
        print(f"\n📊 选股批次信息:")
        print(f"  批次ID: {selection.batch_id}")
        print(f"  策略ID: {selection.strategy_id}")
        print(f"  选股总数: {selection.total_count}")
        print(f"  时间戳: {selection.timestamp}")
        print(f"  版本: {selection.version}")
        
        print(f"\n📈 选股列表:")
        print("-" * 60)
        
        for i, stock in enumerate(selection.stocks, 1):
            print(f"\n  [{i}] {stock.exchange}:{stock.symbol} {stock.name}")
            
            # 打印基本信息
            if stock.basic_info:
                print(f"      昨收价: {stock.basic_info.prev_close}")
                print(f"      MA10: {stock.basic_info.ma10}")
                print(f"      近5日最高: {stock.basic_info.ma5_high}")
                print(f"      量比: {stock.basic_info.volume_ratio}")
                print(f"      换手率: {stock.basic_info.turnover_rate}%")
            
            # 打印技术指标
            if stock.technical_indicators:
                print(f"      技术指标:")
                print(f"        MA5: {stock.technical_indicators.ma5}")
                print(f"        MA10: {stock.technical_indicators.ma10}")
                print(f"        MA20: {stock.technical_indicators.ma20}")
            
            # 打印基本面数据
            if stock.fundamental_data:
                print(f"      基本面:")
                print(f"        PE: {stock.fundamental_data.pe}")
                print(f"        PB: {stock.fundamental_data.pb}")
                print(f"        市值: {stock.fundamental_data.market_cap:.2f}百万")
            
            # 打印5天分钟成交量统计
            volume_days = [
                ("第1天", stock.minute_volume_5d_01),
                ("第2天", stock.minute_volume_5d_02),
                ("第3天", stock.minute_volume_5d_03),
                ("第4天", stock.minute_volume_5d_04),
                ("第5天", stock.minute_volume_5d_05),
            ]
            
            for day_name, volumes in volume_days:
                if volumes:
                    total_volume = sum(v.volume for v in volumes)
                    print(f"      {day_name}成交量: {total_volume:,}")
    
    def consume_market_data(
        self,
        date: str,
        max_snapshots: int = 1000,
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
            print("\n✗ 没有选股数据，无法消费行情数据")
            return 0
        
        print(f"\n{'='*60}")
        print(f"[Step 2] 消费行情数据 - {date}")
        print(f"{'='*60}")
        print(f"将消费以下股票的行情数据:")
        for stock in self.selected_stocks:
            print(f"  - {stock['exchange']}:{stock['symbol']} {stock['name']}")
        
        # 构建订阅模式
        channels = [
            f"market:snapshot:{stock['exchange']}:{stock['symbol']}"
            for stock in self.selected_stocks
        ]
        
        print(f"\n📡 订阅 {len(channels)} 个行情通道")
        print("-" * 60)
        
        count = 0
        start_time = time.time()
        
        try:
            # 使用回调方式订阅
            def on_snapshot(snapshot: SnapshotData):
                nonlocal count
                count += 1
                self._print_snapshot(snapshot, count)
                self.consumed_snapshots.append(snapshot)
                
                # 达到最大数量时停止
                if count >= max_snapshots:
                    raise StopIteration()
            
            # 订阅所有选股股票的行情
            pattern = "market:snapshot:*"
            print(f"  订阅模式: {pattern}")
            print(f"  等待行情数据... (最多{max_snapshots}条, 超时{timeout}秒)\n")
            
            for snapshot in self.snapshot_subscriber.subscribe(pattern):
                # 检查是否是指定股票的行情
                stock_key = f"{snapshot.exchange}:{snapshot.symbol}"
                if any(
                    s['exchange'] == snapshot.exchange and 
                    s['symbol'] == snapshot.symbol 
                    for s in self.selected_stocks
                ):
                    count += 1
                    self._print_snapshot(snapshot, count)
                    self.consumed_snapshots.append(snapshot)
                    
                    if count >= max_snapshots:
                        break
                    
                    if time.time() - start_time > timeout:
                        print(f"\n⏱ 行情数据消费超时")
                        break
                
        except StopIteration:
            print(f"\n✓ 已达到最大消费数量 {max_snapshots}")
        except KeyboardInterrupt:
            print(f"\n✓ 用户中断")
        except Exception as e:
            print(f"\n✗ 消费行情数据出错: {e}")
        
        print(f"\n{'='*60}")
        print(f"✓ 共消费 {count} 条行情快照")
        print(f"{'='*60}")
        
        return count
    
    def _print_snapshot(self, snapshot: SnapshotData, index: int):
        """
        打印行情快照
        
        Args:
            snapshot: 行情快照
            index: 序号
        """
        data = snapshot.data
        
        print(f"\n📈 [{index}] {snapshot.exchange}:{snapshot.symbol}")
        print(f"    时间: {data.date} {data.timestamp}")
        print(f"    最新价: {data.last_price}")
        print(f"    成交量: {data.volume:,}")
        print(f"    成交额: {data.amount:,.2f}")
        
        # 买卖盘
        print(f"    买盘:")
        for i, (price, vol) in enumerate(zip(data.bid_price[:5], data.bid_volume[:5]), 1):
            print(f"      买{i}: {price:.2f} x {vol:,}")
        
        print(f"    卖盘:")
        for i, (price, vol) in enumerate(zip(data.ask_price[:5], data.ask_volume[:5]), 1):
            print(f"      卖{i}: {price:.2f} x {vol:,}")
    
    def run(self, date: str):
        """
        运行消费者
        
        Args:
            date: 日期
        """
        print(f"\n{'#'*60}")
        print(f"# 股票数据消费者启动 - {date}")
        print(f"{'#'*60}")
        
        # 步骤1: 消费选股池
        if not self.consume_selection(date):
            print("\n✗ 消费流程终止")
            return
        
        # 步骤2: 消费行情数据
        count = self.consume_market_data(date)
        
        # 打印消费统计
        self._print_summary()
    
    def _print_summary(self):
        """打印消费统计"""
        print(f"\n{'#'*60}")
        print(f"# 消费统计")
        print(f"{'#'*60}")
        print(f"选股数量: {len(self.selected_stocks)}")
        print(f"行情快照: {len(self.consumed_snapshots)}")
        
        if self.consumed_snapshots:
            # 按股票统计
            stock_stats: Dict[str, int] = {}
            for snapshot in self.consumed_snapshots:
                key = f"{snapshot.exchange}:{snapshot.symbol}"
                stock_stats[key] = stock_stats.get(key, 0) + 1
            
            print(f"\n各股票行情统计:")
            for stock_key, count in sorted(stock_stats.items()):
                print(f"  {stock_key}: {count} 条")
    
    def close(self):
        """关闭消费者"""
        print("\n关闭消费者...")
        self.selection_reader.close()
        self.snapshot_subscriber.close()
        print("消费者已关闭")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='股票数据消费者')
    parser.add_argument('--date', type=str, default='20241008',
                        help='日期，格式YYYYMMDD')
    parser.add_argument('--max-snapshots', type=int, default=100,
                        help='最大消费行情快照数')
    
    args = parser.parse_args()
    
    # 创建消费者
    consumer = StockConsumer()
    
    try:
        # 运行消费者
        consumer.run(args.date)
    except KeyboardInterrupt:
        print("\n\n用户中断")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
