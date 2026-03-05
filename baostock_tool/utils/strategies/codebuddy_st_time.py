"""
CodeBuddy时间策略

策略逻辑：
1. 买入条件：昨日成交量为N日内最低，下一交易日买入
2. 卖出条件：浮盈达到阈值 / 浮亏达到阈值 / 持仓天数达到阈值

适用于按时间遍历的回测框架
"""

from .base_strategy import BaseStrategy, Position
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd
import numpy as np


class CodeBuddyStrategyTimeBased(BaseStrategy):
    """
    CodeBuddy时间策略
    
    买入信号：昨日成交量为N日（period参数）内最低
    卖出信号：
        - 浮盈达到profit_threshold（默认10%）
        - 浮亏达到drawdown_threshold（默认-3%）
        - 持仓天数达到hold_days_threshold（默认99999天）
    """
    
    STRATEGY_NAME = "CodeBuddyStrategy"
    
    DEFAULT_PARAMS = {
        'period': 30,                    # 查找最低成交量的周期
        'profit_threshold': 10.0,        # 止盈阈值（百分比）
        'drawdown_threshold': 3.0,       # 止损阈值（百分比）
        'hold_days_threshold': 99999,    # 最大持仓天数阈值
        'printlog': True,
    }
    
    DEFAULT_STOP_PARAMS = {
        'take_profit': 0.12,             # 覆盖基类默认止盈
        'stop_loss': -0.06,              # 覆盖基类默认止损
        'trailing_stop_trigger': 0.06,   # 移动止损触发阈值
        'trailing_stop_pct': 0.03,       # 移动止损回撤比例
        'trailing_stop_min_profit': 0.02,  # 移动止损最低保底盈利
    }
    
    def _validate_params(self):
        """验证参数有效性"""
        if self.params['period'] < 2:
            raise ValueError("period 必须 >= 2")
        if self.params['profit_threshold'] <= 0:
            raise ValueError("profit_threshold 必须 > 0")
        if self.params['drawdown_threshold'] <= 0:
            raise ValueError("drawdown_threshold 必须 > 0")
        if self.params['hold_days_threshold'] < 1:
            raise ValueError("hold_days_threshold 必须 >= 1")
    
    def get_min_data_length(self) -> int:
        """返回策略所需的最小数据长度"""
        return self.params['period'] + 1
    
    def check_buy_signal(self, stock_code: str, market: str, 
                         stock_data: pd.DataFrame, current_date: str) -> Tuple[bool, float, Optional[Dict]]:
        """
        检查买入信号
        
        买入条件：昨日成交量为N日内最低
        
        Args:
            stock_code: 股票代码
            market: 市场代码
            stock_data: 截止到当前日期的历史数据
            current_date: 当前日期
            
        Returns:
            Tuple[bool, float, Dict]: (是否买入, 信号强度, 信号信息)
        """
        # 检查数据长度是否足够
        if len(stock_data) < self.params['period'] + 1:
            return False, 0, None
        
        # 获取当前日期数据
        current_date_dt = pd.to_datetime(current_date)
        if current_date_dt not in stock_data.index:
            return False, 0, None
        
        today_data = stock_data.loc[current_date_dt]
        
        # 获取过去N天的成交量数据（不包含当天，取昨日及之前）
        volume_series = stock_data['volume'].iloc[-self.params['period']-1:-1]
        
        if len(volume_series) < self.params['period']:
            return False, 0, None
        
        # 昨日成交量
        yesterday_volume = volume_series.iloc[-1]
        
        # N日最低成交量
        min_volume = volume_series.min()
        
        # 检查昨日成交量是否为N日最低
        if yesterday_volume == min_volume:
            # 信号强度：根据成交量萎缩程度计算
            # 萎缩越严重，信号越强
            avg_volume = volume_series.mean()
            volume_shrink_rate = 1 - (yesterday_volume / avg_volume) if avg_volume > 0 else 0
            signal_strength = min(1.0, volume_shrink_rate + 0.5)  # 基础强度0.5，加上萎缩比例
            
            signal_info = {
                'close_price': float(today_data['open']),  # 使用开盘价买入
                'yesterday_volume': float(yesterday_volume),
                'min_volume': float(min_volume),
                'volume_rank': f'{self.params["period"]}日最低',
                'volume_shrink_rate': round(volume_shrink_rate, 4),
            }
            
            return True, signal_strength, signal_info
        
        return False, 0, None
    
    def check_sell_signal(self, position: Position, stock_data: pd.DataFrame, 
                          current_date: str) -> Tuple[bool, str, float]:
        """
        检查卖出信号
        
        卖出条件（满足任一）：
        1. 浮盈达到 profit_threshold
        2. 浮亏达到 drawdown_threshold
        3. 持仓天数达到 hold_days_threshold
        
        Args:
            position: 持仓信息
            stock_data: 截止到当前日期的历史数据
            current_date: 当前日期
            
        Returns:
            Tuple[bool, str, float]: (是否卖出, 卖出原因, 卖出价格)
        """
        # 获取当前日期数据
        current_date_dt = pd.to_datetime(current_date)
        if current_date_dt not in stock_data.index:
            return False, '', position.buy_price
        
        today_data = stock_data.loc[current_date_dt]
        current_price = float(today_data['open'])  # 使用开盘价卖出
        
        # 计算盈亏比例
        profit_rate = position.get_profit_rate(current_price) * 100  # 转为百分比
        
        # 条件1：浮盈达到阈值
        if profit_rate >= self.params['profit_threshold']:
            return True, f'浮盈达到{self.params["profit_threshold"]}%', current_price
        
        # 条件2：浮亏达到阈值
        if profit_rate <= -self.params['drawdown_threshold']:
            return True, f'浮亏达到-{self.params["drawdown_threshold"]}%', current_price
        
        # 条件3：持仓天数达到阈值
        if position.hold_days >= self.params['hold_days_threshold']:
            return True, f'持仓天数达到{self.params["hold_days_threshold"]}天', current_price
        
        # 使用基类的动态止盈止损检查
        should_stop, stop_reason = self.check_dynamic_stop_loss(position, current_price)
        if should_stop:
            return True, stop_reason, current_price
        
        return False, '', current_price
    
    def check_add_position_signal(self, position: Position, stock_data: pd.DataFrame,
                                   current_date: str) -> Tuple[bool, float, Optional[Dict]]:
        """
        检查补仓信号（可选实现）
        
        本策略不支持补仓，返回False
        
        Args:
            position: 持仓信息
            stock_data: 截止到当前日期的历史数据
            current_date: 当前日期
            
        Returns:
            Tuple[bool, float, Dict]: (是否补仓, 补仓价格, 补仓信息)
        """
        return False, 0.0, None
    
    def check_buy_signal_batch(
        self,
        stock_codes: List[str],
        markets: List[str],
        stock_data_map: Dict[str, pd.DataFrame],
        current_date: str
    ) -> List[Dict[str, Any]]:
        """
        向量化批量检查买入信号
        
        使用 pandas/numpy 向量化操作，大幅提升多股票信号检查性能
        
        优化策略：
        1. 预过滤：快速排除数据不足的股票
        2. 批量提取：一次性提取所有股票的关键数据
        3. 向量化计算：使用 numpy 批量计算指标
        4. 避免重复拷贝：直接在原数据上操作
        
        Args:
            stock_codes: 股票代码列表
            markets: 市场代码列表
            stock_data_map: 股票数据字典（已切片到当前日期，时区已处理）
            current_date: 当前日期
            
        Returns:
            List[Dict]: 信号结果列表
        """
        current_date_dt = pd.to_datetime(current_date)
        period = self.params['period']
        n_stocks = len(stock_codes)
        
        # 预分配结果列表（使用列表推导式更快）
        results = [{
            'stock_code': stock_codes[i],
            'market': markets[i],
            'is_signal': False,
            'signal_strength': 0.0,
            'signal_info': None
        } for i in range(n_stocks)]
        
        # ===== 第一阶段：快速预过滤 =====
        # 批量检查数据有效性，避免在循环中重复检查
        valid_mask = np.ones(n_stocks, dtype=bool)
        stock_lengths = np.zeros(n_stocks, dtype=int)
        has_current_date = np.zeros(n_stocks, dtype=bool)
        
        for i, stock_code in enumerate(stock_codes):
            stock_data = stock_data_map.get(stock_code)
            if stock_data is None:
                valid_mask[i] = False
                continue
            
            stock_lengths[i] = len(stock_data)
            
            # 检查当前日期是否存在（快速检查）
            if stock_data.index.tz is not None:
                has_current_date[i] = current_date_dt in stock_data.index.tz_localize(None)
            else:
                has_current_date[i] = current_date_dt in stock_data.index
        
        # 数据长度检查
        valid_mask &= (stock_lengths >= period + 1)
        valid_mask &= has_current_date
        
        valid_indices = np.where(valid_mask)[0]
        
        if len(valid_indices) == 0:
            return results
        
        # ===== 第二阶段：批量提取关键数据 =====
        # 预分配数组存储需要的数据
        yesterday_volumes = np.zeros(len(valid_indices))
        min_volumes = np.zeros(len(valid_indices))
        avg_volumes = np.zeros(len(valid_indices))
        open_prices = np.zeros(len(valid_indices))
        
        for arr_idx, stock_idx in enumerate(valid_indices):
            stock_code = stock_codes[stock_idx]
            stock_data = stock_data_map[stock_code]
            
            # 处理时区
            if stock_data.index.tz is not None:
                stock_data = stock_data.copy()
                stock_data.index = stock_data.index.tz_localize(None)
            
            # 获取当日开盘价
            open_prices[arr_idx] = stock_data.loc[current_date_dt, 'open']
            
            # 获取过去N天成交量（向量化切片）
            volume_series = stock_data['volume'].iloc[-period-1:-1]
            
            if len(volume_series) >= period:
                volumes = volume_series.values
                yesterday_volumes[arr_idx] = volumes[-1]
                min_volumes[arr_idx] = np.min(volumes)
                avg_volumes[arr_idx] = np.mean(volumes)
            else:
                # 标记无效
                yesterday_volumes[arr_idx] = -1
        
        # ===== 第三阶段：向量化计算信号 =====
        # 批量判断：昨日成交量是否为N日最低
        is_min_volume = (yesterday_volumes == min_volumes) & (yesterday_volumes > 0)
        
        # 批量计算信号强度
        volume_shrink_rates = np.where(
            avg_volumes > 0,
            1 - (yesterday_volumes / avg_volumes),
            0
        )
        signal_strengths = np.minimum(1.0, volume_shrink_rates + 0.5)
        
        # ===== 第四阶段：填充结果 =====
        signal_indices = valid_indices[is_min_volume]
        
        for arr_idx, stock_idx in enumerate(valid_indices):
            if is_min_volume[arr_idx]:
                results[stock_idx] = {
                    'stock_code': stock_codes[stock_idx],
                    'market': markets[stock_idx],
                    'is_signal': True,
                    'signal_strength': float(signal_strengths[arr_idx]),
                    'signal_info': {
                        'close_price': float(open_prices[arr_idx]),
                        'yesterday_volume': float(yesterday_volumes[arr_idx]),
                        'min_volume': float(min_volumes[arr_idx]),
                        'volume_rank': f'{period}日最低',
                        'volume_shrink_rate': round(float(volume_shrink_rates[arr_idx]), 4),
                    }
                }
        
        return results
    
    def check_sell_signal_batch(
        self,
        positions: List[Position],
        stock_data_map: Dict[str, pd.DataFrame],
        current_date: str
    ) -> List[Dict[str, Any]]:
        """
        向量化批量检查卖出信号
        
        Args:
            positions: 持仓对象列表
            stock_data_map: 股票数据字典（已切片到当前日期，时区已处理）
            current_date: 当前日期
            
        Returns:
            List[Dict]: 卖出信号列表
        """
        results = []
        current_date_dt = pd.to_datetime(current_date)
        
        for position in positions:
            result = {
                'stock_code': position.stock_code,
                'should_sell': False,
                'sell_reason': '',
                'sell_price': position.buy_price
            }
            
            stock_data = stock_data_map.get(position.stock_code)
            if stock_data is None:
                results.append(result)
                continue
            
            # 确保索引无时区（兼容性处理）
            if stock_data.index.tz is not None:
                stock_data = stock_data.copy()
                stock_data.index = stock_data.index.tz_localize(None)
            
            if current_date_dt not in stock_data.index:
                results.append(result)
                continue
            
            try:
                today_data = stock_data.loc[current_date_dt]
                current_price = float(today_data['open'])
                
                # 计算盈亏比例
                profit_rate = position.get_profit_rate(current_price) * 100
                
                # 条件1：浮盈达到阈值
                if profit_rate >= self.params['profit_threshold']:
                    result = {
                        'stock_code': position.stock_code,
                        'should_sell': True,
                        'sell_reason': f'浮盈达到{self.params["profit_threshold"]}%',
                        'sell_price': current_price
                    }
                # 条件2：浮亏达到阈值
                elif profit_rate <= -self.params['drawdown_threshold']:
                    result = {
                        'stock_code': position.stock_code,
                        'should_sell': True,
                        'sell_reason': f'浮亏达到-{self.params["drawdown_threshold"]}%',
                        'sell_price': current_price
                    }
                # 条件3：持仓天数达到阈值
                elif position.hold_days >= self.params['hold_days_threshold']:
                    result = {
                        'stock_code': position.stock_code,
                        'should_sell': True,
                        'sell_reason': f'持仓天数达到{self.params["hold_days_threshold"]}天',
                        'sell_price': current_price
                    }
                else:
                    # 动态止盈止损检查
                    should_stop, stop_reason = self.check_dynamic_stop_loss(position, current_price)
                    if should_stop:
                        result = {
                            'stock_code': position.stock_code,
                            'should_sell': True,
                            'sell_reason': stop_reason,
                            'sell_price': current_price
                        }
                    else:
                        result['sell_price'] = current_price
                
            except Exception:
                pass
            
            results.append(result)
        
        return results
