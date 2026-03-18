"""
序列化工具模块
"""

import json
from typing import Any, Optional
from datetime import datetime


class Serializer:
    """通用序列化工具"""
    
    @staticmethod
    def to_json(data: Any) -> str:
        """
        序列化为JSON字符串
        
        Args:
            data: 任意可序列化数据
            
        Returns:
            str: JSON字符串
        """
        return json.dumps(data, ensure_ascii=False)
    
    @staticmethod
    def from_json(json_str: str) -> Any:
        """
        反序列化JSON字符串
        
        Args:
            json_str: JSON字符串
            
        Returns:
            Any: 反序列化后的数据
        """
        return json.loads(json_str)
    
    @staticmethod
    def to_json_bytes(data: Any) -> bytes:
        """
        序列化为JSON字节
        
        Args:
            data: 任意可序列化数据
            
        Returns:
            bytes: JSON字节
        """
        return json.dumps(data, ensure_ascii=False).encode("utf-8")
    
    @staticmethod
    def from_json_bytes(json_bytes: bytes) -> Any:
        """
        反序列化JSON字节
        
        Args:
            json_bytes: JSON字节
            
        Returns:
            Any: 反序列化后的数据
        """
        return json.loads(json_bytes.decode("utf-8"))


class TimestampUtil:
    """时间戳工具"""
    
    @staticmethod
    def current_timestamp() -> int:
        """
        获取当前毫秒时间戳
        
        Returns:
            int: 毫秒时间戳
        """
        return int(datetime.now().timestamp() * 1000)
    
    @staticmethod
    def current_date() -> str:
        """
        获取当前日期
        
        Returns:
            str: 日期，格式YYYYMMDD
        """
        return datetime.now().strftime("%Y%m%d")
    
    @staticmethod
    def current_time() -> str:
        """
        获取当前时间
        
        Returns:
            str: 时间，格式HH:MM:SS
        """
        return datetime.now().strftime("%H:%M:%S")
    
    @staticmethod
    def format_timestamp(ts: int) -> str:
        """
        格式化时间戳
        
        Args:
            ts: 毫秒时间戳
            
        Returns:
            str: 格式化的时间字符串
        """
        dt = datetime.fromtimestamp(ts / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串，格式YYYYMMDD
            
        Returns:
            datetime: 日期对象
        """
        return datetime.strptime(date_str, "%Y%m%d")
    
    @staticmethod
    def format_date(dt: datetime) -> str:
        """
        格式化日期为字符串
        
        Args:
            dt: 日期对象
            
        Returns:
            str: 日期字符串，格式YYYYMMDD
        """
        return dt.strftime("%Y%m%d")
    
    @staticmethod
    def parse_timestamp(ts_str: str) -> datetime:
        """
        解析时间戳字符串
        
        Args:
            ts_str: 时间戳字符串
            
        Returns:
            datetime: 日期时间对象
        """
        # 尝试多种格式
        formats = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d%H%M%S%f",
            "%Y%m%d%H%M%S"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(ts_str[:len(fmt)], fmt)
            except ValueError:
                continue
        
        # 默认返回当前时间
        return datetime.now()
