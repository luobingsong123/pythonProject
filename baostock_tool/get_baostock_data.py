# -*- coding: utf-8 -*-
import baostock as bs
import pandas as pd
import pandas_ta as ta
import pymysql
from datetime import datetime, timedelta
from utils.logger_utils import setup_logger
import sys
import configparser
import os


config_path = os.path.join("./config.ini")
if not os.path.exists(config_path):
    raise FileNotFoundError(f"配置文件 {config_path} 未找到！")
config = configparser.ConfigParser()
config.read(config_path, encoding="utf-8")  # 注意编码，避免中文乱码

logger = setup_logger(logger_name=__name__,
                      log_level=config.get("logging","level"),
                      log_dir=config.get("logging","log_dir"),)


class BaostockDataCollector:
    def __init__(self, db_config):
        """
        初始化数据库连接配置
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None

    def connect_database(self):
        """连接MySQL数据库"""
        try:
            self.conn = pymysql.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cursor = self.conn.cursor()
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False

    def close_database(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("数据库连接已关闭")

    def login_baostock(self):
        """登录Baostock系统"""
        try:
            lg = bs.login()
            if lg.error_code == '0':
                logger.info("Baostock登录成功")
                return True
            else:
                logger.error(f"Baostock登录失败: {lg.error_msg}")
                return False
        except Exception as e:
            logger.error(f"Baostock登录异常: {e}")
            return False

    def logout_baostock(self):
        """登出Baostock系统"""
        try:
            bs.logout()
            logger.info("Baostock已登出")
        except Exception as e:
            logger.error(f"Baostock登出异常: {e}")

    def parse_stock_code(self, full_code):
        """解析股票代码，返回(market, code_int)"""
        if '.' in full_code:
            market, code_str = full_code.split('.')
            market = market.strip().lower()
            code_int = int(code_str.strip())
            return market, code_int
        else:
            code_str = full_code.strip()
            if code_str.startswith(('6', '9')):
                return 'sh', int(code_str)
            elif code_str.startswith(('0', '2', '3')):
                return 'sz', int(code_str)
            else:
                raise ValueError(f"无法解析股票代码: {full_code}")

    def get_all_stocks(self, query_date=None):
        """
        获取所有股票基本信息
        """
        if query_date is None:
            # query_date = datetime.now().strftime("%Y-%m-%d")
            query_date = "2025-11-17"

        try:
            rs = bs.query_all_stock(day=query_date)
            if rs.error_code != '0':
                logger.error(f"获取股票列表失败: {rs.error_msg}")
                return None

            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                logger.warning("未获取到股票数据")
                return None

            df = pd.DataFrame(data_list, columns=rs.fields)
            logger.info(f"成功获取 {len(df)} 只股票基本信息")
            return df

        except Exception as e:
            logger.error(f"获取股票列表异常: {e}")
            return None

    def save_stock_basic_info(self, stock_df):
        """
        将股票基本信息保存到数据库（新表结构）
        """
        if stock_df is None or stock_df.empty:
            logger.warning("股票数据为空，跳过保存")
            return False

        try:
            inserted_count = 0
            updated_count = 0

            for _, row in stock_df.iterrows():
                full_code = row['code']
                code_name = row.get('code_name', '')

                # 跳过指数代码
                if not full_code.startswith(('sh.', 'sz.')) or '000' in full_code:
                    continue

                try:
                    market, code_int = self.parse_stock_code(full_code)
                except ValueError as e:
                    logger.warning(f"跳过无法解析的代码: {full_code}")
                    continue

                # 使用REPLACE INTO处理重复数据
                replace_sql = """
                REPLACE INTO stock_basic_info 
                (market, code_int, name, list_date, created_at, updated_at) 
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """

                list_date = datetime.now().strftime("%Y-%m-%d")
                self.cursor.execute(replace_sql, (market, code_int, code_name, list_date))
                inserted_count += 1

            self.conn.commit()
            logger.info(f"股票基本信息保存完成: 处理{inserted_count}条")
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"保存股票基本信息异常: {e}")
            return False

    def get_stock_k_data(self, code, start_date, end_date, frequency='d', fields=None):
        """
        获取股票K线数据
        """
        if fields is None:
            if frequency == 'd':
                fields = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST"
            else:
                fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"

        try:
            rs = bs.query_history_k_data_plus(
                code=code,
                fields=fields,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag="2"
            )

            if rs.error_code != '0':
                logger.warning(f"股票{code} {frequency}线数据获取失败: {rs.error_msg}")
                return None

            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                logger.warning(f"股票{code} 未获取到{frequency}线数据")
                return None

            df = pd.DataFrame(data_list, columns=rs.fields)
            logger.debug(f"成功获取股票{code} {len(df)}条{frequency}线数据")
            return df

        except Exception as e:
            logger.error(f"获取股票{code}K线数据异常: {e}")
            return None

    def save_daily_data_batch(self, code, daily_df):
        """批量保存日线数据到数据库（新表结构）"""
        if daily_df is None or daily_df.empty:
            return False

        try:
            # 解析股票代码
            market, code_int = self.parse_stock_code(code)

            data_tuples = []
            for _, row in daily_df.iterrows():
                # 数据清洗和转换
                date = row['date']
                open_price = float(row['open']) if row['open'] != '' else 0
                high = float(row['high']) if row['high'] != '' else 0
                low = float(row['low']) if row['low'] != '' else 0
                close = float(row['close']) if row['close'] != '' else 0
                preclose = float(row['preclose']) if 'preclose' in row and row['preclose'] != '' else 0
                volume = int(float(row['volume'])) if row['volume'] != '' else 0
                amount = float(row['amount']) if row['amount'] != '' else 0
                turn = float(row['turn']) if 'turn' in row and row['turn'] != '' else 0
                pctchg = float(row['pctChg']) if 'pctChg' in row and row['pctChg'] != '' else 0
                peTTM = float(row['peTTM']) if 'peTTM' in row and row['peTTM'] != '' else 0
                pbMRQ = float(row['pbMRQ']) if 'pbMRQ' in row and row['pbMRQ'] != '' else 0
                psTTM = float(row['psTTM']) if 'psTTM' in row and row['psTTM'] != '' else 0
                pcfNcfTTM = float(row['pcfNcfTTM']) if 'pcfNcfTTM' in row and row['pcfNcfTTM'] != '' else 0
                tradestatus = 1 if row.get('tradestatus', '1') == '1' else 0
                isst = 1 if row.get('isST', '0') == '1' else 0

                data_tuples.append((
                    date, market, code_int, 'd', open_price, high, low, close, preclose,
                    volume, amount, 2, turn, tradestatus, pctchg, peTTM, pbMRQ, psTTM, pcfNcfTTM, isst
                ))

            # 批量插入
            insert_sql = """
            REPLACE INTO stock_daily_data 
            (date, market, code_int, frequency, open, high, low, close, preclose, volume, amount, 
             adjustflag, turn, tradestatus, pctChg, peTTM, pbMRQ, psTTM, pcfNcfTTM, isST, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """

            self.cursor.executemany(insert_sql, data_tuples)
            self.conn.commit()
            logger.info(f"股票{code} 日线数据批量保存 {len(data_tuples)} 条")
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"批量保存日线数据异常: {e}")
            return False

    def save_minute_data_batch(self, code, minute_df, frequency):
        """批量保存分钟线数据到数据库（新表结构）"""
        if minute_df is None or minute_df.empty:
            return False

        try:
            # 解析股票代码
            market, code_int = self.parse_stock_code(code)

            freq_map = {'5': 5, '15': 15, '30': 30, '60': 60}
            freq_value = freq_map.get(frequency, 5)

            data_tuples = []
            for _, row in minute_df.iterrows():
                date = row['date']
                time_val = row.get('time', '000000')

                open_price = float(row['open']) if row['open'] != '' else 0
                high = float(row['high']) if row['high'] != '' else 0
                low = float(row['low']) if row['low'] != '' else 0
                close = float(row['close']) if row['close'] != '' else 0
                volume = int(float(row['volume'])) if row['volume'] != '' else 0
                amount = float(row['amount']) if row['amount'] != '' else 0

                data_tuples.append((
                    date, time_val, market, code_int, freq_value, open_price, high, low, close,
                    volume, amount, 2
                ))

            # 批量插入
            insert_sql = """
            REPLACE INTO stock_minute_data 
            (date, time, market, code_int, frequency, open, high, low, close, volume, amount, 
             adjustflag, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """

            self.cursor.executemany(insert_sql, data_tuples)
            self.conn.commit()
            logger.info(f"股票{code} {frequency}分钟线数据批量保存 {len(data_tuples)} 条")
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"批量保存分钟线数据异常: {e}")
            return False

    def collect_all_data(self, start_date="2020-01-01", minute_frequencies=['5']):
        """
        主函数：收集所有数据（全量拉取，无存在性检查）
        """
        # end_date = datetime.now().strftime("%Y-%m-%d")
        end_date = "2025-11-14"
        logger.info(f"开始全量数据收集，时间范围: {start_date} 到 {end_date}")

        # 1. 登录Baostock
        if not self.login_baostock():
            return False

        # 2. 连接数据库
        if not self.connect_database():
            self.logout_baostock()
            return False

        try:
            # 3. 获取并保存所有股票基本信息
            logger.info("步骤1: 获取股票基本信息")
            stock_df = self.get_all_stocks()
            if stock_df is not None:
                self.save_stock_basic_info(stock_df)

                # 4. 检查数据库中已存在的股票代码
                logger.info("步骤2: 检查数据库中已存在的股票")
                existing_stocks_sql = "SELECT DISTINCT code_int FROM stock_daily_data"
                self.cursor.execute(existing_stocks_sql)
                existing_stocks = {str(row['code_int']) for row in self.cursor.fetchall()}  # 转换为字符串确保一致比较
                logger.info(f"数据库中已存在 {len(existing_stocks)} 只股票的K线数据")

                # 5.筛选需要处理的股票（排除已存在的和特定代码）
                stocks_to_process = [
                    code for code in stock_df['code']
                    if code.startswith(('sh.', 'sz.')) and '000' not in code
                       and code.split('.')[1] not in existing_stocks  # 提取数字部分检查是否已存在
                ]

                logger.info(f"需要处理 {len(stocks_to_process)} 只A股股票的K线数据")

                # 6. 逐个获取未处理股票的K线数据
                total_stocks = len(stocks_to_process)
                for idx, code in enumerate(stocks_to_process):
                    logger.info(f"处理股票 [{idx + 1}/{total_stocks}]: {code}")

                    # 获取日线数据（全历史）
                    daily_df = self.get_stock_k_data(code, start_date, end_date, frequency='d')
                    if daily_df is not None:
                        self.save_daily_data_batch(code, daily_df)

                    # 获取分钟线数据（最近90天，避免数据量过大）
                    minute_start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                    for freq in minute_frequencies:
                        minute_df = self.get_stock_k_data(code, minute_start_date, end_date, frequency=freq)
                        if minute_df is not None:
                            self.save_minute_data_batch(code, minute_df, freq)

                    # # 添加延迟，避免请求过快
                    # time.sleep(0.3)

                logger.info("全量数据收集完成")
                return True
            else:
                logger.error("获取股票列表失败")
                return False

        except Exception as e:
            logger.error(f"数据收集过程异常: {e}")
            return False

        finally:
            # 清理资源
            self.close_database()
            self.logout_baostock()


def main():
    """主函数"""
    # 新数据库配置
    db_config = {
        'host': config.get("database","host"),
        'port': config.getint("database", "port"),
        'user': config.get("database","username"),
        'password': config.get("database","password"),
        'database': config.get("database","database")  # 修改为新数据库名
    }

    # 创建收集器实例
    collector = BaostockDataCollector(db_config)

    # 执行全量数据收集
    success = collector.collect_all_data(
        start_date="2020-01-01",  # 从2020年开始拉取
        # minute_frequencies=['5', '15', '30']  # 获取多种分钟线数据
        minute_frequencies=['5']  # 获取多种分钟线数据
    )

    if success:
        logger.info("全量数据收集任务完成")
    else:
        logger.error("全量数据收集任务失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
