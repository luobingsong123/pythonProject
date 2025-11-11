import pandas as pd
import numpy as np
from jqdatasdk import *
import pymysql
from sqlalchemy import create_engine
import time
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库配置 - 请根据实际情况修改
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'your_username',
    'password': 'your_password',
    'database': 'jq_data',
    'charset': 'utf8mb4'
}

# 认证
auth('13877907589', 'aA*963.-+')


class StockDataToMySQL:
    """
    将聚宽数据存储到MySQL数据库的类
    本代码仅用于回测研究，实盘使用风险自担
    """

    def __init__(self, db_config):
        self.db_config = db_config
        self.engine = None
        self.connection = None
        self.connect_db()

    def connect_db(self):
        """建立数据库连接"""
        try:
            self.engine = create_engine(
                f"mysql+pymysql://{self.db_config['user']}:{self.db_config['password']}"
                f"@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            )
            self.connection = self.engine.connect()
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def get_existing_stock_codes(self):
        """
        查询数据库中已存在日线数据的股票代码

        返回:
        set: 已存在的股票代码集合
        """
        try:
            query = "SELECT DISTINCT CODE FROM stock_daily_price"
            existing_codes = pd.read_sql(query, self.connection)
            existing_set = set(existing_codes['CODE'].tolist())
            logger.info(f"数据库中已存在 {len(existing_set)} 只股票的日线数据")
            return existing_set
        except Exception as e:
            logger.warning(f"查询已存在股票代码失败: {e}")
            return set()

    def get_stock_latest_date(self, stock_code):
        """
        获取某只股票在数据库中的最新交易日期

        参数:
        stock_code: str, 股票代码

        返回:
        str: 最新交易日期，格式为'YYYY-MM-DD'，如果无数据则返回None
        """
        try:
            query = f"SELECT MAX(trade_date) as latest_date FROM stock_daily_price WHERE CODE = '{stock_code}'"
            result = pd.read_sql(query, self.connection)
            latest_date = result['latest_date'].iloc[0]

            if pd.isna(latest_date):
                return None
            else:
                # 转换为字符串格式
                return latest_date.strftime('%Y-%m-%d')
        except Exception as e:
            logger.warning(f"查询股票 {stock_code} 最新日期失败: {e}")
            return None

    def save_stock_basic_to_db(self, stocks_data):
        """
        将股票基础信息保存到数据库

        参数:
        stocks_data: DataFrame, 股票基础数据
        """
        try:
            # 数据预处理，映射到数据库表结构
            basic_data = stocks_data.reset_index()
            basic_data = basic_data.rename(columns={
                'index': 'CODE',
                'display_name': 'NAME',
                'start_date': 'list_date'
            })

            # 选择需要的列
            basic_data = basic_data[['CODE', 'NAME', 'list_date']]
            basic_data['industry'] = None  # 行业信息需要额外获取

            # 转换为合适的日期格式
            basic_data['list_date'] = pd.to_datetime(basic_data['list_date']).dt.date

            # 保存到数据库
            basic_data.to_sql(
                'stock_basic',
                self.engine,
                if_exists='replace',  # 首次运行使用replace，后续可改为append
                index=False,
                chunksize=1000
            )

            logger.info(f"成功保存 {len(basic_data)} 条股票基础信息到数据库")
            return True

        except Exception as e:
            logger.error(f"保存股票基础信息失败: {e}")
            return False

    def get_stock_daily_data(self, stock_code, start_date, end_date):
        """
        获取单只股票的日线数据

        参数:
        stock_code: str, 股票代码
        start_date: str, 开始日期
        end_date: str, 结束日期

        返回:
        DataFrame: 日线数据
        """
        try:
            # 获取日线数据
            price_data = get_price(
                stock_code,
                start_date=start_date,
                end_date=end_date,
                frequency='daily',
                fields=['open', 'high', 'low', 'close', 'volume', 'money']
            )

            if price_data is not None and not price_data.empty:
                price_data = price_data.reset_index()
                price_data['CODE'] = stock_code
                price_data = price_data.rename(columns={
                    'index': 'trade_date',
                    'open': 'OPEN',
                    'high': 'high',
                    'low': 'low',
                    'close': 'CLOSE',
                    'volume': 'volume',
                    'money': 'money'
                })

                # 选择需要的列并处理数据类型
                price_data = price_data[['CODE', 'trade_date', 'OPEN', 'high', 'low', 'CLOSE', 'volume', 'money']]
                price_data['trade_date'] = pd.to_datetime(price_data['trade_date']).dt.date

                return price_data
            else:
                return None

        except Exception as e:
            logger.warning(f"获取股票 {stock_code} 日线数据失败: {e}")
            return None

    def save_daily_data_to_db_incremental(self, all_stock_codes, start_date='2005-01-01', end_date=None, batch_size=30):
        """
        增量保存日线数据到数据库，跳过已存在的股票

        参数:
        all_stock_codes: list, 所有股票代码列表
        start_date: str, 开始日期
        end_date: str, 结束日期（默认今天）
        batch_size: int, 批量处理大小
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # 获取已存在的股票代码
        existing_codes = self.get_existing_stock_codes()

        # 筛选需要处理的股票代码
        pending_codes = [code for code in all_stock_codes if code not in existing_codes]

        if not pending_codes:
            logger.info("所有股票的日线数据已存在，无需更新")
            return

        logger.info(f"需要处理的股票数量: {len(pending_codes)}")
        logger.info(f"已存在的股票数量: {len(existing_codes)}")

        total_codes = len(pending_codes)
        successful_codes = 0
        failed_codes = 0

        logger.info(f"开始获取 {total_codes} 只股票的日线数据...")

        for i in range(0, total_codes, batch_size):
            batch_codes = pending_codes[i:i + batch_size]
            batch_data = []

            for code in batch_codes:
                try:
                    # 对于每只股票，检查是否需要从特定日期开始获取
                    latest_date = self.get_stock_latest_date(code)
                    actual_start_date = start_date

                    if latest_date:
                        # 如果已有数据，从最新日期的下一天开始获取
                        latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
                        next_day = latest_dt + timedelta(days=1)
                        actual_start_date = next_day.strftime('%Y-%m-%d')

                        # 如果最新日期已经等于或晚于结束日期，跳过该股票
                        if latest_dt >= datetime.strptime(end_date, '%Y-%m-%d'):
                            logger.info(f"股票 {code} 数据已是最新，跳过")
                            successful_codes += 1
                            continue

                    daily_data = self.get_stock_daily_data(code, actual_start_date, end_date)
                    if daily_data is not None and not daily_data.empty:
                        batch_data.append(daily_data)
                        successful_codes += 1
                        logger.info(f"成功获取股票 {code} 从 {actual_start_date} 到 {end_date} 的数据，共 {len(daily_data)} 条")
                    else:
                        failed_codes += 1
                        logger.warning(f"股票 {code} 无数据或获取失败")

                    # 避免请求频率过高
                    time.sleep(0.1)

                except Exception as e:
                    logger.warning(f"处理股票 {code} 时出错: {e}")
                    failed_codes += 1
                    continue

            # 批量保存当前批次数据
            if batch_data:
                try:
                    combined_data = pd.concat(batch_data, ignore_index=True)
                    combined_data.to_sql(
                        'stock_daily_price',
                        self.engine,
                        if_exists='append',
                        index=False,
                        chunksize=1000
                    )
                    logger.info(f"已处理批次 {i // batch_size + 1}/{(total_codes - 1) // batch_size + 1}, "
                                f"成功: {successful_codes}, 失败: {failed_codes}")

                except Exception as e:
                    logger.error(f"保存批次数据失败: {e}")

            # 查询计数检查（修复后的版本）
            if (i + batch_size) % 200 == 0:
                remaining_queries = get_query_count()
                logger.info(f"剩余查询次数: {remaining_queries}")

                # 修复：比较剩余查询次数而不是字典
                if isinstance(remaining_queries, dict) and 'spare' in remaining_queries:
                    if remaining_queries['spare'] < 100:
                        logger.warning("查询次数不足，暂停10分钟")
                        time.sleep(600)
                else:
                    # 如果返回的不是字典，直接使用
                    if remaining_queries < 100:
                        logger.warning("查询次数不足，暂停10分钟")
                        time.sleep(600)

        logger.info(f"日线数据获取完成！成功: {successful_codes}, 失败: {failed_codes}")

    def close_connection(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
        logger.info("数据库连接已关闭")


def main():
    """主函数"""
    # 初始化数据库操作类
    stock_db = StockDataToMySQL(DB_CONFIG)

    try:
        # 获取账户信息
        account_info = get_account_info()
        query_count = get_query_count()
        logger.info(f"账户信息: {account_info}")
        logger.info(f"初始查询次数: {query_count}")

        # 获取全市场股票数据
        end_date = pd.Timestamp.today().strftime('%Y-%m-%d')
        all_stocks = get_all_securities(types=['stock'], date=end_date)
        logger.info(f"全市场股票数量: {len(all_stocks)}")

        # 保存股票基础信息到数据库（如果需要更新基础信息，取消注释）
        # logger.info("开始保存股票基础信息...")
        # stock_db.save_stock_basic_to_db(all_stocks)

        # 获取股票代码列表
        stock_codes = all_stocks.index.tolist()

        # 增量保存日线数据到数据库
        logger.info("开始增量获取日线数据...")
        stock_db.save_daily_data_to_db_incremental(
            stock_codes=stock_codes,
            start_date='2020-01-01',  # 可根据需要调整起始日期
            end_date=end_date,
            batch_size=30  # 每批处理30只股票
        )

        # 最终查询计数
        final_query_count = get_query_count()
        logger.info(f"最终查询次数: {final_query_count}")

    except Exception as e:
        logger.error(f"主程序执行失败: {e}")

    finally:
        stock_db.close_connection()


if __name__ == "__main__":
    main()