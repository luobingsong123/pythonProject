"""
按时间遍历所有个股的标准回测脚本

特点：
1. 按交易日顺序遍历，每个时间点检查所有股票信号
2. 支持总资金管理（跨股票）
3. 支持选股机制和仓位控制
4. 支持策略模块化替换
5. 更接近实盘交易场景

使用方式：
    # 方式1：使用默认策略
    backtester = TimeBasedBacktester()
    backtester.run_backtest()
    
    # 方式2：使用指定策略
    from utils.strategies import get_strategy
    strategy = get_strategy('value', params={'max_pe_ttm': 25})
    backtester = TimeBasedBacktester(strategy=strategy)
    backtester.run_backtest()
    
    # 方式3：使用自定义策略
    from utils.strategies import BaseStrategy
    class MyStrategy(BaseStrategy):
        ...
    backtester = TimeBasedBacktester(strategy=MyStrategy())

本代码仅用于回测研究，实盘使用风险自担
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from datetime import datetime, timedelta
from collections import defaultdict
import config
from utils.logger_utils import setup_logger
from database_schema.strategy_trigger_db import StrategyTriggerDB
from utils.strategies import BaseStrategy, Position, get_strategy, list_strategies
import time
import os
import json

# ============ 回测配置 ============
BACKTEST_CONFIG = {
    'start_date': '2024-01-01',       # 回测开始日期
    'end_date': '2024-12-31',         # 回测结束日期
    'initial_cash': 10000000,         # 初始资金
    'commission': 0.001,              # 手续费率（0.1%）
    'slippage_perc': 0.001,           # 滑点率（0.1%）
    'max_positions': 100,             # 最大持仓数量
    'max_daily_buys': 10,             # 每日最大开仓数量
    'position_size_pct': 0.01,        # 单只股票仓位比例（%）
    'min_hold_days': 1,               # 最小持仓天数（T+1限制）
    'lookback_days': 365,             # 历史数据回溯天数
    
    # ========== 回避时间段配置 ==========
    'enable_blackout': False,         # 是否启用回避功能（默认关闭）
    'blackout_periods': [
        # 回避时间段列表，每个时间段包含：
        # - force_sell_date: 该日期后的第一个交易日强制卖出所有持仓
        # - resume_buy_date: 该日期后才允许买入
        # - reason: 原因说明（可选）
        # 示例：
        # {
        #     'force_sell_date': '2025-04-01',   # 4月1日后第一个交易日强制卖出
        #     'resume_buy_date': '2025-04-20',   # 4月20日后才能买入
        #     'reason': '国际关税政策波动期'
        # }
    ],
}

os.makedirs("csv", exist_ok=True)
os.makedirs("log", exist_ok=True)

db_config = config.get_db_config()
log_config = config.get_log_config()
date_config = config.get_backtrade_date_config()

# 使用配置文件中的日期覆盖默认配置
BACKTEST_CONFIG['start_date'] = date_config.get("start_date", BACKTEST_CONFIG['start_date'])
BACKTEST_CONFIG['end_date'] = date_config.get("end_date", BACKTEST_CONFIG['end_date'])

logger = setup_logger(
    logger_name=__name__,
    log_level=log_config["log_level"],
    log_dir=log_config["log_dir"]
)

db_url = URL.create(
    drivername="mysql+pymysql",
    username=db_config["user"],
    password=db_config["password"],
    host=db_config["host"],
    port=db_config["port"],
    database=db_config["database"]
)
engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)


class TimeBasedBacktester:
    """
    按时间遍历的回测引擎
    
    支持策略模块化，可以通过 strategy 参数注入不同的策略
    """
    
    def __init__(self, config_dict=None, strategy=None):
        """
        初始化回测引擎
        
        Args:
            config_dict: 回测配置字典
            strategy: 策略对象（继承自 BaseStrategy），如果为 None 则使用默认价值策略
        """
        self.config = config_dict or BACKTEST_CONFIG.copy()
        
        # 初始化策略
        if strategy is None:
            # 使用默认价值策略
            from utils.strategies import ValueStrategyTimeBased
            self.strategy = ValueStrategyTimeBased()
        elif isinstance(strategy, str):
            # 传入策略名称字符串
            self.strategy = get_strategy(strategy)
        elif isinstance(strategy, BaseStrategy):
            # 直接传入策略实例
            self.strategy = strategy
        else:
            raise TypeError(f"strategy 参数类型错误，期望 str 或 BaseStrategy，实际为 {type(strategy)}")
        
        self.cash = self.config['initial_cash']
        self.positions = {}  # {stock_code: Position}
        self.trading_records = []  # 交易记录
        self.daily_values = []  # 每日资产记录
        self.trigger_points = []  # 触发点位记录
        self.all_stock_data = {}  # 预加载的所有股票数据 {stock_code: DataFrame}
        self.stock_info_map = {}  # 股票信息映射 {stock_code: (market, name)}
        
        # 统计数据
        self.total_buy_commission = 0
        self.total_sell_commission = 0
        self.profit_trade_count = 0
        self.loss_trade_count = 0
        
    def get_trade_calendar(self, start_date, end_date):
        """获取交易日历"""
        query = f"""
        SELECT calendar_date 
        FROM trade_calendar 
        WHERE is_trading_day = 1
          AND calendar_date >= '{start_date}'
          AND calendar_date <= '{end_date}'
        ORDER BY calendar_date
        """
        df = pd.read_sql(query, engine)
        df['calendar_date'] = pd.to_datetime(df['calendar_date'])
        return df['calendar_date'].tolist()
    
    def get_stock_list(self):
        """获取股票列表"""
        query = """
        SELECT market, code_int, name
        FROM stock_basic_info 
        WHERE (market = 'sh' AND code_int > 600000 AND code_int < 610000)
           OR (market = 'sz' AND code_int > 0 AND code_int < 310000)
        ORDER BY code_int
        """
        df = pd.read_sql(query, engine)
        return df
    
    def preload_all_stock_data(self, stock_codes, start_date, end_date, lookback_days=365):
        """
        预加载所有股票的完整历史数据到内存
        
        Args:
            stock_codes: 股票代码列表 [(market, code_int, name), ...]
            start_date: 回测开始日期
            end_date: 回测结束日期
            lookback_days: 历史数据回溯天数
            
        Returns:
            dict: {stock_code: DataFrame}
        """
        if not stock_codes:
            return {}
        
        # 计算数据起始日期（向前推lookback_days天）
        data_start_date = (pd.to_datetime(start_date) - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        logger.info(f"开始预加载股票数据...")
        logger.info(f"  数据时间范围: {data_start_date} 至 {end_date}")
        logger.info(f"  股票数量: {len(stock_codes)}")
        
        # 构建股票代码条件
        conditions = []
        for market, code_int, name in stock_codes:
            conditions.append(f"(market = '{market}' AND code_int = {code_int})")
            # 保存股票信息映射
            self.stock_info_map[str(code_int)] = (market, name)
        
        where_clause = " OR ".join(conditions)
        
        query = f"""
        SELECT market, code_int, date, open, high, low, close, volume, amount, 
               pctChg, peTTM, psTTM, pcfNcfTTM, pbMRQ
        FROM stock_daily_data
        WHERE ({where_clause})
          AND frequency = 'd'
          AND date >= '{data_start_date}'
          AND date <= '{end_date}'
        ORDER BY code_int, date
        """
        
        df = pd.read_sql(query, engine)
        
        if df.empty:
            logger.warning("未查询到任何股票数据")
            return {}
        
        df['date'] = pd.to_datetime(df['date'])
        
        # 按股票分组
        result = {}
        for (market, code_int), group in df.groupby(['market', 'code_int']):
            stock_code = str(code_int)
            group = group.sort_values('date')
            group.set_index('date', inplace=True)
            result[stock_code] = group
        
        self.all_stock_data = result
        
        # 统计信息
        total_rows = len(df)
        total_stocks = len(result)
        avg_rows_per_stock = total_rows / total_stocks if total_stocks > 0 else 0
        
        logger.info(f"数据预加载完成:")
        logger.info(f"  总数据行数: {total_rows:,}")
        logger.info(f"  股票数量: {total_stocks}")
        logger.info(f"  平均每只股票数据行数: {avg_rows_per_stock:.0f}")
        logger.info(f"  内存估算: ~{total_rows * 0.001:.1f} MB")
        
        return result
    
    def get_stock_data_up_to_date(self, stock_code, current_date):
        """
        从预加载数据中获取指定日期之前的历史数据
        
        Args:
            stock_code: 股票代码
            current_date: 当前日期
            
        Returns:
            DataFrame: 截止到当前日期的历史数据
        """
        if stock_code not in self.all_stock_data:
            return None
        
        stock_data = self.all_stock_data[stock_code]
        current_date_dt = pd.to_datetime(current_date)
        
        # 筛选截止到当前日期的数据
        return stock_data[stock_data.index <= current_date_dt]
    
    def get_stock_data_on_date(self, stock_code, current_date):
        """
        从预加载数据中获取指定日期的单只股票数据
        
        Args:
            stock_code: 股票代码
            current_date: 当前日期
            
        Returns:
            Series: 当日数据
        """
        if stock_code not in self.all_stock_data:
            return None
        
        stock_data = self.all_stock_data[stock_code]
        current_date_dt = pd.to_datetime(current_date)
        
        if current_date_dt not in stock_data.index:
            return None
        
        return stock_data.loc[current_date_dt]
    
    def execute_buy(self, stock_code, market, name, price, volume, current_date, signal_info=None):
        """执行买入"""
        if stock_code in self.positions:
            logger.debug(f"{current_date}: 股票 {stock_code} 已持仓，跳过买入")
            return False
        
        # 计算费用
        amount = price * volume
        commission = amount * self.config['commission']
        slippage_cost = amount * self.config['slippage_perc']
        total_cost = amount + commission + slippage_cost
        
        if total_cost > self.cash:
            logger.debug(f"{current_date}: 资金不足，无法买入 {stock_code}")
            return False
        
        # 扣除资金
        self.cash -= total_cost
        self.total_buy_commission += commission
        
        # 创建持仓
        position = Position(
            stock_code=stock_code,
            market=market,
            name=name,
            buy_date=current_date,
            buy_price=price,
            volume=volume,
            commission=commission
        )
        self.positions[stock_code] = position
        
        # 记录交易
        trade_record = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': market,
            'name': name,
            'action': 'buy',
            'price': price,
            'volume': volume,
            'amount': amount,
            'commission': commission,
            'signal_info': signal_info
        }
        self.trading_records.append(trade_record)
        
        # 记录触发点位
        trigger_point = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': market,
            'name': name,
            'trigger_type': 'buy',
            'price': float(price),
            'volume': float(volume),
            'commission': float(commission),
            'signal_info': signal_info
        }
        self.trigger_points.append(trigger_point)
        
        # 计算当前总资产和盈亏比例
        total_value = self.cash
        for pos_code, pos in self.positions.items():
            total_value += pos.get_current_value(price if pos_code == stock_code else pos.buy_price)
        profit_rate = (total_value / self.config['initial_cash'] - 1) * 100
        
        logger.info(f"[买入] {current_date} | {stock_code:0>6} {name} | "
                   f"价格: {price:.2f} | 数量: {volume} | 金额: {amount:.2f} | 手续费: {commission:.2f} | "
                   f"总资产: {total_value:,.2f} | 盈亏: {profit_rate:+.2f}%")
        
        return True
    
    def execute_sell(self, stock_code, price, volume, current_date, sell_reason=''):
        """执行卖出"""
        if stock_code not in self.positions:
            return False
        
        position = self.positions[stock_code]
        
        # 计算费用
        amount = price * volume
        commission = amount * self.config['commission']
        slippage_cost = amount * self.config['slippage_perc']
        actual_amount = amount - commission - slippage_cost
        
        # 增加资金
        self.cash += actual_amount
        self.total_sell_commission += commission
        position.sell_commission = commission
        
        # 计算盈亏
        profit = amount - position.buy_price * volume
        profit_rate = position.get_profit_rate(price)
        
        # 统计盈亏交易
        if profit > 0:
            self.profit_trade_count += 1
        else:
            self.loss_trade_count += 1
        
        # 记录交易
        trade_record = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': position.market,
            'name': position.name,
            'action': 'sell',
            'price': price,
            'volume': volume,
            'amount': amount,
            'commission': commission,
            'profit': profit,
            'profit_rate': profit_rate,
            'hold_days': position.hold_days,
            'sell_reason': sell_reason
        }
        self.trading_records.append(trade_record)
        
        # 记录触发点位
        trigger_point = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': position.market,
            'name': position.name,
            'trigger_type': 'sell',
            'price': float(price),
            'volume': float(volume),
            'commission': float(commission),
            'profit': float(profit),
            'profit_rate': float(profit_rate),
            'hold_days': position.hold_days,
            'sell_reason': sell_reason
        }
        self.trigger_points.append(trigger_point)
        
        # 计算当前总资产和盈亏比例（卖出后）
        total_value = self.cash
        for pos_code, pos in self.positions.items():
            if pos_code != stock_code:  # 排除已卖出的股票
                total_value += pos.get_current_value(pos.buy_price)
        total_profit_rate = (total_value / self.config['initial_cash'] - 1) * 100
        
        logger.info(f"[卖出] {current_date} | {stock_code:0>6} {position.name} | "
                   f"价格: {price:.2f} | 数量: {volume} | 金额: {amount:.2f} | "
                   f"盈亏: {profit:.2f} ({profit_rate*100:.2f}%) | 原因: {sell_reason} | "
                   f"总资产: {total_value:,.2f} | 总盈亏: {total_profit_rate:+.2f}%")
        
        # 移除持仓
        del self.positions[stock_code]
        
        return True
    
    def execute_add_position(self, stock_code, add_price, add_volume, current_date, add_info=None):
        """
        执行补仓
        
        Args:
            stock_code: 股票代码
            add_price: 补仓价格
            add_volume: 补仓数量
            current_date: 当前日期
            add_info: 补仓信号信息
            
        Returns:
            bool: 是否成功补仓
        """
        if stock_code not in self.positions:
            return False
        
        position = self.positions[stock_code]
        
        # 计算补仓费用
        amount = add_price * add_volume
        commission = amount * self.config['commission']
        slippage_cost = amount * self.config['slippage_perc']
        total_cost = amount + commission + slippage_cost
        
        if total_cost > self.cash:
            logger.debug(f"{current_date}: 资金不足，无法补仓 {stock_code}")
            return False
        
        # 扣除资金
        self.cash -= total_cost
        self.total_buy_commission += commission
        
        # 更新持仓信息
        position.update_avg_cost(add_price, add_volume)
        
        # 记录交易
        trade_record = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': position.market,
            'name': position.name,
            'action': 'add_position',
            'price': add_price,
            'volume': add_volume,
            'amount': amount,
            'commission': commission,
            'signal_info': add_info
        }
        self.trading_records.append(trade_record)
        
        # 记录触发点位
        trigger_point = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': position.market,
            'name': position.name,
            'trigger_type': 'add_position',
            'price': float(add_price),
            'volume': float(add_volume),
            'commission': float(commission),
            'signal_info': add_info
        }
        self.trigger_points.append(trigger_point)
        
        # 计算当前总资产和盈亏比例
        total_value = self.cash
        for pos_code, pos in self.positions.items():
            total_value += pos.get_current_value(add_price if pos_code == stock_code else pos.buy_price)
        profit_rate = (total_value / self.config['initial_cash'] - 1) * 100
        
        logger.info(f"[补仓] {current_date} | {stock_code:0>6} {position.name} | "
                   f"价格: {add_price:.2f} | 数量: {add_volume} | 金额: {amount:.2f} | 手续费: {commission:.2f} | "
                   f"新持仓: {position.volume} | 新成本: {position.avg_cost:.2f} | "
                   f"总资产: {total_value:,.2f} | 盈亏: {profit_rate:+.2f}%")
        
        return True
    
    def calculate_portfolio_value(self, current_date):
        """计算总资产（使用预加载数据）"""
        total_value = self.cash
        current_date_dt = pd.to_datetime(current_date)
        
        for stock_code, position in self.positions.items():
            if stock_code in self.all_stock_data:
                stock_data = self.all_stock_data[stock_code]
                if current_date_dt in stock_data.index:
                    current_price = stock_data.loc[current_date_dt, 'close']
                    total_value += position.get_current_value(current_price)
            else:
                # 使用买入价格估算
                total_value += position.get_current_value(position.buy_price)
        
        return total_value
    
    def _check_blackout_force_sell(self, current_date: str, trading_dates: list):
        """
        检查是否需要在当前日期强制卖出（回避时间段开始）
        
        Args:
            current_date: 当前日期
            trading_dates: 交易日历
            
        Returns:
            Tuple[bool, str]: (是否强制卖出, 原因)
        """
        if not self.config.get('enable_blackout', False):
            return False, ''
        
        blackout_periods = self.config.get('blackout_periods', [])
        if not blackout_periods:
            return False, ''
        
        current_date_dt = pd.to_datetime(current_date)
        
        for period in blackout_periods:
            force_sell_date = pd.to_datetime(period['force_sell_date'])
            
            # 找到 force_sell_date 之后的第一个交易日
            for trade_date in trading_dates:
                if trade_date >= force_sell_date:
                    # 如果当前日期就是这个交易日，则强制卖出
                    if trade_date.strftime('%Y-%m-%d') == current_date:
                        reason = period.get('reason', '回避时间段开始')
                        return True, f'强制卖出: {reason}'
                    break
        
        return False, ''
    
    def _is_in_blackout_period(self, current_date: str):
        """
        检查当前是否在禁止买入时间段内
        
        Args:
            current_date: 当前日期
            
        Returns:
            Tuple[bool, str]: (是否禁止买入, 原因)
        """
        if not self.config.get('enable_blackout', False):
            return False, ''
        
        blackout_periods = self.config.get('blackout_periods', [])
        if not blackout_periods:
            return False, ''
        
        current_date_dt = pd.to_datetime(current_date)
        
        for period in blackout_periods:
            force_sell_date = pd.to_datetime(period['force_sell_date'])
            resume_buy_date = pd.to_datetime(period['resume_buy_date'])
            
            # 在强制卖出日期到恢复买入日期之间，禁止买入
            if force_sell_date <= current_date_dt < resume_buy_date:
                reason = period.get('reason', '回避时间段')
                return True, f'禁止买入: {reason}'
        
        return False, ''
    
    def run_backtest(self, strategy_name='TimeBasedStrategy', save_to_db=False):
        """
        执行回测
        
        Args:
            strategy_name: 策略名称
            save_to_db: 是否保存结果到数据库
        """
        start_time = time.time()
        
        # 初始化策略数据库
        strategy_db = None
        if save_to_db:
            strategy_db = StrategyTriggerDB()
            # 删除旧的每日记录
            deleted_count = strategy_db.delete_daily_records(
                strategy_name=strategy_name,
                backtest_start_date=self.config['start_date'],
                backtest_end_date=self.config['end_date']
            )
            if deleted_count > 0:
                logger.info(f"已删除旧的每日记录: {deleted_count} 条")
        
        # 获取交易日历
        trading_dates = self.get_trade_calendar(
            self.config['start_date'],
            self.config['end_date']
        )
        
        if not trading_dates:
            logger.error("无法获取交易日历")
            return None
        
        logger.info(f"{'='*60}")
        logger.info(f"开始按时间遍历回测")
        logger.info(f"策略: {strategy_name}")
        logger.info(f"回测期间: {self.config['start_date']} 至 {self.config['end_date']}")
        logger.info(f"初始资金: {self.config['initial_cash']:,.0f}")
        logger.info(f"最大持仓: {self.config['max_positions']} 只")
        logger.info(f"交易日数: {len(trading_dates)} 天")
        
        # 显示回避功能状态
        if self.config.get('enable_blackout', False):
            blackout_periods = self.config.get('blackout_periods', [])
            logger.info(f"回避功能: 已启用，共 {len(blackout_periods)} 个回避时间段")
            for idx, period in enumerate(blackout_periods, 1):
                logger.info(f"  时间段{idx}: {period.get('force_sell_date')} 卖出 -> "
                           f"{period.get('resume_buy_date')} 恢复买入 ({period.get('reason', '未指定原因')})")
        else:
            logger.info(f"回避功能: 未启用")
        
        logger.info(f"{'='*60}")
        
        # 获取股票列表
        stock_list_df = self.get_stock_list()
        stock_codes = [(row['market'], row['code_int'], row['name']) 
                       for _, row in stock_list_df.iterrows()]
        
        logger.info(f"股票总数: {len(stock_codes)}")
        
        # ========== 核心优化：预加载所有数据到内存 ==========
        preload_start = time.time()
        self.preload_all_stock_data(
            stock_codes,
            self.config['start_date'],
            self.config['end_date'],
            self.config['lookback_days']
        )
        preload_time = time.time() - preload_start
        logger.info(f"数据预加载耗时: {preload_time:.2f} 秒")
        logger.info(f"{'='*60}")
        
        # 按日期遍历
        for i, trade_date in enumerate(trading_dates):
            current_date = trade_date.strftime('%Y-%m-%d')
            current_date_dt = pd.to_datetime(current_date)
            
            # 进度显示
            if (i + 1) % 50 == 0 or i == 0:
                logger.info(f"处理进度: {i+1}/{len(trading_dates)} - {current_date}")
            
            # 记录当日操作数量
            daily_buy_count = 0
            daily_sell_count = 0
            daily_add_count = 0
            
            # ========== 检查是否需要强制卖出（回避时间段开始）==========
            force_sell, force_sell_reason = self._check_blackout_force_sell(current_date, trading_dates)
            if force_sell:
                # 强制卖出所有持仓
                for stock_code, position in list(self.positions.items()):
                    stock_data = self.get_stock_data_up_to_date(stock_code, current_date)
                    if stock_data is not None and len(stock_data) > 0:
                        today_data = stock_data.loc[current_date_dt]
                        sell_price = today_data['open']  # 以开盘价卖出
                        self.execute_sell(stock_code, sell_price, position.volume, current_date, force_sell_reason)
                        daily_sell_count += 1
                logger.warning(f"[回避时间段] {current_date}: {force_sell_reason}, 已清仓 {daily_sell_count} 只股票")
            
            # 1. 先处理卖出信号（检查当前持仓）
            stocks_to_sell = []
            stocks_to_add = []  # 补仓列表
            
            for stock_code, position in list(self.positions.items()):
                position.hold_days += 1
                
                # T+1限制
                if position.hold_days < self.config['min_hold_days']:
                    continue
                
                # 从预加载数据获取历史数据
                stock_data = self.get_stock_data_up_to_date(stock_code, current_date)
                if stock_data is not None and len(stock_data) > 0:
                    # 先检查补仓信号（如果策略支持）
                    if hasattr(self.strategy, 'check_add_position_signal'):
                        should_add, add_price, add_info = self.strategy.check_add_position_signal(
                            position, stock_data, current_date
                        )
                        if should_add:
                            stocks_to_add.append((stock_code, add_price, position.volume, add_info))
                            continue  # 补仓后跳过当天的卖出检查
                    
                    should_sell, sell_reason, sell_price = self.strategy.check_sell_signal(
                        position, stock_data, current_date
                    )
                    if should_sell:
                        stocks_to_sell.append((stock_code, sell_price, position.volume, sell_reason))
            
            # 执行补仓
            daily_add_count = 0
            for stock_code, add_price, add_volume, add_info in stocks_to_add:
                if self.execute_add_position(stock_code, add_price, add_volume, current_date, add_info):
                    daily_add_count += 1
            
            # 执行卖出
            for stock_code, price, volume, reason in stocks_to_sell:
                self.execute_sell(stock_code, price, volume, current_date, reason)
                daily_sell_count += 1
            
            # 2. 处理买入信号（如果还有持仓空间）
            # ========== 检查是否在禁止买入时间段 ==========
            in_blackout, blackout_reason = self._is_in_blackout_period(current_date)
            if in_blackout:
                logger.debug(f"{current_date}: {blackout_reason}")
            elif len(self.positions) < self.config['max_positions']:
                buy_signals = []
                
                for market, code_int, name in stock_codes:
                    stock_code = str(code_int)
                    
                    # 跳过已持仓股票
                    if stock_code in self.positions:
                        continue
                    
                    # 从预加载数据获取历史数据
                    stock_data = self.get_stock_data_up_to_date(stock_code, current_date)
                    if stock_data is not None and len(stock_data) > 0:
                        should_buy, signal_strength, signal_info = self.strategy.check_buy_signal(
                            stock_code, market, stock_data, current_date
                        )
                        if should_buy:
                            buy_signals.append({
                                'stock_code': stock_code,
                                'market': market,
                                'name': name,
                                'signal_strength': signal_strength,
                                'signal_info': signal_info
                            })
                
                # 按信号强度排序，选择最强的信号
                buy_signals.sort(key=lambda x: x['signal_strength'], reverse=True)
                
                # 计算可买入数量（考虑持仓上限和每日开仓上限）
                available_slots = self.config['max_positions'] - len(self.positions)
                max_daily_buys = self.config.get('max_daily_buys', 10)
                max_buys_today = min(available_slots, max_daily_buys)
                
                for signal in buy_signals[:max_buys_today]:
                    stock_code = signal['stock_code']
                    signal_info = signal['signal_info']
                    price = signal_info['close_price']
                    
                    # 计算买入金额（优化：基于当前总资产动态计算）
                    # 策略：按剩余可用仓位平均分配剩余现金
                    # 这样可以充分利用资金，同时保持仓位均衡
                    position_value = self.cash / available_slots
                    
                    # 可选：限制单只股票最大仓位（防止过度集中）
                    # max_single_position = self.config['initial_cash'] * 0.30  # 最多30%初始资金
                    # position_value = min(position_value, max_single_position)
                    
                    # 计算买入数量（100股为一手）
                    volume = int(position_value / price / 100) * 100
                    
                    if volume >= 100:  # 至少买一手
                        # 再次检查资金是否足够
                        amount = price * volume
                        commission = amount * self.config['commission']
                        slippage_cost = amount * self.config['slippage_perc']
                        total_cost = amount + commission + slippage_cost
                        
                        if total_cost <= self.cash:
                            self.execute_buy(
                                stock_code=stock_code,
                                market=signal['market'],
                                name=signal['name'],
                                price=price,
                                volume=volume,
                                current_date=current_date,
                                signal_info=signal_info
                            )
                            daily_buy_count += 1
                            # 更新剩余可用仓位
                            available_slots -= 1
            
            # 3. 记录每日资产
            portfolio_value = self.calculate_portfolio_value(current_date)
            self.daily_values.append({
                'date': current_date,
                'cash': self.cash,
                'position_count': len(self.positions),
                'portfolio_value': portfolio_value
            })
            
            # 打印每个交易日的摘要日志
            total_value = self.cash
            for pos_code, pos in self.positions.items():
                if pos_code in self.all_stock_data:
                    stock_data = self.all_stock_data[pos_code]
                    if current_date_dt in stock_data.index:
                        current_price = stock_data.loc[current_date_dt, 'close']
                        total_value += pos.get_current_value(current_price)
                else:
                    total_value += pos.get_current_value(pos.buy_price)
            
            profit_rate = (total_value / self.config['initial_cash'] - 1) * 100
            
            # 构建持仓信息
            position_info = ""
            if self.positions:
                position_list = []
                for pos_code, pos in self.positions.items():
                    pos_profit_rate = 0
                    if pos_code in self.all_stock_data:
                        stock_data = self.all_stock_data[pos_code]
                        if current_date_dt in stock_data.index:
                            current_price = stock_data.loc[current_date_dt, 'close']
                            pos_profit_rate = pos.get_profit_rate(current_price) * 100
                    position_list.append(f"{pos_code:0>6}({pos_profit_rate:+.2f}%)")
                position_info = " | 持仓: " + ", ".join(position_list)
            
            # 打印当日摘要
            if daily_buy_count > 0 or daily_sell_count > 0 or daily_add_count > 0:
                add_info_str = f" | 补仓: {daily_add_count}" if daily_add_count > 0 else ""
                logger.info(f"[交易日] {current_date} | 买入: {daily_buy_count} | 卖出: {daily_sell_count}{add_info_str} | "
                           f"总资产: {total_value:,.2f} | 盈亏: {profit_rate:+.2f}% | "
                           f"持仓数: {len(self.positions)}/{self.config['max_positions']}{position_info}")
            else:
                logger.info(f"[交易日] {current_date} | 无操作 | "
                           f"总资产: {total_value:,.2f} | 盈亏: {profit_rate:+.2f}% | "
                           f"持仓数: {len(self.positions)}/{self.config['max_positions']}{position_info}")
            
            # 保存每日记录到数据库
            if save_to_db:
                # 构建持仓详情列表
                position_detail_list = []
                for pos_code, pos in self.positions.items():
                    pos_profit_rate = 0
                    if pos_code in self.all_stock_data:
                        stock_data = self.all_stock_data[pos_code]
                        if current_date_dt in stock_data.index:
                            current_price = stock_data.loc[current_date_dt, 'close']
                            pos_profit_rate = round(pos.get_profit_rate(current_price) * 100, 2)
                    position_detail_list.append({
                        'code': pos_code,
                        'name': pos.name,
                        'profit_rate': pos_profit_rate
                    })
                
                try:
                    strategy_db.insert_daily_record(
                        strategy_name=strategy_name,
                        backtest_start_date=self.config['start_date'],
                        backtest_end_date=self.config['end_date'],
                        trade_date=current_date,
                        buy_count=daily_buy_count,
                        sell_count=daily_sell_count,
                        is_no_action=1 if (daily_buy_count == 0 and daily_sell_count == 0) else 0,
                        total_asset=round(total_value, 2),
                        profit_rate=round(profit_rate, 4),
                        cash=round(self.cash, 2),
                        position_count=len(self.positions),
                        max_positions=self.config['max_positions'],
                        position_detail=position_detail_list
                    )
                except Exception as e:
                    logger.error(f"保存每日记录失败: {str(e)}")
        
        # 回测结束，强制清仓
        logger.info(f"{'='*60}")
        logger.info("回测结束，执行强制清仓...")
        
        last_date = trading_dates[-1].strftime('%Y-%m-%d')
        last_date_dt = pd.to_datetime(last_date)
        last_sell_count = 0
        for stock_code, position in list(self.positions.items()):
            # 使用预加载数据获取最后价格
            today_data = self.get_stock_data_on_date(stock_code, last_date)
            if today_data is not None:
                last_price = today_data['close']
                self.execute_sell(
                    stock_code, 
                    last_price, 
                    position.volume, 
                    last_date, 
                    '回测结束清仓'
                )
                last_sell_count += 1
        
        # 计算清仓后的最终资产
        final_value = self.cash
        final_profit_rate = (final_value / self.config['initial_cash'] - 1) * 100
        logger.info(f"[交易日] {last_date} | 买入: 0 | 卖出: {last_sell_count} | "
                    f"总资产: {final_value:,.2f} | 盈亏: {final_profit_rate:+.2f}% | "
                    f"持仓数: 0/{self.config['max_positions']}")
        
        # 保存清仓当日记录
        if save_to_db and strategy_db:
            try:
                strategy_db.insert_daily_record(
                    strategy_name=strategy_name,
                    backtest_start_date=self.config['start_date'],
                    backtest_end_date=self.config['end_date'],
                    trade_date=last_date,
                    buy_count=0,
                    sell_count=last_sell_count,
                    is_no_action=0 if last_sell_count > 0 else 1,
                    total_asset=round(final_value, 2),
                    profit_rate=round(final_profit_rate, 4),
                    cash=round(self.cash, 2),
                    position_count=0,
                    max_positions=self.config['max_positions'],
                    position_detail=[]
                )
            except Exception as e:
                logger.error(f"保存清仓记录失败: {str(e)}")
        
        # 计算最终结果
        end_time = time.time()
        total_time = end_time - start_time
        
        total_return = final_profit_rate  # 使用前面计算的最终盈亏比例
        total_commission = self.total_buy_commission + self.total_sell_commission
        
        # 计算最大回撤和夏普比率
        daily_values_df = pd.DataFrame(self.daily_values)
        max_drawdown = 0
        sharpe_ratio = 0
        
        if len(daily_values_df) > 1:
            daily_values_df['return'] = daily_values_df['portfolio_value'].pct_change()
            
            # 最大回撤
            cumulative_max = daily_values_df['portfolio_value'].cummax()
            drawdown = (daily_values_df['portfolio_value'] - cumulative_max) / cumulative_max
            max_drawdown = drawdown.min() * 100
            
            # 夏普比率（假设无风险利率为3%年化）
            daily_returns = daily_values_df['return'].dropna()
            if len(daily_returns) > 0 and daily_returns.std() > 0:
                excess_returns = daily_returns - 0.03/252
                sharpe_ratio = (excess_returns.mean() / daily_returns.std()) * np.sqrt(252)
        
        # 输出结果
        logger.info(f"{'='*60}")
        logger.info(f"回测结果汇总")
        logger.info(f"{'='*60}")
        logger.info(f"初始资金: {self.config['initial_cash']:,.0f}")
        logger.info(f"期末资金: {final_value:,.2f}")
        logger.info(f"总收益率: {total_return:.2f}%")
        logger.info(f"最大回撤: {max_drawdown:.2f}%")
        logger.info(f"夏普比率: {sharpe_ratio:.2f}" if sharpe_ratio != 0 else "夏普比率: N/A")
        logger.info(f"总交易次数: {len(self.trading_records)}")
        logger.info(f"买入次数: {len([r for r in self.trading_records if r['action'] == 'buy'])}")
        logger.info(f"卖出次数: {len([r for r in self.trading_records if r['action'] == 'sell'])}")
        logger.info(f"盈利交易: {self.profit_trade_count}")
        logger.info(f"亏损交易: {self.loss_trade_count}")
        logger.info(f"胜率: {self.profit_trade_count/(self.profit_trade_count+self.loss_trade_count)*100:.2f}%" 
                   if (self.profit_trade_count+self.loss_trade_count) > 0 else "胜率: N/A")
        logger.info(f"总手续费: {total_commission:.2f}")
        logger.info(f"  买入手续费: {self.total_buy_commission:.2f}")
        logger.info(f"  卖出手续费: {self.total_sell_commission:.2f}")
        logger.info(f"手续费占比: {total_commission/self.config['initial_cash']*100:.2f}%")
        logger.info(f"回测耗时: {total_time:.2f} 秒 ({total_time/60:.2f} 分钟)")
        logger.info(f"{'='*60}")
        
        # 保存结果
        result = {
            'strategy_name': strategy_name,
            'start_date': self.config['start_date'],
            'end_date': self.config['end_date'],
            'initial_cash': self.config['initial_cash'],
            'final_value': final_value,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(self.trading_records),
            'profit_trade_count': self.profit_trade_count,
            'loss_trade_count': self.loss_trade_count,
            'win_rate': self.profit_trade_count/(self.profit_trade_count+self.loss_trade_count)*100 
                        if (self.profit_trade_count+self.loss_trade_count) > 0 else 0,
            'total_commission': total_commission,
            'buy_commission': self.total_buy_commission,
            'sell_commission': self.total_sell_commission,
            'execution_time': total_time,
            'trading_records': self.trading_records,
            'daily_values': self.daily_values
        }
        
        # 保存到CSV
        summary_file = f"csv/time_based_backtest_{self.config['start_date'].replace('-', '')}_to_{self.config['end_date'].replace('-', '')}.csv"
        pd.DataFrame(self.trading_records).to_csv(summary_file, index=False, encoding='utf-8-sig')
        logger.info(f"交易记录已保存至: {summary_file}")
        
        daily_file = f"csv/time_based_daily_values_{self.config['start_date'].replace('-', '')}_to_{self.config['end_date'].replace('-', '')}.csv"
        pd.DataFrame(self.daily_values).to_csv(daily_file, index=False, encoding='utf-8-sig')
        logger.info(f"每日资产已保存至: {daily_file}")
        
        # 保存到数据库
        if save_to_db:
            try:
                strategy_db = StrategyTriggerDB()
                
                # 保存触发点位
                if self.trigger_points:
                    # 按股票分组保存
                    trigger_by_stock = defaultdict(list)
                    for tp in self.trigger_points:
                        trigger_by_stock[tp['stock_code']].append(tp)
                    
                    for stock_code, points in trigger_by_stock.items():
                        if points:
                            first_point = points[0]
                            strategy_db.insert_trigger_points(
                                strategy_name=strategy_name,
                                stock_code=stock_code,
                                market=first_point.get('market', 'sh'),
                                trigger_points_json=points,
                                backtest_start_date=self.config['start_date'],
                                backtest_end_date=self.config['end_date'],
                                trigger_count=len(points)
                            )
                    
                    logger.info(f"触发点位已保存到数据库: 共 {len(self.trigger_points)} 条记录")
                
                # 保存汇总结果
                summary_json = {
                    "trading_days_count": len(trading_dates),
                    "initial_cash": self.config['initial_cash'],
                    "final_value": round(final_value, 2),
                    "total_return": round(total_return, 2),
                    "max_drawdown": round(max_drawdown, 2),
                    "sharpe_ratio": round(sharpe_ratio, 2) if sharpe_ratio != 0 else 0,
                    "total_trades": len(self.trading_records),
                    "profit_trade_count": self.profit_trade_count,
                    "loss_trade_count": self.loss_trade_count,
                    "win_rate": round(result['win_rate'], 2),
                    "total_commission": round(total_commission, 2),
                    "buy_commission": round(self.total_buy_commission, 2),
                    "sell_commission": round(self.total_sell_commission, 2),
                    "commission_ratio": round(total_commission/self.config['initial_cash']*100, 2),
                    "commission": self.config['commission'],
                    "slippage_perc": self.config['slippage_perc'],
                    "max_positions": self.config['max_positions'],
                    "position_size_pct": self.config['position_size_pct'],
                    "csv_file_path": summary_file,
                    "execution_time": round(total_time, 2),
                    "created_by": "time_based_backtest"
                }
                
                strategy_db.insert_or_update_summary(
                    strategy_name=strategy_name,
                    backtest_start_date=self.config['start_date'],
                    backtest_end_date=self.config['end_date'],
                    summary_json=summary_json,
                    stock_count=len(trigger_by_stock),
                    execution_time=total_time,
                    backtest_framework='time_based',
                    strategy_params_json=self.strategy.get_all_params()
                )
                
                logger.info(f"汇总结果已保存到数据库")
                
            except Exception as e:
                logger.error(f"保存结果到数据库失败: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        return result


def main():
    """主函数"""
    # ============ 使用方式示例 ============
    
    # 方式1：使用 value_strategy_time_1000 策略
    # from utils.strategies.value_strategy_time_1000 import ValueStrategyTimeBased
    from utils.strategies.value_strategy_time import ValueStrategyTimeBased
    strategy = ValueStrategyTimeBased()
    backtester = TimeBasedBacktester(BACKTEST_CONFIG, strategy=strategy)
    
    # 方式2：使用默认策略（价值策略）
    # backtester = TimeBasedBacktester(BACKTEST_CONFIG)
    
    # 方式3：使用策略名称指定
    # backtester = TimeBasedBacktester(BACKTEST_CONFIG, strategy='value')
    
    # 方式4：使用策略名称+自定义参数
    # from utils.strategies import get_strategy
    # strategy = get_strategy('value', params={'max_pe_ttm': 25, 'buy_threshold': -0.10})
    # backtester = TimeBasedBacktester(BACKTEST_CONFIG, strategy=strategy)
    
    # 方式5：使用MA策略
    # backtester = TimeBasedBacktester(BACKTEST_CONFIG, strategy='ma')
    
    # 执行回测
    result = backtester.run_backtest(
        strategy_name=backtester.strategy.STRATEGY_NAME,
        save_to_db=True
    )
    
    return result


if __name__ == "__main__":
    main()
