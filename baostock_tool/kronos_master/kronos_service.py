# kronos_service.py - 建议创建这个新文件

# -*- coding: utf-8 -*-
"""
KronosPredictorService - A股日线预测服务

可独立移植到其他项目中使用的预测服务类
"""

import os
import sys

# 设置 Hugging Face 国内镜像源（需在导入 transformers 前设置）
if 'HF_ENDPOINT' not in os.environ:
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 获取模型目录的绝对路径
_MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')

import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# 导入配置模块
try:
    import baostock_tool.config as db_config
    CONFIG_AVAILABLE = True
except ImportError:
    # 尝试从父目录导入
    import sys
    config_path = os.path.dirname(os.path.dirname(__file__))
    if config_path not in sys.path:
        sys.path.insert(0, config_path)
    import config as db_config
    CONFIG_AVAILABLE = True

# 从本地 model 模块导入 Kronos 相关类
KRONOS_AVAILABLE = False
KronosTokenizer = None
Kronos = None
KronosPredictor = None

# 方式1: 尝试相对导入（当作为包使用时）
try:
    from .model import Kronos, KronosTokenizer, KronosPredictor
    KRONOS_AVAILABLE = True
    print("✅ Kronos模块加载成功 (from .model)")
except ImportError:
    # 方式2: 尝试绝对导入
    try:
        from baostock_tool.kronos_master.model import Kronos, KronosTokenizer, KronosPredictor
        KRONOS_AVAILABLE = True
        print("✅ Kronos模块加载成功 (from baostock_tool.kronos_master.model)")
    except ImportError:
        # 方式3: 添加项目根目录到 sys.path 后再导入
        try:
            # 获取项目根目录（向上两级）
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            from baostock_tool.kronos_master.model import Kronos, KronosTokenizer, KronosPredictor
            KRONOS_AVAILABLE = True
            print(f"✅ Kronos模块加载成功 (from {project_root})")
        except ImportError as e3:
            print(f"⚠️ Kronos模块未安装: {e3}")

# mplfinance 可选导入
try:
    from mplfinance.original_flavor import candlestick_ohlc
    MPLFINANCE_AVAILABLE = True
except ImportError:
    MPLFINANCE_AVAILABLE = False
    print("⚠️ mplfinance未安装，K线图绘制功能不可用")
    print("   安装方法: pip install mplfinance")


@dataclass
class KronosConfig:
    """Kronos 预测配置"""
    # 模型配置（默认使用本地模型）
    tokenizer_pretrained: str = field(
        default_factory=lambda: os.path.join(_MODELS_DIR, 'Kronos-Tokenizer-base')
    )
    model_pretrained: str = field(
        default_factory=lambda: os.path.join(_MODELS_DIR, 'Kronos-small')
    )
    device: str = "cpu"
    max_context: int = 512

    # 预测参数
    lookback: int = 360  # 历史数据回看天数
    pred_len: int = 5  # 预测未来天数
    temperature: float = 0.3  # 温度参数
    top_p: float = 0.1  # 核采样概率
    sample_count: int = 5  # 采样次数

    # 涨跌停配置
    default_limit_rate: float = 0.1  # 默认涨跌停幅度 10%
    gem_limit_rate: float = 0.2  # 创业板涨跌停幅度 20%


@dataclass
class PredictionResult:
    """预测结果"""
    symbol: str
    stock_name: str
    historical_df: pd.DataFrame
    prediction_df: pd.DataFrame
    combined_df: pd.DataFrame
    last_close: float
    predicted_change_pct: float

    # 可选输出路径
    csv_path: Optional[str] = None
    chart_path: Optional[str] = None
    candlestick_path: Optional[str] = None


class KronosPredictorService:
    """
    A股日线预测服务

    使用示例:
        >>> config = KronosConfig(pred_len=10, device="cuda:0")
        >>> service = KronosPredictorService(config)
        >>> result = service.predict("000001")
        >>> print(result.prediction_df)
    """

    def __init__(self, config: Optional[KronosConfig] = None):
        """
        初始化预测服务

        Args:
            config: 配置对象，为 None 时使用默认配置
        """
        self.config = config or KronosConfig()
        self._model = None
        self._tokenizer = None
        self._predictor = None
        self._stock_name_cache = {}  # 股票名称缓存

        # 初始化数据库连接（使用配置文件）
        if not CONFIG_AVAILABLE:
            raise RuntimeError(
                "配置模块未找到。请确保 baostock_tool/config.py 存在"
            )
        db_config_ = db_config.get_db_config()
        db_url = URL.create(
            drivername="mysql+pymysql",
            username=db_config_["user"],
            password=db_config_["password"],
            host=db_config_["host"],
            port=db_config_["port"],
            database=db_config_["database"]
        )
        self._engine = create_engine(db_url)
        print(f"✅ 数据库连接已建立: {db_config_['host']}:{db_config_['port']}/{db_config_['database']}")

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

    def _ensure_model_loaded(self):
        """懒加载模型"""
        if self._predictor is not None:
            return

        if not KRONOS_AVAILABLE:
            raise RuntimeError(
                "Kronos模块未安装。请安装: pip install kronos-stock\n"
                "或确保 kronos_stock 目录在正确路径下"
            )

        print(f"🚀 Loading Kronos model...")

        try:
            self._tokenizer = KronosTokenizer.from_pretrained(
                self.config.tokenizer_pretrained
            )
            self._model = Kronos.from_pretrained(
                self.config.model_pretrained
            )
        except Exception as e:
            print(f"⚠️ Failed to load from hub: {e}")
            raise RuntimeError(f"模型加载失败: {e}")

        self._predictor = KronosPredictor(
            self._model,
            self._tokenizer,
            device=self.config.device,
            max_context=self.config.max_context
        )
        print(f"✅ Model loaded on {self.config.device}")

    def get_stock_name(self, symbol: str) -> str:
        """从数据库获取股票名称"""
        market, code_int = self._parse_symbol(symbol)
        cache_key = f"{market}.{code_int}"

        if cache_key in self._stock_name_cache:
            return self._stock_name_cache[cache_key]

        try:
            query = f"""
            SELECT name FROM stock_basic_info
            WHERE market = '{market}' AND code_int = {code_int}
            LIMIT 1
            """
            df = pd.read_sql(query, self._engine)
            if not df.empty:
                stock_name = df.iloc[0]['name']
            else:
                stock_name = "Unknown"
            self._stock_name_cache[cache_key] = stock_name
            return stock_name
        except Exception as e:
            print(f"⚠️ Failed to get stock name: {e}")
            return "Unknown"

    def _parse_symbol(self, symbol: str) -> Tuple[str, int]:
        """解析股票代码，返回 (market, code_int)"""
        if symbol.startswith(('sh.', 'sz.')):
            market, code = symbol.split('.')
            return market, int(code)
        if symbol.startswith(('00', '30')):
            return 'sz', int(symbol)
        if symbol.startswith(('60', '688')):
            return 'sh', int(symbol)
        return 'sz', int(symbol)

    def load_data(self, symbol: str) -> pd.DataFrame:
        """从数据库获取股票历史数据"""
        market, code_int = self._parse_symbol(symbol)
        print(f"📥 Fetching {market}.{code_int} daily data from database...")

        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        start_date = (
            datetime.datetime.now() - datetime.timedelta(days=self.config.lookback)
        ).strftime('%Y-%m-%d')

        try:
            query = f"""
            SELECT date, open, high, low, close, volume, amount
            FROM stock_daily_data
            WHERE market = '{market}'
              AND code_int = {code_int}
              AND frequency = 'd'
              AND date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY date
            """
            df = pd.read_sql(query, self._engine)

            if df is None or df.empty:
                raise RuntimeError(f"No data found for {market}.{code_int}")

            # 数据清洗
            df = self._clean_data(df)
            return df

        except Exception as e:
            raise RuntimeError(f"Failed to fetch data for {symbol}: {e}")

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        numeric_cols = ["open", "high", "low", "close", "volume", "amount"]
        for col in numeric_cols:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .replace({"--": None, "": None})
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # 修复开盘价
        open_bad = (df["open"] == 0) | (df["open"].isna())
        if open_bad.any():
            df.loc[open_bad, "open"] = df["close"].shift(1)
            df["open"].fillna(df["close"], inplace=True)

        # 修复成交额
        if df["amount"].isna().all() or (df["amount"] == 0).all():
            df["amount"] = df["close"] * df["volume"]

        df = df.dropna()
        return df

    def _prepare_inputs(
            self,
            df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """准备模型输入"""
        x_df = df.iloc[-self.config.lookback:][
            ["open", "high", "low", "close", "volume", "amount"]
        ]
        x_timestamp = df.iloc[-self.config.lookback:]["date"]

        y_timestamp = pd.bdate_range(
            start=df["date"].iloc[-1] + pd.Timedelta(days=1),
            periods=self.config.pred_len
        )

        return x_df, pd.Series(x_timestamp), pd.Series(y_timestamp)

    def _apply_price_limits(
            self,
            pred_df: pd.DataFrame,
            last_close: float,
            limit_rate: float
    ) -> pd.DataFrame:
        """应用涨跌停限制"""
        pred_df = pred_df.reset_index(drop=True)
        cols = ["open", "high", "low", "close"]
        pred_df[cols] = pred_df[cols].astype("float64")

        for i in range(len(pred_df)):
            limit_up = last_close * (1 + limit_rate)
            limit_down = last_close * (1 - limit_rate)

            for col in cols:
                value = pred_df.at[i, col]
                if pd.notna(value):
                    pred_df.at[i, col] = float(
                        max(min(value, limit_up), limit_down)
                    )

            last_close = float(pred_df.at[i, "close"])

        return pred_df

    def predict(
            self,
            symbol: str,
            output_dir: Optional[str] = None,
            save_csv: bool = True,
            save_chart: bool = True
    ) -> PredictionResult:
        """
        执行预测

        Args:
            symbol: 股票代码
            output_dir: 输出目录，为 None 时不保存文件
            save_csv: 是否保存 CSV
            save_chart: 是否保存图表

        Returns:
            PredictionResult: 预测结果对象
        """
        # 确保模型已加载
        self._ensure_model_loaded()

        # 解析股票代码
        market, code_int = self._parse_symbol(symbol)
        formatted_symbol = f"{market}.{code_int}"

        # 获取股票名称
        stock_name = self.get_stock_name(symbol)

        # 加载数据
        df = self.load_data(symbol)

        # 准备输入
        x_df, x_timestamp, y_timestamp = self._prepare_inputs(df)

        # 生成预测
        print(f"🔮 Generating predictions for {formatted_symbol}...")
        pred_df = self._predictor.predict(
            df=x_df,
            x_timestamp=x_timestamp,
            y_timestamp=y_timestamp,
            pred_len=self.config.pred_len,
            T=self.config.temperature,
            top_p=self.config.top_p,
            sample_count=self.config.sample_count,
        )
        pred_df["date"] = y_timestamp.values

        # 应用涨跌停限制
        last_close = df["close"].iloc[-1]
        limit_rate = (
            self.config.gem_limit_rate
            if market == 'sz' and str(code_int).startswith('30')
            else self.config.default_limit_rate
        )
        pred_df = self._apply_price_limits(pred_df, last_close, limit_rate)

        # 合并结果
        combined_df = pd.concat([
            df[["date", "open", "high", "low", "close", "volume", "amount"]],
            pred_df[["date", "open", "high", "low", "close", "volume", "amount"]]
        ]).reset_index(drop=True)

        # 计算涨跌幅
        pred_change_pct = (
                (pred_df['close'].iloc[-1] - last_close) / last_close * 100
        )

        # 创建结果对象
        result = PredictionResult(
            symbol=formatted_symbol,
            stock_name=stock_name,
            historical_df=df,
            prediction_df=pred_df,
            combined_df=combined_df,
            last_close=last_close,
            predicted_change_pct=pred_change_pct
        )

        # 保存文件
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            self._save_outputs(result, output_dir, save_csv, save_chart)

        return result

    def _save_outputs(
            self,
            result: PredictionResult,
            output_dir: str,
            save_csv: bool,
            save_chart: bool
    ):
        """保存输出文件"""
        safe_name = result.symbol.replace('.', '_')

        if save_csv:
            csv_path = os.path.join(
                output_dir,
                f"pred_{safe_name}_{result.stock_name}_data.csv"
            )
            result.combined_df.to_csv(csv_path, index=False)
            result.csv_path = csv_path
            print(f"✅ CSV saved: {csv_path}")

        if save_chart:
            # 折线图
            chart_path = os.path.join(
                output_dir,
                f"pred_{safe_name}_{result.stock_name}_chart.png"
            )
            self._plot_line_chart(
                result.historical_df,
                result.prediction_df,
                result.symbol,
                result.stock_name,
                chart_path
            )
            result.chart_path = chart_path

            # K线图
            candle_path = os.path.join(
                output_dir,
                f"pred_{safe_name}_{result.stock_name}_candlestick.png"
            )
            self._plot_candlestick(
                result.historical_df,
                result.prediction_df,
                result.symbol,
                result.stock_name,
                candle_path
            )
            result.candlestick_path = candle_path

    def _plot_line_chart(
            self,
            df_hist: pd.DataFrame,
            df_pred: pd.DataFrame,
            symbol: str,
            stock_name: str,
            save_path: str
    ):
        """绘制折线图"""
        plt.figure(figsize=(12, 6))

        plt.plot(
            df_hist["date"], df_hist["close"],
            label="历史数据", color="blue", linewidth=1.5
        )
        plt.plot(
            df_pred["date"], df_pred["close"],
            label="预测数据", color="red", linestyle="--", linewidth=2
        )

        plt.axvline(
            x=df_hist["date"].iloc[-1],
            color='gray', linestyle=':', alpha=0.7
        )

        plt.title(f"Kronos 股票价格预测 - {symbol} {stock_name}")
        plt.xlabel("日期")
        plt.ylabel("收盘价 (元)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"📊 Chart saved: {save_path}")

    def _plot_candlestick(
            self,
            df_hist: pd.DataFrame,
            df_pred: pd.DataFrame,
            symbol: str,
            stock_name: str,
            save_path: str
    ):
        """绘制K线图"""
        if not MPLFINANCE_AVAILABLE:
            print("⚠️ mplfinance未安装，跳过K线图绘制")
            return

        hist_display = df_hist.tail(5)
        pred_display = df_pred

        combined = pd.concat([hist_display, pred_display]).sort_values('date')
        combined['index'] = range(len(combined))

        ohlc = [
            (row['index'], row['open'], row['high'], row['low'], row['close'])
            for _, row in combined.iterrows()
        ]

        fig, ax = plt.subplots(figsize=(16, 8))
        candlestick_ohlc(
            ax, ohlc, width=0.6,
            colorup='red', colordown='green', alpha=0.8
        )

        ax.set_xticks(combined['index'])
        ax.set_xticklabels(
            combined['date'].dt.strftime('%Y-%m-%d'),
            rotation=45
        )

        plt.title(f"Kronos股票价格预测 - {symbol}-{stock_name}")
        plt.xlabel("日期")
        plt.ylabel("收盘价 (元)")
        plt.tight_layout()

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"📊 Candlestick saved: {save_path}")


# ============================================
# 批量预测辅助函数
# ============================================
def batch_predict(
        symbols: List[str],
        output_dir: str,
        config: Optional[KronosConfig] = None,
        report_path: Optional[str] = None
) -> List[PredictionResult]:
    """
    批量预测多只股票

    Args:
        symbols: 股票代码列表
        output_dir: 输出目录
        config: 配置对象
        report_path: 报告文件路径，为 None 时自动生成

    Returns:
        预测结果列表
    """
    service = KronosPredictorService(config)
    results = []

    # 创建报告文件
    if report_path is None:
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        report_path = os.path.join(output_dir, f"{date_str}_report.csv")

    os.makedirs(os.path.dirname(report_path) or '.', exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("code,name,last_close,pred_close_max,change_pct,pred_days\n")

    for symbol in symbols:
        try:
            result = service.predict(symbol, output_dir)
            results.append(result)

            # 追加报告
            with open(report_path, "a", encoding="utf-8") as f:
                f.write(
                    f"{result.symbol},{result.stock_name},"
                    f"{result.last_close:.2f},"
                    f"{result.prediction_df['close'].max():.2f},"
                    f"{result.predicted_change_pct:+.2f},"
                    f"{len(result.prediction_df)}\n"
                )
        except Exception as e:
            print(f"❌ Failed to predict {symbol}: {e}")

    return results


# ============================================
# 主函数 - 用于命令行直接执行预测
# ============================================
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Kronos股票预测工具')
    parser.add_argument('symbol', nargs='?', default='000001', 
                        help='股票代码（默认: 000001）')
    parser.add_argument('--lookback', type=int, default=60, 
                        help='历史数据天数（默认: 60）')
    parser.add_argument('--pred-days', type=int, default=5, 
                        help='预测天数（默认: 5）')
    parser.add_argument('--temperature', type=float, default=0.5, 
                        help='温度参数（默认: 0.5）')
    parser.add_argument('--top-p', type=float, default=0.5, 
                        help='采样概率（默认: 0.5）')
    parser.add_argument('--sample-count', type=int, default=5, 
                        help='采样次数（默认: 5）')
    parser.add_argument('--output-dir', type=str, default=None, 
                        help='输出目录（默认: 不保存文件）')
    parser.add_argument('--device', type=str, default='cpu', 
                        choices=['cpu', 'cuda', 'cuda:0', 'cuda:1'],
                        help='计算设备（默认: cpu）')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Kronos 股票预测工具")
    print("=" * 50)
    print(f"股票代码: {args.symbol}")
    print(f"历史天数: {args.lookback}")
    print(f"预测天数: {args.pred_days}")
    print(f"温度参数: {args.temperature}")
    print(f"采样概率: {args.top_p}")
    print(f"采样次数: {args.sample_count}")
    print(f"计算设备: {args.device}")
    print("=" * 50)
    
    # 检查 Kronos 模块是否可用
    if not KRONOS_AVAILABLE:
        print("\n❌ 错误: Kronos模块未安装!")
        print("\n安装方法:")
        print("  pip install kronos-stock")
        print("\n或者克隆项目到当前目录:")
        print("  git clone https://github.com/xxx/kronos_stock.git")
        sys.exit(1)
    
    try:
        # 创建配置
        config = KronosConfig(
            lookback=args.lookback,
            pred_len=args.pred_days,
            temperature=args.temperature,
            top_p=args.top_p,
            sample_count=args.sample_count,
            device=args.device
        )
        
        # 创建服务
        service = KronosPredictorService(config)
        
        # 执行预测
        result = service.predict(
            args.symbol,
            output_dir=args.output_dir,
            save_csv=args.output_dir is not None,
            save_chart=args.output_dir is not None
        )
        
        # 打印结果
        print("\n" + "=" * 50)
        print("预测结果")
        print("=" * 50)
        print(f"股票: {result.symbol} {result.stock_name}")
        print(f"最新收盘价: {result.last_close:.2f}")
        print(f"预测涨跌幅: {result.predicted_change_pct:+.2f}%")
        print(f"\n预测数据:")
        print(result.prediction_df[['date', 'open', 'high', 'low', 'close']].to_string(index=False))
        
        if args.output_dir:
            print(f"\n✅ 输出文件已保存到: {args.output_dir}")
        
    except Exception as e:
        print(f"\n❌ 预测失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
