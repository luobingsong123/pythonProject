"""
交易执行器模块

负责执行买入、卖出、补仓等交易操作
"""

from typing import Dict, Any, Optional, List
from utils.strategies.base_strategy import Position
from utils.backtest_engine.account import Account
from utils.backtest_engine.portfolio import PortfolioManager
from utils.logger_utils import setup_logger
import config

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"]
)


class TradeExecutor:
    """交易执行器"""

    def __init__(self, account: Account, portfolio: PortfolioManager, commission: float,
                 strategy_db=None, strategy_name=None, backtest_start_date=None, backtest_end_date=None):
        """
        初始化交易执行器

        Args:
            account: 账户管理器
            portfolio: 持仓管理器
            commission: 手续费率
            strategy_db: 策略数据库管理器（可选）
            strategy_name: 策略名称（可选）
            backtest_start_date: 回测开始日期（可选）
            backtest_end_date: 回测结束日期（可选）
        """
        self.account = account
        self.portfolio = portfolio
        self.commission_rate = commission
        self.trading_records: List[Dict[str, Any]] = []  # 交易记录
        self.trigger_points: List[Dict[str, Any]] = []  # 触发点位记录
        self.strategy_db = strategy_db
        self.strategy_name = strategy_name
        self.backtest_start_date = backtest_start_date
        self.backtest_end_date = backtest_end_date

    def execute_buy(
        self,
        stock_code: str,
        market: str,
        name: str,
        price: float,
        volume: int,
        current_date: str,
        signal_info: Optional[Dict] = None,
        initial_cash: float = 10000000.0
    ) -> bool:
        """
        执行买入

        Args:
            stock_code: 股票代码
            market: 市场
            name: 股票名称
            price: 买入价格
            volume: 买入数量
            current_date: 当前日期
            signal_info: 信号信息
            initial_cash: 初始资金（用于计算盈亏比例）

        Returns:
            bool: 是否成功买入
        """
        if self.portfolio.has_position(stock_code):
            logger.debug(f"{current_date}: 股票 {stock_code} 已持仓，跳过买入")
            return False

        # 计算费用
        cost_info = self.account.calc_buy_cost(price, volume)
        total_cost = cost_info['total_cost']
        commission = cost_info['commission']
        amount = cost_info['amount']

        if not self.account.can_afford(total_cost):
            logger.debug(f"{current_date}: 资金不足，无法买入 {stock_code}")
            return False

        # 扣除资金
        self.account.debit(total_cost)
        self.account.add_buy_commission(commission)

        # 创建持仓
        position = Position(
            stock_code=stock_code,
            market=market,
            name=name,
            buy_date=current_date,
            buy_price=price,
            volume=volume,
            commission=commission
        )
        self.portfolio.add_position(stock_code, position)

        # 记录交易
        trade_record = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': market,
            'name': name,
            'action': 'buy',
            'price': price,
            'volume': volume,
            'amount': amount,
            'commission': commission,
            'signal_info': signal_info
        }
        self.trading_records.append(trade_record)

        # 记录触发点位
        trigger_point = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': market,
            'name': name,
            'trigger_type': 'buy',
            'price': float(price),
            'volume': float(volume),
            'commission': float(commission),
            'signal_info': signal_info
        }
        self.trigger_points.append(trigger_point)

        # 计算当前总资产和盈亏比例
        total_value = self.account.cash
        for pos_code, pos in self.portfolio.get_all_positions().items():
            total_value += pos.get_current_value(price if pos_code == stock_code else pos.buy_price)
        profit_rate = (total_value / initial_cash - 1) * 100

        logger.info(f"[买入] {current_date} | {stock_code:0>6} {name} | "
                    f"价格: {price:.2f} | 数量: {volume} | 金额: {amount:.2f} | 手续费: {commission:.2f} | "
                    f"总资产: {total_value:,.2f} | 盈亏: {profit_rate:+.2f}%")

        # 记录到数据库
        if self.strategy_db and self.strategy_name and self.backtest_start_date and self.backtest_end_date:
            try:
                self.strategy_db.insert_trade_record(
                    strategy_name=self.strategy_name,
                    backtest_start_date=self.backtest_start_date,
                    backtest_end_date=self.backtest_end_date,
                    trade_date=current_date,
                    market=market,
                    code_int=int(stock_code),
                    trigger_type='buy',
                    price=price,
                    volume=volume,
                    amount=amount,
                    commission=commission,
                    signal_info=signal_info
                )
            except Exception as e:
                logger.debug(f"记录买入交易到数据库失败: {e}")

        return True

    def execute_sell(
        self,
        stock_code: str,
        price: float,
        volume: int,
        current_date: str,
        sell_reason: str = '',
        initial_cash: float = 10000000.0
    ) -> bool:
        """
        执行卖出

        Args:
            stock_code: 股票代码
            price: 卖出价格
            volume: 卖出数量
            current_date: 当前日期
            sell_reason: 卖出原因
            initial_cash: 初始资金（用于计算盈亏比例）

        Returns:
            bool: 是否成功卖出
        """
        position = self.portfolio.get_position(stock_code)
        if position is None:
            return False

        # 计算费用
        proceeds_info = self.account.calc_sell_proceeds(price, volume)
        actual_amount = proceeds_info['actual_amount']
        commission = proceeds_info['commission']
        amount = proceeds_info['amount']

        # 增加资金
        self.account.credit(actual_amount)
        self.account.add_sell_commission(commission)
        position.sell_commission = commission

        # 计算盈亏
        profit = amount - position.buy_price * volume
        profit_rate = position.get_profit_rate(price)

        # 统计盈亏交易
        self.account.record_trade(profit)

        # 记录交易
        trade_record = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': position.market,
            'name': position.name,
            'action': 'sell',
            'price': price,
            'volume': volume,
            'amount': amount,
            'commission': commission,
            'profit': profit,
            'profit_rate': profit_rate,
            'hold_days': position.hold_days,
            'sell_reason': sell_reason
        }
        self.trading_records.append(trade_record)

        # 记录触发点位
        trigger_point = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': position.market,
            'name': position.name,
            'trigger_type': 'sell',
            'price': float(price),
            'volume': float(volume),
            'commission': float(commission),
            'profit': float(profit),
            'profit_rate': float(profit_rate),
            'hold_days': position.hold_days,
            'sell_reason': sell_reason
        }
        self.trigger_points.append(trigger_point)

        # 计算当前总资产和盈亏比例（卖出后）
        total_value = self.account.cash
        for pos_code, pos in self.portfolio.get_all_positions().items():
            if pos_code != stock_code:  # 排除已卖出的股票
                total_value += pos.get_current_value(pos.buy_price)
        total_profit_rate = (total_value / initial_cash - 1) * 100

        logger.info(f"[卖出] {current_date} | {stock_code:0>6} {position.name} | "
                    f"价格: {price:.2f} | 数量: {volume} | 金额: {amount:.2f} | "
                    f"盈亏: {profit:.2f} ({profit_rate * 100:.2f}%) | 原因: {sell_reason} | "
                    f"总资产: {total_value:,.2f} | 总盈亏: {total_profit_rate:+.2f}%")

        # 记录到数据库
        if self.strategy_db and self.strategy_name and self.backtest_start_date and self.backtest_end_date:
            try:
                self.strategy_db.insert_trade_record(
                    strategy_name=self.strategy_name,
                    backtest_start_date=self.backtest_start_date,
                    backtest_end_date=self.backtest_end_date,
                    trade_date=current_date,
                    market=position.market,
                    code_int=int(stock_code),
                    trigger_type='sell',
                    price=price,
                    volume=volume,
                    amount=amount,
                    commission=commission,
                    profit=profit,
                    profit_rate=profit_rate * 100,  # 转换为百分比
                    hold_days=position.hold_days,
                    sell_reason=sell_reason,
                    signal_info={'sell_reason': sell_reason}
                )
            except Exception as e:
                logger.debug(f"记录卖出交易到数据库失败: {e}")

        # 移除持仓
        self.portfolio.remove_position(stock_code)

        return True

    def execute_add_position(
        self,
        stock_code: str,
        add_price: float,
        add_volume: int,
        current_date: str,
        add_info: Optional[Dict] = None,
        initial_cash: float = 10000000.0
    ) -> bool:
        """
        执行补仓

        Args:
            stock_code: 股票代码
            add_price: 补仓价格
            add_volume: 补仓数量
            current_date: 当前日期
            add_info: 补仓信号信息
            initial_cash: 初始资金（用于计算盈亏比例）

        Returns:
            bool: 是否成功补仓
        """
        position = self.portfolio.get_position(stock_code)
        if position is None:
            return False

        # 计算补仓费用
        cost_info = self.account.calc_buy_cost(add_price, add_volume)
        total_cost = cost_info['total_cost']
        commission = cost_info['commission']
        amount = cost_info['amount']

        if not self.account.can_afford(total_cost):
            logger.debug(f"{current_date}: 资金不足，无法加仓 {stock_code}")
            return False

        # 扣除资金
        self.account.debit(total_cost)
        self.account.add_buy_commission(commission)

        # 更新持仓信息
        position.update_avg_cost(add_price, add_volume)

        # 记录交易
        trade_record = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': position.market,
            'name': position.name,
            'action': 'add_position',
            'price': add_price,
            'volume': add_volume,
            'amount': amount,
            'commission': commission,
            'signal_info': add_info
        }
        self.trading_records.append(trade_record)

        # 记录触发点位
        trigger_point = {
            'date': str(current_date),
            'stock_code': stock_code,
            'market': position.market,
            'name': position.name,
            'trigger_type': 'add_position',
            'price': float(add_price),
            'volume': float(add_volume),
            'commission': float(commission),
            'signal_info': add_info
        }
        self.trigger_points.append(trigger_point)

        # 计算当前总资产和盈亏比例
        total_value = self.account.cash
        for pos_code, pos in self.portfolio.get_all_positions().items():
            total_value += pos.get_current_value(add_price if pos_code == stock_code else pos.buy_price)
        profit_rate = (total_value / initial_cash - 1) * 100

        logger.info(f"[加仓] {current_date} | {stock_code:0>6} {position.name} | "
                    f"价格: {add_price:.2f} | 数量: {add_volume} | 金额: {amount:.2f} | 手续费: {commission:.2f} | "
                    f"新持仓: {position.volume} | 新成本: {position.avg_cost:.2f} | "
                    f"总资产: {total_value:,.2f} | 盈亏: {profit_rate:+.2f}%")

        # 记录到数据库
        if self.strategy_db and self.strategy_name and self.backtest_start_date and self.backtest_end_date:
            try:
                self.strategy_db.insert_trade_record(
                    strategy_name=self.strategy_name,
                    backtest_start_date=self.backtest_start_date,
                    backtest_end_date=self.backtest_end_date,
                    trade_date=current_date,
                    market=position.market,
                    code_int=int(stock_code),
                    trigger_type='add_position',
                    price=add_price,
                    volume=add_volume,
                    amount=amount,
                    commission=commission,
                    signal_info=add_info
                )
            except Exception as e:
                logger.debug(f"记录加仓交易到数据库失败: {e}")

        return True

    def get_trading_records(self) -> List[Dict[str, Any]]:
        """获取交易记录"""
        return self.trading_records.copy()

    def get_trigger_points(self) -> List[Dict[str, Any]]:
        """获取触发点位记录"""
        return self.trigger_points.copy()

    def clear_records(self) -> None:
        """清空交易记录"""
        self.trading_records.clear()
        self.trigger_points.clear()
