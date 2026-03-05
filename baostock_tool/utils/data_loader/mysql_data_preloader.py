"""
MySQL数据预加载模块

负责从MySQL预加载股票历史数据到内存
"""

from typing import Dict, List, Tuple
import pandas as pd
from datetime import timedelta
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from utils.logger_utils import setup_logger
import config

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"]
)


class MySQLDataPreloader:
    """MySQL数据预加载器"""

    def __init__(self):
        """初始化MySQL数据预加载器"""
        self.all_stock_data: Dict[str, pd.DataFrame] = {}  # {stock_code: DataFrame}
        self.stock_info_map: Dict[str, Tuple[str, str]] = {}  # {stock_code: (market, name)}
        self.engine = self._create_engine()

    def _create_engine(self):
        """创建MySQL连接引擎"""
        db_config = config.get_db_config()
        db_url = URL.create(
            drivername="mysql+pymysql",
            username=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"]
        )
        return create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)

    def preload_all_stock_data(
        self,
        stock_codes: List[Tuple[str, int, str]],
        start_date: str,
        end_date: str,
        lookback_days: int = 365
    ) -> Dict[str, pd.DataFrame]:
        """
        预加载所有股票的完整历史数据到内存（从MySQL一次性查询）

        Args:
            stock_codes: 股票代码列表 [(market, code_int, name), ...]
            start_date: 回测开始日期
            end_date: 回测结束日期
            lookback_days: 历史数据回溯天数

        Returns:
            dict: {stock_code: DataFrame}
        """
        if not stock_codes:
            return {}

        # 计算数据起始日期（向前推lookback_days天）
        data_start_date = (pd.to_datetime(start_date) - timedelta(days=lookback_days)).strftime('%Y-%m-%d')

        logger.info(f"开始从MySQL预加载股票数据...")
        logger.info(f"  数据时间范围: {data_start_date} 至 {end_date}")
        logger.info(f"  股票数量: {len(stock_codes)}")

        # 保存股票信息映射
        for market, code_int, name in stock_codes:
            self.stock_info_map[str(code_int)] = (market, name)

        # 构建股票代码条件
        conditions = []
        for market, code_int, name in stock_codes:
            conditions.append(f"(market = '{market}' AND code_int = {code_int})")
        where_clause = " OR ".join(conditions)

        query = f"""
        SELECT market, code_int, date, open, high, low, close, volume, amount,
               pctChg, peTTM, psTTM, pcfNcfTTM, pbMRQ
        FROM stock_daily_data
        WHERE ({where_clause})
          AND frequency = 'd'
          AND date >= '{data_start_date}'
          AND date <= '{end_date}'
        ORDER BY code_int, date
        """

        try:
            df = pd.read_sql(query, self.engine)
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return {}

        if df.empty:
            logger.warning("未查询到任何股票数据")
            return {}

        df['date'] = pd.to_datetime(df['date'])

        # 按股票分组
        result = {}
        for (market, code_int), group in df.groupby(['market', 'code_int']):
            stock_code = str(code_int)
            group = group.sort_values('date')
            group.set_index('date', inplace=True)
            result[stock_code] = group

        self.all_stock_data = result

        # 统计信息
        total_rows = len(df)
        total_stocks = len(result)
        avg_rows_per_stock = total_rows / total_stocks if total_stocks > 0 else 0

        logger.info(f"MySQL数据预加载完成:")
        logger.info(f"  总数据行数: {total_rows:,}")
        logger.info(f"  股票数量: {total_stocks}")
        logger.info(f"  平均每只股票数据行数: {avg_rows_per_stock:.0f}")
        logger.info(f"  内存估算: ~{total_rows * 0.001:.1f} MB")

        return result

    def get_stock_data_up_to_date(self, stock_code: str, current_date: str) -> pd.DataFrame:
        """
        从预加载数据中获取指定日期之前的历史数据

        Args:
            stock_code: 股票代码
            current_date: 当前日期

        Returns:
            DataFrame: 截止到当前日期的历史数据
        """
        if stock_code not in self.all_stock_data:
            return None

        stock_data = self.all_stock_data[stock_code]
        current_date_dt = pd.to_datetime(current_date)

        # 筛选截止到当前日期的数据
        return stock_data[stock_data.index <= current_date_dt]

    def get_stock_data_on_date(self, stock_code: str, current_date: str) -> pd.Series:
        """
        从预加载数据中获取指定日期的单只股票数据

        Args:
            stock_code: 股票代码
            current_date: 当前日期

        Returns:
            Series: 当日数据
        """
        if stock_code not in self.all_stock_data:
            return None

        stock_data = self.all_stock_data[stock_code]
        current_date_dt = pd.to_datetime(current_date)

        if current_date_dt not in stock_data.index:
            return None

        return stock_data.loc[current_date_dt]

    def get_stock_info(self, stock_code: str) -> Tuple[str, str]:
        """
        获取股票信息

        Args:
            stock_code: 股票代码

        Returns:
            Tuple[str, str]: (market, name)
        """
        return self.stock_info_map.get(stock_code, ('', ''))

    def clear(self) -> None:
        """清空预加载数据"""
        self.all_stock_data.clear()
        self.stock_info_map.clear()
