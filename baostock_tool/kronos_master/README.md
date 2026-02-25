# Kronos Master - A股日线预测模块

基于 Kronos 模型的 A 股日线数据预测服务模块，支持快速移植到其他项目中使用。

## 目录结构

```
kronos_master/
├── kronos_service.py       # 预测服务入口
└── model/
    ├── __init__.py         # 模块导出
    ├── kronos.py           # 核心模型定义 (Kronos, KronosTokenizer, KronosPredictor)
    └── module.py           # 基础神经网络组件
```

## 核心组件

### 服务层

| 类名 | 说明 |
|------|------|
| `KronosPredictorService` | A股日线预测服务，封装数据获取、预测、输出完整流程 |
| `KronosConfig` | 预测配置类 |
| `PredictionResult` | 预测结果数据类 |
| `batch_predict()` | 批量预测辅助函数 |

### 模型层

| 类名 | 说明 |
|------|------|
| `Kronos` | 主预测模型，基于 Transformer 的自回归预测 |
| `KronosTokenizer` | 数据分词器，使用 Binary Spherical Quantization |
| `KronosPredictor` | 预测器封装，提供 `predict()` 和 `predict_batch()` 方法 |
| `BSQuantizer` | 二进制球面量化器 |

## 快速开始

### 环境依赖

```bash
pip install torch pandas baostock matplotlib mplfinance huggingface_hub einops
```

### 单只股票预测

```python
from kronos_service import KronosPredictorService, KronosConfig

# 创建配置（可选）
config = KronosConfig(
    pred_len=5,        # 预测未来5天
    device="cuda:0",   # 使用GPU
    temperature=0.3,   # 温度参数
    sample_count=5     # 采样次数
)

# 创建服务实例
service = KronosPredictorService(config)

# 执行预测
result = service.predict("000001", output_dir="./output")

# 查看结果
print(result.prediction_df)      # 预测数据
print(result.predicted_change_pct)  # 预测涨跌幅
```

### 批量预测

```python
from kronos_service import batch_predict

symbols = ["000001", "000002", "600000"]
results = batch_predict(symbols, output_dir="./output")
```

### 直接使用预测器

```python
from model import Kronos, KronosTokenizer, KronosPredictor

# 加载模型
tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
model = Kronos.from_pretrained("NeoQuasar/Kronos-base")
predictor = KronosPredictor(model, tokenizer, device="cuda:0")

# 执行预测
pred_df = predictor.predict(
    df=historical_data,
    x_timestamp=history_timestamps,
    y_timestamp=future_timestamps,
    pred_len=5,
    T=0.3,
    top_p=0.9,
    sample_count=5
)
```

## 配置参数

### KronosConfig

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `tokenizer_pretrained` | `"NeoQuasar/Kronos-Tokenizer-base"` | Tokenizer 模型路径 |
| `model_pretrained` | `"NeoQuasar/Kronos-base"` | 主模型路径 |
| `device` | `"cpu"` | 运行设备 |
| `max_context` | `512` | 最大上下文长度 |
| `lookback` | `360` | 历史数据回看天数 |
| `pred_len` | `5` | 预测未来天数 |
| `temperature` | `0.3` | 采样温度 |
| `top_p` | `0.1` | 核采样概率 |
| `sample_count` | `5` | 采样次数 |
| `default_limit_rate` | `0.1` | 默认涨跌停幅度 (10%) |
| `gem_limit_rate` | `0.2` | 创业板涨跌停幅度 (20%) |

## 输出说明

### PredictionResult

| 属性 | 类型 | 说明 |
|------|------|------|
| `symbol` | `str` | 股票代码 |
| `stock_name` | `str` | 股票名称 |
| `historical_df` | `DataFrame` | 历史数据 |
| `prediction_df` | `DataFrame` | 预测数据 |
| `combined_df` | `DataFrame` | 合并数据 |
| `last_close` | `float` | 最新收盘价 |
| `predicted_change_pct` | `float` | 预测涨跌幅 |
| `csv_path` | `str` | CSV文件路径 |
| `chart_path` | `str` | 折线图路径 |
| `candlestick_path` | `str` | K线图路径 |

### 生成的文件

- `pred_{code}_{name}_data.csv` - 历史与预测合并数据
- `pred_{code}_{name}_chart.png` - 收盘价折线图
- `pred_{code}_{name}_candlestick.png` - K线图

## 模型架构

Kronos 模型采用分层 Token 化 + 自回归预测的架构：

1. **Tokenizer**: 将连续的价格数据量化为离散 Token
   - 使用 Binary Spherical Quantization (BSQ)
   - 分为 s1 (粗粒度) 和 s2 (细粒度) 两级 Token

2. **Kronos Model**: 基于 Transformer 的自回归预测
   - 层次化嵌入 (Hierarchical Embedding)
   - 旋转位置编码 (RoPE)
   - 依赖感知层 (Dependency-aware Layer)

3. **Decoder**: 将预测 Token 解码为价格数据

## 注意事项

1. 模型首次加载时会从 HuggingFace Hub 下载，需要网络连接
2. 股票数据通过 baostock 获取，需要有稳定的网络环境
3. 预测结果仅供参考，不构成投资建议
4. 创业板股票 (代码以 30 开头) 自动应用 20% 涨跌停限制

## 许可证

请遵循模型和数据源的相关许可协议。
