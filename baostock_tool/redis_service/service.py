"""
后台推送服务主控

职责：
  1. 定时读取 MySQL 行情数据，通过 Pub/Sub 广播给策略模块
  2. 定时读取 MySQL 选股结果，写入 Redis Stream 供策略模块消费
  3. 优雅启停（SIGINT / SIGTERM / KeyboardInterrupt）
  4. 异常自恢复（单次循环失败不中断服务）

运行模式：
  - snapshot_only : 只推行情快照（Pub/Sub）
  - selection_only: 只推选股股池（Stream）
  - both           : 同时推送（默认）

用法示例：
    from redis_service.service import MarketService
    svc = MarketService()
    svc.start()                    # 阻塞运行，Ctrl+C 停止

    # 或只跑一次（测试用）
    svc.run_once_snapshot()
    svc.run_once_selection("2026-03-17")
"""

import signal
import threading
import time
from datetime import datetime
from typing import Optional

import config
from utils.logger_utils import setup_logger
from redis_service.db_reader import DbReader
from redis_service.publisher import RedisPublisher
from redis_service.transformer import Transformer

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"],
)


class MarketService:
    """
    行情 & 选股 Redis 推送后台服务
    """

    def __init__(
        self,
        mode: str = "both",
        snapshot_interval: Optional[int] = None,
        selection_interval: Optional[int] = None,
    ):
        """
        Args:
            mode:                运行模式："snapshot_only" / "selection_only" / "both"
            snapshot_interval:   行情推送间隔（秒），不传则读配置文件
            selection_interval:  选股推送间隔（秒），不传则读配置文件
        """
        redis_cfg = config.get_redis_config()
        self.mode = mode
        self.snapshot_interval = snapshot_interval or redis_cfg["snapshot_interval"]
        self.selection_interval = selection_interval or redis_cfg["selection_interval"]

        self._stop_event = threading.Event()
        self._db = DbReader()
        self._pub = RedisPublisher()
        self._transformer = Transformer()

        logger.info(
            f"MarketService 初始化: mode={mode}, "
            f"snapshot_interval={self.snapshot_interval}s, "
            f"selection_interval={self.selection_interval}s"
        )

    # ------------------------------------------------------------------
    # 单次执行（方便测试 / 外部调用）
    # ------------------------------------------------------------------

    def run_once_snapshot(self, trade_date: Optional[str] = None) -> dict:
        """
        执行一次行情快照推送

        Args:
            trade_date: 指定日期（YYYY-MM-DD），不传则自动取最新交易日

        Returns:
            dict: {"success": int, "failed": int, "trade_date": str}
        """
        logger.info("--- 开始推送行情快照 ---")
        df = self._db.read_latest_snapshots(trade_date=trade_date)
        if df.empty:
            logger.warning("行情快照：无数据，跳过本次推送")
            return {"success": 0, "failed": 0, "trade_date": trade_date}

        items = Transformer.batch_snapshot_items(df)
        result = self._pub.publish_snapshot_batch(items)

        actual_date = str(df["date"].iloc[0]) if "date" in df.columns else trade_date
        self._pub.set_last_sync_time("snapshot")
        logger.info(
            f"行情快照推送完成: date={actual_date}, "
            f"success={result['success']}, failed={result['failed']}"
        )
        result["trade_date"] = actual_date
        return result

    def run_once_selection(
        self,
        trade_date: str,
        strategy_id: str = "MA10_BREAKTHROUGH",
    ) -> Optional[str]:
        """
        执行一次选股数据推送

        Args:
            trade_date: 选股日期，格式 YYYY-MM-DD
            strategy_id: 策略标识

        Returns:
            str: Stream entry_id；失败返回 None
        """
        logger.info(f"--- 开始推送选股数据: {trade_date} ---")
        df = self._db.read_stock_selection(trade_date=trade_date, strategy_id=strategy_id)
        if df.empty:
            logger.warning(f"选股数据：{trade_date} 无数据，跳过本次推送")
            return None

        message = Transformer.selection_message(
            df=df,
            trade_date=trade_date,
            strategy_id=strategy_id,
            db_reader=self._db,
        )
        date_compact = trade_date.replace("-", "")
        entry_id = self._pub.push_stock_selection(date_compact, message)
        self._pub.set_last_sync_time("selection")
        logger.info(f"选股数据推送完成: entry_id={entry_id}")
        return entry_id

    # ------------------------------------------------------------------
    # 后台循环
    # ------------------------------------------------------------------

    def _snapshot_loop(self):
        """行情快照推送循环（独立线程）"""
        logger.info(f"[快照线程] 启动，间隔 {self.snapshot_interval}s")
        while not self._stop_event.is_set():
            try:
                self.run_once_snapshot()
            except Exception as e:
                logger.error(f"[快照线程] 本次推送异常（服务继续运行）: {e}", exc_info=True)
            self._stop_event.wait(self.snapshot_interval)
        logger.info("[快照线程] 已退出")

    def _selection_loop(self):
        """选股数据推送循环（独立线程）"""
        logger.info(f"[选股线程] 启动，间隔 {self.selection_interval}s")
        while not self._stop_event.is_set():
            trade_date = datetime.now().strftime("%Y-%m-%d")
            try:
                self.run_once_selection(trade_date)
            except Exception as e:
                logger.error(f"[选股线程] 本次推送异常（服务继续运行）: {e}", exc_info=True)
            self._stop_event.wait(self.selection_interval)
        logger.info("[选股线程] 已退出")

    # ------------------------------------------------------------------
    # 启动 / 停止
    # ------------------------------------------------------------------

    def start(self, block: bool = True) -> None:
        """
        启动服务

        Args:
            block: True = 阻塞主线程直到收到停止信号（默认）
                   False = 后台运行，主线程继续执行
        """
        if not self._pub.ping():
            logger.error("Redis 连接失败，服务启动中止")
            raise ConnectionError("Redis 连接失败，请检查 config.ini [redis] 配置")

        logger.info(f"MarketService 启动（mode={self.mode}）")
        self._stop_event.clear()

        # 注册信号处理（仅在主线程中有效）
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (OSError, ValueError):
            pass    # 非主线程时 signal 注册会失败，忽略

        threads = []
        if self.mode in ("snapshot_only", "both"):
            t = threading.Thread(target=self._snapshot_loop, name="snapshot", daemon=True)
            threads.append(t)
            t.start()

        if self.mode in ("selection_only", "both"):
            t = threading.Thread(target=self._selection_loop, name="selection", daemon=True)
            threads.append(t)
            t.start()

        if block:
            try:
                while not self._stop_event.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("收到 KeyboardInterrupt，正在停止服务...")
                self.stop()

            for t in threads:
                t.join(timeout=5)
            logger.info("MarketService 已停止")

    def stop(self) -> None:
        """停止服务（线程安全）"""
        logger.info("MarketService 正在停止...")
        self._stop_event.set()

    def _signal_handler(self, signum, frame):
        logger.info(f"收到信号 {signum}，正在停止服务...")
        self.stop()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
        self._db.close()
        self._pub.close()
