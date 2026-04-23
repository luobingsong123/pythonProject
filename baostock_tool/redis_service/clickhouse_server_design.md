# ClickHouse 数据推送服务设计方案

## 一、目标

基于 ClickHouse 数据库，新建 `clickhouse_server.py`，替代现有 `tick_server.py`（MySQL 数据源）。
支持 `sub_type=1`（快照）、`sub_type=2`（全逐笔）、`sub_type=3`（逐笔委托）、`sub_type=4`（逐笔成交）四种推送模式，推送字段与 ClickHouse 表结构保持一致。

## 二、现有架构回顾

```
tick_client.py ──TCP──▶ tick_server.py ──▶ StockQueryService(MySQL) ──▶ level2_3s_YYYYMMDD
                         │
                         └──▶ TickDataPublisher ──▶ SnapshotPublisher(Redis Pub/Sub)
                                                      │
                                                      └── market:snapshot:{exchange}:{symbol}
```

- 数据源：MySQL `level2_3s_YYYYMMDD` 表，3秒快照
- 只支持 `sub_type=1`（快照），推送前将 MySQL 字段转换为精简的 `SnapshotData` 格式（5档买卖盘）
- Redis 通道：`market:snapshot:{exchange}:{symbol}`

## 三、新架构设计

```
clickhouse_client.py ──TCP──▶ clickhouse_server.py ──▶ ClickHouseQueryService(ClickHouse)
                               │                        ├─ snapshot_YYYYMMDD  (sub_type=1)
                               │                        └─ tick_YYYYMMDD      (sub_type=2/3/4)
                               │
                               └──▶ DataPublisher(Redis Pub/Sub)
                                      ├─ market:snapshot:{exchange}:{symbol}  (sub_type=1)
                                      └─ market:tick:{exchange}:{symbol}      (sub_type=2/3/4)
```

### 核心变化

| 对比项 | 旧 tick_server | 新 clickhouse_server |
|--------|---------------|---------------------|
| 数据源 | MySQL (pymysql) | ClickHouse (clickhouse-driver) |
| 快照表 | `level2_3s_YYYYMMDD` | `snapshot_YYYYMMDD` |
| 逐笔表 | 无 | `tick_YYYYMMDD` |
| sub_type | 仅支持 1 | 支持 1(快照) + 2(全逐笔) + 3(逐笔委托) + 4(逐笔成交) |
| 推送字段 | 精简的 SnapshotData (5档) | 快照核心列 ~30列 + 逐笔全部20列 |
| 空数据处理 | 生成全天3秒间隔全-1数据 | 仅推一条全-1数据 |
| 服务端口 | 9999 | 9998 |
| Redis 通道 | `market:snapshot:*` | `market:snapshot:*` + `market:tick:*` |

## 四、ClickHouse 表结构参考

### 4.1 快照表 `snapshot_YYYYMMDD`（120列，推送核心列 ~30列）

**推送用核心列**（其余列不推送）:

| ClickHouse 列名 | 类型 | 说明 |
|-----------------|------|------|
| `trade_date` | Date | 交易日期 |
| `data_time` | UInt32 | 行情时间（整数格式 HHMMSSMMM） |
| `trade_datetime` | DateTime64(3) | 精确到毫秒的交易时间 |
| `security_id` | String | 6位股票代码 |
| `exchange_id` | UInt8 | 交易所：1=沪, 2=深 |
| `last_price` | Float64 | 最新价 |
| `pre_close_price` | Float64 | 昨收价 |
| `open_price` | Float64 | 开盘价 |
| `high_price` | Float64 | 最高价 |
| `low_price` | Float64 | 最低价 |
| `qty` | UInt64 | 成交量 |
| `turnover` | Float64 | 成交额 |
| `avg_price` | Float64 | 均价 |
| `trades_count` | UInt64 | 成交笔数 |
| `ticker_status` | String | 证券状态 |
| `total_bid_qty` | UInt64 | 买单总量 |
| `total_ask_qty` | UInt64 | 卖单总量 |
| `bid0_price` ~ `bid9_price` | Float64 | 买1~买10价 |
| `bid0_qty` ~ `bid9_qty` | UInt64 | 买1~买10量 |
| `ask0_price` ~ `ask9_price` | Float64 | 卖1~卖10价 |
| `ask0_qty` ~ `ask9_qty` | UInt64 | 卖1~卖10量 |

> 共 17个独立字段 + 10档买价 + 10档买量 + 10档卖价 + 10档卖量 = ~37列
> 实际以 `SNAPSHOT_PUSH_COLUMNS` 列表定义为准，可按需增减

### 4.2 逐笔表 `tick_YYYYMMDD`（20列，全部推送）

| ClickHouse 列名 | 类型 | 说明 |
|-----------------|------|------|
| `trade_date` | Date | 交易日期 |
| `update_time` | UInt32 | 更新时间 |
| `trade_datetime` | DateTime64(3) | 精确到毫秒的交易时间 |
| `exchange_id` | UInt8 | 交易所：1=沪, 2=深 |
| `channel_no` | UInt32 | 通道号 |
| `seq_no` | UInt64 | 序列号 |
| `security_id` | String | 6位股票代码 |
| `trade2_order1` | UInt8 | 成交/委托标志：1=成交, 2=委托 |
| `price` | Float64 | 价格 |
| `volume` | UInt64 | 数量 |
| `trd_money` | Float64 | 成交金额 |
| `ord_side` | String | 委托方向 |
| `ord_type` | String | 委托类型 |
| `trd_bs_flag` | String | 成交买卖标志 |
| `trd_buy_no` | UInt64 | 买方委托序号 |
| `trd_sell_no` | UInt64 | 卖方委托序号 |
| `ord_no` | UInt64 | 委托序号 |
| `biz_index` | UInt64 | 业务序列号 |
| `trans_flag` | UInt32 | 传输标志 |
| `order_trd_volume` | UInt64 | 委托成交量 |

## 五、sub_type 定义

| sub_type | 含义 | 数据来源 | 过滤条件 |
|----------|------|---------|---------|
| 1 | 快照 | `snapshot_YYYYMMDD` | 无 |
| 2 | 全逐笔 | `tick_YYYYMMDD` | 无 |
| 3 | 逐笔委托 | `tick_YYYYMMDD` | `trade2_order1 = 2` |
| 4 | 逐笔成交 | `tick_YYYYMMDD` | `trade2_order1 = 1` |

## 六、推送消息格式设计

### 6.1 快照消息 (`sub_type=1`)

**Redis 通道**: `market:snapshot:{exchange}:{symbol}`

**消息结构**:
```json
{
  "type": "snapshot",
  "timestamp": 1706140800123,
  "seqno": 42,
  "exchange": "SSE",
  "symbol": "600036",
  "data": {
    "trade_date": "2025-04-01",
    "data_time": 93001500,
    "trade_datetime": "2025-04-01 09:30:01.500",
    "exchange_id": 1,
    "last_price": 38.52,
    "pre_close_price": 38.30,
    "open_price": 38.35,
    "high_price": 38.55,
    "low_price": 38.30,
    "qty": 123456,
    "turnover": 47567890.0,
    "avg_price": 38.42,
    "trades_count": 890,
    "ticker_status": "N",
    "total_bid_qty": 50000,
    "total_ask_qty": 45000,
    "bid_price": [38.51, 38.50, 38.49, 38.48, 38.47, 38.46, 38.45, 38.44, 38.43, 38.42],
    "bid_volume": [100, 200, 300, 150, 250, 180, 220, 160, 140, 190],
    "ask_price": [38.53, 38.54, 38.55, 38.56, 38.57, 38.58, 38.59, 38.60, 38.61, 38.62],
    "ask_volume": [180, 220, 160, 140, 190, 170, 210, 150, 130, 200]
  }
}
```

**字段映射说明**:
- `exchange_id` (UInt8) → 消息外层 `exchange` (SSE/SZSE 字符串)，`data` 中保留原始 `exchange_id`
- `security_id` → 消息外层 `symbol`
- `trade_datetime` → 消息外层 `timestamp` (毫秒时间戳)
- 10档买卖盘：`bid0_price`~`bid9_price` → `bid_price` 列表，`bid0_qty`~`bid9_qty` → `bid_volume` 列表
- 只推送核心列，非核心列（如 `cancel_buy_count`、`etf_buy_qty` 等）不推送

### 6.2 逐笔消息 (`sub_type=2/3/4`)

**Redis 通道**: `market:tick:{exchange}:{symbol}`

三种 sub_type 共用相同的消息格式，区别仅在于查询时的过滤条件不同。

**消息结构**:
```json
{
  "type": "tick",
  "sub_type": 2,
  "timestamp": 1706140800123,
  "seqno": 42,
  "exchange": "SSE",
  "symbol": "600036",
  "data": {
    "trade_date": "2025-04-01",
    "update_time": 93001500,
    "trade_datetime": "2025-04-01 09:30:01.500",
    "exchange_id": 1,
    "channel_no": 1,
    "seq_no": 12345,
    "trade2_order1": 1,
    "price": 38.52,
    "volume": 100,
    "trd_money": 3852.0,
    "ord_side": "B",
    "ord_type": "L",
    "trd_bs_flag": "B",
    "trd_buy_no": 67890,
    "trd_sell_no": 67891,
    "ord_no": 54321,
    "biz_index": 98765,
    "trans_flag": 0,
    "order_trd_volume": 100
  }
}
```

**过滤条件**:
- `sub_type=2`：无额外过滤，返回全部逐笔数据
- `sub_type=3`：`WHERE trade2_order1 = 2`（逐笔委托）
- `sub_type=4`：`WHERE trade2_order1 = 1`（逐笔成交）

## 七、空数据处理

当 ClickHouse 查不到某只股票的数据时，推送 **一条** 全字段为 -1 的消息：

- 快照空数据：`last_price`、`pre_close_price`、`open_price` 等价格字段设为 -1，`bid_price`/`ask_price` 为10个-1的列表，`bid_volume`/`ask_volume` 为10个-1的列表，其余数值字段为 -1
- 逐笔空数据：`price`、`trd_money` 设为 -1，`volume`、`seq_no` 等数值字段设为 -1，`ord_side`、`ord_type` 等字符串字段设为空字符串
- 该条消息的 `seqno = 0`（同时表示推送完成信号）

## 八、新增/修改文件清单

### 8.1 新增文件

| 文件路径 | 说明 |
|---------|------|
| `clickhouse_server.py` | 新服务主入口，TCP 服务端（端口 9998），参考现有 `tick_server.py` 结构 |
| `clickhouse_queries.py` | ClickHouse 查询服务，参考现有 `database/queries.py` 中的 tick 相关方法 |
| `clickhouse_publisher.py` | ClickHouse 数据发布器，参考现有 `backtest/publisher.py` |
| `clickhouse_models.py` | 快照/逐笔数据模型定义，参考现有 `models/snapshot.py` |

### 8.2 后续新增文件

| 文件路径 | 说明 |
|---------|------|
| `clickhouse_client.py` | 新客户端，适配新消息格式，后续单独实现 |

### 8.3 修改文件

| 文件路径 | 说明 |
|---------|------|
| `config/settings.py` | 新增 `ClickHouseConfig` 配置类 |
| `config/config.ini` | 新增 `[clickhouse]` 配置段 |

### 8.4 不修改的文件

- `tick_server.py` / `tick_client.py` — 旧服务保持不变，新旧服务独立运行
- `database/` — MySQL 查询服务保持不变
- `backtest/publisher.py` — 旧发布器保持不变
- `models/snapshot.py` — 旧模型保持不变

## 九、模块详细设计

### 9.1 `clickhouse_queries.py` — ClickHouse 查询服务

```python
class ClickHouseQueryService:
    """ClickHouse 数据查询服务"""
    
    def __init__(self, client):
        self.client = client  # clickhouse-driver.Client
    
    def get_snapshot_data(self, date: str, stocks: List[Tuple]) -> Dict[str, List[Dict]]:
        """查询快照数据（核心列）
        - date: YYYYMMDD
        - stocks: [(market, code), ...]  market: sh/sz
        - 返回: {symbol: [row1, row2, ...]}
        - SQL: SELECT {核心列} FROM snapshot_{date}
               WHERE security_id IN (...) AND exchange_id IN (...)
               ORDER BY trade_datetime
        """
    
    def get_tick_data(self, date: str, stocks: List[Tuple], sub_type: int = 2) -> Dict[str, List[Dict]]:
        """查询逐笔数据
        - date: YYYYMMDD
        - stocks: [(market, code), ...]
        - sub_type: 2=全逐笔, 3=逐笔委托(trade2_order1=2), 4=逐笔成交(trade2_order1=1)
        - 返回: {symbol: [row1, row2, ...]}
        - SQL: SELECT * FROM tick_{date}
               WHERE security_id IN (...) AND exchange_id IN (...)
               [AND trade2_order1 = ?]  -- sub_type 3/4 时追加
               ORDER BY trade_datetime
        """
    
    def check_table_exists(self, date: str, table_type: str) -> bool:
        """检查分表是否存在
        - table_type: 'snapshot' 或 'tick'
        """
```

**关键 SQL 差异**:
- 表名: `snapshot_20250401` / `tick_20250401`
- 市场过滤: `exchange_id = 1` (沪) / `exchange_id = 2` (深)，不再用字符串 `SSE`/`SZSE`
- 参数占位: ClickHouse 用 `%(param)s` 而非 MySQL 的 `%s`
- 排序: `ORDER BY trade_datetime` 而非 `ORDER BY TradingTime`
- 快照查询只 SELECT 核心列，逐笔查询 SELECT 全部20列

### 9.2 `clickhouse_models.py` — 数据模型

```python
# 快照推送核心列定义
SNAPSHOT_PUSH_COLUMNS = [
    'trade_date', 'data_time', 'trade_datetime', 'security_id', 'exchange_id',
    'last_price', 'pre_close_price', 'open_price', 'high_price', 'low_price',
    'qty', 'turnover', 'avg_price', 'trades_count', 'ticker_status',
    'total_bid_qty', 'total_ask_qty',
    'bid0_price', 'bid0_qty', 'ask0_price', 'ask0_qty',
    'bid1_price', 'bid1_qty', 'ask1_price', 'ask1_qty',
    'bid2_price', 'bid2_qty', 'ask2_price', 'ask2_qty',
    'bid3_price', 'bid3_qty', 'ask3_price', 'ask3_qty',
    'bid4_price', 'bid4_qty', 'ask4_price', 'ask4_qty',
    'bid5_price', 'bid5_qty', 'ask5_price', 'ask5_qty',
    'bid6_price', 'bid6_qty', 'ask6_price', 'ask6_qty',
    'bid7_price', 'bid7_qty', 'ask7_price', 'ask7_qty',
    'bid8_price', 'bid8_qty', 'ask8_price', 'ask8_qty',
    'bid9_price', 'bid9_qty', 'ask9_price', 'ask9_qty',
]

class SnapshotMessage(BaseModel):
    """快照推送消息"""
    type: str = "snapshot"           # 消息类型
    timestamp: int                    # 毫秒时间戳 (来自 trade_datetime)
    seqno: int                        # 序列号 (1递增, 最后一笔=0)
    exchange: str                     # SSE / SZSE
    symbol: str                       # 6位股票代码
    data: Dict[str, Any]              # 核心列数据 (买卖盘转为列表)
    
    def get_channel(self) -> str:
        return f"market:snapshot:{self.exchange}:{self.symbol}"


class TickMessage(BaseModel):
    """逐笔推送消息"""
    type: str = "tick"                # 消息类型
    sub_type: int                     # 2=全逐笔, 3=逐笔委托, 4=逐笔成交
    timestamp: int                    # 毫秒时间戳
    seqno: int                        # 序列号
    exchange: str                     # SSE / SZSE
    symbol: str                       # 6位股票代码
    data: Dict[str, Any]              # 与 ClickHouse tick 表列一致
    
    def get_channel(self) -> str:
        return f"market:tick:{self.exchange}:{self.symbol}"
```

**设计要点**:
- 快照：`data` 中只包含 `SNAPSHOT_PUSH_COLUMNS` 定义的核心列，10档买卖盘转为 `bid_price`/`bid_volume`/`ask_price`/`ask_volume` 列表
- 逐笔：`data` 中包含全部20列原始数据
- `exchange_id` (数字) → `exchange` (字符串) 在消息外层，`data` 中保留原始 `exchange_id` 数值

### 9.3 `clickhouse_publisher.py` — 数据发布器

```python
class ClickHousePublisher:
    """ClickHouse 数据发布器"""
    
    BATCH_SIZE = 5000  # Pipeline 分批大小
    
    def __init__(self, query_service, redis_client, use_pipeline=True):
        self.query_service = query_service
        self.redis_client = redis_client
        self.use_pipeline = use_pipeline
    
    def publish_snapshot_batch(self, date, stocks) -> Dict[str, int]:
        """批量推送快照数据 (sub_type=1)
        1. 查询 ClickHouse snapshot_{date} 核心列
        2. 按 trade_datetime 全局排序
        3. 逐条构建 SnapshotMessage → Redis Pub/Sub
        4. 查不到数据的股票：推送一条全-1消息
        """
    
    def publish_tick_batch(self, date, stocks, sub_type=2) -> Dict[str, int]:
        """批量推送逐笔数据 (sub_type=2/3/4)
        1. 查询 ClickHouse tick_{date} (按 sub_type 过滤)
        2. 按 trade_datetime 全局排序
        3. 逐条构建 TickMessage → Redis Pub/Sub
        4. 查不到数据的股票：推送一条全-1消息
        """
```

**与旧 `TickDataPublisher` 的差异**:
- 空数据降级改为：只推一条全-1消息（而非全天3秒间隔数据）
- 不再做 MySQL→SnapshotData 的字段映射转换，直接按 ClickHouse 字段构建消息
- `seqno` 编号机制不变：每只证券独立编号，1 递增，最后一笔为 0

### 9.4 `clickhouse_server.py` — 服务主入口

```python
class ClickHouseServer:
    """ClickHouse 数据推送服务器"""
    
    def __init__(self, host="0.0.0.0", port=9998):
        # 端口 9998，与旧 tick_server (9999) 独立
        ...
    
    def initialize(self, ch_config, redis_config):
        """初始化 ClickHouse 连接 + Redis 连接"""
        ...
    
    def _handle_client(self, client_socket, client_address):
        """处理客户端请求"""
        # 解析 TickRequest (复用现有 TickRequest 类)
        # 根据 sub_type 分发:
        #   sub_type=1 → publisher.publish_snapshot_batch()
        #   sub_type=2 → publisher.publish_tick_batch(sub_type=2)
        #   sub_type=3 → publisher.publish_tick_batch(sub_type=3)
        #   sub_type=4 → publisher.publish_tick_batch(sub_type=4)
        #   其他 → 返回错误
        ...
```

**请求格式**（兼容现有 `TickRequest`）:
```json
{
  "sub_type": 1,           // 1=快照, 2=全逐笔, 3=逐笔委托, 4=逐笔成交
  "start_date": "20250401",
  "end_date": "20250402",
  "stock": ["600036", "000001"]
}
```

## 十、配置扩展

在 `config/config.ini` 中新增 ClickHouse 配置段:

```ini
[clickhouse]
host = 10.10.1.90
port = 9000
user = default
password = 
database = quant_trader
```

在 `config/settings.py` 中新增:

```python
class ClickHouseConfig(BaseModel):
    """ClickHouse连接配置"""
    host: str = "localhost"
    port: int = 9000
    user: str = "default"
    password: str = ""
    database: str = "quant_trader"

# Settings 中新增:
class Settings(BaseModel):
    ...
    clickhouse: ClickHouseConfig = ClickHouseConfig()
```

## 十一、exchange_id 映射关系

| exchange_id (ClickHouse) | exchange (推送/通道) | market (请求参数) |
|--------------------------|--------------------|--------------------|
| 1 | SSE | sh |
| 2 | SZSE | sz |

查询时：`market` → `exchange_id`（sh→1, sz→2）
推送时：`exchange_id` → `exchange`（1→SSE, 2→SZSE）

## 十二、关键实现细节

### 12.1 ClickHouse 查询返回值处理

`clickhouse-driver` 默认返回 **元组列表**，需指定 `column_names` 或使用 `with_column_types` 获取字典。

推荐方式：
```python
# 方式一：查询后手动构建字典
rows = client.execute(sql, params, column_names=columns)
result = [dict(zip(columns, row)) for row in rows]

# 方式二：使用 with_column_types 获取列名
rows, columns = client.execute(sql, params, with_column_types=True)
column_names = [c[0] for c in columns]
result = [dict(zip(column_names, row)) for row in rows]
```

### 12.2 DateTime64 → 毫秒时间戳

```python
from datetime import datetime

# ClickHouse 返回的 DateTime64(3) 是 Python datetime 对象
dt = row['trade_datetime']  # datetime(2025, 4, 1, 9, 30, 1, 500000)
timestamp_ms = int(dt.timestamp() * 1000)
```

### 12.3 10档买卖盘 → 列表

```python
# ClickHouse 返回: bid0_price, bid1_price, ..., bid9_price
bid_price = [row[f'bid{i}_price'] for i in range(10)]
bid_volume = [row[f'bid{i}_qty'] for i in range(10)]
ask_price = [row[f'ask{i}_price'] for i in range(10)]
ask_volume = [row[f'ask{i}_qty'] for i in range(10)]
```

### 12.4 Redis Pipeline 推送

沿用现有模式，每 5000 条一个 Pipeline 批次：
```python
pipe = redis_client.pipeline()
for msg in batch:
    pipe.publish(msg.get_channel(), msg.model_dump_json())
pipe.execute()
```
