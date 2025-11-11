# from backtesting.test import GOOG
# print(GOOG.head())
import pandas as pd
import numpy as np
from jqdatasdk import *

# 认证
auth('13877907589', 'aA*963.-+')

print(get_account_info())
print(get_query_count())

# 获取数据
end_date = pd.Timestamp.today().strftime('%Y-%m-%d')
all_stocks = get_all_securities(types=['stock'], date=end_date)
print(f"全市场股票数量: {len(all_stocks)}")
print(all_stocks.head())


# 优化后的CSV写入代码
def save_stocks_to_csv_optimized(stocks_data, filename='全市场股票代码.csv'):
    """
    将股票数据优化保存为CSV格式

    参数:
    stocks_data: DataFrame, 股票数据
    filename: str, 输出文件名
    """
    try:
        # 优化CSV保存参数
        stocks_data.to_csv(
            filename,
            index=True,  # 保留索引（股票代码）
            encoding='utf-8-sig',  # 支持中文且Excel兼容
            index_label='symbol',  # 为索引列设置标签
            na_rep='N/A'  # 缺失值处理
        )
        print(f"股票数据已优化保存至: {filename}")

        # 验证保存结果
        verify_data = pd.read_csv(filename, encoding='utf-8-sig')
        print(f"验证: 成功读取{len(verify_data)}条记录")
        print("前5行数据预览:")
        print(verify_data.head())

    except Exception as e:
        print(f"保存CSV时出错: {e}")


# 使用优化后的函数
save_stocks_to_csv_optimized(all_stocks)


# 可选：保存为其他格式的备份
def save_additional_formats(stocks_data, base_filename='全市场股票代码'):
    """保存为多种格式以供不同用途使用"""

    # 1. 简洁版CSV（不含索引）
    stocks_data.to_csv(f"{base_filename}_简洁版.csv",
                       index=False, encoding='utf-8-sig')

    # 2. 带时间戳的备份
    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    stocks_data.to_csv(f"{base_filename}_备份_{timestamp}.csv",
                       index=True, encoding='utf-8-sig')

    print("多格式备份完成")


# 执行多格式保存
save_additional_formats(all_stocks)

print(get_query_count())

# 日K数据获取
print(get_price("600900.XSHG", start_date='2024-08-03', end_date='2025-08-10', frequency='1d'))

print(get_query_count())