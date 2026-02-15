"""
策略基类模块

用于按时间遍历回测的策略接口定义
所有自定义策略需要继承 BaseStrategy 并实现相关方法
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import pandas as pd


class BaseStrategy(ABC):
    """
    策略基类
    
    所有用于按时间遍历回测的策略都需要继承此类
    """
    
    # 策略名称（子类必须设置）
    STRATEGY_NAME = "BaseStrategy"
    
    # 策略参数默认值（子类可覆盖）
    DEFAULT_PARAMS = {}
    
    # 动态止盈止损默认参数
    DEFAULT_STOP_PARAMS = {
        'take_profit': 0.12,           # 基础止盈点：12%
        'stop_loss': -0.06,            # 基础止损点：-6%
        'trailing_stop_trigger': 0.06, # 触发移动止损的盈利阈值：6%
        'trailing_stop_pct': 0.03,     # 移动止损回撤比例：3%（从最高点回撤）
        'trailing_stop_min_profit': 0.02,  # 移动止损最低保底盈利：2%
    }
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化策略
        
        Args:
            params: 策略参数字典
        """
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        
        # 合并止盈止损参数
        stop_params = {k: v for k, v in self.DEFAULT_STOP_PARAMS.items()}
        if params:
            for key in stop_params.keys():
                if key in params:
                    stop_params[key] = params[key]
        self.stop_params = stop_params
        
        self._validate_params()
    
    def _validate_params(self):
        """验证参数有效性（子类可重写）"""
        # 验证止盈止损参数
        if self.stop_params['take_profit'] <= 0:
            raise ValueError("take_profit 必须大于 0")
        if self.stop_params['stop_loss'] >= 0:
            raise ValueError("stop_loss 必须小于 0")
    
    @abstractmethod
    def check_buy_signal(
        self, 
        stock_code: str,
        market: str,
        stock_data: pd.DataFrame,
        current_date: str
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        检查买入信号
        
        Args:
            stock_code: 股票代码
            market: 市场类型 (sh/sz/bj)
            stock_data: 股票历史数据DataFrame（索引为日期）
            current_date: 当前日期 (YYYY-MM-DD)
            
        Returns:
            Tuple[bool, float, Dict]:
                - is_signal: 是否触发买入信号
                - signal_strength: 信号强度（用于多信号排序）
                - signal_info: 信号详情字典，至少包含:
                    - close_price: 收盘价（用于计算买入数量）
                    - 其他策略相关信息
        """
        pass
    
    @abstractmethod
    def check_sell_signal(
        self,
        position: Any,  # Position 对象
        stock_data: pd.DataFrame,
        current_date: str
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        检查卖出信号
        
        Args:
            position: 持仓对象，包含以下属性:
                - stock_code: 股票代码
                - market: 市场类型
                - name: 股票名称
                - buy_date: 买入日期
                - buy_price: 买入价格
                - volume: 持仓数量
                - hold_days: 持仓天数
                - get_profit_rate(current_price): 计算盈亏比例
            stock_data: 股票历史数据DataFrame
            current_date: 当前日期 (YYYY-MM-DD)
            
        Returns:
            Tuple[bool, Optional[str], Optional[float]]:
                - should_sell: 是否应该卖出
                - sell_reason: 卖出原因（可选）
                - sell_price: 建议卖出价格（可选，None则使用收盘价）
        """
        pass
    
    @abstractmethod
    def get_min_data_length(self) -> int:
        """
        获取策略所需的最小数据长度
        
        Returns:
            int: 最小数据长度（用于过滤数据不足的股票）
        """
        pass
    
    def on_backtest_start(self, context: Dict[str, Any]):
        """
        回测开始时的回调（可选实现）
        
        Args:
            context: 回测上下文信息
        """
        pass
    
    def on_backtest_end(self, context: Dict[str, Any]):
        """
        回测结束时的回调（可选实现）
        
        Args:
            context: 回测上下文信息
        """
        pass
    
    def on_trade(self, trade_info: Dict[str, Any]):
        """
        交易完成时的回调（可选实现）
        
        Args:
            trade_info: 交易信息
        """
        pass
    
    def check_dynamic_stop_loss(
        self,
        position: 'Position',
        current_price: float
    ) -> Tuple[bool, Optional[str]]:
        """
        检查动态止盈止损
        
        动态止损逻辑：
        1. 基础止损：亏损达到 stop_loss（如-6%）则止损
        2. 移动止损：当盈利超过 trailing_stop_trigger（如6%）后，
           如果从最高点回撤超过 trailing_stop_pct（如3%），则触发止损
        3. 保底止损：移动止损时，至少保住 trailing_stop_min_profit（如2%）的利润
        4. 基础止盈：盈利达到 take_profit（如12%）则止盈
        
        Args:
            position: 持仓对象
            current_price: 当前价格
            
        Returns:
            Tuple[bool, Optional[str]]: (是否触发, 原因)
        """
        profit_rate = position.get_profit_rate(current_price)
        
        # 更新最高价
        position.update_high_price(current_price)
        
        # 1. 基础止盈
        if profit_rate >= self.stop_params['take_profit']:
            return True, f'止盈: 浮盈{profit_rate*100:.1f}%'
        
        # 2. 基础止损
        if profit_rate <= self.stop_params['stop_loss']:
            return True, f'止损: 浮亏{abs(profit_rate)*100:.1f}%'
        
        # 3. 移动止损（追踪止损）
        max_profit_rate = position.get_max_profit_rate()
        if max_profit_rate >= self.stop_params['trailing_stop_trigger']:
            # 计算从最高点的回撤
            drawdown = max_profit_rate - profit_rate
            
            # 回撤超过阈值，触发移动止损
            if drawdown >= self.stop_params['trailing_stop_pct']:
                # 检查是否还能保住最低利润
                min_profit = self.stop_params['trailing_stop_min_profit']
                if profit_rate >= min_profit:
                    return True, f'移动止损: 从最高{max_profit_rate*100:.1f}%回撤{drawdown*100:.1f}%'
                else:
                    return True, f'保底止损: 保住{min_profit*100:.1f}%利润'
        
        return False, None
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.STRATEGY_NAME}>"


class Position:
    """
    持仓信息类
    
    用于在策略间传递持仓信息
    支持动态止盈止损的追踪功能
    """
    def __init__(
        self, 
        stock_code: str, 
        market: str, 
        name: str, 
        buy_date: str, 
        buy_price: float, 
        volume: int, 
        commission: float
    ):
        self.stock_code = stock_code
        self.market = market
        self.name = name
        self.buy_date = buy_date
        self.buy_price = buy_price
        self.volume = volume
        self.commission = commission
        self.sell_commission = 0.0
        self.hold_days = 0
        
        # 动态止盈止损相关
        self.high_price = buy_price  # 持仓期间最高价
        self.stop_loss_price = None  # 动态止损价
    
    def update_high_price(self, current_price: float):
        """更新最高价"""
        if current_price > self.high_price:
            self.high_price = current_price
    
    def get_max_profit_rate(self) -> float:
        """获取持仓期间最大盈亏比例"""
        if self.buy_price > 0:
            return (self.high_price - self.buy_price) / self.buy_price
        return 0.0
    
    def get_current_value(self, current_price: float) -> float:
        """获取当前市值"""
        return self.volume * current_price
    
    def get_profit_rate(self, current_price: float) -> float:
        """计算盈亏比例"""
        if self.buy_price > 0:
            return (current_price - self.buy_price) / self.buy_price
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'market': self.market,
            'name': self.name,
            'buy_date': self.buy_date,
            'buy_price': self.buy_price,
            'volume': self.volume,
            'commission': self.commission,
            'sell_commission': self.sell_commission,
            'hold_days': self.hold_days,
            'high_price': self.high_price,
            'max_profit_rate': self.get_max_profit_rate()
        }
    
    def __repr__(self):
        return (f"<Position: {self.stock_code} {self.name}, "
                f"价格: {self.buy_price:.2f}, "
                f"数量: {self.volume}, "
                f"持仓天数: {self.hold_days}>")
