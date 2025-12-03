import pandas as pd
import numpy as np
import pymysql
from sqlalchemy import create_engine
import talib        # pip install TA-Lib
from tqdm import tqdm
import time
import warnings
from datetime import datetime, timedelta
from baostock_tool.utils.logger_utils import setup_logger
import sys
import baostock_tool.config

db_config_ = baostock_tool.config.get_db_config()
log_config = baostock_tool.config.get_log_config()

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
        try:
            self.engine = create_engine(
                f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            )
            self.connection = self.engine.connect()
            logger.info("数据库连接成功")
        except Exception as e:
            logger.info(f"数据库连接失败: {e}")
            raise

    def get_all_stock_codes(self):
        """获取所有股票代码列表[3](@ref)"""
        query = """
        SELECT DISTINCT market, code_int 
        FROM stock_daily_data 
        WHERE frequency = 'd' 
        ORDER BY market, code_int
        """
        df = pd.read_sql(query, self.connection)
        return list(zip(df['market'], df['code_int']))

    def get_stock_data(self, market, code_int):
        """获取单只股票的完整历史数据[6](@ref)"""
        query = f"""
        SELECT date, open, high, low, close, volume, amount, turn, preclose, isST
        FROM stock_daily_data 
        WHERE market = '{market}' AND code_int = {code_int} AND frequency = 'd'
        ORDER BY date ASC
        """
        return pd.read_sql(query, self.connection, parse_dates=['date'])

    def calculate_technical_indicators(self, df):
        """计算所有技术指标"""
        if len(df) < 34:  # 最长指标需要34日数据
            return df

        # 价格数据转换为numpy数组
        closes = df['close'].astype(float).values
        highs = df['high'].astype(float).values
        lows = df['low'].astype(float).values
        # volumes = df['volume'].astype(float).values
        turn = df['turn'].astype(float).values if 'turn' in df.columns and df['turn'].astype(float).values > 0 else 1
        amount = df['amount'].astype(float).values

        try:
            # MACD指标计算[1](@ref)
            macd_dif, macd_dea, macd_hist = talib.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)
            df['macd_dif'] = macd_dif
            df['macd_dea'] = macd_dea
            df['macd_histogram'] = macd_hist

            # 移动平均线[2](@ref)
            df['ma_5'] = talib.SMA(closes, timeperiod=5)
            df['ma_8'] = talib.SMA(closes, timeperiod=8)
            df['ma_13'] = talib.SMA(closes, timeperiod=13)
            df['ma_21'] = talib.SMA(closes, timeperiod=21)
            df['ma_34'] = talib.SMA(closes, timeperiod=34)

            # KDJ指标[4](@ref)
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

            # 涨跌停判断（A股规则）[7](@ref)
            df['pct_chg'] = (df['close'] - df['preclose']) / df['preclose'] * 100
            df['is_raising_limit'] = 0  # 默认值

            # ST股涨跌停幅度5%，非ST股10%
            for i in range(1, len(df)):
                if df['isST'].iloc[i] == 1:  # ST股
                    limit_rate = 0.05
                else:  # 非ST股
                    limit_rate = 0.1

                if df['pct_chg'].iloc[i] >= limit_rate * 100:  # 涨停
                    df.loc[df.index[i], 'is_raising_limit'] = 1
                elif df['pct_chg'].iloc[i] <= -limit_rate * 100:  # 跌停
                    df.loc[df.index[i], 'is_raising_limit'] = -1

            # 流动市值计算（需要流通股本数据，这里用总市值替代）
            # 注意：实际应用中需要获取流通股本数据
            df['close_fcap'] =(amount / turn)/100   # 简化计算

        except Exception as e:
            logger.info(f"指标计算错误: {e}")

        return df

    def update_database_batch(self, market, code_int, df, batch_size=1000):
        if df.empty:
            return

        update_columns = [
            'close_fcap', 'is_raising_limit', 'macd_dif', 'macd_dea', 'macd_histogram',
            'ma_5', 'ma_8', 'ma_13', 'ma_21', 'ma_34', 'kdj_k', 'kdj_d', 'kdj_j',
            'rsi_6', 'rsi_12', 'rsi_24', 'cci_10', 'cci_20'
        ]

        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i + batch_size].copy()

            # 构建字典列表（SQLAlchemy 2.0要求格式）
            dict_list = []
            for _, row in batch_df.iterrows():
                record_dict = {
                    'date': row['date'],
                    'market': market,
                    'code_int': code_int,
                    'frequency': 'd'
                }
                # 添加技术指标字段
                for col in update_columns:
                    record_dict[col] = row[col] if pd.notna(row[col]) else None
                dict_list.append(record_dict)

            # 构建ON DUPLICATE KEY UPDATE子句
            set_clause = ', '.join([f"{col} = VALUES({col})" for col in update_columns])

            update_query = f"""
            INSERT INTO stock_daily_data 
            (date, market, code_int, frequency, {', '.join(update_columns)})
            VALUES 
            (:date, :market, :code_int, :frequency, {', '.join([f':{col}' for col in update_columns])})
            ON DUPLICATE KEY UPDATE
            {set_clause}
            """
            try:
                # 使用字典列表格式执行（SQLAlchemy 2.0兼容）
                from sqlalchemy import text
                stmt = text(update_query)
                # 分批执行，避免参数过多
                chunk_size = 100  # 每批100条记录
                for j in range(0, len(dict_list), chunk_size):
                    chunk = dict_list[j:j + chunk_size]

                    # 使用connection的execute方法，传递字典列表
                    result = self.connection.execute(stmt, chunk)
                    logger.info(f"批次 {i // batch_size + 1}.{j // chunk_size + 1} 更新 {result.rowcount} 行")

                # 提交事务
                self.connection.commit()

            except Exception as e:
                logger.info(f"批量更新失败: {e}")
                # 确保在异常时回滚
                self.connection.rollback()
                raise

    def process_all_stocks(self, batch_size=1000, test_mode=False):
        """处理所有股票数据[3](@ref)"""
        stock_codes = self.get_all_stock_codes()
        logger.info(f"找到 {len(stock_codes)} 只股票需要处理")

        if test_mode:
            stock_codes = stock_codes[600:610]  # 测试模式下只处理10只股票
            logger.info(f"测试模式：只处理前 {len(stock_codes)} 只股票")

        processed = 0
        successful = 0

        with tqdm(total=len(stock_codes), desc="处理进度") as pbar:
            for market, code_int in stock_codes:
                try:
                    # 获取股票数据
                    df = self.get_stock_data(market, code_int)
                    logger.info(f"\n处理股票 {market}{code_int:06d}，数据行数: {len(df)}")
                    if len(df) > 0:
                        # 计算技术指标
                        df_with_indicators = self.calculate_technical_indicators(df)

                        # 更新数据库
                        self.update_database_batch(market, code_int, df_with_indicators, batch_size)

                        successful += 1

                    processed += 1
                    pbar.set_description(f"处理进度 [{market}{code_int:06d}]")
                    pbar.update(1)

                    # 短暂休眠，避免数据库压力过大
                    time.sleep(0.01)

                except Exception as e:
                    logger.info(f"\n处理股票 {market}{code_int:06d} 时出错, 可能是单个股票已经处理完成: {e}")
                    processed += 1
                    pbar.update(1)
                    continue

        logger.info(f"\n处理完成！成功处理 {successful}/{processed} 只股票")

    def close_connection(self):
        """关闭数据库连接[4](@ref)"""
        if self.connection:
            self.connection.close()
        if self.engine:
            self.engine.dispose()
        logger.info("数据库连接已关闭")


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

        # 开始处理（测试模式设置为True，正式运行改为False）
        calculator.process_all_stocks(batch_size=500, test_mode=False)

    except Exception as e:
        logger.info(f"程序执行出错: {e}")
    finally:
        if calculator:
            calculator.close_connection()


if __name__ == "__main__":
    # 安装依赖：pip install pandas numpy pymysql sqlalchemy talib-binary tqdm
    main()