"""
Redis 推送器

负责两类数据的写入：
  1. 行情快照（market snapshot）: 使用 Pub/Sub 广播
     通道格式: market:snapshot:{exchange}:{symbol}
     如:      market:snapshot:SSE:600036

  2. 选股股池（stock selection）: 使用 Redis Stream 存储
     Key 格式:  selection:stream:{date}
     如:        selection:stream:20260317
"""

import json
import time
import redis
from redis import ConnectionPool
from typing import Any

import config
from utils.logger_utils import setup_logger

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"],
)


class RedisPublisher:
    """Redis 推送器：行情 Pub/Sub + 股池 Stream"""

    def __init__(self):
        redis_cfg = config.get_redis_config()
        pool = ConnectionPool(
            host=redis_cfg["host"],
            port=redis_cfg["port"],
            password=redis_cfg["password"],
            db=redis_cfg["db"],
            max_connections=redis_cfg["max_connections"],
            decode_responses=True,      # 返回 str 而非 bytes
        )
        self._client = redis.Redis(connection_pool=pool)
        self._max_stream_len = 10000    # Stream 最大保留条数
        logger.info(
            f"RedisPublisher 初始化完成: "
            f"{redis_cfg['host']}:{redis_cfg['port']} db={redis_cfg['db']}"
        )

    # ------------------------------------------------------------------
    # 公共工具
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """测试 Redis 连接"""
        try:
            return self._client.ping()
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            return False

    # ------------------------------------------------------------------
    # 4.1 行情快照 —— Pub/Sub
    # ------------------------------------------------------------------

    def publish_snapshot(self, exchange: str, symbol: str, message: dict) -> int:
        """
        发布行情快照到 Pub/Sub 通道

        通道命名: market:snapshot:{exchange}:{symbol}
        如:       market:snapshot:SSE:600036

        Args:
            exchange: 交易所代码，如 "SSE" / "SZSE"
            symbol:   股票代码，如 "600036"
            message:  完整消息字典（由 Transformer 生成）

        Returns:
            int: 收到该消息的订阅者数量（0 表示无人订阅，消息仍会发出）
        """
        channel = f"market:snapshot:{exchange}:{symbol}"
        payload = json.dumps(message, ensure_ascii=False)
        try:
            receivers = self._client.publish(channel, payload)
            logger.debug(
                f"[Pub/Sub] 推送 {channel} -> {receivers} 个订阅者"
            )
            return receivers
        except Exception as e:
            logger.error(f"[Pub/Sub] 推送失败 {channel}: {e}")
            raise

    def publish_snapshot_batch(self, snapshots: list[dict]) -> dict:
        """
        批量推送行情快照（使用 pipeline 减少网络往返）

        Args:
            snapshots: 快照消息列表，每个元素需包含 exchange / symbol / message 三个 key
                       例如: [{"exchange": "SSE", "symbol": "600036", "message": {...}}, ...]

        Returns:
            dict: {"success": int, "failed": int}
        """
        success, failed = 0, 0
        pipe = self._client.pipeline(transaction=False)
        channels = []

        for item in snapshots:
            exchange = item["exchange"]
            symbol = item["symbol"]
            message = item["message"]
            channel = f"market:snapshot:{exchange}:{symbol}"
            payload = json.dumps(message, ensure_ascii=False)
            pipe.publish(channel, payload)
            channels.append(channel)

        try:
            results = pipe.execute()
            for ch, res in zip(channels, results):
                if isinstance(res, Exception):
                    logger.error(f"[Pub/Sub] 批量推送失败 {ch}: {res}")
                    failed += 1
                else:
                    success += 1
        except Exception as e:
            logger.error(f"[Pub/Sub] pipeline 执行失败: {e}")
            failed = len(snapshots)

        logger.info(f"[Pub/Sub] 批量推送完成: 成功={success}, 失败={failed}")
        return {"success": success, "failed": failed}

    # ------------------------------------------------------------------
    # 4.2 选股股池 —— Redis Stream
    # ------------------------------------------------------------------

    def push_stock_selection(self, date: str, message: dict) -> str:
        """
        将选股结果写入 Redis Stream

        Key 格式: selection:stream:{date}
        如:       selection:stream:20260317

        Args:
            date:    交易日期，格式 YYYYMMDD，如 "20260317"
            message: 完整选股消息字典（由 Transformer 生成）

        Returns:
            str: Stream entry ID，如 "1703234567890-0"
        """
        stream_key = f"selection:stream:{date}"
        # Stream field 的 value 必须是 str，将整个消息序列化为一个 field
        stream_entry = {"data": json.dumps(message, ensure_ascii=False)}
        try:
            entry_id = self._client.xadd(
                stream_key,
                stream_entry,
                maxlen=self._max_stream_len,
                approximate=True,   # ~ maxlen，性能更好
            )
            logger.info(
                f"[Stream] 写入 {stream_key} entry_id={entry_id}, "
                f"股票数={message.get('total_count', '?')}"
            )
            return entry_id
        except Exception as e:
            logger.error(f"[Stream] 写入失败 {stream_key}: {e}")
            raise

    def get_stream_length(self, date: str) -> int:
        """查询指定日期 Stream 的条目数"""
        stream_key = f"selection:stream:{date}"
        try:
            return self._client.xlen(stream_key)
        except Exception as e:
            logger.error(f"[Stream] 查询长度失败 {stream_key}: {e}")
            return -1

    # ------------------------------------------------------------------
    # 状态管理 key（记录最后同步时间，用于增量推送）
    # ------------------------------------------------------------------

    def set_last_sync_time(self, service_name: str, ts: float = None) -> None:
        """
        记录服务最后一次同步时间戳（毫秒）

        Args:
            service_name: 服务标识，如 "snapshot" / "selection"
            ts:           毫秒时间戳，默认取当前时间
        """
        ts = ts or (time.time() * 1000)
        key = f"service:last_sync:{service_name}"
        self._client.set(key, str(int(ts)))

    def get_last_sync_time(self, service_name: str) -> int:
        """
        获取服务最后一次同步时间戳（毫秒），不存在则返回 0
        """
        key = f"service:last_sync:{service_name}"
        val = self._client.get(key)
        return int(val) if val else 0

    def close(self) -> None:
        """关闭连接池"""
        try:
            self._client.close()
            logger.info("RedisPublisher 已关闭")
        except Exception:
            pass
