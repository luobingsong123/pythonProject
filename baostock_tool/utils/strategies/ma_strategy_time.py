"""
均线突破策略

买入条件：
1. 当日收盘价上穿20日均线

卖出条件：
1. 当日收盘价下穿20日均线
2. 持仓达到最大天数
3. 动态止盈止损触发
"""

from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy, Position


class MAStrategyTimeBased(BaseStrategy):
    """
    均线突破策略（按时间遍历版本）
    支持动态止盈止损
    """
    
    STRATEGY_NAME = "MAStrategy"
    
    DEFAULT_PARAMS = {
        'ma_period': 20,            # 均线周期
        'max_hold_days': 30,        # 最大持仓天数
        # 动态止盈止损参数（可覆盖基类默认值）
        'take_profit': 0.15,        # 止盈
        'stop_loss': -0.06,         # 止损
        'trailing_stop_trigger': 0.10,   # 触发移动止损
        'trailing_stop_pct': 0.05,       # 移动止损回撤
        'trailing_stop_min_profit': 0.01, # 移动止损保底
        'printlog': True,
    }
    
    def get_min_data_length(self) -> int:
        """需要至少MA周期+1的数据"""
        return self.params['ma_period'] + 1
    
    def check_buy_signal(
        self, 
        stock_code: str,
        market: str,
        stock_data: pd.DataFrame,
        current_date: str
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        检查买入信号
        
        买入条件：当日收盘价上穿MA
        """
        try:
            ma_period = self.params['ma_period']
            
            if stock_data is None or len(stock_data) < ma_period + 1:
                return False, 0, {'reason': f'数据不足{ma_period+1}天'}
            
            # 获取当日和昨日数据
            current_date_dt = pd.to_datetime(current_date)
            if current_date_dt not in stock_data.index:
                return False, 0, {'reason': '当日无数据'}
            
            # 获取收盘价序列
            close_prices = stock_data['close']
            
            # 计算MA
            ma_series = close_prices.rolling(window=ma_period).mean()
            
            # 获取当日和昨日数据
            current_close = close_prices.iloc[-1]
            prev_close = close_prices.iloc[-2]
            current_ma = ma_series.iloc[-1]
            prev_ma = ma_series.iloc[-2]
            
            if pd.isna(current_ma) or pd.isna(prev_ma):
                return False, 0, {'reason': '均线无效'}
            
            # 判断上穿：昨日收盘价 < 昨日MA，且 当日收盘价 > 当日MA
            if prev_close < prev_ma and current_close > current_ma:
                # 信号强度 = 突破幅度
                signal_strength = (current_close - current_ma) / current_ma
                signal_info = {
                    'current_close': float(current_close),
                    'current_ma': float(current_ma),
                    'prev_close': float(prev_close),
                    'prev_ma': float(prev_ma),
                    'breakthrough_pct': float(signal_strength),
                    'close_price': float(current_close)
                }
                return True, signal_strength, signal_info
            
            return False, 0, {'reason': '未触发上穿'}
            
        except Exception as e:
            return False, 0, {'error': str(e)}
    
    def check_sell_signal(
        self,
        position: Position,
        stock_data: pd.DataFrame,
        current_date: str
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        检查卖出信号
        
        卖出条件：
        1. 动态止盈止损触发
        2. 当日收盘价下穿MA
        3. 持仓达到最大天数
        """
        try:
            ma_period = self.params['ma_period']
            
            current_date_dt = pd.to_datetime(current_date)
            if current_date_dt not in stock_data.index:
                return False, None, None
            
            # 获取收盘价序列
            close_prices = stock_data['close']
            ma_series = close_prices.rolling(window=ma_period).mean()
            
            current_close = close_prices.iloc[-1]
            prev_close = close_prices.iloc[-2]
            current_ma = ma_series.iloc[-1]
            prev_ma = ma_series.iloc[-2]
            
            # 1. 检查动态止盈止损
            should_stop, stop_reason = self.check_dynamic_stop_loss(position, current_close)
            if should_stop:
                return True, stop_reason, current_close
            
            # 2. 条件：下穿MA
            if not pd.isna(current_ma) and not pd.isna(prev_ma):
                if prev_close > prev_ma and current_close < current_ma:
                    return True, '收盘价下穿MA', current_close
            
            # 3. 条件：持仓天数达到最大
            if position.hold_days >= self.params['max_hold_days']:
                return True, f'持仓达到{self.params["max_hold_days"]}天', None

            return False, None, None
            
        except Exception as e:
            return False, None, None
