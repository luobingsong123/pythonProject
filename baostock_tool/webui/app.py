"""
策略触发点位可视化Web应用
提供策略、证券代码、回测时段、触发点位的层级查询界面
"""

from flask import Flask, render_template, jsonify, request
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baostock_tool.database_schema.strategy_trigger_db import StrategyTriggerDB
from baostock_tool.utils.trigger_points_reader import TriggerPointsReader

app = Flask(__name__)

# 初始化数据库管理器和数据读取器
db_manager = StrategyTriggerDB()
reader = TriggerPointsReader()


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
    """
    try:
        strategy_name = request.args.get('strategy', '')

        if strategy_name:
            # 查询指定策略的证券代码
            results = db_manager.query_trigger_points(strategy_name=strategy_name)
            stocks = list(set([f"{r.market}.{r.stock_code}" for r in results]))
        else:
            # 查询所有证券代码
            results = db_manager.query_trigger_points()
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

        # 解析证券代码（去除市场前缀）
        market = 'sh'
        code = stock_code
        if '.' in stock_code:
            parts = stock_code.split('.')
            market = parts[0]
            code = parts[1]

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
            key=lambda x: (x[1].get('买入点位：', ''), x[0])
        )

        result = []
        for key, point in sorted_points:
            result.append({
                'key': key,
                'buy_date': point.get('买入', ''),
                'sell_date': point.get('卖出', ''),
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
