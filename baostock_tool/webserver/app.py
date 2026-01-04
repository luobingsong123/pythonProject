"""
Flask K线图与指标展示应用
此应用提供一个三区域界面：
1. 左侧：策略列表展示
2. 上方：搜索栏
3. 中间：K线图与成交量图
4. 右侧：技术指标选择
"""

from flask import Flask, render_template, jsonify, request
import json
import os
from datetime import datetime, timedelta
import random

app = Flask(__name__)

# 模拟策略数据
STRATEGIES = [
    {"id": 1, "name": "趋势跟踪策略", "description": "基于移动平均线的趋势跟踪", "status": "active", "created_at": "2024-01-15"},
    {"id": 2, "name": "均值回归策略", "description": "基于布林带的均值回归交易", "status": "paused", "created_at": "2024-01-20"},
    {"id": 3, "name": "动量突破策略", "description": "基于价格动量突破", "status": "active", "created_at": "2024-01-25"},
    {"id": 4, "name": "波动率策略", "description": "基于ATR的波动率突破", "status": "active", "created_at": "2024-02-01"},
    {"id": 5, "name": "网格交易策略", "description": "固定价差网格交易", "status": "active", "created_at": "2024-02-05"},
    {"id": 6, "name": "套利策略", "description": "跨市场套利策略", "status": "paused", "created_at": "2024-02-10"},
    {"id": 7, "name": "高频策略", "description": "高频做市策略", "status": "active", "created_at": "2024-02-15"},
    {"id": 8, "name": "机器学习策略", "description": "基于随机森林的预测模型", "status": "active", "created_at": "2024-02-20"},
]

# 技术指标列表
TECHNICAL_INDICATORS = [
    {"id": "ma", "name": "移动平均线(MA)", "description": "简单移动平均线"},
    {"id": "ema", "name": "指数移动平均线(EMA)", "description": "指数移动平均线"},
    {"id": "macd", "name": "MACD", "description": "异同移动平均线"},
    {"id": "boll", "name": "布林带(BOLL)", "description": "布林带指标"},
    {"id": "kdj", "name": "KDJ", "description": "随机指标"},
    {"id": "rsi", "name": "RSI", "description": "相对强弱指数"},
    {"id": "volume", "name": "成交量指标", "description": "成交量柱状图"},
    {"id": "atr", "name": "ATR", "description": "平均真实波幅"},
]


def generate_kline_data(days=100):
    """生成模拟K线数据"""
    data = []
    base_price = 100  # 初始价格
    base_time = datetime.now() - timedelta(days=days)

    for i in range(days):
        date = base_time + timedelta(days=i)

        # 模拟价格波动
        open_price = base_price
        close_price = open_price + random.uniform(-5, 5)
        high_price = max(open_price, close_price) + random.uniform(0, 3)
        low_price = min(open_price, close_price) - random.uniform(0, 3)

        # 确保高低价正确
        high_price = max(open_price, close_price, high_price)
        low_price = min(open_price, close_price, low_price)

        # 模拟成交量
        volume = random.randint(10000, 50000)

        data.append({
            "time": date.strftime("%Y-%m-%d"),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume
        })

        # 更新基础价格
        base_price = close_price

    return data


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/strategies')
def get_strategies():
    """获取策略列表API"""
    search_query = request.args.get('search', '').lower()

    if search_query:
        filtered_strategies = [s for s in STRATEGIES if search_query in s['name'].lower()]
    else:
        filtered_strategies = STRATEGIES

    return jsonify({
        "success": True,
        "data": filtered_strategies,
        "total": len(filtered_strategies)
    })


@app.route('/api/kline-data')
def get_kline_data():
    """获取K线数据API"""
    days = int(request.args.get('days', 100))
    kline_data = generate_kline_data(days)

    return jsonify({
        "success": True,
        "data": kline_data
    })


@app.route('/api/indicators')
def get_indicators():
    """获取技术指标列表API"""
    return jsonify({
        "success": True,
        "data": TECHNICAL_INDICATORS
    })


@app.route('/api/indicator-data/<indicator_id>')
def get_indicator_data(indicator_id):
    """获取特定指标数据API（模拟）"""
    # 生成模拟指标数据
    days = int(request.args.get('days', 100))
    kline_data = generate_kline_data(days)

    indicator_data = []

    for i, candle in enumerate(kline_data):
        close_price = candle['close']

        # 根据指标类型生成模拟数据
        if indicator_id == 'ma':
            # 移动平均线
            if i >= 9:  # 10日移动平均
                ma_value = sum([kline_data[j]['close'] for j in range(i - 9, i + 1)]) / 10
                indicator_data.append({
                    "time": candle['time'],
                    "value": round(ma_value, 2)
                })
        elif indicator_id == 'ema':
            # 指数移动平均线
            if i >= 9:  # 10日指数移动平均
                ema_value = close_price * 0.2 + (kline_data[i - 1]['close'] if i > 0 else close_price) * 0.8
                indicator_data.append({
                    "time": candle['time'],
                    "value": round(ema_value, 2)
                })
        elif indicator_id == 'boll':
            # 布林带
            if i >= 19:  # 20日布林带
                closes = [kline_data[j]['close'] for j in range(i - 19, i + 1)]
                ma = sum(closes) / 20
                std = (sum([(c - ma) ** 2 for c in closes]) / 20) ** 0.5
                indicator_data.append({
                    "time": candle['time'],
                    "upper": round(ma + 2 * std, 2),  # 上轨
                    "middle": round(ma, 2),  # 中轨
                    "lower": round(ma - 2 * std, 2)  # 下轨
                })

    return jsonify({
        "success": True,
        "indicator_id": indicator_id,
        "data": indicator_data
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)