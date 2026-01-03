# 策略触发点位保存到数据库使用指南

## 功能说明

回测完成后，可以将策略的触发点位（买入/卖出日期及详细信息）以JSON格式保存到数据库中，方便后续分析和回溯。

## 使用方法

### 1. 单只股票回测并保存触发点位

```python
from backtrade_local_data_myst import run_backtest, BACKTEST_CONFIG
from utils.strategies.codebuddy_st import CodeBuddyStrategy

# 执行回测并保存触发点位到数据库
result = run_backtest(
    stock_code="601288",
    market="sh",
    name="农业银行",
    start_date=BACKTEST_CONFIG['start_date'],
    end_date=BACKTEST_CONFIG['end_date'],
    strategy_class=CodeBuddyStrategy,
    save_to_db=True  # 关键参数：设置为True保存到数据库
)
```

### 2. 批量回测并保存触发点位

```python
from backtrade_local_data_myst import batch_backtest, BACKTEST_CONFIG
from utils.strategies.codebuddy_st import CodeBuddyStrategy

# 批量回测并保存触发点位到数据库
batch_backtest(
    start_date=BACKTEST_CONFIG['start_date'],
    end_date=BACKTEST_CONFIG['end_date'],
    strategy_class=CodeBuddyStrategy,
    save_to_db=True  # 关键参数：设置为True保存到数据库
)
```

### 3. 不保存触发点位（默认行为）

```python
# 不设置save_to_db参数或设置为False，不保存触发点位
result = run_backtest(
    stock_code="601288",
    market="sh",
    name="农业银行",
    start_date="2024-01-01",
    end_date="2024-12-31",
    strategy_class=CodeBuddyStrategy
    # save_to_db 默认为 False
)
```

## 保存的JSON数据结构

### 买入点位示例

```json
{
  "date": "2024-01-05",
  "trigger_type": "buy",
  "price": 3.52,
  "volume": 1000,
  "commission": 3.52,
  "volume_rank": "20日最低",
  "trigger_volume": 1250000
}
```

### 卖出点位示例

```json
{
  "date": "2024-01-08",
  "trigger_type": "sell",
  "price": 3.58,
  "volume": 1000,
  "commission": 3.58,
  "profit": 60.0,
  "profit_rate": 1.70,
  "hold_days": 2
}
```

### 完整示例（一对买卖）

```json
[
  {
    "date": "2024-01-05",
    "trigger_type": "buy",
    "price": 3.52,
    "volume": 1000,
    "commission": 3.52,
    "volume_rank": "20日最低",
    "trigger_volume": 1250000
  },
  {
    "date": "2024-01-08",
    "trigger_type": "sell",
    "price": 3.58,
    "volume": 1000,
    "commission": 3.58,
    "profit": 60.0,
    "profit_rate": 1.70,
    "hold_days": 2
  }
]
```

## 数据库查询示例

### 1. 查询指定策略的所有触发点位

```python
from database_schema.strategy_trigger_db import StrategyTriggerDB

db = StrategyTriggerDB()
results = db.query_trigger_points(strategy_name="CodeBuddyStrategy")

for result in results:
    print(f"股票: {result.stock_code}, 市场类型: {result.market}")
    print(f"触发次数: {result.trigger_count}")
    print(f"触发点位JSON: {result.trigger_points_json}")
    print("-" * 60)
```

### 2. 查询指定股票的触发数据

```python
results = db.query_trigger_points(stock_code="601288", market="sh")
for result in results:
    print(f"策略: {result.strategy_name}")
    print(f"触发点位: {result.trigger_points_json}")
```

### 3. 查询指定时间范围的回测数据

```python
results = db.query_trigger_points(
    backtest_start_date="2024-01-01",
    backtest_end_date="2024-12-31"
)
```

### 4. 使用SQL直接查询

```sql
-- 查询指定策略的所有触发点位
SELECT * FROM strategy_trigger_points
WHERE strategy_name = 'CodeBuddyStrategy';

-- 查询JSON数据中的特定字段
SELECT
    stock_code,
    market,
    JSON_LENGTH(trigger_points_json) as trigger_count,
    JSON_EXTRACT(trigger_points_json, '$[0].date') as first_trigger_date
FROM strategy_trigger_points
WHERE strategy_name = 'CodeBuddyStrategy';
```

## 字段说明

### 买入点位字段

| 字段 | 类型 | 说明 |
|------|------|------|
| date | string | 触发日期 (YYYY-MM-DD) |
| trigger_type | string | 交易类型 (buy/sell) |
| price | float | 成交价格 |
| volume | float | 成交数量（股数） |
| commission | float | 手续费 |
| volume_rank | string | 成交量排名（如：20日最低） |
| trigger_volume | float | 触发时的成交量 |

### 卖出点位字段

| 字段 | 类型 | 说明 |
|------|------|------|
| date | string | 触发日期 (YYYY-MM-DD) |
| trigger_type | string | 交易类型 (buy/sell) |
| price | float | 成交价格 |
| volume | float | 成交数量（股数） |
| commission | float | 手续费 |
| profit | float | 利润（毛利润） |
| profit_rate | float | 收益率（%） |
| hold_days | int | 持有天数 |

## 注意事项

1. **唯一性约束**：同一策略、同一股票、同一回测时间范围只能有一条记录，重复运行会自动更新
2. **触发点位数量**：买入和卖出成对出现，所以触发点位数量总是偶数
3. **自动计算**：`trigger_count` 字段会自动根据JSON数组长度计算
4. **策略命名**：保存时使用策略类的 `__name__` 作为策略名称
5. **性能考虑**：批量回测时保存大量数据可能会影响性能，可以根据需要选择是否保存

## 扩展自定义策略

如果你有自定义策略，需要保存触发点位，请参考以下步骤：

### 1. 在策略的 `__init__` 方法中添加触发点位记录变量

```python
def __init__(self):
    # ... 其他初始化代码 ...
    self.trigger_points = []
    self.current_buy_info = None
```

### 2. 在 `notify_order` 方法中记录买卖点位

```python
def notify_order(self, order):
    if order.status in [order.Completed]:
        if order.isbuy():
            # 记录买入信息
            buy_info = {
                'date': str(self.datas[0].datetime.date()),
                'trigger_type': 'buy',
                'price': float(order.executed.price),
                'volume': float(order.executed.size),
                'commission': float(order.executed.comm)
            }
            self.current_buy_info = buy_info
        else:
            # 记录卖出信息
            if self.current_buy_info:
                sell_info = {
                    'date': str(self.datas[0].datetime.date()),
                    'trigger_type': 'sell',
                    'price': float(order.executed.price),
                    'volume': float(order.executed.size),
                    'commission': float(order.executed.comm),
                    'profit': float(order.executed.pnl),
                    'profit_rate': round((order.executed.pnl / self.buyprice) * 100, 2)
                }
                self.trigger_points.append(self.current_buy_info)
                self.trigger_points.append(sell_info)
                self.current_buy_info = None
```

### 3. 在 `run_backtest` 中设置 `save_to_db=True`

```python
run_backtest(
    stock_code="601288",
    market="sh",
    name="农业银行",
    start_date="2024-01-01",
    end_date="2024-12-31",
    strategy_class=YourCustomStrategy,
    save_to_db=True
)
```

## 完整示例

```python
# 示例：回测并保存触发点位
from backtrade_local_data_myst import run_backtest, BACKTEST_CONFIG
from utils.strategies.codebuddy_st import CodeBuddyStrategy
from database_schema.strategy_trigger_db import StrategyTriggerDB

# 1. 执行回测并保存
result = run_backtest(
    stock_code="601288",
    market="sh",
    name="农业银行",
    start_date="2024-01-01",
    end_date="2024-12-31",
    strategy_class=CodeBuddyStrategy,
    save_to_db=True
)

# 2. 查询保存的触发点位
db = StrategyTriggerDB()
results = db.query_trigger_points(
    strategy_name="CodeBuddyStrategy",
    stock_code="601288"
)

if results:
    for result in results:
        print(f"回测时间范围: {result.backtest_start_date} 至 {result.backtest_end_date}")
        print(f"触发点位数量: {result.trigger_count}")
        print(f"触发点位数据:")
        import json
        print(json.dumps(result.trigger_points_json, indent=2, ensure_ascii=False))
```

## 常见问题

### Q: 如何删除已保存的触发点位数据？

A: 可以使用SQL直接删除：

```sql
DELETE FROM strategy_trigger_points
WHERE strategy_name = 'CodeBuddyStrategy'
  AND stock_code = '601288';
```

### Q: 如何导出触发点位数据到文件？

A: 可以查询后使用pandas导出：

```python
import pandas as pd
import json

results = db.query_trigger_points(strategy_name="CodeBuddyStrategy")

data = []
for result in results:
    for point in result.trigger_points_json:
        point['strategy_name'] = result.strategy_name
        point['stock_code'] = result.stock_code
        point['market'] = result.market
        data.append(point)

df = pd.DataFrame(data)
df.to_csv('trigger_points.csv', index=False, encoding='utf-8-sig')
```

### Q: 批量回测时保存触发点位会不会很慢？

A: 会有一定性能影响，如果不需要保存，可以设置 `save_to_db=False` 或不设置该参数。
