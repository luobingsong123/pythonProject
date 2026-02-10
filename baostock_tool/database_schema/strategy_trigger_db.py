"""
策略触发点位数据库管理模块
用于创建和管理策略触发点位表
以及批量回测汇总结果表
"""

from sqlalchemy import create_engine, text, Column, BigInteger, String, Enum, Date, Integer, JSON, Numeric, TIMESTAMP, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import URL
from baostock_tool import config
import pymysql
from baostock_tool.utils.logger_utils import setup_logger

log_config = config.get_log_config()
logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"])

# 创建基类
Base = declarative_base()


class StrategyTriggerPoints(Base):
    """策略触发点位表
    该模型类既可以用于查询也可以用于写入，它是一个完整的数据库模型定义，支持CRUD（创建、读取、更新、删除）所有操作
    """

    __tablename__ = 'strategy_trigger_points'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    strategy_name = Column(String(100), nullable=False, comment='策略名称')
    stock_code = Column(String(10), nullable=False, comment='证券代码')
    market = Column(Enum('sh', 'sz', 'bj'), nullable=False, default='sh', comment='市场：sh=上海，sz=深圳，bj=北京')
    trigger_points_json = Column(JSON, nullable=False, comment='策略触发的对应日期JSON数据')
    backtest_start_date = Column(Date, nullable=False, comment='策略回测开始日期')
    backtest_end_date = Column(Date, nullable=False, comment='策略回测结束日期')
    trigger_count = Column(Integer, default=0, comment='触发点位数量')
    created_at = Column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP'), comment='创建时间')
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间')

    # 唯一索引：同一策略、同一股票、同一回测时间范围只能有一条记录
    __table_args__ = (
        UniqueConstraint('strategy_name', 'stock_code', 'market', 'backtest_start_date', 'backtest_end_date',
                        name='uk_strategy_stock_backtest'),
        Index('idx_strategy_name', 'strategy_name'),
        Index('idx_stock_code', 'stock_code'),
        Index('idx_market', 'market'),
        Index('idx_created_at', 'created_at'),
        {
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'comment': '策略触发点位表'
        }
    )

    def __repr__(self):
        return (f"<StrategyTriggerPoints(id={self.id}, strategy_name='{self.strategy_name}', "
                f"stock_code='{self.stock_code}', market='{self.market}')>")


class BacktestBatchSummary(Base):
    """批量回测汇总结果表"""

    __tablename__ = 'backtest_batch_summary'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    strategy_name = Column(String(100), nullable=False, comment='策略名称')
    backtest_start_date = Column(Date, nullable=False, comment='回测开始日期')
    backtest_end_date = Column(Date, nullable=False, comment='回测结束日期')
    summary_json = Column(type_=String, nullable=False, comment='汇总结果JSON数据')
    stock_count = Column(Integer, default=0, comment='回测股票数量')
    execution_time = Column(Numeric(12, 4), default=0.00, comment='执行时间（秒）')
    created_at = Column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP'), comment='创建时间')
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间')

    # 唯一索引：同一策略、同一回测时间范围只能有一条记录
    __table_args__ = (
        UniqueConstraint('strategy_name', 'backtest_start_date', 'backtest_end_date',
                        name='uk_strategy_period'),
        Index('idx_strategy_name', 'strategy_name'),
        Index('idx_backtest_period', 'backtest_start_date', 'backtest_end_date'),
        Index('idx_created_at', 'created_at'),
        {
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'comment': '批量回测汇总结果表'
        }
    )

    def __repr__(self):
        return (f"<BacktestBatchSummary(strategy_name='{self.strategy_name}', "
                f"backtest_start_date='{self.backtest_start_date}', "
                f"backtest_end_date='{self.backtest_end_date}')>")


class StrategyTriggerDB:
    """策略触发点位数据库管理类"""

    def __init__(self):
        """初始化数据库连接"""
        db_config_ = config.get_db_config()
        self.db_url = URL.create(
            drivername="mysql+pymysql",
            username=db_config_["user"],
            password=db_config_["password"],
            host=db_config_["host"],
            port=db_config_["port"],
            database=db_config_["database"],
            query={"charset": "utf8mb4"}
        )
        self.engine = create_engine(self.db_url, pool_pre_ping=True, pool_recycle=3600)

    def create_tables(self, drop_existing=False):
        """
        创建所有表（策略触发点位表和批量回测汇总结果表）

        Args:
            drop_existing (bool): 是否删除已存在的表（慎用）

        Returns:
            bool: 是否成功创建
        """
        try:
            if drop_existing:
                BacktestBatchSummary.__table__.drop(self.engine, checkfirst=True)
                StrategyTriggerPoints.__table__.drop(self.engine, checkfirst=True)
                logger.debug("已删除旧表")

            # 创建表（先创建没有外键的表）
            StrategyTriggerPoints.__table__.create(self.engine, checkfirst=True)
            BacktestBatchSummary.__table__.create(self.engine, checkfirst=True)
            logger.debug("所有表创建成功")
            return True
        except Exception as e:
            logger.debug(f"创建表失败: {str(e)}")
            return False

    def create_table(self, drop_existing=False):
        """
        创建策略触发点位表（保留方法以兼容旧代码）

        Args:
            drop_existing (bool): 是否删除已存在的表（慎用）

        Returns:
            bool: 是否成功创建
        """
        try:
            if drop_existing:
                StrategyTriggerPoints.__table__.drop(self.engine, checkfirst=True)
                logger.debug("已删除旧表")

            StrategyTriggerPoints.__table__.create(self.engine, checkfirst=True)
            logger.debug("策略触发点位表创建成功")
            return True
        except Exception as e:
            logger.debug(f"创建表失败: {str(e)}")
            return False

    def insert_trigger_points(self, strategy_name, stock_code, market, trigger_points_json,
                             backtest_start_date, backtest_end_date, trigger_count=None):
        """
        插入策略触发点位数据

        Args:
            strategy_name (str): 策略名称
            stock_code (str): 证券代码
            market (str): 市场 (sh/sz/bj)
            trigger_points_json (list/dict): 触发点位JSON数据
            backtest_start_date (str): 回测开始日期 (YYYY-MM-DD)
            backtest_end_date (str): 回测结束日期 (YYYY-MM-DD)
            trigger_count (int, optional): 触发点位数量，如果为None则自动计算

        Returns:
            bool: 是否插入成功
        """
        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            session = Session()

            # 如果未提供trigger_count，则自动计算
            if trigger_count is None:
                if isinstance(trigger_points_json, (list, dict)):
                    trigger_count = len(trigger_points_json)
                else:
                    trigger_count = 0

            # 检查是否已存在相同记录
            existing = session.query(StrategyTriggerPoints).filter(
                StrategyTriggerPoints.strategy_name == strategy_name,
                StrategyTriggerPoints.stock_code == stock_code,
                StrategyTriggerPoints.market == market,
                StrategyTriggerPoints.backtest_start_date == backtest_start_date,
                StrategyTriggerPoints.backtest_end_date == backtest_end_date
            ).first()

            if existing:
                # 更新现有记录
                existing.trigger_points_json = trigger_points_json
                existing.trigger_count = trigger_count
                session.commit()
                logger.debug(f"更新策略触发点位数据成功: {strategy_name} - {stock_code}")
            else:
                # 插入新记录
                new_record = StrategyTriggerPoints(
                    strategy_name=strategy_name,
                    stock_code=stock_code,
                    market=market,
                    trigger_points_json=trigger_points_json,
                    backtest_start_date=backtest_start_date,
                    backtest_end_date=backtest_end_date,
                    trigger_count=trigger_count
                )
                session.add(new_record)
                session.commit()
                logger.debug(f"插入策略触发点位数据成功: {strategy_name} - {stock_code}")

            session.close()
            return True
        except Exception as e:
            logger.debug(f"插入数据失败: {str(e)}")
            import traceback
            traceback.logger.debug_exc()
            return False

    def query_trigger_points(self, strategy_name=None, stock_code=None, market=None,
                           backtest_start_date=None, backtest_end_date=None):
        """
        查询策略触发点位数据

        Args:
            strategy_name (str, optional): 策略名称
            stock_code (str, optional): 证券代码
            market (str, optional): 市场
            backtest_start_date (str, optional): 回测开始日期
            backtest_end_date (str, optional): 回测结束日期

        Returns:
            list: 查询结果列表
        """
        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            session = Session()

            query = session.query(StrategyTriggerPoints)

            if strategy_name:
                query = query.filter(StrategyTriggerPoints.strategy_name == strategy_name)
            if stock_code:
                query = query.filter(StrategyTriggerPoints.stock_code == stock_code)
            if market:
                query = query.filter(StrategyTriggerPoints.market == market)
            if backtest_start_date:
                query = query.filter(StrategyTriggerPoints.backtest_start_date >= backtest_start_date)
            if backtest_end_date:
                query = query.filter(StrategyTriggerPoints.backtest_end_date <= backtest_end_date)

            results = query.all()
            session.close()
            return results
        except Exception as e:
            logger.debug(f"查询数据失败: {str(e)}")
            return []

    def get_statistics(self):
        """
        获取统计信息

        Returns:
            dict: 统计信息字典
        """
        try:
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy import func
            Session = sessionmaker(bind=self.engine)
            session = Session()

            # 策略数量
            strategy_count = session.query(
                func.count(func.distinct(StrategyTriggerPoints.strategy_name))
            ).scalar()

            # 股票数量
            stock_count = session.query(
                func.count(func.distinct(StrategyTriggerPoints.stock_code))
            ).scalar()

            # 总记录数
            total_records = session.query(func.count(StrategyTriggerPoints.id)).scalar()

            # 总触发次数
            total_triggers = session.query(func.sum(StrategyTriggerPoints.trigger_count)).scalar() or 0

            # 各策略统计
            strategy_stats = session.query(
                StrategyTriggerPoints.strategy_name,
                func.count(StrategyTriggerPoints.id).label('stock_count'),
                func.sum(StrategyTriggerPoints.trigger_count).label('total_triggers')
            ).group_by(StrategyTriggerPoints.strategy_name).all()

            session.close()

            return {
                'strategy_count': strategy_count,
                'stock_count': stock_count,
                'total_records': total_records,
                'total_triggers': total_triggers,
                'strategy_stats': [
                    {
                        'strategy_name': stat.strategy_name,
                        'stock_count': stat.stock_count,
                        'total_triggers': stat.total_triggers
                    }
                    for stat in strategy_stats
                ]
            }
        except Exception as e:
            logger.debug(f"获取统计信息失败: {str(e)}")
            return {}

    # ============ 批量回测汇总结果相关方法 ============

    def insert_or_update_summary(self, strategy_name, backtest_start_date, backtest_end_date,
                                 summary_json, stock_count=0, execution_time=0.0):
        """
        插入或更新批量回测汇总结果

        Args:
            strategy_name (str): 策略名称
            backtest_start_date (str): 回测开始日期 (YYYY-MM-DD)
            backtest_end_date (str): 回测结束日期 (YYYY-MM-DD)
            summary_json (dict/list/str): 汇总结果JSON数据（字典、列表或JSON字符串）
            stock_count (int): 回测股票数量
            execution_time (float): 执行时间（秒）

        Returns:
            bool: 是否成功插入或更新
        """
        try:
            from sqlalchemy.orm import sessionmaker
            import json
            Session = sessionmaker(bind=self.engine)
            session = Session()

            # 转换summary_json为JSON字符串
            if isinstance(summary_json, (dict, list)):
                summary_json_str = json.dumps(summary_json, ensure_ascii=False)
            else:
                summary_json_str = str(summary_json)

            # 检查是否已存在相同记录
            existing = session.query(BacktestBatchSummary).filter(
                BacktestBatchSummary.strategy_name == strategy_name,
                BacktestBatchSummary.backtest_start_date == backtest_start_date,
                BacktestBatchSummary.backtest_end_date == backtest_end_date
            ).first()

            if existing:
                # 更新现有记录
                existing.summary_json = summary_json_str
                existing.stock_count = stock_count
                existing.execution_time = execution_time
                session.commit()
                logger.debug(f"更新批量回测汇总成功: {strategy_name} - {backtest_start_date}至{backtest_end_date}")
            else:
                # 插入新记录
                new_record = BacktestBatchSummary(
                    strategy_name=strategy_name,
                    backtest_start_date=backtest_start_date,
                    backtest_end_date=backtest_end_date,
                    summary_json=summary_json_str,
                    stock_count=stock_count,
                    execution_time=execution_time
                )
                session.add(new_record)
                session.commit()
                logger.debug(f"插入批量回测汇总成功: {strategy_name} - {backtest_start_date}至{backtest_end_date}")

            session.close()
            return True
        except Exception as e:
            logger.debug(f"插入或更新汇总结果失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def query_summary(self, strategy_name=None, backtest_start_date=None, backtest_end_date=None):
        """
        查询批量回测汇总结果

        Args:
            strategy_name (str, optional): 策略名称
            backtest_start_date (str, optional): 回测开始日期
            backtest_end_date (str, optional): 回测结束日期

        Returns:
            list: 查询结果列表
        """
        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            session = Session()

            query = session.query(BacktestBatchSummary)

            if strategy_name:
                query = query.filter(BacktestBatchSummary.strategy_name == strategy_name)
            if backtest_start_date:
                query = query.filter(BacktestBatchSummary.backtest_start_date >= backtest_start_date)
            if backtest_end_date:
                query = query.filter(BacktestBatchSummary.backtest_end_date <= backtest_end_date)

            results = query.order_by(BacktestBatchSummary.created_at.desc()).all()
            session.close()
            return results
        except Exception as e:
            logger.debug(f"查询汇总结果失败: {str(e)}")
            return []

    def get_summary(self, strategy_name, backtest_start_date, backtest_end_date):
        """
        获取指定策略和时间段的汇总结果

        Args:
            strategy_name (str): 策略名称
            backtest_start_date (str): 回测开始日期
            backtest_end_date (str): 回测结束日期

        Returns:
            BacktestBatchSummary: 汇总结果对象，不存在则返回None
        """
        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            session = Session()

            result = session.query(BacktestBatchSummary).filter(
                BacktestBatchSummary.strategy_name == strategy_name,
                BacktestBatchSummary.backtest_start_date == backtest_start_date,
                BacktestBatchSummary.backtest_end_date == backtest_end_date
            ).first()

            session.close()
            return result
        except Exception as e:
            logger.debug(f"获取汇总结果失败: {str(e)}")
            return None

    def delete_summary(self, strategy_name, backtest_start_date, backtest_end_date):
        """
        删除指定策略和时间段的汇总结果

        Args:
            strategy_name (str): 策略名称
            backtest_start_date (str): 回测开始日期
            backtest_end_date (str): 回测结束日期

        Returns:
            bool: 是否删除成功
        """
        try:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.engine)
            session = Session()

            count = session.query(BacktestBatchSummary).filter(
                BacktestBatchSummary.strategy_name == strategy_name,
                BacktestBatchSummary.backtest_start_date == backtest_start_date,
                BacktestBatchSummary.backtest_end_date == backtest_end_date
            ).delete()

            session.commit()
            session.close()
            logger.debug(f"删除汇总结果: {count} 条记录")
            return count > 0
        except Exception as e:
            logger.debug(f"删除汇总结果失败: {str(e)}")
            return False

    def exists_summary(self, strategy_name, backtest_start_date, backtest_end_date):
        """
        检查是否存在指定策略和时间段的汇总结果

        Args:
            strategy_name (str): 策略名称
            backtest_start_date (str): 回测开始日期
            backtest_end_date (str): 回测结束日期

        Returns:
            bool: 是否存在
        """
        return self.get_summary(strategy_name, backtest_start_date, backtest_end_date) is not None

    def get_all_strategies(self):
        """
        获取所有策略名称列表

        Returns:
            list: 策略名称列表
        """
        try:
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy import func
            Session = sessionmaker(bind=self.engine)
            session = Session()

            strategies = session.query(
                func.distinct(BacktestBatchSummary.strategy_name)
            ).order_by(BacktestBatchSummary.strategy_name).all()

            session.close()
            return [s[0] for s in strategies]
        except Exception as e:
            logger.debug(f"获取策略列表失败: {str(e)}")
            return []

    def get_summary_statistics(self):
        """
        获取批量回测汇总统计信息

        Returns:
            dict: 统计信息字典
        """
        try:
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy import func
            Session = sessionmaker(bind=self.engine)
            session = Session()

            # 总回测批次数
            total_batches = session.query(func.count(BacktestBatchSummary.id)).scalar()

            # 策略数量
            strategy_count = session.query(
                func.count(func.distinct(BacktestBatchSummary.strategy_name))
            ).scalar()

            # 总回测股票数
            total_stocks = session.query(func.sum(BacktestBatchSummary.stock_count)).scalar() or 0

            # 总执行时间
            total_time = session.query(func.sum(BacktestBatchSummary.execution_time)).scalar() or 0

            session.close()

            return {
                'total_batches': total_batches,
                'strategy_count': strategy_count,
                'total_stocks': total_stocks,
                'total_time': float(total_time)
            }
        except Exception as e:
            logger.debug(f"获取汇总统计信息失败: {str(e)}")
            return {}


# 使用示例
if __name__ == "__main__":
    import json

    # 创建数据库管理实例
    db = StrategyTriggerDB()

    # 创建所有表（首次运行时使用）
    # db.create_tables(drop_existing=False)

    # ========== 策略触发点位示例 ==========
    # 插入示例数据
    trigger_data = [
        {
            "date": "2024-01-05",
            "trigger_type": "buy",
            "price": 3.52,
            "volume": 1250000,
            "volume_rank": "20日最低"
        },
        {
            "date": "2024-01-08",
            "trigger_type": "sell",
            "price": 3.58,
            "hold_days": 2,
            "profit": 0.06,
            "profit_rate": 1.70
        }
    ]

    db.insert_trigger_points(
        strategy_name="CodeBuddyStrategy",
        stock_code="601288",
        market="sh",
        trigger_points_json=trigger_data,
        backtest_start_date="2024-01-01",
        backtest_end_date="2024-12-31"
    )

    # 查询数据
    results = db.query_trigger_points(strategy_name="CodeBuddyStrategy")
    for result in results:
        logger.debug(f"策略: {result.strategy_name}, 股票: {result.stock_code}, 触发次数: {result.trigger_count}")

    # 获取统计信息
    stats = db.get_statistics()
    logger.debug(f"\n策略触发点位统计信息: {stats}")

    # ========== 批量回测汇总示例 ==========
    # 示例：构建汇总JSON数据
    summary_json = {
        "trading_days_count": 1200,
        "initial_cash": 100000,
        "commission": 0.001,
        "slippage_perc": 0.001,
        "avg_return_rate": 5.23,
        "avg_max_drawdown": 8.45,
        "profit_stock_count": 650,
        "loss_stock_count": 350,
        "profit_ratio": 65.0,
        "total_trade_count": 15000,
        "total_profit_trade_count": 8500,
        "total_loss_trade_count": 6500,
        "win_rate": 56.67,
        "total_commission": 2500000.00,
        "total_buy_commission": 1250000.00,
        "total_sell_commission": 1250000.00,
        "commission_ratio": 2.50,
        "max_return_rate": 35.50,
        "min_return_rate": -15.20,
        "max_sharpe_ratio": 1.85,
        "avg_sharpe_ratio": 0.85,
        "csv_file_path": "csv/backtest_summary_20200101_to_20251220.csv",
        "execution_time": 3600.5,
        "avg_time_per_stock": 3.6005,
        "created_at": "2024-01-22 10:30:00",
        "created_by": "batch_backtest"
    }

    # 插入或更新汇总结果
    db.insert_or_update_summary(
        strategy_name="CodeBuddyStrategyDFX",
        backtest_start_date="2020-01-01",
        backtest_end_date="2025-12-20",
        summary_json=summary_json,
        stock_count=1000,
        execution_time=3600.5
    )

    # 查询汇总结果
    summary_results = db.query_summary(strategy_name="CodeBuddyStrategyDFX")
    for result in summary_results:
        logger.debug(f"策略: {result.strategy_name}")
        logger.debug(f"回测期间: {result.backtest_start_date} 至 {result.backtest_end_date}")
        logger.debug(f"股票数量: {result.stock_count}")
        logger.debug(f"执行时间: {result.execution_time} 秒")
        # 解析JSON数据
        summary_data = json.loads(result.summary_json)
        logger.debug(f"平均收益率: {summary_data.get('avg_return_rate')}%")
        logger.debug(f"盈利占比: {summary_data.get('profit_ratio')}%")
        logger.debug("-" * 60)

    # 检查是否存在
    exists = db.exists_summary("CodeBuddyStrategyDFX", "2020-01-01", "2025-12-20")
    logger.debug(f"是否存在该汇总记录: {exists}")

    # 获取所有策略
    strategies = db.get_all_strategies()
    logger.debug(f"所有策略: {strategies}")

    # 获取汇总统计信息
    summary_stats = db.get_summary_statistics()
    logger.debug(f"汇总统计信息: {summary_stats}")
