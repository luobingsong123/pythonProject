# 策略触发点位K线图WebUI使用说明

## 功能介绍

本WebUI提供以下功能：

1. **策略选择**：从数据库中读取所有已保存的策略名称
2. **股票选择**：选择指定策略下的股票
3. **触发点位展示**：显示该股票在指定策略下的所有触发点位
4. **K线图展示**：显示触发点位前后50个交易日的K线图（可调整）
5. **触发点位详情**：显示触发点位的详细信息（价格、数量、利润等）

## 项目结构

```
webui/
├── app.py              # Flask应用主文件
├── templates/
│   └── index.html     # 前端页面
├── static/             # 静态文件目录（可选）
└── README.md          # 本说明文档
```

## 安装依赖

确保已安装以下Python包：

```bash
pip install flask sqlalchemy pandas pymysql
```

## 启动服务

### 方法1：直接运行

```bash
cd webui
python app.py
```

### 方法2：通过主程序启动

在 `baostock_tool` 目录下：

```python
# 可以在主程序中添加启动WebUI的选项
```

服务启动后，访问 `http://localhost:5000`（具体地址和端口取决于配置文件）

## API接口说明

### 1. 获取所有策略

**接口**：`GET /api/strategies`

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "strategy_name": "CodeBuddyStrategy",
      "stock_count": 10
    }
  ]
}
```

### 2. 获取指定策略的股票列表

**接口**：`GET /api/stocks?strategy_name={strategy_name}`

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "stock_code": "601288",
      "market": "sh",
      "trigger_count": 8,
      "backtest_start_date": "2024-01-01",
      "backtest_end_date": "2024-12-31"
    }
  ]
}
```

### 3. 获取触发点位

**接口**：`GET /api/trigger_points?strategy_name={strategy_name}&stock_code={stock_code}&market={market}`

**响应**：
```json
{
  "success": true,
  "data": {
    "strategy_name": "CodeBuddyStrategy",
    "stock_code": "601288",
    "market": "sh",
    "backtest_start_date": "2024-01-01",
    "backtest_end_date": "2024-12-31",
    "trigger_count": 8,
    "trigger_points": [
      {
        "date": "2024-01-05",
        "trigger_type": "buy",
        "price": 3.52,
        "volume": 1000,
        "commission": 3.52,
        "volume_rank": "20日最低",
        "trigger_volume": 1250000
      }
    ]
  }
}
```

### 4. 获取K线数据

**接口**：`GET /api/kline_data`

**参数**：
- `strategy_name`: 策略名称（必填）
- `stock_code`: 股票代码（必填）
- `market`: 市场类型（必填）
- `trigger_index`: 触发点位索引（必填，从0开始）
- `bars_before`: 前置交易日数（可选，默认50）
- `bars_after`: 后置交易日数（可选，默认50）

**响应**：
```json
{
  "success": true,
  "data": {
    "strategy_name": "CodeBuddyStrategy",
    "stock_code": "601288",
    "market": "SH",
    "trigger_date": "2024-01-05",
    "trigger_type": "buy",
    "trigger_price": 3.52,
    "trigger_index": 50,
    "kline_data": [
      {
        "date": "2023-10-25",
        "open": 3.48,
        "high": 3.50,
        "low": 3.47,
        "close": 3.49,
        "volume": 1250000,
        "amount": 4362500
      }
    ],
    "trigger_info": {
      "date": "2024-01-05",
      "trigger_type": "buy",
      "price": 3.52,
      "volume": 1000,
      "commission": 3.52,
      "volume_rank": "20日最低",
      "trigger_volume": 1250000
    }
  }
}
```

### 5. 获取统计信息

**接口**：`GET /api/statistics`

**响应**：
```json
{
  "success": true,
  "data": {
    "strategy_count": 2,
    "stock_count": 20,
    "total_records": 20,
    "total_triggers": 150,
    "strategy_stats": [
      {
        "strategy_name": "CodeBuddyStrategy",
        "stock_count": 10,
        "total_triggers": 80
      }
    ]
  }
}
```

## 使用流程

1. **启动服务**
   ```bash
   python webui/app.py
   ```

2. **打开浏览器**
   - 访问 `http://localhost:5000`（或配置文件中指定的地址）

3. **选择策略**
   - 从下拉菜单中选择要查看的策略

4. **选择股票**
   - 选择策略后，股票列表会自动加载
   - 选择要查看的股票

5. **查看触发点位**
   - 页面会显示该股票的所有触发点位
   - 买入点位显示为红色，卖出点位显示为绿色

6. **查看K线图**
   - 点击任意触发点位按钮
   - K线图会自动加载，显示该触发点位前后的走势
   - 可以通过滑动条调整显示范围
   - 可以通过下拉菜单选择显示前后30/50/100天

## K线图功能

### 图表元素

1. **K线蜡烛图**：
   - 红色：当日收盘价 >= 开盘价（涨）
   - 绿色：当日收盘价 < 开盘价（跌）

2. **均线**：
   - MA5：5日移动平均线
   - MA10：10日移动平均线
   - MA20：20日移动平均线
   - MA30：30日移动平均线

3. **触发点位标记**：
   - 图钉图标标记触发点位
   - 买入：红色
   - 卖出：绿色

4. **触发价位线**：
   - 虚线标记触发价格
   - 买入：红色
   - 卖出：绿色

5. **成交量柱状图**：
   - 显示每个交易日的成交量
   - 颜色与当日K线对应

### 交互功能

- **鼠标悬停**：显示详细信息
- **缩放**：支持鼠标滚轮缩放和拖拽
- **数据缩放条**：底部滑块调整显示范围
- **响应式**：自动适应窗口大小

## 配置说明

服务配置在 `config/config.ini` 中：

```ini
[webserver]
host = 0.0.0.0
port = 5000
```

## 常见问题

### Q: 如何修改K线图显示的默认天数？

A: 修改 `app.py` 中的默认参数：
```python
bars_before = request.args.get('bars_before', 50, type=int)
bars_after = request.args.get('bars_after', 50, type=int)
```

### Q: 如何添加更多的技术指标？

A: 在 `templates/index.html` 的 `drawKlineChart` 函数中添加新的系列：

```javascript
{
    name: 'MACD',
    type: 'line',
    data: calculateMACD(),
    // ...
}
```

### Q: 如何自定义K线图颜色？

A: 修改 `templates/index.html` 中的 `itemStyle` 配置：

```javascript
itemStyle: {
    color: '#你的颜色',      // 涨
    color0: '#你的颜色',     // 跌
    borderColor: '#你的颜色',
    borderColor0: '#你的颜色'
}
```

### Q: 如何导出K线图数据？

A: 可以在浏览器控制台执行：

```javascript
// 获取当前图表数据
const chart = echarts.getInstanceByDom(document.getElementById('kline-chart'));
const option = chart.getOption();
console.log(option);
```

## 技术栈

- **后端**：Flask
- **前端**：原生JavaScript + ECharts
- **样式**：Tailwind CSS
- **数据库**：MySQL (通过SQLAlchemy)

## 性能优化建议

1. **缓存机制**：对于频繁访问的数据可以添加Redis缓存
2. **分页加载**：触发点位较多时可以分页显示
3. **异步加载**：K线图使用懒加载方式
4. **数据压缩**：API响应使用gzip压缩

## 扩展功能建议

1. **多策略对比**：同时显示多个策略的触发点位
2. **收益统计**：计算和显示每个策略的收益情况
3. **回测报告**：生成完整的回测报告PDF
4. **实盘监控**：接入实时行情，监控策略触发情况
5. **策略回放**：以动画形式回放交易过程

## 注意事项

1. 确保数据库中有策略触发点位数据
2. 确保股票日线数据完整
3. 服务启动前确保配置文件正确
4. 大量数据查询时注意性能

## 许可证

本代码仅供学习研究使用，实盘交易风险自担。
