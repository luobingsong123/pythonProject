# ClickHouse 数据推送服务说明

## 一、服务概述

| 项目 | 说明 |
|------|------|
| 入口文件 | `clickhouse_server.py` |
| 监听地址 | `0.0.0.0:9998` |
| 协议 | TCP Socket，请求/响应均为 JSON（UTF-8） |
| 数据源 | ClickHouse |
| 输出 | Redis Publish |
| 配置文件 | `config/config.ini` |

## 二、订阅请求格式

### 2.1 请求 JSON

```json
{
  "sub_type": 1,
  "start_date": "20241111",
  "end_date": "20241112",
  "stock": ["000001", "600001"]
}
```

### 2.2 字段说明

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `sub_type` | int | 否 | 1 | 订阅类型，见下表 |
| `start_date` | str | 是 | - | 起始日期，格式 YYYYMMDD |
| `end_date` | str | 是 | - | 结束日期，格式 YYYYMMDD（含当天） |
| `stock` | str[] | 是 | - | 股票代码列表 |

### 2.3 sub_type 订阅类型

| sub_type | 含义 | 数据源表 | 过滤条件 |
|:--------:|------|----------|----------|
| 1 | 快照 | `snapshot_{YYYYMMDD}` | 无 |
| 2 | 全量逐笔 | `tick_{YYYYMMDD}` | 无（委托+成交全部推送） |
| 3 | 逐笔成交 | `tick_{YYYYMMDD}` | `trade2_order1 = 2` |
| 4 | 逐笔委托 | `tick_{YYYYMMDD}` | `trade2_order1 = 1` |

> `trade2_order1` 字段含义：1=委托，2=成交

### 2.4 股票代码格式

| 格式 | 示例 | 说明 |
|------|------|------|
| 完整格式 | `sh.600000`、`sz.000001` | 带交易所前缀 |
| 纯代码 | `600000`、`000001` | 自动识别：6开头→sh，0/3开头→sz |

### 2.5 日期范围

`start_date` 和 `end_date` 之间的每一天都会查询并推送，包含首尾两天。

示例：`start_date=20241111, end_date=20241112` → 查询 20241111 和 20241112 两天的数据。

---

## 三、服务端响应格式

### 3.1 成功响应

```json
{
  "success": true,
  "sub_type": 1,
  "start_date": "20241111",
  "end_date": "20241112",
  "stats": [
    {
      "date": "20241111",
      "items": [
        {"code": "600036", "count": 4800},
        {"code": "000001", "count": 4800}
      ]
    },
    {
      "date": "20241112",
      "items": [
        {"code": "600036", "count": 4800},
        {"code": "000001", "count": 4800}
      ]
    }
  ]
}
```

### 3.2 失败响应

```json
{
  "success": false,
  "error": "错误描述信息",
  "timestamp": "2024-11-11T10:00:00.000000"
}
```

### 3.3 常见错误

| 错误信息 | 原因 |
|----------|------|
| `JSON解析错误: ...` | 请求非合法 JSON |
| `不支持的订阅类型: N` | sub_type 不在 {1,2,3,4} |
| `无效的日期范围或日期格式，期望格式: YYYYMMDD` | 日期为空或格式错误 |
| `无效的股票代码: ...` | 股票代码格式不合法 |
| `未提供有效的股票代码` | stock 列表为空或全部无效 |

---

## 四、Redis 推送频道

| 订阅类型 | 频道格式 | 示例 |
|----------|----------|------|
| 快照 (sub_type=1) | `market:snapshot:{exchange}:{symbol}` | `market:snapshot:SSE:600036` |
| 逐笔 (sub_type=2/3/4) | `market:tick:{exchange}:{symbol}` | `market:tick:SZSE:000001` |

---

## 五、推送消息结构

### 5.1 快照消息（sub_type=1）

```json
{
  "type": "snapshot",
  "timestamp": 1699670400000,
  "seqno": 1,
  "exchange": "SSE",
  "symbol": "600036",
  "data": { ... }
}
```

#### 外层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | str | 固定 `"snapshot"` |
| `timestamp` | int | 毫秒时间戳，由 `trade_datetime` 转换 |
| `seqno` | int | 序列号，从1递增，该股票最后一笔=0 |
| `exchange` | str | 交易所：SSE / SZSE |
| `symbol` | str | 6位股票代码 |
| `data` | object | 快照数据，见下表 |

#### data 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `trade_date` | str | 交易日期 |
| `data_time` | str | 数据时间 |
| `trade_datetime` | str | 交易时间（datetime 序列化为字符串） |
| `last_price` | float | 最新价 |
| `pre_close_price` | float | 昨收价 |
| `open_price` | float | 开盘价 |
| `high_price` | float | 最高价 |
| `low_price` | float | 最低价 |
| `qty` | int | 成交量 |
| `turnover` | float | 成交额 |
| `avg_price` | float | 均价 |
| `trades_count` | int | 成交笔数 |
| `ticker_status` | str | 证券状态 |
| `total_bid_qty` | int | 买方总量 |
| `total_ask_qty` | int | 卖方总量 |
| `bid_price` | float[10] | 十档买价（bid0~bid9） |
| `bid_volume` | int[10] | 十档买量（bid0~bid9） |
| `ask_price` | float[10] | 十档卖价（ask0~ask9） |
| `ask_volume` | int[10] | 十档卖量（ask0~ask9） |

> `security_id` 和 `exchange_id` 不在 data 中推送。

### 5.2 逐笔消息（sub_type=2/3/4）

```json
{
  "type": "tick",
  "sub_type": 2,
  "timestamp": 1699670400000,
  "seqno": 1,
  "exchange": "SSE",
  "symbol": "600036",
  "data": { ... }
}
```

#### 外层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | str | 固定 `"tick"` |
| `sub_type` | int | 2=全量逐笔, 3=逐笔成交, 4=逐笔委托 |
| `timestamp` | int | 毫秒时间戳，由 `trade_datetime` 转换 |
| `seqno` | int | 序列号，从1递增，该股票最后一笔=0 |
| `exchange` | str | 交易所：SSE / SZSE |
| `symbol` | str | 6位股票代码 |
| `data` | object | 逐笔数据，见下表 |

#### data 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `trade_date` | str | 交易日期 |
| `update_time` | str | 更新时间 |
| `trade_datetime` | str | 交易时间 |
| `exchange_id` | int | 交易所ID（1=SSE, 2=SZSE） |
| `channel_no` | int | 通道号 |
| `seq_no` | int | 序列号 |
| `trade2_order1` | int | 成交/委托标志（1=委托, 2=成交） |
| `price` | float | 价格 |
| `volume` | int | 成交量 |
| `trd_money` | float | 成交金额 |
| `ord_side` | str | 委托方向（缺省空字符串） |
| `ord_type` | str | 委托类型（缺省空字符串） |
| `trd_bs_flag` | str | 成交买卖标志（缺省空字符串） |
| `trd_buy_no` | int | 买方订单号 |
| `trd_sell_no` | int | 卖方订单号 |
| `ord_no` | int | 委托号 |
| `biz_index` | int | 业务索引 |
| `trans_flag` | int | 传输标志 |
| `order_trd_volume` | int | 委托成交量 |

> `security_id` 不在 data 中推送。`ord_side`、`ord_type`、`trd_bs_flag` 无值时为空字符串而非 -1。

---

## 六、ClickHouse 数据库表结构

### 6.1 快照表 `snapshot_{YYYYMMDD}`

查询字段（`SNAPSHOT_PUSH_COLUMNS`）：

```
trade_date, data_time, trade_datetime, security_id, exchange_id,
last_price, pre_close_price, open_price, high_price, low_price,
qty, turnover, avg_price, trades_count, ticker_status,
total_bid_qty, total_ask_qty,
bid0_price, bid0_qty, ask0_price, ask0_qty,
bid1_price, bid1_qty, ask1_price, ask1_qty,
... (共10档买价+10档买量+10档卖价+10档卖量)
```

### 6.2 逐笔表 `tick_{YYYYMMDD}`

查询字段（`TICK_PUSH_COLUMNS`）：

```
trade_date, update_time, trade_datetime, exchange_id, channel_no,
seq_no, security_id, trade2_order1, price, volume, trd_money,
ord_side, ord_type, trd_bs_flag, trd_buy_no, trd_sell_no,
ord_no, biz_index, trans_flag, order_trd_volume
```

### 6.3 查询过滤

- 按 `exchange_id` + `security_id` 过滤股票
- 按 `trade_datetime` 排序
- sub_type=3 额外过滤 `trade2_order1 = 2`（成交）
- sub_type=4 额外过滤 `trade2_order1 = 1`（委托）

---

## 七、连接池与并发

| 项目 | 说明 |
|------|------|
| 连接池类 | `ClickHouseConnectionPool` |
| 池大小 | 5 |
| 线程模型 | 每个客户端连接一个线程（daemon） |
| 连接获取 | `get()` 从队列取或新建 |
| 连接归还 | `put()` 归还队列，队列满则 disconnect |
| 服务停止 | `close_all()` 关闭所有池中连接 |

---

## 八、seqno 规则

- 每只股票的消息从 **seqno=1** 开始递增
- 该股票的**最后一笔** seqno=0，表示结束
- 排序：按 (timestamp, symbol, seqno) 排序后推送

---

## 九、空数据处理

当某只股票在指定日期无数据时，生成 **1条空记录** 推送：

### 快照空记录

- 数值字段：`-1`
- 日期/时间/状态字段：空字符串 `""`
- 十档盘口：均为 `-1`

### 逐笔空记录

- 数值字段：`-1`
- 日期/时间字段：空字符串 `""`
- `ord_side`/`ord_type`/`trd_bs_flag`：空字符串 `""`

---

## 十、启动与配置

### 启动命令

```bash
python clickhouse_server.py
```

### 配置项（config/config.ini）

| 配置组 | 关键配置 | 说明 |
|--------|----------|------|
| ClickHouse | host, port, user, password, database | ClickHouse 连接信息 |
| Redis | host, port, db | Redis 连接信息 |
| Backtest | use_pipeline | 是否使用 Redis Pipeline 推送 |

### 启动日志示例

```
============================================================
ClickHouse 数据推送服务 配置信息
============================================================
配置文件: config/config.ini
TCP监听地址: 0.0.0.0:9998
Redis: 127.0.0.1:6379 DB=0
ClickHouse: 127.0.0.1:9000/stock_data
============================================================
```
