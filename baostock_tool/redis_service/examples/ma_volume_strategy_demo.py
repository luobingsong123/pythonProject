"""
均线成交量策略使用示例

选股条件：
1. 市值低于200亿
2. 60日均线和20日均线单调性一致，斜率大于0°，小于30°
3. 60日内最大成交量和最小成交量之比小于等于3
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from database.connection import init_db_pool
from strategy.selector import StockSelector
from strategy.ma_volume_strategy import MAVolumeStrategy


def demo_ma_volume_strategy():
    """均线成交量策略示例"""
    print("="*70)
    print("均线成交量策略选股示例")
    print("="*70)
    print("\n选股条件：")
    print("  1. 市值低于200亿")
    print("  2. 60日均线和20日均线单调性一致，斜率0°~30°")
    print("  3. 60日内最大成交量/最小成交量 ≤ 3")
    print()
    
    # 配置数据库连接
    db_config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "your_password",
        "database": "stock_db"
    }
    
    # 初始化数据库
    init_db_pool(db_config)
    
    # 创建策略
    strategy_params = {
        "max_market_cap": 200000,    # 200亿
        "min_slope_angle": 0,         # 最小0°
        "max_slope_angle": 30,        # 最大30°
        "ma_short_period": 20,        # 20日均线
        "ma_long_period": 60,         # 60日均线
        "volume_lookback": 60,        # 60日成交量
        "max_volume_ratio": 3         # 成交量比≤3
    }
    
    strategy = MAVolumeStrategy(strategy_params)
    
    # 创建选择器
    selector = StockSelector(strategy=strategy)
    
    # 执行选股
    date = "20241008"
    print(f"\n执行选股：{date}")
    print("-"*70)
    
    try:
        stocks = selector.select(
            date=date,
            strategy_id="MA_VOLUME_FILTER",
            count=20,
            save_to_db=True,           # 保存到数据库
            strategy_params=strategy_params
        )
        
        print(f"\n✓ 选股完成，共选出 {len(stocks)} 只股票\n")
        
        # 打印选股结果
        for i, stock in enumerate(stocks, 1):
            print(f"[{i}] {stock.exchange}:{stock.symbol} {stock.name}")
            
            if stock.fundamental_data:
                print(f"    市值: {stock.fundamental_data.market_cap:.2f}百万 "
                      f"({'✓' if stock.fundamental_data.market_cap < 200000 else '✗'})")
            
            if stock.technical_indicators:
                print(f"    MA20: {stock.technical_indicators.ma20:.2f}")
                print(f"    MA60: {stock.technical_indicators.ma60:.2f}")
            
            print()
        
    except Exception as e:
        print(f"\n✗ 选股失败: {e}")
        import traceback
        traceback.print_exc()


def demo_compare_strategies():
    """对比不同策略的选股结果"""
    print("\n" + "="*70)
    print("策略对比示例")
    print("="*70)
    
    # 配置数据库连接
    db_config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "your_password",
        "database": "stock_db"
    }
    
    init_db_pool(db_config)
    
    date = "20241008"
    
    # 策略1: MA10突破
    print("\n策略1: MA10突破策略")
    print("-"*70)
    selector1 = StockSelector()
    selector1.strategy = selector1.create_strategy("MA10_BREAKTHROUGH")
    stocks1 = selector1.select(date=date, count=10)
    print(f"选出 {len(stocks1)} 只股票")
    for stock in stocks1[:5]:
        print(f"  - {stock.exchange}:{stock.symbol} {stock.name}")
    
    # 策略2: 均线成交量
    print("\n策略2: 均线成交量策略")
    print("-"*70)
    selector2 = StockSelector()
    selector2.strategy = selector2.create_strategy("MA_VOLUME_FILTER", {
        "max_market_cap": 200000,
        "max_slope_angle": 30,
        "max_volume_ratio": 3
    })
    stocks2 = selector2.select(date=date, count=10)
    print(f"选出 {len(stocks2)} 只股票")
    for stock in stocks2[:5]:
        cap = stock.fundamental_data.market_cap if stock.fundamental_data else 0
        print(f"  - {stock.exchange}:{stock.symbol} {stock.name} (市值:{cap:.0f}百万)")
    
    # 策略3: 无策略（按成交额）
    print("\n策略3: 无策略（按成交额前10）")
    print("-"*70)
    selector3 = StockSelector()
    stocks3 = selector3.select(date=date, count=10)
    print(f"选出 {len(stocks3)} 只股票")
    for stock in stocks3[:5]:
        print(f"  - {stock.exchange}:{stock.symbol} {stock.name}")


if __name__ == "__main__":
    # 运行示例
    demo_ma_volume_strategy()
    # demo_compare_strategies()
