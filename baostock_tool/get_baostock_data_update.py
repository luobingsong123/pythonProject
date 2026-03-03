# -*- coding: utf-8 -*-
import baostock as bs
import pandas as pd
import pymysql
from datetime import datetime, timedelta
from baostock_tool.utils.logger_utils import setup_logger
from baostock_tool.config import get_db_config, get_log_config
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

db_config_ = get_db_config()
log_config = get_log_config()
logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"],)

# 全局参数：最新交易日
LATEST_TRADING_DAY = None

# 复权状态常量
ADJUSTFLAG_NONE = 3      # 不复权
ADJUSTFLAG_FRONT = 2     # 前复权
ADJUSTFLAG_BACK = 1      # 后复权

# baostock全局锁（baostock可能不是线程安全的）
_baostock_lock = threading.Lock()


def create_db_connection(db_config):
    """创建独立的数据库连接"""
    conn = pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn


def parse_stock_code(full_code):
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


def get_stock_k_data_safe(code, start_date, end_date, frequency='d', fields=None, adjustflag="3"):
    """
    线程安全的获取股票K线数据
    """
    if fields is None:
        if frequency == 'd':
            fields = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST"
        else:
            fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"

    with _baostock_lock:
        rs = bs.query_history_k_data_plus(
            code=code,
            fields=fields,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag=adjustflag
        )

        if rs.error_code != '0':
            return None

        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return None

        df = pd.DataFrame(data_list, columns=rs.fields)
        return df


def get_adjust_factor_safe(code, start_date, end_date):
    """
    线程安全的获取复权因子
    """
    with _baostock_lock:
        rs = bs.query_adjust_factor(code=code, start_date=start_date, end_date=end_date)

        if rs.error_code != '0':
            return None

        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return None

        df = pd.DataFrame(data_list, columns=rs.fields)
        return df


def clamp(value):
    lower_bound = -9999.9999
    upper_bound = 9999.9999
    return max(lower_bound, min(upper_bound, value))


class BaostockDataCollector:
    def __init__(self, db_config, max_workers=50):
        """
        初始化数据库连接配置

        参数:
            db_config: 数据库配置
            max_workers: 最大并行线程数，默认20
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        self.max_workers = max_workers
        self._progress_lock = threading.Lock()
        self._completed_count = 0
        self._failed_count = 0

    def connect_database(self):
        """连接MySQL数据库（主线程用）"""
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

    def create_adjust_factor_table(self):
        """创建复权因子表（如果不存在）"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS stock_adjust_factor (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            date DATE NOT NULL COMMENT '日期',
            market VARCHAR(2) NOT NULL COMMENT '市场代码：sh=上海, sz=深圳', 
            code_int INT(10) UNSIGNED NOT NULL COMMENT '6位数字股票代码',
            fore_adjust_factor DECIMAL(20,10) DEFAULT 1.0 COMMENT '前复权因子',
            back_adjust_factor DECIMAL(20,10) DEFAULT 1.0 COMMENT '后复权因子',
            dividend_rate DECIMAL(10,6) DEFAULT NULL COMMENT '除权除息信息',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
            UNIQUE KEY uk_date_market_code (date, market, code_int),
            KEY idx_market_code (market, code_int),
            KEY idx_date (date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票复权因子表'
        """
        try:
            self.cursor.execute(create_sql)
            self.conn.commit()
            logger.info("复权因子表创建/检查完成")
            return True
        except Exception as e:
            logger.error(f"创建复权因子表失败: {e}")
            return False

    def get_trade_dates(self, start_date, end_date):
        """获取交易日数据"""
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

    def save_trade_dates_to_database(self, df):
        """将交易日数据保存到数据库"""
        if df is None or df.empty:
            logger.warning("无数据可保存")
            return False

        try:
            for _, row in df.iterrows():
                sql = """
                REPLACE INTO trade_calendar (calendar_date, is_trading_day)
                VALUES (%s, %s)
                """
                values = (row['calendar_date'], row['is_trading_day'])
                self.cursor.execute(sql, values)

            self.conn.commit()
            logger.info(f"成功保存交易日数据到数据库")

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
        """获取所有股票基本信息"""
        global LATEST_TRADING_DAY

        if query_date is None:
            if LATEST_TRADING_DAY:
                query_date = LATEST_TRADING_DAY.strftime("%Y-%m-%d")
            else:
                query_date = datetime.now().strftime("%Y-%m-%d")

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
        """保存股票基本信息"""
        if stock_df is None or stock_df.empty:
            return False

        try:
            for _, row in stock_df.iterrows():
                full_code = row['code']
                code_name = row.get('code_name', '')

                try:
                    market, code_int = parse_stock_code(full_code)
                except ValueError:
                    continue

                replace_sql = """
                REPLACE INTO stock_basic_info 
                (market, code_int, name, list_date, created_at, updated_at) 
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """

                list_date = datetime.now().strftime("%Y-%m-%d")
                self.cursor.execute(replace_sql, (market, code_int, code_name, list_date))

            self.conn.commit()
            logger.info(f"股票基本信息保存完成")
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"保存股票基本信息异常: {e}")
            return False

    def get_stock_start_dates(self, stocks_to_process, default_start_date):
        """批量查询所有股票的起始日期"""
        stock_start_dates = {}
        for code in stocks_to_process:
            market, code_int = parse_stock_code(code)
            sql = """
            SELECT MAX(date) AS latest_date
            FROM stock_daily_data
            WHERE market = %s AND code_int = %s
            """
            self.cursor.execute(sql, (market, code_int))
            result = self.cursor.fetchone()

            if result and result['latest_date']:
                stock_start_dates[code] = result['latest_date'].strftime('%Y-%m-%d')
            else:
                stock_start_dates[code] = default_start_date

        return stock_start_dates

    def process_single_stock(self, code, start_date, end_date, minute_frequencies, idx, total_stocks):
        """
        处理单只股票的完整流程（线程独立执行）
        每个线程创建独立的数据库连接
        """
        conn = None
        cursor = None

        try:
            # 1. 创建独立的数据库连接
            conn = create_db_connection(self.db_config)
            cursor = conn.cursor()

            logger.info(f"处理股票 [{idx + 1}/{total_stocks}]: {code}")

            # 2. 检查是否有新的除权事件
            need_adjust, has_new_factor, factor_df = self.check_need_adjust_with_conn(
                cursor, code, start_date, end_date
            )

            # 3. 如果有新的复权因子，触发全量重建
            if has_new_factor:
                logger.warning(f"股票{code} 检测到新的除权事件，触发全量重建")
                self.rebuild_stock_all_data_with_conn(cursor, conn, code, end_date)
            else:
                # 4. 获取日线数据
                daily_df = get_stock_k_data_safe(code, start_date, end_date, frequency='d')

                if daily_df is not None and not daily_df.empty:
                    # 5. 获取最新的复权因子
                    latest_factor = self.get_latest_adjust_factor_with_conn(cursor, code)

                    # 6. 应用前复权
                    if latest_factor != 1.0:
                        daily_df = self.apply_front_adjust(daily_df, latest_factor=latest_factor)

                    # 7. 保存日线数据
                    self.save_daily_data_with_conn(cursor, conn, code, daily_df, ADJUSTFLAG_FRONT)

            # 8. 获取并保存分钟线数据
            for freq in minute_frequencies:
                if freq != 'd':
                    minute_df = get_stock_k_data_safe(code, start_date, end_date, frequency=freq)
                    if minute_df is not None and not minute_df.empty:
                        self.save_minute_data_with_conn(cursor, conn, code, minute_df, freq)

            return True

        except Exception as e:
            logger.error(f"处理股票{code}异常: {e}")
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def check_need_adjust_with_conn(self, cursor, code, start_date, end_date):
        """
        检查股票是否需要复权处理（使用传入的cursor）
        返回: (need_adjust, has_new_factor, factor_df)
        """
        try:
            factor_df = get_adjust_factor_safe(code, start_date, end_date)

            if factor_df is None or factor_df.empty:
                return False, False, None

            market, code_int = parse_stock_code(code)

            sql = """
            SELECT COUNT(*) as cnt FROM stock_adjust_factor 
            WHERE market = %s AND code_int = %s AND date >= %s AND date <= %s
            """
            cursor.execute(sql, (market, code_int, start_date, end_date))
            result = cursor.fetchone()
            db_count = result['cnt'] if result else 0

            has_new_factor = len(factor_df) > db_count

            return True, has_new_factor, factor_df

        except Exception as e:
            logger.error(f"检查复权需求异常: {e}")
            return False, False, None

    def get_latest_adjust_factor_with_conn(self, cursor, code):
        """获取最新复权因子（使用传入的cursor）"""
        try:
            market, code_int = parse_stock_code(code)

            sql = """
            SELECT fore_adjust_factor 
            FROM stock_adjust_factor 
            WHERE market = %s AND code_int = %s
            ORDER BY date DESC
            LIMIT 1
            """
            cursor.execute(sql, (market, code_int))
            result = cursor.fetchone()

            if result:
                return float(result['fore_adjust_factor'])
            return 1.0

        except Exception as e:
            logger.error(f"获取最新复权因子异常: {e}")
            return 1.0

    def save_adjust_factor_with_conn(self, cursor, conn, code, factor_df):
        """保存复权因子（使用传入的连接）"""
        if factor_df is None or factor_df.empty:
            return False

        try:
            market, code_int = parse_stock_code(code)

            data_tuples = []
            for _, row in factor_df.iterrows():
                if 'dividOperateDate' in row:
                    date = row['dividOperateDate']
                elif 'tradeDate' in row:
                    date = row['tradeDate']
                elif 'date' in row:
                    date = row['date']
                else:
                    continue

                fore_factor = float(row['foreAdjustFactor']) if 'foreAdjustFactor' in row and row['foreAdjustFactor'] != '' and pd.notna(row['foreAdjustFactor']) else 1.0
                back_factor = float(row['backAdjustFactor']) if 'backAdjustFactor' in row and row['backAdjustFactor'] != '' and pd.notna(row['backAdjustFactor']) else 1.0
                dividend_rate = float(row['dividendRate']) if 'dividendRate' in row and row['dividendRate'] != '' and pd.notna(row.get('dividendRate', '')) else None

                data_tuples.append((date, market, code_int, fore_factor, back_factor, dividend_rate))

            insert_sql = """
            REPLACE INTO stock_adjust_factor 
            (date, market, code_int, fore_adjust_factor, back_adjust_factor, dividend_rate, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """

            cursor.executemany(insert_sql, data_tuples)
            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"保存复权因子异常: {e}")
            return False

    def rebuild_stock_all_data_with_conn(self, cursor, conn, code, end_date, full_start_date='1999-01-01'):
        """重建股票历史数据（使用传入的连接）"""
        try:
            market, code_int = parse_stock_code(code)
            logger.info(f"股票{code} 开始重建历史数据...")

            # 删除旧数据
            delete_sql = "DELETE FROM stock_daily_data WHERE market = %s AND code_int = %s"
            cursor.execute(delete_sql, (market, code_int))

            # 获取并保存复权因子
            factor_df = get_adjust_factor_safe(code, full_start_date, end_date)
            if factor_df is not None and not factor_df.empty:
                self.save_adjust_factor_with_conn(cursor, conn, code, factor_df)

            # 获取最新复权因子
            latest_factor = self.get_latest_adjust_factor_with_conn(cursor, code)

            # 获取日线数据
            daily_df = get_stock_k_data_safe(code, full_start_date, end_date, frequency='d')

            if daily_df is not None and not daily_df.empty:
                if latest_factor != 1.0:
                    daily_df = self.apply_front_adjust(daily_df, latest_factor=latest_factor)

                self.save_daily_data_with_conn(cursor, conn, code, daily_df, ADJUSTFLAG_FRONT)
                logger.info(f"股票{code} 历史数据重建完成，共 {len(daily_df)} 条")
                return True

            return False

        except Exception as e:
            conn.rollback()
            logger.error(f"重建股票{code}历史数据异常: {e}")
            return False

    def apply_front_adjust(self, daily_df, latest_factor=None):
        """应用前复权"""
        if daily_df is None or daily_df.empty:
            return daily_df

        if latest_factor is None:
            return daily_df

        try:
            df = daily_df.copy()
            df['date'] = pd.to_datetime(df['date']).dt.date

            # 向量化操作，比循环快很多
            for col in ['open', 'high', 'low', 'close', 'preclose']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) * latest_factor

            return df

        except Exception as e:
            logger.error(f"应用前复权异常: {e}")
            return daily_df

    def save_daily_data_with_conn(self, cursor, conn, code, daily_df, adjustflag=ADJUSTFLAG_FRONT):
        """保存日线数据（使用传入的连接）"""
        if daily_df is None or daily_df.empty:
            return False

        try:
            market, code_int = parse_stock_code(code)
            data_tuples = []

            for _, row in daily_df.iterrows():
                date = row['date']
                open_price = float(row['open']) if pd.notna(row.get('open')) and row['open'] != '' else 0
                high = float(row['high']) if pd.notna(row.get('high')) and row['high'] != '' else 0
                low = float(row['low']) if pd.notna(row.get('low')) and row['low'] != '' else 0
                close = float(row['close']) if pd.notna(row.get('close')) and row['close'] != '' else 0
                preclose = float(row['preclose']) if pd.notna(row.get('preclose')) and row['preclose'] != '' else 0
                volume = int(float(row['volume'])) if pd.notna(row.get('volume')) and row['volume'] != '' else 0
                amount = float(row['amount']) if pd.notna(row.get('amount')) and row['amount'] != '' else 0
                turn = float(row['turn']) if pd.notna(row.get('turn')) and row['turn'] != '' else 0
                pctchg = clamp(float(row['pctChg']) if pd.notna(row.get('pctChg')) and row['pctChg'] != '' else 0)
                peTTM = clamp(float(row['peTTM']) if pd.notna(row.get('peTTM')) and row['peTTM'] != '' else 0)
                pbMRQ = clamp(float(row['pbMRQ']) if pd.notna(row.get('pbMRQ')) and row['pbMRQ'] != '' else 0)
                psTTM = clamp(float(row['psTTM']) if pd.notna(row.get('psTTM')) and row['psTTM'] != '' else 0)
                pcfNcfTTM = clamp(float(row['pcfNcfTTM']) if pd.notna(row.get('pcfNcfTTM')) and row['pcfNcfTTM'] != '' else 0)
                tradestatus = 1 if row.get('tradestatus', '1') == '1' else 0
                isst = 1 if row.get('isST', '0') == '1' else 0

                data_tuples.append((
                    date, market, code_int, 'd', open_price, high, low, close, preclose,
                    volume, amount, adjustflag, turn, tradestatus, pctchg, peTTM, pbMRQ, psTTM, pcfNcfTTM, isst
                ))

            insert_sql = """
            REPLACE INTO stock_daily_data 
            (date, market, code_int, frequency, open, high, low, close, preclose, volume, amount, 
             adjustflag, turn, tradestatus, pctChg, peTTM, pbMRQ, psTTM, pcfNcfTTM, isST, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.executemany(insert_sql, data_tuples)
            conn.commit()
            logger.debug(f"股票{code} 日线数据保存 {len(data_tuples)} 条")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"保存日线数据异常: {e}")
            return False

    def save_minute_data_with_conn(self, cursor, conn, code, minute_df, frequency):
        """保存分钟线数据（使用传入的连接）"""
        if minute_df is None or minute_df.empty:
            return False

        try:
            market, code_int = parse_stock_code(code)

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

            insert_sql = """
            REPLACE INTO stock_minute_data 
            (date, time, market, code_int, frequency, open, high, low, close, volume, amount, 
             adjustflag, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """

            cursor.executemany(insert_sql, data_tuples)
            conn.commit()
            logger.debug(f"股票{code} {frequency}分钟线数据保存 {len(data_tuples)} 条")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"保存分钟线数据异常: {e}")
            return False

    def collect_all_data(self, minute_frequencies=['5']):
        """
        主函数：收集所有数据（真正的并行处理）
        """
        # 1. 登录Baostock
        if not self.login_baostock():
            return False

        # 2. 连接数据库（主线程用）
        if not self.connect_database():
            self.logout_baostock()
            return False

        # 3. 创建复权因子表
        self.create_adjust_factor_table()

        # 4. 确定时间范围
        sql = "SELECT MAX(DATE) AS latest_date FROM stock_daily_data WHERE code_int = 399998"
        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        if result['latest_date']:
            start_date = result['latest_date'].strftime('%Y-%m-%d')
        else:
            start_date = '2000-01-01'

        global LATEST_TRADING_DAY

        now = datetime.now()
        current_time = now.time()
        target_time = datetime.strptime("18:30", "%H:%M").time()

        if current_time < target_time:
            end_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            end_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"增量数据收集，时间范围: {start_date} 到 {end_date}")

        # 5. 获取并保存交易日
        try:
            df = self.get_trade_dates(start_date, end_date)
            if df is None:
                return False
            self.save_trade_dates_to_database(df)

            if LATEST_TRADING_DAY:
                end_date = LATEST_TRADING_DAY.strftime("%Y-%m-%d")
                logger.info(f"使用最新交易日: {end_date}")
        except Exception as e:
            logger.error(f"保存交易日数据异常: {e}")

        try:
            # 6. 获取股票列表
            logger.info("获取股票基本信息...")
            stock_df = self.get_all_stocks()
            if stock_df is None:
                return False

            self.save_stock_basic_info(stock_df)

            # 7. 筛选股票
            stocks_to_process = [
                code for code in stock_df['code']
                if code.startswith(('sh.', 'sz.'))
            ]

            logger.info(f"需要处理 {len(stocks_to_process)} 只股票，并行线程数: {self.max_workers}")

            # 8. 批量查询起始日期
            stock_start_dates = self.get_stock_start_dates(stocks_to_process, start_date)

            # 9. 并行处理所有股票
            total_stocks = len(stocks_to_process)
            self._completed_count = 0
            self._failed_count = 0

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_code = {
                    executor.submit(
                        self.process_single_stock,
                        code,
                        stock_start_dates[code],
                        end_date,
                        minute_frequencies,
                        idx,
                        total_stocks
                    ): code
                    for idx, code in enumerate(stocks_to_process)
                }

                for future in as_completed(future_to_code):
                    code = future_to_code[future]
                    try:
                        success = future.result()
                        with self._progress_lock:
                            if success:
                                self._completed_count += 1
                            else:
                                self._failed_count += 1

                            # 每100只股票输出进度
                            total_done = self._completed_count + self._failed_count
                            if total_done % 100 == 0:
                                logger.info(f"进度: {total_done}/{total_stocks} (成功: {self._completed_count}, 失败: {self._failed_count})")

                    except Exception as e:
                        with self._progress_lock:
                            self._failed_count += 1
                        logger.error(f"股票{code}处理异常: {e}")

            logger.info(f"数据收集完成: 成功 {self._completed_count}, 失败 {self._failed_count}")
            return True

        except Exception as e:
            logger.error(f"数据收集过程异常: {e}")
            return False

        finally:
            self.close_database()
            self.logout_baostock()


def main():
    """主函数"""
    db_config = {
        'host': db_config_["host"],
        'port': db_config_["port"],
        'user': db_config_["user"],
        'password': db_config_["password"],
        'database': db_config_["database"],
    }

    collector = BaostockDataCollector(db_config, max_workers=50)
    success = collector.collect_all_data(minute_frequencies=['d'])

    if success:
        logger.info("数据收集任务完成")
    else:
        logger.error("数据收集任务失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
