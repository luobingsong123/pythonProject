"""
回测记录查看器 Web 应用
用于展示 backtest_batch_summary 表中两种不同类型的回测记录：
- time_based: 基于时间的回测汇总展示
- backtrader: 触发点位和K线图展示
"""

from flask import Flask, render_template, jsonify, request
import sys
import os
import json
from datetime import datetime, timedelta
import pandas as pd

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baostock_tool.database_schema.strategy_trigger_db import StrategyTriggerDB
from baostock_tool.utils.trigger_points_reader import TriggerPointsReader
from baostock_tool.webui.app import determine_market_by_code
from baostock_tool import config

app = Flask(__name__)

# 初始化数据库管理器和数据读取器
db_manager = StrategyTriggerDB()
reader = TriggerPointsReader()


def get_kline_data_optimized(stock_code, market, buy_date, sell_date=None):
    """
    从数据库获取股票K线数据（优化版本）
    参数:
        stock_code: 证券代码
        market: 市场（sh/sz/bj）
        buy_date: 买入日期
        sell_date: 卖出日期（可选）
    """
    try:
        # 计算查询时间范围
        buy_dt = datetime.strptime(buy_date, "%Y-%m-%d")

        if sell_date:
            sell_dt = datetime.strptime(sell_date, "%Y-%m-%d")
            query_start_date = (buy_dt - timedelta(days=42)).strftime("%Y-%m-%d")
            query_end_date = (sell_dt + timedelta(days=42)).strftime("%Y-%m-%d")
        else:
            query_start_date = (buy_dt - timedelta(days=60)).strftime("%Y-%m-%d")
            query_end_date = (buy_dt + timedelta(days=60)).strftime("%Y-%m-%d")

        # 优化查询：使用索引提示，只查询必要字段
        # idx_market_code_date 索引覆盖 (market, code_int, date)，配合分区裁剪
        query = f"""
        SELECT date, open, high, low, close, volume, amount, pctChg
        FROM stock_daily_data USE INDEX (idx_market_code_date)
        WHERE market = '{market}'
          AND code_int = {int(stock_code)}
          AND frequency = 'd'
          AND date >= '{query_start_date}'
          AND date <= '{query_end_date}'
        ORDER BY date
        """

        # 使用原生连接执行查询，避免pandas开销
        with db_manager.engine.connect() as conn:
            df = pd.read_sql(query, conn)

        if df.empty:
            return []

        # 优化数据处理：使用向量化操作替代循环
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df = df.fillna(0)

        # 直接转换为字典列表，避免逐行迭代
        result = df.to_dict('records')

        # 转换数值类型
        for item in result:
            item['open'] = float(item['open'])
            item['high'] = float(item['high'])
            item['low'] = float(item['low'])
            item['close'] = float(item['close'])
            item['volume'] = int(item['volume'])
            item['amount'] = float(item['amount'])
            item['pctChg'] = float(item['pctChg'])

        return result

    except Exception as e:
        print(f"查询K线数据失败: {str(e)}")
        return []


@app.route('/')
def index():
    """主页面"""
    return render_template('backtest_viewer.html')


@app.route('/api/strategies')
def get_strategies():
    """获取策略名称列表，支持按回测框架类型过滤"""
    try:
        backtest_framework = request.args.get('backtest_framework', '')
        strategies = db_manager.get_all_strategies(
            backtest_framework=backtest_framework if backtest_framework else None
        )
        return jsonify({
            'success': True,
            'data': strategies
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/backtest_types')
def get_backtest_types():
    """获取回测类型列表"""
    return jsonify({
        'success': True,
        'data': [
            {'value': 'time_based', 'label': '基于时间的回测'},
            {'value': 'backtrader', 'label': 'Backtrader回测'}
        ]
    })


@app.route('/api/summary_list')
def get_summary_list():
    """
    获取回测汇总列表
    参数:
        - strategy: 策略名称（可选）
        - backtest_framework: 回测框架类型（可选，time_based 或 backtrader）
    """
    try:
        strategy_name = request.args.get('strategy', '')
        backtest_framework = request.args.get('backtest_framework', '')

        results = db_manager.query_summary(
            strategy_name=strategy_name if strategy_name else None,
            backtest_framework=backtest_framework if backtest_framework else None
        )

        data = []
        for r in results:
            summary_data = json.loads(r.summary_json) if r.summary_json else {}
            data.append({
                'id': r.id,
                'strategy_name': r.strategy_name,
                'backtest_start_date': r.backtest_start_date.strftime('%Y-%m-%d'),
                'backtest_end_date': r.backtest_end_date.strftime('%Y-%m-%d'),
                'backtest_framework': r.backtest_framework,
                'stock_count': r.stock_count,
                'execution_time': float(r.execution_time) if r.execution_time else 0,
                'summary': summary_data,
                'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else ''
            })

        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/summary_detail')
def get_summary_detail():
    """
    获取回测汇总详情
    参数:
        - strategy: 策略名称
        - start_date: 回测开始日期
        - end_date: 回测结束日期
        - framework: 回测框架类型
    """
    try:
        strategy_name = request.args.get('strategy', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        framework = request.args.get('framework', 'backtrader')

        if not strategy_name or not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': '参数不完整'
            })

        result = db_manager.get_summary(strategy_name, start_date, end_date, framework)

        if not result:
            return jsonify({
                'success': False,
                'error': '未找到该回测记录'
            })

        summary_data = json.loads(result.summary_json) if result.summary_json else {}

        return jsonify({
            'success': True,
            'data': {
                'id': result.id,
                'strategy_name': result.strategy_name,
                'backtest_start_date': result.backtest_start_date.strftime('%Y-%m-%d'),
                'backtest_end_date': result.backtest_end_date.strftime('%Y-%m-%d'),
                'backtest_framework': result.backtest_framework,
                'stock_count': result.stock_count,
                'execution_time': float(result.execution_time) if result.execution_time else 0,
                'summary': summary_data,
                'created_at': result.created_at.strftime('%Y-%m-%d %H:%M:%S') if result.created_at else ''
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


# ============ Backtrader 相关接口（复用原有逻辑） ============

@app.route('/api/stocks')
def get_stocks():
    """获取指定策略的证券代码列表，支持分页"""
    try:
        strategy_name = request.args.get('strategy', '')
        stock_code_input = request.args.get('stock_code', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 14))

        stock_code = None
        market = None

        if stock_code_input:
            if '.' in stock_code_input:
                parts = stock_code_input.split('.')
                market = parts[0]
                stock_code = parts[1]
            else:
                market = determine_market_by_code(stock_code_input)
                stock_code = stock_code_input

            stock_code = str(stock_code).zfill(6)

        if strategy_name:
            results = db_manager.query_trigger_points(strategy_name=strategy_name)
        else:
            results = db_manager.query_trigger_points()

        if stock_code:
            results = [r for r in results if str(r.stock_code).zfill(6) == stock_code]
            if market:
                results = [r for r in results if r.market == market]

        stocks = list(set([f"{r.market}.{r.stock_code}" for r in results]))
        stocks.sort()

        # 计算分页
        total = len(stocks)
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        stocks_page = stocks[start_idx:end_idx]

        return jsonify({
            'success': True,
            'data': stocks_page,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/backtest_periods')
def get_backtest_periods():
    """获取回测时段列表"""
    try:
        strategy_name = request.args.get('strategy', '')
        stock_code = request.args.get('stock_code', '')

        if not strategy_name:
            return jsonify({
                'success': False,
                'error': '策略名称不能为空'
            })

        market = 'sh'
        code = stock_code
        if '.' in stock_code:
            parts = stock_code.split('.')
            market = parts[0]
            code = parts[1]
        else:
            market = determine_market_by_code(stock_code)
            code = stock_code  # 保持字符串类型，与数据库字段类型一致

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
    """获取触发点位列表"""
    try:
        strategy_name = request.args.get('strategy', '')
        stock_code = request.args.get('stock_code', '')
        backtest_period = request.args.get('backtest_period', '')

        if not strategy_name or not stock_code or not backtest_period:
            return jsonify({
                'success': False,
                'error': '参数不完整'
            })

        trigger_points = reader.get_backtest_data(
            strategy_name=strategy_name,
            stock_code=stock_code,
            backtest_period=backtest_period
        )

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
    """获取K线数据"""
    try:
        stock_code_full = request.args.get('stock_code', '')
        buy_date = request.args.get('start_date', '')
        sell_date = request.args.get('sell_date', None)

        if not stock_code_full or not buy_date:
            return jsonify({
                'success': False,
                'error': '参数不完整'
            })

        market = 'sh'
        stock_code = stock_code_full
        if '.' in stock_code_full:
            parts = stock_code_full.split('.')
            market = parts[0]
            stock_code = parts[1]
        else:
            market = determine_market_by_code(stock_code_full)
            stock_code = stock_code_full

        stock_code = str(stock_code).zfill(6)

        # 使用优化后的查询函数，复用数据库连接
        kline_data = get_kline_data_optimized(
            stock_code=stock_code,
            market=market,
            buy_date=buy_date,
            sell_date=sell_date
        )

        return jsonify({
            'success': True,
            'data': kline_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


# ============ Time Based 回测相关接口 ============

@app.route('/api/strategy_params')
def get_strategy_params():
    """
    获取策略参数
    参数:
        - strategy: 策略名称
        - start_date: 回测开始日期
        - end_date: 回测结束日期
    """
    try:
        strategy_name = request.args.get('strategy', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')

        if not strategy_name or not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': '参数不完整'
            })

        result = db_manager.get_summary(strategy_name, start_date, end_date, 'time_based')

        if not result:
            return jsonify({
                'success': False,
                'error': '未找到该回测记录'
            })

        summary_data = json.loads(result.summary_json) if result.summary_json else {}
        
        # 从 strategy_params_json 字段获取策略参数
        strategy_params = {}
        if result.strategy_params_json:
            try:
                strategy_params = json.loads(result.strategy_params_json)
            except:
                strategy_params = {}

        # 回测框架配置（从 summary_json 中提取）
        backtest_config = {}
        config_keys = ['initial_cash', 'commission', 'slippage_perc', 'max_positions', 'position_size_pct']
        for key in config_keys:
            if key in summary_data:
                backtest_config[key] = summary_data[key]

        return jsonify({
            'success': True,
            'data': {
                'strategy_params': strategy_params,
                'backtest_config': backtest_config
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/profit_chart')
def get_profit_chart():
    """
    获取收益曲线数据（策略收益 vs 基准收益）
    参数:
        - strategy: 策略名称
        - start_date: 回测开始日期
        - end_date: 回测结束日期
        - benchmark: 基准指数代码（如 sh000001, sz399001, sh000300, sh000852）
    """
    try:
        strategy_name = request.args.get('strategy', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        benchmark = request.args.get('benchmark', 'sh000001')

        if not strategy_name or not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': '参数不完整'
            })

        # 查询每日记录
        daily_records = db_manager.query_daily_records(
            strategy_name=strategy_name,
            backtest_start_date=start_date,
            backtest_end_date=end_date
        )

        if not daily_records:
            return jsonify({
                'success': True,
                'data': {
                    'dates': [],
                    'strategy_values': [],
                    'benchmark_values': [],
                    'total_assets': [],
                    'benchmark_prices': []
                }
            })

        # 构建策略收益曲线（直接使用profit_rate字段，保留两位小数）
        dates = []
        strategy_values = []
        total_assets = []

        for record in daily_records:
            dates.append(record.trade_date.strftime('%Y-%m-%d'))
            # 直接使用profit_rate，保留两位小数
            profit = float(record.profit_rate) if record.profit_rate is not None else 0
            strategy_values.append(round(profit, 2))
            # 总资产
            asset = float(record.total_asset) if record.total_asset is not None else 0
            total_assets.append(round(asset, 2))

        # 获取基准收益和价格
        benchmark_data = get_benchmark_returns(start_date, end_date, dates, benchmark)

        return jsonify({
            'success': True,
            'data': {
                'dates': dates,
                'strategy_values': strategy_values,
                'benchmark_values': benchmark_data['values'],
                'total_assets': total_assets,
                'benchmark_prices': benchmark_data['prices']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def get_benchmark_returns(start_date, end_date, target_dates, benchmark='sh000001'):
    """
    获取基准收益和价格
    参数:
        - start_date: 开始日期
        - end_date: 结束日期
        - target_dates: 目标日期列表
        - benchmark: 基准指数代码（如 sh000001）
    返回:
        - values: 相对于起始点的涨跌幅度（百分比）
        - prices: 基准指数原始数值
    """
    try:
        # 解析基准指数代码
        if benchmark.startswith('sh'):
            market = 'sh'
            code = benchmark[2:]
        elif benchmark.startswith('sz'):
            market = 'sz'
            code = benchmark[2:]
        else:
            market = 'sh'
            code = '000001'

        # 查询基准指数数据（包含收盘价）
        query = f"""
        SELECT date, pctChg, close
        FROM stock_daily_data
        WHERE market = '{market}'
          AND code_int = '{code}'
          AND frequency = 'd'
          AND date >= '{start_date}'
          AND date <= '{end_date}'
        ORDER BY date
        """

        df = pd.read_sql(query, db_manager.engine)

        if df.empty:
            return {
                'values': [0] * len(target_dates),
                'prices': [0] * len(target_dates)
            }

        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df.set_index('date', inplace=True)

        # 获取起始点价格
        first_date = target_dates[0] if target_dates else None
        base_price = None
        if first_date and first_date in df.index:
            base_price = float(df.loc[first_date, 'close']) if pd.notna(df.loc[first_date, 'close']) else None

        # 返回与策略日期对应的数据
        benchmark_values = []
        benchmark_prices = []

        for date in target_dates:
            if date in df.index:
                price = float(df.loc[date, 'close']) if pd.notna(df.loc[date, 'close']) else 0
                benchmark_prices.append(round(price, 2))
                
                # 计算相对于起始点的涨跌幅度
                if base_price and base_price > 0:
                    change_pct = ((price - base_price) / base_price) * 100
                    benchmark_values.append(round(change_pct, 2))
                else:
                    benchmark_values.append(0)
            else:
                benchmark_prices.append(0)
                benchmark_values.append(0)

        return {
            'values': benchmark_values,
            'prices': benchmark_prices
        }
    except Exception as e:
        print(f"获取基准收益失败: {str(e)}")
        return {
            'values': [0] * len(target_dates),
            'prices': [0] * len(target_dates)
        }


@app.route('/api/daily_records')
def get_daily_records():
    """
    获取回测每日记录
    参数:
        - strategy: 策略名称
        - start_date: 回测开始日期
        - end_date: 回测结束日期
    """
    try:
        strategy_name = request.args.get('strategy', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')

        if not strategy_name or not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': '参数不完整'
            })

        records = db_manager.query_daily_records(
            strategy_name=strategy_name,
            backtest_start_date=start_date,
            backtest_end_date=end_date
        )

        data = []
        for r in records:
            data.append({
                'trade_date': r.trade_date.strftime('%Y-%m-%d'),
                'buy_count': r.buy_count or 0,
                'sell_count': r.sell_count or 0,
                'is_no_action': r.is_no_action or 0,
                'total_asset': float(r.total_asset) if r.total_asset else 0,
                'profit_rate': float(r.profit_rate) if r.profit_rate else 0,
                'cash': float(r.cash) if r.cash else 0,
                'position_count': r.position_count or 0,
                'max_positions': r.max_positions or 5,
                'position_detail': r.position_detail
            })

        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


if __name__ == '__main__':
    web_config = config.get_web_config()
    # host='0.0.0.0' 表示监听所有网络接口，同时支持 127.0.0.1 和本地IP访问
    app.run(debug=True, host='0.0.0.0', port=5001)
