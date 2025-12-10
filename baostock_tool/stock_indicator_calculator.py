import pandas as pd
import numpy as np
import pymysql
from sqlalchemy import create_engine
import talib
from tqdm import tqdm
import time
import warnings
from datetime import datetime, timedelta
from backtest_platform.utils.logger_utils import setup_logger
import sys
import backtest_platform.config
import concurrent.futures
from threading import Lock

db_config_ = backtest_platform.config.get_db_config()
log_config = backtest_platform.config.get_log_config()

logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"], )

warnings.filterwarnings('ignore')


class StockIndicatorCalculator:
    def __init__(self, db_config):
        """
        初始化数据库连接
        db_config: 数据库连接配置字典
        """
        self.db_config = db_config
        self.connection_lock = Lock()  # 数据库连接锁，确保线程安全
        self._create_connection()

    def _create_connection(self):
        """创建数据库连接（线程安全）"""
        with self.connection_lock:
            try:
                self.engine = create_engine(
                    f"mysql+pymysql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}",
                    pool_size=20,  # 增加连接池大小
                    max_overflow=30,  # 增加最大溢出连接数
                    pool_pre_ping=True  # 连接前ping检测
                )
                self.connection = self.engine.connect()
                logger.info("数据库连接成功")
            except Exception as e:
                logger.error(f"数据库连接失败: {e}")
                raise

    def get_all_stock_codes(self):
        """获取所有股票代码列表"""
        query = """
        SELECT DISTINCT market, code_int 
        FROM stock_daily_data 
        WHERE frequency = 'd' 
        ORDER BY market, code_int
        """
        df = pd.read_sql(query, self.connection)
        return list(zip(df['market'], df['code_int']))

    def get_stock_data(self, market, code_int):
        """获取单只股票的完整历史数据"""
        query = f"""
        SELECT date, open, high, low, close, volume, amount, turn, preclose, isST
        FROM stock_daily_data 
        WHERE market = '{market}' AND code_int = {code_int} AND frequency = 'd'
        ORDER BY date ASC
        """
        return pd.read_sql(query, self.connection, parse_dates=['date'])

    def calculate_technical_indicators(self, df):
        """计算所有技术指标"""
        if len(df) < 34:
            return df

        # 价格数据转换为numpy数组
        closes = df['close'].astype(float).values
        highs = df['high'].astype(float).values
        lows = df['low'].astype(float).values
        amount = df['amount'].astype(float).values

        # 修复turn列的处理逻辑
        if 'turn' in df.columns:
            # 确保turn列有有效值，将无效值替换为1
            turn = df['turn'].astype(float).values.copy()
            turn[turn <= 0] = 1.0  # 将小于等于0的值替换为1
        else:
            # 如果turn列不存在，创建全为1的数组
            turn = np.ones(len(df))

        try:
            # MACD指标计算
            macd_dif, macd_dea, macd_hist = talib.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)
            df['macd_dif'] = macd_dif
            df['macd_dea'] = macd_dea
            df['macd_histogram'] = macd_hist

            # 移动平均线
            df['ma_5'] = talib.SMA(closes, timeperiod=5)
            df['ma_8'] = talib.SMA(closes, timeperiod=8)
            df['ma_13'] = talib.SMA(closes, timeperiod=13)
            df['ma_21'] = talib.SMA(closes, timeperiod=21)
            df['ma_34'] = talib.SMA(closes, timeperiod=34)

            # KDJ指标
            df['kdj_k'], df['kdj_d'] = talib.STOCH(highs, lows, closes,
                                                   fastk_period=9, slowk_period=3,
                                                   slowk_matype=0, slowd_period=3, slowd_matype=0)
            df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']

            # RSI指标
            df['rsi_6'] = talib.RSI(closes, timeperiod=6)
            df['rsi_12'] = talib.RSI(closes, timeperiod=12)
            df['rsi_24'] = talib.RSI(closes, timeperiod=24)

            # CCI指标
            df['cci_10'] = talib.CCI(highs, lows, closes, timeperiod=10)
            df['cci_20'] = talib.CCI(highs, lows, closes, timeperiod=20)

            # 涨跌停判断（A股规则）
            df['pct_chg'] = (df['close'] - df['preclose']) / df['preclose'] * 100
            df['is_raising_limit'] = 0

            # ST股涨跌停幅度5%，非ST股10%
            for i in range(1, len(df)):
                if df['isST'].iloc[i] == 1:
                    limit_rate = 0.05
                else:
                    limit_rate = 0.1

                if df['pct_chg'].iloc[i] >= limit_rate * 100:
                    df.loc[df.index[i], 'is_raising_limit'] = 1
                elif df['pct_chg'].iloc[i] <= -limit_rate * 100:
                    df.loc[df.index[i], 'is_raising_limit'] = -1

            # 流动市值计算
            df['close_fcap'] = (amount / turn) / 100

        except Exception as e:
            logger.error(f"指标计算错误: {e}")

        return df

    def update_database_batch(self, market, code_int, df, batch_size=1000):
        """批量更新数据库（线程安全版本）"""
        if df.empty:
            return

        update_columns = [
            'close_fcap', 'is_raising_limit', 'macd_dif', 'macd_dea', 'macd_histogram',
            'ma_5', 'ma_8', 'ma_13', 'ma_21', 'ma_34', 'kdj_k', 'kdj_d', 'kdj_j',
            'rsi_6', 'rsi_12', 'rsi_24', 'cci_10', 'cci_20'
        ]

        # 使用线程锁确保数据库操作安全
        with self.connection_lock:
            try:
                # 重新获取连接（确保线程安全）
                if self.connection.closed:
                    self._create_connection()

                for i in range(0, len(df), batch_size):
                    batch_df = df.iloc[i:i + batch_size].copy()

                    dict_list = []
                    for _, row in batch_df.iterrows():
                        record_dict = {
                            'date': row['date'],
                            'market': market,
                            'code_int': code_int,
                            'frequency': 'd'
                        }
                        for col in update_columns:
                            record_dict[col] = row[col] if pd.notna(row[col]) else None
                        dict_list.append(record_dict)

                    set_clause = ', '.join([f"{col} = VALUES({col})" for col in update_columns])

                    update_query = f"""
                    INSERT INTO stock_daily_data 
                    (date, market, code_int, frequency, {', '.join(update_columns)})
                    VALUES 
                    (:date, :market, :code_int, :frequency, {', '.join([f':{col}' for col in update_columns])})
                    ON DUPLICATE KEY UPDATE
                    {set_clause}
                    """

                    from sqlalchemy import text
                    stmt = text(update_query)

                    chunk_size = 100
                    for j in range(0, len(dict_list), chunk_size):
                        chunk = dict_list[j:j + chunk_size]
                        result = self.connection.execute(stmt, chunk)
                        logger.debug(f"股票 {market}{code_int:06d} 批次更新 {result.rowcount} 行")

                    self.connection.commit()

            except Exception as e:
                logger.error(f"股票 {market}{code_int:06d} 批量更新失败: {e}")
                self.connection.rollback()
                raise

    def process_single_stock(self, stock_info):
        """处理单只股票（用于并发执行）"""
        market, code_int = stock_info
        try:
            # 为每个线程创建独立的数据库连接
            thread_calculator = StockIndicatorCalculator(self.db_config)

            df = thread_calculator.get_stock_data(market, code_int)
            if len(df) > 0:
                df_with_indicators = thread_calculator.calculate_technical_indicators(df)
                thread_calculator.update_database_batch(market, code_int, df_with_indicators, batch_size=500)
                thread_calculator.close_connection()
                return (market, code_int, True, f"成功处理 {len(df)} 行数据")
            else:
                thread_calculator.close_connection()
                return (market, code_int, False, "无数据")

        except Exception as e:
            logger.error(f"处理股票 {market}{code_int:06d} 时出错: {e}")
            return (market, code_int, False, str(e))

    def process_all_stocks_concurrent(self, max_workers=10, test_mode=False):
        """并发处理所有股票数据"""
        stock_codes = self.get_all_stock_codes()
        logger.info(f"找到 {len(stock_codes)} 只股票需要处理")

        if test_mode:
            stock_codes = stock_codes[:50]  # 测试模式减少股票数量
            logger.info(f"测试模式：只处理前 {len(stock_codes)} 只股票")

        successful = 0
        failed = 0

        # 使用线程池并发处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_stock = {
                executor.submit(self.process_single_stock, stock): stock
                for stock in stock_codes
            }

            # 使用tqdm显示进度
            with tqdm(total=len(stock_codes), desc="并发处理进度") as pbar:
                for future in concurrent.futures.as_completed(future_to_stock):
                    stock = future_to_stock[future]
                    market, code_int = stock

                    try:
                        result = future.result()
                        market, code_int, success, message = result

                        if success:
                            successful += 1
                            logger.info(f"✓ {market}{code_int:06d} - {message}")
                        else:
                            failed += 1
                            logger.warning(f"✗ {market}{code_int:06d} - {message}")

                    except Exception as exc:
                        failed += 1
                        logger.error(f"✗ {market}{code_int:06d} - 异常: {exc}")

                    pbar.update(1)
                    pbar.set_description(f"处理进度 [成功: {successful} 失败: {failed}]")

        logger.info(f"\n处理完成！成功: {successful}, 失败: {failed}, 总计: {len(stock_codes)}")

    def process_all_stocks(self, batch_size=1000, test_mode=False):
        """保留原有串行处理方式（兼容性）"""
        # 默认使用并发处理，可以通过参数控制
        return self.process_all_stocks_concurrent(max_workers=10, test_mode=test_mode)

    def close_connection(self):
        """关闭数据库连接"""
        with self.connection_lock:
            if hasattr(self, 'connection') and self.connection:
                self.connection.close()
            if hasattr(self, 'engine') and self.engine:
                self.engine.dispose()
        logger.debug("数据库连接已关闭")


def main():
    # 数据库配置
    db_config = {
        'host': db_config_["host"],
        'port': db_config_["port"],
        'user': db_config_["user"],
        'password': db_config_["password"],
        'database': db_config_["database"],
        'charset': 'utf8mb4'
    }

    # 创建计算器实例
    calculator = None
    try:
        calculator = StockIndicatorCalculator(db_config)

        # 使用并发处理（可调整max_workers数量）
        calculator.process_all_stocks_concurrent(max_workers=15, test_mode=False)

    except Exception as e:
        logger.error(f"程序执行出错: {e}")
    finally:
        if calculator:
            calculator.close_connection()


if __name__ == "__main__":
    # 安装依赖：pip install pandas numpy pymysql sqlalchemy talib-binary tqdm
    main()