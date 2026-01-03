# 策略触发点位数据库设计

## 概述

本数据库设计用于存储和量化交易策略的触发点位JSON数据，方便后续分析和回测。

## 表结构

### strategy_trigger_points（策略触发点位表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | bigint unsigned | 主键ID，自增 |
| strategy_name | varchar(100) | 策略名称 |
| stock_code | varchar(10) | 证券代码 |
| market | enum('sh','sz','bj') | 市场：sh=上海，sz=深圳，bj=北京 |
| trigger_points_json | json | 策略触发的对应日期JSON数据 |
| backtest_start_date | date | 策略回测开始日期 |
| backtest_end_date | date | 策略回测结束日期 |
| trigger_count | int unsigned | 触发点位数量 |
| created_at | timestamp | 创建时间 |
| updated_at | timestamp | 更新时间 |

### 索引

- 主键索引：`id`
- 唯一索引：`uk_strategy_stock_backtest` (strategy_name, stock_code, market, backtest_start_date, backtest_end_date)
- 普通索引：
  - `idx_strategy_name` (strategy_name)
  - `idx_stock_code` (stock_code)
  - `idx_market` (market)
  - `idx_created_at` (created_at)

## JSON数据结构示例

```json
[
  {
    "date": "2024-01-05",
    "trigger_type": "buy",
    "price": 3.52,
    "volume": 1250000,
    "volume_rank": "20日最低"
  },
  {
    "date": "2024-01-08",
    "trigger_type": "sell",
    "price": 3.58,
    "hold_days": 2,
    "profit": 0.06,
    "profit_rate": 1.70
  }
]
```

## 使用方法

### 1. 创建表

```python
from database_schema.strategy_trigger_db import StrategyTriggerDB

db = StrategyTriggerDB()
db.create_table(drop_existing=False)
```

### 2. 插入数据

```python
trigger_data = [
    {
        "date": "2024-01-05",
        "trigger_type": "buy",
        "price": 3.52,
        "volume": 1250000,
        "volume_rank": "20日最低"
    }
]

db.insert_trigger_points(
    strategy_name="CodeBuddyStrategy",
    stock_code="601288",
    market="sh",
    trigger_points_json=trigger_data,
    backtest_start_date="2024-01-01",
    backtest_end_date="2024-12-31"
)
```

### 3. 查询数据

```python
# 查询指定策略的所有触发点位
results = db.query_trigger_points(strategy_name="CodeBuddyStrategy")

# 查询指定股票的策略触发数据
results = db.query_trigger_points(stock_code="601288", market="sh")

# 查询指定时间范围内的回测数据
results = db.query_trigger_points(
    backtest_start_date="2024-01-01",
    backtest_end_date="2024-12-31"
)
```

### 4. 获取统计信息

```python
stats = db.get_statistics()
print(stats)
```

## 常用SQL查询

### 查询指定策略的所有触发点位

```sql
SELECT * FROM strategy_trigger_points
WHERE strategy_name = 'CodeBuddyStrategy';
```

### 查询指定股票的策略触发数据

```sql
SELECT * FROM strategy_trigger_points
WHERE stock_code = '601288' AND market = 'sh';
```

### 统计各策略的触发次数

```sql
SELECT
    strategy_name,
    COUNT(*) as stock_count,
    SUM(trigger_count) as total_triggers
FROM strategy_trigger_points
GROUP BY strategy_name;
```

### 查询JSON数据中的特定字段

```sql
SELECT
    strategy_name,
    stock_code,
    market,
    JSON_LENGTH(trigger_points_json) as trigger_count,
    JSON_EXTRACT(trigger_points_json, '$[0].date') as first_trigger_date
FROM strategy_trigger_points
WHERE stock_code = '601288';
```

## 注意事项

1. **唯一约束**：同一策略、同一股票、同一回测时间范围只能有一条记录，重复插入会自动更新
2. **JSON字段**：MySQL 5.7+支持JSON类型，可以使用JSON函数进行查询和操作
3. **市场标识**：使用枚举类型限制市场只能为 'sh'、'sz'、'bj'
4. **触发次数**：`trigger_count` 字段会自动计算JSON数组长度
5. **时间戳**：`created_at` 和 `updated_at` 自动维护

## 文件说明

- `strategy_trigger_points.sql` - SQL建表脚本
- `strategy_trigger_db.py` - Python数据库管理类
- `README.md` - 本文档
