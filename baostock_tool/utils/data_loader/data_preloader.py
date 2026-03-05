"""
数据预加载模块

负责从QuestDB预加载股票历史数据到内存
"""

from typing import Dict, List, Tuple
import pandas as pd
from datetime import timedelta
from utils.data_loader.questdb_client import QuestDBClient
from utils.logger_utils import setup_logger
import config

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"]
)


class DataPreloader:
    """数据预加载器"""

    def __init__(self, questdb_client: QuestDBClient):
        """
        初始化数据预加载器

        Args:
            questdb_client: QuestDB客户端
        """
        self.questdb_client = questdb_client
        self.all_stock_data: Dict[str, pd.DataFrame] = {}  # {stock_code: DataFrame}
        self.stock_info_map: Dict[str, Tuple[str, str]] = {}  # {stock_code: (market, name)}

    def preload_all_stock_data(
        self,
        stock_codes: List[Tuple[str, int, str]],
        start_date: str,
        end_date: str,
        lookback_days: int = 365
    ) -> Dict[str, pd.DataFrame]:
        """
        预加载所有股票的完整历史数据到内存（从QuestDB一次性查询）

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

        logger.info(f"开始从QuestDB预加载股票数据...")
        logger.info(f"  数据时间范围: {data_start_date} 至 {end_date}")
        logger.info(f"  股票数量: {len(stock_codes)}")

        # 保存股票信息映射
        for market, code_int, name in stock_codes:
            self.stock_info_map[str(code_int)] = (market, name)

        # 时序数据库不需要复杂的条件
        query = f"""
        SELECT *
        FROM stock_daily_data
        WHERE 
        date >= '{data_start_date}'
        AND date <= '{end_date}'
        """

        try:
            df = self.questdb_client.query(query)
            logger.info(f"  返回 {len(df)} 行数据")
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return {}

        if df.empty:
            logger.warning("未查询到任何股票数据")
            return {}

        # QuestDB返回的date列可能是timestamp类型，需要处理
        if 'date' in df.columns:
            # 确保date列是日期格式
            if df['date'].dtype == 'object' or str(df['date'].dtype).startswith('datetime'):
                df['date'] = pd.to_datetime(df['date'])
            else:
                # 如果是timestamp类型
                df['date'] = pd.to_datetime(df['date'], unit='s', utc=True).dt.tz_localize(None)

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

        logger.info(f"QuestDB数据预加载完成:")
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

        # 确保索引不带时区（处理UTC时区问题）
        if stock_data.index.tz is not None:
            stock_data = stock_data.tz_localize(None)

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

        # 确保索引不带时区（处理UTC时区问题）
        if stock_data.index.tz is not None:
            stock_data = stock_data.tz_localize(None)

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
