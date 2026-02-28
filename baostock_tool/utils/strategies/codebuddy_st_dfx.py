import backtrader as bt
from ..logger_utils import setup_logger
from baostock_tool import config

log_config = config.get_log_config()
logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"])

class CodeBuddyStrategyDFX(bt.Strategy):
    """
    CodeBuddy底分型策略：
    1. 检查K线是否形成底分型（中间K线最低）
    2. 出现底分型后，下一交易日以开盘价买入
    3. 设置止盈、止损和持仓天数限制

    底分型定义：
    - 连续三根K线：K1(前天), K2(昨天), K3(今天)
    - 条件：K2的最低价 < K1的最低价 且 K2的最低价 < K3的最低价
    """
    # 策略名称（用于数据库存储）
    STRATEGY_NAME = "底分型策略"

    params = (
        ('profit_threshold', 10.0),    # 总浮盈阈值（百分比）
        ('drawdown_threshold', 3.0),  # 总回撤阈值（百分比）
        ('hold_days_threshold', 99999),  # 最大持仓天数阈值
        ('printlog', True),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datalow = self.datas[0].low
        self.datahigh = self.datas[0].high
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
        self.last_trigger_dfx_info = None  # 记录底分型触发信息

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
                    'volume_rank': '底分型',
                    'trigger_volume': str(self.last_trigger_dfx_info) if self.last_trigger_dfx_info else None
                }
                self.current_buy_info = buy_info
                self.last_trigger_dfx_info = None
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
                    # 买入记录
                    self.trigger_points.append(self.current_buy_info)
                    # 底分型触发记录
                    if self.last_trigger_dfx_info:
                        dfx_info = self.last_trigger_dfx_info.copy()
                        dfx_info['trigger_type'] = 'buy_signal'
                        self.trigger_points.append(dfx_info)
                    # 卖出记录
                    self.trigger_points.append(sell_info)
                    self.current_buy_info = None
                    self.last_trigger_dfx_info = None
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
                logger.warning(f'证券代码: {self.datas[0]}  订单取消/拒绝 - 状态: {order.getstatusname()} - 日期: {self.datas[0].datetime.date()}')

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

    def is_bottom_fractal(self):
        """
        判断是否形成底分型
        底分型定义：连续三根K线，中间K线的最低价最低
        返回: (是否为底分型, 触发信息字典)
        """
        # 需要至少3根K线数据
        if len(self.datalow) < 3:
            return False, None

        # 获取最近三根K线的最低价
        # low[-3] = 前天, low[-2] = 昨天, low[-1] = 今天
        low_t3 = self.datalow[-3]  # 前天最低价
        low_t2 = self.datalow[-2]  # 昨天最低价
        low_t1 = self.datalow[-1]  # 今天最低价

        # 判断是否为底分型：昨天最低价 < 前天最低价 且 昨天最低价 < 今天最低价
        if low_t2 < low_t3 and low_t2 < low_t1:
            # 获取对应的日期
            date_t3 = self.datas[0].datetime.date(-3)
            date_t2 = self.datas[0].datetime.date(-2)
            date_t1 = self.datas[0].datetime.date(-1)

            trigger_info = {
                'date_t3': str(date_t3),
                'low_t3': float(low_t3),
                'date_t2': str(date_t2),
                'low_t2': float(low_t2),
                'date_t1': str(date_t1),
                'low_t1': float(low_t1)
            }
            return True, trigger_info

        return False, None

    def stop(self):
        """回测结束时的处理"""
        # 如果还有未平仓的买入记录，需要保存到trigger_points
        if self.current_buy_info:
            # 标记为未完成交易
            self.trigger_points.append(self.current_buy_info)
            # 保存底分型触发记录
            if self.last_trigger_dfx_info:
                dfx_info = self.last_trigger_dfx_info.copy()
                dfx_info['trigger_type'] = 'buy_signal'
                self.trigger_points.append(dfx_info)
            if self.p.printlog:
                logger.warning(f'回测结束，存在未平仓持仓 - 买入日期: {self.current_buy_info["date"]}, '
                          f'持仓天数: {self.hold_days}')

    def next(self):
        """主逻辑"""
        # 如果有待处理订单，跳过
        if self.order:
            return

        # 如果有持仓，检查是否需要卖出
        if self.position:
            self.hold_days += 1
            # 计算当前持仓的盈亏情况
            current_price = self.dataclose[0]
            if self.buyprice > 0:
                # 计算总浮盈百分比
                profit_rate = ((current_price - self.buyprice) / self.buyprice) * 100

                # 检查卖出条件
                # 条件1：总浮盈大于阈值
                # 条件2：总回撤大于阈值（负收益）
                # 条件3：持有天数大于阈值
                sell_condition_met = (profit_rate >= self.p.profit_threshold) or \
                                     (profit_rate <= -self.p.drawdown_threshold) or \
                                     (self.hold_days >= self.p.hold_days_threshold)

                if sell_condition_met:
                    # 满仓卖出：卖出全部持仓
                    if self.p.printlog:
                        sell_reason = []
                        if profit_rate >= self.p.profit_threshold:
                            sell_reason.append(f'浮盈达到{self.p.profit_threshold}%')
                        if profit_rate <= -self.p.drawdown_threshold:
                            sell_reason.append(f'浮亏达到-{self.p.drawdown_threshold}%')
                        if self.hold_days >= self.p.hold_days_threshold:
                            sell_reason.append(f'持仓天数达到{self.p.hold_days_threshold}天')

                        logger.info(f'触发卖出信号 - 日期: {self.datas[0].datetime.date()}, '
                                  f'当前价格: {current_price:.2f}, '
                                  f'买入价格: {self.buyprice:.2f}, '
                                  f'浮盈: {profit_rate:.2f}%, '
                                  f'持有天数: {self.hold_days}, '
                                  f'卖出原因: {", ".join(sell_reason)}, '
                                  f'卖出数量: {self.position.size}')
                    self.order = self.sell(size=self.position.size)
            return

        # 无持仓时，检查买入条件
        # 检查是否形成底分型
        is_dfx, dfx_info = self.is_bottom_fractal()

        if is_dfx:
            # 形成底分型，记录触发信息
            self.last_trigger_dfx_info = dfx_info
            # 在下一个交易日开盘买入
            # next()在当前bar收盘后执行，order会在下一天开盘执行
            if self.p.printlog:
                logger.info(f'触发买入信号 - 当前日期: {self.datas[0].datetime.date()}, '
                          f'底分型形成: {dfx_info["date_t3"]}低({dfx_info["low_t3"]:.2f}) -> '
                          f'{dfx_info["date_t2"]}低({dfx_info["low_t2"]:.2f}) -> '
                          f'{dfx_info["date_t1"]}低({dfx_info["low_t1"]:.2f})')
            # 计算最大可买数量，使用全部可用资金
            cash = self.broker.getvalue()
            # 获取当前价格，使用昨天的收盘价作为参考
            price = self.dataclose[-1]
            # 计算可买数量（考虑手续费，预留10%作为手续费缓冲）
            if price > 0:
                buy_size = int((cash * 0.90) / price)  # 90%仓位，预留10%手续费缓冲
                if buy_size > 0:
                    self.order = self.buy(size=buy_size)
