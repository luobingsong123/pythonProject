"""ClickHouse 服务订阅示例。"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clickhouse_client import ClickHouseClient
from config.config_loader import update_global_settings
from utils.log_manager import get_logger, setup_logging


def main():
    parser = argparse.ArgumentParser(description="ClickHouse 订阅示例")
    parser.add_argument("--date", required=True, help="选股日期，格式 YYYYMMDD")
    parser.add_argument("--sub-type", type=int, default=1, choices=[1, 2, 3, 4])
    parser.add_argument("--server-host", default="localhost")
    parser.add_argument("--server-port", type=int, default=9998)
    parser.add_argument("--config", default="config/config.ini")
    parser.add_argument("--output-prefix", default=None, help="输出文件前缀，不带后缀")
    args = parser.parse_args()

    update_global_settings(args.config)
    setup_logging()
    logger = get_logger("clickhouse_subscribe_demo")

    client = ClickHouseClient(host=args.server_host, port=args.server_port)
    try:
        stocks = client.read_selection_stocks(args.date)
        if not stocks:
            logger.error(f"日期 {args.date} 没有可订阅股票")
            return

        output_prefix = args.output_prefix or f"clickhouse_demo/{args.date}_subtype_{args.sub_type}"
        stats_file = f"{output_prefix}_stats.csv"
        data_file = f"{output_prefix}_data.csv"

        response = client.subscribe(
            sub_type=args.sub_type,
            start_date=args.date,
            end_date=args.date,
            stocks=stocks,
            data_file_path=data_file,
        )
        if response.get("success"):
            client._ensure_parent_dir(stats_file)
            client.save_result(response, stats_file)
            logger.info(f"订阅成功，统计文件: {stats_file}")
            logger.info(f"订阅成功，数据文件: {data_file}")
        else:
            logger.error(f"订阅失败: {response.get('error')}")
    finally:
        client.close()


if __name__ == "__main__":
    main()