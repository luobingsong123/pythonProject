"""
行情快照发布示例
"""

import time
from market.publisher import SnapshotPublisher
from models.snapshot import SnapshotData, MarketQuote


def main():
    """发布行情快照示例"""
    
    # 创建发布器
    publisher = SnapshotPublisher()
    
    # 创建行情数据
    snapshot = SnapshotData(
        type="snapshot",
        timestamp=int(time.time() * 1000),
        exchange="SSE",
        symbol="600036",
        data=MarketQuote(
            last_price=32.56,
            volume=12345678,
            amount=3987654321,
            bid_price=[32.55, 32.54, 32.53, 32.52, 32.51],
            bid_volume=[100, 200, 300, 400, 500],
            ask_price=[32.57, 32.58, 32.59, 32.60, 32.61],
            ask_volume=[150, 250, 350, 450, 550],
            date="20260317",
            timestamp="14:45:15"
        )
    )
    
    # 发布
    print(f"Publishing to channel: {snapshot.get_channel()}")
    count = publisher.publish(snapshot)
    print(f"Message published, {count} subscribers received")
    
    # 使用便捷方法发布
    count = publisher.build_and_publish(
        exchange="SSE",
        symbol="600036",
        last_price=32.60,
        volume=13000000,
        amount=4000000000,
        bid_price=[32.59, 32.58, 32.57, 32.56, 32.55],
        bid_volume=[200, 300, 400, 500, 600],
        ask_price=[32.61, 32.62, 32.63, 32.64, 32.65],
        ask_volume=[250, 350, 450, 550, 650],
        date="20260317",
        timestamp="14:46:00"
    )
    print(f"Second message published, {count} subscribers received")


if __name__ == "__main__":
    main()
