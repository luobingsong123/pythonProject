"""
数据库读取器

从 MySQL 读取两类数据：
  1. 行情快照数据  —— stock_daily_data 表（模拟快照推送）
  2. 选股结果数据  —— stock_basic_info + stock_daily_data 联合查询（构建股池消息）

说明：
  当前项目数据库存的是 日线历史数据，不是实时 tick。
  本模块以"最新一个交易日的日线数据"模拟行情快照，
  实盘接入实时行情源后，只需替换 read_latest_snapshots() 的实现即可，
  其余 Transformer / Publisher / Service 层无需改动。
"""

from typing import Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

import config
from utils.logger_utils import setup_logger

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"],
)

# 市场代码映射: MySQL market 字段 -> 交易所代码（用于 Redis 通道命名）
_MARKET_TO_EXCHANGE = {
    "sh": "SSE",    # 上海证券交易所
    "sz": "SZSE",   # 深圳证券交易所
    "bj": "BSE",    # 北京证券交易所
}


class DbReader:
    """MySQL 数据读取器"""

    def __init__(self):
        self._engine = self._create_engine()
        logger.info("DbReader 初始化完成")

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _create_engine():
        db_cfg = config.get_db_config()
        url = URL.create(
            drivername="mysql+pymysql",
            username=db_cfg["user"],
            password=db_cfg["password"],
            host=db_cfg["host"],
            port=db_cfg["port"],
            database=db_cfg["database"],
        )
        return create_engine(url, pool_pre_ping=True, pool_recycle=3600)

    @staticmethod
    def market_to_exchange(market: str) -> str:
        """将 MySQL market 字段转换为交易所代码"""
        return _MARKET_TO_EXCHANGE.get(market.lower(), market.upper())

    # ------------------------------------------------------------------
    # 4.1 行情快照数据
    # ------------------------------------------------------------------

    def read_latest_snapshots(
        self,
        trade_date: Optional[str] = None,
        market: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        读取最新交易日的日线行情（模拟快照）

        每行对应一只股票的"快照"，包含：
          market, code_int, date, open, high, low, close,
          volume, amount, pctChg, peTTM, psTTM, pcfNcfTTM, pbMRQ

        Args:
            trade_date: 指定交易日 (YYYY-MM-DD)；不传则自动取最新交易日
            market:     限定市场，"sh"/"sz"；不传则全市场

        Returns:
            DataFrame, 每行一条快照记录
        """
        # 1. 确定目标日期
        if trade_date is None:
            trade_date = self._get_latest_trade_date()
            if trade_date is None:
                logger.warning("未能获取最新交易日，跳过本次快照读取")
                return pd.DataFrame()

        logger.info(f"读取行情快照: trade_date={trade_date}, market={market or '全市场'}")

        # 2. 构建查询
        market_filter = ""
        params: dict = {"trade_date": trade_date}
        if market:
            market_filter = "AND d.market = :market"
            params["market"] = market

        sql = f"""
            SELECT
                d.market,
                d.code_int,
                b.name,
                d.date,
                d.open,
                d.high,
                d.low,
                d.close,
                d.volume,
                d.amount,
                d.pctChg,
                d.peTTM,
                d.psTTM,
                d.pcfNcfTTM,
                d.pbMRQ
            FROM stock_daily_data d
            LEFT JOIN stock_basic_info b
                   ON d.market = b.market AND d.code_int = b.code_int
            WHERE d.date = :trade_date
              AND d.frequency = 'd'
              {market_filter}
            ORDER BY d.market, d.code_int
        """

        try:
            df = pd.read_sql(text(sql), self._engine, params=params)
            logger.info(f"行情快照读取完成: {len(df)} 条记录 @ {trade_date}")
            return df
        except Exception as e:
            logger.error(f"行情快照读取失败: {e}")
            return pd.DataFrame()

    def _get_latest_trade_date(self) -> Optional[str]:
        """从 stock_daily_data 获取最新的交易日期"""
        sql = "SELECT MAX(date) AS latest_date FROM stock_daily_data WHERE frequency = 'd'"
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(sql)).fetchone()
            if result and result[0]:
                return str(result[0])
            return None
        except Exception as e:
            logger.error(f"获取最新交易日失败: {e}")
            return None

    # ------------------------------------------------------------------
    # 4.2 选股股池数据
    # ------------------------------------------------------------------

    def read_stock_selection(
        self,
        trade_date: str,
        strategy_id: str = "MA10_BREAKTHROUGH",
        lookback_days: int = 10,
    ) -> pd.DataFrame:
        """
        读取选股所需的基础数据（供 Transformer 构建股池消息）

        查询逻辑：
          - 取 trade_date 当日所有股票的行情
          - 同时关联近期数据，计算 MA5/MA10/MA20/昨收 等技术指标
          - 关联 stock_basic_info 获取名称、PE、PB 等基本面

        Args:
            trade_date:    选股日期，格式 YYYY-MM-DD
            strategy_id:   策略标识（写入消息头，不影响查询逻辑）
            lookback_days: 向前取多少天历史，用于均线计算（默认 10 天足够 MA10）

        Returns:
            DataFrame，每行一只股票，包含当日行情 + 近期历史
        """
        logger.info(f"读取选股数据: trade_date={trade_date}, strategy={strategy_id}")

        # --- 当日快照 ---
        snapshot_sql = """
            SELECT
                d.market,
                d.code_int,
                b.name,
                d.date,
                d.open,
                d.high,
                d.low,
                d.close    AS last_price,
                d.volume,
                d.amount,
                d.pctChg,
                d.peTTM    AS pe,
                d.pbMRQ    AS pb
            FROM stock_daily_data d
            LEFT JOIN stock_basic_info b
                   ON d.market = b.market AND d.code_int = b.code_int
            WHERE d.date = :trade_date
              AND d.frequency = 'd'
            ORDER BY d.market, d.code_int
        """

        # --- 近期历史（用于均线计算） ---
        history_sql = """
            SELECT
                market,
                code_int,
                date,
                close,
                volume
            FROM stock_daily_data
            WHERE date <= :trade_date
              AND date >= DATE_SUB(:trade_date, INTERVAL :lookback_days DAY)
              AND frequency = 'd'
            ORDER BY market, code_int, date
        """

        try:
            df_today = pd.read_sql(
                text(snapshot_sql), self._engine,
                params={"trade_date": trade_date}
            )
            df_history = pd.read_sql(
                text(history_sql), self._engine,
                params={"trade_date": trade_date, "lookback_days": lookback_days}
            )
        except Exception as e:
            logger.error(f"选股数据读取失败: {e}")
            return pd.DataFrame()

        if df_today.empty:
            logger.warning(f"trade_date={trade_date} 无行情数据")
            return pd.DataFrame()

        # --- 合并均线指标 ---
        df_today = self._attach_ma_indicators(df_today, df_history)

        logger.info(f"选股数据读取完成: {len(df_today)} 只股票 @ {trade_date}")
        return df_today

    @staticmethod
    def _attach_ma_indicators(
        df_today: pd.DataFrame,
        df_history: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        将历史数据中计算出的 MA5/MA10/MA20/vol_ma5/vol_ma10/prev_close
        合并回当日快照 DataFrame

        Returns:
            合并后的 df_today（新增多个指标列）
        """
        if df_history.empty:
            return df_today

        df_history["date"] = pd.to_datetime(df_history["date"])
        records = []

        for (market, code_int), grp in df_history.groupby(["market", "code_int"]):
            grp = grp.sort_values("date")
            closes = grp["close"].values
            volumes = grp["volume"].values

            def _ma(arr, n):
                return float(arr[-n:].mean()) if len(arr) >= n else None

            # 昨收 = 今天之前最后一天的收盘
            prev_close = float(closes[-2]) if len(closes) >= 2 else None
            # 近 5 日最高收盘
            ma5_high = float(closes[-5:].max()) if len(closes) >= 1 else None

            records.append({
                "market": market,
                "code_int": code_int,
                "prev_close": prev_close,
                "ma5_high": ma5_high,
                "ma5": _ma(closes, 5),
                "ma10": _ma(closes, 10),
                "ma20": _ma(closes, 20),
                "vol_ma5": _ma(volumes, 5),
                "vol_ma10": _ma(volumes, 10),
            })

        df_ma = pd.DataFrame(records)
        df_merged = df_today.merge(df_ma, on=["market", "code_int"], how="left")
        return df_merged

    def read_minute_volume_5d(
        self,
        market: str,
        code_int: int,
        end_date: str,
        days: int = 5,
    ) -> list:
        """
        读取指定股票近 N 日的每 5 分钟成交量（若有分钟数据表则查；否则返回空列表）

        注：当前项目只有日线数据表（stock_daily_data），无分钟线表。
            此方法预留接口，实盘接入分钟线数据后按实际表名填充 SQL。

        Returns:
            list of dict: [{"time": "09:35", "volume": 1234}, ...]
        """
        # TODO: 接入分钟线数据表后，在此实现真实查询
        logger.debug(
            f"read_minute_volume_5d: {market}{code_int} "
            f"近{days}日分钟数据（当前无分钟线表，返回空列表）"
        )
        return []

    def close(self):
        """释放数据库连接"""
        try:
            self._engine.dispose()
            logger.info("DbReader 已关闭")
        except Exception:
            pass
