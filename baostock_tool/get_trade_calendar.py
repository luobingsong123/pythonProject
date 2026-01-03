# -*- coding: utf-8 -*-
import baostock as bs
import pandas as pd
import pymysql
from datetime import datetime, timedelta
from baostock_tool.utils.logger_utils import setup_logger
from baostock_tool.config import get_db_config, get_log_config

db_config_ = get_db_config()
log_config = get_log_config()
logger = setup_logger(logger_name=__name__,
                   log_level=log_config["log_level"],
                   log_dir=log_config["log_dir"], )


class TradeCalendarManager:
    def __init__(self, db_config=None):
        """
        初始化交易日历管理器
        """
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 3306,
            'user': 'your_username',
            'password': 'your_password',
            'database': 'quant_data',
            'charset': 'utf8mb4'
        }
        
    def connect_database(self):
        """连接数据库"""
        try:
            self.conn = pymysql.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False

    def disconnect_database(self):
        """断开数据库连接"""
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
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
        bs.logout()
        logger.info("Baostock已登出")

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
        将交易日数据保存到数据库
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
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"保存数据到数据库失败: {e}")
            return False

    def get_latest_trade_date(self):
        """
        获取数据库中最新的交易日日期
        """
        try:
            sql = "SELECT MAX(calendar_date) FROM trade_calendar WHERE is_trading_day = 1"
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
            latest_date = result[0] if result[0] else None

            if latest_date:
                logger.info(f"数据库中最新的交易日: {latest_date}")
                # 返回下一个交易日作为开始日期
                next_date = latest_date + timedelta(days=1)
                return next_date.strftime('%Y-%m-%d')
            else:
                logger.info("数据库中无交易日数据，使用默认开始日期")
                return None

        except Exception as e:
            logger.error(f"获取最新交易日失败: {e}")
            return None

    def update_trade_calendar(self, start_date=None, end_date=None):
        """
        更新交易日历数据 - 优化版本：从数据库最新交易日开始
        """
        # 设置结束日期为今天
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # 连接数据库获取最新交易日
        if not self.connect_database():
            return False

        # 获取开始日期：优先使用数据库最新交易日，其次使用传入参数，最后使用默认值
        if start_date is None:
            db_start_date = self.get_latest_trade_date()
            if db_start_date:
                start_date = db_start_date
            else:
                # 如果数据库为空，使用一年前作为开始日期
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        self.disconnect_database()  # 先断开，后面会重新连接

        logger.info(f"开始更新交易日历数据: {start_date} 至 {end_date}")

        # 检查日期范围是否有效
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        if start_dt > end_dt:
            logger.warning("开始日期晚于结束日期，无需更新")
            return True

        if start_dt == end_dt:
            logger.info("开始日期等于结束日期，检查是否需要更新单日数据")

        # 重新连接数据库
        if not self.connect_database():
            return False

        # 登录Baostock
        if not self.login_baostock():
            self.disconnect_database()
            return False

        try:
            df = self.get_trade_dates(start_date, end_date)
            if df is None:
                return False

            result = self.save_to_database(df)
            return result

        finally:
            self.logout_baostock()
            self.disconnect_database()

    def batch_update_history(self, years=10):
        """
        批量更新历史数据 - 保留原有功能
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y-%m-%d')

        logger.info(f"开始批量更新 {years} 年历史数据")
        return self.update_trade_calendar(start_date, end_date)

    def force_update_from_date(self, start_date):
        """
        强制从指定日期开始更新
        """
        logger.info(f"强制从指定日期开始更新: {start_date}")
        return self.update_trade_calendar(start_date=start_date)


def main():
    """主函数示例"""
    db_config = {
        'host': db_config_["host"],
        'port': db_config_["port"],
        'user': db_config_["user"],
        'password': db_config_["password"],
        'database': db_config_["database"],
        'charset': 'utf8mb4'
    }

    manager = TradeCalendarManager(db_config)

    # 智能更新：从数据库最新交易日开始
    success = manager.update_trade_calendar()

    if success:
        print("交易日历数据更新成功！")
    else:
        print("交易日历数据更新失败，请检查日志文件。")

    # 其他更新方式示例：
    # 1. 强制更新特定时间段
    # manager.force_update_from_date("2024-01-01")

    # 2. 批量更新历史数据
    # manager.batch_update_history(years=5)


if __name__ == "__main__":
    main()
