"""
回测记录查看器 Web 应用
用于展示 backtest_batch_summary 表中两种不同类型的回测记录：
- time_based: 基于时间的回测汇总展示
- backtrader: 触发点位和K线图展示
"""

from flask import Flask, render_template, jsonify, request, Response
import sys
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import threading
import io
import subprocess
import traceback
import random

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baostock_tool.database_schema.strategy_trigger_db import StrategyTriggerDB
from baostock_tool.utils.trigger_points_reader import TriggerPointsReader
from baostock_tool.webui.app import determine_market_by_code
from baostock_tool import config

# 配置静态文件和模板路径
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

# 初始化数据库管理器和数据读取器
db_manager = StrategyTriggerDB()
reader = TriggerPointsReader()

# 全局证券代码列表（启动时加载）
ALL_STOCK_CODES = []

def load_all_stock_codes():
    """
    启动时加载所有证券代码到内存
    """
    global ALL_STOCK_CODES
    try:
        print("📥 正在加载证券代码列表...")
        query = """
        SELECT DISTINCT code_int
        FROM stock_basic_info
        ORDER BY code_int
        """
        df = pd.read_sql(query, db_manager.engine)
        # 转换为字符串并补零到6位
        ALL_STOCK_CODES = df['code_int'].astype(str).str.zfill(6).tolist()
        print(f"✅ 已加载 {len(ALL_STOCK_CODES)} 个证券代码")
    except Exception as e:
        print(f"❌ 加载证券代码失败: {str(e)}")
        ALL_STOCK_CODES = []

# 启动时加载
load_all_stock_codes()


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
        market_filter = None

        if stock_code_input:
            if '.' in stock_code_input:
                parts = stock_code_input.split('.')
                market_filter = parts[0]
                stock_code = parts[1]
            else:
                market_filter = determine_market_by_code(stock_code_input)
                stock_code = stock_code_input

            stock_code = str(stock_code).zfill(6)

        # 使用优化的查询方法，在数据库层面去重，避免传输大量JSON数据
        stocks = db_manager.query_distinct_stocks(
            strategy_name=strategy_name if strategy_name else None,
            stock_code=stock_code,
            market=market_filter
        )

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


@app.route('/api/update_market_data', methods=['POST'])
def update_market_data():
    """
    执行市场数据更新操作（流式响应）
    """
    def generate():
        try:
            # 获取 update_market_data.py 的路径
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'update_market_data.py')

            yield f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行市场数据更新...\n"
            yield f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 脚本路径: {script_path}\n\n"

            # 使用 subprocess 执行脚本并实时输出
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )

            # 实时读取输出
            for line in process.stdout:
                yield line

            process.wait()

            if process.returncode == 0:
                yield f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 数据更新成功完成\n"
            else:
                yield f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 数据更新失败，退出码: {process.returncode}\n"

        except Exception as e:
            yield f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 执行异常: {str(e)}\n"

    return Response(generate(), mimetype='text/plain; charset=utf-8')


# ============ Kronos 预测相关接口 ============

@app.route('/api/stock_search')
def stock_search():
    """
    股票代码联想搜索API
    参数:
        - keyword: 搜索关键词（仅支持证券代码）
    返回:
        - 最多5个匹配的股票代码（补零到6位）
    """
    try:
        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return jsonify({'success': True, 'data': []})

        # 只支持数字搜索
        if not keyword.isdigit():
            return jsonify({'success': True, 'data': []})

        # 从内存中匹配证券代码
        # 直接用输入的关键词匹配（代码已补零到6位）
        # 如输入"0009"匹配"0009xx"，输入"9"匹配"000009"、"000019"等
        keyword_padded = keyword.zfill(6)
        matches = [code for code in ALL_STOCK_CODES if code.startswith(keyword) or code.startswith(keyword_padded)]
        
        # 去重并排序
        matches = sorted(set(matches))
        
        # 最多返回5个结果
        results = [{'code': code, 'display': code} for code in matches[:5]]

        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/kronos_predict', methods=['POST'])
def kronos_predict():
    """
    Kronos预测API
    参数(JSON body):
        - stock_code: 证券代码（6位数字）
        - lookback_days: 加载历史天数
        - pred_days: 预测天数
        - temperature: 温度参数
        - top_p: 采样概率
        - sample_count: 采样次数
    """
    try:
        data = request.get_json()
        stock_code = data.get('stock_code', '')
        lookback_days = int(data.get('lookback_days', 60))
        pred_days = int(data.get('pred_days', 5))
        temperature = float(data.get('temperature', 0.5))
        top_p = float(data.get('top_p', 0.5))
        sample_count = int(data.get('sample_count', 5))

        # 参数验证
        if not stock_code:
            return jsonify({'success': False, 'error': '证券代码不能为空'})
        if lookback_days < 20 or lookback_days > 220:
            return jsonify({'success': False, 'error': '加载历史天数必须在20-220之间'})
        if pred_days < 5 or pred_days > 20:
            return jsonify({'success': False, 'error': '预测天数必须在5-20之间'})
        if temperature < 0.1 or temperature > 1.0:
            return jsonify({'success': False, 'error': '温度参数必须在0.1-1.0之间'})
        if top_p < 1 or top_p > 10:
            return jsonify({'success': False, 'error': '采样概率必须在1-10之间'})
        if sample_count < 1 or sample_count > 10:
            return jsonify({'success': False, 'error': '采样次数必须在1-10之间'})

        # 确定市场
        market = determine_market_by_code(stock_code)

        # 查询最新日期
        max_date_query = f"""
        SELECT MAX(date) as max_date FROM stock_daily_data
        WHERE code_int = {int(stock_code)} AND market = '{market}' AND frequency = 'd'
        """
        max_date_result = pd.read_sql(max_date_query, db_manager.engine)
        if max_date_result.empty or max_date_result['max_date'].iloc[0] is None:
            return jsonify({'success': False, 'error': '未找到该股票的历史数据'})

        max_date = max_date_result['max_date'].iloc[0]
        start_date = (max_date - timedelta(days=lookback_days * 1.5)).strftime('%Y-%m-%d')
        end_date = max_date.strftime('%Y-%m-%d')

        # 查询历史K线数据
        hist_query = f"""
        SELECT date, open, high, low, close, volume, amount, pctChg
        FROM stock_daily_data
        WHERE market = '{market}'
          AND code_int = {int(stock_code)}
          AND frequency = 'd'
          AND date >= '{start_date}'
          AND date <= '{end_date}'
        ORDER BY date DESC
        LIMIT {lookback_days}
        """
        hist_df = pd.read_sql(hist_query, db_manager.engine)
        hist_df = hist_df.sort_values('date').reset_index(drop=True)

        if hist_df.empty:
            return jsonify({'success': False, 'error': '未找到足够的历史数据'})

        # 构建历史K线数据
        historical_data = []
        for _, row in hist_df.iterrows():
            historical_data.append({
                'date': row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], datetime) else str(row['date']),
                'open': float(row['open']) if pd.notna(row['open']) else 0,
                'high': float(row['high']) if pd.notna(row['high']) else 0,
                'low': float(row['low']) if pd.notna(row['low']) else 0,
                'close': float(row['close']) if pd.notna(row['close']) else 0,
                'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
                'amount': float(row['amount']) if pd.notna(row['amount']) else 0,
                'pctChg': float(row['pctChg']) if pd.notna(row['pctChg']) else 0,
                'isPrediction': False
            })

        # 获取股票名称
        name_query = f"""
        SELECT name FROM stock_basic_info
        WHERE code_int = {int(stock_code)} AND market = '{market}'
        LIMIT 1
        """
        name_df = pd.read_sql(name_query, db_manager.engine)
        stock_name = name_df['name'].iloc[0] if not name_df.empty else 'Unknown'

        # 调用Kronos模型进行预测
        try:
            from baostock_tool.kronos_master.kronos_service import KronosPredictorService, KronosConfig

            kronos_config = KronosConfig(
                lookback=lookback_days,
                pred_len=pred_days,
                temperature=temperature,
                top_p=top_p / 10.0,  # 转换为0.1-1.0范围
                sample_count=sample_count,
                device='cpu'
            )
            service = KronosPredictorService(kronos_config)
            result = service.predict(f"{market}.{stock_code}", output_dir=None, save_csv=False, save_chart=False)

            # 构建预测K线数据
            prediction_data = []
            for _, row in result.prediction_df.iterrows():
                date_val = row['date']
                if isinstance(date_val, datetime):
                    date_str = date_val.strftime('%Y-%m-%d')
                elif hasattr(date_val, 'strftime'):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)
                prediction_data.append({
                    'date': date_str,
                    'open': float(row['open']) if pd.notna(row['open']) else 0,
                    'high': float(row['high']) if pd.notna(row['high']) else 0,
                    'low': float(row['low']) if pd.notna(row['low']) else 0,
                    'close': float(row['close']) if pd.notna(row['close']) else 0,
                    'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
                    'amount': float(row['amount']) if pd.notna(row['amount']) else 0,
                    'pctChg': 0,
                    'isPrediction': True
                })

            last_close = result.last_close
            pred_change_pct = result.predicted_change_pct

        except ImportError as ie:
            # 如果Kronos模块未安装，生成模拟预测数据
            print(f"Kronos模块未安装: {ie}")
            prediction_data = generate_mock_prediction(historical_data, pred_days, stock_code, market)
            last_close = historical_data[-1]['close'] if historical_data else 0
            pred_change_pct = 0
        except Exception as e:
            print(f"预测出错: {e}")
            traceback.print_exc()
            prediction_data = generate_mock_prediction(historical_data, pred_days, stock_code, market)
            last_close = historical_data[-1]['close'] if historical_data else 0
            pred_change_pct = 0

        return jsonify({
            'success': True,
            'data': {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'market': market,
                'historical': historical_data,
                'prediction': prediction_data,
                'last_close': last_close,
                'pred_change_pct': pred_change_pct,
                'pred_days': pred_days
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def generate_mock_prediction(historical_data, pred_days, stock_code, market):
    """生成模拟预测数据（当Kronos模型不可用时使用）"""
    if not historical_data:
        return []

    last_date_str = historical_data[-1]['date']
    last_close = historical_data[-1]['close']

    try:
        last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
    except:
        last_date = datetime.now()

    predictions = []
    current_date = last_date
    current_close = last_close

    for i in range(pred_days):
        # 跳过周末
        current_date = current_date + timedelta(days=1)
        while current_date.weekday() >= 5:  # 周六、周日
            current_date = current_date + timedelta(days=1)

        # 生成随机波动
        change_pct = random.uniform(-0.03, 0.03)  # -3% 到 +3%
        current_close = current_close * (1 + change_pct)

        open_price = current_close * (1 + random.uniform(-0.01, 0.01))
        high_price = max(open_price, current_close) * (1 + random.uniform(0, 0.01))
        low_price = min(open_price, current_close) * (1 - random.uniform(0, 0.01))

        predictions.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(current_close, 2),
            'volume': 0,
            'amount': 0,
            'pctChg': round(change_pct * 100, 2),
            'isPrediction': True
        })

    return predictions


if __name__ == '__main__':
    web_config = config.get_web_config()
    # host='0.0.0.0' 表示监听所有网络接口，同时支持 127.0.0.1 和本地IP访问
    app.run(debug=True, host='0.0.0.0', port=5001)
