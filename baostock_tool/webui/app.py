"""
WebUI Flask应用
用于展示策略触发点位K线图
"""

from flask import Flask, render_template, jsonify, request
from database_schema.strategy_trigger_db import StrategyTriggerDB
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import pandas as pd
import config
import json
from utils.logger_utils import setup_logger

log_config = config.get_log_config()
logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"])

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# 数据库连接
db_config_ = config.get_db_config()
db_url = URL.create(
    drivername="mysql+pymysql",
    username=db_config_["user"],
    password=db_config_["password"],
    host=db_config_["host"],
    port=db_config_["port"],
    database=db_config_["database"]
)
engine = create_engine(db_url)

# 初始化策略触发点位数据库
strategy_db = StrategyTriggerDB()


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/strategies')
def get_strategies():
    """获取所有策略名称"""
    try:
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import func
        Session = sessionmaker(bind=strategy_db.engine)
        session = Session()

        strategies = session.query(
            StrategyTriggerPoints.strategy_name,
            func.count(StrategyTriggerPoints.id).label('stock_count')
        ).group_by(StrategyTriggerPoints.strategy_name).all()

        result = [{'strategy_name': s.strategy_name, 'stock_count': s.stock_count} for s in strategies]
        session.close()

        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"获取策略列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/stocks')
def get_stocks():
    """获取指定策略的股票列表"""
    try:
        strategy_name = request.args.get('strategy_name')
        if not strategy_name:
            return jsonify({
                'success': False,
                'message': 'strategy_name参数缺失'
            }), 400

        results = strategy_db.query_trigger_points(strategy_name=strategy_name)

        stocks = []
        for result in results:
            stocks.append({
                'stock_code': result.stock_code,
                'market': result.market,
                'trigger_count': result.trigger_count,
                'backtest_start_date': str(result.backtest_start_date),
                'backtest_end_date': str(result.backtest_end_date)
            })

        return jsonify({
            'success': True,
            'data': stocks
        })
    except Exception as e:
        logger.error(f"获取股票列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/trigger_points')
def get_trigger_points():
    """获取指定股票的触发点位"""
    try:
        strategy_name = request.args.get('strategy_name')
        stock_code = request.args.get('stock_code')
        market = request.args.get('market')

        if not all([strategy_name, stock_code, market]):
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400

        results = strategy_db.query_trigger_points(
            strategy_name=strategy_name,
            stock_code=stock_code,
            market=market
        )

        if not results:
            return jsonify({
                'success': False,
                'message': '未找到触发点位数据'
            }), 404

        result = results[0]

        return jsonify({
            'success': True,
            'data': {
                'strategy_name': result.strategy_name,
                'stock_code': result.stock_code,
                'market': result.market,
                'backtest_start_date': str(result.backtest_start_date),
                'backtest_end_date': str(result.backtest_end_date),
                'trigger_count': result.trigger_count,
                'trigger_points': result.trigger_points_json
            }
        })
    except Exception as e:
        logger.error(f"获取触发点位失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/kline_data')
def get_kline_data():
    """获取K线数据（触发点位前后50个交易日）"""
    try:
        strategy_name = request.args.get('strategy_name')
        stock_code = request.args.get('stock_code')
        market = request.args.get('market')
        trigger_index = request.args.get('trigger_index', type=int)
        bars_before = request.args.get('bars_before', 50, type=int)
        bars_after = request.args.get('bars_after', 50, type=int)

        if not all([strategy_name, stock_code, market, trigger_index is not None]):
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400

        # 获取触发点位数据
        results = strategy_db.query_trigger_points(
            strategy_name=strategy_name,
            stock_code=stock_code,
            market=market
        )

        if not results or len(results[0].trigger_points_json) <= trigger_index:
            return jsonify({
                'success': False,
                'message': '触发点位索引无效'
            }), 400

        trigger_point = results[0].trigger_points_json[trigger_index]
        trigger_date = pd.to_datetime(trigger_point['date'])

        # 计算需要的日期范围
        # 前后各50个交易日，总共100天，考虑到节假日可能更多，取120天
        start_date = trigger_date - pd.Timedelta(days=120)
        end_date = trigger_date + pd.Timedelta(days=120)

        # 从数据库获取K线数据
        query = f"""
        SELECT date, open, high, low, close, volume, amount
        FROM stock_daily_data
        WHERE market = '{market}'
          AND code_int = {stock_code}
          AND frequency = 'd'
          AND date >= '{start_date.strftime('%Y-%m-%d')}'
          AND date <= '{end_date.strftime('%Y-%m-%d')}'
        ORDER BY date
        """

        df = pd.read_sql(query, engine)
        if df.empty:
            return jsonify({
                'success': False,
                'message': '未找到K线数据'
            }), 404

        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # 找到触发点位的索引
        try:
            trigger_idx = df.index.get_loc(trigger_date)
        except KeyError:
            # 如果触发日期不是交易日，找到最近的交易日
            trigger_idx = df.index.get_indexer([trigger_date], method='nearest')[0]
            trigger_date = df.index[trigger_idx]

        # 提取前后N个交易日
        start_idx = max(0, trigger_idx - bars_before)
        end_idx = min(len(df), trigger_idx + bars_after + 1)

        kline_df = df.iloc[start_idx:end_idx]

        # 转换为前端可用的格式
        kline_data = []
        for idx, row in kline_df.iterrows():
            kline_data.append({
                'date': idx.strftime('%Y-%m-%d'),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']),
                'amount': float(row['amount']) if 'amount' in row else 0
            })

        # 标记触发点位位置
        trigger_idx_in_data = trigger_idx - start_idx

        return jsonify({
            'success': True,
            'data': {
                'strategy_name': strategy_name,
                'stock_code': stock_code,
                'market': market.upper(),
                'trigger_date': trigger_date.strftime('%Y-%m-%d'),
                'trigger_type': trigger_point.get('trigger_type', 'unknown'),
                'trigger_price': trigger_point.get('price', 0),
                'trigger_index': trigger_idx_in_data,
                'kline_data': kline_data,
                'trigger_info': trigger_point
            }
        })
    except Exception as e:
        logger.error(f"获取K线数据失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/statistics')
def get_statistics():
    """获取统计信息"""
    try:
        stats = strategy_db.get_statistics()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


if __name__ == '__main__':
    # 使用配置文件中的设置
    web_config = config.get_web_config()
    logger.info(f"启动WebUI服务: {web_config['host']}:{web_config['port']}")
    app.run(
        host=web_config['host'],
        port=web_config['port'],
        debug=True
    )
