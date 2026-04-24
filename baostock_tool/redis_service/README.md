# Redis Service Framework

本项目提供行情快照、股池数据存储和回测功能的Redis服务框架。

## 功能特性

- **行情快照**: 基于Redis Pub/Sub的实时行情广播
- **股池存储**: 基于Redis Stream的选股数据持久化
- **回测引擎**: 完整的回测流程支持
- **数据库集成**: MySQL股票数据查询
- **ClickHouse推送服务**: 支持快照、全逐笔、逐笔委托、逐笔成交四种推送模式
- **选股策略**: 可扩展的选股策略框架
- **连接池**: 高效的Redis和MySQL连接管理
- **类型提示**: 完整的Python类型注解

## 项目结构

```
redis_service/
├── clickhouse_server.py       # ClickHouse TCP推送服务入口
├── tick_server.py             # MySQL Tick推送服务入口
├── config/                  # 配置管理
│   ├── config.ini
│   └── settings.py
├── core/                    # Redis连接池
│   ├── connection.py
│   └── base_service.py
├── database/                # 数据查询层
│   ├── connection.py
│   ├── clickhouse_queries.py
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
│   ├── clickhouse_publisher.py
│   └── publisher.py
├── models/                  # 数据模型
│   ├── clickhouse_models.py
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
pip install redis pydantic pymysql clickhouse-driver
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

### 配置ClickHouse连接

```python
from config.settings import settings

# 修改ClickHouse配置
settings.clickhouse.host = "localhost"
settings.clickhouse.port = 9000
settings.clickhouse.user = "default"
settings.clickhouse.password = ""
settings.clickhouse.database = "quant_trader"
```

## ClickHouse 数据推送服务

ClickHouse 服务与原有 MySQL Tick 服务并行存在，不替换旧服务。

### 服务入口

- MySQL 服务: tick_server.py，默认端口 9999
- ClickHouse 服务: clickhouse_server.py，默认端口 9998

### 数据来源

- 快照: snapshot_YYYYMMDD
- 逐笔: tick_YYYYMMDD

### 支持的 sub_type

- 1: 快照
- 2: 全逐笔
- 3: 逐笔委托
- 4: 逐笔成交

### Redis 通道

- 快照: market:snapshot:{exchange}:{symbol}
- 逐笔: market:tick:{exchange}:{symbol}

### 启动方式

在 redis_service 目录下执行：

```bash
python clickhouse_server.py
```

如果使用项目虚拟环境：

```bash
..\.venv\Scripts\python.exe clickhouse_server.py
```

### 客户端启动方式

ClickHouse 客户端入口为 clickhouse_client.py，默认连接 9998 端口，并从选股池读取股票代码后发起订阅。

```bash
python clickhouse_client.py --sub-type 1 --start-date 20250401 --end-date 20250401
```

使用项目虚拟环境：

```bash
..\.venv\Scripts\python.exe clickhouse_client.py --sub-type 2 --start-date 20250401 --end-date 20250401
```

常用参数：

- --sub-type: 1=快照, 2=全逐笔, 3=逐笔委托, 4=逐笔成交
- --server-host: 服务端地址，默认 localhost
- --server-port: 服务端端口，默认 9998
- --output: 输出文件前缀，客户端会分别生成统计文件和数据文件

### 示例脚本

examples/clickhouse_subscribe_demo.py 提供了一个最小联调入口，适合在服务已启动、选股池已有数据时快速验证：

```bash
python examples/clickhouse_subscribe_demo.py --date 20250401 --sub-type 1
```

### 请求格式

客户端通过 TCP 发送 JSON，请求格式与原有 Tick 服务保持兼容：

```json
{
    "sub_type": 1,
    "start_date": "20250401",
    "end_date": "20250402",
    "stock": ["600036", "000001"]
}
```

### 配置示例

config/config.ini 中新增了 ClickHouse 配置段：

```ini
[clickhouse]
host = 10.10.1.90
port = 9000
user = default
password =
database = quant_trader
```

### 模块分层

- 服务入口: clickhouse_server.py
- 查询层: database/clickhouse_queries.py
- 发布层: backtest/clickhouse_publisher.py
- 模型层: models/clickhouse_models.py

### 空数据处理

当某只股票在 ClickHouse 中查不到数据时，服务只推送一条全字段降级消息，并使用 seqno = 0 作为结束标记。

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

### ClickHouse逐笔
- 通道格式: `market:tick:{exchange}:{symbol}`
- 示例: `market:tick:SSE:600036`

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
- `snapshot_YYYYMMDD`: ClickHouse快照表
- `tick_YYYYMMDD`: ClickHouse逐笔表

### 选股结果表
- `stock_selection_result`: 选股结果主表
- `stock_selection_detail`: 选股结果明细表
- `stock_selection_stats`: 选股结果统计表
