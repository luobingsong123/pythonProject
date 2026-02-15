"""
价值投资策略

买入条件：
1. 市盈率(PE TTM)小于30
2. 市净率(PB MRQ)小于12
3. 当日股价最低价，比220日均价小15%以上

卖出条件：
1. 当日股价最高价，比220日均价大15%以上
2. 持仓日期达到120日
3. 动态止盈止损触发
"""

from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy, Position


class ValueStrategyTimeBased(BaseStrategy):
    """
    价值投资策略（按时间遍历版本）
    支持动态止盈止损
    """
    
    STRATEGY_NAME = "ValueStrategy"
    
    DEFAULT_PARAMS = {
        'ma_period': 210,           # 均线周期
        'max_pe_ttm': 30.0,         # 最大市盈率
        'max_pb_mrq': 12.0,         # 最大市净率
        'buy_threshold': -0.15,     # 买入阈值：最低价比MA低
        'sell_threshold_up': 0.25,  # 卖出阈值：最高价比MA高
        'max_hold_days': 120,       # 最大持仓天数
        # 动态止盈止损参数（可覆盖基类默认值）
        'take_profit': 0.26,        # 止盈
        'stop_loss': -0.06,         # 止损
        'trailing_stop_trigger': 0.10,   # 触发移动止损
        'trailing_stop_pct': 0.05,       # 移动止损回撤
        'trailing_stop_min_profit': 0.03, # 移动止损保底
        'printlog': True,
    }
    
    def _validate_params(self):
        """验证参数"""
        assert 0 < self.params['max_pe_ttm'] < 1000, "max_pe_ttm 应在 (0, 1000) 范围内"
        assert 0 < self.params['max_pb_mrq'] < 1000, "max_pb_mrq 应在 (0, 1000) 范围内"
        assert -1 < self.params['buy_threshold'] < 0, "buy_threshold 应在 (-1, 0) 范围内"
        assert 0 < self.params['sell_threshold_up'] < 1, "sell_threshold_up 应在 (0, 1) 范围内"
    
    def get_min_data_length(self) -> int:
        """需要至少MA周期的数据"""
        return self.params['ma_period']
    
    def check_buy_signal(
        self, 
        stock_code: str,
        market: str,
        stock_data: pd.DataFrame,
        current_date: str
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        检查买入信号
        
        买入条件：
        1. PE < max_pe_ttm 且 PB < max_pb_mrq
        2. 当日最低价比MA_period低 buy_threshold 以上
        """
        try:
            ma_period = self.params['ma_period']
            
            if stock_data is None or len(stock_data) < ma_period:
                return False, 0, {'reason': f'数据不足{ma_period}天'}
            
            # 获取当日数据
            current_date_dt = pd.to_datetime(current_date)
            if current_date_dt not in stock_data.index:
                return False, 0, {'reason': '当日无数据'}
            
            today_data = stock_data.loc[current_date_dt]
            
            # 检查基本面条件
            pe_ttm = today_data.get('peTTM', None)
            pb_mrq = today_data.get('pbMRQ', None)
            
            if pe_ttm is None or pe_ttm <= 0 or pe_ttm >= self.params['max_pe_ttm']:
                return False, 0, {'reason': f'PE不满足: {pe_ttm}'}
            
            if pb_mrq is None or pb_mrq <= 0 or pb_mrq >= self.params['max_pb_mrq']:
                return False, 0, {'reason': f'PB不满足: {pb_mrq}'}
            
            # 计算均线
            close_prices = stock_data['close']
            ma_value = close_prices.rolling(window=ma_period).mean().iloc[-1]
            
            if pd.isna(ma_value) or ma_value <= 0:
                return False, 0, {'reason': '均线无效'}
            
            # 检查买入条件
            low_price = today_data['low']
            deviation = (low_price - ma_value) / ma_value
            
            if deviation <= self.params['buy_threshold']:
                # 信号强度 = 偏离度绝对值
                signal_strength = abs(deviation)
                signal_info = {
                    'low_price': float(low_price),
                    'ma_value': float(ma_value),
                    'deviation': float(deviation),
                    'pe_ttm': float(pe_ttm),
                    'pb_mrq': float(pb_mrq),
                    'close_price': float(today_data['close'])
                }
                return True, signal_strength, signal_info
            
            return False, 0, {'reason': f'偏离度不满足: {deviation:.2%}'}
            
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
        1. 最高价比MA高15%以上
        2. 持仓达到最大天数
        3. 动态止盈止损触发
        """
        try:
            current_date_dt = pd.to_datetime(current_date)
            if current_date_dt not in stock_data.index:
                return False, None, None
            
            today_data = stock_data.loc[current_date_dt]
            current_price = today_data['close']
            
            # 1. 检查动态止盈止损
            should_stop, stop_reason = self.check_dynamic_stop_loss(position, current_price)
            if should_stop:
                return True, stop_reason, current_price
            
            # 2. 条件：最高价比MA高15%以上
            ma_period = self.params['ma_period']
            close_prices = stock_data['close']
            if len(close_prices) >= ma_period:
                ma_value = close_prices.rolling(window=ma_period).mean().iloc[-1]
                if not pd.isna(ma_value) and ma_value > 0:
                    high_price = today_data['high']
                    if high_price >= ma_value * (1 + self.params['sell_threshold_up']):
                        return True, f'最高价触及MA+{self.params["sell_threshold_up"]*100:.0f}%', current_price
            
            # 3. 条件：持仓天数达到最大
            if position.hold_days >= self.params['max_hold_days']:
                return True, f'持仓达到{self.params["max_hold_days"]}天', today_data['open']
            
            return False, None, None
            
        except Exception as e:
            return False, None, None
