"""
股池选股数据模型
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class BasicInfo(BaseModel):
    """股票基本信息"""
    prev_close: float = Field(..., description="昨收价")
    ma10: float = Field(..., description="10日均线")
    ma5_high: float = Field(..., description="近5日最高价")
    volume_ratio: float = Field(..., description="量比")
    turnover_rate: float = Field(..., description="换手率")


class MinuteVolume(BaseModel):
    """单条分钟成交量数据"""
    time: str = Field(..., description="时间，格式HH:MM")
    volume: int = Field(..., description="成交量")


class TechnicalIndicators(BaseModel):
    """技术指标"""
    ma5: float = Field(..., description="5日均线")
    ma10: float = Field(..., description="10日均线")
    ma20: float = Field(..., description="20日均线")
    vol_ma5: float = Field(..., description="5日均量")
    vol_ma10: float = Field(..., description="10日均量")


class FundamentalData(BaseModel):
    """基本面数据"""
    pe: float = Field(..., description="市盈率")
    pb: float = Field(..., description="市净率")
    market_cap: float = Field(..., description="市值（百万）")


class StockInfo(BaseModel):
    """单只股票详细信息"""
    symbol: str = Field(..., description="股票代码")
    exchange: str = Field(..., description="交易所代码")
    name: str = Field(..., description="股票名称")
    basic_info: BasicInfo = Field(..., description="基本信息")
    minute_volume_5d_01: List[MinuteVolume] = Field(
        default_factory=list, 
        description="第1天每5分钟成交量"
    )
    minute_volume_5d_02: List[MinuteVolume] = Field(
        default_factory=list, 
        description="第2天每5分钟成交量"
    )
    minute_volume_5d_03: List[MinuteVolume] = Field(
        default_factory=list, 
        description="第3天每5分钟成交量"
    )
    minute_volume_5d_04: List[MinuteVolume] = Field(
        default_factory=list, 
        description="第4天每5分钟成交量"
    )
    minute_volume_5d_05: List[MinuteVolume] = Field(
        default_factory=list, 
        description="第5天每5分钟成交量"
    )
    technical_indicators: Optional[TechnicalIndicators] = Field(
        default=None, 
        description="技术指标"
    )
    fundamental_data: Optional[FundamentalData] = Field(
        default=None, 
        description="基本面数据"
    )


class SelectionMessage(BaseModel):
    """选股消息结构"""
    type: str = Field(default="stock_selection", description="消息类型")
    version: str = Field(default="1.0", description="版本号")
    timestamp: int = Field(..., description="毫秒时间戳")
    batch_id: str = Field(..., description="选股批次ID")
    strategy_id: str = Field(..., description="选股策略ID")
    total_count: int = Field(..., description="本次选股总数")
    stocks: List[StockInfo] = Field(default_factory=list, description="股票列表")
    
    def get_stream_key(self, date: str) -> str:
        """
        获取Stream Key
        
        Args:
            date: 日期，格式YYYYMMDD
            
        Returns:
            str: Stream Key，格式为 selection:stream:{date}
        """
        return f"selection:stream:{date}"


class SelectionParser:
    """选股数据解析器"""
    
    @staticmethod
    def build_stream_key(date: str) -> str:
        """
        构建Stream Key
        
        Args:
            date: 日期，格式YYYYMMDD
            
        Returns:
            str: Stream Key
        """
        return f"selection:stream:{date}"
    
    @staticmethod
    def parse_message(message: dict) -> SelectionMessage:
        """
        解析Stream消息
        
        Args:
            message: Redis Stream消息字典
            
        Returns:
            SelectionMessage: 选股消息对象
        """
        import json
        
        # 消息内容在第一个元素中
        if isinstance(message, tuple):
            msg_id, msg_data = message
            data = json.loads(msg_data.get("data", "{}"))
        else:
            data = json.loads(message.get("data", "{}"))
        
        return SelectionMessage(**data)
    
    @staticmethod
    def to_json(selection: SelectionMessage) -> str:
        """
        序列化选股消息为JSON字符串
        
        Args:
            selection: 选股消息对象
            
        Returns:
            str: JSON字符串
        """
        return selection.model_dump_json()
    
    @staticmethod
    def to_stream_fields(selection: SelectionMessage) -> dict:
        """
        转换为Stream写入格式
        
        Args:
            selection: 选股消息对象
            
        Returns:
            dict: 用于XADD的字段字典
        """
        return {
            "data": selection.model_dump_json()
        }
