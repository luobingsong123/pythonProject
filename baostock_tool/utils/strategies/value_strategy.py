import backtrader as bt
from ..logger_utils import setup_logger
from baostock_tool import config
import pandas as pd
import talib
import numpy as np

log_config = config.get_log_config()
logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"])


class ValueStrategy(bt.Strategy):
    """
    价值投资策略：

    筛选条件：
    1. 市盈率(PE TTM)小于30
    2. 市净率(PB MRQ)小于12

    买入条件：
    - 当日股价最低价，比220日均价小15%以上时建仓以收盘价全仓买入

    卖出条件：
    - 条件一：当日股价最高价，比220日均价大15%以上时建仓以收盘价全仓卖出
    - 条件二：持仓日期达到120日以当天开盘价卖出
    - 条件三：浮亏达到10%时以收盘价卖出
    - 条件四：浮盈达到20%时以收盘价卖出
    """

    # 策略名称，用于数据库识别
    STRATEGY_NAME = 'ValueStrategy'

    params = (
        ('ma220_period', 220),          # 220日均线周期
        ('max_pe_ttm', 30.0),          # 最大市盈率PE TTM
        ('max_pb_mrq', 12.0),          # 最大市净率PB MRQ
        ('buy_threshold', -0.03),      # 买入阈值：最低价比MA220低15%
        ('sell_threshold_up', 0.10),   # 卖出阈值：最高价比MA220高15%
        ('max_hold_days', 120),        # 最大持仓天数
        ('stop_loss', -0.5),          # 止损：浮亏10%
        ('take_profit', 0.20),         # 止盈：浮盈20%
        ('printlog', True),
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume

        # 估值指标
        self.peTTM = self.datas[0].peTTM
        self.psTTM = self.datas[0].psTTM
        self.pcfNcfTTM = self.datas[0].pcfNcfTTM
        self.pbMRQ = self.datas[0].pbMRQ

        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.buy_date = None
        self.hold_days = 0

        # 手续费统计
        self.total_commission = 0.0
        self.buy_commission = 0.0
        self.sell_commission = 0.0

        # 盈利交易统计
        self.profit_trade_count = 0
        self.loss_trade_count = 0

        # 触发点位记录
        self.trigger_points = []
        self.current_buy_info = None

        # 当前 MA220 值（用于记录触发点位）
        self.current_ma220 = None



    def get_pe_pb_from_data(self):
        """
        从backtrader数据源获取当前的PE和PB数据

        Returns:
            tuple: (pe_ttm, pb_mrq) 如果不存在则返回 (None, None)
        """
        try:
            # 检查数据是否有效
            if len(self.peTTM) > 0:
                pe_ttm = self.peTTM[0] if self.peTTM[0] >= 0 else None
                pb_mrq = self.pbMRQ[0] if self.pbMRQ[0] >= 0 else None
                return pe_ttm, pb_mrq
            return None, None
        except Exception as e:
            logger.error(f"获取PE PB数据失败: {e}")
            return None, None

    def check_fundamental_conditions(self, date):
        """
        检查基本面筛选条件

        Args:
            date: 日期对象

        Returns:
            tuple: (是否满足条件, PE, PB)
        """
        # 从数据源获取PE和PB
        pe_ttm, pb_mrq = self.get_pe_pb_from_data()

        # 检查条件
        conditions_met = True
        reasons = []

        # 条件1：市盈率小于30
        if pe_ttm is None:
            conditions_met = False
            reasons.append("市盈率数据缺失")
        elif pe_ttm >= self.p.max_pe_ttm:
            conditions_met = False
            reasons.append(f"市盈率{pe_ttm:.2f}大于{self.p.max_pe_ttm}")

        # 条件2：市净率小于12
        if pb_mrq is None:
            conditions_met = False
            reasons.append("市净率数据缺失")
        elif pb_mrq >= self.p.max_pb_mrq:
            conditions_met = False
            reasons.append(f"市净率{pb_mrq:.2f}大于{self.p.max_pb_mrq}")

        # 每日打印当前基本面指标值
        if self.p.printlog:
            logger.debug(f'基本面指标检查 - 日期: {date}, PE: {pe_ttm}, PB: {pb_mrq}, '
                      f'PE阈值: {self.p.max_pe_ttm}, PB阈值: {self.p.max_pb_mrq}, '
                      f'满足条件: {conditions_met}')
            if not conditions_met:
                logger.info(f'不满足原因: {", ".join(reasons)}')

        return conditions_met, pe_ttm, pb_mrq

    def next(self):
        """主逻辑"""
        # 如果有待处理订单，跳过
        if self.order:
            return

        current_date = self.datas[0].datetime.date()

        # 动态计算 MA220（使用 talib）
        ma220_value = None
        if len(self.dataclose) >= self.p.ma220_period:
            # 获取收盘价数组并转换为 numpy.ndarray
            close_prices = self.dataclose.get(size=self.p.ma220_period)
            close_prices_np = np.array(close_prices)
            # 使用 talib 计算 MA
            ma220_value = talib.SMA(close_prices_np, timeperiod=self.p.ma220_period)[-1]

        # 更新当前 MA220 值（用于记录触发点位）
        self.current_ma220 = ma220_value

        # 打印调试信息
        if self.p.printlog and len(self.dataclose) <= self.p.ma220_period:
            logger.info(f'数据初始化中 - 日期: {current_date}, '
                       f'当前数据长度: {len(self.dataclose)}, '
                       f'MA220值: {ma220_value}, '
                       f'需要数据: {self.p.ma220_period}')

        # 如果有持仓，检查是否需要卖出
        if self.position:
            self.hold_days += 1

            # 计算当前持仓的盈亏情况
            current_price = self.dataclose[0]
            if self.buyprice > 0:
                # 计算浮盈百分比
                profit_rate = ((current_price - self.buyprice) / self.buyprice) * 100

                # 检查卖出条件
                sell_reasons = []

                # 条件一：当日最高价比220日均价大15%以上，以收盘价卖出
                if ma220_value is not None and ma220_value > 0:
                    if self.datahigh[0] >= ma220_value * (1 + self.p.sell_threshold_up):
                        sell_reasons.append(f'最高价触及MA220+{self.p.sell_threshold_up*100}%')

                # 条件二：持仓日期达到120日，以开盘价卖出（但在next中执行时已开盘，使用开盘价）
                if self.hold_days >= self.p.max_hold_days:
                    # 使用开盘价卖出
                    if self.p.printlog:
                        logger.info(f'触发卖出信号（持仓天数） - 日期: {current_date}, '
                                  f'开盘价: {self.dataopen[0]:.2f}, '
                                  f'持有天数: {self.hold_days}, '
                                  f'卖出数量: {self.position.size}')
                    self.order = self.sell(price=self.dataopen[0], size=self.position.size)
                    return

                # 条件三：浮亏达到10%，以收盘价卖出
                if profit_rate <= self.p.stop_loss * 100:
                    sell_reasons.append(f'浮亏达到{abs(self.p.stop_loss)*100}%')

                # 条件四：浮盈达到20%，以收盘价卖出
                if profit_rate >= self.p.take_profit * 100:
                    sell_reasons.append(f'浮盈达到{self.p.take_profit*100}%')

                # 执行卖出（使用收盘价）
                if sell_reasons:
                    if self.p.printlog:
                        logger.info(f'触发卖出信号 - 日期: {current_date}, '
                                  f'当前价格: {current_price:.2f}, '
                                  f'买入价格: {self.buyprice:.2f}, '
                                  f'浮盈: {profit_rate:.2f}%, '
                                  f'持有天数: {self.hold_days}, '
                                  f'卖出原因: {", ".join(sell_reasons)}, '
                                  f'卖出数量: {self.position.size}')
                    self.order = self.sell(size=self.position.size)

            return

        # 无持仓时，检查买入条件
        # 检查是否有足够的历史数据（至少220天）
        if len(self.dataclose) < self.p.ma220_period:
            return

        # 检查基本面筛选条件
        fundamental_ok, pe_ttm, pb_mrq = self.check_fundamental_conditions(current_date)

        if not fundamental_ok:
            return

        # 检查买入条件：当日最低价比220日均价小15%以上
        if ma220_value is not None and ma220_value > 0:
            low_vs_ma220 = (self.datalow[0] - ma220_value) / ma220_value

            # 每日打印买入条件检查
            if self.p.printlog:
                logger.info(f'买入条件检查 - 日期: {current_date}, '
                          f'最低价: {self.datalow[0]:.2f}, '
                          f'MA220: {ma220_value:.2f}, '
                          f'偏离度: {low_vs_ma220*100:.2f}%, '
                          f'买入阈值: {self.p.buy_threshold*100:.2f}%, '
                          f'是否触发: {low_vs_ma220 <= self.p.buy_threshold}')

            if low_vs_ma220 <= self.p.buy_threshold:
                # 满足买入条件，以收盘价全仓买入
                if self.p.printlog:
                    logger.info(f'触发买入信号 - 日期: {current_date}, '
                              f'最低价: {self.datalow[0]:.2f}, '
                              f'MA220: {ma220_value:.2f}, '
                              f'偏离度: {low_vs_ma220*100:.2f}%, '
                              f'PE: {pe_ttm:.2f}, '
                              f'PB: {pb_mrq:.2f}')

                # 计算最大可买数量，使用全部可用资金
                cash = self.broker.getvalue()
                price = self.dataclose[0]

                # 计算可买数量（考虑手续费，预留10%作为手续费缓冲）
                if price > 0:
                    buy_size = int((cash * 0.90) / price)  # 90%仓位，预留10%手续费缓冲
                    if buy_size > 0:
                        self.order = self.buy(size=buy_size)

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
                    'ma220': float(self.current_ma220) if self.current_ma220 is not None else None,
                    'buy_reason': '最低价低于MA220 15%'
                }
                self.current_buy_info = buy_info
                
                if self.p.printlog:
                    logger.info(f'买入执行 - 价格: {order.executed.price:.2f}, '
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
                    self.trigger_points.append(sell_info)
                    self.current_buy_info = None
                
                if self.p.printlog:
                    logger.info(f'卖出执行 - 价格: {order.executed.price:.2f}, '
                              f'数量: {order.executed.size}, '
                              f'手续费: {order.executed.comm:.2f}, '
                              f'利润: {order.executed.pnl:.2f}, '
                              f'日期: {self.datas[0].datetime.date()}')
                              
                self.buy_date = None
                self.hold_days = 0

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.p.printlog:
                logger.warning(f'证券代码: {self.stock_code} 订单取消/拒绝 - 状态: {order.getstatusname()} - 日期: {self.datas[0].datetime.date()}')

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

        current_date = self.datas[0].datetime.date()

        # 动态计算 MA220（使用 talib）
        ma220_value = None
        if len(self.dataclose) >= self.p.ma220_period:
            # 获取收盘价数组并转换为 numpy.ndarray
            close_prices = self.dataclose.get(size=self.p.ma220_period)
            close_prices_np = np.array(close_prices)
            # 使用 talib 计算 MA
            ma220_value = talib.SMA(close_prices_np, timeperiod=self.p.ma220_period)[-1]

        # 打印调试信息
        if self.p.printlog and len(self.dataclose) <= self.p.ma220_period:
            logger.debug(f'数据初始化中 - 日期: {current_date}, '
                       f'当前数据长度: {len(self.dataclose)}, '
                       f'MA220值: {ma220_value}, '
                       f'需要数据: {self.p.ma220_period}')

        # 如果有持仓，检查是否需要卖出
        if self.position:
            self.hold_days += 1
            
            # 计算当前持仓的盈亏情况
            current_price = self.dataclose[0]
            if self.buyprice > 0:
                # 计算浮盈百分比
                profit_rate = ((current_price - self.buyprice) / self.buyprice) * 100
                
                # 检查卖出条件
                sell_reasons = []
                
                # 条件一：当日最高价比220日均价大15%以上，以收盘价卖出
                if ma220_value is not None and ma220_value > 0:
                    if self.datahigh[0] >= ma220_value * (1 + self.p.sell_threshold_up):
                        sell_reasons.append(f'最高价触及MA220+{self.p.sell_threshold_up*100}%')
                
                # 条件二：持仓日期达到120日，以开盘价卖出（但在next中执行时已开盘，使用开盘价）
                if self.hold_days >= self.p.max_hold_days:
                    # 使用开盘价卖出
                    if self.p.printlog:
                        logger.info(f'触发卖出信号（持仓天数） - 日期: {current_date}, '
                                  f'开盘价: {self.dataopen[0]:.2f}, '
                                  f'持有天数: {self.hold_days}, '
                                  f'卖出数量: {self.position.size}')
                    self.order = self.sell(price=self.dataopen[0], size=self.position.size)
                    return
                
                # 条件三：浮亏达到10%，以收盘价卖出
                if profit_rate <= self.p.stop_loss * 100:
                    sell_reasons.append(f'浮亏达到{abs(self.p.stop_loss)*100}%')
                
                # 条件四：浮盈达到20%，以收盘价卖出
                if profit_rate >= self.p.take_profit * 100:
                    sell_reasons.append(f'浮盈达到{self.p.take_profit*100}%')
                
                # 执行卖出（使用收盘价）
                if sell_reasons:
                    if self.p.printlog:
                        logger.info(f'触发卖出信号 - 日期: {current_date}, '
                                  f'当前价格: {current_price:.2f}, '
                                  f'买入价格: {self.buyprice:.2f}, '
                                  f'浮盈: {profit_rate:.2f}%, '
                                  f'持有天数: {self.hold_days}, '
                                  f'卖出原因: {", ".join(sell_reasons)}, '
                                  f'卖出数量: {self.position.size}')
                    self.order = self.sell(size=self.position.size)
            
            return

        # 无持仓时，检查买入条件
        # 检查是否有足够的历史数据（至少220天）
        if len(self.dataclose) < self.p.ma220_period:
            return

                # 检查基本面筛选条件
        fundamental_ok, pe_ttm, pb_mrq = self.check_fundamental_conditions(current_date)

        if not fundamental_ok:
            return

        # 检查买入条件：当日最低价比220日均价小15%以上
        if ma220_value is not None and ma220_value > 0:
            low_vs_ma220 = (self.datalow[0] - ma220_value) / ma220_value

            # 每日打印买入条件检查
            if self.p.printlog:
                logger.debug(f'买入条件检查 - 日期: {current_date}, '
                          f'最低价: {self.datalow[0]:.2f}, '
                          f'MA220: {ma220_value:.2f}, '
                          f'偏离度: {low_vs_ma220*100:.2f}%, '
                          f'买入阈值: {self.p.buy_threshold*100:.2f}%, '
                          f'是否触发: {low_vs_ma220 <= self.p.buy_threshold}')

            if low_vs_ma220 <= self.p.buy_threshold:
                # 满足买入条件，以收盘价全仓买入
                if self.p.printlog:
                    logger.info(f'触发买入信号 - 日期: {current_date}, '
                              f'最低价: {self.datalow[0]:.2f}, '
                              f'MA220: {ma220_value:.2f}, '
                              f'偏离度: {low_vs_ma220*100:.2f}%, '
                              f'PE: {pe_ttm:.2f}, '
                              f'PB: {pb_mrq:.2f}')
                
                # 计算最大可买数量，使用全部可用资金
                cash = self.broker.getvalue()
                price = self.dataclose[0]
                
                # 计算可买数量（考虑手续费，预留10%作为手续费缓冲）
                if price > 0:
                    buy_size = int((cash * 0.90) / price)  # 90%仓位，预留10%手续费缓冲
                    if buy_size > 0:
                        self.order = self.buy(size=buy_size)
