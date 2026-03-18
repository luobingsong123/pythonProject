"""
策略基类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StrategyResult(BaseModel):
    """策略结果"""
    symbol: str = Field(..., description="股票代码")
    exchange: str = Field(..., description="交易所代码")
    name: str = Field(..., description="股票名称")
    score: float = Field(..., description="策略得分")
    signals: Dict[str, Any] = Field(default_factory=dict, description="信号详情")
    

class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, strategy_id: str, params: Optional[Dict[str, Any]] = None):
        """
        初始化策略
        
        Args:
            strategy_id: 策略ID
            params: 策略参数
        """
        self.strategy_id = strategy_id
        self.params = params or {}
    
    @abstractmethod
    def select(
        self,
        date: str,
        daily_data: List[Dict[str, Any]],
        **kwargs
    ) -> List[StrategyResult]:
        """
        执行选股
        
        Args:
            date: 日期
            daily_data: 日线数据列表
            **kwargs: 其他参数
            
        Returns:
            List[StrategyResult]: 选股结果
        """
        pass
    
    @abstractmethod
    def filter(self, stock_data: Dict[str, Any]) -> bool:
        """
        单只股票过滤
        
        Args:
            stock_data: 股票数据
            
        Returns:
            bool: 是否通过过滤
        """
        pass
    
    def get_name(self) -> str:
        """获取策略名称"""
        return self.strategy_id
