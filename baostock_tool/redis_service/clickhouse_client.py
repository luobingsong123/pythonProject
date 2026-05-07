"""ClickHouse 数据客户端。"""

import argparse
import csv
import json
import os
import socket
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import redis

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from baostock_tool.redis_service.config.config_loader import update_global_settings
from baostock_tool.redis_service.config.settings import settings
from baostock_tool.redis_service.core.connection import get_redis_client
from baostock_tool.redis_service.models.clickhouse_models import ClickHouseMessageParser, SnapshotMessage, TickMessage
from baostock_tool.redis_service.selection.reader import SelectionReader
from baostock_tool.redis_service.utils.log_manager import get_logger, setup_logging


class ClickHouseClient:
    """ClickHouse 数据客户端。"""

    def __init__(self, host: str = "localhost", port: int = 9998):
        self.host = host
        self.port = port
        self.logger = get_logger("clickhouse_client")
        self.selection_reader = SelectionReader()
        self.redis_client = get_redis_client()
        self.receiving = False
        self.subscribed = False
        self.received_count = 0
        self.receive_thread: Optional[threading.Thread] = None
        self.data_file = None
        self.data_writer = None
        self.pubsub = None

    @staticmethod
    def _ensure_parent_dir(file_path: str):
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

    def read_selection_stocks(self, date: str) -> List[Dict[str, Any]]:
        self.logger.info(f"读取选股数据: {date}")
        messages = self.selection_reader.read_latest(date, count=1)
        if not messages:
            self.logger.warning(f"未找到选股数据: {date}")
            return []

        selections = self.selection_reader.parse_messages(messages)
        if not selections:
            self.logger.warning(f"解析选股数据失败: {date}")
            return []

        selection = selections[0]
        stocks = [{"symbol": stock.symbol, "exchange": stock.exchange} for stock in selection.stocks]
        self.logger.info(f"读取到 {len(stocks)} 只选股: {selection.batch_id}, 策略: {selection.strategy_id}")
        return stocks

    def subscribe(
        self,
        sub_type: int,
        start_date: str,
        end_date: str,
        stocks: List[Dict[str, Any]],
        data_file_path: str,
    ) -> Dict[str, Any]:
        stock_codes = [stock["symbol"] for stock in stocks]
        request = {
            "sub_type": sub_type,
            "start_date": start_date,
            "end_date": end_date,
            "stock": stock_codes,
        }
        request_json = json.dumps(request, ensure_ascii=False)
        self.logger.info(f"发送订阅请求: {request_json}")

        try:
            self._start_receiving(sub_type, data_file_path, stocks)
            time.sleep(0.5)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            self.logger.info(f"已连接到服务器: {self.host}:{self.port}")
            sock.sendall(request_json.encode("utf-8"))

            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
            sock.close()

            response = json.loads(response_data.decode("utf-8"))
            self.logger.info(f"收到服务器响应: {response}")

            if response.get("success"):
                expected_count = 0
                for date_stat in response.get("stats", []):
                    for item in date_stat.get("items", []):
                        expected_count += item.get("count", 0)

                self._wait_for_completion(expected_count)
            else:
                time.sleep(3)

            self._stop_receiving()
            return response
        except Exception as exc:
            self.logger.error(f"订阅失败: {exc}")
            self._stop_receiving()
            return {"success": False, "error": f"连接服务器失败: {exc}"}

    def _wait_for_completion(self, expected_count: int):
        self.logger.info(f"预期接收数据: {expected_count} 条")
        timeout = 300
        start_wait = time.time()
        last_count = 0
        no_change_time = 0

        while time.time() - start_wait < timeout:
            current_count = self.received_count
            if expected_count > 0 and current_count >= expected_count:
                self.logger.info(f"数据接收完成: {current_count}/{expected_count} 条")
                break

            if current_count == last_count:
                no_change_time += 1
                if no_change_time >= 30:
                    self.logger.info(f"数据接收静默结束: {current_count} 条")
                    break
            else:
                no_change_time = 0

            last_count = current_count
            time.sleep(1)

        if time.time() - start_wait >= timeout:
            self.logger.warning(f"等待数据超时，已接收: {self.received_count}/{expected_count} 条")

    def _start_receiving(self, sub_type: int, data_file_path: str, stocks: List[Dict[str, Any]]):
        self.receiving = True
        self.subscribed = False
        self.received_count = 0

        self._ensure_parent_dir(data_file_path)
        self.data_file = open(data_file_path, "w", encoding="utf-8", newline="")
        self.data_writer = csv.writer(self.data_file, delimiter="|")
        self._write_header(sub_type)

        stock_set = {f"{stock['exchange']}:{stock['symbol']}" for stock in stocks}
        self.receive_thread = threading.Thread(
            target=self._receive_loop,
            args=(sub_type, stock_set),
            daemon=True,
        )
        self.receive_thread.start()

        for _ in range(10):
            if self.subscribed:
                break
            time.sleep(0.1)

    def _write_header(self, sub_type: int):
        if sub_type == 1:
            self.data_writer.writerow([
                "seqno", "timestamp", "exchange", "symbol", "trade_date", "data_time", "trade_datetime",
                "exchange_id", "last_price", "pre_close_price", "open_price", "high_price", "low_price",
                "qty", "turnover", "avg_price", "trades_count", "ticker_status", "total_bid_qty",
                "total_ask_qty", "bid_price", "bid_volume", "ask_price", "ask_volume",
            ])
            return

        self.data_writer.writerow([
            "seqno", "timestamp", "sub_type", "exchange", "symbol", "trade_date", "update_time",
            "trade_datetime", "exchange_id", "channel_no", "seq_no", "trade2_order1", "price",
            "volume", "trd_money", "ord_side", "ord_type", "trd_bs_flag", "trd_buy_no",
            "trd_sell_no", "ord_no", "biz_index", "trans_flag", "order_trd_volume",
        ])

    def _receive_loop(self, sub_type: int, stock_set: Set[str]):
        pattern = "market:snapshot:*" if sub_type == 1 else "market:tick:*"
        finished_stocks: Set[str] = set()

        try:
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.psubscribe(pattern)
            confirm_msg = self.pubsub.get_message(timeout=5)
            if confirm_msg and confirm_msg["type"] == "psubscribe":
                self.subscribed = True
                self.logger.info(f"Redis订阅确认: {confirm_msg}")

            while self.receiving:
                try:
                    message = self.pubsub.get_message(timeout=1)
                    if message is None or message["type"] in ("psubscribe", "subscribe", "punsubscribe", "unsubscribe"):
                        continue
                    if message["type"] != "pmessage":
                        continue

                    channel_info = ClickHouseMessageParser.parse_channel(message["channel"])
                    key = f"{channel_info['exchange']}:{channel_info['symbol']}"
                    if key not in stock_set:
                        continue

                    parsed = ClickHouseMessageParser.parse_message(message["data"])
                    self._write_message(parsed)
                    self.received_count += 1

                    if parsed.seqno == 0:
                        finished_stocks.add(key)
                        self.logger.info(f"证券 {key} 推送完成(seqno=0), 已完成: {len(finished_stocks)}/{len(stock_set)}")
                        if finished_stocks >= stock_set:
                            self.logger.info(f"所有证券推送完成，数据接收完成: {self.received_count} 条")
                            self.receiving = False
                            break
                except redis.ConnectionError:
                    if not self.receiving:
                        break
                    continue
        except Exception as exc:
            self.logger.error(f"接收数据异常: {exc}")
        finally:
            self.receiving = False
            if self.pubsub:
                try:
                    self.pubsub.punsubscribe()
                    self.pubsub.close()
                except Exception:
                    pass
                self.pubsub = None

    def _write_message(self, message: Any):
        if isinstance(message, SnapshotMessage):
            data = message.data
            self.data_writer.writerow([
                message.seqno,
                message.timestamp,
                message.exchange,
                message.symbol,
                data.get("trade_date", ""),
                data.get("data_time", -1),
                data.get("trade_datetime", ""),
                data.get("exchange_id", -1),
                data.get("last_price", -1),
                data.get("pre_close_price", -1),
                data.get("open_price", -1),
                data.get("high_price", -1),
                data.get("low_price", -1),
                data.get("qty", -1),
                data.get("turnover", -1),
                data.get("avg_price", -1),
                data.get("trades_count", -1),
                data.get("ticker_status", ""),
                data.get("total_bid_qty", -1),
                data.get("total_ask_qty", -1),
                ",".join(str(item) for item in data.get("bid_price", [])),
                ",".join(str(item) for item in data.get("bid_volume", [])),
                ",".join(str(item) for item in data.get("ask_price", [])),
                ",".join(str(item) for item in data.get("ask_volume", [])),
            ])
            return

        if isinstance(message, TickMessage):
            data = message.data
            self.data_writer.writerow([
                message.seqno,
                message.timestamp,
                message.sub_type,
                message.exchange,
                message.symbol,
                data.get("trade_date", ""),
                data.get("update_time", -1),
                data.get("trade_datetime", ""),
                data.get("exchange_id", -1),
                data.get("channel_no", -1),
                data.get("seq_no", -1),
                data.get("trade2_order1", -1),
                data.get("price", -1),
                data.get("volume", -1),
                data.get("trd_money", -1),
                data.get("ord_side", ""),
                data.get("ord_type", ""),
                data.get("trd_bs_flag", ""),
                data.get("trd_buy_no", -1),
                data.get("trd_sell_no", -1),
                data.get("ord_no", -1),
                data.get("biz_index", -1),
                data.get("trans_flag", -1),
                data.get("order_trd_volume", -1),
            ])

    def save_result(self, response: Dict[str, Any], output_file: str):
        with open(output_file, "w", encoding="utf-8", newline="") as file_obj:
            writer = csv.writer(file_obj, delimiter="|")
            writer.writerow(["date", "code", "count"])
            if response.get("success"):
                for date_stat in response.get("stats", []):
                    date = date_stat["date"]
                    for item in date_stat.get("items", []):
                        writer.writerow([date, item["code"], item["count"]])

    def _stop_receiving(self):
        self.receiving = False
        if self.pubsub:
            try:
                self.pubsub.unsubscribe()
                self.pubsub.punsubscribe()
            except Exception:
                pass
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=5)
        if self.data_file:
            self.data_file.close()
            self.data_file = None
            self.data_writer = None

    def close(self):
        self._stop_receiving()
        self.selection_reader.close()
        if self.redis_client:
            self.redis_client.close()


def main():
    parser = argparse.ArgumentParser(description="ClickHouse数据客户端")

    config_path = "config/config.ini"
    try:
        update_global_settings(config_path)
    except Exception:
        pass

    parser.add_argument("--start-date", type=str, default=settings.backtest.start_date)
    parser.add_argument("--end-date", type=str, default=settings.backtest.end_date)
    parser.add_argument("--config", type=str, default="config/config.ini")
    parser.add_argument("--server-host", type=str, default="localhost")
    parser.add_argument("--server-port", type=int, default=9998)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--sub-type", type=int, default=1, choices=[1, 2, 3, 4])
    args = parser.parse_args()

    try:
        update_global_settings(args.config)
        setup_logging()
        logger = get_logger("clickhouse_client_main")
    except Exception as exc:
        print(f"配置文件加载失败: {exc}")
        return

    client = ClickHouseClient(host=args.server_host, port=args.server_port)

    try:
        start_dt = datetime.strptime(args.start_date, "%Y%m%d")
        end_dt = datetime.strptime(args.end_date, "%Y%m%d")
        current_dt = start_dt
        all_stats = []

        while current_dt <= end_dt:
            current_date = current_dt.strftime("%Y%m%d")
            logger.info("=" * 60)
            logger.info(f"处理日期: {current_date}, sub_type={args.sub_type}")
            logger.info("=" * 60)

            stocks = client.read_selection_stocks(current_date)
            if not stocks:
                current_dt += timedelta(days=1)
                continue

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            if args.output:
                base_dir = os.path.dirname(args.output)
                base_name = os.path.splitext(os.path.basename(args.output))[0]
                stats_file = os.path.join(base_dir, f"{base_name}_{current_date}.csv") if base_dir else f"clickhouse_client_result/{base_name}_{current_date}.csv"
                data_file = os.path.join(base_dir, f"{base_name}_{current_date}_data.csv") if base_dir else f"clickhouse_client_result/{base_name}_{current_date}_data.csv"
            else:
                stats_file = f"clickhouse_client_result/{current_date}_{timestamp}.csv"
                data_file = f"clickhouse_client_result/{current_date}_{timestamp}_data.csv"

            response = client.subscribe(args.sub_type, current_date, current_date, stocks, data_file)
            if response.get("success"):
                client._ensure_parent_dir(stats_file)
                client.save_result(response, stats_file)
                all_stats.extend(response.get("stats", []))
                logger.info(f"日期 {current_date} 订阅成功")
                logger.info(f"统计文件: {stats_file}")
                logger.info(f"数据文件: {data_file}")
            else:
                logger.error(f"日期 {current_date} 订阅失败: {response.get('error')}")

            current_dt += timedelta(days=1)

        if all_stats:
            total_count = 0
            for date_stat in all_stats:
                total_count += sum(item["count"] for item in date_stat.get("items", []))
            logger.info(f"总接收数量: {total_count}")
    except Exception as exc:
        logger.error(f"客户端运行失败: {exc}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()