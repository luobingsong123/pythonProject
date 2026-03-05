"""
回避时间段管理模块

负责处理回测中的回避时间段逻辑
"""

from typing import List, Tuple
import pandas as pd
from utils.backtest_engine.config import BacktestConfig
from utils.logger_utils import setup_logger
import config

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"]
)


class BlackoutManager:
    """回避时间段管理器"""

    def __init__(self, backtest_config: BacktestConfig):
        """
        初始化回避时间段管理器

        Args:
            backtest_config: 回测配置
        """
        self.config = backtest_config

    def check_force_sell(self, current_date: str, trading_dates: List[pd.Timestamp]) -> Tuple[bool, str]:
        """
        检查是否需要在当前日期强制卖出（回避时间段开始）

        Args:
            current_date: 当前日期
            trading_dates: 交易日历

        Returns:
            Tuple[bool, str]: (是否强制卖出, 原因)
        """
        if not self.config.enable_blackout:
            return False, ''

        blackout_periods = self.config.blackout_periods
        if not blackout_periods:
            return False, ''

        current_date_dt = pd.to_datetime(current_date)

        for period in blackout_periods:
            force_sell_date = pd.to_datetime(period.force_sell_date)

            # 找到 force_sell_date 之后的第一个交易日
            for trade_date in trading_dates:
                if trade_date >= force_sell_date:
                    # 如果当前日期就是这个交易日，则强制卖出
                    if trade_date.strftime('%Y-%m-%d') == current_date:
                        reason = period.reason if period.reason else '回避时间段开始'
                        return True, f'强制卖出: {reason}'
                    break

        return False, ''

    def is_in_blackout_period(self, current_date: str) -> Tuple[bool, str]:
        """
        检查当前是否在禁止买入时间段内

        Args:
            current_date: 当前日期

        Returns:
            Tuple[bool, str]: (是否禁止买入, 原因)
        """
        if not self.config.enable_blackout:
            return False, ''

        blackout_periods = self.config.blackout_periods
        if not blackout_periods:
            return False, ''

        current_date_dt = pd.to_datetime(current_date)

        for period in blackout_periods:
            force_sell_date = pd.to_datetime(period.force_sell_date)
            resume_buy_date = pd.to_datetime(period.resume_buy_date)

            # 在强制卖出日期到恢复买入日期之间，禁止买入
            if force_sell_date <= current_date_dt < resume_buy_date:
                reason = period.reason if period.reason else '回避时间段'
                return True, f'禁止买入: {reason}'

        return False, ''

    def log_blackout_status(self) -> None:
        """记录回避时间段配置状态"""
        if self.config.enable_blackout:
            blackout_periods = self.config.blackout_periods
            logger.info(f"回避功能: 已启用，共 {len(blackout_periods)} 个回避时间段")
            for idx, period in enumerate(blackout_periods, 1):
                logger.info(f"  时间段{idx}: {period.force_sell_date} 卖出 -> "
                            f"{period.resume_buy_date} 恢复买入 ({period.reason if period.reason else '未指定原因'})")
        else:
            logger.info(f"回避功能: 未启用")
