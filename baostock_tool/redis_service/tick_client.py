"""
Tick数据客户端

从Redis选股池读取股票代码，向Tick服务器订阅数据，并将订阅结果落地到文件
"""

import sys
import os
import socket
import json
import csv
from typing import List, Dict, Any
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import argparse
from utils.log_manager import setup_logging
from config.settings import settings
from config.config_loader import update_global_settings
from selection.reader import SelectionReader
from utils.log_manager import get_logger


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
        stocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        向服务器订阅Tick数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            stocks: 股票列表

        Returns:
            Dict: 服务器响应
        """
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

            return response

        except Exception as e:
            self.logger.error(f"订阅失败: {e}")
            return {
                "success": False,
                "error": f"连接服务器失败: {e}"
            }

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
                writer.writerow(['code', 'count'])

                # 写入数据
                if response.get("success") and "stats" in response:
                    for stat in response["stats"]:
                        writer.writerow([stat["code"], stat["count"]])

            self.logger.info(f"订阅结果已保存: {output_file}")

        except Exception as e:
            self.logger.error(f"保存结果失败: {e}")

    def close(self):
        """关闭客户端"""
        self.selection_reader.close()


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
        response = client.subscribe(args.start_date, args.end_date, stocks)

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
                total_count = sum(s["count"] for s in response["stats"])
                logger.info(f"总推送数量: {total_count}")
                for stat in response["stats"]:
                    logger.info(f"  {stat['code']}: {stat['count']}")
            logger.info(f"结果文件: {output_file}")
            logger.info("="*60)
        else:
            logger.error(f"订阅失败: {response.get('error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"客户端运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
