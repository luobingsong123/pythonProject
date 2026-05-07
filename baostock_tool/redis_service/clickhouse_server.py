"""ClickHouse 数据推送服务。"""

import json
import os
import queue
import socket
import sys
import threading
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from clickhouse_driver import Client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from baostock_tool.redis_service.backtest.clickhouse_publisher import ClickHousePublisher
from baostock_tool.redis_service.database.clickhouse_queries import ClickHouseQueryService
from baostock_tool.redis_service.config.config_loader import update_global_settings
from baostock_tool.redis_service.config.settings import settings
from baostock_tool.redis_service.tick_server import TickRequest
from baostock_tool.redis_service.utils.log_manager import get_logger, setup_logging


class ClickHouseConnectionPool:
    """ClickHouse 连接池，为每个线程提供独立的 Client 实例。"""

    def __init__(self, ch_config: Dict[str, Any], pool_size: int = 5):
        self._ch_config = ch_config
        self._pool: queue.Queue[Client] = queue.Queue(maxsize=pool_size)
        self._pool_size = pool_size
        self._lock = threading.Lock()
        self._created = 0

    def _create_client(self) -> Client:
        client = Client(**self._ch_config)
        client.execute("SELECT 1")
        return client

    def get(self) -> Client:
        try:
            return self._pool.get_nowait()
        except queue.Empty:
            pass
        with self._lock:
            if self._created < self._pool_size:
                client = self._create_client()
                self._created += 1
                return client
        return self._pool.get()

    def put(self, client: Client):
        try:
            self._pool.put_nowait(client)
        except queue.Full:
            client.disconnect()

    def close_all(self):
        while not self._pool.empty():
            try:
                client = self._pool.get_nowait()
                client.disconnect()
            except queue.Empty:
                break


class ClickHouseServer:
    """ClickHouse 数据推送服务器。"""

    def __init__(self, host: str = "0.0.0.0", port: int = 9998):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.logger = get_logger("clickhouse_server")
        self._conn_pool: Optional[ClickHouseConnectionPool] = None

    def initialize(self, ch_config: Dict[str, Any]):
        try:
            self._conn_pool = ClickHouseConnectionPool(ch_config, pool_size=5)
            client = self._conn_pool.get()
            try:
                self.logger.info("ClickHouse 连接池初始化成功")
            finally:
                self._conn_pool.put(client)
        except Exception as exc:
            self.logger.error("ClickHouse 初始化失败: %s", exc)
            raise

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        self.logger.info("ClickHouse 服务器启动成功，监听 %s:%s", self.host, self.port)

        try:
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True,
                    )
                    client_thread.start()
                except OSError as exc:
                    if self.running:
                        self.logger.error("接受连接错误: %s", exc)
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self._conn_pool:
            self._conn_pool.close_all()
        self.logger.info("ClickHouse 服务器已停止")

    def _handle_client(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        try:
            data = b""
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                data += chunk
                if len(chunk) < 1024:
                    break

            if not data:
                return

            request = TickRequest(data.decode("utf-8").strip())
            if not request.valid:
                self._send_response(client_socket, self._error_response(request.error))
                return

            if request.sub_type not in {1, 2, 3, 4}:
                self._send_response(client_socket, self._error_response(f"不支持的订阅类型: {request.sub_type}"))
                return

            if not request.date_list:
                self._send_response(client_socket, self._error_response("无效的日期范围或日期格式，期望格式: YYYYMMDD"))
                return

            stocks = []
            invalid_codes = []
            for code in request.codes:
                stock_info = TickRequest.validate_code(code)
                if stock_info:
                    stocks.append(stock_info)
                else:
                    invalid_codes.append(code)

            if invalid_codes:
                self._send_response(client_socket, self._error_response(f"无效的股票代码: {', '.join(invalid_codes)}"))
                return

            if not stocks:
                self._send_response(client_socket, self._error_response("未提供有效的股票代码"))
                return

            all_results = {}
            ch_client = self._conn_pool.get()
            try:
                query_service = ClickHouseQueryService(ch_client)
                publisher = ClickHousePublisher(
                    query_service=query_service,
                    use_pipeline=settings.backtest.use_pipeline,
                )
                for date in request.date_list:
                    if request.sub_type == 1:
                        results = publisher.publish_snapshot_batch(date, stocks)
                    else:
                        results = publisher.publish_tick_batch(date, stocks, sub_type=request.sub_type)
                    all_results[date] = results
            finally:
                self._conn_pool.put(ch_client)

            response = {
                "success": True,
                "sub_type": request.sub_type,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "stats": [
                    {
                        "date": date,
                        "items": [{"code": symbol, "count": count} for symbol, count in result.items()],
                    }
                    for date, result in all_results.items()
                ],
            }
            self._send_response(client_socket, response)
            self.logger.info("请求处理完成: %s, sub_type=%s", client_address, request.sub_type)
        except Exception as exc:
            self.logger.error("处理客户端错误: %s", exc)
            try:
                self._send_response(client_socket, self._error_response(f"处理请求时发生错误: {exc}"))
            except Exception:
                pass
        finally:
            try:
                client_socket.close()
            except Exception:
                pass

    def _send_response(self, client_socket: socket.socket, response: Dict[str, Any]):
        client_socket.sendall(json.dumps(response, ensure_ascii=False).encode("utf-8"))

    @staticmethod
    def _error_response(message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat(),
        }


def main():
    config_path = "config/config.ini"
    try:
        update_global_settings(config_path)
        setup_logging()
        logger = get_logger("clickhouse_server_main")
    except Exception as exc:
        print(f"配置文件加载失败: {exc}")
        return

    logger.info("=" * 60)
    logger.info("ClickHouse 数据推送服务 配置信息")
    logger.info("=" * 60)
    logger.info("配置文件: %s", config_path)
    logger.info("TCP监听地址: 0.0.0.0:9998")
    logger.info("Redis: %s:%s DB=%s", settings.redis.host, settings.redis.port, settings.redis.db)
    logger.info(
        "ClickHouse: %s:%s/%s",
        settings.clickhouse.host,
        settings.clickhouse.port,
        settings.clickhouse.database,
    )
    logger.info("=" * 60)

    ch_config = {
        "host": settings.clickhouse.host,
        "port": settings.clickhouse.port,
        "user": settings.clickhouse.user,
        "password": settings.clickhouse.password,
        "database": settings.clickhouse.database,
    }

    server = ClickHouseServer(host="0.0.0.0", port=9998)
    server.initialize(ch_config)

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("接收到中断信号")
    finally:
        server.stop()


if __name__ == "__main__":
    main()