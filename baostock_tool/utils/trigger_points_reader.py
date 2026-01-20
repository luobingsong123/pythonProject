"""
策略触发点位读取和格式化模块
用于从数据库读取策略触发点位并格式化返回
"""

from baostock_tool.database_schema.strategy_trigger_db import StrategyTriggerDB
from baostock_tool.utils.logger_utils import setup_logger
from baostock_tool import config

log_config = config.get_log_config()
logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"])


class TriggerPointsReader:
    """策略触发点位读取和格式化类"""

    def __init__(self):
        """初始化数据库连接"""
        self.db = StrategyTriggerDB()
        self._cache = None

    def get_all_formatted_data(self, use_cache=True):
        """
        获取所有策略的格式化触发点位数据

        Args:
            use_cache (bool): 是否使用缓存

        Returns:
            dict: 格式化后的数据，结构为：
                  {
                      策略名: {
                          证券代码: {
                              回测时段: {
                                  触发点位1: {买入, 卖出, 盈亏标志},
                                  触发点位2: {买入, 卖出, 盈亏标志},
                                  ...
                              }
                          }
                      }
                  }
        """
        if use_cache and self._cache:
            return self._cache

        try:
            # 查询所有触发点位数据
            results = self.db.query_trigger_points()

            # 格式化数据
            formatted_data = {}

            for record in results:
                strategy_name = record.strategy_name
                stock_code = record.stock_code
                market = record.market
                trigger_points_json = record.trigger_points_json
                backtest_start_date = record.backtest_start_date.strftime('%Y-%m-%d')
                backtest_end_date = record.backtest_end_date.strftime('%Y-%m-%d')

                # 组合证券代码（加上市场前缀）
                full_stock_code = f"{market}.{stock_code}"
                backtest_period = f"{backtest_start_date}至{backtest_end_date}"

                # 初始化策略层级
                if strategy_name not in formatted_data:
                    formatted_data[strategy_name] = {}

                # 初始化证券代码层级
                if full_stock_code not in formatted_data[strategy_name]:
                    formatted_data[strategy_name][full_stock_code] = {}

                # 初始化回测时段层级
                if backtest_period not in formatted_data[strategy_name][full_stock_code]:
                    formatted_data[strategy_name][full_stock_code][backtest_period] = {}

                # 处理触发点位数据
                trigger_points = self._parse_trigger_points(trigger_points_json)

                # 按触发点位索引组织数据
                for idx, trigger_point in enumerate(trigger_points):
                    trigger_key = f"触发点位{idx + 1}"
                    formatted_data[strategy_name][full_stock_code][backtest_period][trigger_key] = trigger_point

            # 缓存数据
            self._cache = formatted_data

            logger.info(f"成功获取格式化触发点位数据，策略数: {len(formatted_data)}")
            return formatted_data

        except Exception as e:
            logger.error(f"获取格式化触发点位数据失败: {str(e)}")
            return {}

    def _parse_trigger_points(self, trigger_points_json):
        """
        解析触发点位JSON数据，提取买卖日期和盈亏标志

        JSON数据格式示例:
        [
          {
            "date": "2024-01-05",
            "price": 3.52,
            "volume": 1250000,
            "volume_rank": "20日最低",
            "trigger_type": "buy"
          },
          {
            "date": "2024-01-08",
            "price": 3.58,
            "profit": 0.06,
            "hold_days": 2,
            "profit_rate": 1.7,
            "trigger_type": "sell"
          }
        ]

        Args:
            trigger_points_json (list): 触发点位JSON数据

        Returns:
            list: 格式化后的触发点位信息列表
        """
        trigger_points = []

        # 如果是字典形式，转换为列表
        if isinstance(trigger_points_json, dict):
            trigger_points_json = list(trigger_points_json.values())

        if not isinstance(trigger_points_json, list):
            logger.warning(f"触发点位数据格式不正确: {type(trigger_points_json)}")
            return []

        # 按买入卖出配对处理（相邻的两个JSON为一组）
        i = 0
        while i < len(trigger_points_json):
            point = trigger_points_json[i]

            # 检查point是否为None或不是字典
            if point is None or not isinstance(point, dict):
                logger.warning(f"触发点位数据为空或格式不正确: {point}, 跳过该点位")
                i += 1
                continue

            if point.get('trigger_type') == 'buy':
                # 找到买入点
                buy_date = point.get('date', '')
                buy_price = point.get('price', 0)

                # 默认卖出信息和盈亏标志
                sell_date = ''
                sell_price = 0
                profit_flag = 0  # 0=平盘/未知, 1=盈利, -1=亏损

                # 查找相邻的卖出点（下一个元素）
                if i + 1 < len(trigger_points_json):
                    next_point = trigger_points_json[i + 1]
                    # 检查卖出点是否为None或不是字典
                    if next_point is not None and isinstance(next_point, dict) and next_point.get('trigger_type') == 'sell':
                        sell_date = next_point.get('date', '')
                        sell_price = next_point.get('price', 0)

                        # 从卖出JSON中获取profit字段判断盈亏
                        profit = next_point.get('profit', 0)
                        profit_rate = next_point.get('profit_rate', 0)

                        # 计算盈亏标志: 1=盈利, 0=平盘, -1=亏损
                        # 优先使用profit字段判断，profit>0则为盈利
                        if profit > 0:
                            profit_flag = 1
                        elif profit < 0:
                            profit_flag = -1
                        elif profit_rate > 0:
                            profit_flag = 1
                        elif profit_rate < 0:
                            profit_flag = -1
                        else:
                            profit_flag = 0

                        i += 1  # 跳过卖出点，下一次循环从下一个买入点开始

                # 添加配对后的触发点信息
                trigger_points.append({
                    '买入': buy_date,
                    '卖出': sell_date,
                    '买入价格': buy_price,
                    '卖出价格': sell_price,
                    '盈亏标志': profit_flag
                })

            i += 1

        return trigger_points

    def get_strategy_data(self, strategy_name):
        """
        获取指定策略的触发点位数据

        Args:
            strategy_name (str): 策略名称

        Returns:
            dict: 该策略的格式化数据
        """
        all_data = self.get_all_formatted_data()
        return all_data.get(strategy_name, {})

    def get_stock_data(self, strategy_name, stock_code):
        """
        获取指定策略和股票的触发点位数据

        Args:
            strategy_name (str): 策略名称
            stock_code (str): 证券代码（可带或不带市场前缀，如 'sh.601288' 或 '601288'）

        Returns:
            dict: 该股票的格式化数据
        """
        all_data = self.get_all_formatted_data()
        strategy_data = all_data.get(strategy_name, {})

        # 查找匹配的证券代码
        for full_code, stock_data in strategy_data.items():
            if full_code == stock_code or full_code.endswith('.' + stock_code):
                return stock_data

        return {}

    def get_backtest_data(self, strategy_name, stock_code, backtest_period):
        """
        获取指定策略、股票和回测时段的触发点位数据

        Args:
            strategy_name (str): 策略名称
            stock_code (str): 证券代码
            backtest_period (str): 回测时段（格式: 'YYYY-MM-DD至YYYY-MM-DD'）

        Returns:
            dict: 该回测时段的格式化数据
        """
        stock_data = self.get_stock_data(strategy_name, stock_code)
        return stock_data.get(backtest_period, {})

    def refresh_cache(self):
        """刷新缓存"""
        self._cache = None

    def get_trigger_points_by_date_range(self, start_date, end_date):
        """
        获取指定日期范围内的触发点位数据

        Args:
            start_date (str): 开始日期 (YYYY-MM-DD)
            end_date (str): 结束日期 (YYYY-MM-DD)

        Returns:
            dict: 格式化的触发点位数据
        """
        results = self.db.query_trigger_points(
            backtest_start_date=start_date,
            backtest_end_date=end_date
        )

        formatted_data = {}

        for record in results:
            strategy_name = record.strategy_name
            stock_code = record.stock_code
            market = record.market
            trigger_points_json = record.trigger_points_json
            backtest_start_date = record.backtest_start_date.strftime('%Y-%m-%d')
            backtest_end_date = record.backtest_end_date.strftime('%Y-%m-%d')

            full_stock_code = f"{market}.{stock_code}"
            backtest_period = f"{backtest_start_date}至{backtest_end_date}"

            if strategy_name not in formatted_data:
                formatted_data[strategy_name] = {}

            if full_stock_code not in formatted_data[strategy_name]:
                formatted_data[strategy_name][full_stock_code] = {}

            if backtest_period not in formatted_data[strategy_name][full_stock_code]:
                formatted_data[strategy_name][full_stock_code][backtest_period] = {}

            trigger_points = self._parse_trigger_points(trigger_points_json)

            for idx, trigger_point in enumerate(trigger_points):
                trigger_key = f"触发点位{idx + 1}"
                formatted_data[strategy_name][full_stock_code][backtest_period][trigger_key] = trigger_point

        return formatted_data

    def get_statistics_summary(self):
        """
        获取触发点位统计摘要

        Returns:
            dict: 统计摘要数据
        """
        all_data = self.get_all_formatted_data()
        summary = {}

        for strategy_name, strategy_data in all_data.items():
            summary[strategy_name] = {
                'stock_count': len(strategy_data),
                'total_triggers': 0,
                'profit_count': 0,
                'loss_count': 0,
                'flat_count': 0
            }

            for stock_code, stock_data in strategy_data.items():
                for backtest_period, trigger_data in stock_data.items():
                    for trigger_key, trigger_info in trigger_data.items():
                        summary[strategy_name]['total_triggers'] += 1
                        profit_flag = trigger_info.get('盈亏标志', 0)

                        if profit_flag == 1:
                            summary[strategy_name]['profit_count'] += 1
                        elif profit_flag == -1:
                            summary[strategy_name]['loss_count'] += 1
                        else:
                            summary[strategy_name]['flat_count'] += 1

        return summary


# 使用示例
if __name__ == "__main__":
    # 创建读取器实例
    reader = TriggerPointsReader()

    # 获取所有格式化数据
    all_data = reader.get_all_formatted_data()
    print("=" * 80)
    print("所有策略触发点位数据:")
    print("=" * 80)
    import json
    print(json.dumps(all_data, indent=2, ensure_ascii=False))

    # 获取指定策略数据
    print("\n" + "=" * 80)
    print("指定策略触发点位数据:")
    print("=" * 80)
    strategy_data = reader.get_strategy_data("CodeBuddyStrategy")
    print(json.dumps(strategy_data, indent=2, ensure_ascii=False))

    # 获取指定股票数据
    print("\n" + "=" * 80)
    print("指定股票触发点位数据:")
    print("=" * 80)
    stock_data = reader.get_stock_data("CodeBuddyStrategy", "sh.601288")
    print(json.dumps(stock_data, indent=2, ensure_ascii=False))

    # 获取统计摘要
    print("\n" + "=" * 80)
    print("触发点位统计摘要:")
    print("=" * 80)
    summary = reader.get_statistics_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
