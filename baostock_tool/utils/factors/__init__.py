"""
Alpha因子计算模块

提供各类alpha因子的计算功能

主要组件:
    - BaseFactor: 因子基类
    - FactorUtils: 因子计算工具函数
    - FactorEngine: 因子计算引擎
    - alpha: alpha系列因子（alpha001-191）
    - worldalpha: worldalpha系列因子（worldalpha001-101，部分可计算）
"""

from .base_factor import BaseFactor, FactorEngine
from .factor_utils import FactorUtils

# 导出核心类
__all__ = [
    'BaseFactor',
    'FactorEngine',
    'FactorUtils',
]

__version__ = '1.0.0'
__author__ = 'Alpha Factor Team'
