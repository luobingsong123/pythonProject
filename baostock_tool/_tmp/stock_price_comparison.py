"""
股票开盘价对比工具
查询所有个股在两个日期的开盘价，并计算涨跌幅
"""

import sys
import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baostock_tool import config


def get_db_engine():
    """获取数据库引擎"""
    db_config = config.get_db_config()
    db_url = URL.create(
        drivername="mysql+pymysql",
        username=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["database"],
        query={"charset": "utf8mb4"}
    )
    return create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)


def get_all_stocks(engine):
    """获取数据库中所有个股"""
    query = """
    SELECT DISTINCT market, code_int
    FROM stock_daily_data
    WHERE frequency = 'd'
    ORDER BY market, code_int
    """
    df = pd.read_sql(query, engine)
    return df


def get_open_price(engine, market, code_int, target_date):
    """
    获取指定股票在目标日期的开盘价
    如果没有该日期的数据，则返回最近的开盘价和实际日期
    """
    # 查询该股票在目标日期附近的开盘价
    query = text("""
    SELECT date, open
    FROM stock_daily_data
    WHERE market = :market
      AND code_int = :code_int
      AND frequency = 'd'
    ORDER BY ABS(DATEDIFF(date, :target_date))
    LIMIT 1
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {
            'market': market,
            'code_int': code_int,
            'target_date': target_date
        }).fetchone()
    
    if result:
        return result[1], result[0]
    return None, None


def calculate_price_change():
    """计算所有个股在两个日期的涨跌幅"""
    engine = get_db_engine()
    
    # 设置目标日期
    date1 = "2024-09-27"
    date2 = "2026-02-03"
    
    print(f"正在查询股票数据...")
    print(f"日期1: {date1}")
    print(f"日期2: {date2}")
    print()
    
    # 获取所有个股
    stocks_df = get_all_stocks(engine)
    print(f"数据库中共有 {len(stocks_df)} 只个股")
    print()
    
    results = []
    
    # 遍历每只股票
    for idx, row in stocks_df.iterrows():
        market = row['market']
        code_int = row['code_int']
        
        # 获取日期1的开盘价（最远日期）
        open1, actual_date1 = get_open_price(engine, market, code_int, date1)
        
        # 获取日期2的开盘价（最近日期）
        open2, actual_date2 = get_open_price(engine, market, code_int, date2)
        
        if open1 is not None and open2 is not None:
            # 计算涨跌幅
            price_change = open2 - open1
            pct_change = (price_change / open1) * 100 if open1 != 0 else 0
            
            results.append({
                'market': market,
                'code_int': code_int,
                'stock_code': f"{market}.{code_int}",
                'open_price_date1': open1,
                'actual_date1': actual_date1,
                'open_price_date2': open2,
                'actual_date2': actual_date2,
                'price_change': price_change,
                'pct_change': pct_change
            })
        
        # 显示进度
        if (idx + 1) % 100 == 0:
            print(f"已处理 {idx + 1}/{len(stocks_df)} 只股票...")
    
    # 转换为DataFrame
    results_df = pd.DataFrame(results)
    
    if not results_df.empty:
        # 按涨跌幅排序
        results_df = results_df.sort_values('pct_change', ascending=False)
        
        # 转换为数值类型
        results_df['open_price_date1'] = pd.to_numeric(results_df['open_price_date1'], errors='coerce')
        results_df['open_price_date2'] = pd.to_numeric(results_df['open_price_date2'], errors='coerce')
        results_df['price_change'] = pd.to_numeric(results_df['price_change'], errors='coerce')
        results_df['pct_change'] = pd.to_numeric(results_df['pct_change'], errors='coerce')
        
        # 格式化输出
        results_df['open_price_date1'] = results_df['open_price_date1'].round(2)
        results_df['open_price_date2'] = results_df['open_price_date2'].round(2)
        results_df['price_change'] = results_df['price_change'].round(2)
        results_df['pct_change'] = results_df['pct_change'].round(2)
        
        print("\n" + "="*100)
        print("股票开盘价对比结果（按涨跌幅排序）")
        print("="*100)
        print(f"{'股票代码':<15} {'日期1(实际)':<12} {'开盘价1':<10} {'日期2(实际)':<12} {'开盘价2':<10} {'涨跌额':<10} {'涨跌幅(%)':<10}")
        print("-"*100)
        
        for _, row in results_df.iterrows():
            print(f"{row['stock_code']:<15} {str(row['actual_date1']):<12} {row['open_price_date1']:<10.2f} "
                  f"{str(row['actual_date2']):<12} {row['open_price_date2']:<10.2f} "
                  f"{row['price_change']:<10.2f} {row['pct_change']:<10.2f}")
        
        print("\n" + "="*100)
        print("统计信息")
        print("="*100)
        print(f"总股票数: {len(results_df)}")
        print(f"上涨股票数: {len(results_df[results_df['pct_change'] > 0])}")
        print(f"下跌股票数: {len(results_df[results_df['pct_change'] < 0])}")
        print(f"平盘股票数: {len(results_df[results_df['pct_change'] == 0])}")
        print(f"平均涨跌幅: {results_df['pct_change'].mean():.2f}%")
        print(f"最大涨幅: {results_df['pct_change'].max():.2f}%")
        print(f"最大跌幅: {results_df['pct_change'].min():.2f}%")
        
        # 保存到CSV文件
        output_file = os.path.join(os.path.dirname(__file__), f"stock_price_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存到: {output_file}")
        
        return results_df
    else:
        print("未查询到任何股票数据")
        return None


if __name__ == "__main__":
    calculate_price_change()
