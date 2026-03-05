"""
并行信号检查器

提供向量化批处理 + 多进程并行的混合优化方案

优化策略：
1. 向量化批处理：使用 pandas/numpy 批量计算，减少 Python 循环开销
2. 多进程并行：当股票数量较大时，将批处理任务分配到多个进程执行
3. 自适应切换：根据股票数量自动选择最优执行方式
4. 进程池复用：在 Windows 平台上预创建进程池，避免重复启动开销
"""

import os
import multiprocessing as mp
from multiprocessing import shared_memory
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple, Optional, Callable
import pandas as pd
import numpy as np
import pickle
import warnings
import atexit
import logging

# Windows 多进程支持
if os.name == 'nt':
    try:
        mp.set_start_method('spawn', force=True)
    except RuntimeError:
        pass  # 已经设置过

# 获取日志
logger = logging.getLogger(__name__)

# 全局进程池（单例模式）
_global_pool: Optional[ProcessPoolExecutor] = None
_pool_ref_count = 0


def _get_global_pool(max_workers: int) -> ProcessPoolExecutor:
    """获取全局进程池（单例）"""
    global _global_pool, _pool_ref_count
    
    if _global_pool is None:
        logger.info(f"[进程池] 创建全局进程池，max_workers={max_workers}")
        _global_pool = ProcessPoolExecutor(max_workers=max_workers)
        _pool_ref_count = 0
        
        # 注册清理函数
        atexit.register(_cleanup_global_pool)
    
    _pool_ref_count += 1
    return _global_pool


def _cleanup_global_pool():
    """清理全局进程池"""
    global _global_pool
    
    if _global_pool is not None:
        logger.info("[进程池] 关闭全局进程池")
        _global_pool.shutdown(wait=True)
        _global_pool = None


class ParallelSignalChecker:
    """
    并行信号检查器
    
    支持三种模式：
    1. 串行模式（股票数量少时）
    2. 向量化批处理模式（中等数量时）
    3. 多进程并行 + 向量化（大量股票时）
    
    优化特性：
    - 进程池复用：避免 Windows 平台重复启动进程的开销
    - 自适应阈值：根据数据量自动选择最优执行模式
    """
    
    # 阈值配置（降低阈值，更容易触发多进程）
    SERIAL_THRESHOLD = 30         # 低于此数量使用串行（降低以便测试）
    PARALLEL_THRESHOLD = 100      # 高于此数量使用多进程（降低以便测试）
    
    def __init__(
        self,
        strategy,
        max_workers: Optional[int] = None,
        enable_parallel: bool = True
    ):
        """
        初始化并行信号检查器
        
        Args:
            strategy: 策略对象（BaseStrategy子类实例）
            max_workers: 最大进程数，默认为 CPU 核心数
            enable_parallel: 是否启用多进程并行
        """
        self.strategy = strategy
        self.max_workers = max_workers or os.cpu_count()
        self.enable_parallel = enable_parallel
        
        # 预创建进程池（如果启用并行）
        self._pool: Optional[ProcessPoolExecutor] = None
        if self.enable_parallel:
            self._pool = _get_global_pool(self.max_workers)
            logger.info(f"[ParallelSignalChecker] 初始化完成，阈值: SERIAL={self.SERIAL_THRESHOLD}, PARALLEL={self.PARALLEL_THRESHOLD}")
    
    def __del__(self):
        """析构时释放进程池引用"""
        global _pool_ref_count
        
        if self._pool is not None:
            _pool_ref_count -= 1
            
            # 如果没有引用了，关闭进程池
            if _pool_ref_count <= 0:
                _cleanup_global_pool()
    
    def check_buy_signals(
        self,
        stock_codes: List[str],
        markets: List[str],
        stock_data_map: Dict[str, pd.DataFrame],
        current_date: str
    ) -> List[Dict[str, Any]]:
        """
        批量检查买入信号（自适应模式选择）
        
        Args:
            stock_codes: 股票代码列表
            markets: 市场代码列表
            stock_data_map: 股票数据字典
            current_date: 当前日期
            
        Returns:
            List[Dict]: 信号结果列表
        """
        total_stocks = len(stock_codes)
        
        # 根据股票数量选择执行模式
        if not self.enable_parallel or total_stocks < self.SERIAL_THRESHOLD:
            # 模式1：串行批处理（小规模）
            logger.debug(f"[{current_date}] 串行批处理模式，股票数={total_stocks}")
            return self._check_buy_signals_vectorized(
                stock_codes, markets, stock_data_map, current_date
            )
        elif total_stocks < self.PARALLEL_THRESHOLD:
            # 模式2：向量化批处理（中等规模）
            logger.debug(f"[{current_date}] 向量化批处理模式，股票数={total_stocks}")
            return self._check_buy_signals_vectorized(
                stock_codes, markets, stock_data_map, current_date
            )
        else:
            # 模式3：多进程并行 + 向量化（大规模）
            logger.info(f"[{current_date}] 🚀 多进程并行模式，股票数={total_stocks}, 进程数={self.max_workers}")
            return self._check_buy_signals_parallel(
                stock_codes, markets, stock_data_map, current_date
            )
    
    def _check_buy_signals_vectorized(
        self,
        stock_codes: List[str],
        markets: List[str],
        stock_data_map: Dict[str, pd.DataFrame],
        current_date: str
    ) -> List[Dict[str, Any]]:
        """
        向量化批处理检查买入信号
        """
        return self.strategy.check_buy_signal_batch(
            stock_codes, markets, stock_data_map, current_date
        )
    
    def _check_buy_signals_parallel(
        self,
        stock_codes: List[str],
        markets: List[str],
        stock_data_map: Dict[str, pd.DataFrame],
        current_date: str
    ) -> List[Dict[str, Any]]:
        """
        多进程并行检查买入信号（使用复用的进程池）
        """
        import time
        start_time = time.time()
        
        # 计算每个进程处理的股票数量
        chunk_size = max(1, len(stock_codes) // self.max_workers)
        chunks = []
        
        for i in range(0, len(stock_codes), chunk_size):
            chunk_codes = stock_codes[i:i + chunk_size]
            chunk_markets = markets[i:i + chunk_size]
            # 只传递当前 chunk 需要的数据
            chunk_data = {code: stock_data_map[code] for code in chunk_codes if code in stock_data_map}
            chunks.append((chunk_codes, chunk_markets, chunk_data))
        
        logger.debug(f"[{current_date}] 分块完成，共{len(chunks)}块，每块约{chunk_size}只股票")
        
        # 多进程执行（复用进程池）
        all_results = [None] * len(stock_codes)  # 预分配结果列表
        
        # 使用预创建的进程池
        futures = {
            self._pool.submit(
                _worker_check_buy_signals,
                self.strategy.STRATEGY_NAME,
                self.strategy.params,
                self.strategy.stop_params,
                codes, mkts, data, current_date
            ): (codes, i)
            for i, (codes, mkts, data) in enumerate(chunks)
        }
        
        for future in as_completed(futures):
            chunk_codes, chunk_idx = futures[future]
            try:
                chunk_results = future.result()
                # 将结果放回正确位置
                start_idx = chunk_idx * chunk_size
                for j, result in enumerate(chunk_results):
                    if start_idx + j < len(all_results):
                        all_results[start_idx + j] = result
            except Exception as e:
                warnings.warn(f"并行任务执行失败: {e}")
                # 回退到串行处理这个 chunk
                chunk_markets = markets[chunk_idx * chunk_size:(chunk_idx + 1) * chunk_size]
                chunk_data = {code: stock_data_map.get(code) for code in chunk_codes}
                fallback_results = self.strategy.check_buy_signal_batch(
                    chunk_codes, chunk_markets, chunk_data, current_date
                )
                start_idx = chunk_idx * chunk_size
                for j, result in enumerate(fallback_results):
                    if start_idx + j < len(all_results):
                        all_results[start_idx + j] = result
        
        # 填充缺失结果
        for i, result in enumerate(all_results):
            if result is None:
                all_results[i] = {
                    'stock_code': stock_codes[i],
                    'market': markets[i],
                    'is_signal': False,
                    'signal_strength': 0.0,
                    'signal_info': None
                }
        
        elapsed = time.time() - start_time
        logger.debug(f"[{current_date}] 多进程并行完成，耗时={elapsed:.2f}秒")
        
        return all_results


def _worker_check_buy_signals(
    strategy_class_name: str,
    strategy_params: Dict,
    stop_params: Dict,
    stock_codes: List[str],
    markets: List[str],
    stock_data_map: Dict[str, pd.DataFrame],
    current_date: str
) -> List[Dict[str, Any]]:
    """
    子进程工作函数：检查买入信号
    
    Args:
        strategy_class_name: 策略名称或类名
        strategy_params: 策略参数
        stop_params: 止盈止损参数
        stock_codes: 股票代码列表
        markets: 市场代码列表
        stock_data_map: 股票数据字典
        current_date: 当前日期
        
    Returns:
        List[Dict]: 信号结果列表
    """
    # 动态导入策略类
    from utils.strategies import get_strategy, STRATEGY_REGISTRY
    
    try:
        # 创建策略实例（尝试多种名称查找）
        strategy = None
        names_to_try = [
            strategy_class_name,           # 原名（如 "CodeBuddyStrategy"）
            strategy_class_name.lower(),   # 小写（如 "codebuddystatregy"）
        ]
        
        for name in names_to_try:
            try:
                strategy = get_strategy(name)
                break
            except ValueError:
                continue
        
        if strategy is None:
            # 如果都失败，返回空结果
            return [{
                'stock_code': code,
                'market': mkt,
                'is_signal': False,
                'signal_strength': 0.0,
                'signal_info': None
            } for code, mkt in zip(stock_codes, markets)]
        
        # 设置参数
        strategy.params = strategy_params
        strategy.stop_params = stop_params
        
        # 执行批处理
        return strategy.check_buy_signal_batch(
            stock_codes, markets, stock_data_map, current_date
        )
    except Exception as e:
        # 返回空结果
        warnings.warn(f"子进程策略检查失败: {e}")
        return [{
            'stock_code': code,
            'market': mkt,
            'is_signal': False,
            'signal_strength': 0.0,
            'signal_info': None
        } for code, mkt in zip(stock_codes, markets)]


class OptimizedDataPreloader:
    """
    优化的数据预加载器
    
    提供数据切片功能，减少多进程间的数据传输量
    """
    
    def __init__(self, data_preloader):
        """
        初始化优化数据预加载器
        
        Args:
            data_preloader: 原始 DataPreloader 实例
        """
        self.data_preloader = data_preloader
        self._slice_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
    
    def get_batch_data(
        self,
        stock_codes: List[str],
        current_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        获取批量股票数据（已切片到当前日期）
        
        Args:
            stock_codes: 股票代码列表
            current_date: 当前日期
            
        Returns:
            Dict[str, DataFrame]: 股票数据字典
        """
        cache_key = current_date
        if cache_key not in self._slice_cache:
            self._slice_cache[cache_key] = {}
        
        result = {}
        current_date_dt = pd.to_datetime(current_date)
        
        for code in stock_codes:
            # 优先从缓存获取
            if code in self._slice_cache[cache_key]:
                result[code] = self._slice_cache[cache_key][code]
                continue
            
            # 从预加载数据中获取
            if code not in self.data_preloader.all_stock_data:
                continue
            
            stock_data = self.data_preloader.all_stock_data[code].copy()
            
            # 处理时区 - 确保索引无时区
            if stock_data.index.tz is not None:
                stock_data.index = stock_data.index.tz_localize(None)
            
            # 切片到当前日期
            sliced = stock_data[stock_data.index <= current_date_dt]
            result[code] = sliced
            self._slice_cache[cache_key][code] = sliced
        
        return result
    
    def clear_cache(self):
        """清空缓存"""
        self._slice_cache.clear()
