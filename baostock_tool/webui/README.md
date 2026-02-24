# 回测记录查看器

基于 Flask 的 Web 应用，用于查询和展示回测记录数据，支持两种回测框架：

- **time_based**：基于时间的回测汇总展示
- **backtrader**：触发点位和 K 线图展示

## 功能特性

### 1. 基于时间回测（Time Based）

- 策略选择与回测区间查询
- 收益曲线对比（支持多种基准指数：上证指数、深证成指、沪深300、中证1000）
- 策略参数展示
- 每日持仓记录表格
- 回测统计数据（收益率、胜率、最大回撤、夏普比率等）

### 2. 遍历回测（Backtrader）

- 策略与股票选择（支持分页）
- 回测时段展示
- 触发点位详情（买入/卖出日期、价格、盈亏标志）
- K 线图展示（标记买卖点位）

### 3. 数据更新

- 一键更新股票日线数据和 5 分钟线数据
- 实时日志输出

## 目录结构

```
webui/
├── app.py                    # 基础 Flask 应用
├── backtest_viewer.py        # 回测查看器主应用
├── requirements.txt          # Python 依赖
├── README.md                 # 说明文档
├── static/                   # 静态资源
│   ├── css/
│   │   └── backtest_viewer.css   # 样式文件
│   └── js/
│       ├── utils.js              # 通用工具函数
│       ├── tabs.js               # Tab 导航管理
│       ├── time_based_panel.js   # 基于时间回测面板
│       ├── backtrader_panel.js   # 遍历回测面板
│       ├── data_update_panel.js  # 数据更新面板
│       ├── kline_chart.js        # K线图模块
│       └── main.js               # 主入口文件
└── templates/                # 模板文件
    ├── index.html            # 基础页面
    └── backtest_viewer.html  # 回测查看器页面
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行应用

```bash
# 运行回测查看器
python backtest_viewer.py

# 或运行基础应用
python app.py
```

应用启动后访问：http://localhost:5001

## API 接口

### 通用接口

#### 1. 获取策略列表

```
GET /api/strategies?backtest_framework=time_based|backtrader
```

返回：
```json
{
  "success": true,
  "data": ["StrategyA", "StrategyB"]
}
```

### Time Based 接口

#### 2. 获取回测汇总列表

```
GET /api/summary_list?backtest_framework=time_based&strategy=策略名称
```

#### 3. 获取策略参数

```
GET /api/strategy_params?strategy=策略名称&start_date=开始日期&end_date=结束日期
```

#### 4. 获取收益曲线数据

```
GET /api/profit_chart?strategy=策略名称&start_date=开始日期&end_date=结束日期&benchmark=基准指数
```

#### 5. 获取每日记录

```
GET /api/daily_records?strategy=策略名称&start_date=开始日期&end_date=结束日期
```

### Backtrader 接口

#### 6. 获取证券代码列表（支持分页）

```
GET /api/stocks?strategy=策略名称&stock_code=证券代码(可选)&page=1&page_size=13
```

#### 7. 获取回测时段

```
GET /api/backtest_periods?strategy=策略名称&stock_code=证券代码
```

#### 8. 获取触发点位

```
GET /api/trigger_points?strategy=策略名称&stock_code=证券代码&backtest_period=回测时段
```

#### 9. 获取 K 线数据

```
GET /api/kline_data?stock_code=证券代码&start_date=买入日期&sell_date=卖出日期(可选)
```

### 数据更新接口

#### 10. 更新市场数据

```
POST /api/update_market_data
```

流式响应，实时返回更新日志。

## 盈亏标志说明

| 值 | 含义      | 颜色 |
|---|---------|------|
| `1` | 盈利      | 红色 |
| `0` | 平盘（未卖出） | 灰色 |
| `-1` | 亏损      | 绿色 |

## 前端技术栈

- **ECharts 5.4.3**：图表渲染
- **Material Design**：UI 设计风格
- **Google Fonts**：Roboto 字体 + Material Icons

## 代码架构

前端采用模块化架构，各功能模块独立封装：

```javascript
// 模块间通信使用自定义事件
document.dispatchEvent(new CustomEvent('tabChanged', { detail: { tab: 'xxx' } }));
document.addEventListener('loadKline', function(e) { ... });
```

每个模块通过 `window` 对象暴露接口：

```javascript
window.TimeBasedPanel = { init, getCurrentPeriod, getProfitChart, refresh };
window.BacktraderPanel = { init, getCurrentStock, refresh };
window.DataUpdatePanel = { init };
window.KlineChart = { init, load, resize, getChart };
window.Tabs = { init, getCurrent };
window.Utils = { determineMarket, formatNumber, ... };
```
