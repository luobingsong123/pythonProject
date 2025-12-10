import pandas as pd
import backtrader as bt
import pandas_ta as ta
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
import config
from utils.logger_utils import setup_logger
import matplotlib.pyplot as plt

db_config_ = config.get_db_config()
log_config = config.get_log_config()
logger = setup_logger(logger_name=__name__,
                   log_level=log_config["log_level"],
                   log_dir=log_config["log_dir"], )


# 本代码仅用于回测研究，实盘使用风险自担

def get_stock_data_from_db(stock_code="601288", market="sh", start_date="2019-01-01"):
    """
    从数据库提取单只股票历史数据（修复版本）
    """
    # 使用SQLAlchemy连接（推荐方式）
    db_url = URL.create(
        drivername="mysql+pymysql",
        username=db_config_["user"],
        password=db_config_["password"],
        host=db_config_["host"],
        port=db_config_["port"],
        database=db_config_["database"]
    )
    engine = create_engine(db_url)

    query = f"""
    SELECT date, open, high, low, close, volume, amount, pctChg
    FROM stock_daily_data 
    WHERE market = '{market}' 
      AND code_int = {stock_code}
      AND frequency = 'd'
      AND date >= '{start_date}'
    ORDER BY date
    """

    df = pd.read_sql(query, engine)

    # 数据清洗与格式化
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df = df.ffill()  # 前向填充缺失值

    return df


# 本代码仅用于回测研究，实盘使用风险自担

# 定义改进的MACD策略
class ImprovedMACDStrategy(bt.Strategy):
    params = (
        ('fast', 12),
        ('slow', 26),
        ('signal', 9),
        ('converge_days', 4),  # 收敛天数参数
        ('stop_loss_threshold', 2.0),  # 止损阈值2%
    )

    def __init__(self):
        # 计算MACD指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast,
            period_me2=self.params.slow,
            period_signal=self.params.signal
        )
        self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # 跟踪变量
        self.dead_cross_peak = None  # 死叉后的MACD峰值
        self.dead_cross_converge_count = 0  # 死叉后收敛计数
        self.golden_cross_peak = None  # 金叉后的MACD峰值
        self.golden_cross_converge_count = 0  # 金叉后收敛计数
        self.peak_profit = 0  # 持仓期间的最大盈利
        self.current_profit = 0  # 当前盈利

        # 增强手续费统计
        self.trade_count = 0
        self.total_commission = 0
        self.buy_commission = 0
        self.sell_commission = 0
        self.trade_wins = 0
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            commission = order.executed.comm

            if order.isbuy():
                self.trade_count += 1
                self.buy_commission += commission
                self.total_commission += commission
                # 重置盈利跟踪
                self.peak_profit = 0
                self.current_profit = 0
                logger.info(f'买入完成: 价格={order.executed.price:.2f}, 手续费={commission:.2f}')
            elif order.issell():
                self.trade_count += 1
                self.sell_commission += commission
                self.total_commission += commission
                if order.executed.pnl > 0:
                    self.trade_wins += 1
                logger.info(f'卖出完成: 价格={order.executed.price:.2f}, 收益={order.executed.pnl:.2f}, 手续费={commission:.2f}')

                # 卖出后重置跟踪变量
                self.reset_tracking_variables()

            self.order = None

    def reset_tracking_variables(self):
        """重置所有跟踪变量"""
        self.dead_cross_peak = None
        self.dead_cross_converge_count = 0
        self.golden_cross_peak = None
        self.golden_cross_converge_count = 0
        self.peak_profit = 0
        self.current_profit = 0

    def check_convergence_condition(self, current_macd, peak_value, converge_count, is_increasing=False):
        """
        检查收敛条件
        is_increasing: True表示检查上升趋势的收敛，False表示检查下降趋势的收敛
        """
        if peak_value is None:
            return None, 0, False

        if is_increasing:
            # 对于上升趋势，收敛意味着MACD值开始下降
            if current_macd > peak_value:
                # 更新峰值
                return current_macd, 0, False
            else:
                # 继续收敛计数
                new_count = converge_count + 1
                return peak_value, new_count, new_count >= self.params.converge_days
        else:
            # 对于下降趋势，收敛意味着MACD值开始上升
            if current_macd < peak_value:
                # 更新峰值（更小的值）
                return current_macd, 0, False
            else:
                # 继续收敛计数
                new_count = converge_count + 1
                return peak_value, new_count, new_count >= self.params.converge_days

    def next(self):
        # 如果已有订单，不执行新操作
        if self.order:
            return

        # 检查MACD指标是否已初始化
        if len(self.macd.macd) < 2 or len(self.macd.signal) < 2:
            return

        current_macd = self.macd.macd[0]

        # 更新当前盈利（如果有持仓）
        if self.position:
            self.current_profit = (self.data.close[0] - self.position.price) / self.position.price * 100
            self.peak_profit = max(self.peak_profit, self.current_profit)

        # 检查MACD交叉信号
        if self.macd_cross > 0:  # 金叉
            if not self.position:
                # 空仓状态下发生金叉，重置死叉跟踪
                self.dead_cross_peak = None
                self.dead_cross_converge_count = 0
            else:
                # 持仓状态下发生金叉，开始跟踪金叉后的峰值
                self.golden_cross_peak = abs(current_macd)
                self.golden_cross_converge_count = 0
                logger.debug(f'{self.data.datetime.date()} - 金叉发生，开始跟踪峰值: {current_macd:.4f}')

        elif self.macd_cross < 0:  # 死叉
            if self.position:
                # 持仓状态下发生死叉，重置金叉跟踪
                self.golden_cross_peak = None
                self.golden_cross_converge_count = 0
            else:
                # 空仓状态下发生死叉，开始跟踪死叉后的峰值
                self.dead_cross_peak = current_macd
                self.dead_cross_converge_count = 0
                logger.debug(f'{self.data.datetime.date()} - 死叉发生，开始跟踪峰值: {current_macd:.4f}')

        # 检查是否持有仓位
        if not self.position:
            # === 买入条件：死叉后的MACD出现最大值后连续4个交易日收敛 ===
            if self.dead_cross_peak is not None:
                # 检查收敛条件（下降趋势的收敛）
                self.dead_cross_peak, self.dead_cross_converge_count, buy_signal = self.check_convergence_condition(
                    current_macd, self.dead_cross_peak, self.dead_cross_converge_count, is_increasing=False
                )

                if buy_signal:
                    # 计算可买数量
                    size = int(self.broker.getcash() * 0.95 / self.data.close[0])
                    if size > 0:
                        self.order = self.buy(size=size)
                        logger.info(f'{self.data.datetime.date()} - 死叉后收敛买入信号，价格: {self.data.close[0]:.2f}, MACD: {current_macd:.4f}')
                        # 买入后重置死叉跟踪
                        self.dead_cross_peak = None
                        self.dead_cross_converge_count = 0
        else:
            # === 卖出条件1：金叉后的MACD出现最大值后连续4个交易日收敛 ===
            sell_signal_1 = False
            if self.golden_cross_peak is not None:
                # 检查收敛条件（上升趋势的收敛）
                self.golden_cross_peak, self.golden_cross_converge_count, sell_signal_1 = self.check_convergence_condition(
                    current_macd, self.golden_cross_peak, self.golden_cross_converge_count, is_increasing=True
                )

                if sell_signal_1:
                    logger.info(f'{self.data.datetime.date()} - 金叉后收敛卖出信号，价格: {self.data.close[0]:.2f}, MACD: {current_macd:.4f}')

            # === 卖出条件2：亏损相较最大盈利回撤2%以上 ===
            sell_signal_2 = False
            if self.peak_profit > 0 and self.current_profit < (self.peak_profit - self.params.stop_loss_threshold):
                sell_signal_2 = True
                logger.info(f'{self.data.datetime.date()} - 盈利回撤卖出信号，当前盈利: {self.current_profit:.2f}%, 峰值盈利: {self.peak_profit:.2f}%')

            # 执行卖出
            if sell_signal_1 or sell_signal_2:
                self.order = self.sell(size=self.position.size)
                sell_reason = "收敛" if sell_signal_1 else "回撤"
                logger.info(f'{self.data.datetime.date()} - 执行卖出({sell_reason})，价格: {self.data.close[0]:.2f}')


# 定义MACD金叉死叉策略（修复版本）
class MACDStrategy(bt.Strategy):
    params = (
        ('fast', 12),
        ('slow', 26),
        ('signal', 9),
    )

    def __init__(self):
        # 计算MACD指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast,
            period_me2=self.params.slow,
            period_signal=self.params.signal
        )
        self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # 增强手续费统计
        self.trade_count = 0
        self.total_commission = 0  # 总手续费
        self.buy_commission = 0  # 买入手续费
        self.sell_commission = 0  # 卖出手续费
        self.trade_wins = 0  # 盈利交易次数
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            commission = order.executed.comm

            if order.isbuy():
                self.trade_count += 1
                self.buy_commission += commission
                self.total_commission += commission
                logger.info(f'买入完成: 价格={order.executed.price:.2f}, 手续费={commission:.2f}')
            elif order.issell():
                self.trade_count += 1
                self.sell_commission += commission
                self.total_commission += commission
                if order.executed.pnl > 0:
                    self.trade_wins += 1
                logger.info(f'卖出完成: 价格={order.executed.price:.2f}, 收益={order.executed.pnl:.2f}, 手续费={commission:.2f}')

            self.order = None

    def next(self):
        # 如果已有订单，不执行新操作
        if self.order:
            return

        # 检查MACD指标是否已初始化（需要足够的数据周期）
        if len(self.macd.macd) < 2 or len(self.macd.signal) < 2:
            return

        # 检查是否持有仓位
        if not self.position:
            # MACD金叉买入信号
            if self.macd_cross > 0:
                # 计算可买数量（留部分现金）
                size = int(self.broker.getcash() * 0.95 / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    logger.info(f'{self.data.datetime.date()} - MACD金叉买入信号，价格: {self.data.close[0]:.2f}')
        else:
            # MACD死叉卖出信号
            if self.macd_cross < 0:
                self.order = self.sell(size=self.position.size)
                logger.info(f'{self.data.datetime.date()} - MACD死叉卖出信号，价格: {self.data.close[0]:.2f}')


# 使用pandas_ta计算MACD（用于验证和对比）
def calculate_macd_with_pandas_ta(df):
    """使用pandas_ta计算MACD指标"""
    macd_df = df.ta.macd(fast=12, slow=26, signal=9)
    return pd.concat([df, macd_df], axis=1)


def safe_get_analysis(analyzer, key_path, default="无法计算"):
    """安全获取分析器结果"""
    try:
        result = analyzer.get_analysis()
        keys = key_path.split('.')
        for key in keys:
            if key in result:
                result = result[key]
            else:
                return default
        return result if result is not None else default
    except:
        return default


def run_backtest():
    start_time = pd.Timestamp.now()
    # 获取更早的数据以确保MACD有足够初始化周期
    stock_data = get_stock_data_from_db(stock_code="300750", market="sz", start_date="1990-12-19")
    logger.info(f"数据量：{len(stock_data)}条")
    logger.info(f"数据时间范围：{stock_data.index[0]} 到 {stock_data.index[-1]}")

    # 使用pandas_ta计算MACD（用于验证）
    stock_data_with_macd = calculate_macd_with_pandas_ta(stock_data)

    # 检查MACD指标是否计算成功
    macd_cols = [col for col in stock_data_with_macd.columns if 'MACD' in col]
    if macd_cols:
        # 找到第一个非NaN的MACD值
        first_valid_idx = stock_data_with_macd[macd_cols[0]].first_valid_index()
        if first_valid_idx is not None:
            logger.info(f"MACD指标从 {first_valid_idx} 开始有效")
            logger.info(f"前5个有效MACD值:")
            valid_data = stock_data_with_macd.loc[first_valid_idx:].head(5)
            logger.info(valid_data[macd_cols])

    # 创建回测引擎
    cerebro = bt.Cerebro()

    # 添加策略
    # cerebro.addstrategy(MACDStrategy)
    cerebro.addstrategy(ImprovedMACDStrategy)
    # 准备数据格式（backtrader要求）
    data = bt.feeds.PandasData(
        dataname=stock_data,
        datetime=None,  # 使用索引作为日期
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1
    )

    # 添加数据
    cerebro.adddata(data)

    # 设置初始资金
    initial_cash = 100000.0
    cerebro.broker.setcash(initial_cash)

    # 设置交易手续费（A股标准）
    cerebro.broker.setcommission(commission=0.001)  # 0.1%手续费
    # 设置滑点 - 百分比方式
    cerebro.broker.set_slippage_perc(perc=0.002)  # 0.2%滑点
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Transactions, _name='transactions')

    # 运行回测
    logger.info('\n开始回测...')
    results = cerebro.run()
    strategy = results[0]

    # 打印回测结果
    final_value = cerebro.broker.getvalue()
    total_return = (final_value / initial_cash - 1) * 100
    total_time = pd.Timestamp.now() - start_time
    logger.info('\n=== 回测结果 ===')
    logger.info(f'回测耗时: {total_time}')
    logger.info(f'初始资金: {initial_cash:,.2f}')
    logger.info(f'最终资金: {final_value:,.2f}')
    logger.info(f'总收益率: {total_return:.2f}%')
    logger.info(f'交易次数: {strategy.trade_count}')
    logger.info(f'盈利交易次数: {strategy.trade_wins}')


    # 手续费统计
    logger.info(f'总手续费: {strategy.total_commission:.2f}')
    logger.info(f'买入手续费: {strategy.buy_commission:.2f}')
    logger.info(f'卖出手续费: {strategy.sell_commission:.2f}')
    logger.info(f'手续费占最终资金比例: {(strategy.total_commission / final_value * 100):.2f}%')

    # 安全获取分析器结果
    sharpe_ratio = safe_get_analysis(strategy.analyzers.sharpe, 'sharperatio', 0)
    max_drawdown = safe_get_analysis(strategy.analyzers.drawdown, 'max.drawdown', 0)
    annual_return = safe_get_analysis(strategy.analyzers.returns, 'rnorm100', 0)

    logger.info(f'夏普比率: {sharpe_ratio:.2f}' if isinstance(sharpe_ratio, (int, float)) else f'夏普比率: {sharpe_ratio}')
    logger.info(f'最大回撤: {max_drawdown:.2f}%' if isinstance(max_drawdown, (int, float)) else f'最大回撤: {max_drawdown}')
    logger.info(f'年化收益率: {annual_return:.2f}%' if isinstance(annual_return, (int, float)) else f'年化收益率: {annual_return}')

    # 交易分析
    trades_analysis = safe_get_analysis(strategy.analyzers.trades, 'total.total', 0)
    logger.info(f'总交易数: {trades_analysis}')
    logger.info(f'交易胜率： {(strategy.trade_wins / trades_analysis * 100) if trades_analysis > 0 else 0:.2f}%')

    # 如果收益率不为0，绘制图表
    if abs(total_return) > 0.01 and strategy.trade_count > 0:
        logger.info('\n生成回测图表...')
        cerebro.plot(style='candlestick', volume=True)
    else:
        logger.info('\n无有效交易，跳过图表生成')
        logger.info('可能原因:')
        logger.info('1. MACD指标需要更多数据周期进行初始化')
        logger.info('2. 在回测期间内没有产生有效的金叉/死叉信号')
        logger.info('3. 数据质量问题')


if __name__ == '__main__':
    run_backtest()