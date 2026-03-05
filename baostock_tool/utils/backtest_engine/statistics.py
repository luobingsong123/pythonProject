"""
统计计算模块

负责计算回测的统计指标，如最大回撤、夏普比率等
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import pandas as pd
import numpy as np


@dataclass
class BacktestStatistics:
    """回测统计数据"""
    total_return: float  # 总收益率（%）
    max_drawdown: float  # 最大回撤（%）
    sharpe_ratio: float  # 夏普比率
    total_trades: int  # 总交易次数（平仓次数）
    profit_trade_count: int  # 盈利交易次数
    loss_trade_count: int  # 亏损交易次数
    win_rate: float  # 胜率（%）
    total_commission: float  # 总手续费
    buy_commission: float  # 买入手续费
    sell_commission: float  # 卖出手续费
    commission_ratio: float  # 手续费占比（%）
    buy_count: int = 0  # 买入次数（含补仓）
    sell_count: int = 0  # 卖出次数


class StatisticsCalculator:
    """统计计算器"""

    @staticmethod
    def calculate_from_daily_values(
        daily_values: List[Dict[str, Any]],
        initial_cash: float,
        profit_trade_count: int,
        loss_trade_count: int,
        total_buy_commission: float,
        total_sell_commission: float,
        trading_records: List[Dict[str, Any]] = None
    ) -> BacktestStatistics:
        """
        从每日资产数据计算统计指标

        Args:
            daily_values: 每日资产记录列表
            initial_cash: 初始资金
            profit_trade_count: 盈利交易次数
            loss_trade_count: 亏损交易次数
            total_buy_commission: 买入手续费总额
            total_sell_commission: 卖出手续费总额
            trading_records: 交易记录列表（可选，用于准确统计买卖次数）

        Returns:
            BacktestStatistics: 统计数据
        """
        if not daily_values:
            return BacktestStatistics(
                total_return=0,
                max_drawdown=0,
                sharpe_ratio=0,
                total_trades=0,
                profit_trade_count=0,
                loss_trade_count=0,
                win_rate=0,
                total_commission=0,
                buy_commission=0,
                sell_commission=0,
                commission_ratio=0
            )

        df = pd.DataFrame(daily_values)

        # 计算总资产（现金 + 持仓市值）
        # 如果 daily_values 中已经有 total_value 字段，直接使用
        # 否则使用 cash + portfolio_value
        if 'total_value' in df.columns:
            df['total_asset'] = df['total_value']
        else:
            df['total_asset'] = df['cash'] + df['portfolio_value']

        # 总收益率 - 使用总资产计算
        final_total_asset = df['total_asset'].iloc[-1]
        total_return = (final_total_asset / initial_cash - 1) * 100

        # 最大回撤和夏普比率 - 使用总资产计算
        max_drawdown = 0.0
        sharpe_ratio = 0.0

        if len(df) > 1:
            df['return'] = df['total_asset'].pct_change()

            # 最大回撤
            cumulative_max = df['total_asset'].cummax()
            drawdown = (df['total_asset'] - cumulative_max) / cumulative_max
            max_drawdown = drawdown.min() * 100

            # 夏普比率（假设无风险利率为3%年化）
            daily_returns = df['return'].dropna()
            if len(daily_returns) > 0 and daily_returns.std() > 0:
                excess_returns = daily_returns - 0.03 / 252
                sharpe_ratio = (excess_returns.mean() / daily_returns.std()) * np.sqrt(252)

        # 胜率
        total_trades = profit_trade_count + loss_trade_count
        win_rate = profit_trade_count / total_trades * 100 if total_trades > 0 else 0

        # 手续费
        total_commission = total_buy_commission + total_sell_commission
        commission_ratio = total_commission / initial_cash * 100

        # 从交易记录中准确统计买卖次数
        buy_count = 0
        sell_count = 0
        if trading_records:
            for record in trading_records:
                action = record.get('action', '')
                if action == 'buy':
                    buy_count += 1
                elif action == 'sell':
                    sell_count += 1
                elif action == 'add_position':
                    buy_count += 1  # 补仓也算一次买入

        return BacktestStatistics(
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            total_trades=total_trades,
            profit_trade_count=profit_trade_count,
            loss_trade_count=loss_trade_count,
            win_rate=win_rate,
            total_commission=total_commission,
            buy_commission=total_buy_commission,
            sell_commission=total_sell_commission,
            commission_ratio=commission_ratio,
            buy_count=buy_count,
            sell_count=sell_count
        )

    @staticmethod
    def print_statistics(stats: BacktestStatistics, initial_cash: float, final_value: float, execution_time: float):
        """
        打印统计结果

        Args:
            stats: 统计数据
            initial_cash: 初始资金
            final_value: 最终资金
            execution_time: 执行时间（秒）
        """
        from utils.logger_utils import setup_logger
        import config

        logger = setup_logger(
            logger_name=__name__,
            log_level=config.get_log_config()["log_level"],
            log_dir=config.get_log_config()["log_dir"]
        )

        logger.info(f"{'=' * 60}")
        logger.info(f"回测结果汇总 (QuestDB数据源)")
        logger.info(f"{'=' * 60}")
        logger.info(f"初始资金: {initial_cash:,.0f}")
        logger.info(f"期末资金: {final_value:,.2f}")
        logger.info(f"总收益率: {stats.total_return:.2f}%")
        logger.info(f"最大回撤: {stats.max_drawdown:.2f}%")
        logger.info(f"夏普比率: {stats.sharpe_ratio:.2f}" if stats.sharpe_ratio != 0 else "夏普比率: N/A")
        logger.info(f"盈利交易: {stats.profit_trade_count}")
        logger.info(f"亏损交易: {stats.loss_trade_count}")
        logger.info(f"平仓次数: {stats.total_trades}")
        logger.info(f"买入次数: {stats.buy_count}")
        logger.info(f"卖出次数: {stats.sell_count}")
        logger.info(f"胜率: {stats.win_rate:.2f}%")
        logger.info(f"总手续费: {stats.total_commission:.2f}")
        logger.info(f"  买入手续费: {stats.buy_commission:.2f}")
        logger.info(f"  卖出手续费: {stats.sell_commission:.2f}")
        logger.info(f"手续费占比: {stats.commission_ratio:.2f}%")
        logger.info(f"回测耗时: {execution_time:.2f} 秒 ({execution_time / 60:.2f} 分钟)")
        logger.info(f"{'=' * 60}")
