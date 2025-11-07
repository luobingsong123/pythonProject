# 本地数据接口配置（需申请聚宽本地数据权限）
from jqdatasdk import *


# 初始化本地数据连接
set_benchmark('000300.XSHG')
set_option('use_real_price', True)
set_order_cost(OrderCost(open_tax=0.001, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

# 本地数据缓存路径（需手动创建）
data_path = "D:/jqquant_data"
set_data_path(data_path)


# 基础策略模板（MACD金叉策略）
def initialize(context):
    g.security = get_index_stocks('000300.XSHG')
    run_daily(handle_data, time='09:00')


def handle_data(context, data):
    # 本地数据获取
    close = data.history(g.security, 'close', 30, '1d')

    # 指标计算
    dif, dea = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)[0:2]

    # 信号判断
    if cross_over(dif, dea):
        order_target(g.security, 100000)
    elif cross_under(dif, dea):
        order_target(g.security, 0)

# 多账户并行测试
accounts = {
    'account1': '123456',
    'account2': '654321'
}

def initialize(context):
    for acc in accounts:
        set_account(acc)

# 实时行情订阅
subscribe(symbols='000001.XSHE', frequency='1m')

def on_bar(context, bars):
    for bar in bars:
        print(f"{bar.security} 最新价：{bar.close_price}")


# 异常捕获框架
try:
    # 核心交易逻辑
except DataError as e:
    log.error(f"数据异常：{str(e)}")
except OrderError as e:
    log.error(f"订单异常：{str(e)}")
except Exception as e:
    log.error(f"未知错误：{str(e)}")