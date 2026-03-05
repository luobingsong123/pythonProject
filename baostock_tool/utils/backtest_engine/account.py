"""
账户管理模块

负责资金管理、手续费计算、账户状态维护
"""

from typing import Dict
from utils.logger_utils import setup_logger
import config

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"]
)


class Account:
    """账户管理类"""

    def __init__(self, initial_cash: float, commission: float, slippage: float):
        """
        初始化账户

        Args:
            initial_cash: 初始资金
            commission: 手续费率
            slippage: 滑点率
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_rate = commission
        self.slippage_rate = slippage

        # 统计数据
        self.total_buy_commission = 0.0
        self.total_sell_commission = 0.0
        self.profit_trade_count = 0
        self.loss_trade_count = 0

    def calc_buy_cost(self, price: float, volume: int) -> Dict[str, float]:
        """
        计算买入成本

        Args:
            price: 买入价格
            volume: 买入数量

        Returns:
            Dict: 包含各项成本的字典
                - amount: 股票金额
                - commission: 手续费
                - slippage_cost: 滑点成本
                - total_cost: 总成本
        """
        amount = price * volume
        commission = amount * self.commission_rate
        slippage_cost = amount * self.slippage_rate
        total_cost = amount + commission + slippage_cost

        return {
            'amount': amount,
            'commission': commission,
            'slippage_cost': slippage_cost,
            'total_cost': total_cost
        }

    def calc_sell_proceeds(self, price: float, volume: int) -> Dict[str, float]:
        """
        计算卖出所得

        Args:
            price: 卖出价格
            volume: 卖出数量

        Returns:
            Dict: 包含各项金额的字典
                - amount: 股票金额
                - commission: 手续费
                - slippage_cost: 滑点成本
                - actual_amount: 实际所得
        """
        amount = price * volume
        commission = amount * self.commission_rate
        slippage_cost = amount * self.slippage_rate
        actual_amount = amount - commission - slippage_cost

        return {
            'amount': amount,
            'commission': commission,
            'slippage_cost': slippage_cost,
            'actual_amount': actual_amount
        }

    def can_afford(self, total_cost: float) -> bool:
        """
        检查是否有足够资金

        Args:
            total_cost: 总成本

        Returns:
            bool: 是否有足够资金
        """
        return self.cash >= total_cost

    def debit(self, amount: float) -> None:
        """
        扣除资金

        Args:
            amount: 扣除金额
        """
        self.cash -= amount

    def credit(self, amount: float) -> None:
        """
        增加资金

        Args:
            amount: 增加金额
        """
        self.cash += amount

    def add_buy_commission(self, commission: float) -> None:
        """累计买入手续费"""
        self.total_buy_commission += commission

    def add_sell_commission(self, commission: float) -> None:
        """累计卖出手续费"""
        self.total_sell_commission += commission

    def record_trade(self, profit: float) -> None:
        """
        记录交易盈亏

        Args:
            profit: 交易盈亏
        """
        if profit > 0:
            self.profit_trade_count += 1
        else:
            self.loss_trade_count += 1

    def get_total_commission(self) -> float:
        """获取总手续费"""
        return self.total_buy_commission + self.total_sell_commission

    def get_win_rate(self) -> float:
        """
        获取胜率

        Returns:
            float: 胜率（百分比）
        """
        total_trades = self.profit_trade_count + self.loss_trade_count
        if total_trades == 0:
            return 0.0
        return self.profit_trade_count / total_trades * 100

    def reset(self) -> None:
        """重置账户状态"""
        self.cash = self.initial_cash
        self.total_buy_commission = 0.0
        self.total_sell_commission = 0.0
        self.profit_trade_count = 0
        self.loss_trade_count = 0
