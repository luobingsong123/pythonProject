"""
数据转换器

将从 MySQL 读出的 DataFrame/dict 转换为规范的 Redis 消息结构：

  1. snapshot_message()     -> 4.1 行情快照消息（用于 Pub/Sub）
  2. selection_message()    -> 4.2 选股股池消息（用于 Stream）
  3. batch_snapshot_items() -> 批量快照（供 RedisPublisher.publish_snapshot_batch 使用）
"""

import time
import uuid
from datetime import datetime, date
from typing import Optional

import pandas as pd

from utils.logger_utils import setup_logger
import config

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"],
)

# 市场代码映射
_MARKET_TO_EXCHANGE = {
    "sh": "SSE",
    "sz": "SZSE",
    "bj": "BSE",
}


def _now_ms() -> int:
    """当前毫秒时间戳"""
    return int(time.time() * 1000)


def _safe_float(val, default=None):
    """安全转换为 float，NaN/None 返回 default"""
    if val is None:
        return default
    try:
        f = float(val)
        return default if (f != f) else round(f, 6)   # NaN check
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=None):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


class Transformer:
    """原始数据 -> 标准 Redis 消息结构"""

    # ------------------------------------------------------------------
    # 4.1 行情快照
    # ------------------------------------------------------------------

    @staticmethod
    def snapshot_message(
        row: pd.Series,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> dict:
        """
        将 DataFrame 一行（日线数据）转换为行情快照消息

        消息结构（严格按协议 4.1）:
        {
            "type": "snapshot",
            "timestamp": 1703234567890,
            "exchange": "SSE",
            "symbol": "600036",
            "data": {
                "last_price": 32.56,
                "volume": 12345678,
                "amount": 3987654321,
                "bid_price": [],        // 日线数据无买卖五档，留空
                "bid_volume": [],
                "ask_price": [],
                "ask_volume": [],
                "date": "20260317",
                "timestamp": "14:45:15"
            }
        }

        Args:
            row:      DataFrame 的一行，需包含 market/code_int/date/close/volume/amount
            exchange: 可手动指定；不传则从 row.market 自动推导
            symbol:   可手动指定；不传则取 str(row.code_int)
        """
        market = str(row.get("market", "")).lower()
        exch = exchange or _MARKET_TO_EXCHANGE.get(market, market.upper())
        sym = symbol or str(_safe_int(row.get("code_int"), ""))

        # 日期处理：兼容 date / datetime / str
        raw_date = row.get("date")
        if isinstance(raw_date, (datetime, date, pd.Timestamp)):
            date_str = pd.Timestamp(raw_date).strftime("%Y%m%d")
        else:
            date_str = str(raw_date).replace("-", "")[:8] if raw_date else ""

        msg = {
            "type": "snapshot",
            "timestamp": _now_ms(),
            "exchange": exch,
            "symbol": sym,
            "data": {
                "last_price": _safe_float(row.get("close")),
                "volume": _safe_int(row.get("volume")),
                "amount": _safe_float(row.get("amount")),
                # 日线无买卖盘，协议要求字段存在但可为空列表
                "bid_price": [],
                "bid_volume": [],
                "ask_price": [],
                "ask_volume": [],
                "date": date_str,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            },
        }
        return msg

    @classmethod
    def batch_snapshot_items(cls, df: pd.DataFrame) -> list[dict]:
        """
        将快照 DataFrame 转为 publisher.publish_snapshot_batch() 所需格式

        Returns:
            list of {"exchange": str, "symbol": str, "message": dict}
        """
        items = []
        for _, row in df.iterrows():
            market = str(row.get("market", "")).lower()
            exchange = _MARKET_TO_EXCHANGE.get(market, market.upper())
            symbol = str(_safe_int(row.get("code_int"), ""))
            message = cls.snapshot_message(row, exchange, symbol)
            items.append({"exchange": exchange, "symbol": symbol, "message": message})
        return items

    # ------------------------------------------------------------------
    # 4.2 选股股池消息
    # ------------------------------------------------------------------

    @classmethod
    def selection_message(
        cls,
        df: pd.DataFrame,
        trade_date: str,
        strategy_id: str = "MA10_BREAKTHROUGH",
        batch_id: Optional[str] = None,
        db_reader=None,         # 可选：传入 DbReader 实例以获取分钟线数据
    ) -> dict:
        """
        将选股 DataFrame 转换为完整的股池消息（协议 4.2）

        Args:
            df:           read_stock_selection() 返回的 DataFrame
            trade_date:   交易日期，格式 YYYY-MM-DD，如 "2026-03-17"
            strategy_id:  策略标识
            batch_id:     批次 ID，不传则自动生成
            db_reader:    DbReader 实例（用于拉分钟线数据，可 None）

        Returns:
            完整股池消息 dict
        """
        date_compact = trade_date.replace("-", "")  # "20260317"
        auto_batch_id = batch_id or f"SELECT_{date_compact}_{uuid.uuid4().hex[:6].upper()}"

        stocks = []
        for _, row in df.iterrows():
            market = str(row.get("market", "")).lower()
            exchange = _MARKET_TO_EXCHANGE.get(market, market.upper())
            symbol = str(_safe_int(row.get("code_int"), ""))

            # 分钟成交量（若有 db_reader 则尝试拉取）
            minute_volume_5d = []
            if db_reader is not None:
                try:
                    minute_volume_5d = db_reader.read_minute_volume_5d(
                        market=market,
                        code_int=_safe_int(row.get("code_int")),
                        end_date=trade_date,
                        days=5,
                    )
                except Exception as e:
                    logger.debug(f"读取分钟量失败 {symbol}: {e}")

            # 量比 = 当日成交量 / vol_ma5（简化计算）
            vol = _safe_float(row.get("volume"))
            vol_ma5 = _safe_float(row.get("vol_ma5"))
            volume_ratio = round(vol / vol_ma5, 4) if (vol and vol_ma5 and vol_ma5 > 0) else None

            # 换手率（当前表无流通股数，暂留 None；实盘可补充）
            turnover_rate = None

            stock_item = {
                "symbol": symbol,
                "exchange": exchange,
                "name": str(row.get("name", "")),

                "basic_info": {
                    "prev_close": _safe_float(row.get("prev_close")),
                    "ma10": _safe_float(row.get("ma10")),
                    "ma5_high": _safe_float(row.get("ma5_high")),
                    "volume_ratio": volume_ratio,
                    "turnover_rate": turnover_rate,
                },

                "minute_volume_5d": minute_volume_5d,

                "technical_indicators": {
                    "ma5": _safe_float(row.get("ma5")),
                    "ma10": _safe_float(row.get("ma10")),
                    "ma20": _safe_float(row.get("ma20")),
                    "vol_ma5": _safe_float(row.get("vol_ma5")),
                    "vol_ma10": _safe_float(row.get("vol_ma10")),
                },

                "fundamental_data": {
                    "pe": _safe_float(row.get("pe")),
                    "pb": _safe_float(row.get("pb")),
                    "market_cap": None,   # 当前表无市值字段，预留
                },
            }
            stocks.append(stock_item)

        message = {
            "type": "stock_selection",
            "version": "1.0",
            "timestamp": _now_ms(),
            "batch_id": auto_batch_id,
            "strategy_id": strategy_id,
            "total_count": len(stocks),
            "stocks": stocks,
        }

        logger.info(
            f"[Transformer] 构建股池消息: date={date_compact}, "
            f"strategy={strategy_id}, count={len(stocks)}"
        )
        return message
