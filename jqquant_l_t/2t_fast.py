# 短线选股策略（PE排序+严格风控）
# 策略逻辑：非ST、上市>100天、PE>0、周成交量增长率>100%、近50日涨跌幅<20%、换手率<20%、当日涨幅0%-3%、市值30亿-300亿、非科创/创业/北交所、量比>1
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
    g.max_hold_days = 3  # 最大持有天数
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
    优化后的选股函数：批量处理数据，减少API调用次数
    """
    # 第一步：快速基础过滤（无数据获取）
    all_stocks = get_all_securities(types=['stock'], date=context.current_dt).index
    filtered_stocks = basic_filter(all_stocks, context)

    if len(filtered_stocks) == 0:
        return []

    # 第二步：批量获取基本面数据（一次查询）
    q = query(
        valuation.code,
        valuation.pe_ratio,
        valuation.market_cap,
        valuation.turnover_ratio
    ).filter(valuation.code.in_(filtered_stocks))

    df = get_fundamentals(q, date=context.current_dt)
    df = df[(df['pe_ratio'] > 0) & (df['market_cap'].between(30, 300))]

    if df.empty:
        return []

    # 第三步：批量技术指标过滤
    stock_list = df['code'].tolist()
    technical_ok_stocks = batch_check_technical_conditions(stock_list, context)

    # 过滤出符合条件的股票
    df_final = df[df['code'].isin(technical_ok_stocks)]

    if df_final.empty:
        return []

    # 按PE降序排列并返回前5只
    return df_final.sort_values('pe_ratio', ascending=False)['code'].tolist()[:5]


def batch_check_technical_conditions(stock_list, context):
    """
    批量检查技术指标条件
    """
    if len(stock_list) == 0:
        return []

    ok_stocks = []

    try:
        # 修改：添加 panel=False 参数
        prices = get_price(stock_list, end_date=context.current_dt,
                           count=50, frequency='daily',
                           fields=['close', 'volume', 'high', 'low'],
                           panel=False)  # 添加这行

        # 批量获取换手率数据
        turnovers = get_valuation(stock_list, end_date=context.current_dt,
                                  count=1, fields=['turnover_ratio'])

        # 获取当前数据（用于当日涨幅判断）
        current_data = get_current_data()

        # 修改：处理新的数据格式
        # 将数据重新组织为以股票代码为键的字典
        price_dict = {}
        for stock in stock_list:
            stock_data = prices[prices['code'] == stock]
            if not stock_data.empty:
                price_dict[stock] = stock_data

        for stock in stock_list:
            if stock in price_dict and check_single_stock_conditions(stock, price_dict[stock], turnovers, current_data, context):
                ok_stocks.append(stock)

    except Exception as e:
        log.error('批量检查技术指标出错: %s' % str(e))

    return ok_stocks


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
        if stock.startswith('68') or stock.startswith('30') or stock.startswith('8') or stock.startswith('4'):
            continue

        # 过滤上市天数不足100天的股票
        start_date = get_security_info(stock).start_date
        if (context.current_dt.date() - start_date).days <= 100:
            continue

        filtered.append(stock)

    return filtered


def check_single_stock_conditions(stock, stock_prices, turnovers, current_data, context):
    """
    检查单个股票的技术条件（使用批量获取的数据）
    """
    try:
        # 检查股票数据是否存在
        if stock_prices.empty or len(stock_prices) < 50:
            return False

        stock_turnovers = turnovers[turnovers['code'] == stock]

        if stock_turnovers.empty:
            return False

        # 1. 检查近50日涨跌幅 < 20%
        price_50_days_ago = stock_prices['close'].iloc[0]
        current_price = stock_prices['close'].iloc[-1]
        pct_change_50 = (current_price - price_50_days_ago) / price_50_days_ago

        if pct_change_50 >= 0.2:
            return False

        # 2. 检查周成交量增长率 > 100%
        if len(stock_prices) >= 10:
            last_week_volume = stock_prices['volume'].iloc[-5:].mean()
            prev_week_volume = stock_prices['volume'].iloc[-10:-5].mean()

            if prev_week_volume > 0:  # 避免除零
                volume_growth = (last_week_volume - prev_week_volume) / prev_week_volume
                if volume_growth <= 1.0:
                    return False

        # 3. 检查当日涨幅 0%-3%
        today_open = current_data[stock].day_open
        today_change = (current_price - today_open) / today_open
        if today_change < 0 or today_change > 0.03:
            return False

        # 4. 检查换手率 < 20%
        turnover = stock_turnovers['turnover_ratio'].iloc[0]
        if turnover >= 20:
            return False

        # 5. 检查量比 > 1
        if len(stock_prices) >= 6:
            today_volume = stock_prices['volume'].iloc[-1]
            past_5_days_avg_volume = stock_prices['volume'].iloc[-6:-1].mean()

            if past_5_days_avg_volume > 0:
                volume_ratio = today_volume / past_5_days_avg_volume
                if volume_ratio <= 1:
                    return False

        return True

    except Exception as e:
        log.error('检查股票%s技术条件出错: %s' % (stock, str(e)))
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
    卖出逻辑：检查止损止盈条件和持有天数
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
            # 修改：添加 panel=False 参数
            hist_data = get_price(stock, end_date=context.current_dt,
                                  count=hold_days + 1, frequency='daily',
                                  fields=['high'], panel=False)  # 添加这行

            # 修改：处理新的数据格式
            hist_high = hist_data['high'].max()

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
