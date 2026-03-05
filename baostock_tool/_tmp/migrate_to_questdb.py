#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本：从MySQL迁移到QuestDB (CSV方式)
表名: stock_daily_data

使用方法:
    python migrate_to_questdb.py

注意事项:
    1. 需要安装依赖: pip install pymysql requests
    2. QuestDB HTTP端口: 9000
    3. 先导出CSV，再导入QuestDB，内存占用低
"""

import pymysql
import requests
import time
import os
import csv
from datetime import datetime
from decimal import Decimal

# ============== 配置区域 ==============
# MySQL配置
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'qq852631192',
    'database': 'baostock_api_market_data',
    'charset': 'utf8mb4'
}

# QuestDB配置 (使用HTTP REST API)
QUESTDB_CONFIG = {
    'host': 'localhost',
    'port': 9000,           # HTTP端口
    'user': '',             # 没设置用户则为空
    'password': ''          # 没设置密码则为空
}

# CSV文件路径
CSV_FILE_PATH = 'stock_daily_data_export.csv'

# 导出配置
EXPORT_BATCH_SIZE = 50000  # 每批导出行数
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def get_mysql_connection():
    """获取MySQL连接"""
    return pymysql.connect(**MYSQL_CONFIG)


def questdb_request(endpoint, params=None, files=None, retry=3):
    """执行QuestDB HTTP请求"""
    url = f"http://{QUESTDB_CONFIG['host']}:{QUESTDB_CONFIG['port']}{endpoint}"
    auth = None
    if QUESTDB_CONFIG['user']:
        auth = (QUESTDB_CONFIG['user'], QUESTDB_CONFIG['password'])
    
    for attempt in range(retry):
        try:
            if files:
                response = requests.post(url, files=files, auth=auth, timeout=300)
            elif params:
                response = requests.get(url, params=params, auth=auth, timeout=120)
            else:
                response = requests.get(url, auth=auth, timeout=120)
            
            if response.status_code == 200:
                return response.text
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(1)
                continue
            raise Exception(f"QuestDB请求失败: {e}")


def get_total_count():
    """获取MySQL总数据量"""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM stock_daily_data")
            return cursor.fetchone()[0]
    finally:
        conn.close()


def export_to_csv():
    """从MySQL导出数据到CSV文件"""
    print(f"[INFO] 开始导出MySQL数据到CSV...")
    
    total = get_total_count()
    print(f"[INFO] MySQL总数据量: {total:,}")
    
    conn = get_mysql_connection()
    conn.cursorclass = pymysql.cursors.DictCursor
    
    query = """
    SELECT date, market, code_int, frequency, open, high, low, close,
           preclose, volume, amount, adjustflag, turn, tradestatus,
           pctChg, peTTM, psTTM, pcfNcfTTM, pbMRQ, isST,
           created_at, updated_at
    FROM stock_daily_data
    ORDER BY date, market, code_int, frequency
    """
    
    start_time = time.time()
    exported = 0
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            
            with open(CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow([
                    'date', 'market', 'code_int', 'frequency', 'open', 'high', 'low', 'close',
                    'preclose', 'volume', 'amount', 'adjustflag', 'turn', 'tradestatus',
                    'pctChg', 'peTTM', 'psTTM', 'pcfNcfTTM', 'pbMRQ', 'isST',
                    'created_at', 'updated_at'
                ])
                
                while True:
                    rows = cursor.fetchmany(EXPORT_BATCH_SIZE)
                    if not rows:
                        break
                    
                    for row in rows:
                        writer.writerow([
                            format_value(row['date']),
                            row['market'],
                            row['code_int'],
                            row['frequency'],
                            format_value(row['open']),
                            format_value(row['high']),
                            format_value(row['low']),
                            format_value(row['close']),
                            format_value(row['preclose']),
                            row['volume'],
                            format_value(row['amount']),
                            row['adjustflag'],
                            format_value(row['turn']),
                            row['tradestatus'],
                            format_value(row['pctChg']),
                            format_value(row['peTTM']),
                            format_value(row['psTTM']),
                            format_value(row['pcfNcfTTM']),
                            format_value(row['pbMRQ']),
                            row['isST'] if row['isST'] else 0,
                            format_value(row['created_at']),
                            format_value(row['updated_at'])
                        ])
                    
                    exported += len(rows)
                    progress = (exported / total) * 100
                    elapsed = time.time() - start_time
                    speed = exported / elapsed if elapsed > 0 else 0
                    
                    print(f"\r[PROGRESS] {exported:,}/{total:,} ({progress:.2f}%) - 速度: {speed:.0f} 行/秒", end='')
    
    finally:
        conn.close()
    
    elapsed = time.time() - start_time
    file_size = os.path.getsize(CSV_FILE_PATH) / (1024 * 1024)
    print(f"\n[INFO] CSV导出完成! 文件大小: {file_size:.2f}MB, 耗时: {elapsed:.2f}秒")


def format_value(value):
    """格式化值"""
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.strftime(DATETIME_FORMAT)
    if isinstance(value, Decimal):
        return float(value)
    return value


def create_table():
    """创建QuestDB表"""
    # 先删除已存在的表（如果需要重新导入）
    try:
        questdb_request('/exec', params={'query': 'DROP TABLE IF EXISTS stock_daily_data'})
    except:
        pass
    
    ddl = """
    CREATE TABLE stock_daily_data (
        date TIMESTAMP,
        market SYMBOL,
        code_int INT,
        frequency SYMBOL,
        open DOUBLE,
        high DOUBLE,
        low DOUBLE,
        close DOUBLE,
        preclose DOUBLE,
        volume LONG,
        amount DOUBLE,
        adjustflag INT,
        turn DOUBLE,
        tradestatus INT,
        pctChg DOUBLE,
        peTTM DOUBLE,
        psTTM DOUBLE,
        pcfNcfTTM DOUBLE,
        pbMRQ DOUBLE,
        isST INT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    ) TIMESTAMP(date) PARTITION BY YEAR;
    """
    questdb_request('/exec', params={'query': ddl.strip()})
    print("[INFO] QuestDB表创建成功")


def import_csv_to_questdb():
    """将CSV文件导入QuestDB"""
    print(f"[INFO] 开始导入CSV到QuestDB...")
    
    file_size = os.path.getsize(CSV_FILE_PATH) / (1024 * 1024)
    print(f"[INFO] CSV文件大小: {file_size:.2f}MB")
    
    start_time = time.time()
    
    # 使用QuestDB的/imp端点导入CSV
    url = f"http://{QUESTDB_CONFIG['host']}:{QUESTDB_CONFIG['port']}/imp"
    auth = None
    if QUESTDB_CONFIG['user']:
        auth = (QUESTDB_CONFIG['user'], QUESTDB_CONFIG['password'])
    
    # 导入参数
    params = {
        'name': 'stock_daily_data',
        'timestamp': 'date',
        'partitionBy': 'YEAR',
        'overwrite': 'false',  # 追加模式
        'skipLinesWithErrors': 'true'
    }
    
    with open(CSV_FILE_PATH, 'rb') as f:
        response = requests.post(url, files={'data': f}, params=params, auth=auth, timeout=600)
    
    if response.status_code != 200:
        raise Exception(f"导入失败: HTTP {response.status_code}: {response.text}")
    
    elapsed = time.time() - start_time
    print(f"[INFO] CSV导入完成! 耗时: {elapsed:.2f}秒")
    print(f"[INFO] 响应: {response.text[:500]}")


def verify_data():
    """验证数据"""
    print("\n[INFO] 验证数据...")
    
    mysql_conn = get_mysql_connection()
    
    try:
        # MySQL数量
        with mysql_conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM stock_daily_data")
            mysql_count = cursor.fetchone()[0]
        
        # QuestDB数量
        result = questdb_request('/exec', params={'query': 'SELECT COUNT(*) FROM stock_daily_data'})
        import json
        try:
            data = json.loads(result)
            questdb_count = data[0][0] if data and len(data) > 0 else 0
        except:
            questdb_count = 0
        
        print(f"[INFO] MySQL数据量: {mysql_count:,}")
        print(f"[INFO] QuestDB数据量: {questdb_count:,}")
        
        if mysql_count == questdb_count:
            print("[SUCCESS] 数据迁移验证通过!")
        else:
            print(f"[WARNING] 数据量不一致，差异: {mysql_count - questdb_count}")
            
    finally:
        mysql_conn.close()


def cleanup():
    """清理临时文件"""
    if os.path.exists(CSV_FILE_PATH):
        os.remove(CSV_FILE_PATH)
        print(f"[INFO] 已删除临时CSV文件: {CSV_FILE_PATH}")


if __name__ == '__main__':
    print("=" * 50)
    print("MySQL -> QuestDB 数据迁移工具 (CSV方式)")
    print("=" * 50)
    
    try:
        # 步骤1: 导出MySQL数据到CSV
        print("\n[STEP 1] 导出MySQL数据到CSV...")
        export_to_csv()
        
        # 步骤2: 创建QuestDB表
        print("\n[STEP 2] 创建QuestDB表...")
        create_table()
        
        # 步骤3: 导入CSV到QuestDB
        print("\n[STEP 3] 导入CSV到QuestDB...")
        import_csv_to_questdb()
        
        # 步骤4: 验证
        print("\n[STEP 4] 验证数据...")
        verify_data()
        
        # 步骤5: 清理
        print("\n[STEP 5] 清理临时文件...")
        cleanup()
        
        print("\n" + "=" * 50)
        print("迁移完成!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[ERROR] 迁移失败: {e}")
        raise
