"""
Tick数据推送服务

提供TCP接口接收订阅消息，将指定日期和股票的Tick数据推送到Redis
"""

import sys
import os
import socket
import json
import threading
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from config.config_loader import update_global_settings
from database.queries import StockQueryService
from backtest.publisher import TickDataPublisher
from utils.log_manager import get_logger


class TickRequest:
    """Tick订阅请求"""

    def __init__(self, data: str):
        """
        解析订阅请求

        Args:
            data: JSON字符串
        """
        try:
            req = json.loads(data)

            # 新格式: 支持日期范围
            self.sub_type = req.get("sub_type", 1)
            self.start_date = req.get("start_date", "")
            self.end_date = req.get("end_date", "")
            self.stock_list = req.get("stock", [])
            self.valid = True
            self.error = None

            # 计算日期列表
            self.date_list = self._generate_date_list()

            # 兼容旧格式（单日期）
            if not self.start_date and not self.end_date:
                self.start_date = req.get("date", "")
                self.end_date = self.start_date

            # 将股票代码统一为codes格式
            self.codes = self.stock_list or req.get("codes", [])

        except json.JSONDecodeError as e:
            self.valid = False
            self.error = f"JSON解析错误: {e}"
            self.sub_type = 1
            self.start_date = ""
            self.end_date = ""
            self.codes = []
            self.date_list = []

    def _generate_date_list(self) -> List[str]:
        """
        生成日期列表

        Returns:
            List[str]: 日期列表
        """
        if not self.start_date or not self.end_date:
            return []

        try:
            start = datetime.strptime(self.start_date, "%Y%m%d")
            end = datetime.strptime(self.end_date, "%Y%m%d")

            date_list = []
            current = start
            while current <= end:
                date_list.append(current.strftime("%Y%m%d"))
                current = datetime.fromordinal(current.toordinal() + 1)

            return date_list
        except ValueError:
            return []

    @staticmethod
    def validate_date(date_str: str) -> bool:
        """验证日期格式 YYYYMMDD"""
        if not date_str or len(date_str) != 8:
            return False
        try:
            datetime.strptime(date_str, "%Y%m%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_code(code_str: str) -> Optional[Tuple[str, str, int, str]]:
        """
        验证并转换股票代码

        支持格式:
        - "sh.600000" 或 "sz.000001" (完整格式)
        - "600000" 或 "000001" (纯代码)

        Returns:
            Tuple[market, exchange, code, symbol] 或 None
        """
        if not code_str:
            return None

        code_str = code_str.strip()

        if "." in code_str:
            # 完整格式: sh.600000 或 sz.000001
            parts = code_str.split(".", 1)
            market = parts[0].lower()
            code = parts[1]
        else:
            # 纯代码格式
            if code_str.startswith("6"):
                market = "sh"
                code = code_str
            elif code_str.startswith(("0", "3")):
                market = "sz"
                code = code_str
            else:
                return None

        # 验证代码是否为6位数字
        if not code.isdigit() or len(code) != 6:
            return None

        code_int = int(code)
        exchange = "SSE" if market == "sh" else "SZSE"
        symbol = f"{code_int:06d}"

        return (market, exchange, code_int, symbol)


class TickServer:
    """Tick数据推送服务器"""

    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        """
        初始化服务器

        Args:
            host: 监听地址
            port: 监听端口
        """
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.logger = get_logger("tick_server")

        # 初始化Tick发布器
        self.publisher: Optional[TickDataPublisher] = None

    def initialize(self, db_config: Dict[str, Any]):
        """
        初始化发布器

        Args:
            db_config: 数据库配置
        """
        try:
            query_service = StockQueryService()
            query_service.initialize(**db_config)

            self.publisher = TickDataPublisher(
                query_service=query_service,
                use_pipeline=settings.backtest.use_pipeline
            )
            self.logger.info("Tick发布器初始化成功")
        except Exception as e:
            self.logger.error(f"Tick发布器初始化失败: {e}")
            raise

    def start(self):
        """启动服务器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        self.running = True
        self.logger.info(f"Tick服务器启动成功，监听 {self.host}:{self.port}")

        try:
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    self.logger.info(f"客户端连接: {client_address}")

                    # 为每个客户端创建处理线程
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                except OSError as e:
                    if self.running:
                        self.logger.error(f"接受连接错误: {e}")
        except KeyboardInterrupt:
            self.logger.info("接收到中断信号，正在关闭服务器...")
        finally:
            self.stop()

    def stop(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self.publisher:
            self.publisher.close()
        self.logger.info("Tick服务器已停止")

    def _handle_client(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        """
        处理客户端请求

        Args:
            client_socket: 客户端socket
            client_address: 客户端地址
        """
        try:
            # 接收数据
            data = b""
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                data += chunk
                if len(chunk) < 1024:
                    break

            if not data:
                self.logger.warning(f"客户端 {client_address} 未发送数据")
                return

            # 解码并解析请求
            try:
                request_str = data.decode("utf-8").strip()
                self.logger.info(f"收到请求: {client_address}, 数据: {request_str}")

                request = TickRequest(request_str)

                if not request.valid:
                    response = {
                        "success": False,
                        "error": request.error,
                        "timestamp": datetime.now().isoformat()
                    }
                    self._send_response(client_socket, response)
                    return

                # 验证订阅类型（只处理快照）
                if request.sub_type != 1:
                    response = {
                        "success": False,
                        "error": f"不支持的订阅类型: {request.sub_type}, 当前只支持1-快照",
                        "timestamp": datetime.now().isoformat()
                    }
                    self._send_response(client_socket, response)
                    return

                # 验证日期列表
                if not request.date_list:
                    response = {
                        "success": False,
                        "error": "无效的日期范围或日期格式，期望格式: YYYYMMDD",
                        "timestamp": datetime.now().isoformat()
                    }
                    self._send_response(client_socket, response)
                    return

                # 验证并转换股票代码
                stocks = []
                invalid_codes = []

                for code in request.codes:
                    stock_info = TickRequest.validate_code(code)
                    if stock_info:
                        stocks.append(stock_info)
                    else:
                        invalid_codes.append(code)

                if invalid_codes:
                    response = {
                        "success": False,
                        "error": f"无效的股票代码: {', '.join(invalid_codes)}",
                        "timestamp": datetime.now().isoformat()
                    }
                    self._send_response(client_socket, response)
                    return

                if not stocks:
                    response = {
                        "success": False,
                        "error": "未提供有效的股票代码",
                        "timestamp": datetime.now().isoformat()
                    }
                    self._send_response(client_socket, response)
                    return

                # 逐日推送Tick数据
                all_results = {}
                for date in request.date_list:
                    self.logger.info(f"开始推送Tick数据: 日期={date}, 股票数={len(stocks)}")
                    results = self.publisher.publish_tick_data_batch(date, stocks)

                    # 合并结果
                    for symbol, count in results.items():
                        if symbol in all_results:
                            all_results[symbol] += count
                        else:
                            all_results[symbol] = count

                # 构建统计响应（只返回每个证券代码和各自的数量）
                response = {
                    "success": True,
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                    "stats": [
                        {
                            "code": symbol,
                            "count": count
                        }
                        for symbol, count in all_results.items()
                    ]
                }

                # 发送响应
                self._send_response(client_socket, response)
                total_count = sum(all_results.values())
                self.logger.info(f"推送完成: 日期范围={request.start_date}~{request.end_date}, 总股票={len(stocks)}, 总推送={total_count}")

            except Exception as e:
                self.logger.error(f"处理请求错误: {e}")
                error_response = {
                    "success": False,
                    "error": f"处理请求时发生错误: {e}",
                    "timestamp": datetime.now().isoformat()
                }
                self._send_response(client_socket, error_response)

        except Exception as e:
            self.logger.error(f"处理客户端错误: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass

    def _send_response(self, client_socket: socket.socket, response: Dict[str, Any]):
        """
        发送响应

        Args:
            client_socket: 客户端socket
            response: 响应数据
        """
        try:
            response_json = json.dumps(response, ensure_ascii=False)
            response_bytes = response_json.encode("utf-8")
            client_socket.sendall(response_bytes)
        except Exception as e:
            self.logger.error(f"发送响应错误: {e}")


def main():
    """主函数"""
    from utils.log_manager import setup_logging

    # 配置文件路径
    config_path = 'config/config.ini'

    # 从配置文件加载配置
    try:
        update_global_settings(config_path)
        setup_logging()
        logger = get_logger("tick_server_main")
        logger.info(f"配置文件加载成功: {config_path}")
    except Exception as e:
        print(f"配置文件加载失败: {e}")
        return

    # 打印配置信息
    logger.info("="*60)
    logger.info("Tick数据推送服务 配置信息")
    logger.info("="*60)
    logger.info(f"配置文件: {config_path}")
    logger.info(f"TCP监听地址: 0.0.0.0:9999")
    logger.info(f"Redis: {settings.redis.host}:{settings.redis.port} DB={settings.redis.db}")
    logger.info(f"数据库: {settings.database.host}:{settings.database.port}/{settings.database.database}")
    logger.info("="*60)
    logger.info("")
    logger.info("订阅请求格式 (JSON):")
    logger.info('{')
    logger.info('  "sub_type": 1,           //1-快照，2-逐笔委托，3-逐笔成交')
    logger.info('  "start_date": "20241111",')
    logger.info('  "end_date": "20241112",')
    logger.info('  "stock": ["000001", "600001"]')
    logger.info('}')
    logger.info("")
    logger.info("股票代码支持格式:")
    logger.info('  - "sh.600000" (完整格式)')
    logger.info('  - "sz.000001" (完整格式)')
    logger.info('  - "600000" (纯代码，自动识别市场)')
    logger.info('  - "000001" (纯代码，自动识别市场)')
    logger.info("="*60)

    # 数据库配置
    db_config = {
        "host": settings.database.host,
        "port": settings.database.port,
        "user": settings.database.user,
        "password": settings.database.password,
        "database": settings.database.database,
        "charset": settings.database.charset
    }

    # 创建并启动服务器
    server = TickServer(host="0.0.0.0", port=9999)
    server.initialize(db_config)

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("接收到中断信号")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
