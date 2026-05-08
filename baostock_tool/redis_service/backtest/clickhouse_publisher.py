"""ClickHouse 数据发布器。"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import redis

from baostock_tool.redis_service.core.base_service import BaseRedisService
from baostock_tool.redis_service.database.clickhouse_queries import ClickHouseQueryService
from baostock_tool.redis_service.models.clickhouse_models import (
    EXCHANGE_ID_TO_EXCHANGE,
    MARKET_TO_EXCHANGE_ID,
    SnapshotMessage,
    TickMessage,
    build_empty_snapshot_row,
    build_empty_tick_row,
    build_snapshot_payload,
    build_tick_payload,
    datetime_to_timestamp_ms,
)

logger = logging.getLogger(__name__)


class ClickHousePublisher(BaseRedisService):
    """ClickHouse 数据批量发布器。"""

    BATCH_SIZE = 5000

    def __init__(
        self,
        query_service: ClickHouseQueryService,
        redis_client: Optional[redis.Redis] = None,
        use_pipeline: bool = True,
    ):
        super().__init__(redis_client)
        self.query_service = query_service
        self.use_pipeline = use_pipeline

    def publish_snapshot_batch(self, date: str, stocks: List[Tuple[str, str, int, str]]) -> Dict[str, int]:
        stock_params = [(market, code) for market, _exchange, code, _symbol in stocks]
        rows_by_symbol = self.query_service.get_snapshot_data(date, stock_params)
        all_messages: List[SnapshotMessage] = []

        for market, exchange, _code, symbol in stocks:
            rows = rows_by_symbol.get(symbol)
            if not rows:
                rows = [build_empty_snapshot_row(symbol, MARKET_TO_EXCHANGE_ID[market])]

            total = len(rows)
            for index, row in enumerate(rows, start=1):
                all_messages.append(
                    SnapshotMessage(
                        timestamp=datetime_to_timestamp_ms(row.get("trade_datetime")),
                        seqno=0 if index == total else index,
                        exchange=exchange,
                        symbol=symbol,
                        data=build_snapshot_payload(row),
                    )
                )

        all_messages.sort(key=lambda item: (item.timestamp, item.symbol, item.seqno))
        return self._publish_messages(all_messages)

    def publish_tick_batch(
        self,
        date: str,
        stocks: List[Tuple[str, str, int, str]],
        sub_type: int = 2,
    ) -> Dict[str, int]:
        stock_params = [(market, code) for market, _exchange, code, _symbol in stocks]
        rows_by_symbol = self.query_service.get_tick_data(date, stock_params, sub_type=sub_type)
        all_messages: List[TickMessage] = []

        for market, fallback_exchange, _code, symbol in stocks:
            rows = rows_by_symbol.get(symbol)
            if not rows:
                rows = [build_empty_tick_row(symbol, MARKET_TO_EXCHANGE_ID[market])]

            total = len(rows)
            for index, row in enumerate(rows, start=1):
                exchange = EXCHANGE_ID_TO_EXCHANGE.get(row.get("exchange_id"), fallback_exchange)
                all_messages.append(
                    TickMessage(
                        sub_type=sub_type,
                        timestamp=datetime_to_timestamp_ms(row.get("trade_datetime")),
                        seqno=0 if index == total else index,
                        exchange=exchange,
                        symbol=symbol,
                        data=build_tick_payload(row),
                    )
                )

        all_messages.sort(key=lambda item: (item.timestamp, item.symbol, item.seqno))
        return self._publish_messages(all_messages)

    def _publish_messages(self, messages: List[Any]) -> Dict[str, int]:
        results: Dict[str, int] = {}
        if not messages:
            return results

        if self.use_pipeline:
            for start in range(0, len(messages), self.BATCH_SIZE):
                batch = messages[start:start + self.BATCH_SIZE]
                pipe = self._client.pipeline()
                for message in batch:
                    pipe.publish(message.get_channel(), message.model_dump_json())
                    results[message.symbol] = results.get(message.symbol, 0) + 1
                pipe.execute()
                time.sleep(0.01)
        else:
            for message in messages:
                self._client.publish(message.get_channel(), message.model_dump_json())
                results[message.symbol] = results.get(message.symbol, 0) + 1

        logger.info("Redis 推送完成: 股票数=%s, 消息数=%s", len(results), len(messages))
        return results