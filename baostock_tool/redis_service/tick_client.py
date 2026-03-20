"""
Tick数据客户端

从Redis选股池读取股票代码，向Tick服务器订阅数据，并将订阅结果落地到文件
"""

import sys
import os
import socket
import json
import csv
import threading
import time
from typing import List, Dict, Any
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import argparse
from utils.log_manager import setup_logging
from config.settings import settings
from config.config_loader import update_global_settings
from selection.reader import SelectionReader
from market.subscriber import SnapshotSubscriber
from utils.log_manager import get_logger
import traceback

class TickClient:
    """Tick数据客户端"""

    def __init__(self, host: str = "localhost", port: int = 9999):
        """
        初始化客户端

        Args:
            host: 服务器地址
            port: 服务器端口
        """
        self.host = host
        self.port = port
        self.logger = get_logger("tick_client")
        self.selection_reader = SelectionReader()
        self.snapshot_subscriber = SnapshotSubscriber()
        self.receiving = False
        self.tick_file = None
        self.tick_writer = None
        self.received_count = 0
        self.receive_thread: threading.Thread = None

    def read_selection_stocks(self, date: str) -> List[Dict[str, Any]]:
        """
        从Redis读取选股代码

        Args:
            date: 日期

        Returns:
            List[Dict]: 股票列表 [{"symbol": "600000", "exchange": "SSE"}, ...]
        """
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
        stocks = [
            {
                "symbol": stock.symbol,
                "exchange": stock.exchange
            }
            for stock in selection.stocks
        ]

        self.logger.info(f"读取到 {len(stocks)} 只选股: {selection.batch_id}, 策略: {selection.strategy_id}")
        return stocks

    def subscribe(
        self,
        start_date: str,
        end_date: str,
        stocks: List[Dict[str, Any]],
        tick_file_path: str
    ) -> Dict[str, Any]:
        """
        向服务器订阅Tick数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            stocks: 股票列表
            tick_file_path: tick数据文件路径

        Returns:
            Dict: 服务器响应
        """
        # 先启动接收线程
        self._start_receiving(tick_file_path, stocks)

        # 构建订阅请求
        stock_codes = [s["symbol"] for s in stocks]

        request = {
            "sub_type": 1,
            "start_date": start_date,
            "end_date": end_date,
            "stock": stock_codes
        }

        request_json = json.dumps(request, ensure_ascii=False)
        self.logger.info(f"发送订阅请求: {request_json}")

        try:
            # 连接服务器
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            self.logger.info(f"已连接到服务器: {self.host}:{self.port}")

            # 发送请求
            sock.sendall(request_json.encode("utf-8"))

            # 接收响应
            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk

            sock.close()

            # 解析响应
            response = json.loads(response_data.decode("utf-8"))
            self.logger.info(f"收到服务器响应: {response}")

            # 等待一段时间接收数据
            self.logger.info("等待接收tick数据...")
            time.sleep(10)

            # 停止接收
            self._stop_receiving()

            return response

        except Exception as e:
            self.logger.error(f"订阅失败: {e}")
            self._stop_receiving()
            return {
                "success": False,
                "error": f"连接服务器失败: {e}"
            }

    def _start_receiving(self, tick_file_path: str, stocks: List[Dict[str, Any]]):
        """
        启动接收线程

        Args:
            tick_file_path: tick数据文件路径
            stocks: 股票列表
        """
        self.receiving = True
        self.received_count = 0

        # 打开文件
        os.makedirs(os.path.dirname(tick_file_path), exist_ok=True)
        self.tick_file = open(tick_file_path, 'w', encoding='utf-8', newline='')
        self.tick_writer = csv.writer(self.tick_file, delimiter='|')
        # 写入表头
        self.tick_writer.writerow([
            'timestamp', 'exchange', 'symbol', 'last_price',
            'volume', 'amount', 'bid_price', 'bid_volume',
            'ask_price', 'ask_volume', 'date', 'time'
        ])

        # 构建订阅的股票集合
        stock_set = {
            f"{s['exchange']}:{s['symbol']}"
            for s in stocks
        }

        # 启动接收线程
        self.receive_thread = threading.Thread(
            target=self._receive_loop,
            args=(stock_set,),
            daemon=True
        )
        self.receive_thread.start()
        self.logger.info(f"开始接收tick数据: {tick_file_path}")

    def _receive_loop(self, stock_set: set):
        """
        接收循环

        Args:
            stock_set: 订阅的股票集合
        """
        try:
            pattern = "market:snapshot:*"
            for snapshot in self.snapshot_subscriber.subscribe(pattern):
                if not self.receiving:
                    break

                # 检查是否是订阅的股票
                key = f"{snapshot.exchange}:{snapshot.symbol}"
                if key in stock_set:
                    # 写入文件
                    data = snapshot.data
                    self.tick_writer.writerow([
                        snapshot.timestamp,
                        snapshot.exchange,
                        snapshot.symbol,
                        data.last_price,
                        data.volume,
                        data.amount,
                        ','.join(str(p) for p in data.bid_price),
                        ','.join(str(v) for v in data.bid_volume),
                        ','.join(str(p) for p in data.ask_price),
                        ','.join(str(v) for v in data.ask_volume),
                        data.date,
                        data.timestamp
                    ])
                    self.received_count += 1

                    # 每1000条打印一次
                    if self.received_count % 1000 == 0:
                        self.logger.info(f"已接收 {self.received_count} 条tick数据")

        except Exception as e:
            self.logger.error(f"接收tick数据异常: {e}")
        finally:
            self.receiving = False

    def _stop_receiving(self):
        """停止接收"""
        self.receiving = False
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=5)
        if self.tick_file:
            self.tick_file.close()
            self.tick_file = None
            self.tick_writer = None
        # self.logger.info(f"停止接收，共接收 {self.received_count} 条tick数据")

    def save_result(self, response: Dict[str, Any], output_file: str):
        """
        保存订阅结果到文件

        Args:
            response: 服务器响应
            output_file: 输出文件路径
        """
        try:
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter='|')
                # 写入表头
                writer.writerow(['date', 'code', 'count'])

                # 写入数据（按日期分组）
                if response.get("success") and "stats" in response:
                    for date_stat in response["stats"]:
                        date = date_stat["date"]
                        for item in date_stat["items"]:
                            writer.writerow([date, item["code"], item["count"]])

            self.logger.info(f"订阅结果已保存: {output_file}")

        except Exception as e:
            self.logger.error(f"保存结果失败: {e}")

    def close(self):
        """关闭客户端"""
        self._stop_receiving()
        self.selection_reader.close()
        self.snapshot_subscriber.close()


def main():
    """主函数"""


    parser = argparse.ArgumentParser(
        description='Tick数据客户端',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python tick_client.py --start-date 20241111 --end-date 20241112
  python tick_client.py --start-date 20241111 --end-date 20241112 --output result.csv
        """
    )

    # 先加载配置文件以获取默认值
    config_path = 'config/config.ini'
    try:
        update_global_settings(config_path)
    except:
        pass

    parser.add_argument(
        '--start-date',
        type=str,
        default=settings.backtest.start_date,
        help=f'开始日期，格式YYYYMMDD（默认: {settings.backtest.start_date}）'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        default=settings.backtest.end_date,
        help=f'结束日期，格式YYYYMMDD（默认: {settings.backtest.end_date}）'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/config.ini',
        help='配置文件路径（默认: config/config.ini）'
    )

    parser.add_argument(
        '--server-host',
        type=str,
        default='localhost',
        help='Tick服务器地址（默认: localhost）'
    )

    parser.add_argument(
        '--server-port',
        type=int,
        default=9999,
        help='Tick服务器端口（默认: 9999）'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出文件路径（CSV格式）'
    )

    parser.add_argument(
        '--selection-date',
        type=str,
        default=None,
        help='选股日期，格式YYYYMMDD（默认使用end_date）'
    )

    args = parser.parse_args()

    # 从配置文件加载配置
    try:
        update_global_settings(args.config)
        setup_logging()
        logger = get_logger("tick_client_main")
        logger.info(f"配置文件加载成功: {args.config}")
    except Exception as e:
        print(f"配置文件加载失败: {e}")
        return

    # 打印配置信息
    logger.info("="*60)
    logger.info("Tick数据客户端 配置信息")
    logger.info("="*60)
    logger.info(f"选股日期: {args.selection_date or args.end_date}")
    logger.info(f"订阅日期范围: {args.start_date} ~ {args.end_date}")
    logger.info(f"Tick服务器: {args.server_host}:{args.server_port}")
    logger.info(f"Redis: {settings.redis.host}:{settings.redis.port} DB={settings.redis.db}")
    logger.info("="*60)

    # 创建客户端
    client = TickClient(host=args.server_host, port=args.server_port)

    try:
        # 读取选股数据
        selection_date = args.selection_date or args.end_date
        stocks = client.read_selection_stocks(selection_date)

        if not stocks:
            logger.error("未找到选股数据，退出")
            return

        # 订阅Tick数据
        # tick数据文件路径：与统计文件同目录，后缀为tick.csv
        if args.output:
            base_dir = os.path.dirname(args.output)
            base_name = os.path.splitext(os.path.basename(args.output))[0]
            tick_file = os.path.join(base_dir, f"{base_name}_tick.csv") if base_dir else f"tick_client_result/{base_name}_tick.csv"
        else:
            base_name = f"{selection_date}_{args.start_date}_{args.end_date}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
            tick_file = f"tick_client_result/{base_name}_tick.csv"

        response = client.subscribe(args.start_date, args.end_date, stocks, tick_file)

        # 保存结果
        if response.get("success"):
            # 生成输出文件名
            if args.output:
                output_file = args.output
            else:
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                output_file = f"tick_client_result/{selection_date}_{args.start_date}_{args.end_date}_{timestamp}.csv"

            # 确保目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 保存结果
            client.save_result(response, output_file)

            # 打印统计
            logger.info("="*60)
            logger.info("订阅统计")
            logger.info("="*60)
            logger.info(f"日期范围: {args.start_date} ~ {args.end_date}")
            logger.info(f"股票数量: {len(stocks)}")
            if "stats" in response:
                total_count = 0
                for date_stat in response["stats"]:
                    date_count = sum(item["count"] for item in date_stat["items"])
                    total_count += date_count
                    logger.info(f"日期 {date_stat['date']}: {date_count} 条")
                logger.info("详细信息:")
                for date_stat in response["stats"]:
                    logger.info(f"  {date_stat['date']}:")
                    for item in date_stat["items"]:
                        logger.info(f"    {item['code']}: {item['count']}")
                logger.info(f"总接收数量: {total_count}")
            logger.info(f"统计结果文件: {output_file}")
            logger.info(f"Tick数据文件: {tick_file}")
            # logger.info(f"接收tick数据: {client.received_count} 条")
            logger.info("="*60)
        else:
            logger.error(f"订阅失败: {response.get('error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"客户端运行失败: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
