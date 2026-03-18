# Redis Service Framework

本项目提供行情快照、股池数据存储和回测功能的Redis服务框架。

## 功能特性

- **行情快照**: 基于Redis Pub/Sub的实时行情广播
- **股池存储**: 基于Redis Stream的选股数据持久化
- **回测引擎**: 完整的回测流程支持
- **数据库集成**: MySQL股票数据查询
- **选股策略**: 可扩展的选股策略框架
- **连接池**: 高效的Redis和MySQL连接管理
- **类型提示**: 完整的Python类型注解

## 项目结构

```
redis_service/
├── config/                  # 配置管理
│   └── settings.py
├── core/                    # Redis连接池
│   ├── connection.py
│   └── base_service.py
├── database/                # MySQL数据库
│   ├── connection.py
│   ├── queries.py
│   ├── schema.sql          # 选股结果表结构
│   └── selection_repository.py
├── market/                  # 行情Pub/Sub
│   ├── publisher.py
│   └── subscriber.py
├── selection/               # 股池Stream
│   ├── writer.py
│   └── reader.py
├── strategy/                # 选股策略
│   ├── base.py
│   ├── ma_breakthrough.py
│   ├── ma_volume_strategy.py  # 均线成交量策略
│   └── selector.py
├── backtest/                # 回测引擎
│   ├── engine.py
│   └── publisher.py
├── models/                  # 数据模型
│   ├── snapshot.py
│   └── stock_selection.py
├── utils/                   # 工具函数
│   └── serializer.py
└── examples/                # 使用示例
    ├── publish_snapshot_demo.py
    ├── subscribe_snapshot_demo.py
    ├── write_selection_demo.py
    ├── read_selection_demo.py
    ├── backtest_demo.py
    ├── consumer_demo.py         # 消费者Demo
    └── ma_volume_strategy_demo.py  # 均线成交量策略示例
```

## 快速开始

### 安装依赖

```bash
pip install redis pydantic pymysql
```

### 配置Redis连接

```python
from config.settings import settings

# 修改Redis配置
settings.redis.host = "localhost"
settings.redis.port = 6379
settings.redis.password = "your_password"
```

### 配置数据库连接

```python
from config.settings import settings

# 修改数据库配置
settings.database.host = "localhost"
settings.database.port = 3306
settings.database.user = "root"
settings.database.password = "your_password"
settings.database.database = "stock_db"
```

## 使用示例

### 1. 行情快照

#### 发布行情
```python
from market.publisher import SnapshotPublisher
from models.snapshot import SnapshotData, MarketQuote

publisher = SnapshotPublisher()

snapshot = SnapshotData(
    type="snapshot",
    timestamp=1703234567890,
    exchange="SSE",
    symbol="600036",
    data=MarketQuote(
        last_price=32.56,
        volume=12345678,
        amount=3987654321,
        bid_price=[32.55, 32.54, 32.53, 32.52, 32.51],
        bid_volume=[100, 200, 300, 400, 500],
        ask_price=[32.57, 32.58, 32.59, 32.60, 32.61],
        ask_volume=[150, 250, 350, 450, 550],
        date="20260317",
        timestamp="14:45:15"
    )
)

publisher.publish(snapshot)
```

#### 订阅行情
```python
from market.subscriber import SnapshotSubscriber

subscriber = SnapshotSubscriber()

for message in subscriber.subscribe("market:snapshot:SSE:*"):
    print(message)
```

### 2. 股池数据

#### 写入股池
```python
from selection.writer import SelectionWriter

writer = SelectionWriter()
writer.write_selection(
    date="20260317",
    batch_id="SELECT_20260317_001",
    strategy_id="MA10_BREAKTHROUGH",
    stocks=[...]
)
```

#### 读取股池
```python
from selection.reader import SelectionReader

reader = SelectionReader()
messages = reader.read_selection("20260317", count=100)
```

### 3. 回测引擎

```python
from config.settings import BacktestConfig
from backtest.engine import BacktestEngine

# 配置回测参数
config = BacktestConfig(
    start_date="20241001",
    end_date="20241008",
    strategy_id="MA10_BREAKTHROUGH",
    use_strategy=True,
    default_selection_count=10
)

# 创建并运行回测引擎
engine = BacktestEngine(config)
engine.initialize(db_config={...})
engine.run()
engine.close()
```

### 4. 消费者Demo

```python
from examples.consumer_demo import StockConsumer

# 创建消费者
consumer = StockConsumer()

# 运行消费者（先消费选股池，再消费行情数据）
consumer.run(date="20241008")
consumer.close()
```

### 5. 均线成交量策略

```python
from strategy.ma_volume_strategy import MAVolumeStrategy
from strategy.selector import StockSelector

# 创建策略
strategy = MAVolumeStrategy({
    "max_market_cap": 200000,    # 市值<200亿
    "min_slope_angle": 0,         # 斜率>0°
    "max_slope_angle": 30,        # 斜率<30°
    "max_volume_ratio": 3         # 成交量比≤3
})

# 执行选股
selector = StockSelector(strategy=strategy)
stocks = selector.select(date="20241008", save_to_db=True)
```

## 消息通道规范

### 行情快照
- 通道格式: `market:snapshot:{exchange}:{symbol}`
- 示例: `market:snapshot:SSE:600036`

### 股池数据
- Stream Key: `selection:stream:{date}`
- 示例: `selection:stream:20260317`

## 回测流程

1. **选股阶段**: 从数据库获取日线数据，执行选股策略
2. **推送股池**: 将选股结果推送到Redis Stream
3. **消费股池**: 策略模块消费股池数据
4. **推送行情**: 根据选股结果推送对应的Tick数据到行情通道

## 数据库表结构

### 行情数据表
- `stock_basic_info`: 股票基本信息
- `stock_daily_data`: 日线数据
- `stock_minute_data`: 分钟线数据
- `level2_3s_YYYYMMDD`: Tick数据(按日分表)

### 选股结果表
- `stock_selection_result`: 选股结果主表
- `stock_selection_detail`: 选股结果明细表
- `stock_selection_stats`: 选股结果统计表
