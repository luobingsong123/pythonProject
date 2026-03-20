"""
测试 List 模式的读写功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config_loader import update_global_settings
from selection.writer import SelectionWriter
from selection.reader import SelectionReader
from models.stock_selection import StockInfo, BasicInfo
from utils.serializer import TimestampUtil

# 加载配置
update_global_settings('config/config.ini')

# 初始化写入器和读取器（强制使用 List 模式）
writer = SelectionWriter(data_structure='list')
reader = SelectionReader(data_structure='list')

date = "20240320"
batch_id = "TEST_BATCH_001"
strategy_id = "TEST_STRATEGY"

# 创建测试股票
test_stocks = [
    StockInfo(
        symbol="600000",
        exchange="SSE",
        name="测试股票1",
        basic_info=BasicInfo(
            prev_close=10.0,
            ma10=10.5,
            ma5_high=10.8,
            volume_ratio=1.2,
            turnover_rate=0.5
        )
    ),
    StockInfo(
        symbol="000001",
        exchange="SZSE",
        name="测试股票2",
        basic_info=BasicInfo(
            prev_close=20.0,
            ma10=20.5,
            ma5_high=20.8,
            volume_ratio=1.3,
            turnover_rate=0.6
        )
    )
]

print("="*60)
print("测试 List 模式")
print("="*60)

# 测试写入
print("\n[测试1] 写入选股数据...")
msg_id = writer.write_selection(
    date=date,
    batch_id=batch_id,
    strategy_id=strategy_id,
    stocks=test_stocks
)
print(f"写入成功，消息ID: {msg_id}")

# 测试读取长度
print("\n[测试2] 读取数据长度...")
length = reader.get_length(date)
print(f"数据长度: {length}")

# 测试读取最新消息
print("\n[测试3] 读取最新消息...")
messages = reader.read_latest(date, count=1)
print(f"读取到 {len(messages)} 条消息")

if messages:
    print(f"消息ID: {messages[0][0]}")
    
    # 测试解析消息
    print("\n[测试4] 解析消息...")
    selections = reader.parse_messages(messages)
    print(f"解析到 {len(selections)} 条选股数据")
    
    if selections:
        selection = selections[0]
        print(f"批次ID: {selection.batch_id}")
        print(f"策略ID: {selection.strategy_id}")
        print(f"股票数量: {len(selection.stocks)}")
        print("股票列表:")
        for stock in selection.stocks:
            print(f"  - {stock.exchange}:{stock.symbol} {stock.name}")

# 测试从头读取
print("\n[测试5] 从头读取消息...")
messages_from_start = reader.read_from_beginning(date, count=10)
print(f"从头读取到 {len(messages_from_start)} 条消息")

# 测试写入多条数据
print("\n[测试6] 写入多条数据...")
for i in range(3):
    writer.write_selection(
        date=date,
        batch_id=f"TEST_BATCH_{i:03d}",
        strategy_id=strategy_id,
        stocks=test_stocks
    )
    print(f"写入第 {i+1} 条数据")

# 测试读取最新N条
print("\n[测试7] 读取最新3条消息...")
messages = reader.read_latest(date, count=3)
print(f"读取到 {len(messages)} 条消息")
for i, (msg_id, msg_data) in enumerate(messages):
    print(f"  消息{i+1} ID: {msg_id}")

print("\n[测试8] 再次读取数据长度...")
length = reader.get_length(date)
print(f"数据长度: {length}")

# 清理
print("\n[测试9] 清理数据...")
deleted = writer.delete(date)
print(f"删除结果: {deleted}")

print("\n" + "="*60)
print("测试完成")
print("="*60)

writer.close()
reader.close()
