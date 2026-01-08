# 策略触发点位查询系统

基于 Flask 的 Web 应用，用于查询和展示策略触发点位数据。

## 功能特性

1. **策略选择**：下拉框选择策略名称
2. **证券代码搜索**：输入证券代码精确查询，留空则查询该策略下所有证券
3. **回测时段展示**：点击证券代码后显示该证券的所有回测时段
4. **触发点位详情**：展开回测时段后显示所有触发点位，包括买入日期和盈亏标志

## 目录结构

```
webui/
├── app.py              # Flask 应用主文件
├── requirements.txt    # Python 依赖
└── templates/
    └── index.html      # 前端页面
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行应用

```bash
python app.py
```

应用启动后访问：http://localhost:5001

## API 接口

### 1. 获取策略列表

```
GET /api/strategies
```

返回：
```json
{
  "success": true,
  "data": ["StrategyA", "StrategyB"]
}
```

### 2. 获取证券代码列表

```
GET /api/stocks?strategy=策略名称&stock_code=证券代码(可选)
```

返回：
```json
{
  "success": true,
  "data": ["sh.601288", "sz.000001"]
}
```

### 3. 获取回测时段

```
GET /api/backtest_periods?strategy=策略名称&stock_code=证券代码
```

返回：
```json
{
  "success": true,
  "data": ["2024-01-01至2024-12-31"]
}
```

### 4. 获取触发点位

```
GET /api/trigger_points?strategy=策略名称&stock_code=证券代码&backtest_period=回测时段
```

返回：
```json
{
  "success": true,
  "data": [
    {
      "key": "触发点位1",
      "buy_date": "2024-01-05",
      "sell_date": "2024-01-08",
      "profit_flag": 1
    }
  ]
}
```

## 盈亏标志说明

- `1` = 盈利（绿色标识）
- `0` = 平盘（黄色标识）
- `-1` = 亏损（红色标识）
