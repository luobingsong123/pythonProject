from flask import Flask, render_template, jsonify, request
import pymysql
from datetime import datetime, timedelta
import pandas as pd
import configparser
from backtest_platform.utils.logger_utils import setup_logger
import os

# 配置获取
config_path = os.path.join("../config/config.ini")
# 检查文件是否存在
if not os.path.exists(config_path):
    raise FileNotFoundError(f"配置文件 {config_path} 未找到！")
# 创建配置解析器
config = configparser.ConfigParser()
config.read(config_path, encoding="utf-8")  # 注意编码，避免中文乱码

# 配置日志
logger = setup_logger(logger_name=__name__,
                      log_level=config.get("logging","level"),
                      log_dir=config.get("logging","log_dir"),)

app = Flask(__name__)

# 数据库配置
DB_CONFIG = {
    'host': config.get("database", "host"),
    'port': config.getint("database", "port"),
    'user': config.get("database", "username"),
    'password': config.get("database", "password"),
    'database': config.get("database", "database"),  # 修改为新数据库名
    'charset': 'utf8mb4'
}


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/stocks')
def get_stock_list():
    """获取股票列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 获取股票基本信息列表
        query = """
        SELECT sbi.market, sbi.code_int, sbi.name, sbi.industry, sbi.area
        FROM stock_basic_info sbi
        ORDER BY sbi.market, sbi.code_int
        LIMIT 100  -- 限制返回数量，可根据需要调整
        """

        cursor.execute(query)
        stocks = cursor.fetchall()

        # 格式化股票代码（添加市场前缀和补零）
        for stock in stocks:
            stock['full_code'] = f"{stock['market']}.{str(stock['code_int']).zfill(6)}"

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'data': stocks})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/kline')
def get_kline_data():
    """获取K线数据"""
    try:
        # 获取请求参数
        market = request.args.get('market', 'sh')
        code_int = request.args.get('code_int', '000001')
        frequency = request.args.get('frequency', 'd')  # d, 5, 15, 30
        limit = int(request.args.get('limit', '100'))  # 数据条数限制

        # 验证参数
        if frequency not in ['d', '5', '15', '30']:
            return jsonify({'success': False, 'error': '不支持的频率类型'})

        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        if frequency == 'd':
            # 日线数据
            query = """
            SELECT date, open, high, low, close, volume, amount, pctChg
            FROM stock_daily_data 
            WHERE market = %s AND code_int = %s AND frequency = 'd'
            ORDER BY date DESC 
            LIMIT %s
            """
        else:
            # 分钟线数据（获取最近一天的数据）
            target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            query = """
            SELECT CONCAT(date, ' ', time) as datetime, open, high, low, close, volume, amount
            FROM stock_minute_data 
            WHERE market = %s AND code_int = %s AND frequency = %s 
            AND date = %s
            ORDER BY datetime DESC 
            LIMIT %s
            """
            cursor.execute(query, (market, int(code_int), int(frequency), target_date, limit))
            result = cursor.fetchall()

            # 如果没有当天数据，获取最近有数据的日期
            if not result:
                date_query = """
                SELECT DISTINCT date 
                FROM stock_minute_data 
                WHERE market = %s AND code_int = %s AND frequency = %s 
                ORDER BY date DESC 
                LIMIT 1
                """
                cursor.execute(date_query, (market, int(code_int), int(frequency)))
                date_result = cursor.fetchone()
                if date_result:
                    target_date = date_result['date'].strftime('%Y-%m-%d')
                    cursor.execute(query, (market, int(code_int), int(frequency), target_date, limit))
                    result = cursor.fetchall()

        if frequency == 'd':
            cursor.execute(query, (market, int(code_int), limit))
            result = cursor.fetchall()

        # 格式化数据
        kline_data = []
        for row in result:
            if frequency == 'd':
                timestamp = int(pd.to_datetime(row['date']).timestamp() * 1000)
            else:
                timestamp = int(pd.to_datetime(row['datetime']).timestamp() * 1000)

            kline_data.append([
                timestamp,  # 时间戳
                float(row['open']),
                float(row['close']),
                float(row['low']),
                float(row['high']),
                int(row['volume'])
            ])

        # 反转数据（按时间正序）
        kline_data.reverse()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'data': kline_data,
            'frequency': frequency,
            'stock': f"{market}.{str(code_int).zfill(6)}"
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/stock_info')
def get_stock_info():
    """获取股票基本信息"""
    try:
        market = request.args.get('market', 'sh')
        code_int = request.args.get('code_int', '000001')

        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        query = """
        SELECT name, industry, area, list_date, is_hs
        FROM stock_basic_info 
        WHERE market = %s AND code_int = %s
        """

        cursor.execute(query, (market, int(code_int)))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': '股票信息未找到'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    app.run(host=config.get("webserver","host"), port=config.getint("webserver","port"), debug=True)
