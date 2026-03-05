"""
回测配置模块

定义回测引擎的配置数据类
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class BlackoutPeriod:
    """回避时间段配置"""
    force_sell_date: str  # 该日期后的第一个交易日强制卖出所有持仓
    resume_buy_date: str  # 该日期后才允许买入
    reason: str = ""  # 原因说明

    def __post_init__(self):
        """验证日期格式"""
        # 简单验证日期格式 YYYY-MM-DD
        for date_str in [self.force_sell_date, self.resume_buy_date]:
            if not date_str or len(date_str) != 10:
                raise ValueError(f"日期格式错误: {date_str}，应为 YYYY-MM-DD")


@dataclass
class BacktestConfig:
    """回测配置数据类"""
    start_date: str
    end_date: str
    initial_cash: float = 10000000.0
    commission: float = 0.001
    slippage_perc: float = 0.001
    max_positions: int = 100
    max_daily_buys: int = 10
    position_size_pct: float = 0.01
    min_hold_days: int = 1
    lookback_days: int = 365
    enable_blackout: bool = False
    blackout_periods: List[BlackoutPeriod] = field(default_factory=list)
    # 性能优化配置
    enable_parallel: bool = True         # 是否启用多进程并行
    enable_vectorization: bool = True    # 是否启用向量化批处理
    parallel_threshold: int = 500        # 多进程并行阈值（股票数量）

    def __post_init__(self):
        """验证配置"""
        if self.initial_cash <= 0:
            raise ValueError("initial_cash 必须大于 0")
        if self.commission < 0:
            raise ValueError("commission 不能为负数")
        if self.slippage_perc < 0:
            raise ValueError("slippage_perc 不能为负数")
        if self.max_positions <= 0:
            raise ValueError("max_positions 必须大于 0")

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BacktestConfig':
        """
        从字典创建配置实例

        Args:
            config_dict: 配置字典

        Returns:
            BacktestConfig: 配置实例
        """
        # 处理 blackout_periods
        blackout_periods = []
        if 'blackout_periods' in config_dict:
            for period_dict in config_dict['blackout_periods']:
                if isinstance(period_dict, dict):
                    blackout_periods.append(BlackoutPeriod(
                        force_sell_date=period_dict['force_sell_date'],
                        resume_buy_date=period_dict['resume_buy_date'],
                        reason=period_dict.get('reason', '')
                    ))

        return cls(
            start_date=config_dict['start_date'],
            end_date=config_dict['end_date'],
            initial_cash=config_dict.get('initial_cash', 10000000.0),
            commission=config_dict.get('commission', 0.001),
            slippage_perc=config_dict.get('slippage_perc', 0.001),
            max_positions=config_dict.get('max_positions', 100),
            max_daily_buys=config_dict.get('max_daily_buys', 10),
            position_size_pct=config_dict.get('position_size_pct', 0.01),
            min_hold_days=config_dict.get('min_hold_days', 1),
            lookback_days=config_dict.get('lookback_days', 365),
            enable_blackout=config_dict.get('enable_blackout', False),
            blackout_periods=blackout_periods,
            # 性能优化配置
            enable_parallel=config_dict.get('enable_parallel', True),
            enable_vectorization=config_dict.get('enable_vectorization', True),
            parallel_threshold=config_dict.get('parallel_threshold', 500)
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            Dict: 配置字典
        """
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_cash': self.initial_cash,
            'commission': self.commission,
            'slippage_perc': self.slippage_perc,
            'max_positions': self.max_positions,
            'max_daily_buys': self.max_daily_buys,
            'position_size_pct': self.position_size_pct,
            'min_hold_days': self.min_hold_days,
            'lookback_days': self.lookback_days,
            'enable_blackout': self.enable_blackout,
            'blackout_periods': [
                {
                    'force_sell_date': p.force_sell_date,
                    'resume_buy_date': p.resume_buy_date,
                    'reason': p.reason
                }
                for p in self.blackout_periods
            ],
            # 性能优化配置
            'enable_parallel': self.enable_parallel,
            'enable_vectorization': self.enable_vectorization,
            'parallel_threshold': self.parallel_threshold
        }
