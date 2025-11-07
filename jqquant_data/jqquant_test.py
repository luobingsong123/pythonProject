# 导入聚宽库
from jqdata import *

# 初始化参数
def initialize(context):
    # 定义监控股票（平安银行）
    g.security = '000001.XSHE'
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式（真实价格）
    set_option('use_real_price', True)

    # 交易费用设置（佣金0.03%+印花税0.1%）
    set_order_cost(OrderCost(
        open_tax=0.001,
        close_tax=0.001,
        open_commission=0.0003,
        close_commission=0.0003,
        close_today_commission=0,
        min_commission=5
    ), type='stock')

    # 运行频率（每日开盘执行）
    run_daily(market_open, time='09:00')

# MACD参数设置
FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9

# 主交易逻辑
def market_open(context):
    security = g.security

    # 获取历史收盘价（需要至少26天数据）
    close_data = attribute_history(security, 30, '1d', ['close'])

    # 计算MACD指标
    dif, dea, _ = MACD(close_data['close'], FAST_PERIOD, SLOW_PERIOD, SIGNAL_PERIOD)

    # 反转数据为正序（最新数据在末尾）
    dif = dif[::-1]
    dea = dea[::-1]

    # 获取当前持仓状态
    position = context.portfolio.positions[security].total_amount
    cash = context.portfolio.available_cash

    # 日志输出当前MACD值
    log.info(f"MACD值：DIF={dif[0]:.4f}, DEA={dea[0]:.4f}")

    # 金叉买入条件（DIF上穿DEA且无持仓）
    if dif[1](@ref)<= dea[1](@ref) and dif> dea and position == 0:
        order_value(security, cash)  # 全仓买入
        log.info("MACD金叉买入信号触发")

    # 死叉卖出条件（DIF下穿DEA且有持仓）
    elif dif[1](@ref)>= dea[1](@ref) and dif< dea and position > 0:
        order_target(security, 0)  # 清仓
        log.info("MACD死叉卖出信号触发")