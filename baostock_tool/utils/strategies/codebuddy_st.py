import backtrader as bt
from utils.logger_utils import setup_logger
import config

log_config = config.get_log_config()
logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"])

class CodeBuddyStrategy(bt.Strategy):
    """
    CodeBuddy策略：
    1. 检查当前交易日成交量是否为20日内最低，如果是，则在下一交易日以开盘价买入
    2. 买入后的下一个交易日卖出
    """
    params = (
        ('period', 20),          # 查找最低成交量的周期
        ('printlog', True),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datavolume = self.datas[0].volume
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.buy_date = None
        self.hold_days = 0  # 持有天数计数
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
        self.last_trigger_volume = None  # 记录触发时的成交量

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.buy_date = self.datas[0].datetime.date()
                self.hold_days = 1
                # 统计买入手续费
                self.buy_commission += order.executed.comm
                self.total_commission += order.executed.comm
                # 记录买入触发点位
                buy_info = {
                    'date': str(self.buy_date),
                    'trigger_type': 'buy',
                    'price': float(order.executed.price),
                    'volume': float(order.executed.size),
                    'commission': float(order.executed.comm),
                    'volume_rank': f'{self.p.period}日最低',
                    'trigger_volume': float(self.last_trigger_volume) if self.last_trigger_volume else None
                }
                self.current_buy_info = buy_info
                self.last_trigger_volume = None
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
                        'profit_rate': round((order.executed.pnl / self.buyprice) * 100, 2) if self.buyprice else 0,
                        'hold_days': self.hold_days
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
                self.hold_days = 0

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
            logger.info(f'交易利润 - 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')

    def next(self):
        """主逻辑"""
        # 如果有待处理订单，跳过
        if self.order:
            return

        # 如果有持仓，检查是否需要卖出
        if self.position:
            self.hold_days += 1
            # 持有第2天卖出（买入后的下一个交易日）
            if self.hold_days >= 2:
                self.order = self.sell()
            return

        # 无持仓时，检查买入条件
        # 检查是否有足够的历史数据
        if len(self.datavolume) < self.p.period + 1:
            return

        # 获取过去20天的成交量数据（不包含当天）
        volume_window = [self.datavolume[-i] for i in range(1, self.p.period + 1)]

        # 检查昨天成交量是否为20日内最低
        yesterday_volume = self.datavolume[-1]
        min_volume = min(volume_window)

        if yesterday_volume == min_volume:
            # 成交量为20日内最低，下一天以开盘价买入
            # 记录触发时的成交量
            self.last_trigger_volume = yesterday_volume
            # 注意：next()在当前bar执行，下单会在下一个bar执行
            # 但我们需要在"下一个交易日"买入，所以这里使用limitorder
            # 由于策略描述是"下一交易日以开盘价买入"，使用marketorder即可
            # 因为next()运行时是当前bar收盘后，order会在下一天开盘执行
            if self.p.printlog:
                logger.info(f'触发买入信号 - 当前日期: {self.datas[0].datetime.date()}, '
                          f'昨日成交量: {yesterday_volume}, '
                          f'20日最低成交量: {min_volume}')
            self.order = self.buy()
