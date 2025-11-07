# 自用户自定义策略：短线选股策略（PE排序+严格风控）
# 排序条件：市盈率(PE)从大到小降序排列
# 交易规则：分仓操作，每只股票50%资金，开盘买入，严格止损止盈

from jqdata import *
import pandas as pd
import numpy as np
import datetime


# 初始化函数
def initialize(context):
    # 设置基准收益率
    set_benchmark('000300.XSHG')
    # 设置是否使用真实价格
    set_option('use_real_price', True)
    # 设置手续费/印花税
    set_order_cost(OrderCost(open_tax=0,
                             close_tax=0.001,
                             open_commission=0.0003,
                             close_commission=0.0003,
                             min_commission=5),
                   type='stock')
    # 设置滑点
    set_slippage(FixedSlippage(0.00246))

    # 全局变量
    g.security = None
    g.hold_days = {}  # 记录每只股票的持有天数
    g.max_hold_days = 2  # 最大持有天数
    g.position_size = 0.5  # 每只股票仓位比例（50%）
    g.max_positions = 2  # 最大持仓数量

    # 运行定时器
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    run_daily(market_open, time='open', reference_security='000300.XSHG')
    run_daily(market_close, time='close', reference_security='000300.XSHG')


def before_market_open(context):
    # 盘前选股
    stock_list = select_stocks(context)
    if len(stock_list) > 0:
        g.security = stock_list[0]  # 选择PE最高的股票
        log.info('今日选股结果: %s' % g.security)
    else:
        g.security = None
        log.info('今日无符合条件股票')


def market_open(context):
    # 开盘时执行交易
    execute_trades(context)


def market_close(context):
    # 收盘后更新持有天数
    update_hold_days(context)


def select_stocks(context):
    """
    选股函数：严格按照用户策略条件筛选股票[2,3](@ref)
    """
    # 获取股票池（过滤ST、停牌、科创/创业/北交所）
    all_stocks = get_all_securities(types=['stock'], date=context.current_dt).index
    filtered_stocks = basic_filter(all_stocks, context)

    if len(filtered_stocks) == 0:
        return []

    # 获取基本面数据[4](@ref)
    q = query(
        valuation.code,
        valuation.pe_ratio,
        valuation.market_cap,
        valuation.turnover_ratio
    ).filter(
        valuation.code.in_(filtered_stocks),
        valuation.pe_ratio > 0,  # PE>0
        valuation.market_cap.between(30, 300)  # 市值30亿-300亿
    )

    df = get_fundamentals(q, date=context.current_dt)
    if df.empty:
        return []

    # 进一步技术指标过滤
    final_stocks = []
    for stock in df['code']:
        if check_technical_conditions(stock, context):
            final_stocks.append(stock)

    # 按PE降序排列[3](@ref)
    df_final = df[df['code'].isin(final_stocks)]
    df_sorted = df_final.sort_values('pe_ratio', ascending=False)

    return df_sorted['code'].tolist()[:5]  # 返回前5只供选择


def basic_filter(stock_list, context):
    """
    基础过滤：ST、停牌、板块等[2](@ref)
    """
    current_data = get_current_data()
    filtered = []

    for stock in stock_list:
        # 过滤ST、*ST、退市股票
        if current_data[stock].is_st or current_data[stock].name.startswith('*') or '退' in current_data[stock].name:
            continue

        # 过滤停牌股票
        if current_data[stock].paused:
            continue

        # 过滤科创/创业/北交所股票[2](@ref)
        if stock.startswith('68') or stock.startswith('8') or stock.startswith('4'):
            continue

        # 过滤上市天数不足100天的股票
        start_date = get_security_info(stock).start_date
        if (context.current_dt.date() - start_date).days <= 100:
            continue

        filtered.append(stock)

    return filtered


def check_technical_conditions(stock, context):
    """
    检查技术指标条件[3](@ref)
    """
    try:
        # 获取历史价格数据
        hist_data = get_price(stock,
                              end_date=context.previous_date,
                              count=50,
                              frequency='daily',
                              fields=['close', 'volume', 'high', 'low'])

        if len(hist_data) < 50:
            return False

        # 计算近50日涨跌幅
        price_50_days_ago = hist_data['close'].iloc[0]
        current_price = hist_data['close'].iloc[-1]
        pct_change_50 = (current_price - price_50_days_ago) / price_50_days_ago

        if 0.2 >= pct_change_50 >= -0.2:
            return False

        # 计算周成交量增长率
        if len(hist_data) >= 10:
            last_week_volume = hist_data['volume'].iloc[-5:].mean()
            prev_week_volume = hist_data['volume'].iloc[-10:-5].mean()
            if prev_week_volume == 0:
                volume_growth = 0
            else:
                volume_growth = (last_week_volume - prev_week_volume) / prev_week_volume

            if volume_growth <= 1.0:  # 周成交量增长率>100%
                return False

        # 前一个交易日的收盘价
        previous_close = hist_data['close'].iloc[0]
        # 获取当日开盘价
        today_open = get_current_data()[stock].day_open
        # 计算基于昨日收盘价和今日开盘价的开盘涨幅
        expected_open_change = (today_open - previous_close) / previous_close
        # 开盘涨幅0%-3%
        if expected_open_change < 0 or expected_open_change > 0.03:
            return False

        # 检查换手率<20%
        turnover_df = get_valuation(stock, end_date=context.previous_date, count=1, fields=['turnover_ratio'])
        if not turnover_df.empty:
            turnover = turnover_df['turnover_ratio'].iloc[0]
            if turnover <= 20:  # 注意：换手率单位是百分比，所以20表示20%
                return False
        else:
            return False  # 如果获取不到数据，保守起见认为不符合条件

        hist_data = get_price(stock, end_date=context.previous_date, count=6, frequency='daily', fields=['volume'])

        if len(hist_data) < 6:
            return False

        # 使用前一日作为"当日"，前6日作为历史数据
        yesterday_volume = hist_data['volume'].iloc[-1]  # 前一日成交量
        past_5_days_avg_volume = hist_data['volume'].iloc[-6:-1].mean()  # 前2-6日平均成交量

        if past_5_days_avg_volume == 0:
            volume_ratio = float('inf')
        else:
            volume_ratio = yesterday_volume / past_5_days_avg_volume

        # 量比>1的条件改为基于昨日数据
        if volume_ratio <= 1:
            return False

        return True

    except Exception as e:
        log.error('检查技术指标出错: %s' % str(e))
        return False


def execute_trades(context):
    """
    执行交易：先卖出，后买入[4](@ref)
    """
    # 1. 检查并执行卖出
    sell_stocks(context)

    # 2. 执行买入
    buy_stocks(context)


def sell_stocks(context):
    """
    卖出逻辑：检查止损止盈条件和持有天数[2](@ref)
    """
    current_positions = {stock: amount for stock, amount in context.portfolio.positions.items()
                         if amount.total_amount > 0}

    for stock, position in current_positions.items():
        # 检查持有天数
        hold_days = g.hold_days.get(stock, 0)
        if hold_days >= g.max_hold_days:
            if order_target_value(stock, 0):
                log.info('持有期满卖出: %s, 持有天数: %d' % (stock, hold_days))
                g.hold_days.pop(stock, None)
            continue

        # 检查止损止盈条件
        current_price = get_current_data()[stock].last_price
        avg_cost = position.avg_cost

        # 计算收益率
        returns = (current_price - avg_cost) / avg_cost

        # 止损条件：收益率≤-5%
        if returns <= -0.05:
            if order_target_value(stock, 0):
                log.info('止损卖出: %s, 收益率: %.2f%%' % (stock, returns * 100))
                g.hold_days.pop(stock, None)

        # 止盈条件：收益率≥15%且从最高点回落2%
        elif returns >= 0.15:
            # 获取近期最高价（简化处理，使用持有期间最高价）
            hist_high = get_price(stock, end_date=context.previous_date,
                                  count=hold_days + 1, frequency='daily',
                                  fields=['high'])['high'].max()

            if current_price <= hist_high * 0.98:  # 从最高点回落2%
                if order_target_value(stock, 0):
                    log.info('止盈卖出: %s, 收益率: %.2f%%' % (stock, returns * 100))
                    g.hold_days.pop(stock, None)


def buy_stocks(context):
    """
    买入逻辑：
    - 如果没有持仓，使用半仓资金买入
    - 如果已有持仓，将剩余资金全部买入第二只股票
    """
    if g.security is None:
        return

    # 检查是否已持有该股票
    if g.security in context.portfolio.positions and context.portfolio.positions[g.security].total_amount > 0:
        return

    # 计算当前持仓数量
    current_positions = len([p for p in context.portfolio.positions.values() if p.total_amount > 0])

    if current_positions >= g.max_positions:
        return

    # 计算买入金额
    total_value = context.portfolio.total_value
    available_cash = context.portfolio.available_cash

    if current_positions == 0:
        # 没有持仓，使用半仓资金买入
        buy_value = total_value * g.position_size
        log.info('无持仓，使用半仓买入: %s, 金额: %.2f' % (g.security, buy_value))
    else:
        # 已有持仓，将剩余资金全部买入
        buy_value = available_cash
        log.info('已有持仓，使用剩余资金买入: %s, 金额: %.2f' % (g.security, buy_value))

    # 执行买入
    if buy_value > 0:
        if order_target_value(g.security, buy_value):
            log.info('买入股票: %s, 金额: %.2f, 总资金: %.2f' % (g.security, buy_value, total_value))
            g.hold_days[g.security] = 0


def update_hold_days(context):
    """
    更新持有天数
    """
    for stock in list(g.hold_days.keys()):
        if stock in context.portfolio.positions and context.portfolio.positions[stock].total_amount > 0:
            g.hold_days[stock] += 1
        else:
            g.hold_days.pop(stock, None)


def handle_data(context, data):
    """
    每分钟执行的数据处理（可选）
    """
    pass