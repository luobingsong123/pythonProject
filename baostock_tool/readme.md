# Baostock Tool - 股票数据采集与回测工具

基于 Baostock 的股票数据采集、技术指标计算与策略回测工具集。

## 主要功能

### 1. 数据采集
- 从 Baostock 获取 A 股日线/分钟线数据
- 支持增量更新与全量更新
- 自动存储至 MySQL 数据库

### 2. 策略回测
- **时间遍历回测**：按交易日顺序遍历，支持多股票同时回测
- **触发点位回测**：记录买卖点位，可视化 K 线展示
- 支持自定义策略模块化替换
- 支持手续费、滑点、仓位控制等配置

### 3. Web 可视化
- Flask Web 应用，查看回测结果
- 收益曲线对比（支持多基准指数）
- K 线图展示买卖点位
- 策略参数与统计数据展示

## 目录结构

```
baostock_tool/
├── config/                     # 配置文件目录
│   └── config.ini              # 数据库、日志、Web服务配置
├── database_schema/            # 数据库相关
│   ├── backtest_batch_summary.sql
│   ├── strategy_trigger_points.sql
│   └── strategy_trigger_db.py  # 触发点位数据库操作
├── utils/                      # 工具模块
│   ├── strategies/             # 策略模块
│   ├── data_loader/            # 数据加载器
│   ├── backtest_engine/        # 回测引擎
│   └── logger_utils/           # 日志工具
├── webui/                      # Web 界面
│   ├── app.py                  # Flask 应用入口
│   ├── backtest_viewer.py      # 回测查看器
│   └── templates/              # HTML 模板
├── get_baostock_data.py        # 数据采集主程序
├── get_baostock_data_update.py # 数据增量更新
├── backtest_time_based_standard.py  # 时间遍历回测
├── update_market_data.py       # 市场数据更新
├── stock_indicator_calculator.py    # 技术指标计算
└── config.py                   # 配置读取模块
```

## 安装依赖

```bash
pip install baostock pandas pandas_ta pymysql sqlalchemy flask
```

## 配置

编辑 `config/config.ini`：

```ini
[database]
host = localhost
port = 3306
username = root
password = your_password
database = stock_data

[logging]
level = INFO
log_dir = ./logs

[webserver]
host = 0.0.0.0
port = 5001

[backtradedate]
start_date = 2024-01-01
end_date = 2024-12-31
frequency = d
```

## 快速开始

### 1. 数据采集
```bash
python get_baostock_data.py
```

### 2. 运行回测
```bash
python backtest_time_based_standard.py
```

### 3. 启动 Web 界面
```bash
cd webui
python app.py
```
访问 http://localhost:5001

## 技术指标

支持常用技术指标计算：
- MA/EMA/SMA 移动平均线
- MACD 指标
- RSI 相对强弱指标
- KDJ 随机指标
- 布林带
- 更多指标见 [MyTT 轻量化指标库](https://github.com/mpquant/MyTT)

## 数据库表结构

主要数据表：
- `stock_daily_data` - 日线数据
- `backtest_batch_summary` - 回测汇总
- `strategy_trigger_points` - 策略触发点位

详细表结构见 `database_schema/` 目录。

## 注意事项

- 本工具仅用于回测研究，实盘使用风险自担
- Baostock 登录需要在交易时间段或使用延迟数据
- 建议定期更新数据以保证回测准确性



