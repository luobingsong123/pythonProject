"""ClickHouse 行情消息模型。"""

import json
from datetime import date, datetime
from typing import Any, Dict, List, Union

from pydantic import BaseModel, Field


SNAPSHOT_BASE_COLUMNS = [
    "trade_date",
    "data_time",
    "trade_datetime",
    "security_id",
    "exchange_id",
    "last_price",
    "pre_close_price",
    "open_price",
    "high_price",
    "low_price",
    "qty",
    "turnover",
    "avg_price",
    "trades_count",
    "ticker_status",
    "total_bid_qty",
    "total_ask_qty",
]

SNAPSHOT_PUSH_COLUMNS = SNAPSHOT_BASE_COLUMNS + [
    f"{side}{level}_{field}"
    for level in range(10)
    for side, field in (("bid", "price"), ("bid", "qty"), ("ask", "price"), ("ask", "qty"))
]

TICK_PUSH_COLUMNS = [
    "trade_date",
    "update_time",
    "trade_datetime",
    "exchange_id",
    "channel_no",
    "seq_no",
    "security_id",
    "trade2_order1",
    "price",
    "volume",
    "trd_money",
    "ord_side",
    "ord_type",
    "trd_bs_flag",
    "trd_buy_no",
    "trd_sell_no",
    "ord_no",
    "biz_index",
    "trans_flag",
    "order_trd_volume",
]

MARKET_TO_EXCHANGE_ID = {
    "sh": 1,
    "sz": 2,
}

EXCHANGE_ID_TO_EXCHANGE = {
    1: "SSE",
    2: "SZSE",
}


class SnapshotMessage(BaseModel):
    """快照推送消息。"""

    type: str = Field(default="snapshot")
    timestamp: int
    seqno: int
    exchange: str
    symbol: str
    data: Dict[str, Any]

    def get_channel(self) -> str:
        return f"market:snapshot:{self.exchange}:{self.symbol}"


class TickMessage(BaseModel):
    """逐笔推送消息。"""

    type: str = Field(default="tick")
    sub_type: int
    timestamp: int
    seqno: int
    exchange: str
    symbol: str
    data: Dict[str, Any]

    def get_channel(self) -> str:
        return f"market:tick:{self.exchange}:{self.symbol}"


class ClickHouseMessageParser:
    """ClickHouse 消息解析器。"""

    @staticmethod
    def parse_message(message: Union[str, bytes]) -> Union[SnapshotMessage, TickMessage]:
        if isinstance(message, bytes):
            message = message.decode("utf-8")

        payload = json.loads(message)
        message_type = payload.get("type")
        if message_type == "snapshot":
            return SnapshotMessage(**payload)
        if message_type == "tick":
            return TickMessage(**payload)
        raise ValueError(f"Unsupported message type: {message_type}")

    @staticmethod
    def parse_channel(channel: Union[str, bytes]) -> Dict[str, str]:
        if isinstance(channel, bytes):
            channel = channel.decode("utf-8")

        parts = channel.split(":")
        if len(parts) >= 4 and parts[0] == "market":
            return {
                "category": parts[1],
                "exchange": parts[2],
                "symbol": parts[3],
            }
        raise ValueError(f"Invalid channel format: {channel}")


def normalize_scalar(value: Any) -> Any:
    """将日期时间类型转换为可序列化值。"""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    if isinstance(value, date):
        return value.isoformat()
    return value


def datetime_to_timestamp_ms(value: Any) -> int:
    """将 datetime 转为毫秒时间戳。"""
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    return -1


def build_order_book_lists(row: Dict[str, Any]) -> Dict[str, List[Any]]:
    """将十档盘口字段收敛为数组。"""
    return {
        "bid_price": [normalize_scalar(row.get(f"bid{i}_price", -1)) for i in range(10)],
        "bid_volume": [normalize_scalar(row.get(f"bid{i}_qty", -1)) for i in range(10)],
        "ask_price": [normalize_scalar(row.get(f"ask{i}_price", -1)) for i in range(10)],
        "ask_volume": [normalize_scalar(row.get(f"ask{i}_qty", -1)) for i in range(10)],
    }


def build_snapshot_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    """构建快照 data 负载。"""
    payload = {
        column: normalize_scalar(row.get(column, -1))
        for column in SNAPSHOT_BASE_COLUMNS
        if column != "security_id"
    }
    payload.update(build_order_book_lists(row))
    return payload


def build_tick_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    """构建逐笔 data 负载。"""
    return {
        column: normalize_scalar(row.get(column, "" if column in {"ord_side", "ord_type", "trd_bs_flag"} else -1))
        for column in TICK_PUSH_COLUMNS
        if column != "security_id"
    }


def build_empty_snapshot_row(symbol: str, exchange_id: int) -> Dict[str, Any]:
    """构建空快照原始行。"""
    row: Dict[str, Any] = {
        column: -1 for column in SNAPSHOT_PUSH_COLUMNS if column not in {"security_id", "trade_date", "trade_datetime", "ticker_status"}
    }
    row["trade_date"] = ""
    row["trade_datetime"] = ""
    row["ticker_status"] = ""
    row["security_id"] = symbol
    row["exchange_id"] = exchange_id
    return row


def build_empty_tick_row(symbol: str, exchange_id: int) -> Dict[str, Any]:
    """构建空逐笔原始行。"""
    row: Dict[str, Any] = {
        column: -1 for column in TICK_PUSH_COLUMNS if column not in {"security_id", "trade_date", "trade_datetime", "ord_side", "ord_type", "trd_bs_flag"}
    }
    row["trade_date"] = ""
    row["trade_datetime"] = ""
    row["ord_side"] = ""
    row["ord_type"] = ""
    row["trd_bs_flag"] = ""
    row["security_id"] = symbol
    row["exchange_id"] = exchange_id
    return row