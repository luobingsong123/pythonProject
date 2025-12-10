# utils/strategies/macd_strategy.py
import backtrader as bt
# from baostock_tool.utils.base_strategy import BaseStrategy


class MACDStrategy():
    params = (
        ('fast', 12),
        ('slow', 26),
        ('signal', 9),
    )

    def __init__(self):
        super().__init__()
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast,
            period_me2=self.params.slow,
            period_signal=self.params.signal
        )
        self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        if self.order:
            return

        if not self.position:
            if self.macd_cross > 0 and len(self.macd.macd) > 26:
                size = int(self.broker.getcash() * 0.95 / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
        else:
            if self.macd_cross < 0:
                self.order = self.sell(size=self.position.size)