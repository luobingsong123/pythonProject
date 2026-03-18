"""
股池数据写入示例
"""

import time
from selection.writer import SelectionWriter
from models.stock_selection import (
    SelectionMessage,
    StockInfo,
    BasicInfo,
    MinuteVolume,
    TechnicalIndicators,
    FundamentalData
)


def main():
    """写入股池数据示例"""
    
    # 创建写入器
    writer = SelectionWriter()
    
    # 创建股票信息
    stocks = [
        StockInfo(
            symbol="600036",
            exchange="SSE",
            name="招商银行",
            basic_info=BasicInfo(
                prev_close=32.50,
                ma10=31.80,
                ma5_high=33.00,
                volume_ratio=1.2,
                turnover_rate=0.5
            ),
            minute_volume_5d=[
                MinuteVolume(time="09:35", volume=1234),
                MinuteVolume(time="09:40", volume=2345),
                MinuteVolume(time="09:45", volume=3456),
            ],
            technical_indicators=TechnicalIndicators(
                ma5=31.20,
                ma10=31.80,
                ma20=32.10,
                vol_ma5=4567890,
                vol_ma10=5678901
            ),
            fundamental_data=FundamentalData(
                pe=8.5,
                pb=1.2,
                market_cap=820000
            )
        ),
        StockInfo(
            symbol="600519",
            exchange="SSE",
            name="贵州茅台",
            basic_info=BasicInfo(
                prev_close=1850.00,
                ma10=1800.00,
                ma5_high=1900.00,
                volume_ratio=1.5,
                turnover_rate=0.3
            ),
            minute_volume_5d=[
                MinuteVolume(time="09:35", volume=500),
                MinuteVolume(time="09:40", volume=800),
                MinuteVolume(time="09:45", volume=1200),
            ],
            technical_indicators=TechnicalIndicators(
                ma5=1820.00,
                ma10=1800.00,
                ma20=1750.00,
                vol_ma5=100000,
                vol_ma10=120000
            ),
            fundamental_data=FundamentalData(
                pe=30.0,
                pb=10.5,
                market_cap=2300000
            )
        )
    ]
    
    # 写入数据
    date = "20260317"
    msg_id = writer.write_selection(
        date=date,
        batch_id="SELECT_20260317_001",
        strategy_id="MA10_BREAKTHROUGH",
        stocks=stocks,
        total_count=50
    )
    
    print(f"Selection data written successfully!")
    print(f"  Stream: selection:stream:{date}")
    print(f"  Message ID: {msg_id}")
    
    # 检查Stream是否存在
    print(f"  Stream exists: {writer.stream_exists(date)}")
    print(f"  Stream length: {writer.get_stream_length(date)}")


if __name__ == "__main__":
    main()
