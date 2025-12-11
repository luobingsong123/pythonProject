# utils/backtest_engine/multi_stock_backtester.py
import backtrader as bt
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from baostock_tool.utils.data_loader.market_loader import MarketDataLoader
from baostock_tool.utils.data_loader.stock_loader import StockDataLoader
from baostock_tool.utils.strategies.macd_strategy import MACDStrategy
from baostock_tool.utils.logger_utils.logger_tool import get_logger


# 本代码仅用于回测研究，实盘使用风险自担

class MultiStockBacktester:
    def __init__(self, initial_cash=100000.0, max_workers=None):
        self.initial_cash = initial_cash
        self.max_workers = max_workers or os.cpu_count()
        self.market_loader = MarketDataLoader()
        self.stock_loader = StockDataLoader()
        self.logger = get_logger(__name__)
        self.results = []

    def backtest_single_stock(self, stock_info):
        """单股票回测（用于并行处理）"""
        market, code_int, name = stock_info
        self.logger.info(f"开始回测: {market}{code_int} {name}")

        try:
            # 创建回测引擎
            cerebro = bt.Cerebro()
            cerebro.addstrategy(MACDStrategy)

            # 加载数据（提前2年用于指标初始化）
            data = self.stock_loader.load_single_stock_data(
                market, code_int, '2018-01-01', '2025-12-31'
            )
            if data is None:
                return None

            cerebro.adddata(data)
            cerebro.broker.setcash(self.initial_cash)
            cerebro.broker.setcommission(commission=0.001)

            # 添加分析器
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

            # 运行回测
            results = cerebro.run()
            strategy = results[0]

            # 收集结果
            final_value = cerebro.broker.getvalue()
            result = {
                'market': market,
                'code_int': code_int,
                'name': name,
                'initial_cash': self.initial_cash,
                'final_value': final_value,
                'total_return': (final_value / self.initial_cash - 1) * 100,
                'sharpe_ratio': self._safe_get_analysis(strategy.analyzers.sharpe, 'sharperatio'),
                'max_drawdown': self._safe_get_analysis(strategy.analyzers.drawdown, 'max.drawdown'),
                'total_trades': self._safe_get_analysis(strategy.analyzers.trades, 'total.total')
            }

            self.logger.info(f"完成回测: {market}{code_int}, 收益率: {result['total_return']:.2f}%")
            return result

        except Exception as e:
            self.logger.error(f"回测{market}{code_int}失败: {e}")
            return None

    def run_batch_backtest(self, sample_size=50):
        """批量回测（支持并行）"""
        # 获取股票列表
        trading_dates = self.market_loader.get_trading_dates('2020-01-01', '2024-12-31')
        print(trading_dates)
        stock_list = self.market_loader.get_all_stock_codes()
        if sample_size and len(stock_list) > sample_size:
            stock_list = stock_list.sample(sample_size)  # 抽样测试

        self.logger.info(f"开始批量回测，股票数量: {len(stock_list)}")

        # 串行回测（稳定版）
        results = []
        for _, stock in stock_list.iterrows():
            result = self.backtest_single_stock(
                (stock['market'], stock['code_int'], stock['name'])
            )
            if result:
                results.append(result)

        # 并行回测版本（高级功能，需要时启用）
        # with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
        #     futures = [
        #         executor.submit(self.backtest_single_stock,
        #                        (row['market'], row['code_int'], row['name']))
        #         for _, row in stock_list.iterrows()
        #     ]
        #
        #     for future in as_completed(futures):
        #         result = future.result()
        #         if result:
        #             results.append(result)

        self.results = results
        return self._analyze_results()

    def _safe_get_analysis(self, analyzer, key_path):
        """安全获取分析结果"""
        try:
            result = analyzer.get_analysis()
            keys = key_path.split('.')
            for key in keys:
                result = result.get(key, 0)
            return result if result is not None else 0
        except:
            return 0

    def _analyze_results(self):
        """分析批量回测结果"""
        if not self.results:
            return {"error": "无有效回测结果"}

        df = pd.DataFrame(self.results)

        summary = {
            'total_stocks': len(df),
            'positive_returns': len(df[df['total_return'] > 0]),
            'negative_returns': len(df[df['total_return'] <= 0]),
            'avg_return': df['total_return'].mean(),
            'median_return': df['total_return'].median(),
            'win_rate': len(df[df['total_return'] > 0]) / len(df) * 100,
            'avg_sharpe': df['sharpe_ratio'].mean(),
            'avg_max_drawdown': df['max_drawdown'].mean()
        }

        return summary