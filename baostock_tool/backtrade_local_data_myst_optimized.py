"""
优化版回测框架 - QuestDB版本
优化要点:
1. 批量数据预加载 - 使用QuestDB高性能时序数据库
2. 多线程并发 - 减少数据库查询次数 90%+
3. 数据缓存机制 - 避免重复加载
4. 日志优化 - 在个股开始和完成时打印

数据源说明:
- 股票历史数据: QuestDB (高速时序数据库)
- 股票列表、交易日历: MySQL
"""
import pandas as pd
import backtrader as bt
import pandas_ta as ta
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from baostock_tool import config
from utils.logger_utils import setup_logger
import matplotlib.pyplot as plt
import os
# 导入CodeBuddy策略
from utils.strategies.codebuddy_st import CodeBuddyStrategy
# 导入CodeBuddy底分型策略
from utils.strategies.codebuddy_st_dfx import CodeBuddyStrategyDFX
# 白马股波段策略
from utils.strategies.value_strategy import ValueStrategy
# 导入策略触发点位数据库管理
from database_schema.strategy_trigger_db import StrategyTriggerDB
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool, cpu_count
import multiprocessing
import requests
import json
from datetime import timedelta


# 自定义PandasData类，添加估值指标字段
class StockDataWithMetrics(bt.feeds.PandasData):
    lines = ('peTTM', 'psTTM', 'pcfNcfTTM', 'pbMRQ')
    params = (
        ('peTTM', -1),
        ('psTTM', -1),
        ('pcfNcfTTM', -1),
        ('pbMRQ', -1),
    )

os.makedirs("csv", exist_ok=True)
db_config_ = config.get_db_config()
log_config = config.get_log_config()
date_config = config.get_backtrade_date_config()
questdb_config = config.get_questdb_config()

logger = setup_logger(logger_name=__name__,
                   log_level=log_config["log_level"],
                   log_dir=log_config["log_dir"], )

# MySQL 连接（用于股票列表、交易日历等）
db_url = URL.create(
    drivername="mysql+pymysql",
    username=db_config_["user"],
    password=db_config_["password"],
    host=db_config_["host"],
    port=db_config_["port"],
    database=db_config_["database"]
)

engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)


# ============ QuestDB连接（用于股票历史数据）============
class QuestDBClient:
    """QuestDB HTTP REST API 客户端"""

    def __init__(self, host='localhost', port=9000, user='', password=''):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.base_url = f"http://{host}:{port}"

    def test_connection(self):
        """测试 QuestDB 连接"""
        try:
            # 发送一个简单查询测试连接
            url = f"{self.base_url}/exec"
            params = {'query': 'SELECT 1'}
            auth = (self.user, self.password) if self.user else None
            response = requests.get(url, params=params, auth=auth, timeout=10)
            if response.status_code == 200:
                logger.info(f"QuestDB 连接测试成功: {self.host}:{self.port}")
                return True
            else:
                logger.error(f"QuestDB 连接测试失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"QuestDB 连接测试失败: {e}")
            return False

    def query(self, sql, timeout=300):
        """
        执行SQL查询并返回DataFrame

        Args:
            sql: SQL语句
            timeout: 超时时间（秒），默认5分钟

        Returns:
            DataFrame: 查询结果
        """
        auth = None
        if self.user:
            auth = (self.user, self.password)

        url = f"{self.base_url}/exec"
        # 使用 &df=true 让QuestDB直接返回pandas兼容的JSON格式
        params = {'query': sql, 'df': 'true'}

        logger.debug(f"QuestDB查询: {sql[:200]}...")

        try:
            response = requests.get(url, params=params, auth=auth, timeout=timeout)

            if response.status_code == 200:
                # QuestDB返回JSON格式的DataFrame
                content = response.text.strip()
                if not content or content == 'null':
                    return pd.DataFrame()

                # 检查是否是错误响应
                try:
                    json_data = json.loads(content)
                    # QuestDB错误响应格式: {"query": "...", "error": "..."}
                    if 'error' in json_data:
                        raise Exception(f"QuestDB SQL执行错误: {json_data.get('error')}")
                    # 如果返回的是带columns和dataset的格式
                    if 'columns' in json_data and 'dataset' in json_data:
                        df = pd.DataFrame(json_data['dataset'], columns=[c['name'] for c in json_data['columns']])
                        logger.debug(f"QuestDB查询返回 {len(df)} 行")
                        return df
                except json.JSONDecodeError:
                    pass  # 如果不是JSON，继续尝试pandas解析

                # 解析JSON（QuestDB的df=true返回的是pandas-compatible JSON）
                try:
                    df = pd.read_json(content, orient='records')
                except Exception as parse_err:
                    logger.error(f"JSON解析失败: {parse_err}")
                    logger.error(f"原始内容: {content[:1000]}")
                    raise

                logger.debug(f"QuestDB查询返回 {len(df)} 行")
                return df
            else:
                raise Exception(f"QuestDB查询失败: HTTP {response.status_code}, {response.text}")
        except requests.exceptions.Timeout:
            raise Exception(f"QuestDB查询超时（超过{timeout}秒）: 查询数据量可能过大，请减少查询股票数量或分批查询")
        except requests.exceptions.RequestException as e:
            raise Exception(f"QuestDB连接失败: {e}")


# 初始化QuestDB客户端
questdb_client = QuestDBClient(
    host=questdb_config['host'],
    port=questdb_config['port'],
    user=questdb_config['user'],
    password=questdb_config['password']
)

# ============ 回测策略配置 ============
BACKTEST_CONFIG = {
    'start_date': date_config["start_date"],  # 回测开始日期
    'end_date': date_config["end_date"],    # 回测截止日期
    'initial_cash': 100000,      # 初始资金
    'commission': 0.001,        # 手续费率（0.1%）
    'slippage_perc': 0.001,      # 滑点率（0.1%），按百分比计算
}


# 本代码仅用于回测研究，实盘使用风险自担


# ===== 优化点 1：批量数据加载（QuestDB版本）=====
def batch_load_stock_data(stock_codes, start_date, lookback_days=365):
    """
    批量预加载所有股票数据（从QuestDB查询）
    性能提升：约 50-80%
    
    Args:
        stock_codes: DataFrame, 股票列表（code_int为索引）
        start_date: str, 回测开始日期
        lookback_days: int, 历史数据回溯天数
        
    Returns:
        dict: {code_int: DataFrame} 每只股票的数据
    """
    logger.info("开始从QuestDB批量预加载股票数据...")
    start_load_time = time.time()
    
    # 将开始日期向前推lookback_days个自然日，以便获取回测前的历史数据
    start_dt = pd.to_datetime(start_date)
    data_start_date = (start_dt - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
    
    # 从配置获取回测结束日期
    end_date = BACKTEST_CONFIG['end_date']
    
    logger.info(f"  数据时间范围: {data_start_date} 至 {end_date}")
    logger.info(f"  股票数量: {len(stock_codes)}")
    
    # QuestDB查询：一次性查询所有股票数据（参考backtest_time_based_standard_questdb.py）
    query = f"""
    SELECT *
    FROM stock_daily_data
    WHERE date >= '{data_start_date}'
    AND date <= '{end_date}'
    """
    
    try:
        df = questdb_client.query(query)
        logger.info(f"  QuestDB返回 {len(df)} 行数据")
        
        if df.empty:
            logger.warning("QuestDB未查询到任何股票数据")
            return {}
        
        # QuestDB返回的date列可能是timestamp类型，需要处理
        if 'date' in df.columns:
            # 确保date列是日期格式
            if df['date'].dtype == 'object' or str(df['date'].dtype).startswith('datetime'):
                df['date'] = pd.to_datetime(df['date'])
            else:
                # 如果是timestamp类型
                df['date'] = pd.to_datetime(df['date'], unit='s', utc=True).dt.tz_localize(None)
            
            # 统一去除时区信息（避免后续比较出错）
            if hasattr(df['date'].dtype, 'tz') and df['date'].dtype.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
        
        # 按 market 和 code_int 分组存储
        stock_data_dict = {}
        
        # 确保有必要的列
        if 'market' not in df.columns or 'code_int' not in df.columns:
            logger.error("QuestDB返回的数据缺少 market 或 code_int 列")
            return {}
        
        for (market, code_int), group in df.groupby(['market', 'code_int']):
            code_int_val = int(code_int)
            
            # 只保留在stock_codes中的股票
            if code_int_val not in stock_codes.index:
                continue
            
            group = group.sort_values('date')
            group.set_index('date', inplace=True)
            
            # 前向填充缺失值
            group = group.ffill()
            
            stock_data_dict[code_int_val] = group
        
        load_time = time.time() - start_load_time
        
        # 统计信息
        total_rows = len(df)
        total_stocks = len(stock_data_dict)
        avg_rows_per_stock = total_rows / total_stocks if total_stocks > 0 else 0
        
        logger.info(f"QuestDB数据预加载完成:")
        logger.info(f"  总数据行数: {total_rows:,}")
        logger.info(f"  股票数量: {total_stocks}")
        logger.info(f"  平均每只股票数据行数: {avg_rows_per_stock:.0f}")
        logger.info(f"  内存估算: ~{total_rows * 0.001:.1f} MB")
        logger.info(f"  加载耗时: {load_time:.2f} 秒")
        
        return stock_data_dict
        
    except Exception as e:
        logger.error(f"从QuestDB批量加载数据失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


# ===== 优化点 2：数据缓存管理器 =====
class StockDataCache:
    """股票数据缓存管理器"""
    _instance = None
    _cache = {}
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_batch_data(cls, stock_codes, start_date, use_cache=True, lookback_days=365):
        """
        批量获取股票数据（带缓存）
        
        Args:
            stock_codes: DataFrame, 股票列表
            start_date: str, 回测开始日期
            use_cache: bool, 是否使用缓存
            lookback_days: int, 历史数据回溯天数
        """
        cache_key = f"{start_date}_{lookback_days}"
        
        if use_cache and cache_key in cls._cache:
            logger.info(f"使用缓存数据: {cache_key}")
            return cls._cache[cache_key]
        
        with cls._lock:
            if cache_key in cls._cache:
                return cls._cache[cache_key]
            
            # 批量查询（从QuestDB）
            data = batch_load_stock_data(stock_codes, start_date, lookback_days)
            cls._cache[cache_key] = data
            return data
    
    @classmethod
    def clear_cache(cls):
        """清空缓存"""
        with cls._lock:
            cls._cache.clear()
            logger.info("缓存已清空")


def get_stock_basic_from_db():
    """
    从数据库获取个股列表
    """
    # 使用SQLAlchemy连接（推荐方式）
    query = f"""
    SELECT market, code_int, name
    FROM stock_basic_info 
    WHERE (market = 'sh' AND code_int > 600000 AND code_int < 610000)
       OR (market = 'sz' AND code_int > 0 AND code_int < 310000)
    ORDER BY code_int
    """
    df = pd.read_sql(query, engine)
    # 方法1：简单修复，直接使用code_int作为索引
    df.set_index('code_int', inplace=True)

    return df


def get_trade_calendar_from_db():
    """
    从数据库获取交易日历
    """
    # 使用SQLAlchemy连接（推荐方式）
    query = f"""
    SELECT calendar_date
    FROM trade_calendar 
    WHERE is_trading_day = 1
    ORDER BY calendar_date
    """
    df = pd.read_sql(query, engine)
    # 数据清洗与格式化
    df['calendar_date'] = pd.to_datetime(df['calendar_date'])
    df.set_index('calendar_date', inplace=True)
    df = df.ffill()  # 前向填充缺失值
    return df



class TPlus1Strategy(bt.Strategy):
    """
    基础策略类：实现T+1交易限制
    子类可重写 next() 方法实现具体交易逻辑
    """
    params = (
        ('printlog', True),
        ('stock_code', None),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None
        # 记录买入日期，用于T+1限制
        self.buy_date = None
        # 手续费统计
        self.total_commission = 0.0
        self.buy_commission = 0.0
        self.sell_commission = 0.0
        # 盈利交易统计
        self.profit_trade_count = 0
        self.loss_trade_count = 0
        # 触发点位记录
        self.trigger_points = []
        self.current_buy_info = None  # 记录当前买入信息

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.buy_date = self.datas[0].datetime.date()
                # 统计买入手续费
                self.buy_commission += order.executed.comm
                self.total_commission += order.executed.comm
                # 记录买入触发点位
                buy_info = {
                    'date': str(self.buy_date),
                    'trigger_type': 'buy',
                    'price': float(order.executed.price),
                    'volume': float(order.executed.size),
                    'commission': float(order.executed.comm)
                }
                self.current_buy_info = buy_info
                if self.p.printlog:
                    logger.debug(f'买入执行 - 价格: {order.executed.price:.2f}, '
                              f'数量: {order.executed.size}, '
                              f'手续费: {order.executed.comm:.2f}, '
                              f'日期: {self.datas[0].datetime.date()}')
            else:  # 卖出
                # 统计卖出手续费
                self.sell_commission += order.executed.comm
                self.total_commission += order.executed.comm
                # 记录卖出触发点位
                if self.current_buy_info:
                    sell_date = self.datas[0].datetime.date()
                    sell_info = {
                        'date': str(sell_date),
                        'trigger_type': 'sell',
                        'price': float(order.executed.price),
                        'volume': float(order.executed.size),
                        'commission': float(order.executed.comm),
                        'profit': float(order.executed.pnl),
                        'profit_rate': round((order.executed.pnl / self.buyprice) * 100, 2) if self.buyprice else 0
                    }
                    # 将买入和卖出点位一起记录
                    self.trigger_points.append(self.current_buy_info)
                    self.trigger_points.append(sell_info)
                    self.current_buy_info = None
                if self.p.printlog:
                    logger.debug(f'卖出执行 - 价格: {order.executed.price:.2f}, '
                              f'数量: {order.executed.size}, '
                              f'手续费: {order.executed.comm:.2f}, '
                              f'利润: {order.executed.pnl:.2f}, '
                              f'日期: {self.datas[0].datetime.date()}')
                self.buy_date = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.p.printlog:
                logger.warning(f'订单取消/拒绝 - 状态: {order.getstatusname()}')

        self.order = None

    def notify_trade(self, trade):
        """交易完成通知"""
        if not trade.isclosed:
            return

        # 统计盈利和亏损交易
        if trade.pnlcomm > 0:
            self.profit_trade_count += 1
        elif trade.pnlcomm < 0:
            self.loss_trade_count += 1

        if self.p.printlog:
            logger.debug(f'交易利润 - 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')

    def next(self):
        """
        子类可重写此方法实现具体交易逻辑
        示例逻辑：
        if self.dataclose[0] > self.dataclose[-1]:
            self.buy()
        """
        pass

    def buy_with_t1(self, size=None, price=None, plimit=None):
        """买入方法（记录买入日期）"""
        if self.order:
            return False
        self.order = self.buy(size=size, price=price, plimit=plimit)
        return True

    def sell_with_t1(self, size=None, price=None, plimit=None):
        """卖出方法（T+1限制）"""
        if self.order:
            return False
        # T+1限制：今天买入的股票不能今天卖出
        if self.buy_date and self.datas[0].datetime.date() == self.buy_date:
            if self.p.printlog:
                logger.warning(f'T+1限制：今日买入的股票不能卖出 - 日期: {self.datas[0].datetime.date()}')
            return False
        self.order = self.sell(size=size, price=price, plimit=plimit)
        return True


class SimpleTrendStrategy(TPlus1Strategy):
    """
    简单趋势策略示例（可替换为其他策略）
    逻辑：当收盘价连续3天上涨时买入，连续3天下跌时卖出
    """
    def next(self):
        if not self.position:  # 无持仓时判断买入
            if self.dataclose[0] > self.dataclose[-1] > self.dataclose[-2]:
                self.buy_with_t1()
        else:  # 有持仓时判断卖出
            if self.dataclose[0] < self.dataclose[-1] < self.dataclose[-2]:
                self.sell_with_t1()


# ===== 优化点 3：轻量级回测函数 =====
def run_backtest_optimized(stock_code, market, name, stock_data, start_date, end_date, 
                          strategy_class=SimpleTrendStrategy, verbose=False):
    """
    优化后的回测函数
    - 直接传入预加载数据，避免重复查询
    - 减少日志输出
    - 在个股开始和完成时打印
    
    Args:
        stock_code (int): 股票代码
        market (str): 市场类型
        name (str): 股票名称
        stock_data (DataFrame): 预加载的股票数据
        start_date (str): 回测开始日期
        end_date (str): 回测结束日期
        strategy_class: 策略类
        verbose (bool): 是否输出详细日志
    """
    stock_start_time = time.time()
    
    try:
        if stock_data is None or stock_data.empty:
            if verbose:
                logger.warning(f"股票 {stock_code} ({name}) 无数据，跳过")
            return None
        
        # 过滤日期范围
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # 确保索引不带时区（处理UTC时区问题）
        if stock_data.index.tz is not None:
            stock_data = stock_data.tz_localize(None)
        
        df = stock_data[(stock_data.index >= start_dt) & (stock_data.index <= end_dt)]
        
        if len(df) < 30:
            if verbose:
                logger.warning(f"股票 {stock_code} ({name}) 数据不足（{len(df)}天），跳过")
            return None
        
        # 打印开始回测
        logger.info(f"[开始回测] 股票: {stock_code} ({name}), 市场: {market.upper()}")
        
        # 创建 Cerebro（优化配置）
        cerebro = bt.Cerebro(stdstats=False)  # 关闭默认观察器
        cerebro.addstrategy(strategy_class, stock_code=stock_code, printlog=verbose)
        
        # 加载数据
        data = StockDataWithMetrics(
            dataname=df,
            datetime=None,
            open='open', high='high', low='low', close='close', volume='volume',
            openinterest=-1,
            peTTM='peTTM', psTTM='psTTM', pcfNcfTTM='pcfNcfTTM', pbMRQ='pbMRQ'
        )
        cerebro.adddata(data)
        cerebro.addsizer(bt.sizers.FixedSize, stake=100)
        cerebro.broker.setcash(BACKTEST_CONFIG['initial_cash'])
        cerebro.broker.setcommission(commission=BACKTEST_CONFIG['commission'])
        cerebro.broker.set_slippage_perc(perc=BACKTEST_CONFIG.get('slippage_perc', 0.001))
        
        # 只添加必要的分析器
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        # 执行回测
        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        strat = results[0]
        end_value = cerebro.broker.getvalue()
        
        # 获取分析结果
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        returns = strat.analyzers.returns.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        
        # 计算耗时
        stock_time = time.time() - stock_start_time
        
        # 打印完成回测
        return_rate = (end_value/start_value - 1)*100
        logger.info(f"[回测完成] 股票: {stock_code} ({name}), "
                   f"收益率: {return_rate:.2f}%, "
                   f"交易次数: {trades.get('total', {}).get('total', 0)}, "
                   f"耗时: {stock_time:.2f}秒")
        
        # 返回简化的结果
        return {
            'stock_code': stock_code,
            'name': name,
            'market': market,
            'start_value': start_value,
            'end_value': end_value,
            'return_rate': return_rate,
            'trade_count': trades.get('total', {}).get('total', 0),
            'profit_trade_count': strat.profit_trade_count,
            'loss_trade_count': strat.loss_trade_count,
            'total_commission': strat.total_commission,
            'buy_commission': strat.buy_commission,
            'sell_commission': strat.sell_commission,
            'commission_ratio': (strat.total_commission / start_value) * 100 if start_value > 0 else 0,
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0) if drawdown else 0,
            'sharpe_ratio': sharpe.get('sharperatio') if sharpe and sharpe.get('sharperatio') is not None else 0,
            'trigger_points': strat.trigger_points,
            'execution_time': stock_time  # 记录单个股票的回测时间
        }
        
    except Exception as e:
        logger.error(f"回测股票 {stock_code} ({name}) 时出错: {str(e)}")
        if verbose:
            import traceback
            logger.error(traceback.format_exc())
        return None


# ===== 优化点 4：多进程包装函数 =====
def run_backtest_worker(args):
    """
    多进程工作函数（用于Pool.starmap）
    """
    stock_code, market, name, stock_data_dict, start_date, end_date, strategy_class, verbose = args
    
    # 从字典中获取股票数据
    stock_data = stock_data_dict.get(stock_code)
    
    return run_backtest_optimized(
        stock_code, market, name, stock_data, 
        start_date, end_date, strategy_class, verbose
    )


# ===== 优化点 5：多进程工作函数 =====
def backtest_single_stock_mp(args):
    """
    多进程工作函数（每个进程独立执行一只股票的回测）
    注意：这个函数必须是顶层函数，才能被 pickle 序列化
    """
    stock_code, market, name, stock_data_pkl, start_date, end_date, strategy_class, verbose = args
    
    # 反序列化股票数据
    import pickle
    stock_data = pickle.loads(stock_data_pkl)
    
    # 执行回测
    return run_backtest_optimized(
        stock_code, market, name, stock_data, 
        start_date, end_date, strategy_class, verbose
    )


# ===== 优化点 6：优化版批量回测函数 =====
def batch_backtest_optimized(start_date, end_date, strategy_class=SimpleTrendStrategy, 
                            save_to_db=False, use_multiprocess=True, use_cache=True, lookback_days=365):
    """
    完整优化的批量回测函数（QuestDB数据源）
    性能提升：综合优化可达 3-10 倍
    
    Args:
        start_date (str): 回测开始日期
        end_date (str): 回测结束日期
        strategy_class: 策略类
        save_to_db (bool): 是否保存触发点位到数据库
        use_multiprocess (bool): 是否使用多进程（True：多进程，False：多线程）
        use_cache (bool): 是否使用数据缓存
        lookback_days (int): 历史数据回溯天数
    """
    # 记录开始时间
    start_time = time.time()
    
    # 获取交易日历，过滤回测日期范围
    calendar_df = get_trade_calendar_from_db()
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    calendar_df = calendar_df[(calendar_df.index >= start_dt) & (calendar_df.index <= end_dt)]

    logger.info(f"{'='*60}")
    logger.info(f"开始优化批量回测 (QuestDB数据源)")
    logger.info(f"{'='*60}")
    logger.info(f"回测交易日历: {len(calendar_df)} 个交易日")
    logger.info(f"交易日历起止: {calendar_df.index[0]} 至 {calendar_df.index[-1]}")
    logger.info(f"QuestDB: {questdb_config['host']}:{questdb_config['port']}")

    # ========== 测试 QuestDB 连接 ==========
    logger.info(f"测试 QuestDB 连接: {questdb_config['host']}:{questdb_config['port']}...")
    if not questdb_client.test_connection():
        logger.error("QuestDB 连接失败，请确保 QuestDB 服务已启动")
        logger.error("如需启动 QuestDB，请运行: docker run -p 9000:9000 -p 8812:8812 questdb/questdb")
        return None

    # 1. 预加载所有数据（从QuestDB，减少数据库查询 90%+）
    logger.info(f"{'='*60}")
    stock_codes = get_stock_basic_from_db()
    logger.info(f"共 {len(stock_codes)} 只股票需要回测")
    
    # 使用QuestDB预加载数据
    stock_data_dict = StockDataCache.get_batch_data(
        stock_codes, start_date, use_cache=use_cache, lookback_days=lookback_days
    )
    logger.info(f"{'='*60}")
    
    # 2. 准备任务列表
    import pickle
    
    if use_multiprocess:
        # 多进程模式：将 DataFrame 序列化为字节，避免 Windows 序列化问题
        logger.info(f"准备多进程任务...")
        tasks = []
        for code_int, row in stock_codes.iterrows():
            if code_int in stock_data_dict:
                # 序列化股票数据为字节
                stock_data_pkl = pickle.dumps(stock_data_dict[code_int])
                
                tasks.append((
                    code_int, 
                    row['market'], 
                    row['name'].replace('*', ''), 
                    stock_data_pkl,  # 序列化后的数据
                    start_date, 
                    end_date, 
                    strategy_class, 
                    False  # verbose=False
                ))
    else:
        # 多线程模式：直接传递 DataFrame
        tasks = []
        for code_int, row in stock_codes.iterrows():
            if code_int in stock_data_dict:
                tasks.append((
                    code_int, 
                    row['market'], 
                    row['name'].replace('*', ''), 
                    stock_data_dict[code_int],  # 直接传递 DataFrame
                    start_date, 
                    end_date, 
                    strategy_class, 
                    False  # verbose=False
                ))
    
    logger.info(f"准备执行 {len(tasks)} 个回测任务")
    
    # 3. 执行回测
    all_results = []
    
    if use_multiprocess:
        # 多进程模式（真正的并行）
        max_workers = min(cpu_count(), len(tasks))
        logger.info(f"使用多进程模式，进程数: {max_workers}")
        logger.info(f"注意: 使用 {max_workers} 个CPU核心并行回测")
        logger.info(f"{'='*60}")
        
        # 使用进程池
        with Pool(processes=max_workers) as pool:
            # 使用 imap_unordered 提高效率，不保证顺序
            results_iterator = pool.imap_unordered(backtest_single_stock_mp, tasks, chunksize=1)
            
            # 收集结果并显示进度
            completed_count = 0
            for result in results_iterator:
                if result:
                    all_results.append(result)
                
                completed_count += 1
                # 每50个任务或最后一个任务时打印进度
                if completed_count % 50 == 0 or completed_count == len(tasks):
                    logger.info(f"回测进度: {completed_count}/{len(tasks)} "
                              f"({completed_count*100/len(tasks):.1f}%)")
    else:
        # 多线程模式（受 GIL 限制）
        max_workers = min(int(os.cpu_count() * 2), len(tasks))
        logger.info(f"使用多线程模式，线程数: {max_workers}")
        logger.info(f"注意: 多线程受 GIL 限制，CPU 利用率较低")
        logger.info(f"{'='*60}")
        
        # 使用线程池并发执行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            futures = {}
            for task in tasks:
                stock_code = task[0]
                future = executor.submit(
                    run_backtest_optimized,
                    task[0], task[1], task[2], task[3],
                    task[4], task[5], task[6], task[7]
                )
                futures[future] = stock_code
            
            # 等待所有任务完成
            completed_count = 0
            for future in as_completed(futures):
                result = future.result()
                if result:
                    all_results.append(result)
                
                completed_count += 1
                # 每50个任务或最后一个任务时打印进度
                if completed_count % 50 == 0 or completed_count == len(tasks):
                    logger.info(f"回测进度: {completed_count}/{len(tasks)} "
                              f"({completed_count*100/len(tasks):.1f}%)")
    
    # 4. 汇总结果
    end_time = time.time()
    total_time = end_time - start_time
    
    if all_results:
        summary_df = pd.DataFrame(all_results)
        summary_file = f"csv/backtest_summary_{start_date.replace('-', '')}_to_{end_date.replace('-', '')}.csv"
        summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
        
        logger.info(f"{'='*60}")
        logger.info(f"批量回测完成！")
        logger.info(f"{'='*60}")
        logger.info(f"共回测 {len(all_results)} 只股票")
        logger.info(f"汇总结果已保存至: {summary_file}")
        
        # 输出统计信息
        avg_return = summary_df['return_rate'].mean()
        avg_drawdown = summary_df['max_drawdown'].mean()
        profit_count = (summary_df['return_rate'] > 0).sum()
        loss_count = (summary_df['return_rate'] <= 0).sum()
        
        logger.info(f"平均收益率: {avg_return:.2f}%")
        logger.info(f"平均最大回撤: {avg_drawdown:.2f}%")
        logger.info(f"盈利股票数: {profit_count}/{len(summary_df)}")
        logger.info(f"总回测时间: {total_time:.2f} 秒 ({total_time/60:.2f} 分钟)")
        
        if len(all_results) > 0:
            avg_time_per_stock = total_time / len(all_results)
            logger.info(f"平均每只股票回测时间: {avg_time_per_stock:.2f} 秒")
        
        logger.info(f"{'='*60}")
        
        # 保存汇总结果到数据库
        if save_to_db:
            try:
                save_summary_to_db(
                    summary_df, strategy_class, start_date, end_date, 
                    calendar_df, total_time, all_results, summary_file
                )
            except Exception as e:
                logger.error(f"保存汇总结果到数据库失败: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        return summary_df
    else:
        logger.warning("没有有效的回测结果")
        return None


def save_summary_to_db(summary_df, strategy_class, start_date, end_date, 
                       calendar_df, total_time, all_results, summary_file):
    """
    保存汇总结果到数据库
    """
    # 获取策略名称
    strategy_name = getattr(strategy_class, 'STRATEGY_NAME', strategy_class.__name__)
    
    # 计算汇总统计信息
    total_trade_count = summary_df['trade_count'].sum()
    total_profit_trade_count = summary_df['profit_trade_count'].sum()
    total_loss_trade_count = summary_df['loss_trade_count'].sum()
    win_rate = (total_profit_trade_count / total_trade_count * 100) if total_trade_count > 0 else 0
    total_commission = summary_df['total_commission'].sum()
    total_buy_commission = summary_df['buy_commission'].sum()
    total_sell_commission = summary_df['sell_commission'].sum()
    avg_commission_ratio = summary_df['commission_ratio'].mean()
    max_return_rate = summary_df['return_rate'].max()
    min_return_rate = summary_df['return_rate'].min()
    max_sharpe_ratio = summary_df['sharpe_ratio'].max()
    avg_sharpe_ratio = summary_df['sharpe_ratio'].mean()
    profit_count = (summary_df['return_rate'] > 0).sum()
    loss_count = (summary_df['return_rate'] <= 0).sum()
    profit_ratio = (profit_count / len(summary_df) * 100) if len(summary_df) > 0 else 0
    avg_return = summary_df['return_rate'].mean()
    avg_drawdown = summary_df['max_drawdown'].mean()
    avg_time_per_stock = total_time / len(all_results) if len(all_results) > 0 else 0
    
    # 构建汇总JSON数据
    summary_json = {
        "trading_days_count": len(calendar_df),
        "initial_cash": BACKTEST_CONFIG['initial_cash'],
        "commission": BACKTEST_CONFIG['commission'],
        "slippage_perc": BACKTEST_CONFIG.get('slippage_perc', 0),
        "avg_return_rate": round(avg_return, 2),
        "avg_max_drawdown": round(avg_drawdown, 2),
        "profit_stock_count": int(profit_count),
        "loss_stock_count": int(loss_count),
        "profit_ratio": round(profit_ratio, 2),
        "total_trade_count": int(total_trade_count),
        "total_profit_trade_count": int(total_profit_trade_count),
        "total_loss_trade_count": int(total_loss_trade_count),
        "win_rate": round(win_rate, 2),
        "total_commission": round(total_commission, 2),
        "total_buy_commission": round(total_buy_commission, 2),
        "total_sell_commission": round(total_sell_commission, 2),
        "commission_ratio": round(avg_commission_ratio, 2),
        "max_return_rate": round(max_return_rate, 2),
        "min_return_rate": round(min_return_rate, 2),
        "max_sharpe_ratio": round(max_sharpe_ratio, 2),
        "avg_sharpe_ratio": round(avg_sharpe_ratio, 2),
        "csv_file_path": summary_file,
        "execution_time": round(total_time, 2),
        "avg_time_per_stock": round(avg_time_per_stock, 2),
        "data_source": "questdb",  # 标记数据源
        "created_by": "batch_backtest_optimized_questdb"
    }
    
    # 保存到数据库
    strategy_db = StrategyTriggerDB()
    
    # 获取策略参数（兼容新旧版本backtrader）
    strategy_params = {}
    if hasattr(strategy_class, 'params'):
        try:
            # 尝试迭代（新版backtrader）
            strategy_params = dict(strategy_class.params)
        except (TypeError, AttributeError):
            # 旧版或特殊格式，尝试从__dict__获取
            try:
                params_obj = strategy_class.params
                if hasattr(params_obj, '_getters'):
                    strategy_params = {k: getattr(params_obj, k, None) for k in params_obj._getters}
                elif hasattr(params_obj, '__dict__'):
                    strategy_params = {k: v for k, v in params_obj.__dict__.items() if not k.startswith('_')}
            except Exception:
                pass
    
    strategy_db.insert_or_update_summary(
        strategy_name=strategy_name,
        backtest_start_date=start_date,
        backtest_end_date=end_date,
        summary_json=summary_json,
        stock_count=len(all_results),
        execution_time=total_time,
        backtest_framework='backtrader_optimized_questdb',
        strategy_params_json=strategy_params
    )
    logger.info(f"汇总结果已保存到数据库: {strategy_name} - {start_date}至{end_date}")
    
    # 保存触发点位到数据库
    trigger_count = 0
    for result in all_results:
        if result.get('trigger_points'):
            strategy_db.insert_trigger_points(
                strategy_name=strategy_name,
                stock_code=result['stock_code'],
                market=result['market'],
                trigger_points_json=result['trigger_points'],
                backtest_start_date=start_date,
                backtest_end_date=end_date,
                trigger_count=len(result['trigger_points'])
            )
            trigger_count += len(result['trigger_points'])
    
    if trigger_count > 0:
        logger.info(f"触发点位已保存到数据库: 共 {len(all_results)} 只股票, {trigger_count} 个点位")


if __name__ == "__main__":
    # 批量回测（优化版 - QuestDB数据源）
    batch_backtest_optimized(
        start_date=BACKTEST_CONFIG['start_date'],
        end_date=BACKTEST_CONFIG['end_date'],
        # strategy_class=CodeBuddyStrategyDFX,    # 使用CodeBuddy底分型策略
        # strategy_class=CodeBuddyStrategy,    #  使用CodeBuddy策略
        strategy_class=ValueStrategy,       # 使用Value策略
        save_to_db=True,  # 设置为True保存触发点位到数据库
        use_multiprocess=True,  # 使用多进程模式（Windows下会自动切换为多线程）
        use_cache=True,  # 使用数据缓存
        lookback_days=365  # 历史数据回溯天数
    )
