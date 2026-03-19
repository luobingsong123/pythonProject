"""
回测引擎主流程
"""

import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from database.connection import close_db_pool
from config.settings import settings, BacktestConfig
from database.connection import DatabasePool, init_db_pool
from database.queries import StockQueryService
from selection.writer import SelectionWriter
from selection.reader import SelectionReader
from strategy.selector import StockSelector
from strategy.ma_breakthrough import MABreakthroughStrategy
from backtest.publisher import TickDataPublisher
from utils.serializer import TimestampUtil


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置
        """
        self.config = config or settings.backtest
        self.db_pool: Optional[DatabasePool] = None
        self.query_service: Optional[StockQueryService] = None
        self.selector: Optional[StockSelector] = None
        self.selection_writer: Optional[SelectionWriter] = None
        self.selection_reader: Optional[SelectionReader] = None
        self.tick_publisher: Optional[TickDataPublisher] = None
        
        # 当前回测日期
        self.current_date: Optional[str] = None
        self.selected_stocks: List[Dict[str, Any]] = []
    
    def initialize(
        self,
        db_config: Optional[Dict[str, Any]] = None,
        redis_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化引擎
        
        Args:
            db_config: 数据库配置
            redis_config: Redis配置
        """
        print("Initializing backtest engine...")
        
        # 初始化数据库连接池
        if db_config:
            self.db_pool = init_db_pool(db_config)
        else:
            self.db_pool = init_db_pool({
                "host": settings.database.host,
                "port": settings.database.port,
                "user": settings.database.user,
                "password": settings.database.password,
                "database": settings.database.database
            })
        
        # 初始化服务
        self.query_service = StockQueryService(self.db_pool)
        
        # 初始化策略
        strategy = None
        if self.config.use_strategy:
            strategy = MABreakthroughStrategy(self.config.strategy_params)
        
        self.selector = StockSelector(self.query_service, strategy)
        self.selection_writer = SelectionWriter()
        self.selection_reader = SelectionReader()
        self.tick_publisher = TickDataPublisher(use_pipeline=self.config.use_pipeline)
        
        print("Backtest engine initialized successfully")
    
    def run(self):
        """运行回测"""
        print(f"\nStarting backtest from {self.config.start_date} to {self.config.end_date}")
        
        # 生成交易日列表
        trade_dates = self._generate_trade_dates()
        
        for date in trade_dates:
            self.current_date = date
            print(f"\n{'='*50}")
            print(f"Processing date: {date}")
            print(f"{'='*50}")
            
            # 步骤1: 选股并推送到股池
            self._select_and_publish_stocks(date)
            
            # 步骤2: 等待消费（模拟）
            print("Waiting for stock selection consumption...")
            time.sleep(1)  # 模拟等待
            
            # 步骤3: 读取股池并推送Tick数据
            self._publish_tick_data(date)
        
        print(f"\n{'='*50}")
        print("Backtest completed!")
        print(f"{'='*50}")
    
    def _select_and_publish_stocks(self, date: str):
        """
        选股并推送到股池
        
        Args:
            date: 日期
        """
        print(f"\n[Step 1] Selecting stocks for {date}...")
        
        # 执行选股
        stocks = self.selector.select(
            date=date,
            strategy_id=self.config.strategy_id if self.config.use_strategy else None,
            count=self.config.default_selection_count
        )
        
        if not stocks:
            print(f"No stocks selected for {date}")
            return
        
        print(f"Selected {len(stocks)} stocks:")
        for stock in stocks:
            print(f"  - {stock.exchange}:{stock.symbol} {stock.name}")
        
        # 生成批次ID
        batch_id = f"SELECT_{date}_001"
        
        # 推送到Redis Stream
        msg_id = self.selection_writer.write_selection(
            date=date,
            batch_id=batch_id,
            strategy_id=self.config.strategy_id,
            stocks=stocks,
            total_count=len(stocks)
        )
        
        print(f"Published to selection:stream:{date}, msg_id: {msg_id}")
        
        # 保存选股结果供后续使用
        self.selected_stocks = [
            {
                "symbol": stock.symbol,
                "exchange": stock.exchange,
                "name": stock.name
            }
            for stock in stocks
        ]
    
    def _publish_tick_data(self, date: str):
        """
        读取股池并推送Tick数据
        
        Args:
            date: 日期
        """
        print(f"\n[Step 2] Publishing tick data for {date}...")
        
        # 从Redis读取股池数据
        messages = self.selection_reader.read_latest(date, count=1)
        
        if not messages:
            print(f"No selection data found for {date}")
            return
        
        # 解析选股结果
        selections = self.selection_reader.parse_messages(messages)
        
        if not selections:
            print(f"Failed to parse selection data for {date}")
            return
        
        selection = selections[0]
        
        print(f"Publishing tick data for {len(selection.stocks)} stocks:")
        
        # 构建股票列表用于批量发布
        stocks = []
        exchange_map = {"SSE": "sh", "SZSE": "sz"}
        
        for stock in selection.stocks:
            market = exchange_map.get(stock.exchange, "sh")
            code = int(stock.symbol)
            stocks.append((market, stock.exchange, code, stock.symbol))
        
        # 批量发布Tick数据
        results = self.tick_publisher.publish_tick_data_batch(date, stocks)
        
        # 输出结果
        for symbol, count in results.items():
            print(f"  {symbol}: Published {count} tick messages")
    
    def _generate_trade_dates(self) -> List[str]:
        """
        生成交易日列表（从数据库查询交易日历）
        
        Returns:
            List[str]: 交易日列表
        """
        if self.config.trade_dates:
            return self.config.trade_dates
        
        # 从数据库查询交易日历
        try:
            dates = self.query_service.get_trading_dates(
                self.config.start_date,
                self.config.end_date
            )
            print(f"获取到 {len(dates)} 个交易日")
            return dates
        except Exception as e:
            print(f"查询交易日历失败: {e}，使用简化逻辑（跳过周末）")
            # 回退到简化实现：跳过周末
            start = datetime.strptime(self.config.start_date, "%Y%m%d")
            end = datetime.strptime(self.config.end_date, "%Y%m%d")
            
            dates = []
            current = start
            
            while current <= end:
                if current.weekday() < 5:
                    dates.append(current.strftime("%Y%m%d"))
                current += timedelta(days=1)
            
            return dates
    
    def close(self):
        """关闭引擎"""
        print("\nClosing backtest engine...")
        
        if self.selection_writer:
            self.selection_writer.close()
        
        if self.selection_reader:
            self.selection_reader.close()
        
        if self.tick_publisher:
            self.tick_publisher.close()
        

        close_db_pool()
        
        print("Backtest engine closed")
