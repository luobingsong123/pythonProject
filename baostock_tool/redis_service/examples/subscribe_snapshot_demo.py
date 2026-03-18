"""
行情快照订阅示例
"""

import time
from market.subscriber import SnapshotSubscriber


def simple_subscribe():
    """简单订阅示例"""
    print("Subscribing to market:snapshot:SSE:*")
    
    subscriber = SnapshotSubscriber()
    
    try:
        # 订阅上交所所有股票行情
        for snapshot in subscriber.subscribe("market:snapshot:SSE:*"):
            print(f"\nReceived snapshot:")
            print(f"  Exchange: {snapshot.exchange}")
            print(f"  Symbol: {snapshot.symbol}")
            print(f"  Last Price: {snapshot.data.last_price}")
            print(f"  Volume: {snapshot.data.volume}")
            print(f"  Time: {snapshot.data.timestamp}")
    except KeyboardInterrupt:
        print("\nSubscribed stopped")
    finally:
        subscriber.close()


def subscribe_with_callback():
    """使用回调函数订阅"""
    print("Subscribing with callback...")
    
    def handle_snapshot(snapshot):
        print(f"\n[Callback] {snapshot.exchange}:{snapshot.symbol} - "
              f"Price: {snapshot.data.last_price}")
    
    subscriber = SnapshotSubscriber()
    subscriber.subscribe_callback("market:snapshot:SSE:*", handle_snapshot)
    
    print("Press Enter to stop...")
    input()
    subscriber.close()


def subscribe_to_symbol():
    """订阅指定股票"""
    print("Subscribing to SSE:600036...")
    
    subscriber = SnapshotSubscriber()
    
    try:
        for snapshot in subscriber.subscribe_to_symbol("SSE", "600036"):
            print(f"Price update: {snapshot.data.last_price}")
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        subscriber.close()


if __name__ == "__main__":
    # 选择一种订阅方式
    # simple_subscribe()
    # subscribe_with_callback()
    subscribe_to_symbol()
