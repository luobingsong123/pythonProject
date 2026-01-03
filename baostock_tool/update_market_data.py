# -*- coding: utf-8 -*-
import baostock as bs
import pandas as pd
import pandas_ta as ta
import pymysql
from datetime import datetime, timedelta
from baostock_tool.utils.logger_utils import setup_logger
from baostock_tool.config import get_db_config, get_log_config
import sys
import time

db_config_ = get_db_config()
log_config = get_log_config()
logger = setup_logger(logger_name=__name__,
                   log_level=log_config["log_level"],
                   log_dir=log_config["log_dir"], )


class MarketDataUpdater:
    def __init__(self, db_config=None):
        """
        初始化市场数据更新器
        """
        self.db_config = db_config or db_config_
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

    def disconnect_database(self):
        """断开数据库连接"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
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

    def get_latest_trade_date(self):
        """
        获取最新交易日历，返回最近一个交易日
        """
        try:
            sql = """
            SELECT calendar_date 
            FROM trade_calendar 
            WHERE is_trading_day = 1 
            ORDER BY calendar_date DESC 
            LIMIT 1
            """
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
            
            if result and result['calendar_date']:
                latest_trade_date = result['calendar_date']
                logger.info(f"最新交易日: {latest_trade_date}")
                return latest_trade_date.strftime('%Y-%m-%d')
            else:
                logger.warning("未找到交易日历数据")
                return None
                
        except Exception as e:
            logger.error(f"获取最新交易日失败: {e}")
            return None

    def get_sh_index_latest_date(self):
        """
        获取上证综合指数日线数据最新日期作为开始日期
        """
        try:
            # 上证综合指数代码为 sh.000001
            sql = """
            SELECT MAX(date) as latest_date 
            FROM daily_k_data 
            WHERE code = 'sh.000001'
            """
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
            
            if result and result['latest_date']:
                latest_date = result['latest_date']
                logger.info(f"上证综合指数最新日线日期: {latest_date}")
                # 返回下一天作为开始日期
                next_date = latest_date + timedelta(days=1)
                return next_date.strftime('%Y-%m-%d')
            else:
                logger.warning("未找到上证综合指数日线数据，使用默认开始日期")
                # 如果没有数据，使用一年前作为开始日期
                return (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                
        except Exception as e:
            logger.error(f"获取上证综合指数最新日期失败: {e}")
            return (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    def get_all_stocks(self, query_date=None):
        """
        获取所有股票基本信息，使用 Baostock API，按代码倒序排列
        """
        if query_date is None:
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
            
            # 过滤有效股票代码并按代码倒序排列
            # 跳过指数代码，只保留股票代码
            valid_stocks = []
            for _, row in df.iterrows():
                code = row['code']
                # 跳过指数代码（如 sh.000001 是指数，但我们仍然保留作为基准）
                if code.startswith(('sh.', 'sz.')):
                    valid_stocks.append({
                        'code': code,
                        'name': row.get('code_name', '')
                    })
            
            # 按代码倒序排列（确保上证综合指数在最后）
            valid_stocks.sort(key=lambda x: x['code'], reverse=True)
            
            logger.info(f"成功获取 {len(valid_stocks)} 只股票基本信息")
            return valid_stocks

        except Exception as e:
            logger.error(f"获取股票列表异常: {e}")
            return None



    def get_stock_k_data(self, code, start_date, end_date, frequency='d'):
        """
        获取股票K线数据
        """
        try:
            if frequency == 'd':
                fields = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST"
            else:
                fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"

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
                logger.info(f"股票{code} 无新的{frequency}线数据")
                return None

            df = pd.DataFrame(data_list, columns=rs.fields)
            logger.info(f"股票{code} 获取到 {len(df)} 条{frequency}线数据")
            return df

        except Exception as e:
            logger.error(f"获取股票{code} {frequency}线数据异常: {e}")
            return None

    def save_daily_data(self, df):
        """
        保存日线数据到数据库
        """
        if df is None or df.empty:
            return False

        try:
            success_count = 0
            for _, row in df.iterrows():
                # 处理空值和类型转换
                volume = float(row['volume']) if row['volume'] else 0
                amount = float(row['amount']) if row['amount'] else 0
                pctChg = float(row['pctChg']) if row['pctChg'] else 0
                peTTM = float(row['peTTM']) if row['peTTM'] else 0
                pbMRQ = float(row['pbMRQ']) if row['pbMRQ'] else 0
                psTTM = float(row['psTTM']) if row['psTTM'] else 0
                pcfNcfTTM = float(row['pcfNcfTTM']) if row['pcfNcfTTM'] else 0
                
                sql = """
                REPLACE INTO daily_k_data 
                (date, code, open, high, low, close, preclose, volume, amount, 
                 adjustflag, turn, tradestatus, pctChg, peTTM, pbMRQ, psTTM, 
                 pcfNcfTTM, isST, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
                
                values = (
                    row['date'], row['code'], float(row['open']), float(row['high']), 
                    float(row['low']), float(row['close']), float(row['preclose']) if row['preclose'] else 0,
                    volume, amount, row['adjustflag'], float(row['turn']) if row['turn'] else 0,
                    row['tradestatus'], pctChg, peTTM, pbMRQ, psTTM, pcfNcfTTM, row['isST']
                )

                self.cursor.execute(sql, values)
                success_count += 1

            self.conn.commit()
            logger.info(f"成功保存 {success_count} 条日线数据")
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"保存日线数据失败: {e}")
            return False

    def save_minute_data(self, df):
        """
        保存分钟线数据到数据库
        """
        if df is None or df.empty:
            return False

        try:
            success_count = 0
            for _, row in df.iterrows():
                volume = float(row['volume']) if row['volume'] else 0
                amount = float(row['amount']) if row['amount'] else 0
                
                sql = """
                REPLACE INTO minute_k_data 
                (date, time, code, open, high, low, close, volume, amount, 
                 adjustflag, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
                
                values = (
                    row['date'], row['time'], row['code'], float(row['open']), 
                    float(row['high']), float(row['low']), float(row['close']),
                    volume, amount, row['adjustflag']
                )

                self.cursor.execute(sql, values)
                success_count += 1

            self.conn.commit()
            logger.info(f"成功保存 {success_count} 条5分钟线数据")
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"保存5分钟线数据失败: {e}")
            return False

    def update_market_data(self):
        """
        更新市场数据的主方法
        """
        logger.info("开始更新市场数据...")
        
        # 连接数据库
        if not self.connect_database():
            return False

        try:
            # 1. 获取最新交易日历作为end_date
            end_date = self.get_latest_trade_date()
            if not end_date:
                logger.error("无法获取最新交易日历")
                return False

            # 2. 获取上证综合指数最新日线数据日期作为start_date
            start_date = self.get_sh_index_latest_date()
            if not start_date:
                logger.error("无法获取开始日期")
                return False

            # 检查日期有效性
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_dt > end_dt:
                logger.info(f"开始日期 {start_date} 晚于结束日期 {end_date}，无需更新")
                return True

            logger.info(f"更新日期范围: {start_date} 至 {end_date}")

            # 3. 获取所有股票信息（按代码倒序）
            stocks = self.get_all_stocks()
            if not stocks:
                logger.error("无法获取股票列表")
                return False

            # 4. 登录Baostock
            if not self.login_baostock():
                return False

            total_stocks = len(stocks)
            processed_count = 0

            # 5. 遍历所有股票，更新数据
            for stock in stocks:
                code = stock['code']
                name = stock['name']
                processed_count += 1
                
                logger.info(f"处理股票 {code} ({name}) [{processed_count}/{total_stocks}]")

                try:
                    # 先获取5分钟数据
                    logger.info(f"获取股票 {code} 5分钟数据...")
                    minute_df = self.get_stock_k_data(code, start_date, end_date, '5')
                    if minute_df is not None:
                        self.save_minute_data(minute_df)

                    # 等待一小段时间避免请求过快
                    time.sleep(0.1)

                    # 再获取日线数据
                    logger.info(f"获取股票 {code} 日线数据...")
                    daily_df = self.get_stock_k_data(code, start_date, end_date, 'd')
                    if daily_df is not None:
                        self.save_daily_data(daily_df)

                    # 等待一小段时间避免请求过快
                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"处理股票 {code} 时发生异常: {e}")
                    continue

            logger.info(f"市场数据更新完成，共处理 {processed_count} 只股票")
            return True

        except Exception as e:
            logger.error(f"更新市场数据过程中发生异常: {e}")
            return False

        finally:
            # 登出Baostock并关闭数据库连接
            self.logout_baostock()
            self.disconnect_database()


def main():
    """
    主函数
    """
    updater = MarketDataUpdater()
    success = updater.update_market_data()
    
    if success:
        logger.info("市场数据更新成功完成")
        sys.exit(0)
    else:
        logger.error("市场数据更新失败")
        sys.exit(1)


if __name__ == "__main__":
    main()