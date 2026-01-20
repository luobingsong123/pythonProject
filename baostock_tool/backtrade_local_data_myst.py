import pandas as pd
import backtrader as bt
import pandas_ta as ta
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
import config
from utils.logger_utils import setup_logger
import matplotlib.pyplot as plt
import os
# 导入CodeBuddy策略
from utils.strategies.codebuddy_st import CodeBuddyStrategy
# 导入CodeBuddy底分型策略
from utils.strategies.codebuddy_st_dfx import CodeBuddyStrategyDFX
# 导入策略触发点位数据库管理
from database_schema.strategy_trigger_db import StrategyTriggerDB

os.makedirs("csv", exist_ok=True)
db_config_ = config.get_db_config()
log_config = config.get_log_config()
date_config = config.get_backtrade_date_config()
logger = setup_logger(logger_name=__name__,
                   log_level=log_config["log_level"],
                   log_dir=log_config["log_dir"], )

db_url = URL.create(
    drivername="mysql+pymysql",
    username=db_config_["user"],
    password=db_config_["password"],
    host=db_config_["host"],
    port=db_config_["port"],
    database=db_config_["database"]
)

engine = create_engine(db_url)

# ============ 回测策略配置 ============
BACKTEST_CONFIG = {
    'start_date': date_config["start_date"],  # 回测开始日期
    'end_date': date_config["end_date"],    # 回测截止日期
    'initial_cash': 100000,      # 初始资金
    'commission': 0.001,        # 手续费率（0.1%）
    'slippage_perc': 0.001,      # 滑点率（0.1%），按百分比计算
}


# 本代码仅用于回测研究，实盘使用风险自担

def get_stock_data_from_db(stock_code="601288", market="sh", start_date="2019-01-01"):
    # 使用SQLAlchemy连接（推荐方式）
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


def get_stock_basic_from_db():
    """
    从数据库获取个股列表
    """
    # 使用SQLAlchemy连接（推荐方式）
    query = f"""
    SELECT market, code_int, name
    FROM stock_basic_info 
    WHERE (market = 'sh' AND code_int > 600000 AND code_int < 610000)
       OR (market = 'sz' AND code_int > 0 AND code_int < 310000)
    ORDER BY code_int
    """
    df = pd.read_sql(query, engine)
    # 方法1：简单修复，直接使用code_int作为索引
    df.set_index('code_int', inplace=True)

    return df


def get_trade_calendar_from_db():
    """
    从数据库获取交易日历
    """
    # 使用SQLAlchemy连接（推荐方式）
    query = f"""
    SELECT calendar_date
    FROM trade_calendar 
    WHERE is_trading_day = 1
    ORDER BY calendar_date
    """
    df = pd.read_sql(query, engine)
    # 数据清洗与格式化
    df['calendar_date'] = pd.to_datetime(df['calendar_date'])
    df.set_index('calendar_date', inplace=True)
    df = df.ffill()  # 前向填充缺失值
    return df



class TPlus1Strategy(bt.Strategy):
    """
    基础策略类：实现T+1交易限制
    子类可重写 next() 方法实现具体交易逻辑
    """
    params = (
        ('printlog', True),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None
        # 记录买入日期，用于T+1限制
        self.buy_date = None
        # 手续费统计
        self.total_commission = 0.0
        self.buy_commission = 0.0
        self.sell_commission = 0.0
        # 盈利交易统计
        self.profit_trade_count = 0
        self.loss_trade_count = 0
        # 触发点位记录
        self.trigger_points = []
        self.current_buy_info = None  # 记录当前买入信息

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.buy_date = self.datas[0].datetime.date()
                # 统计买入手续费
                self.buy_commission += order.executed.comm
                self.total_commission += order.executed.comm
                # 记录买入触发点位
                buy_info = {
                    'date': str(self.buy_date),
                    'trigger_type': 'buy',
                    'price': float(order.executed.price),
                    'volume': float(order.executed.size),
                    'commission': float(order.executed.comm)
                }
                self.current_buy_info = buy_info
                if self.p.printlog:
                    logger.debug(f'买入执行 - 价格: {order.executed.price:.2f}, '
                              f'数量: {order.executed.size}, '
                              f'手续费: {order.executed.comm:.2f}, '
                              f'日期: {self.datas[0].datetime.date()}')
            else:  # 卖出
                # 统计卖出手续费
                self.sell_commission += order.executed.comm
                self.total_commission += order.executed.comm
                # 记录卖出触发点位
                if self.current_buy_info:
                    sell_date = self.datas[0].datetime.date()
                    sell_info = {
                        'date': str(sell_date),
                        'trigger_type': 'sell',
                        'price': float(order.executed.price),
                        'volume': float(order.executed.size),
                        'commission': float(order.executed.comm),
                        'profit': float(order.executed.pnl),
                        'profit_rate': round((order.executed.pnl / self.buyprice) * 100, 2) if self.buyprice else 0
                    }
                    # 将买入和卖出点位一起记录
                    self.trigger_points.append(self.current_buy_info)
                    self.trigger_points.append(sell_info)
                    self.current_buy_info = None
                if self.p.printlog:
                    logger.debug(f'卖出执行 - 价格: {order.executed.price:.2f}, '
                              f'数量: {order.executed.size}, '
                              f'手续费: {order.executed.comm:.2f}, '
                              f'利润: {order.executed.pnl:.2f}, '
                              f'日期: {self.datas[0].datetime.date()}')
                self.buy_date = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.p.printlog:
                logger.warning(f'订单取消/拒绝 - 状态: {order.getstatusname()}')

        self.order = None

    def notify_trade(self, trade):
        """交易完成通知"""
        if not trade.isclosed:
            return

        # 统计盈利和亏损交易
        if trade.pnlcomm > 0:
            self.profit_trade_count += 1
        elif trade.pnlcomm < 0:
            self.loss_trade_count += 1

        if self.p.printlog:
            logger.debug(f'交易利润 - 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')

    def next(self):
        """
        子类可重写此方法实现具体交易逻辑
        示例逻辑：
        if self.dataclose[0] > self.dataclose[-1]:
            self.buy()
        """
        pass

    def buy_with_t1(self, size=None, price=None, plimit=None):
        """买入方法（记录买入日期）"""
        if self.order:
            return False
        self.order = self.buy(size=size, price=price, plimit=plimit)
        return True

    def sell_with_t1(self, size=None, price=None, plimit=None):
        """卖出方法（T+1限制）"""
        if self.order:
            return False
        # T+1限制：今天买入的股票不能今天卖出
        if self.buy_date and self.datas[0].datetime.date() == self.buy_date:
            if self.p.printlog:
                logger.warning(f'T+1限制：今日买入的股票不能卖出 - 日期: {self.datas[0].datetime.date()}')
            return False
        self.order = self.sell(size=size, price=price, plimit=plimit)
        return True


class SimpleTrendStrategy(TPlus1Strategy):
    """
    简单趋势策略示例（可替换为其他策略）
    逻辑：当收盘价连续3天上涨时买入，连续3天下跌时卖出
    """
    def next(self):
        if not self.position:  # 无持仓时判断买入
            if self.dataclose[0] > self.dataclose[-1] > self.dataclose[-2]:
                self.buy_with_t1()
        else:  # 有持仓时判断卖出
            if self.dataclose[0] < self.dataclose[-1] < self.dataclose[-2]:
                self.sell_with_t1()


def run_backtest(stock_code, market, name, start_date, end_date, strategy_class=SimpleTrendStrategy, save_to_db=False):
    """
    执行单只股票的回测

    Args:
        stock_code (str): 股票代码
        market (str): 市场类型
        name (str): 股票名称
        start_date (str): 回测开始日期
        end_date (str): 回测结束日期
        strategy_class: 策略类
        save_to_db (bool): 是否保存触发点位到数据库
    """
    try:
        # 获取股票数据
        df = get_stock_data_from_db(stock_code, market, start_date)

        if df.empty:
            logger.warning(f"股票 {stock_code} ({name}) 无数据，跳过")
            return None

        # 过滤回测日期范围
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df[(df.index >= start_dt) & (df.index <= end_dt)]

        if len(df) < 30:  # 数据不足30天跳过
            logger.warning(f"股票 {stock_code} ({name}) 数据不足（{len(df)}天），跳过")
            return None

        # 创建 Cerebro 引擎
        cerebro = bt.Cerebro()

        # 添加策略
        cerebro.addstrategy(strategy_class)

        # 加载数据到回测引擎
        data = bt.feeds.PandasData(
            dataname=df,
            datetime=None,  # 使用索引作为日期
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1  # 无持仓兴趣数据
        )
        cerebro.adddata(data)

        # 设置初始资金
        cerebro.broker.setcash(BACKTEST_CONFIG['initial_cash'])

        # 设置手续费
        cerebro.broker.setcommission(commission=BACKTEST_CONFIG['commission'])

        # ============ 添加滑点设置 ============
        # 按百分比滑点：买入价格上调，卖出价格下调
        cerebro.broker.set_slippage_perc(perc=BACKTEST_CONFIG.get('slippage_perc', 0.001))

        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

        # 执行回测
        logger.info(f"{'='*60}")
        logger.info(f"开始回测 - 股票: {stock_code} ({name}), 市场类型: {market.upper()}")
        logger.info(f"回测期间: {start_date} 至 {end_date}")
        logger.info(f"{'='*60}")

        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        end_value = cerebro.broker.getvalue()

        # 获取分析结果
        strat = results[0]
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        returns = strat.analyzers.returns.get_analysis()
        trades = strat.analyzers.trades.get_analysis()

        # 输出回测结果
        logger.info(f"{'='*60}")
        logger.info(f"回测结果 - 股票: {stock_code} ({name})")
        logger.info(f"{'='*60}")
        logger.info(f"初始资金: {start_value:.2f}")
        logger.info(f"期末资金: {end_value:.2f}")
        logger.info(f"总收益率: {(end_value/start_value - 1)*100:.2f}%")
        logger.info(f"总交易次数: {trades.get('total', {}).get('total', 0)}")
        logger.info(f"盈利交易次数: {strat.profit_trade_count}")
        logger.info(f"亏损交易次数: {strat.loss_trade_count}")
        logger.info(f"总手续费: {strat.total_commission:.2f}")
        logger.info(f"买入手续费: {strat.buy_commission:.2f}")
        logger.info(f"卖出手续费: {strat.sell_commission:.2f}")
        # 在输出回测结果部分添加
        logger.info(f"手续费率: {BACKTEST_CONFIG['commission'] * 100:.2f}%")
        logger.info(f"滑点率: {BACKTEST_CONFIG.get('slippage_perc', 0) * 100:.2f}%")

        if strat.total_commission > 0:
            commission_ratio = (strat.total_commission / start_value) * 100
            logger.info(f"手续费占比: {commission_ratio:.2f}%")
        else:
            logger.info(f"手续费占比: 0.00%")

        if sharpe and 'sharperatio' in sharpe and sharpe['sharperatio'] is not None:
            logger.info(f"夏普比率: {sharpe['sharperatio']:.2f}")
        else:
            logger.info("夏普比率: N/A")

        if drawdown and 'max' in drawdown:
            logger.info(f"最大回撤: {drawdown['max']['drawdown']:.2f}%")

        if returns and 'rtot' in returns:
            logger.info(f"总收益率: {returns['rtot']*100:.2f}%")

        logger.info(f"{'='*60}")

        # 保存触发点位到数据库
        if save_to_db:
            try:
                strategy_db = StrategyTriggerDB()
                # 获取策略名称（从策略类的STRATEGY_NAME属性获取）
                strategy_name = getattr(strategy_class, 'STRATEGY_NAME', strategy_class.__name__)
                # 保存触发点位
                strategy_db.insert_trigger_points(
                    strategy_name=strategy_name,
                    stock_code=stock_code,
                    market=market,
                    trigger_points_json=strat.trigger_points,
                    backtest_start_date=start_date,
                    backtest_end_date=end_date,
                    trigger_count=len(strat.trigger_points)
                )
                logger.info(f"触发点位已保存到数据库: {len(strat.trigger_points)} 个点位")
            except Exception as e:
                logger.error(f"保存触发点位到数据库失败: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())

        return {
            'stock_code': stock_code,
            'name': name,
            'market': market,
            'start_value': start_value,
            'end_value': end_value,
            'return_rate': (end_value/start_value - 1)*100,
            'trade_count': trades.get('total', {}).get('total', 0),
            'profit_trade_count': strat.profit_trade_count,
            'loss_trade_count': strat.loss_trade_count,
            'total_commission': strat.total_commission,
            'buy_commission': strat.buy_commission,
            'sell_commission': strat.sell_commission,
            'commission_ratio': (strat.total_commission / start_value) * 100 if start_value > 0 else 0,
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0) if drawdown else 0,
            'sharpe_ratio': sharpe.get('sharperatio') if sharpe and sharpe.get('sharperatio') is not None else 0
        }

    except Exception as e:
        logger.error(f"回测股票 {stock_code} 时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def batch_backtest(start_date, end_date, strategy_class=SimpleTrendStrategy, save_to_db=False):
    """
    批量回测所有股票

    Args:
        start_date (str): 回测开始日期
        end_date (str): 回测结束日期
        strategy_class: 策略类
        save_to_db (bool): 是否保存触发点位到数据库
    """
    # 获取交易日历，过滤回测日期范围
    calendar_df = get_trade_calendar_from_db()
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    calendar_df = calendar_df[(calendar_df.index >= start_dt) & (calendar_df.index <= end_dt)]

    logger.info(f"回测交易日历: {len(calendar_df)} 个交易日")
    logger.info(f"交易日历起止: {calendar_df.index[0]} 至 {calendar_df.index[-1]}")

    # 获取股票列表
    stock_codes = get_stock_basic_from_db()
    logger.info(f"共 {len(stock_codes)} 只股票需要回测")

    # 存储所有回测结果
    all_results = []
    summary_file = f"csv/backtest_summary_{start_date.replace('-', '')}_to_{end_date.replace('-', '')}.csv"

    # 遍历每只股票进行回测
    for index, row in stock_codes.iterrows():
        stock_code = index
        market = row['market']
        name = row['name'].replace('*', '')

        result = run_backtest(stock_code, market, name, start_date, end_date, strategy_class, save_to_db)
        if result:
            all_results.append(result)

    # 保存汇总结果
    if all_results:
        summary_df = pd.DataFrame(all_results)
        summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
        logger.info(f"{'='*60}")
        logger.info(f"批量回测完成！共回测 {len(all_results)} 只股票")
        logger.info(f"汇总结果已保存至: {summary_file}")
        logger.info(f"{'='*60}")

        # 输出统计信息
        avg_return = summary_df['return_rate'].mean()
        avg_drawdown = summary_df['max_drawdown'].mean()
        profit_count = (summary_df['return_rate'] > 0).sum()
        logger.info(f"平均收益率: {avg_return:.2f}%")
        logger.info(f"平均最大回撤: {avg_drawdown:.2f}%")
        logger.info(f"盈利股票数: {profit_count}/{len(summary_df)}")
        logger.info(f"{'='*60}")
    else:
        logger.warning("没有回测结果")


if __name__ == "__main__":
    # 单只股票回测示例
    # 使用CodeBuddy底分型策略进行回测，并保存触发点位到数据库
    run_backtest(
        stock_code="601288",
        market="sh",
        name="农业银行",
        start_date=BACKTEST_CONFIG['start_date'],
        end_date=BACKTEST_CONFIG['end_date'],
        # strategy_class=CodeBuddyStrategyDFX,    # 使用CodeBuddy底分型策略
        strategy_class=CodeBuddyStrategy,    #  使用CodeBuddy策略
        save_to_db=True  # 设置为True保存触发点位到数据库
    )

    # # 批量回测（保存触发点位到数据库）
    # batch_backtest(
    #     start_date=BACKTEST_CONFIG['start_date'],
    #     end_date=BACKTEST_CONFIG['end_date'],
    #     strategy_class=CodeBuddyStrategy,
    #     save_to_db=True  # 设置为True保存触发点位到数据库
    # )
