# tick_server.py vs clickhouse_server.py 完整对比

## 一、服务基础信息

| 对比项 | tick_server.py | clickhouse_server.py |
|--------|---------------|---------------------|
| 监听端口 | 9999 | 9998 |
| 数据源 | MySQL | ClickHouse |
| 查询表 | `level2_3s_{YYYYMMDD}` | `snapshot_{YYYYMMDD}` / `tick_{YYYYMMDD}` |
| 查询服务 | `StockQueryService` | `ClickHouseQueryService` |
| 发布器 | `TickDataPublisher` | `ClickHousePublisher` |
| 连接管理 | `init_db_pool`（数据库连接池） | `ClickHouseConnectionPool`（自实现，基于 queue.Queue） |

## 二、客户端订阅消息格式

### 2.1 共同格式

两个服务接收的 JSON 消息格式**完全一致**，都由 `TickRequest` 类解析：

```json
{
  "sub_type": 1,
  "start_date": "20241111",
  "end_date": "20241112",
  "stock": ["000001", "600001"]
}
```

### 2.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sub_type` | int | 否（默认1） | 订阅类型 |
| `start_date` | str | 是 | 起始日期，格式 YYYYMMDD |
| `end_date` | str | 是 | 结束日期，格式 YYYYMMDD |
| `stock` | str[] | 是 | 股票代码列表，支持 `sh.600000` 或纯代码 `600000` |

### 2.3 sub_type 支持差异

| sub_type | 含义 | tick_server | clickhouse_server |
|----------|------|:-----------:|:-----------------:|
| 1 | 快照 | ✅ | ✅ |
| 2 | 全量逐笔 | ❌ 仅支持1 | ✅ |
| 3 | 逐笔成交 | ❌ 仅支持1 | ✅ |
| 4 | 逐笔委托 | ❌ 仅支持1 | ✅ |

> **注意**：代码中 sub_type=3 过滤 `trade2_order1=2`（成交），sub_type=4 过滤 `trade2_order1=1`（委托）。

### 2.4 股票代码格式（相同）

| 格式 | 示例 | 说明 |
|------|------|------|
| 完整格式 | `sh.600000`、`sz.000001` | 带交易所前缀 |
| 纯代码 | `600000`、`000001` | 自动识别：6开头→sh，0/3开头→sz |

### 2.5 服务端响应格式差异

#### tick_server 成功响应

```json
{
  "success": true,
  "start_date": "20241111",
  "end_date": "20241112",
  "stats": [
    {
      "date": "20241111",
      "items": [{"code": "600036", "count": 4800}]
    }
  ]
}
```

#### clickhouse_server 成功响应

```json
{
  "success": true,
  "sub_type": 1,
  "start_date": "20241111",
  "end_date": "20241112",
  "stats": [
    {
      "date": "20241111",
      "items": [{"code": "600036", "count": 4800}]
    }
  ]
}
```

> **差异**：clickhouse_server 多返回 `sub_type` 字段。

---

## 三、Redis 推送频道

| 推送类型 | tick_server | clickhouse_server |
|----------|:-----------:|:-----------------:|
| 快照频道 | `market:snapshot:{exchange}:{symbol}` | `market:snapshot:{exchange}:{symbol}` |
| 逐笔频道 | ❌ 不存在 | `market:tick:{exchange}:{symbol}` |

> tick_server **只推送 snapshot 频道**，即使数据来源是3秒tick，也转换为snapshot格式。

---

## 四、推送消息结构对比

### 4.1 快照消息（sub_type=1）

#### 消息外层

| 字段 | tick_server | clickhouse_server |
|------|-------------|-------------------|
| `type` | `"snapshot"` | `"snapshot"` |
| `timestamp` | int，MySQL `UNIX` 字段（已是毫秒） | int，ClickHouse `trade_datetime` 转毫秒 |
| `seqno` | 从1递增，最后一笔=0 | 从1递增，最后一笔=0 |
| `exchange` | SSE / SZSE | SSE / SZSE |
| `symbol` | 6位代码 | 6位代码 |
| `data` | `MarketQuote` 对象 | `Dict[str, Any]` |
| `sub_type` | ❌ 无 | ❌ 无 |

#### data 负载字段对比

| 字段 | tick_server | clickhouse_server | 说明 |
|------|:-----------:|:-----------------:|------|
| `trade_date` | ❌ | ✅ | 交易日期 |
| `data_time` | ❌ | ✅ | 数据时间 |
| `trade_datetime` | ❌ | ✅ | 交易时间 |
| `last_price` | ✅ `last_price` | ✅ | 最新价 |
| `pre_close_price` | ❌ | ✅ | 昨收价 |
| `open_price` | ❌ | ✅ | 开盘价 |
| `high_price` | ❌ | ✅ | 最高价 |
| `low_price` | ❌ | ✅ | 最低价 |
| `volume` | ✅ `volume`（手） | ❌ | 总成交量（tick_server特有） |
| `qty` | ❌ | ✅ | 成交量（clickhouse_server） |
| `amount` | ✅ `amount` | ❌ | 总成交额（tick_server特有） |
| `turnover` | ❌ | ✅ | 成交额（clickhouse_server） |
| `avg_price` | ❌ | ✅ | 均价 |
| `trades_count` | ❌ | ✅ | 成交笔数 |
| `ticker_status` | ❌ | ✅ | 证券状态 |
| `total_bid_qty` | ❌ | ✅ | 买方总量 |
| `total_ask_qty` | ❌ | ✅ | 卖方总量 |
| `bid_price` | ✅ **5档** | ✅ **10档** | 买价 |
| `bid_volume` | ✅ **5档** | ✅ **10档** | 买量 |
| `ask_price` | ✅ **5档** | ✅ **10档** | 卖价 |
| `ask_volume` | ✅ **5档** | ✅ **10档** | 卖量 |
| `date` | ✅ YYYYMMDD | ❌ | 日期（tick_server特有） |
| `timestamp` | ✅ 空字符串 `""` | ❌ | 时间（tick_server特有，但为空） |

**关键差异**：
- tick_server：**5档**盘口，字段少（9个），部分字段名不同（`volume`/`amount`）
- clickhouse_server：**10档**盘口，字段丰富（30+个），含开高低收、均价、成交笔数等

### 4.2 逐笔消息（sub_type=2/3/4）

> ⚠️ tick_server **不支持**逐笔推送，以下仅展示 clickhouse_server 的字段。

#### 消息外层

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | str | 固定 `"tick"` |
| `sub_type` | int | 2=全量逐笔, 3=逐笔成交, 4=逐笔委托 |
| `timestamp` | int | 毫秒时间戳 |
| `seqno` | int | 序列号，最后一笔=0 |
| `exchange` | str | SSE / SZSE |
| `symbol` | str | 6位代码 |
| `data` | Dict | 逐笔数据 |

#### data 负载字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `trade_date` | str | 交易日期 |
| `update_time` | str | 更新时间 |
| `trade_datetime` | str | 交易时间 |
| `exchange_id` | str | 交易所ID |
| `channel_no` | int | 通道号 |
| `seq_no` | int | 序列号 |
| `trade2_order1` | int | 成交/委托标志（1=委托, 2=成交） |
| `price` | float | 价格 |
| `volume` | int | 成交量 |
| `trd_money` | float | 成交金额 |
| `ord_side` | str | 委托方向（缺省空） |
| `ord_type` | str | 委托类型（缺省空） |
| `trd_bs_flag` | str | 成交买卖标志（缺省空） |
| `trd_buy_no` | int | 买方订单号 |
| `trd_sell_no` | int | 卖方订单号 |
| `ord_no` | int | 委托号 |
| `biz_index` | int | 业务索引 |
| `trans_flag` | int | 传输标志 |
| `order_trd_volume` | int | 委托成交量 |

---

## 五、数据处理差异

| 维度 | tick_server | clickhouse_server |
|------|-------------|-------------------|
| 数据粒度 | 3秒级快照 | 真正的逐笔数据（tick级别） |
| 排序方式 | 按UNIX时间戳排序（所有股票混排） | 按 (timestamp, symbol, seqno) 排序 |
| 空数据处理 | 生成一整天3秒间隔的全-1数据（约4800条） | 只生成1条空数据 |
| MySQL查询字段丢弃 | 查询了PreClosePrice/OpenPrice等，但转换时大部分被丢弃 | 查询字段即推送字段，无丢弃 |

---

## 六、代码风格差异

| 维度 | tick_server.py | clickhouse_server.py |
|------|---------------|---------------------|
| 日志格式 | f-string | `%s` 格式化（logging最佳实践） |
| 客户端断连处理 | 无特殊处理 | 捕获 `ConnectionResetError`/`BrokenPipeError` |
| 错误处理层次 | 内层+外层 try-catch | 单层 try-catch + finally |
| 响应构建 | 内联 dict | 提取 `_error_response` 静态方法 |
| 服务停止 | 调用 `publisher.close()` | 调用 `conn_pool.close_all()` |

---

## 七、总结

1. **订阅消息格式完全一致**，都使用 `TickRequest` 解析
2. **tick_server 只支持快照(sub_type=1)**，clickhouse_server 支持快照+逐笔(1/2/3/4)
3. **tick_server 的快照是5档**，clickhouse_server 的快照是**10档**且字段更丰富
4. **tick_server 没有真正的逐笔推送**，尽管名字含"Tick"，所有数据都转为snapshot格式
5. **clickhouse_server 多了 `sub_type` 字段**在响应中
6. **空数据处理策略不同**：tick_server 填充全量空数据（~4800条），clickhouse_server 仅1条
