"""
按时间遍历所有个股的标准回测脚本 - MySQL+QuestDB版本（重构版）

特点：
1. 按交易日顺序遍历，每个时间点检查所有股票信号
2. 支持总资金管理（跨股票）
3. 支持选股机制和仓位控制
4. 支持策略模块化替换
5. 更接近实盘交易场景
6. 交易日历、股票列表使用MySQL存储
7. 股票日K线数据使用QuestDB存储
8. 模块化设计，职责清晰

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
from datetime import datetime
import time
import os
from typing import Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# 配置
import config
from utils.logger_utils import setup_logger
from database_schema.strategy_trigger_db import StrategyTriggerDB
from utils.strategies import BaseStrategy, get_strategy

# 回测引擎组件
from utils.backtest_engine import (
    BacktestConfig,
    Account,
    PortfolioManager,
    TradeExecutor,
    StatisticsCalculator,
    BacktestRecorder,
    BlackoutManager
)

# 数据加载组件
from utils.data_loader.questdb_data_preloader import QuestDBDataPreloader

# 默认回测配置
BACKTEST_CONFIG = {
    'start_date': '2024-01-01',
    'end_date': '2024-12-31',
    'initial_cash': 10000000,
    'commission': 0.001,
    'slippage_perc': 0.001,
    'max_positions': 100,
    'max_daily_buys': 10,
    'position_size_pct': 0.01,
    'min_hold_days': 1,
    'lookback_days': 10,
    'enable_blackout': False,
    'blackout_periods': [],
}

# 创建必要的目录
os.makedirs("csv", exist_ok=True)
os.makedirs("log", exist_ok=True)

# 从配置文件读取日期配置
date_config = config.get_backtrade_date_config()
BACKTEST_CONFIG['start_date'] = date_config.get("start_date", BACKTEST_CONFIG['start_date'])
BACKTEST_CONFIG['end_date'] = date_config.get("end_date", BACKTEST_CONFIG['end_date'])

# 初始化日志
logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"]
)


class TimeBasedBacktester:
    """
    按时间遍历的回测引擎 - MySQL+QuestDB版本（重构版）

    支持策略模块化，可以通过 strategy 参数注入不同的策略
    - 股票日K线数据从QuestDB加载
    - 交易日历、股票列表等从MySQL加载
    """

    def __init__(self, config_dict=None, strategy=None):
        """
        初始化回测引擎

        Args:
            config_dict: 回测配置字典
            strategy: 策略对象（继承自 BaseStrategy），如果为 None 则使用默认价值策略
        """
        # 初始化配置
        config_data = config_dict or BACKTEST_CONFIG.copy()
        self.config = BacktestConfig.from_dict(config_data)

        # 初始化策略
        self.strategy = self._init_strategy(strategy)

        # 初始化核心组件
        self.account = Account(
            initial_cash=self.config.initial_cash,
            commission=self.config.commission,
            slippage=self.config.slippage_perc
        )
        self.portfolio = PortfolioManager()
        self.trade_executor = TradeExecutor(
            account=self.account,
            portfolio=self.portfolio,
            commission=self.config.commission
        )
        self.blackout_manager = BlackoutManager(self.config)
        self.recorder = BacktestRecorder(output_dir="csv")

        # MySQL引擎
        db_config = config.get_db_config()
        db_url = URL.create(
            drivername="mysql+pymysql",
            username=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"]
        )
        self.engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)

        # 数据加载器（使用QuestDB加载股票日K线数据）
        self.data_preloader = QuestDBDataPreloader()

        # 每日资产记录
        self.daily_values = []

    def _init_strategy(self, strategy):
        """初始化策略"""
        if strategy is None:
            from utils.strategies import ValueStrategyTimeBased
            return ValueStrategyTimeBased()
        elif isinstance(strategy, str):
            return get_strategy(strategy)
        elif isinstance(strategy, BaseStrategy):
            return strategy
        else:
            raise TypeError(f"strategy 参数类型错误，期望 str 或 BaseStrategy，实际为 {type(strategy)}")

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
        df = pd.read_sql(query, self.engine)
        df['calendar_date'] = pd.to_datetime(df['calendar_date'])
        return df['calendar_date'].tolist()

    def get_stock_list(self):
        """获取股票列表"""
        query = """
        SELECT market, code_int, name
        FROM stock_basic_info 
        WHERE (market = 'sh' AND code_int > 600000 AND code_int < 610000)
           OR (market = 'sz' AND code_int > 0 AND code_int < 10000)
           OR (market = 'sz' AND code_int > 300000 AND code_int < 310000)
        ORDER BY code_int
        """
        df = pd.read_sql(query, self.engine)
        return df

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
            deleted_count = strategy_db.delete_daily_records(
                strategy_name=strategy_name,
                backtest_start_date=self.config.start_date,
                backtest_end_date=self.config.end_date
            )
            if deleted_count > 0:
                logger.info(f"已删除旧的每日记录: {deleted_count} 条")
            
            # 删除旧交易记录
            deleted_trade_count = strategy_db.delete_trade_records(
                strategy_name=strategy_name,
                backtest_start_date=self.config.start_date,
                backtest_end_date=self.config.end_date
            )
            if deleted_trade_count > 0:
                logger.info(f"已删除旧的交易记录: {deleted_trade_count} 条")
            
            # 将数据库连接传递给交易执行器
            self.trade_executor.strategy_db = strategy_db
            self.trade_executor.strategy_name = strategy_name
            self.trade_executor.backtest_start_date = self.config.start_date
            self.trade_executor.backtest_end_date = self.config.end_date

        # 获取交易日历
        trading_dates = self.get_trade_calendar(self.config.start_date, self.config.end_date)
        if not trading_dates:
            logger.error("无法获取交易日历")
            return None

        # 打印回测配置
        self._print_backtest_info(trading_dates)

        # 获取股票列表
        stock_list_df = self.get_stock_list()
        stock_codes = [(row['market'], row['code_int'], row['name'])
                       for _, row in stock_list_df.iterrows()]
        logger.info(f"股票总数: {len(stock_codes)}")

        # 预加载数据
        preload_start = time.time()
        # 使用策略声明的 lookback_days，如果策略未声明则使用配置中的值
        lookback_days = self.config.lookback_days
        if hasattr(self.strategy, 'get_lookback_days'):
            strategy_lookback = self.strategy.get_lookback_days() * 1.65
            # 取策略需求和配置值中的较大者，确保有足够数据
            lookback_days = max(lookback_days, strategy_lookback)

        self.data_preloader.preload_all_stock_data(
            stock_codes,
            self.config.start_date,
            self.config.end_date,
            lookback_days
        )
        preload_time = time.time() - preload_start
        logger.info(f"数据预加载耗时: {preload_time:.2f} 秒")
        logger.info(f"{'=' * 60}")

        # 按日期遍历
        for i, trade_date in enumerate(trading_dates):
            current_date = trade_date.strftime('%Y-%m-%d')
            current_date_dt = pd.to_datetime(current_date)

            # 进度显示
            if (i + 1) % 50 == 0 or i == 0:
                logger.info(f"处理进度: {i + 1}/{len(trading_dates)} - {current_date}")

            # 处理当前交易日
            daily_buy_count, daily_sell_count, daily_add_count = self._process_trading_day(
                current_date, current_date_dt, trading_dates, stock_codes, strategy_db, strategy_name, save_to_db
            )

        # 回测结束，强制清仓
        final_value = self._liquidate_positions(trading_dates, save_to_db, strategy_db, strategy_name)

        # 计算统计结果
        end_time = time.time()
        total_time = end_time - start_time
        statistics = StatisticsCalculator.calculate_from_daily_values(
            self.daily_values,
            self.config.initial_cash,
            self.account.profit_trade_count,
            self.account.loss_trade_count,
            self.account.total_buy_commission,
            self.account.total_sell_commission,
            self.trade_executor.get_trading_records()
        )

        # 打印统计结果
        StatisticsCalculator.print_statistics(
            statistics, self.config.initial_cash, final_value, total_time
        )

        # 保存结果
        result = self._build_result(
            strategy_name, final_value, statistics, total_time, trading_dates
        )

        # 保存到CSV
        self.recorder.save_trading_records(
            self.trade_executor.get_trading_records(),
            self.config.start_date,
            self.config.end_date
        )
        self.recorder.save_daily_values(
            self.daily_values,
            self.config.start_date,
            self.config.end_date
        )

        # 保存到数据库
        if save_to_db:
            self.recorder.save_to_database(
                strategy_name=strategy_name,
                backtest_config=self.config,
                trading_records=self.trade_executor.get_trading_records(),
                daily_values=self.daily_values,
                trigger_points=self.trade_executor.get_trigger_points(),
                statistics=statistics,
                trading_dates_count=len(trading_dates),
                final_value=final_value,
                execution_time=total_time,
                strategy_params=self.strategy.get_all_params()
            )

        return result

    def _print_backtest_info(self, trading_dates):
        """打印回测配置信息"""
        db_config = config.get_db_config()
        questdb_config = config.get_questdb_config()
        logger.info(f"{'=' * 60}")
        logger.info(f"开始按时间遍历回测 (MySQL+QuestDB数据源)")
        logger.info(f"策略: {self.strategy.STRATEGY_NAME}")
        logger.info(f"回测期间: {self.config.start_date} 至 {self.config.end_date}")
        logger.info(f"初始资金: {self.config.initial_cash:,.0f}")
        logger.info(f"最大持仓: {self.config.max_positions} 只")
        logger.info(f"交易日数: {len(trading_dates)} 天")
        logger.info(f"MySQL: {db_config['host']}:{db_config['port']}/{db_config['database']} (交易日历、股票列表)")
        logger.info(f"QuestDB: {questdb_config['host']}:{questdb_config['port']} (股票日K线)")
        self.blackout_manager.log_blackout_status()
        logger.info(f"{'=' * 60}")

    def _process_trading_day(
        self, current_date, current_date_dt, trading_dates, stock_codes, strategy_db, strategy_name, save_to_db
    ):
        """处理单个交易日"""
        daily_buy_count = 0
        daily_sell_count = 0
        daily_add_count = 0

        # 检查是否需要强制卖出（回避时间段开始）
        force_sell, force_sell_reason = self.blackout_manager.check_force_sell(current_date, trading_dates)
        if force_sell:
            daily_sell_count = self._force_sell_all(current_date, current_date_dt, force_sell_reason)

        # 处理卖出和补仓信号
        stocks_to_sell, stocks_to_add = self._check_sell_and_add_signals(current_date, current_date_dt)

        # 执行补仓
        for stock_code, add_price, add_volume, add_info in stocks_to_add:
            if self.trade_executor.execute_add_position(
                stock_code, add_price, add_volume, current_date, add_info, self.config.initial_cash
            ):
                daily_add_count += 1

        # 执行卖出
        for stock_code, price, volume, reason in stocks_to_sell:
            self.trade_executor.execute_sell(stock_code, price, volume, current_date, reason, self.config.initial_cash)
            daily_sell_count += 1

        # 处理买入信号
        in_blackout, blackout_reason = self.blackout_manager.is_in_blackout_period(current_date)
        if not in_blackout and self.portfolio.get_position_count() < self.config.max_positions:
            daily_buy_count = self._process_buy_signals(current_date, stock_codes)

        # 记录每日资产
        self._record_daily_value(current_date, current_date_dt)

        # 打印当日摘要
        self._print_daily_summary(
            current_date, current_date_dt, daily_buy_count, daily_sell_count, daily_add_count
        )

        # 保存每日记录到数据库
        if save_to_db and strategy_db:
            self._save_daily_record_to_db(
                strategy_db, strategy_name, current_date, current_date_dt,
                daily_buy_count, daily_sell_count
            )

        return daily_buy_count, daily_sell_count, daily_add_count

    def _force_sell_all(self, current_date, current_date_dt, force_sell_reason):
        """强制卖出所有持仓"""
        sell_count = 0
        for stock_code, position in list(self.portfolio.get_all_positions().items()):
            stock_data = self.data_preloader.get_stock_data_up_to_date(stock_code, current_date)
            if stock_data is not None and len(stock_data) > 0:
                today_data = stock_data.loc[current_date_dt]
                sell_price = today_data['open']
                self.trade_executor.execute_sell(
                    stock_code, sell_price, position.volume, current_date, force_sell_reason, self.config.initial_cash
                )
                sell_count += 1
        logger.warning(f"[回避时间段] {current_date}: {force_sell_reason}, 已清仓 {sell_count} 只股票")
        return sell_count

    def _check_sell_and_add_signals(self, current_date, current_date_dt):
        """检查卖出和补仓信号"""
        stocks_to_sell = []
        stocks_to_add = []

        for stock_code, position in list(self.portfolio.get_all_positions().items()):
            position.hold_days += 1

            # T+1限制
            if position.hold_days < self.config.min_hold_days:
                continue

            # 获取历史数据
            stock_data = self.data_preloader.get_stock_data_up_to_date(stock_code, current_date)
            if stock_data is not None and len(stock_data) > 0:
                # 检查补仓信号
                if hasattr(self.strategy, 'check_add_position_signal'):
                    should_add, add_price, add_info = self.strategy.check_add_position_signal(
                        position, stock_data, current_date
                    )
                    if should_add:
                        stocks_to_add.append((stock_code, add_price, position.volume, add_info))
                        continue

                # 检查卖出信号
                should_sell, sell_reason, sell_price = self.strategy.check_sell_signal(
                    position, stock_data, current_date
                )
                if should_sell:
                    stocks_to_sell.append((stock_code, sell_price, position.volume, sell_reason))

        return stocks_to_sell, stocks_to_add

    def _process_buy_signals(self, current_date, stock_codes):
        """处理买入信号"""
        buy_signals = []

        for market, code_int, name in stock_codes:
            stock_code = str(code_int)

            if self.portfolio.has_position(stock_code):
                continue

            stock_data = self.data_preloader.get_stock_data_up_to_date(stock_code, current_date)
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

        # 按信号强度排序
        buy_signals.sort(key=lambda x: x['signal_strength'], reverse=True)

        # 计算可买入数量
        available_slots = self.config.max_positions - self.portfolio.get_position_count()
        max_daily_buys = self.config.max_daily_buys
        max_buys_today = min(available_slots, max_daily_buys)

        daily_buy_count = 0
        for signal in buy_signals[:max_buys_today]:
            stock_code = signal['stock_code']
            signal_info = signal['signal_info']
            price = signal_info['close_price']

            # 计算买入金额
            position_value = self.account.cash / available_slots
            volume = int(position_value / price / 100) * 100

            if volume >= 100:
                cost_info = self.account.calc_buy_cost(price, volume)
                if cost_info['total_cost'] <= self.account.cash:
                    self.trade_executor.execute_buy(
                        stock_code=stock_code,
                        market=signal['market'],
                        name=signal['name'],
                        price=price,
                        volume=volume,
                        current_date=current_date,
                        signal_info=signal_info,
                        initial_cash=self.config.initial_cash
                    )
                    daily_buy_count += 1
                    available_slots -= 1

        return daily_buy_count

    def _record_daily_value(self, current_date, current_date_dt):
        """记录每日资产"""
        portfolio_value = self.portfolio.calculate_total_value(
            self.data_preloader.all_stock_data, current_date
        )
        # 计算总资产（现金 + 持仓市值）
        total_value = self.account.cash + portfolio_value
        self.daily_values.append({
            'date': current_date,
            'cash': self.account.cash,
            'position_count': self.portfolio.get_position_count(),
            'portfolio_value': portfolio_value,
            'total_value': total_value  # 添加总资产字段
        })

    def _print_daily_summary(self, current_date, current_date_dt, daily_buy_count, daily_sell_count, daily_add_count):
        """打印当日摘要"""
        # 计算总资产
        total_value = self.account.cash
        for pos_code, pos in self.portfolio.get_all_positions().items():
            if pos_code in self.data_preloader.all_stock_data:
                stock_data = self.data_preloader.all_stock_data[pos_code]
                if stock_data.index.tz is not None:
                    stock_data = stock_data.tz_localize(None)
                if current_date_dt in stock_data.index:
                    current_price = stock_data.loc[current_date_dt, 'close']
                    total_value += pos.get_current_value(current_price)
            else:
                total_value += pos.get_current_value(pos.buy_price)

        profit_rate = (total_value / self.config.initial_cash - 1) * 100
        position_info = self.portfolio.get_positions_summary(self.data_preloader.all_stock_data, current_date)

        # 打印摘要
        if daily_buy_count > 0 or daily_sell_count > 0 or daily_add_count > 0:
            add_info_str = f" | 补仓: {daily_add_count}" if daily_add_count > 0 else ""
            logger.info(
                f"[交易日] {current_date} | 买入: {daily_buy_count} | 卖出: {daily_sell_count}{add_info_str} | "
                f"总资产: {total_value:,.2f} | 盈亏: {profit_rate:+.2f}% | "
                f"持仓数: {self.portfolio.get_position_count()}/{self.config.max_positions}{position_info}"
            )
        else:
            logger.info(
                f"[交易日] {current_date} | 无操作 | "
                f"总资产: {total_value:,.2f} | 盈亏: {profit_rate:+.2f}% | "
                f"持仓数: {self.portfolio.get_position_count()}/{self.config.max_positions}{position_info}"
            )

    def _save_daily_record_to_db(self, strategy_db, strategy_name, current_date, current_date_dt, daily_buy_count, daily_sell_count):
        """保存每日记录到数据库"""
        total_value = self.account.cash
        for pos_code, pos in self.portfolio.get_all_positions().items():
            if pos_code in self.data_preloader.all_stock_data:
                stock_data = self.data_preloader.all_stock_data[pos_code]
                if stock_data.index.tz is not None:
                    stock_data = stock_data.tz_localize(None)
                if current_date_dt in stock_data.index:
                    current_price = stock_data.loc[current_date_dt, 'close']
                    total_value += pos.get_current_value(current_price)
            else:
                total_value += pos.get_current_value(pos.buy_price)

        profit_rate = (total_value / self.config.initial_cash - 1) * 100

        self.recorder.save_daily_record_to_db(
            strategy_db=strategy_db,
            strategy_name=strategy_name,
            backtest_config=self.config,
            current_date=current_date,
            daily_buy_count=daily_buy_count,
            daily_sell_count=daily_sell_count,
            total_value=total_value,
            profit_rate=profit_rate,
            cash=self.account.cash,
            position_count=self.portfolio.get_position_count(),
            max_positions=self.config.max_positions,
            positions=self.portfolio.get_all_positions(),
            all_stock_data=self.data_preloader.all_stock_data
        )

    def _liquidate_positions(self, trading_dates, save_to_db, strategy_db, strategy_name):
        """回测结束强制清仓"""
        logger.info(f"{'=' * 60}")
        logger.info("回测结束，执行强制清仓...")

        last_date = trading_dates[-1].strftime('%Y-%m-%d')
        last_date_dt = pd.to_datetime(last_date)
        last_sell_count = 0

        for stock_code, position in list(self.portfolio.get_all_positions().items()):
            today_data = self.data_preloader.get_stock_data_on_date(stock_code, last_date)
            if today_data is not None:
                last_price = today_data['close']
                self.trade_executor.execute_sell(
                    stock_code, last_price, position.volume, last_date, '回测结束清仓', self.config.initial_cash
                )
                last_sell_count += 1

        final_value = self.account.cash
        final_profit_rate = (final_value / self.config.initial_cash - 1) * 100

        logger.info(
            f"[交易日] {last_date} | 买入: 0 | 卖出: {last_sell_count} | "
            f"总资产: {final_value:,.2f} | 盈亏: {final_profit_rate:+.2f}% | "
            f"持仓数: 0/{self.config.max_positions}"
        )

        # 保存清仓当日记录
        if save_to_db and strategy_db:
            self.recorder.save_daily_record_to_db(
                strategy_db=strategy_db,
                strategy_name=strategy_name,
                backtest_config=self.config,
                current_date=last_date,
                daily_buy_count=0,
                daily_sell_count=last_sell_count,
                total_value=final_value,
                profit_rate=final_profit_rate,
                cash=self.account.cash,
                position_count=0,
                max_positions=self.config.max_positions,
                positions={},
                all_stock_data=self.data_preloader.all_stock_data
            )

        return final_value

    def _build_result(self, strategy_name, final_value, statistics, total_time, trading_dates):
        """构建结果字典"""
        return {
            'strategy_name': strategy_name,
            'start_date': self.config.start_date,
            'end_date': self.config.end_date,
            'initial_cash': self.config.initial_cash,
            'final_value': final_value,
            'total_return': statistics.total_return,
            'max_drawdown': statistics.max_drawdown,
            'sharpe_ratio': statistics.sharpe_ratio,
            'total_trades': statistics.total_trades,
            'profit_trade_count': statistics.profit_trade_count,
            'loss_trade_count': statistics.loss_trade_count,
            'win_rate': statistics.win_rate,
            'total_commission': statistics.total_commission,
            'buy_commission': statistics.buy_commission,
            'sell_commission': statistics.sell_commission,
            'execution_time': total_time,
            'trading_records': self.trade_executor.get_trading_records(),
            'daily_values': self.daily_values
        }


def main():
    """主函数"""
    # 使用 codebuddy 策略
    from utils.strategies import get_strategy
    strategy = get_strategy('ValueStrategy')
    backtester = TimeBasedBacktester(BACKTEST_CONFIG, strategy=strategy)

    # 执行回测
    result = backtester.run_backtest(
        strategy_name=backtester.strategy.STRATEGY_NAME,
        save_to_db=True
    )

    return result


if __name__ == "__main__":
    main()
