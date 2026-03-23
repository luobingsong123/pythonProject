"""
选股结果数据仓库

用于操作stock_selection_result和stock_selection_detail表
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from database.connection import DatabasePool, get_db_connection
from models.stock_selection import SelectionMessage, StockInfo
from contextlib import contextmanager, get_db_connection, release_db_connection


class SelectionRepository:
    """选股结果数据仓库"""
    
    def __init__(self, db_pool: Optional[DatabasePool] = None):
        """
        初始化数据仓库
        
        Args:
            db_pool: 数据库连接池
        """
        self._db_pool = db_pool
    
    def _get_connection(self):
        """获取数据库连接"""
        if self._db_pool:
            return self._db_pool.connection()
        

        @contextmanager
        def wrapper():
            conn = get_db_connection()
            try:
                yield conn
            finally:
                release_db_connection(conn)  # 释放连接
        return wrapper()
    
    def save_selection_result(
        self,
        selection: SelectionMessage,
        strategy_params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        保存选股结果
        
        Args:
            selection: 选股消息
            strategy_params: 策略参数
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 解析日期
            date_str = selection.batch_id.split('_')[1] if '_' in selection.batch_id else datetime.now().strftime('%Y%m%d')
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # 1. 保存主表
                    self._insert_result(cursor, selection, trade_date, strategy_params)
                    
                    # 2. 保存明细表
                    for i, stock in enumerate(selection.stocks):
                        self._insert_detail(cursor, selection.batch_id, trade_date, stock, i + 1)
                    
                    # 3. 保存统计表
                    self._insert_stats(cursor, selection, trade_date)
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"Error saving selection result: {e}")
            return False
    
    def _insert_result(
        self,
        cursor,
        selection: SelectionMessage,
        trade_date,
        strategy_params: Optional[Dict[str, Any]]
    ):
        """插入主表"""
        sql = """
            INSERT INTO stock_selection_result (
                batch_id, strategy_id, version, trade_date,
                total_count, strategy_params, selection_time
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                strategy_id = VALUES(strategy_id),
                total_count = VALUES(total_count),
                strategy_params = VALUES(strategy_params),
                selection_time = VALUES(selection_time),
                updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.execute(sql, (
            selection.batch_id,
            selection.strategy_id,
            selection.version,
            trade_date,
            selection.total_count,
            json.dumps(strategy_params) if strategy_params else None,
            datetime.fromtimestamp(selection.timestamp / 1000)
        ))
    
    def _insert_detail(
        self,
        cursor,
        batch_id: str,
        trade_date,
        stock: StockInfo,
        sort_order: int
    ):
        """插入明细表"""
        sql = """
            INSERT INTO stock_selection_detail (
                batch_id, trade_date, symbol, exchange, market, code_int, name, sort_order,
                prev_close, ma5, ma10, ma20, ma60, ma5_high, volume_ratio, turnover_rate,
                vol_ma5, vol_ma10, vol_ma20,
                pe, pb, market_cap,
                strategy_score, strategy_signals,
                minute_volume_5d_01, minute_volume_5d_02, minute_volume_5d_03,
                minute_volume_5d_04, minute_volume_5d_05
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                sort_order = VALUES(sort_order),
                strategy_score = VALUES(strategy_score),
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 转换市场代码
        market_map = {"SSE": "sh", "SZSE": "sz"}
        market = market_map.get(stock.exchange, "sh")
        code_int = int(stock.symbol)
        
        # 获取技术指标
        tech = stock.technical_indicators
        fund = stock.fundamental_data
        basic = stock.basic_info
        
        cursor.execute(sql, (
            batch_id,
            trade_date,
            stock.symbol,
            stock.exchange,
            market,
            code_int,
            stock.name,
            sort_order,
            
            # 基本信息
            basic.prev_close if basic else None,
            tech.ma5 if tech else None,
            tech.ma10 if tech else None,
            tech.ma20 if tech else None,
            tech.ma60 if tech else None,
            basic.ma5_high if basic else None,
            basic.volume_ratio if basic else None,
            basic.turnover_rate if basic else None,
            
            # 成交量指标
            tech.vol_ma5 if tech else None,
            tech.vol_ma10 if tech else None,
            None,  # vol_ma20
            
            # 基本面
            fund.pe if fund else None,
            fund.pb if fund else None,
            fund.market_cap if fund else None,
            
            # 策略相关
            None,  # strategy_score
            None,  # strategy_signals
            
            # 分钟成交量
            json.dumps([{"time": v.time, "volume": v.volume} for v in stock.minute_volume_5d_01]) if stock.minute_volume_5d_01 else None,
            json.dumps([{"time": v.time, "volume": v.volume} for v in stock.minute_volume_5d_02]) if stock.minute_volume_5d_02 else None,
            json.dumps([{"time": v.time, "volume": v.volume} for v in stock.minute_volume_5d_03]) if stock.minute_volume_5d_03 else None,
            json.dumps([{"time": v.time, "volume": v.volume} for v in stock.minute_volume_5d_04]) if stock.minute_volume_5d_04 else None,
            json.dumps([{"time": v.time, "volume": v.volume} for v in stock.minute_volume_5d_05]) if stock.minute_volume_5d_05 else None,
        ))
    
    def _insert_stats(
        self,
        cursor,
        selection: SelectionMessage,
        trade_date
    ):
        """插入统计表"""
        # 计算统计数据
        market_caps = []
        sse_count = 0
        szse_count = 0
        
        for stock in selection.stocks:
            if stock.fundamental_data:
                market_caps.append(stock.fundamental_data.market_cap)
            
            if stock.exchange == "SSE":
                sse_count += 1
            else:
                szse_count += 1
        
        sql = """
            INSERT INTO stock_selection_stats (
                batch_id, trade_date,
                avg_market_cap, min_market_cap, max_market_cap,
                sse_count, szse_count
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                avg_market_cap = VALUES(avg_market_cap),
                min_market_cap = VALUES(min_market_cap),
                max_market_cap = VALUES(max_market_cap),
                sse_count = VALUES(sse_count),
                szse_count = VALUES(szse_count),
                updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.execute(sql, (
            selection.batch_id,
            trade_date,
            sum(market_caps) / len(market_caps) if market_caps else None,
            min(market_caps) if market_caps else None,
            max(market_caps) if market_caps else None,
            sse_count,
            szse_count
        ))
    
    def get_selection_by_date(
        self,
        trade_date: str,
        strategy_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        查询某日的选股结果
        
        Args:
            trade_date: 交易日期，格式YYYYMMDD
            strategy_id: 策略ID过滤
            
        Returns:
            List[Dict]: 选股结果列表
        """
        formatted_date = datetime.strptime(trade_date, '%Y%m%d').date()
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                if strategy_id:
                    sql = """
                        SELECT r.*, d.symbol, d.exchange, d.name,
                               d.prev_close, d.ma10, d.market_cap, d.strategy_score
                        FROM stock_selection_result r
                        JOIN stock_selection_detail d ON r.batch_id = d.batch_id
                        WHERE r.trade_date = %s AND r.strategy_id = %s
                        ORDER BY r.batch_id, d.sort_order
                    """
                    cursor.execute(sql, (formatted_date, strategy_id))
                else:
                    sql = """
                        SELECT r.*, d.symbol, d.exchange, d.name,
                               d.prev_close, d.ma10, d.market_cap, d.strategy_score
                        FROM stock_selection_result r
                        JOIN stock_selection_detail d ON r.batch_id = d.batch_id
                        WHERE r.trade_date = %s
                        ORDER BY r.batch_id, d.sort_order
                    """
                    cursor.execute(sql, (formatted_date,))
                
                return cursor.fetchall()
    
    def get_selection_by_batch(
        self,
        batch_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        查询某批次的选股结果
        
        Args:
            batch_id: 批次ID
            
        Returns:
            Dict: 选股结果，包含主表和明细
        """
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                # 查询主表
                cursor.execute(
                    "SELECT * FROM stock_selection_result WHERE batch_id = %s",
                    (batch_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                # 查询明细
                cursor.execute(
                    """
                    SELECT * FROM stock_selection_detail 
                    WHERE batch_id = %s 
                    ORDER BY sort_order
                    """,
                    (batch_id,)
                )
                details = cursor.fetchall()
                
                result['stocks'] = details
                return result
    
    def get_selection_history(
        self,
        strategy_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        查询策略历史选股结果
        
        Args:
            strategy_id: 策略ID
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量
            
        Returns:
            List[Dict]: 历史选股结果
        """
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        r.trade_date,
                        r.batch_id,
                        r.strategy_id,
                        r.total_count,
                        AVG(d.pct_chg) as avg_return,
                        COUNT(*) as stock_count
                    FROM stock_selection_result r
                    JOIN stock_selection_detail d ON r.batch_id = d.batch_id
                    WHERE r.strategy_id = %s
                """
                params = [strategy_id]
                
                if start_date:
                    sql += " AND r.trade_date >= %s"
                    params.append(datetime.strptime(start_date, '%Y%m%d').date())
                
                if end_date:
                    sql += " AND r.trade_date <= %s"
                    params.append(datetime.strptime(end_date, '%Y%m%d').date())
                
                sql += """
                    GROUP BY r.trade_date, r.batch_id, r.strategy_id, r.total_count
                    ORDER BY r.trade_date DESC
                    LIMIT %s
                """
                params.append(limit)
                
                cursor.execute(sql, params)
                return cursor.fetchall()
    
    def delete_selection(self, batch_id: str) -> bool:
        """
        删除选股结果
        
        Args:
            batch_id: 批次ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # 删除明细
                    cursor.execute(
                        "DELETE FROM stock_selection_detail WHERE batch_id = %s",
                        (batch_id,)
                    )
                    
                    # 删除统计
                    cursor.execute(
                        "DELETE FROM stock_selection_stats WHERE batch_id = %s",
                        (batch_id,)
                    )
                    
                    # 删除主表
                    cursor.execute(
                        "DELETE FROM stock_selection_result WHERE batch_id = %s",
                        (batch_id,)
                    )
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"Error deleting selection: {e}")
            return False
