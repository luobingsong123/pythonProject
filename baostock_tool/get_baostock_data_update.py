# -*- coding: utf-8 -*-
import baostock as bs
import pandas as pd
import pandas_ta as ta
import pymysql
from datetime import datetime, timedelta
from baostock_tool.utils.logger_utils import setup_logger
from baostock_tool.config import get_db_config, get_log_config
import sys

db_config_ = get_db_config()
log_config = get_log_config()
logger = setup_logger(logger_name=__name__,
                   log_level=log_config["log_level"],
                   log_dir=log_config["log_dir"], )

# 全局参数：最新交易日
LATEST_TRADING_DAY = None


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

    def get_trade_dates(self, start_date, end_date):
        """
        获取交易日数据
        """
        try:
            rs = bs.query_trade_dates(start_date=start_date, end_date=end_date)
            if rs.error_code != '0':
                logger.error(f"获取交易日数据失败: {rs.error_msg}")
                return None

            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                df['calendar_date'] = pd.to_datetime(df['calendar_date']).dt.date
                df['is_trading_day'] = df['is_trading_day'].astype(int)
                logger.info(f"成功获取 {len(df)} 条交易日数据")
                return df
            else:
                logger.warning("未获取到交易日数据")
                return None

        except Exception as e:
            logger.error(f"获取交易日数据异常: {e}")
            return None

    def save_to_database(self, df):
        """
        将交易日数据保存到数据库，并更新全局最新交易日
        """
        if df is None or df.empty:
            logger.warning("无数据可保存")
            return False

        try:
            success_count = 0
            for _, row in df.iterrows():
                sql = """
                REPLACE INTO trade_calendar (calendar_date, is_trading_day)
                VALUES (%s, %s)
                """
                values = (row['calendar_date'], row['is_trading_day'])

                self.cursor.execute(sql, values)
                success_count += 1

            self.conn.commit()
            logger.info(f"成功保存 {success_count} 条数据到数据库")

            # 更新全局最新交易日参数
            global LATEST_TRADING_DAY
            trading_days = df[df['is_trading_day'] == 1]['calendar_date']
            if not trading_days.empty:
                LATEST_TRADING_DAY = trading_days.max()
                logger.info(f"全局最新交易日已更新为: {LATEST_TRADING_DAY}")

            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"保存数据到数据库失败: {e}")
            return False

    def get_all_stocks(self, query_date=None):
        """
        获取所有股票基本信息
        """
        global LATEST_TRADING_DAY

        if query_date is None:
            if LATEST_TRADING_DAY:
                query_date = LATEST_TRADING_DAY.strftime("%Y-%m-%d")
                logger.info(f"使用全局最新交易日: {query_date}")
            else:
                query_date = datetime.now().strftime("%Y-%m-%d")
                logger.info(f"使用当前日期: {query_date}")

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

            for _, row in stock_df.iterrows():
                full_code = row['code']
                code_name = row.get('code_name', '')

                try:
                    market, code_int = self.parse_stock_code(full_code)
                except ValueError as e:
                    logger.warning(f"跳过无法解析的代码: {full_code}")
                    logger.error(str(e))
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
                turn = float(row['turn']) if 'turn' in row and row['turn'] != '' else 0     # 换手*成交额算出来的是流通市值
                pctchg = self.clamp(float(row['pctChg']) if 'pctChg' in row and row['pctChg'] != '' else 0)
                peTTM = self.clamp(float(row['peTTM']) if 'peTTM' in row and row['peTTM'] != '' else 0)
                pbMRQ = self.clamp(float(row['pbMRQ']) if 'pbMRQ' in row and row['pbMRQ'] != '' else 0)
                psTTM = self.clamp(float(row['psTTM']) if 'psTTM' in row and row['psTTM'] != '' else 0)
                pcfNcfTTM = self.clamp(float(row['pcfNcfTTM']) if 'pcfNcfTTM' in row and row['pcfNcfTTM'] != '' else 0)
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
            # # 获取traceback对象
            # _, _, tb = sys.exc_info()
            # # 提取报错的行数
            # error_line = tb.tb_lineno
            # print(f"报错行数：{error_line}")  # 输出：报错行数：3（假设try块的第3行是1/0）
            # print(f"异常类型：{type(e).__name__}")  # 输出：异常类型：ZeroDivisionError
            self.conn.rollback()
            logger.error(f"批量保存日线数据异常: {e}")
            with open(code + "data_tuples.csv", "w") as f:
                f.write(f"股票代码: {code}\n")
                for item in data_tuples:
                    f.write(",".join(map(str, item)) + "\n")
                f.write("\n")
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

    def collect_all_data(self, minute_frequencies=['5']):
        """
        主函数：收集所有数据（全量拉取，无存在性检查）
        """

        # 1. 登录Baostock
        if not self.login_baostock():
            return False

        # 2. 连接数据库
        if not self.connect_database():
            self.logout_baostock()
            return False

        sql = """
        SELECT MAX(DATE) AS latest_date
        FROM stock_daily_data
        WHERE code_int = 399998
        """
        self.cursor.execute(sql)
        result = self.cursor.fetchone()  # 获取单个结果
        if result['latest_date']:
            start_date = result['latest_date'].strftime('%Y-%m-%d')
        else:
            start_date = '2000-01-01'

        global LATEST_TRADING_DAY

        now = datetime.now()
        current_time = now.time()
        target_time = datetime.strptime("18:30", "%H:%M").time()
        # 判断当前时间是否在18:30前
        if current_time < target_time:
            # 在当前时间前，用前一天
            end_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            # 在18:30后，用当天
            end_date = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"增量数据收集，时间范围: {start_date} 到 {end_date}")

        try:
            df = self.get_trade_dates(start_date, end_date)
            if df is None:
                return False
            result = self.save_to_database(df)
            logger.info(f"保存交易日数据结果: {result}")

            # 使用全局最新交易日作为end_date
            global LATEST_TRADING_DAY
            if LATEST_TRADING_DAY:
                end_date = LATEST_TRADING_DAY.strftime("%Y-%m-%d")
                logger.info(f"使用全局最新交易日作为end_date: {end_date}")
        except Exception as e:
            logger.error(f"保存交易日数据异常: {e}")

        try:
            # 3. 获取并保存所有股票基本信息
            logger.info("步骤1: 获取股票基本信息")
            stock_df = self.get_all_stocks()  # 不传递end_date，使用全局最新交易日
            if stock_df is not None:
                self.save_stock_basic_info(stock_df)

                # 4. 检查数据库中已存在的股票代码
                # logger.info("步骤2: 检查数据库中已存在的股票")
                # existing_stocks_sql = "SELECT DISTINCT code_int FROM stock_daily_data"
                # self.cursor.execute(existing_stocks_sql)
                # existing_stocks = {str(row['code_int']) for row in self.cursor.fetchall()}  # 转换为字符串确保一致比较
                # logger.info(f"数据库中已存在 {len(existing_stocks)} 只股票的K线数据")

                # 5.筛选需要处理的股票（排除已存在的和特定代码）
                stocks_to_process = [
                    code for code in stock_df['code']
                    # if code.startswith(('sh.', 'sz.')) and code.split('.')[1] not in existing_stocks  # 提取数字部分检查是否已存在
                    if code.startswith(('sh.', 'sz.')) and code.split('.')[1]
                    # if code.startswith(('sh.', 'sz.')) and '000' not in code
                    #    and code.split('.')[1] not in existing_stocks  # 提取数字部分检查是否已存在
                ]

                logger.info(f"需要处理 {len(stocks_to_process)} 只A股股票的K线数据")

                # 6. 逐个获取未处理股票的K线数据
                total_stocks = len(stocks_to_process)
                for idx, code in enumerate(stocks_to_process):
                    logger.info(f"处理股票 [{idx + 1}/{total_stocks}]: {code}")

                    # 查询该股票在stock_daily_data表中的最新date
                    market, code_int = self.parse_stock_code(code)
                    sql = """
                    SELECT MAX(date) AS latest_date
                    FROM stock_daily_data
                    WHERE market = %s AND code_int = %s
                    """
                    self.cursor.execute(sql, (market, code_int))
                    result = self.cursor.fetchone()

                    # 如果存在最新日期，则使用该日期的下一个交易日作为start_date
                    if result and result['latest_date']:
                        # 使用原始的start_date（数据库中最新日期）
                        stock_start_date = result['latest_date'].strftime('%Y-%m-%d')
                        logger.info(f"股票{code} 数据库最新日期: {stock_start_date}")
                    else:
                        # 如果数据库中没有该股票的数据，使用全局start_date
                        stock_start_date = start_date
                        logger.info(f"股票{code} 无历史数据，使用起始日期: {stock_start_date}")

                    for freq in minute_frequencies:
                        if freq != 'd':
                            minute_df = self.get_stock_k_data(code, stock_start_date, end_date, frequency=freq)
                            if minute_df is not None:
                                self.save_minute_data_batch(code, minute_df, freq)
                        else:
                            daily_df = self.get_stock_k_data(code, stock_start_date, end_date, frequency=freq)
                            if daily_df is not None:
                                self.save_daily_data_batch(code, daily_df)

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

    @staticmethod
    def clamp(value):
        lower_bound = -9999.9999
        upper_bound = 9999.9999
        return max(lower_bound, min(upper_bound, value))


def main():
    """主函数"""
    # 新数据库配置
    db_config = {
        'host': db_config_["host"],
        'port': db_config_["port"],
        'user': db_config_["user"],
        'password': db_config_["password"],
        'database': db_config_["database"],
    }

    # 创建收集器实例
    collector = BaostockDataCollector(db_config)
    # 执行全量数据收集
    success = collector.collect_all_data(
        # start_date="2020-01-01",  # 从2020年开始拉取
        minute_frequencies=['d']  # 获取多种分钟线数据
    )

    if success:
        logger.info("全量数据收集任务完成")
    else:
        logger.error("全量数据收集任务失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
