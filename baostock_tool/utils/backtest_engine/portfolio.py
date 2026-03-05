"""
持仓管理模块

负责持仓信息的管理和资产计算
"""

from typing import Dict, Optional
import pandas as pd
from utils.strategies.base_strategy import Position
from utils.logger_utils import setup_logger
import config

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"]
)


class PortfolioManager:
    """持仓管理类"""

    def __init__(self):
        """初始化持仓管理器"""
        self.positions: Dict[str, Position] = {}  # {stock_code: Position}

    def add_position(self, stock_code: str, position: Position) -> None:
        """
        添加持仓

        Args:
            stock_code: 股票代码
            position: 持仓对象
        """
        self.positions[stock_code] = position

    def remove_position(self, stock_code: str) -> Optional[Position]:
        """
        移除持仓

        Args:
            stock_code: 股票代码

        Returns:
            Optional[Position]: 被移除的持仓对象，如果不存在则返回None
        """
        return self.positions.pop(stock_code, None)

    def get_position(self, stock_code: str) -> Optional[Position]:
        """
        获取持仓

        Args:
            stock_code: 股票代码

        Returns:
            Optional[Position]: 持仓对象，如果不存在则返回None
        """
        return self.positions.get(stock_code)

    def has_position(self, stock_code: str) -> bool:
        """
        检查是否有持仓

        Args:
            stock_code: 股票代码

        Returns:
            bool: 是否有持仓
        """
        return stock_code in self.positions

    def get_position_count(self) -> int:
        """
        获取持仓数量

        Returns:
            int: 持仓数量
        """
        return len(self.positions)

    def get_all_positions(self) -> Dict[str, Position]:
        """
        获取所有持仓

        Returns:
            Dict[str, Position]: 所有持仓
        """
        return self.positions.copy()

    def calculate_total_value(self, all_stock_data: Dict[str, pd.DataFrame], current_date: str) -> float:
        """
        计算持仓总市值

        Args:
            all_stock_data: 所有股票数据 {stock_code: DataFrame}
            current_date: 当前日期

        Returns:
            float: 持仓总市值
        """
        total_value = 0.0
        current_date_dt = pd.to_datetime(current_date)

        for stock_code, position in self.positions.items():
            if stock_code in all_stock_data:
                stock_data = all_stock_data[stock_code]
                # 确保索引不带时区
                if stock_data.index.tz is not None:
                    stock_data = stock_data.tz_localize(None)
                if current_date_dt in stock_data.index:
                    current_price = stock_data.loc[current_date_dt, 'close']
                    total_value += position.get_current_value(current_price)
                else:
                    # 如果当天没有数据，使用买入价格估算
                    total_value += position.get_current_value(position.buy_price)
            else:
                # 使用买入价格估算
                total_value += position.get_current_value(position.buy_price)

        return total_value

    def increment_hold_days(self) -> None:
        """增加所有持仓的持仓天数"""
        for position in self.positions.values():
            position.hold_days += 1

    def clear(self) -> None:
        """清空所有持仓"""
        self.positions.clear()

    def get_positions_summary(self, all_stock_data: Dict[str, pd.DataFrame], current_date: str) -> str:
        """
        获取持仓摘要信息

        Args:
            all_stock_data: 所有股票数据
            current_date: 当前日期

        Returns:
            str: 持仓摘要信息
        """
        if not self.positions:
            return ""

        current_date_dt = pd.to_datetime(current_date)
        position_list = []

        for stock_code, pos in self.positions.items():
            pos_profit_rate = 0.0
            if stock_code in all_stock_data:
                stock_data = all_stock_data[stock_code]
                if stock_data.index.tz is not None:
                    stock_data = stock_data.tz_localize(None)
                if current_date_dt in stock_data.index:
                    current_price = stock_data.loc[current_date_dt, 'close']
                    pos_profit_rate = pos.get_profit_rate(current_price) * 100
            position_list.append(f"{stock_code:0>6}({pos_profit_rate:+.2f}%)")

        return " | 持仓: " + ", ".join(position_list)
