"""
策略模块

提供按时间遍历回测的策略接口和实现
"""

from .base_strategy import BaseStrategy, Position
from .value_strategy_time import ValueStrategyTimeBased
from .ma_strategy_time import MAStrategyTimeBased


# 策略注册表
STRATEGY_REGISTRY = {
    'value': ValueStrategyTimeBased,
    'ma': MAStrategyTimeBased,
    'ValueStrategy': ValueStrategyTimeBased,
    'MAStrategy': MAStrategyTimeBased,
}


def get_strategy(name: str, params: dict = None) -> BaseStrategy:
    """
    根据名称获取策略实例
    
    Args:
        name: 策略名称（支持简称和全称）
        params: 策略参数
        
    Returns:
        BaseStrategy: 策略实例
        
    Raises:
        ValueError: 策略名称不存在
    """
    if name not in STRATEGY_REGISTRY:
        available = list(set(STRATEGY_REGISTRY.keys()))
        raise ValueError(f"策略 '{name}' 不存在，可用策略: {available}")
    
    strategy_class = STRATEGY_REGISTRY[name]
    return strategy_class(params=params)


def list_strategies() -> dict:
    """
    列出所有可用策略
    
    Returns:
        dict: {简称: 策略类}
    """
    return {
        'value': ValueStrategyTimeBased,
        'ma': MAStrategyTimeBased,
    }


def register_strategy(name: str, strategy_class: type):
    """
    注册自定义策略
    
    Args:
        name: 策略简称
        strategy_class: 策略类（必须继承 BaseStrategy）
    """
    if not issubclass(strategy_class, BaseStrategy):
        raise TypeError(f"策略类必须继承 BaseStrategy")
    
    STRATEGY_REGISTRY[name] = strategy_class
    STRATEGY_REGISTRY[strategy_class.STRATEGY_NAME] = strategy_class


__all__ = [
    'BaseStrategy',
    'Position',
    'ValueStrategyTimeBased',
    'MAStrategyTimeBased',
    'get_strategy',
    'list_strategies',
    'register_strategy',
    'STRATEGY_REGISTRY',
]
