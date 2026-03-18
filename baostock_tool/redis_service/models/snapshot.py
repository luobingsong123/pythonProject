"""
行情快照数据模型
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class MarketQuote(BaseModel):
    """行情报价数据"""
    last_price: float = Field(..., description="最新价")
    volume: int = Field(..., description="成交量（手）")
    amount: float = Field(..., description="成交额")
    bid_price: List[float] = Field(default_factory=list, description="买一到买五价格")
    bid_volume: List[int] = Field(default_factory=list, description="买一到买五量")
    ask_price: List[float] = Field(default_factory=list, description="卖一到卖五价格")
    ask_volume: List[int] = Field(default_factory=list, description="卖一到卖五量")
    date: str = Field(..., description="行情日期，格式YYYYMMDD")
    timestamp: str = Field(..., description="行情时间，格式HH:MM:SS")


class SnapshotData(BaseModel):
    """行情快照消息结构"""
    type: str = Field(default="snapshot", description="消息类型")
    timestamp: int = Field(..., description="毫秒时间戳")
    exchange: str = Field(..., description="交易所代码，如SSE、SZSE")
    symbol: str = Field(..., description="股票代码")
    data: MarketQuote = Field(..., description="行情数据")
    
    def get_channel(self) -> str:
        """
        获取消息通道名
        
        Returns:
            str: 通道名，格式为 market:snapshot:{exchange}:{symbol}
        """
        return f"market:snapshot:{self.exchange}:{self.symbol}"


class SnapshotParser:
    """行情快照解析器"""
    
    @staticmethod
    def parse_channel(channel: str) -> dict:
        """
        解析通道名获取交易所和股票代码
        
        Args:
            channel: 通道名，如 market:snapshot:SSE:600036
            
        Returns:
            dict: 包含exchange和symbol的字典
        """
        parts = channel.split(":")
        if len(parts) >= 4 and parts[0] == "market" and parts[1] == "snapshot":
            return {
                "exchange": parts[2],
                "symbol": parts[3]
            }
        raise ValueError(f"Invalid channel format: {channel}")
    
    @staticmethod
    def build_channel(exchange: str, symbol: str) -> str:
        """
        构建通道名
        
        Args:
            exchange: 交易所代码
            symbol: 股票代码
            
        Returns:
            str: 通道名
        """
        return f"market:snapshot:{exchange}:{symbol}"
    
    @staticmethod
    def parse_message(message: str) -> SnapshotData:
        """
        解析消息JSON字符串
        
        Args:
            message: JSON格式的消息字符串
            
        Returns:
            SnapshotData: 行情快照数据对象
        """
        import json
        data = json.loads(message)
        return SnapshotData(**data)
    
    @staticmethod
    def to_json(snapshot: SnapshotData) -> str:
        """
        序列化行情快照为JSON字符串
        
        Args:
            snapshot: 行情快照数据对象
            
        Returns:
            str: JSON字符串
        """
        return snapshot.model_dump_json()
