"""
股池数据读取示例
"""

from baostock_tool.redis_service.selection.reader import SelectionReader


def main():
    """读取股池数据示例"""
    
    # 创建读取器
    reader = SelectionReader()
    
    date = "20260317"
    
    # 检查Stream是否存在
    if not reader.stream_exists(date):
        print(f"Stream selection:stream:{date} does not exist!")
        print("Please run write_selection_demo.py first")
        return
    
    print(f"Reading from selection:stream:{date}")
    print(f"Stream length: {reader.get_stream_length(date)}")
    print("-" * 50)
    
    # 方式1: 从头开始读取
    print("\n=== Reading from beginning ===")
    messages = reader.read_from_beginning(date, count=10)
    selections = reader.parse_messages(messages)
    
    for selection in selections:
        print(f"Batch ID: {selection.batch_id}")
        print(f"Strategy: {selection.strategy_id}")
        print(f"Total Count: {selection.total_count}")
        print(f"Stocks: {len(selection.stocks)}")
        
        for stock in selection.stocks:
            print(f"  - {stock.exchange}:{stock.symbol} {stock.name}")
            print(f"    Prev Close: {stock.basic_info.prev_close}")
            print(f"    MA10: {stock.basic_info.ma10}")
            if stock.technical_indicators:
                print(f"    MA5: {stock.technical_indicators.ma5}")
        print()
    
    # 方式2: 读取最新消息
    print("\n=== Reading latest ===")
    messages = reader.read_latest(date, count=5)
    selections = reader.parse_messages(messages)
    
    for selection in selections:
        print(f"Latest Batch: {selection.batch_id}, Stocks: {len(selection.stocks)}")
    
    # 方式3: 使用消费者组读取
    print("\n=== Reading with consumer group ===")
    
    # 先确保消费者组存在
    group_name = "strategy_consumer"
    reader.create_consumer_group(date, group_name)
    
    messages = reader.read_with_consumer_group(
        date=date,
        group_name=group_name,
        consumer_name="strategy_1",
        count=10
    )
    
    if messages:
        selections = reader.parse_messages(messages)
        
        # 确认消息
        msg_ids = [msg[0] for msg in messages]
        ack_count = reader.ack_message(date, group_name, *msg_ids)
        print(f"Received {len(messages)} messages, acknowledged {ack_count}")
    else:
        print("No new messages")


if __name__ == "__main__":
    main()
