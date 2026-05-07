"""
回测引擎使用示例
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baostock_tool.redis_service.config.settings import settings, BacktestConfig
from baostock_tool.redis_service.backtest.engine import BacktestEngine


def demo_with_strategy():
    """使用策略的回测示例"""
    print("="*60)
    print("回测示例1: 使用MA10突破策略")
    print("="*60)
    
    # 配置回测参数
    config = BacktestConfig(
        start_date="20241001",
        end_date="20241008",
        strategy_id="MA10_BREAKTHROUGH",
        use_strategy=True,
        strategy_params={
            "ma_period": 10,
            "volume_ratio_min": 1.0,
            "turnover_min": 0.3
        },
        default_selection_count=10
    )
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 配置数据库连接（请根据实际情况修改）
    db_config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "your_password",
        "database": "stock_db"
    }
    
    try:
        # 初始化引擎
        engine.initialize(db_config=db_config)
        
        # 运行回测
        engine.run()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # 关闭引擎
        engine.close()


def demo_without_strategy():
    """不使用策略的回测示例（取成交额前10）"""
    print("\n" + "="*60)
    print("回测示例2: 不使用策略（取成交额前10）")
    print("="*60)
    
    # 配置回测参数
    config = BacktestConfig(
        start_date="20241001",
        end_date="20241003",
        use_strategy=False,  # 不使用策略
        default_selection_count=10
    )
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 配置数据库连接
    db_config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "your_password",
        "database": "stock_db"
    }
    
    try:
        # 初始化引擎
        engine.initialize(db_config=db_config)
        
        # 运行回测
        engine.run()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # 关闭引擎
        engine.close()


def demo_single_day():
    """单日回测示例"""
    print("\n" + "="*60)
    print("回测示例3: 单日回测")
    print("="*60)
    
    # 配置回测参数
    config = BacktestConfig(
        start_date="20241008",
        end_date="20241008",
        use_strategy=False,
        default_selection_count=5
    )
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 配置数据库连接
    db_config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "your_password",
        "database": "stock_db"
    }
    
    try:
        # 初始化引擎
        engine.initialize(db_config=db_config)
        
        # 运行回测
        engine.run()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # 关闭引擎
        engine.close()


if __name__ == "__main__":
    # 选择要运行的示例
    # demo_with_strategy()
    # demo_without_strategy()
    demo_single_day()
