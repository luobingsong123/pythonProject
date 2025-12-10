# utils/backtrader_batch.py
import pandas as pd
from backtest_engine.multi_stock_backtester import MultiStockBacktester
from logger_utils.logger_tool import get_logger


# 本代码仅用于回测研究，实盘使用风险自担

def main():
    logger = get_logger(__name__)

    # 创建回测器
    backtester = MultiStockBacktester(initial_cash=100000.0, max_workers=4)

    # 运行批量回测（使用50只股票抽样测试）
    logger.info("开始全市场回测...")
    results = backtester.run_batch_backtest(sample_size=50)

    # 输出结果
    print("\n=== 全市场回测结果汇总 ===")
    for key, value in results.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")

    # 保存详细结果
    if backtester.results:
        results_df = pd.DataFrame(backtester.results)
        results_df.to_csv('../backtest_report/batch_backtest_results.csv', index=False, encoding='utf-8-sig')
        logger.info(f"详细结果已保存至: ../backtest_report/batch_backtest_results.csv")


if __name__ == '__main__':
    main()