"""
回测引擎模块

包含回测相关的核心组件
"""

from utils.backtest_engine.config import BacktestConfig, BlackoutPeriod
from utils.backtest_engine.account import Account
from utils.backtest_engine.portfolio import PortfolioManager
from utils.backtest_engine.trade_executor import TradeExecutor
from utils.backtest_engine.statistics import StatisticsCalculator, BacktestStatistics
from utils.backtest_engine.recorder import BacktestRecorder
from utils.backtest_engine.blackout_manager import BlackoutManager

__all__ = [
    'BacktestConfig',
    'BlackoutPeriod',
    'Account',
    'PortfolioManager',
    'TradeExecutor',
    'StatisticsCalculator',
    'BacktestStatistics',
    'BacktestRecorder',
    'BlackoutManager'
]
