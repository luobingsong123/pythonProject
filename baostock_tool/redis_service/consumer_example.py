"""
策略模块消费示例

演示如何从 Redis 订阅行情快照 / 消费选股 Stream。
此文件仅作参考，不是服务本体。
"""

import json
import redis

# ======================================================================
# 示例 1：订阅行情快照（Pub/Sub）
# ======================================================================

def subscribe_snapshots():
    """
    策略模块订阅行情快照

    支持模式匹配：
      - 订阅单只: "market:snapshot:SSE:600036"
      - 订阅全市场: "market:snapshot:*"
      - 订阅上交所: "market:snapshot:SSE:*"
    """
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    pubsub = r.pubsub()

    # 用 psubscribe 支持通配符（* 匹配任意字符）
    pubsub.psubscribe("market:snapshot:SSE:*")
    print("已订阅 market:snapshot:SSE:*，等待行情...")

    for msg in pubsub.listen():
        if msg["type"] != "pmessage":
            continue

        channel = msg["channel"]          # e.g. "market:snapshot:SSE:600036"
        payload = json.loads(msg["data"])

        exchange = payload["exchange"]    # "SSE"
        symbol   = payload["symbol"]      # "600036"
        data     = payload["data"]

        last_price = data["last_price"]
        volume     = data["volume"]
        date_str   = data["date"]
        time_str   = data["timestamp"]

        print(
            f"[{date_str} {time_str}] {exchange}:{symbol} "
            f"最新价={last_price}  量={volume:,}"
        )


# ======================================================================
# 示例 2：消费选股股池（Redis Stream）
# ======================================================================

def consume_stock_selection(date: str = "20260317"):
    """
    策略模块从 Stream 消费选股结果

    Args:
        date: 交易日期，格式 YYYYMMDD
    """
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    stream_key = f"selection:stream:{date}"

    print(f"读取 Stream: {stream_key}")

    # 从头读取，count=100 表示每次最多取 100 条
    messages = r.xread({stream_key: "0-0"}, count=100)

    if not messages:
        print("Stream 中暂无数据")
        return

    for stream_name, entries in messages:
        for entry_id, fields in entries:
            payload = json.loads(fields["data"])

            batch_id     = payload["batch_id"]
            strategy_id  = payload["strategy_id"]
            total_count  = payload["total_count"]
            stocks       = payload["stocks"]

            print(f"\n批次: {batch_id}  策略: {strategy_id}  共 {total_count} 只")
            for stock in stocks[:5]:   # 只打印前 5 只
                sym   = stock["symbol"]
                exch  = stock["exchange"]
                name  = stock["name"]
                ma10  = stock["basic_info"]["ma10"]
                pe    = stock["fundamental_data"]["pe"]
                print(f"  {exch}:{sym} {name}  MA10={ma10}  PE={pe}")
            if total_count > 5:
                print(f"  ... 还有 {total_count - 5} 只")


# ======================================================================
# 示例 3：增量消费 Stream（从上次消费位置继续）
# ======================================================================

def consume_incremental(date: str = "20260317", last_id: str = "0-0"):
    """
    增量消费：记录上次消费到的 entry_id，下次从该位置继续

    Args:
        date:    交易日期，格式 YYYYMMDD
        last_id: 上次最后消费的 entry_id，"0-0" 表示从头开始
    """
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    stream_key = f"selection:stream:{date}"

    while True:
        messages = r.xread({stream_key: last_id}, count=10, block=5000)  # block 5s
        if not messages:
            print("等待新消息...")
            continue

        for stream_name, entries in messages:
            for entry_id, fields in entries:
                payload = json.loads(fields["data"])
                print(f"[{entry_id}] 收到选股批次: {payload['batch_id']}, "
                      f"共 {payload['total_count']} 只")
                last_id = entry_id   # 更新消费位置


if __name__ == "__main__":
    # 取消注释以运行对应示例
    # subscribe_snapshots()
    consume_stock_selection("20260317")
    # consume_incremental("20260317")
