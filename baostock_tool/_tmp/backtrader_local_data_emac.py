import pandas as pd
import backtrader as bt
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from baostock_tool import config
from .utils.logger_utils import setup_logger
import matplotlib.pyplot as plt

db_config_ = config.get_db_config()
log_config = config.get_log_config()
logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"], )


# 本代码仅用于回测研究，实盘使用风险自担

def get_stock_data_from_db(stock_code="601288", market="sh", start_date="2019-01-01"):
    """
    从数据库提取单只股票历史数据
    """
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
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df = df.ffill()

    return df


# 本代码仅用于回测研究，实盘使用风险自担

class EMAChannelStrategy(bt.Strategy):
    """
    高风险高收益均线通道策略
    策略逻辑：
    1. 使用EMA(12)和EMA(26)形成交易通道
    2. 价格突破通道上轨且创N日新高时买入
    3. 价格跌破通道下轨或动态止损时卖出
    4. 加入波动率过滤和成交量确认
    """
    params = (
        ('ema_fast', 8),  # 快线EMA周期
        ('ema_slow', 22),  # 慢线EMA周期
        ('new_high_days', 20),  # 创新高判断周期
        ('stop_loss_pct', 7),  # 移动止损比例(高风险设置)
        ('volatility_threshold', 0.02),  # 波动率阈值
        ('volume_multiplier', 1.2),  # 成交量倍数要求
        ('position_size', 0.95),  # 仓位比例(高风险)
    )

    def __init__(self):
        # 计算EMA指标
        self.ema_fast = bt.indicators.EMA(self.data.close, period=self.params.ema_fast)
        self.ema_slow = bt.indicators.EMA(self.data.close, period=self.params.ema_slow)

        # 计算通道宽度和波动率
        self.channel_width = self.ema_fast - self.ema_slow
        self.atr = bt.indicators.ATR(self.data, period=14)

        # 创新高判断
        self.highest_close = bt.indicators.Highest(self.data.close, period=self.params.new_high_days)

        # 成交量均线
        self.volume_ma = bt.indicators.SMA(self.data.volume, period=20)

        # 跟踪变量
        self.entry_price = 0
        self.peak_price = 0  # 持仓期间最高价
        self.stop_price = 0  # 止损价
        self.trade_count = 0
        self.win_count = 0
        self.total_commission = 0
        self.order = None

        logger.info(f"策略初始化完成: EMA({self.params.ema_fast}/{self.params.ema_slow})")

    def notify_order(self, order):
        if order.status in [order.Completed]:
            commission = order.executed.comm
            self.total_commission += commission

            if order.isbuy():
                self.trade_count += 1
                self.entry_price = order.executed.price
                self.peak_price = self.entry_price
                self.stop_price = self.entry_price * (1 - self.params.stop_loss_pct / 100)
                logger.info(f'买入完成: 价格={order.executed.price:.2f}, 数量={order.executed.size}')

            elif order.issell():
                pnl = order.executed.pnl
                if pnl > 0:
                    self.win_count += 1
                logger.info(f'卖出完成: 价格={order.executed.price:.2f}, 收益={pnl:.2f}')

            self.order = None

    def next(self):
        # 如果有未完成订单，跳过
        if self.order:
            return

        # 确保有足够的数据
        if len(self.data) < max(self.params.ema_slow, self.params.new_high_days) + 5:
            return

        current_close = self.data.close[0]
        current_volume = self.data.volume[0]

        # 更新持仓最高价
        if self.position:
            self.peak_price = max(self.peak_price, current_close)
            # 更新移动止损价
            new_stop = self.peak_price * (1 - self.params.stop_loss_pct / 100)
            self.stop_price = max(self.stop_price, new_stop)

        # === 买入条件 ===
        if not self.position:
            # 条件1: 价格突破EMA快线(通道上轨)
            condition1 = (current_close > self.ema_fast[0] and
                          self.data.close[-1] <= self.ema_fast[-1])

            # 条件2: 创N日新高
            condition2 = (current_close >= self.highest_close[0])

            # 条件3: 成交量确认(超过均量1.2倍)
            condition3 = (current_volume > self.volume_ma[0] * self.params.volume_multiplier)

            # 条件4: 波动率过滤(避免在异常波动时入场)
            condition4 = (self.atr[0] / current_close < self.params.volatility_threshold)

            # 条件5: 趋势确认(快线在慢线上方)
            condition5 = (self.ema_fast[0] > self.ema_slow[0])

            if condition1 and condition2 and condition3 and condition4 and condition5:
                size = int(self.broker.getcash() * self.params.position_size / current_close)
                if size > 0:
                    self.order = self.buy(size=size)
                    logger.info(f'{self.data.datetime.date()} - 通道突破买入信号')
                    logger.info(f'  价格: {current_close:.2f}, EMA快线: {self.ema_fast[0]:.2f}')
                    logger.info(f'  成交量: {current_volume:.0f}, 均量: {self.volume_ma[0]:.0f}')

        # === 卖出条件 ===
        else:
            sell_signal = False
            sell_reason = ""

            # 条件1: 价格跌破EMA慢线(通道下轨)
            if current_close < self.ema_slow[0]:
                sell_signal = True
                sell_reason = "跌破通道下轨"

            # 条件2: 移动止损触发
            elif current_close <= self.stop_price:
                sell_signal = True
                sell_reason = f"移动止损(回撤{self.params.stop_loss_pct}%)"

            # 条件3: 波动率异常放大(保护利润)
            elif self.atr[0] / current_close > self.params.volatility_threshold * 2:
                sell_signal = True
                sell_reason = "波动率异常"

            if sell_signal:
                self.order = self.sell(size=self.position.size)
                current_profit = (current_close - self.entry_price) / self.entry_price * 100
                logger.info(f'{self.data.datetime.date()} - {sell_reason}卖出信号')
                logger.info(f'  持仓收益: {current_profit:.2f}%')

    def stop(self):
        """回测结束时调用"""
        if self.trade_count > 0:
            win_rate = (self.win_count / self.trade_count) * 100
            logger.info(f'策略统计: 总交易{self.trade_count}次, 盈利{self.win_count}次, 胜率{win_rate:.1f}%')
            logger.info(f'总手续费: {self.total_commission:.2f}')


def run_ema_channel_backtest():
    """运行均线通道策略回测"""
    start_time = pd.Timestamp.now()

    # 获取数据（建议使用流动性较好的股票）
    stock_data = get_stock_data_from_db(stock_code="000858", market="sz", start_date="1990-12-19")
    logger.info(f"数据量：{len(stock_data)}条")
    logger.info(f"数据时间范围：{stock_data.index[0]} 到 {stock_data.index[-1]}")

    # 创建回测引擎
    cerebro = bt.Cerebro()

    # 添加策略（使用高风险参数）
    cerebro.addstrategy(
        EMAChannelStrategy,
        ema_fast=12,
        ema_slow=26,
        stop_loss_pct=5,  # 5%移动止损
        position_size=0.95,  # 95%仓位
        volume_multiplier=1.2
    )

    # 准备数据
    data = bt.feeds.PandasData(
        dataname=stock_data,
        datetime=None,
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1
    )
    cerebro.adddata(data)

    # 设置资金和手续费
    initial_cash = 100000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)  # 0.1%手续费
    cerebro.broker.set_slippage_perc(perc=0.002)  # 0.2%滑点

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # 运行回测
    logger.info('\n开始均线通道策略回测...')
    results = cerebro.run()
    strategy = results[0]

    # 输出结果
    final_value = cerebro.broker.getvalue()
    total_return = (final_value / initial_cash - 1) * 100
    total_time = pd.Timestamp.now() - start_time

    logger.info('\n=== 高风险均线通道策略回测结果 ===')
    logger.info(f'回测耗时: {total_time}')
    logger.info(f'初始资金: {initial_cash:,.2f}')
    logger.info(f'最终资金: {final_value:,.2f}')
    logger.info(f'总收益率: {total_return:.2f}%')

    # 分析器结果
    try:
        sharpe = strategy.analyzers.sharpe.get_analysis()
        drawdown = strategy.analyzers.drawdown.get_analysis()
        returns = strategy.analyzers.returns.get_analysis()

        logger.info(f'夏普比率: {sharpe.get("sharperatio", 0):.2f}')
        logger.info(f'最大回撤: {drawdown.get("max", {}).get("drawdown", 0):.2f}%')
        logger.info(f'年化收益率: {returns.get("rnorm100", 0):.2f}%')
    except:
        logger.info("部分分析器数据计算失败")

    # 绘制图表（如果有交易）
    if strategy.trade_count > 0:
        cerebro.plot(style='candlestick', volume=True)
    else:
        logger.info('无有效交易，建议检查数据或调整参数')


if __name__ == '__main__':
    # 本代码仅用于回测研究，实盘使用风险自担
    run_ema_channel_backtest()