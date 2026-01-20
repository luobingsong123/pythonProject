"""
策略触发点位可视化Web应用
提供策略、证券代码、回测时段、触发点位的层级查询界面
"""

from flask import Flask, render_template, jsonify, request
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baostock_tool.database_schema.strategy_trigger_db import StrategyTriggerDB
from baostock_tool.utils.trigger_points_reader import TriggerPointsReader
from baostock_tool import config

app = Flask(__name__)

# 初始化数据库管理器和数据读取器
db_manager = StrategyTriggerDB()
reader = TriggerPointsReader()


def determine_market_by_code(stock_code):
    """
    根据证券代码自动判断市场
    参数:
        stock_code: 证券代码（6位数字）
    返回:
        市场代码：'sh' 或 'sz'
    """
    # 沪市股票代码规则：
    # 600000-604999: 沪市主板
    # 605000-605999: 科创板
    # 688000-688999: 科创板
    # 689000-689999: 科创板
    # 688689: 特殊
    # 北交所：83、87、43开头
    # 深市股票代码规则：
    # 000000-001999: 深市主板
    # 002000-002999: 中小板
    # 003000-003999: 深市主板
    # 300000-300999: 创业板
    # 301000-301999: 创业板

    if not stock_code or len(stock_code) != 6:
        return 'sh'  # 默认返回沪市

    code_num = stock_code[:3]

    # 沪市代码
    if code_num in ['600', '601', '602', '603', '604', '605', '688', '689']:
        return 'sh'
    # 北交所代码
    # elif code_num in ['830', '831', '832', '833', '834', '835', '836', '837', '838', '839',
    #                  '870', '871', '872', '873', '874', '875', '876', '877', '878', '879',
    #                  '430', '431', '432', '433', '434', '435', '436', '437', '438', '439']:
    #     return 'bj'
    # 深市代码
    else:
        return 'sz'


def get_stock_data_from_db(stock_code="601288", market="sh", buy_date="2019-01-01", sell_date=None):
    """
    从数据库获取股票K线数据
    参数:
        stock_code: 证券代码
        market: 市场（sh/sz/bj）
        buy_date: 买入日期
        sell_date: 卖出日期（可选）
    """
    try:
        # 获取数据库引擎
        db_config = config.get_db_config()
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import URL

        db_url = URL.create(
            drivername="mysql+pymysql",
            username=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            query={"charset": "utf8mb4"}
        )

        engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)

        # 计算查询时间范围
        buy_dt = datetime.strptime(buy_date, "%Y-%m-%d")

        # 当存在卖出点位时，展示买入前30个交易日到卖出后30个交易日之间的数据
        # 当卖出点位不存在时，保留原展示逻辑（买入前后38个交易日，约60个自然日）
        if sell_date:
            sell_dt = datetime.strptime(sell_date, "%Y-%m-%d")
            # 买入前30个交易日约42个自然日，卖出后30个交易日约42个自然日
            query_start_date = (buy_dt - timedelta(days=42)).strftime("%Y-%m-%d")
            query_end_date = (sell_dt + timedelta(days=42)).strftime("%Y-%m-%d")
        else:
            # 原逻辑：买入日期前后38个交易日，约60个自然日
            query_start_date = (buy_dt - timedelta(days=60)).strftime("%Y-%m-%d")
            query_end_date = (buy_dt + timedelta(days=60)).strftime("%Y-%m-%d")

        # 使用SQLAlchemy连接查询（限制在买入日期前后的时间范围内）
        query = f"""
        SELECT date, open, high, low, close, volume, amount, pctChg
        FROM stock_daily_data
        WHERE market = '{market}'
          AND code_int = '{int(stock_code)}'
          AND frequency = 'd'
          AND date >= '{query_start_date}'
          AND date <= '{query_end_date}'
        ORDER BY date
        """

        df = pd.read_sql(query, engine)

        # 数据清洗与格式化
        if df.empty:
            return []

        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df = df.ffill()  # 前向填充缺失值

        # 转换为列表格式
        result = []
        for idx, row in df.iterrows():
            result.append({
                'date': idx.strftime('%Y-%m-%d'),
                'open': float(row['open']) if pd.notna(row['open']) else 0,
                'high': float(row['high']) if pd.notna(row['high']) else 0,
                'low': float(row['low']) if pd.notna(row['low']) else 0,
                'close': float(row['close']) if pd.notna(row['close']) else 0,
                'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
                'amount': float(row['amount']) if pd.notna(row['amount']) else 0,
                'pctChg': float(row['pctChg']) if pd.notna(row['pctChg']) else 0
            })

        return result

    except Exception as e:
        print(f"查询K线数据失败: {str(e)}")
        return []


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/strategies')
def get_strategies():
    """获取策略名称列表"""
    try:
        # 查询所有策略名称
        results = db_manager.query_trigger_points()
        strategies = list(set([r.strategy_name for r in results if r.strategy_name]))
        strategies.sort()

        return jsonify({
            'success': True,
            'data': strategies
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/stocks')
def get_stocks():
    """
    获取指定策略的证券代码列表
    参数:
        - strategy: 策略名称（可选）
        - stock_code: 证券代码（可选，支持6位代码或带市场前缀的格式，如 "000700" 或 "sh.601288"）
    """
    try:
        strategy_name = request.args.get('strategy', '')
        stock_code_input = request.args.get('stock_code', '')

        # 处理证券代码参数
        stock_code = None
        market = None

        if stock_code_input:
            # 解析证券代码
            if '.' in stock_code_input:
                parts = stock_code_input.split('.')
                market = parts[0]
                stock_code = parts[1]
            else:
                # 没有市场前缀，自动判断市场
                market = determine_market_by_code(stock_code_input)
                stock_code = stock_code_input

            # 统一格式化为6位字符串（补前导零）
            stock_code = str(stock_code).zfill(6)

        if strategy_name:
            # 查询指定策略的证券代码
            results = db_manager.query_trigger_points(strategy_name=strategy_name)
        else:
            # 查询所有证券代码
            results = db_manager.query_trigger_points()

        # 根据stock_code参数过滤
        if stock_code:
            # 确保数据库中的stock_code也格式化为6位字符串进行比较
            results = [r for r in results if str(r.stock_code).zfill(6) == stock_code]
            if market:
                results = [r for r in results if r.market == market]

        stocks = list(set([f"{r.market}.{r.stock_code}" for r in results]))
        stocks.sort()

        return jsonify({
            'success': True,
            'data': stocks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/backtest_periods')
def get_backtest_periods():
    """
    获取指定策略和证券代码的回测时段列表
    参数:
        - strategy: 策略名称
        - stock_code: 证券代码
    """
    try:
        strategy_name = request.args.get('strategy', '')
        stock_code = request.args.get('stock_code', '')

        if not strategy_name:
            return jsonify({
                'success': False,
                'error': '策略名称不能为空'
            })

        # 解析证券代码（去除市场前缀，如果没有则自动判断）
        market = 'sh'
        code = stock_code
        if '.' in stock_code:
            parts = stock_code.split('.')
            market = parts[0]
            code = parts[1]
        else:
            # 没有市场前缀，自动判断
            market = determine_market_by_code(stock_code)
            code = int(stock_code)


        # 查询数据库获取回测时段
        results = db_manager.query_trigger_points(
            strategy_name=strategy_name,
            stock_code=code,
            market=market
        )

        periods = []
        for r in results:
            start_date = r.backtest_start_date.strftime('%Y-%m-%d')
            end_date = r.backtest_end_date.strftime('%Y-%m-%d')
            period_str = f"{start_date}至{end_date}"
            if period_str not in periods:
                periods.append(period_str)

        periods.sort()

        return jsonify({
            'success': True,
            'data': periods
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/trigger_points')
def get_trigger_points():
    """
    获取指定策略、证券代码、回测时段的触发点位列表
    参数:
        - strategy: 策略名称
        - stock_code: 证券代码
        - backtest_period: 回测时段
    """
    try:
        strategy_name = request.args.get('strategy', '')
        stock_code = request.args.get('stock_code', '')
        backtest_period = request.args.get('backtest_period', '')

        if not strategy_name or not stock_code or not backtest_period:
            return jsonify({
                'success': False,
                'error': '参数不完整'
            })

        # 使用TriggerPointsReader获取格式化数据
        trigger_points = reader.get_backtest_data(
            strategy_name=strategy_name,
            stock_code=stock_code,
            backtest_period=backtest_period
        )

        # 按买入日期排序
        sorted_points = sorted(
            trigger_points.items(),
            key=lambda x: (x[1].get('买入', ''), x[0])
        )

        result = []
        for key, point in sorted_points:
            result.append({
                'key': key,
                'buy_date': point.get('买入', ''),
                'sell_date': point.get('卖出', ''),
                'buy_price': point.get('买入价格', 0),
                'sell_price': point.get('卖出价格', 0),
                'profit_flag': point.get('盈亏标志', 0)
            })

        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/kline_data')
def get_kline_data():
    """
    获取K线数据API
    参数:
        - stock_code: 证券代码（带市场前缀，如 sh.601288）
        - start_date: 买入日期
        - sell_date: 卖出日期（可选）
    """
    try:
        stock_code_full = request.args.get('stock_code', '')
        buy_date = request.args.get('start_date', '')
        sell_date = request.args.get('sell_date', None)

        if not stock_code_full or not buy_date:
            return jsonify({
                'success': False,
                'error': '参数不完整'
            })

        # 解析证券代码（如果没有市场前缀则自动判断）
        market = 'sh'
        stock_code = stock_code_full
        if '.' in stock_code_full:
            parts = stock_code_full.split('.')
            market = parts[0]
            stock_code = parts[1]
        else:
            # 没有市场前缀，自动判断
            market = determine_market_by_code(stock_code_full)
            stock_code = stock_code_full

        # 统一格式化为6位字符串（补前导零）
        stock_code = str(stock_code).zfill(6)

        # 查询K线数据（根据是否有卖出日期决定时间范围）
        kline_data = get_stock_data_from_db(stock_code=stock_code, market=market, buy_date=buy_date, sell_date=sell_date)

        return jsonify({
            'success': True,
            'data': kline_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
