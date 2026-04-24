"""ClickHouse 查询服务。"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from clickhouse_driver import Client

from models.clickhouse_models import (
    EXCHANGE_ID_TO_EXCHANGE,
    MARKET_TO_EXCHANGE_ID,
    SNAPSHOT_PUSH_COLUMNS,
    TICK_PUSH_COLUMNS,
)

logger = logging.getLogger(__name__)


class ClickHouseQueryService:
    """ClickHouse 数据查询服务。"""

    def __init__(self, client: Client):
        self.client = client

    def check_table_exists(self, date: str, table_type: str) -> bool:
        table_name = f"{table_type}_{date}"
        try:
            result = self.client.execute(f"EXISTS TABLE {table_name}")
            return bool(result and result[0][0])
        except Exception as exc:
            logger.warning("检查表存在性失败: %s, 错误: %s", table_name, exc)
            return False

    def get_snapshot_data(self, date: str, stocks: List[Tuple[str, int]]) -> Dict[str, List[Dict[str, Any]]]:
        return self._get_rows_by_symbol(date=date, stocks=stocks, table_type="snapshot", columns=SNAPSHOT_PUSH_COLUMNS)

    def get_tick_data(
        self,
        date: str,
        stocks: List[Tuple[str, int]],
        sub_type: int = 2,
    ) -> Dict[str, List[Dict[str, Any]]]:
        extra_where = ""
        params: Dict[str, Any] = {}
        if sub_type == 3:
            extra_where = " AND trade2_order1 = %(trade_flag)s"
            params["trade_flag"] = 2
        elif sub_type == 4:
            extra_where = " AND trade2_order1 = %(trade_flag)s"
            params["trade_flag"] = 1

        return self._get_rows_by_symbol(
            date=date,
            stocks=stocks,
            table_type="tick",
            columns=TICK_PUSH_COLUMNS,
            extra_where=extra_where,
            extra_params=params,
        )

    def _get_rows_by_symbol(
        self,
        date: str,
        stocks: List[Tuple[str, int]],
        table_type: str,
        columns: List[str],
        extra_where: str = "",
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not stocks:
            return {}

        table_name = f"{table_type}_{date}"
        if not self.check_table_exists(date, table_type):
            logger.warning("表不存在: %s", table_name)
            return {}

        grouped_codes: Dict[int, List[str]] = {}
        for market, code in stocks:
            exchange_id = MARKET_TO_EXCHANGE_ID.get(market)
            if exchange_id is None:
                continue
            grouped_codes.setdefault(exchange_id, []).append(f"{code:06d}")

        if not grouped_codes:
            return {}

        conditions: List[str] = []
        params: Dict[str, Any] = dict(extra_params or {})
        for index, (exchange_id, codes) in enumerate(grouped_codes.items()):
            exchange_key = f"exchange_id_{index}"
            codes_key = f"codes_{index}"
            conditions.append(f"(exchange_id = %({exchange_key})s AND security_id IN %({codes_key})s)")
            params[exchange_key] = exchange_id
            params[codes_key] = tuple(codes)

        sql = (
            f"SELECT {', '.join(columns)} FROM {table_name} "
            f"WHERE ({' OR '.join(conditions)}){extra_where} ORDER BY trade_datetime"
        )

        try:
            rows, column_types = self.client.execute(sql, params, with_column_types=True)
            column_names = [item[0] for item in column_types]
            results: Dict[str, List[Dict[str, Any]]] = {}
            for row in rows:
                item = dict(zip(column_names, row))
                symbol = item.get("security_id", "")
                exchange_id = item.get("exchange_id")
                if symbol and exchange_id in EXCHANGE_ID_TO_EXCHANGE:
                    results.setdefault(symbol, []).append(item)
            logger.info("ClickHouse 查询完成: %s, 股票数=%s, 记录数=%s", table_name, len(stocks), len(rows))
            return results
        except Exception as exc:
            logger.warning("ClickHouse 查询失败: %s, 错误: %s", table_name, exc)
            return {}