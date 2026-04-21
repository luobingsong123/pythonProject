"""
Tick数据发布器
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from database.queries import StockQueryService
from market.publisher import SnapshotPublisher
from models.snapshot import SnapshotData, MarketQuote, SnapshotParser
from utils.serializer import TimestampUtil

logger = logging.getLogger(__name__)


class TickDataPublisher:
    """Tick数据发布器"""
    
    def __init__(
        self,
        query_service: Optional[StockQueryService] = None,
        snapshot_publisher: Optional[SnapshotPublisher] = None,
        use_pipeline: bool = True
    ):
        """
        初始化发布器
        
        Args:
            query_service: 查询服务
            snapshot_publisher: 行情发布器
            use_pipeline: 是否使用Redis Pipeline批量推送，默认True
        """
        self.query_service = query_service or StockQueryService()
        self.publisher = snapshot_publisher or SnapshotPublisher()
        self.use_pipeline = use_pipeline
        
        # 空数据缓存：{date: empty_tick_list}
        self._empty_tick_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    def publish_tick_data(
        self,
        date: str,
        market: str,
        code: int,
        exchange: str,
        symbol: str
    ) -> int:
        """
        发布Tick数据
        
        Args:
            date: 日期
            market: 市场代码(sh/sz)
            code: 股票代码
            exchange: 交易所代码(SSE/SZSE)
            symbol: 股票代码(6位)
            
        Returns:
            int: 发布的消息数量
        """
        # 获取Tick数据
        tick_data = self.query_service.get_tick_data(date, market, code)
        
        if not tick_data:
            # 查不到数据时，推送一天全-1的数据
            logger.debug(f"未查到Tick数据，生成空数据推送: {market}:{code}")
            tick_data = self._generate_empty_tick_data(date)
        else:
            logger.debug(f"查到 {len(tick_data)} 条Tick数据: {market}:{code}")
        
        count = 0
        total = len(tick_data)
        
        # 发布每条Tick数据，seqno从1累加，最后一笔为0
        for idx, tick in enumerate(tick_data):
            snapshot = self._convert_tick_to_snapshot(
                tick, date, exchange, symbol
            )
            
            if snapshot:
                snapshot.seqno = 0 if idx == total - 1 else idx + 1
                self.publisher.publish(snapshot)
                count += 1
        
        logger.debug(f"推送Tick数据完成: {exchange}:{symbol}, 数量={count}")
        return count
    
    def publish_tick_data_batch(
        self,
        date: str,
        stocks: List[Tuple[str, str, int, str]]
    ) -> Dict[str, int]:
        """
        批量发布多只股票的Tick数据（推荐使用）
        
        按UNIX时间戳排序推送，不区分证券代码先后，
        确保所有股票的Tick数据按照真实时间顺序发布。
        
        Args:
            date: 日期 YYYYMMDD
            stocks: 股票列表 [(market, exchange, code, symbol), ...]
                   market: sh/sz, exchange: SSE/SZSE, code: int, symbol: 6位代码
            
        Returns:
            Dict[str, int]: {symbol: 发布数量}
        """
        if not stocks:
            return {}
        
        logger.info(f"批量发布Tick数据: 日期={date}, 股票数={len(stocks)}, pipeline={self.use_pipeline}")
        
        # 1. 批量查询数据库（一次查询所有股票）
        stock_params = [(market, code) for market, exchange, code, symbol in stocks]
        tick_data_map = self.query_service.get_tick_data_batch(date, stock_params)
        
        # 2. 收集所有股票的tick数据，带上股票信息，按UNIX时间戳排序
        all_ticks: List[Dict[str, Any]] = []
        for market, exchange, code, symbol in stocks:
            code_str = f"{code:06d}"
            tick_data = tick_data_map.get(code_str)
            
            if not tick_data:
                tick_data = self._get_cached_empty_tick_data(date)
                logger.debug(f"未查到Tick数据，使用缓存空数据: {market}:{code}")
            
            for tick in tick_data:
                unix_ts = tick.get("UNIX")
                timestamp_ms = int(unix_ts) if unix_ts else 0
                all_ticks.append({
                    "tick": tick,
                    "exchange": exchange,
                    "symbol": symbol,
                    "timestamp_ms": timestamp_ms
                })
        
        # 按UNIX时间戳排序，时间早的先推送
        all_ticks.sort(key=lambda x: x["timestamp_ms"])
        logger.info(f"按时间戳排序完成: 总Tick数={len(all_ticks)}")
        
        # 3. 统计每个证券的tick总数，用于判断该证券最后一笔(seqno=0)
        symbol_total: Dict[str, int] = {}
        for item in all_ticks:
            symbol_total[item["symbol"]] = symbol_total.get(item["symbol"], 0) + 1
        
        # 4. 按时间顺序推送，seqno按证券代码单独编号，从1累加，该证券最后一笔为0
        results: Dict[str, int] = {}
        symbol_seq: Dict[str, int] = {}  # 每个证券的当前序号
        
        if self.use_pipeline:
            # 使用 Pipeline 批量推送
            pipe = self.publisher._client.pipeline()
            
            for item in all_ticks:
                snapshot = self._convert_tick_to_snapshot(
                    item["tick"], date, item["exchange"], item["symbol"]
                )
                if snapshot:
                    symbol = item["symbol"]
                    symbol_seq[symbol] = symbol_seq.get(symbol, 0) + 1
                    # 该证券最后一笔seqno=0，其余从1递增
                    snapshot.seqno = 0 if symbol_seq[symbol] == symbol_total[symbol] else symbol_seq[symbol]
                    channel = snapshot.get_channel()
                    message = SnapshotParser.to_json(snapshot)
                    pipe.publish(channel, message)
                    results[symbol] = results.get(symbol, 0) + 1
            
            # 一次性执行所有 publish
            pipe.execute()
            logger.info(f"Pipeline批量推送完成(按时间排序): 总股票数={len(results)}, 总Tick数={len(all_ticks)}")
        else:
            # 逐条推送（兼容模式）
            for item in all_ticks:
                snapshot = self._convert_tick_to_snapshot(
                    item["tick"], date, item["exchange"], item["symbol"]
                )
                if snapshot:
                    symbol = item["symbol"]
                    symbol_seq[symbol] = symbol_seq.get(symbol, 0) + 1
                    # 该证券最后一笔seqno=0，其余从1递增
                    snapshot.seqno = 0 if symbol_seq[symbol] == symbol_total[symbol] else symbol_seq[symbol]
                    self.publisher.publish(snapshot)
                    results[symbol] = results.get(symbol, 0) + 1
            
            logger.info(f"逐条推送完成(按时间排序): 总股票数={len(results)}, 总Tick数={len(all_ticks)}")
        
        return results
    
    def _get_cached_empty_tick_data(self, date: str) -> List[Dict[str, Any]]:
        """
        获取缓存的空Tick数据
        
        Args:
            date: 日期 YYYYMMDD
            
        Returns:
            List[Dict]: 空tick数据列表
        """
        if date not in self._empty_tick_cache:
            self._empty_tick_cache[date] = self._generate_empty_tick_data(date)
            logger.debug(f"生成并缓存空Tick数据: {date}")
        return self._empty_tick_cache[date]
    
    def _generate_empty_tick_data(self, date: str) -> List[Dict[str, Any]]:
        """
        生成一天的空Tick数据（全-1）
        
        Args:
            date: 日期 YYYYMMDD
            
        Returns:
            List[Dict]: 全-1的tick数据列表
        """
        result = []
        
        # 交易时段：9:30-11:30, 13:00-15:00
        # 每3秒一条
        year = int(date[:4])
        month = int(date[4:6])
        day = int(date[6:8])
        
        base_date = datetime(year, month, day)
        
        # 上午时段 9:30-11:30
        start_am = base_date.replace(hour=9, minute=30, second=0)
        end_am = base_date.replace(hour=11, minute=30, second=0)
        
        current = start_am
        while current <= end_am:
            result.append(self._create_empty_tick(current))
            current += timedelta(seconds=3)
        
        # 下午时段 13:00-15:00
        start_pm = base_date.replace(hour=13, minute=0, second=0)
        end_pm = base_date.replace(hour=15, minute=0, second=0)
        
        current = start_pm
        while current <= end_pm:
            result.append(self._create_empty_tick(current))
            current += timedelta(seconds=3)
        
        return result
    
    def _create_empty_tick(self, dt: datetime) -> Dict[str, Any]:
        """
        创建单条空tick数据
        
        Args:
            dt: 时间
            
        Returns:
            Dict: 空tick数据
        """
        return {
            "TradingTime": dt.strftime("%Y%m%d%H%M%S"),
            "PreClosePrice": -1,
            "OpenPrice": -1,
            "HighPrice": -1,
            "LowPrice": -1,
            "LastPrice": -1,
            "TotalVolume": -1,
            "TradeVolume": -1,
            "TotalAmount": -1,
            "TradeAmount": -1,
            "BuyPrice01": -1,
            "BuyPrice02": -1,
            "BuyPrice03": -1,
            "BuyPrice04": -1,
            "BuyPrice05": -1,
            "BuyVolume01": -1,
            "BuyVolume02": -1,
            "BuyVolume03": -1,
            "BuyVolume04": -1,
            "BuyVolume05": -1,
            "SellPrice01": -1,
            "SellPrice02": -1,
            "SellPrice03": -1,
            "SellPrice04": -1,
            "SellPrice05": -1,
            "SellVolume01": -1,
            "SellVolume02": -1,
            "SellVolume03": -1,
            "SellVolume04": -1,
            "SellVolume05": -1
        }
    
    def _convert_tick_to_snapshot(
        self,
        tick: Dict[str, Any],
        date: str,
        exchange: str,
        symbol: str
    ) -> Optional[SnapshotData]:
        """
        将Tick数据转换为行情快照
        
        Args:
            tick: Tick数据
            date: 日期
            exchange: 交易所代码
            symbol: 股票代码
            
        Returns:
            SnapshotData: 行情快照
        """
        try:
            # 使用 UNIX 字段作为时间戳（毫秒），直接使用原值
            unix_ts = tick.get("UNIX")
            if unix_ts:
                timestamp_ms = int(unix_ts)
            else:
                timestamp_ms = TimestampUtil.current_timestamp()
            
            time_str = ""  # 不需要转换
            
            # 构建买卖盘
            bid_prices = [
                float(tick.get("BuyPrice01", 0) or 0),
                float(tick.get("BuyPrice02", 0) or 0),
                float(tick.get("BuyPrice03", 0) or 0),
                float(tick.get("BuyPrice04", 0) or 0),
                float(tick.get("BuyPrice05", 0) or 0)
            ]
            
            bid_volumes = [
                int(tick.get("BuyVolume01", 0) or 0),
                int(tick.get("BuyVolume02", 0) or 0),
                int(tick.get("BuyVolume03", 0) or 0),
                int(tick.get("BuyVolume04", 0) or 0),
                int(tick.get("BuyVolume05", 0) or 0)
            ]
            
            ask_prices = [
                float(tick.get("SellPrice01", 0) or 0),
                float(tick.get("SellPrice02", 0) or 0),
                float(tick.get("SellPrice03", 0) or 0),
                float(tick.get("SellPrice04", 0) or 0),
                float(tick.get("SellPrice05", 0) or 0)
            ]
            
            ask_volumes = [
                int(tick.get("SellVolume01", 0) or 0),
                int(tick.get("SellVolume02", 0) or 0),
                int(tick.get("SellVolume03", 0) or 0),
                int(tick.get("SellVolume04", 0) or 0),
                int(tick.get("SellVolume05", 0) or 0)
            ]
            
            # 构建行情快照
            snapshot = SnapshotData(
                type="snapshot",
                timestamp=timestamp_ms,
                exchange=exchange,
                symbol=symbol,
                data=MarketQuote(
                    last_price=float(tick.get("LastPrice", 0) or 0),
                    volume=int(tick.get("TotalVolume", 0) or 0),
                    amount=float(tick.get("TotalAmount", 0) or 0),
                    bid_price=bid_prices,
                    bid_volume=bid_volumes,
                    ask_price=ask_prices,
                    ask_volume=ask_volumes,
                    date=date,
                    timestamp=time_str
                )
            )
            
            return snapshot
            
        except Exception as e:
            logger.warning(f"Tick转换失败: {e}")
            return None
    
    def close(self):
        """关闭发布器"""
        if self.publisher:
            self.publisher.close()
