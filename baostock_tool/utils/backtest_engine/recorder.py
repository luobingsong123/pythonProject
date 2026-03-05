"""
结果记录器模块

负责保存回测结果到CSV文件和数据库
"""

import os
from typing import List, Dict, Any
from collections import defaultdict
import pandas as pd
from utils.logger_utils import setup_logger
from database_schema.strategy_trigger_db import StrategyTriggerDB
import config

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"]
)


class BacktestRecorder:
    """回测结果记录器"""

    def __init__(self, output_dir: str = "csv"):
        """
        初始化记录器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def save_trading_records(
        self,
        records: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        prefix: str = "time_based_backtest_questdb"
    ) -> str:
        """
        保存交易记录到CSV

        Args:
            records: 交易记录列表
            start_date: 开始日期
            end_date: 结束日期
            prefix: 文件名前缀

        Returns:
            str: 保存的文件路径
        """
        if not records:
            logger.warning("没有交易记录需要保存")
            return ""

        filename = f"{self.output_dir}/{prefix}_{start_date.replace('-', '')}_to_{end_date.replace('-', '')}.csv"
        df = pd.DataFrame(records)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"交易记录已保存至: {filename}")
        return filename

    def save_daily_values(
        self,
        daily_values: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        prefix: str = "time_based_daily_values_questdb"
    ) -> str:
        """
        保存每日资产记录到CSV

        Args:
            daily_values: 每日资产记录列表
            start_date: 开始日期
            end_date: 结束日期
            prefix: 文件名前缀

        Returns:
            str: 保存的文件路径
        """
        if not daily_values:
            logger.warning("没有每日资产记录需要保存")
            return ""

        filename = f"{self.output_dir}/{prefix}_{start_date.replace('-', '')}_to_{end_date.replace('-', '')}.csv"
        df = pd.DataFrame(daily_values)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"每日资产已保存至: {filename}")
        return filename

    def save_to_database(
        self,
        strategy_name: str,
        backtest_config: Any,
        trading_records: List[Dict[str, Any]],
        daily_values: List[Dict[str, Any]],
        trigger_points: List[Dict[str, Any]],
        statistics: Any,
        trading_dates_count: int,
        final_value: float,
        execution_time: float,
        strategy_params: Dict[str, Any]
    ) -> bool:
        """
        保存回测结果到数据库

        Args:
            strategy_name: 策略名称
            backtest_config: 回测配置
            trading_records: 交易记录
            daily_values: 每日资产记录
            trigger_points: 触发点位记录
            statistics: 统计数据
            trading_dates_count: 交易日数量
            final_value: 最终资产
            execution_time: 执行时间
            strategy_params: 策略参数

        Returns:
            bool: 是否保存成功
        """
        try:
            strategy_db = StrategyTriggerDB()

            # 保存触发点位
            if trigger_points:
                trigger_by_stock = defaultdict(list)
                for tp in trigger_points:
                    trigger_by_stock[tp['stock_code']].append(tp)

                for stock_code, points in trigger_by_stock.items():
                    if points:
                        first_point = points[0]
                        strategy_db.insert_trigger_points(
                            strategy_name=strategy_name,
                            stock_code=stock_code,
                            market=first_point.get('market', 'sh'),
                            trigger_points_json=points,
                            backtest_start_date=backtest_config.start_date,
                            backtest_end_date=backtest_config.end_date,
                            trigger_count=len(points)
                        )

                logger.info(f"触发点位已保存到数据库: 共 {len(trigger_points)} 条记录")

            # 保存汇总结果
            summary_json = {
                "trading_days_count": trading_dates_count,
                "initial_cash": backtest_config.initial_cash,
                "final_value": round(final_value, 2),
                "total_return": round(statistics.total_return, 2),
                "max_drawdown": round(statistics.max_drawdown, 2),
                "sharpe_ratio": round(statistics.sharpe_ratio, 2) if statistics.sharpe_ratio != 0 else 0,
                "total_trades": statistics.total_trades,
                "profit_trade_count": statistics.profit_trade_count,
                "loss_trade_count": statistics.loss_trade_count,
                "win_rate": round(statistics.win_rate, 2),
                "total_commission": round(statistics.total_commission, 2),
                "buy_commission": round(statistics.buy_commission, 2),
                "sell_commission": round(statistics.sell_commission, 2),
                "commission_ratio": round(statistics.commission_ratio, 2),
                "commission": backtest_config.commission,
                "slippage_perc": backtest_config.slippage_perc,
                "max_positions": backtest_config.max_positions,
                "position_size_pct": backtest_config.position_size_pct,
                "execution_time": round(execution_time, 2),
                "data_source": "questdb",
                "created_by": "time_based_backtest_questdb"
            }

            strategy_db.insert_or_update_summary(
                strategy_name=strategy_name,
                backtest_start_date=backtest_config.start_date,
                backtest_end_date=backtest_config.end_date,
                summary_json=summary_json,
                stock_count=len(trigger_by_stock) if trigger_points else 0,
                execution_time=execution_time,
                backtest_framework='time_based_questdb',
                strategy_params_json=strategy_params
            )

            logger.info(f"汇总结果已保存到数据库")
            return True

        except Exception as e:
            logger.error(f"保存结果到数据库失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def save_daily_record_to_db(
        self,
        strategy_db: StrategyTriggerDB,
        strategy_name: str,
        backtest_config: Any,
        current_date: str,
        daily_buy_count: int,
        daily_sell_count: int,
        total_value: float,
        profit_rate: float,
        cash: float,
        position_count: int,
        max_positions: int,
        positions: Dict[str, Any],
        all_stock_data: Dict[str, Any]
    ) -> bool:
        """
        保存每日记录到数据库

        Args:
            strategy_db: 策略数据库实例
            strategy_name: 策略名称
            backtest_config: 回测配置
            current_date: 当前日期
            daily_buy_count: 当日买入数量
            daily_sell_count: 当日卖出数量
            total_value: 总资产
            profit_rate: 盈亏比例
            cash: 现金
            position_count: 持仓数量
            max_positions: 最大持仓数
            positions: 持仓字典
            all_stock_data: 所有股票数据

        Returns:
            bool: 是否保存成功
        """
        import pandas as pd
        
        try:
            # 构建持仓详情列表
            position_detail_list = []
            current_date_dt = pd.to_datetime(current_date)
            
            for pos_code, pos in positions.items():
                pos_profit_rate = 0
                if pos_code in all_stock_data:
                    stock_data = all_stock_data[pos_code]
                    if stock_data.index.tz is not None:
                        stock_data = stock_data.tz_localize(None)
                    if current_date_dt in stock_data.index:
                        current_price = stock_data.loc[current_date_dt, 'close']
                        pos_profit_rate = round(pos.get_profit_rate(current_price) * 100, 2)
                position_detail_list.append({
                    'code': pos_code,
                    'name': pos.name,
                    'profit_rate': pos_profit_rate
                })

            strategy_db.insert_daily_record(
                strategy_name=strategy_name,
                backtest_start_date=backtest_config.start_date,
                backtest_end_date=backtest_config.end_date,
                trade_date=current_date,
                buy_count=daily_buy_count,
                sell_count=daily_sell_count,
                is_no_action=1 if (daily_buy_count == 0 and daily_sell_count == 0) else 0,
                total_asset=round(total_value, 2),
                profit_rate=round(profit_rate, 4),
                cash=round(cash, 2),
                position_count=position_count,
                max_positions=max_positions,
                position_detail=position_detail_list
            )
            return True

        except Exception as e:
            logger.error(f"保存每日记录失败: {str(e)}")
            return False
