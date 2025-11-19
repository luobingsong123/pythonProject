import pandas as pd
import backtrader as bt
import pandas_ta as ta
from sqlalchemy import create_engine
import matplotlib.pyplot as plt


# 本代码仅用于回测研究，实盘使用风险自担

def get_stock_data_from_db(stock_code="600101", market="sh", start_date="2019-01-01"):
    """
    从数据库提取单只股票历史数据（修复版本）
    """
    # 使用SQLAlchemy连接（推荐方式）
    engine = create_engine('mysql+pymysql://root:Root_123@192.168.1.78:3306/baostock_api_market_data')

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

        # 交叉信号
        self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # 添加交易计数器
        self.trade_count = 0
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.trade_count += 1
                print(f'买入完成: 价格={order.executed.price:.2f}, 成本={order.executed.value:.2f}, 手续费={order.executed.comm:.2f}')
            elif order.issell():
                self.trade_count += 1
                print(f'卖出完成: 价格={order.executed.price:.2f}, 收益={order.executed.pnl:.2f}')

            # 重置订单状态
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
                    print(f'{self.data.datetime.date()} - MACD金叉买入信号，价格: {self.data.close[0]:.2f}')
        else:
            # MACD死叉卖出信号
            if self.macd_cross < 0:
                self.order = self.sell(size=self.position.size)
                print(f'{self.data.datetime.date()} - MACD死叉卖出信号，价格: {self.data.close[0]:.2f}')


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
    # 获取更早的数据以确保MACD有足够初始化周期
    stock_data = get_stock_data_from_db("600101", "sh", "2019-01-01")
    print(f"数据量：{len(stock_data)}条")
    print(f"数据时间范围：{stock_data.index[0]} 到 {stock_data.index[-1]}")

    # 使用pandas_ta计算MACD（用于验证）
    stock_data_with_macd = calculate_macd_with_pandas_ta(stock_data)

    # 检查MACD指标是否计算成功
    macd_cols = [col for col in stock_data_with_macd.columns if 'MACD' in col]
    if macd_cols:
        # 找到第一个非NaN的MACD值
        first_valid_idx = stock_data_with_macd[macd_cols[0]].first_valid_index()
        if first_valid_idx is not None:
            print(f"MACD指标从 {first_valid_idx} 开始有效")
            print(f"前5个有效MACD值:")
            valid_data = stock_data_with_macd.loc[first_valid_idx:].head(5)
            print(valid_data[macd_cols])

    # 创建回测引擎
    cerebro = bt.Cerebro()

    # 添加策略
    cerebro.addstrategy(MACDStrategy)

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

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Transactions, _name='transactions')

    # 运行回测
    print('\n开始回测...')
    results = cerebro.run()
    strategy = results[0]

    # 打印回测结果
    final_value = cerebro.broker.getvalue()
    total_return = (final_value / initial_cash - 1) * 100

    print('\n=== 回测结果 ===')
    print(f'初始资金: {initial_cash:,.2f}')
    print(f'最终资金: {final_value:,.2f}')
    print(f'总收益率: {total_return:.2f}%')
    print(f'交易次数: {strategy.trade_count}')

    # 安全获取分析器结果
    sharpe_ratio = safe_get_analysis(strategy.analyzers.sharpe, 'sharperatio', 0)
    max_drawdown = safe_get_analysis(strategy.analyzers.drawdown, 'max.drawdown', 0)
    annual_return = safe_get_analysis(strategy.analyzers.returns, 'rnorm100', 0)

    print(f'夏普比率: {sharpe_ratio:.2f}' if isinstance(sharpe_ratio, (int, float)) else f'夏普比率: {sharpe_ratio}')
    print(f'最大回撤: {max_drawdown:.2f}%' if isinstance(max_drawdown, (int, float)) else f'最大回撤: {max_drawdown}')
    print(f'年化收益率: {annual_return:.2f}%' if isinstance(annual_return, (int, float)) else f'年化收益率: {annual_return}')

    # 交易分析
    trades_analysis = safe_get_analysis(strategy.analyzers.trades, 'total.total', 0)
    print(f'总交易数: {trades_analysis}')

    # 如果收益率不为0，绘制图表
    if abs(total_return) > 0.01 and strategy.trade_count > 0:
        print('\n生成回测图表...')
        cerebro.plot(style='candlestick', volume=True)
    else:
        print('\n无有效交易，跳过图表生成')
        print('可能原因:')
        print('1. MACD指标需要更多数据周期进行初始化')
        print('2. 在回测期间内没有产生有效的金叉/死叉信号')
        print('3. 数据质量问题')


if __name__ == '__main__':
    run_backtest()